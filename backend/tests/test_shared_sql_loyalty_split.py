"""碎另案 l：忠诚度列按 cap 拆；wallet 默认不灌积分/会员/券；非交易有单域不灌售后宽列。"""

from __future__ import annotations

import re
import unittest

from app.bake.engine_sql import domain_sql
from app.bake.sql.fragments import (
    ensure_shared_sql_columns,
    loyalty_order_columns_for,
    loyalty_user_columns_for,
    order_refund_columns_for,
)


def _create_cols(sql: str, table: str) -> set[str]:
    m = re.search(
        rf"CREATE TABLE IF NOT EXISTS\s+`?{table}`?\s*\((.*?)\)\s*;",
        sql,
        re.I | re.S,
    )
    if not m:
        return set()
    out: set[str] = set()
    for line in m.group(1).splitlines():
        line = line.strip().rstrip(",")
        if not line or line.upper().startswith(
            ("PRIMARY", "KEY", "UNIQUE", "CONSTRAINT", "INDEX")
        ):
            continue
        out.add(line.split()[0].strip("`").lower())
    return out


class LoyaltyColumnSplitUnitTests(unittest.TestCase):
    def test_wallet_only_columns(self) -> None:
        u = {n for n, _ in loyalty_user_columns_for({"wallet"})}
        o = {n for n, _ in loyalty_order_columns_for({"wallet"})}
        self.assertEqual(u, {"balance_yuan"})
        self.assertEqual(o, {"pay_balance_yuan"})
        self.assertNotIn("points", u)
        self.assertNotIn("coupon_code", o)

    def test_points_and_coupon_columns(self) -> None:
        u = {n for n, _ in loyalty_user_columns_for({"wallet", "points", "coupon"})}
        o = {n for n, _ in loyalty_order_columns_for({"wallet", "points", "coupon"})}
        self.assertIn("points", u)
        self.assertIn("points_earned", o)
        self.assertIn("coupon_code", o)
        self.assertNotIn("member_tier", u)

    def test_refund_trade_vs_hotel(self) -> None:
        shop = {n for n, _ in order_refund_columns_for("DOM-SHOP")}
        hotel = {n for n, _ in order_refund_columns_for("DOM-HOTEL")}
        self.assertIn("refund_status", shop)
        self.assertIn("refund_type", shop)
        self.assertIn("completed_at", hotel)
        self.assertNotIn("refund_type", hotel)
        self.assertNotIn("refund_status", hotel)


class BareOpeningSqlGateTests(unittest.TestCase):
    def test_shop_bare_wallet_not_points_pack(self) -> None:
        sql = domain_sql(
            "DOM-SHOP",
            "t_l_shop",
            title="简易商城系统",
            proposal_text="商品浏览购物车下单支付",
        )
        user = _create_cols(sql, "sys_user")
        order = _create_cols(sql, "biz_order")
        self.assertIn("balance_yuan", user)
        self.assertIn("pay_balance_yuan", order)
        self.assertNotIn("points", user)
        self.assertNotIn("member_tier", user)
        self.assertNotIn("points_earned", order)
        self.assertNotIn("coupon_code", order)
        self.assertNotIn("warranty_until", order)
        self.assertNotIn("invoice_title", order)
        # 交易域售后 A 壳仍可有
        self.assertIn("refund_status", order)

    def test_shop_points_opening_gets_points_cols(self) -> None:
        sql = domain_sql(
            "DOM-SHOP",
            "t_l_shop_pts",
            title="积分商城系统",
            proposal_text="购物车下单与会员积分兑换",
        )
        user = _create_cols(sql, "sys_user")
        order = _create_cols(sql, "biz_order")
        self.assertIn("points", user)
        self.assertIn("points_earned", order)

    def test_hotel_no_refund_wide_or_points_pack(self) -> None:
        sql = domain_sql(
            "DOM-HOTEL",
            "t_l_hotel",
            title="酒店预订系统",
            proposal_text="客房预订入住离店",
        )
        user = _create_cols(sql, "sys_user")
        order = _create_cols(sql, "biz_order")
        self.assertIn("balance_yuan", user)
        self.assertNotIn("points", user)
        self.assertNotIn("coupon_code", order)
        self.assertNotIn("refund_type", order)
        self.assertNotIn("refund_tracking_no", order)
        self.assertIn("completed_at", order)

    def test_food_bare_no_points_pack(self) -> None:
        sql = domain_sql(
            "DOM-FOOD",
            "t_l_food",
            title="点餐系统",
            proposal_text="堂食外卖下单",
        )
        user = _create_cols(sql, "sys_user")
        order = _create_cols(sql, "biz_order")
        self.assertNotIn("points", user)
        self.assertNotIn("member_tier", user)
        self.assertNotIn("coupon_code", order)
        self.assertIn("refund_status", order)

    def test_ensure_prunes_stale_loyalty_cols(self) -> None:
        raw = """
CREATE TABLE IF NOT EXISTS sys_user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  points INT NOT NULL DEFAULT 0,
  member_tier VARCHAR(32) DEFAULT '',
  balance_yuan DECIMAL(10,2) NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS biz_order (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL,
  total_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  points_earned INT NOT NULL DEFAULT 0,
  coupon_code VARCHAR(32) DEFAULT '',
  pay_balance_yuan DECIMAL(10,2) NOT NULL DEFAULT 0
);
"""
        out = ensure_shared_sql_columns(
            raw,
            domain="DOM-SHOP",
            loyalty_caps={"wallet"},
        )
        user = _create_cols(out, "sys_user")
        order = _create_cols(out, "biz_order")
        self.assertIn("balance_yuan", user)
        self.assertNotIn("points", user)
        self.assertNotIn("member_tier", user)
        self.assertIn("pay_balance_yuan", order)
        self.assertNotIn("points_earned", order)
        self.assertNotIn("coupon_code", order)


if __name__ == "__main__":
    unittest.main()
