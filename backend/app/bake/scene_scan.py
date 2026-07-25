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
# 社区网格/公卫排查口径。勿把光杆「养老」算进来：养老机构走 institution。
# 「复工」不进社区：企业复工健康监测走 enterprise（见 EVENT_ENTERPRISE_HINTS）。
COMMUNITY_HINTS = ("社区", "网格", "流调", "居民", "小区")
# 机构端照护（养老院等）：用强词，避免「老人/护士/院内」误伤慢病随访、院感等题
EVENT_INSTITUTION_HINTS = (
    "养老机构",
    "养老院",
    "护理院",
    "敬老院",
    "照护员",
    "入住老人",
    "重点老人",
)
# 企业员工健康监测/复工（压过 community 的「复工」误伤）
EVENT_ENTERPRISE_HINTS = ("企业员工", "复工", "班组", "园区办公", "EHS", "同班次")

ATTEND_CAMPUS_HINTS = ("学生", "班级", "班主任", "大学生", "校园", "学工")
EVENT_CAMPUS_HINTS = ("晨午检", "因病缺课", "校园", "班级", "学生", "学校", "高校")
RECRUIT_CAMPUS_HINTS = ("校园", "校招", "高校", "毕业生", "大学生", "双选会", "就业")
RECRUIT_ENTERPRISE_HINTS = ("企业", "公司", "人事", "人力资源", "HR")
DATING_CAMPUS_HINTS = ("校园", "高校", "大学生", "同学", "校内", "学工", "院系", "学校")
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
FOOD_CAMPUS_HINTS = ("食堂", "校园", "档口", "学子", "高校", "学校")
SHOP_CAMPUS_HINTS = ("校园", "校内", "二手", "学校", "高校")
HOSPITAL_PET_HINTS = ("宠物", "宠医", "爱宠", "猫狗", "犬猫")
# 资助：校园奖助学金默认；企业员工福利/补助走 enterprise
FUND_CAMPUS_HINTS = (
    "学生资助",
    "奖学金",
    "助学金",
    "困难补助",
    "奖助",
    "学工",
    "高校",
    "校园",
    "学生",
)
FUND_ENTERPRISE_HINTS = ("员工福利", "企业补助", "人事福利", "职工补助", "内部福利", "HR福利")
# 成绩：教务默认；企业内训/培训考核走 enterprise
GRADE_ENTERPRISE_HINTS = ("内训", "培训成绩", "员工考核", "培训结业", "企业培训", "岗位认证")
# 实习：校就业办默认；企业带教周报走 enterprise
INTERN_ENTERPRISE_HINTS = ("企业带教", "带教导师", "校招实习生", "入职实习", "企业实习生", "导师审阅周报")
# 实验室准入：校园默认；厂区/安环走 enterprise
LABSAFE_ENTERPRISE_HINTS = ("厂区", "安环", "企业实验室", "EHS准入", "产线实验室", "车间实验室")
# 物业：小区住户默认；校园物业/公寓走 campus
PROPERTY_CAMPUS_HINTS = ("校园物业", "学生公寓", "高校物业", "宿舍物业", "校园报修", "学校物业")
# 内容域：商业点播默认；校园媒资/院刊走 campus
CONTENT_CAMPUS_HINTS = ("校园", "高校", "学校", "院系", "学院", "学工", "大学生")
# 论坛：校园 BBS 默认；兴趣/小区社区走 community（有校园词仍 campus）
FORUM_COMMUNITY_HINTS = (
    "兴趣社区",
    "社区论坛",
    "居民论坛",
    "小区论坛",
    "同城论坛",
    "贴吧",
    "邻里互助",
)

Scene = Literal[
    "campus",
    "enterprise",
    "community",
    "commercial",
    "adopt",
    "institution",
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
        "DOM-DATING",
        "DOM-PARCEL",
        "DOM-MEETING",
        "DOM-PARKING",
        "DOM-IT",
        "DOM-LOST",
        "DOM-FOOD",
        "DOM-SHOP",
        "DOM-HOSPITAL",
        "DOM-SALON",
        "DOM-FUND",
        "DOM-GRADE",
        "DOM-INTERN",
        "DOM-LABSAFE",
        "DOM-PROPERTY",
        "DOM-MEDIA",
        "DOM-MUSIC",
        "DOM-BLOG",
        "DOM-FORUM",
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
    # 机构养老/照护：独立档，不用社区网格壳、也不用校园晨午检种子
    if scan_has(text, EVENT_INSTITUTION_HINTS):
        return "institution"
    # 企业复工/员工监测：先于 community，避免「复工」套网格壳
    if scan_has(text, EVENT_ENTERPRISE_HINTS) or (
        scan_has(text, ("企业", "公司")) and scan_has(text, ("员工", "健康监测", "健康打卡"))
    ):
        return "enterprise"
    if scan_has(text, COMMUNITY_HINTS):
        return "community"
    # 慢病随访/院感/献血等：default（公卫随访档，非校园种子）
    return "default"


def scene_recruit(text: str) -> Scene:
    campus = scan_has(text, RECRUIT_CAMPUS_HINTS)
    enterprise = scan_has(text, RECRUIT_ENTERPRISE_HINTS)
    if campus:
        return "campus"
    if enterprise:
        return "enterprise"
    return "campus"  # 默认校招（与 builder 一致）


def scene_dating(text: str) -> Scene:
    """校园交友 vs 社区相亲；未写清默认社区。"""
    if scan_has(text, DATING_CAMPUS_HINTS) or is_campus_general(text):
        return "campus"
    return "community"


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


def scene_food(text: str) -> Scene:
    if scan_has(text, FOOD_CAMPUS_HINTS):
        return "campus"
    return "commercial"


def scene_shop(text: str) -> Scene:
    if scan_has(text, SHOP_CAMPUS_HINTS):
        return "campus"
    return "commercial"


def scene_hospital(text: str) -> Scene:
    """门诊默认；宠物医院走 adopt（资料页宠主口径）。疫苗仍 default。"""
    if scan_has(text, HOSPITAL_PET_HINTS):
        return "adopt"
    return "default"


def scene_salon(text: str) -> Scene:
    """美发/健身均为商业门店身份；产品文案仍由 builder 本地扫词。"""
    return "commercial"


def scene_fund(text: str) -> Scene:
    """默认校园资助；开题写清员工福利/企业补助时 enterprise。"""
    if scan_has(text, FUND_ENTERPRISE_HINTS):
        return "enterprise"
    if scan_has(text, FUND_CAMPUS_HINTS) or is_campus_general(text):
        return "campus"
    return "campus"


def scene_grade(text: str) -> Scene:
    """默认教务成绩；内训/培训考核走 enterprise。"""
    if scan_has(text, GRADE_ENTERPRISE_HINTS):
        return "enterprise"
    return "campus"


def scene_intern(text: str) -> Scene:
    """默认校就业办周报；企业带教走 enterprise。"""
    if scan_has(text, INTERN_ENTERPRISE_HINTS):
        return "enterprise"
    return "campus"


def scene_labsafe(text: str) -> Scene:
    """默认校园实验室准入；厂区/安环走 enterprise。"""
    if scan_has(text, LABSAFE_ENTERPRISE_HINTS):
        return "enterprise"
    return "campus"


def scene_property(text: str) -> Scene:
    """默认小区物业；校园公寓/高校物业走 campus。"""
    if scan_has(text, PROPERTY_CAMPUS_HINTS) or (
        is_campus_general(text) and scan_has(text, ("物业", "报修", "公寓"))
    ):
        return "campus"
    return "community"


def scene_media(text: str) -> Scene:
    """默认商业点播；校园媒资走 campus。"""
    if scan_has(text, CONTENT_CAMPUS_HINTS):
        return "campus"
    return "commercial"


def scene_music(text: str) -> Scene:
    if scan_has(text, CONTENT_CAMPUS_HINTS):
        return "campus"
    return "commercial"


def scene_blog(text: str) -> Scene:
    if scan_has(text, CONTENT_CAMPUS_HINTS):
        return "campus"
    return "commercial"


def scene_forum(text: str) -> Scene:
    """默认校园论坛；开题写清兴趣/小区社区且无校园口径时 community。"""
    if is_campus_general(text) or scan_has(text, CONTENT_CAMPUS_HINTS):
        return "campus"
    if scan_has(text, FORUM_COMMUNITY_HINTS) or (
        scan_has(text, COMMUNITY_HINTS) and scan_has(text, ("论坛", "BBS", "发帖", "回帖", "贴吧"))
    ):
        return "community"
    return "campus"


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
    if domain == "DOM-DATING":
        return scene_dating(t)
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
    if domain == "DOM-FOOD":
        return scene_food(t)
    if domain == "DOM-SHOP":
        return scene_shop(t)
    if domain == "DOM-HOSPITAL":
        return scene_hospital(t)
    if domain == "DOM-SALON":
        return scene_salon(t)
    if domain == "DOM-FUND":
        return scene_fund(t)
    if domain == "DOM-GRADE":
        return scene_grade(t)
    if domain == "DOM-INTERN":
        return scene_intern(t)
    if domain == "DOM-LABSAFE":
        return scene_labsafe(t)
    if domain == "DOM-PROPERTY":
        return scene_property(t)
    if domain == "DOM-MEDIA":
        return scene_media(t)
    if domain == "DOM-MUSIC":
        return scene_music(t)
    if domain == "DOM-BLOG":
        return scene_blog(t)
    if domain == "DOM-FORUM":
        return scene_forum(t)
    return "default"
