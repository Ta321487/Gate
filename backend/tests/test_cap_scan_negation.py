# -*- coding: utf-8 -*-
"""能力扫词：非本期否定不得误挂。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.features.dm import scan_dm
from app.bake.features.e_sign import scan_e_sign
from app.bake.features.exam import scan_exam
from app.bake.features.seat_select import scan_seat_select
from app.bake.features.stock_io import scan_stock_io
from app.bake.features.survey import scan_survey
from app.bake.features.timebank import scan_timebank
from app.services.proposal import strip_non_dev_sections

ROOT = Path(__file__).resolve().parents[2]


def _body(rel: str) -> str:
    return strip_non_dev_sections((ROOT / rel).read_text(encoding="utf-8"))


class CapScanNegationTests(unittest.TestCase):
    def test_oos_electronic_sign_not_esign(self) -> None:
        t = _body("data/samples/申请预设开题/P-01-DOM-SEAL-学校行政印章使用申请审批系统.txt")
        self.assertIn("电子签", t)
        self.assertFalse(scan_e_sign(t))

    def test_oos_survey_not_on_exam_sample(self) -> None:
        t = _body("data/samples/能力预设开题/C-01-DOM-EXAM-高校在线考试与题库管理系统.txt")
        self.assertFalse(scan_survey(t))

    def test_oos_exam_not_on_survey_sample(self) -> None:
        t = _body("data/samples/能力预设开题/C-03-DOM-SURVEY-高校学生满意度问卷调查系统.txt")
        self.assertTrue(scan_survey(t))
        self.assertFalse(scan_exam(t))

    def test_oos_dm_not_on_forum(self) -> None:
        t = _body("data/samples/域开题样例近五年/26-DOM-FORUM-校园论坛发帖回帖管理系统.txt")
        self.assertFalse(scan_dm(t))

    def test_oos_seat_not_on_media(self) -> None:
        t = _body("data/samples/域开题样例近五年/24-DOM-MEDIA-校园影视资源点播管理系统.txt")
        self.assertFalse(scan_seat_select(t))

    def test_oos_timebank_not_on_labor(self) -> None:
        t = _body("data/samples/学工预设开题/P-13-DOM-LABOR-高校劳动教育与志愿时长认定系统.txt")
        self.assertFalse(scan_timebank(t))

    def test_oos_stock_not_on_generic(self) -> None:
        t = _body("data/samples/域开题样例近五年/99-DOM-GENERIC-实验室试剂基础信息台账系统.txt")
        self.assertFalse(scan_stock_io(t))

    def test_recruit_wenjuan_delivery_not_survey(self) -> None:
        t = _body("data/samples/域开题样例近五年/07-DOM-RECRUIT-高校校园招聘岗位投递管理系统.txt")
        self.assertFalse(scan_survey(t))


if __name__ == "__main__":
    unittest.main()
