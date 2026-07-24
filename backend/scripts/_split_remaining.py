# -*- coding: utf-8 -*-
"""Split proposal_packs / themes.css / er_labels / agents / engine / system."""
from __future__ import annotations

import ast
import json
import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def split_proposal_packs() -> None:
    path = ROOT / "app" / "bake" / "proposal_packs.py"
    text = path.read_text(encoding="utf-8")
    if "proposal_packs_data" in text and "PACKS: list" in text and "json.loads" in text:
        print("proposal_packs already split")
        return
    # Evaluate PACKS via ast of the list literal
    m = re.search(r"^PACKS: list\[dict\[str, Any\]\] = (\[[\s\S]*\])\s*$", text, re.M)
    if not m:
        # fallback: exec only the list
        ns: dict = {}
        exec(text.replace("from __future__ import annotations\n", "")
             .replace("from typing import Any\n\n", ""), ns)
        packs = ns["PACKS"]
    else:
        packs = ast.literal_eval(m.group(1))

    out = ROOT / "app" / "bake" / "proposal_packs_data"
    out.mkdir(parents=True, exist_ok=True)
    for p in packs:
        pid = p["id"]
        (out / f"{pid}.json").write_text(
            json.dumps(p, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("pack", pid)
    path.write_text(
        '''"""常见本科/专科 Web 毕设选题包（覆盖优先，不完全等于 DOMAINS 原文）。

正文在 proposal_packs_data/*.json。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DIR = Path(__file__).resolve().parent / "proposal_packs_data"

PACKS: list[dict[str, Any]] = [
    json.loads(p.read_text(encoding="utf-8"))
    for p in sorted(_DIR.glob("*.json"), key=lambda x: x.stem)
]
''',
        encoding="utf-8",
    )
    print("proposal_packs", len(packs))


def split_themes_css() -> None:
    css_path = REPO / "skeletons" / "baseline" / "frontend" / "src" / "styles" / "themes.css"
    text = css_path.read_text(encoding="utf-8")
    if '@import "./themes/' in text:
        print("themes.css already split")
        return
    out_dir = css_path.parent / "themes"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Keep shared preamble (root + dark shared) separate
    # Split remaining into family files by first token of data-theme="family-*"
    header_end = text.find('[data-theme="lib-grove"]')
    if header_end < 0:
        raise SystemExit("themes header marker not found")
    shared = text[:header_end].rstrip() + "\n"

    rest = text[header_end:]
    # Split on comment headers like /* —— ... —— */ or on [data-theme="prefix-
    # Group by theme family prefix (lib, shop, dorm, ...)
    blocks: dict[str, list[str]] = {}
    # Find all top-level theme rule starts
    parts = re.split(r"(?=\n(?:/\* ——[^*]+—— \*/\n)?\[data-theme=\")", "\n" + rest)
    for part in parts:
        part = part.strip("\n")
        if not part.strip():
            continue
        m = re.search(r'\[data-theme="([a-z0-9]+)-', part)
        if not m:
            # orphan (shared dark already in header)
            fam = "_misc"
        else:
            fam = m.group(1)
        blocks.setdefault(fam, []).append(part.rstrip() + "\n")

    imports: list[str] = []
    # Preserve approximate original order via first appearance
    order: list[str] = []
    for fam in blocks:
        if fam not in order:
            order.append(fam)

    for fam in order:
        body = "\n".join(blocks[fam]).rstrip() + "\n"
        fname = f"{fam}.css"
        (out_dir / fname).write_text(body, encoding="utf-8")
        imports.append(f'@import "./themes/{fname}";')
        print("theme family", fam, "lines", len(body.splitlines()))

    css_path.write_text(
        shared.rstrip()
        + "\n\n"
        + "\n".join(imports)
        + "\n",
        encoding="utf-8",
    )
    print("themes.css imports", len(imports))


def split_er_labels() -> None:
    src = ROOT / "app" / "bake" / "schema" / "er_labels.py"
    text = src.read_text(encoding="utf-8")
    if (ROOT / "app" / "bake" / "schema" / "er_zh.py").exists() and "from app.bake.schema.er_zh" in text:
        print("er_labels already split")
        return

    # Extract dict section through _COL_SUFFIX_RULES ending
    m = re.search(
        r"(# —— 中文：[\s\S]*?_COL_SUFFIX_RULES: tuple\[tuple\[str, str, str\], \.\.\.\] = \([\s\S]*?\n\))\n",
        text,
    )
    if not m:
        raise SystemExit("er_zh block not found")
    zh_body = m.group(1)
    rest = text[m.end() :]

    zh_mod = (
        '"""E-R 中文词表（表名/列名/后缀规则）。"""\n\n'
        "from __future__ import annotations\n\n"
        + zh_body
        + "\n"
    )
    # Fix: zh_body starts with comment that assumed Path/re already imported in original
    # Original had Path, re, json imports before dicts — er_zh only needs nothing for dicts
    (ROOT / "app" / "bake" / "schema" / "er_zh.py").write_text(zh_mod, encoding="utf-8")

    # Split rest by function groups using line markers
    # roles: expand_user_role_entities and helpers before it from _camel through expand
    # Actually keep logic in er_labels.py but import zh from er_zh — simplest valuable split
    new_head = '''"""E-R 中文标签、角色展开与 LLM 补丁。

词表见 er_zh；本模块保留拼装与补丁逻辑。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.bake.schema.er_zh import (  # noqa: F401
    _COL_SUFFIX_RULES,
    _COMMON_COL_ZH,
    _INFRA_TABLE_ZH,
    _STEM_ZH,
    _TABLE_PART_ZH,
)

'''
    # rest still has _LATIN_RE and _ER_LABELS_REL which were after dicts
    # Check if rest starts with those
    src.write_text(new_head + rest.lstrip(), encoding="utf-8")
    print("er_labels + er_zh", len(zh_body.splitlines()), "zh lines")


def _extract_funcs(text: str, names: list[str]) -> tuple[str, str]:
    """Return (extracted_chunk, remaining_text) for top-level defs in names (in order found)."""
    matches = list(re.finditer(r"^(async )?def (\w+)\(", text, re.M))
    by_name = {m.group(2): (m.start(), i) for i, m in enumerate(matches)}
    chunks: list[str] = []
    ranges: list[tuple[int, int]] = []
    for name in names:
        if name not in by_name:
            raise SystemExit(f"missing func {name}")
        start, idx = by_name[name]
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        # include preceding blank lines / comments tied to def — keep from start
        chunks.append(text[start:end].rstrip() + "\n\n")
        ranges.append((start, end))
    # remove from original (high to low)
    remaining = text
    for start, end in sorted(ranges, reverse=True):
        remaining = remaining[:start] + remaining[end:]
    return "".join(chunks), remaining


def split_agents() -> None:
    src = ROOT / "app" / "llm" / "agents.py"
    text = src.read_text(encoding="utf-8")
    if (ROOT / "app" / "llm" / "agents_match.py").exists():
        print("agents already split")
        return

    # Keep shared constants + helpers in agents_common, then concern modules
    # Simpler approach: cut by function groups into files that import from each other carefully.

    header_end = text.find("def _proposal_text")
    header = text[:header_end]

    groups = {
        "agents_common.py": [
            "_proposal_text",
        ],
        "agents_match.py": [
            "run_upload_cluster_agent",
            "run_match_agent",
            "run_spec_agent",
        ],
        "agents_island.py": [
            "_sanitize_island_roles",
            "_sanitize_island_patch",
            "run_island_agent",
        ],
        "agents_labels.py": [
            "run_er_label_agent",
            "run_module_label_agent",
            "run_testcase_label_agent",
        ],
        "agents_fix.py": [
            "_mvn_compile",
            "run_fix_agent",
        ],
        "agents_qa.py": [
            "_read_clip",
            "_collect_qa_context",
            "_fallback_qa",
            "_normalize_findings",
            "run_qa_agent",
        ],
        "agents_sample.py": [
            "run_sample_proposal_agent",
        ],
    }

    # Also need constants that sit between functions
    # Extract all named defs + any module-level assigns between them via sequential cut
    body = text[header_end:]
    extracted: dict[str, str] = {}
    remaining = body
    for fname, names in groups.items():
        chunk, remaining = _extract_funcs(remaining, names)
        extracted[fname] = chunk

    # leftover constants like _ROLE_LABEL_SLOTS, _QA_FILES, _SAMPLE_PROPOSAL_PID
    leftover = remaining.strip()
    if leftover:
        extracted["agents_common.py"] = leftover + "\n\n" + extracted["agents_common.py"]

    # Write common first with trimmed header (imports)
    common_header = '''"""Agent 共用：开题文本与常量。"""

from __future__ import annotations

from typing import Any

'''
    # Detect which consts need Path etc — put full original imports into each file that needs them
    # For robustness: each concern file gets the original header imports + specific helpers

    full_imports = header  # includes docstring + imports + early consts _LABEL_KEYS etc.

    # Split early consts from imports
    # full_imports already has _LABEL_KEYS and _SEED_KEYS before _proposal_text

    (ROOT / "app" / "llm" / "agents_common.py").write_text(
        full_imports.rstrip()
        + "\n\n"
        + extracted["agents_common.py"],
        encoding="utf-8",
    )

    def write_agent(fname: str, extra_imports: str, body: str) -> None:
        (ROOT / "app" / "llm" / fname).write_text(
            f'"""{fname}"""\n\n'
            "from __future__ import annotations\n\n"
            + extra_imports
            + "\n"
            + body,
            encoding="utf-8",
        )

    # Use a shared approach: each module imports what it needs from agents_common
    # and reuses the big import set via star from a private _agents_imports — too fragile.
    # Better: keep original header in each file (duplicate imports OK).

    for fname, names in groups.items():
        if fname == "agents_common.py":
            continue
        write_agent(
            fname,
            # Import everything from common that might be needed + original third-party
            textwrap.dedent(
                """\
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
                """
            ),
            extracted[fname],
        )
        print("wrote", fname, names)

    # Fix island needing _LABEL_KEYS from common; sample needing others
    # Thin re-export agents.py
    src.write_text(
        '''"""窄 Agent：匹配推荐 / Spec 润色 / 填岛 / E-R 中文补全 / 模块图命名 / 测试用例文案 / 修复 / 质检。

实现拆至 agents_*.py；本模块再导出对外符号。
"""

from __future__ import annotations

from app.llm.agents_common import (  # noqa: F401
    _LABEL_KEYS,
    _SEED_KEYS,
    _proposal_text,
)
from app.llm.agents_fix import run_fix_agent  # noqa: F401
from app.llm.agents_island import (  # noqa: F401
    _sanitize_island_patch,
    _sanitize_island_roles,
    run_island_agent,
)
from app.llm.agents_labels import (  # noqa: F401
    run_er_label_agent,
    run_module_label_agent,
    run_testcase_label_agent,
)
from app.llm.agents_match import (  # noqa: F401
    run_match_agent,
    run_spec_agent,
    run_upload_cluster_agent,
)
from app.llm.agents_qa import run_qa_agent  # noqa: F401
from app.llm.agents_sample import run_sample_proposal_agent  # noqa: F401

__all__ = [
    "_LABEL_KEYS",
    "_SEED_KEYS",
    "_proposal_text",
    "_sanitize_island_patch",
    "_sanitize_island_roles",
    "run_upload_cluster_agent",
    "run_match_agent",
    "run_spec_agent",
    "run_island_agent",
    "run_er_label_agent",
    "run_module_label_agent",
    "run_testcase_label_agent",
    "run_fix_agent",
    "run_qa_agent",
    "run_sample_proposal_agent",
]
''',
        encoding="utf-8",
    )
    print("agents reexport ok")


def split_engine() -> None:
    src = ROOT / "app" / "bake" / "engine.py"
    text = src.read_text(encoding="utf-8")
    if (ROOT / "app" / "bake" / "engine_sql.py").exists():
        print("engine already split")
        return

    header_end = text.find("TABLE_COUNT_MIN")
    # Keep docstring + imports as shared
    imports = text[:header_end]

    # Groups by function
    groups = {
        "engine_sql.py": [
            "count_create_tables",
            "assert_table_budget",
            "_write",
            "_patch_student_readme",
            "_merge_tree",
            "_sql_template_path",
            "_load_named_domain_sql",
            "domain_sql",
        ],
        "engine_bake.py": [
            "bake_project",
            "_patch_thesis_yml",
        ],
        "engine_resources.py": [
            "_write_profile_fields_resource",
            "_write_loyalty_resource",
            "_write_ticket_columns_resource",
            "_write_archive_columns_resource",
            "_write_ticket_copy_resource",
            "_write_factory_delivered",
        ],
        "engine_islands.py": [
            "emit_schema_to_workspace",
            "sync_workspace_thesis_yml",
            "llm_fill_islands",
        ],
    }

    # Constants before first def
    first_def = text.find("\ndef count_create_tables")
    consts = text[header_end:first_def]
    body = text[first_def + 1 :]  # drop leading newline for extract

    extracted: dict[str, str] = {}
    remaining = body
    for fname, names in groups.items():
        chunk, remaining = _extract_funcs(remaining, names)
        extracted[fname] = chunk
    if remaining.strip():
        print("WARN engine leftover:\n", remaining[:400])

    sql_mod = (
        '"""Bake：SQL 装载与表数量门禁。"""\n\n'
        + imports
        + consts
        + extracted["engine_sql.py"]
    )
    (ROOT / "app" / "bake" / "engine_sql.py").write_text(sql_mod, encoding="utf-8")

    for fname in ("engine_bake.py", "engine_resources.py", "engine_islands.py"):
        (ROOT / "app" / "bake" / fname).write_text(
            f'"""{fname}"""\n\n'
            + imports
            + "from app.bake.engine_sql import (  # noqa: F401\n"
            "    TABLE_COUNT_MAX,\n"
            "    TABLE_COUNT_MIN,\n"
            "    _SQL_DIR,\n"
            "    _FALLBACK_SQL,\n"
            "    _load_named_domain_sql,\n"
            "    _merge_tree,\n"
            "    _patch_student_readme,\n"
            "    _sql_template_path,\n"
            "    _write,\n"
            "    assert_table_budget,\n"
            "    count_create_tables,\n"
            "    domain_sql,\n"
            ")\n\n"
            + extracted[fname],
            encoding="utf-8",
        )
        print("wrote", fname)

    # bake_project likely calls resource writers — need cross imports
    # Fix engine_bake to import resources
    bake_path = ROOT / "app" / "bake" / "engine_bake.py"
    bake_text = bake_path.read_text(encoding="utf-8")
    if "_write_factory_delivered" in bake_text or "_write_profile" in bake_text:
        bake_path.write_text(
            bake_text.replace(
                "from app.bake.engine_sql import (",
                "from app.bake.engine_resources import (  # noqa: F401\n"
                "    _write_archive_columns_resource,\n"
                "    _write_factory_delivered,\n"
                "    _write_loyalty_resource,\n"
                "    _write_profile_fields_resource,\n"
                "    _write_ticket_columns_resource,\n"
                "    _write_ticket_copy_resource,\n"
                ")\n"
                "from app.bake.engine_sql import (",
            ),
            encoding="utf-8",
        )

    src.write_text(
        '''"""确定性 bake：复制骨架 + 领域叠加 + SQL / Spec。

实现见 engine_sql / engine_bake / engine_resources / engine_islands。
"""

from __future__ import annotations

from app.bake.engine_bake import bake_project  # noqa: F401
from app.bake.engine_islands import (  # noqa: F401
    emit_schema_to_workspace,
    llm_fill_islands,
    sync_workspace_thesis_yml,
)
from app.bake.engine_sql import (  # noqa: F401
    TABLE_COUNT_MAX,
    TABLE_COUNT_MIN,
    assert_table_budget,
    count_create_tables,
    domain_sql,
)

__all__ = [
    "TABLE_COUNT_MIN",
    "TABLE_COUNT_MAX",
    "count_create_tables",
    "assert_table_budget",
    "domain_sql",
    "bake_project",
    "emit_schema_to_workspace",
    "sync_workspace_thesis_yml",
    "llm_fill_islands",
]
''',
        encoding="utf-8",
    )
    print("engine reexport ok")


def split_system() -> None:
    src = ROOT / "app" / "api" / "system.py"
    text = src.read_text(encoding="utf-8")
    if (ROOT / "app" / "api" / "system_deepseek.py").exists():
        print("system already split")
        return

    # Cut by route groups using line markers
    markers = [
        ("system_deepseek.py", "def _clamp_token_budgets", "def _hydrate_gemini_settings"),
        ("system_gemini.py", "def _hydrate_gemini_settings", "@router.get(\"/unsplash\""),
        ("system_unsplash.py", "@router.get(\"/unsplash\"", "@router.get(\"/deepseek/balance\""),
        ("system_usage.py", "@router.get(\"/deepseek/balance\"", "def _cmd_version"),
        ("system_info.py", "def _cmd_version", "@router.get(\"/tools/sample-proposal/packs\""),
        ("system_tools.py", "@router.get(\"/tools/sample-proposal/packs\"", None),
    ]

    header_end = text.find("router = APIRouter")
    header = text[:header_end]
    # include router line in shared
    shared = header + "router = APIRouter(prefix=\"/api\")\n\n"

    # Find starts
    pieces: list[tuple[str, str]] = []
    for fname, start_pat, end_pat in markers:
        s = text.find(start_pat)
        if s < 0:
            raise SystemExit(f"marker not found: {start_pat}")
        if end_pat is None:
            e = len(text)
        else:
            e = text.find(end_pat)
            if e < 0:
                raise SystemExit(f"end marker not found: {end_pat}")
        pieces.append((fname, text[s:e].rstrip() + "\n"))

    for fname, body in pieces:
        (ROOT / "app" / "api" / fname).write_text(
            '"""system 子模块。"""\n\n'
            "from __future__ import annotations\n\n"
            "# 延迟：由 system.py 注入 router 与共用依赖后再 exec 不安全。\n"
            "# 改为：本文件只提供 register(router) 内联定义。\n"
            "pass\n",
            encoding="utf-8",
        )

    # Safer approach for FastAPI: keep helpers+routes in modules that accept router
    # Rewrite: each module defines register(router) with the route functions copied.

    def make_register_module(fname: str, body: str, needs: str) -> None:
        # Indent body into register? Decorators use @router — so modules should import router from system
        # Circular: system imports modules which import system.router
        # Pattern: modules import `from app.api.system_router import router`
        (ROOT / "app" / "api" / fname).write_text(
            f'"""{fname} — 由 system 聚合。"""\n\n'
            + header
            + "from app.api.system_router import router  # noqa: E402\n\n"
            + body
            + "\n",
            encoding="utf-8",
        )
        print("wrote", fname, len(body.splitlines()))

    (ROOT / "app" / "api" / "system_router.py").write_text(
        '''"""共享 APIRouter（避免 system 子模块循环导入）。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api")
''',
        encoding="utf-8",
    )

    for fname, body in pieces:
        make_register_module(fname, body, "")

    # system.py becomes aggregator + re-exports for main.py private helpers
    src.write_text(
        '''"""系统配置 / LLM 用量 / 运行环境 / 样例开题工具。

路由实现见 system_*.py；本模块聚合 router 并再导出 main 所需符号。
"""

from __future__ import annotations

from app.api.system_router import router  # noqa: F401

# 注册路由（导入副作用）
from app.api import system_deepseek as _system_deepseek  # noqa: F401
from app.api import system_gemini as _system_gemini  # noqa: F401
from app.api import system_info as _system_info  # noqa: F401
from app.api import system_tools as _system_tools  # noqa: F401
from app.api import system_unsplash as _system_unsplash  # noqa: F401
from app.api import system_usage as _system_usage  # noqa: F401

# main.py 启动时水合 DeepSeek
from app.api.system_deepseek import _get_ds_row, _hydrate_ds_settings  # noqa: F401

__all__ = ["router", "_get_ds_row", "_hydrate_ds_settings"]
''',
        encoding="utf-8",
    )
    print("system reexport ok")


if __name__ == "__main__":
    split_proposal_packs()
    split_themes_css()
    split_er_labels()
    split_agents()
    split_engine()
    split_system()
