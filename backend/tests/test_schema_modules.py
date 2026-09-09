"""功能模块图：默认按身份（材料优先）；按业务保留；细节可展开。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.bake.schema.modules import (
    _SCHEMA_LEAF_NOTE,
    apply_proposal_hints,
    module_model,
    parse_identity_modules,
    render_module_svg,
    sanitize_module_label_patch,
)


_SHOP_ENUM = """
用户功能模块划分为：登录注册模块、个人中心模块【个人信息（头像、昵
称、联系方式、修改密码等）、收藏、收货地址】、商品模块【浏览搜索农
产品、查看农产品详情（产地、采摘时间、商品规格、价格、简介、图
片）、收藏、加入购物车、查看评价】、活动模块【查看促销信息、节日优
惠等公告信息】、留言反馈模块（与管理员沟通)、客服模块（与商家在线
沟通)、评价模块【查看其他用户对此商品的评价、确认收货后可发表评
价】、购物车【商品数量增减、删除商品、价格计算、在线支付】、支付模
块（可做到在线支付，选择支付宝、微信输入密码支付，假的就行）、订单
模块【查看订单状态(待发货、已发货、已完成、已取消)】、申请售后
【退货申请】。
商家功能模块划分为：登录注册模块、个人中心模块【店铺信息编辑（店铺
名称、简介、联系方式、修改密码)】、农产品管理模块（农产品商品新
增、上下架、信息编辑、查看库存以及库存预警等)、评价管理模块（查看
或回复用户评价)、订单管理模块(修改或查看订单状态(待付款、待发
货、已发货、运输中、已签收、已完成、已取消)、发货操作等)、售后管
理【退货审核】、客服模块（与用户在线沟通)、留言反馈模块（与管理员
沟通)、活动管理模块（添加促销信息、添加新品公告）、数据分析（查看
店铺销售总额、每日/每月销量、商品销量排行、库存数据统计、订单数据
统计、热销商品分析)。
管理员功能模块划分为：登录、用户管理模块、商家管理模块、评价管理模
块【查看全部用户评价，删除】、售后管理模块【查看全平台售后工单，拥
有最高权限】、订单管理模块【查看全平台所有订单状态，拥有最高权
限】、农产品商品管理模块【全局商品信息增删改查、最高权限审核商品内
容与图片，违规商品强制下架】、留言反馈模块【分别与用户和商家沟
通】、农产品分类模块、活动管理模块（审核商家添加的促销、新品公告等
信息)。
"""


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

    def test_parse_shop_identity_enum(self) -> None:
        secs = parse_identity_modules(_SHOP_ENUM)
        labs = [s["label"] for s in secs]
        self.assertEqual(labs, ["用户", "商家", "管理员"])
        user_mods = [m["label"] for m in secs[0]["modules"]]
        self.assertIn("登录注册模块", user_mods)
        self.assertIn("商品模块", user_mods)
        self.assertIn("购物车", user_mods)
        self.assertIn("申请售后", user_mods)
        # 【】细节进 details，不进一级名
        goods = next(m for m in secs[0]["modules"] if m["label"] == "商品模块")
        self.assertTrue(goods["details"])
        self.assertTrue(any("浏览" in d or "详情" in d for d in goods["details"]))

    def test_parse_stops_before_methodology(self) -> None:
        text = (
            _SHOP_ENUM
            + "2.1.2文献研究法在前期准备阶段，主要通过文献研究法通过阅读大量关于农产品销售"
            "SpringBoot框架、Vue框架以及MySQL数据库相关的关键技术的文献资料。"
        )
        secs = parse_identity_modules(text)
        self.assertEqual([s["label"] for s in secs], ["用户", "商家", "管理员"])
        admin_labs = [m["label"] for m in secs[2]["modules"]]
        self.assertLessEqual(len(admin_labs), 12)
        self.assertNotIn("SpringBoot框架", admin_labs)
        blob = " ".join(admin_labs)
        self.assertNotIn("文献研究", blob)
        self.assertIn("活动管理模块", admin_labs)

    def test_parse_nested_and_mixed_brackets(self) -> None:
        text = (
            "用户功能模块划分为：个人中心模块【个人信息（头像、昵称）、收藏】、"
            "留言反馈模块（与管理员沟通)、订单模块【状态(待发货、已完成)】。"
        )
        secs = parse_identity_modules(text)
        self.assertEqual(secs[0]["label"], "用户")
        labs = [m["label"] for m in secs[0]["modules"]]
        self.assertEqual(labs, ["个人中心模块", "留言反馈模块", "订单模块"])
        center = secs[0]["modules"][0]
        self.assertIn("收藏", center["details"])
        self.assertTrue(any("个人信息" in d for d in center["details"]))

    def test_parse_alt_phrasing(self) -> None:
        text = (
            "学生端功能主要包括：登录注册、选题申请、文档上传。"
            "教师功能模块包括：课题发布、选题审核、成绩录入。"
            "管理员主要功能如下：用户管理、公告管理。"
        )
        secs = parse_identity_modules(text)
        labs = [s["label"] for s in secs]
        self.assertEqual(labs, ["学生", "教师", "管理员"])
        self.assertIn("选题申请", [m["label"] for m in secs[0]["modules"]])

    def test_remap_front_back_jargon(self) -> None:
        schema = self._shop_schema()
        text = "前台功能模块划分为：浏览商品、下单。后台功能模块划分为：用户管理、订单管理。"
        secs = parse_identity_modules(text, schema=schema)
        labs = [s["label"] for s in secs]
        self.assertNotIn("前台", labs)
        self.assertNotIn("后台", labs)
        # 框上用交付 roles 短名（买家 / 商城主管），不写前台后台
        self.assertTrue(any(x in labs for x in ("买家", "用户")))
        self.assertTrue(any("管" in x or x == "管理员" for x in labs))

    def test_model_by_identity_from_materials(self) -> None:
        schema = self._shop_schema()
        model = module_model(
            schema,
            proposal_text=_SHOP_ENUM,
            layout="identity",
        )
        self.assertEqual(model["layout"], "identity")
        self.assertEqual(model["leaf_source"], "materials")
        self.assertEqual(model["leaf_source_note"], "")
        branches = {c["label"]: c for c in model["root"]["children"]}
        self.assertIn("用户", branches)
        self.assertIn("商家", branches)
        self.assertIn("管理员", branches)
        user_labs = [c["label"] for c in branches["用户"]["children"]]
        self.assertIn("商品模块", user_labs)
        # 默认不展开细节
        goods = next(c for c in branches["用户"]["children"] if c["label"] == "商品模块")
        self.assertNotIn("children", goods)

    def test_expand_details(self) -> None:
        schema = self._shop_schema()
        model = module_model(
            schema,
            proposal_text=_SHOP_ENUM,
            layout="identity",
            expand_details=True,
        )
        user = next(c for c in model["root"]["children"] if c["label"] == "用户")
        goods = next(c for c in user["children"] if c["label"] == "商品模块")
        self.assertTrue(goods.get("children"))

    def test_identity_schema_fallback_note(self) -> None:
        schema = self._shop_schema()
        model = module_model(schema, proposal_text="", layout="identity")
        self.assertEqual(model["leaf_source"], "schema")
        self.assertEqual(model["leaf_source_note"], _SCHEMA_LEAF_NOTE)
        branches = {c["label"]: c for c in model["root"]["children"]}
        # 身份用 roles 短名，不叫前台/后台
        self.assertNotIn("前台功能", branches)
        self.assertNotIn("后台管理", branches)
        self.assertTrue(set(branches) & {"买家", "用户", "管理员"})
        svg = render_module_svg(model)
        self.assertNotIn(_SCHEMA_LEAF_NOTE, svg)
        self.assertNotIn("仅供参考", svg)

    def test_side_alias_is_identity(self) -> None:
        schema = self._shop_schema()
        model = module_model(schema, layout="side")
        self.assertEqual(model["layout"], "identity")

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
        archive_labs = {c["label"] for c in branches["biz:archive"]["children"]}
        self.assertIn("商品浏览", archive_labs)
        self.assertIn("商品管理", archive_labs)
        self.assertNotIn("分类管理", archive_labs)
        admin_labs = {c["label"] for c in branches["biz:admin"]["children"]}
        self.assertIn("分类管理", admin_labs)
        self.assertIn("用户管理", admin_labs)
        self.assertNotIn("children", branches["biz:cart"])
        self.assertEqual(branches["biz:cart"]["label"], "购物车")
        user_labs = {c["label"] for c in branches["biz:user"]["children"]}
        self.assertIn("注册", user_labs)
        self.assertIn("登录", user_labs)
        self.assertIn("个人资料", user_labs)

    def test_default_layout_is_identity(self) -> None:
        schema = self._shop_schema()
        model = module_model(schema)
        self.assertEqual(model["layout"], "identity")

    def test_no_phantom_from_proposal(self) -> None:
        schema = self._shop_schema()
        model = module_model(
            schema,
            proposal_text="需要大数据分析与区块链溯源模块",
            layout="biz",
        )
        blob = " ".join(self._walk_labels(model))
        self.assertNotIn("区块链", blob)
        self.assertNotIn("大数据", blob)

    def test_hospital_identity_and_biz(self) -> None:
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
        ident = module_model(schema, layout="identity")
        self.assertEqual(ident["root"]["children"][0]["label"], "患者")
        user_labs = [c["label"] for c in ident["root"]["children"][0]["children"]]
        self.assertEqual(user_labs[0], "登录注册模块")
        self.assertIn("选医生模块", user_labs)

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

    def test_hotel_order_stay_fulfill_not_logistics(self) -> None:
        schema = self._schema("DOM-HOTEL")
        order = (schema.get("entities") or {}).get("order") or {}
        self.assertEqual(order.get("fulfillMode"), "stay")
        self.assertEqual((order.get("verbs") or {}).get("ship"), "办理入住")
        self.assertEqual((order.get("verbs") or {}).get("complete"), "办理离店")
        self.assertEqual((order.get("states") or {}).get("shipped"), "已入住")
        self.assertEqual((order.get("states") or {}).get("completed"), "已离店")
        self.assertEqual(
            ((schema.get("entities") or {}).get("archive") or {})
            .get("fields", [{}])[1]
            .get("format"),
            "money",
        )

    def test_carrent_merges_slot_and_order(self) -> None:
        schema = self._schema("DOM-CARRENT")
        model = module_model(schema, layout="biz")
        branches = {c["id"]: c for c in model["root"]["children"]}
        self.assertIn("biz:slot", branches)
        self.assertNotIn("biz:order", branches)
        labs = {c["label"] for c in branches["biz:slot"]["children"]}
        self.assertTrue(labs & {"我的租约", "租约记录", "我的订单", "租车订单"})

    def test_carrent_order_rental_fulfill_not_logistics(self) -> None:
        schema = self._schema("DOM-CARRENT")
        order = (schema.get("entities") or {}).get("order") or {}
        self.assertEqual(order.get("fulfillMode"), "rental")
        self.assertEqual((order.get("verbs") or {}).get("ship"), "办理取车")
        self.assertEqual((order.get("verbs") or {}).get("complete"), "办理还车")
        self.assertEqual((order.get("states") or {}).get("shipped"), "租赁中")
        self.assertEqual((order.get("states") or {}).get("completed"), "已还车")
        self.assertEqual(
            ((schema.get("entities") or {}).get("archive") or {})
            .get("fields", [{}])[1]
            .get("format"),
            "money",
        )

    def test_blog_favorite_instant_not_ticket_audit(self) -> None:
        schema = self._schema("DOM-BLOG")
        model = module_model(schema, layout="biz")
        labels = self._walk_labels(model)
        self.assertNotIn("收藏确认", labels)
        self.assertNotIn("收藏审核", labels)
        self.assertIn("我的收藏", labels)
        branches = {c["id"]: c for c in model["root"]["children"]}
        self.assertIn("biz:favorite", branches)
        self.assertEqual(branches["biz:favorite"]["label"], "收藏模块")
        self.assertNotIn("biz:ticket", branches)

    def test_svg_renders(self) -> None:
        schema = self._shop_schema()
        for layout in ("biz", "identity"):
            model = module_model(schema, proposal_text=_SHOP_ENUM, layout=layout)
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
            {"nodes": {"identity:0": "用户门户", "x": "Hack"}},
            [{"id": "identity:0", "label": "用户"}],
        )
        self.assertEqual(clean["nodes"].get("identity:0"), "用户门户")
        self.assertNotIn("x", clean["nodes"])

    def test_proposal_hints_skip_identity(self) -> None:
        model = {
            "title": "系统",
            "layout": "identity",
            "root": {
                "id": "root",
                "label": "系统",
                "children": [
                    {"id": "identity:0", "label": "用户", "children": []},
                ],
            },
        }
        out = apply_proposal_hints(model, "前台功能说明")
        self.assertEqual(out["root"]["children"][0]["label"], "用户")


if __name__ == "__main__":
    unittest.main()
