"""LinkedIn OAuth 2.0 Token Generator & Setup Helper.
Starts a local callback server, opens browser for authorization, fetches the
OAuth 2.0 Access Token and Person URN, and outputs the exact JSON configuration
to put in your mcp_config.json env block.
"""

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import sys
import threading
import urllib.parse
import webbrowser
import httpx
from dotenv import load_dotenv, set_key

load_dotenv()

REDIRECT_URI = "http://localhost:8000/callback"
SCOPES = ["openid", "profile", "w_member_social", "email"]

received_code: str | None = None
auth_error: str | None = None
server_event = threading.Event()


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handles OAuth redirect callback from LinkedIn."""

    def log_message(self, format, *args):
        # Silence default HTTP server logging
        return

    def do_GET(self):
        global received_code, auth_error
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/callback":
            params = urllib.parse.parse_qs(parsed.query)
            if "code" in params:
                received_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                html = """
                <html>
                <body style="font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #f3f4f6;">
                    <div style="background: white; padding: 2.5rem; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); text-align: center; max-width: 420px;">
                        <div style="font-size: 3rem; margin-bottom: 1rem;">🎉</div>
                        <h2 style="color: #0a66c2; margin-bottom: 0.5rem;">Authentication Successful!</h2>
                        <p style="color: #4b5563;">You can close this tab and return to your terminal.</p>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(html.encode("utf-8"))
            elif "error" in params:
                auth_error = params.get("error_description", [params["error"][0]])[0]
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"<h2>Authentication failed: {auth_error}</h2>".encode("utf-8"))

            server_event.set()


def run_local_server(port: int = 8000):
    httpd = HTTPServer(("localhost", port), OAuthCallbackHandler)
    httpd.timeout = 120
    while not server_event.is_set():
        httpd.handle_request()


def exchange_code_for_token(client_id: str, client_secret: str, code: str) -> dict:
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    resp = httpx.post(token_url, data=payload, headers=headers, timeout=30.0)
    if resp.status_code != 200:
        print(f"\n❌ Error exchanging code for token ({resp.status_code}): {resp.text}")
        sys.exit(1)
    return resp.json()


def fetch_userinfo(access_token: str) -> dict:
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = httpx.get(url, headers=headers, timeout=15.0)
    if resp.status_code != 200:
        print(f"\n⚠️ Could not fetch user profile automatically: {resp.text}")
        return {}
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="LinkedIn OAuth 2.0 Setup Helper")
    parser.add_argument("--client-id", help="LinkedIn App Client ID")
    parser.add_argument("--client-secret", help="LinkedIn App Client Secret")
    parser.add_argument(
        "--save-env", action="store_true", help="Automatically save credentials to .env"
    )
    args = parser.parse_args()

    client_id = args.client_id or os.environ.get("LINKEDIN_CLIENT_ID")
    client_secret = args.client_secret or os.environ.get("LINKEDIN_CLIENT_SECRET")

    print("\n" + "=" * 60)
    print(" 🚀 LinkedIn Post Manager - OAuth 2.0 Setup Helper")
    print("=" * 60)

    if not client_id:
        client_id = input("\nEnter your LinkedIn App Client ID: ").strip()
    if not client_secret:
        client_secret = input("Enter your LinkedIn App Client Secret: ").strip()

    if not client_id or not client_secret:
        print("\n❌ Client ID and Client Secret are required!")
        sys.exit(1)

    print(
        f"\n👉 Ensure your LinkedIn Developer App has this Redirect URL configured:\n   {REDIRECT_URI}"
    )

    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
    }
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urllib.parse.urlencode(auth_params)}"

    server_thread = threading.Thread(target=run_local_server, daemon=True)
    server_thread.start()

    print("\n🌐 Opening browser for authorization...")
    print(f"If browser doesn't open automatically, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("⏳ Waiting for LinkedIn authorization callback (timeout: 120s)...")
    server_event.wait(timeout=120)

    if auth_error:
        print(f"\n❌ Authorization failed: {auth_error}")
        sys.exit(1)

    if not received_code:
        print("\n❌ Authorization timed out or no code received.")
        sys.exit(1)

    print("✅ Authorization code received! Exchanging for access token...")
    token_data = exchange_code_for_token(client_id, client_secret, received_code)
    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in", 5184000)

    print(f"✅ Access token acquired! (Expires in {expires_in // 86400} days)")

    # Fetch User Person URN
    user_info = fetch_userinfo(access_token)
    person_urn = f"urn:li:person:{user_info.get('sub')}" if user_info.get("sub") else ""
    user_name = user_info.get("name", "User")

    if person_urn:
        print(f"👤 Authenticated as: {user_name} ({person_urn})")

    # Save to .env if requested
    env_file = Path(".env")
    set_key(str(env_file), "LINKEDIN_ACCESS_TOKEN", access_token)
    if person_urn:
        set_key(str(env_file), "LINKEDIN_PERSON_URN", person_urn)
    set_key(str(env_file), "LINKEDIN_CLIENT_ID", client_id)
    set_key(str(env_file), "LINKEDIN_CLIENT_SECRET", client_secret)
    print(f"💾 Saved credentials to {env_file.resolve()}")

    python_executable = sys.executable.replace("\\", "/")

    print("\n" + "=" * 60)
    print(" 📋 YOUR MCP CONFIGURATION SNIPPET (mcp_config.json)")
    print("=" * 60)
    print(
        f"""
Add this inside your "mcpServers" object in ~/.gemini/config/mcp_config.json
(or Claude Desktop / Cursor MCP config):

{{
  "mcpServers": {{
    "linkedin-post-manager": {{
      "command": "{python_executable}",
      "args": ["-m", "linkedin_post_manager.server"],
      "env": {{
        "LINKEDIN_ACCESS_TOKEN": "{access_token}",
        "LINKEDIN_PERSON_URN": "{person_urn}"
      }}
    }}
  }}
}}
"""
    )
    print("=" * 60)
    print("Setup completed successfully! 🚀\n")


if __name__ == "__main__":
    main()
