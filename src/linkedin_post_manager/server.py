"""LinkedIn Post Manager MCP 2.0 Server.
Exposes tools, resources, and prompts to manage, format, schedule, and publish LinkedIn posts.
Credentials are read directly from MCP environment variables (env configuration).
"""

import json
import logging
import sys
from typing import Any, Optional

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer

from linkedin_post_manager.client import LinkedInAPIError, linkedin_client
from linkedin_post_manager.config import settings
from linkedin_post_manager.db import db
from linkedin_post_manager.formatter import (
    POST_TEMPLATES,
    analyze_post_structure,
    format_linkedin_post,
)
from linkedin_post_manager.scheduler import process_due_posts

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("linkedin_post_manager.server")

# Initialize MCP 2.0 Server
mcp = MCPServer(
    name="LinkedIn-Post-Manager",
    instructions="Manage, format, schedule, draft, and publish LinkedIn posts using official LinkedIn APIs and local SQLite storage.",
    version="0.1.0",
)


# ==========================================
# 1. PUBLISHING TOOLS
# ==========================================


@mcp.tool(
    name="publish_text_post",
    description="Publish a text post directly to LinkedIn. Credentials are read from MCP environment variables.",
)
async def publish_text_post(
    text: str,
    visibility: str = "PUBLIC",
) -> dict[str, Any]:
    """Publish a text post to LinkedIn.

    Args:
        text: The text content of the post.
        visibility: 'PUBLIC' (default) or 'CONNECTIONS'.
    """
    valid, err = settings.validate_posting_credentials()
    if not valid:
        return {"status": "error", "message": err}

    try:
        result = await linkedin_client.publish_text_post(text=text, visibility=visibility)
        post_urn = result.get("post_urn", "")
        db.log_published_post(
            post_urn=post_urn,
            content=text,
            visibility=visibility,
        )
        return {
            "status": "success",
            "message": "Post successfully published to LinkedIn!",
            "post_urn": post_urn,
            "post_url": f"https://www.linkedin.com/feed/update/{post_urn}" if post_urn else "",
            "visibility": visibility,
        }
    except LinkedInAPIError as e:
        return {
            "status": "error",
            "error_type": "LinkedInAPIError",
            "message": str(e),
            "status_code": e.status_code,
        }
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}


@mcp.tool(
    name="publish_image_post",
    description="Upload a local image and publish a post with media to LinkedIn. Credentials are read from MCP environment variables.",
)
async def publish_image_post(
    text: str,
    image_path: str,
    title: str = "",
    visibility: str = "PUBLIC",
) -> dict[str, Any]:
    """Publish an image post to LinkedIn.

    Args:
        text: The post commentary / caption.
        image_path: Absolute or relative local path to the image file.
        title: Optional title for the image asset.
        visibility: 'PUBLIC' (default) or 'CONNECTIONS'.
    """
    valid, err = settings.validate_posting_credentials()
    if not valid:
        return {"status": "error", "message": err}

    try:
        result = await linkedin_client.publish_image_post(
            text=text,
            image_path=image_path,
            title=title,
            visibility=visibility,
        )
        post_urn = result.get("post_urn", "")
        db.log_published_post(
            post_urn=post_urn,
            content=text,
            media_path=image_path,
            visibility=visibility,
        )
        return {
            "status": "success",
            "message": "Image post successfully uploaded and published to LinkedIn!",
            "post_urn": post_urn,
            "image_urn": result.get("image_urn"),
            "post_url": f"https://www.linkedin.com/feed/update/{post_urn}" if post_urn else "",
            "visibility": visibility,
        }
    except FileNotFoundError as e:
        return {"status": "error", "message": str(e)}
    except LinkedInAPIError as e:
        return {
            "status": "error",
            "error_type": "LinkedInAPIError",
            "message": str(e),
            "status_code": e.status_code,
        }
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}


@mcp.tool(
    name="delete_post",
    description="Delete a published post on LinkedIn using its post URN.",
)
async def delete_post(post_urn: str) -> dict[str, Any]:
    """Delete a post from LinkedIn.

    Args:
        post_urn: The URN of the post (e.g., 'urn:li:share:123456789' or 'urn:li:ugcPost:123456789').
    """
    valid, err = settings.validate_posting_credentials()
    if not valid:
        return {"status": "error", "message": err}

    try:
        result = await linkedin_client.delete_post(post_urn)
        return {
            "status": "success",
            "message": f"Post {post_urn} successfully deleted from LinkedIn.",
            "details": result,
        }
    except LinkedInAPIError as e:
        return {
            "status": "error",
            "error_type": "LinkedInAPIError",
            "message": str(e),
            "status_code": e.status_code,
        }


# ==========================================
# 2. DRAFTS MANAGEMENT TOOLS
# ==========================================


@mcp.tool(
    name="save_draft",
    description="Save a post idea or draft to local SQLite storage.",
)
def save_draft(
    content: str,
    title: str = "",
    tags: Optional[list[str]] = None,
    media_path: Optional[str] = None,
) -> dict[str, Any]:
    """Save a draft to local SQLite database.

    Args:
        content: The text of the draft.
        title: Optional title or headline.
        tags: Optional list of tags or topic categories.
        media_path: Optional path to an image for this post.
    """
    draft = db.create_draft(content=content, title=title, tags=tags, media_path=media_path)
    return {
        "status": "success",
        "message": f"Draft #{draft.get('id')} saved successfully.",
        "draft": draft,
    }


@mcp.tool(
    name="list_drafts",
    description="List all saved post drafts with optional filtering.",
)
def list_drafts(
    status: str = "all",
    search: str = "",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List drafts from local database.

    Args:
        status: Filter by status ('all', 'draft', 'scheduled', 'published').
        search: Optional keyword search in content or title.
        limit: Maximum number of drafts to return.
    """
    return db.list_drafts(status=status, search=search, limit=limit)


@mcp.tool(
    name="get_draft",
    description="Get details of a specific draft by its ID.",
)
def get_draft(draft_id: int) -> dict[str, Any]:
    """Retrieve full details for a draft.

    Args:
        draft_id: Unique ID of the draft.
    """
    draft = db.get_draft(draft_id)
    if not draft:
        return {"status": "error", "message": f"Draft with ID {draft_id} not found."}
    return {"status": "success", "draft": draft}


@mcp.tool(
    name="update_draft",
    description="Update content, title, tags, or media path of an existing draft.",
)
def update_draft(
    draft_id: int,
    content: Optional[str] = None,
    title: Optional[str] = None,
    tags: Optional[list[str]] = None,
    media_path: Optional[str] = None,
    status: Optional[str] = None,
) -> dict[str, Any]:
    """Update a draft in SQLite database."""
    updated = db.update_draft(
        draft_id=draft_id,
        content=content,
        title=title,
        tags=tags,
        media_path=media_path,
        status=status,
    )
    if not updated:
        return {"status": "error", "message": f"Draft with ID {draft_id} not found."}
    return {
        "status": "success",
        "message": f"Draft #{draft_id} updated successfully.",
        "draft": updated,
    }


@mcp.tool(
    name="delete_draft",
    description="Delete a draft by its ID.",
)
def delete_draft(draft_id: int) -> dict[str, Any]:
    """Delete draft by ID."""
    success = db.delete_draft(draft_id)
    if not success:
        return {"status": "error", "message": f"Draft with ID {draft_id} not found."}
    return {"status": "success", "message": f"Draft #{draft_id} deleted."}


# ==========================================
# 3. SCHEDULING TOOLS
# ==========================================


@mcp.tool(
    name="schedule_post",
    description="Schedule a post for future automated publishing. Provide time in ISO-8601 format (e.g. '2026-09-07T10:30:00Z').",
)
def schedule_post(
    content: str,
    scheduled_at_iso: str,
    media_path: Optional[str] = None,
    visibility: str = "PUBLIC",
    draft_id: Optional[int] = None,
) -> dict[str, Any]:
    """Schedule a post to be published later.

    Args:
        content: Post text commentary.
        scheduled_at_iso: When to publish (ISO 8601 string, UTC recommended).
        media_path: Optional local image path.
        visibility: 'PUBLIC' or 'CONNECTIONS'.
        draft_id: Optional draft ID to associate with this schedule.
    """
    item = db.create_scheduled_post(
        content=content,
        scheduled_at=scheduled_at_iso,
        media_path=media_path,
        visibility=visibility,
        draft_id=draft_id,
    )
    return {
        "status": "success",
        "message": f"Post scheduled with ID #{item.get('id')} for {scheduled_at_iso}.",
        "scheduled_post": item,
    }


@mcp.tool(
    name="list_scheduled_posts",
    description="List upcoming scheduled posts in the queue.",
)
def list_scheduled_posts(status: str = "pending", limit: int = 50) -> list[dict[str, Any]]:
    """List scheduled posts.

    Args:
        status: 'pending', 'completed', 'failed', 'cancelled', or 'all'.
        limit: Max posts to return.
    """
    return db.list_scheduled_posts(status=status, limit=limit)


@mcp.tool(
    name="cancel_scheduled_post",
    description="Cancel a pending scheduled post by its schedule ID.",
)
def cancel_scheduled_post(schedule_id: int) -> dict[str, Any]:
    """Cancel a scheduled post."""
    success = db.cancel_scheduled_post(schedule_id)
    if not success:
        return {
            "status": "error",
            "message": f"Pending scheduled post with ID {schedule_id} not found or already executed.",
        }
    return {
        "status": "success",
        "message": f"Scheduled post #{schedule_id} has been cancelled.",
    }


@mcp.tool(
    name="check_and_publish_due_posts",
    description="Check the database for any scheduled posts whose time has arrived and publish them immediately.",
)
async def check_and_publish_due_posts() -> dict[str, Any]:
    """Trigger dispatch of all due scheduled posts."""
    results = await process_due_posts()
    return {
        "status": "success",
        "processed_count": len(results),
        "results": results,
    }


# ==========================================
# 4. POST FORMATTING & OPTIMIZATION TOOLS
# ==========================================


@mcp.tool(
    name="format_post",
    description="Format raw thoughts into a high-engagement LinkedIn post with hooks, spacing, bullet points, and CTA.",
)
def format_post(
    raw_text: str,
    tone: str = "professional",
    add_cta: bool = True,
    hashtags: Optional[list[str]] = None,
) -> str:
    """Format post for LinkedIn readability and algorithm performance.

    Args:
        raw_text: Unformatted draft or thoughts.
        tone: 'professional', 'casual', or 'technical'.
        add_cta: Whether to append a call-to-action at the end.
        hashtags: Optional list of hashtags to add at the bottom.
    """
    return format_linkedin_post(
        raw_text=raw_text,
        tone=tone,
        add_cta=add_cta,
        hashtags=hashtags,
    )


@mcp.tool(
    name="analyze_post",
    description="Analyze a LinkedIn post for length, hook visibility (before '...see more'), hashtag density, and mobile readability.",
)
def analyze_post(content: str) -> dict[str, Any]:
    """Analyze post structure and return readability score and actionable suggestions.

    Args:
        content: The LinkedIn post text to evaluate.
    """
    return analyze_post_structure(content)


# ==========================================
# 5. PROFILE & DIAGNOSTICS TOOLS
# ==========================================


@mcp.tool(
    name="get_my_profile",
    description="Fetch the authenticated user's LinkedIn profile details and person URN using configured credentials.",
)
async def get_my_profile() -> dict[str, Any]:
    """Fetch user profile details from LinkedIn."""
    valid, err = settings.validate_posting_credentials()
    if not valid:
        return {
            "status": "unconfigured",
            "message": err,
            "instructions": (
                "To configure credentials, set 'LINKEDIN_ACCESS_TOKEN' and 'LINKEDIN_PERSON_URN' "
                "in your MCP client environment config (mcp_config.json)."
            ),
        }

    try:
        profile = await linkedin_client.get_user_profile()
        return {
            "status": "authenticated",
            "name": profile.get("name"),
            "email": profile.get("email"),
            "person_urn": profile.get("person_urn"),
            "raw_profile": profile,
        }
    except LinkedInAPIError as e:
        return {
            "status": "error",
            "error_type": "LinkedInAPIError",
            "message": str(e),
            "status_code": e.status_code,
        }


@mcp.tool(
    name="get_post_history",
    description="Retrieve the history of posts published through this manager.",
)
def get_post_history(limit: int = 10) -> list[dict[str, Any]]:
    """List recently published posts logged in the local database.

    Args:
        limit: Max number of posts to fetch (default: 10).
    """
    return db.list_published_history(limit=limit)


@mcp.tool(
    name="get_manager_stats",
    description="Get statistics on total drafts, pending schedules, and published posts in the local database.",
)
def get_manager_stats() -> dict[str, Any]:
    """Get manager stats and environment status."""
    has_token, _ = settings.validate_posting_credentials()
    stats = db.get_summary_stats()
    return {
        "database_path": str(settings.db_path),
        "has_access_token": has_token,
        "person_urn_configured": bool(settings.person_urn),
        "stats": stats,
    }


# ==========================================
# 6. MCP 2.0 RESOURCES
# ==========================================


@mcp.resource("linkedin://templates/list")
def get_templates_list() -> str:
    """Return list of all available LinkedIn post templates."""
    available = list(POST_TEMPLATES.keys())
    return json.dumps({"available_templates": available}, indent=2)


@mcp.resource("linkedin://stats/summary")
def get_stats_resource() -> str:
    """Return JSON string summary of current drafts and post queue."""
    stats = db.get_summary_stats()
    return json.dumps(stats, indent=2)


# ==========================================
# 7. MCP 2.0 PROMPTS
# ==========================================


@mcp.prompt("draft_tech_post")
def draft_tech_post_prompt(topic: str, key_takeaway: str) -> str:
    """Generate a prompt to draft a viral technical LinkedIn post."""
    return f"""Draft a high-impact LinkedIn post about '{topic}'.
Key takeaway: {key_takeaway}

Guidelines:
1. Opening Hook: 1-2 lines maximum (under 140 chars) to ensure it appears above the '...see more' fold.
2. Structure: Break content into 1-2 sentence paragraphs with clean line breaks.
3. Bullets: Use bullet points for key insights.
4. Call To Action (CTA): Ask an engaging question at the end to invite discussion.
5. Hashtags: Include 3-4 targeted hashtags at the very bottom.
6. Tone: Passionate, developer-friendly, and actionable.
"""


@mcp.prompt("generate_viral_hooks")
def generate_viral_hooks_prompt(post_topic: str) -> str:
    """Generate 5 distinct opening hook ideas for a LinkedIn post."""
    return f"""Generate 5 different LinkedIn opening hooks for a post on '{post_topic}'.
Each hook must:
- Be strictly under 140 characters.
- Evoke curiosity, present a counter-intuitive observation, or ask a thought-provoking question.
- Avoid clickbait clichés like 'You won't believe this'.
- Be ready to copy-paste.
"""


def main():
    """Server entry point."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
