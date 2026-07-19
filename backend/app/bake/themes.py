"""主题 / 登录版式映射与规范化。"""

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


# 登录/注册版式：bake 时随机写入 spec，交付后固定
AUTH_TEMPLATES = [
    {"id": "split", "label": "双栏书香"},
    {"id": "mirror", "label": "镜像入口"},
    {"id": "center", "label": "雾面居中"},
    {"id": "ribbon", "label": "顶栏色带"},
    {"id": "ledge", "label": "浮台登录"},
    {"id": "folio", "label": "对开页"},
]

# 登录入口：统一 / 身份选择 / 门户与管理分端（交付后固定）
AUTH_ENTRY_MODES = [
    {"id": "unified", "label": "统一登录（无身份选择）"},
    {"id": "role_pick", "label": "登录页身份选择（毕设经典）"},
    {"id": "split_entry", "label": "门户与管理端分入口"},
]

# 身份控件：仅 role_pick / split 管理端会用到
AUTH_ROLE_WIDGETS = [
    {"id": "radio", "label": "单选分段"},
    {"id": "select", "label": "下拉选择"},
]


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


def pick_auth_template(seed: str | None = None) -> str:
    ids = [t["id"] for t in AUTH_TEMPLATES]
    return _pick_by_seed(ids, seed, "split")


def normalize_auth_template(template: str | None) -> str:
    ids = {t["id"] for t in AUTH_TEMPLATES}
    if template and template in ids:
        return template
    return "split"


def pick_auth_entry_mode(seed: str | None = None) -> str:
    ids = [t["id"] for t in AUTH_ENTRY_MODES]
    return _pick_by_seed(ids, seed, "role_pick")


def normalize_auth_entry_mode(mode: str | None) -> str:
    ids = {t["id"] for t in AUTH_ENTRY_MODES}
    if mode and mode in ids:
        return mode
    return "role_pick"


def pick_auth_role_widget(seed: str | None = None) -> str:
    ids = [t["id"] for t in AUTH_ROLE_WIDGETS]
    return _pick_by_seed(ids, seed, "radio")


def normalize_auth_role_widget(widget: str | None) -> str:
    ids = {t["id"] for t in AUTH_ROLE_WIDGETS}
    if widget and widget in ids:
        return widget
    return "radio"


def all_theme_ids() -> set[str]:
    ids = set(THEME_ALIASES.keys())
    for dom in DOMAINS.values():
        for t in dom.get("themes") or []:
            ids.add(t["id"])
    return ids


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
