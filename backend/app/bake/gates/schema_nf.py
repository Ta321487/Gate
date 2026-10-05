"""出包库表：业务一对多走子表；禁止 JSON 列承载业务规则。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.bake.schema.er_model import COL_RE, CREATE_RE

# 表.列：快照 / 媒体袋 / 资料扩展（不当闸口规则）
ALLOWED_JSON_TABLE_COL: frozenset[tuple[str, str]] = frozenset(
    {
        ("archive_log", "payload_json"),
        ("sys_user", "profile_json"),
    }
)
ALLOWED_JSON_COL_ANY_TABLE: frozenset[str] = frozenset(
    {
        "gallery_json",
        "post_gallery_json",
    }
)
# 逗号串当 1:N 实体，等同未满足 1NF
FORBIDDEN_MULTI_VALUE_COLUMNS: frozenset[str] = frozenset(
    {
        "companion_names",
    }
)

_ADD_COLUMN_RE = re.compile(
    r"(?i)ADD\s+COLUMN\s+`?([A-Za-z_][A-Za-z0-9_]*)`?",
)


def _json_allowed(table: str, col: str) -> bool:
    t, c = table.lower(), col.lower()
    if c in ALLOWED_JSON_COL_ANY_TABLE:
        return True
    return (t, c) in ALLOWED_JSON_TABLE_COL


def find_schema_nf_issues(sql: str) -> list[str]:
    """扫 CREATE TABLE：非白名单 *_json / JSON 类型、以及逗号集合列。"""
    issues: list[str] = []
    for tm in CREATE_RE.finditer(sql or ""):
        table = tm.group(1).lower()
        body = tm.group(2) or ""
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("--"):
                continue
            upper = line.upper()
            if upper.startswith(("PRIMARY ", "KEY ", "UNIQUE ", "CONSTRAINT ", "INDEX ", "FOREIGN ")):
                continue
            cm = COL_RE.match(line.rstrip(","))
            if not cm:
                continue
            col = cm.group(1).lower()
            ctype = (cm.group(2) or "").lower()
            if col in FORBIDDEN_MULTI_VALUE_COLUMNS:
                issues.append(f"{table}.{col} 用逗号串装 1:N，须改子表")
                continue
            is_json_col = col.endswith("_json") or ctype.startswith("json")
            if is_json_col and not _json_allowed(table, col):
                issues.append(f"{table}.{col} 用 JSON 装业务，须改列或子表")
    return issues


def assert_schema_nf(sql: str) -> None:
    issues = find_schema_nf_issues(sql)
    if issues:
        raise ValueError("库表须满足 3NF 口径（禁止 JSON 当业务规则）：" + "；".join(issues[:12]))


def evaluate_workspace_schema_nf(workspace: Path) -> dict[str, Any]:
    path = Path(workspace) / "sql" / "schema.sql"
    if not path.is_file():
        return {
            "ok": False,
            "label": "库表 3NF · JSON",
            "desc": "缺少 sql/schema.sql",
            "issues": ["missing sql/schema.sql"],
        }
    sql = path.read_text(encoding="utf-8", errors="ignore")
    issues = find_schema_nf_issues(sql)
    return {
        "ok": not issues,
        "label": "库表 3NF · JSON",
        "desc": "；".join(issues[:8]) if issues else "未见非白名单 JSON 业务列",
        "issues": issues,
    }


def find_forbidden_add_column_json(java_text: str) -> list[str]:
    """骨架不得 ADD COLUMN 非白名单 JSON（含 detail_json）。"""
    hits: list[str] = []
    for m in _ADD_COLUMN_RE.finditer(java_text or ""):
        col = m.group(1).lower()
        if col.endswith("_json") and col not in ALLOWED_JSON_COL_ANY_TABLE:
            if col in {"payload_json", "profile_json"}:
                continue
            hits.append(col)
    return hits
