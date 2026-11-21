"""档案字段 → 控件映射（与 skeletons/.../archiveFieldWidget.js 对齐）。

真源纪律：docs/form-controls.md §1；标签启发式真源 services.widget_hints。
改 JS 映射须同步本表与测。
"""

from __future__ import annotations

from typing import Any

from app.services import widget_hints as wh

# 与 JS archiveFieldWidget 返回值全集一致
WIDGET_KINDS: frozenset[str] = wh.WIDGET_KINDS


def is_archive_money_field(
    field: dict[str, Any] | None,
    *,
    rows: list[dict[str, Any]] | None = None,
) -> bool:
    """对齐 domainSchema.isArchiveMoneyField（最小子集）。"""
    f = field or {}
    if f.get("format") == "money" or f.get("money") is True:
        return True
    if str(f.get("type") or "") != "number":
        return False
    key = str(f.get("key") or "")
    label = str(f.get("label") or "")
    if key == "author":
        return True
    hit = wh.match_widget_hint(
        field_type="number",
        key=key,
        label=label,
        rows=rows,
        only_widgets=frozenset({"money"}),
    )
    return hit == "money"


def archive_field_widget(
    field: dict[str, Any] | None,
    *,
    stock_as_toggle: bool = False,
    body_field: str = "",
    rows: list[dict[str, Any]] | None = None,
) -> str:
    """对齐 archiveFieldWidget.js 决策序。"""
    if not field or not field.get("key"):
        return "text"
    typ = str(field.get("type") or "string")
    key = str(field.get("key"))
    label = str(field.get("label") or "")

    if typ == "hidden":
        return "hidden"
    if key == "stock" and stock_as_toggle:
        return "switch"
    if typ in ("boolean", "switch"):
        return "switch"
    # 标签启发式：number+是否 → switch
    hint = wh.match_widget_hint(
        field_type=typ, key=key, label=label, rows=rows, only_widgets=frozenset({"switch"})
    )
    if hint == "switch" and typ == "number":
        return "switch"
    if typ == "select":
        return "select"
    if typ == "datetime":
        return "datetime"
    if typ == "date":
        return "date"
    if typ == "time":
        return "time"
    if typ == "url":
        return "url"
    if typ == "textarea":
        return "textarea"
    if typ == "richtext" or (body_field and key == body_field):
        return "richtext"
    if typ == "number":
        return "money" if is_archive_money_field(field, rows=rows) else "number"
    # string 标签覆盖：number / textarea 等
    if typ == "string":
        hit = wh.match_widget_hint(field_type="string", key=key, label=label, rows=rows)
        if hit:
            return hit
    return "text"


# (field, ctx_kwargs, expected_widget) — 钉死语义表；增删改须与 JS 同批
WIDGET_CASES: tuple[tuple[dict[str, Any], dict[str, Any], str], ...] = (
    ({"key": "secret", "type": "hidden"}, {}, "hidden"),
    ({"key": "stock", "type": "number"}, {"stock_as_toggle": True}, "switch"),
    ({"key": "enabled", "type": "boolean"}, {}, "switch"),
    ({"key": "flag", "type": "switch"}, {}, "switch"),
    ({"key": "needTrain", "type": "number", "label": "是否需培训（1是0否）"}, {}, "switch"),
    ({"key": "category", "type": "select"}, {}, "select"),
    ({"key": "startAt", "type": "datetime"}, {}, "datetime"),
    ({"key": "bornOn", "type": "date"}, {}, "date"),
    ({"key": "openAt", "type": "time"}, {}, "time"),
    ({"key": "home", "type": "url"}, {}, "url"),
    ({"key": "note", "type": "textarea"}, {}, "textarea"),
    ({"key": "body", "type": "richtext"}, {}, "richtext"),
    ({"key": "intro", "type": "string"}, {"body_field": "intro"}, "richtext"),
    ({"key": "qty", "type": "number", "label": "数量"}, {}, "number"),
    ({"key": "price", "type": "number", "label": "单价（元）"}, {}, "money"),
    ({"key": "fee", "type": "number", "format": "money"}, {}, "money"),
    ({"key": "author", "type": "number", "label": "价"}, {}, "money"),
    ({"key": "remark", "type": "string", "label": "备注"}, {}, "textarea"),
    ({"key": "loadCap", "type": "string", "label": "承重"}, {}, "number"),
    ({"key": "resistance", "type": "string", "label": "阻力"}, {}, "number"),
    ({"key": "title", "type": "string", "label": "名称"}, {}, "text"),
    ({}, {}, "text"),
)
