"""agents_match.py"""

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

async def run_upload_cluster_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    plan_id: str,
    profiles: list[Any],
) -> dict[str, Any] | None:
    """多材料聚类：discard + clusters[].files/reason。失败返回 None。"""
    if not (rt.stage_on("match_recommend") and rt.configured):
        return None
    if not await budget_ok(db, plan_id, rt):
        append_deepseek_log(plan_id, "upload_cluster skip · budget exceeded")
        return None

    lines: list[str] = []
    for p in profiles:
        fp = "、".join(getattr(p, "fingerprint", [])[:10])
        lines.append(
            f"[{p.index}] name={p.name} role={p.role} signal={p.signal} "
            f"title={p.title}\n"
            f"  fingerprint={fp or '（空）'}\n"
            f"  excerpt={(getattr(p, 'excerpt', '') or '')[:400]}"
        )
    blob = "\n".join(lines)
    messages = [
        {
            "role": "system",
            "content": (
                "你是毕设港上传分堆 Agent。只输出 JSON，禁止改写材料、禁止推荐领域。\n"
                "任务：把多份上传材料分成若干「同一毕设项目」簇，并剔除无关文件。\n"
                "规则：\n"
                "1) 开题/任务书/功能清单若同一课题（题目相近或清单能力是开题子集）→ 同簇；\n"
                "2) 不同课题 → 不同簇；同领域但功能清单差异大（如都图书，一套借阅罚金、一套二手交易）→ 拆开；\n"
                "3) 与本科毕设无关（简历、课程笔记、空文件等）→ discard；\n"
                "4) 每个文件索引必须恰好出现一次（在 discard 或某个 cluster.files）；\n"
                "5) 两份都像完整开题且题目明显不同 → 禁止同簇。\n"
                "字段：discard:number[]；clusters:[{files:number[], reason:string≤80}]；notes:string≤120。\n"
                "reason 只写归组依据（如「独立开题」「开题+清单同题」），禁止复述题目全文。\n"
            ),
        },
        {
            "role": "user",
            "content": f"共 {len(profiles)} 份材料（索引从 0）：\n\n{blob}",
        },
    ]
    res = await chat(rt, messages, json_mode=True, temperature=0.05, timeout=90.0)
    await record_call(
        db,
        project_id=plan_id,
        stage="upload_cluster",
        tokens=res.tokens,
        ok=res.ok and bool(res.data),
        detail=format_usage_detail(res, "上传分堆"),
    )
    append_deepseek_log(
        plan_id,
        f"upload_cluster ok={res.ok} {format_usage_detail(res)}",
    )
    if not res.ok or not isinstance(res.data, dict):
        return None
    return res.data


# ---------- Agent M：匹配推荐 ----------

async def run_match_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    raw_text: str,
    keyword: MatchResult,
) -> MatchResult:
    """在封闭目录内推荐 archetype/domain；失败回落关键词结果。"""
    if not (rt.stage_on("match_recommend") and rt.configured):
        return keyword
    if not await budget_ok(db, project_id, rt):
        append_deepseek_log(project_id, "match skip · budget exceeded")
        return keyword

    excerpt = (raw_text or "")[:7000]
    catalog = catalog_brief_for_match()
    messages = [
        {
            "role": "system",
            "content": (
                "你是毕设港 Match Agent。只输出 JSON。\n"
                "从目录选 archetype/domain（须为目录 ID）；可附 archetypes[]。\n"
                "以拟实现/主要功能为准；综述对比与否定句不当事。\n"
                "关键词初判已给路径并集；多路径请尽量都列出，最终以服务端并集+reconcile 为准。\n"
                "单路径时行业皮与行为一致（领用→FLOW、商城→TRADE、挂号/车位→RESERVE）。\n"
                "另给 slug：英文短标识，小写字母开头，可含数字下划线，3～24 字；"
                "抓题目功能差异，勿一律领域泛名（如 dorm_repair 而非一律 dorm）。\n"
                "字段：archetype, domain, archetypes, confidence, rationale(≤120字), slug, "
                "alts([{archetype,domain,confidence}]≤3)。\n"
            ),
        },
        {
            "role": "user",
            "content": (
                f"关键词初判：{keyword.archetype} × {keyword.domain} "
                f"（置信 {keyword.confidence}；路径并集 {', '.join(keyword.archetypes or [keyword.archetype])}）\n"
                f"命中词：{', '.join((keyword.hits or [])[:12])}\n\n"
                f"目录：\n{catalog}\n\n"
                f"开题摘录：\n{excerpt}"
            ),
        },
    ]
    res = await chat(rt, messages, json_mode=True, temperature=0.1, timeout=120.0)
    await record_call(
        db,
        project_id=project_id,
        stage="match_recommend",
        tokens=res.tokens,
        ok=res.ok and bool(res.data),
        detail=format_usage_detail(res, "匹配推荐"),
    )
    append_deepseek_log(
        project_id,
        f"match ok={res.ok} {format_usage_detail(res)}",
    )
    if not res.ok or not isinstance(res.data, dict):
        append_deepseek_log(project_id, "match fallback · keyword")
        return keyword
    merged = merge_llm_match(keyword, res.data)
    if not merged:
        append_deepseek_log(
            project_id,
            f"match invalid ids · fallback keyword · raw={str(res.data)[:200]}",
        )
        return keyword
    append_deepseek_log(
        project_id,
        f"match pick {merged.archetype}×{merged.domain} conf={merged.confidence} "
        f"(kw {keyword.archetype}×{keyword.domain})",
    )
    return merged


# ---------- Agent A：Spec ----------

async def run_spec_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    raw_text: str,
    spec: dict[str, Any],
) -> dict[str, Any]:
    """润色 proposal / 功能点摘要；不改 archetype/domain。"""
    if not (rt.stage_on("parse_spec") and rt.configured):
        return spec
    if not await budget_ok(db, project_id, rt):
        append_deepseek_log(project_id, "spec skip · budget exceeded")
        return spec

    domain = spec.get("domain") or ""
    title = spec.get("title") or ""
    excerpt = (raw_text or "")[:6000]
    messages = [
        {
            "role": "system",
            "content": (
                "你是毕设开题 Spec Agent。只输出 JSON。禁止改技术栈/造新表/改领域 ID。\n"
                "字段：title, background, feature_lines(≤8), out_scope_lines(≤5), summary；中文短句。\n"
                "feature←开题肯定要做；out_scope←开题明确否定；禁止臆造排除项。"
                "互斥与去重由服务端处理。\n"
            ),
        },
        {
            "role": "user",
            "content": (
                f"已匹配领域={domain}，当前标题={title}\n"
                f"开题摘录：\n{excerpt}"
            ),
        },
    ]
    res = await chat(rt, messages, json_mode=True, temperature=0.2)
    await record_call(
        db,
        project_id=project_id,
        stage="parse_spec",
        tokens=res.tokens,
        ok=res.ok and bool(res.data),
        detail=format_usage_detail(res, "摘要润色"),
    )
    append_deepseek_log(
        project_id,
        f"spec ok={res.ok} {format_usage_detail(res)}",
    )
    if not res.ok or not res.data:
        return spec

    data = res.data
    prop = dict(spec.get("proposal") or {})
    if data.get("title"):
        prop["title"] = str(data["title"])[:120]
        # 仅当标题明显更好时同步 spec.title（上传后未确认前可改）
        if not spec.get("title") or len(str(data["title"])) > 4:
            spec["title"] = str(data["title"])[:120]
    if data.get("background"):
        prop["background"] = str(data["background"])[:400]
    if data.get("summary"):
        prop["summary"] = str(data["summary"])[:400]
    if isinstance(data.get("feature_lines"), list):
        prop["feature_lines"] = [str(x)[:80] for x in data["feature_lines"][:8]]
    if isinstance(data.get("out_scope_lines"), list):
        prop["out_scope_lines"] = dedupe_out_scope_vs_features(
            prop.get("feature_lines"),
            data["out_scope_lines"],
            limit=5,
        )
    prop["llm_enriched"] = True
    spec["proposal"] = prop
    return spec

