"""匹配确认：身份场景 / 主路径入口手改（复用 scene_scan，不另写扫词）。"""

from __future__ import annotations

import unittest

from app.bake.catalog import build_spec
from app.bake.domain_schema import build_domain_schema, ensure_spec_schema
from app.bake.match_path_axes import (
    match_path_override_scope,
    recommend_entry,
    resolve_match_path,
)
from app.bake.scene_scan import event_self_report, scene_for


class MatchPathAxesTests(unittest.TestCase):
    def test_event_weak_default_needs_ack(self) -> None:
        path = resolve_match_path(
            "DOM-EVENT",
            "社区网格员走访台账",
            "网格员维护对象档案并上门随访",
        )
        self.assertEqual(path["recommended_entry"], "caseload")
        self.assertTrue(path["entry_weak"])
        self.assertTrue(path["needs_path_ack"])
        self.assertTrue(any(o["id"] == "self_report" for o in path["entry_options"]))

    def test_event_self_report_scan_no_ack(self) -> None:
        path = resolve_match_path(
            "DOM-EVENT",
            "校园晨午检管理系统",
            "学生（或家长代填）每日健康打卡",
        )
        self.assertEqual(path["recommended_entry"], "self_report")
        self.assertFalse(path["entry_weak"])
        self.assertFalse(path["needs_path_ack"])

    def test_manual_entry_clears_needs_ack(self) -> None:
        path = resolve_match_path(
            "DOM-EVENT",
            "社区网格员走访台账",
            "网格员维护对象档案",
            entry="self_report",
        )
        self.assertEqual(path["entry"], "self_report")
        self.assertEqual(path["overrides"].get("entry"), "self_report")
        self.assertFalse(path["needs_path_ack"])
        self.assertTrue(path["deviant"])

    def test_override_scope_drives_scene_for_and_entry(self) -> None:
        title = "社区网格员走访台账"
        body = "网格员维护对象档案"
        self.assertFalse(event_self_report(title, body))
        with match_path_override_scope("DOM-EVENT", scene="campus", entry="self_report"):
            self.assertEqual(scene_for("DOM-EVENT", title, body), "campus")
            self.assertTrue(event_self_report(title, body))
        self.assertFalse(event_self_report(title, body))

    def test_build_spec_schema_follows_entry_override(self) -> None:
        path = resolve_match_path(
            "DOM-EVENT",
            "社区网格员走访台账",
            "网格员维护对象档案",
            entry="self_report",
        )
        spec = build_spec(
            title="社区网格员走访台账",
            archetype="ARCH-FOLLOWUP",
            domain="DOM-EVENT",
            theme="ink",
            llm_enabled=False,
            match_mode="manual_override",
            confidence=0.5,
            proposal={"excerpt": "网格员维护对象档案"},
            match_path=path,
        )
        ticket = ((spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("applyFromList"))
        menus = ((spec.get("schema") or {}).get("menus") or {}).get("user") or []
        self.assertEqual(menus[0].get("key"), "my_tickets")
        self.assertEqual(spec.get("match_path", {}).get("entry"), "self_report")

    def test_recommend_entry_intern_bind(self) -> None:
        self.assertEqual(
            recommend_entry(
                "DOM-INTERN",
                "学生实习管理系统",
                "一人一岗绑定实习单位与岗位后提交周报",
            ),
            "post_bound",
        )

    def test_library_has_no_entry_axis(self) -> None:
        path = resolve_match_path("DOM-LIBRARY", "图书借阅", "借还管理")
        self.assertEqual(path["entry_options"], [])
        self.assertFalse(path["needs_path_ack"])

    def test_ensure_spec_schema_honors_entry_override(self) -> None:
        """一键生成前重编壳不得丢掉运营台手改的入口。"""
        title = "社区网格员走访台账"
        body = "网格员维护对象档案"
        path = resolve_match_path(
            "DOM-EVENT", title, body, entry="self_report"
        )
        stale = build_domain_schema(title, "DOM-EVENT", proposal_text=body)
        ticket_stale = (stale.get("entities") or {}).get("ticket") or {}
        self.assertFalse(ticket_stale.get("applyFromList"))
        out = ensure_spec_schema(
            {
                "domain": "DOM-EVENT",
                "title": title,
                "proposal_text": body,
                "schema": stale,
                "archetype": "ARCH-FOLLOWUP",
                "match_path": path,
            }
        )
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("applyFromList"))
        menus = ((out.get("schema") or {}).get("menus") or {}).get("user") or []
        self.assertEqual(menus[0].get("key"), "my_tickets")


if __name__ == "__main__":
    unittest.main()
