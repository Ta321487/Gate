"""agents_labels.py"""

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

async def run_er_label_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    workspace: Path,
    spec: dict[str, Any] | None = None,
    llm_enabled: bool = True,
) -> dict[str, Any]:
    """扫描 E-R 展示名漏网英文，调 LLM 补中文；写入 islands/er_labels.json。"""
    fresh = build_schema_model(workspace, with_er_patch=False)
    if not fresh:
        return {"mode": "skip", "gaps": 0, "filled": 0, "detail": "no schema"}

    gaps = collect_english_gaps(fresh)
    n_gaps = count_er_gaps(gaps)
    if n_gaps == 0:
        save_er_label_patch(workspace, {"mode": "clean", "tables": {}, "columns": {}, "relations": {}})
        await record_call(
            db, project_id=project_id, stage="er_labels", tokens=0, ok=True, detail="无需补全 · 无英文缺口"
        )
        return {"mode": "clean", "gaps": 0, "filled": 0}

    use_llm = bool(llm_enabled and rt.stage_on("er_labels") and rt.configured)
    if use_llm and not await budget_ok(db, project_id, rt):
        use_llm = False
        append_deepseek_log(project_id, "er_labels skip llm · budget exceeded")

    def remain_after(patch: dict | None) -> int:
        return count_er_gaps(collect_english_gaps(apply_er_label_patch(dict(fresh), patch)))

    if not use_llm:
        existing = load_er_label_patch(workspace)
        remain = remain_after(existing)
        mode = "deterministic_only"
        await record_call(
            db,
            project_id=project_id,
            stage="er_labels",
            tokens=0,
            ok=True,
            detail=f"仅确定性 · 缺口={n_gaps} · 剩余={remain}",
        )
        append_deepseek_log(project_id, f"er_labels {mode} gaps={n_gaps} remain={remain}")
        return {"mode": mode, "gaps": n_gaps, "filled": 0, "remain": remain}

    title = ""
    domain = ""
    if isinstance(spec, dict):
        title = str(spec.get("title") or "")
        domain = str(spec.get("domain") or "")
        schema = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
        labels = schema.get("labels") if isinstance(schema.get("labels"), dict) else {}
        if not title:
            title = str(labels.get("appName") or "")

    messages = [
        {
            "role": "system",
            "content": (
                "你是毕设港 ER Label Agent。只输出 JSON：\n"
                '{"tables":{"表名":"中文实体名"},'
                '"columns":{"表名":{"列名":"中文属性名"}},'
                '"relations":{"联系名":"中文联系名"}}\n'
                "规则：只翻译 gaps 里列出的项；纯中文短名（实体≤8字、属性≤8字、联系≤6字）；"
                "联系名必须是动词或动宾（发布/指派/属于/接收…），禁止用实体名（用户/分类/公告）；"
                "禁止拼音/英文/代码；贴合领域语义；不要发明 gaps 以外的键。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {"domain": domain, "title": title, "gaps": gaps},
                ensure_ascii=False,
            ),
        },
    ]
    res = await chat(rt, messages, json_mode=True, temperature=0.2)
    append_deepseek_log(project_id, f"er_labels ok={res.ok} {format_usage_detail(res)}")

    if res.ok and isinstance(res.data, dict):
        patch = {**sanitize_er_label_patch(res.data, gaps), "mode": "llm"}
    else:
        old = sanitize_er_label_patch(load_er_label_patch(workspace), gaps)
        patch = {
            **old,
            "mode": "llm_failed_keep_old" if count_er_patch_fills(old) else "llm_failed",
        }

    save_er_label_patch(workspace, patch)
    filled = count_er_patch_fills(patch)
    remain = remain_after(patch)
    await record_call(
        db,
        project_id=project_id,
        stage="er_labels",
        tokens=res.tokens,
        ok=bool(res.ok),
        detail=format_usage_detail(
            res, f"{patch.get('mode')} · 缺口={n_gaps} · 已填={filled} · 剩余={remain}"
        ),
    )
    return {"mode": patch.get("mode"), "gaps": n_gaps, "filled": filled, "remain": remain}


# ---------- Agent E2：功能模块图中文补全（只改展示名，不增删模块） ----------

async def run_module_label_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    workspace: Path,
    spec: dict[str, Any] | None = None,
    proposal_text: str = "",
    llm_enabled: bool = True,
) -> dict[str, Any]:
    """扫描模块图漏网英文名，结合开题片段补中文；写入 islands/module_labels.json。"""
    # 两种布局的节点 id 不同，都扫一遍缺口
    fresh_biz = build_module_model(
        workspace, with_label_patch=False, proposal_text=proposal_text or "", layout="biz"
    )
    fresh_side = build_module_model(
        workspace, with_label_patch=False, proposal_text=proposal_text or "", layout="side"
    )
    fresh = fresh_biz or fresh_side
    if not fresh:
        return {"mode": "skip", "gaps": 0, "filled": 0, "detail": "no schema"}

    # 开题辅助：即使无英文缺口，也允许 LLM 按材料微调已有节点称呼（仅 gaps 为空时用全量节点作候选）
    gaps_by_id: dict[str, dict[str, str]] = {}
    for m in (fresh_biz, fresh_side):
        if not m:
            continue
        for g in collect_module_label_gaps(m):
            gid = str(g.get("id") or "")
            if gid and gid not in gaps_by_id:
                gaps_by_id[gid] = g
    gaps = list(gaps_by_id.values())
    n_gaps = len(gaps)
    use_llm = bool(llm_enabled and rt.stage_on("module_labels") and rt.configured)
    if use_llm and not await budget_ok(db, project_id, rt):
        use_llm = False
        append_deepseek_log(project_id, "module_labels skip llm · budget exceeded")

    if not use_llm:
        save_module_label_patch(
            workspace,
            {**sanitize_module_label_patch(load_module_label_patch(workspace)), "mode": "deterministic"},
        )
        await record_call(
            db,
            project_id=project_id,
            stage="module_labels",
            tokens=0,
            ok=True,
            detail=f"确定性 · 拉丁缺口={n_gaps}",
        )
        return {"mode": "deterministic", "gaps": n_gaps, "filled": 0}

    title = ""
    domain = ""
    if isinstance(spec, dict):
        title = str(spec.get("title") or "")
        domain = str(spec.get("domain") or "")

    def _flat(n: dict, acc: list) -> None:
        acc.append({"id": n.get("id"), "label": n.get("label"), "source": n.get("source")})
        for c in n.get("children") or []:
            if isinstance(c, dict):
                _flat(c, acc)

    flat: list[dict] = []
    for m in (fresh_biz, fresh_side):
        if isinstance(m, dict) and isinstance(m.get("root"), dict):
            _flat(m["root"], flat)
    # 按 id 去重，优先保留先出现的（biz）
    seen_flat: set[str] = set()
    flat_dedup: list[dict] = []
    for row in flat:
        rid = str(row.get("id") or "")
        if not rid or rid in seen_flat:
            continue
        seen_flat.add(rid)
        flat_dedup.append(row)
    flat = flat_dedup

    # 有英文缺口只翻缺口；否则允许按开题微调一级分支称呼
    if n_gaps:
        target = gaps
        scope = "gaps_only"
    else:
        target = [x for x in flat if str(x.get("source") or "") in ("branch", "system")]
        scope = "branch_refine"
        if not target:
            save_module_label_patch(workspace, {"mode": "clean", "nodes": {}})
            await record_call(
                db, project_id=project_id, stage="module_labels", tokens=0, ok=True, detail="无需补全"
            )
            return {"mode": "clean", "gaps": 0, "filled": 0}

    excerpt = (proposal_text or "")[:2400]
    messages = [
        {
            "role": "system",
            "content": (
                "你是毕设港 Module Label Agent。只输出 JSON：\n"
                '{"nodes":{"节点id":"中文模块名"}}\n'
                "规则：只翻译/微调 target 列出的 id；纯中文短名（≤10字）；"
                "必须贴合开题材料用语，但禁止发明 target 以外的模块；"
                "禁止拼音/英文/代码。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "domain": domain,
                    "title": title,
                    "scope": scope,
                    "target": target,
                    "proposal_excerpt": excerpt,
                },
                ensure_ascii=False,
            ),
        },
    ]
    res = await chat(rt, messages, json_mode=True, temperature=0.2)
    append_deepseek_log(project_id, f"module_labels ok={res.ok} {format_usage_detail(res)}")

    allowed_ids = {str(t.get("id") or "") for t in target}
    gap_like = [{"id": i, "label": "", "source": ""} for i in allowed_ids if i]
    if res.ok and isinstance(res.data, dict):
        patch = {**sanitize_module_label_patch(res.data, gap_like), "mode": "llm"}
    else:
        old = sanitize_module_label_patch(load_module_label_patch(workspace), gap_like)
        patch = {
            **old,
            "mode": "llm_failed_keep_old" if old.get("nodes") else "llm_failed",
        }

    save_module_label_patch(workspace, patch)
    filled = len(patch.get("nodes") or {})
    await record_call(
        db,
        project_id=project_id,
        stage="module_labels",
        tokens=res.tokens,
        ok=bool(res.ok),
        detail=format_usage_detail(res, f"{patch.get('mode')} · 已填={filled} · 范围={scope}"),
    )
    return {"mode": patch.get("mode"), "gaps": n_gaps, "filled": filled, "scope": scope}


# ---------- Agent E3：测试用例文案润色（只改已有行的前置/步骤/输入/预期，不增删用例） ----------

async def run_testcase_label_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    workspace: Path,
    spec: dict[str, Any] | None = None,
    proposal_text: str = "",
    llm_enabled: bool = True,
) -> dict[str, Any]:
    """确定性骨架已由 menus 生成；LLM 仅润色文案列，写入 islands/testcase_labels.json。"""
    skeleton_model = build_testcase_skeleton(workspace)
    if not skeleton_model:
        return {"mode": "skip", "rows": 0, "filled": 0, "detail": "no schema"}

    rows = skeleton_model.get("skeleton") or []
    n_rows = len(rows)
    allowed = {str(r.get("id") or "") for r in rows if r.get("id")}
    use_llm = bool(llm_enabled and rt.stage_on("testcase_labels") and rt.configured)
    if use_llm and not await budget_ok(db, project_id, rt):
        use_llm = False
        append_deepseek_log(project_id, "testcase_labels skip llm · budget exceeded")

    if not use_llm or n_rows == 0:
        save_testcase_label_patch(
            workspace,
            {
                **sanitize_testcase_label_patch(load_testcase_label_patch(workspace), allowed),
                "mode": "deterministic",
            },
        )
        await record_call(
            db,
            project_id=project_id,
            stage="testcase_labels",
            tokens=0,
            ok=True,
            detail=f"确定性 · 行数={n_rows}",
        )
        return {"mode": "deterministic", "rows": n_rows, "filled": 0}

    title = ""
    domain = ""
    if isinstance(spec, dict):
        title = str(spec.get("title") or "")
        domain = str(spec.get("domain") or "")

    # 控制 token：只送 id/module/item/key/side + 当前文案
    target = [
        {
            "id": r.get("id"),
            "module": r.get("module"),
            "item": r.get("item"),
            "key": r.get("key"),
            "side": r.get("side"),
            "precondition": r.get("precondition"),
            "steps": r.get("steps"),
            "input": r.get("input"),
            "expected": r.get("expected"),
        }
        for r in rows
    ]
    excerpt = (proposal_text or "")[:1800]
    messages = [
        {
            "role": "system",
            "content": (
                "你是毕设港 Testcase Label Agent。只输出 JSON：\n"
                '{"cases":{"TC-XXX-001":{"precondition":"...","steps":"...","input":"...","expected":"..."}}}\n'
                "硬约束：\n"
                "1) 只能改 target 里已有的 id；禁止新增/删除用例；禁止改 id/module/item；\n"
                "2) 文案必须描述该菜单已实现操作，贴合开题用语但禁止发明未实现功能；\n"
                "3) steps 用①②③…；中文为主；input 可含 username=admin 这类演示数据；\n"
                "4) 不要写 actual/verdict；不要输出 target 以外的键。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "domain": domain,
                    "title": title,
                    "target": target,
                    "proposal_excerpt": excerpt,
                },
                ensure_ascii=False,
            ),
        },
    ]
    res = await chat(rt, messages, json_mode=True, temperature=0.2)
    append_deepseek_log(project_id, f"testcase_labels ok={res.ok} {format_usage_detail(res)}")

    if res.ok and isinstance(res.data, dict):
        patch = {**sanitize_testcase_label_patch(res.data, allowed), "mode": "llm"}
    else:
        old = sanitize_testcase_label_patch(load_testcase_label_patch(workspace), allowed)
        patch = {
            **old,
            "mode": "llm_failed_keep_old" if old.get("cases") else "llm_failed",
        }

    save_testcase_label_patch(workspace, patch)
    filled = len(patch.get("cases") or {})
    await record_call(
        db,
        project_id=project_id,
        stage="testcase_labels",
        tokens=res.tokens,
        ok=bool(res.ok),
        detail=format_usage_detail(res, f"{patch.get('mode')} · 行数={n_rows} · 已填={filled}"),
    )
    return {"mode": patch.get("mode"), "rows": n_rows, "filled": filled}


# ---------- Agent C：构建修复（诊断 + 重放填岛，不改 Java/Vue） ----------

