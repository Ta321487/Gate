"""dm 一对一私信：开题扫描、域默认、SQL 注入、Spec 挂载。"""

from __future__ import annotations

import unittest

from app.bake.capabilities import resolve_accept, scan_out_of_scope
from app.bake.domain_schema import attach_accept
from app.bake.engine import count_create_tables, domain_sql
from app.bake.features.dm import (
    DM_CAP,
    apply_dm_to_spec,
    merge_dm_capabilities,
    scan_dm,
)
from tests.helpers.normalize import normalize_sql


class DmCapabilityTests(unittest.TestCase):
    def test_scan_dm_keywords(self) -> None:
        self.assertTrue(scan_dm("支持用户实时私信与回帖审核"))
        self.assertTrue(scan_dm("会员之间可一对一私聊"))
        self.assertTrue(scan_dm("即时私信功能"))
        self.assertFalse(scan_dm("仅公告与跟帖，无其它互动"))

    def test_dating_default_dm_forum_opt_in(self) -> None:
        dating = merge_dm_capabilities(
            ["archive", "ticket_flow", "content", "org_users"],
            "",
            domain="DOM-DATING",
        )
        self.assertIn(DM_CAP, dating)
        forum = merge_dm_capabilities(
            ["archive", "ticket_flow", "content", "org_users"],
            "发帖回帖与版主审核",
            domain="DOM-FORUM",
        )
        self.assertNotIn(DM_CAP, forum)
        forum_on = merge_dm_capabilities(
            ["archive", "ticket_flow", "content", "org_users"],
            "支持用户实时私信与回帖审核",
            domain="DOM-FORUM",
        )
        self.assertIn(DM_CAP, forum_on)

    def test_library_without_keyword_no_dm(self) -> None:
        caps = merge_dm_capabilities(
            ["archive", "ticket_flow", "content"],
            "图书借阅与逾期提醒",
            domain="DOM-LIBRARY",
        )
        self.assertNotIn(DM_CAP, caps)

    def test_proposal_adds_dm_on_library(self) -> None:
        caps = merge_dm_capabilities(
            ["archive", "ticket_flow", "content"],
            "读者可与馆员一对一私信咨询",
            domain="DOM-LIBRARY",
        )
        self.assertIn(DM_CAP, caps)

    def test_realtime_dm_no_longer_overreach(self) -> None:
        hits = scan_out_of_scope("三、主要功能\n\n1. 实时私信\n2. 发帖回帖\n")
        self.assertNotIn("实时私信", hits)

    def test_websocket_im_still_overreach(self) -> None:
        hits = scan_out_of_scope("三、主要功能\n\n1. 接入环信即时通讯 SDK\n")
        self.assertTrue(any("IM" in h or "云服务" in h for h in hits))

    def test_apply_spec_menus_and_strip_oos(self) -> None:
        spec = apply_dm_to_spec(
            {
                "domain": "DOM-FORUM",
                "capabilities": ["archive", "ticket_flow", "content", "org_users"],
                "entities": ["Post", "Category", "Reply", "Notice"],
                "features": [{"name": "实时私信", "status": "out_of_mvp"}],
                "out_of_mvp": ["实时私信", "无限深度树形嵌套引擎"],
                "schema": {"menus": {"admin": [], "user": []}, "labels": {}},
                "gate": {},
            },
            "支持用户实时私信与回帖",
        )
        self.assertIn(DM_CAP, spec["capabilities"])
        self.assertIn("Dm", spec["entities"])
        self.assertNotIn("实时私信", spec["out_of_mvp"])
        user_keys = [m["key"] for m in spec["schema"]["menus"]["user"]]
        self.assertIn("dm", user_keys)
        names = {f.get("name") for f in spec["features"] if isinstance(f, dict)}
        self.assertIn("一对一私信", names)
        self.assertNotIn("实时私信", names)

    def test_attach_accept_forum_full(self) -> None:
        text = (
            "本科毕业设计开题报告\n\n"
            "题目：校园论坛系统设计与实现\n\n"
            "三、主要功能\n\n"
            "1. 发帖回帖审核\n"
            "2. 用户实时私信\n"
            "3. 公告管理\n"
        )
        spec = attach_accept(
            {
                "title": "校园论坛系统",
                "domain": "DOM-FORUM",
                "archetype": "ARCH-FLOW",
                "archetypes": ["ARCH-FLOW"],
                "capabilities": [
                    "archive",
                    "ticket_flow",
                    "content",
                    "org_users",
                ],
                "entities": ["Post", "Category", "Reply", "Notice"],
                "features": [],
                "schema": {"version": 1, "title": "t", "capabilities": []},
            },
            text,
        )
        self.assertIn(DM_CAP, spec["capabilities"])
        self.assertEqual(spec.get("accept"), "full")
        self.assertNotIn("实时私信", spec.get("out_of_mvp") or [])

    def test_forum_sql_injects_dm_when_scanned(self) -> None:
        sql = domain_sql(
            "DOM-FORUM",
            "thesis_test",
            proposal_text="校园论坛发帖回帖，并支持用户实时私信。",
        )
        self.assertIn("sys_dm_message", sql)
        self.assertIn("user2", sql)
        n = count_create_tables(sql)
        self.assertLessEqual(n, 15)
        self.assertGreaterEqual(n, 6)

    def test_forum_sql_no_dm_by_default(self) -> None:
        sql = normalize_sql(domain_sql("DOM-FORUM", "thesis_test"))
        self.assertNotIn("sys_dm_message", sql)

    def test_library_sql_no_dm_table(self) -> None:
        sql = normalize_sql(domain_sql("DOM-LIBRARY", "thesis_test"))
        self.assertNotIn("sys_dm_message", sql)

    def test_resolve_accept_with_dm_cap(self) -> None:
        d = resolve_accept(
            ["archive", "ticket_flow", "content", "org_users", "dm"],
            "主要功能含一对一私信",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-FLOW"],
            domain="DOM-FORUM",
            primary_archetype="ARCH-FLOW",
        )
        self.assertEqual(d["accept"], "full")


if __name__ == "__main__":
    unittest.main()
