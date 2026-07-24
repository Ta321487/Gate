# -*- coding: utf-8 -*-
"""archive_log 扫词复用 keyword_mentioned；域词硬分流回归。"""

from __future__ import annotations

import unittest

from app.bake.catalog import match_text
from app.bake.features.archive_log import scan_archive_log
from app.bake.proposal_lexicon import keyword_mentioned


class ArchiveLogScanTests(unittest.TestCase):
    def test_negation_excludes_checkin(self) -> None:
        self.assertFalse(scan_archive_log("预约接种；不含健康打卡主流程。"))
        self.assertFalse(scan_archive_log("挂号占坑；不以健康打卡为主。"))
        self.assertFalse(keyword_mentioned("非传染病晨检。", "晨检"))
        self.assertFalse(keyword_mentioned("非传染病晨检。", "传染病"))

    def test_positive_checkin_still_hits(self) -> None:
        self.assertTrue(scan_archive_log("每日健康打卡与体温登记。"))
        self.assertTrue(scan_archive_log("献血者健康筛查打卡后异常上报。"))
        self.assertTrue(scan_archive_log("矫正对象定位打卡与异常上报。"))
        self.assertTrue(
            keyword_mentioned("主要功能为物资领用，非公卫上报。", "物资领用")
        )


class MatchBatchRegressionTests(unittest.TestCase):
    def test_dorm_hygiene_not_event(self) -> None:
        m = match_text(
            "题目：宿舍卫生检查与整改工单系统\n"
            "主要功能：宿管发起卫生检查问题，学生整改申请与审核闭环；非传染病晨检。"
        )
        self.assertEqual(m.domain, "DOM-DORM")
        self.assertEqual(m.archetype, "ARCH-FLOW")

    def test_cold_chain_to_asset(self) -> None:
        m = match_text(
            "题目：冷链食品仓储温湿度与出入库系统\n"
            "主要功能：冷库货品台账、出入库登记、温湿度预警与盘点；主线为仓储库存。"
        )
        self.assertEqual(m.domain, "DOM-ASSET")
        self.assertIn(m.archetype, ("ARCH-STOCK", "ARCH-FLOW"))

    def test_vaccine_reserve_no_alog_scan(self) -> None:
        text = (
            "题目：社区疫苗接种预约与提醒系统\n"
            "主要功能：居民预约接种时段、约满不可再约、接种点公告；不含健康打卡主流程。"
        )
        m = match_text(text)
        self.assertEqual(m.archetype, "ARCH-RESERVE")
        self.assertFalse(scan_archive_log(text))

    def test_blood_screen_to_event(self) -> None:
        m = match_text(
            "题目：献血车流动献血点现场筛查登记系统\n"
            "主要功能：献血者现场建档、健康筛查打卡、不合格转上报观察；不做血液库存进销存。"
        )
        self.assertEqual(m.domain, "DOM-EVENT")
        self.assertEqual(m.archetype, "ARCH-FLOW")


if __name__ == "__main__":
    unittest.main()
