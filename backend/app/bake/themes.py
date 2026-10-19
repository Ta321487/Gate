"""主题 / 登录版式 / 质感 / 门户壳：目录挑选与规范化。

配色、质感、布局壳正交；共用 pick/normalize/label，避免每轴复制一份。
"""

from __future__ import annotations

from app.bake.domains import DOMAINS


# 兼容旧全局主题 id → 映射到图书行业默认
THEME_ALIASES = {
    "theme-ink": "lib-ink",
    "theme-grove": "lib-grove",
    "theme-clay": "lib-amber",
    "theme-night": "lib-night",
}


def themes_for_domain(domain: str) -> list[dict]:
    dom = DOMAINS.get(domain) or DOMAINS["DOM-GENERIC"]
    return list(dom.get("themes") or [])


def default_theme(domain: str) -> str:
    themes = themes_for_domain(domain)
    return themes[0]["id"] if themes else "gen-ink"


def _pick_by_seed(ids: list[str], seed: str | None, default: str) -> str:
    """按种子稳定挑选，便于同一项目重 bake 可复现；无种子则随机。"""
    import hashlib
    import random

    if not ids:
        return default
    if seed:
        h = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16)
        return ids[h % len(ids)]
    return random.choice(ids)


def pick_from_catalog(catalog: list[dict], seed: str | None, default: str) -> str:
    return _pick_by_seed([t["id"] for t in catalog], seed, default)


def normalize_from_catalog(catalog: list[dict], value: str | None, default: str) -> str:
    ids = {t["id"] for t in catalog}
    if value and value in ids:
        return value
    return default


def label_from_catalog(catalog: list[dict], value: str) -> str:
    return next((t["label"] for t in catalog if t["id"] == value), value)


def resolve_or_pick(
    catalog: list[dict],
    override: str | None,
    seed: str | None,
    default: str,
) -> str:
    """有覆盖用覆盖，否则按种子挑。"""
    if override:
        return normalize_from_catalog(catalog, override, default)
    return pick_from_catalog(catalog, seed, default)


def resolve_style_override(
    *,
    reset: bool,
    body_value: str | None,
    prev_value: str | None,
    catalog: list[dict],
    default: str,
    unknown_message: str,
) -> str | None:
    """匹配更新时：重置→重抽；显式选择→校验；否则保留上次。None = 交给 resolve_or_pick。"""
    if reset:
        return None
    if body_value is not None:
        if body_value not in {t["id"] for t in catalog}:
            raise ValueError(unknown_message)
        return normalize_from_catalog(catalog, body_value, default)
    if prev_value:
        return normalize_from_catalog(catalog, prev_value, default)
    return None


def pick_theme(domain: str, seed: str | None = None) -> str:
    """按种子从领域配色集中稳定挑选，避免同领域总落第一个。"""
    themes = themes_for_domain(domain)
    return pick_from_catalog(themes, seed, default_theme(domain))


# 登录/注册版式：bake 时随机写入 spec，交付后固定
AUTH_TEMPLATES = [
    {"id": "split", "label": "双栏书香"},
    {"id": "mirror", "label": "镜像入口"},
    {"id": "center", "label": "雾面居中"},
    {"id": "ribbon", "label": "顶栏色带"},
    {"id": "ledge", "label": "浮台登录"},
    {"id": "folio", "label": "对开页"},
    {"id": "editorial", "label": "资讯侧栏"},
]

# 门户首页构图（与 layout 壳正交）：功能卡片 / 资讯侧栏 / 商城货架
PORTAL_HOME_STYLES = [
    {"id": "cards", "label": "功能卡片首页"},
    {"id": "editorial", "label": "资讯侧栏首页"},
    {"id": "mall", "label": "商城货架首页"},
]

# 内容域种子抽签只用这两档（勿把 mall 抽进博客等）
CONTENT_PORTAL_HOME_PICK = [
    {"id": "cards", "label": "功能卡片首页"},
    {"id": "editorial", "label": "资讯侧栏首页"},
]

# 内容域：未手选时按种子在 cards/editorial 间抽；其它域默认 cards
CONTENT_PORTAL_HOME_DOMAINS = frozenset(
    {"DOM-BLOG", "DOM-MEDIA", "DOM-MUSIC", "DOM-FORUM"}
)

# 商城货架首页仅交易货架域可选手选；默认仍 cards
MALL_PORTAL_HOME_DOMAINS = frozenset({"DOM-SHOP", "DOM-FOOD"})

# 内容组页内构图（ArchiveBrowse；与 portal_home_style 正交）
CONTENT_SURFACE_STYLES = [
    {"id": "folio", "label": "刊头阅读流"},
    {"id": "coverwall", "label": "封面墙"},
    {"id": "ledger", "label": "条目清单"},
    {"id": "splitdesk", "label": "双栏阅读台"},
]

# 与 content_thicken.CONTENT_DOMAINS 对齐；仅这些域写入/生效 content_surface_style
CONTENT_SURFACE_DOMAINS = frozenset(
    {"DOM-MEDIA", "DOM-MUSIC", "DOM-FORUM", "DOM-BLOG", "DOM-DOCLIB"}
)

CONTENT_SURFACE_DOMAIN_DEFAULTS: dict[str, str] = {
    "DOM-BLOG": "folio",
    "DOM-FORUM": "folio",
    "DOM-MEDIA": "coverwall",
    "DOM-MUSIC": "coverwall",
    "DOM-DOCLIB": "ledger",
}

# 交易组页内构图（ArchiveBrowse/Cart；与 portal_home_style=mall 正交）
TRADE_SURFACE_STYLES = [
    {"id": "shelfgrid", "label": "货架密铺"},
    {"id": "menuboard", "label": "档口菜单板"},
    {"id": "showtime", "label": "排片选座行"},
]

# 与 trade_thicken.TRADE_DOMAINS 对齐；仅这些域写入/生效 trade_surface_style
TRADE_SURFACE_DOMAINS = frozenset({"DOM-SHOP", "DOM-FOOD", "DOM-CINEMA"})

TRADE_SURFACE_DOMAIN_DEFAULTS: dict[str, str] = {
    "DOM-SHOP": "shelfgrid",
    "DOM-FOOD": "menuboard",
    "DOM-CINEMA": "showtime",
}

# 交易隐喻不可乱跨域：排片只影院、档口只餐饮；货架密铺可作交易通用备选
TRADE_SURFACE_STYLE_ALLOWED: dict[str, frozenset[str]] = {
    "shelfgrid": frozenset({"DOM-SHOP", "DOM-FOOD", "DOM-CINEMA"}),
    "menuboard": frozenset({"DOM-FOOD"}),
    "showtime": frozenset({"DOM-CINEMA"}),
}

# 预约组页内构图（SlotBook/ArchiveBrowse；与 portal_home_style 正交）
RESERVE_SURFACE_STYLES = [
    {"id": "slotstrip", "label": "时段条/号源行"},
    {"id": "roomstate", "label": "房态格"},
    {"id": "vehiclecard", "label": "车型档期卡"},
]

# 与 reserve_thicken.RESERVE_DOMAINS 对齐；仅这些域写入/生效 reserve_surface_style
RESERVE_SURFACE_DOMAINS = frozenset(
    {
        "DOM-HOSPITAL",
        "DOM-PARKING",
        "DOM-MEETING",
        "DOM-SALON",
        "DOM-HOTEL",
        "DOM-CARRENT",
        "DOM-INSTRUMENT",
    }
)

RESERVE_SURFACE_DOMAIN_DEFAULTS: dict[str, str] = {
    "DOM-HOSPITAL": "slotstrip",
    "DOM-MEETING": "slotstrip",
    "DOM-SALON": "slotstrip",
    "DOM-INSTRUMENT": "slotstrip",
    "DOM-HOTEL": "roomstate",
    "DOM-CARRENT": "vehiclecard",
    "DOM-PARKING": "vehiclecard",
}

# 房态/车型隐喻绑域；时段条留给号源/场地类预约
RESERVE_SURFACE_STYLE_ALLOWED: dict[str, frozenset[str]] = {
    "slotstrip": frozenset(
        {"DOM-HOSPITAL", "DOM-MEETING", "DOM-SALON", "DOM-INSTRUMENT"}
    ),
    "roomstate": frozenset({"DOM-HOTEL"}),
    "vehiclecard": frozenset({"DOM-CARRENT", "DOM-PARKING"}),
}

# 借用组页内构图（ArchiveBrowse；与 portal_home_style 正交）
BORROW_SURFACE_STYLES = [
    {"id": "bookshelf", "label": "书架脊列"},
    {"id": "stockrow", "label": "库存台账行"},
    {"id": "bedblocks", "label": "床位色块墙"},
    {"id": "parcelshelf", "label": "驿站货架格"},
]

# 与 borrow_thicken.BORROW_DOMAINS 对齐；仅这些域写入/生效 borrow_surface_style
BORROW_SURFACE_DOMAINS = frozenset(
    {
        "DOM-LIBRARY",
        "DOM-EQUIP",
        "DOM-ASSET",
        "DOM-PARCEL",
        "DOM-BED",
        "DOM-PROCURE",
    }
)

BORROW_SURFACE_DOMAIN_DEFAULTS: dict[str, str] = {
    "DOM-LIBRARY": "bookshelf",
    "DOM-ASSET": "stockrow",
    "DOM-EQUIP": "stockrow",
    "DOM-PROCURE": "stockrow",
    "DOM-BED": "bedblocks",
    "DOM-PARCEL": "parcelshelf",
}

# 书架/床位/驿站隐喻绑域；台账行留给库存类（图书也可作台账备选）
BORROW_SURFACE_STYLE_ALLOWED: dict[str, frozenset[str]] = {
    "bookshelf": frozenset({"DOM-LIBRARY"}),
    "stockrow": frozenset(
        {"DOM-ASSET", "DOM-EQUIP", "DOM-PROCURE", "DOM-LIBRARY"}
    ),
    "bedblocks": frozenset({"DOM-BED"}),
    "parcelshelf": frozenset({"DOM-PARCEL"}),
}

# 报名组页内构图（ArchiveBrowse；与 portal_home_style 正交）
APPLY_SURFACE_STYLES = [
    {"id": "eventposter", "label": "活动海报墙"},
    {"id": "coursetable", "label": "课表网"},
    {"id": "noticeboard", "label": "启事板"},
    {"id": "tourcard", "label": "线路行程卡"},
]

# 与 apply_thicken.APPLY_DOMAINS 对齐；仅这些域写入/生效 apply_surface_style
APPLY_SURFACE_DOMAINS = frozenset(
    {"DOM-ACTIVITY", "DOM-COURSE", "DOM-LOST", "DOM-TOUR"}
)

APPLY_SURFACE_DOMAIN_DEFAULTS: dict[str, str] = {
    "DOM-ACTIVITY": "eventposter",
    "DOM-COURSE": "coursetable",
    "DOM-LOST": "noticeboard",
    "DOM-TOUR": "tourcard",
}

# 海报/课表/启事/线路隐喻一一绑域
APPLY_SURFACE_STYLE_ALLOWED: dict[str, frozenset[str]] = {
    "eventposter": frozenset({"DOM-ACTIVITY"}),
    "coursetable": frozenset({"DOM-COURSE"}),
    "noticeboard": frozenset({"DOM-LOST"}),
    "tourcard": frozenset({"DOM-TOUR"}),
}

# 互动组页内构图（ArchiveBrowse；与 portal_home_style 正交）
# EXAM/SURVEY/VOTE 有专用页，不进本轴（见选型册 G-1.9）
INTERACT_SURFACE_STYLES = [
    {"id": "profilegrid", "label": "资料卡片墙"},
    {"id": "mutualpick", "label": "双选志愿卡"},
    {"id": "triprow", "label": "行程同行行"},
]

INTERACT_SURFACE_DOMAINS = frozenset(
    {
        "DOM-DATING",
        "DOM-MUTUAL-TUTOR",
        "DOM-MUTUAL-TOPIC",
        "DOM-MUTUAL-TEAM",
        "DOM-CARPOOL",
        "DOM-TIMEBANK",
    }
)

INTERACT_SURFACE_DOMAIN_DEFAULTS: dict[str, str] = {
    "DOM-DATING": "profilegrid",
    "DOM-MUTUAL-TUTOR": "mutualpick",
    "DOM-MUTUAL-TOPIC": "mutualpick",
    "DOM-MUTUAL-TEAM": "mutualpick",
    "DOM-CARPOOL": "triprow",
    "DOM-TIMEBANK": "triprow",
}

# 资料墙/双选卡/行程行隐喻绑域
INTERACT_SURFACE_STYLE_ALLOWED: dict[str, frozenset[str]] = {
    "profilegrid": frozenset({"DOM-DATING"}),
    "mutualpick": frozenset(
        {"DOM-MUTUAL-TUTOR", "DOM-MUTUAL-TOPIC", "DOM-MUTUAL-TEAM"}
    ),
    "triprow": frozenset({"DOM-CARPOOL", "DOM-TIMEBANK"}),
}

# 跟进组页内构图（ArchiveBrowse；与 portal_home_style 正交）
FOLLOW_SURFACE_STYLES = [
    {"id": "pipeline", "label": "阶段看板"},
    {"id": "dossier", "label": "档案行+下次跟进"},
    {"id": "listing", "label": "挂牌价签卡"},
]

# 与 follow_thicken.FOLLOW_DOMAINS 对齐
FOLLOW_SURFACE_DOMAINS = frozenset(
    {
        "DOM-CRM",
        "DOM-EVENT",
        "DOM-ATTEND",
        "DOM-FUND",
        "DOM-RECRUIT",
        "DOM-GRADE",
        "DOM-INTERN",
        "DOM-LISTING",
    }
)

FOLLOW_SURFACE_DOMAIN_DEFAULTS: dict[str, str] = {
    "DOM-CRM": "pipeline",
    "DOM-LISTING": "listing",
    "DOM-EVENT": "dossier",
    "DOM-ATTEND": "dossier",
    "DOM-FUND": "dossier",
    "DOM-RECRUIT": "dossier",
    "DOM-GRADE": "dossier",
    "DOM-INTERN": "dossier",
}

# 阶段看板只客户跟进；挂牌价签只房源；档案行是跟进通用备选
FOLLOW_SURFACE_STYLE_ALLOWED: dict[str, frozenset[str]] = {
    "pipeline": frozenset({"DOM-CRM"}),
    "listing": frozenset({"DOM-LISTING"}),
    "dossier": FOLLOW_SURFACE_DOMAINS,
}

REPAIR_SURFACE_STYLES = [
    {"id": "ticketfeed", "label": "我的工单进度流"},
    {"id": "faultboard", "label": "分类故障看板"},
]

# 与 repair_thicken.REPAIR_DOMAINS 对齐
REPAIR_SURFACE_DOMAINS = frozenset({"DOM-DORM", "DOM-PROPERTY", "DOM-IT"})

REPAIR_SURFACE_DOMAIN_DEFAULTS: dict[str, str] = {
    "DOM-DORM": "ticketfeed",
    "DOM-PROPERTY": "ticketfeed",
    "DOM-IT": "ticketfeed",
}

# 两档都是报修隐喻，三域都能手选；非报修域不进轴
REPAIR_SURFACE_STYLE_ALLOWED: dict[str, frozenset[str]] = {
    "ticketfeed": REPAIR_SURFACE_DOMAINS,
    "faultboard": REPAIR_SURFACE_DOMAINS,
}

APPROVE_SURFACE_STYLES = [
    {"id": "typelist", "label": "事项类型清单+申请"},
    {"id": "inboxsteps", "label": "待审收件箱+步骤条"},
]

# 与 approve_thicken.APPROVE_DOMAINS 对齐
APPROVE_SURFACE_DOMAINS = frozenset(
    {
        "DOM-LABSAFE",
        "DOM-SEAL",
        "DOM-FLEET",
        "DOM-CERT",
        "DOM-PROMO",
        "DOM-FITOUT",
        "DOM-ACAD",
        "DOM-TRIP",
        "DOM-EXPENSE",
        "DOM-CREDIT",
        "DOM-LABOR",
        "DOM-EVAL",
        "DOM-MORAL",
        "DOM-AWARD",
        "DOM-PROCURE",
        "DOM-CLUB",
        "DOM-PROJ",
        "DOM-ETHIC",
        "DOM-PARTY",
        "DOM-CONTRACT",
        "DOM-CARPASS",
        "DOM-VISITOR",
        "DOM-CHECKIN",
    }
)

APPROVE_SURFACE_DOMAIN_DEFAULTS: dict[str, str] = {
    domain: "typelist" for domain in APPROVE_SURFACE_DOMAINS
}

# 两档都是审批隐喻，审批域都能手选；非审批域不进轴
APPROVE_SURFACE_STYLE_ALLOWED: dict[str, frozenset[str]] = {
    "typelist": APPROVE_SURFACE_DOMAINS,
    "inboxsteps": APPROVE_SURFACE_DOMAINS,
}

AUTH_ENTRY_MODES = [
    {"id": "unified", "label": "统一登录（无身份选择）"},
    {"id": "role_pick", "label": "登录页身份选择（毕设经典）"},
    {"id": "split_entry", "label": "门户与管理端分入口"},
]

AUTH_ROLE_WIDGETS = [
    {"id": "radio", "label": "单选分段"},
    {"id": "select", "label": "下拉选择"},
]

# 界面质感（圆角/边框/按钮/密度）：与配色正交
CHROME_STYLES = [
    {"id": "soft", "label": "圆润浮起"},
    {"id": "sharp", "label": "直角扁平"},
    {"id": "pill", "label": "胶囊按钮"},
    {"id": "outline", "label": "粗线线框"},
    {"id": "dense", "label": "紧凑密排"},
    {"id": "ruled", "label": "细线分区"},
]

# 门户壳（导航放置）：与质感正交；管理端仍用工作台
LAYOUT_SHELLS = [
    {"id": "topbar", "label": "顶栏门户"},
    {"id": "rail", "label": "侧栏门户"},
    {"id": "masthead", "label": "通栏抬头"},
    {"id": "island", "label": "居中岛屿"},
]

# 字体配对：标题/正文字族成套挑，与配色·质感·布局正交
TYPE_PAIRINGS = [
    {"id": "clean", "label": "净白无衬线"},
    {"id": "serif", "label": "书香衬线"},
    {"id": "tech", "label": "理工无衬线"},
    {"id": "soft", "label": "圆润人文"},
]


def pick_auth_template(seed: str | None = None) -> str:
    return pick_from_catalog(AUTH_TEMPLATES, seed, "split")


def normalize_auth_template(template: str | None) -> str:
    return normalize_from_catalog(AUTH_TEMPLATES, template, "split")


def pick_auth_entry_mode(seed: str | None = None) -> str:
    return pick_from_catalog(AUTH_ENTRY_MODES, seed, "role_pick")


def normalize_auth_entry_mode(mode: str | None) -> str:
    return normalize_from_catalog(AUTH_ENTRY_MODES, mode, "role_pick")


def pick_auth_role_widget(seed: str | None = None) -> str:
    return pick_from_catalog(AUTH_ROLE_WIDGETS, seed, "radio")


def normalize_auth_role_widget(widget: str | None) -> str:
    return normalize_from_catalog(AUTH_ROLE_WIDGETS, widget, "radio")


def pick_chrome(seed: str | None = None) -> str:
    return pick_from_catalog(CHROME_STYLES, seed, "soft")


def normalize_chrome(chrome: str | None) -> str:
    return normalize_from_catalog(CHROME_STYLES, chrome, "soft")


def pick_layout(seed: str | None = None) -> str:
    return pick_from_catalog(LAYOUT_SHELLS, seed, "topbar")


def normalize_layout(layout: str | None) -> str:
    return normalize_from_catalog(LAYOUT_SHELLS, layout, "topbar")


def pick_typeface(seed: str | None = None) -> str:
    return pick_from_catalog(TYPE_PAIRINGS, seed, "clean")


def normalize_typeface(typeface: str | None) -> str:
    return normalize_from_catalog(TYPE_PAIRINGS, typeface, "clean")


def pick_portal_home_style(seed: str | None = None) -> str:
    return pick_from_catalog(CONTENT_PORTAL_HOME_PICK, seed, "editorial")


def normalize_portal_home_style(style: str | None) -> str:
    return normalize_from_catalog(PORTAL_HOME_STYLES, style, "cards")


def resolve_portal_home_style(
    domain: str,
    override: str | None,
    seed: str | None,
) -> str:
    """手选优先；货架域默认 mall；内容域未选手动则种子抽 cards/editorial；其它域固定 cards。"""
    if override:
        style = normalize_portal_home_style(override)
        if style == "mall" and domain not in MALL_PORTAL_HOME_DOMAINS:
            return "cards"
        return style
    if domain in MALL_PORTAL_HOME_DOMAINS:
        return "mall"
    if domain in CONTENT_PORTAL_HOME_DOMAINS:
        return pick_portal_home_style(f"{seed or ''}|portalHome")
    return "cards"


def pick_content_surface_style(seed: str | None = None) -> str:
    return pick_from_catalog(CONTENT_SURFACE_STYLES, seed, "folio")


def normalize_content_surface_style(style: str | None) -> str:
    return normalize_from_catalog(CONTENT_SURFACE_STYLES, style, "folio")


def resolve_content_surface_style(
    domain: str,
    override: str | None,
    seed: str | None,
) -> str:
    """手选优先；内容域按域默认；非内容域空串（不进学生包分支）。"""
    if domain not in CONTENT_SURFACE_DOMAINS:
        return ""
    if override:
        return normalize_content_surface_style(override)
    default = CONTENT_SURFACE_DOMAIN_DEFAULTS.get(domain, "folio")
    # 未选手选：域默认固定；splitdesk 等靠手选，不靠种子误抽离域默认
    if default in {t["id"] for t in CONTENT_SURFACE_STYLES}:
        return default
    return pick_content_surface_style(f"{seed or ''}|contentSurface")


def pick_trade_surface_style(seed: str | None = None) -> str:
    return pick_from_catalog(TRADE_SURFACE_STYLES, seed, "shelfgrid")


def normalize_trade_surface_style(style: str | None) -> str:
    return normalize_from_catalog(TRADE_SURFACE_STYLES, style, "shelfgrid")


def _surface_style_allowed(
    allowed: dict[str, frozenset[str]],
    style: str,
    domain: str,
) -> bool:
    return domain in allowed.get(style, frozenset())


def resolve_trade_surface_style(
    domain: str,
    override: str | None,
    seed: str | None,
) -> str:
    """手选优先；交易域按域默认；非交易域空串（不进学生包分支）。

    隐喻绑域：showtime 只影院、menuboard 只餐饮；越界手选回落域默认。
    """
    if domain not in TRADE_SURFACE_DOMAINS:
        return ""
    if override:
        style = normalize_trade_surface_style(override)
        if _surface_style_allowed(TRADE_SURFACE_STYLE_ALLOWED, style, domain):
            return style
    default = TRADE_SURFACE_DOMAIN_DEFAULTS.get(domain, "shelfgrid")
    if default in {t["id"] for t in TRADE_SURFACE_STYLES}:
        return default
    return pick_trade_surface_style(f"{seed or ''}|tradeSurface")


def pick_reserve_surface_style(seed: str | None = None) -> str:
    return pick_from_catalog(RESERVE_SURFACE_STYLES, seed, "slotstrip")


def normalize_reserve_surface_style(style: str | None) -> str:
    return normalize_from_catalog(RESERVE_SURFACE_STYLES, style, "slotstrip")


def resolve_reserve_surface_style(
    domain: str,
    override: str | None,
    seed: str | None,
) -> str:
    """手选优先；预约域按域默认；非预约域空串（不进学生包分支）。

    房态只酒店、车型只租车/停车；越界手选回落域默认。
    """
    if domain not in RESERVE_SURFACE_DOMAINS:
        return ""
    if override:
        style = normalize_reserve_surface_style(override)
        if _surface_style_allowed(RESERVE_SURFACE_STYLE_ALLOWED, style, domain):
            return style
    default = RESERVE_SURFACE_DOMAIN_DEFAULTS.get(domain, "slotstrip")
    if default in {t["id"] for t in RESERVE_SURFACE_STYLES}:
        return default
    return pick_reserve_surface_style(f"{seed or ''}|reserveSurface")


def pick_borrow_surface_style(seed: str | None = None) -> str:
    return pick_from_catalog(BORROW_SURFACE_STYLES, seed, "bookshelf")


def normalize_borrow_surface_style(style: str | None) -> str:
    return normalize_from_catalog(BORROW_SURFACE_STYLES, style, "bookshelf")


def resolve_borrow_surface_style(
    domain: str,
    override: str | None,
    seed: str | None,
) -> str:
    """手选优先；借用域按域默认；非借用域空串（不进学生包分支）。

    书架/床位/驿站绑域；台账行留给库存类；越界手选回落域默认。
    """
    if domain not in BORROW_SURFACE_DOMAINS:
        return ""
    if override:
        style = normalize_borrow_surface_style(override)
        if _surface_style_allowed(BORROW_SURFACE_STYLE_ALLOWED, style, domain):
            return style
    default = BORROW_SURFACE_DOMAIN_DEFAULTS.get(domain, "bookshelf")
    if default in {t["id"] for t in BORROW_SURFACE_STYLES}:
        return default
    return pick_borrow_surface_style(f"{seed or ''}|borrowSurface")


def pick_apply_surface_style(seed: str | None = None) -> str:
    return pick_from_catalog(APPLY_SURFACE_STYLES, seed, "eventposter")


def normalize_apply_surface_style(style: str | None) -> str:
    return normalize_from_catalog(APPLY_SURFACE_STYLES, style, "eventposter")


def resolve_apply_surface_style(
    domain: str,
    override: str | None,
    seed: str | None,
) -> str:
    """手选优先；报名域按域默认；非报名域空串（不进学生包分支）。

    海报/课表/启事/线路一一绑域；越界手选回落域默认。
    """
    if domain not in APPLY_SURFACE_DOMAINS:
        return ""
    if override:
        style = normalize_apply_surface_style(override)
        if _surface_style_allowed(APPLY_SURFACE_STYLE_ALLOWED, style, domain):
            return style
    default = APPLY_SURFACE_DOMAIN_DEFAULTS.get(domain, "eventposter")
    if default in {t["id"] for t in APPLY_SURFACE_STYLES}:
        return default
    return pick_apply_surface_style(f"{seed or ''}|applySurface")


def pick_interact_surface_style(seed: str | None = None) -> str:
    return pick_from_catalog(INTERACT_SURFACE_STYLES, seed, "profilegrid")


def normalize_interact_surface_style(style: str | None) -> str:
    return normalize_from_catalog(INTERACT_SURFACE_STYLES, style, "profilegrid")


def resolve_interact_surface_style(
    domain: str,
    override: str | None,
    seed: str | None,
) -> str:
    """手选优先；互动浏览域按域默认；非本轴域空串（含 EXAM/SURVEY/VOTE）。

    资料墙/双选卡/行程行绑域；越界手选回落域默认。
    """
    if domain not in INTERACT_SURFACE_DOMAINS:
        return ""
    if override:
        style = normalize_interact_surface_style(override)
        if _surface_style_allowed(INTERACT_SURFACE_STYLE_ALLOWED, style, domain):
            return style
    default = INTERACT_SURFACE_DOMAIN_DEFAULTS.get(domain, "profilegrid")
    if default in {t["id"] for t in INTERACT_SURFACE_STYLES}:
        return default
    return pick_interact_surface_style(f"{seed or ''}|interactSurface")


def pick_follow_surface_style(seed: str | None = None) -> str:
    return pick_from_catalog(FOLLOW_SURFACE_STYLES, seed, "dossier")


def normalize_follow_surface_style(style: str | None) -> str:
    return normalize_from_catalog(FOLLOW_SURFACE_STYLES, style, "dossier")


def resolve_follow_surface_style(
    domain: str,
    override: str | None,
    seed: str | None,
) -> str:
    """手选优先；跟进域按域默认；非跟进域空串。

    阶段看板只 CRM，挂牌价签只 LISTING；越界手选回落域默认。
    """
    if domain not in FOLLOW_SURFACE_DOMAINS:
        return ""
    if override:
        style = normalize_follow_surface_style(override)
        if _surface_style_allowed(FOLLOW_SURFACE_STYLE_ALLOWED, style, domain):
            return style
    default = FOLLOW_SURFACE_DOMAIN_DEFAULTS.get(domain, "dossier")
    if default in {t["id"] for t in FOLLOW_SURFACE_STYLES}:
        return default
    return pick_follow_surface_style(f"{seed or ''}|followSurface")


def pick_repair_surface_style(seed: str | None = None) -> str:
    return pick_from_catalog(REPAIR_SURFACE_STYLES, seed, "ticketfeed")


def normalize_repair_surface_style(style: str | None) -> str:
    return normalize_from_catalog(REPAIR_SURFACE_STYLES, style, "ticketfeed")


def resolve_repair_surface_style(
    domain: str,
    override: str | None,
    seed: str | None,
) -> str:
    """手选优先；报修域默认进度流；非报修域空串。

    进度流与分类看板都只给宿舍/物业/IT；越界手选回落进度流。
    """
    if domain not in REPAIR_SURFACE_DOMAINS:
        return ""
    if override:
        style = normalize_repair_surface_style(override)
        if _surface_style_allowed(REPAIR_SURFACE_STYLE_ALLOWED, style, domain):
            return style
    default = REPAIR_SURFACE_DOMAIN_DEFAULTS.get(domain, "ticketfeed")
    if default in {t["id"] for t in REPAIR_SURFACE_STYLES}:
        return default
    return pick_repair_surface_style(f"{seed or ''}|repairSurface")


def pick_approve_surface_style(seed: str | None = None) -> str:
    return pick_from_catalog(APPROVE_SURFACE_STYLES, seed, "typelist")


def normalize_approve_surface_style(style: str | None) -> str:
    return normalize_from_catalog(APPROVE_SURFACE_STYLES, style, "typelist")


def resolve_approve_surface_style(
    domain: str,
    override: str | None,
    seed: str | None,
) -> str:
    """手选优先；审批域默认事项清单；非审批域空串。

    事项清单与待审步骤条都只给审批域；越界手选回落事项清单。
    """
    if domain not in APPROVE_SURFACE_DOMAINS:
        return ""
    if override:
        style = normalize_approve_surface_style(override)
        if _surface_style_allowed(APPROVE_SURFACE_STYLE_ALLOWED, style, domain):
            return style
    default = APPROVE_SURFACE_DOMAIN_DEFAULTS.get(domain, "typelist")
    if default in {t["id"] for t in APPROVE_SURFACE_STYLES}:
        return default
    return pick_approve_surface_style(f"{seed or ''}|approveSurface")


def all_theme_ids() -> set[str]:
    ids = set(THEME_ALIASES.keys())
    for dom in DOMAINS.values():
        for t in dom.get("themes") or []:
            ids.add(t["id"])
    return ids


def is_dark_theme(theme: str | None) -> bool:
    """深色行业配色（与骨架 themes.css / themeScheme.js 一致）。"""
    tid = THEME_ALIASES.get(theme or "", theme or "")
    if not tid:
        return False
    if tid.endswith("-night") or tid == "theme-night":
        return True
    return tid in {"media-cinema", "music-vinyl"}


def normalize_theme(theme: str, domain: str) -> str:
    theme = THEME_ALIASES.get(theme, theme)
    allowed = {t["id"] for t in themes_for_domain(domain)}
    if theme in allowed:
        return theme
    return default_theme(domain)


# 扁平表：id → label（校验 / 展示）
THEMES: dict[str, str] = {}
for _dom in DOMAINS.values():
    for _t in _dom.get("themes") or []:
        THEMES[_t["id"]] = _t["label"]
for _old, _new in THEME_ALIASES.items():
    THEMES[_old] = THEMES.get(_new, _old)
