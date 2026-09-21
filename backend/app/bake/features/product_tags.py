"""商品标签 product_tags：开题写明「标签」才挂；仅 DOM-SHOP。

推广论坛 tag + 关联表模式；不靠「包邮/热门/新品」等模糊词单独开岛。
论坛域已有标签，本岛不挂、不另起第二套表。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

PRODUCT_TAGS_CAP = "product_tags"

_SHOP_DOMAINS = frozenset({"DOM-SHOP"})
# 必须点名标签；包邮/热门/新品只作种子候选词，不作挂载触发
_TAG_ANCHORS = (
    "标签",
    "商品标签",
    "多标签",
    "标签筛选",
    "标签云",
)


def scan_product_tags(text: str, title: str = "") -> bool:
    blob = f"{title or ''}\n{text or ''}"
    if not blob.strip():
        return False
    return any(keyword_mentioned(blob, kw, ignore_contrast=True) for kw in _TAG_ANCHORS)


def merge_product_tags_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if PRODUCT_TAGS_CAP in out:
        return out
    # 论坛已有标签 runtime，禁止再挂本岛
    if (domain or "") == "DOM-FORUM":
        return out
    if (domain or "") not in _SHOP_DOMAINS:
        return out
    if "archive" not in out:
        return out
    if not scan_product_tags(proposal_text or "", title):
        return out
    out.append(PRODUCT_TAGS_CAP)
    return out


def attach_product_tags_fields(schema: dict[str, Any]) -> None:
    ents = schema.setdefault("entities", {})
    archive = ents.setdefault("archive", {})
    if not isinstance(archive, dict):
        return
    archive["tagFilter"] = True
    labels = schema.setdefault("labels", {})
    labels.setdefault("tagFilterHint", "可多选标签组合筛选。")


def apply_product_tags_to_spec(
    spec: dict[str, Any], proposal_text: str = ""
) -> dict[str, Any]:
    title = str(spec.get("title") or "")
    caps = merge_product_tags_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if PRODUCT_TAGS_CAP not in caps:
        return {**spec, "schema": schema}

    attach_product_tags_fields(schema)
    runtime = dict(spec.get("runtime") or {})
    runtime.setdefault("archive_tag_table", "tag")
    runtime.setdefault("archive_item_tag_table", "product_tag")
    spec["runtime"] = runtime

    features = list(spec.get("features") or [])
    names = {f.get("name") for f in features if isinstance(f, dict)}
    if "商品标签" not in names:
        features.append({"name": "商品标签", "status": "module"})
    spec["features"] = features
    spec["schema"] = schema
    return spec
