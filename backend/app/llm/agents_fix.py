"""agents_fix.py"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable

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

# mvn/javac：[ERROR] path/File.java:[行,列] 文案  或  File.java:行:列: 文案
_JAVAC_LOCUS_RE = re.compile(
    r"(?P<file>[\w./\\-]+\.java)(?::\[(?P<line1>\d+),(?P<col1>\d+)\]|:(?P<line2>\d+):(?P<col2>\d+):?)"
    r"\s*(?P<msg>[^\r\n]+)?",
)


def parse_javac_error_loci(log: str, *, limit: int = 8) -> list[tuple[str, int, int, str]]:
    """从 mvn compile 日志稳定抽出 (文件, 行, 列, 文案) ，供失败回灌与截断优先保留。"""
    out: list[tuple[str, int, int, str]] = []
    seen: set[tuple[str, int, int]] = set()
    for m in _JAVAC_LOCUS_RE.finditer(log or ""):
        line_s = m.group("line1") or m.group("line2") or "0"
        col_s = m.group("col1") or m.group("col2") or "0"
        try:
            line, col = int(line_s), int(col_s)
        except ValueError:
            continue
        raw_file = (m.group("file") or "").replace("\\", "/")
        file_name = raw_file.rsplit("/", 1)[-1]
        key = (file_name, line, col)
        if key in seen:
            continue
        seen.add(key)
        msg = (m.group("msg") or "").strip()
        # 去掉 maven 前缀噪音
        if msg.startswith("[ERROR]"):
            msg = msg[len("[ERROR]") :].strip()
        out.append((file_name, line, col, msg))
        if len(out) >= limit:
            break
    return out


def format_compile_fail_meta(log: str, *, head: int = 500) -> str:
    """编译失败对外短句：先放文件:行:列+文案，再跟截断原文，避免只剩尾巴。"""
    loci = parse_javac_error_loci(log)
    if loci:
        bullets = "；".join(f"{f}:{ln}:{col} {msg}" for f, ln, col, msg in loci[:5])
        return f"编译失败 · {bullets}"
    raw = (log or "").strip()
    return f"编译失败 · {raw[:head]}" if raw else "编译失败"

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
            encoding="utf-8",
            errors="replace",
            timeout=180,
            shell=use_shell,
        )
        out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
        if p.returncode == 0:
            return True, (out[-800:] if out else "compile ok")
        # 失败日志：三元组置顶，再跟原文尾部，避免截断丢掉报错行
        loci = parse_javac_error_loci(out)
        if loci:
            head = "\n".join(f"{f}:{ln}:{col} {msg}" for f, ln, col, msg in loci)
            tail = out[-2000:] if out else ""
            return False, f"{head}\n{tail}".strip()
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
    on_status: Callable[[str], Awaitable[None]] | None = None,
) -> tuple[bool, str]:
    """
    结构校验后尝试 mvn compile；编译失败硬拦交付（ok=False）。
    开了 auto_fix 时：LLM 诊断 + 重放确定性/LLM 填岛（不改业务源码）后重编；仍失败则 ok=False。
    本机未装 mvn 时跳过编译（无法验），不挡交付。
    on_status：可选，用于工厂页步骤文案（如「正在编译后端…」）；勿传内部日志。
    返回 (ok, meta)。
    """
    async def _status(msg: str) -> None:
        if on_status is None:
            return
        try:
            await on_status(msg)
        except Exception:  # noqa: BLE001
            pass

    ok_be = (workspace / "backend").exists()
    ok_fe = (workspace / "frontend").exists()
    if not (ok_be and ok_fe):
        return False, "骨架不完整"

    await _status("正在编译后端，大约需要 1～3 分钟…")
    # mvn compile 可长达数分钟，必须进线程，否则工厂 API 整体假死
    compile_ok, log = await asyncio.to_thread(_mvn_compile, workspace)
    if not (rt.stage_on("auto_fix") and rt.configured):
        if compile_ok:
            return True, "结构校验通过 · 已预编译" if "skip" not in log else "结构校验通过 · " + log
        return False, format_compile_fail_meta(log)

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
        await _status(f"编译未过，正在尝试自动修复（第 {i + 1} 轮）…")
        loci = parse_javac_error_loci(last or "")
        loci_block = (
            "\n".join(f"- {f}:{ln}:{col} {msg}" for f, ln, col, msg in loci)
            if loci
            else "（未能解析出文件:行:列）"
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 Build Fix Agent。错误码保持 BUILD_COMPILE；工厂禁止改业务 Java/Vue。"
                    "只输出 JSON：{\"diagnosis\":string,\"suggest_schema_tweak\":boolean,\"note\":string}。"
                    "诊断须点名日志里的文件:行:列与原文错误；"
                    "若文案含「不是语句」，常见成因是裁剪残留（if(cond) null; / if(false)else 体被误删），"
                    "应建议查 pack_prune 类型剥离，而不是改学生包。"
                    "若像环境/依赖问题，suggest_schema_tweak=false。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"第{i+1}轮编译失败（BUILD_COMPILE）。\n"
                    f"解析出的报错点：\n{loci_block}\n\n"
                    f"日志原文：\n{(last or '')[:3000]}"
                ),
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
        await _status(f"正在重新编译（第 {i + 1} 轮）…")
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

    fail_meta = format_compile_fail_meta(last or "")
    await record_call(
        db,
        project_id=project_id,
        stage="auto_fix",
        tokens=total_tokens,
        ok=False,
        detail=fail_meta[:500],
    )
    return False, fail_meta

