"""LinkedIn REST API client for publishing posts, uploading media, and managing profile."""

import mimetypes
from pathlib import Path
from typing import Any, Optional
import urllib.parse
import httpx
from linkedin_post_manager.config import settings
from linkedin_post_manager.formatter import escape_linkedin_commentary

LINKEDIN_API_BASE = "https://api.linkedin.com"
DEFAULT_LINKEDIN_VERSION = "202608"
RESTLI_PROTOCOL_VERSION = "2.0.0"


class LinkedInAPIError(Exception):
    """Custom exception for LinkedIn API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class LinkedInClient:
    """Async client for LinkedIn REST API (Posts and Media)."""

    def __init__(self, access_token: Optional[str] = None, person_urn: Optional[str] = None):
        self._custom_token = access_token
        self._custom_urn = person_urn
        self._cached_urn: Optional[str] = None

    @property
    def access_token(self) -> str:
        return self._custom_token or settings.access_token

    @property
    def person_urn(self) -> str:
        return self._custom_urn or self._cached_urn or settings.person_urn

    def _get_headers(self, content_type: str = "application/json") -> dict[str, str]:
        token = self.access_token
        if not token:
            raise LinkedInAPIError(
                "LinkedIn Access Token is missing! Please configure 'LINKEDIN_ACCESS_TOKEN' "
                "in your MCP server environment (env section in mcp_config.json)."
            )
        headers = {
            "Authorization": f"Bearer {token}",
            "LinkedIn-Version": settings.api_version or DEFAULT_LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": RESTLI_PROTOCOL_VERSION,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    async def get_user_profile(self) -> dict[str, Any]:
        """Fetch authenticated user profile information using OpenID Connect userinfo."""
        headers = self._get_headers()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{LINKEDIN_API_BASE}/v2/userinfo", headers=headers)
            if resp.status_code != 200:
                raise LinkedInAPIError(
                    f"Failed to fetch user profile (HTTP {resp.status_code}): {resp.text}",
                    status_code=resp.status_code,
                    details=resp.text,
                )
            data = resp.json()
            sub = data.get("sub")
            if sub:
                self._cached_urn = f"urn:li:person:{sub}"
                data["person_urn"] = self._cached_urn
            return data

    async def resolve_author_urn(self) -> str:
        """Resolve the author URN, fetching it dynamically from user profile if not configured."""
        if self.person_urn:
            return self.person_urn

        # Fetch profile to auto-discover URN
        profile = await self.get_user_profile()
        urn = profile.get("person_urn")
        if not urn:
            raise LinkedInAPIError("Could not automatically determine LinkedIn Person URN.")
        self._cached_urn = urn
        return urn

    async def publish_text_post(
        self,
        text: str,
        visibility: str = "PUBLIC",
    ) -> dict[str, Any]:
        """Publish a text post directly to LinkedIn feed."""
        author_urn = await self.resolve_author_urn()
        headers = self._get_headers()

        payload = {
            "author": author_urn,
            "commentary": escape_linkedin_commentary(text),
            "visibility": visibility.upper(),
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{LINKEDIN_API_BASE}/rest/posts",
                headers=headers,
                json=payload,
            )

            if resp.status_code not in (200, 201):
                raise LinkedInAPIError(
                    f"LinkedIn Post failed (HTTP {resp.status_code}): {resp.text}",
                    status_code=resp.status_code,
                    details=resp.text,
                )

            post_urn = resp.headers.get("x-restli-id") or resp.headers.get("x-linkedin-id")
            if not post_urn and resp.text:
                try:
                    body = resp.json()
                    post_urn = body.get("id") or body.get("urn")
                except Exception:
                    pass

            return {
                "status": "success",
                "post_urn": post_urn or "urn:li:share:unknown",
                "commentary": text,
                "visibility": visibility,
                "author": author_urn,
            }

    async def initialize_image_upload(self, owner_urn: str) -> tuple[str, str]:
        """Initialize image upload with LinkedIn Images API.
        Returns: (upload_url, image_urn)
        """
        headers = self._get_headers()
        payload = {
            "initializeUploadRequest": {
                "owner": owner_urn,
            }
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{LINKEDIN_API_BASE}/rest/images?action=initializeUpload",
                headers=headers,
                json=payload,
            )

            if resp.status_code not in (200, 201):
                raise LinkedInAPIError(
                    f"Failed to initialize image upload (HTTP {resp.status_code}): {resp.text}",
                    status_code=resp.status_code,
                    details=resp.text,
                )

            data = resp.json().get("value", {})
            upload_url = data.get("uploadUrl")
            image_urn = data.get("image")

            if not upload_url or not image_urn:
                raise LinkedInAPIError(
                    f"Invalid upload initialization response from LinkedIn: {resp.text}"
                )

            return upload_url, image_urn

    async def upload_image_binary(self, upload_url: str, file_path: Path) -> None:
        """Upload raw image binary to LinkedIn provided upload URL."""
        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "image/jpeg"

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": mime_type,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.put(upload_url, headers=headers, content=file_bytes)
            if resp.status_code not in (200, 201):
                raise LinkedInAPIError(
                    f"Binary upload failed (HTTP {resp.status_code}): {resp.text}",
                    status_code=resp.status_code,
                )

    async def publish_image_post(
        self,
        text: str,
        image_path: str,
        title: str = "",
        visibility: str = "PUBLIC",
    ) -> dict[str, Any]:
        """Upload image to LinkedIn and publish post with media attachment."""
        path = Path(image_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Local image file not found at: {image_path}")

        author_urn = await self.resolve_author_urn()

        # Step 1: Initialize image upload
        upload_url, image_urn = await self.initialize_image_upload(author_urn)

        # Step 2: Upload image binary
        await self.upload_image_binary(upload_url, path)

        # Step 3: Create post referencing uploaded image URN
        headers = self._get_headers()
        payload = {
            "author": author_urn,
            "commentary": escape_linkedin_commentary(text),
            "visibility": visibility.upper(),
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {
                "media": {
                    "title": title or path.stem,
                    "id": image_urn,
                }
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{LINKEDIN_API_BASE}/rest/posts",
                headers=headers,
                json=payload,
            )

            if resp.status_code not in (200, 201):
                raise LinkedInAPIError(
                    f"Image post creation failed (HTTP {resp.status_code}): {resp.text}",
                    status_code=resp.status_code,
                    details=resp.text,
                )

            post_urn = resp.headers.get("x-restli-id") or resp.headers.get("x-linkedin-id")
            if not post_urn and resp.text:
                try:
                    body = resp.json()
                    post_urn = body.get("id") or body.get("urn")
                except Exception:
                    pass

            return {
                "status": "success",
                "post_urn": post_urn or image_urn,
                "image_urn": image_urn,
                "commentary": text,
                "visibility": visibility,
                "author": author_urn,
            }

    async def delete_post(self, post_urn: str) -> dict[str, Any]:
        """Delete a post from LinkedIn by URN."""
        encoded_urn = urllib.parse.quote(post_urn, safe="")
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.delete(
                f"{LINKEDIN_API_BASE}/rest/posts/{encoded_urn}",
                headers=headers,
            )

            if resp.status_code not in (200, 204):
                raise LinkedInAPIError(
                    f"Delete post failed (HTTP {resp.status_code}): {resp.text}",
                    status_code=resp.status_code,
                    details=resp.text,
                )

            return {
                "status": "deleted",
                "post_urn": post_urn,
            }


linkedin_client = LinkedInClient()
