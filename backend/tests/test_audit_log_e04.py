"""能力扩岛 E-04：操作审计日志 audit_log（开题扫词才挂，无域默认）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.audit_log import (
    AUDIT_LOG_CAP,
    audit_login_only,
    merge_audit_log_capabilities,
    scan_audit_log,
)
from tests.helpers.normalize import normalize_sql

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class AuditLogE04Tests(unittest.TestCase):
    def test_capability_registered_no_domain_default(self) -> None:
        self.assertEqual(CAPABILITIES[AUDIT_LOG_CAP]["status"], "implemented")
        for dom, caps in DOMAIN_CAPABILITIES.items():
            self.assertNotIn(AUDIT_LOG_CAP, caps or [], dom)

    def test_scan_terms(self) -> None:
        self.assertTrue(scan_audit_log("系统记录操作日志与审计。"))
        self.assertTrue(scan_audit_log("支持登录日志查询。"))
        self.assertTrue(scan_audit_log("查看操作记录。"))
        self.assertFalse(scan_audit_log("图书借还与催还。"))
        self.assertTrue(audit_login_only("仅提供登录日志。"))
        self.assertFalse(audit_login_only("操作日志与登录日志。"))

    def test_merge_only_when_scanned(self) -> None:
        base = list(DOMAIN_CAPABILITIES["DOM-LIBRARY"])
        no = merge_audit_log_capabilities(base, "图书借还催还。", domain="DOM-LIBRARY")
        self.assertNotIn(AUDIT_LOG_CAP, no)
        yes = merge_audit_log_capabilities(
            base, "图书借还；记录操作日志。", domain="DOM-LIBRARY"
        )
        self.assertIn(AUDIT_LOG_CAP, yes)

    def test_attach_accept_sql_yml_fe_be(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "archetype": "ARCH-FLOW",
            },
            "图书借还催还管理。",
        )
        self.assertNotIn(AUDIT_LOG_CAP, plain.get("capabilities") or [])
        menus0 = (plain.get("schema") or {}).get("menus", {}).get("admin") or []
        self.assertFalse(any(m.get("key") == "audit_logs" for m in menus0))

        rich = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "archetype": "ARCH-FLOW",
            },
            "图书借还；支持操作日志与审计查询。",
        )
        caps = rich.get("capabilities") or []
        self.assertIn(AUDIT_LOG_CAP, caps)
        self.assertFalse(bool((rich.get("schema") or {}).get("auditLoginOnly")))
        menus = (rich.get("schema") or {}).get("menus", {}).get("admin") or []
        self.assertTrue(any(m.get("key") == "audit_logs" for m in menus))
        gate = rich.get("gate") or {}
        self.assertIn("audit_log", (gate.get("flow_api") or {}))

        yml = _patch_thesis_yml("thesis:\n  domain: DOM-LIBRARY\n", "DOM-LIBRARY", rich)
        self.assertIn("audit-log-enabled: true", yml)
        self.assertNotIn("audit-log-login-only: true", yml)

        sql = domain_sql(
            "DOM-LIBRARY",
            "thesis_lib",
            capabilities=caps,
            proposal_text="图书借还；支持操作日志与审计查询。",
        )
        n = normalize_sql(sql)
        self.assertIn("sys_audit_log", n)

        login_only = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "archetype": "ARCH-FLOW",
            },
            "系统提供登录日志查询。",
        )
        self.assertIn(AUDIT_LOG_CAP, login_only.get("capabilities") or [])
        self.assertTrue(bool((login_only.get("schema") or {}).get("auditLoginOnly")))
        yml2 = _patch_thesis_yml(
            "thesis:\n  domain: DOM-LIBRARY\n", "DOM-LIBRARY", login_only
        )
        self.assertIn("audit-log-login-only: true", yml2)

    def test_unmounted_sql_has_no_audit_table(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "archetype": "ARCH-FLOW",
            },
            "图书借还催还管理。",
        )
        sql = domain_sql(
            "DOM-LIBRARY",
            "thesis_lib",
            capabilities=plain.get("capabilities") or [],
            proposal_text="图书借还催还管理。",
        )
        self.assertNotIn("sys_audit_log", normalize_sql(sql))

    def test_baseline_files_and_hooks(self) -> None:
        store = (
            BASELINE
            / "backend/src/main/java/com/thesis/capability/AuditLogStore.java"
        )
        ctrl = (
            BASELINE
            / "backend/src/main/java/com/thesis/controller/AuditLogController.java"
        )
        fe = BASELINE / "frontend/src/views/admin/AuditLogsAdmin.vue"
        self.assertTrue(store.is_file())
        self.assertTrue(ctrl.is_file())
        self.assertTrue(fe.is_file())
        stext = store.read_text(encoding="utf-8")
        self.assertIn("record", stext)
        self.assertIn("loginOnly", stext)
        self.assertIn("/api/admin/audit-logs", ctrl.read_text(encoding="utf-8"))

        auth = (
            BASELINE / "backend/src/main/java/com/thesis/controller/AuthController.java"
        ).read_text(encoding="utf-8")
        self.assertIn('AuditLogStore.record', auth)
        self.assertIn('"login"', auth)

        ticket = (
            BASELINE
            / "backend/src/main/java/com/thesis/controller/TicketController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("ticket_approve", ticket)
        self.assertIn("ticket_reject", ticket)

        users = (
            BASELINE
            / "backend/src/main/java/com/thesis/controller/UsersAdminController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("user_update", users)

        router = (BASELINE / "frontend/src/router/index.js").read_text(encoding="utf-8")
        self.assertIn("withAuditLogRoutes", router)
        self.assertIn("AuditLogsAdmin", router)


if __name__ == "__main__":
    unittest.main()
