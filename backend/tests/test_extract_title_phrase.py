"""题名抽取：通用规则，不靠单题特判。"""

from __future__ import annotations

import unittest

from app.bake.catalog import extract_title
from app.services.upload_cluster import guess_role


def _opening(topic: str, *, lit_other: str) -> str:
    return (
        f"毕业设计(论文)开题报告\n"
        f"1 选题的意义和研究现状\n"
        f"1.1 选题的意义\n"
        f"因此打造一套“{topic}”显得尤为迫切。设计并实现{topic}具有现实意义。\n"
        f"1.2 国内外研究现状\n"
        f"某作者设计并实现了{lit_other}[6]；他人又以SpringBoot构建系统。\n"
        f"2 研究内容\n"
        f"本系统主要实现用户登录与核心业务。\n"
    )


class ExtractTitlePhraseTests(unittest.TestCase):
    def test_quoted_topic_beats_literature_system(self):
        title = extract_title(
            _opening("方木健身用品电商平台", lit_other="面向特定场景的健身管理平台")
        )
        self.assertEqual(title, "方木健身用品电商平台")
        self.assertNotIn("了面向", title)
        self.assertNotIn("面向特定场景", title)

    def test_library_and_dorm_not_poisoned_by_lit(self):
        for topic, lit in (
            ("校园图书借阅管理系统", "通用档案信息管理平台"),
            ("学生宿舍报修服务平台", "物业综合维修管理系统"),
        ):
            with self.subTest(topic=topic):
                title = extract_title(_opening(topic, lit_other=lit))
                self.assertEqual(title, topic)
                self.assertNotEqual(title, lit)

    def test_explicit_title_line_wins(self):
        body = (
            "毕业设计（论文）任务书\n"
            "设计题目:智慧停车场预约管理系统的设计与实现\n"
            "1.本课题目的\n"
            "设计并实现一个面向特定场景的健身管理平台[1]。\n"
        )
        self.assertIn("智慧停车场", extract_title(body))

    def test_full_line_design_and_implement(self):
        body = (
            "开题报告\n"
            "基于SpringBoot的社区团购管理系统的设计与实现\n"
            "一、选题背景\n"
            "国内外研究现状\n"
            "有人设计并实现了外卖配送平台[3]。\n"
        )
        self.assertEqual(
            extract_title(body), "基于SpringBoot的社区团购管理系统的设计与实现"
        )

    def test_filename_taskbook_role(self):
        text = "毕业设计（论文）任务书\n" + ("设计并实现一个图书管理系统。" * 40)
        self.assertEqual(guess_role("方木-任务书.docx", text), "taskbook")
        self.assertEqual(guess_role("方木-开题报告.docx", text), "proposal")


if __name__ == "__main__":
    unittest.main()
