"""engine_islands.py"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.bake.catalog import (
    normalize_auth_entry_mode,
    normalize_auth_role_widget,
    normalize_auth_template,
    normalize_chrome,
    normalize_layout,
    normalize_typeface,
)
from app.bake.domain_schema import (
    deterministic_llm_patch,
    merge_schema,
    product_name_from_title,
    validate_schema,
    write_schema_artifacts,
)

# 答辩/开题常见硬约束：交付库表不宜过少或灌水过多
from app.bake.engine_sql import (  # noqa: F401
    TABLE_COUNT_MAX,
    TABLE_COUNT_MIN,
    _SQL_DIR,
    _FALLBACK_SQL,
    _load_named_domain_sql,
    _merge_tree,
    _patch_student_readme,
    _sql_template_path,
    _write,
    assert_table_budget,
    count_create_tables,
    domain_sql,
)

def emit_schema_to_workspace(workspace: Path, spec: dict[str, Any]) -> list[str]:
    """把已合并的 schema 写入 islands / appDelivered / spec.json，并同步 thesis yml。"""
    merged = spec.get("schema") or {}
    ok, errors = validate_schema(merged)
    if not ok:
        raise RuntimeError("schema 校验失败: " + "; ".join(errors))
    written = write_schema_artifacts(workspace, merged)
    _write(workspace / "spec.json", json.dumps(spec, ensure_ascii=False, indent=2))
    auth_tpl = normalize_auth_template(spec.get("auth_template"))
    auth_entry = normalize_auth_entry_mode(spec.get("auth_entry_mode"))
    auth_widget = normalize_auth_role_widget(spec.get("auth_role_widget"))
    chrome = normalize_chrome(spec.get("chrome"))
    layout = normalize_layout(spec.get("layout"))
    typeface = normalize_typeface(spec.get("typeface"))
    _write_factory_delivered(
        workspace,
        spec.get("title", "毕设系统"),
        spec.get("theme", "lib-ink"),
        auth_tpl,
        merged,
        spec.get("accept"),
        domain=spec.get("domain", "DOM-GENERIC"),
        auth_entry_mode=auth_entry,
        auth_role_widget=auth_widget,
        chrome=chrome,
        layout=layout,
        typeface=typeface,
        seed=workspace.name,
    )
    sync_workspace_thesis_yml(workspace, spec)
    return written

def sync_workspace_thesis_yml(workspace: Path, spec: dict[str, Any]) -> None:
    """与 bake 同一套 _patch_thesis_yml，避免只改 schema 导致 Java 默认值漂移。"""
    app_yml = workspace / "backend" / "src" / "main" / "resources" / "application.yml"
    if not app_yml.exists():
        return
    domain = str(spec.get("domain") or "DOM-GENERIC")
    text = app_yml.read_text(encoding="utf-8")
    app_yml.write_text(_patch_thesis_yml(text, domain, spec), encoding="utf-8")

def llm_fill_islands(workspace: Path, spec: dict[str, Any], enabled: bool) -> list[str]:
    """确定性填岛（无 LLM）。真填岛走 app.llm.agents.run_island_agent。"""
    base = spec.get("schema") or {}
    patch = deterministic_llm_patch(spec, enabled)
    merged = merge_schema(base, patch)
    for k in ("accept", "missing_capabilities", "out_of_mvp_signals", "capabilities"):
        if k in base:
            merged[k] = base[k]
    spec["schema"] = merged
    return emit_schema_to_workspace(workspace, spec)

