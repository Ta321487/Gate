"""用例图描述准确性：禁空壳、禁同名、描述须引用全部 L1/L2。"""

from __future__ import annotations

import re
import unittest

from app.bake.domain_schema import build_domain_schema
from app.bake.schema.templates import SCHEMA_BUILDERS
from app.bake.schema.usecases import list_usecase_actors, usecase_model
from app.llm.agents_usecase import accept_polished_description

_SHOP_OPENING = """
用户功能模块划分为：登录注册模块、个人中心模块【个人信息、收藏、收货地址】、商品模块【浏览搜索农产品、加入购物车】、活动模块【查看促销信息】、留言反馈模块、客服模块、评价模块、购物车【在线支付】、支付模块、订单模块、申请售后。
商家功能模块划分为：登录注册模块、个人中心模块【店铺信息编辑】、农产品管理模块【农产品商品新增、上下架、信息编辑、库存以及库存预警等】、评价管理模块【查看或回复用户评价】、订单管理模块【修改或查看订单状态、发货操作等】、售后管理【退货审核】、客服模块、留言反馈模块、活动管理模块【添加促销信息、添加新品公告】、数据分析。
管理员功能模块划分为：登录、用户管理模块、商家管理模块、评价管理模块、售后管理模块、订单管理模块、农产品商品管理模块、留言反馈模块、农产品分类模块、活动管理模块。
"""


class UsecaseProseAccuracyTests(unittest.TestCase):
    def test_library_user_no_filler_or_confirm(self) -> None:
        schema = build_domain_schema("图书馆管理系统", "DOM-LIBRARY")
        model = usecase_model(schema, actor="user", title_fallback="图书馆")
        desc = model["description"]
        self.assertNotIn("完成相关操作", desc)
        self.assertNotIn("确认", desc)
        self.assertIn("登录注册", desc)
        self.assertIn("检索图书", desc)
        for uc in model["level1"]:
            labs = {uc["label"]}
            for kid in uc["includes"]:
                self.assertNotEqual(kid["label"], uc["label"])
                self.assertNotIn(kid["label"], labs)
                labs.add(kid["label"])
                self.assertIn(f"「{kid['label']}」", desc)
            self.assertIn(f"「{uc['label']}」", desc)

    def test_merchant_materials_no_garbled_l2(self) -> None:
        """开题细节驱动时：禁「等」、禁「管理添加」、禁「…编辑列表」叠词。"""
        schema = build_domain_schema(
            "农产品电商系统", "DOM-SHOP", proposal_text=_SHOP_OPENING
        )
        actors = list_usecase_actors(schema)
        merchant = next(a for a in actors if a["id"].startswith("staff:"))
        model = usecase_model(
            schema,
            actor=merchant["id"],
            proposal_text=_SHOP_OPENING,
            title_fallback="电商",
        )
        desc = model["description"]
        self.assertNotIn("完成相关操作", desc)
        self.assertNotRegex(desc, r"」与「[^」]+」与「")
        labels: list[str] = []
        for uc in model["level1"]:
            labels.append(uc["label"])
            for k in uc["includes"]:
                labels.append(k["label"])
        joined = " | ".join(labels)
        self.assertNotIn("等", joined)
        for lab in labels:
            self.assertIsNone(
                re.match(r"^管理(新增|添加|编辑|修改|删除|审核|查看|回复)", lab),
                f"叠动词 {lab}",
            )
            self.assertIsNone(re.search(r"编辑.+编辑", lab), f"叠编辑 {lab}")
            self.assertIsNone(re.search(r"查看.+编辑列表", lab), f"脏列表名 {lab}")
        self.assertNotIn("管理发货操作等", joined)
        self.assertNotIn("管理添加促销信息", joined)
        self.assertNotIn("查看店铺信息编辑列表", joined)
        # 开题有农产品管理：不得为凑 5 个一级并进订单后丢掉独立业务名
        l1_blob = " ".join(uc["label"] for uc in model["level1"])
        self.assertTrue(
            any(t in l1_blob for t in ("农产品", "商品")),
            f"合并丢业务名: {l1_blob}",
        )
        n = len(model["level1"])
        self.assertEqual(desc.count("（"), n)
        self.assertGreaterEqual(n, 5)
        # 个人中心不得被并进农产品后消失
        self.assertTrue(
            any("个人" in uc["label"] or "中心" in uc["label"] for uc in model["level1"])
            or any("资料" in k["label"] or "店铺" in k["label"] for uc in model["level1"] for k in uc["includes"]),
            "个人中心/店铺资料应保留",
        )

    def test_study_like_materials_no_business_filler(self) -> None:
        """类校多样例：禁「查看业务列表」、禁「查看选购/查看充值」叠动词。"""
        opening = """
用户功能模块划分为：注册与账户登录模块、预约模块【长期或短期座位预约、扫码支付】、自习室模块【查看自习室信息、选购优惠套餐】、通知模块【查看预约记录、查看占用记录、查看交易通知】、个人中心模块【余额充值、修改个人信息、提交意见反馈、欠费补缴】。
"""
        schema = build_domain_schema("图书馆管理系统", "DOM-LIBRARY", proposal_text=opening)
        model = usecase_model(
            schema, actor="user", proposal_text=opening, title_fallback="自习室"
        )
        self.assertEqual(len(model["level1"]), 5)
        self.assertEqual(model["description"].count("（"), 5)
        labels = [k["label"] for uc in model["level1"] for k in uc["includes"]]
        for lab in labels:
            self.assertNotIn("业务", lab, lab)
            self.assertFalse(lab.startswith("查看选购"), lab)
            self.assertFalse(lab.startswith("查看余额"), lab)
            self.assertFalse(lab.startswith("查看欠费"), lab)
        blob = " ".join(labels)
        self.assertTrue(any("支付" in x for x in labels) or "进行支付" in blob)
        self.assertTrue(any("充值" in x for x in labels))
        self.assertTrue(any("选购" in x or "套餐" in x for x in labels))

    def test_admin_materials_action_names_and_dashboard_extend(self) -> None:
        """管理员开题：禁权限腔/CRUD；工作台为 extend；用户/商品不并进分类。"""
        opening = """
用户功能模块划分为：登录注册模块、商品模块、订单模块。
商家功能模块划分为：登录注册模块、农产品管理模块、订单管理模块。
管理员功能模块划分为：登录、用户管理模块、商家管理模块、评价管理模块、售后管理模块、订单管理模块【拥有最高权限】、农产品商品管理模块【全局商品信息增删改查、最高权限审核商品内容与图片】、留言反馈模块、农产品分类模块、活动管理模块、客服模块【分别与用户和商家沟通】。
"""
        schema = build_domain_schema(
            "农产品电商系统", "DOM-SHOP", proposal_text=opening
        )
        model = usecase_model(
            schema, actor="admin", proposal_text=opening, title_fallback="电商"
        )
        labels: list[str] = []
        dash_rels: list[str] = []
        for uc in model["level1"]:
            labels.append(uc["label"])
            for k in uc["includes"]:
                labels.append(k["label"])
                if k["label"] == "查看工作台":
                    dash_rels.append(str(k.get("relation") or ""))
        joined = " ".join(labels)
        self.assertNotIn("增删改查", joined)
        self.assertNotIn("最高权限", joined)
        self.assertNotIn("拥有最高权限", joined)
        self.assertNotIn("分别与", joined)
        self.assertNotIn("查看管理列表", joined)
        self.assertTrue(dash_rels, "应挂查看工作台")
        self.assertTrue(all(r == "extend" for r in dash_rels), dash_rels)
        # 分类不得吞并用户/商品成为唯一入口名
        l1 = [uc["label"] for uc in model["level1"]]
        if any("分类" in x for x in l1):
            cat = next(x for x in l1 if "分类" in x)
            kids = next(uc["includes"] for uc in model["level1"] if uc["label"] == cat)
            kid_labs = " ".join(k["label"] for k in kids)
            self.assertNotIn("管理用户", kid_labs)
        self.assertTrue(
            any("用户" in x for x in l1) or any("商品" in x or "农产品" in x for x in l1),
            l1,
        )

    def test_cross_domain_builders_prose(self) -> None:
        samples = [
            ("DOM-LIBRARY", "图书馆管理系统"),
            ("DOM-SHOP", "农产品电商系统"),
            ("DOM-HOSPITAL", "医院预约系统"),
            ("DOM-HOTEL", "酒店预订系统"),
        ]
        for domain, title in samples:
            if domain not in SCHEMA_BUILDERS and domain != "DOM-LIBRARY":
                pass
            schema = build_domain_schema(title, domain)
            for a in list_usecase_actors(schema):
                with self.subTest(domain=domain, actor=a["id"]):
                    model = usecase_model(schema, actor=a["id"], title_fallback=title)
                    desc = model["description"]
                    self.assertNotIn("完成相关操作", desc)
                    self.assertNotRegex(desc, r"包含「[^」]+」，包含「")
                    for uc in model["level1"]:
                        for kid in uc["includes"]:
                            lab = kid["label"]
                            self.assertNotEqual(
                                lab,
                                uc["label"],
                                f"{domain}/{a['id']}: {uc['label']}=={lab}",
                            )
                            if lab.startswith("确认"):
                                self.fail(f"凑数确认二级: {lab}")
                            self.assertNotIn("等", lab)
                            self.assertIsNone(
                                re.match(
                                    r"^管理(新增|添加|编辑|修改|删除|审核|查看|回复)",
                                    lab,
                                ),
                                f"叠动词 {lab}",
                            )

    def test_school_five_modules_numbers_match_circles(self) -> None:
        """校样：段落写到（5）则一级恰好 5；二级须真动词开头（禁「预约记录」假动宾）。"""
        opening = """
用户功能模块划分为：注册与账户登录模块、预约模块【座位预约、扫码支付】、商品模块【浏览商品、选购套餐】、通知模块【预约记录、交易通知】、个人中心模块【余额充值、修改个人信息、意见反馈】。
"""
        schema = build_domain_schema(
            "农产品电商系统", "DOM-SHOP", proposal_text=opening
        )
        model = usecase_model(
            schema, actor="user", proposal_text=opening, title_fallback="电商"
        )
        self.assertEqual(len(model["level1"]), 5)
        desc = model["description"]
        for i in range(1, 6):
            self.assertEqual(desc.count(f"（{i}）"), 1)
        self.assertNotIn("（6）", desc)
        labs = [k["label"] for uc in model["level1"] for k in uc["includes"]]
        self.assertNotIn("预约记录", labs)
        self.assertTrue(
            any(x in labs for x in ("查看预约记录", "查看交易通知")),
            labs,
        )
        for lab in labs:
            self.assertRegex(
                lab,
                r"^(查看|进行|编辑|提交|管理|选择|确认|登录|注册|办理|预约|浏览|进入|使用|申请|收藏|发表|加入|联系|审核|支付|添加|修改|删除|回复|新增|选购|充值|反馈|填写|检索|导出|补缴)",
            )

    def test_polish_accept_keeps_quotes(self) -> None:
        level1 = [
            {
                "label": "登录注册",
                "includes": [
                    {"label": "登录", "relation": "include"},
                    {"label": "注册", "relation": "include"},
                ],
            },
            {
                "label": "检索图书",
                "includes": [
                    {"label": "浏览图书列表", "relation": "include"},
                    {"label": "查看图书详情", "relation": "include"},
                ],
            },
        ]
        draft = (
            "（1）读者可通过「登录注册」完成身份认证，其中包含「登录」与「注册」。"
            "（2）读者可通过「检索图书」查询业务资料，其中包含「浏览图书列表」与「查看图书详情」。"
        )
        good = (
            "（1）读者可通过「登录注册」完成身份认证，其中包含「登录」与「注册」。"
            "（2）读者可通过「检索图书」查询馆藏信息，其中包含「浏览图书列表」与「查看图书详情」。"
        )
        self.assertEqual(
            accept_polished_description(
                good, draft=draft, actor="读者", level1=level1, n_l1=2
            ),
            good,
        )
        bad_rename = good.replace("「检索图书」", "「图书查询」")
        self.assertIsNone(
            accept_polished_description(
                bad_rename, draft=draft, actor="读者", level1=level1, n_l1=2
            )
        )
        bad_filler = good.replace("查询馆藏信息", "完成相关操作")
        self.assertIsNone(
            accept_polished_description(
                bad_filler, draft=draft, actor="读者", level1=level1, n_l1=2
            )
        )


if __name__ == "__main__":
    unittest.main()
