"""资助公示 / 发放台账：域默认旁路岛（表 + 三套同源 Store），不扩 ticket 状态机。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.engine_sql import domain_sql

ROOT = Path(__file__).resolve().parents[2]
STORES = {
    "baseline": ROOT / "skeletons" / "baseline",
    "mybatis": ROOT / "skeletons" / "overlays" / "persistence-mybatis",
    "jpa": ROOT / "skeletons" / "overlays" / "persistence-jpa",
}


class FundIslandTests(unittest.TestCase):
    def test_fund_domain_carries_both_tables(self) -> None:
        sql = domain_sql("DOM-FUND", "t_fund", title="学生资助奖学金申请")
        self.assertIn("fund_publicity", sql)
        self.assertIn("fund_disburse", sql)
        # 旁路岛不扩 ticket 状态机：不出现公示/发放态
        self.assertNotIn("publicizing", sql.split("fund_publicity")[0])

    def test_other_domains_not_leaked(self) -> None:
        for dom in ("DOM-GRADE", "DOM-ATTEND", "DOM-INTERN", "DOM-LISTING"):
            with self.subTest(domain=dom):
                sql = domain_sql(dom, "t_x", title="通用")
                self.assertNotIn("fund_publicity", sql)
                self.assertNotIn("fund_disburse", sql)

    def test_three_stacks_share_store_apis(self) -> None:
        for label, root in STORES.items():
            for name, apis in (
                (
                    "FundPublicityStore",
                    (
                        "public static List<Map<String, Object>> listAdmin(",
                        "public static List<Map<String, Object>> listMine(",
                        "public static Map<String, Object> save(",
                        "public static void close(long id, String operator)",
                        "public static void remove(long id)",
                    ),
                ),
                (
                    "FundDisburseStore",
                    (
                        "public static List<Map<String, Object>> listAdmin(",
                        "public static Map<String, Object> save(",
                        "public static String totalOf(long ticketId)",
                        "public static void remove(long id)",
                    ),
                ),
            ):
                text = (
                    root / "backend/src/main/java/com/thesis/service" / f"{name}.java"
                ).read_text(encoding="utf-8")
                for api in apis:
                    self.assertIn(api, text, msg=f"{label}:{name}:{api}")
                self.assertIn("仅审核通过的申请", text, msg=f"{label}:{name} 缺少通过校验")

    def test_controllers_expose_endpoints(self) -> None:
        base = ROOT / "skeletons" / "baseline" / "backend/src/main/java/com/thesis/controller"
        cases = (
            (
                "FundPublicityController",
                (
                    '@RequestMapping("/api/fund-publicity")',
                    '@GetMapping("/mine")',
                    '@GetMapping("/admin")',
                    '@PostMapping("/admin")',
                    '@PostMapping("/admin/{id}/close")',
                    '@DeleteMapping("/admin/{id}")',
                ),
            ),
            (
                "FundDisburseController",
                (
                    '@RequestMapping("/api/fund-disburse")',
                    '@GetMapping("/admin")',
                    '@GetMapping("/admin/total")',
                    '@PostMapping("/admin")',
                    '@DeleteMapping("/admin/{id}")',
                ),
            ),
        )
        for name, paths in cases:
            text = (base / f"{name}.java").read_text(encoding="utf-8")
            for path in paths:
                self.assertIn(path, text, msg=f"{name}:{path}")
            self.assertIn("AdminAuth.requireAdmin(session)", text, msg=name)
        """发放台账只记事实，不得写 balance_ledger（额度扣减另有其人）。"""
        for label, root in STORES.items():
            text = (
                root / "backend/src/main/java/com/thesis/service/FundDisburseStore.java"
            ).read_text(encoding="utf-8")
            for sql in ("INSERT INTO balance_ledger", "UPDATE balance_ledger"):
                self.assertNotIn(sql, text, msg=label)
