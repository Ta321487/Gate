"""E-R 总图布局：ELK layered 初局；禁全环；拖拽路径不重排。"""

from __future__ import annotations

import math
import unittest
from pathlib import Path

from app.bake.schema.er import _layout_entities, load_schema_model, render_er_svg
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

    def test_k5_not_circular(self) -> None:
        names = ["a", "b", "c", "d", "e"]
        edges = [
            (a, b)
            for i, a in enumerate(names)
            for b in names[i + 1 :]
        ]
        _order, pos, outer = _layout_entities(names, edges, 0.0, 0.0, 220.0)
        self.assertEqual(outer, set())
        self.assertFalse(is_approx_circular(pos, min_n=5))

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
            self.assertEqual(outer, set())
            self.assertFalse(
                is_approx_circular(pos),
                f"{wp.name} layout looks circular",
            )
            checked += 1
            if checked >= 3:
                break
        if checked == 0:
            self.skipTest("no suitable workspace fixtures")

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
