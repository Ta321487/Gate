"""交易域忠诚度能力：余额 / 积分 / 满减 / 会员成长 / 券码。

有 order_lines 的交易壳默认挂 wallet（有钱必有账户余额 + 模拟充值）；
其它忠诚度项仍按开题扫词附加。
"""

from __future__ import annotations

import re
from typing import Any

LOYALTY_CAPS = ("wallet", "points", "spend_discount", "member_tier", "coupon")

# 开题关键词 → 能力（仅在已有 order_lines 时附加；wallet 另见默认挂载）
_LOYALTY_SIGNALS: list[tuple[str, list[str]]] = [
    (r"余额|充值|校园卡|一卡通|电子钱包|预存|钱包", ["wallet"]),
    (r"积分(?!登录)|会员积分|签到积分|消费积分|积分兑换", ["points"]),
    (r"满减|满\s*\d+\s*减|优惠门槛|满额优惠", ["spend_discount"]),
    (r"会员等级|会员成长|成长值|银卡|金卡|会员折扣|会员价", ["member_tier"]),
    (r"优惠券|兑换码|红包码|券码|领券", ["coupon"]),
]

_DEFAULT_TIERS = [
    {"id": "normal", "label": "普通", "minSpend": 0, "discountRate": 1},
    {"id": "silver", "label": "银卡", "minSpend": 200, "discountRate": 0.95},
    {"id": "gold", "label": "金卡", "minSpend": 500, "discountRate": 0.9},
]

_DEFAULT_COUPONS = [
    {"code": "SAVE10", "label": "满50减10", "minYuan": 50, "offYuan": 10},
    {"code": "WELCOME5", "label": "满30减5", "minYuan": 30, "offYuan": 5},
]


def scan_loyalty_caps(text: str) -> list[str]:
    """从开题正文扫描忠诚度能力（去重保序）。"""
    from app.bake.proposal_lexicon import pattern_mentioned

    raw = text or ""
    out: list[str] = []
    for pat, caps in _LOYALTY_SIGNALS:
        if pattern_mentioned(raw, re.compile(pat), ignore_contrast=True):
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
    coupon: bool = False,
) -> dict[str, Any]:
    """写入 schema.loyalty；未开启的键仍给默认结构便于前端判空。"""
    return {
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
        "coupons": {
            "enabled": bool(coupon),
            "items": list(_DEFAULT_COUPONS),
        },
    }


def merge_loyalty_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    force: list[str] | None = None,
) -> list[str]:
    """
    在已有 order_lines 时：默认挂 wallet；再按开题附加其它忠诚度能力。
    无 order_lines 则剥掉误带的忠诚度能力。
    """
    out = list(caps or [])
    has_order = "order_lines" in out
    if not has_order:
        return [c for c in out if c not in LOYALTY_CAPS]

    # 有下单付钱 → 默认账户余额（模拟充值），不单靠开题扫到「钱包」才开
    if "wallet" not in out:
        out.append("wallet")

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
        coupon="coupon" in caps,
    )
    return schema


def attach_coupon_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
    admin = menus.setdefault("admin", [])
    ensure_menu(
        user,
        "coupons",
        {"key": "coupons", "label": "优惠券"},
        before_key="cart",
    )
    ensure_menu(
        admin,
        "coupons",
        {"key": "coupons", "label": "优惠券管理"},
        before_key="orders",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("couponsPageTitle", "优惠券")
    labels.setdefault("couponsPageLead", "领取可用券，下单时选用券码抵扣。")
    ents = schema.setdefault("entities", {})
    ents.setdefault("coupon", {"key": "coupon", "label": "优惠券", "labelPlural": "优惠券"})


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
        coupon="coupon" in caps,
    )
    if existing:
        for key in ("wallet", "points", "spendDiscount", "memberTiers", "coupons"):
            if key in existing and isinstance(existing[key], dict) and key in base:
                merged = dict(base[key])
                for k, v in existing[key].items():
                    if k == "enabled":
                        continue
                    merged[k] = v
                merged["enabled"] = base[key].get("enabled", False)
                base[key] = merged
    title = str(spec.get("title") or "")
    base = enrich_points_modes(base, proposal_text or "", title=title)
    if (base.get("points") or {}).get("enabled") and "points" not in caps:
        caps.append("points")
        spec = {**spec, "capabilities": caps}
    base = enrich_member_tiers(
        base,
        proposal_text or "",
        title=title,
        domain=str(spec.get("domain") or ""),
        seed=spec.get("seed"),
        points_on="points" in caps,
    )
    schema["loyalty"] = base
    schema["capabilities"] = caps
    if "coupon" in caps:
        attach_coupon_menus(schema)
    spec["schema"] = schema

    if any(c in caps for c in LOYALTY_CAPS):
        from app.bake.gate_contracts import merge_loyalty_gate

        # 券生命周期 gate 由 order_extras.merge_order_extras_gate 统一挂（attach_accept 后置）
        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_loyalty_gate(gate, caps)

    features = list(spec.get("features") or [])
    names = {f.get("name") for f in features if isinstance(f, dict)}
    label_map = {
        "wallet": "账户余额（模拟充值）",
        "points": "积分（赠分 / 兑换 / 抵扣；写到才开登录涨分与过期）",
        "spend_discount": "满减优惠",
        "member_tier": "会员成长等级",
        "coupon": "优惠券（领取·我的券·核销）",
    }
    for c in LOYALTY_CAPS:
        if c in caps and label_map[c] not in names:
            features.append({"name": label_map[c], "status": "module"})
    spec["features"] = features
    return spec


_PAY_TERMS = ("积分兑换", "积分商城", "用积分兑换")
_OFFSET_TERMS = ("积分抵扣", "积分抵现", "积分当钱花", "购物抵扣")
_CHECKIN_TERMS = ("签到积分", "每日签到", "登录送积分", "签到领积分", "登录积分", "登录送", "每日登录")
_EXPIRE_HINTS = ("积分有效期", "积分过期", "过期清零", "月底清", "年底清", "积分清零", "清本月", "清本年度")

_TIER_PACKS = (
    ("青铜", "白银", "黄金", "铂金", "钻石"),
    ("普通会员", "银卡", "金卡", "白金", "钻石", "黑卡", "至尊"),
    ("一星", "二星", "三星", "四星", "五星"),
)

_NAMED_TIERS = (
    "青铜", "白银", "黄金", "铂金", "钻石",
    "普通会员", "银卡", "金卡", "白金", "黑卡", "至尊",
    "一星", "二星", "三星", "四星", "五星",
)


def _hit_any(text: str, terms: tuple[str, ...]) -> bool:
    from app.bake.proposal_lexicon import keyword_mentioned

    return any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in terms)


def points_pay_mode(text: str, title: str = "") -> str:
    blob = f"{title or ''}\n{text or ''}"
    if _hit_any(blob, _PAY_TERMS) or "积分兑换商城" in blob:
        return "pay"
    if _hit_any(blob, _OFFSET_TERMS) or ("抵扣" in blob and "积分" in blob):
        return "offset"
    return "earn"


def checkin_points(text: str, title: str = "") -> int | None:
    import re

    blob = f"{title or ''}\n{text or ''}"
    if not _hit_any(blob, _CHECKIN_TERMS):
        return None
    m = re.search(r"(?:每天|每日|登录送|签到)\s*(\d+)\s*分", blob)
    if m:
        return max(1, int(m.group(1)))
    return 10


def expire_rule(text: str, title: str = "") -> tuple[str, str] | None:
    blob = f"{title or ''}\n{text or ''}"
    if not any(k in blob for k in _EXPIRE_HINTS):
        return None
    if any(k in blob for k in ("清本月", "本月获得", "当月积分")):
        return "month", "period_earn"
    if any(k in blob for k in ("清本年度", "本年获得")):
        return "year", "period_earn"
    if any(k in blob for k in ("月底", "月末", "每月清零")):
        return "month", "all"
    return "year", "all"


def enrich_points_modes(loyalty: dict[str, Any], text: str, *, title: str = "") -> dict[str, Any]:
    out = dict(loyalty)
    pts = dict(out.get("points") or {})
    mode = points_pay_mode(text, title)
    checkin = checkin_points(text, title)
    expire = expire_rule(text, title)
    if mode == "pay":
        pts["enabled"] = True
        pts["payEnabled"] = True
        pts["offsetEnabled"] = False
    elif mode == "offset":
        pts["enabled"] = True
        pts["payEnabled"] = False
        pts["offsetEnabled"] = True
        pts["pointsPerYuan"] = 100
        pts["offsetCapRate"] = 0.5
    else:
        pts["payEnabled"] = False
        pts["offsetEnabled"] = False
    if checkin is not None:
        pts["enabled"] = True
        pts["checkInEnabled"] = True
        pts["checkInPoints"] = checkin
    else:
        pts["checkInEnabled"] = False
        pts["checkInPoints"] = 0
    if expire is not None:
        pts["enabled"] = True
        pts["expireEnabled"] = True
        pts["expirePeriod"] = expire[0]
        pts["expireScope"] = expire[1]
    else:
        pts["expireEnabled"] = False
        pts["expirePeriod"] = ""
        pts["expireScope"] = ""
    out["points"] = pts
    return out


def enrich_member_tiers(
    loyalty: dict[str, Any],
    text: str,
    *,
    title: str,
    domain: str,
    seed: Any = None,
    points_on: bool = False,
) -> dict[str, Any]:
    out = dict(loyalty)
    block = dict(out.get("memberTiers") or {})
    if not block.get("enabled"):
        return out
    blob = f"{title}\n{text}"
    found = [name for name in _NAMED_TIERS if name in blob]
    found.sort(key=lambda n: blob.find(n))
    labels: list[str] = []
    for name in found:
        if any(name != other and name in other for other in found):
            continue
        labels.append(name)
    digest = f"{title}|{domain}|{seed}"
    pick = abs(hash(digest))
    if len(labels) < 2:
        labels = list(_TIER_PACKS[pick % len(_TIER_PACKS)])
    basis = "spend"
    if any(k in blob for k in ("积分升级", "成长值", "满一定积分", "累计积分")):
        basis = "points"
    elif points_on and "会员成长" in blob:
        basis = "points"
    if basis == "points":
        ladders = (
            (0, 100, 300, 800, 2000, 5000, 12000),
            (0, 50, 200, 600, 1500, 4000, 9000),
            (0, 80, 240, 700, 1800, 4500, 10000),
        )
        steps = ladders[pick % len(ladders)]
    else:
        base_steps = (0, 200, 500, 1200, 3000, 8000, 20000)
        factor = 1 + (pick % 3) * 0.15
        steps = tuple(0 if i == 0 else int(n * factor) for i, n in enumerate(base_steps))
    tiers = []
    for i, label in enumerate(labels):
        tiers.append(
            {
                "id": f"t{i}",
                "label": label,
                "minSpend": int(steps[min(i, len(steps) - 1)]),
                "discountRate": round(max(0.8, 1 - i * 0.02), 2),
            }
        )
    block["tiers"] = tiers
    block["basis"] = basis
    out["memberTiers"] = block
    return out
