"""报修组 repair_thicken：域默认催办/结单/SLA；扫词备件/报价/远程等。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.ticket_policy import policy_preview
from app.bake.engine_sql import domain_sql
from app.bake.features.repair_thicken import (
    REPAIR_DOMAINS,
    scan_parts_ledger,
    scan_quote_confirm,
    scan_remote_assist,
    scan_ticket_merge,
)


def _spec(domain: str, title: str, body: str = "") -> dict:
    return attach_accept(
        {
            "domain": domain,
            "title": title,
            "capabilities": list(DOMAIN_CAPABILITIES[domain]),
            "features": [],
            "archetype": "ARCH-FLOW",
        },
        body,
    )


class RepairThickenFeatureTests(unittest.TestCase):
    def test_dorm_core_defaults(self) -> None:
        out = _spec("DOM-DORM", "学生宿舍报修管理系统", "")
        schema = out.get("schema") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        thicken = schema.get("repairThicken") or {}
        labels = schema.get("labels") or {}
        self.assertTrue(ticket.get("repairThicken"))
        self.assertTrue(thicken.get("core"))
        self.assertTrue(ticket.get("allowUserUrge"))
        self.assertGreaterEqual(int(ticket.get("urgeCooldownMinutes") or 0), 1)
        self.assertTrue(ticket.get("requireFaultReason"))
        self.assertTrue(ticket.get("requireCloseSummary"))
        self.assertTrue(ticket.get("slaSplit"))
        self.assertTrue(ticket.get("allowHoldResume"))
        self.assertTrue(ticket.get("dupRoomCheck"))
        self.assertTrue(ticket.get("allowPublicArea"))
        self.assertTrue(thicken.get("buildingHeat"))
        self.assertIn("urgeLabel", labels)
        self.assertIn("workloadHint", labels)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-DORM", out) + policy_preview("DOM-DORM", out)
        self.assertIn("ticket-repair-thicken: true", yml)
        self.assertIn("ticket-allow-user-urge: true", yml)
        self.assertIn("ticket-urge-cooldown-minutes:", yml)
        self.assertIn("ticket-require-fault-reason: true", yml)
        self.assertIn("ticket-sla-split: true", yml)

    def test_property_parts_default(self) -> None:
        out = _spec("DOM-PROPERTY", "智慧社区物业报修", "")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        thicken = (out.get("schema") or {}).get("repairThicken") or {}
        self.assertTrue(ticket.get("allowPartsNote"))
        self.assertTrue(ticket.get("allowSerialNo"))
        self.assertTrue(thicken.get("parts"))
        self.assertTrue(ticket.get("allowPublicArea"))

    def test_it_asset_and_remote(self) -> None:
        out = _spec("DOM-IT", "校园网故障报修", "")
        schema = out.get("schema") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        thicken = schema.get("repairThicken") or {}
        labels = schema.get("labels") or {}
        self.assertTrue(ticket.get("allowAssetCode"))
        self.assertTrue(ticket.get("allowRemoteUrl"))
        self.assertTrue(thicken.get("assetCode"))
        self.assertTrue(thicken.get("remote"))
        self.assertIn("assetCodeLabel", labels)
        self.assertIn("faqPageHint", labels)

    def test_non_repair_domain_skips(self) -> None:
        out = _spec("DOM-LIBRARY", "图书借阅", "")
        schema = out.get("schema") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertFalse(ticket.get("repairThicken"))
        self.assertNotIn("repairThicken", schema)

    def test_quote_scan(self) -> None:
        self.assertTrue(scan_quote_confirm("支持维修报价用户确认"))
        out = _spec("DOM-DORM", "宿舍报修", "维修报价与材料费确认支付")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowQuote"))

    def test_parts_scan_on_dorm(self) -> None:
        self.assertTrue(scan_parts_ledger("结单登记备件出库"))
        out = _spec("DOM-DORM", "宿舍报修", "备件出库与耗材台账")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowPartsNote"))

    def test_merge_and_remote_scan(self) -> None:
        self.assertTrue(scan_ticket_merge("重复工单合并为主从"))
        self.assertTrue(scan_remote_assist("IT 远程协助会议号"))
        out = _spec("DOM-IT", "IT 工单", "重复工单合并与远程协助备注")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowTicketMerge"))
        self.assertTrue(ticket.get("allowRemoteUrl"))

    def test_domain_sql_has_repair_cols(self) -> None:
        for domain in sorted(REPAIR_DOMAINS):
            out = _spec(domain, f"{domain} 报修", "")
            ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
            text = domain_sql(
                domain,
                "db_test",
                capabilities=list(out.get("capabilities") or []),
                title="报修",
                ticket_flags=ticket,
            )
            self.assertIn("urge_at", text, domain)
            self.assertIn("fault_reason", text, domain)
            self.assertIn("close_summary", text, domain)
            self.assertIn("response_due_at", text, domain)


if __name__ == "__main__":
    unittest.main()
