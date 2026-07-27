"""泳道 E · C-14：时间银行 timebank + DOM-TIMEBANK。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES, resolve_accept
from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept, build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.timebank import TIMEBANK_CAP
from app.bake.menu_routes import shell_kind
from app.bake.schema.templates import SCHEMA_BUILDERS

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "samples" / "时间银行预设开题"
BASELINE = ROOT / "skeletons" / "baseline"


class TimebankC14Tests(unittest.TestCase):
    def test_capability_and_domain(self) -> None:
        self.assertIn("timebank", CAPABILITIES)
        self.assertEqual(CAPABILITIES["timebank"]["status"], "implemented")
        self.assertIn("DOM-TIMEBANK", DOMAINS)
        caps = DOMAIN_CAPABILITIES["DOM-TIMEBANK"]
        self.assertIn(TIMEBANK_CAP, caps)
        self.assertIn("ticket_flow", caps)
        self.assertIn("archive", caps)
        self.assertNotIn("quota", caps)
        self.assertNotIn("wallet", caps)
        self.assertNotIn("points", caps)
        self.assertIn("DOM-TIMEBANK", SCHEMA_BUILDERS)

    def test_match(self) -> None:
        got = match_text(
            "基于 Spring Boot 的社区时间银行志愿时长账户存取核销管理系统的设计与实现。"
            "主要功能：服务事项、时长账户余额、流水台账、核销申请审核。"
        )
        self.assertEqual(got.domain, "DOM-TIMEBANK", f"hits={got.hits[:12]}")

    def test_neighbors(self) -> None:
        cases = [
            ("社区时间银行志愿时长账户存取核销", "DOM-TIMEBANK", "DOM-LABOR"),
            ("劳动教育志愿时长认定审批", "DOM-LABOR", "DOM-TIMEBANK"),
            ("社团志愿活动报名管理系统", "DOM-ACTIVITY", "DOM-TIMEBANK"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")
                self.assertNotEqual(got.domain, avoid)

    def test_schema_and_shell(self) -> None:
        schema = build_domain_schema("社区时间银行志愿时长账户管理系统", "DOM-TIMEBANK")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        self.assertEqual(shell_kind(DOMAIN_CAPABILITIES["DOM-TIMEBANK"]), "archive_ticket")
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowQty"))
        spec = attach_accept(
            {
                "domain": "DOM-TIMEBANK",
                "title": "社区时间银行志愿时长账户管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-TIMEBANK"]),
                "archetype": "ARCH-FLOW",
            },
            "时长账户余额；流水；核销申请审核。",
        )
        sch = spec.get("schema") or {}
        user_keys = {m.get("key") for m in (sch.get("menus") or {}).get("user") or []}
        admin_keys = {m.get("key") for m in (sch.get("menus") or {}).get("admin") or []}
        self.assertIn("tb_account", user_keys)
        self.assertIn("tb_ledger", user_keys)
        self.assertIn("tb_accounts", admin_keys)
        self.assertIn("tb_ledger_admin", admin_keys)
        self.assertIn(TIMEBANK_CAP, spec.get("capabilities") or [])

    def test_sql_yml_accept(self) -> None:
        sql = domain_sql(
            "DOM-TIMEBANK",
            "t_tb",
            title="社区时间银行志愿时长账户管理系统",
            proposal_text="时间银行时长账户核销",
        )
        for t in ("tb_service", "tb_account", "tb_ledger", "tb_redeem"):
            self.assertIn(t, sql)
        spec = attach_accept(
            {
                "domain": "DOM-TIMEBANK",
                "title": "社区时间银行志愿时长账户管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-TIMEBANK"]),
                "archetype": "ARCH-FLOW",
            },
            "时间银行",
        )
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-TIMEBANK", spec)
        self.assertIn("timebank-enabled: true", yml)
        self.assertIn("timebank-redeem-on-approve: true", yml)
        self.assertIn("enable-ticket: true", yml)
        d = resolve_accept(
            list(DOMAIN_CAPABILITIES["DOM-TIMEBANK"]),
            "时长账户；流水加减；核销审核。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-FLOW"],
            domain="DOM-TIMEBANK",
            primary_archetype="ARCH-FLOW",
        )
        self.assertEqual(d["accept"], "full", d)

    def test_runtime_files(self) -> None:
        self.assertTrue(
            (BASELINE / "backend/src/main/java/com/thesis/service/TimebankStore.java").is_file()
        )
        self.assertTrue(
            (BASELINE / "backend/src/main/java/com/thesis/controller/TimebankController.java").is_file()
        )
        self.assertTrue((BASELINE / "frontend/src/views/TimebankAccount.vue").is_file())
        self.assertTrue((BASELINE / "frontend/src/views/admin/TimebankAccountsAdmin.vue").is_file())
        ticket = (
            BASELINE / "backend/src/main/java/com/thesis/capability/TicketStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("configureTimebankRedeem", ticket)
        self.assertIn("debitForTicketApprove", ticket)

    def test_sample(self) -> None:
        path = SAMPLES / "C-14-DOM-TIMEBANK-社区时间银行志愿时长账户存取核销系统.txt"
        self.assertTrue(path.is_file(), path)


if __name__ == "__main__":
    unittest.main()
