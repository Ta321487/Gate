"""能力扩岛 E-02：候补 waitlist（开题扫词才挂，无域默认）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES, resolve_accept
from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.features.ticket_flow_opts import (
    WAITLIST_CAP,
    merge_waitlist_capabilities,
    scan_waitlist,
)

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class WaitlistE02Tests(unittest.TestCase):
    def test_capability_registered(self) -> None:
        self.assertIn(WAITLIST_CAP, CAPABILITIES)
        self.assertEqual(CAPABILITIES[WAITLIST_CAP]["status"], "implemented")
        for dom in ("DOM-ACTIVITY", "DOM-COURSE", "DOM-TOUR", "DOM-LOST"):
            self.assertNotIn(WAITLIST_CAP, DOMAIN_CAPABILITIES.get(dom) or [])

    def test_scan_terms(self) -> None:
        self.assertTrue(scan_waitlist("名额满可候补报名。"))
        self.assertTrue(scan_waitlist("支持满员候补与等位。"))
        self.assertFalse(scan_waitlist("活动报名审核与签到。"))

    def test_merge_only_when_scanned_on_quota_domain(self) -> None:
        base = list(DOMAIN_CAPABILITIES["DOM-ACTIVITY"])
        self.assertIn("quota", base)
        no = merge_waitlist_capabilities(base, "活动报名审核签到。", domain="DOM-ACTIVITY")
        self.assertNotIn(WAITLIST_CAP, no)

        yes = merge_waitlist_capabilities(
            base, "社团活动报名，支持满员候补。", domain="DOM-ACTIVITY"
        )
        self.assertIn(WAITLIST_CAP, yes)

        course = merge_waitlist_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-COURSE"]),
            "公选课选课，满员可候补。",
            domain="DOM-COURSE",
        )
        self.assertIn(WAITLIST_CAP, course)

        # 非名额报名域即使写候补也不挂
        lib = merge_waitlist_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
            "图书借阅支持候补。",
            domain="DOM-LIBRARY",
        )
        self.assertNotIn(WAITLIST_CAP, lib)

    def test_attach_accept_schema_and_yml(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-ACTIVITY",
                "title": "社团活动报名系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-ACTIVITY"]),
                "archetype": "ARCH-FLOW",
            },
            "活动发布、报名、审核、签到。",
        )
        self.assertNotIn(WAITLIST_CAP, plain.get("capabilities") or [])
        ticket = (plain.get("schema") or {}).get("entities", {}).get("ticket") or {}
        self.assertFalse(bool(ticket.get("allowWaitlist")))

        with_wl = attach_accept(
            {
                "domain": "DOM-ACTIVITY",
                "title": "社团活动报名系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-ACTIVITY"]),
                "archetype": "ARCH-FLOW",
            },
            "活动发布与报名审核；名额满时可候补，取消后按序晋升。",
        )
        self.assertIn(WAITLIST_CAP, with_wl.get("capabilities") or [])
        self.assertEqual(with_wl.get("accept"), "full", with_wl.get("accept_reason"))
        t2 = (with_wl.get("schema") or {}).get("entities", {}).get("ticket") or {}
        self.assertTrue(t2.get("allowWaitlist"))
        states = t2.get("states") or {}
        self.assertIn("waitlisted", states)
        labels = (with_wl.get("schema") or {}).get("labels") or {}
        self.assertIn("候补", str(labels.get("waitlistVerb") or "候补"))

        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-ACTIVITY", with_wl)
        self.assertIn("ticket-allow-waitlist: true", yml)

        feats = with_wl.get("features") or []
        self.assertTrue(
            any(isinstance(f, dict) and "候补" in str(f.get("name") or "") for f in feats),
            feats,
        )

    def test_match_activity_still(self) -> None:
        got = match_text(
            "基于 Spring Boot 的校园社团活动报名系统。"
            "主要功能：活动发布、报名、审核、候补、签到。"
        )
        self.assertEqual(got.domain, "DOM-ACTIVITY", f"hits={got.hits[:12]}")

    def test_runtime_paths_reuse_ticket(self) -> None:
        for rel in (
            "backend/src/main/java/com/thesis/capability/TicketStore.java",
            "frontend/src/views/user/ArchiveBrowse.vue",
            "frontend/src/views/user/MyTickets.vue",
        ):
            self.assertTrue((BASELINE / rel).is_file(), rel)
        store = (BASELINE / "backend/src/main/java/com/thesis/capability/TicketStore.java").read_text(
            encoding="utf-8"
        )
        self.assertIn("configureWaitlist", store)
        self.assertIn("tryPromoteWaitlist", store)
        self.assertIn("waitlisted", store)
        fe = (BASELINE / "frontend/src/views/user/ArchiveBrowse.vue").read_text(encoding="utf-8")
        self.assertIn("allowWaitlist", fe)
        self.assertIn("waitlisted", fe)
        self.assertNotIn("演示", fe)
        my = (BASELINE / "frontend/src/views/user/MyTickets.vue").read_text(encoding="utf-8")
        self.assertIn("waitlisted", my)

    def test_accept_full_with_waitlist(self) -> None:
        caps = list(DOMAIN_CAPABILITIES["DOM-ACTIVITY"]) + [WAITLIST_CAP]
        d = resolve_accept(
            caps,
            "活动报名候补。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-FLOW"],
            domain="DOM-ACTIVITY",
            primary_archetype="ARCH-FLOW",
        )
        self.assertEqual(d["accept"], "full", d)


if __name__ == "__main__":
    unittest.main()
