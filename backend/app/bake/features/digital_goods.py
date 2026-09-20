"""数字商品履约。开题写到才挂，挂在商城订单上。

付款后写入激活码或下载链接，跳过发货。数字单默认不支持无理由退。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

DIGITAL_GOODS_CAP = "digital_goods"

_TERMS = (
    "数字商品",
    "激活码",
    "电子书",
    "虚拟商品",
    "下载链接",
    "无物流",
    "即时交付",
    "会员开通",
    "在线课程销售",
    "数字下载",
)


def _hit(text: str, terms: tuple[str, ...]) -> bool:
    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in terms)


def scan_digital_goods(text: str, title: str = "") -> bool:
    blob = f"{title or ''}\n{text or ''}"
    if _hit(blob, _TERMS):
        return True
    if _hit(blob, ("电子", "虚拟", "数字")) and _hit(blob, ("商城", "商品", "课程", "会员", "素材")):
        return True
    return False


def merge_digital_goods_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if (domain or "") != "DOM-SHOP" or "order_lines" not in out:
        return [c for c in out if c != DIGITAL_GOODS_CAP]
    if DIGITAL_GOODS_CAP in out:
        return out
    if scan_digital_goods(proposal_text or "", title):
        out.append(DIGITAL_GOODS_CAP)
    return out


def apply_digital_goods_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    caps = merge_digital_goods_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if DIGITAL_GOODS_CAP not in caps:
        return {**spec, "schema": schema}

    schema["digitalGoods"] = True
    schema["noCasualRefund"] = True
    labels = dict(schema.get("labels") or {})
    labels.setdefault("digitalDeliveryMenu", "数字交付")
    labels.setdefault("myDigitalMenu", "我的兑换码")
    labels.setdefault(
        "digitalGoodsHint",
        "付款后即可查看激活码或下载链接，无需发货。数字商品不支持无理由退款。",
    )
    schema["labels"] = labels

    ents = dict(schema.get("entities") or {})
    order = dict(ents.get("order") or {})
    order["fulfillMode"] = "digital"
    order["states"] = {
        "pending": "待付款",
        "confirmed": "已交付",
        "completed": "已完成",
        "cancelled": "已取消",
    }
    order["verbs"] = {
        "confirm": "确认交付",
        "complete": "办结",
    }
    ents["order"] = order
    archive = dict(ents.get("archive") or {})
    fields = list(archive.get("fields") or [])
    if not any(f.get("key") == "digitalKind" for f in fields):
        fields.append(
            {
                "key": "digitalKind",
                "label": "交付方式",
                "type": "select",
                "options": [
                    {"value": "code", "label": "激活码"},
                    {"value": "link", "label": "下载链接"},
                    {"value": "permit", "label": "课程权限"},
                ],
            }
        )
    archive["fields"] = fields
    ents["archive"] = archive
    schema["entities"] = ents

    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    ensure_menu(
        admin,
        "digital_codes",
        {"key": "digital_codes", "label": "数字码池", "superOnly": False},
        before_key="orders",
    )
    menus["admin"] = admin
    user = list(menus.get("user") or [])
    ensure_menu(user, "my_digital", {"key": "my_digital", "label": labels.get("myDigitalMenu", "我的兑换码")})
    menus["user"] = user
    schema["menus"] = menus
    return {**spec, "schema": schema}
