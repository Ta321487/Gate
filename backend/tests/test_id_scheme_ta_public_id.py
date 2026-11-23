"""编号合同 D2：终稿吸收 public_id=gf-ta-…；展示 #N。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.services import thesis_absorb as ta


class TaPublicIdUnitTests(unittest.TestCase):
    def test_stamp_shape(self) -> None:
        s = ta._ta_public_id_stamp()
        self.assertTrue(s.startswith("gf-ta-"))
        self.assertRegex(s, r"^gf-ta-\d{8}-\d{6}$")

    def test_row_dict_has_display_and_public(self) -> None:
        row = MagicMock()
        row.id = 12
        row.public_id = "gf-ta-20261124-021800"
        row.role = "thesis"
        row.focus = "thesis_impl"
        row.source_files = ["a.pdf"]
        row.source_path = ""
        row.proposal_json = {"feature_lines": ["借阅"], "title": "t"}
        row.status = "stored"
        row.coverage = "unknown"
        row.coverage_note = ""
        row.extract_round = 1
        row.content_sha256 = "x" * 64
        row.extractor_version = "45"
        row.has_figure_text = False
        row.char_count = 10
        row.warnings_json = []
        row.draft_roles = []
        row.draft_entities = []
        row.draft_features = []
        row.draft_schema_sql = ""
        row.schema_extract_meta = {}
        row.trial_project_id = None
        row.created_at = datetime(2026, 11, 24, 2, 18, 0)
        row.updated_at = row.created_at
        d = ta._row_to_dict(row, fig_ready=True, fig_hint="")
        self.assertEqual(d["display_no"], "#12")
        self.assertEqual(d["public_id"], "gf-ta-20261124-021800")

    def test_resolve_key_digit_and_public(self) -> None:
        async def _run() -> None:
            db = AsyncMock()
            row = MagicMock()
            row.id = 7
            db.get = AsyncMock(return_value=row)
            self.assertEqual(await ta.resolve_record_key(db, "7"), 7)
            db.get = AsyncMock(return_value=None)
            self.assertIsNone(await ta.resolve_record_key(db, "999"))

            row2 = MagicMock()
            row2.id = 3
            db.scalar = AsyncMock(return_value=row2)
            self.assertEqual(
                await ta.resolve_record_key(db, "gf-ta-20261124-021800"), 3
            )
            self.assertIsNone(await ta.resolve_record_key(db, "nope"))

        asyncio.run(_run())

    def test_feed_mentions_public_id(self) -> None:
        from app.services.thesis_absorb_extract import build_feed_markdown

        md = build_feed_markdown(
            record_id=5,
            public_id="gf-ta-20261124-021800",
            coverage="unknown",
            proposal={"feature_lines": ["a", "b", "c"]},
        )
        self.assertIn("gf-ta-20261124-021800", md)
        self.assertIn("#5", md)


class TaPublicIdShapeTests(unittest.TestCase):
    def test_model_has_public_id_column(self) -> None:
        from app.models import FactoryThesisAbsorb

        cols = {c.name for c in FactoryThesisAbsorb.__table__.columns}
        self.assertIn("public_id", cols)


if __name__ == "__main__":
    unittest.main()
