"""骨架匹配 / build_spec。目录见 domains，主题见 themes。"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass

from app.bake.domains import ARCHETYPES, DOMAINS  # re-export for callers
from app.bake.themes import (  # re-export for callers
    AUTH_TEMPLATES,
    THEME_ALIASES,
    THEMES,
    all_theme_ids,
    default_theme,
    normalize_auth_template,
    normalize_theme,
    pick_auth_template,
    themes_for_domain,
)


def copy_features(features: list) -> list:
    return copy.deepcopy(features)


@dataclass
class MatchResult:
    title: str
    archetype: str
    domain: str
    confidence: float
    hits: list[str]
    text_excerpt: str


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


def score_catalog(
    text: str,
    catalog: dict,
    *,
    fallback: str | None = None,
) -> tuple[str, float, list[str]]:
    """关键词打分；全员 0 分时回落 fallback（域目录务必传 DOM-GENERIC，禁止误落第一项 LIBRARY）。"""
    lower = text.lower()
    best_key = next(iter(catalog))
    best_score = 0
    hits: list[str] = []
    tie_rank = {k: i for i, k in enumerate(_ARCHETYPE_TIE_PRIORITY)}

    def _better(score: int, key: str) -> bool:
        if score > best_score:
            return True
        if score == best_score and score > 0 and key in tie_rank and best_key in tie_rank:
            return tie_rank[key] < tie_rank[best_key]
        return False

    for key, meta in catalog.items():
        score = 0
        local_hits = []
        for kw in meta.get("keywords", []):
            if kw.lower() in lower or kw in text:
                score += 1
                local_hits.append(kw)
        if _better(score, key):
            best_score = score
            best_key = key
            hits = local_hits
    if best_score == 0 and fallback and fallback in catalog:
        return fallback, 0.35, []
    conf = min(0.95, 0.45 + best_score * 0.12) if best_score else 0.42
    return best_key, conf, hits


def match_text(text: str, filename: str = "") -> MatchResult:
    title = extract_title(text, fallback=filename.rsplit(".", 1)[0] or "未命名毕设项目")
    arch, arch_conf, arch_hits = score_catalog(text, ARCHETYPES, fallback="ARCH-CRUD")
    dom, dom_conf, dom_hits = score_catalog(text, DOMAINS, fallback="DOM-GENERIC")
    # 未命中具体行业域时，保留 ARCH-* 命中（预约/订单/审核），供 GENERIC 绑壳
    confidence = round((arch_conf + dom_conf) / 2, 2)
    hits = list(dict.fromkeys(arch_hits + dom_hits))
    return MatchResult(
        title=title,
        archetype=arch,
        domain=dom,
        confidence=confidence,
        hits=hits,
        text_excerpt=text[:2000],
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
) -> dict:
    from app.bake.domain_schema import attach_accept, build_domain_schema

    dom = DOMAINS.get(domain, DOMAINS["DOM-GENERIC"])
    arch = ARCHETYPES.get(archetype, ARCHETYPES["ARCH-CRUD"])
    theme = normalize_theme(theme, domain)
    # 按题目+领域稳定抽一套登录版式，交付后写入 .env，不再随浏览器变化
    auth_template = pick_auth_template(f"{title}|{domain}")
    schema = build_domain_schema(title, domain, archetype=archetype)
    spec = {
        "title": title,
        "archetype": archetype,
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
        "llm_enabled": llm_enabled,
        "password_hash": normalize_password_hash(password_hash),
        "match_mode": match_mode,
        "confidence": confidence,
        "hits": hits or [],
        "roles": dom["roles"],
        "entities": dom["entities"],
        "flows": dom["flows"],
        # profile：业务用户与子管理员可改资料/头像；顶级超管可不提供修改入口
        "baseline": ["captcha", "upload", "page", "errorcode", "profile", "avatar", "register"],
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
