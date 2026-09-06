"""Unit tests for LinkedIn Post Manager modules."""

import os
from pathlib import Path
import tempfile
import unittest

from linkedin_post_manager.db import Database
from linkedin_post_manager.formatter import (
    analyze_post_structure,
    format_linkedin_post,
    POST_TEMPLATES,
)
from linkedin_post_manager.server import mcp


class TestLinkedInPostManager(unittest.TestCase):
    def setUp(self):
        # Create temporary database for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_linkedin.db"
        self.test_db = Database(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_drafts_crud(self):
        # Create draft
        draft = self.test_db.create_draft(
            content="Excited to launch our new AI tool! #AI #Python",
            title="AI Launch",
            tags=["AI", "Python"],
            media_path="/path/to/image.png",
        )
        self.assertIsNotNone(draft.get("id"))
        draft_id = draft["id"]
        self.assertEqual(draft["title"], "AI Launch")
        self.assertEqual(draft["tags"], ["AI", "Python"])
        self.assertEqual(draft["status"], "draft")

        # Get draft
        fetched = self.test_db.get_draft(draft_id)
        self.assertEqual(fetched["content"], "Excited to launch our new AI tool! #AI #Python")

        # Update draft
        updated = self.test_db.update_draft(
            draft_id,
            content="Updated AI launch announcement!",
            title="Updated Title",
            status="ready",
        )
        self.assertEqual(updated["content"], "Updated AI launch announcement!")
        self.assertEqual(updated["status"], "ready")

        # List drafts
        drafts_list = self.test_db.list_drafts(status="ready")
        self.assertEqual(len(drafts_list), 1)

        # Delete draft
        deleted = self.test_db.delete_draft(draft_id)
        self.assertTrue(deleted)
        self.assertIsNone(self.test_db.get_draft(draft_id))

    def test_scheduling_crud(self):
        item = self.test_db.create_scheduled_post(
            content="Scheduled post for tomorrow morning.",
            scheduled_at="2026-09-07T09:00:00Z",
            visibility="PUBLIC",
        )
        self.assertIsNotNone(item.get("id"))
        sched_id = item["id"]
        self.assertEqual(item["status"], "pending")

        # List scheduled
        pending = self.test_db.list_scheduled_posts(status="pending")
        self.assertTrue(any(p["id"] == sched_id for p in pending))

        # Cancel scheduled
        cancelled = self.test_db.cancel_scheduled_post(sched_id)
        self.assertTrue(cancelled)

        fetched = self.test_db.get_scheduled_post(sched_id)
        self.assertEqual(fetched["status"], "cancelled")

    def test_published_history_log(self):
        res = self.test_db.log_published_post(
            post_urn="urn:li:share:987654321",
            content="Live post content test",
            visibility="PUBLIC",
        )
        self.assertEqual(res["post_urn"], "urn:li:share:987654321")

        history = self.test_db.list_published_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["post_urn"], "urn:li:share:987654321")

    def test_post_formatter(self):
        raw = "Line 1.\n\n- Point A\n- Point B"
        formatted = format_linkedin_post(raw, tone="professional", add_cta=True, hashtags=["Python", "AI"])
        self.assertIn("• Point A", formatted)
        self.assertIn("• Point B", formatted)
        self.assertIn("#Python", formatted)
        self.assertIn("#AI", formatted)
        self.assertIn("👇", formatted)

    def test_post_structure_analyzer(self):
        short_post = "Short hook line here.\n\nHere is some body text. #tech #code"
        analysis = analyze_post_structure(short_post)
        self.assertIn("character_count", analysis)
        self.assertIn("hook_character_count", analysis)
        self.assertEqual(analysis["hook_text"], "Short hook line here.")
        self.assertEqual(analysis["hashtag_count"], 2)
        self.assertGreater(analysis["score"], 0)

    def test_templates_exist(self):
        self.assertIn("project-launch", POST_TEMPLATES)
        self.assertIn("tech-learning", POST_TEMPLATES)
        self.assertIn("career-milestone", POST_TEMPLATES)

    def test_mcp_server_tools_registered(self):
        import asyncio
        tools = asyncio.run(mcp.list_tools())
        tool_names = [t.name for t in tools]
        expected_tools = [
            "publish_text_post",
            "publish_image_post",
            "delete_post",
            "save_draft",
            "list_drafts",
            "get_draft",
            "update_draft",
            "delete_draft",
            "schedule_post",
            "list_scheduled_posts",
            "cancel_scheduled_post",
            "check_and_publish_due_posts",
            "format_post",
            "analyze_post",
            "get_my_profile",
            "get_post_history",
            "get_manager_stats",
        ]
        for t in expected_tools:
            self.assertIn(t, tool_names, f"Tool '{t}' missing from MCP server.")


if __name__ == "__main__":
    unittest.main()
