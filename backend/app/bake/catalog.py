"""骨架匹配 / build_spec。目录见 domains，主题见 themes。"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass

from app.bake.domains import ARCHETYPES, DOMAIN_CAPABILITIES, DOMAINS  # re-export for callers
from app.bake.themes import (  # re-export for callers
    AUTH_ENTRY_MODES,
    AUTH_ROLE_WIDGETS,
    AUTH_TEMPLATES,
    THEME_ALIASES,
    THEMES,
    all_theme_ids,
    default_theme,
    normalize_auth_entry_mode,
    normalize_auth_role_widget,
    normalize_auth_template,
    normalize_theme,
    pick_auth_entry_mode,
    pick_auth_role_widget,
    pick_auth_template,
    themes_for_domain,
)


def copy_features(features: list) -> list:
    return copy.deepcopy(features)


# 基线能力标签（build_spec / ensure_spec_schema / 门禁路由 from_baseline 共用）
BASELINE_TAGS: list[str] = [
    "captcha",
    "upload",
    "page",
    "errorcode",
    "profile",
    "avatar",
    "register",
]


@dataclass
class MatchResult:
    title: str
    archetype: str
    domain: str
    confidence: float
    hits: list[str]
    text_excerpt: str
    archetypes: list[str] | None = None
    match_warnings: list[str] | None = None


def extract_title(text: str, fallback: str = "未命名毕设项目") -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines[:30]:
        if "题目" in ln or "课题" in ln:
            m = re.search(r"[：:]\s*(.+)$", ln)
            if m and len(m.group(1)) >= 4:
                return m.group(1)[:80]
        if ln.startswith("基于") and len(ln) >= 8:
            return ln[:80]
    for ln in lines[:10]:
        if 6 <= len(ln) <= 60 and not ln.startswith("http"):
            return ln[:80]
    return fallback


# 同分时优先更具体的行为原型（避免 CRUD 因字典顺序压过预约/交易）
_ARCHETYPE_TIE_PRIORITY = (
    "ARCH-RESERVE",
    "ARCH-TRADE",
    "ARCH-FLOW",
    "ARCH-STOCK",
    "ARCH-CONTENT",
    "ARCH-CRUD",
)


def _catalog_scores(text: str, catalog: dict) -> list[tuple[str, int, list[str]]]:
    lower = text.lower()
    scored: list[tuple[str, int, list[str]]] = []
    for key, meta in catalog.items():
        score = 0
        local_hits: list[str] = []
        for kw in meta.get("keywords", []):
            if kw.lower() in lower or kw in text:
                score += 1
                local_hits.append(kw)
        if score > 0:
            scored.append((key, score, local_hits))
    return scored


def score_catalog(
    text: str,
    catalog: dict,
    *,
    fallback: str | None = None,
) -> tuple[str, float, list[str]]:
    """关键词打分；全员 0 分时回落 fallback（域目录务必传 DOM-GENERIC，禁止误落第一项 LIBRARY）。"""
    scored = _catalog_scores(text, catalog)
    tie_rank = {k: i for i, k in enumerate(_ARCHETYPE_TIE_PRIORITY)}
    if not scored:
        if fallback and fallback in catalog:
            return fallback, 0.35, []
        best_key = next(iter(catalog))
        return best_key, 0.42, []
    scored.sort(key=lambda t: (-t[1], tie_rank.get(t[0], 99)))
    best_key, best_score, hits = scored[0]
    conf = min(0.95, 0.45 + best_score * 0.12)
    return best_key, conf, hits


def score_all_archetypes(text: str) -> list[str]:
    """开题命中的全部行为原型（score>0），按优先级排序；无命中则 CRUD。"""
    scored = _catalog_scores(text, ARCHETYPES)
    if not scored:
        return ["ARCH-CRUD"]
    tie_rank = {k: i for i, k in enumerate(_ARCHETYPE_TIE_PRIORITY)}
    scored.sort(key=lambda t: (-t[1], tie_rank.get(t[0], 99)))
    return [k for k, _, _ in scored]


# 原型要求的能力：具体 DOM 若不覆盖，降为 GENERIC（行为优先于行业皮肤）
_ARCH_REQUIRED_CAPS: dict[str, frozenset[str]] = {
    "ARCH-RESERVE": frozenset({"slot_reserve"}),
    "ARCH-TRADE": frozenset({"order_lines"}),
    "ARCH-FLOW": frozenset({"ticket_flow"}),
    "ARCH-STOCK": frozenset({"ticket_flow"}),
    "ARCH-CONTENT": frozenset({"ticket_flow"}),
    "ARCH-CRUD": frozenset(),
}

# 域皮肤自带的默认行为（仅当 ARCH 仍是 CRUD 时抬升，避免食堂题无订单词却落纯档案）
_DOMAIN_DEFAULT_ARCH: dict[str, str] = {
    "DOM-SHOP": "ARCH-TRADE",
    "DOM-FOOD": "ARCH-TRADE",
    "DOM-HOSPITAL": "ARCH-RESERVE",
    "DOM-PARKING": "ARCH-RESERVE",
    "DOM-MEETING": "ARCH-RESERVE",
    "DOM-SALON": "ARCH-RESERVE",
    "DOM-HOTEL": "ARCH-RESERVE",
    "DOM-DORM": "ARCH-FLOW",
    "DOM-PROPERTY": "ARCH-FLOW",
    "DOM-IT": "ARCH-FLOW",
    "DOM-LIBRARY": "ARCH-FLOW",
    "DOM-EQUIP": "ARCH-FLOW",
    "DOM-ASSET": "ARCH-FLOW",
    "DOM-CRM": "ARCH-FLOW",
    "DOM-ACTIVITY": "ARCH-FLOW",
    "DOM-LOST": "ARCH-FLOW",
    "DOM-COURSE": "ARCH-FLOW",
    "DOM-MEDIA": "ARCH-CONTENT",
    "DOM-MUSIC": "ARCH-CONTENT",
    "DOM-FORUM": "ARCH-CONTENT",
    "DOM-BLOG": "ARCH-CONTENT",
}


def domain_covers_archetype(domain: str, archetype: str) -> bool:
    """具体行业域的能力积木是否撑得起该行为原型。"""
    if domain == "DOM-GENERIC" or not domain:
        return True
    need = _ARCH_REQUIRED_CAPS.get(archetype or "ARCH-CRUD", frozenset())
    if not need:
        return True
    caps = set(DOMAIN_CAPABILITIES.get(domain) or [])
    return bool(need & caps)


def domain_covers_archetypes(domain: str, archetypes: list[str]) -> bool:
    return all(domain_covers_archetype(domain, a) for a in archetypes)


def reconcile_match(
    archetype: str,
    domain: str,
    archetypes: list[str] | None = None,
) -> tuple[str, str, list[str], list[str]]:
    """行为优先：多 ARCH 并集。

    - 域完全盖不住 → 降 GENERIC，保留全部行为路径。
    - 域只能盖住一部分：若丢掉的是预约/交易等「重」路径 → 仍降 GENERIC 保行为；
      否则保留行业皮并丢掉多余轻路径。
    """
    notes: list[str] = []
    arches = [a for a in (archetypes or [archetype]) if a in ARCHETYPES]
    if not arches:
        arches = ["ARCH-CRUD"]
    dom = domain if domain in DOMAINS else "DOM-GENERIC"
    dom_label = (DOMAINS.get(dom) or {}).get("label") or dom

    if arches == ["ARCH-CRUD"]:
        promoted = _DOMAIN_DEFAULT_ARCH.get(dom)
        if promoted:
            arches = [promoted]
            notes.append(f"提示：按「{dom_label}」默认补齐行为 → {ARCHETYPES.get(promoted, {}).get('label', promoted)}")

    # 预约/交易比「纯审核流」更重：丢掉它们会答辩像套错模板
    _HEAVY = frozenset({"ARCH-RESERVE", "ARCH-TRADE"})

    if dom != "DOM-GENERIC":
        covered = [a for a in arches if domain_covers_archetype(dom, a)]
        if not covered:
            notes.append(
                f"提示：行业皮「{dom_label}」撑不起当前行为，已改用通用壳，保留预约/下单/审核等能力。"
            )
            dom = "DOM-GENERIC"
        else:
            dropped = [a for a in arches if a not in covered]
            if dropped:
                drop_labels = "、".join(
                    ARCHETYPES.get(a, {}).get("label", a) for a in dropped
                )
                if any(a in _HEAVY for a in dropped):
                    notes.append(
                        f"提示：若保留「{dom_label}」将丢掉{drop_labels}；已改用通用壳以保住这些能力（行为优先于行业皮）。"
                    )
                    dom = "DOM-GENERIC"
                else:
                    notes.append(
                        f"提示：已保留「{dom_label}」皮肤，并去掉不兼容路径：{drop_labels}。"
                    )
                    arches = covered

    tie_rank = {k: i for i, k in enumerate(_ARCHETYPE_TIE_PRIORITY)}
    arches = sorted(dict.fromkeys(arches), key=lambda a: tie_rank.get(a, 99))
    primary = arches[0]
    return primary, dom, arches, notes


def match_warnings_from_hits(hits: list[str] | None) -> list[str]:
    """从命中列表抽出给人看的匹配提示。"""
    return [h for h in (hits or []) if isinstance(h, str) and h.startswith("提示：")]


# 开题里「要做什么」优先于综述噪声；accept 的 L3 扫描仍用全文
_FOCUS_SECTION = re.compile(
    r"(?:^|\n)\s*[（(]?\d*[)）.、]?\s*"
    r"(?:主要功能|研究内容|功能模块|功能需求|拟实现(?:功能)?|核心功能|系统功能)"
    r"[^\n]{0,40}\n([\s\S]{0,3000})",
    re.IGNORECASE,
)


def proposal_focus_for_match(text: str) -> str:
    """抽取开题功能/研究内容段并加权；无则退回全文（上传链路本就喂全文）。"""
    raw = text or ""
    blocks = [m.group(0) for m in _FOCUS_SECTION.finditer(raw)]
    if not blocks:
        return raw
    head = "\n".join(ln for ln in raw.splitlines()[:8] if ln.strip())
    focus = "\n".join(blocks)
    # 功能段计两遍，压过背景综述里顺带出现的词
    return f"{head}\n{focus}\n{focus}"


def match_text(text: str, filename: str = "") -> MatchResult:
    title = extract_title(text, fallback=filename.rsplit(".", 1)[0] or "未命名毕设项目")
    scored = proposal_focus_for_match(text)
    arch_hits_all: list[str] = []
    for _k, _s, local in _catalog_scores(scored, ARCHETYPES):
        arch_hits_all.extend(local)
    arches = score_all_archetypes(scored)
    _, arch_conf, _ = score_catalog(scored, ARCHETYPES, fallback="ARCH-CRUD")
    dom, dom_conf, dom_hits = score_catalog(scored, DOMAINS, fallback="DOM-GENERIC")
    arch, dom, arches, recon_notes = reconcile_match(arches[0], dom, arches)
    confidence = round((arch_conf + dom_conf) / 2, 2)
    hits = list(dict.fromkeys(arch_hits_all + dom_hits + recon_notes))
    warnings = match_warnings_from_hits(hits)
    return MatchResult(
        title=title,
        archetype=arch,
        domain=dom,
        confidence=confidence,
        hits=hits,
        text_excerpt=text[:2000],
        archetypes=arches,
        match_warnings=warnings,
    )


PASSWORD_HASH_MODES = frozenset({"none", "bcrypt", "md5", "sha256"})


def normalize_password_hash(mode: str | None) -> str:
    m = (mode or "none").strip().lower()
    if m in ("sha", "sha-256", "sha_256"):
        m = "sha256"
    return m if m in PASSWORD_HASH_MODES else "none"


def _roles_for_spec(domain_roles: list, schema: dict | None) -> list[str]:
    """领域 roles 定序，schema.roles 补全（如 subadmin）。"""
    schema_roles = schema.get("roles") if isinstance(schema, dict) else None
    keys = list(schema_roles.keys()) if isinstance(schema_roles, dict) else []
    out: list[str] = []
    for r in domain_roles or []:
        if r and r not in out:
            out.append(str(r))
    for r in keys:
        if r and r not in out:
            out.append(str(r))
    return out or ["user", "admin"]


def build_spec(
    title: str,
    archetype: str,
    domain: str,
    theme: str,
    llm_enabled: bool,
    match_mode: str,
    confidence: float,
    hits: list[str] | None = None,
    proposal: dict | None = None,
    password_hash: str = "none",
    archetypes: list[str] | None = None,
) -> dict:
    from app.bake.domain_schema import attach_accept, build_domain_schema

    dom = DOMAINS.get(domain, DOMAINS["DOM-GENERIC"])
    arch = ARCHETYPES.get(archetype, ARCHETYPES["ARCH-CRUD"])
    theme = normalize_theme(theme, domain)
    seed = f"{title}|{domain}"
    auth_template = pick_auth_template(seed)
    auth_entry_mode = pick_auth_entry_mode(f"{seed}|entry")
    auth_role_widget = pick_auth_role_widget(f"{seed}|widget")
    arches = list(archetypes or [archetype])
    schema = build_domain_schema(title, domain, archetype=archetype, archetypes=arches)
    spec = {
        "title": title,
        "archetype": archetype,
        "archetypes": arches,
        "archetype_label": arch["label"],
        "domain": domain,
        "domain_label": dom["label"],
        "industry": dom["label"],
        "theme": theme,
        "theme_label": THEMES.get(theme, theme),
        "auth_template": auth_template,
        "auth_template_label": next(
            (t["label"] for t in AUTH_TEMPLATES if t["id"] == auth_template), auth_template
        ),
        "auth_entry_mode": auth_entry_mode,
        "auth_entry_mode_label": next(
            (t["label"] for t in AUTH_ENTRY_MODES if t["id"] == auth_entry_mode), auth_entry_mode
        ),
        "auth_role_widget": auth_role_widget,
        "auth_role_widget_label": next(
            (t["label"] for t in AUTH_ROLE_WIDGETS if t["id"] == auth_role_widget), auth_role_widget
        ),
        "llm_enabled": llm_enabled,
        "password_hash": normalize_password_hash(password_hash),
        "match_mode": match_mode,
        "confidence": confidence,
        "hits": hits or [],
        "match_warnings": match_warnings_from_hits(hits),
        # 角色顺序跟领域清单，文案/补全跟 schema.roles（避免 Spec 漏子管）
        "roles": _roles_for_spec(dom.get("roles") or [], schema),
        "entities": dom["entities"],
        "flows": dom["flows"],
        "baseline": list(BASELINE_TAGS),
        "out_of_mvp": dom["out_of_mvp"],
        "features": copy_features(dom["features"]),
        "gate": dom.get("gate") or {},
        "available_themes": themes_for_domain(domain),
        "schema": schema,
        "runtime": copy.deepcopy(dom.get("runtime") or {}),
    }
    if domain == "DOM-GENERIC":
        from app.bake.archetype_shells import apply_generic_shell

        spec = apply_generic_shell(spec)
    if proposal:
        spec["proposal"] = proposal
    proposal_text = ""
    if isinstance(proposal, dict):
        proposal_text = str(
            proposal.get("excerpt")
            or proposal.get("text")
            or proposal.get("summary")
            or proposal.get("background")
            or ""
        )
    elif isinstance(proposal, str):
        proposal_text = proposal
    if not proposal_text:
        proposal_text = title
    return attach_accept(spec, proposal_text)
