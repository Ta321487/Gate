"""答辩 PPT：evidence / phase / deck / check / fingerprint / ZIP 排除。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.services.defense_ppt.check import run_check
from app.services.defense_ppt.cover import require_cover_complete
from app.services.defense_ppt.deck_io import load_deck, save_cover, save_deck, save_skin
from app.services.defense_ppt.evidence import assemble_evidence, evidence_ready
from app.services.defense_ppt.fingerprint import (
    clear_biz_dirty,
    compute_biz_fingerprint,
    is_biz_dirty,
    mark_biz_dirty_if_changed,
    save_fingerprint,
)
from app.services.defense_ppt.job_fill import build_deck_from_context
from app.services.defense_ppt.planner import build_ppt_plan
from app.services.defense_ppt.status import derive_phase
from app.llm.unit_flow.models import UnitKind
from app.services.defense_ppt.themes import cover_complete, empty_cover, seed_theme_for_project
from app.services.jobs import _ZIP_EXCLUDE_DIRS


def _project(ws: Path, **kwargs):
    base = dict(
        id="ppt-test-1",
        title="某管理系统的设计与实现",
        workspace_path=str(ws),
        source_path=None,
        domain="DOM-demo",
        archetype="ARCH-demo",
        persistence="jdbc",
        spring_security=False,
        spec={"persistence": "jdbc"},
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _full_cover() -> dict:
    return {
        "school": "测试大学",
        "college": "计算机学院",
        "class_name": "软工2101",
        "student_name": "张三",
        "student_id": "2021001",
        "advisor": "李老师",
        "badge_data_url": "data:image/png;base64,aaaa",
    }


class DefensePptThemesTest(unittest.TestCase):
    def test_seed_stable(self) -> None:
        a = seed_theme_for_project("abc")
        b = seed_theme_for_project("abc")
        self.assertEqual(a, b)
        self.assertIn(a["theme"], ("scholar", "ink", "grove"))
        self.assertIn(a["layout_family"], ("band", "center", "footer"))

    def test_cover_complete(self) -> None:
        self.assertFalse(cover_complete(empty_cover()))
        self.assertTrue(cover_complete(_full_cover()))
        with self.assertRaises(ValueError):
            require_cover_complete(empty_cover())


class DefensePptEvidenceTest(unittest.TestCase):
    def test_evidence_ready_all_true(self) -> None:
        self.assertTrue(
            evidence_ready(
                {
                    "proposal": True,
                    "modules": True,
                    "er": True,
                    "testcases": True,
                    "gates_overall": True,
                }
            )
        )
        self.assertFalse(evidence_ready({"proposal": True, "modules": False}))

    def test_assemble_uses_delivery_block(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            p = _project(ws)
            with (
                patch(
                    "app.services.defense_ppt.evidence.has_proposal", return_value=True
                ),
                patch(
                    "app.services.defense_ppt.evidence.has_modules", return_value=True
                ),
                patch("app.services.defense_ppt.evidence.has_er", return_value=True),
                patch(
                    "app.services.defense_ppt.evidence.has_testcases", return_value=True
                ),
                patch(
                    "app.services.defense_ppt.evidence.delivery_block_reason",
                    return_value="门禁未过",
                ),
            ):
                ev = assemble_evidence(p)
            self.assertFalse(ev["gates_overall"])
            self.assertFalse(evidence_ready(ev))


class DefensePptPhaseTest(unittest.TestCase):
    def test_phase_matrix(self) -> None:
        p = _project(Path("."))
        ready_ev = {
            "proposal": True,
            "modules": True,
            "er": True,
            "testcases": True,
            "gates_overall": True,
        }
        self.assertEqual(
            derive_phase(p, evidence=ready_ev, has_deck=False, biz_dirty=False, active_job=True),
            "generating",
        )
        self.assertEqual(
            derive_phase(p, evidence={"proposal": False}, has_deck=False, biz_dirty=False, active_job=False),
            "locked",
        )
        self.assertEqual(
            derive_phase(p, evidence=ready_ev, has_deck=False, biz_dirty=False, active_job=False),
            "ready",
        )
        self.assertEqual(
            derive_phase(p, evidence=ready_ev, has_deck=True, biz_dirty=False, active_job=False),
            "done",
        )
        self.assertEqual(
            derive_phase(p, evidence=ready_ev, has_deck=True, biz_dirty=True, active_job=False),
            "dirty",
        )


class DefensePptDeckCheckTest(unittest.TestCase):
    def test_build_check_demo_shot_and_export_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            p = _project(ws)
            cover = _full_cover()
            save_cover(p, cover)
            save_skin(p, {"theme": "scholar", "layout_family": "band", "master": "none"})
            ctx = {
                "title": p.title,
                "proposal": "开题正文示例。",
                "menus": [{"label": "借用申请", "key": "borrow"}],
                "features": [],
                "entities": [],
                "modules": {"groups": [{"id": "g1", "label": "业务"}]},
                "er": {"tables": [{"name": "t_borrow", "zh": "借用"}]},
                "testcases": {"rows": [{"name": "登录", "steps": "输入账号", "expect": "进入"}]},
                "persistence": "jdbc",
                "spring_security": False,
            }
            deck = build_deck_from_context(
                p, ctx, cover=cover, theme="scholar", layout_family="band", master="none"
            )
            save_deck(p, deck)
            self.assertTrue(load_deck(p))
            self.assertGreaterEqual(len(deck["pages"]), 8)

            with patch(
                "app.services.defense_ppt.check.delivery_block_reason", return_value=None
            ):
                result = run_check(p)
            codes = {i["code"] for i in result["items"] if i["level"] == "error"}
            self.assertIn("demo_shot", codes)
            self.assertFalse(result["can_export"])

            # 补截图后仍可因其它项通过
            demo = next(pg for pg in deck["pages"] if pg["role"] == "demo")
            demo["figure"] = {
                "kind": "screenshot",
                "available": True,
                "missing": False,
                "path": "figures/shots/x.png",
            }
            save_deck(p, deck)
            with patch(
                "app.services.defense_ppt.check.delivery_block_reason", return_value=None
            ):
                result2 = run_check(p)
            self.assertTrue(result2["can_export"])


class DefensePptFingerprintTest(unittest.TestCase):
    def test_dirty_on_change_skin_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            p = _project(ws)
            cover = _full_cover()
            ctx = {
                "title": p.title,
                "proposal": "v1",
                "menus": [{"label": "A", "key": "a"}],
                "features": [],
                "entities": [],
                "modules": None,
                "er": None,
                "testcases": None,
                "persistence": "jdbc",
                "spring_security": False,
                "domain": p.domain,
                "archetype": p.archetype,
            }
            with patch(
                "app.services.defense_ppt.fingerprint.collect_context", return_value=ctx
            ):
                deck = build_deck_from_context(
                    p, ctx, cover=cover, theme="scholar", layout_family="band", master="none"
                )
                save_deck(p, deck)
                h1 = compute_biz_fingerprint(p)
                save_fingerprint(p, h1)
                self.assertFalse(is_biz_dirty(p))
                # 换皮不计入指纹
                deck["theme"] = "ink"
                save_deck(p, deck)
                self.assertFalse(is_biz_dirty(p))
                # 业务变更
                ctx2 = {**ctx, "proposal": "v2-changed"}
                with patch(
                    "app.services.defense_ppt.fingerprint.collect_context",
                    return_value=ctx2,
                ):
                    self.assertTrue(mark_biz_dirty_if_changed(p))
                    self.assertTrue(load_deck(p).get("biz_dirty"))
                clear_biz_dirty(p)
                self.assertFalse(load_deck(p).get("biz_dirty"))


class DefensePptZipExcludeTest(unittest.TestCase):
    def test_factory_dir_excluded(self) -> None:
        self.assertIn(".factory", _ZIP_EXCLUDE_DIRS)


class DefensePptUnitFlowHookTest(unittest.TestCase):
    def test_plan_uses_ppt_page_kind(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = _project(Path(td))
            cover = _full_cover()
            ctx = {
                "title": p.title,
                "proposal": "开题。",
                "menus": [{"label": "列表", "key": "list"}],
                "features": [],
                "entities": [],
                "modules": {"groups": []},
                "er": {"tables": []},
                "testcases": {"rows": []},
                "persistence": "jdbc",
                "spring_security": False,
                "domain": p.domain,
                "archetype": p.archetype,
            }
            plan = build_ppt_plan(p, ctx, cover=cover)
            self.assertTrue(plan.units)
            self.assertTrue(all(u.kind == UnitKind.ppt_page for u in plan.units))
            self.assertTrue(all(u.id.startswith("ppt.") for u in plan.units))

    def test_demo_shot_not_job_hard_failure(self) -> None:
        from app.services.defense_ppt.check import job_hard_failures

        soft = {
            "items": [
                {"level": "error", "code": "demo_shot", "message": "缺截图"},
                {"level": "error", "code": "structure", "message": "缺页"},
            ]
        }
        hard = job_hard_failures(soft)
        self.assertEqual(len(hard), 1)
        self.assertIn("缺页", hard[0])


class DefensePptCaptureTest(unittest.TestCase):
    def test_capture_into_deck_marks_missing_without_preview(self) -> None:
        import asyncio

        from app.services.defense_ppt.screenshots import capture_into_deck
        from app.services.defense_ppt.job_fill import build_deck_from_context

        with tempfile.TemporaryDirectory() as td:
            p = _project(Path(td), frontend_running=False, frontend_port=None)
            cover = _full_cover()
            deck = build_deck_from_context(
                p,
                {
                    "title": p.title,
                    "proposal": "x",
                    "menus": [],
                    "persistence": "jdbc",
                    "spring_security": False,
                },
                cover=cover,
                theme="scholar",
                layout_family="band",
                master="none",
            )
            result = asyncio.run(capture_into_deck(p, deck))
            self.assertFalse(result["ok"])
            demo = next(pg for pg in deck["pages"] if pg["role"] == "demo")
            self.assertTrue(demo["figure"]["missing"])


if __name__ == "__main__":
    unittest.main()
