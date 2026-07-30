"""泳道 E · C-06：多维评分挂 DOM-EVAL；P-14 升格。"""

from __future__ import annotations

import unittest

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_resources import _write_ticket_copy_resource
from app.bake.sql.fragments import _ticket_flag_column_names
import tempfile
from pathlib import Path
import json


class RatingDimsC06Tests(unittest.TestCase):
    def test_capability_registered(self) -> None:
        self.assertIn("rating_dims", CAPABILITIES)
        self.assertEqual(CAPABILITIES["rating_dims"]["status"], "implemented")
        self.assertIn("rating_dims", DOMAIN_CAPABILITIES["DOM-EVAL"])

    def test_eval_schema_has_dims_and_approve_ends(self) -> None:
        schema = build_domain_schema("高校学生网上评教管理系统", "DOM-EVAL")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowRating"))
        self.assertTrue(ticket.get("approveEndsFlow"))
        self.assertTrue(ticket.get("autoApprove"))
        self.assertTrue(ticket.get("allowAnonymousRating"))
        dims = ticket.get("ratingDims") or []
        self.assertGreaterEqual(len(dims), 3, dims)
        keys = {d["key"] for d in dims}
        self.assertTrue({"content", "attitude", "outcome"} <= keys)

    def test_flag_columns_include_dims(self) -> None:
        names = _ticket_flag_column_names(
            {
                "allowRating": True,
                "ratingDims": [{"key": "a", "label": "A"}],
            }
        )
        self.assertIn("rating_dims_json", names)
        self.assertIn("rating_anonymous", names)

    def test_ticket_copy_resource_writes_dims(self) -> None:
        schema = build_domain_schema("高校学生网上评教管理系统", "DOM-EVAL")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            _write_ticket_copy_resource(dest, schema)
            path = dest / "backend" / "src" / "main" / "resources" / "domain-ticket-copy.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(data.get("ratingDims") or []), 3)
            self.assertTrue(data.get("allowAnonymousRating"))

    def test_eval_out_of_mvp_no_longer_blocks_dims(self) -> None:
        from app.bake.domains import DOMAINS

        oom = DOMAINS["DOM-EVAL"].get("out_of_mvp") or []
        self.assertNotIn("多维度评教量表", oom)


if __name__ == "__main__":
    unittest.main()
