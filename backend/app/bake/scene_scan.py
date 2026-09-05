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

import re
from contextvars import ContextVar, Token
from typing import Any, Literal

# 匹配确认手改：scene / entry 覆盖（由 match_path_axes 注入；扫词逻辑不复制）
_PATH_OVERRIDE: ContextVar[dict[str, Any] | None] = ContextVar(
    "match_path_override", default=None
)


def push_path_override(
    *,
    domain: str,
    scene: str | None = None,
    entry: str | None = None,
) -> Token:
    return _PATH_OVERRIDE.set(
        {
            "domain": domain or "",
            "scene": (scene or "").strip() or None,
            "entry": (entry or "").strip() or None,
        }
    )


def reset_path_override(token: Token) -> None:
    _PATH_OVERRIDE.reset(token)


def _path_override() -> dict[str, Any] | None:
    return _PATH_OVERRIDE.get()

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

ATTEND_CAMPUS_HINTS = ("学生", "班级", "班主任", "大学生", "校园", "学工", "高校", "课堂")
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
LOST_DONATE_HINTS = ("捐赠物资", "物资认领", "捐赠认领", "捐赠名录")
IT_ENTERPRISE_HINTS = ("企业", "公司", "办公", "员工", "运维工单")
FOOD_CAMPUS_HINTS = ("食堂", "校园", "档口", "学子", "高校", "学校")
# 点餐只分两档：canteen（食堂/校内）| restaurant（社会餐饮，不按菜系开皮）
FOOD_RESTAURANT_TITLE_HINTS = ("餐厅", "外卖", "餐饮", "饭店", "美食", "小吃", "快餐", "茶饮")
# 商城 campus 须有校园口径；裸「二手」≠校园（社区二手走零售档，不按行业开皮）
SHOP_CAMPUS_HINTS = ("校园", "校内", "学校", "高校")
SHOP_PRINT_HINTS = ("文印", "打印店", "打印社", "复印", "装订")
SHOP_FLOWER_HINTS = ("鲜花", "花店", "花束", "特产", "农资")
SHOP_FARM_HINTS = ("农产品", "农产", "生鲜", "果蔬", "助农", "农贸")
SHOP_ERRAND_HINTS = ("跑腿", "代买", "代购", "代取")
SHOP_POINTS_HINTS = ("积分兑换", "积分商城", "积分兑换商城")
# 商城：campus 二手成色档 + 行业货皮 + retail 兜底
SHOP_RETAIL_TITLE_HINTS = ("销售", "商城", "电商", "网店", "店铺", "零售", "售卖", "购物")

# 与 domain_scene_seed 各 _SHOP_* 种子 category.name 必须同字（AI FAQ 分类跟货架分类统一）
SHOP_KIND_CATEGORIES: dict[str, tuple[str, str, str]] = {
    "farm": ("水果", "蔬菜", "粮油"),
    "retail": ("热销", "日用", "配件"),
    "campus": ("教材教辅", "数码", "日用文创"),
    "print": ("黑白打印", "彩印装订", "耗材"),
    "flowers": ("鲜切花", "盆花绿植", "地方特产"),
    "errand": ("代买餐饮", "代买日用", "代取快递"),
    "points": ("文创兑换", "生活兑换", "虚拟权益"),
}
PARKING_COMMERCIAL_TITLE_HINTS = ("商场", "园区", "写字楼", "小区", "商业", "地下车库", "停车场")
HOSPITAL_PET_HINTS = ("宠物", "宠医", "爱宠", "猫狗", "犬猫")
# 产品皮（样例开题 / builder 共用）：pet | vaccine | clinic
HOSPITAL_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (HOSPITAL_PET_HINTS, "pet"),
    (("疫苗", "HPV", "接种预约", "接种点", "接种", "体检预约", "入职体检"), "vaccine"),
    (("窗口取号", "政务预约", "车管预约", "银行预约", "政务窗口"), "window"),
    (("探视预约", "探视"), "visit"),
    (("医院", "门诊", "挂号", "校医"), "clinic"),
]
SALON_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (("健身", "私教", "瑜伽", "游泳私教", "器械课", "团课"), "fitness"),
    (("心理咨询", "心理辅导", "咨询预约"), "counsel"),
    (("驾校", "练车", "陪驾"), "drive"),
    (("家政", "上门维修预约", "上门服务"), "home"),
    (("家教", "辅导预约", "技能辅导"), "tutor"),
    (("美发", "理发", "造型", "美甲", "美容"), "salon"),
]
# CRM 深皮：销售默认；律所/家访/校企合作换档案列与菜单（勿只靠 keywords）
CRM_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (("法律援助", "律所", "案件跟进", "法律咨询案"), "legal"),
    (("家访", "谈心谈话", "谈心", "家访谈话"), "homevisit"),
    (("校企合作", "合作单位库", "产学研合作", "校友企业库"), "coop"),
]
# 图书域：卷宗档案 / 漂流 / 普通借阅
LIBRARY_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (("档案借阅", "卷宗", "档案馆", "档案室", "文书档案", "学籍卷宗"), "archive"),
    (("图书漂流", "漂流图书", "漂流借阅"), "drift"),
]
# 设备借用深皮：具名档优先；未点名实验室时「器材/设备借用」走中性 gear，避免一律实验室壳
# light → costume 物品 → sports/media/music/teach/outdoor → gear；演出语境兜底；强实验室 → lab
EQUIP_LIGHT_HINTS = (
    "雨伞",
    "充电宝",
    "门禁卡",
    "钥匙卡",
    "钥匙租借",
    "共享雨伞",
    "共享充电宝",
    "雨伞租借",
    "充电宝租借",
    "门禁卡租借",
    "校园轻资产",
    "共享物品",
    "临时门禁",
    "储物柜钥匙",
)
EQUIP_COSTUME_ITEM_HINTS = (
    "服装",
    "道具",
    "戏服",
    "演出服",
    "表演服",
    "舞蹈服",
    "礼服",
    "舞美",
    "布景",
    "戏箱",
    "演出器材",
    "舞台器材",
    "舞台道具",
    "服装租借",
    "道具租借",
    "演出服装",
    "演出道具",
    "服装道具",
)
EQUIP_SPORTS_HINTS = (
    "体育器材",
    "运动器材",
    "体育器械",
    "球类器材",
    "羽毛球拍",
    "乒乓球拍",
    "篮球架",
    "足球门",
    "排球",
    "跳绳",
    "哑铃",
    "健身器材借用",
    "体育用品租借",
)
EQUIP_MEDIA_HINTS = (
    "摄影器材",
    "摄像器材",
    "影像器材",
    "单反",
    "摄像机",
    "航拍",
    "无人机",
    "录像设备",
    "相机租借",
    "摄影设备",
    "多媒体设备",
    "投影机",
    "投影仪借用",
    "录音笔",
)
EQUIP_MUSIC_HINTS = (
    "乐器",
    "乐器租借",
    "乐器借用",
    "吉他",
    "小提琴",
    "大提琴",
    "钢琴租借",
    "钢琴借用",
    "民乐",
    "管乐",
    "打击乐",
    "尤克里里",
)
EQUIP_TEACH_HINTS = (
    "教具",
    "教学器材",
    "教学设备借用",
    "模型教具",
    "演示教具",
    "实训教具",
    "挂图教具",
)
EQUIP_OUTDOOR_HINTS = (
    "户外器材",
    "拓展器材",
    "露营",
    "帐篷",
    "登山杖",
    "户外装备",
    "素质拓展装备",
)
EQUIP_GEAR_HINTS = (
    "器材借用",
    "设备借用",
    "设备租借",
    "器材租借",
    "器械借用",
    "器械租借",
    "公用器材",
    "公共器材",
    "物资器材",
)
EQUIP_COSTUME_SCENE_HINTS = (
    "演出",
    "晚会",
    "剧社",
    "话剧",
    "艺术团",
    "文艺汇演",
    "舞台",
    "戏剧",
    "音乐会",
    "合唱",
    "舞蹈团",
    "校园文化节",
    "文艺演出",
    "毕业汇演",
    "迎新晚会",
)
EQUIP_COSTUME_LOAN_HINTS = ("租借", "借用", "借还", "出借", "归还")
EQUIP_LAB_STRONG_HINTS = (
    "实验室",
    "实验器材",
    "实验设备",
    "示波器",
    "万用表",
    "实训设备",
    "仪器仪表",
    "测量仪器",
    "单片机",
)
EQUIP_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (EQUIP_LIGHT_HINTS, "light"),
    (EQUIP_COSTUME_ITEM_HINTS, "costume"),
    (EQUIP_SPORTS_HINTS, "sports"),
    (EQUIP_MEDIA_HINTS, "media"),
    (EQUIP_MUSIC_HINTS, "music"),
    (EQUIP_TEACH_HINTS, "teach"),
    (EQUIP_OUTDOOR_HINTS, "outdoor"),
    # gear 不进本表：避免「实验室器材借用」被「器材借用」抢档；见 equip_product_kind 兜底
]
# 物业工单：市政 / 投诉 / 报修
PROPERTY_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (("市政", "路灯", "井盖", "市政设施", "路灯报修", "井盖报修"), "municipal"),
    (("投诉建议", "物业投诉", "业主投诉", "信访"), "complaint"),
]
# IT 工单：售后 / 维保 / 故障报修
IT_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (("售后工单", "客服工单", "客服售后", "售后咨询"), "aftersales"),
    (("设备维保", "维保工单", "维保"), "maintenance"),
]
MEETING_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (("自习室", "研习室", "研讨室"), "study"),
    (("琴房", "排练", "舞蹈"), "piano"),
    (("体育场", "体育馆", "球馆", "羽毛球场", "篮球场", "足球场", "游泳"), "gym"),
    (("座位", "占座", "选座"), "seat"),
    (("工位", "实验室", "实训室", "创客"), "lab"),
    (("博物馆", "展览", "党史馆", "参观预约"), "exhibit"),
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
INTERN_ENTERPRISE_HINTS = (
    "企业带教",
    "带教导师",
    "校招实习生",
    "入职实习",
    "企业实习生",
    "导师审阅周报",
    "企业员工周报",
    "员工周报",
    "工时填报",
)
# 开题写绑岗/一人一岗 → 资料绑岗交周报（复用 matchProfileRoom）；未写则填单选已建档岗
INTERN_BIND_HINTS = (
    "岗位与学生绑定",
    "学生与岗位绑定",
    "一人一岗",
    "岗生绑定",
    "绑定实习岗位",
    "分配实习岗",
    "定岗后交周报",
    "对号入岗",
    "实习岗绑定",
)
# 事件：学生/家长/员工本人填报打卡（填单优先）；未写则对象台账作业（网格员/班主任）
EVENT_SELF_REPORT_HINTS = (
    "家长代填",
    "学生填报",
    "学生打卡",
    "学生端打卡",
    "本人晨午检",
    "自行打卡",
    "学生健康打卡",
    "家长填报",
    "学生每日打卡",
    "本人健康打卡",
    "员工自行打卡",
    "员工每日健康打卡",
    "学生（或家长代填）",
    "学生或家长",
    # 校园晨午检毕设多为学生/家长填报（班主任台账题少写「晨午检」作主路径词）
    "晨午检",
    "晨检",
    "午检",
    "健康打卡",
    "每日打卡",
    "每日健康",
    "防疫打卡",
)
# 床位：开题主写调宿/退宿 → 填单优先；纯选房/分床仍逛目录；选房+调宿混写偏填单
BED_TRANSFER_HINTS = (
    "调宿",
    "退宿",
    "调宿退宿",
    "调宿申请",
    "退宿申请",
    "调换宿舍",
)
BED_SELECT_HINTS = (
    "新生选房",
    "在线选房",
    "床位分配",
    "分床",
    "选房系统",
    "床位选择",
    "宿舍选房",
)
# 实验室准入：校园默认；厂区/安环走 enterprise
LABSAFE_ENTERPRISE_HINTS = ("厂区", "安环", "企业实验室", "EHS准入", "产线实验室", "车间实验室")

# OA 申请 / 车证：企业·园区 vs 校园（身份与 profile 同 scene_for）
OA_ENTERPRISE_HINTS = (
    "企业", "公司", "单位", "集团", "机关", "事业单位",
    "员工", "职工", "人事", "行政办", "综合办",
)
OA_CAMPUS_HINTS = ("高校", "校园", "学校", "学院", "师生", "教职工", "学工")
FITOUT_COMMUNITY_HINTS = ("小区", "业主", "物业", "社区装修", "入户装修")
CARPASS_ENTERPRISE_HINTS = (
    "园区", "产业园", "厂区", "企业", "公司", "办公区", "写字楼",
)
CARPASS_CAMPUS_HINTS = ("高校", "校园", "学校", "校门", "进校", "校内")
# 物业：小区住户默认；校园物业/公寓走 campus
PROPERTY_CAMPUS_HINTS = ("校园物业", "学生公寓", "高校物业", "宿舍物业", "校园报修", "学校物业")
# 内容域：商业点播默认；校园媒资/院刊走 campus
CONTENT_CAMPUS_HINTS = (
    "校园",
    "高校",
    "学校",
    "院系",
    "学院",
    "学工",
    "大学生",
    "记者站",
    "广播稿",
    "广播台",
    "院刊",
    "点播课",
    "课程视频",
    "点歌台",
    "点歌",
    "表白墙",
    "树洞",
)
BLOG_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (("记者站", "广播稿", "广播台", "校媒稿件"), "press"),
]
MEDIA_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (("点播课", "课程视频", "教学视频库", "微课视频", "课程视频库"), "coursevod"),
]
MUSIC_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (("点歌台", "点歌"), "karaoke"),
]
FORUM_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (("表白墙", "树洞", "匿名墙"), "wall"),
]
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
    "donate",
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
    律所/家访/校企走 product_kind，场景与创业孵化皮分离。
    """
    t = (title or "").strip()
    b = (body or "").strip()
    kind = crm_product_kind(t, b)
    if kind == "legal":
        return "enterprise"
    if kind == "homevisit":
        return "campus"
    if kind == "coop":
        return "campus" if (
            is_campus_general(t) or scan_has(t, ("高校", "校园", "学院", "校友"))
            or is_campus_general(b)
        ) else "enterprise"
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
    if any(k in text for k in LOST_DONATE_HINTS):
        return "donate"
    if is_campus_general(text):
        return "campus"
    return "community"


def scene_lost_parts(title: str, body: str = "") -> Scene:
    """题名优先：避免 scene「失物招领 / 宠物领养」把招领题洗成领养。"""
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, LOST_ADOPT_HINTS):
        return "adopt"
    if scan_has(t, LOST_DONATE_HINTS) or (
        scan_has(t, ("捐赠",)) and scan_has(t, ("认领", "物资"))
    ):
        return "donate"
    if scan_has(t, ("失物", "招领", "寻物")):
        return "campus" if is_campus_general(t) else "community"
    if scan_has(b, LOST_ADOPT_HINTS) and not scan_has(t, ("失物", "招领", "寻物", "校园", "高校")):
        return "adopt"
    if scan_has(b, LOST_DONATE_HINTS) and not scan_has(t, ("失物", "招领", "寻物", "领养")):
        return "donate"
    return scene_lost(copy_scan_text(t, b))


# 活动报名深皮：default | cert | ticket | blood | camp
ACTIVITY_KIND_RULES: list[tuple[tuple[str, ...], str]] = [
    (("证书报考", "培训班", "四六级", "考证报名", "证书培训"), "cert"),
    (("票务", "领票", "演出票", "景区票", "门票报名", "演出票务"), "ticket"),
    (("献血", "开放日"), "blood"),
    (("研学报名", "夏令营", "赛事报名", "大赛报名", "研学夏令营"), "camp"),
]


def activity_product_kind(title: str, body: str = "") -> str:
    """活动域产品皮；题名优先。"""
    picked = title_then_body_hit(title, body, ACTIVITY_KIND_RULES)
    return str(picked) if picked else "default"


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
    """``farm`` | ``print`` | ``flowers`` | ``errand`` | ``points`` | ``campus`` | ``retail``。

    行业货皮跟题名优先；校园二手成色仅 ``campus``；其余社会售卖 ``retail``。
    题名无校园口径时，正文「校园二手」对比句不得洗成 campus。
    分类名见 ``SHOP_KIND_CATEGORIES``（与 SQL 种子、AI FAQ 同字）。
    """
    t = (title or "").strip()
    b = (body or "").strip()
    for hints, kind in (
        (SHOP_ERRAND_HINTS, "errand"),
        (SHOP_PRINT_HINTS, "print"),
        (SHOP_FARM_HINTS, "farm"),
        (SHOP_FLOWER_HINTS, "flowers"),
        (SHOP_POINTS_HINTS, "points"),
        (SHOP_CAMPUS_HINTS, "campus"),
    ):
        if scan_has(t, hints):
            return kind
    if t:
        return "retail"
    for hints, kind in (
        (SHOP_ERRAND_HINTS, "errand"),
        (SHOP_PRINT_HINTS, "print"),
        (SHOP_FARM_HINTS, "farm"),
        (SHOP_FLOWER_HINTS, "flowers"),
        (SHOP_POINTS_HINTS, "points"),
        (SHOP_CAMPUS_HINTS, "campus"),
    ):
        if scan_has(b, hints):
            return kind
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


def crm_product_kind(title: str, body: str = "") -> str:
    """销售 / 律所案件 / 家访 / 校企：与 ``_crm_schema`` 同一扫词。"""
    kind = title_then_body_hit(title, body, CRM_KIND_RULES)
    return str(kind or "sales")


def library_product_kind(title: str, body: str = "") -> str:
    """图书 / 卷宗档案 / 漂流：与 ``_library_schema`` 同一扫词。"""
    kind = title_then_body_hit(title, body, LIBRARY_KIND_RULES)
    return str(kind or "book")


def equip_product_kind(title: str, body: str = "") -> str:
    """设备借用产品皮：与 ``_equip_schema`` 同一扫词。

    具名档见 ``EQUIP_KIND_RULES``；演出语境×租借动词 → costume；
    强实验室信号 → lab；其余未点名实验室的器材/设备借用 → gear；默认 lab。
    gear 眉题由 ``equip_gear_noun`` 从题名抠，不必再枚举行业。
    """
    kind = title_then_body_hit(title, body, EQUIP_KIND_RULES)
    if kind:
        return str(kind)
    for text in ((title or "").strip(), (body or "").strip()):
        if not text:
            continue
        if scan_has(text, EQUIP_LAB_STRONG_HINTS):
            return "lab"
        if scan_has(text, EQUIP_COSTUME_SCENE_HINTS) and scan_has(
            text, EQUIP_COSTUME_LOAN_HINTS
        ):
            return "costume"
        # 中性器材皮：具名短语或「器材/器械/设备 × 借」；实验室已在上方压回
        if scan_has(text, EQUIP_GEAR_HINTS) or (
            scan_has(text, ("器材", "器械", "设备"))
            and scan_has(text, EQUIP_COSTUME_LOAN_HINTS)
        ):
            return "gear"
    return "lab"


_EQUIP_GEAR_NOUN_RE = re.compile(
    r"((?:[\u4e00-\u9fff]{2,12}?)(?:器材|设备|装备|器械|用具))"
)
_EQUIP_GEAR_STRIP_PREFIX = (
    "基于SpringBoot与Vue的",
    "基于SpringBoot的",
    "基于Vue的",
    "高校",
    "校园",
    "学校",
    "单位",
    "社区",
)


def equip_gear_noun(title: str, body: str = "") -> str:
    """gear 档眉题：从题名/开题抠「消防器材」「军训器械」等；抠不出 → 器材借用。

    具名 kind（体育/影像…）不走此函数；只服务枚举盖不住的开题。
    """
    for text in ((title or "").strip(), (body or "").strip()):
        if not text:
            continue
        blob = text
        for p in _EQUIP_GEAR_STRIP_PREFIX:
            blob = blob.replace(p, "")
        # 优先「××器材借用/租借」整段前的名词
        m = re.search(
            r"([\u4e00-\u9fff]{2,12}(?:器材|设备|装备|器械|用具))(?:借用|租借|借还|管理)",
            blob,
        )
        if not m:
            m = _EQUIP_GEAR_NOUN_RE.search(blob)
        if not m:
            continue
        noun = m.group(1).strip()
        for p in ("的", "与", "和", "及"):
            if noun.startswith(p):
                noun = noun[len(p) :].strip()
        # 过短或纯壳词不要
        if len(noun) < 2 or noun in ("设备", "器材", "装备", "器械", "用具"):
            continue
        if scan_has(noun, EQUIP_LAB_STRONG_HINTS):
            continue
        return noun[:16]
    return "器材借用"


def property_product_kind(title: str, body: str = "") -> str:
    """报修 / 投诉 / 市政：与 ``_property_schema`` 同一扫词。"""
    kind = title_then_body_hit(title, body, PROPERTY_KIND_RULES)
    return str(kind or "repair")


def it_product_kind(title: str, body: str = "") -> str:
    """故障 / 售后 / 维保：与 ``_it_schema`` 同一扫词。"""
    kind = title_then_body_hit(title, body, IT_KIND_RULES)
    return str(kind or "ticket")


def meeting_product_kind(title: str, body: str = "") -> str:
    """场地名词：与 ``_meeting_schema`` 同一扫词。"""
    kind = title_then_body_hit(title, body, MEETING_KIND_RULES)
    return str(kind or "room")


PARKING_CHARGE_HINTS = ("充电桩", "充电车位", "新能源充电", "共享充电", "充电站")


def parking_product_kind(title: str, body: str = "") -> str:
    """车位 / 充电桩：与 ``_parking_schema``、充电叠层同一扫词。"""
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, PARKING_CHARGE_HINTS) or scan_has(b, PARKING_CHARGE_HINTS):
        return "charge"
    return "space"


HOTEL_HOMESTAY_HINTS = ("民宿", "客栈", "农家乐", "乡村民宿")


def hotel_product_kind(title: str, body: str = "") -> str:
    """宾馆 / 民宿：与 ``_hotel_schema``、民宿叠层同一扫词。"""
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, HOTEL_HOMESTAY_HINTS) or scan_has(b, HOTEL_HOMESTAY_HINTS):
        return "homestay"
    return "hotel"


def lost_product_kind(title: str, body: str = "") -> str:
    """失物 / 领养 / 捐赠认领：复用 ``scene_lost_parts``。"""
    return scene_lost_parts(title, body)


def product_kind_for(domain: str, title: str = "", body: str = "") -> str | None:
    """域内产品变体 id；样例开题 ``variant_overlays`` 按此键取文案。"""
    if domain == "DOM-HOSPITAL":
        return hospital_product_kind(title, body)
    if domain == "DOM-SALON":
        return salon_product_kind(title, body)
    if domain == "DOM-LOST":
        return lost_product_kind(title, body)
    if domain == "DOM-ACTIVITY":
        return activity_product_kind(title, body)
    if domain == "DOM-MEETING":
        return meeting_product_kind(title, body)
    if domain == "DOM-PARKING":
        return parking_product_kind(title, body)
    if domain == "DOM-HOTEL":
        return hotel_product_kind(title, body)
    if domain == "DOM-BLOG":
        return blog_product_kind(title, body)
    if domain == "DOM-MEDIA":
        return media_product_kind(title, body)
    if domain == "DOM-MUSIC":
        return music_product_kind(title, body)
    if domain == "DOM-FORUM":
        return forum_product_kind(title, body)
    if domain == "DOM-SHOP":
        return shop_product_kind(title, body)
    if domain == "DOM-FOOD":
        return food_product_kind(title, body)
    if domain == "DOM-EVENT":
        return event_product_kind(title, body)
    if domain == "DOM-CRM":
        return crm_product_kind(title, body)
    if domain == "DOM-LIBRARY":
        return library_product_kind(title, body)
    if domain == "DOM-EQUIP":
        return equip_product_kind(title, body)
    if domain == "DOM-PROPERTY":
        return property_product_kind(title, body)
    if domain == "DOM-IT":
        return it_product_kind(title, body)
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
    if scan_has(t, INTERN_ENTERPRISE_HINTS) or scan_has(
        t, ("企业带教", "带教导师", "企业员工周报", "工时填报")
    ):
        return "enterprise"
    return scene_intern(copy_scan_text(t, b))


def intern_post_bound(
    title: str = "",
    proposal_text: str = "",
    *,
    respect_override: bool = True,
) -> bool:
    """开题要求岗位与学生绑定 / 一人一岗时为 True（否则选已建档岗交周报）。"""
    if respect_override:
        ov = _path_override()
        if (
            ov
            and ov.get("domain") == "DOM-INTERN"
            and ov.get("entry") in {"post_bound", "select_post"}
        ):
            return ov["entry"] == "post_bound"
    return scan_has(copy_scan_text(title or "", proposal_text or ""), INTERN_BIND_HINTS)


def event_self_report(
    title: str = "",
    proposal_text: str = "",
    *,
    respect_override: bool = True,
) -> bool:
    """开题主写学生/家长/员工本人打卡填报 → True（填单优先）；对象台账作业保持默认。"""
    if respect_override:
        ov = _path_override()
        if (
            ov
            and ov.get("domain") == "DOM-EVENT"
            and ov.get("entry") in {"self_report", "caseload"}
        ):
            return ov["entry"] == "self_report"
    return scan_has(
        copy_scan_text(title or "", proposal_text or ""), EVENT_SELF_REPORT_HINTS
    )


def bed_transfer_primary(
    title: str = "",
    proposal_text: str = "",
    *,
    respect_override: bool = True,
) -> bool:
    """开题写调宿/退宿 → True（填单优先）。

    纯选房/分床（无调宿词）→ False 逛目录。
    选房+调宿混写 → 仍 True（偏本人填单，目录仅作余量查阅）。
    """
    if respect_override:
        ov = _path_override()
        if (
            ov
            and ov.get("domain") == "DOM-BED"
            and ov.get("entry") in {"transfer", "select_bed"}
        ):
            return ov["entry"] == "transfer"
    t = copy_scan_text(title or "", proposal_text or "")
    if scan_has(t, BED_TRANSFER_HINTS):
        return True
    return False


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


def blog_product_kind(title: str, body: str = "") -> str:
    """院刊校园 / 记者站稿件 / 个人博客。"""
    kind = title_then_body_hit(title, body, BLOG_KIND_RULES)
    if kind:
        return str(kind)
    if scene_content_parts(title, body) == "campus":
        return "campus"
    return "personal"


def media_product_kind(title: str, body: str = "") -> str:
    """点播课 / 校园媒资 / 商业影视综。"""
    kind = title_then_body_hit(title, body, MEDIA_KIND_RULES)
    if kind:
        return str(kind)
    if scene_content_parts(title, body) == "campus":
        return "campus"
    return "commercial"


def music_product_kind(title: str, body: str = "") -> str:
    """点歌台 / 校园曲库 / 商业曲库。"""
    kind = title_then_body_hit(title, body, MUSIC_KIND_RULES)
    if kind:
        return str(kind)
    if scene_content_parts(title, body) == "campus":
        return "campus"
    return "commercial"


def forum_product_kind(title: str, body: str = "") -> str:
    """表白墙 / 社区论坛 / 校园论坛。"""
    kind = title_then_body_hit(title, body, FORUM_KIND_RULES)
    if kind:
        return str(kind)
    if scene_forum_parts(title, body) == "community":
        return "community"
    return "campus"


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


_TOUR_CAMPUS_HINTS = (
    "高校",
    "校园",
    "研学旅行社",
    "学生研学",
    "暑期社会实践线路",
)


def scene_tour(text: str) -> Scene:
    """默认旅行社企业档；开题写清高校研学线路再 campus。"""
    if scan_has(text, _TOUR_CAMPUS_HINTS) or is_campus_general(text):
        return "campus"
    return "enterprise"


def scene_tour_parts(title: str, body: str = "") -> Scene:
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, _TOUR_CAMPUS_HINTS) or is_campus_general(t):
        return "campus"
    if t:
        return "enterprise"
    return scene_tour(copy_scan_text(t, b))


def scene_carrent(text: str) -> Scene:
    """四轮商业租车门店身份。"""
    return "commercial"


def scene_carrent_parts(title: str, body: str = "") -> Scene:
    return "commercial"


def scene_timebank(text: str) -> Scene:
    """社区时间银行默认 community；开题写清校园志愿再 campus。"""
    if scan_has(text, COMMUNITY_HINTS):
        return "community"
    if is_campus_general(text) or scan_has(text, ("高校", "校园", "学号", "院系")):
        return "campus"
    # C-14 默认社区档（≠劳动认定）
    return "community"


def scene_timebank_parts(title: str, body: str = "") -> Scene:
    t = (title or "").strip()
    b = (body or "").strip()
    joined = copy_scan_text(t, b)
    if scan_has(t, COMMUNITY_HINTS) or scan_has(joined, COMMUNITY_HINTS):
        return "community"
    if is_campus_general(t) or is_campus_general(joined):
        return "campus"
    if t:
        return scene_timebank(joined)
    return scene_timebank(joined)


def scene_oa(text: str) -> Scene:
    """用章/用车/报销等：默认校园办事；开题写清企业/公司走 enterprise。"""
    if scan_has(text, OA_ENTERPRISE_HINTS) and not scan_has(text, OA_CAMPUS_HINTS):
        return "enterprise"
    if scan_has(text, OA_CAMPUS_HINTS) or is_campus_general(text):
        return "campus"
    if scan_has(text, OA_ENTERPRISE_HINTS):
        return "enterprise"
    return "campus"


def scene_oa_parts(title: str, body: str = "") -> Scene:
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, OA_ENTERPRISE_HINTS) and not scan_has(t, OA_CAMPUS_HINTS):
        return "enterprise"
    if scan_has(t, OA_CAMPUS_HINTS) or is_campus_general(t):
        return "campus"
    return scene_oa(copy_scan_text(t, b))


def scene_fitout(text: str) -> Scene:
    """装修备案：小区业主 community；企业/校园各走对应档。"""
    if scan_has(text, FITOUT_COMMUNITY_HINTS) or scan_has(text, COMMUNITY_HINTS):
        return "community"
    if scan_has(text, OA_ENTERPRISE_HINTS) and not scan_has(text, OA_CAMPUS_HINTS):
        return "enterprise"
    if scan_has(text, OA_CAMPUS_HINTS) or is_campus_general(text):
        return "campus"
    return "community"


def scene_fitout_parts(title: str, body: str = "") -> Scene:
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, FITOUT_COMMUNITY_HINTS) or scan_has(t, ("小区", "业主")):
        return "community"
    if scan_has(t, OA_ENTERPRISE_HINTS) and not scan_has(t, OA_CAMPUS_HINTS):
        return "enterprise"
    if scan_has(t, OA_CAMPUS_HINTS) or is_campus_general(t):
        return "campus"
    return scene_fitout(copy_scan_text(t, b))


def scene_carpass(text: str) -> Scene:
    """车辆通行证：校园进校 / 园区企业。"""
    if scan_has(text, CARPASS_ENTERPRISE_HINTS) and not scan_has(text, CARPASS_CAMPUS_HINTS):
        return "enterprise"
    if scan_has(text, CARPASS_CAMPUS_HINTS) or is_campus_general(text):
        return "campus"
    if scan_has(text, CARPASS_ENTERPRISE_HINTS):
        return "enterprise"
    return "campus"


def scene_carpass_parts(title: str, body: str = "") -> Scene:
    t = (title or "").strip()
    b = (body or "").strip()
    if scan_has(t, CARPASS_ENTERPRISE_HINTS) and not scan_has(t, CARPASS_CAMPUS_HINTS):
        return "enterprise"
    if scan_has(t, CARPASS_CAMPUS_HINTS) or is_campus_general(t):
        return "campus"
    return scene_carpass(copy_scan_text(t, b))


def scene_for(
    domain: str,
    title: str = "",
    proposal_text: str = "",
    *,
    respect_override: bool = True,
) -> Scene:
    """域级场景 id：壳文案与 profileFields 必须读同一结果。"""
    if respect_override:
        ov = _path_override()
        if ov and ov.get("domain") == domain and ov.get("scene"):
            return ov["scene"]  # type: ignore[return-value]
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
    if domain == "DOM-TOUR":
        return scene_tour_parts(title, proposal_text)
    if domain == "DOM-CARRENT":
        return scene_carrent_parts(title, proposal_text)
    if domain == "DOM-TIMEBANK":
        return scene_timebank_parts(title, proposal_text)
    if domain in {
        "DOM-SEAL",
        "DOM-FLEET",
        "DOM-CERT",
        "DOM-PROMO",
        "DOM-TRIP",
        "DOM-EXPENSE",
    }:
        return scene_oa_parts(title, proposal_text)
    if domain == "DOM-FITOUT":
        return scene_fitout_parts(title, proposal_text)
    if domain == "DOM-CARPASS":
        return scene_carpass_parts(title, proposal_text)
    if domain == "DOM-ACAD":
        return "campus"
    return "default"
