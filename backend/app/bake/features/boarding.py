"""寄养。开题写到才挂，挂在已有按天入住上。

寄养位和日价沿用房型与房价。重叠日期用现有时段占用，满了不能再约。
只写酒店入住、宠物挂号、领养或宠物咖啡不开日志。
"""

from __future__ import annotations

import re
from app.bake.sql.ddl_edit import (
    CREATE_TABLE_RE as _CREATE_TABLE_RE,
    inject_missing_columns as _inject_missing_columns,
    prune_columns as _prune_columns,
)

from decimal import Decimal
from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

BOARDING_CAP = "boarding"

_ANCHORS = ("寄养", "每日反馈")


def stay_yuan(unit: Decimal | int | str, days: int) -> Decimal:
    n = int(days)
    if n < 1:
        raise ValueError("离店须晚于入住")
    return (Decimal(str(unit)) * Decimal(n)).quantize(Decimal("0.01"))


def _hit(text: str) -> bool:
    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _ANCHORS)


def scan_boarding(text: str, title: str = "") -> bool:
    return _hit(f"{title or ''}\n{text or ''}")


def merge_boarding_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if (domain or "") != "DOM-HOTEL" or "slot_reserve" not in out:
        return [c for c in out if c != BOARDING_CAP]
    if BOARDING_CAP in out:
        return out
    if scan_boarding(proposal_text or "", title):
        out.append(BOARDING_CAP)
    return out


def apply_boarding_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    caps = merge_boarding_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if BOARDING_CAP not in caps:
        return {**spec, "schema": schema}

    schema["boarding"] = True
    labels = dict(schema.get("labels") or {})
    labels.setdefault("careOptionMenu", "特殊要求")
    labels.setdefault("stayLogMenu", "寄养日志")
    labels.setdefault("myStayMenu", "寄养记录")
    labels.setdefault(
        "boardingHint",
        "选择寄养位和日期。金额按日价乘以天数。特殊要求记在这一次入住上。",
    )
    schema["labels"] = labels
    ents = dict(schema.get("entities") or {})
    archive = dict(ents.get("archive") or {})
    fields = []
    for field in list(archive.get("fields") or []):
        row = dict(field)
        if row.get("key") == "title":
            row["label"] = "寄养位"
        elif row.get("key") == "author":
            row["label"] = "日价(元)"
        elif row.get("key") == "stock":
            row["label"] = "可寄养数"
        fields.append(row)
    if fields:
        archive["fields"] = fields
        ents["archive"] = archive
    resv = dict(ents.get("reservation") or {})
    if resv:
        resv["guestNameLabel"] = "宠物名"
        ents["reservation"] = resv
    schema["entities"] = ents
    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    ensure_menu(
        admin,
        "care_options",
        {"key": "care_options", "label": "特殊要求", "superOnly": False},
    )
    ensure_menu(
        admin,
        "stay_logs",
        {"key": "stay_logs", "label": "寄养日志", "superOnly": False},
    )
    menus["admin"] = admin
    user = list(menus.get("user") or [])
    ensure_menu(user, "my_stay", {"key": "my_stay", "label": "寄养记录"})
    menus["user"] = user
    schema["menus"] = menus
    return {**spec, "schema": schema}


# --- SQL ensure (moved from fragments.py) ---

_BOARDING_DDL = """
CREATE TABLE IF NOT EXISTS stay_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  reservation_id BIGINT NULL,
  option_name VARCHAR(64) DEFAULT '',
  enabled TINYINT DEFAULT 1,
  day_key DATE NULL,
  note VARCHAR(255) DEFAULT '',
  photo_url VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

def ensure_boarding_sql(sql: str, *, enabled: bool) -> str:
    """寄养日期与日志。未开不加。特殊要求与每日记录共用 stay_log。"""
    if not enabled:
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "reservation":
            return m.group(0)
        body = _inject_missing_columns(
            body,
            [
                ("stay_from", "DATE NULL"),
                ("stay_to", "DATE NULL"),
                ("care_ids", "VARCHAR(128) NULL"),
            ],
        )
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?stay_log`?\b", out):
        return out
    seed = """INSERT INTO stay_log (id, option_name, enabled)
SELECT 1, '喂药', 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM stay_log WHERE id=1);
INSERT INTO stay_log (id, option_name, enabled)
SELECT 2, '遛弯', 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM stay_log WHERE id=2);
INSERT INTO stay_log (id, reservation_id, day_key, note, photo_url)
SELECT 3, 1, '2026-09-21', '已喂食，精神好', '/files/pet-1.jpg' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM stay_log WHERE id=3);
"""
    return out.rstrip() + "\n" + _BOARDING_DDL + "\n" + seed
