"""窄 Agent：匹配推荐 / Spec 润色 / 填岛 / E-R 中文补全 / 模块图命名 / 测试用例文案 / 修复 / 质检；不生成业务 Java/Vue。"""

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
from app.llm.client import (
    append_deepseek_log,
    budget_ok,
    chat,
    format_usage_detail,
    monthly_tokens_used,
    record_call,
    write_qa_report,
)
from app.llm.runtime import LlmRuntime
from app.services.runtime import _resolve_cmd

# 填岛允许 LLM 改写的 labels 键（页面文案）
_LABEL_KEYS = (
    "appName",
    "authEyebrow",
    "authLead",
    "authPoints",
    "registerRoleHint",
    "noticePageTitle",
    "noticePageLead",
)
_SEED_KEYS = ("noticeTitle", "noticeBody")

_ROLE_LABEL_SLOTS = ("user", "admin", "subadmin")

_QA_FILES = (
    "frontend/src/appDelivered.js",
    "frontend/src/views/Notices.vue",
    "frontend/src/views/NoticeDetail.vue",
    "frontend/src/views/user/MyTickets.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "islands/island_ui_hints.json",
    "islands/island_notice_seed.json",
)

_SAMPLE_PROPOSAL_PID = "gf-sample"


def _proposal_text(spec: dict[str, Any]) -> str:
    prop = spec.get("proposal")
    if isinstance(prop, dict):
        parts = [
            prop.get("title"),
            prop.get("background"),
            "\n".join(prop.get("feature_lines") or []),
            "\n".join(prop.get("out_scope_lines") or []),
            prop.get("excerpt"),
        ]
        return "\n".join(str(x) for x in parts if x)
    return str(prop or "")

