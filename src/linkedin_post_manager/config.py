"""Configuration manager for LinkedIn Post Manager.
Reads credentials directly from MCP environment variables (env block in mcp_config.json)
with fallback to .env file if available.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load fallback .env if present
load_dotenv()

# App directories and paths
DEFAULT_DB_DIR = Path.home() / ".linkedin_post_manager"
DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "linkedin_posts.db"


class Settings:
    """Environment configuration settings for LinkedIn MCP."""

    @property
    def access_token(self) -> str:
        """LinkedIn OAuth 2.0 Access Token provided via MCP env."""
        return os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()

    @property
    def person_urn(self) -> str:
        """LinkedIn Person or Organization URN (e.g. urn:li:person:XXXXX or urn:li:organization:XXXXX)."""
        return os.environ.get("LINKEDIN_PERSON_URN", "").strip()

    @property
    def client_id(self) -> str:
        """LinkedIn OAuth Client ID (used for auth helper flow)."""
        return os.environ.get("LINKEDIN_CLIENT_ID", "").strip()

    @property
    def client_secret(self) -> str:
        """LinkedIn OAuth Client Secret (used for auth helper flow)."""
        return os.environ.get("LINKEDIN_CLIENT_SECRET", "").strip()

    @property
    def api_version(self) -> str:
        """LinkedIn REST API Version (defaults to recent active version '202608')."""
        return os.environ.get("LINKEDIN_VERSION", "202608").strip()

    @property
    def db_path(self) -> Path:
        """SQLite database path for drafts and schedules."""
        custom_path = os.environ.get("LINKEDIN_DB_PATH")
        if custom_path:
            p = Path(custom_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
        return DEFAULT_DB_PATH

    def validate_posting_credentials(self) -> tuple[bool, str]:
        """Validate if required posting credentials are set in environment."""
        if not self.access_token:
            return (
                False,
                "LINKEDIN_ACCESS_TOKEN is not configured in MCP environment. "
                "Please add 'LINKEDIN_ACCESS_TOKEN' inside the 'env' section of your mcp_config.json."
            )
        return True, ""


settings = Settings()
