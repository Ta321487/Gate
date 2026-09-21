"""下单明细快照：刻字/祝语/规格选项/图片。开题写到才挂。

不是商品列，也不是礼品专表。文印、蛋糕祝语、刻章共用 order_line 三列。
状态码仍是 confirmed → shipped；写了制作/定制才把 confirmed 文案改成待制作，并下单即进入该态。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

LINE_CUSTOM_CAP = "line_custom"

# 「定制」是宽词：开题研究现状里的「定制化程度有限 / 可定制电商系统」属系统语义，
# 曾被误判成商品定制而挂上本能力；故只保留与商品/内容共现的强语境形态，宽词不再单独触发。
_TERMS = (
    "定做",
    "刻字",
    "印字",
    "来图定制",
    "祝语",
    "刻章",
    "定制商品",
    "定制款",
    "定制品",
    "定制文字",
    "定制内容",
    "定制图片",
    "定制礼品",
)

_MAKE_TERMS = ("制作", "定做", "定制", "刻字")

_NO_CASUAL_TERMS = (
    "不支持无理由退货",
    "不支持七天无理由",
    "定制品不退",
    "定制不退",
    "不退不换",
    "不予退货",
)

_SPEC_TERMS = ("字体", "颜色", "尺寸")
_IMAGE_TERMS = ("上传", "印图", "来图", "照片", "图片")


def _hit(text: str, terms: tuple[str, ...]) -> bool:
    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in terms)


def scan_line_custom(text: str) -> bool:
    return _hit(text or "", _TERMS)


def line_custom_wants_spec(text: str, title: str = "") -> bool:
    blob = f"{title or ''}\n{text or ''}"
    return _hit(blob, _SPEC_TERMS) or _hit(blob, ("定制", "定做", "刻字"))


def merge_line_custom_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    out = list(caps or [])
    if "order_lines" not in out:
        return [c for c in out if c != LINE_CUSTOM_CAP]
    if LINE_CUSTOM_CAP in out:
        return out
    if scan_line_custom(proposal_text or ""):
        out.append(LINE_CUSTOM_CAP)
    return out


def apply_line_custom_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    text = proposal_text or ""
    title = str(spec.get("title") or "")
    blob = f"{title}\n{text}"
    caps = merge_line_custom_capabilities(
        list(spec.get("capabilities") or []),
        blob,
        domain=spec.get("domain"),
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if LINE_CUSTOM_CAP not in caps:
        return {**spec, "schema": schema}

    labels = dict(schema.get("labels") or {})
    if _hit(blob, ("刻字",)):
        text_label = "刻字内容"
    elif _hit(blob, ("祝语",)) and not _hit(blob, ("定制", "定做", "刻字")):
        text_label = "祝语"
    elif _hit(blob, ("刻章",)):
        text_label = "刻制内容"
    else:
        text_label = "定制文字"
    labels["lineCustomTextLabel"] = text_label
    show_spec = _hit(blob, _SPEC_TERMS) or _hit(blob, ("定制", "定做", "刻字"))
    if show_spec:
        labels["lineCustomSpecLabel"] = (
            "字体/颜色/尺寸" if _hit(blob, _SPEC_TERMS) else "规格选项"
        )
    show_image = _hit(blob, _IMAGE_TERMS)
    if show_image:
        labels["lineCustomImageLabel"] = "定制图片"
    labels["lineCustomHint"] = "填写后会记在本订单上。"
    schema["labels"] = labels
    schema["lineCustom"] = True
    if show_spec:
        from app.bake.schema.menu_utils import ensure_menu

        menus = dict(schema.get("menus") or {})
        admin = list(menus.get("admin") or [])
        ensure_menu(
            admin,
            "line_specs",
            {"key": "line_specs", "label": "规格选项", "superOnly": False},
            before_key="orders",
        )
        menus["admin"] = admin
        schema["menus"] = menus

    make = _hit(blob, _MAKE_TERMS)
    schema["lineCustomPlaceConfirmed"] = make
    if make:
        entities = dict(schema.get("entities") or {})
        order = dict(entities.get("order") or {})
        states = dict(order.get("states") or {})
        states["confirmed"] = "待制作"
        if states.get("shipped") in (None, "", "配送中"):
            states["shipped"] = "已发货"
        order["states"] = states
        verbs = dict(order.get("verbs") or {})
        verbs.setdefault("ship", "发货")
        order["verbs"] = verbs
        entities["order"] = order
        schema["entities"] = entities

    if _hit(blob, _NO_CASUAL_TERMS):
        schema["noCasualRefund"] = True
        labels["refundPolicyHint"] = "不支持无理由退货，请填写质量问题等具体原因。"
        schema["labels"] = labels

    return {**spec, "schema": schema}
