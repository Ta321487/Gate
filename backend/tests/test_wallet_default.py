"""交易壳默认钱包：有 order_lines 即挂 wallet；多店默认支付超时。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.features.loyalty import apply_loyalty_to_spec, merge_loyalty_capabilities
from app.bake.features.order_extras import apply_order_extras_to_spec, order_timeout_minutes
from app.bake.gate_contracts import merge_loyalty_gate


class WalletDefaultTests(unittest.TestCase):
    def test_order_lines_defaults_wallet(self) -> None:
        caps = merge_loyalty_capabilities(["archive", "order_lines", "quota"], "")
        self.assertIn("wallet", caps)

    def test_no_order_lines_strips_wallet(self) -> None:
        caps = merge_loyalty_capabilities(["archive", "wallet", "ticket_flow"], "余额充值")
        self.assertNotIn("wallet", caps)

    def test_scan_still_adds_points(self) -> None:
        caps = merge_loyalty_capabilities(
            ["archive", "order_lines"],
            "会员积分与满减优惠",
        )
        self.assertIn("wallet", caps)
        self.assertIn("points", caps)
        self.assertIn("spend_discount", caps)

    def test_apply_loyalty_schema_wallet(self) -> None:
        spec = apply_loyalty_to_spec(
            {
                "domain": "DOM-SHOP",
                "capabilities": ["archive", "order_lines", "quota", "content"],
                "schema": {},
            },
            "助农生鲜下单配送",
        )
        self.assertIn("wallet", spec.get("capabilities") or [])
        loy = (spec.get("schema") or {}).get("loyalty") or {}
        self.assertTrue((loy.get("wallet") or {}).get("enabled"))

    def test_gate_needs_demo_recharge(self) -> None:
        gate = merge_loyalty_gate({}, ["wallet", "order_lines"])
        need = ((gate.get("flow_api") or {}).get("loyalty") or {}).get("need") or []
        self.assertIn("/api/loyalty/demo-recharge", need)

    def test_marketplace_default_timeout(self) -> None:
        self.assertEqual(
            order_timeout_minutes(
                "",
                ["order_lines"],
                schema={"shopMarketplace": True, "demoPay": True},
            ),
            15,
        )
        self.assertEqual(order_timeout_minutes("", ["order_lines"]), 0)
        self.assertEqual(
            order_timeout_minutes("支付超时自动取消", ["order_lines"]),
            30,
        )

    def test_attach_accept_shop_marketplace_wallet_and_timeout(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "多商家农产品电商平台",
                "capabilities": ["archive", "order_lines", "quota", "content", "org_users"],
                "schema": {},
            },
            "支持商家入驻与店铺审核，买家购物车下单支付配送",
        )
        caps = out.get("capabilities") or []
        self.assertIn("wallet", caps)
        schema = out.get("schema") or {}
        self.assertTrue(schema.get("shopMarketplace"))
        self.assertEqual(schema.get("orderTimeoutMinutes"), 15)
        hint = (schema.get("labels") or {}).get("orderTimeoutHint") or ""
        self.assertIn("待付款", hint)

    def test_apply_order_extras_marketplace_timeout(self) -> None:
        spec = apply_order_extras_to_spec(
            {
                "domain": "DOM-SHOP",
                "title": "多店电商",
                "capabilities": ["archive", "order_lines"],
                "schema": {"shopMarketplace": True, "demoPay": True},
            },
            "商家入驻平台",
        )
        self.assertEqual((spec.get("schema") or {}).get("orderTimeoutMinutes"), 15)


if __name__ == "__main__":
    unittest.main()
