"""会议室设备清单 room_equipment：开题扫词才挂；无域默认。

档案 equipment_json 存设备名列表；总管维护 sys_equipment_dict；
详情/预约页展示。≠ 设备借用（DOM-EQUIP）。
"""

from __future__ import annotations

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
        {"key": "equipment_dict", "label": "设备字典", "superOnly": True},
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
