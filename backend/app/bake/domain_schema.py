"""Domain Schema 组装：accept / merge / 校验；模板见 schema_templates，档案见 profile_fields。"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from app.bake.capabilities import CAPABILITIES, resolve_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.schema_templates import (  # re-export
    SCHEMA_BUILDERS,
    product_name_from_title,
    _generic_schema,
)
from app.bake.profile_fields import attach_profile_fields

# 哪些 domain 当前有 skeletons/domains 叠加（与 bake overlay 一致）
DOMAINS_WITH_OVERLAY = frozenset({"DOM-LIBRARY"})

# 基线通用壳已覆盖的能力（无需厚 overlay 即可跑）
BASELINE_RUNTIME_CAPS = frozenset({
    "archive",
    "ticket_flow",
    "quota",
    "deadline",
    "content",
    "org_users",
    "recommend",
    "time_conflict",
    "order_lines",
    "slot_reserve",
})


def baseline_runtime_covers(domain: str, archetype: str | None = None) -> bool:
    """所需能力均落在基线已实现积木内（无需厚 overlay）。"""
    req = set(required_capabilities(domain, archetype))
    if not req:
        return True
    if req - BASELINE_RUNTIME_CAPS:
        return False
    from app.bake.capabilities import implemented_capability_ids

    return req <= implemented_capability_ids()


# 主数据菜单 key（领域实体管理，总管专属）
MASTER_MENU_KEYS = frozenset({"archive", "category", "lookup_site", "lookup_type"})
REQUIRED_SUPER_MENU_KEYS = frozenset({"users", "content"})


def build_domain_schema(
    title: str, domain: str, archetype: str | None = None
) -> dict[str, Any]:
    if domain == "DOM-GENERIC":
        from app.bake.archetype_shells import build_generic_shell_schema

        schema = build_generic_shell_schema(title, archetype)
        return attach_profile_fields(schema, domain)
    builder = SCHEMA_BUILDERS.get(domain, lambda t: _generic_schema(t, domain))
    if domain in SCHEMA_BUILDERS:
        schema = builder(title)
    else:
        schema = _generic_schema(title, domain)
    return attach_profile_fields(schema, domain)


def required_capabilities(domain: str, archetype: str | None = None) -> list[str]:
    if domain == "DOM-GENERIC" and archetype:
        from app.bake.archetype_shells import shell_capabilities

        return shell_capabilities(archetype)
    return list(DOMAIN_CAPABILITIES.get(domain, DOMAIN_CAPABILITIES["DOM-GENERIC"]))


def ensure_spec_schema(spec: dict[str, Any] | None) -> dict[str, Any]:
    """旧项目无 accept/schema 时补齐；gate 始终以 catalog 为准，避免契约过期导致门禁误杀。"""
    from app.bake.catalog import DOMAINS

    spec = dict(spec or {})
    domain = spec.get("domain") or "DOM-GENERIC"
    archetype = spec.get("archetype") or "ARCH-CRUD"
    title = spec.get("title") or "毕设系统"
    # GENERIC：按 ARCH-* 重绑壳（runtime/gate/features/capabilities/schema）
    if domain == "DOM-GENERIC":
        from app.bake.archetype_shells import apply_generic_shell

        spec = apply_generic_shell(spec)
    else:
        dom = DOMAINS.get(domain) or DOMAINS["DOM-GENERIC"]
        catalog_gate = dom.get("gate")
        if catalog_gate:
            spec["gate"] = copy.deepcopy(catalog_gate)
        cat_feats = dom.get("features") or []
        cur_feats = spec.get("features") or []
        if cat_feats and len(cur_feats) < len(cat_feats):
            spec["features"] = copy.deepcopy(cat_feats)
    if not isinstance(spec.get("schema"), dict) or not spec["schema"].get("labels"):
        spec["schema"] = build_domain_schema(title, domain, archetype=archetype)
    elif not (spec["schema"].get("profileFields")):
        spec["schema"] = attach_profile_fields(spec["schema"], domain)
    if not spec.get("accept"):
        proposal_text = ""
        prop = spec.get("proposal")
        if isinstance(prop, dict):
            proposal_text = str(
                prop.get("excerpt")
                or prop.get("text")
                or prop.get("summary")
                or prop.get("background")
                or ""
            )
        elif isinstance(prop, str):
            proposal_text = prop
        if not proposal_text:
            proposal_text = title
        spec = attach_accept(spec, proposal_text)
    return spec


def attach_accept(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain", "DOM-GENERIC")
    archetype = spec.get("archetype")
    req = list(spec.get("capabilities") or required_capabilities(domain, archetype))
    decision = resolve_accept(
        req,
        proposal_text,
        has_domain_overlay=domain in DOMAINS_WITH_OVERLAY,
        has_baseline_runtime=baseline_runtime_covers(domain, archetype),
    )
    schema = spec.get("schema") or build_domain_schema(
        spec.get("title") or "毕设系统", domain, archetype=archetype
    )
    schema = copy.deepcopy(schema)
    schema["capabilities"] = req
    schema["accept"] = decision["accept"]
    schema["missing_capabilities"] = decision["missing_capabilities"]
    schema["out_of_mvp_signals"] = decision["out_of_mvp_signals"]

    # 将未实现卖点并入 features out_of_mvp（去重）
    features = list(spec.get("features") or [])
    existing = {
        f.get("name")
        for f in features
        if isinstance(f, dict) and f.get("status") == "out_of_mvp"
    }
    for sig in decision["out_of_mvp_signals"]:
        name = f"{sig}（开题提及）"
        if name not in existing:
            features.append({"name": name, "status": "out_of_mvp"})

    return {
        **spec,
        "capabilities": req,
        "accept": decision["accept"],
        "accept_reason": decision["reason"],
        "missing_capabilities": decision["missing_capabilities"],
        "out_of_mvp_signals": decision["out_of_mvp_signals"],
        "schema": schema,
        "features": features,
    }


def validate_schema(schema: dict[str, Any] | None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(schema, dict):
        return False, ["schema 缺失或非对象"]
    if schema.get("version") != 1:
        errors.append("schema.version 必须为 1")
    if not schema.get("title"):
        errors.append("schema.title 必填")
    caps = schema.get("capabilities") or []
    if not isinstance(caps, list):
        errors.append("schema.capabilities 必须为列表")
    else:
        for c in caps:
            if c not in CAPABILITIES:
                errors.append(f"未知 capability: {c}")
    labels = schema.get("labels") or {}
    if not isinstance(labels, dict) or not labels.get("appName"):
        errors.append("schema.labels.appName 必填")

    # 全厂不变式：admin 菜单须含用户 + 公告 + ≥1 领域主数据（均应 superOnly）
    admin_menus = (schema.get("menus") or {}).get("admin") or []
    if isinstance(admin_menus, list) and admin_menus:
        keys = {
            m.get("key")
            for m in admin_menus
            if isinstance(m, dict) and m.get("key")
        }
        for req in REQUIRED_SUPER_MENU_KEYS:
            if req not in keys:
                errors.append(f"admin 菜单缺少必要项: {req}")
        if not (keys & MASTER_MENU_KEYS):
            errors.append(
                "admin 菜单缺少领域主数据"
                f"（需含其一: {', '.join(sorted(MASTER_MENU_KEYS))}）"
            )
        # 有 ticket 业务流时禁止假 archive（无 archive 能力却挂 archive 菜单）
        if "ticket_flow" in caps and "archive" not in caps and "archive" in keys:
            errors.append("ticket 域禁止未实现的 archive 菜单")
        for m in admin_menus:
            if not isinstance(m, dict):
                continue
            k = m.get("key")
            if k in MASTER_MENU_KEYS or k in REQUIRED_SUPER_MENU_KEYS:
                if m.get("superOnly") is not True:
                    errors.append(f"admin 菜单 {k} 必须 superOnly=true")

    pfs = schema.get("profileFields")
    if pfs is not None:
        if not isinstance(pfs, list):
            errors.append("schema.profileFields 必须为列表")
        else:
            seen: set[str] = set()
            for i, f in enumerate(pfs):
                if not isinstance(f, dict):
                    errors.append(f"profileFields[{i}] 必须为对象")
                    continue
                if not f.get("key") or not f.get("label"):
                    errors.append(f"profileFields[{i}] 缺少 key/label")
                k = str(f.get("key") or "")
                if k in seen:
                    errors.append(f"profileFields 重复 key: {k}")
                seen.add(k)
                if f.get("type") == "select" and not isinstance(f.get("options"), list):
                    errors.append(f"profileFields.{k} select 需 options 列表")

    return len(errors) == 0, errors


def merge_schema(base: dict[str, Any], patch: dict[str, Any] | None) -> dict[str, Any]:
    """浅合并 labels/seeds/menus；entities 按 key 深合并；禁止改 capabilities 集合外的随意结构由校验兜底。"""
    out = copy.deepcopy(base)
    if not patch:
        return out
    for key in ("title",):
        if patch.get(key):
            out[key] = patch[key]
    for key in ("labels", "seeds", "roles"):
        if isinstance(patch.get(key), dict):
            out.setdefault(key, {})
            out[key] = {**out.get(key, {}), **patch[key]}
    if isinstance(patch.get("profileFields"), list):
        out["profileFields"] = patch["profileFields"]
    if isinstance(patch.get("menus"), dict):
        out.setdefault("menus", {})
        for side, items in patch["menus"].items():
            if isinstance(items, list):
                out["menus"][side] = items
    if isinstance(patch.get("entities"), dict):
        out.setdefault("entities", {})
        for ek, ev in patch["entities"].items():
            if isinstance(ev, dict):
                cur = out["entities"].get(ek) or {}
                merged = {**cur, **ev}
                if isinstance(ev.get("verbs"), dict):
                    merged["verbs"] = {**(cur.get("verbs") or {}), **ev["verbs"]}
                if isinstance(ev.get("states"), dict):
                    merged["states"] = {**(cur.get("states") or {}), **ev["states"]}
                out["entities"][ek] = merged
    return out


def deterministic_llm_patch(spec: dict[str, Any], enabled: bool) -> dict[str, Any]:
    """
    白名单 patch。尚未接真实模型时：用开题/标题润色 labels 与 seeds。
    enabled=True 时标记 mode=llm_deterministic（可替换为真 LLM）。
    """
    title = spec.get("title") or "毕设系统"
    proposal = ""
    prop = spec.get("proposal")
    if isinstance(prop, dict):
        proposal = str(
            prop.get("excerpt") or prop.get("text") or prop.get("summary") or prop.get("background") or ""
        )
    elif isinstance(prop, str):
        proposal = prop
    excerpt = (proposal or title).strip().replace("\n", " ")
    excerpt = re.sub(r"\s+", " ", excerpt)[:80]

    labels = dict((spec.get("schema") or {}).get("labels") or {})
    # 保留领域已给的短产品名；勿用开题长标题盖掉
    if not labels.get("appName") or labels.get("appName") == title:
        labels["appName"] = product_name_from_title(title)
    if excerpt and excerpt != title:
        labels["authLead"] = f"{excerpt}。验证码登录后即可使用系统主流程。"
    seeds = dict((spec.get("schema") or {}).get("seeds") or {})
    if not seeds.get("noticeTitle"):
        seeds["noticeTitle"] = f"{title}上线通知"
    # 公告页标题/导语：领域 schema 已给默认；仅缺省时补齐（真 LLM 可改写白名单槽，勿覆盖已有领域文案）
    if not labels.get("noticePageTitle"):
        labels["noticePageTitle"] = "公告"
    if not labels.get("noticePageLead"):
        if enabled and excerpt and excerpt != title:
            labels["noticePageLead"] = "与本系统相关的通知与须知，点击条目阅读全文。"
        else:
            labels["noticePageLead"] = "通知与须知，点击条目阅读全文。"
    if enabled and excerpt and not seeds.get("noticeBody"):
        seeds["noticeBody"] = f"系统已就绪。{excerpt}"[:200]
    return {
        "mode": "llm" if enabled else "deterministic",
        "labels": labels,
        "seeds": seeds,
        "title": title,
    }


def write_schema_artifacts(workspace: Path, schema: dict[str, Any]) -> list[str]:
    """写入 domain.schema.json 与 islands 摘要，供 gate / 前端对照。"""
    written: list[str] = []
    schema_path = workspace / "domain.schema.json"
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    written.append("domain.schema.json")

    islands = workspace / "islands"
    islands.mkdir(exist_ok=True)
    for name, payload in (
        ("island_entity_labels.json", schema.get("entities") or {}),
        ("island_flow_copy.json", {
            "ticket": (schema.get("entities") or {}).get("ticket") or {},
            "menus": schema.get("menus") or {},
        }),
        ("island_notice_seed.json", schema.get("seeds") or {}),
        ("island_ui_hints.json", schema.get("labels") or {}),
    ):
        path = islands / name
        path.write_text(
            json.dumps({"island": name, "data": payload}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        written.append(f"islands/{name}")
    return written
