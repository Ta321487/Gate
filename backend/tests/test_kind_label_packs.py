"""预约壳 / 内容域标签包：builder 眉标来自 kind_label_packs。"""

from __future__ import annotations

import unittest

from app.bake.schema.builders_content import _blog_schema, _media_schema, _music_schema
from app.bake.schema.builders_slot import _hospital_schema, _meeting_schema, _salon_schema
from app.bake.schema.kind_label_packs import (
    hospital_label_pack,
    meeting_label_pack,
    salon_label_pack,
)


class KindLabelPackTests(unittest.TestCase):
    def test_salon_kinds_eyebrow(self) -> None:
        cases = [
            ("校园私教健身预约系统", "fitness", "健身预约"),
            ("心理咨询预约平台", "counsel", "心理咨询预约"),
            ("驾校练车预约", "drive", "练车预约"),
            ("美发门店预约", "salon", "服务预约"),
        ]
        for title, kind, brow in cases:
            with self.subTest(kind=kind):
                self.assertEqual(salon_label_pack(kind)["eyebrow"], brow)
                schema = _salon_schema(title, "")
                self.assertEqual(schema["labels"]["authEyebrow"], brow)

    def test_hospital_kinds_eyebrow(self) -> None:
        cases = [
            ("宠物医院挂号预约", "pet", "宠物挂号"),
            ("疫苗接种预约系统", "vaccine", "疫苗预约"),
            ("校医院门诊挂号", "clinic", "门诊挂号"),
        ]
        for title, kind, brow in cases:
            with self.subTest(kind=kind):
                self.assertEqual(hospital_label_pack(kind)["eyebrow"], brow)
                schema = _hospital_schema(title, "")
                self.assertEqual(schema["labels"]["authEyebrow"], brow)

    def test_meeting_kinds_noun(self) -> None:
        cases = [
            ("自习室预约管理系统", "study", "自习室"),
            ("琴房预约系统", "piano", "琴房"),
            ("会议室预约系统", "meeting", "会议室"),
        ]
        for title, kind, noun in cases:
            with self.subTest(kind=kind):
                self.assertEqual(meeting_label_pack(kind)["noun"], noun)
                schema = _meeting_schema(title, "")
                self.assertEqual(schema["labels"]["authEyebrow"], f"{noun}预约")

    def test_content_eyebrows(self) -> None:
        self.assertEqual(
            _media_schema("在线点播课视频平台", "")["labels"]["authEyebrow"],
            "点播课",
        )
        self.assertEqual(
            _music_schema("KTV 点歌台系统", "")["labels"]["authEyebrow"],
            "点歌台",
        )
        self.assertEqual(
            _blog_schema("记者站稿件发布系统", "")["labels"]["authEyebrow"],
            "记者站稿件",
        )


if __name__ == "__main__":
    unittest.main()
