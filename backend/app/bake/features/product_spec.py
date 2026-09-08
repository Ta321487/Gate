"""商品规格说明 product_spec：开题扫词才挂；无域默认。

档案「规格」文案字段（复用/对齐 spec_note）；详情展示；下单明细标题可带规格快照。
不做色×码矩阵、每规格独立库存（完整 SKU = 不支持，且不挂本 cap 冒充）。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

PRODUCT_SPEC_CAP = "product_spec"

_SPEC_DOMAINS = frozenset({"DOM-SHOP", "DOM-FOOD"})
_TERMS = ("规格参数", "商品规格", "产地规格", "规格说明", "规格")
# 完整 SKU 矩阵话术：不挂本 cap（避免冒充）
_MATRIX_BLOCKS = (
    "多规格库存",
    "多规格SKU",
    "多规格 SKU",
    "SKU矩阵",
    "SKU 矩阵",
    "色×码",
    "色码矩阵",
    "每规格独立库存",
    "独立规格库存",
)


def scan_product_spec_matrix_block(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _MATRIX_BLOCKS)


def scan_product_spec(text: str) -> bool:
    raw = text or ""
    if scan_product_spec_matrix_block(raw):
        return False
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _TERMS)


def merge_product_spec_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    out = list(caps or [])
    if PRODUCT_SPEC_CAP in out:
        return out
    if (domain or "") not in _SPEC_DOMAINS:
        return out
    # 仅订单壳域：无 order_lines 不挂
    if "order_lines" not in out:
        return out
    if not scan_product_spec(proposal_text or ""):
        return out
    out.append(PRODUCT_SPEC_CAP)
    return out


def attach_product_spec_fields(schema: dict[str, Any], *, domain: str | None = None) -> None:
    """挂规格字段：isbn 已是「规格」则复用；否则加 specNote（对齐 spec_note 列）。"""
    ents = schema.setdefault("entities", {})
    archive = ents.setdefault("archive", {})
    if not isinstance(archive, dict):
        return
    fields = list(archive.get("fields") or [])
    isbn_f = next((f for f in fields if isinstance(f, dict) and f.get("key") == "isbn"), None)
    isbn_lab = str((isbn_f or {}).get("label") or "")
    dom = domain or ""

    if "规格" in isbn_lab:
        source = "isbn"
    elif dom == "DOM-FOOD" and isbn_f is not None:
        isbn_f["label"] = "规格"
        source = "isbn"
    else:
        keys = {f.get("key") for f in fields if isinstance(f, dict)}
        if "specNote" not in keys:
            # 插在 isbn 后，便于管理端表单顺序
            at = next(
                (i + 1 for i, f in enumerate(fields) if isinstance(f, dict) and f.get("key") == "isbn"),
                len(fields),
            )
            fields.insert(at, {"key": "specNote", "label": "规格", "type": "string"})
        source = "specNote"

    archive["fields"] = fields
    archive["productSpecEnabled"] = True
    archive["productSpecSource"] = source
    labels = schema.setdefault("labels", {})
    labels.setdefault("productSpecLabel", "规格")
    labels.setdefault(
        "productSpecHint",
        "填写规格说明（如净含量、产地规格）；下单明细标题可带该文案。不支持色码矩阵与每规格独立库存。",
    )


def apply_product_spec_to_spec(
    spec: dict[str, Any], proposal_text: str = ""
) -> dict[str, Any]:
    text = proposal_text or ""
    caps = merge_product_spec_capabilities(
        list(spec.get("capabilities") or []),
        text,
        domain=spec.get("domain"),
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if PRODUCT_SPEC_CAP in caps:
        attach_product_spec_fields(schema, domain=spec.get("domain"))
        from app.bake.gate_contracts import merge_product_spec_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_product_spec_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "商品规格说明" not in names:
            features.append({"name": "商品规格说明", "status": "module"})
        spec["features"] = features
    spec["schema"] = schema
    return spec
