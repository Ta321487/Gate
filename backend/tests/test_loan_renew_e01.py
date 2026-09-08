"""能力扩岛 E-01：续借 loan_renew（开题扫词才挂，无域默认）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES, resolve_accept
from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.core_cap_scan import (
    LOAN_RENEW_CAP,
    merge_loan_renew_capabilities,
    scan_loan_renew,
)

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class LoanRenewE01Tests(unittest.TestCase):
    def test_capability_registered(self) -> None:
        self.assertIn(LOAN_RENEW_CAP, CAPABILITIES)
        self.assertEqual(CAPABILITIES[LOAN_RENEW_CAP]["status"], "implemented")
        # 禁止域默认硬塞
        self.assertNotIn(LOAN_RENEW_CAP, DOMAIN_CAPABILITIES.get("DOM-LIBRARY") or [])
        self.assertNotIn(LOAN_RENEW_CAP, DOMAIN_CAPABILITIES.get("DOM-EQUIP") or [])

    def test_scan_terms(self) -> None:
        self.assertTrue(scan_loan_renew("支持续借与逾期催还。"))
        self.assertTrue(scan_loan_renew("读者可申请续借延长借期。"))
        self.assertFalse(scan_loan_renew("借阅归还与催还。"))

    def test_merge_only_when_scanned_on_loan_domain(self) -> None:
        base = list(DOMAIN_CAPABILITIES["DOM-LIBRARY"])
        no = merge_loan_renew_capabilities(base, "借阅归还催还。", domain="DOM-LIBRARY")
        self.assertNotIn(LOAN_RENEW_CAP, no)

        yes = merge_loan_renew_capabilities(
            base, "借阅归还；支持续借与逾期催还。", domain="DOM-LIBRARY"
        )
        self.assertIn(LOAN_RENEW_CAP, yes)
        self.assertIn("deadline", yes)

        # 非借还域即使写续借也不挂
        shop = merge_loan_renew_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
            "商城支持续借商品？",
            domain="DOM-SHOP",
        )
        self.assertNotIn(LOAN_RENEW_CAP, shop)

    def test_attach_accept_schema_and_yml(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书借阅管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "archetype": "ARCH-FLOW",
            },
            "图书借阅、归还与催还。",
        )
        self.assertNotIn(LOAN_RENEW_CAP, plain.get("capabilities") or [])
        ticket = (plain.get("schema") or {}).get("entities", {}).get("ticket") or {}
        self.assertFalse(bool(ticket.get("allowRenew")))

        with_renew = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书借阅管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "archetype": "ARCH-FLOW",
            },
            "图书检索借阅归还；支持续借与逾期催还罚款。",
        )
        self.assertIn(LOAN_RENEW_CAP, with_renew.get("capabilities") or [])
        self.assertEqual(with_renew.get("accept"), "full", with_renew.get("accept_reason"))
        t2 = (with_renew.get("schema") or {}).get("entities", {}).get("ticket") or {}
        self.assertTrue(t2.get("allowRenew"))
        self.assertGreaterEqual(int(t2.get("maxRenew") or 0), 1)
        labels = (with_renew.get("schema") or {}).get("labels") or {}
        self.assertIn("续借", str(labels.get("renewVerb") or "续借"))

        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-LIBRARY", with_renew)
        self.assertIn("ticket-allow-renew: true", yml)

        sql = domain_sql(
            "DOM-LIBRARY",
            "t_book",
            title="图书借阅",
            proposal_text="借阅续借逾期催还",
            capabilities=list(with_renew.get("capabilities") or []),
            ticket_flags=t2,
        )
        self.assertIn("renew_count", sql)

    def test_no_renew_column_without_cap(self) -> None:
        sql = domain_sql(
            "DOM-LIBRARY",
            "t_book",
            title="图书借阅",
            proposal_text="借阅归还催还",
        )
        self.assertNotIn("renew_count", sql)

    def test_match_library_still(self) -> None:
        got = match_text(
            "基于 Spring Boot 的图书借阅管理系统。"
            "主要功能：检索、借阅、归还、续借、逾期催还。"
        )
        self.assertEqual(got.domain, "DOM-LIBRARY", f"hits={got.hits[:12]}")

    def test_runtime_paths_reuse_ticket(self) -> None:
        # 改原 TicketStore/Controller/MyTickets，无旁挂续借文件
        for rel in (
            "backend/src/main/java/com/thesis/capability/TicketStore.java",
            "backend/src/main/java/com/thesis/controller/TicketController.java",
            "frontend/src/views/user/MyTickets.vue",
        ):
            self.assertTrue((BASELINE / rel).is_file(), rel)
        store = (BASELINE / "backend/src/main/java/com/thesis/capability/TicketStore.java").read_text(
            encoding="utf-8"
        )
        self.assertIn("configureRenew", store)
        self.assertIn("public static Map<String, Object> renew(", store)
        ctrl = (
            BASELINE / "backend/src/main/java/com/thesis/controller/TicketController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("/{id}/renew", ctrl)
        fe = (BASELINE / "frontend/src/views/user/MyTickets.vue").read_text(encoding="utf-8")
        self.assertIn("canRenew", fe)
        self.assertIn("/api/tickets/${row.id}/renew", fe)
        self.assertNotIn("演示", fe)

    def test_accept_full_with_renew(self) -> None:
        caps = list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]) + [LOAN_RENEW_CAP]
        d = resolve_accept(
            caps,
            "借阅续借催还。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-FLOW"],
            domain="DOM-LIBRARY",
            primary_archetype="ARCH-FLOW",
        )
        self.assertEqual(d["accept"], "full", d)


if __name__ == "__main__":
    unittest.main()
