"""驿站货架管理 parcel_shelf：PARCEL 域默认。

管理端维护货架/柜格编码；与已有 structural DDL parcel_shelf 对齐。
≠ 丰巢柜机对接；≠ 寄件。
"""

from __future__ import annotations

from typing import Any

PARCEL_SHELF_CAP = "parcel_shelf"

_PARCEL_SHELF_DOMAINS = frozenset({"DOM-PARCEL"})


def merge_parcel_shelf_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    del proposal_text
    out = list(caps or [])
    if PARCEL_SHELF_CAP in out:
        return out
    if (domain or "") not in _PARCEL_SHELF_DOMAINS:
        return out
    out.append(PARCEL_SHELF_CAP)
    return out


def attach_parcel_shelf_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    ensure_menu(
        admin,
        "parcel_shelf",
        {"key": "parcel_shelf", "label": "货架管理", "superOnly": False},
        before_key="content",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("parcelShelfTitle", "货架管理")
    labels.setdefault(
        "parcelShelfLead",
        "维护驿站货架与柜格编号，便于到件入库时对照存放位置。",
    )
    ents = schema.setdefault("entities", {})
    ents.setdefault(
        "parcel_shelf",
        {"key": "parcel_shelf", "label": "货架", "labelPlural": "货架"},
    )


def apply_parcel_shelf_to_spec(
    spec: dict[str, Any], proposal_text: str = ""
) -> dict[str, Any]:
    caps = merge_parcel_shelf_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=spec.get("domain"),
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if PARCEL_SHELF_CAP in caps:
        attach_parcel_shelf_menus(schema)
        from app.bake.gate_contracts import merge_parcel_shelf_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_parcel_shelf_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "货架管理" not in names:
            features.append({"name": "货架管理", "status": "module"})
        spec["features"] = features
    spec["schema"] = schema
    return spec
