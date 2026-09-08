"""能力扩岛 E-06：站内消息模板 message_template（开题扫词才挂，无域默认）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.message_template import (
    MESSAGE_TEMPLATE_CAP,
    merge_message_template_capabilities,
    scan_message_template,
)
from tests.helpers.normalize import normalize_sql

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class MessageTemplateE06Tests(unittest.TestCase):
    def test_capability_registered_no_domain_default(self) -> None:
        self.assertEqual(CAPABILITIES[MESSAGE_TEMPLATE_CAP]["status"], "implemented")
        for dom, caps in DOMAIN_CAPABILITIES.items():
            self.assertNotIn(MESSAGE_TEMPLATE_CAP, caps or [], dom)

    def test_scan_terms(self) -> None:
        self.assertTrue(scan_message_template("支持消息模板与站内通知。"))
        self.assertTrue(scan_message_template("可配置通知模板。"))
        self.assertTrue(scan_message_template("站内信模板维护。"))
        self.assertFalse(scan_message_template("站内消息铃铛与审核通知。"))

    def test_merge_only_when_scanned(self) -> None:
        base = list(DOMAIN_CAPABILITIES["DOM-LIBRARY"])
        no = merge_message_template_capabilities(base, "图书借还催还。", domain="DOM-LIBRARY")
        self.assertNotIn(MESSAGE_TEMPLATE_CAP, no)
        yes = merge_message_template_capabilities(
            base, "图书借还；支持消息模板。", domain="DOM-LIBRARY"
        )
        self.assertIn(MESSAGE_TEMPLATE_CAP, yes)

    def test_attach_accept_sql_yml_menu(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "archetype": "ARCH-FLOW",
            },
            "图书借还催还。",
        )
        self.assertNotIn(MESSAGE_TEMPLATE_CAP, plain.get("capabilities") or [])
        menus0 = (plain.get("schema") or {}).get("menus", {}).get("admin") or []
        self.assertFalse(any(m.get("key") == "message_templates" for m in menus0))

        rich = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "archetype": "ARCH-FLOW",
            },
            "图书借还；支持消息模板与通知模板。",
        )
        caps = rich.get("capabilities") or []
        self.assertIn(MESSAGE_TEMPLATE_CAP, caps)
        menus = (rich.get("schema") or {}).get("menus", {}).get("admin") or []
        self.assertTrue(any(m.get("key") == "message_templates" for m in menus))
        lead = ((rich.get("schema") or {}).get("labels") or {}).get(
            "messageTemplatesPageLead"
        ) or ""
        self.assertNotIn("演示", str(lead))
        self.assertIn("message_template", (rich.get("gate") or {}).get("flow_api") or {})

        yml = _patch_thesis_yml("thesis:\n  domain: DOM-LIBRARY\n", "DOM-LIBRARY", rich)
        self.assertIn("message-template-enabled: true", yml)

        sql = domain_sql(
            "DOM-LIBRARY",
            "thesis_lib",
            capabilities=caps,
            proposal_text="图书借还；支持消息模板与通知模板。",
        )
        n = normalize_sql(sql)
        self.assertIn("sys_message_template", n)
        self.assertIn("ticket_approved", n)
        self.assertIn("ticket_rejected", n)

    def test_unmounted_no_template_table(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "archetype": "ARCH-FLOW",
            },
            "图书借还催还。",
        )
        sql = domain_sql(
            "DOM-LIBRARY",
            "thesis_lib",
            capabilities=plain.get("capabilities") or [],
            proposal_text="图书借还催还。",
        )
        self.assertNotIn("sys_message_template", normalize_sql(sql))

    def test_baseline_store_controller_fe_hook(self) -> None:
        store = (
            BASELINE / "backend/src/main/java/com/thesis/service/MessageStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("configureTemplate", store)
        self.assertIn("sendWithTemplate", store)
        self.assertIn("pageTemplates", store)
        self.assertIn("updateTemplate", store)
        ctrl = (
            BASELINE
            / "backend/src/main/java/com/thesis/controller/MessageTemplateController.java"
        )
        self.assertTrue(ctrl.is_file())
        self.assertIn("/api/admin/message-templates", ctrl.read_text(encoding="utf-8"))
        fe = BASELINE / "frontend/src/views/admin/MessageTemplatesAdmin.vue"
        self.assertTrue(fe.is_file())
        ticket = (
            BASELINE
            / "backend/src/main/java/com/thesis/capability/TicketStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("sendWithTemplate", ticket)
        self.assertIn("ticket_approved", ticket)
        router = (BASELINE / "frontend/src/router/index.js").read_text(encoding="utf-8")
        self.assertIn("withMessageTemplateRoutes", router)
        self.assertIn("MessageTemplatesAdmin", router)


if __name__ == "__main__":
    unittest.main()
