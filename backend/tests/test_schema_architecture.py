"""系统逻辑架构图：角色取自交付；SVG 画法对齐论文分层图。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.bake.schema.architecture import (
    architecture_model,
    architecture_roles,
    render_architecture_svg,
)


class ArchitectureDiagramTests(unittest.TestCase):
    def _schema(self, stem: str) -> dict:
        path = Path(__file__).resolve().parents[0] / "golden" / "schema" / f"{stem}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_roles_from_shop_schema(self) -> None:
        roles = architecture_roles(self._schema("DOM-SHOP"))
        ids = [r["id"] for r in roles]
        self.assertIn("user", ids)
        self.assertIn("admin", ids)
        # 论文习惯：用户 → 中间角色 → 管理员
        self.assertEqual(ids[0], "user")
        self.assertEqual(ids[-1], "admin")
        labels = [r["label"] for r in roles]
        self.assertTrue(any("买家" in x or x == "买家" for x in labels))

    def test_model_layers_fixed(self) -> None:
        model = architecture_model(self._schema("DOM-SHOP"))
        labs = [x["label"] for x in model["layers"]]
        self.assertEqual(labs, ["界面", "Vue", "SpringBoot", "MySQL"])
        self.assertEqual(model["protocol_label"], "HTTPS")
        self.assertEqual(model["action_label"], "发起请求")

    def test_svg_has_boxes_and_protocol(self) -> None:
        model = architecture_model(self._schema("DOM-SHOP"))
        svg = render_architecture_svg(model)
        self.assertIn("界面", svg)
        self.assertIn("Vue", svg)
        self.assertIn("SpringBoot", svg)
        self.assertIn("MySQL", svg)
        self.assertIn("HTTPS", svg)
        self.assertIn("发起请求", svg)
        self.assertIn("#5B9BD5", svg)
        self.assertIn('stroke="#000"', svg)
        self.assertIn("买家", svg)
        # 直角框：无 rx
        self.assertNotIn("rx=", svg)
        # 协议文案只出现在界面↔Vue：角色数列份；下层居中一对不重复标
        n_roles = len(model["roles"])
        self.assertEqual(svg.count(">HTTPS<"), n_roles)
        self.assertEqual(svg.count(">发起请求<"), n_roles)

    def test_svg_single_role(self) -> None:
        schema = {
            "title": "单角色",
            "roles": {"user": {"id": "user", "label": "访客"}},
            "menus": {"user": [{"key": "home", "label": "首页"}]},
        }
        model = architecture_model(schema)
        self.assertEqual([r["label"] for r in model["roles"]], ["访客"])
        svg = render_architecture_svg(model)
        self.assertIn("访客", svg)
        self.assertIn("MySQL", svg)


if __name__ == "__main__":
    unittest.main()
