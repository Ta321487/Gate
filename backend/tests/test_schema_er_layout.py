"""E-R 总图布局：ELK layered 初局；禁全环；直线交叉进外页。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.schema.er import (
    _layout_entities,
    _partition_geometric_outer,
    _straight_layout_crossings,
    load_schema_model,
    render_er_svg,
)
from app.bake.schema.layout_elk import is_approx_circular, layout_graph


class ErLayoutTests(unittest.TestCase):
    def test_elk_chain_is_layered_not_ring(self) -> None:
        names = [f"t{i}" for i in range(8)]
        edges = [(names[i], names[i + 1]) for i in range(7)]
        _order, pos, outer = _layout_entities(names, edges, 0.0, 0.0, 200.0)
        self.assertEqual(outer, set())
        self.assertEqual(len(pos), 8)
        xs = [pos[n][0] for n in names]
        # 链式 layered 应沿主轴拉开，而不是围成圆
        self.assertGreater(max(xs) - min(xs), 200.0)
        self.assertFalse(is_approx_circular(pos))

    def test_k5_not_circular_and_outer_clears_straight_cross(self) -> None:
        names = ["a", "b", "c", "d", "e"]
        edges = [(a, b) for i, a in enumerate(names) for b in names[i + 1 :]]
        _order, pos, outer = _layout_entities(names, edges, 0.0, 0.0, 220.0)
        self.assertFalse(is_approx_circular(pos, min_n=5))
        # K5 直线必有交叉 → 外页非空；内页直线应零交叉
        self.assertTrue(outer)
        undirected = []
        for a, b in edges:
            k = (a, b) if a <= b else (b, a)
            if k not in outer:
                undirected.append(k)
        self.assertEqual(_straight_layout_crossings(pos, undirected), 0)
        # 拆页函数与 layout 一致
        self.assertEqual(_partition_geometric_outer(pos, edges), outer)

    def test_hub_shopish_renders_outer_route(self) -> None:
        """用户中心辐射图：总图改走正交折线，连线不压实体框、菱形不互叠。"""
        names = [
            "user",
            "order",
            "product",
            "msg",
            "fav",
            "addr",
            "ledger",
            "review",
        ]
        edges = [("user", x) for x in names[1:]]
        edges += [("order", "product"), ("order", "review"), ("product", "fav")]
        model = {
            "tables": [{"name": n, "label": n, "columns": []} for n in names],
            "relations": [
                {
                    "name": f"r{i}",
                    "label": f"联{i}",
                    "left": a,
                    "right": b,
                    "card_left": "1",
                    "card_right": "n",
                }
                for i, (a, b) in enumerate(edges)
            ],
        }
        _o, pos, outer = _layout_entities(names, edges, 0.0, 0.0, 200.0)
        self.assertFalse(is_approx_circular(pos))
        svg = render_er_svg(model, mode="total")
        self.assertIn('data-kind="entity"', svg)
        # 对齐样例：全部走正交折线（不再绕外页大弧）
        self.assertNotIn('data-route="outer"', svg)
        self.assertGreater(svg.count('data-route="ortho"'), 0)

    def test_render_total_svg_has_entities(self) -> None:
        model = {
            "tables": [
                {"name": "user", "label": "用户", "columns": []},
                {"name": "order", "label": "订单", "columns": []},
                {"name": "item", "label": "商品", "columns": []},
            ],
            "relations": [
                {
                    "name": "place",
                    "label": "下单",
                    "left": "user",
                    "right": "order",
                    "card_left": "1",
                    "card_right": "n",
                },
                {
                    "name": "contain",
                    "label": "包含",
                    "left": "order",
                    "right": "item",
                    "card_left": "1",
                    "card_right": "n",
                },
            ],
        }
        svg = render_er_svg(model, mode="total")
        self.assertIn('data-kind="entity"', svg)
        self.assertIn('data-kind="rel"', svg)
        self.assertIn("用户", svg)

    def test_workspace_not_circular_when_present(self) -> None:
        root = Path(__file__).resolve().parents[2] / "data" / "workspace"
        if not root.is_dir():
            self.skipTest("no workspace fixtures")
        checked = 0
        for wp in sorted(root.glob("*/")):
            model = load_schema_model(wp)
            if not model or not (model.get("relations") or []):
                continue
            tables = model.get("tables") or []
            rels = model.get("relations") or []
            linked = {x.get("left") for x in rels} | {x.get("right") for x in rels}
            names = [
                t["name"]
                for t in tables
                if t.get("name") in linked and not t.get("assoc_link")
            ]
            if len(names) < 5:
                continue
            edges = [
                (x["left"], x["right"])
                for x in rels
                if x.get("left") in names and x.get("right") in names
            ]
            _o, pos, outer = _layout_entities(names, edges, 0.0, 0.0, 200.0)
            self.assertFalse(
                is_approx_circular(pos),
                f"{wp.name} layout looks circular",
            )
            undirected = []
            for a, b in edges:
                k = (a, b) if a <= b else (b, a)
                if k not in outer:
                    undirected.append(k)
            self.assertEqual(
                _straight_layout_crossings(pos, undirected),
                0,
                f"{wp.name} inner straight edges still cross",
            )
            checked += 1
            if checked >= 3:
                break
        if checked == 0:
            self.skipTest("no suitable workspace fixtures")

    def test_total_svg_edges_clear_entity_boxes_and_diamonds(self) -> None:
        """门禁：总图连线不穿过实体框，联系菱形互不重叠（用户点名的“别叠在一起”）。"""
        import itertools
        import re

        names = ["user", "order", "item", "addr", "pay", "msg", "review", "fav"]
        edges = [
            ("user", "order"),
            ("user", "addr"),
            ("user", "msg"),
            ("user", "fav"),
            ("order", "item"),
            ("order", "pay"),
            ("item", "review"),
        ]
        model = {
            "tables": [{"name": n, "label": n, "columns": []} for n in names],
            "relations": [
                {
                    "name": f"r{i}",
                    "label": "关联",
                    "left": a,
                    "right": b,
                    "card_left": "1",
                    "card_right": "n",
                }
                for i, (a, b) in enumerate(edges)
            ],
        }
        svg = render_er_svg(model, mode="total")

        def _boxes(kind: str) -> list[tuple[float, float, float, float]]:
            out = []
            for m in re.finditer(
                rf'data-kind="{kind}"[^>]*data-cx="([0-9.\-]+)" data-cy="([0-9.\-]+)" '
                r'data-hw="([0-9.\-]+)" data-hh="([0-9.\-]+)"',
                svg,
            ):
                cx, cy, hw, hh = (float(x) for x in m.groups())
                out.append((cx - hw, cy - hh, cx + hw, cy + hh))
            return out

        ents = _boxes("entity")
        rels = _boxes("rel")
        self.assertEqual(len(ents), len(names))
        self.assertEqual(len(rels), len(edges))

        def _seg_hits(x1, y1, x2, y2, r) -> bool:
            l, t, rr, b = r
            eps = 1.0
            if abs(y1 - y2) <= 0.5:
                return t + eps < y1 < b - eps and max(x1, x2) > l + eps and min(x1, x2) < rr - eps
            if abs(x1 - x2) <= 0.5:
                return l + eps < x1 < rr - eps and max(y1, y2) > t + eps and min(y1, y2) < b - eps
            return False

        for m in re.finditer(
            r'class="er-edge"[^>]*x1="([0-9.\-]+)" y1="([0-9.\-]+)" '
            r'x2="([0-9.\-]+)" y2="([0-9.\-]+)"',
            svg,
        ):
            x1, y1, x2, y2 = (float(x) for x in m.groups())
            for r in ents:
                self.assertFalse(
                    _seg_hits(x1, y1, x2, y2, r),
                    f"ER 连线压到实体框：({x1},{y1})->({x2},{y2})",
                )
        for a, b in itertools.combinations(rels, 2):
            overlap = a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
            self.assertFalse(overlap, "ER 联系菱形相互重叠")

    def test_total_svg_has_no_line_crossings(self) -> None:
        """门禁：总图 ER 连线之间不出现交叉（样例口径「消灭交叉线」）。"""
        import re

        names = ["user", "order", "item", "addr", "pay", "msg", "review", "fav"]
        edges = [
            ("user", "order"),
            ("user", "addr"),
            ("user", "msg"),
            ("user", "fav"),
            ("order", "item"),
            ("order", "pay"),
            ("item", "review"),
        ]
        model = {
            "tables": [{"name": n, "label": n, "columns": []} for n in names],
            "relations": [
                {
                    "name": f"r{i}",
                    "label": "关联",
                    "left": a,
                    "right": b,
                    "card_left": "1",
                    "card_right": "n",
                }
                for i, (a, b) in enumerate(edges)
            ],
        }
        svg = render_er_svg(model, mode="total")
        segs = [
            (float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)))
            for m in re.finditer(
                r'class="er-edge"[^>]*x1="([0-9.\-]+)" y1="([0-9.\-]+)" '
                r'x2="([0-9.\-]+)" y2="([0-9.\-]+)"',
                svg,
            )
        ]

        def _cross(a, b) -> bool:
            p, q, r, s = (a[0], a[1]), (a[2], a[3]), (b[0], b[1]), (b[2], b[3])
            if p in (r, s) or q in (r, s):
                return False

            def orient(o, u, v) -> float:
                return (u[1] - o[1]) * (v[0] - u[0]) - (u[0] - o[0]) * (v[1] - u[1])

            return orient(p, q, r) * orient(p, q, s) < 0 and orient(r, s, p) * orient(r, s, q) < 0

        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                self.assertFalse(
                    _cross(segs[i], segs[j]),
                    f"ER 连线交叉：{segs[i]} × {segs[j]}",
                )

    def test_layout_graph_smoke(self) -> None:
        laid = layout_graph(
            [
                {"id": "a", "width": 80, "height": 40},
                {"id": "b", "width": 80, "height": 40},
            ],
            [{"id": "e1", "sources": ["a"], "targets": ["b"]}],
        )
        self.assertIn("a", laid["positions"])
        self.assertIn("b", laid["positions"])
        self.assertLess(laid["elapsed_ms"], 8000.0)


if __name__ == "__main__":
    unittest.main()
