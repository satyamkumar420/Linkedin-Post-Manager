"""Scheduler engine to process and auto-publish queued posts."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any
from linkedin_post_manager.client import linkedin_client
from linkedin_post_manager.db import db

logger = logging.getLogger("linkedin_post_manager.scheduler")


async def process_due_posts() -> list[dict[str, Any]]:
    """Check database for pending posts whose scheduled time has passed and publish them."""
    now_iso = datetime.now(timezone.utc).isoformat()
    pending_posts = db.list_scheduled_posts(status="pending", limit=20)
    results = []

    for post in pending_posts:
        sched_time = post["scheduled_at"]
        if sched_time <= now_iso:
            post_id = post["id"]
            content = post["content"]
            media_path = post.get("media_path")
            visibility = post.get("visibility", "PUBLIC")
            draft_id = post.get("draft_id")

            try:
                if media_path:
                    res = await linkedin_client.publish_image_post(
                        text=content,
                        image_path=media_path,
                        visibility=visibility,
                    )
                else:
                    res = await linkedin_client.publish_text_post(
                        text=content,
                        visibility=visibility,
                    )

                post_urn = res.get("post_urn", "published")
                db.update_scheduled_status(post_id, status="completed", post_urn=post_urn)
                db.log_published_post(
                    post_urn=post_urn,
                    content=content,
                    media_path=media_path,
                    visibility=visibility,
                )
                if draft_id:
                    db.update_draft(draft_id, status="published")

                results.append({"id": post_id, "status": "success", "post_urn": post_urn})
                logger.info(f"Successfully published scheduled post ID {post_id}: {post_urn}")

            except Exception as e:
                err_msg = str(e)
                db.update_scheduled_status(post_id, status="failed", error_message=err_msg)
                results.append({"id": post_id, "status": "failed", "error": err_msg})
                logger.error(f"Failed to publish scheduled post ID {post_id}: {err_msg}")

    return results


async def background_scheduler_worker(interval_seconds: int = 60) -> None:
    """Continuous background loop checking for due posts."""
    logger.info("LinkedIn Post Manager scheduler background worker started.")
    while True:
        try:
            await process_due_posts()
        except Exception as e:
            logger.error(f"Error in background scheduler cycle: {e}")
        await asyncio.sleep(interval_seconds)
