"""单据列表列可见性契约：避免 bake 后才发现空「开始/结束」等错位列。

与基线 ``domainSchema.js`` 中 ticketShows* 规则对齐；改 UI 规则时同步改本测试。
"""

from __future__ import annotations

import re
import unittest

from app.bake.domain_skin import traits_for_domain
from app.bake.engine_sql import domain_sql
from app.bake.schema.templates import SCHEMA_BUILDERS
from app.bake.sql.fragments import TICKET_DOMAIN_COLUMNS


def _archive_fields(schema: dict) -> list[dict]:
    arch = (schema.get("entities") or {}).get("archive") or {}
    return [f for f in (arch.get("fields") or []) if isinstance(f, dict)]


def _ticket(schema: dict) -> dict:
    return (schema.get("entities") or {}).get("ticket") or {}


def shows_schedule(schema: dict) -> bool:
    ticket = _ticket(schema)
    if ticket.get("pickDateRange"):
        return True
    keys = {f.get("key") for f in _archive_fields(schema)}
    return "startAt" in keys or "endAt" in keys


def shows_follow(domain: str) -> bool:
    return bool(traits_for_domain(domain).get("followUp") or traits_for_domain(domain).get("crm"))


def shows_type(schema: dict) -> bool:
    fields = _archive_fields(schema)
    if not fields:
        return True
    keys = {f.get("key") for f in fields}
    return "category" in keys or "itemKind" in keys


def shows_location(schema: dict) -> bool:
    fields = _archive_fields(schema)
    if not fields:
        return True
    isbn = next((f for f in fields if f.get("key") == "isbn"), None)
    if not isbn or isbn.get("type") in ("hidden", "richtext"):
        return False
    return True


class TicketUiColumnContractTests(unittest.TestCase):
    def test_schedule_only_when_schema_has_times(self) -> None:
        """无时段字段的 ticket 域禁止「应当显示开始/结束」（防空列回归）。"""
        must_hide: list[str] = []
        must_show: list[str] = []
        for domain, builder in sorted(SCHEMA_BUILDERS.items()):
            schema = builder("测试课题")
            if "ticket_flow" not in (schema.get("capabilities") or []):
                continue
            if shows_schedule(schema):
                must_show.append(domain)
            else:
                must_hide.append(domain)
        self.assertIn("DOM-ACTIVITY", must_show)
        self.assertIn("DOM-COURSE", must_show)
        for d in (
            "DOM-EVENT",
            "DOM-CRM",
            "DOM-ATTEND",
            "DOM-LIBRARY",
            "DOM-ASSET",
            "DOM-LOST",
            "DOM-FORUM",
            "DOM-DORM",
        ):
            self.assertIn(d, must_hide, f"{d} 不应显示空开始/结束列")

    def test_crm_trait_matches_contact_channel(self) -> None:
        for domain, builder in sorted(SCHEMA_BUILDERS.items()):
            schema = builder("测试课题")
            if "ticket_flow" not in (schema.get("capabilities") or []):
                continue
            with self.subTest(domain=domain):
                follow = shows_follow(domain)
                has_label = bool(_ticket(schema).get("contactChannelLabel"))
                self.assertEqual(
                    follow,
                    has_label,
                    "crm trait 须与 ticket.contactChannelLabel 同在/同无",
                )
                sql_has = "contact_channel" in TICKET_DOMAIN_COLUMNS.get(domain, [])
                self.assertEqual(
                    follow,
                    sql_has,
                    "crm trait 须与 SQL contact_channel 列同在/同无",
                )

    def test_forum_hides_richtext_location_col(self) -> None:
        schema = SCHEMA_BUILDERS["DOM-FORUM"]("测试课题")
        self.assertTrue(shows_type(schema))
        self.assertFalse(shows_location(schema))

    def test_standalone_domains_have_priority_sql_and_no_archive(self) -> None:
        """宿舍/物业/IT 报修：SQL 有 priority，无 archive；UI 应走独立报修列。"""
        for domain in ("DOM-DORM", "DOM-PROPERTY", "DOM-IT"):
            with self.subTest(domain=domain):
                schema = SCHEMA_BUILDERS[domain]("测试课题")
                caps = schema.get("capabilities") or []
                self.assertIn("ticket_flow", caps)
                self.assertNotIn("archive", caps)
                sql_cols = TICKET_DOMAIN_COLUMNS.get(domain, [])
                self.assertIn("priority", sql_cols)
                self.assertIn("contact_phone", sql_cols)
                self.assertFalse(shows_schedule(schema))
                sql = domain_sql(domain, "thesis_test")
                self.assertIn("priority", sql)
                self.assertIn("contact_phone", sql)

    def test_schedule_domains_seed_start_at(self) -> None:
        """有 startAt 的档案域，默认种子须写入非空 start_at（避免列表有列无值）。"""
        for domain, builder in sorted(SCHEMA_BUILDERS.items()):
            schema = builder("测试课题")
            fields = _archive_fields(schema)
            if not any(f.get("key") == "startAt" for f in fields):
                continue
            with self.subTest(domain=domain):
                sql = domain_sql(domain, "thesis_test")
                # 字面日期 '20xx-..' 或查寝窗 DATE_ADD(CURDATE(), ...)
                self.assertRegex(
                    sql,
                    re.compile(
                        r"INSERT IGNORE INTO \w+.*start_at.*VALUES[\s\S]*?"
                        r"('20\d{2}-\d{2}-\d{2}|DATE_ADD\s*\(\s*CURDATE\s*\()",
                        re.IGNORECASE,
                    ),
                    f"{domain} 有 startAt 字段但种子未写入 start_at",
                )

    def test_baseline_ticket_records_gates_schedule(self) -> None:
        """基线记录页须用 showScheduleCols，禁止无条件画开始/结束。"""
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]  # graduate_factory_v3
        vue = (
            root
            / "skeletons"
            / "baseline"
            / "frontend"
            / "src"
            / "views"
            / "admin"
            / "TicketRecordsAdmin.vue"
        )
        text = vue.read_text(encoding="utf-8")
        self.assertIn("showScheduleCols", text)
        self.assertIn("ticketShowsScheduleCols", text)
        self.assertIn("showPriorityCols", text)
        self.assertIn("ticketShowsPriorityCols", text)
        # 禁止恢复「永远画出开始/结束」
        self.assertNotRegex(
            text,
            r'<el-table-column\s+prop="startAt"\s+label="开始"',
        )


if __name__ == "__main__":
    unittest.main()
