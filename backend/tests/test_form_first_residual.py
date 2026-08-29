"""市面开题软缺口：PARCEL 本人件、GRADE 课感、EVENT/BED 混写、排课诚实双显。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import (
    compose_out_of_mvp,
    resolve_accept,
    scan_out_of_scope,
    scan_soft_out_of_mvp,
)
from app.bake.domain_schema import build_domain_schema
from app.bake.profile_fields import profile_fields_for
from app.bake.proposal_packs import PACKS
from app.bake.scene_scan import bed_transfer_primary, event_self_report

_REPO = Path(__file__).resolve().parents[2]
_MY_TICKETS = (
    _REPO
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "views"
    / "user"
    / "MyTickets.vue"
)
_OWNER_MATCH = (
    _REPO
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "utils"
    / "profileRoomMatch.js"
)


class FormFirstResidualTests(unittest.TestCase):
    def test_event_self_report_true_morning_check(self) -> None:
        self.assertTrue(
            event_self_report("校园晨午检管理系统", "学生（或家长代填）每日健康打卡")
        )
        self.assertTrue(event_self_report("学生晨午检打卡", "班主任确认"))
        self.assertTrue(event_self_report("健康打卡管理系统", "每日打卡与异常上报"))

    def test_event_self_report_false_grid_ledger(self) -> None:
        self.assertFalse(
            event_self_report("社区网格员走访台账", "网格员维护对象档案并上门随访")
        )

    def test_bed_transfer_primary_true(self) -> None:
        self.assertTrue(
            bed_transfer_primary("学生宿舍调宿退宿申请审批", "调宿退宿申请与审批")
        )

    def test_bed_transfer_primary_false_select(self) -> None:
        self.assertFalse(
            bed_transfer_primary("新生选房床位分配", "新生选房与床位分配")
        )

    def test_bed_mixed_prefers_transfer_form_first(self) -> None:
        """选房+调宿混写 → 仍填单优先（软缺口）。"""
        self.assertTrue(
            bed_transfer_primary("宿舍选房与调宿管理系统", "支持新生选房与在校生调宿退宿")
        )

    def test_grade_schema_form_first(self) -> None:
        schema = build_domain_schema("高校成绩管理系统", "DOM-GRADE")
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("applyFromList"))
        self.assertTrue(ticket.get("filterByOwnerToken"))
        self.assertEqual(ticket.get("ownerTokenSource"), "studentNo")
        self.assertFalse(ticket.get("ownerTokenStrict"))
        user_menus = (schema.get("menus") or {}).get("user") or []
        self.assertEqual(user_menus[0].get("key"), "my_tickets")
        archive = next(m for m in user_menus if m.get("key") == "archive")
        self.assertEqual(archive.get("label"), "课程说明")
        notice = str((schema.get("seeds") or {}).get("noticeBody") or "")
        labels_blob = " ".join(
            str(x)
            for x in (
                notice,
                (schema.get("labels") or {}).get("myTicketsPageLead"),
                (schema.get("labels") or {}).get("myTicketsEmpty"),
            )
            if x
        )
        self.assertTrue(
            ("本人" in notice or "本人" in labels_blob or "我的成绩" in labels_blob),
            msg=f"grade notice/body should emphasize 本人/我的成绩: {notice!r}",
        )
        self.assertIn("本人相关课程", notice)

    def test_grade_pack_main_path_本人(self) -> None:
        grade = next(p for p in PACKS if p.get("id") == "grade")
        self.assertIn("本人", str(grade.get("main_path") or ""))

    def test_carpass_profile_has_plate_no(self) -> None:
        fields = profile_fields_for("DOM-CARPASS")
        keys = {f.get("key") for f in fields if isinstance(f, dict)}
        self.assertIn("plateNo", keys)

    def test_parcel_schema_owner_phone_and_claim(self) -> None:
        schema = build_domain_schema("校园快递驿站管理系统", "DOM-PARCEL")
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("requireClaimCode"))
        self.assertTrue(ticket.get("applyFromList"))
        self.assertTrue(ticket.get("filterByOwnerToken"))
        self.assertEqual(ticket.get("ownerTokenSource"), "phone")
        self.assertTrue(ticket.get("ownerTokenStrict"))
        self.assertEqual(ticket.get("remarkLabel"), "取件码")
        user_menus = (schema.get("menus") or {}).get("user") or []
        self.assertEqual(user_menus[0].get("key"), "my_tickets")
        archive = next(m for m in user_menus if m.get("key") == "archive")
        self.assertEqual(archive.get("label"), "本人件")

    def test_parcel_claim_filter_documented_in_frontend(self) -> None:
        if not _MY_TICKETS.is_file():
            self.skipTest("baseline MyTickets.vue not present")
        src = _MY_TICKETS.read_text(encoding="utf-8")
        self.assertIn("requireClaimCode", src)
        self.assertIn("claimFilteredArchiveItems", src)
        self.assertIn("filterByOwnerToken", src)
        self.assertIn("本人待取件", src)
        if _OWNER_MATCH.is_file():
            util = _OWNER_MATCH.read_text(encoding="utf-8")
            self.assertIn("filterArchiveByOwnerToken", util)

    def test_event_campus_self_report_form_first(self) -> None:
        schema = build_domain_schema(
            "校园晨午检管理系统",
            "DOM-EVENT",
            proposal_text="学生（或家长代填）每日健康打卡",
        )
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("applyFromList"))
        user_menus = (schema.get("menus") or {}).get("user") or []
        self.assertEqual(user_menus[0].get("key"), "my_tickets")
        self.assertIn("打卡", str(user_menus[0].get("label") or ""))

    def test_bed_mixed_schema_form_first(self) -> None:
        schema = build_domain_schema(
            "宿舍选房与调宿管理系统",
            "DOM-BED",
            proposal_text="支持新生选房与在校生调宿退宿",
        )
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("applyFromList"))
        user_menus = (schema.get("menus") or {}).get("user") or []
        self.assertEqual(user_menus[0].get("key"), "my_tickets")

    def test_course_schedule_soft_dual_not_reject(self) -> None:
        """开题写智能排课 → 本期不做双显，不 reject。"""
        body = (
            "三、主要功能\n"
            "1. 课程检索与选课申请\n"
            "2. 智能排课引擎自动生成课表\n"
            "3. 时间冲突检测\n"
        )
        soft = scan_soft_out_of_mvp(body)
        self.assertIn("智能排课", soft)
        self.assertNotIn("智能排课", scan_out_of_scope(body))
        oos = compose_out_of_mvp("DOM-COURSE", body, scanned_signals=[])
        self.assertIn("智能排课", oos)
        decision = resolve_accept(
            ["archive", "ticket_flow", "content", "org_users"],
            body,
            has_baseline_runtime=True,
            domain="DOM-COURSE",
            archetypes=["ARCH-CRUD"],
        )
        self.assertEqual(decision["accept"], "full")
        # 智能排课走 soft 双显，不进 reject 信号
        self.assertNotIn("智能排课", decision.get("out_of_mvp_signals") or [])


if __name__ == "__main__":
    unittest.main()
