"""交易域忠诚度能力：余额 / 积分 / 满减 / 会员成长（均为开关，默认不硬塞）。"""

from __future__ import annotations

import re
from typing import Any

LOYALTY_CAPS = ("wallet", "points", "spend_discount", "member_tier")

# 开题关键词 → 能力（仅在已有 order_lines 时附加）
_LOYALTY_SIGNALS: list[tuple[str, list[str]]] = [
    (r"余额|充值|校园卡|一卡通|电子钱包|预存", ["wallet"]),
    (r"积分(?!登录)|会员积分|签到积分|消费积分|积分兑换", ["points"]),
    (r"满减|满\s*\d+\s*减|优惠门槛|满额优惠", ["spend_discount"]),
    (r"会员等级|会员成长|成长值|银卡|金卡|会员折扣|会员价", ["member_tier"]),
]

_DEFAULT_TIERS = [
    {"id": "normal", "label": "普通", "minSpend": 0, "discountRate": 1},
    {"id": "silver", "label": "银卡", "minSpend": 200, "discountRate": 0.95},
    {"id": "gold", "label": "金卡", "minSpend": 500, "discountRate": 0.9},
]


def scan_loyalty_caps(text: str) -> list[str]:
    """从开题正文扫描忠诚度能力（去重保序）。"""
    raw = text or ""
    out: list[str] = []
    for pat, caps in _LOYALTY_SIGNALS:
        if re.search(pat, raw):
            for c in caps:
                if c not in out:
                    out.append(c)
    return out


def default_loyalty_schema(
    *,
    wallet: bool = False,
    points: bool = False,
    spend_discount: bool = False,
    member_tier: bool = False,
) -> dict[str, Any]:
    """写入 schema.loyalty；未开启的键仍给默认结构便于前端判空。"""
    loyalty: dict[str, Any] = {
        "wallet": {"enabled": bool(wallet), "label": "余额"},
        "points": {
            "enabled": bool(points),
            "label": "积分",
            "earnPerYuan": 1,
        },
        "spendDiscount": {
            "enabled": bool(spend_discount),
            "thresholdYuan": 100,
            "offYuan": 10,
        },
        "memberTiers": {
            "enabled": bool(member_tier),
            "tiers": list(_DEFAULT_TIERS),
        },
    }
    return loyalty


def merge_loyalty_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    force: list[str] | None = None,
) -> list[str]:
    """
    在已有 order_lines 时，按开题附加忠诚度能力。
    无 order_lines 则剥掉误带的忠诚度能力。
    """
    out = list(caps or [])
    has_order = "order_lines" in out
    if not has_order:
        return [c for c in out if c not in LOYALTY_CAPS]

    add = list(force or [])
    add.extend(scan_loyalty_caps(proposal_text))
    for c in add:
        if c in LOYALTY_CAPS and c not in out:
            out.append(c)
    return out


def attach_loyalty_schema(schema: dict[str, Any], caps: list[str] | None) -> dict[str, Any]:
    """按 capabilities 写入 schema.loyalty。"""
    caps = list(caps or schema.get("capabilities") or [])
    schema = dict(schema)
    schema["loyalty"] = default_loyalty_schema(
        wallet="wallet" in caps,
        points="points" in caps,
        spend_discount="spend_discount" in caps,
        member_tier="member_tier" in caps,
    )
    return schema


def apply_loyalty_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """合并能力列表并写入 schema.loyalty；同步 gate 文件（若有订单壳）。"""
    caps = list(spec.get("capabilities") or [])
    caps = merge_loyalty_capabilities(caps, proposal_text)
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    existing = schema.get("loyalty") if isinstance(schema.get("loyalty"), dict) else {}
    base = default_loyalty_schema(
        wallet="wallet" in caps,
        points="points" in caps,
        spend_discount="spend_discount" in caps,
        member_tier="member_tier" in caps,
    )
    if existing:
        for key in ("wallet", "points", "spendDiscount", "memberTiers"):
            if key in existing and isinstance(existing[key], dict) and key in base:
                merged = dict(base[key])
                for k, v in existing[key].items():
                    if k == "enabled":
                        continue
                    merged[k] = v
                merged["enabled"] = base[key].get("enabled", False)
                base[key] = merged
    schema["loyalty"] = base
    schema["capabilities"] = caps
    spec["schema"] = schema

    if any(c in caps for c in LOYALTY_CAPS):
        from app.bake.gate_contracts import merge_loyalty_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_loyalty_gate(gate, caps)

    features = list(spec.get("features") or [])
    names = {f.get("name") for f in features if isinstance(f, dict)}
    label_map = {
        "wallet": "演示余额（管理端充值）",
        "points": "积分（下单赠送，不可充值）",
        "spend_discount": "满减优惠",
        "member_tier": "会员成长等级",
    }
    for c in LOYALTY_CAPS:
        if c in caps and label_map[c] not in names:
            features.append({"name": label_map[c], "status": "module"})
    spec["features"] = features
    return spec
