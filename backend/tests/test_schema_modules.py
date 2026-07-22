"""功能模块图：交付 menus 驱动，开题只辅助命名。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.bake.schema_modules import (
    apply_proposal_hints,
    module_model,
    render_module_svg,
    sanitize_module_label_patch,
)


class ModuleDiagramTests(unittest.TestCase):
    def _schema(self, stem: str) -> dict:
        path = Path(__file__).resolve().parents[0] / "golden" / "schema" / f"{stem}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def _shop_schema(self) -> dict:
        return self._schema("DOM-SHOP")

    def _walk_labels(self, model: dict) -> list[str]:
        labels: list[str] = []

        def walk(n: dict) -> None:
            labels.append(str(n.get("label") or ""))
            for c in n.get("children") or []:
                if isinstance(c, dict):
                    walk(c)

        walk(model["root"])
        return labels

    def test_model_by_side(self) -> None:
        schema = self._shop_schema()
        model = module_model(
            schema,
            proposal_text="后台管理与前台功能",
            layout="side",
        )
        self.assertEqual(model["title"], "测试课题")
        self.assertEqual(model["layout"], "side")
        root = model["root"]
        self.assertEqual(root["id"], "root")
        branches = {c["id"]: c for c in root["children"]}
        self.assertIn("branch:user", branches)
        self.assertIn("branch:admin", branches)
        self.assertEqual(branches["branch:user"]["label"], "前台功能")
        self.assertEqual(branches["branch:admin"]["label"], "后台管理")
        user_labs = [c["label"] for c in branches["branch:user"]["children"]]
        self.assertEqual(user_labs[:2], ["注册", "登录"])
        self.assertIn("商品浏览", user_labs)
        self.assertIn("购物车", user_labs)

    def test_model_by_biz(self) -> None:
        schema = self._shop_schema()
        model = module_model(schema, layout="biz")
        self.assertEqual(model["layout"], "biz")
        branches = {c["id"]: c for c in model["root"]["children"]}
        self.assertIn("biz:user", branches)
        self.assertIn("biz:archive", branches)
        self.assertIn("biz:cart", branches)
        self.assertIn("biz:order", branches)
        self.assertIn("biz:admin", branches)
        self.assertEqual(branches["biz:archive"]["label"], "商品模块")
        # 分类管理进管理员模块
        archive_labs = {c["label"] for c in branches["biz:archive"]["children"]}
        self.assertIn("商品浏览", archive_labs)
        self.assertIn("商品管理", archive_labs)
        self.assertNotIn("分类管理", archive_labs)
        admin_labs = {c["label"] for c in branches["biz:admin"]["children"]}
        self.assertIn("分类管理", admin_labs)
        self.assertIn("用户管理", admin_labs)
        # 购物车单叶子 → 一级叶子
        self.assertNotIn("children", branches["biz:cart"])
        self.assertEqual(branches["biz:cart"]["label"], "购物车")
        user_labs = {c["label"] for c in branches["biz:user"]["children"]}
        self.assertIn("注册", user_labs)
        self.assertIn("登录", user_labs)
        self.assertIn("个人资料", user_labs)

    def test_default_layout_is_biz(self) -> None:
        schema = self._shop_schema()
        model = module_model(schema)
        self.assertEqual(model["layout"], "biz")

    def test_no_phantom_from_proposal(self) -> None:
        schema = self._shop_schema()
        model = module_model(schema, proposal_text="需要大数据分析与区块链溯源模块")
        blob = " ".join(self._walk_labels(model))
        self.assertNotIn("区块链", blob)
        self.assertNotIn("大数据", blob)

    def test_hospital_side_and_biz(self) -> None:
        schema = {
            "title": "校医院门诊挂号预约系统",
            "labels": {"appName": "校医院门诊挂号预约系统"},
            "roles": {
                "user": {"label": "患者"},
                "admin": {"label": "管理员"},
            },
            "entities": {"archive": {"label": "医生"}},
            "menus": {
                "user": [
                    {"key": "archive", "label": "选医生"},
                    {"key": "my_reservations", "label": "我的挂号"},
                    {"key": "content", "label": "公告"},
                    {"key": "profile", "label": "个人资料"},
                ],
                "admin": [
                    {"key": "dashboard", "label": "工作台"},
                    {"key": "archive", "label": "医生管理"},
                    {"key": "category", "label": "分类管理"},
                    {"key": "users", "label": "患者管理"},
                    {"key": "reservations", "label": "挂号记录"},
                    {"key": "content", "label": "公告管理"},
                ],
            },
            "capabilities": ["org_users", "archive", "slot_reserve", "content"],
        }
        side = module_model(schema, layout="side")
        side_user = [c["label"] for c in side["root"]["children"][0]["children"]]
        self.assertEqual(side_user[:2], ["注册", "登录"])
        side_admin = [c["label"] for c in side["root"]["children"][1]["children"]]
        self.assertEqual(
            side_admin,
            ["医生管理", "分类管理", "患者管理", "挂号记录", "公告管理"],
        )

        biz = module_model(schema, layout="biz")
        branches = {c["id"]: c for c in biz["root"]["children"]}
        self.assertNotIn("其它功能", self._walk_labels(biz))
        self.assertNotIn("工作台", self._walk_labels(biz))
        self.assertIn("分类管理", {c["label"] for c in branches["biz:admin"]["children"]})
        self.assertNotIn(
            "分类管理",
            {c["label"] for c in branches["biz:archive"]["children"]},
        )

    def test_hotel_merges_slot_and_order(self) -> None:
        schema = self._schema("DOM-HOTEL")
        model = module_model(schema, layout="biz")
        branches = {c["id"]: c for c in model["root"]["children"]}
        self.assertIn("biz:slot", branches)
        self.assertNotIn("biz:order", branches)
        labs = {c["label"] for c in branches["biz:slot"]["children"]}
        self.assertTrue(labs & {"我的预订", "预订记录", "我的订单", "预订订单"})
        self.assertIn("预订", branches["biz:slot"]["label"])

    def test_blog_favorite_not_ticket_confirm(self) -> None:
        schema = self._schema("DOM-BLOG")
        model = module_model(schema, layout="biz")
        labels = self._walk_labels(model)
        self.assertNotIn("收藏确认", labels)
        self.assertIn("收藏审核", labels)
        branches = {c["id"]: c for c in model["root"]["children"]}
        self.assertIn("biz:favorite", branches)
        self.assertEqual(branches["biz:favorite"]["label"], "收藏模块")
        self.assertNotIn("biz:ticket", branches)

    def test_svg_renders(self) -> None:
        schema = self._shop_schema()
        for layout in ("biz", "side"):
            model = module_model(schema, layout=layout)
            svg = render_module_svg(model)
            self.assertIn("<svg", svg)
            self.assertIn("mod-node", svg)
            self.assertIn("测试课题", svg)
            self.assertIn('stroke="#000"', svg)
            self.assertIn('fill="#fff"', svg)
            self.assertNotIn("#eef2ff", svg)
            self.assertNotIn("#334155", svg)

    def test_patch_sanitize(self) -> None:
        clean = sanitize_module_label_patch(
            {"nodes": {"branch:user": "用户门户", "x": "Hack"}},
            [{"id": "branch:user", "label": "用户端"}],
        )
        self.assertEqual(clean["nodes"].get("branch:user"), "用户门户")
        self.assertNotIn("x", clean["nodes"])

    def test_proposal_hints_idempotent(self) -> None:
        model = {
            "title": "系统",
            "root": {
                "id": "root",
                "label": "系统",
                "children": [
                    {"id": "branch:user", "label": "用户端", "children": []},
                ],
            },
        }
        out = apply_proposal_hints(model, "学生端功能说明")
        self.assertEqual(out["root"]["children"][0]["label"], "用户端")


if __name__ == "__main__":
    unittest.main()
