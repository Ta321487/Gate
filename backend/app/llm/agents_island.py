"""agents_island.py"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.bake.catalog import MatchResult, catalog_brief_for_match, merge_llm_match
from app.bake.domain_schema import (
    deterministic_llm_patch,
    merge_schema,
    validate_schema,
)
from app.bake.engine import emit_schema_to_workspace, llm_fill_islands
from app.bake.proposal_lexicon import dedupe_out_scope_vs_features
from app.bake.schema.er import (
    apply_er_label_patch,
    build_schema_model,
    collect_english_gaps,
    count_er_gaps,
    count_er_patch_fills,
    load_er_label_patch,
    sanitize_er_label_patch,
    save_er_label_patch,
)
from app.bake.schema.modules import (
    build_module_model,
    collect_module_label_gaps,
    load_module_label_patch,
    sanitize_module_label_patch,
    save_module_label_patch,
)
from app.bake.schema.testcases import (
    build_testcase_skeleton,
    load_testcase_label_patch,
    sanitize_testcase_label_patch,
    save_testcase_label_patch,
)
from app.llm.agents_common import *  # noqa: F403
from app.llm.client import (
    append_deepseek_log,
    budget_ok,
    chat,
    format_usage_detail,
    monthly_tokens_used,
)

def _sanitize_island_roles(data: dict[str, Any], base_roles: dict) -> dict[str, Any] | None:
    """只允许改已有角色/岗位的中文 label（开题原样）；禁止增删 id、改 kind/packs。"""
    if not isinstance(base_roles, dict) or not base_roles:
        return None
    src = data.get("roles") if isinstance(data.get("roles"), dict) else {}
    if not src:
        return None
    out: dict[str, Any] = {}
    for rid in _ROLE_LABEL_SLOTS:
        base_slot = base_roles.get(rid)
        if not isinstance(base_slot, dict):
            continue
        piece = src.get(rid) if isinstance(src.get(rid), dict) else None
        lab = None
        if piece and piece.get("label"):
            lab = str(piece["label"]).strip()[:24]
        elif isinstance(src.get(rid), str):
            lab = str(src[rid]).strip()[:24]
        if not lab:
            continue
        out[rid] = {
            **base_slot,
            "id": base_slot.get("id") or rid,
            "label": lab,
        }

    base_posts = base_roles.get("staff_posts")
    src_posts = src.get("staff_posts")
    if isinstance(base_posts, list) and base_posts and isinstance(src_posts, list):
        by_id = {
            str(p.get("id")): str(p.get("label") or "").strip()[:24]
            for p in src_posts
            if isinstance(p, dict) and p.get("id") and p.get("label")
        }
        if by_id:
            merged_posts = []
            changed = False
            for p in base_posts:
                if not isinstance(p, dict) or not p.get("id"):
                    continue
                row = dict(p)
                pid = str(p["id"])
                if pid in by_id and by_id[pid] and by_id[pid] != str(p.get("label") or ""):
                    row["label"] = by_id[pid]
                    changed = True
                merged_posts.append(row)
            if changed:
                out["staff_posts"] = merged_posts
                # 首个 clerk 与 subadmin 文案对齐（与 attach_staff_posts 一致）
                clerks = [p for p in merged_posts if p.get("kind") == "clerk"]
                if clerks and isinstance(base_roles.get("subadmin"), dict):
                    out["subadmin"] = {
                        **(out.get("subadmin") or base_roles["subadmin"]),
                        "id": "subadmin",
                        "label": clerks[0].get("label") or base_roles["subadmin"].get("label"),
                        "staffPostId": clerks[0].get("id"),
                    }
    return out or None

def _sanitize_island_patch(
    data: dict[str, Any],
    base_labels: dict,
    base_seeds: dict,
    base_roles: dict | None = None,
) -> dict[str, Any]:
    labels: dict[str, Any] = {}
    src_l = data.get("labels") if isinstance(data.get("labels"), dict) else data
    for k in _LABEL_KEYS:
        if k in src_l and src_l[k] is not None:
            v = src_l[k]
            if k == "authPoints" and isinstance(v, list):
                labels[k] = [str(x)[:40] for x in v[:6]]
            else:
                labels[k] = str(v)[:200]
    # 领域专名标题：若基线已有 noticePageTitle，LLM 可润色但保留非空
    if not labels.get("noticePageTitle") and base_labels.get("noticePageTitle"):
        labels["noticePageTitle"] = base_labels["noticePageTitle"]
    seeds: dict[str, Any] = {}
    src_s = data.get("seeds") if isinstance(data.get("seeds"), dict) else {}
    for k in _SEED_KEYS:
        if k in src_s and src_s[k] is not None:
            seeds[k] = str(src_s[k])[:500]
        elif k in data and isinstance(data.get(k), str):
            seeds[k] = str(data[k])[:500]
    if not seeds.get("noticeTitle") and base_seeds.get("noticeTitle"):
        seeds["noticeTitle"] = base_seeds["noticeTitle"]
    # 实体文案：仅 verbs/states/label
    entities_out: dict[str, Any] = {}
    ents = data.get("entities") if isinstance(data.get("entities"), dict) else {}
    for ek, ev in ents.items():
        if not isinstance(ev, dict):
            continue
        piece: dict[str, Any] = {}
        if ev.get("label"):
            lab = str(ev["label"])[:40].strip()
            # 动作名词勿带「记录」（与 merge_schema 一致）
            if ek in ("reservation", "ticket") and lab.endswith("记录") and len(lab) > 2:
                lab = lab.removesuffix("记录").strip() or lab
            piece["label"] = lab
        if ev.get("labelPlural"):
            piece["labelPlural"] = str(ev["labelPlural"])[:40]
        if isinstance(ev.get("verbs"), dict):
            piece["verbs"] = {str(k): str(v)[:40] for k, v in list(ev["verbs"].items())[:12]}
        if isinstance(ev.get("states"), dict):
            piece["states"] = {str(k): str(v)[:40] for k, v in list(ev["states"].items())[:12]}
        if piece:
            entities_out[ek] = piece
    patch: dict[str, Any] = {"mode": "llm", "labels": labels, "seeds": seeds}
    if entities_out:
        patch["entities"] = entities_out
    roles_out = _sanitize_island_roles(data, base_roles or {})
    if roles_out:
        patch["roles"] = roles_out
    if data.get("title"):
        patch["title"] = str(data["title"])[:120]
    return patch

async def run_island_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    workspace: Path,
    spec: dict[str, Any],
    llm_enabled: bool,
) -> tuple[list[str], str]:
    """
    返回 (written_paths, mode_meta)。
    无 Key / 关开关 / 超预算 → 确定性填岛。
    """
    use_llm = bool(llm_enabled and rt.stage_on("island_fill") and rt.configured)
    if use_llm and not await budget_ok(db, project_id, rt):
        use_llm = False
        append_deepseek_log(project_id, "island skip llm · budget exceeded")

    base = spec.get("schema") or {}
    if not use_llm:
        written = llm_fill_islands(workspace, spec, llm_enabled)
        await record_call(
            db,
            project_id=project_id,
            stage="emit",
            tokens=0,
            ok=True,
            detail="确定性," + ",".join(written),
        )
        return written, "deterministic"

    labels = dict(base.get("labels") or {})
    seeds = dict(base.get("seeds") or {})
    roles = dict(base.get("roles") or {})
    domain = spec.get("domain") or ""
    title = spec.get("title") or labels.get("appName") or "毕设系统"
    messages = [
        {
            "role": "system",
            "content": (
                "你是毕设港 Island Agent。只输出 JSON："
                '{"title","labels":{...},"seeds":{noticeTitle,noticeBody},'
                '"entities":{ticket?:{label,labelPlural,verbs,states},reservation?:{label,labelPlural,states}},'
                '"roles":{user?:{label},admin?:{label},subadmin?:{label},staff_posts?:[{id,label}]}}。'
                "labels 可含: " + ",".join(_LABEL_KEYS) + "。"
                "roles：开题/材料里写了什么岗位称呼就原样填进对应 label，禁止改写、近义替换或「润色」"
                "（写随访员就填随访员，勿改成上报人/业务员）；材料未写角色则不要输出 roles，保留 current_roles。"
                "禁止增删角色 id、禁止改 kind/packs。"
                "禁止改 menus/capabilities/路由/表结构；禁止输出代码。"
                "文案必须贴合领域，禁止出现其它领域错词（如宿舍系统勿写馆内/借阅）。"
                "entities.reservation/ticket 的 label 须为短动作名词（如挂号/预约/借阅），禁止带「记录」；「XX记录」仅用于管理端菜单。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "domain": domain,
                    "title": title,
                    "current_labels": labels,
                    "current_seeds": seeds,
                    "current_roles": {
                        "user": (roles.get("user") or {}).get("label")
                        if isinstance(roles.get("user"), dict)
                        else None,
                        "admin": (roles.get("admin") or {}).get("label")
                        if isinstance(roles.get("admin"), dict)
                        else None,
                        "subadmin": (roles.get("subadmin") or {}).get("label")
                        if isinstance(roles.get("subadmin"), dict)
                        else None,
                        "staff_posts": [
                            {"id": p.get("id"), "label": p.get("label"), "kind": p.get("kind")}
                            for p in (roles.get("staff_posts") or [])
                            if isinstance(p, dict) and p.get("id")
                        ],
                    },
                    "proposal": _proposal_text(spec)[:2500],
                    "entities_keys": list((base.get("entities") or {}).keys()),
                },
                ensure_ascii=False,
            ),
        },
    ]
    res = await chat(rt, messages, json_mode=True, temperature=0.35)
    append_deepseek_log(
        project_id,
        f"island ok={res.ok} {format_usage_detail(res)}",
    )

    patch = deterministic_llm_patch(spec, True)
    mode = "llm_fallback_deterministic"
    if res.ok and res.data:
        try:
            llm_patch = _sanitize_island_patch(res.data, labels, seeds, roles)
            merged_try = merge_schema(base, llm_patch)
            for k in ("accept", "missing_capabilities", "out_of_mvp_signals", "capabilities"):
                if k in base:
                    merged_try[k] = base[k]
            ok, errors = validate_schema(merged_try)
            if ok:
                patch = llm_patch
                mode = "llm"
            else:
                append_deepseek_log(project_id, "island validate fail · " + "; ".join(errors[:3]))
        except Exception as e:  # noqa: BLE001
            append_deepseek_log(project_id, f"island merge fail · {e}")

    merged = merge_schema(base, patch)
    for k in ("accept", "missing_capabilities", "out_of_mvp_signals", "capabilities"):
        if k in base:
            merged[k] = base[k]
    ok, errors = validate_schema(merged)
    if not ok:
        # 最后兜底确定性
        patch = deterministic_llm_patch(spec, False)
        merged = merge_schema(base, patch)
        for k in ("accept", "missing_capabilities", "out_of_mvp_signals", "capabilities"):
            if k in base:
                merged[k] = base[k]
        mode = "deterministic_recover"
        ok, errors = validate_schema(merged)
        if not ok:
            await record_call(
                db,
                project_id=project_id,
                stage="island_fill",
                tokens=res.tokens,
                ok=False,
                detail=format_usage_detail(res, "; ".join(errors)),
            )
            raise RuntimeError("schema 校验失败: " + "; ".join(errors))

    spec["schema"] = merged
    if patch.get("title"):
        spec["title"] = patch["title"]
    written = emit_schema_to_workspace(workspace, spec)
    await record_call(
        db,
        project_id=project_id,
        stage="island_fill",
        tokens=res.tokens,
        ok=True,
        detail=format_usage_detail(res, f"{mode}," + ",".join(written)),
    )
    return written, mode


# ---------- Agent E：E-R 中文补全（只补展示名，不改 SQL/源码） ----------

