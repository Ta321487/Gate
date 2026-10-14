"""表预算：舒适区警告 / 硬顶打回 / 选题必需表例外。"""

from __future__ import annotations

import unittest

from app.bake.engine_sql import (
    TABLE_COUNT_HARD,
    TABLE_COUNT_MAX,
    assert_table_budget,
    evaluate_table_budget,
)


def _sql(n: int, names: list[str] | None = None) -> str:
    if names is None:
        names = [f"t{i}" for i in range(n)]
    parts = [f"CREATE TABLE IF NOT EXISTS {name} (id BIGINT PRIMARY KEY);" for name in names]
    return "\n".join(parts)


class TableBudgetTests(unittest.TestCase):
    def test_comfort_zone_ok(self) -> None:
        r = evaluate_table_budget(_sql(12), "DOM-SHOP")
        self.assertTrue(r.ok)
        self.assertFalse(r.warn)
        self.assertEqual(r.count, 12)

    def test_over_soft_warns_not_reject(self) -> None:
        r = evaluate_table_budget(_sql(16), "DOM-SHOP")
        self.assertTrue(r.ok)
        self.assertTrue(r.warn)
        self.assertEqual(r.count, 16)
        assert_table_budget(_sql(16), "DOM-SHOP")  # 不抛

    def test_over_hard_rejects(self) -> None:
        r = evaluate_table_budget(_sql(19), "DOM-SHOP")
        self.assertFalse(r.ok)
        self.assertFalse(r.warn)
        with self.assertRaises(ValueError) as ctx:
            assert_table_budget(_sql(19), "DOM-SHOP")
        self.assertIn(str(TABLE_COUNT_HARD), str(ctx.exception))

    def test_essential_scanned_tables_exempt_from_hard(self) -> None:
        # 域默认无 group_buy；19 张里含 2 张团购表 → 计费 17 ≤ 18
        names = [f"t{i}" for i in range(17)] + ["group_campaign", "group_member"]
        sql = _sql(0, names)
        r = evaluate_table_budget(sql, "DOM-SHOP", caps=["group_buy"])
        self.assertEqual(r.count, 19)
        self.assertEqual(r.charged, 17)
        self.assertTrue(r.ok)
        self.assertTrue(r.warn)
        assert_table_budget(sql, "DOM-SHOP", caps=["group_buy"])

    def test_domain_default_cap_tables_still_charged(self) -> None:
        # guestbook 是 DOM-SHOP 默认能力，sys_guestbook 仍计费
        names = [f"t{i}" for i in range(18)] + ["sys_guestbook"]
        sql = _sql(0, names)
        r = evaluate_table_budget(sql, "DOM-SHOP", caps=["guestbook"])
        self.assertEqual(r.count, 19)
        self.assertEqual(r.charged, 19)
        self.assertFalse(r.ok)

    def test_platform_crosscut_tables_exempt_from_hard(self) -> None:
        # 18 张业务壳 + 7 张通识横切 → 计费仍 18，不打回
        names = [f"t{i}" for i in range(18)] + [
            "sys_auth_session",
            "sys_login_log",
            "sys_invite_code",
            "sys_account_cancel",
            "sys_notice_ack",
            "sys_banner",
            "sys_site_stat",
        ]
        sql = _sql(0, names)
        r = evaluate_table_budget(sql, "DOM-SHOP")
        self.assertEqual(r.count, 25)
        self.assertEqual(r.charged, 18)
        self.assertTrue(r.ok)
        self.assertTrue(r.warn)
        assert_table_budget(sql, "DOM-SHOP")

    def test_shop_scanned_caps_with_platform_ok(self) -> None:
        from app.bake.domains import DOMAIN_CAPABILITIES
        from app.bake.engine_sql import domain_sql

        caps = list(DOMAIN_CAPABILITIES["DOM-SHOP"]) + [
            "dm",
            "favorites",
            "wallet",
            "digital_goods",
        ]
        sql = domain_sql(
            "DOM-SHOP",
            "t_shop",
            title="农产商城",
            proposal_text="数字商品 私信 收藏 余额",
            capabilities=caps,
        )
        r = evaluate_table_budget(sql, "DOM-SHOP", caps)
        self.assertTrue(r.ok, r.message)
        self.assertLessEqual(r.charged, TABLE_COUNT_HARD)

    def test_below_floor_rejects(self) -> None:
        r = evaluate_table_budget(_sql(5), "DOM-SHOP")
        self.assertFalse(r.ok)
        self.assertIn("低于下限", r.message)

    def test_soft_max_constant(self) -> None:
        self.assertEqual(TABLE_COUNT_MAX, 15)
        self.assertEqual(TABLE_COUNT_HARD, 18)


if __name__ == "__main__":
    unittest.main()
