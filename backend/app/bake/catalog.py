"""骨架匹配 / build_spec。目录见 domains，主题见 themes。"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass

from app.bake.domains import ARCHETYPES, DOMAIN_CAPABILITIES, DOMAINS, ARCH_PATH_ORDER
from app.bake.proposal_lexicon import FEATURE_HEAD_TERMS
from app.bake.themes import (  # re-export for callers
    AUTH_ENTRY_MODES,
    AUTH_ROLE_WIDGETS,
    AUTH_TEMPLATES,
    CHROME_STYLES,
    THEME_ALIASES,
    THEMES,
    all_theme_ids,
    default_theme,
    normalize_auth_entry_mode,
    normalize_auth_role_widget,
    normalize_auth_template,
    normalize_chrome,
    normalize_theme,
    pick_auth_entry_mode,
    pick_auth_role_widget,
    pick_auth_template,
    pick_chrome,
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
    match_source: str = "keyword"  # keyword | llm
    rationale: str = ""
    alts: list[dict] | None = None
    keyword_arch: str | None = None
    keyword_domain: str | None = None
    delivery_slug: str = ""


def catalog_brief_for_match() -> str:
    """给 Match Agent 的封闭目录摘要（短）。"""
    arch_lines = [f"- {k}: {v.get('label')}" for k, v in ARCHETYPES.items()]
    dom_lines: list[str] = []
    for k, v in DOMAINS.items():
        kws = "、".join((v.get("keywords") or [])[:6])
        flows = "；".join((v.get("flows") or [])[:2])
        dom_lines.append(f"- {k}（{v.get('label')}）关键词:{kws} 流程:{flows}")
    return (
        "骨架 ARCHETYPES:\n"
        + "\n".join(arch_lines)
        + "\n\n领域 DOMAINS:\n"
        + "\n".join(dom_lines)
    )


def merge_llm_match(kw: MatchResult, data: dict) -> MatchResult | None:
    """校验 LLM 推荐；非法则返回 None（调用方回落关键词）。

    Path B：关键词已打出多主路径并集时，与 LLM 结果做并集再 reconcile，
    禁止压成单行业皮丢掉开题里的第二条路径（如图书馆挤掉二手下单）。
    """
    arch = str(data.get("archetype") or "").strip()
    dom = str(data.get("domain") or "").strip()
    if arch not in ARCHETYPES or dom not in DOMAINS:
        return None
    try:
        raw_conf = float(data.get("confidence") if data.get("confidence") is not None else 0.7)
    except (TypeError, ValueError):
        raw_conf = 0.7
    raw_conf = max(0.35, min(0.95, raw_conf))

    llm_arches_raw = data.get("archetypes")
    llm_arches: list[str] = []
    if isinstance(llm_arches_raw, list):
        llm_arches = [str(a).strip() for a in llm_arches_raw if str(a).strip() in ARCHETYPES]
    if not llm_arches:
        llm_arches = [arch]

    combined: list[str] = []
    for a in list(kw.archetypes or []) + llm_arches + [arch]:
        if a in ARCHETYPES and a not in combined:
            combined.append(a)
    if not combined:
        combined = [arch]

    primary, dom_final, arches_final, recon_notes = reconcile_match(arch, dom, combined)

    same_dom = dom_final == kw.domain
    same_arch = primary == kw.archetype
    if same_dom and same_arch and set(arches_final) == set(kw.archetypes or []):
        conf = min(0.95, max(raw_conf, kw.confidence) + 0.05)
    elif same_dom:
        conf = min(0.92, (raw_conf * 0.7 + kw.confidence * 0.3))
    else:
        conf = min(0.88, raw_conf * 0.85)

    # 保留关键词 reconcile 提示 + 本轮并集提示；若 LLM 原推荐被改写则明示
    hits = [h for h in (kw.hits or []) if isinstance(h, str)]
    warnings: list[str] = []
    for n in recon_notes:
        if n not in hits:
            hits.append(n)
        if n.startswith("提示：") and n not in warnings:
            warnings.append(n)
    if dom != dom_final or arch != primary or set(llm_arches) != set(arches_final):
        tip = (
            f"提示：大模型初荐 {arch}×{dom}；已与关键词主路径并集调和为 "
            f"{primary}×{dom_final}（{'+'.join(arches_final)}），请人工确认。"
        )
        if tip not in hits:
            hits.append(tip)
        warnings.append(tip)
    elif not same_dom or not same_arch:
        kw_label = (DOMAINS.get(kw.domain) or {}).get("label") or kw.domain
        llm_label = (DOMAINS.get(dom_final) or {}).get("label") or dom_final
        tip = (
            f"提示：大模型推荐 {primary}×{dom_final}（{llm_label}）；"
            f"关键词初判为 {kw.archetype}×{kw.domain}（{kw_label}），请人工确认。"
        )
        warnings.append(tip)
        if tip not in hits:
            hits.append(tip)

    alts_out: list[dict] = []
    for item in data.get("alts") or []:
        if not isinstance(item, dict):
            continue
        a = str(item.get("archetype") or "").strip()
        d = str(item.get("domain") or "").strip()
        if a not in ARCHETYPES or d not in DOMAINS:
            continue
        if a == primary and d == dom_final:
            continue
        try:
            c = float(item.get("confidence") if item.get("confidence") is not None else 0.5)
        except (TypeError, ValueError):
            c = 0.5
        alts_out.append(
            {
                "archetype": a,
                "domain": d,
                "confidence": max(0.2, min(0.9, c)),
                "label": f"{ARCHETYPES[a]['label']} × {DOMAINS[d]['label']}",
            }
        )
        if len(alts_out) >= 3:
            break

    rationale = str(data.get("rationale") or "").strip()[:400]
    from app.bake.naming import sanitize_delivery_slug

    delivery_slug = sanitize_delivery_slug(
        str(data.get("slug") or data.get("delivery_slug") or ""),
        domain=dom_final,
    )

    return MatchResult(
        title=kw.title,
        archetype=primary,
        domain=dom_final,
        confidence=round(conf, 2),
        hits=hits,
        text_excerpt=kw.text_excerpt,
        archetypes=arches_final,
        match_warnings=warnings,
        match_source="llm",
        rationale=rationale,
        alts=alts_out,
        keyword_arch=kw.archetype,
        keyword_domain=kw.domain,
        delivery_slug=delivery_slug,
    )


def extract_title(text: str, fallback: str = "未命名毕设项目") -> str:
    """从开题/任务书等结构里捞课题名。"""
    from app.services.proposal import (
        _SKIP_TITLE_LINE,
        _TITLE_EXPLICIT,
        _TITLE_HEADING,
        _TITLE_PHRASE,
        _TITLE_TABLE,
        strip_non_dev_sections,
    )

    body = strip_non_dev_sections(text or "")
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]

    m = _TITLE_TABLE.search(body[:3000])
    if m and len(m.group(1).strip()) >= 4:
        return m.group(1).strip()[:80]

    for ln in lines[:40]:
        m = _TITLE_EXPLICIT.search(ln)
        if m and len(m.group(1).strip()) >= 4:
            t = m.group(1).strip()
            if not t.startswith("|"):
                return t[:80]

    # 任务书：「一、毕业设计题目」下一行才是题名
    for i, ln in enumerate(lines[:40]):
        if _TITLE_HEADING.match(ln) and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if 4 <= len(nxt) <= 60 and not _SKIP_TITLE_LINE.match(nxt) and "。" not in nxt:
                return nxt[:80]

    phrases: list[str] = []
    for m in _TITLE_PHRASE.finditer(body[:8000]):
        p = m.group(1).strip()
        if 4 <= len(p) <= 40 and not _SKIP_TITLE_LINE.match(p):
            phrases.append(p)
    if phrases:
        best = max(set(phrases), key=lambda p: (phrases.count(p), len(p)))
        return best[:80]

    for ln in lines[:30]:
        if ln.startswith("基于") and 8 <= len(ln) <= 80 and "。" not in ln:
            return ln[:80]
        m = _TITLE_PHRASE.search(ln)
        if m:
            return m.group(1).strip()[:80]

    for ln in lines[:12]:
        if _SKIP_TITLE_LINE.match(ln):
            continue
        if 8 <= len(ln) <= 48 and "。" not in ln and not ln.startswith("http"):
            return ln[:80]
    return fallback


# 同分时优先更具体的行为原型（避免 CRUD 因字典顺序压过预约/交易）
_ARCHETYPE_TIE_PRIORITY = ARCH_PATH_ORDER


def _catalog_scores(text: str, catalog: dict) -> list[tuple[str, int, list[str]]]:
    from app.bake.proposal_lexicon import keyword_mentioned

    scored: list[tuple[str, int, list[str]]] = []
    for key, meta in catalog.items():
        score = 0
        local_hits: list[str] = []
        for kw in meta.get("keywords", []):
            if keyword_mentioned(text, kw):
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
    - 域只能盖住一部分 → **一律**降 GENERIC 并保留并集（Path B：
      不再把「审核流」当可丢掉的轻路径；否则借阅+二手会落成纯商城）。
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
            notes.append(
                f"提示：按「{dom_label}」默认补齐行为 → "
                f"{ARCHETYPES.get(promoted, {}).get('label', promoted)}"
            )

    if dom != "DOM-GENERIC":
        covered = [a for a in arches if domain_covers_archetype(dom, a)]
        if not covered:
            notes.append(
                f"提示：行业皮「{dom_label}」撑不起当前行为，已改用通用壳，"
                "保留预约/下单/审核等能力。"
            )
            dom = "DOM-GENERIC"
        else:
            dropped = [a for a in arches if a not in covered]
            if dropped:
                drop_labels = "、".join(
                    ARCHETYPES.get(a, {}).get("label", a) for a in dropped
                )
                notes.append(
                    f"提示：若保留「{dom_label}」将丢掉{drop_labels}；"
                    "已改用通用壳以保住开题全部主路径（行为优先于行业皮）。"
                )
                dom = "DOM-GENERIC"

    tie_rank = {k: i for i, k in enumerate(_ARCHETYPE_TIE_PRIORITY)}
    arches = sorted(dict.fromkeys(arches), key=lambda a: tie_rank.get(a, 99))
    primary = arches[0]
    return primary, dom, arches, notes


def match_warnings_from_hits(hits: list[str] | None) -> list[str]:
    """从命中列表抽出给人看的匹配提示。"""
    return [h for h in (hits or []) if isinstance(h, str) and h.startswith("提示：")]


# 开题里「要做什么」优先于综述噪声；标题词表见 proposal_lexicon
_FOCUS_SECTION = re.compile(
    r"(?:^|\n)\s*(?:[（(]?\d+[)）.、]|[一二三四五六七八九十百]+[、．.]|"
    r"[（(][一二三四五六七八九十\d]+[)）])?\s*"
    rf"(?:{FEATURE_HEAD_TERMS}|"
    r"研究内容[^\n]{0,20}拟实现|拟实现[^\n]{0,12}功能)"
    r"[^\n]{0,80}\n([\s\S]{0,3500})",
    re.IGNORECASE,
)


def _proposal_focus_parts(text: str) -> tuple[str, list[str], list[str]]:
    """共用：去噪声正文 + 功能段块 + 模块行。"""
    from app.services.proposal import extract_module_lines, strip_non_dev_sections

    raw = strip_non_dev_sections(text or "")
    blocks = [m.group(0) for m in _FOCUS_SECTION.finditer(raw)]
    modules = extract_module_lines(raw)
    return raw, blocks, modules


def proposal_impl_sections_for_scope(text: str) -> str:
    """仅「拟实现/主要功能」段 + 模块行，供业务过重扫描（不含文首现状综述）。"""
    _raw, blocks, modules = _proposal_focus_parts(text)
    parts = list(blocks)
    if modules:
        parts.append("\n".join(modules))
    return "\n".join(parts).strip()


def proposal_focus_for_match(text: str) -> str:
    """抽取对开发有用的片段并加权：功能/实现段 + 模块行；去掉参考文献噪声。"""
    raw, blocks, modules = _proposal_focus_parts(text)
    head = "\n".join(ln for ln in raw.splitlines()[:8] if ln.strip())
    title = extract_title(raw)
    parts = [title, head]
    if blocks:
        focus = "\n".join(blocks)
        parts.extend([focus, focus])
    if modules:
        mod_block = "\n".join(modules)
        # 模块行再加权重：直接对应要开发的实体/能力
        parts.extend([mod_block, mod_block, mod_block])
    scored = "\n".join(p for p in parts if p)
    return scored or raw


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
        match_source="keyword",
        rationale="",
        alts=[],
        keyword_arch=arch,
        keyword_domain=dom,
    )


PASSWORD_HASH_MODES = frozenset({"none", "bcrypt", "md5", "sha256"})


def normalize_password_hash(mode: str | None) -> str:
    m = (mode or "none").strip().lower()
    if m in ("sha", "sha-256", "sha_256"):
        m = "sha256"
    return m if m in PASSWORD_HASH_MODES else "none"


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
    match_meta: dict | None = None,
) -> dict:
    from app.bake.domain_schema import attach_accept, build_domain_schema
    from app.bake.staff_posts import roles_for_spec

    dom = DOMAINS.get(domain, DOMAINS["DOM-GENERIC"])
    arch = ARCHETYPES.get(archetype, ARCHETYPES["ARCH-CRUD"])
    theme = normalize_theme(theme, domain)
    seed = f"{title}|{domain}"
    auth_template = pick_auth_template(seed)
    auth_entry_mode = pick_auth_entry_mode(f"{seed}|entry")
    auth_role_widget = pick_auth_role_widget(f"{seed}|widget")
    chrome = pick_chrome(f"{seed}|chrome")
    arches = list(archetypes or [archetype])
    # GENERIC 壳由 apply_generic_shell 一次组装（含岗位）；具名域在此建 schema
    schema = (
        {}
        if domain == "DOM-GENERIC"
        else build_domain_schema(title, domain, archetype=archetype, archetypes=arches)
    )
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
        "chrome": chrome,
        "chrome_label": next(
            (t["label"] for t in CHROME_STYLES if t["id"] == chrome), chrome
        ),
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
        "roles": roles_for_spec(dom.get("roles") or [], schema),
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
    if match_meta:
        spec["match_meta"] = match_meta
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
