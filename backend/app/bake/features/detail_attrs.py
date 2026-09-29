"""商品详情属性 detail_attrs：开题点名详情属性才挂；DOM-SHOP / FOOD / CINEMA。

认「详情（…）」括号，以及「详情显示辣度、份量」句式。
「菜品详情 / 影片详情 / 详情显示多个属性字段」等开题话术也可开岛。
价格、简介、图片、库存、分类、规格已有字段，不重复加。
工厂侧用 detailAttrKeys 列表收集；出包按语义落真列（string/number/date），不写 detail_json。
影院域皮未预置导演/主演/时长时，开题点名才加字段；仅开题话术则开岛不硬补列。
"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

DETAIL_ATTRS_CAP = "detail_attrs"

_TRADE_DOMAINS = frozenset({"DOM-SHOP", "DOM-FOOD", "DOM-CINEMA"})
# 房源详情属性（面积/租金/朝向）：与商品详情同理，开题点名才落真列
_EXTRA_DETAIL_DOMAINS = frozenset({"DOM-LISTING"})

_DETAIL_RE = re.compile(r"详情[（(]([^）)]{2,160})[）)]")
# 「详情显示辣度、份量、食材」——到句号/分号为止
_DETAIL_SHOW_RE = re.compile(r"详情显示([^。；;\n]{2,80})")

_OPENING_PHRASES = (
    "详情显示多个属性字段",
    "多个属性字段",
    "菜品详情",
    "场次详情",
    "影片详情",
    "商品详情属性",
)

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
        "多个属性字段",
        "属性字段",
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
    "辣度": "spicyLevel",
    "份量": "portionSize",
    "食材": "ingredients",
    "导演": "director",
    "主演": "castNames",
    "时长": "durationMin",
    "面积": "areaSqm",
    "租金": "rentYuan",
    "朝向": "facing",
}


def _collect_from_blob(blob: str) -> list[str]:
    labels: list[str] = []
    for match in _DETAIL_RE.finditer(blob or ""):
        for part in re.split(r"[、,，]", match.group(1)):
            label = part.strip().strip("等")
            if not label or label in _SKIP_LABELS or label in labels:
                continue
            if len(label) > 16:
                continue
            labels.append(label)
    for match in _DETAIL_SHOW_RE.finditer(blob or ""):
        chunk = match.group(1).strip()
        # 「详情显示多个属性字段」整句不当属性名
        if any(phrase in chunk for phrase in ("多个属性", "属性字段")) and "、" not in chunk:
            continue
        for part in re.split(r"[、,，]", chunk):
            label = part.strip().strip("等")
            if not label or label in _SKIP_LABELS or label in labels:
                continue
            if len(label) > 16:
                continue
            labels.append(label)
    return labels[:12]


def parse_detail_labels(text: str) -> list[str]:
    return _collect_from_blob(text or "")


def scan_detail_attrs_opening(text: str, title: str = "") -> bool:
    """有具名属性，或开题点名详情属性话术。"""
    blob = f"{title or ''}\n{text or ''}"
    if parse_detail_labels(blob):
        return True
    return any(keyword_mentioned(blob, kw, ignore_contrast=True) for kw in _OPENING_PHRASES)


def _field_type(label: str) -> str:
    if "时间" in label or "日期" in label:
        return "date"
    if label in ("重量", "时长", "份量"):
        return "number"
    # 房源等：面积/租金按数值录入（含「建筑面积」「月租金」等写法）
    if any(k in label for k in ("面积", "租金")):
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


def detail_attr_column_name(key: str) -> str:
    """API camelCase → SQL snake_case（portionSize→portion_size）。"""
    raw = (key or "").strip()
    if not raw or not re.match(r"^[A-Za-z][A-Za-z0-9]{0,31}$", raw):
        return ""
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw).lower()
    if not re.match(r"^[a-z][a-z0-9_]{0,47}$", snake):
        return ""
    return snake


def detail_attr_sql_ddl(field_type: str | None) -> str:
    """schema type → 列类型：文本 VARCHAR、数值 DECIMAL、日期 DATE。"""
    t = (field_type or "string").strip().lower()
    if t == "date":
        return "DATE NULL"
    if t == "number":
        return "DECIMAL(10,2) NULL"
    return "VARCHAR(80) DEFAULT ''"


def detail_attr_sql_columns(
    fields: list[dict[str, str]] | list[str] | None,
) -> list[tuple[str, str]]:
    """开题字段 → 真列 DDL；工厂侧仍用 key 列表收集，出包按语义落列。"""
    cols: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in fields or []:
        if isinstance(item, dict):
            key = str(item.get("key") or "")
            ftype = str(item.get("type") or "string")
        else:
            key = str(item)
            ftype = "string"
        col = detail_attr_column_name(key)
        if not col or col in seen:
            continue
        seen.add(col)
        cols.append((col, detail_attr_sql_ddl(ftype)))
    return cols


def merge_detail_attrs_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    out = list(caps or [])
    if DETAIL_ATTRS_CAP in out:
        return out
    if (domain or "") not in (_TRADE_DOMAINS | _EXTRA_DETAIL_DOMAINS):
        return out
    if "archive" not in out:
        return out
    if not scan_detail_attrs_opening(proposal_text or ""):
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
    # 仅开题话术、无可加字段：仍保留岛（detailAttrKeys 可空），不拆掉
    if added:
        archive["fields"] = existing + added
        schema["detailAttrKeys"] = [field["key"] for field in added]
    else:
        schema.setdefault("detailAttrKeys", [])
    features = list(spec.get("features") or [])
    names = {f.get("name") for f in features if isinstance(f, dict)}
    if "商品详情属性" not in names:
        features.append({"name": "商品详情属性", "status": "module"})
    spec["features"] = features
    spec["schema"] = schema
    return spec
