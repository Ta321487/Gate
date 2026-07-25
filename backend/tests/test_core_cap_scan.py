"""开题扫词挂 recommend / time_conflict / 借阅逾期：只增不减。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_sql import domain_sql
from app.bake.features.core_cap_scan import (
    scan_loan_deadline,
    scan_recommend,
    scan_time_conflict,
)


class CoreCapScanTests(unittest.TestCase):
    def test_scan_positive_and_negation(self) -> None:
        self.assertTrue(scan_recommend("门户展示猜你喜欢与热度推荐。"))
        self.assertFalse(scan_recommend("本期不实现猜你喜欢。"))
        self.assertFalse(scan_recommend("推荐使用 Spring Boot 开发。"))  # 裸「推荐」不够

        self.assertTrue(scan_time_conflict("报名时做时间冲突检测，避免课表冲突。"))
        self.assertFalse(scan_time_conflict("本期不实现时间冲突检测。"))
        self.assertFalse(scan_time_conflict("系统支持审核与办结。"))

        self.assertTrue(scan_loan_deadline("支持逾期催还与逾期罚款。"))
        self.assertFalse(scan_loan_deadline("本期不实现逾期催还。"))
        # 申报窗口里的「逾期」不得当成借阅逾期
        self.assertFalse(scan_loan_deadline("各项目设置申报截止日期，逾期不可申请。"))

    def test_shop_no_mount_without_signals(self) -> None:
        caps = list(DOMAIN_CAPABILITIES["DOM-SHOP"])
        self.assertNotIn("recommend", caps)
        self.assertNotIn("time_conflict", caps)
        self.assertNotIn("deadline", caps)
        spec = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "校园二手商城",
                "capabilities": caps,
                "features": [],
            },
            "学生浏览商品、下单与评价。",
        )
        out = spec.get("capabilities") or []
        self.assertNotIn("recommend", out)
        self.assertNotIn("time_conflict", out)
        self.assertNotIn("deadline", out)

    def test_shop_mounts_recommend_when_scanned(self) -> None:
        body = "商城首页提供猜你喜欢与相关推荐，便于发现好物。"
        spec = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "校园二手商城",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
                "features": [],
            },
            body,
        )
        self.assertIn("recommend", spec.get("capabilities") or [])
        labels = (spec.get("schema") or {}).get("labels") or {}
        self.assertEqual(labels.get("recommendSectionTitle"), "猜你喜欢")
        feat = {f.get("name") for f in (spec.get("features") or []) if isinstance(f, dict)}
        self.assertIn("猜你喜欢", feat)

    def test_meeting_mounts_time_conflict(self) -> None:
        """预约域默认无 time_conflict；开题写到才挂，并补起止时间字段。"""
        caps = list(DOMAIN_CAPABILITIES["DOM-MEETING"])
        self.assertNotIn("time_conflict", caps)
        # MEETING 是 slot_reserve，无 ticket_flow → 扫到也不挂
        body = "支持时间冲突检测，避免同一人重复占用。"
        spec_no = attach_accept(
            {
                "domain": "DOM-MEETING",
                "title": "会议室预约",
                "capabilities": caps,
                "features": [],
            },
            body,
        )
        self.assertNotIn("time_conflict", spec_no.get("capabilities") or [])

        # 物资领用：有 archive+ticket_flow，扫到可挂
        asset_caps = list(DOMAIN_CAPABILITIES["DOM-ASSET"])
        self.assertNotIn("time_conflict", asset_caps)
        spec = attach_accept(
            {
                "domain": "DOM-ASSET",
                "title": "物资领用系统",
                "capabilities": asset_caps,
                "features": [],
            },
            body,
        )
        self.assertIn("time_conflict", spec.get("capabilities") or [])
        arch = ((spec.get("schema") or {}).get("entities") or {}).get("archive") or {}
        keys = {f.get("key") for f in (arch.get("fields") or []) if isinstance(f, dict)}
        self.assertIn("startAt", keys)
        self.assertIn("endAt", keys)

        sql = domain_sql(
            "DOM-ASSET",
            "thesis_test",
            title="物资领用系统",
            proposal_text=body,
        )
        # 档案表应有起止列
        self.assertIn("start_at", sql)
        self.assertIn("end_at", sql)

    def test_asset_mounts_loan_deadline(self) -> None:
        body = "领用后支持逾期催还与逾期罚款提醒。"
        caps = list(DOMAIN_CAPABILITIES["DOM-ASSET"])
        self.assertNotIn("deadline", caps)
        spec = attach_accept(
            {
                "domain": "DOM-ASSET",
                "title": "物资领用系统",
                "capabilities": caps,
                "features": [],
            },
            body,
        )
        self.assertIn("deadline", spec.get("capabilities") or [])
        admin = ((spec.get("schema") or {}).get("menus") or {}).get("admin") or []
        self.assertTrue(any(m.get("key") == "deadline" for m in admin if isinstance(m, dict)))
        ticket = ((spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("pickLoanPeriod"))

        sql = domain_sql(
            "DOM-ASSET",
            "thesis_test",
            title="物资领用系统",
            proposal_text=body,
            ticket_flags=ticket,
        )
        self.assertIn("due_at", sql)
        self.assertIn("fine_yuan", sql)

    def test_domain_defaults_survive_empty_proposal(self) -> None:
        """图书域默认 recommend+deadline；活动域默认 time_conflict：空开题不剥。"""
        lib = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书借阅",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "features": [],
            },
            "借还图书。",
        )
        self.assertIn("recommend", lib.get("capabilities") or [])
        self.assertIn("deadline", lib.get("capabilities") or [])

        act = attach_accept(
            {
                "domain": "DOM-ACTIVITY",
                "title": "活动报名",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-ACTIVITY"]),
                "features": [],
            },
            "学生报名活动。",
        )
        self.assertIn("time_conflict", act.get("capabilities") or [])

    def test_apply_deadline_text_does_not_add_loan_shell(self) -> None:
        body = "各项目设置申报截止日期，逾期不可申请。"
        spec = attach_accept(
            {
                "domain": "DOM-FUND",
                "title": "学生资助",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-FUND"]),
                "features": [],
            },
            body,
        )
        self.assertNotIn("deadline", spec.get("capabilities") or [])
        sql = domain_sql(
            "DOM-FUND",
            "thesis_test",
            title="学生资助",
            proposal_text=body,
        )
        # 申报截止列可以有；借阅罚金壳不能有
        self.assertIn("apply_deadline_at", sql)
        chunk = sql.split("fund_apply")[1].split("CREATE TABLE")[0]
        self.assertNotIn("fine_yuan", chunk)


if __name__ == "__main__":
    unittest.main()
