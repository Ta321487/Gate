"""Domain Schema 组装：accept / merge / 校验；模板见 schema.templates，档案见 profile_fields。"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from app.bake.capabilities import CAPABILITIES, compose_out_of_mvp, implemented_capability_ids, resolve_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.schema.templates import (  # re-export
    SCHEMA_BUILDERS,
    product_name_from_title,
    generic_schema,
)
from app.bake.profile_fields import attach_profile_fields

# 哪些 domain 仍有 skeletons/domains 厚叠加（空 = 全部走 baseline 薄壳）
DOMAINS_WITH_OVERLAY = frozenset()

# 基线通用壳已覆盖的能力 = CAPABILITIES 中 status=implemented（单一真源）
BASELINE_RUNTIME_CAPS = frozenset(implemented_capability_ids())


def baseline_runtime_covers(
    domain: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
) -> bool:
    """所需能力均落在基线已实现积木内（无需厚 overlay）。"""
    req = set(required_capabilities(domain, archetype, archetypes=archetypes))
    if not req:
        return True
    return req <= BASELINE_RUNTIME_CAPS


# 主数据菜单 key（领域实体管理，总管专属）
MASTER_MENU_KEYS = frozenset({"archive", "category", "lookup_site", "lookup_type"})
REQUIRED_SUPER_MENU_KEYS = frozenset({"users", "content"})


def build_domain_schema(
    title: str,
    domain: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    *,
    proposal_text: str = "",
) -> dict[str, Any]:
    from app.bake.staff_posts import attach_staff_posts

    if domain == "DOM-GENERIC":
        from app.bake.archetype_shells import finalize_generic_schema

        return finalize_generic_schema(
            title, archetype, archetypes, proposal_text=proposal_text
        )
    builder = SCHEMA_BUILDERS.get(domain, lambda t: generic_schema(t, domain))
    if domain in SCHEMA_BUILDERS:
        from app.bake.schema.templates import _SCENE_COPY_DOMAINS

        if domain in _SCENE_COPY_DOMAINS:
            schema = builder(title, proposal_text=proposal_text)
        else:
            schema = builder(title)
    else:
        schema = generic_schema(title, domain)
    schema = attach_profile_fields(
        schema, domain, title=title, proposal_text=proposal_text
    )
    return attach_staff_posts(
        schema, domain, archetype, archetypes, proposal_text=proposal_text
    )


def required_capabilities(
    domain: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
) -> list[str]:
    if domain == "DOM-GENERIC" and (archetype or archetypes):
        from app.bake.archetype_shells import shell_capabilities

        return shell_capabilities(archetype, archetypes=archetypes)
    return list(DOMAIN_CAPABILITIES.get(domain, DOMAIN_CAPABILITIES["DOM-GENERIC"]))


def _merge_baseline_tags(spec: dict[str, Any]) -> None:
    from app.bake.catalog import BASELINE_TAGS

    baseline = list(spec.get("baseline") or [])
    for tag in BASELINE_TAGS:
        if tag not in baseline:
            baseline.append(tag)
    spec["baseline"] = baseline


def _sync_named_domain_from_catalog(spec: dict[str, Any], dom: dict[str, Any]) -> None:
    """结构性字段以 catalog 为准；保留题面 out_of_mvp 附加项。"""
    catalog_gate = dom.get("gate")
    if catalog_gate:
        spec["gate"] = copy.deepcopy(catalog_gate)
    if "runtime" in dom:
        spec["runtime"] = copy.deepcopy(dom.get("runtime") or {})
    if dom.get("flows"):
        spec["flows"] = list(dom["flows"])
    if dom.get("roles"):
        spec["roles"] = list(dom["roles"])
    if dom.get("entities"):
        spec["entities"] = list(dom["entities"])

    cat_feats = copy.deepcopy(dom.get("features") or [])
    if not cat_feats:
        return
    cat_names = {f.get("name") for f in cat_feats if isinstance(f, dict)}
    extras = [
        f
        for f in (spec.get("features") or [])
        if isinstance(f, dict)
        and f.get("status") == "out_of_mvp"
        and f.get("name") not in cat_names
    ]
    spec["features"] = cat_feats + extras


def ensure_spec_schema(spec: dict[str, Any] | None) -> dict[str, Any]:
    """旧项目补齐；gate/features/runtime 等结构性字段以 catalog 为准，避免契约漂移误杀。"""
    from app.bake.catalog import DOMAINS

    spec = dict(spec or {})
    domain = spec.get("domain") or "DOM-GENERIC"
    archetype = spec.get("archetype") or "ARCH-CRUD"
    title = spec.get("title") or "毕设系统"
    _merge_baseline_tags(spec)
    # GENERIC：按 ARCH-* 重绑壳（runtime/gate/features/capabilities/schema/岗位）
    if domain == "DOM-GENERIC":
        from app.bake.archetype_shells import apply_generic_shell

        prop_body = ""
        if isinstance(spec.get("proposal_text"), str):
            prop_body = spec["proposal_text"]
        else:
            prop = spec.get("proposal")
            if isinstance(prop, dict):
                prop_body = str(
                    prop.get("excerpt")
                    or prop.get("text")
                    or prop.get("summary")
                    or prop.get("background")
                    or ""
                )
            elif isinstance(prop, str):
                prop_body = prop
        spec = apply_generic_shell(spec, proposal_text=prop_body)
        _merge_baseline_tags(spec)
    else:
        dom = DOMAINS.get(domain) or DOMAINS["DOM-GENERIC"]
        _sync_named_domain_from_catalog(spec, dom)
        arches = list(spec.get("archetypes") or [archetype])
        prop_body = ""
        if isinstance(spec.get("proposal_text"), str):
            prop_body = spec["proposal_text"]
        else:
            prop = spec.get("proposal")
            if isinstance(prop, dict):
                prop_body = str(
                    prop.get("excerpt")
                    or prop.get("text")
                    or prop.get("summary")
                    or ""
                )
            elif isinstance(prop, str):
                prop_body = prop
        if not isinstance(spec.get("schema"), dict) or not spec["schema"].get("labels"):
            spec["schema"] = build_domain_schema(
                title,
                domain,
                archetype=archetype,
                archetypes=arches,
                proposal_text=prop_body,
            )
        else:
            # 资料页身份随开题场景；有 profile 时也重绑，避免旧壳校园身份残留
            spec["schema"] = attach_profile_fields(
                spec["schema"],
                domain,
                title=title,
                proposal_text=prop_body,
            )
            # 始终重绑岗位表 + allowAppointFromUsers（仅有 staff_posts 的旧壳会漏关任命）
            from app.bake.staff_posts import attach_staff_posts

            spec["schema"] = attach_staff_posts(
                dict(spec["schema"]),
                domain,
                archetype,
                arches,
                proposal_text=prop_body,
            )
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


def apply_reservation_options_from_proposal(schema: dict[str, Any], proposal_text: str) -> None:
    """开题若写明人工确认预约，打开 reservation.requireConfirm（默认占坑即确认）。"""
    caps = schema.get("capabilities") or []
    if "slot_reserve" not in caps:
        return
    text = proposal_text or ""
    if not re.search(
        r"人工确认|管理员确认|人工审核|"
        r"预约须?(?:经)?审核|审核通过后(?:再)?(?:预约|挂号|生效)|"
        r"确认后(?:再)?(?:生效|预约|挂号)|待确认后",
        text,
    ):
        return
    entities = schema.setdefault("entities", {})
    resv = entities.get("reservation")
    if isinstance(resv, dict):
        resv["requireConfirm"] = True


def attach_accept(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain", "DOM-GENERIC")
    archetype = spec.get("archetype")
    arches = list(spec.get("archetypes") or ([archetype] if archetype else []))
    req = list(
        spec.get("capabilities")
        or required_capabilities(domain, archetype, archetypes=arches)
    )
    from app.bake.features.archive_log import apply_archive_log_to_spec
    from app.bake.features.favorites import apply_favorites_to_spec
    from app.bake.features.guestbook import apply_guestbook_to_spec
    from app.bake.features.loyalty import apply_loyalty_to_spec
    from app.bake.features.order_extras import apply_order_extras_to_spec
    from app.bake.features.proposal_caps import merge_proposal_capabilities
    from app.bake.features.ux_scan import apply_ux_to_spec
    from app.services.proposal import strip_non_dev_sections

    body = strip_non_dev_sections(proposal_text or "")
    req = merge_proposal_capabilities(
        req,
        body,
        domain=domain,
        archetype=archetype,
        archetypes=arches,
    )
    decision = resolve_accept(
        req,
        body,
        has_domain_overlay=domain in DOMAINS_WITH_OVERLAY,
        has_baseline_runtime=baseline_runtime_covers(
            domain, archetype, archetypes=arches
        )
        and not (set(req) - BASELINE_RUNTIME_CAPS),
        archetypes=arches,
        domain=domain,
        primary_archetype=archetype,
    )
    schema = build_domain_schema(
        spec.get("title") or "毕设系统",
        domain,
        archetype=archetype,
        archetypes=arches,
        proposal_text=body,
    )
    schema = copy.deepcopy(schema)
    schema["capabilities"] = req
    schema["accept"] = decision["accept"]
    schema["missing_capabilities"] = decision["missing_capabilities"]
    schema["out_of_mvp_signals"] = decision["out_of_mvp_signals"]

    apply_reservation_options_from_proposal(schema, body)

    # 「本期不做」随域目录 + 开题扫描合成；不把 catalog 列表当写死交付契约
    composed_oos = compose_out_of_mvp(
        domain,
        body,
        scanned_signals=decision["out_of_mvp_signals"],
    )
    signal_set = {str(s) for s in (decision["out_of_mvp_signals"] or [])}
    keep_features = [
        f
        for f in (spec.get("features") or [])
        if not (isinstance(f, dict) and f.get("status") == "out_of_mvp")
    ]
    for item in composed_oos:
        name = f"{item}（开题提及）" if item in signal_set else item
        keep_features.append({"name": name, "status": "out_of_mvp"})

    out = {
        **spec,
        "capabilities": req,
        "accept": decision["accept"],
        "accept_reason": decision["reason"],
        "missing_capabilities": decision["missing_capabilities"],
        "out_of_mvp_signals": decision["out_of_mvp_signals"],
        "out_of_mvp": composed_oos,
        "schema": schema,
        "features": keep_features,
        # bake 扫词/岗位文案用；与 proposal 摘要并存
        "proposal_text": body,
    }
    out = apply_loyalty_to_spec(out, body)
    out = apply_guestbook_to_spec(out, body)
    out = apply_favorites_to_spec(out, body)
    out = apply_ux_to_spec(out, body)
    out = apply_archive_log_to_spec(out, body)
    out = apply_order_extras_to_spec(out, body)

    # 岗位随开题补挂（如 FOOD 骑手）；复用 attach_staff_posts，刷新 spec.roles
    from app.bake.domains import DOMAINS
    from app.bake.staff_posts import attach_staff_posts, roles_for_spec

    sch = out.get("schema") if isinstance(out.get("schema"), dict) else {}
    out["schema"] = attach_staff_posts(
        dict(sch),
        domain,
        archetype,
        arches,
        proposal_text=body,
    )
    dom_roles = list((DOMAINS.get(domain) or {}).get("roles") or [])
    out["roles"] = roles_for_spec(dom_roles, out["schema"])
    return out


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

    roles = schema.get("roles") or {}
    if isinstance(roles, dict):
        posts = roles.get("staff_posts")
        if posts is not None:
            from app.bake.staff_posts import validate_staff_posts

            for e in validate_staff_posts(posts if isinstance(posts, list) else []):
                errors.append(e)

    return len(errors) == 0, errors


def merge_schema(base: dict[str, Any], patch: dict[str, Any] | None) -> dict[str, Any]:
    """浅合并 labels/seeds/menus；entities 按 key 深合并；禁止改 capabilities 集合外的随意结构由校验兜底。"""
    out = copy.deepcopy(base)
    if not patch:
        return out
    for key in ("title",):
        if patch.get(key):
            out[key] = patch[key]
    for key in ("labels", "seeds"):
        if isinstance(patch.get(key), dict):
            out.setdefault(key, {})
            out[key] = {**out.get(key, {}), **patch[key]}
    # roles：user/admin/subadmin 按槽深合并（只改 label 时保留 id）；staff_posts 整表替换
    if isinstance(patch.get("roles"), dict):
        out.setdefault("roles", {})
        for rk, rv in patch["roles"].items():
            if rk == "staff_posts" and isinstance(rv, list):
                out["roles"]["staff_posts"] = rv
            elif isinstance(rv, dict) and isinstance(out["roles"].get(rk), dict):
                out["roles"][rk] = {**out["roles"][rk], **rv}
            else:
                out["roles"][rk] = rv
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
                # 动作实体 label 须为短名词；LLM 常把管理端「XX记录」写进 label
                if ek in ("reservation", "ticket") and isinstance(merged.get("label"), str):
                    lab = merged["label"].strip()
                    if lab.endswith("记录") and len(lab) > 2:
                        merged["label"] = lab.removesuffix("记录").strip() or cur.get("label") or lab
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
    if not labels.get("messagesPageLead"):
        ticket = ((spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        remind = (ticket.get("verbs") or {}).get("remind")
        if remind and remind != "提醒":
            labels["messagesPageLead"] = f"审核结果、{remind}提醒与系统通知。"
        elif ticket.get("allowCheckin"):
            labels["messagesPageLead"] = "审核结果、活动提醒与系统通知。"
        else:
            labels["messagesPageLead"] = "审核结果与系统通知。"
    if not labels.get("recommendLatestHint"):
        labels["recommendLatestHint"] = "最新发布"
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
