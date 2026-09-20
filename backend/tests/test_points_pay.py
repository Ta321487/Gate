"""积分三态：兑换 / 抵扣 / 赠分；登录涨分；过期；会员档按积分。"""

from __future__ import annotations

from pathlib import Path

from app.bake.domain_schema import attach_accept
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.features.loyalty import (
    checkin_points,
    enrich_member_tiers,
    enrich_points_modes,
    expire_rule,
    points_pay_mode,
)


ROOT = Path(__file__).resolve().parents[2]
LOYALTY_JAVA = (
    ROOT
    / "skeletons/baseline/backend/src/main/java/com/thesis/capability/LoyaltyStore.java"
).read_text(encoding="utf-8")
BINDER_JAVA = (
    ROOT
    / "skeletons/baseline/backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java"
).read_text(encoding="utf-8")
AUTH_JAVA = (
    ROOT
    / "skeletons/baseline/backend/src/main/java/com/thesis/controller/AuthController.java"
).read_text(encoding="utf-8")
ORDER_JAVA = (
    ROOT
    / "skeletons/baseline/backend/src/main/java/com/thesis/controller/OrderController.java"
).read_text(encoding="utf-8")
CTRL_JAVA = (
    ROOT
    / "skeletons/baseline/backend/src/main/java/com/thesis/controller/LoyaltyController.java"
).read_text(encoding="utf-8")


def _spec(title: str, body: str, *, caps: list[str] | None = None) -> dict:
    return attach_accept(
        {"domain": "DOM-SHOP", "title": title, "capabilities": caps or []},
        body,
    )


def test_points_pay_mode_detection() -> None:
    assert points_pay_mode("积分兑换商城", "文创") == "pay"
    assert points_pay_mode("下单可用积分抵扣一部分货款", "商城") == "offset"
    assert points_pay_mode("购物完成后赠送积分", "商城") == "earn"


def test_checkin_and_expire_rules() -> None:
    assert checkin_points("每日登录送积分", "会员") == 10
    assert checkin_points("登录送 20 分", "会员") == 20
    assert checkin_points("仅下单赠分", "商城") is None
    assert expire_rule("积分年底清零", "") == ("year", "all")
    assert expire_rule("清本月获得的积分", "") == ("month", "period_earn")


def test_pay_mode_yml_and_runtime_hooks() -> None:
    title = "积分兑换商城"
    body = "用户用积分兑换商品，另支持每日登录送积分，积分年底清零。管理员可为会员充积分。"
    spec = _spec(title, body)
    assert "points" in (spec.get("capabilities") or [])
    pts = ((spec.get("schema") or {}).get("loyalty") or {}).get("points") or {}
    assert pts.get("payEnabled") is True
    assert pts.get("checkInEnabled") is True
    assert pts.get("expireEnabled") is True

    yml = _patch_thesis_yml("thesis:\n  domain: DOM-SHOP\n", "DOM-SHOP", spec)
    assert "points-enabled: true" in yml
    assert "points-pay-enabled: true" in yml
    assert "points-checkin-enabled: true" in yml
    assert "points-expire-enabled: true" in yml

    assert "configurePointsModes" in BINDER_JAVA
    assert "checkInOnLogin" in AUTH_JAVA
    assert "beginOffset" in ORDER_JAVA
    assert "credit-points" in CTRL_JAVA
    assert "adminCreditPoints" in LOYALTY_JAVA
    assert "pointsPayEnabled" in LOYALTY_JAVA


def test_offset_mode_opens_cap() -> None:
    body = "购物车结算可用积分抵扣，100 积分抵 1 元。"
    spec = _spec("日用商城", body)
    assert "points" in (spec.get("capabilities") or [])
    pts = ((spec.get("schema") or {}).get("loyalty") or {}).get("points") or {}
    assert pts.get("offsetEnabled") is True
    assert pts.get("payEnabled") is not True


def test_member_tier_points_basis() -> None:
    loyalty = {
        "memberTiers": {"enabled": True, "tiers": []},
        "points": {"enabled": True},
    }
    out = enrich_member_tiers(
        loyalty,
        "累计积分升级会员等级，青铜白银黄金",
        title="积分会员商城",
        domain="DOM-SHOP",
        points_on=True,
    )
    mt = out.get("memberTiers") or {}
    assert mt.get("basis") == "points"
    assert len(mt.get("tiers") or []) >= 3


def test_plain_shop_no_pay_offset() -> None:
    modes = enrich_points_modes(
        {"points": {"enabled": True, "earnPerYuan": 1}},
        "下单后发货",
        title="百货",
    )
    pts = modes.get("points") or {}
    assert pts.get("payEnabled") is False
    assert pts.get("offsetEnabled") is False
    assert pts.get("checkInEnabled") is False
