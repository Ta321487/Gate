"""能力扩岛 E-11：图书预约 book_hold（开题扫词才挂，无域默认）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.book_hold import (
    BOOK_HOLD_CAP,
    merge_book_hold_capabilities,
    scan_book_hold,
)
from app.bake.features.ticket_flow_opts import WAITLIST_CAP, scan_waitlist
from tests.helpers.normalize import normalize_sql

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class BookHoldE11Tests(unittest.TestCase):
    def test_capability_registered_no_domain_default(self) -> None:
        self.assertEqual(CAPABILITIES[BOOK_HOLD_CAP]["status"], "implemented")
        for dom in ("DOM-LIBRARY", "DOM-EQUIP", "DOM-ACTIVITY", "DOM-COURSE"):
            self.assertNotIn(BOOK_HOLD_CAP, DOMAIN_CAPABILITIES.get(dom) or [], dom)

    def test_scan_terms_not_waitlist(self) -> None:
        self.assertTrue(scan_book_hold("支持图书预约与到书通知。"))
        self.assertTrue(scan_book_hold("读者可预约借阅。"))
        self.assertFalse(scan_book_hold("借阅归还与催还。"))
        self.assertFalse(scan_waitlist("图书预约与到书通知。"))
        self.assertFalse(scan_book_hold("活动报名候补队列。"))

    def test_merge_library_only_when_scanned(self) -> None:
        base = list(DOMAIN_CAPABILITIES["DOM-LIBRARY"])
        no = merge_book_hold_capabilities(base, "图书借还系统。", domain="DOM-LIBRARY")
        self.assertNotIn(BOOK_HOLD_CAP, no)
        yes = merge_book_hold_capabilities(
            base, "图书借还；支持图书预约与到书通知。", domain="DOM-LIBRARY"
        )
        self.assertIn(BOOK_HOLD_CAP, yes)

        act = list(DOMAIN_CAPABILITIES["DOM-ACTIVITY"])
        blocked = merge_book_hold_capabilities(
            act, "图书预约。", domain="DOM-ACTIVITY"
        )
        self.assertNotIn(BOOK_HOLD_CAP, blocked)

    def test_attach_accept_sql_yml_states(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "archetype": "ARCH-LOAN",
            },
            "图书检索借还催还。",
        )
        self.assertNotIn(BOOK_HOLD_CAP, plain.get("capabilities") or [])
        ticket0 = ((plain.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(ticket0.get("allowBookHold"))

        rich = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "archetype": "ARCH-LOAN",
            },
            "图书借还；支持图书预约、到书通知与限时取书。",
        )
        caps = rich.get("capabilities") or []
        self.assertIn(BOOK_HOLD_CAP, caps)
        self.assertNotIn(WAITLIST_CAP, caps)
        ticket = ((rich.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowBookHold"))
        states = ticket.get("states") or {}
        self.assertIn("held", states)
        self.assertIn("hold_ready", states)
        labels = (rich.get("schema") or {}).get("labels") or {}
        self.assertNotIn("演示", str(labels.get("bookHoldOkMessage") or ""))
        self.assertIn("book_hold", (rich.get("gate") or {}).get("flow_api") or {})

        yml = _patch_thesis_yml("thesis:\n  domain: DOM-LIBRARY\n", "DOM-LIBRARY", rich)
        self.assertIn("ticket-allow-book-hold: true", yml)
        self.assertIn("ticket-hold-hours:", yml)

        sql = domain_sql(
            "DOM-LIBRARY",
            "t_book",
            title="图书借阅",
            proposal_text="图书预约到书通知",
            capabilities=caps,
            ticket_flags=ticket,
        )
        norm = normalize_sql(sql)
        self.assertIn("hold_expire_at", norm)

    def test_unmounted_no_hold_sql(self) -> None:
        sql = domain_sql(
            "DOM-LIBRARY",
            "t_book",
            title="图书借阅",
            proposal_text="图书借还",
        )
        norm = normalize_sql(sql)
        self.assertNotIn("hold_expire_at", norm)

    def test_baseline_files(self) -> None:
        store = (
            BASELINE
            / "backend/src/main/java/com/thesis/capability/TicketStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("configureBookHold", store)
        self.assertIn("tryPromoteBookHold", store)
        self.assertIn("claimHold", store)
        self.assertIn("hold_ready", store)
        ctrl = (
            BASELINE
            / "backend/src/main/java/com/thesis/controller/TicketController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("claim-hold", ctrl)
        browse = (
            BASELINE / "frontend/src/views/user/ArchiveBrowse.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("book_hold", browse)
        self.assertIn("allowBookHold", browse)
        mine = (BASELINE / "frontend/src/views/user/MyTickets.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("claim-hold", mine)
        self.assertIn("canClaimHold", mine)


if __name__ == "__main__":
    unittest.main()
