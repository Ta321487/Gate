"""借用/跟进加厚：序列/泳道图须扫到批量录用、导出清单、续借等演示按钮。"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from app.bake.domain_schema import ensure_spec_schema
from app.bake.schema.er_zh import _COMMON_COL_ZH
from app.bake.schema.sequence import build_diagram_messages, list_sequence_candidates


ROOT = Path(__file__).resolve().parents[2]
SK_FE = ROOT / "skeletons" / "baseline" / "frontend" / "src"
SK_BE = ROOT / "skeletons" / "baseline" / "backend" / "src" / "main" / "java" / "com" / "thesis" / "controller"


class SequenceThickenButtonTests(unittest.TestCase):
    def _workspace(self, schema: dict) -> Path:
        td = Path(tempfile.mkdtemp(prefix="seq_thicken_"))
        self.addCleanup(lambda: shutil.rmtree(td, ignore_errors=True))
        (td / "frontend" / "src").mkdir(parents=True)
        (td / "backend" / "src" / "main" / "java" / "com" / "thesis" / "controller").mkdir(
            parents=True
        )
        for rel in (
            "views/admin/TicketsAdmin.vue",
            "views/admin/TicketRecordsAdmin.vue",
            "views/user/MyFavorites.vue",
            "views/user/MyTickets.vue",
        ):
            dest = td / "frontend" / "src" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SK_FE / rel, dest)
        for name in ("TicketController.java", "AuthController.java"):
            shutil.copy2(SK_BE / name, td / "backend/src/main/java/com/thesis/controller" / name)
        (td / "domain.schema.json").write_text(
            json.dumps(schema, ensure_ascii=False), encoding="utf-8"
        )
        return td

    def test_er_zh_has_thicken_columns(self) -> None:
        for col in (
            "interview_result",
            "expire_on",
            "week_no",
            "renew_count",
            "hold_expire_at",
            "contact_channel",
            "follow_soon_notified_at",
            "fine_status",
        ):
            self.assertIn(col, _COMMON_COL_ZH)
            self.assertTrue(_COMMON_COL_ZH[col])

    def test_recruit_batch_hire_and_favorites_export(self) -> None:
        spec = ensure_spec_schema(
            {
                "title": "校园招聘",
                "domain": "DOM-RECRUIT",
                "proposal_text": "批量录用 岗位收藏分享",
            }
        )
        sch = spec.get("schema") or {}
        ws = self._workspace(sch)
        cands = list_sequence_candidates(sch, proposal_text="批量录用 岗位收藏分享")
        pending = next(c for c in cands if c["kind"] == "ticket_pending")
        msgs, _ = build_diagram_messages(pending, sch, ws)
        blob = " ".join(str(m.get("text") or "") for m in msgs)
        self.assertIn("批量录用", blob)

        fav = next(c for c in cands if c["kind"] == "favorites")
        msgs2, _ = build_diagram_messages(fav, sch, ws)
        blob2 = " ".join(str(m.get("text") or "") for m in msgs2)
        self.assertTrue("导出清单" in blob2 or "复制清单" in blob2)

    def test_library_renew_in_my_tickets(self) -> None:
        spec = ensure_spec_schema(
            {
                "title": "图书借阅",
                "domain": "DOM-LIBRARY",
                "proposal_text": "续借 罚款减免",
            }
        )
        sch = spec.get("schema") or {}
        ws = self._workspace(sch)
        cands = list_sequence_candidates(sch, proposal_text="续借")
        mine = next(c for c in cands if c["kind"] == "my_tickets")
        msgs, _ = build_diagram_messages(mine, sch, ws)
        blob = " ".join(str(m.get("text") or "") for m in msgs)
        self.assertIn("续借", blob)

    def test_custom_batch_hire_label_from_schema(self) -> None:
        """界面仍走 {{ batchHireLabel }}；出图须跟 schema.labels，禁止写死域词。"""
        spec = ensure_spec_schema(
            {
                "title": "校园招聘",
                "domain": "DOM-RECRUIT",
                "proposal_text": "批量录用 岗位收藏分享",
            }
        )
        sch = dict(spec.get("schema") or {})
        labels = dict(sch.get("labels") or {})
        labels["batchHireLabel"] = "批量录取"
        sch["labels"] = labels
        ws = self._workspace(sch)
        cands = list_sequence_candidates(sch, proposal_text="批量录取")
        pending = next(c for c in cands if c["kind"] == "ticket_pending")
        msgs, _ = build_diagram_messages(pending, sch, ws)
        blob = " ".join(str(m.get("text") or "") for m in msgs)
        self.assertIn("批量录取", blob)
        self.assertNotIn("批量录用", blob)


if __name__ == "__main__":
    unittest.main()
