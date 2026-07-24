"""agents_fix.py"""

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

def _mvn_compile(workspace: Path) -> tuple[bool, str]:
    be = workspace / "backend"
    if not be.exists():
        return False, "无 backend 目录"
    mvn = _resolve_cmd("mvn")
    if not mvn:
        return True, "skip · 未检测到 mvn"
    try:
        if sys.platform == "win32":
            from subprocess import list2cmdline

            args: str | list[str] = list2cmdline([mvn, "-q", "-DskipTests", "compile"])
            use_shell = True
        else:
            args = [mvn, "-q", "-DskipTests", "compile"]
            use_shell = False
        p = subprocess.run(
            args,
            cwd=str(be),
            capture_output=True,
            text=True,
            timeout=180,
            shell=use_shell,
        )
        out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
        if p.returncode == 0:
            return True, (out[-800:] if out else "compile ok")
        return False, out[-2500:] or f"exit {p.returncode}"
    except subprocess.TimeoutExpired:
        return False, "mvn compile timeout 180s"
    except Exception as e:  # noqa: BLE001
        return False, str(e)

async def run_fix_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    workspace: Path,
    spec: dict[str, Any],
) -> tuple[bool, str]:
    """
    结构校验后尝试 mvn compile；失败则 LLM 诊断 + 重放确定性/LLM 填岛（不改业务源码）。
    返回 (ok, meta)。
    """
    ok_be = (workspace / "backend").exists()
    ok_fe = (workspace / "frontend").exists()
    if not (ok_be and ok_fe):
        return False, "骨架不完整"

    # mvn compile 可长达数分钟，必须进线程，否则工厂 API 整体假死
    # 未开自动修复时仍预编译暖 target（失败不挡交付，与原先跳过同口径）
    compile_ok, log = await asyncio.to_thread(_mvn_compile, workspace)
    if not (rt.stage_on("auto_fix") and rt.configured):
        if compile_ok:
            return True, "结构校验通过 · 已预编译" if "skip" not in log else "结构校验通过 · " + log
        return True, "结构校验通过 · 未开自动修复"

    if compile_ok:
        await record_call(
            db,
            project_id=project_id,
            stage="auto_fix",
            tokens=0,
            ok=True,
            detail="编译通过 / 已跳过",
        )
        return True, "结构+编译通过" if "skip" not in log else "结构校验通过 · " + log

    rounds = max(0, int(rt.fix_rounds_max))
    last = log
    total_tokens = 0
    for i in range(rounds):
        if not await budget_ok(db, project_id, rt):
            break
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 Build Fix Agent。工厂禁止改业务 Java/Vue。"
                    "只输出 JSON：{\"diagnosis\":string,\"suggest_schema_tweak\":boolean,\"note\":string}。"
                    "说明失败原因；若像环境/依赖问题，suggest_schema_tweak=false。"
                ),
            },
            {
                "role": "user",
                "content": f"第{i+1}轮编译失败日志：\n{last[:3500]}",
            },
        ]
        res = await chat(rt, messages, json_mode=True, temperature=0.1)
        total_tokens += res.tokens
        append_deepseek_log(
            project_id,
            f"fix#{i+1} ok={res.ok} {format_usage_detail(res)}",
        )
        # 仅重放交付配置，不写业务源码
        try:
            await asyncio.to_thread(emit_schema_to_workspace, workspace, spec)
        except Exception:  # noqa: BLE001
            await asyncio.to_thread(llm_fill_islands, workspace, spec, True)
        compile_ok, last = await asyncio.to_thread(_mvn_compile, workspace)
        if compile_ok:
            await record_call(
                db,
                project_id=project_id,
                stage="auto_fix",
                tokens=total_tokens,
                ok=True,
                detail=f"修复成功 · 共 {i+1} 轮",
            )
            return True, f"编译修复成功 · {i+1} 轮"

    await record_call(
        db,
        project_id=project_id,
        stage="auto_fix",
        tokens=total_tokens,
        ok=False,
        detail=(last or "编译失败")[:500],
    )
    # 编译失败不阻断交付（本机缺 JDK/依赖常见）；记警告继续门禁
    return True, f"编译未过已记录 · 继续门禁 · {(last or '')[:120]}"

