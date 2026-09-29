"""驿站寄件登记 parcel_ship：开题写「寄件」才挂；无域默认。

用户提交寄件登记 → 店员受理 → 已寄出。≠ 取件核销主路径；≠ 快递公司电子面单。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

PARCEL_SHIP_CAP = "parcel_ship"

_TERMS = (
    "寄件",
    "寄快递",
    "寄出包裹",
    "寄件登记",
    "发件",
    "寄件服务",
)

_PARCEL_SHIP_DOMAINS = frozenset({"DOM-PARCEL"})


def scan_parcel_ship(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _TERMS)


def merge_parcel_ship_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    out = list(caps or [])
    if PARCEL_SHIP_CAP in out:
        return out
    if (domain or "") not in _PARCEL_SHIP_DOMAINS:
        return out
    if not scan_parcel_ship(proposal_text or ""):
        return out
    out.append(PARCEL_SHIP_CAP)
    return out


def attach_parcel_ship_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
    admin = menus.setdefault("admin", [])
    ensure_menu(
        user,
        "parcel_ship",
        {"key": "parcel_ship", "label": "寄件登记"},
        before_key="my_tickets",
    )
    ensure_menu(
        admin,
        "parcel_ship",
        {"key": "parcel_ship", "label": "寄件办理", "superOnly": False},
        before_key="ticket_pending",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("parcelShipPageTitle", "寄件登记")
    labels.setdefault(
        "parcelShipPageLead",
        "填写收件信息与物品说明提交寄件；到站后由店员受理并登记寄出。",
    )
    labels.setdefault("parcelShipAdminTitle", "寄件办理")
    labels.setdefault(
        "parcelShipAdminLead",
        "受理用户寄件登记：确认揽收后标记已寄出。",
    )
    labels.setdefault("parcelShipOkMessage", "寄件已提交，请等待驿站受理")
    ents = schema.setdefault("entities", {})
    ents.setdefault(
        "parcel_ship",
        {"key": "parcel_ship", "label": "寄件单", "labelPlural": "寄件单"},
    )


def apply_parcel_ship_to_spec(
    spec: dict[str, Any], proposal_text: str = ""
) -> dict[str, Any]:
    text = proposal_text or ""
    caps = merge_parcel_ship_capabilities(
        list(spec.get("capabilities") or []),
        text,
        domain=spec.get("domain"),
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if PARCEL_SHIP_CAP in caps:
        attach_parcel_ship_menus(schema)
        from app.bake.gate_contracts import merge_parcel_ship_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_parcel_ship_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "寄件登记" not in names:
            features.append({"name": "寄件登记", "status": "flow"})
        spec["features"] = features
    spec["schema"] = schema
    return spec
