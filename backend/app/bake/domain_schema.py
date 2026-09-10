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
# 多商家商城：商品/活动对商家开放（builders_slot 显式 superOnly=false），不强制超管
MARKETPLACE_MERCHANT_MENU_KEYS = frozenset({"archive", "content"})


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

        if domain in _SCENE_COPY_DOMAINS or domain == "DOM-LIBRARY":
            schema = builder(title, proposal_text=proposal_text)
        else:
            schema = builder(title)
    else:
        schema = generic_schema(title, domain)
    schema = attach_profile_fields(
        schema, domain, title=title, proposal_text=proposal_text
    )
    schema = attach_staff_posts(
        schema,
        domain,
        archetype,
        archetypes,
        proposal_text=proposal_text,
        title=title,
    )
    from app.bake.features.temporal_field import apply_soft_calendar_types

    apply_soft_calendar_types(schema, proposal_text)
    return schema


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
        from app.bake.match_path_axes import match_path_override_scope
        from app.bake.schema.shells import _SCENE_COPY_DOMAINS

        # 场景/产品皮域必须按开题重编壳：否则匹配期旧 schema 会卡住
        # （例：EVENT 种子已是应急事件标题，列表仍显示「对象姓名/提交打卡」）
        # 须带 match_path 覆盖：否则生成前重编会丢掉运营台手改的身份/入口
        path = spec.get("match_path") if isinstance(spec.get("match_path"), dict) else {}
        stale_or_missing = (
            not isinstance(spec.get("schema"), dict) or not spec["schema"].get("labels")
        )
        with match_path_override_scope(
            domain, path.get("scene"), path.get("entry")
        ):
            if stale_or_missing or domain in _SCENE_COPY_DOMAINS:
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
                    title=title,
                )
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
    if not prop_body:
        prop_body = title

    if not spec.get("accept"):
        from app.bake.match_path_axes import match_path_override_scope

        path = spec.get("match_path") if isinstance(spec.get("match_path"), dict) else {}
        with match_path_override_scope(
            domain, path.get("scene"), path.get("entry")
        ):
            spec = attach_accept(spec, prop_body)
    else:
        # accept 已定稿时 attach_accept 不再跑；仍须同步按需 AI 开关 → cap/SQL/菜单
        from app.bake.features.ai_assistant import apply_ai_assistant_to_spec

        spec = apply_ai_assistant_to_spec(spec, prop_body)
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
    from app.bake.features.audit_log import apply_audit_log_to_spec
    from app.bake.features.message_template import apply_message_template_to_spec
    from app.bake.features.code_qr import apply_code_qr_to_spec
    from app.bake.features.staff_roster import apply_staff_roster_to_spec
    from app.bake.features.room_equipment import apply_room_equipment_to_spec
    from app.bake.features.book_hold import apply_book_hold_to_spec
    from app.bake.features.post_mute import apply_post_mute_to_spec
    from app.bake.features.book_suggest import apply_book_suggest_to_spec
    from app.bake.features.product_spec import apply_product_spec_to_spec
    from app.bake.features.favorites import apply_favorites_to_spec
    from app.bake.features.dm import apply_dm_to_spec
    from app.bake.features.exam import apply_exam_to_spec
    from app.bake.features.survey import apply_survey_to_spec
    from app.bake.features.vote import apply_vote_to_spec
    from app.bake.features.doclib import apply_doclib_to_spec
    from app.bake.features.timebank import apply_timebank_to_spec
    from app.bake.features.seat_select import apply_seat_select_to_spec
    from app.bake.features.stock_io import apply_stock_io_to_spec
    from app.bake.features.stock_scrap import apply_stock_scrap_to_spec
    from app.bake.features.e_sign import apply_e_sign_to_spec
    from app.bake.features.guestbook import apply_guestbook_to_spec
    from app.bake.features.ai_assistant import apply_ai_assistant_to_spec
    from app.bake.features.loyalty import apply_loyalty_to_spec
    from app.bake.features.order_extras import apply_order_extras_to_spec
    from app.bake.features.proposal_caps import merge_proposal_capabilities
    from app.bake.features.ux_scan import apply_ux_to_spec
    from app.bake.match_path_axes import match_path_override_scope
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
    # 须吃 match_path：否则 ensure_spec_schema / 二次 attach 会丢掉运营台手改入口
    path = spec.get("match_path") if isinstance(spec.get("match_path"), dict) else {}
    with match_path_override_scope(domain, path.get("scene"), path.get("entry")):
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
    from app.bake.features.ticket_flow_opts import apply_ticket_flow_opts_to_schema

    apply_ticket_flow_opts_to_schema(schema, body)

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
    out = apply_exam_to_spec(out, body)
    out = apply_survey_to_spec(out, body)
    out = apply_vote_to_spec(out, body)
    out = apply_doclib_to_spec(out, body)
    out = apply_timebank_to_spec(out, body)
    out = apply_seat_select_to_spec(out, body)
    out = apply_stock_io_to_spec(out, body)
    out = apply_stock_scrap_to_spec(out, body)
    out = apply_e_sign_to_spec(out, body)
    out = apply_guestbook_to_spec(out, body)
    out = apply_ai_assistant_to_spec(out, body)
    out = apply_dm_to_spec(out, body)
    out = apply_favorites_to_spec(out, body)
    out = apply_ux_to_spec(out, body)
    out = apply_archive_log_to_spec(out, body)
    out = apply_audit_log_to_spec(out, body)
    out = apply_message_template_to_spec(out, body)
    out = apply_code_qr_to_spec(out, body)
    out = apply_staff_roster_to_spec(out, body)
    out = apply_room_equipment_to_spec(out, body)
    out = apply_book_hold_to_spec(out, body)
    out = apply_post_mute_to_spec(out, body)
    out = apply_book_suggest_to_spec(out, body)
    out = apply_product_spec_to_spec(out, body)
    out = apply_order_extras_to_spec(out, body)
    from app.bake.features.core_cap_scan import apply_core_caps_to_spec
    from app.bake.features.ticket_flow_opts import apply_ticket_flow_opts_to_spec

    out = apply_core_caps_to_spec(out, body)
    out = apply_ticket_flow_opts_to_spec(out, body)

    # 岗位随开题补挂（如 FOOD 骑手）；复用 attach_staff_posts，刷新 spec.roles
    from app.bake.domains import DOMAINS
    from app.bake.staff_posts import attach_staff_posts, roles_for_spec

    sch = out.get("schema") if isinstance(out.get("schema"), dict) else {}
    # 岗包按能力并菜单：须带上最终 capabilities
    sch = dict(sch)
    sch["capabilities"] = list(out.get("capabilities") or sch.get("capabilities") or [])
    with match_path_override_scope(domain, path.get("scene"), path.get("entry")):
        out["schema"] = attach_staff_posts(
            sch,
            domain,
            archetype,
            arches,
            proposal_text=body,
            title=str(spec.get("title") or ""),
        )
    dom_roles = list((DOMAINS.get(domain) or {}).get("roles") or [])
    out["roles"] = roles_for_spec(dom_roles, out["schema"])
    # 收束：能力已开则用户菜单必有对应项（防壳文案重写 / 填岛漏挂）
    from app.bake.schema.menu_utils import sync_user_menus_from_caps

    sch_final = out.get("schema") if isinstance(out.get("schema"), dict) else {}
    sync_user_menus_from_caps(sch_final)
    out["schema"] = sch_final
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

    # 全厂不变式：admin 菜单须含用户 + 公告 + ≥1 领域主数据（默认 superOnly；
    # shopMarketplace 下 archive/content 对商家开放，见 MARKETPLACE_MERCHANT_MENU_KEYS）
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
        marketplace = bool(schema.get("shopMarketplace"))
        for m in admin_menus:
            if not isinstance(m, dict):
                continue
            k = m.get("key")
            if k in MASTER_MENU_KEYS or k in REQUIRED_SUPER_MENU_KEYS:
                if marketplace and k in MARKETPLACE_MERCHANT_MENU_KEYS:
                    continue
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
        # 有岗位表时任命开关必须是显式 bool（避免 FE schema 缺省 false、yml 回落 true 分叉）
        if isinstance(posts, list) and posts:
            ap = roles.get("allowAppointFromUsers")
            if not isinstance(ap, bool):
                errors.append("roles.allowAppointFromUsers 须为 bool（有 staff_posts 时）")

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
            if not isinstance(items, list):
                continue
            # 按 key 合并：禁止填岛整表替换把 favorites/dm/order_reviews 冲掉
            base_list = list(out["menus"].get(side) or [])
            by_key: dict[str, dict] = {}
            order: list[str] = []
            for m in base_list:
                if not isinstance(m, dict) or not m.get("key"):
                    continue
                k = str(m["key"])
                by_key[k] = dict(m)
                order.append(k)
            for m in items:
                if not isinstance(m, dict) or not m.get("key"):
                    continue
                k = str(m["key"])
                if k in by_key:
                    by_key[k] = {**by_key[k], **m}
                else:
                    by_key[k] = dict(m)
                    order.append(k)
            out["menus"][side] = [by_key[k] for k in order if k in by_key]
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


_MATERIAL_HEADER_RE = re.compile(r"【材料[：:][^】]*】\s*")
_THESIS_BOILER_RE = re.compile(
    r"(?:本科)?毕业设计[（(]?论文[）)]?开题报告\s*(?:题目[：:]\s*)?"
)
_AUTH_LEAD_FALLBACK = "验证码登录，开放注册；登录后可使用系统主流程。"
# 开题合并正文 / 样例文件名不得上登录页与轮播
_UI_COPY_DOM_ID_RE = re.compile(r"(?:^|[^\w-])DOM-[A-Z]{2,}(?:-|[^A-Z]|$)")
_UI_COPY_SAMPLE_FILE_RE = re.compile(r"\d{1,2}-DOM-[A-Z]+")

# 学生可见面禁止的工厂说明书腔（出包前全量扫）
FACTORY_UI_FORBIDDEN: tuple[str, ...] = (
    "双通道",
    "分通道",
    "双轨沟通",
    "双轨",
    "非即时通讯",
    "非即时",
    "短轮询",
    "非 WebSocket",
    "非WebSocket",
    "非站内信",
    "商家走商家端",
    "商家端「留言",
    "走商家端",
    "由 bake",
    "不含工厂",
    "开题写明",
    "开题写到",
    "开题可",
    "本开题",
    "开题含",
    "开题提及",
    "材料命中",
    "填岛",
    "能力岛",
    "本期不做",
    "不在本期",
    "本期不对接",
    "本期不含",
    "扫词开",
    "不对接",
    "不对接银行",
    "不对接闸机",
    "不对接学信网",
    "不对接微信",
    "不对接支付宝",
    "第三方支付",
    "商户平台",
    "本系统内支付",
    "本系统内支付流程",
    "模拟支付",  # 学生端写「在线支付」
    "无真支付",
    "无真对象",
    "占位 URL",
    "占位URL",
    "非真支付",
    "非真机考",
    "非真对象",
    "非真锁座",
    "非真门禁",
    "非 CA",
    "非CA",
    "非法大大",
    "非智能排课",
    "弱约束",
    "真门禁硬件",
    "人脸/GPS",
    "见 e_sign",
    "本地签章见",
    # 与 p3s 同源：学生可见「演示*」口吻（清洗按钮应能盖住，不只靠重 bake）
    "演示密码",
    "演示支付",
    "演示数据",
    "演示账号",
    "演示余额",
    "演示通行",
    "本期演示",
    "演示库",
    "本地签章演示",
    "演示物流",
)

# schema/种子字符串里演示口吻 → 产品表述（与 p3s 对齐）
_DEMO_UI_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("演示密码", "支付密码"),
    ("演示支付", "在线支付"),
    ("演示数据", "业务数据"),
    ("演示账号", "登录账号"),
    ("演示余额", "账户余额"),
    ("演示通行", "通行码"),
    ("本期演示", "本期"),
    ("演示库", "业务库"),
    ("本地签章演示", "本地签章"),
    ("演示物流", "物流信息"),
)

# 含禁词的括注整段去掉（保留主句）
_FACTORY_PAREN_RE = re.compile(
    r"[（(][^）)]*(?:"
    + "|".join(re.escape(x) for x in (
        "双通道",
        "分通道",
        "双轨",
        "非即时",
        "短轮询",
        "WebSocket",
        "非站内信",
        "占位",
        "无真",
        "商户平台",
        "第三方支付",
        "本系统内",
        "不对接",
        "bake",
        "开题",
        "工厂",
        "扫词",
        "非真",
        "非 CA",
        "非CA",
        "非法大大",
        "非智能",
        "弱约束",
        "不在本期",
        "本期不",
        "真门禁",
        "≠",
        "e_sign",
    ))
    + r")[^）)]*[）)]"
)

_LABEL_FALLBACKS: dict[str, str] = {
    "guestbookPageLead": "有问题可向平台留言，我们会尽快回复。",
    "dmPageLead": "与其他用户一对一沟通，打开会话后自动刷新新消息。",
    "dmNewTitle": "新建私信",
    "dmPeerPlaceholder": "选择对方账号",
    "dmEmptyPeers": "暂无会话，点「新建」选人开聊。",
    "dmEmptyChat": "选择左侧会话，或新建私信。",
    "dmMerchantPageLead": "回复买家咨询，打开会话后自动刷新新消息。",
    "dmMerchantNewTitle": "联系买家",
    "dmMerchantPeerPlaceholder": "选择买家账号",
    "dmMerchantEmptyPeers": "暂无会话，买家发起咨询后会出现在这里；也可点「新建」选买家。",
    "dmMerchantEmptyChat": "选择左侧会话，或新建联系买家。",
    "demoPayHint": "在线支付：选择支付宝或微信并输入支付密码完成本单。",
    "authLead": _AUTH_LEAD_FALLBACK,
    "noticePageLead": "通知与须知，点击条目阅读全文。",
    "messagesPageLead": "审核结果与系统通知。",
    "orderReviewPageLead": "对已完成订单进行星级与文字评价。",
    "eSignLead": "上传签章图并勾选同意后完成签署。",
    "codeQrHint": "扫码可识别下方码文，用于现场出示核对。",
    "docBrowseLead": "浏览开放资料，按权限下载；下载将记入台账。",
    "staffRosterPageLead": "按员工与日期维护班次；预约页可查看当日当班人员。",
}


def factory_ui_polluted(text: str) -> bool:
    """产品 UI / 种子文案是否混进工厂说明书口吻或演示口吻。"""
    s = str(text or "")
    if not s.strip():
        return False
    if ui_copy_polluted(s):
        return True
    for bad in FACTORY_UI_FORBIDDEN:
        if bad in s:
            return True
    # DOM-* 域编号不得进学生可见句
    if _UI_COPY_DOM_ID_RE.search(s) or "DOM-" in s:
        return True
    try:
        from app.bake.gates.semantic import DEMO_VISIBLE_RE

        if DEMO_VISIBLE_RE.search(s):
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def scrub_factory_ui_text(text: str, *, fallback: str = "") -> str:
    """去掉工厂括注与演示口吻；仍污染则回退到调用方给出的产品文案（勿拆分句硬凑）。"""
    raw = str(text or "").strip()
    if not raw:
        return fallback
    cleaned = _FACTORY_PAREN_RE.sub("", raw)
    for old, new in _DEMO_UI_REPLACEMENTS:
        cleaned = cleaned.replace(old, new)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip(" ，,。.;；")
    if cleaned != raw.strip():
        # 只在剥掉括注后补句号，避免把短标题改成「客服。」
        if cleaned and not cleaned.endswith(("。", "！", "？", ".", "!", "?")):
            if any("\u4e00" <= c <= "\u9fff" for c in cleaned):
                cleaned += "。"
    if factory_ui_polluted(cleaned):
        return fallback
    return cleaned or fallback


def find_factory_ui_hits(obj: Any, path: str = "") -> list[tuple[str, str, str]]:
    """递归找出学生可见字符串中的工厂禁词命中：(path, bad, snippet)。"""
    hits: list[tuple[str, str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            # 内部键不扫（能力码 / 表名等）
            if k in (
                "capabilities",
                "runtime",
                "gate",
                "proposal_text",
                "proposal",
                "out_of_mvp",
                "accept_reason",
                "domain",
                "archetype",
                "archetypes",
            ):
                continue
            hits.extend(find_factory_ui_hits(v, f"{path}.{k}" if path else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(find_factory_ui_hits(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        s = obj.strip()
        if not s:
            return hits
        for bad in FACTORY_UI_FORBIDDEN:
            if bad in s:
                hits.append((path or "(root)", bad, s[:120]))
                break
        else:
            if _UI_COPY_DOM_ID_RE.search(s) or (
                "DOM-" in s and not s.startswith("http")
            ):
                hits.append((path or "(root)", "DOM-*", s[:120]))
    return hits


def scrub_schema_student_copy(schema: dict[str, Any]) -> dict[str, Any]:
    """出包前清洗 labels / seeds / 菜单文案等学生可见面。"""
    if not isinstance(schema, dict):
        return schema
    out = dict(schema)
    # 工厂键不进学生 schema 面
    out.pop("dmPeerMode", None)

    labels = dict(out.get("labels") or {})
    shop_cs = bool(out.get("dmShopCs"))
    for key, val in list(labels.items()):
        fb = _LABEL_FALLBACKS.get(key, "")
        if key == "dmPageLead" and shop_cs:
            fb = "与店铺商家一对一沟通，打开会话后自动刷新新消息。"
        if key == "dmNewTitle" and shop_cs:
            fb = "联系商家客服"
        if key == "dmPeerPlaceholder" and shop_cs:
            fb = "选择店铺商家"
        if key == "dmEmptyPeers" and shop_cs:
            fb = "暂无会话，点「新建」选店铺商家。"
        if key == "dmEmptyChat" and shop_cs:
            fb = "选择左侧会话，或新建联系商家。"
        if key == "dmMerchantPageLead" and shop_cs:
            fb = "回复买家咨询，打开会话后自动刷新新消息。"
        if key == "dmMerchantNewTitle" and shop_cs:
            fb = "联系买家"
        if key == "dmMerchantPeerPlaceholder" and shop_cs:
            fb = "选择买家账号"
        if key == "dmMerchantEmptyPeers" and shop_cs:
            fb = "暂无会话，买家发起咨询后会出现在这里；也可点「新建」选买家。"
        if key == "dmMerchantEmptyChat" and shop_cs:
            fb = "选择左侧会话，或新建联系买家。"
        if key == "guestbookPageLead" and shop_cs:
            fb = "有问题可向平台留言，我们会尽快回复。"
        if isinstance(val, str):
            if factory_ui_polluted(val) or _FACTORY_PAREN_RE.search(val):
                labels[key] = scrub_factory_ui_text(val, fallback=fb or "欢迎使用。")
        elif isinstance(val, list):
            new_list = []
            changed = False
            for item in val:
                if isinstance(item, str) and factory_ui_polluted(item):
                    new_list.append(scrub_factory_ui_text(item, fallback=""))
                    changed = True
                else:
                    new_list.append(item)
            if changed:
                labels[key] = [x for x in new_list if x != ""]
    out["labels"] = labels

    seeds = dict(out.get("seeds") or {})
    for key, val in list(seeds.items()):
        if not isinstance(val, str):
            continue
        fb = "系统已就绪，欢迎使用。" if key == "noticeBody" else ""
        if factory_ui_polluted(val):
            seeds[key] = scrub_factory_ui_text(val, fallback=fb)
    out["seeds"] = seeds

    for surface_key in ("registerHint",):
        raw = out.get(surface_key)
        if isinstance(raw, str) and factory_ui_polluted(raw):
            out[surface_key] = scrub_factory_ui_text(
                raw, fallback="开放注册；管理员账号由系统维护。"
            )

    # auth / notice / homeCards 等嵌套文案
    for surface_key in ("auth", "notice", "homeCards", "portal"):
        raw = out.get(surface_key)
        if isinstance(raw, str) and factory_ui_polluted(raw):
            out[surface_key] = scrub_factory_ui_text(raw, fallback="")
        elif isinstance(raw, dict):
            nested = dict(raw)
            changed = False
            for nk, nv in list(nested.items()):
                if isinstance(nv, str) and factory_ui_polluted(nv):
                    nested[nk] = scrub_factory_ui_text(nv, fallback="")
                    changed = True
                elif isinstance(nv, list):
                    nl = []
                    lc = False
                    for item in nv:
                        if isinstance(item, str) and factory_ui_polluted(item):
                            nl.append(scrub_factory_ui_text(item, fallback=""))
                            lc = True
                        elif isinstance(item, dict):
                            im = dict(item)
                            for ik in ("title", "lead", "label", "desc", "body", "text"):
                                iv = im.get(ik)
                                if isinstance(iv, str) and factory_ui_polluted(iv):
                                    im[ik] = scrub_factory_ui_text(iv, fallback="")
                                    lc = True
                            nl.append(im)
                        else:
                            nl.append(item)
                    if lc:
                        nested[nk] = [x for x in nl if x != ""]
                        changed = True
            if changed:
                out[surface_key] = nested
        elif isinstance(raw, list):
            nl = []
            changed = False
            for item in raw:
                if isinstance(item, str) and factory_ui_polluted(item):
                    nl.append(scrub_factory_ui_text(item, fallback=""))
                    changed = True
                elif isinstance(item, dict):
                    im = dict(item)
                    for ik in ("title", "lead", "label", "desc", "body", "text"):
                        iv = im.get(ik)
                        if isinstance(iv, str) and factory_ui_polluted(iv):
                            im[ik] = scrub_factory_ui_text(iv, fallback="")
                            changed = True
                    nl.append(im)
                else:
                    nl.append(item)
            if changed:
                out[surface_key] = nl

    ents = out.get("entities")
    if isinstance(ents, dict):
        ents_out: dict[str, Any] = {}
        for ek, ev in ents.items():
            if not isinstance(ev, dict):
                ents_out[ek] = ev
                continue
            em = dict(ev)
            for ik in ("label", "labelPlural", "lead", "hint"):
                iv = em.get(ik)
                if isinstance(iv, str) and factory_ui_polluted(iv):
                    em[ik] = scrub_factory_ui_text(iv, fallback=str(em.get("key") or ek))
            ents_out[ek] = em
        out["entities"] = ents_out

    menus = out.get("menus")
    if isinstance(menus, dict):
        menus_out: dict[str, Any] = {}
        for role, items in menus.items():
            if not isinstance(items, list):
                menus_out[role] = items
                continue
            new_items = []
            for m in items:
                if not isinstance(m, dict):
                    new_items.append(m)
                    continue
                mm = dict(m)
                lab = mm.get("label")
                if isinstance(lab, str) and factory_ui_polluted(lab):
                    mm["label"] = scrub_factory_ui_text(lab, fallback=str(mm.get("key") or "菜单"))
                new_items.append(mm)
            menus_out[role] = new_items
        out["menus"] = menus_out

    return out


def ui_copy_polluted(text: str) -> bool:
    """界面导语是否粘进开题材料头、样例文件名或开题报告套话。"""
    s = str(text or "")
    if not s.strip():
        return False
    if "【材料：" in s or "【材料:" in s:
        return True
    if "开题报告" in s:
        return True
    if ".txt】" in s or ".txt]" in s:
        return True
    if _UI_COPY_SAMPLE_FILE_RE.search(s) or _UI_COPY_DOM_ID_RE.search(s):
        return True
    if "题目：" in s or "题目:" in s:
        return True
    if "毕业设计" in s and ("论文" in s or "Spring" in s or "Vue" in s):
        return True
    return False


def scrub_ui_copy(text: str, *, fallback: str = "") -> str:
    """污染则回退；否则原样（已截断的开题句不硬修）。"""
    raw = str(text or "").strip()
    if not raw:
        return fallback
    if ui_copy_polluted(raw):
        return fallback
    return raw


def _ui_safe_excerpt(text: str, limit: int = 80) -> str:
    """开题合并正文 → 可上界面的短句；去掉材料文件名头与开题报告套话。"""
    s = (text or "").strip().replace("\n", " ")
    s = _MATERIAL_HEADER_RE.sub("", s)
    s = _THESIS_BOILER_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip(" ：:，,。.")
    if ui_copy_polluted(s):
        return ""
    return s[:limit]


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
    # 开题合并正文常带【材料：文件名】与开题报告套话，不可直接上登录页/轮播
    excerpt = _ui_safe_excerpt(proposal or title, limit=80)

    labels = dict((spec.get("schema") or {}).get("labels") or {})
    # 污染的导语槽清空，后面按缺省补中性句（与 _welcome_lead 同一套材料头判断）
    for key in ("authLead", "portalBannerWelcomeLead", "portalBannerLead"):
        raw = str(labels.get(key) or "")
        if ui_copy_polluted(raw):
            labels[key] = ""
    # 保留领域已给的短产品名；勿用开题长标题盖掉
    if not labels.get("appName") or labels.get("appName") == title:
        labels["appName"] = product_name_from_title(title)
    # 领域壳已写 authLead 时绝不覆盖；缺省才给中性登录导语（禁止粘贴开题原文）
    if not str(labels.get("authLead") or "").strip():
        labels["authLead"] = _AUTH_LEAD_FALLBACK
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
    caps = (spec.get("schema") or {}).get("capabilities") or spec.get("capabilities") or []
    if "recommend" in caps and not labels.get("recommendLatestHint"):
        labels["recommendLatestHint"] = "最新发布"
    if enabled and excerpt and excerpt != title and not seeds.get("noticeBody"):
        seeds["noticeBody"] = f"系统已就绪。{excerpt}"[:200]
    # 开题摘录 / 既有种子不得把说明书腔带上公告
    for sk, sv in list(seeds.items()):
        if isinstance(sv, str) and factory_ui_polluted(sv):
            fb = "系统已就绪，欢迎使用。" if sk == "noticeBody" else ""
            seeds[sk] = scrub_factory_ui_text(sv, fallback=fb)
    for lk, lv in list(labels.items()):
        if isinstance(lv, str) and factory_ui_polluted(lv):
            labels[lk] = scrub_factory_ui_text(
                lv, fallback=_LABEL_FALLBACKS.get(lk, "欢迎使用。")
            )
    return {
        "mode": "llm" if enabled else "deterministic",
        "labels": labels,
        "seeds": seeds,
        "title": title,
    }


def write_schema_artifacts(workspace: Path, schema: dict[str, Any]) -> list[str]:
    """写入 domain.schema.json 与 islands 摘要，供 gate / 前端对照。"""
    from app.bake.schema.menu_utils import sync_user_menus_from_caps

    if isinstance(schema, dict):
        sync_user_menus_from_caps(schema)
    schema = scrub_schema_student_copy(schema)
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


def text_has_factory_ui_forbidden(text: str) -> bool:
    """原文是否含工厂禁词 / 演示口吻（门禁 / 覆写判定共用）。"""
    if not text:
        return False
    for bad in FACTORY_UI_FORBIDDEN:
        if bad in text:
            return True
    try:
        from app.bake.gates.semantic import DEMO_VISIBLE_RE

        if DEMO_VISIBLE_RE.search(text):
            return True
    except Exception:  # noqa: BLE001
        pass
    return factory_ui_polluted(text)


def refresh_polluted_vue_from_baseline(workspace: Path) -> list[str]:
    """工作区 Vue 仍脏（工厂腔或演示口吻）、现网 baseline 已干净时，按相对路径覆写。

    不必整题重 bake。只动 frontend/src 下与 baseline 同路径且骨架侧已干净的文件。
    """
    from app.core.config import get_settings

    sk_root = get_settings().skeletons_dir / "baseline" / "frontend" / "src"
    fe = workspace / "frontend" / "src"
    if not sk_root.is_dir() or not fe.is_dir():
        return []
    written: list[str] = []
    for path in fe.rglob("*.vue"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text_has_factory_ui_forbidden(text):
            continue
        rel = path.relative_to(fe)
        src = sk_root / rel
        if not src.is_file():
            continue
        try:
            clean = src.read_text(encoding="utf-8")
        except OSError:
            continue
        if text_has_factory_ui_forbidden(clean):
            # 骨架本身仍脏：应修骨架，勿用脏文件覆盖
            continue
        if clean == text:
            continue
        path.write_text(clean, encoding="utf-8")
        written.append(
            ("frontend/src/" + rel.as_posix()).replace("\\", "/")
        )
    return written
