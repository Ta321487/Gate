"""演示种子日程修复：SeedCalendarAligner 之后仍可能因「今日已过点」被 expirePastStarts 下架。"""

from __future__ import annotations

import re
from pathlib import Path

_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\((.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)
_YML_ITEM_TABLE_RE = re.compile(r"^\s*archive-item-table:\s*(\S+)\s*$", re.MULTILINE)


def archive_item_tables_in_sql(sql: str) -> list[str]:
    """从 CREATE TABLE 中找出带 start_at 的档案类主表。"""
    out: list[str] = []
    for m in _CREATE_TABLE_RE.finditer(sql or ""):
        table, body = m.group(1), m.group(2)
        if re.search(r"\bstart_at\b", body, re.IGNORECASE):
            out.append(table)
    return out


def read_archive_item_table(workspace: Path) -> str | None:
    yml = workspace / "backend" / "src" / "main" / "resources" / "application.yml"
    if not yml.is_file():
        return None
    m = _YML_ITEM_TABLE_RE.search(yml.read_text(encoding="utf-8", errors="ignore"))
    return m.group(1).strip() if m else None


def replay_archive_inserts_if_empty(
    cur,
    db_name: str,
    sql_text: str,
    *,
    item_table: str | None,
    split_sql,
) -> None:
    """档案主表被清空时回放 schema 里的 INSERT IGNORE（幂等）。"""
    table = (item_table or "").strip()
    if not table or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table):
        return
    try:
        cur.execute(f"SELECT COUNT(*) FROM `{db_name}`.`{table}`")
        row = cur.fetchone()
        if row and int(row[0] or 0) > 0:
            return
    except Exception:  # noqa: BLE001
        return
    for stmt in split_sql(sql_text or ""):
        if re.match(rf"INSERT\s+IGNORE\s+INTO\s+`?{re.escape(table)}`?\b", stmt, re.I):
            try:
                cur.execute(stmt)
            except Exception:  # noqa: BLE001
                pass


def repair_demo_schedules_in_db(cur, db_name: str, *, item_tables: list[str]) -> None:
    """预览启动后复位过期日程与演示下架行（幂等）。"""
    seen: set[str] = set()
    for table in item_tables:
        t = (table or "").strip()
        if not t or t in seen or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
            continue
        seen.add(t)
        _repair_item_table(cur, db_name, t)
    _repair_slot_table(cur, db_name)


def _repair_item_table(cur, db_name: str, table: str) -> None:
    for col, add_days in (
        ("start_at", 14),
        ("end_at", 15),
        ("apply_deadline_at", 13),
    ):
        try:
            cur.execute(
                f"UPDATE `{db_name}`.`{table}` SET `{col}`=DATE_ADD(NOW(), INTERVAL %s DAY) "
                f"WHERE `{col}` IS NOT NULL AND `{col}` <= NOW()",
                (add_days,),
            )
        except Exception:  # noqa: BLE001
            pass
    try:
        cur.execute(
            f"UPDATE `{db_name}`.`{table}` SET status='available' "
            f"WHERE status='unavailable' AND id <= 50"
        )
    except Exception:  # noqa: BLE001
        pass


def _repair_slot_table(cur, db_name: str) -> None:
    try:
        cur.execute(
            f"UPDATE `{db_name}`.`resource_slot` SET start_at=DATE_ADD(NOW(), INTERVAL 1 DAY), "
            f"end_at=DATE_ADD(NOW(), INTERVAL 1 DAY) + INTERVAL 1 HOUR "
            f"WHERE start_at IS NOT NULL AND start_at <= NOW()"
        )
    except Exception:  # noqa: BLE001
        pass
