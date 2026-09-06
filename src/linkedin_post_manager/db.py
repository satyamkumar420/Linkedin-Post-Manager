"""SQLite storage manager for drafts, schedules, and published post logs."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from linkedin_post_manager.config import settings


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get SQLite database connection with row factory."""
    path = db_path or settings.db_path
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize database tables."""
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                media_path TEXT,
                status TEXT DEFAULT 'draft',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                draft_id INTEGER,
                content TEXT NOT NULL,
                media_path TEXT,
                visibility TEXT DEFAULT 'PUBLIC',
                scheduled_at TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                post_urn TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                executed_at TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS published_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_urn TEXT UNIQUE,
                content TEXT,
                media_path TEXT,
                visibility TEXT,
                published_at TEXT NOT NULL
            )
        """)
    conn.close()


class Database:
    """Database operations interface for LinkedIn Post Manager."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.db_path
        init_db(self.db_path)

    # --- Drafts CRUD ---

    def create_draft(
        self,
        content: str,
        title: str = "",
        tags: Optional[list[str]] = None,
        media_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new post draft."""
        now = datetime.now(timezone.utc).isoformat()
        tags_json = json.dumps(tags or [])
        conn = get_connection(self.db_path)
        with conn:
            cur = conn.execute(
                """
                INSERT INTO drafts (title, content, tags, media_path, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'draft', ?, ?)
                """,
                (title, content, tags_json, media_path, now, now),
            )
            draft_id = cur.lastrowid
        conn.close()
        return self.get_draft(draft_id) or {}

    def get_draft(self, draft_id: int) -> Optional[dict[str, Any]]:
        """Retrieve a draft by ID."""
        conn = get_connection(self.db_path)
        cur = conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        data = dict(row)
        data["tags"] = json.loads(data["tags"]) if data.get("tags") else []
        return data

    def list_drafts(
        self, status: str = "all", search: str = "", limit: int = 50
    ) -> list[dict[str, Any]]:
        """List drafts with optional status and search filters."""
        query = "SELECT * FROM drafts WHERE 1=1"
        params: list[Any] = []

        if status and status.lower() != "all":
            query += " AND status = ?"
            params.append(status.lower())

        if search:
            query += " AND (content LIKE ? OR title LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        conn = get_connection(self.db_path)
        cur = conn.execute(query, tuple(params))
        rows = cur.fetchall()
        conn.close()

        results = []
        for row in rows:
            d = dict(row)
            d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
            results.append(d)
        return results

    def update_draft(
        self,
        draft_id: int,
        content: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[list[str]] = None,
        media_path: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Update an existing draft."""
        existing = self.get_draft(draft_id)
        if not existing:
            return None

        fields: list[str] = []
        params: list[Any] = []

        if content is not None:
            fields.append("content = ?")
            params.append(content)
        if title is not None:
            fields.append("title = ?")
            params.append(title)
        if tags is not None:
            fields.append("tags = ?")
            params.append(json.dumps(tags))
        if media_path is not None:
            fields.append("media_path = ?")
            params.append(media_path)
        if status is not None:
            fields.append("status = ?")
            params.append(status)

        now = datetime.now(timezone.utc).isoformat()
        fields.append("updated_at = ?")
        params.append(now)

        params.append(draft_id)
        query = f"UPDATE drafts SET {', '.join(fields)} WHERE id = ?"

        conn = get_connection(self.db_path)
        with conn:
            conn.execute(query, tuple(params))
        conn.close()
        return self.get_draft(draft_id)

    def delete_draft(self, draft_id: int) -> bool:
        """Delete draft by ID."""
        conn = get_connection(self.db_path)
        with conn:
            cur = conn.execute("DELETE FROM drafts WHERE id = ?", (draft_id,))
            deleted = cur.rowcount > 0
        conn.close()
        return deleted

    # --- Scheduled Posts CRUD ---

    def create_scheduled_post(
        self,
        content: str,
        scheduled_at: str,
        media_path: Optional[str] = None,
        visibility: str = "PUBLIC",
        draft_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Add a post to the scheduling queue."""
        now = datetime.now(timezone.utc).isoformat()
        conn = get_connection(self.db_path)
        with conn:
            cur = conn.execute(
                """
                INSERT INTO scheduled_posts 
                (draft_id, content, media_path, visibility, scheduled_at, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
                """,
                (draft_id, content, media_path, visibility, scheduled_at, now),
            )
            schedule_id = cur.lastrowid
            if draft_id:
                conn.execute(
                    "UPDATE drafts SET status = 'scheduled', updated_at = ? WHERE id = ?",
                    (now, draft_id),
                )
        conn.close()
        return self.get_scheduled_post(schedule_id) or {}

    def get_scheduled_post(self, schedule_id: int) -> Optional[dict[str, Any]]:
        """Retrieve scheduled post by ID."""
        conn = get_connection(self.db_path)
        cur = conn.execute("SELECT * FROM scheduled_posts WHERE id = ?", (schedule_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def list_scheduled_posts(
        self, status: str = "pending", limit: int = 50
    ) -> list[dict[str, Any]]:
        """List scheduled posts."""
        query = "SELECT * FROM scheduled_posts"
        params: list[Any] = []
        if status and status.lower() != "all":
            query += " WHERE status = ?"
            params.append(status.lower())
        query += " ORDER BY scheduled_at ASC LIMIT ?"
        params.append(limit)

        conn = get_connection(self.db_path)
        cur = conn.execute(query, tuple(params))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_scheduled_status(
        self,
        schedule_id: int,
        status: str,
        post_urn: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update scheduled post status after publish attempt."""
        now = datetime.now(timezone.utc).isoformat()
        conn = get_connection(self.db_path)
        with conn:
            conn.execute(
                """
                UPDATE scheduled_posts
                SET status = ?, post_urn = ?, error_message = ?, executed_at = ?
                WHERE id = ?
                """,
                (status, post_urn, error_message, now, schedule_id),
            )
        conn.close()

    def cancel_scheduled_post(self, schedule_id: int) -> bool:
        """Cancel a pending scheduled post."""
        conn = get_connection(self.db_path)
        with conn:
            cur = conn.execute(
                "UPDATE scheduled_posts SET status = 'cancelled' WHERE id = ? AND status = 'pending'",
                (schedule_id,),
            )
            cancelled = cur.rowcount > 0
        conn.close()
        return cancelled

    # --- Published Posts History ---

    def log_published_post(
        self,
        post_urn: str,
        content: str,
        media_path: Optional[str] = None,
        visibility: str = "PUBLIC",
    ) -> dict[str, Any]:
        """Record a successful LinkedIn post."""
        now = datetime.now(timezone.utc).isoformat()
        conn = get_connection(self.db_path)
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO published_posts 
                (post_urn, content, media_path, visibility, published_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (post_urn, content, media_path, visibility, now),
            )
        conn.close()
        return {
            "post_urn": post_urn,
            "content": content,
            "media_path": media_path,
            "visibility": visibility,
            "published_at": now,
        }

    def list_published_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recently published posts."""
        conn = get_connection(self.db_path)
        cur = conn.execute(
            "SELECT * FROM published_posts ORDER BY published_at DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_summary_stats(self) -> dict[str, int]:
        """Get counts of drafts, pending schedules, and published posts."""
        conn = get_connection(self.db_path)
        drafts_count = conn.execute("SELECT COUNT(*) FROM drafts").fetchone()[0]
        pending_schedules = conn.execute(
            "SELECT COUNT(*) FROM scheduled_posts WHERE status = 'pending'"
        ).fetchone()[0]
        published_count = conn.execute(
            "SELECT COUNT(*) FROM published_posts"
        ).fetchone()[0]
        conn.close()
        return {
            "drafts_count": drafts_count,
            "pending_scheduled": pending_schedules,
            "total_published": published_count,
        }


db = Database()
