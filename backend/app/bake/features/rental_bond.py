"""租赁押金/租金/逾期费与验损退押。开题写到才挂，挂在租约订单上。

不是设备借用申请审还。押金、租金、逾期费三笔分开记；还车后验损再退押金。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

RENTAL_BOND_CAP = "rental_bond"

_TERMS = (
    "押金",
    "验损",
    "逾期费",
    "退押金",
    "租赁商城",
    "日租金",
)

_GEAR_HINTS = ("租设备", "设备租赁", "器材租赁", "租器材")
_CLOTHES_HINTS = ("租衣服", "服装租赁", "租服装", "礼服租赁", "婚纱租赁")


def _hit(text: str, terms: tuple[str, ...]) -> bool:
    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in terms)


def scan_rental_bond(text: str, title: str = "") -> bool:
    blob = f"{title or ''}\n{text or ''}"
    if _hit(blob, _TERMS):
        return True
    if _hit(blob, ("租金",)) and _hit(blob, ("押金", "逾期", "归还")):
        return True
    return False


def rental_archive_skin(title: str, proposal_text: str = "") -> str:
    """车型 / 器材 / 服装档案文案皮。"""
    blob = f"{title or ''}\n{proposal_text or ''}"
    if _hit(blob, _CLOTHES_HINTS):
        return "clothes"
    if _hit(blob, _GEAR_HINTS):
        return "gear"
    return "car"


def merge_rental_bond_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if (domain or "") != "DOM-CARRENT" or "order_lines" not in out or "slot_reserve" not in out:
        return [c for c in out if c != RENTAL_BOND_CAP]
    if RENTAL_BOND_CAP in out:
        return out
    if scan_rental_bond(proposal_text or "", title):
        out.append(RENTAL_BOND_CAP)
    return out


def apply_rental_bond_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    caps = merge_rental_bond_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if RENTAL_BOND_CAP not in caps:
        return {**spec, "schema": schema}

    schema["rentalBond"] = True
    skin = rental_archive_skin(title, proposal_text or "")
    schema["rentalBondSkin"] = skin
    labels = dict(schema.get("labels") or {})
    labels.setdefault("rentalInspectMenu", "验损退押")
    labels.setdefault("rentalBondHint", "下单支付押金与租金；还车后店员验损，再退还或扣除押金。逾期另计逾期费。")
    schema["labels"] = labels

    ents = dict(schema.get("entities") or {})
    archive = dict(ents.get("archive") or {})
    fields = list(archive.get("fields") or [])
    noun = {"car": "车型", "gear": "器材", "clothes": "服装"}.get(skin, "车型")
    day_lab = {"car": "日租金(元)", "gear": "日租金(元)", "clothes": "日租金(元)"}.get(skin, "日租金(元)")
    stock_lab = {"car": "可租辆数", "gear": "可租件数", "clothes": "可租件数"}.get(skin, "可租辆数")
    new_fields = []
    has_deposit = False
    for field in fields:
        row = dict(field)
        if row.get("key") == "title":
            row["label"] = noun
        elif row.get("key") == "author":
            row["label"] = day_lab
        elif row.get("key") == "stock":
            row["label"] = stock_lab
        elif row.get("key") == "depositYuan":
            has_deposit = True
        new_fields.append(row)
    if not has_deposit:
        new_fields.append(
            {"key": "depositYuan", "label": "押金(元)", "type": "number", "format": "money"}
        )
    if not any(f.get("key") == "rentStage" for f in new_fields):
        new_fields.append(
            {
                "key": "rentStage",
                "label": "租用状态",
                "type": "select",
                "options": [
                    {"value": "available", "label": "可租"},
                    {"value": "rented", "label": "已租"},
                    {"value": "repair", "label": "维修中"},
                ],
            }
        )
    archive["fields"] = new_fields
    ents["archive"] = archive

    order = dict(ents.get("order") or {})
    states = dict(order.get("states") or {})
    states.setdefault("shipped", "租赁中")
    states.setdefault("completed", "已还车")
    order["states"] = states
    order["rentalBond"] = True
    ents["order"] = order
    schema["entities"] = ents

    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    ensure_menu(
        admin,
        "rental_inspect",
        {"key": "rental_inspect", "label": labels.get("rentalInspectMenu", "验损退押"), "superOnly": False},
        before_key="orders",
    )
    menus["admin"] = admin
    schema["menus"] = menus
    return {**spec, "schema": schema}
