"""E-R 总图布局：环序 / 内点直线 / 环外折线，联系线零交叉。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.schema.er import (
    _book_embedding,
    _circular_crossings,
    _layout_entities,
    _two_page_partition,
    load_schema_model,
    render_er_svg,
)


def _segments_from_svg(svg: str) -> list[tuple[float, float, float, float]]:
    segs: list[tuple[float, float, float, float]] = []
    for m in re.finditer(
        r'<line class="er-edge"[^>]*'
        r'x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"',
        svg,
    ):
        segs.append(tuple(float(m.group(i)) for i in range(1, 5)))  # type: ignore[arg-type]
    return segs


def _orient(ax, ay, bx, by, cx, cy) -> float:
    return (by - ay) * (cx - bx) - (bx - ax) * (cy - by)


def _segs_cross(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> bool:
    ax, ay, bx, by = a
    cx, cy, dx, dy = b
    pts_a = {(round(ax, 2), round(ay, 2)), (round(bx, 2), round(by, 2))}
    pts_b = {(round(cx, 2), round(cy, 2)), (round(dx, 2), round(dy, 2))}
    if pts_a & pts_b:
        return False
    o1 = _orient(ax, ay, bx, by, cx, cy)
    o2 = _orient(ax, ay, bx, by, dx, dy)
    o3 = _orient(cx, cy, dx, dy, ax, ay)
    o4 = _orient(cx, cy, dx, dy, bx, by)
    return o1 * o2 < 0 and o3 * o4 < 0


def _count_geo_crossings(svg: str) -> int:
    segs = _segments_from_svg(svg)
    n = 0
    for i, s in enumerate(segs):
        for t in segs[i + 1 :]:
            if _segs_cross(s, t):
                n += 1
    return n


class ErLayoutTests(unittest.TestCase):
    def test_hospital_like_outerplanar_all_inner(self) -> None:
        names = [
            "category",
            "doctor",
            "resource_slot",
            "reservation",
            "sys_message",
            "sys_notice",
            "user_ledger",
            "sys_user:user",
            "sys_user:subadmin",
            "sys_user:admin",
        ]
        edges = [
            ("category", "doctor"),
            ("doctor", "resource_slot"),
            ("resource_slot", "reservation"),
            ("sys_user:user", "reservation"),
            ("sys_user:user", "sys_message"),
            ("sys_user:admin", "sys_notice"),
            ("sys_user:user", "user_ledger"),
            ("sys_user:admin", "user_ledger"),
            ("sys_user:admin", "sys_user:subadmin"),
            ("sys_user:admin", "sys_user:user"),
        ]
        order, inner, outer = _book_embedding(names, edges)
        self.assertTrue(_two_page_partition(order, edges)[0])
        self.assertEqual(_circular_crossings(order, list(inner)), 0)
        self.assertEqual(_circular_crossings(order, list(outer)), 0)
        self.assertEqual(outer, set())
        self.assertEqual(len(inner), 10)

    def test_k4_hub_layout_no_outer(self) -> None:
        names = ["a", "b", "c", "d"]
        edges = [
            ("a", "b"),
            ("b", "c"),
            ("c", "d"),
            ("d", "a"),
            ("a", "c"),
            ("b", "d"),
        ]
        _order, pos, outer = _layout_entities(names, edges, 0.0, 0.0, 200.0)
        self.assertEqual(outer, set())
        at_origin = [n for n, p in pos.items() if abs(p[0]) < 1e-6 and abs(p[1]) < 1e-6]
        self.assertEqual(len(at_origin), 1)

    def test_activity_workspace_prefers_hub_not_detour(self) -> None:
        wp = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "workspace"
            / "gf-20260720-020122"
        )
        if not wp.is_dir():
            self.skipTest("activity workspace missing")
        model = load_schema_model(wp)
        self.assertIsNotNone(model)
        assert model is not None
        tables = model.get("tables") or []
        rels = model.get("relations") or []
        linked = {x.get("left") for x in rels} | {x.get("right") for x in rels}
        names = [t["name"] for t in tables if t["name"] in linked]
        edges = [(x["left"], x["right"]) for x in rels]
        _order, pos, outer = _layout_entities(names, edges, 400.0, 400.0, 220.0)
        self.assertEqual(outer, set(), "应走内点直线，而不是环外绕线")
        at_c = [
            n
            for n, p in pos.items()
            if abs(p[0] - 400.0) < 1e-6 and abs(p[1] - 400.0) < 1e-6
        ]
        self.assertEqual(len(at_c), 1)
        svg = render_er_svg(model, mode="total")
        self.assertEqual(_count_geo_crossings(svg), 0)

    def test_workspace_svgs_have_no_edge_crossings(self) -> None:
        root = Path(__file__).resolve().parents[2] / "data" / "workspace"
        if not root.is_dir():
            self.skipTest("no workspace fixtures")
        checked = 0
        for wp in sorted(root.glob("*/")):
            model = load_schema_model(wp)
            if not model or not (model.get("relations") or []):
                continue
            svg = render_er_svg(model, mode="total")
            crossings = _count_geo_crossings(svg)
            self.assertEqual(crossings, 0, f"{wp.name} has {crossings} crossings")
            checked += 1
        self.assertGreaterEqual(checked, 1)


if __name__ == "__main__":
    unittest.main()
