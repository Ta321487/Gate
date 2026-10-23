"""起包前布局闸 D3 管道 + D4 全表视觉覆盖率。"""

from __future__ import annotations

import unittest

from app.bake.layout_inventory import generate_layout_inventory
from app.bake.layout_smoke import (
    PILOT_COMPONENT_ROW_ID,
    PILOT_PAGE_ROW_ID,
    PILOT_ROW_IDS,
    Box,
    assert_metrics_ok,
    box_contains,
    box_iou,
    build_visit_plan,
    concrete_path,
    page_surface_tag,
    pilot_rows,
    run_layout_smoke_full,
    run_layout_smoke_pilot,
    surface_to_delivered,
)


class LayoutSmokeGeometryTests(unittest.TestCase):
    def test_box_contains_and_iou(self) -> None:
        parent = Box(0, 0, 100, 100)
        child = Box(10, 10, 20, 20)
        self.assertTrue(box_contains(parent, child))
        self.assertFalse(box_contains(parent, Box(90, 90, 30, 30)))
        self.assertGreater(box_iou(Box(0, 0, 50, 50), Box(25, 25, 50, 50)), 0.1)
        self.assertEqual(box_iou(Box(0, 0, 10, 10), Box(20, 20, 10, 10)), 0.0)

    def test_metrics_good_green(self) -> None:
        metrics = {
            "not_blank": True,
            "expect_footer": True,
            "auth": {"x": 0, "y": 0, "w": 800, "h": 600},
            "panel": {"x": 400, "y": 40, "w": 360, "h": 500},
            "brand": {"x": 0, "y": 40, "w": 360, "h": 500},
            "footer": {"x": 420, "y": 480, "w": 320, "h": 40},
            "cta": {"x": 420, "y": 400, "w": 200, "h": 40},
            "cta_full_ellipsis": False,
        }
        self.assertEqual(assert_metrics_ok(metrics), [])

    def test_metrics_overflow_red(self) -> None:
        metrics = {
            "not_blank": True,
            "expect_footer": True,
            "auth": {"x": 0, "y": 0, "w": 800, "h": 600},
            "panel": {"x": 400, "y": 40, "w": 200, "h": 200},
            "brand": {"x": 0, "y": 40, "w": 360, "h": 500},
            "footer": {"x": 420, "y": 180, "w": 160, "h": 40},
            "cta": {"x": 420, "y": 100, "w": 300, "h": 40},
            "cta_full_ellipsis": False,
        }
        hits = assert_metrics_ok(metrics)
        self.assertTrue(
            any(f.defect_class == "overflow" for f in hits),
            f"溢出未红: {hits}",
        )

    def test_metrics_crush_ellipsis_red(self) -> None:
        metrics = {
            "not_blank": True,
            "expect_footer": True,
            "auth": {"x": 0, "y": 0, "w": 390, "h": 800},
            "panel": {"x": 20, "y": 40, "w": 350, "h": 700},
            "brand": None,
            "footer": {"x": 30, "y": 700, "w": 330, "h": 30},
            "cta": {"x": 30, "y": 400, "w": 100, "h": 36},
            "cta_full_ellipsis": True,
        }
        hits = assert_metrics_ok(metrics)
        self.assertTrue(
            any(f.defect_class == "clip_hide" for f in hits),
            f"挤破 ellipsis 未红: {hits}",
        )

    def test_metrics_overlap_red(self) -> None:
        metrics = {
            "not_blank": True,
            "expect_footer": True,
            "auth": {"x": 0, "y": 0, "w": 800, "h": 600},
            "panel": {"x": 100, "y": 100, "w": 400, "h": 400},
            "brand": {"x": 120, "y": 120, "w": 360, "h": 360},
            "footer": {"x": 120, "y": 450, "w": 200, "h": 30},
            "cta": {"x": 140, "y": 300, "w": 120, "h": 40},
            "cta_full_ellipsis": False,
        }
        hits = assert_metrics_ok(metrics)
        self.assertTrue(
            any(f.defect_class == "overlap" and f.row_id == PILOT_COMPONENT_ROW_ID for f in hits),
            f"叠穿未红: {hits}",
        )

    def test_pilot_rows_in_inventory(self) -> None:
        rows = pilot_rows()
        ids = {r.row_id for r in rows}
        self.assertEqual(ids, set(PILOT_ROW_IDS))
        page = next(r for r in rows if r.row_id == PILOT_PAGE_ROW_ID)
        comp = next(r for r in rows if r.row_id == PILOT_COMPONENT_ROW_ID)
        self.assertEqual(page.vue, "views/Login.vue")
        self.assertEqual(comp.vue, "components/AuthShell.vue")
        self.assertIn(PILOT_PAGE_ROW_ID, comp.hosts)


class LayoutSmokePlanTests(unittest.TestCase):
    """D4：visit plan 须覆盖台账全行（除已知不可访）。"""

    def test_concrete_and_surface_helpers(self) -> None:
        self.assertEqual(concrete_path("/notices/:id"), "/notices/1")
        self.assertEqual(
            surface_to_delivered("trade:shelfgrid"),
            {"tradeSurfaceStyle": "shelfgrid"},
        )
        rows = generate_layout_inventory()
        surf = next(
            (r for r in rows if r.kind == "page" and page_surface_tag(r)),
            None,
        )
        self.assertIsNotNone(surf)
        assert surf is not None
        tag = page_surface_tag(surf)
        self.assertIn(":", tag)
        self.assertTrue(surface_to_delivered(tag))

    def test_visit_plan_covers_inventory(self) -> None:
        rows = generate_layout_inventory()
        visits, unvisitable = build_visit_plan()
        planned: set[str] = set()
        for v in visits:
            planned.update(v.row_ids)
        planned.update(unvisitable)
        missing = sorted({r.row_id for r in rows} - planned)
        self.assertEqual(missing, [], f"台账行未进 visit plan: {missing[:20]}")
        # 孤儿组件只允许已知集合
        self.assertTrue(
            set(unvisitable) <= set(_BASELINE_UNVISITABLE),
            f"新出现不可访行（须记账或修 hosts）: {set(unvisitable) - set(_BASELINE_UNVISITABLE)}",
        )
        # 须含挤破代表 path + 多脸 visit
        paths = {v.path for v in visits}
        self.assertIn("/login", paths)
        self.assertTrue(
            any(v.delivered for v in visits),
            "缺少 surface 皮覆盖 visit（多脸未循环）",
        )
        self.assertGreaterEqual(len(visits), 100, f"visit 过少: {len(visits)}")


class LayoutSmokeBrowserTests(unittest.TestCase):
    """需 Node + Chromium/Chrome/Edge + baseline node_modules。"""

    def test_pilot_browser_pipe(self) -> None:
        try:
            findings = run_layout_smoke_pilot()
        except FileNotFoundError as exc:
            self.skipTest(f"冒烟环境缺失: {exc}")
        except TimeoutError as exc:
            self.skipTest(f"Vite 未就绪: {exc}")
        except RuntimeError as exc:
            msg = str(exc).lower()
            if "executable doesn't exist" in msg or "browsertype.launch" in msg:
                self.skipTest(f"Playwright 浏览器未安装: {exc}")
            raise
        known = _BASELINE_SMOKE_KNOWN
        unexpected = [
            f
            for f in findings
            if (f.defect_class, f.row_id, f.message) not in known
        ]
        self.assertEqual(
            unexpected,
            [],
            "非预期视觉红灯（本刀不改页；真阳性请记入 _BASELINE_SMOKE_KNOWN）:\n"
            + "\n".join(str(f) for f in unexpected[:20]),
        )

    def test_full_table_coverage(self) -> None:
        """D4：台账行 visual 覆盖率 100%（ok + 已知债 + 已知不可访）。"""
        try:
            report = run_layout_smoke_full(
                known=_BASELINE_FULL_KNOWN,
                known_unvisitable=_BASELINE_UNVISITABLE,
            )
        except FileNotFoundError as exc:
            self.skipTest(f"冒烟环境缺失: {exc}")
        except TimeoutError as exc:
            self.skipTest(f"Vite 未就绪: {exc}")
        except RuntimeError as exc:
            msg = str(exc).lower()
            if "executable doesn't exist" in msg or "browsertype.launch" in msg:
                self.skipTest(f"Playwright 浏览器未安装: {exc}")
            raise

        # 写出摘要便于补记账
        fails = [s for s in report.rows if s.status == "visual_fail"]
        if fails:
            preview = "\n".join(
                f"{s.row_id} :: " + " | ".join(f.key().__repr__() for f in s.findings[:3])
                for s in fails[:40]
            )
            self.fail(
                f"D4 未齐 coverage={report.coverage_pct:.1f}% "
                f"ok={report.visual_ok} debt={report.known_debt} "
                f"fail={report.visual_fail} unvisitable={report.unvisitable} "
                f"crush_ok={report.crush_ok}\n"
                f"非预期失败（记入 _BASELINE_FULL_KNOWN，禁止改页消红）:\n{preview}"
            )
        self.assertTrue(report.gate_ok)
        self.assertEqual(report.coverage_pct, 100.0)


# D3 试点：表空 = 须零红
_BASELINE_SMOKE_KNOWN: frozenset[tuple[str, str, str]] = frozenset()

# D1 孤儿：无 hosts，D4 记不可访（不改页挂回）
_BASELINE_UNVISITABLE: frozenset[str] = frozenset(
    {
        "component:components/EntityDetailLayout.vue",
    }
)

# D4 全表真阳性记账：(defect_class, row_id, message)；本刀不改页消红
_BASELINE_FULL_KNOWN: frozenset[tuple[str, str, str]] = frozenset(
    {
        # 门户根与公告详情主 CTA 命中盒偏小（基线真阳性）
        ("crushed", "page:user:/", "主 CTA 可点尺寸过小"),
        ("crushed", "page:user:/notices/:id", "主 CTA 可点尺寸过小"),
    }
)


if __name__ == "__main__":
    unittest.main()
