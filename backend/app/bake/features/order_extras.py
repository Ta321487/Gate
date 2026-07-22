"""订单壳增强：评价（扫词）；超时关单（扫词 → yml 分钟数，默认 30）。"""

from __future__ import annotations

import re
from typing import Any

ORDER_REVIEW_CAP = "order_review"

_REVIEW_SIGNALS = re.compile(
    r"订单评价|商品评价|评价功能|评价管理|售后评价|完成评价|星级评价|评论功能"
)
_TIMEOUT_SIGNALS = re.compile(
    r"超时取消|支付超时|自动取消订单|未支付取消|订单超时|超时关单"
)


def scan_order_review(text: str) -> bool:
    return bool(_REVIEW_SIGNALS.search(text or ""))


def scan_order_timeout(text: str) -> bool:
    return bool(_TIMEOUT_SIGNALS.search(text or ""))


def merge_order_extras_capabilities(caps: list[str], proposal_text: str = "") -> list[str]:
    out = list(caps or [])
    if "order_lines" not in out:
        return [c for c in out if c != ORDER_REVIEW_CAP]
    if scan_order_review(proposal_text) and ORDER_REVIEW_CAP not in out:
        out.append(ORDER_REVIEW_CAP)
    return out


def order_timeout_minutes(proposal_text: str = "", caps: list[str] | None = None) -> int:
    """材料写超时关单 → 30 分钟；否则 0（关）。"""
    caps = list(caps or [])
    if "order_lines" not in caps:
        return 0
    if scan_order_timeout(proposal_text):
        return 30
    return 0


def attach_order_extras_schema(schema: dict[str, Any], caps: list[str], *, timeout_minutes: int = 0) -> None:
    caps = list(caps or [])
    labels = schema.setdefault("labels", {})
    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
    admin = menus.setdefault("admin", [])

    if timeout_minutes > 0:
        schema["orderTimeoutMinutes"] = int(timeout_minutes)
        labels.setdefault("orderTimeoutHint", f"待确认订单超过 {timeout_minutes} 分钟将自动取消")

    if ORDER_REVIEW_CAP not in caps:
        return

    def ensure(menus_list: list, key: str, item: dict, before: str | None = None) -> None:
        if any(m.get("key") == key for m in menus_list):
            return
        if before:
            for i, m in enumerate(menus_list):
                if m.get("key") == before:
                    menus_list.insert(i, item)
                    return
        menus_list.append(item)

    ensure(user, "order_reviews", {"key": "order_reviews", "label": "我的评价"}, before="my_orders")
    ensure(admin, "order_reviews", {"key": "order_reviews", "label": "评价管理"}, before="orders")
    labels.setdefault("orderReviewPageTitle", "我的评价")
    labels.setdefault("orderReviewPageLead", "对已完成订单进行星级与文字评价。")
    ents = schema.setdefault("entities", {})
    ents.setdefault(
        "orderReview",
        {"key": "order_review", "label": "评价", "labelPlural": "评价"},
    )


def apply_order_extras_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    caps = merge_order_extras_capabilities(list(spec.get("capabilities") or []), proposal_text)
    timeout = order_timeout_minutes(proposal_text, caps)
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    attach_order_extras_schema(schema, caps, timeout_minutes=timeout)
    # 券 / 评价 / 超时关单 gate 只在此处合并（loyalty 不再二次 merge）
    if ORDER_REVIEW_CAP in caps or timeout > 0 or "coupon" in caps:
        from app.bake.gate_contracts import merge_order_extras_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_order_extras_gate(gate, caps, timeout_minutes=timeout)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if ORDER_REVIEW_CAP in caps and "订单评价" not in names:
            features.append({"name": "订单评价", "status": "module"})
        if timeout > 0 and "订单超时自动取消" not in names:
            features.append({"name": "订单超时自动取消", "status": "module"})
        spec["features"] = features
    spec["schema"] = schema
    return spec