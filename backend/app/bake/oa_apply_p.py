"""OA 申请预设 P-01～P-08；互选 P-09～P-11（C-05）。"""

from __future__ import annotations

OA_APPLY_CASES: list[tuple[str, str, str, str]] = [
    ("P-01", "行政印章使用申请审批", "DOM-SEAL", "学校行政印章使用申请审批系统"),
    ("P-02", "公务用车选车申请审批", "DOM-FLEET", "公务用车申请审批管理系统"),
    ("P-03", "在读成绩单在职证明开具申请审批", "DOM-CERT", "在读成绩单在职证明开具申请系统"),
    ("P-04", "横幅海报户外宣传方案审批", "DOM-PROMO", "横幅海报户外宣传审批管理系统"),
    ("P-05", "装修进场施工备案申请审批", "DOM-FITOUT", "装修进场施工备案审批系统"),
    ("P-06", "学籍异动转专业缓考申请审批", "DOM-ACAD", "学籍异动转专业缓考申请系统"),
    ("P-07", "出差加班申请审批与销结", "DOM-TRIP", "出差加班申请审批管理系统"),
    ("P-08", "经费差旅报销单填写与审批", "DOM-EXPENSE", "经费报销申请审批管理系统"),
]

MUTUAL_CASES: list[tuple[str, str, str, str]] = [
    ("P-09", "研究生导师双向选择志愿与确认", "DOM-MUTUAL-TUTOR", "研究生导师双向选择志愿与确认系统"),
    ("P-10", "毕业论文选题双选志愿与确认", "DOM-MUTUAL-TOPIC", "毕业论文选题双选志愿与确认系统"),
    ("P-11", "竞赛组队学习搭子意向匹配", "DOM-MUTUAL-TEAM", "竞赛组队学习搭子意向匹配系统"),
]

OA_MUTUAL_SKELETON: list[tuple[str, str, str]] = []
