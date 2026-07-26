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
# 产品皮（与 scene 正交）：监测打卡 vs 应急事件上报
EVENT_MONITOR_HINTS = (
    "晨午检",
    "健康监测",
    "健康打卡",
    "健康随访",
    "随访管理",
    "因病缺课",
    "体征监测",
    "复工监测",
)
EVENT_INCIDENT_HINTS = (
    "应急上报",
    "应急处置",
    "公共卫生事件",
    "公卫事件",
    "疫情事件",
    "突发事件",
    "疫情上报",
    "事件应急",
    "应急管理",
    "隐患上报",
)
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
# 点餐只分两档：canteen（食堂/校内）| restaurant（社会餐饮，不按菜系开皮）
FOOD_RESTAURANT_TITLE_HINTS = ("餐厅", "外卖", "餐饮", "饭店", "美食", "小吃", "快餐", "茶饮")
# 商城 campus 须有校园口径；裸「二手」≠校园（社区二手走零售档，不按行业开皮）
SHOP_CAMPUS_HINTS = ("校园", "校内", "学校", "高校")
# 商城只分两档：campus（校内二手）| retail（社会售卖，含鲜花/数码/同城二手等）
SHOP_RETAIL_TITLE_HINTS = ("销售", "商城", "电商", "网店", "店铺", "零售", "售卖", "购物")
PARKING_COMMERCIAL_TITLE_HINTS = ("商场", "园区", "写字楼", "小区", "商业", "地下车库", "停车场")
HOSPITAL_PET_HINTS = ("宠物", "宠医", "爱宠", "猫狗", "犬猫")
# 产品皮（样例开题 / builder 共用）：pet | vaccine | clinic
HOSPITAL_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (HOSPITAL_PET_HINTS, "pet"),
    (("疫苗", "HPV", "接种预约", "接种点", "接种"), "vaccine"),
    (("医院", "门诊", "挂号", "校医"), "clinic"),
]
SALON_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (("健身", "私教", "瑜伽", "游泳私教", "器械课", "团课"), "fitness"),
    (("美发", "理发", "造型", "美甲", "美容"), "salon"),
]
MEETING_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (("自习室", "研习室", "研讨室"), "study"),
    (("琴房", "排练", "舞蹈"), "piano"),
    (("体育场", "体育馆", "球馆", "羽毛球场", "篮球场", "足球场", "游泳"), "gym"),
    (("座位", "占座", "选座"), "seat"),
    (("工位", "实验室", "实训室"), "lab"),
    (("会议",), "meeting"),
]
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


def title_then_body_hit(
    title: str,
    body: str,
    rules: list[tuple[tuple[str, ...], object]],
) -> object | None:
    """产品/场景分支扫词：先题名后正文。

    样例开题常把多变体写进同一段 ``scene``/``problem``（如「美发 / 健身」），
    合并扫描会让无关变体关键词压过题名。规则按优先级排列，每条为 (hints, value)。
    """
    for text in ((title or "").strip(), (body or "").strip()):
        if not text:
            continue
        for hints, value in rules:
            if scan_has(text, hints):
                return value
    return None


def is_campus_general(text: str) -> bool:
    return scan_has(text, CAMPUS_HINTS) or scan_has(text, ("院系", "教职工", "学号"))


def scene_crm(text: str) -> Scene:
    """默认企业销售；仅无销售口径且明确校园师生/创业团队时 campus。"""
    if scan_has(text, CRM_ENTERPRISE_HINTS):
        return "enterprise"
    if is_campus_general(text) or scan_has(text, CRM_CAMPUS_EXTRA):
        return "campus"
    return "enterprise"


def scene_crm_parts(title: str, body: str = "") -> Scene:
    """题名优先：避免 problem「中小企业或校园创业」把校园创业题洗成销售档。

    题名里的「客户跟进」是产品词，不能单独压过「校园创业」场景口径。
    """
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, CRM_CAMPUS_EXTRA) or (
        is_campus_general(t)
        and not scan_has(t, ("中小企业", "销售", "业务员", "客户经理"))
    ):
        return "campus"
    if scan_has(t, CRM_ENTERPRISE_HINTS):
        return "enterprise"
    return scene_crm(copy_scan_text(t, b))


def scene_asset(text: str) -> Scene:
    if is_campus_general(text) or scan_has(text, ("院系", "教职工")):
        return "campus"
    return "enterprise"


def scene_asset_parts(title: str, body: str = "") -> Scene:
    """题名优先：企业物资题不被正文「院系/教职工」对比句洗成校园档。"""
    t = (title or "").strip()
    b = (body or "").strip()
    if is_campus_general(t) or scan_has(t, ("院系", "教职工", "高校", "校园")):
        return "campus"
    if scan_has(t, ("企业", "公司", "仓储")):
        return "enterprise"
    return scene_asset(copy_scan_text(t, b))


def scene_attend(text: str) -> Scene:
    if scan_has(text, ATTEND_CAMPUS_HINTS):
        return "campus"
    return "enterprise"


def scene_attend_parts(title: str, body: str = "") -> Scene:
    """题名优先：企业请假题不被正文「学生请假」对比句洗成学工档。"""
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, ATTEND_CAMPUS_HINTS):
        return "campus"
    if scan_has(t, ("企业", "员工", "公司", "人事")):
        return "enterprise"
    return scene_attend(copy_scan_text(t, b))


def scene_event(text: str) -> Scene:
    if scan_has(text, EVENT_INSTITUTION_HINTS):
        return "institution"
    if scan_has(text, EVENT_ENTERPRISE_HINTS) or (
        scan_has(text, ("企业", "公司")) and scan_has(text, ("员工", "健康监测", "健康打卡"))
    ):
        return "enterprise"
    has_campus = scan_has(text, EVENT_CAMPUS_HINTS)
    has_community = scan_has(text, COMMUNITY_HINTS)
    # 同段「社区或校园」双写：本段不确定，交给 title_then_body 下一段
    if has_campus and has_community:
        return "default"
    if has_community:
        return "community"
    if has_campus:
        return "campus"
    return "default"


def scene_event_parts(title: str, body: str = "") -> Scene:
    """题名优先：避免 problem「社区或校园」把社区题洗成晨午检。"""
    for text in ((title or "").strip(), (body or "").strip()):
        if not text:
            continue
        sc = scene_event(text)
        if sc != "default":
            return sc
    return "default"


def event_product_kind(title: str, body: str = "") -> str:
    """仅 ``monitor`` | ``incident``。

    - monitor：晨午检 / 健康监测 / 随访打卡（现网默认皮）
    - incident：应急上报 / 公共卫生事件（弱化每日打卡叙事）

    题名优先；正文「晨午检」对比句不得把应急题洗成 monitor。
    """
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, EVENT_MONITOR_HINTS):
        return "monitor"
    if scan_has(t, EVENT_INCIDENT_HINTS):
        return "incident"
    if scan_has(b, EVENT_MONITOR_HINTS) and not scan_has(b, EVENT_INCIDENT_HINTS):
        return "monitor"
    if scan_has(b, EVENT_INCIDENT_HINTS):
        return "incident"
    return "monitor"


def scene_recruit(text: str) -> Scene:
    campus = scan_has(text, RECRUIT_CAMPUS_HINTS)
    enterprise = scan_has(text, RECRUIT_ENTERPRISE_HINTS)
    if campus:
        return "campus"
    if enterprise:
        return "enterprise"
    return "campus"  # 默认校招（与 builder 一致）


def scene_recruit_parts(title: str, body: str = "") -> Scene:
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, RECRUIT_ENTERPRISE_HINTS) and not scan_has(t, RECRUIT_CAMPUS_HINTS):
        return "enterprise"
    if scan_has(t, RECRUIT_CAMPUS_HINTS):
        return "campus"
    return scene_recruit(copy_scan_text(t, b))


def scene_dating(text: str) -> Scene:
    """校园交友 vs 社区相亲；未写清默认社区。"""
    if scan_has(text, DATING_CAMPUS_HINTS) or is_campus_general(text):
        return "campus"
    return "community"


def scene_dating_parts(title: str, body: str = "") -> Scene:
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, DATING_CAMPUS_HINTS) or is_campus_general(t):
        return "campus"
    if scan_has(t, COMMUNITY_HINTS) or scan_has(t, ("相亲", "婚恋")):
        return "community"
    return scene_dating(copy_scan_text(t, b))


def scene_parcel(text: str) -> Scene:
    if scan_has(text, PARCEL_COMMUNITY_HINTS) and not scan_has(text, PARCEL_CAMPUS_HINTS):
        return "community"
    return "campus"


def scene_parcel_parts(title: str, body: str = "") -> Scene:
    """题名优先：小区驿站题不被正文「校园驿站」对比句洗成校园档。"""
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, PARCEL_CAMPUS_HINTS):
        return "campus"
    if scan_has(t, PARCEL_COMMUNITY_HINTS):
        return "community"
    return scene_parcel(copy_scan_text(t, b))


def scene_meeting(text: str) -> Scene:
    if any(k in text for k in MEETING_CAMPUS_NOUNS) or is_campus_general(text):
        return "campus"
    return "enterprise"


def scene_meeting_parts(title: str, body: str = "") -> Scene:
    """题名优先：避免正文样例里的琴房/自习室把企业会议室题洗成校园档。"""
    for text in ((title or "").strip(), (body or "").strip()):
        if not text:
            continue
        if any(k in text for k in MEETING_CAMPUS_NOUNS) or is_campus_general(text):
            return "campus"
        if scan_has(text, ("企业", "公司", "办公")) or "会议" in text:
            return "enterprise"
    return "enterprise"


def scene_parking(text: str) -> Scene:
    if scan_has(text, CAMPUS_HINTS):
        return "campus"
    return "commercial"


def scene_parking_parts(title: str, body: str = "") -> Scene:
    """题名优先：避免 problem「校园或园区」把商场/园区车场题洗成校园档。"""
    t = (title or "").strip()
    b = (body or "").strip()
    if is_campus_general(t) or scan_has(t, ("校园", "高校", "校内", "学校")):
        return "campus"
    if scan_has(t, PARKING_COMMERCIAL_TITLE_HINTS):
        return "commercial"
    if is_campus_general(b) or scan_has(b, ("校园", "高校", "校内", "学校")):
        return "campus"
    return "commercial"


def scene_it(text: str) -> Scene:
    if is_campus_general(text):
        return "campus"
    if scan_has(text, IT_ENTERPRISE_HINTS):
        return "enterprise"
    return "campus"


def scene_it_parts(title: str, body: str = "") -> Scene:
    """题名优先：企业内网报修不被正文「校园网」对比句洗成校园档。"""
    t = (title or "").strip()
    b = (body or "").strip()
    if is_campus_general(t) or scan_has(t, ("校园网", "高校", "学校")):
        return "campus"
    if scan_has(t, IT_ENTERPRISE_HINTS) or scan_has(t, ("企业", "公司")):
        return "enterprise"
    return scene_it(copy_scan_text(t, b))


def scene_lost(text: str) -> Scene:
    if any(k in text for k in LOST_ADOPT_HINTS):
        return "adopt"
    if is_campus_general(text):
        return "campus"
    return "community"


def scene_lost_parts(title: str, body: str = "") -> Scene:
    """题名优先：避免 scene「失物招领 / 宠物领养」把招领题洗成领养。"""
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, LOST_ADOPT_HINTS):
        return "adopt"
    if scan_has(t, ("失物", "招领", "寻物")):
        return "campus" if is_campus_general(t) else "community"
    if scan_has(b, LOST_ADOPT_HINTS) and not scan_has(t, ("失物", "招领", "寻物", "校园", "高校")):
        return "adopt"
    return scene_lost(copy_scan_text(t, b))


def scene_food(text: str) -> Scene:
    if scan_has(text, FOOD_CAMPUS_HINTS):
        return "campus"
    return "commercial"


def food_product_kind(title: str, body: str = "") -> str:
    """仅 ``canteen`` | ``restaurant``。

    不按菜系/业态开皮；题名已写餐厅/外卖且无食堂口径时，正文「食堂档口」对比句不得洗成 canteen。
    """
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, FOOD_CAMPUS_HINTS):
        return "canteen"
    if scan_has(t, FOOD_RESTAURANT_TITLE_HINTS):
        return "restaurant"
    if scan_has(b, FOOD_CAMPUS_HINTS):
        return "canteen"
    return "restaurant"


def scene_food_parts(title: str, body: str = "") -> Scene:
    """资料页：食堂 → campus；社会餐饮 → commercial。"""
    if food_product_kind(title, body) == "canteen":
        return "campus"
    return "commercial"


def scene_shop(text: str) -> Scene:
    if scan_has(text, SHOP_CAMPUS_HINTS):
        return "campus"
    return "commercial"


def shop_product_kind(title: str, body: str = "") -> str:
    """仅 ``campus`` | ``retail``。

    不按鲜花/数码/服装开行业皮；社会售卖共用零售档。
    题名无校园口径时（含社区二手、鲜花销售），正文「校园二手」对比句不得洗成 campus。
    """
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, SHOP_CAMPUS_HINTS):
        return "campus"
    if t:
        return "retail"
    if scan_has(b, SHOP_CAMPUS_HINTS):
        return "campus"
    return "retail"


def scene_shop_parts(title: str, body: str = "") -> Scene:
    """资料页：校园二手 → campus；其余售卖 → commercial。"""
    if shop_product_kind(title, body) == "campus":
        return "campus"
    return "commercial"


def scene_hospital(text: str) -> Scene:
    """门诊默认；宠物医院走 adopt（资料页宠主口径）。疫苗仍 default。"""
    if scan_has(text, HOSPITAL_PET_HINTS):
        return "adopt"
    return "default"


def scene_hospital_parts(title: str, body: str = "") -> Scene:
    """题名优先：避免 scene「校医院 / 宠物医院」把门诊/疫苗题洗成宠主。"""
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, HOSPITAL_PET_HINTS):
        return "adopt"
    if scan_has(t, ("医院", "门诊", "挂号", "校医", "疫苗", "HPV", "接种")):
        return "default"
    if scan_has(b, HOSPITAL_PET_HINTS):
        return "adopt"
    return "default"


def hospital_product_kind(title: str, body: str = "") -> str:
    """门诊 / 疫苗 / 宠物：与 ``_hospital_schema``、样例开题叠层同一判定。"""
    kind = title_then_body_hit(title, body, HOSPITAL_KIND_RULES)
    if kind is None and scene_hospital_parts(title, body) == "adopt":
        return "pet"
    return str(kind or "clinic")


def salon_product_kind(title: str, body: str = "") -> str:
    """美发 / 健身：与 ``_salon_schema``、样例开题叠层同一判定。"""
    kind = title_then_body_hit(title, body, SALON_KIND_RULES)
    return str(kind or "salon")


def meeting_product_kind(title: str, body: str = "") -> str:
    """场地名词：与 ``_meeting_schema`` 同一扫词。"""
    kind = title_then_body_hit(title, body, MEETING_KIND_RULES)
    return str(kind or "room")


def lost_product_kind(title: str, body: str = "") -> str:
    """失物 / 领养：复用 ``scene_lost_parts``。"""
    return scene_lost_parts(title, body)


def product_kind_for(domain: str, title: str = "", body: str = "") -> str | None:
    """域内产品变体 id；样例开题 ``variant_overlays`` 按此键取文案。"""
    if domain == "DOM-HOSPITAL":
        return hospital_product_kind(title, body)
    if domain == "DOM-SALON":
        return salon_product_kind(title, body)
    if domain == "DOM-LOST":
        return lost_product_kind(title, body)
    if domain == "DOM-MEETING":
        return meeting_product_kind(title, body)
    if domain == "DOM-SHOP":
        return shop_product_kind(title, body)
    if domain == "DOM-FOOD":
        return food_product_kind(title, body)
    if domain == "DOM-EVENT":
        return event_product_kind(title, body)
    return None


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


def scene_fund_parts(title: str, body: str = "") -> Scene:
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, FUND_ENTERPRISE_HINTS) or (
        scan_has(t, ("企业", "员工", "人事")) and scan_has(t, ("福利", "补助", "资助"))
    ):
        return "enterprise"
    if scan_has(t, FUND_CAMPUS_HINTS) or is_campus_general(t):
        return "campus"
    return scene_fund(copy_scan_text(t, b))


def scene_grade(text: str) -> Scene:
    """默认教务成绩；内训/培训考核走 enterprise。"""
    if scan_has(text, GRADE_ENTERPRISE_HINTS):
        return "enterprise"
    return "campus"


def scene_grade_parts(title: str, body: str = "") -> Scene:
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, GRADE_ENTERPRISE_HINTS) or scan_has(t, ("企业", "内训", "员工考核")):
        return "enterprise"
    return scene_grade(copy_scan_text(t, b))


def scene_intern(text: str) -> Scene:
    """默认校就业办周报；企业带教走 enterprise。"""
    if scan_has(text, INTERN_ENTERPRISE_HINTS):
        return "enterprise"
    return "campus"


def scene_intern_parts(title: str, body: str = "") -> Scene:
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, INTERN_ENTERPRISE_HINTS) or scan_has(t, ("企业带教", "带教导师")):
        return "enterprise"
    return scene_intern(copy_scan_text(t, b))


def scene_labsafe(text: str) -> Scene:
    """默认校园实验室准入；厂区/安环走 enterprise。"""
    if scan_has(text, LABSAFE_ENTERPRISE_HINTS):
        return "enterprise"
    return "campus"


def scene_labsafe_parts(title: str, body: str = "") -> Scene:
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, LABSAFE_ENTERPRISE_HINTS) or scan_has(t, ("厂区", "安环", "EHS")):
        return "enterprise"
    return scene_labsafe(copy_scan_text(t, b))


def scene_property(text: str) -> Scene:
    """默认小区物业；校园公寓/高校物业走 campus。"""
    if scan_has(text, PROPERTY_CAMPUS_HINTS) or (
        is_campus_general(text) and scan_has(text, ("物业", "报修", "公寓"))
    ):
        return "campus"
    return "community"


def scene_property_parts(title: str, body: str = "") -> Scene:
    """题名优先：写字楼/小区物业不被正文「校园物业」对比句洗成校园档。"""
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, PROPERTY_CAMPUS_HINTS) or (
        is_campus_general(t) and scan_has(t, ("物业", "报修", "公寓"))
    ):
        return "campus"
    if scan_has(t, ("写字楼", "小区", "社区", "商业物业")):
        return "community"
    return scene_property(copy_scan_text(t, b))


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


def scene_content_parts(title: str, body: str = "") -> Scene:
    """媒资/曲库/博客共用：题名优先，正文校园对比句不得洗商业题。"""
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, CONTENT_CAMPUS_HINTS):
        return "campus"
    if t:
        return "commercial"
    if scan_has(b, CONTENT_CAMPUS_HINTS):
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


def scene_forum_parts(title: str, body: str = "") -> Scene:
    t = (title or "").strip()
    b = (body or "").strip()
    if is_campus_general(t) or scan_has(t, CONTENT_CAMPUS_HINTS):
        return "campus"
    if scan_has(t, FORUM_COMMUNITY_HINTS) or (
        scan_has(t, COMMUNITY_HINTS) and scan_has(t, ("论坛", "BBS", "发帖", "回帖", "贴吧"))
    ):
        return "community"
    return scene_forum(copy_scan_text(t, b))


def scene_for(
    domain: str,
    title: str = "",
    proposal_text: str = "",
) -> Scene:
    """域级场景 id：壳文案与 profileFields 必须读同一结果。"""
    t = copy_scan_text(title, proposal_text)
    if domain == "DOM-CRM":
        return scene_crm_parts(title, proposal_text)
    if domain == "DOM-ASSET":
        return scene_asset_parts(title, proposal_text)
    if domain == "DOM-ATTEND":
        return scene_attend_parts(title, proposal_text)
    if domain == "DOM-EVENT":
        return scene_event_parts(title, proposal_text)
    if domain == "DOM-RECRUIT":
        return scene_recruit_parts(title, proposal_text)
    if domain == "DOM-DATING":
        return scene_dating_parts(title, proposal_text)
    if domain == "DOM-PARCEL":
        return scene_parcel_parts(title, proposal_text)
    if domain == "DOM-MEETING":
        return scene_meeting_parts(title, proposal_text)
    if domain == "DOM-PARKING":
        return scene_parking_parts(title, proposal_text)
    if domain == "DOM-IT":
        return scene_it_parts(title, proposal_text)
    if domain == "DOM-LOST":
        return scene_lost_parts(title, proposal_text)
    if domain == "DOM-FOOD":
        return scene_food_parts(title, proposal_text)
    if domain == "DOM-SHOP":
        return scene_shop_parts(title, proposal_text)
    if domain == "DOM-HOSPITAL":
        return scene_hospital_parts(title, proposal_text)
    if domain == "DOM-SALON":
        return scene_salon(t)
    if domain == "DOM-FUND":
        return scene_fund_parts(title, proposal_text)
    if domain == "DOM-GRADE":
        return scene_grade_parts(title, proposal_text)
    if domain == "DOM-INTERN":
        return scene_intern_parts(title, proposal_text)
    if domain == "DOM-LABSAFE":
        return scene_labsafe_parts(title, proposal_text)
    if domain == "DOM-PROPERTY":
        return scene_property_parts(title, proposal_text)
    if domain == "DOM-MEDIA":
        return scene_content_parts(title, proposal_text)
    if domain == "DOM-MUSIC":
        return scene_content_parts(title, proposal_text)
    if domain == "DOM-BLOG":
        return scene_content_parts(title, proposal_text)
    if domain == "DOM-FORUM":
        return scene_forum_parts(title, proposal_text)
    return "default"
