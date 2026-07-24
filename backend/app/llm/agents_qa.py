"""agents_qa.py"""

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

def _read_clip(path: Path, limit: int = 1800) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")[:limit]

def _collect_qa_context(workspace: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """只采集上下文，不做领域词硬编码判定。"""
    schema = spec.get("schema") or {}
    files: dict[str, Any] = {}
    missing: list[str] = []
    for rel in _QA_FILES:
        path = workspace / rel
        if not path.exists():
            missing.append(rel)
            continue
        files[rel] = _read_clip(path)
    return {
        "domain": spec.get("domain"),
        "title": spec.get("title"),
        "accept": spec.get("accept"),
        "proposal": _proposal_text(spec)[:1500],
        "labels": schema.get("labels") or {},
        "seeds": schema.get("seeds") or {},
        "menus": schema.get("menus") or {},
        "entities": {
            k: {
                "label": (v or {}).get("label"),
                "labelPlural": (v or {}).get("labelPlural"),
                "verbs": (v or {}).get("verbs"),
                "states": (v or {}).get("states"),
            }
            for k, v in (schema.get("entities") or {}).items()
            if isinstance(v, dict)
        },
        "missing_files": missing,
        "files": files,
    }

def _fallback_qa(ctx: dict[str, Any]) -> dict[str, Any]:
    """无 Key / 关 QA 时的极简结构回退（不写死领域错词表）。"""
    findings: list[dict[str, str]] = []
    for rel in ctx.get("missing_files") or []:
        findings.append({"level": "warn", "msg": f"缺失文件 {rel}", "where": rel})
    labels = ctx.get("labels") or {}
    if not labels.get("noticePageTitle"):
        findings.append({"level": "warn", "msg": "labels.noticePageTitle 缺失", "where": "schema.labels"})
    if not labels.get("appName"):
        findings.append({"level": "warn", "msg": "labels.appName 缺失", "where": "schema.labels"})
    return {
        "summary": "未启用 LLM QA，仅做结构回退检查",
        "findings": findings,
        "ok": not any(f.get("level") == "error" for f in findings),
        "mode": "fallback",
    }

def _normalize_findings(raw: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(raw, list):
        return out
    for item in raw[:24]:
        if isinstance(item, str):
            out.append({"level": "warn", "msg": item[:200], "where": ""})
            continue
        if not isinstance(item, dict):
            continue
        level = str(item.get("level") or "warn").lower()
        if level not in ("error", "warn", "info"):
            level = "warn"
        out.append(
            {
                "level": level,
                "msg": str(item.get("msg") or item.get("message") or "")[:200],
                "where": str(item.get("where") or item.get("file") or "")[:120],
            }
        )
    return [f for f in out if f["msg"]]

async def run_qa_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    workspace: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    ctx = _collect_qa_context(workspace, spec)
    use_llm = rt.stage_on("qa_report") and rt.configured and await budget_ok(db, project_id, rt)

    if not use_llm:
        report = _fallback_qa(ctx)
        await record_call(
            db,
            project_id=project_id,
            stage="qa_report",
            tokens=0,
            ok=True,
            detail="回退：仅结构扫描（未调用大模型）",
        )
        write_qa_report(
            workspace, {**report, "domain": ctx.get("domain"), "title": ctx.get("title")}
        )
        return report

    payload = {
        "domain": ctx["domain"],
        "title": ctx["title"],
        "accept": ctx["accept"],
        "proposal": ctx["proposal"],
        "labels": ctx["labels"],
        "seeds": ctx["seeds"],
        "menus": ctx["menus"],
        "entities": ctx["entities"],
        "missing_files": ctx["missing_files"],
        "file_excerpts": ctx["files"],
    }
    messages = [
        {
            "role": "system",
            "content": (
                "你是毕设交付 QA Agent（Drift/Consistency）。根据领域与摘录审查文案/菜单/种子是否一致，"
                "找出跨领域错词、写死文案、空壳、占位符、菜单与实体不符等问题。"
                "禁止改代码；只输出 JSON：\n"
                '{"ok":boolean,"summary":string,'
                '"findings":[{"level":"error|warn|info","msg":string,"where":string}],'
                '"priorities":string[]}\n'
                "level=error 仅用于会误导答辩/明显错域的问题；其余用 warn/info。"
                "where 填文件路径或 schema 字段名。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False),
        },
    ]
    res = await chat(rt, messages, json_mode=True, temperature=0.25, timeout=120.0)
    append_deepseek_log(project_id, f"qa ok={res.ok} {format_usage_detail(res)}")

    if not res.ok or not res.data:
        report = _fallback_qa(ctx)
        report["summary"] = f"LLM QA 失败，回退结构检查 · {res.error or 'no json'}"
        report["mode"] = "fallback_after_llm_error"
        await record_call(
            db,
            project_id=project_id,
            stage="qa_report",
            tokens=res.tokens,
            ok=False,
            detail=format_usage_detail(res, "质量摘要：大模型失败"),
        )
        write_qa_report(
            workspace, {**report, "domain": ctx.get("domain"), "title": ctx.get("title")}
        )
        return report

    data = res.data
    findings = _normalize_findings(data.get("findings"))
    for p in data.get("priorities") or []:
        findings.append({"level": "info", "msg": str(p)[:200], "where": "priority"})
    for rel in ctx.get("missing_files") or []:
        if not any(rel in (f.get("where") or "") or rel in f.get("msg", "") for f in findings):
            findings.append({"level": "warn", "msg": f"缺失文件 {rel}", "where": rel})

    ok = data.get("ok")
    if not isinstance(ok, bool):
        ok = not any(f.get("level") == "error" for f in findings)
    summary = str(data.get("summary") or "").strip() or (
        f"LLM QA 完成 · {len(findings)} 条发现" if findings else "LLM QA 未发现明显问题"
    )
    report = {
        "domain": ctx.get("domain"),
        "title": ctx.get("title"),
        "summary": summary[:800],
        "findings": findings,
        "ok": ok,
        "mode": "llm",
    }
    await record_call(
        db,
        project_id=project_id,
        stage="qa_report",
        tokens=res.tokens,
        ok=True,
        detail=format_usage_detail(res, summary[:400]),
    )
    write_qa_report(workspace, report)
    return report

