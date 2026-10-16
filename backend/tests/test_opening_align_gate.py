"""开题对齐门禁：登记开关双向对上（交易/借用 B 扫词 + C cap）。

禁止开题全文 vs 页面全文自由匹配。
"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.features.borrow_thicken import (
    BORROW_A_SHELL_WHITELIST,
    BORROW_B_ALIGN_RULES,
    BORROW_C_ALIGN_RULES,
    diff_borrow_align,
    diff_borrow_b_align,
    diff_borrow_c_align,
    expected_borrow_b_flags,
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


if __name__ == "__main__":
    unittest.main()
