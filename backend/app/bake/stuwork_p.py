"""学工预设 P-12～P-16；P-20/P-21 床位；P-22 查寝签到。"""

from __future__ import annotations

from app.bake.stuwork_meta import STUWORK_META

STUWORK_CASES: list[tuple[str, str, str, str]] = [
    (m["pid"], m["phrase"], m["domain"], m["title"]) for m in STUWORK_META
]

BED_CASES: list[tuple[str, str, str, str]] = [
    ("P-20", "新生宿舍床位在线选择分配", "DOM-BED", "高校宿舍床位分配与调宿管理系统"),
    ("P-21", "学生宿舍调宿退宿申请审批", "DOM-BED", "学生宿舍调宿退宿申请审批系统"),
]

CHECKIN_CASES: list[tuple[str, str, str, str]] = [
    ("P-22", "宿舍查寝归寝签到缺勤记录", "DOM-CHECKIN", "高校宿舍查寝归寝签到管理系统"),
]

STUWORK_BED_SKELETON: list[tuple[str, str, str, str]] = []
