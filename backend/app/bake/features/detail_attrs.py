"""商品详情属性 detail_attrs：开题在详情括号里点名的属性才挂；仅 DOM-SHOP / DOM-FOOD。

价格、简介、图片、库存、分类、规格已有字段，不重复加。
其余属性进档案字段，落 detail_json，不按行业写死列。
"""

from __future__ import annotations

import re
from typing import Any

DETAIL_ATTRS_CAP = "detail_attrs"

_TRADE_DOMAINS = frozenset({"DOM-SHOP", "DOM-FOOD"})

_DETAIL_RE = re.compile(r"详情[（(]([^）)]{2,160})[）)]")

_SKIP_LABELS = frozenset(
    {
        "价格",
        "单价",
        "简介",
        "图片",
        "图集",
        "库存",
        "分类",
        "名称",
        "商品名",
        "货号",
        "规格",
        "商品规格",
    }
)

# 常见属性到稳定英文键。未收录的按出现顺序用 attr1、attr2。
_LABEL_KEYS: dict[str, str] = {
    "品牌": "brand",
    "材质": "material",
    "重量": "weight",
    "尺寸": "size",
    "承重": "loadCap",
    "阻力": "resistance",
    "承重/阻力": "loadCap",
    "适用人群": "audience",
    "产地": "originPlace",
    "采摘时间": "pickedOn",
    "香型": "aroma",
    "净含量": "netContent",
    "保质期": "shelfLife",
    "口味": "flavor",
    "容量": "capacity",
    "颜色": "colorName",
    "型号": "modelName",
    "功效": "effectNote",
}


def parse_detail_labels(text: str) -> list[str]:
    labels: list[str] = []
    for match in _DETAIL_RE.finditer(text or ""):
        for part in re.split(r"[、,，]", match.group(1)):
            label = part.strip().strip("等")
            if not label or label in _SKIP_LABELS or label in labels:
                continue
            if len(label) > 16:
                continue
            labels.append(label)
    return labels[:12]


def _field_type(label: str) -> str:
    if "时间" in label or "日期" in label:
        return "date"
    if label == "重量":
        return "number"
    return "string"


def detail_attr_fields(labels: list[str]) -> list[dict[str, str]]:
    used: set[str] = set()
    fields: list[dict[str, str]] = []
    seq = 0
    for label in labels:
        key = _LABEL_KEYS.get(label, "")
        if not key or key in used:
            seq += 1
            key = f"attr{seq}"
            while key in used:
                seq += 1
                key = f"attr{seq}"
        used.add(key)
        fields.append({"key": key, "label": label, "type": _field_type(label)})
    return fields


def merge_detail_attrs_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    out = list(caps or [])
    if DETAIL_ATTRS_CAP in out:
        return out
    if (domain or "") not in _TRADE_DOMAINS:
        return out
    if "archive" not in out:
        return out
    if not parse_detail_labels(proposal_text or ""):
        return out
    out.append(DETAIL_ATTRS_CAP)
    return out


def apply_detail_attrs_to_spec(
    spec: dict[str, Any], proposal_text: str = ""
) -> dict[str, Any]:
    title = str(spec.get("title") or "")
    blob = f"{title}\n{proposal_text or ''}"
    caps = merge_detail_attrs_capabilities(
        list(spec.get("capabilities") or []),
        blob,
        domain=spec.get("domain"),
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if DETAIL_ATTRS_CAP not in caps:
        return {**spec, "schema": schema}

    ents = schema.setdefault("entities", {})
    archive = ents.setdefault("archive", {})
    if not isinstance(archive, dict):
        return {**spec, "schema": schema}
    existing = list(archive.get("fields") or [])
    have_labels = {
        str(field.get("label") or "")
        for field in existing
        if isinstance(field, dict)
    }
    have_keys = {
        str(field.get("key") or "")
        for field in existing
        if isinstance(field, dict)
    }
    added: list[dict[str, str]] = []
    for field in detail_attr_fields(parse_detail_labels(blob)):
        if field["label"] in have_labels or field["key"] in have_keys:
            continue
        added.append(field)
        have_labels.add(field["label"])
        have_keys.add(field["key"])
    if not added:
        caps = [c for c in caps if c != DETAIL_ATTRS_CAP]
        schema["capabilities"] = caps
        return {**spec, "capabilities": caps, "schema": schema}
    archive["fields"] = existing + added
    schema["detailAttrKeys"] = [field["key"] for field in added]
    features = list(spec.get("features") or [])
    names = {f.get("name") for f in features if isinstance(f, dict)}
    if "商品详情属性" not in names:
        features.append({"name": "商品详情属性", "status": "module"})
    spec["features"] = features
    spec["schema"] = schema
    return spec
