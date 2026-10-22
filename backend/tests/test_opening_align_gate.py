"""开题对齐门禁：登记开关双向对上（交易～互动全族 B 扫词 + C cap）。

禁止开题全文 vs 页面全文自由匹配。
"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.features.apply_thicken import (
    APPLY_A_SHELL_WHITELIST,
    APPLY_B_ALIGN_RULES,
    APPLY_C_ALIGN_RULES,
    diff_apply_align,
    diff_apply_b_align,
    diff_apply_c_align,
    expected_apply_b_flags,
)
from app.bake.features.approve_thicken import (
    APPROVE_A_SHELL_WHITELIST,
    APPROVE_B_ALIGN_RULES,
    APPROVE_C_ALIGN_RULES,
    diff_approve_align,
    diff_approve_b_align,
    diff_approve_c_align,
    expected_approve_b_flags,
)
from app.bake.features.borrow_thicken import (
    BORROW_A_SHELL_WHITELIST,
    BORROW_B_ALIGN_RULES,
    BORROW_C_ALIGN_RULES,
    diff_borrow_align,
    diff_borrow_b_align,
    diff_borrow_c_align,
    expected_borrow_b_flags,
)
from app.bake.features.content_thicken import (
    CONTENT_A_SHELL_WHITELIST,
    CONTENT_B_ALIGN_RULES,
    CONTENT_C_ALIGN_RULES,
    diff_content_align,
    diff_content_b_align,
    diff_content_c_align,
)
from app.bake.features.follow_thicken import (
    FOLLOW_A_SHELL_WHITELIST,
    FOLLOW_B_ALIGN_RULES,
    FOLLOW_C_ALIGN_RULES,
    diff_follow_align,
    diff_follow_b_align,
    expected_follow_b_flags,
)
from app.bake.features.interact_thicken import (
    INTERACT_A_SHELL_WHITELIST,
    INTERACT_B_ALIGN_RULES,
    INTERACT_C_ALIGN_RULES,
    diff_interact_align,
    diff_interact_b_align,
    diff_interact_c_align,
)
from app.bake.features.repair_thicken import (
    REPAIR_A_SHELL_WHITELIST,
    REPAIR_B_ALIGN_RULES,
    REPAIR_C_ALIGN_RULES,
    diff_repair_align,
    diff_repair_b_align,
    expected_repair_b_flags,
)
from app.bake.features.reserve_thicken import (
    RESERVE_A_SHELL_WHITELIST,
    RESERVE_B_ALIGN_RULES,
    RESERVE_C_ALIGN_RULES,
    diff_reserve_align,
    diff_reserve_b_align,
    diff_reserve_c_align,
)
from app.bake.features.trade_thicken import (
    TRADE_A_SHELL_WHITELIST,
    TRADE_B_ALIGN_RULES,
    TRADE_C_ALIGN_RULES,
    diff_trade_align,
    diff_trade_b_align,
    diff_trade_c_align,
    expected_trade_b_flags,
)


def _spec(domain: str, title: str, body: str = "", *, archetype: str = "ARCH-TRADE") -> dict:
    return attach_accept(
        {
            "domain": domain,
            "title": title,
            "capabilities": list(DOMAIN_CAPABILITIES[domain]),
            "features": [],
            "archetype": archetype,
        },
        body,
    )


def _borrow_spec(domain: str, title: str, body: str = "") -> dict:
    return _spec(domain, title, body, archetype="ARCH-FLOW")


def _follow_spec(domain: str, title: str, body: str = "") -> dict:
    return _spec(domain, title, body, archetype="ARCH-FLOW")


def _repair_spec(domain: str, title: str, body: str = "") -> dict:
    return _spec(domain, title, body, archetype="ARCH-FLOW")


def _apply_spec(domain: str, title: str, body: str = "") -> dict:
    return _spec(domain, title, body, archetype="ARCH-FLOW")


def _approve_spec(domain: str, title: str, body: str = "") -> dict:
    return _spec(domain, title, body, archetype="ARCH-FLOW")


def _reserve_spec(domain: str, title: str, body: str = "") -> dict:
    return _spec(domain, title, body, archetype="ARCH-RESERVE")


def _content_spec(domain: str, title: str, body: str = "") -> dict:
    return _spec(domain, title, body, archetype="ARCH-CONTENT")


def _interact_spec(domain: str, title: str, body: str = "") -> dict:
    return _spec(domain, title, body, archetype="ARCH-FLOW")


class OpeningAlignGateTradeBTests(unittest.TestCase):
    def test_b_rules_not_in_shell_as_shop_only_dup(self) -> None:
        """B 专用键不得假装成「一律壳底」；packagingFee/orderReceiptPrint 可双档分域。"""
        b_flags = {f for f, _, _ in TRADE_B_ALIGN_RULES}
        # 纯 B 键（无 FOOD/CINEMA 壳底复用）应不在白名单，或白名单注释为分域
        pure_b = b_flags - {"packagingFee", "orderReceiptPrint"}
        overlap = pure_b & TRADE_A_SHELL_WHITELIST
        self.assertEqual(overlap, set(), f"纯 B 键误入壳底白名单: {overlap}")

    def test_empty_shop_no_over_mount(self) -> None:
        out = _spec("DOM-SHOP", "校园二手商城系统", "")
        over, under = diff_trade_b_align(out, "")
        self.assertEqual(over, [], f"空开题多挂: {over}")
        self.assertEqual(under, [], f"空开题不应漏挂 B: {under}")

    def test_empty_food_shelf_and_receive_off(self) -> None:
        out = _spec("DOM-FOOD", "校园点餐配送系统", "")
        over, under = diff_trade_b_align(out, "")
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (out.get("schema") or {}).get("tradeThicken") or {}
        self.assertFalse(th.get("shelfSchedule"))
        self.assertFalse(th.get("receiveCode"))
        self.assertTrue(th.get("packagingFee"))  # FOOD 壳底，不在 SHOP-B 期望里

    def test_scan_hits_no_under_or_over(self) -> None:
        body = (
            "支持换货与物流进度手填；延保登记；收货码核销；分享口令查单；"
            "打印小票；发票开票；满赠活动；包装费；预售定金尾款；"
            "到货通知；商品问答；定时上架与定时下架；商品规格换规格。"
        )
        out = _spec("DOM-SHOP", "校园二手商城系统", body)
        over, under = diff_trade_b_align(out, body)
        self.assertEqual(over, [], f"多挂: {over}")
        self.assertEqual(under, [], f"漏挂: {under}")
        expected = expected_trade_b_flags("DOM-SHOP", out, body)
        self.assertTrue(expected.get("refundExchange"))
        self.assertTrue(expected.get("cartChangeSpec"))
        self.assertTrue(expected.get("invoiceTitle"))

    def test_manual_over_mount_detected(self) -> None:
        """人为把开关拨开但扫词未命中 → 多挂。"""
        out = _spec("DOM-SHOP", "校园二手商城系统", "")
        schema = out.setdefault("schema", {})
        th = schema.setdefault("tradeThicken", {})
        th["refundExchange"] = True
        th["invoiceTitle"] = True
        over, under = diff_trade_b_align(out, "")
        self.assertIn("refundExchange", over)
        self.assertIn("invoiceTitle", over)
        self.assertEqual(under, [])

    def test_manual_under_mount_detected(self) -> None:
        out = _spec("DOM-SHOP", "校园二手商城系统", "支持售后换货")
        schema = out.setdefault("schema", {})
        th = schema.setdefault("tradeThicken", {})
        th["refundExchange"] = False
        over, under = diff_trade_b_align(out, "支持售后换货")
        self.assertEqual(over, [])
        self.assertIn("refundExchange", under)

    def test_logistics_damage_reason_not_ship_nodes(self) -> None:
        """售后原因「物流损坏」≠ 物流进度手填。"""
        out = _spec("DOM-SHOP", "校园二手商城系统", "售后原因含物流损坏可退货退款")
        over, under = diff_trade_b_align(out, "售后原因含物流损坏可退货退款")
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (out.get("schema") or {}).get("tradeThicken") or {}
        self.assertFalse(th.get("shipNodes"))

    def test_cinema_shop_scan_words_do_not_arm_shop_b(self) -> None:
        """开题写商城 B 词，影院不挂 SHOP 专属 B；小票仍可壳底开。"""
        body = "发票与换货与物流进度"
        out = _spec("DOM-CINEMA", "影院在线选座购票系统", body)
        over, under = diff_trade_b_align(out, body)
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (out.get("schema") or {}).get("tradeThicken") or {}
        self.assertFalse(th.get("invoiceTitle"))
        self.assertFalse(th.get("refundExchange"))
        self.assertFalse(th.get("shipNodes"))
        self.assertTrue(th.get("orderReceiptPrint"))  # CINEMA 壳底


class OpeningAlignGateTradeCTests(unittest.TestCase):
    def test_default_shop_c_aligns_with_domain_caps(self) -> None:
        """域默认带 order_review/quota → 对应 C 加深开；无 coupon 等 → 关。"""
        out = _spec("DOM-SHOP", "校园二手商城系统", "")
        over, under = diff_trade_c_align(out)
        self.assertEqual(over, [], f"多挂: {over}")
        self.assertEqual(under, [], f"漏挂: {under}")
        th = (out.get("schema") or {}).get("tradeThicken") or {}
        self.assertTrue(th.get("stockLock"))
        self.assertTrue(th.get("reviewImage"))
        self.assertFalse(th.get("browseHistory"))
        self.assertFalse(th.get("couponRedeemCode"))

    def test_c_over_mount_without_cap(self) -> None:
        out = _spec("DOM-SHOP", "校园二手商城系统", "")
        th = out.setdefault("schema", {}).setdefault("tradeThicken", {})
        th["browseHistory"] = True
        th["couponRedeemCode"] = True
        over, under = diff_trade_c_align(out)
        self.assertIn("browseHistory", over)
        self.assertIn("couponRedeemCode", over)
        self.assertEqual(under, [])

    def test_c_under_mount_when_cap_present(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "校园二手商城系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SHOP"])
                + ["browse_history", "coupon"],
                "features": [],
                "archetype": "ARCH-TRADE",
            },
            "",
        )
        th = out.setdefault("schema", {}).setdefault("tradeThicken", {})
        th["browseHistory"] = False
        th["couponRedeemCode"] = False
        over, under = diff_trade_c_align(out)
        self.assertEqual(over, [])
        self.assertIn("browseHistory", under)
        self.assertIn("couponRedeemCode", under)

    def test_c_with_caps_bake_clean(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "校园二手商城系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SHOP"])
                + ["browse_history", "coupon", "group_buy", "points"],
                "features": [],
                "archetype": "ARCH-TRADE",
            },
            "",
        )
        over, under = diff_trade_c_align(out)
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (out.get("schema") or {}).get("tradeThicken") or {}
        self.assertTrue(th.get("browseHistory"))
        self.assertTrue(th.get("groupBuyProgress"))
        self.assertTrue(th.get("pointsLedger"))

    def test_bc_merged_diff(self) -> None:
        out = _spec("DOM-SHOP", "校园二手商城系统", "")
        th = out.setdefault("schema", {}).setdefault("tradeThicken", {})
        th["refundExchange"] = True  # B 多挂
        th["browseHistory"] = True  # C 多挂
        over, under = diff_trade_align(out, "")
        self.assertIn("refundExchange", over)
        self.assertIn("browseHistory", over)
        self.assertEqual(under, [])

    def test_c_rule_count_stable(self) -> None:
        self.assertGreaterEqual(len(TRADE_C_ALIGN_RULES), 10)


class OpeningAlignGateBorrowBTests(unittest.TestCase):
    def test_b_rules_not_in_shell(self) -> None:
        b_flags = {f for f, _, _ in BORROW_B_ALIGN_RULES}
        overlap = b_flags & BORROW_A_SHELL_WHITELIST
        self.assertEqual(overlap, set(), f"B 键误入壳底白名单: {overlap}")

    def test_empty_library_no_over_mount(self) -> None:
        out = _borrow_spec("DOM-LIBRARY", "图书借阅管理系统", "")
        over, under = diff_borrow_b_align(out, "")
        self.assertEqual(over, [], f"空开题多挂: {over}")
        self.assertEqual(under, [], f"空开题不应漏挂 B: {under}")
        th = (out.get("schema") or {}).get("borrowThicken") or {}
        self.assertFalse(th.get("isbnValidate"))
        self.assertFalse(th.get("fineWaive"))
        self.assertTrue(th.get("hotLoanBoard"))

    def test_empty_bed_peer_off(self) -> None:
        out = _borrow_spec("DOM-BED", "学生床位调配管理系统", "")
        over, under = diff_borrow_b_align(out, "")
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (out.get("schema") or {}).get("borrowThicken") or {}
        self.assertFalse(th.get("peerConfirm"))
        self.assertFalse(th.get("bedSwapMatch"))
        self.assertTrue(th.get("bedConstraint"))

    def test_empty_equip_maintain_due_off(self) -> None:
        out = _borrow_spec("DOM-EQUIP", "实验室设备借用管理系统", "")
        over, under = diff_borrow_b_align(out, "")
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (out.get("schema") or {}).get("borrowThicken") or {}
        self.assertFalse(th.get("maintainDue"))
        self.assertTrue(th.get("maintainWorkOrder"))

    def test_scan_hits_library_equip_bed(self) -> None:
        lib_body = "ISBN校验；随书光盘；逾期罚款减免；续借须无预约；预约取消次数限制。"
        lib = _borrow_spec("DOM-LIBRARY", "图书借阅管理系统", lib_body)
        over, under = diff_borrow_b_align(lib, lib_body)
        self.assertEqual(over, [], f"LIBRARY 多挂: {over}")
        self.assertEqual(under, [], f"LIBRARY 漏挂: {under}")
        expected = expected_borrow_b_flags("DOM-LIBRARY", lib, lib_body)
        self.assertTrue(expected.get("isbnValidate"))
        self.assertTrue(expected.get("fineWaive"))

        eq_body = "保养到期提醒；设备押金登记；校准证书到期；设备保险声明；随借配件清单。"
        eq = _borrow_spec("DOM-EQUIP", "实验室设备借用管理系统", eq_body)
        over, under = diff_borrow_b_align(eq, eq_body)
        self.assertEqual(over, [], f"EQUIP 多挂: {over}")
        self.assertEqual(under, [], f"EQUIP 漏挂: {under}")
        self.assertTrue((eq.get("schema") or {}).get("borrowThicken", {}).get("maintainDue"))

        bed_body = "调宿双方确认与对向同意；住宿费预定金；退宿水电清算；退宿行李清点。"
        bed = _borrow_spec("DOM-BED", "学生床位调配管理系统", bed_body)
        over, under = diff_borrow_b_align(bed, bed_body)
        self.assertEqual(over, [], f"BED 多挂: {over}")
        self.assertEqual(under, [], f"BED 漏挂: {under}")
        th = (bed.get("schema") or {}).get("borrowThicken") or {}
        self.assertTrue(th.get("peerConfirm"))
        self.assertTrue(th.get("bedSwapMatch"))

    def test_manual_over_mount_detected(self) -> None:
        out = _borrow_spec("DOM-LIBRARY", "图书借阅管理系统", "")
        th = out.setdefault("schema", {}).setdefault("borrowThicken", {})
        th["isbnValidate"] = True
        th["fineWaive"] = True
        over, under = diff_borrow_b_align(out, "")
        self.assertIn("isbnValidate", over)
        self.assertIn("fineWaive", over)
        self.assertEqual(under, [])

    def test_manual_under_mount_detected(self) -> None:
        body = "图书录入支持 ISBN 校验与查重提示。"
        out = _borrow_spec("DOM-LIBRARY", "图书借阅管理系统", body)
        th = out.setdefault("schema", {}).setdefault("borrowThicken", {})
        th["isbnValidate"] = False
        over, under = diff_borrow_b_align(out, body)
        self.assertEqual(over, [])
        self.assertIn("isbnValidate", under)


class OpeningAlignGateBorrowCTests(unittest.TestCase):
    def test_empty_library_suggest_budget_off(self) -> None:
        out = _borrow_spec("DOM-LIBRARY", "图书借阅管理系统", "")
        over, under = diff_borrow_c_align(out)
        self.assertEqual(over, [], f"多挂: {over}")
        self.assertEqual(under, [], f"漏挂: {under}")
        th = (out.get("schema") or {}).get("borrowThicken") or {}
        self.assertFalse(th.get("suggestBudget"))

    def test_c_over_mount_without_cap(self) -> None:
        out = _borrow_spec("DOM-LIBRARY", "图书借阅管理系统", "")
        th = out.setdefault("schema", {}).setdefault("borrowThicken", {})
        th["suggestBudget"] = True
        over, under = diff_borrow_c_align(out)
        self.assertIn("suggestBudget", over)
        self.assertEqual(under, [])

    def test_c_with_book_suggest_bake_clean(self) -> None:
        out = _borrow_spec("DOM-LIBRARY", "图书借阅管理系统", "支持图书荐购与读者荐购审核。")
        over, under = diff_borrow_c_align(out)
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (out.get("schema") or {}).get("borrowThicken") or {}
        self.assertTrue(th.get("suggestBudget"))
        self.assertIn("book_suggest", out.get("capabilities") or [])

    def test_c_under_mount_when_cap_present(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书借阅管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]) + ["book_suggest"],
                "features": [],
                "archetype": "ARCH-FLOW",
            },
            "",
        )
        th = out.setdefault("schema", {}).setdefault("borrowThicken", {})
        th["suggestBudget"] = False
        over, under = diff_borrow_c_align(out)
        self.assertEqual(over, [])
        self.assertIn("suggestBudget", under)

    def test_bc_merged_diff(self) -> None:
        out = _borrow_spec("DOM-LIBRARY", "图书借阅管理系统", "")
        th = out.setdefault("schema", {}).setdefault("borrowThicken", {})
        th["isbnValidate"] = True
        th["suggestBudget"] = True
        over, under = diff_borrow_align(out, "")
        self.assertIn("isbnValidate", over)
        self.assertIn("suggestBudget", over)
        self.assertEqual(under, [])

    def test_c_rule_count_stable(self) -> None:
        self.assertGreaterEqual(len(BORROW_C_ALIGN_RULES), 1)


class OpeningAlignGateFollowBTests(unittest.TestCase):
    def test_b_rules_not_in_shell(self) -> None:
        b_flags = {f for f, _, _ in FOLLOW_B_ALIGN_RULES}
        overlap = b_flags & FOLLOW_A_SHELL_WHITELIST
        self.assertEqual(overlap, set(), f"B 键误入壳底白名单: {overlap}")

    def test_empty_crm_no_over_mount(self) -> None:
        out = _follow_spec("DOM-CRM", "客户跟进管理系统", "")
        over, under = diff_follow_b_align(out, "")
        self.assertEqual(over, [], f"空开题多挂: {over}")
        self.assertEqual(under, [], f"空开题不应漏挂 B: {under}")
        th = (out.get("schema") or {}).get("followThicken") or {}
        self.assertFalse(th.get("phoneDupCheck"))
        self.assertFalse(th.get("stalePool"))
        self.assertFalse(th.get("homeVisit"))
        self.assertTrue(th.get("followRemind"))
        self.assertTrue(th.get("dealAmount"))

    def test_empty_event_recruit_listing_b_off(self) -> None:
        ev = _follow_spec("DOM-EVENT", "事件上报管理系统", "")
        over, under = diff_follow_b_align(ev, "")
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (ev.get("schema") or {}).get("followThicken") or {}
        self.assertFalse(th.get("levelSla"))
        self.assertFalse(th.get("notifyDuty"))
        self.assertTrue(th.get("closeAttach"))

        rec = _follow_spec("DOM-RECRUIT", "招聘投递管理系统", "")
        over, under = diff_follow_b_align(rec, "")
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (rec.get("schema") or {}).get("followThicken") or {}
        self.assertFalse(th.get("jobFav"))
        self.assertFalse(th.get("onboardMat"))
        self.assertTrue(th.get("batchHire"))

        listing = _follow_spec("DOM-LISTING", "房源带看管理系统", "")
        over, under = diff_follow_b_align(listing, "")
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (listing.get("schema") or {}).get("followThicken") or {}
        self.assertFalse(th.get("listingFav"))
        self.assertFalse(th.get("listingConflict"))
        self.assertTrue(th.get("listingRating"))

    def test_scan_hits_crm_and_event(self) -> None:
        crm_body = (
            "客户查重与同手机号提示；家访谈话记录；分配负责人；"
            "未跟进 N 天列表；回款计划；下次行动待办；线索来源统计。"
        )
        crm = _follow_spec("DOM-CRM", "客户跟进管理系统", crm_body)
        over, under = diff_follow_b_align(crm, crm_body)
        self.assertEqual(over, [], f"CRM 多挂: {over}")
        self.assertEqual(under, [], f"CRM 漏挂: {under}")
        expected = expected_follow_b_flags("DOM-CRM", crm, crm_body)
        self.assertTrue(expected.get("phoneDupCheck"))
        self.assertTrue(expected.get("homeVisit"))
        self.assertTrue(expected.get("stalePool"))

        ev_body = "事件等级时限；保密标记；分拨科室；值班排班；一键通知值班。"
        ev = _follow_spec("DOM-EVENT", "事件上报管理系统", ev_body)
        over, under = diff_follow_b_align(ev, ev_body)
        self.assertEqual(over, [], f"EVENT 多挂: {over}")
        self.assertEqual(under, [], f"EVENT 漏挂: {under}")
        th = (ev.get("schema") or {}).get("followThicken") or {}
        self.assertTrue(th.get("levelSla"))
        self.assertTrue(th.get("dutyRoster"))

    def test_manual_over_mount_detected(self) -> None:
        out = _follow_spec("DOM-CRM", "客户跟进管理系统", "")
        th = out.setdefault("schema", {}).setdefault("followThicken", {})
        th["phoneDupCheck"] = True
        th["stalePool"] = True
        over, under = diff_follow_b_align(out, "")
        self.assertIn("phoneDupCheck", over)
        self.assertIn("stalePool", over)
        self.assertEqual(under, [])

    def test_manual_under_mount_detected(self) -> None:
        body = "支持客户查重与同手机号提示。"
        out = _follow_spec("DOM-CRM", "客户跟进管理系统", body)
        th = out.setdefault("schema", {}).setdefault("followThicken", {})
        th["phoneDupCheck"] = False
        over, under = diff_follow_b_align(out, body)
        self.assertEqual(over, [])
        self.assertIn("phoneDupCheck", under)

    def test_bc_merged_diff(self) -> None:
        out = _follow_spec("DOM-CRM", "客户跟进管理系统", "")
        th = out.setdefault("schema", {}).setdefault("followThicken", {})
        th["phoneDupCheck"] = True
        over, under = diff_follow_align(out, "")
        self.assertIn("phoneDupCheck", over)
        self.assertEqual(under, [])

    def test_c_rules_empty_stable(self) -> None:
        """跟进组暂无纯 C 键；表存在且为空，避免误登 B 为 C。"""
        self.assertEqual(FOLLOW_C_ALIGN_RULES, [])
        self.assertGreaterEqual(len(FOLLOW_B_ALIGN_RULES), 20)


class OpeningAlignGateRepairBTests(unittest.TestCase):
    def test_b_rules_not_in_shell_as_pure(self) -> None:
        """纯 B 键不得进壳底；parts/serial/faq/assetCode/remote 可双档分域。"""
        b_flags = {f for f, _, _ in REPAIR_B_ALIGN_RULES}
        dual = {"parts", "serial", "faq", "assetCode", "remote"}
        overlap = (b_flags - dual) & REPAIR_A_SHELL_WHITELIST
        self.assertEqual(overlap, set(), f"纯 B 键误入壳底白名单: {overlap}")

    def test_empty_dorm_no_over_mount(self) -> None:
        out = _repair_spec("DOM-DORM", "学生宿舍报修管理系统", "")
        over, under = diff_repair_b_align(out, "")
        self.assertEqual(over, [], f"空开题多挂: {over}")
        self.assertEqual(under, [], f"空开题不应漏挂 B: {under}")
        th = (out.get("schema") or {}).get("repairThicken") or {}
        self.assertFalse(th.get("parts"))
        self.assertFalse(th.get("quote"))
        self.assertFalse(th.get("merge"))
        self.assertTrue(th.get("core"))
        self.assertTrue(th.get("skill"))
        self.assertTrue(th.get("dupRoomCheck"))

    def test_empty_property_it_shell_on(self) -> None:
        prop = _repair_spec("DOM-PROPERTY", "智慧社区物业报修", "")
        over, under = diff_repair_b_align(prop, "")
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (prop.get("schema") or {}).get("repairThicken") or {}
        self.assertTrue(th.get("parts"))
        self.assertTrue(th.get("serial"))
        self.assertTrue(th.get("faq"))
        self.assertFalse(th.get("quote"))
        self.assertFalse(th.get("merge"))

        it = _repair_spec("DOM-IT", "校园网故障报修", "")
        over, under = diff_repair_b_align(it, "")
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (it.get("schema") or {}).get("repairThicken") or {}
        self.assertTrue(th.get("assetCode"))
        self.assertTrue(th.get("remote"))
        self.assertTrue(th.get("faq"))
        self.assertFalse(th.get("quote"))
        self.assertFalse(th.get("knowledge"))

    def test_scan_hits_dorm_and_it(self) -> None:
        dorm_body = (
            "备件出库与耗材台账；备件序列号；常见问题自助排查；"
            "资产编号扫码；远程协助；维修报价确认；重复工单合并；值班表冲突。"
        )
        dorm = _repair_spec("DOM-DORM", "学生宿舍报修管理系统", dorm_body)
        over, under = diff_repair_b_align(dorm, dorm_body)
        self.assertEqual(over, [], f"DORM 多挂: {over}")
        self.assertEqual(under, [], f"DORM 漏挂: {under}")
        expected = expected_repair_b_flags("DOM-DORM", dorm, dorm_body)
        self.assertTrue(expected.get("parts"))
        self.assertTrue(expected.get("quote"))
        self.assertTrue(expected.get("merge"))

        it_body = "结单知识沉淀写入常见问题；维修报价；工单合并。"
        it = _repair_spec("DOM-IT", "校园网故障报修", it_body)
        over, under = diff_repair_b_align(it, it_body)
        self.assertEqual(over, [], f"IT 多挂: {over}")
        self.assertEqual(under, [], f"IT 漏挂: {under}")
        th = (it.get("schema") or {}).get("repairThicken") or {}
        self.assertTrue(th.get("knowledge"))
        self.assertTrue(th.get("quote"))

    def test_manual_over_mount_detected(self) -> None:
        out = _repair_spec("DOM-DORM", "学生宿舍报修管理系统", "")
        th = out.setdefault("schema", {}).setdefault("repairThicken", {})
        th["quote"] = True
        th["merge"] = True
        over, under = diff_repair_b_align(out, "")
        self.assertIn("quote", over)
        self.assertIn("merge", over)
        self.assertEqual(under, [])

    def test_manual_under_mount_detected(self) -> None:
        body = "支持维修报价用户确认与材料费。"
        out = _repair_spec("DOM-DORM", "学生宿舍报修管理系统", body)
        th = out.setdefault("schema", {}).setdefault("repairThicken", {})
        th["quote"] = False
        over, under = diff_repair_b_align(out, body)
        self.assertEqual(over, [])
        self.assertIn("quote", under)

    def test_bc_merged_diff(self) -> None:
        out = _repair_spec("DOM-DORM", "学生宿舍报修管理系统", "")
        th = out.setdefault("schema", {}).setdefault("repairThicken", {})
        th["quote"] = True
        over, under = diff_repair_align(out, "")
        self.assertIn("quote", over)
        self.assertEqual(under, [])

    def test_c_rules_empty_stable(self) -> None:
        self.assertEqual(REPAIR_C_ALIGN_RULES, [])
        self.assertGreaterEqual(len(REPAIR_B_ALIGN_RULES), 8)


class OpeningAlignGateApplyBTests(unittest.TestCase):
    def test_b_rules_not_in_shell(self) -> None:
        b_flags = {f for f, _, _ in APPLY_B_ALIGN_RULES}
        overlap = b_flags & APPLY_A_SHELL_WHITELIST
        self.assertEqual(overlap, set(), f"B 键误入壳底白名单: {overlap}")

    def test_empty_activity_survey_off(self) -> None:
        out = _apply_spec("DOM-ACTIVITY", "校园活动报名系统", "")
        over, under = diff_apply_b_align(out, "")
        self.assertEqual(over, [], f"空开题多挂: {over}")
        self.assertEqual(under, [], f"空开题不应漏挂 B: {under}")
        th = (out.get("schema") or {}).get("applyThicken") or {}
        self.assertFalse(th.get("surveyLink"))
        self.assertTrue(th.get("core"))
        self.assertTrue(th.get("noticeAck"))

    def test_scan_survey_link(self) -> None:
        body = "活动结束后填写满意度问卷，问卷联动回收统计。"
        out = _apply_spec("DOM-ACTIVITY", "校园活动报名系统", body)
        over, under = diff_apply_b_align(out, body)
        self.assertEqual(over, [], f"多挂: {over}")
        self.assertEqual(under, [], f"漏挂: {under}")
        expected = expected_apply_b_flags("DOM-ACTIVITY", out, body)
        self.assertTrue(expected.get("surveyLink"))
        self.assertTrue((out.get("schema") or {}).get("applyThicken", {}).get("surveyLink"))

    def test_manual_over_under(self) -> None:
        out = _apply_spec("DOM-ACTIVITY", "校园活动报名系统", "")
        th = out.setdefault("schema", {}).setdefault("applyThicken", {})
        th["surveyLink"] = True
        over, under = diff_apply_b_align(out, "")
        self.assertIn("surveyLink", over)
        self.assertEqual(under, [])

        body = "活动满意度卷联动。"
        out2 = _apply_spec("DOM-ACTIVITY", "校园活动报名系统", body)
        th2 = out2.setdefault("schema", {}).setdefault("applyThicken", {})
        th2["surveyLink"] = False
        over, under = diff_apply_b_align(out2, body)
        self.assertEqual(over, [])
        self.assertIn("surveyLink", under)


class OpeningAlignGateApplyCTests(unittest.TestCase):
    def test_empty_tour_waitlist_off(self) -> None:
        out = _apply_spec("DOM-TOUR", "旅行社线路报名", "")
        over, under = diff_apply_c_align(out)
        self.assertEqual(over, [], f"多挂: {over}")
        self.assertEqual(under, [], f"漏挂: {under}")
        th = (out.get("schema") or {}).get("applyThicken") or {}
        self.assertFalse(th.get("tourWaitlist"))

    def test_c_over_mount_without_cap(self) -> None:
        out = _apply_spec("DOM-TOUR", "旅行社线路报名", "")
        th = out.setdefault("schema", {}).setdefault("applyThicken", {})
        th["tourWaitlist"] = True
        over, under = diff_apply_c_align(out)
        self.assertIn("tourWaitlist", over)
        self.assertEqual(under, [])

    def test_c_with_waitlist_bake_clean(self) -> None:
        out = _apply_spec("DOM-TOUR", "旅行社线路报名", "研学满员可候补。")
        over, under = diff_apply_c_align(out)
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (out.get("schema") or {}).get("applyThicken") or {}
        self.assertTrue(th.get("tourWaitlist"))
        self.assertIn("waitlist", out.get("capabilities") or [])

    def test_c_under_mount_when_cap_present(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-TOUR",
                "title": "旅行社线路报名",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-TOUR"]) + ["waitlist"],
                "features": [],
                "archetype": "ARCH-FLOW",
            },
            "",
        )
        th = out.setdefault("schema", {}).setdefault("applyThicken", {})
        th["tourWaitlist"] = False
        over, under = diff_apply_c_align(out)
        self.assertEqual(over, [])
        self.assertIn("tourWaitlist", under)

    def test_bc_merged_diff(self) -> None:
        out = _apply_spec("DOM-ACTIVITY", "校园活动报名系统", "")
        th = out.setdefault("schema", {}).setdefault("applyThicken", {})
        th["surveyLink"] = True
        over, under = diff_apply_align(out, "")
        self.assertIn("surveyLink", over)
        self.assertEqual(under, [])

    def test_c_rule_count_stable(self) -> None:
        self.assertGreaterEqual(len(APPLY_C_ALIGN_RULES), 1)
        self.assertGreaterEqual(len(APPLY_B_ALIGN_RULES), 1)


class OpeningAlignGateApproveBTests(unittest.TestCase):
    def test_b_rules_not_in_shell(self) -> None:
        b_flags = {f for f, _, _ in APPROVE_B_ALIGN_RULES}
        overlap = b_flags & APPROVE_A_SHELL_WHITELIST
        self.assertEqual(overlap, set(), f"B 键误入壳底白名单: {overlap}")

    def test_empty_auto_pass_off(self) -> None:
        out = _approve_spec("DOM-SEAL", "用印审批系统", "")
        over, under = diff_approve_b_align(out, "")
        self.assertEqual(over, [], f"空开题多挂: {over}")
        self.assertEqual(under, [], f"空开题不应漏挂 B: {under}")
        th = (out.get("schema") or {}).get("approveThicken") or {}
        self.assertFalse(th.get("autoPass"))
        self.assertTrue(th.get("core"))
        self.assertTrue(th.get("withdraw"))

    def test_scan_auto_pass(self) -> None:
        body = "支持限时自动通过，超时自动审过。"
        out = _approve_spec("DOM-SEAL", "用印审批系统", body)
        over, under = diff_approve_b_align(out, body)
        self.assertEqual(over, [], f"多挂: {over}")
        self.assertEqual(under, [], f"漏挂: {under}")
        expected = expected_approve_b_flags("DOM-SEAL", out, body)
        self.assertTrue(expected.get("autoPass"))
        self.assertTrue((out.get("schema") or {}).get("approveThicken", {}).get("autoPass"))

    def test_manual_over_under(self) -> None:
        out = _approve_spec("DOM-CERT", "校园证明开具", "")
        th = out.setdefault("schema", {}).setdefault("approveThicken", {})
        th["autoPass"] = True
        over, under = diff_approve_b_align(out, "")
        self.assertIn("autoPass", over)
        self.assertEqual(under, [])

        body = "审批超时自动通过。"
        out2 = _approve_spec("DOM-CERT", "校园证明开具", body)
        th2 = out2.setdefault("schema", {}).setdefault("approveThicken", {})
        th2["autoPass"] = False
        over, under = diff_approve_b_align(out2, body)
        self.assertEqual(over, [])
        self.assertIn("autoPass", under)


class OpeningAlignGateApproveCTests(unittest.TestCase):
    def test_empty_labsafe_exam_pass_min_off(self) -> None:
        out = _approve_spec("DOM-LABSAFE", "实验室安全准入", "")
        over, under = diff_approve_c_align(out)
        self.assertEqual(over, [], f"多挂: {over}")
        self.assertEqual(under, [], f"漏挂: {under}")
        th = (out.get("schema") or {}).get("approveThicken") or {}
        self.assertFalse(th.get("examPassMin"))

    def test_c_over_mount_without_cap(self) -> None:
        out = _approve_spec("DOM-LABSAFE", "实验室安全准入", "")
        th = out.setdefault("schema", {}).setdefault("approveThicken", {})
        th["examPassMin"] = True
        over, under = diff_approve_c_align(out)
        self.assertIn("examPassMin", over)
        self.assertEqual(under, [])

    def test_c_with_exam_bake_clean(self) -> None:
        out = _approve_spec(
            "DOM-LABSAFE",
            "实验室安全准入",
            "准入须先考后申，安全考试通过后方可提交。",
        )
        over, under = diff_approve_c_align(out)
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (out.get("schema") or {}).get("approveThicken") or {}
        self.assertTrue(th.get("examPassMin"))
        self.assertIn("exam", out.get("capabilities") or [])

    def test_c_under_mount_when_cap_present(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-LABSAFE",
                "title": "实验室安全准入",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LABSAFE"]) + ["exam"],
                "features": [],
                "archetype": "ARCH-FLOW",
            },
            "",
        )
        th = out.setdefault("schema", {}).setdefault("approveThicken", {})
        th["examPassMin"] = False
        over, under = diff_approve_c_align(out)
        self.assertEqual(over, [])
        self.assertIn("examPassMin", under)

    def test_bc_merged_diff(self) -> None:
        out = _approve_spec("DOM-SEAL", "用印审批", "")
        th = out.setdefault("schema", {}).setdefault("approveThicken", {})
        th["autoPass"] = True
        over, under = diff_approve_align(out, "")
        self.assertIn("autoPass", over)
        self.assertEqual(under, [])

    def test_c_rule_count_stable(self) -> None:
        self.assertGreaterEqual(len(APPROVE_C_ALIGN_RULES), 1)
        self.assertGreaterEqual(len(APPROVE_B_ALIGN_RULES), 1)


class OpeningAlignGateReserveBTests(unittest.TestCase):
    def test_b_rules_empty_stable(self) -> None:
        self.assertEqual(RESERVE_B_ALIGN_RULES, [])
        self.assertGreaterEqual(len(RESERVE_A_SHELL_WHITELIST), 20)
        self.assertGreaterEqual(len(RESERVE_C_ALIGN_RULES), 5)

    def test_empty_b_diff_clean(self) -> None:
        out = _reserve_spec("DOM-MEETING", "会议室预约系统", "")
        over, under = diff_reserve_b_align(out, "")
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (out.get("schema") or {}).get("reserveThicken") or {}
        self.assertTrue(th.get("core"))
        self.assertTrue(th.get("cancelFreeHours"))


class OpeningAlignGateReserveCTests(unittest.TestCase):
    def test_empty_salon_r09_off(self) -> None:
        out = _reserve_spec("DOM-SALON", "美发美容预约系统", "")
        over, under = diff_reserve_c_align(out)
        self.assertEqual(over, [], f"多挂: {over}")
        self.assertEqual(under, [], f"漏挂: {under}")
        th = (out.get("schema") or {}).get("reserveThicken") or {}
        self.assertFalse(th.get("salonWallet"))
        self.assertFalse(th.get("salonGallery"))
        self.assertFalse(th.get("salonLessonRemain"))
        self.assertFalse(th.get("salonLeaveBlock"))

    def test_c_over_mount_without_cap(self) -> None:
        out = _reserve_spec("DOM-SALON", "美发美容预约系统", "")
        th = out.setdefault("schema", {}).setdefault("reserveThicken", {})
        th["salonWallet"] = True
        over, under = diff_reserve_c_align(out)
        self.assertIn("salonWallet", over)
        self.assertEqual(under, [])

    def test_c_with_roster_bake_clean(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-HOSPITAL",
                "title": "医院挂号预约系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-HOSPITAL"]) + ["staff_roster"],
                "features": [],
                "archetype": "ARCH-RESERVE",
            },
            "医生排班值班表",
        )
        over, under = diff_reserve_c_align(out)
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (out.get("schema") or {}).get("reserveThicken") or {}
        self.assertTrue(th.get("hospitalRoster"))
        self.assertIn("staff_roster", out.get("capabilities") or [])

    def test_c_under_mount_when_cap_present(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-MEETING",
                "title": "会议室预约系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-MEETING"]) + ["room_equipment"],
                "features": [],
                "archetype": "ARCH-RESERVE",
            },
            "",
        )
        th = out.setdefault("schema", {}).setdefault("reserveThicken", {})
        th["meetingEquipBorrow"] = False
        over, under = diff_reserve_c_align(out)
        self.assertEqual(over, [])
        self.assertIn("meetingEquipBorrow", under)

    def test_bc_merged_diff(self) -> None:
        out = _reserve_spec("DOM-SALON", "美发美容预约系统", "")
        th = out.setdefault("schema", {}).setdefault("reserveThicken", {})
        th["salonGallery"] = True
        over, under = diff_reserve_align(out, "")
        self.assertIn("salonGallery", over)
        self.assertEqual(under, [])

    def test_c_rule_count_stable(self) -> None:
        self.assertGreaterEqual(len(RESERVE_C_ALIGN_RULES), 7)
        self.assertEqual(len(RESERVE_B_ALIGN_RULES), 0)


class OpeningAlignGateContentBTests(unittest.TestCase):
    def test_b_rules_empty_stable(self) -> None:
        self.assertEqual(CONTENT_B_ALIGN_RULES, [])
        self.assertGreaterEqual(len(CONTENT_A_SHELL_WHITELIST), 20)
        self.assertGreaterEqual(len(CONTENT_C_ALIGN_RULES), 8)

    def test_empty_b_diff_clean(self) -> None:
        out = _content_spec("DOM-BLOG", "个人博客专栏管理系统", "")
        over, under = diff_content_b_align(out, "")
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (out.get("schema") or {}).get("contentThicken") or {}
        self.assertTrue(th.get("core"))
        self.assertTrue(th.get("viewCount"))


class OpeningAlignGateContentCTests(unittest.TestCase):
    def test_empty_doclib_points_off(self) -> None:
        out = _content_spec("DOM-DOCLIB", "资料文库下载台管理系统", "")
        over, under = diff_content_c_align(out)
        self.assertEqual(over, [], f"多挂: {over}")
        self.assertEqual(under, [], f"漏挂: {under}")
        th = (out.get("schema") or {}).get("contentThicken") or {}
        self.assertFalse(th.get("docPointsDownload"))
        self.assertFalse(th.get("docPaidDownload"))

    def test_empty_forum_points_off_report_on(self) -> None:
        out = _content_spec("DOM-FORUM", "校园论坛交流管理系统", "")
        over, under = diff_content_c_align(out)
        self.assertEqual(over, [], f"多挂: {over}")
        self.assertEqual(under, [], f"漏挂: {under}")
        th = (out.get("schema") or {}).get("contentThicken") or {}
        self.assertFalse(th.get("essencePointsReward"))
        self.assertFalse(th.get("followersOnlyComment"))
        self.assertTrue(th.get("muteExpire"))
        self.assertTrue(th.get("reportReasonDict"))

    def test_c_over_mount_without_cap(self) -> None:
        out = _content_spec("DOM-DOCLIB", "资料文库下载台管理系统", "")
        th = out.setdefault("schema", {}).setdefault("contentThicken", {})
        th["docPointsDownload"] = True
        over, under = diff_content_c_align(out)
        self.assertIn("docPointsDownload", over)
        self.assertEqual(under, [])

    def test_c_with_points_bake_clean(self) -> None:
        out = _content_spec(
            "DOM-DOCLIB",
            "资料文库下载台管理系统",
            "支持会员积分下载资料，下载前扣积分。",
        )
        over, under = diff_content_c_align(out)
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (out.get("schema") or {}).get("contentThicken") or {}
        self.assertTrue(th.get("docPointsDownload"))
        self.assertIn("points", out.get("capabilities") or [])

    def test_c_under_mount_when_cap_present(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-BLOG",
                "title": "个人博客专栏管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-BLOG"]) + ["item_comment"],
                "features": [],
                "archetype": "ARCH-CONTENT",
            },
            "",
        )
        th = out.setdefault("schema", {}).setdefault("contentThicken", {})
        th["followersOnlyComment"] = False
        over, under = diff_content_c_align(out)
        self.assertEqual(over, [])
        self.assertIn("followersOnlyComment", under)

    def test_bc_merged_diff(self) -> None:
        out = _content_spec("DOM-DOCLIB", "资料文库下载台管理系统", "")
        th = out.setdefault("schema", {}).setdefault("contentThicken", {})
        th["docPaidDownload"] = True
        over, under = diff_content_align(out, "")
        self.assertIn("docPaidDownload", over)
        self.assertEqual(under, [])

    def test_c_rule_count_stable(self) -> None:
        self.assertGreaterEqual(len(CONTENT_C_ALIGN_RULES), 10)
        self.assertEqual(len(CONTENT_B_ALIGN_RULES), 0)


class OpeningAlignGateInteractBTests(unittest.TestCase):
    def test_b_rules_empty_stable(self) -> None:
        self.assertEqual(INTERACT_B_ALIGN_RULES, [])
        self.assertGreaterEqual(len(INTERACT_A_SHELL_WHITELIST), 40)
        self.assertGreaterEqual(len(INTERACT_C_ALIGN_RULES), 4)

    def test_empty_b_diff_clean(self) -> None:
        out = _interact_spec("DOM-CARPOOL", "校园拼车管理系统", "")
        over, under = diff_interact_b_align(out, "")
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (out.get("schema") or {}).get("interactThicken") or {}
        self.assertTrue(th.get("core"))
        self.assertTrue(th.get("carpoolFullClose"))


class OpeningAlignGateInteractCTests(unittest.TestCase):
    def test_empty_dating_dm_on_report_off(self) -> None:
        out = _interact_spec("DOM-DATING", "校园婚恋交友管理系统", "")
        over, under = diff_interact_c_align(out)
        self.assertEqual(over, [], f"多挂: {over}")
        self.assertEqual(under, [], f"漏挂: {under}")
        th = (out.get("schema") or {}).get("interactThicken") or {}
        self.assertTrue(th.get("dmIsland"))
        self.assertTrue(th.get("favoritesIsland"))
        self.assertFalse(th.get("datingReportDeadline"))
        self.assertFalse(th.get("reportDeadlineIsland"))

    def test_empty_exam_islands_off(self) -> None:
        out = _interact_spec("DOM-EXAM", "在线考试管理系统", "")
        over, under = diff_interact_c_align(out)
        self.assertEqual(over, [], f"多挂: {over}")
        self.assertEqual(under, [], f"漏挂: {under}")
        th = (out.get("schema") or {}).get("interactThicken") or {}
        self.assertFalse(th.get("favoritesIsland"))
        self.assertFalse(th.get("dmIsland"))
        self.assertFalse(th.get("ratingIsland"))

    def test_c_over_mount_without_cap(self) -> None:
        out = _interact_spec("DOM-EXAM", "在线考试管理系统", "")
        th = out.setdefault("schema", {}).setdefault("interactThicken", {})
        th["dmIsland"] = True
        over, under = diff_interact_c_align(out)
        self.assertIn("dmIsland", over)
        self.assertEqual(under, [])

    def test_c_with_content_report_bake_clean(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-DATING",
                "title": "校园婚恋交友管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-DATING"]) + ["content_report"],
                "features": [],
                "archetype": "ARCH-FLOW",
            },
            "",
        )
        over, under = diff_interact_c_align(out)
        self.assertEqual(over, [])
        self.assertEqual(under, [])
        th = (out.get("schema") or {}).get("interactThicken") or {}
        self.assertTrue(th.get("datingReportDeadline"))
        self.assertTrue(th.get("reportDeadlineIsland"))

    def test_c_under_mount_when_cap_present(self) -> None:
        out = _interact_spec("DOM-CARPOOL", "校园拼车管理系统", "")
        th = out.setdefault("schema", {}).setdefault("interactThicken", {})
        th["ratingIsland"] = False
        over, under = diff_interact_c_align(out)
        self.assertEqual(over, [])
        self.assertIn("ratingIsland", under)

    def test_bc_merged_diff(self) -> None:
        out = _interact_spec("DOM-EXAM", "在线考试管理系统", "")
        th = out.setdefault("schema", {}).setdefault("interactThicken", {})
        th["favoritesIsland"] = True
        over, under = diff_interact_align(out, "")
        self.assertIn("favoritesIsland", over)
        self.assertEqual(under, [])

    def test_c_rule_count_stable(self) -> None:
        self.assertGreaterEqual(len(INTERACT_C_ALIGN_RULES), 5)
        self.assertEqual(len(INTERACT_B_ALIGN_RULES), 0)


if __name__ == "__main__":
    unittest.main()
