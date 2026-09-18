"""全域答辩厚度合同：双扫、签名皮、商家枝、开题清单对齐。"""

from __future__ import annotations

import unittest

from app.bake.deep_skin_s import S_SKIN_CASES
from app.bake.domain_schema import attach_accept, build_domain_schema
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.features.opening_align import scan_opening_delivery_gaps
from app.bake.schema.modules import module_model
from app.bake.schema.templates import SCHEMA_BUILDERS
from app.bake.scene_scan import shop_product_kind

_LEAK = ("ISBN", "书名", "出版社", "索书号")


def _arch_fields(schema: dict) -> list[str]:
    ent = (schema.get("entities") or {}).get("archive") or {}
    return [
        str(f.get("label") or "")
        for f in (ent.get("fields") or [])
        if isinstance(f, dict)
    ]


def _arch_label(schema: dict) -> str:
    ent = (schema.get("entities") or {}).get("archive") or {}
    return str(ent.get("label") or "")


class DomainThicknessContractTests(unittest.TestCase):
    def test_all_builders_accept_proposal_text(self) -> None:
        for dom in sorted(SCHEMA_BUILDERS):
            with self.subTest(dom=dom):
                schema = build_domain_schema(
                    "测试课题", dom, proposal_text="占位开题正文用于双扫"
                )
                self.assertTrue(schema.get("labels") or schema.get("roles"))

    def test_bland_title_no_library_leak(self) -> None:
        for dom in sorted(SCHEMA_BUILDERS):
            with self.subTest(dom=dom):
                schema = build_domain_schema(
                    "管理系统", dom, proposal_text="主要功能：办理与查询。"
                )
                labels = _arch_fields(schema)
                if dom == "DOM-LIBRARY":
                    self.assertTrue(any("书" in x or "ISBN" in x for x in labels) or labels)
                    continue
                if dom in ("DOM-BLOG", "DOM-MEDIA", "DOM-MUSIC", "DOM-FORUM"):
                    continue
                for lab in labels:
                    for bad in _LEAK:
                        self.assertNotIn(bad, lab, msg=f"{dom} field {lab}")

    def test_body_only_deep_skin_moves(self) -> None:
        """正文写变体词、题名泛称 → 仍须切皮（双扫）。"""
        cases = [
            (
                "DOM-PROCURE",
                "管理系统",
                "学术期刊品目遴选荐购审核",
                "期刊品目",
            ),
            (
                "DOM-HOTEL",
                "管理系统",
                "乡村民宿客房预订入住离店",
                None,  # 看 authEyebrow
            ),
            (
                "DOM-SHOP",
                "电商系统",
                "文印打印店订单下单装订",
                None,
            ),
        ]
        for dom, title, body, want_arch in cases:
            with self.subTest(dom=dom):
                schema = build_domain_schema(title, dom, proposal_text=body)
                if want_arch:
                    self.assertEqual(_arch_label(schema), want_arch)
                if dom == "DOM-HOTEL":
                    self.assertIn("民宿", (schema.get("labels") or {}).get("authEyebrow") or "")
                if dom == "DOM-SHOP":
                    self.assertEqual(shop_product_kind(title, body), "print")
                    self.assertIn("装订规格", _arch_fields(schema))

    def test_shop_signature_labels(self) -> None:
        samples = [
            ("文印打印店", "装订规格"),
            ("鲜花零售商城", "配送说明"),
            ("校园跑腿代买", "代买说明"),
            ("积分兑换商城", "兑换说明"),
            ("农产品选购", "产地"),
        ]
        for title, needle in samples:
            with self.subTest(title=title):
                schema = build_domain_schema(title, "DOM-SHOP", proposal_text=title)
                self.assertIn(needle, _arch_fields(schema))

    def test_s_skin_body_only_subset(self) -> None:
        """深皮册抽样：仅正文也能推动字段或档案名（相对裸题）。"""
        bland = "管理系统"
        checked = 0
        for sid, hint, dom, _title in S_SKIN_CASES:
            if dom not in SCHEMA_BUILDERS:
                continue
            if checked >= 12:
                break
            # 跳过工单无档案列域
            if dom in ("DOM-DORM", "DOM-PROPERTY", "DOM-IT"):
                continue
            base = build_domain_schema(bland, dom, proposal_text="主要功能：办理。")
            skinned = build_domain_schema(bland, dom, proposal_text=hint)
            moved = (
                _arch_fields(base) != _arch_fields(skinned)
                or _arch_label(base) != _arch_label(skinned)
                or (base.get("labels") or {}).get("authEyebrow")
                != (skinned.get("labels") or {}).get("authEyebrow")
            )
            # 不是每条都必须改字段（有的只换种子）；至少抽样里多数应动
            if moved:
                checked += 1
        self.assertGreaterEqual(checked, 3, "正文双扫应至少推动若干深皮样例")

    def test_marketplace_module_branch_and_accept(self) -> None:
        text = """
用户功能模块划分为：登录注册、商品、购物车、支付（支付宝微信假的就行）、订单、申请售后、评价模块、留言反馈、客服模块（与商家在线沟通）。
商家功能模块划分为：店铺、农产品管理、订单、售后、客服、活动、数据分析。
管理员功能模块划分为：用户管理、商家管理、商品、分类、订单、售后、活动审核、留言。
"""
        schema = build_domain_schema("农产品电商", "DOM-SHOP", proposal_text=text)
        self.assertTrue(schema.get("shopMarketplace"))
        model = module_model(schema, proposal_text=text, layout="identity")
        labs = [c["label"] for c in model["root"]["children"]]
        self.assertIn("商家", labs)

        spec = attach_accept(
            {
                "title": "农产品电商",
                "domain": "DOM-SHOP",
                "archetype": "ARCH-TRADE",
                "archetypes": ["ARCH-TRADE"],
                "capabilities": list(schema.get("capabilities") or []),
                "entities": [],
                "features": [],
                "schema": schema,
            },
            text,
        )
        self.assertEqual(spec.get("accept"), "full", spec.get("accept_reason"))
        self.assertFalse(scan_opening_delivery_gaps(spec, text))

    def test_opening_gap_rejects_thin_shop(self) -> None:
        """开题写了客服/评价，能力未挂 → 对齐门禁拒收。"""
        text = "主要功能：客服模块与商家在线沟通；评价模块确认收货后发表评价；购物车下单。"
        # 裸 schema 无 dm / order_review
        schema = build_domain_schema("日用百货商城", "DOM-SHOP", proposal_text="购物车下单")
        spec = {
            "title": "日用百货商城",
            "domain": "DOM-SHOP",
            "capabilities": ["archive", "order_lines", "org_users", "content", "quota"],
            "schema": schema,
            "accept": "full",
        }
        gaps = scan_opening_delivery_gaps(spec, text)
        self.assertTrue(any("客服" in g or "评价" in g for g in gaps), gaps)

    def test_opening_gap_rejects_thin_blog(self) -> None:
        """内容壳写了评论/投稿/先审但未挂 → 对齐门禁拒收。"""
        text = (
            "个人博客：专栏浏览收藏；评论区发表读后评论；"
            "读者可用户发布文章；投稿需审核，审核通过后可见。"
        )
        schema = build_domain_schema("个人博客", "DOM-BLOG", proposal_text="仅浏览与收藏。")
        arch = ((schema.get("entities") or {}).get("archive") or {})
        self.assertFalse(arch.get("userPublish"))
        spec = {
            "title": "个人博客",
            "domain": "DOM-BLOG",
            "capabilities": list(DOMAIN_CAPABILITIES["DOM-BLOG"]),
            "schema": schema,
            "accept": "full",
        }
        gaps = scan_opening_delivery_gaps(spec, text)
        self.assertTrue(any("评论" in g for g in gaps), gaps)
        self.assertTrue(any("投稿" in g for g in gaps), gaps)
        # 先审依附投稿；未挂 userPublish 时先审也会缺
        self.assertTrue(any("先审" in g for g in gaps), gaps)

        full = attach_accept(
            {
                "title": "个人博客",
                "domain": "DOM-BLOG",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-BLOG"]),
                "archetype": "ARCH-CONTENT",
            },
            text,
        )
        self.assertEqual(full.get("accept"), "full", full.get("accept_reason"))
        self.assertFalse(scan_opening_delivery_gaps(full, text))
        farch = ((full.get("schema") or {}).get("entities") or {}).get("archive") or {}
        self.assertTrue(farch.get("userPublish"))
        self.assertTrue(farch.get("publishReview"))
        self.assertIn("item_comment", full.get("capabilities") or [])


if __name__ == "__main__":
    unittest.main()
