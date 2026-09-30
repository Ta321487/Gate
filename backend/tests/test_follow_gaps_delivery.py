"""开题地图 §1.2 本组待补 → 已齐：查重/未跟进筛/退回次数 的交付闭环门禁。

已齐口径：管理端能管 + 用户端可产生数据（写库） + 三份骨架一致。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.ticket_policy import policy_preview
from app.bake.ticket_policy import collect

REPO = Path(__file__).resolve().parents[2]
MAP = REPO / "docs" / "opening-feature-delivery-map.md"
THE = "backend/src/main/java/com/thesis"
COPIES = {
    "baseline": REPO / "skeletons" / "baseline",
    "mybatis": REPO / "skeletons" / "overlays" / "persistence-mybatis",
    "jpa": REPO / "skeletons" / "overlays" / "persistence-jpa",
}
FE = REPO / "skeletons" / "baseline" / "frontend" / "src" / "views"


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


def _ticket_store(copy: str) -> str:
    return (COPIES[copy] / THE / "capability" / "TicketStore.java").read_text(encoding="utf-8")


def _sections(md: str, marker: str) -> str:
    """同名小节可能多组（§1.1/§1.2/...），取并集。"""
    parts = re.split(r"(?=#### 本组)", md)
    return "\n".join(p for p in parts if p.startswith(marker))


class FollowGapsDeliveryTests(unittest.TestCase):
    def test_bake_emits_stale_follow_days(self) -> None:
        """开题扫命中未跟进池 → 写 ticket-stale-follow-days（clamp 1..90）。"""
        out = _spec("DOM-CRM", "客户跟进管理系统", "支持长期未跟进客户列表筛选")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertEqual(int(ticket.get("staleFollowDays") or 0), 14)
        self.assertEqual(collect("DOM-CRM", out).get("STALE_FOLLOW_DAYS"), 14)
        # yml 已不承载单据键；策略值见 TicketPolicy（回显核对）
        self.assertIn("ticket-stale-follow-days: 14", policy_preview("DOM-CRM", out))
        self.assertNotIn("ticket-", _patch_thesis_yml("thesis:\n  title: x\n", "DOM-CRM", out))

    def test_store_flags_in_all_three_copies(self) -> None:
        for copy in COPIES:
            text = _ticket_store(copy)
            with self.subTest(copy=copy):
                self.assertIn("configureFollowOps", text)
                self.assertIn("static int staleFollowDays = 0;", text)
                self.assertIn("static boolean phoneDupCheck = false;", text)
                self.assertIn("dupPhoneOpenId", text)
                self.assertIn('"stale".equals(status)', text)
                self.assertIn('out.put("staleFollowDays"', text)
                self.assertIn("returnForRevise", text)
                self.assertIn("public static Map<String, Object> resubmit(", text)
                self.assertIn("reviseCountOf", text)

    def test_binder_wires_follow_ops(self) -> None:
        for copy in COPIES:
            text = (COPIES[copy] / THE / "config" / "DomainRuntimeBinder.java").read_text(encoding="utf-8")
            with self.subTest(copy=copy):
                self.assertIn("TicketPolicy.STALE_FOLLOW_DAYS", text)
                self.assertIn("ticketPhoneDupCheck", text)
                self.assertIn("TicketStore.configureFollowOps(", text)

    def test_revise_limit_enforced_with_db_counter(self) -> None:
        """次数记库（baseline 原生 SQL / mybatis mapper）且超限拒绝。"""
        base = _ticket_store("baseline")
        self.assertIn("revise_count=?", base)
        self.assertIn("used >= maxReviseTimes", base)
        self.assertIn("reviseCountOf(m) >= maxReviseTimes", base)
        mb = _ticket_store("mybatis")
        self.assertIn("mapper().updateReturnRevise", mb)
        mapper = (COPIES["mybatis"] / THE / "mapper" / "TicketMapper.java").read_text(encoding="utf-8")
        self.assertIn("updateReturnRevise", mapper)
        self.assertIn("selectOpenIdByPhone", mapper)
        xml = (COPIES["mybatis"] / "backend/src/main/resources/mapper/TicketMapper.xml").read_text(
            encoding="utf-8"
        )
        self.assertIn("statusStale", xml)
        self.assertIn("next_follow_at", xml)

    def test_controller_endpoints(self) -> None:
        text = (COPIES["baseline"] / THE / "controller" / "TicketController.java").read_text(encoding="utf-8")
        self.assertIn('@PostMapping("/{id}/return-revise")', text)
        self.assertIn('@PostMapping("/{id}/resubmit")', text)

    def test_frontend_wired(self) -> None:
        mine = (FE / "user" / "MyTickets.vue").read_text(encoding="utf-8")
        for needle in ("stalePoolHint", "phoneDupHint", "maxReviseHint", "resubmitTicket", "stalePoolLabel"):
            self.assertIn(needle, mine, f"MyTickets 缺 {needle}")
        admin = (FE / "admin" / "TicketsAdmin.vue").read_text(encoding="utf-8")
        for needle in ("returnRevise", "return-revise"):
            self.assertIn(needle, admin, f"TicketsAdmin 缺 {needle}")

    def test_map_rows_moved_to_done(self) -> None:
        md = MAP.read_text(encoding="utf-8")
        todo = _sections(md, "#### 本组待补")
        keys = (
            "phoneDupCheck",
            "staleFollowDays",
            "maxReviseTimes",
            "levelAffectsDeadline",
            "notifyDutyOnReport",
            "allowObjectionWindow",
            "objectionDays",
        )
        for key in keys:
            self.assertNotIn(key, todo, f"待补表仍有 {key}")
        done = _sections(md, "#### 本组本轮已齐")
        for key in keys:
            self.assertIn(key, done, f"已齐表缺 {key}")


class EventGapsDeliveryTests(unittest.TestCase):
    """第二批 4 键：等级时限 / 上报群发值班 / 公示异议窗口 / 成绩异议时限。"""

    def test_bake_emits_level_sla_keys(self) -> None:
        out = _spec("DOM-EVENT", "校园传染病防控晨检管理系统", "事件等级时限：高等级事件处理时限更短，按等级处理时限")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("levelAffectsDeadline"))
        self.assertEqual(int(ticket.get("levelSlaHighDays") or 0), 1)
        self.assertEqual(int(ticket.get("levelSlaMidDays") or 0), 3)
        self.assertEqual(int(ticket.get("levelSlaLowDays") or 0), 7)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-EVENT", out) + policy_preview("DOM-EVENT", out)
        self.assertIn("ticket-level-affects-deadline: true", yml)
        self.assertIn("ticket-level-sla-high-days: 1", yml)
        self.assertIn("ticket-level-sla-mid-days: 3", yml)
        self.assertIn("ticket-level-sla-low-days: 7", yml)

    def test_bake_emits_duty_notify_key(self) -> None:
        out = _spec("DOM-EVENT", "校园传染病防控晨检管理系统", "新上报一键通知值班，支持值班群发")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("notifyDutyOnReport"))
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-EVENT", out) + policy_preview("DOM-EVENT", out)
        self.assertIn("ticket-notify-duty-on-report: true", yml)

    def test_bake_emits_objection_keys(self) -> None:
        fund = _spec("DOM-FUND", "高校助学贷款与困难认定申请系统", "奖学金公示异议登记窗口：公示结束前可提交异议登记")
        fticket = ((fund.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(fticket.get("allowObjectionWindow"))
        self.assertEqual(int(fticket.get("objectionDays") or 0), 5)
        fyml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-FUND", fund) + policy_preview("DOM-FUND", fund)
        self.assertIn("ticket-allow-objection-window: true", fyml)
        self.assertIn("ticket-objection-days: 5", fyml)

        grade = _spec("DOM-GRADE", "企业内训成绩与岗位认证管理系统", "成绩异议申请时限：成绩发布后 N 日内可提交更正申请")
        gticket = ((grade.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertEqual(int(gticket.get("objectionDays") or 0), 7)
        gyml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-GRADE", grade) + policy_preview("DOM-GRADE", grade)
        self.assertIn("ticket-objection-days: 7", gyml)

    def test_optional_columns_injected_by_flag(self) -> None:
        from app.bake.sql.fragments import TICKET_OPTIONAL_COLUMNS, _ticket_flag_column_names

        cols = {n.lower() for n, _ in TICKET_OPTIONAL_COLUMNS}
        for col in ("objection_due_at", "objection_note", "objection_at"):
            self.assertIn(col, cols, f"TICKET_OPTIONAL_COLUMNS 缺 {col}")
        fund = _ticket_flag_column_names({"allowObjectionWindow": True, "objectionDays": 5})
        self.assertIn("objection_due_at", fund)
        grade = _ticket_flag_column_names({"objectionDays": 7})
        self.assertIn("objection_note", grade)

    def test_ticket_store_level_and_duty_in_all_copies(self) -> None:
        for copy in COPIES:
            text = _ticket_store(copy)
            with self.subTest(copy=copy):
                self.assertIn("public static void configureEventOps(", text)
                self.assertIn("static int levelSlaDays(Map<String, Object> m, int fallback)", text)
                self.assertIn("plusDays(levelSlaDays(m, loanDays()))", text)
                self.assertIn("levelSlaCsv()", text)
                self.assertIn("notifyDutyOnNewReport(id, username, t)", text)
                self.assertIn("StaffRosterStore.onDutyUsernames(", text)
                self.assertIn("import java.time.LocalDate;", text)

    def test_binder_wires_event_and_objection(self) -> None:
        for copy in COPIES:
            text = (COPIES[copy] / THE / "config" / "DomainRuntimeBinder.java").read_text(encoding="utf-8")
            with self.subTest(copy=copy):
                for needle in (
                    "TicketPolicy.LEVEL_AFFECTS_DEADLINE",
                    "TicketPolicy.NOTIFY_DUTY_ON_REPORT",
                    "TicketPolicy.ALLOW_OBJECTION_WINDOW",
                    "TicketPolicy.OBJECTION_DAYS",
                    "TicketStore.configureEventOps(",
                    "FundPublicityStore.configureObjection(",
                    "GradeScoreStore.configureObjectionDays(",
                ):
                    self.assertIn(needle, text, f"{copy} Binder 缺 {needle}")

    def test_fund_objection_window_writes_db(self) -> None:
        for copy in COPIES:
            text = (COPIES[copy] / THE / "service" / "FundPublicityStore.java").read_text(encoding="utf-8")
            with self.subTest(copy=copy):
                self.assertIn("public static void configureObjection(", text)
                self.assertIn("static java.sql.Date windowDue(", text)
                self.assertIn("SET objection_due_at=?", text)
                self.assertIn('m.put("objectionDueAt"', text)
                self.assertIn("public static Map<String, Object> submitObjection(", text)
                self.assertIn("SET objection_note=?, objection_at=NOW()", text)
                self.assertIn("异议登记窗口已于 ", text)
        ctrl = (COPIES["baseline"] / THE / "controller" / "FundPublicityController.java").read_text(encoding="utf-8")
        self.assertIn('@PostMapping("/{id}/objection")', ctrl)

    def test_grade_objection_entry_closed_after_window(self) -> None:
        for copy in COPIES:
            text = (COPIES[copy] / THE / "service" / "GradeScoreStore.java").read_text(encoding="utf-8")
            with self.subTest(copy=copy):
                self.assertIn("public static void configureObjectionDays(int days)", text)
                self.assertIn("objectionWindow(String username, long courseId)", text)
                self.assertIn("public static void assertObjectionOpen(String username, long courseId)", text)
                self.assertIn('out.put("objectionDays"', text)
                self.assertIn("import java.time.LocalDate;", text)
        ctrl = (COPIES["baseline"] / THE / "controller" / "GradeScoreController.java").read_text(encoding="utf-8")
        self.assertIn('@GetMapping("/objection-window")', ctrl)
        ticket_ctrl = (COPIES["baseline"] / THE / "controller" / "TicketController.java").read_text(encoding="utf-8")
        self.assertIn("GradeScoreStore.assertObjectionOpen(uid, itemId);", ticket_ctrl)

    def test_frontend_wired_for_event_and_objection(self) -> None:
        mine = (FE / "user" / "MyTickets.vue").read_text(encoding="utf-8")
        for needle in ("levelSlaHint", "levelSlaDays", "notifyDutyHint", "objectionWindowHint", "dutyNotified"):
            self.assertIn(needle, mine, f"MyTickets 缺 {needle}")
        admin = (FE / "admin" / "TicketsAdmin.vue").read_text(encoding="utf-8")
        for needle in ("levelSlaHint", "levelSlaText", "dutyNotifyOn", "notifyDutyHint"):
            self.assertIn(needle, admin, f"TicketsAdmin 缺 {needle}")
        fund_mine = (FE / "user" / "FundPublicity.vue").read_text(encoding="utf-8")
        for needle in ("objectionWindowLabel", "objectionNoteLabel", "/objection", "objectionClosed"):
            self.assertIn(needle, fund_mine, f"用户端公示页缺 {needle}")
        fund_admin = (FE / "admin" / "FundPublicityAdmin.vue").read_text(encoding="utf-8")
        for needle in ("objectionWindowLabel", "objectionDueAt", "objectionNote"):
            self.assertIn(needle, fund_admin, f"管理端公示页缺 {needle}")
        grade = (FE / "GradeScoresMine.vue").read_text(encoding="utf-8")
        for needle in ("objectionOpen", "objectionWindowLabel", "objectionWindowHint"):
            self.assertIn(needle, grade, f"成绩查询页缺 {needle}")

    def test_overlay_sync_tool_marks_idempotent(self) -> None:
        tool = (REPO / "tools" / "sync_objection_event_overlays.py").read_text(encoding="utf-8")
        self.assertIn("已同步", tool)
        self.assertIn("锚点命中", tool)
        for need in ("mb:fund-objection", "jp:grade-fields", "jp:ticket-due-standalone"):
            self.assertIn(need, tool)


if __name__ == "__main__":
    unittest.main()
