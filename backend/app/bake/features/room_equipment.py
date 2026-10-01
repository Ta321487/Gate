"""会议室设备清单 room_equipment：开题扫词才挂；无域默认。

档案 equipment_json 存设备名列表；总管维护 sys_equipment_dict；
详情/预约页展示。≠ 设备借用（DOM-EQUIP）。
"""

from __future__ import annotations

import re
from app.bake.sql.ddl_edit import (
    CREATE_TABLE_RE as _CREATE_TABLE_RE,
    inject_missing_columns as _inject_missing_columns,
    prune_columns as _prune_columns,
)

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

ROOM_EQUIPMENT_CAP = "room_equipment"

_TERMS = ("设备清单", "会议室设备", "配套设备", "投影音响清单", "会议室配套")


def scan_room_equipment(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _TERMS)


def merge_room_equipment_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    out = list(caps or [])
    if ROOM_EQUIPMENT_CAP in out:
        return out
    # 禁止挂到设备借用主路径域
    if (domain or "") == "DOM-EQUIP":
        return out
    if "archive" not in out:
        return out
    # 会议室/时段预约壳才挂
    if (domain or "") != "DOM-MEETING" and "slot_reserve" not in out:
        return out
    if not scan_room_equipment(proposal_text or ""):
        return out
    out.append(ROOM_EQUIPMENT_CAP)
    return out


def attach_room_equipment_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    ensure_menu(
        admin,
        "equipment_dict",
        {"key": "equipment_dict", "label": "设备字典", "superOnly": False},
        before_key="archive",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("equipmentDictPageTitle", "设备字典")
    labels.setdefault(
        "equipmentDictPageLead",
        "维护会议室可勾选的配套设备名称；档案详情与预约页展示已选清单。",
    )
    labels.setdefault("roomEquipmentSectionTitle", "配套设备")
    ents = schema.setdefault("entities", {})
    ents.setdefault(
        "roomEquipment",
        {"key": "room_equipment", "label": "配套设备", "labelPlural": "配套设备"},
    )


def apply_room_equipment_to_spec(
    spec: dict[str, Any], proposal_text: str = ""
) -> dict[str, Any]:
    text = proposal_text or ""
    caps = merge_room_equipment_capabilities(
        list(spec.get("capabilities") or []),
        text,
        domain=spec.get("domain"),
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if ROOM_EQUIPMENT_CAP in caps:
        attach_room_equipment_menus(schema)
        from app.bake.gate_contracts import merge_room_equipment_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_room_equipment_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "会议室设备清单" not in names:
            features.append({"name": "会议室设备清单", "status": "module"})
        spec["features"] = features
    spec["schema"] = schema
    return spec


# --- SQL ensure (moved from fragments.py) ---

ROOM_EQUIPMENT_COLUMNS: list[tuple[str, str]] = [
    ("equipment_json", "TEXT NULL"),
]

_EQUIPMENT_DICT_DDL = """
CREATE TABLE IF NOT EXISTS sys_equipment_dict (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_equip_name (name)
);
"""

_EQUIPMENT_DICT_SEED = """
INSERT INTO sys_equipment_dict (name, sort_order, enabled)
SELECT '投影仪', 10, 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_equipment_dict WHERE name='投影仪');
INSERT INTO sys_equipment_dict (name, sort_order, enabled)
SELECT '音响', 20, 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_equipment_dict WHERE name='音响');
INSERT INTO sys_equipment_dict (name, sort_order, enabled)
SELECT '白板', 30, 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_equipment_dict WHERE name='白板');
INSERT INTO sys_equipment_dict (name, sort_order, enabled)
SELECT '视频会议终端', 40, 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_equipment_dict WHERE name='视频会议终端');
INSERT INTO sys_equipment_dict (name, sort_order, enabled)
SELECT '投屏线', 50, 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_equipment_dict WHERE name='投屏线');
"""

def ensure_room_equipment_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """档案主表补 equipment_json + 设备字典；仅 room_equipment 开启时注入。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    out = sql
    if t and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):

        def repl(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != t.lower():
                return m.group(0)
            body = _inject_missing_columns(body, ROOM_EQUIPMENT_COLUMNS)
            return f"{head}{body}{tail}"

        out = _CREATE_TABLE_RE.sub(repl, out)
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?sys_equipment_dict`?\b", out):
        out = out.rstrip() + "\n" + _EQUIPMENT_DICT_DDL + "\n" + _EQUIPMENT_DICT_SEED
    if t and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        seed_upd = (
            f"\nUPDATE `{t}` SET equipment_json="
            f"""'["投影仪","音响","白板"]' """
            f"WHERE id=1 AND (equipment_json IS NULL OR equipment_json='' OR equipment_json='[]');\n"
        )
        if f"UPDATE `{t}` SET equipment_json=" not in out:
            out = out.rstrip() + seed_upd
    return out
