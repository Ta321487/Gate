# -*- coding: utf-8 -*-
"""ACTIVITY↔CLUB：题名含「社团」不得一律改年审；报名主路径保 ACTIVITY。"""

from __future__ import annotations

import unittest

from app.bake.catalog import match_text


class ActivityClubTitleOverrideTests(unittest.TestCase):
    def test_club_volunteer_signup_stays_activity(self) -> None:
        m = match_text(
            "社团志愿活动报名管理系统",
            "社团志愿活动报名管理系统.txt",
        )
        self.assertEqual(m.domain, "DOM-ACTIVITY", m.hits[:12])

    def test_campus_activity_canary_title(self) -> None:
        m = match_text("校园活动报名管理系统", "校园活动报名管理系统.txt")
        self.assertEqual(m.domain, "DOM-ACTIVITY", m.hits[:12])

    def test_club_register_annual_review_stays_club(self) -> None:
        m = match_text(
            "学生社团注册成立与年审材料审批",
            "学生社团注册成立与年审材料审批.txt",
        )
        self.assertEqual(m.domain, "DOM-CLUB", m.hits[:12])

    def test_club_manage_title_with_signup_body_keeps_club(self) -> None:
        """题名主写社团管理时，正文活动报名不抢 ACTIVITY。"""
        body = (
            "学生社团管理系统的设计与实现。\n"
            "支持社团注册与年审材料审批；社团也可发布活动报名作为附属。"
        )
        m = match_text(body, "学生社团管理系统.txt")
        self.assertEqual(m.domain, "DOM-CLUB", m.hits[:12])


if __name__ == "__main__":
    unittest.main()
