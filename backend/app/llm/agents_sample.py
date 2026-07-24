"""agents_sample.py"""

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

async def run_sample_proposal_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    draft_text: str,
    title: str,
    anchor_domain: str,
) -> tuple[str, bool]:
    """润色测试开题全文。返回 (text, used_llm)。无 Key / 失败则回退草稿。"""
    if not rt.configured:
        return draft_text, False
    # 仅受月度预算约束；合成 ID gf-sample，避免挤占真实项目额度统计观感
    monthly = await monthly_tokens_used(db)
    if monthly >= rt.monthly_token_budget:
        append_deepseek_log(_SAMPLE_PROPOSAL_PID, "sample_proposal skip · monthly budget")
        return draft_text, False

    messages = [
        {
            "role": "system",
            "content": (
                "你是本科毕设开题报告润色助手。输出完整开题正文（纯文本，保留原有九段标题结构），"
                "不要 Markdown 代码围栏，不要 JSON。\n"
                "要求：正式开题腔；可改写措辞与细节使读感像新写；"
                "保持 Spring Boot + Vue + MySQL 与原稿主业务路径。"
                "原稿写在「不纳入本期 / 背景对比」里的扩展能力，润色后仍放在范围外，不要强行塞进拟实现。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"锚域提示={anchor_domain}（仅供理解场景，不要输出领域 ID）\n"
                f"题目={title}\n\n"
                f"待润色开题草稿：\n{draft_text[:12000]}"
            ),
        },
    ]
    res = await chat(rt, messages, json_mode=False, temperature=0.55, timeout=120.0)
    await record_call(
        db,
        project_id=_SAMPLE_PROPOSAL_PID,
        stage="sample_proposal",
        tokens=res.tokens,
        ok=res.ok and bool((res.text or "").strip()),
        detail=format_usage_detail(res, "样例开题"),
    )
    append_deepseek_log(
        _SAMPLE_PROPOSAL_PID,
        f"sample_proposal ok={res.ok} {format_usage_detail(res)}",
    )
    text = (res.text or "").strip()
    if not res.ok or len(text) < 200:
        return draft_text, False
    # 去掉偶发代码围栏
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("text"):
            text = text[4:].lstrip()
        elif text.lower().startswith("markdown"):
            text = text[8:].lstrip()
    return text, True

