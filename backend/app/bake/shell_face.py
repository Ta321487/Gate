# -*- coding: utf-8 -*-
"""门户脸：检索占位、卡面叙事、软皮/域壳色（与 surface_style 正交）。

规矩见 docs/domain-group-ui-styles.md §0.0 / §2.5 / §3.0.4。
不新开 surface id；不发明 dense/airy/band。
68 个 DOM 均有显式占位 / voice / 壳色（审批组可共用色板但占位分域）。

壳强调色真源：有行业配色（theme）时，从骨架 themes/*.css 派生 brand/accent/cover；
货架皮/域表只作无 theme 时的兜底，禁止健身橙等与下拉配色打架。
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any


def _c(brand: str, accent: str, bg: str, ink: str, surface: str = "#FFFFFF") -> dict[str, str]:
    """壳色角色。cover/glow 由 brand·accent 派生，供登录氛围与首屏横幅兜底，避免主题默认青绿。"""
    return {
        "brand": brand,
        "accent": accent,
        "bg": bg,
        "surface": surface,
        "ink": ink,
        "cover": f"linear-gradient(160deg, {accent}, {brand})",
        "glow": accent,
    }


_THEME_BLOCK_RE = re.compile(
    r'\[data-theme=(["\'])([^"\']+)\1\]\s*\{([^}]*)\}',
    re.DOTALL,
)
_CSS_VAR_RE = re.compile(
    r"--portal-(brand|accent|bg|surface|ink|cover)\s*:\s*([^;]+);",
)


def _themes_css_dir() -> Path:
    # backend/app/bake → 仓库根 / skeletons/...
    return (
        Path(__file__).resolve().parents[3]
        / "skeletons"
        / "baseline"
        / "frontend"
        / "src"
        / "styles"
        / "themes"
    )


@lru_cache(maxsize=1)
def _theme_token_map() -> dict[str, dict[str, str]]:
    """从学生包 themes CSS 读各行业配色的 portal 变量（与预览同源）。"""
    root = _themes_css_dir()
    out: dict[str, dict[str, str]] = {}
    if not root.is_dir():
        return out
    for path in sorted(root.glob("*.css")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in _THEME_BLOCK_RE.finditer(text):
            tid = (m.group(2) or "").strip()
            body = m.group(3) or ""
            if not tid:
                continue
            toks: dict[str, str] = {}
            for vm in _CSS_VAR_RE.finditer(body):
                toks[vm.group(1)] = vm.group(2).strip()
            if toks.get("brand") and toks.get("accent"):
                out[tid] = toks
    return out


def shell_colors_from_theme(theme_id: str | None) -> dict[str, str] | None:
    """行业配色 → 壳强调色。读不到 CSS 则 None，由域/货架兜底。"""
    tid = (theme_id or "").strip()
    if not tid:
        return None
    from app.bake.themes import THEME_ALIASES

    tid = THEME_ALIASES.get(tid, tid)
    toks = _theme_token_map().get(tid)
    if not toks:
        return None
    brand = toks["brand"]
    accent = toks["accent"]
    cover = toks.get("cover") or f"linear-gradient(160deg, {accent}, {brand})"
    return {
        "brand": brand,
        "accent": accent,
        "bg": toks.get("bg") or "#F4F6F8",
        "surface": toks.get("surface") or "#FFFFFF",
        "ink": toks.get("ink") or "#1A1E24",
        "cover": cover,
        "glow": accent,
    }


# 优先开顶栏检索：有 archive 时自动开（审批收件箱主路径弱化，不进本集）
_SEARCH_ARCHIVE_DOMAINS = frozenset(
    {
        # 借用
        "DOM-LIBRARY",
        "DOM-EQUIP",
        "DOM-ASSET",
        "DOM-PARCEL",
        "DOM-BED",
        "DOM-INSTRUMENT",
        "DOM-TIMEBANK",
        # 跟进
        "DOM-CRM",
        "DOM-LISTING",
        "DOM-EVENT",
        "DOM-INTERN",
        # 报名
        "DOM-ACTIVITY",
        "DOM-COURSE",
        "DOM-LOST",
        "DOM-TOUR",
        "DOM-RECRUIT",
        # 交易
        "DOM-SHOP",
        "DOM-FOOD",
        "DOM-CINEMA",
        # 预约
        "DOM-HOSPITAL",
        "DOM-MEETING",
        "DOM-SALON",
        "DOM-PARKING",
        "DOM-HOTEL",
        "DOM-CARRENT",
        # 内容
        "DOM-MEDIA",
        "DOM-MUSIC",
        "DOM-FORUM",
        "DOM-BLOG",
        "DOM-DOCLIB",
        # 互动（考试/问卷/投票专用页，仍有 archive 种子时开检索）
        "DOM-DATING",
        "DOM-MUTUAL-TUTOR",
        "DOM-MUTUAL-TOPIC",
        "DOM-MUTUAL-TEAM",
        "DOM-CARPOOL",
        "DOM-EXAM",
        "DOM-SURVEY",
        "DOM-VOTE",
        # 审批里偏「项目/课程清单浏览」的仍开
        "DOM-GRADE",
        "DOM-EVAL",
        "DOM-CREDIT",
        "DOM-LABOR",
        "DOM-MORAL",
        "DOM-AWARD",
        "DOM-FUND",
        "DOM-LABSAFE",
        "DOM-PROCURE",
        "DOM-PROJ",
    }
)

# 域默认检索占位（学生可见，禁工厂腔）——68 域全覆盖
_DOMAIN_SEARCH_PLACEHOLDER: dict[str, str] = {
    "DOM-LIBRARY": "书名 / 作者",
    "DOM-EQUIP": "器材名称",
    "DOM-ASSET": "物资名称",
    "DOM-PARCEL": "取件码 / 姓名",
    "DOM-BED": "楼栋 / 床位",
    "DOM-INSTRUMENT": "仪器名称",
    "DOM-TIMEBANK": "服务事项",
    "DOM-CRM": "客户名称",
    "DOM-LISTING": "房源关键词",
    "DOM-EVENT": "事件关键词",
    "DOM-INTERN": "岗位 / 周报",
    "DOM-DORM": "工单 / 地点",
    "DOM-PROPERTY": "工单 / 房屋",
    "DOM-IT": "工单 / 故障",
    "DOM-ACTIVITY": "活动名称",
    "DOM-COURSE": "课程名称",
    "DOM-LOST": "启事关键词",
    "DOM-TOUR": "线路名称",
    "DOM-RECRUIT": "岗位 / 公司",
    "DOM-SEAL": "用章事项",
    "DOM-CERT": "证明类型",
    "DOM-CLUB": "社团名称",
    "DOM-PARTY": "发展阶段",
    "DOM-FLEET": "用车申请",
    "DOM-TRIP": "出差事项",
    "DOM-PROMO": "宣传事项",
    "DOM-FITOUT": "装修区域",
    "DOM-ACAD": "学籍事项",
    "DOM-EXPENSE": "报销单号 / 事由",
    "DOM-FUND": "资助项目",
    "DOM-CONTRACT": "合同名称",
    "DOM-PROJ": "项目名称",
    "DOM-ETHIC": "审查事项",
    "DOM-ATTEND": "假条 / 事由",
    "DOM-GRADE": "课程名称",
    "DOM-EVAL": "评教课程",
    "DOM-CREDIT": "认定项目",
    "DOM-LABOR": "劳动项目",
    "DOM-MORAL": "综测指标",
    "DOM-AWARD": "获奖类型",
    "DOM-LABSAFE": "实验室名称",
    "DOM-PROCURE": "申购物资",
    "DOM-VISITOR": "访客姓名",
    "DOM-CARPASS": "车牌号",
    "DOM-CHECKIN": "寝室 / 归寝",
    "DOM-SHOP": "商品名称",
    "DOM-FOOD": "菜名 / 档口",
    "DOM-CINEMA": "影片 / 场次",
    "DOM-HOSPITAL": "科室 / 医生",
    "DOM-MEETING": "场地名称",
    "DOM-SALON": "服务项目",
    "DOM-PARKING": "车位",
    "DOM-HOTEL": "房型",
    "DOM-CARRENT": "车型",
    "DOM-MEDIA": "片名",
    "DOM-MUSIC": "歌名 / 歌手",
    "DOM-FORUM": "帖子标题",
    "DOM-BLOG": "文章标题",
    "DOM-DOCLIB": "资料名称",
    "DOM-DATING": "资料关键词",
    "DOM-MUTUAL-TUTOR": "导师 / 方向",
    "DOM-MUTUAL-TOPIC": "选题关键词",
    "DOM-MUTUAL-TEAM": "组队关键词",
    "DOM-EXAM": "试卷 / 题目",
    "DOM-SURVEY": "问卷标题",
    "DOM-VOTE": "候选人 / 选项",
    "DOM-CARPOOL": "行程 / 地点",
    "DOM-GENERIC": "关键词",
}

_SHOP_KIND_PLACEHOLDER: dict[str, str] = {
    "farm": "商品 / 产地",
    "print": "文印商品",
    "retail_pharmacy": "药品 / 商品",
    "retail_pet": "宠物用品",
    "retail_auto": "汽配名称",
    "retail_beauty": "美妆名称",
    "retail_market": "商品名称",
    "retail_anime": "周边商品",
    "retail_office": "办公用品",
    "retail_agri": "农资名称",
    "retail_gift": "礼品名称",
    "retail_fitness": "器材名称",
    "retail_sports": "运动用品",
}

# 域默认叙事 —— 68 域全覆盖
_DOMAIN_CARD_VOICE: dict[str, str] = {
    "DOM-LIBRARY": "catalog",
    "DOM-EQUIP": "catalog",
    "DOM-ASSET": "catalog",
    "DOM-PARCEL": "board",
    "DOM-BED": "board",
    "DOM-INSTRUMENT": "catalog",
    "DOM-TIMEBANK": "board",
    "DOM-CRM": "board",
    "DOM-LISTING": "catalog",
    "DOM-EVENT": "board",
    "DOM-INTERN": "catalog",
    "DOM-DORM": "board",
    "DOM-PROPERTY": "board",
    "DOM-IT": "board",
    "DOM-ACTIVITY": "story",
    "DOM-COURSE": "catalog",
    "DOM-LOST": "story",
    "DOM-TOUR": "story",
    "DOM-RECRUIT": "catalog",
    "DOM-SEAL": "catalog",
    "DOM-CERT": "catalog",
    "DOM-CLUB": "catalog",
    "DOM-PARTY": "catalog",
    "DOM-FLEET": "board",
    "DOM-TRIP": "board",
    "DOM-PROMO": "board",
    "DOM-FITOUT": "board",
    "DOM-ACAD": "catalog",
    "DOM-EXPENSE": "board",
    "DOM-FUND": "catalog",
    "DOM-CONTRACT": "catalog",
    "DOM-PROJ": "catalog",
    "DOM-ETHIC": "catalog",
    "DOM-ATTEND": "board",
    "DOM-GRADE": "catalog",
    "DOM-EVAL": "story",
    "DOM-CREDIT": "catalog",
    "DOM-LABOR": "catalog",
    "DOM-MORAL": "catalog",
    "DOM-AWARD": "catalog",
    "DOM-LABSAFE": "catalog",
    "DOM-PROCURE": "catalog",
    "DOM-VISITOR": "board",
    "DOM-CARPASS": "board",
    "DOM-CHECKIN": "board",
    "DOM-SHOP": "catalog",
    "DOM-FOOD": "story",
    "DOM-CINEMA": "board",
    "DOM-HOSPITAL": "board",
    "DOM-MEETING": "board",
    "DOM-SALON": "story",
    "DOM-PARKING": "board",
    "DOM-HOTEL": "board",
    "DOM-CARRENT": "catalog",
    "DOM-MEDIA": "story",
    "DOM-MUSIC": "story",
    "DOM-FORUM": "story",
    "DOM-BLOG": "story",
    "DOM-DOCLIB": "catalog",
    "DOM-DATING": "story",
    "DOM-MUTUAL-TUTOR": "catalog",
    "DOM-MUTUAL-TOPIC": "catalog",
    "DOM-MUTUAL-TEAM": "catalog",
    "DOM-EXAM": "catalog",
    "DOM-SURVEY": "catalog",
    "DOM-VOTE": "story",
    "DOM-CARPOOL": "board",
    "DOM-GENERIC": "catalog",
}

_SHOP_KIND_VOICE: dict[str, str] = {
    "farm": "story",
    "print": "catalog",
    "retail_pharmacy": "catalog",
    "retail_pet": "story",
    "retail_auto": "catalog",
    "retail_beauty": "story",
    "retail_market": "story",
    "retail_anime": "story",
    "retail_office": "catalog",
    "retail_agri": "catalog",
    "retail_gift": "story",
    "retail_fitness": "catalog",
    "retail_sports": "catalog",
}

_CARD_VOICES = frozenset({"catalog", "story", "board"})

# 壳色 —— 对齐 §3 域表；组内可近但禁止 55 域共用同一默认
_APPROVE_BASE = _c("#243044", "#4A6280", "#F4F5F7", "#1A1E26")
_APPROVE_STEPS = _c("#2A3040", "#5A6A80", "#F4F5F7", "#1A1E26")
_APPROVE_CREDIT = _c("#243848", "#4A6878", "#F4F6F7", "#1A2228")
_MUTUAL = _c("#3A4050", "#5A6280", "#F5F5F8", "#1E1C24")

_DOMAIN_SHELL_COLORS: dict[str, dict[str, str]] = {
    # G-3.1 借用
    "DOM-LIBRARY": _c("#2C4A6E", "#4A6E8C", "#F4F6F8", "#1A2330"),
    "DOM-EQUIP": _c("#2A3F55", "#4D6A82", "#F4F6F8", "#1A2330"),
    "DOM-ASSET": _c("#335064", "#5A7A90", "#F4F6F8", "#1A2330"),
    "DOM-PARCEL": _c("#3A4A58", "#6B7C8C", "#F4F6F8", "#1A2330"),
    "DOM-BED": _c("#3D4F5C", "#5C7A88", "#F4F6F8", "#1A2330"),
    "DOM-INSTRUMENT": _c("#2C4558", "#4A7088", "#F4F6F8", "#1A2330"),
    "DOM-TIMEBANK": _c("#2F4A42", "#4A7A68", "#F3F7F5", "#1A2824"),
    # G-3.2 跟进
    "DOM-CRM": _c("#1E4A45", "#3D7A72", "#F3F6F5", "#1A2422"),
    "DOM-LISTING": _c("#3A4A3E", "#6A8A5A", "#F5F7F3", "#1A2420"),
    "DOM-EVENT": _c("#3A4550", "#5A6A78", "#F4F5F7", "#1A1E26"),
    "DOM-INTERN": _c("#2A4850", "#3E7880", "#F3F7F7", "#1A2828"),
    # G-3.3 报修
    "DOM-DORM": _c("#1A5C62", "#3A8A90", "#F2F7F7", "#1A2828"),
    "DOM-PROPERTY": _c("#1A5C62", "#3A8A7A", "#F2F7F6", "#1A2828"),
    "DOM-IT": _c("#1A4A62", "#3A6A90", "#F2F6F8", "#1A2430"),
    # G-3.4 报名
    "DOM-ACTIVITY": _c("#2A4A55", "#3E7A78", "#F4F7F7", "#1C2830"),
    "DOM-COURSE": _c("#2A4558", "#3E6A88", "#F4F6F8", "#1C2830"),
    "DOM-LOST": _c("#4A4A3A", "#7A7A4A", "#F7F6F2", "#2A2820"),
    "DOM-TOUR": _c("#3A4A5A", "#4A7A9A", "#F4F6F8", "#1A2430"),
    "DOM-RECRUIT": _c("#2A4858", "#3E7088", "#F4F7F8", "#1C2830"),
    # G-3.5 审批（同组近色，占位已分域）
    "DOM-SEAL": dict(_APPROVE_BASE),
    "DOM-CERT": dict(_APPROVE_BASE),
    "DOM-CLUB": dict(_APPROVE_BASE),
    "DOM-PARTY": dict(_APPROVE_BASE),
    "DOM-FLEET": dict(_APPROVE_BASE),
    "DOM-TRIP": dict(_APPROVE_BASE),
    "DOM-PROMO": dict(_APPROVE_BASE),
    "DOM-FITOUT": dict(_APPROVE_BASE),
    "DOM-ACAD": dict(_APPROVE_BASE),
    "DOM-EXPENSE": dict(_APPROVE_STEPS),
    "DOM-FUND": dict(_APPROVE_STEPS),
    "DOM-CONTRACT": dict(_APPROVE_STEPS),
    "DOM-PROJ": dict(_APPROVE_STEPS),
    "DOM-ETHIC": dict(_APPROVE_STEPS),
    "DOM-ATTEND": _c("#2A3848", "#4A6880", "#F4F5F7", "#1A1E26"),
    "DOM-GRADE": _c("#2A3440", "#4A6078", "#F4F5F7", "#1A1E26"),
    "DOM-EVAL": _c("#2A3844", "#5A6878", "#F4F5F7", "#1A1E26"),
    "DOM-CREDIT": dict(_APPROVE_CREDIT),
    "DOM-LABOR": dict(_APPROVE_CREDIT),
    "DOM-MORAL": dict(_APPROVE_CREDIT),
    "DOM-AWARD": dict(_APPROVE_CREDIT),
    "DOM-LABSAFE": _c("#1E3A48", "#3A6A78", "#F3F6F7", "#1A2428"),
    "DOM-PROCURE": _c("#2A3840", "#5A6870", "#F4F5F6", "#1A1E22"),
    "DOM-VISITOR": _c("#2A3448", "#4A6080", "#F4F5F7", "#1A1E26"),
    "DOM-CARPASS": _c("#2A3448", "#4A6080", "#F4F5F7", "#1A1E26"),
    "DOM-CHECKIN": _c("#2A3A48", "#4A6878", "#F4F5F7", "#1A1E26"),
    # G-3.6 交易（SHOP 再被软皮覆盖）
    "DOM-SHOP": _c("#2A3038", "#5B6B7A", "#F5F6F8", "#1A1E24"),
    "DOM-FOOD": _c("#8C4A32", "#C4784A", "#F8F4EF", "#2C2416"),
    "DOM-CINEMA": _c("#2C2A33", "#C4A574", "#F6F5F7", "#1A1820"),
    # G-3.7 预约
    "DOM-HOSPITAL": _c("#1A5A66", "#2F8A8A", "#F2F8F8", "#163033"),
    "DOM-MEETING": _c("#1A4A5A", "#2F7A8A", "#F2F7F8", "#163033"),
    "DOM-SALON": _c("#5A3A4A", "#8A5A6A", "#F8F4F6", "#2A1C24"),
    "DOM-PARKING": _c("#2A3A4A", "#4A6A7A", "#F4F6F8", "#1A1E24"),
    "DOM-HOTEL": _c("#3A3A4A", "#8A7A5A", "#F7F6F4", "#1A1820"),
    "DOM-CARRENT": _c("#2A3540", "#4A6A7A", "#F4F6F8", "#1A1E24"),
    # G-3.8 内容
    "DOM-BLOG": _c("#3D4A3A", "#5C7056", "#F6F5F1", "#242820"),
    "DOM-FORUM": _c("#3A4240", "#5A6A60", "#F5F6F4", "#242820"),
    "DOM-MEDIA": _c("#2A2A38", "#6A5A8A", "#F5F4F8", "#1A1824"),
    "DOM-MUSIC": _c("#2A3040", "#5A7A8A", "#F4F6F8", "#1A1E24"),
    "DOM-DOCLIB": _c("#3A4038", "#5A6850", "#F6F6F2", "#242820"),
    # G-3.9 互动
    "DOM-DATING": _c("#3E4454", "#6A6278", "#F5F4F7", "#1E1C24"),
    "DOM-MUTUAL-TUTOR": dict(_MUTUAL),
    "DOM-MUTUAL-TOPIC": dict(_MUTUAL),
    "DOM-MUTUAL-TEAM": dict(_MUTUAL),
    "DOM-EXAM": _c("#2A3040", "#4A6080", "#F4F5F7", "#1A1E26"),
    "DOM-SURVEY": _c("#2A3840", "#4A6870", "#F4F6F5", "#1A2224"),
    "DOM-VOTE": _c("#3A3848", "#6A5A78", "#F6F5F8", "#1E1C24"),
    "DOM-CARPOOL": _c("#2A3A48", "#4A6A78", "#F4F6F8", "#1A1E24"),
    # 兜底
    "DOM-GENERIC": _c("#2A3540", "#4A6A7A", "#F4F6F8", "#1A1E24"),
}

_SHOP_KIND_SHELL_COLORS: dict[str, dict[str, str]] = {
    "farm": _c("#1F6B4A", "#3D8F62", "#F3F7F4", "#1C2B24"),
    "print": _c("#2A3540", "#5A6A78", "#F5F6F8", "#1A1E24"),
    "retail_pharmacy": _c("#1A4A58", "#3A7A88", "#F3F7F8", "#1A2830"),
    "retail_pet": _c("#4A3A2A", "#8A6A4A", "#F7F5F2", "#2A2418"),
    "retail_auto": _c("#2A3038", "#5A6A78", "#F4F5F7", "#1A1E24"),
    "retail_beauty": _c("#5A3A48", "#8A5A6A", "#F8F4F6", "#2A1C24"),
    "retail_market": _c("#3A4A3A", "#6A8A5A", "#F5F7F3", "#1A2420"),
    "retail_anime": _c("#3A2A48", "#7A5A9A", "#F6F4F8", "#1E1A24"),
    "retail_office": _c("#2A3848", "#4A6880", "#F4F5F7", "#1A1E26"),
    "retail_agri": _c("#3A4A2A", "#6A8A4A", "#F5F7F2", "#1A2418"),
    "retail_gift": _c("#5A3A3A", "#8A5A5A", "#F8F4F4", "#2A1C1C"),
    "retail_fitness": _c("#12151A", "#E85D04", "#F4F5F7", "#1A1D21"),
    "retail_sports": _c("#1A3040", "#3A7A8A", "#F3F6F7", "#1A2428"),
}

_DEFAULT_SHELL = _c("#2A3540", "#4A6A7A", "#F4F6F8", "#1A1E24")


def _shop_kind_key(title: str, proposal_text: str) -> str:
    from app.bake.scene_scan import shop_catalog_kind, shop_product_kind

    pk = shop_product_kind(title or "", proposal_text or "")
    if pk == "farm":
        return "farm"
    ck = shop_catalog_kind(title or "", proposal_text or "")
    if ck and ck.startswith("retail_"):
        return ck
    if ck == "print":
        return "print"
    return pk or ""


def top_search_placeholder(
    domain: str,
    title: str = "",
    proposal_text: str = "",
) -> str:
    if domain == "DOM-SHOP":
        kind = _shop_kind_key(title, proposal_text)
        if kind in _SHOP_KIND_PLACEHOLDER:
            return _SHOP_KIND_PLACEHOLDER[kind]
    return _DOMAIN_SEARCH_PLACEHOLDER.get(domain) or "关键词"


def should_enable_global_search(
    domain: str,
    capabilities: list[str] | None,
    flags_from_scan: bool,
) -> bool:
    """扫词命中，或优先域且具备 archive 能力。"""
    if flags_from_scan:
        return True
    caps = set(capabilities or [])
    if "archive" not in caps:
        return False
    return domain in _SEARCH_ARCHIVE_DOMAINS


def resolve_card_voice(
    domain: str,
    title: str = "",
    proposal_text: str = "",
    override: str | None = None,
) -> str:
    if override:
        o = str(override).strip().lower()
        if o in _CARD_VOICES:
            return o
    if domain == "DOM-SHOP":
        kind = _shop_kind_key(title, proposal_text)
        if kind in _SHOP_KIND_VOICE:
            return _SHOP_KIND_VOICE[kind]
    return _DOMAIN_CARD_VOICE.get(domain) or "catalog"


def resolve_shell_colors(
    domain: str,
    title: str = "",
    proposal_text: str = "",
    theme: str | None = None,
) -> dict[str, str]:
    """有 theme 时跟行业配色；否则才用域/货架皮默认（匹配早期无 theme 的兜底）。"""
    derived = shell_colors_from_theme(theme)
    if derived:
        return derived
    if domain == "DOM-SHOP":
        kind = _shop_kind_key(title, proposal_text)
        if kind in _SHOP_KIND_SHELL_COLORS:
            return dict(_SHOP_KIND_SHELL_COLORS[kind])
    base = _DOMAIN_SHELL_COLORS.get(domain) or _DEFAULT_SHELL
    return dict(base)


def shell_colors_for_pack(
    spec: dict[str, Any] | None,
    *,
    theme: str | None = None,
    domain: str | None = None,
    title: str | None = None,
) -> dict[str, str]:
    """出包时按当前行业配色重算壳色（避免 spec 里旧货架橙盖住下拉选中的蓝）。"""
    sp = spec if isinstance(spec, dict) else {}
    tid = (theme or sp.get("theme") or "").strip() or None
    dom = str(domain or sp.get("domain") or "")
    tit = str(title or sp.get("title") or "")
    return resolve_shell_colors(dom, tit, tit, theme=tid)


# 农产/文印/花店等「货架市集」皮：顶栏短链 + 右侧图标栏（淘宝感，矢量勿表情）
# 健身等零售软皮：店面短链 + 角标 + 头像「我的」（勿抄农产右侧栏）
_SHELL_NAV_MARKETPLACE_KINDS = frozenset(
    {
        "farm",
        "print",
        "flowers",
        "errand",
        "points",
        "campus",
        "retail",  # 未点名 niche 的通用零售，仍走市集栏
    }
)


def resolve_shell_nav_style(
    domain: str,
    title: str = "",
    proposal_text: str = "",
    override: str | None = None,
) -> str:
    """``marketplace`` | ``storefront``。非 SHOP 恒为 storefront。"""
    if override:
        o = str(override).strip().lower()
        if o in ("marketplace", "storefront"):
            return o
    if domain != "DOM-SHOP":
        return "storefront"
    kind = _shop_kind_key(title, proposal_text)
    if kind in _SHELL_NAV_MARKETPLACE_KINDS:
        return "marketplace"
    # retail_fitness / retail_pharmacy / … → 店面壳
    if kind.startswith("retail_"):
        return "storefront"
    return "marketplace"


def known_face_domains() -> frozenset[str]:
    """三表并集，供测试断言全覆盖。"""
    return frozenset(_DOMAIN_SEARCH_PLACEHOLDER) | frozenset(
        _DOMAIN_CARD_VOICE
    ) | frozenset(_DOMAIN_SHELL_COLORS)


def apply_shell_face_to_spec(
    spec: dict[str, Any],
    proposal_text: str = "",
) -> dict[str, Any]:
    """写入 card_voice、shell_colors、shell_nav_style、domain_group；检索占位由 list_crosscut。"""
    from app.bake.domains import domain_group_of

    domain = str(spec.get("domain") or "")
    title = str(spec.get("title") or "")
    body = proposal_text or title
    theme = str(spec.get("theme") or "").strip() or None
    voice = resolve_card_voice(domain, title, body, spec.get("card_voice"))
    colors = resolve_shell_colors(domain, title, body, theme=theme)
    nav = resolve_shell_nav_style(domain, title, body, spec.get("shell_nav_style"))
    group = domain_group_of(domain)
    return {
        **spec,
        "card_voice": voice,
        "shell_colors": colors,
        "shell_nav_style": nav,
        "domain_group": group,
    }
