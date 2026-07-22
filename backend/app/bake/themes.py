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
]

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
