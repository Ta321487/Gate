"""开题场景扫描（单一真源）。

硬原则
------
1. **开题 / 任务书等材料为准**：不改写开题去迁就工厂模板。
2. **工厂跟场景走**：壳文案、资料页身份、岗位别名、能力挂载均扫「题名 + 开题正文」。
3. **壳与资料页同判定**：同一 ``DOM-*`` 的校园/企业/社区分支必须调用本模块，禁止各写一套 hint。
4. **开题未写清时用域默认**：默认档写在各 builder / ``PROFILE_FIELDS_BY_DOMAIN``，不是臆造开题。
5. **业务角色优先于背景装饰**：例如 CRM 正文里的「学院孵化」不压过「销售/客户跟进」企业档。

扫词不是全文复述开题措辞，而是选场景分支；场景定了，文案与身份字段必须一致。
"""

from __future__ import annotations

from typing import Literal

# 与历史 shells 导出名兼容（builders / profile 经本模块或 shells 再导出使用）
CAMPUS_HINTS = ("学生", "班级", "班主任", "大学生", "校园", "学工", "高校", "学校", "校内")
COMMUNITY_HINTS = ("社区", "网格", "养老", "复工", "流调", "居民", "小区")

ATTEND_CAMPUS_HINTS = ("学生", "班级", "班主任", "大学生", "校园", "学工")
EVENT_CAMPUS_HINTS = ("晨午检", "因病缺课", "校园", "班级", "学生", "学校", "高校")
RECRUIT_CAMPUS_HINTS = ("校园", "校招", "高校", "毕业生", "大学生", "双选会", "就业")
RECRUIT_ENTERPRISE_HINTS = ("企业", "公司", "人事", "人力资源", "HR")
CRM_ENTERPRISE_HINTS = ("业务员", "销售", "客户经理", "客户跟进", "中小企业", "线索", "意向客户")
CRM_CAMPUS_EXTRA = ("校园创业", "创业孵化", "学生团队")
PARCEL_COMMUNITY_HINTS = ("社区", "小区", "菜鸟", "丰巢", "代收点")
PARCEL_CAMPUS_HINTS = ("校园", "高校", "学校", "学生")
MEETING_CAMPUS_NOUNS = (
    "座位",
    "占座",
    "选座",
    "自习室",
    "研习室",
    "研讨室",
    "琴房",
    "体育场",
    "体育馆",
    "图书馆",
    "实验室",
    "实训室",
)
LOST_ADOPT_HINTS = ("领养", "待领养", "领养站")
IT_ENTERPRISE_HINTS = ("企业", "公司", "办公", "员工", "运维工单")

Scene = Literal[
    "campus",
    "enterprise",
    "community",
    "commercial",
    "adopt",
    "default",
]

# 须与壳文案 / 资料页同时跟开题分支的域（预防针清单）
SCENE_BRANCH_DOMAINS = frozenset(
    {
        "DOM-CRM",
        "DOM-ASSET",
        "DOM-ATTEND",
        "DOM-EVENT",
        "DOM-RECRUIT",
        "DOM-PARCEL",
        "DOM-MEETING",
        "DOM-PARKING",
        "DOM-IT",
        "DOM-LOST",
        "DOM-FOOD",
        "DOM-SHOP",
        "DOM-HOSPITAL",
        "DOM-SALON",
    }
)


def copy_scan_text(title: str, proposal_text: str = "") -> str:
    """题名 + 开题正文（同 staff_posts / attach_accept 扫材料）。"""
    return f"{title or ''}\n{proposal_text or ''}"


def scan_has(text: str, hints: tuple[str, ...]) -> bool:
    return any(k in (text or "") for k in hints)


def is_campus_general(text: str) -> bool:
    return scan_has(text, CAMPUS_HINTS) or scan_has(text, ("院系", "教职工", "学号"))


def scene_crm(text: str) -> Scene:
    """默认企业销售；仅无销售口径且明确校园师生/创业团队时 campus。"""
    if scan_has(text, CRM_ENTERPRISE_HINTS):
        return "enterprise"
    if is_campus_general(text) or scan_has(text, CRM_CAMPUS_EXTRA):
        return "campus"
    return "enterprise"


def scene_asset(text: str) -> Scene:
    if is_campus_general(text) or scan_has(text, ("院系", "教职工")):
        return "campus"
    return "enterprise"


def scene_attend(text: str) -> Scene:
    if scan_has(text, ATTEND_CAMPUS_HINTS):
        return "campus"
    return "enterprise"


def scene_event(text: str) -> Scene:
    if scan_has(text, EVENT_CAMPUS_HINTS):
        return "campus"
    if scan_has(text, COMMUNITY_HINTS):
        return "community"
    return "default"


def scene_recruit(text: str) -> Scene:
    campus = scan_has(text, RECRUIT_CAMPUS_HINTS)
    enterprise = scan_has(text, RECRUIT_ENTERPRISE_HINTS)
    if campus:
        return "campus"
    if enterprise:
        return "enterprise"
    return "campus"  # 默认校招（与 builder 一致）


def scene_parcel(text: str) -> Scene:
    if scan_has(text, PARCEL_COMMUNITY_HINTS) and not scan_has(text, PARCEL_CAMPUS_HINTS):
        return "community"
    return "campus"


def scene_meeting(text: str) -> Scene:
    if any(k in text for k in MEETING_CAMPUS_NOUNS) or is_campus_general(text):
        return "campus"
    return "enterprise"


def scene_parking(text: str) -> Scene:
    if scan_has(text, CAMPUS_HINTS):
        return "campus"
    return "commercial"


def scene_it(text: str) -> Scene:
    if is_campus_general(text):
        return "campus"
    if scan_has(text, IT_ENTERPRISE_HINTS):
        return "enterprise"
    return "campus"


def scene_lost(text: str) -> Scene:
    if any(k in text for k in LOST_ADOPT_HINTS):
        return "adopt"
    if is_campus_general(text):
        return "campus"
    return "community"


def scene_for(
    domain: str,
    title: str = "",
    proposal_text: str = "",
) -> Scene:
    """域级场景 id：壳文案与 profileFields 必须读同一结果。"""
    t = copy_scan_text(title, proposal_text)
    if domain == "DOM-CRM":
        return scene_crm(t)
    if domain == "DOM-ASSET":
        return scene_asset(t)
    if domain == "DOM-ATTEND":
        return scene_attend(t)
    if domain == "DOM-EVENT":
        return scene_event(t)
    if domain == "DOM-RECRUIT":
        return scene_recruit(t)
    if domain == "DOM-PARCEL":
        return scene_parcel(t)
    if domain == "DOM-MEETING":
        return scene_meeting(t)
    if domain == "DOM-PARKING":
        return scene_parking(t)
    if domain == "DOM-IT":
        return scene_it(t)
    if domain == "DOM-LOST":
        return scene_lost(t)
    return "default"
