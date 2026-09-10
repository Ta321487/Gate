"""用例图契约：数量、动词、include/extend 方向、菜单溯源、SVG/mdj、全域 builder。"""

from __future__ import annotations

import json
import re
import unittest

from app.bake.domain_schema import build_domain_schema
from app.bake.schema.templates import SCHEMA_BUILDERS
from app.bake.schema.usecases import (
    _LEVEL1_COUNT,
    assert_usecase_invariants,
    export_staruml_mdj,
    layout_usecase,
    list_usecase_actors,
    render_usecase_svg,
    usecase_model,
)


def _has_extend(model: dict) -> bool:
    for uc in model.get("level1") or []:
        for k in uc.get("includes") or []:
            if isinstance(k, dict) and k.get("relation") == "extend":
                return True
    return False


class UsecaseContractTests(unittest.TestCase):
    def test_shop_user_five_l1_and_extend(self) -> None:
        schema = build_domain_schema("农产品电商系统", "DOM-SHOP")
        model = usecase_model(schema, actor="user", title_fallback="农产品电商")
        self.assertEqual(len(model["level1"]), _LEVEL1_COUNT)
        desc = model["description"]
        for i in range(1, _LEVEL1_COUNT + 1):
            self.assertIn(f"（{i}）", desc)
        self.assertNotIn(f"（{_LEVEL1_COUNT + 1}）", desc)
        self.assertTrue(_has_extend(model), "电商域用户侧应有 extend（如支付）")
        lay = layout_usecase(model)
        self.assertEqual(len({round(n["cx"], 1) for n in lay["l1"]}), 1)
        self.assertEqual(len({round(n["cx"], 1) for n in lay["l2"]}), 1)
        for e in lay["edges"]:
            if e["kind"] == "extend":
                self.assertEqual(e["label"], "<<extend>>")
                self.assertTrue(any(n["id"] == e["from"] for n in lay["l2"]))
            elif e["kind"] == "include":
                self.assertEqual(e["label"], "<<include>>")
                self.assertTrue(any(n["id"] == e["from"] for n in lay["l1"]))
        svg = render_usecase_svg(model)
        # SVG 文本节点会转义尖括号
        self.assertTrue(
            "<<include>>" in svg or "&lt;&lt;include&gt;&gt;" in svg,
            "SVG 缺 include 标注",
        )
        self.assertTrue(
            "<<extend>>" in svg or "&lt;&lt;extend&gt;&gt;" in svg,
            "SVG 缺 extend 标注",
        )
        self.assertIn("stroke-dasharray", svg)
        mdj = json.loads(export_staruml_mdj(model))
        blob = json.dumps(mdj, ensure_ascii=False)
        self.assertIn("UMLUseCase", blob)
        self.assertIn("UMLInclude", blob)
        self.assertIn("UMLExtend", blob)
        # 同宽椭圆视图
        views = []

        def walk(o):
            if isinstance(o, dict):
                if o.get("_type") == "UMLUseCaseView":
                    views.append(o)
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for x in o:
                    walk(x)

        walk(mdj)
        self.assertGreaterEqual(len(views), 5)
        widths = {int(v.get("width") or 0) for v in views}
        self.assertEqual(len(widths), 1, widths)

    def test_verb_prefix_on_l2(self) -> None:
        schema = build_domain_schema("图书馆管理系统", "DOM-LIBRARY")
        for side in ("user", "admin"):
            model = usecase_model(schema, actor=side, title_fallback="图书馆")
            for uc in model["level1"]:
                for kid in uc["includes"]:
                    self.assertRegex(
                        kid["label"],
                        r"^(查看|进行|编辑|提交|管理|选择|确认|登录|注册|充值|反馈|审核|"
                        r"办理|预约|取消|支付|导出|催办|评价|驳回|通过|填写|检索|打开|结束|"
                        r"切换|连接|打卡|签到|开门|补缴|申请|下单|收藏|浏览|进入|使用|参加|参与|收发|查阅)",
                        kid["label"],
                    )

    def test_no_invented_menu_keys(self) -> None:
        schema = build_domain_schema("酒店预订系统", "DOM-HOTEL")
        menus = schema.get("menus") or {}
        for side in ("user", "admin"):
            allowed = {
                str(m.get("key") or "")
                for m in (menus.get(side) or [])
                if isinstance(m, dict)
            }
            if side == "admin":
                allowed.add("dashboard")
            model = usecase_model(schema, actor=side, title_fallback="酒店")
            for uc in model["level1"]:
                for k in uc.get("menu_keys") or []:
                    self.assertIn(k, allowed, f"{side} L1 invented {k}")
                for kid in uc["includes"]:
                    for k in kid.get("menu_keys") or []:
                        self.assertIn(k, allowed, f"{side} L2 invented {k}")

    def test_staff_posts_listed_as_actors(self) -> None:
        schema = build_domain_schema("图书馆管理系统", "DOM-LIBRARY")
        actors = list_usecase_actors(schema)
        ids = [a["id"] for a in actors]
        self.assertIn("user", ids)
        self.assertIn("admin", ids)
        self.assertTrue(any(i.startswith("staff:") for i in ids), ids)
        # 馆员岗位可出图
        staff_id = next(i for i in ids if i.startswith("staff:"))
        model = usecase_model(schema, actor=staff_id, title_fallback="图书馆")
        self.assertEqual(len(model["level1"]), _LEVEL1_COUNT)
        self.assertEqual(model["actor"]["id"], staff_id)

    def test_no_pay_extend_on_admin_or_staff(self) -> None:
        """管理端/商家/馆员不得挂「进行支付」；标签不得叠字。"""
        for domain, title in (
            ("DOM-SHOP", "农产品电商"),
            ("DOM-FOOD", "餐饮"),
            ("DOM-HOTEL", "酒店"),
            ("DOM-LIBRARY", "图书馆"),
        ):
            schema = build_domain_schema(title, domain)
            for a in list_usecase_actors(schema):
                if a["id"] == "user":
                    continue
                model = usecase_model(schema, actor=a["id"], title_fallback=title)
                for uc in model["level1"]:
                    self.assertFalse(
                        re.match(r"^管理.+管理$", str(uc.get("label") or "")),
                        f"{domain}/{a['id']} L1 {uc.get('label')}",
                    )
                    for kid in uc.get("includes") or []:
                        self.assertNotEqual(
                            kid.get("label"),
                            "进行支付",
                            f"{domain}/{a['id']} 误挂支付 under {uc.get('label')}",
                        )
                        self.assertFalse(
                            re.match(r"^管理.+管理$", str(kid.get("label") or "")),
                            f"{domain}/{a['id']} L2 {kid.get('label')}",
                        )

    def test_user_pay_only_under_orderish_l1(self) -> None:
        schema = build_domain_schema("农产品电商系统", "DOM-SHOP")
        model = usecase_model(schema, actor="user", title_fallback="电商")
        pay_parents = []
        for uc in model["level1"]:
            for kid in uc.get("includes") or []:
                if kid.get("label") == "进行支付":
                    pay_parents.append(str(uc.get("label") or ""))
                    self.assertEqual(kid.get("relation"), "extend")
        # 若有支付扩展，父级不得是留言类
        for lab in pay_parents:
            self.assertNotIn("留言", lab)
            self.assertFalse(lab.startswith("提交留言"))

    def test_materials_first_shop_opening(self) -> None:
        """开题身份模块枚举应驱动一级用例，且非用户不得支付。"""
        opening = """
用户功能模块划分为：登录注册模块、个人中心模块【个人信息、收藏、收货地址】、商品模块【浏览搜索农产品、加入购物车】、活动模块【查看促销信息】、留言反馈模块、客服模块、评价模块、购物车【在线支付】、支付模块、订单模块、申请售后。
商家功能模块划分为：登录注册模块、个人中心模块、农产品管理模块、评价管理模块、订单管理模块、售后管理、客服模块、留言反馈模块、活动管理模块、数据分析。
管理员功能模块划分为：登录、用户管理模块、商家管理模块、评价管理模块、售后管理模块、订单管理模块、农产品商品管理模块、留言反馈模块、农产品分类模块、活动管理模块。
"""
        schema = build_domain_schema("农产品电商系统", "DOM-SHOP", proposal_text=opening)
        # 买家
        user = usecase_model(schema, actor="user", proposal_text=opening, title_fallback="电商")
        self.assertIn("开题", user.get("source_note", ""))
        blobs = json.dumps(user, ensure_ascii=False)
        self.assertTrue(any(x in blobs for x in ("浏览商品", "商品", "购物车", "订单")))
        # 平台管理员
        admin = usecase_model(schema, actor="admin", proposal_text=opening, title_fallback="电商")
        for uc in admin["level1"]:
            for kid in uc["includes"]:
                self.assertNotEqual(kid.get("label"), "进行支付")
                self.assertFalse(re.match(r"^管理.+管理$", str(kid.get("label") or "")))
                self.assertRegex(
                    str(kid.get("label") or ""),
                    r"^(查看|进行|编辑|提交|管理|选择|确认|登录|注册|办理|预约|取消|支付|审核|浏览|进入|使用|参加|参与|联系|收藏|发表|加入|评价)",
                )
        # 商家
        actors = list_usecase_actors(schema)
        merchant = next((a for a in actors if a["id"].startswith("staff:")), None)
        self.assertIsNotNone(merchant)
        m = usecase_model(schema, actor=merchant["id"], proposal_text=opening, title_fallback="电商")
        self.assertIn("开题", m.get("source_note", ""))
        for uc in m["level1"]:
            for kid in uc["includes"]:
                self.assertNotEqual(kid.get("label"), "进行支付")

    def test_customer_hard_constraints(self) -> None:
        """客户硬约束：同尺寸竖线、include、图文序号一一对应、段落、二级动词。"""
        from app.bake.schema.usecase_style import resolve_usecase_style

        style = resolve_usecase_style()
        n_l1 = int(style["level1_count"])
        schema = build_domain_schema("图书馆管理系统", "DOM-LIBRARY")
        model = usecase_model(schema, actor="user", title_fallback="图书馆")
        self.assertEqual(len(model["level1"]), n_l1)
        desc = model["description"]
        self.assertNotIn("\n", desc.strip())
        # 序号与图上一级一一对应（现客户 n_l1=5，故到（5）；不是抽象「最多五个」）
        for i in range(1, n_l1 + 1):
            self.assertEqual(desc.count(f"（{i}）"), 1)
        self.assertNotIn(f"（{n_l1 + 1}）", desc)
        lay = layout_usecase(model)
        self.assertEqual(len({round(n["cx"], 1) for n in lay["l1"]}), 1)
        self.assertEqual(len({round(n["cx"], 1) for n in lay["l2"]}), 1)
        self.assertTrue(all(abs(n["w"] - lay["uc_w"]) < 0.1 for n in lay["l1"] + lay["l2"]))
        self.assertTrue(any(e["kind"] == "include" and e["label"] == "<<include>>" for e in lay["edges"]))
        for uc in model["level1"]:
            self.assertNotIn("综合功能", uc["label"])
            self.assertNotIn("综合业务", uc["label"])
            self.assertTrue(any(k.get("relation") == "include" for k in uc["includes"]))
            for kid in uc["includes"]:
                self.assertRegex(
                    kid["label"],
                    r"^(查看|进行|编辑|提交|管理|选择|确认|登录|注册|办理|预约|浏览|进入|使用|申请|收藏|发表|加入|联系|审核|支付)",
                )
        self.assertEqual(model.get("style", {}).get("id"), style["id"])

    def test_no_shell_composite_l1_labels(self) -> None:
        """合并凑满一级时禁止「使用综合功能/办理综合业务」空壳名。"""
        opening = """
用户功能模块划分为：登录注册模块、个人中心模块【个人信息、收藏、收货地址】、商品模块【浏览搜索农产品、加入购物车】、活动模块【查看促销信息】、留言反馈模块、客服模块、评价模块、购物车【在线支付】、支付模块、订单模块、申请售后。
商家功能模块划分为：登录注册模块、个人中心模块、农产品管理模块、评价管理模块、订单管理模块、售后管理、客服模块、留言反馈模块、活动管理模块、数据分析。
管理员功能模块划分为：登录、用户管理模块、商家管理模块、评价管理模块、售后管理模块、订单管理模块、农产品商品管理模块、留言反馈模块、农产品分类模块、活动管理模块。
"""
        schema = build_domain_schema("农产品电商系统", "DOM-SHOP", proposal_text=opening)
        for a in list_usecase_actors(schema):
            m = usecase_model(schema, actor=a["id"], proposal_text=opening, title_fallback="电商")
            blob = json.dumps(m, ensure_ascii=False)
            self.assertNotIn("综合功能", blob, a["id"])
            self.assertNotIn("综合业务", blob, a["id"])
            self.assertEqual(len(m["level1"]), 5)
            self.assertEqual(m["description"].count("（"), 5)

    def test_all_schema_builders(self) -> None:
        fails: list[str] = []
        for domain in sorted(SCHEMA_BUILDERS.keys()):
            try:
                schema = build_domain_schema(domain.replace("DOM-", "") + "系统", domain)
                actors = list_usecase_actors(schema)
                self.assertTrue(actors, domain)
                for a in actors:
                    model = usecase_model(schema, actor=a["id"], title_fallback=domain)
                    assert_usecase_invariants(model, schema=schema, actor=a["id"])
                    svg = render_usecase_svg(model)
                    self.assertIn("ellipse", svg)
                    json.loads(export_staruml_mdj(model))
            except Exception as e:
                fails.append(f"{domain}: {e}")
        self.assertFalse(fails, "\n".join(fails[:20]))


if __name__ == "__main__":
    unittest.main()
