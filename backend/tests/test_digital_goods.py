"""数字商品：电子书商城开，普通日用商城不开。"""

from __future__ import annotations

from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import domain_sql
from app.bake.features.digital_goods import DIGITAL_GOODS_CAP


def _spec(domain: str, title: str, body: str) -> dict:
    return attach_accept(
        {"domain": domain, "title": title, "capabilities": []},
        body,
    )


def test_ebook_shop_skips_ship_and_blocks_casual_refund() -> None:
    title = "电子书素材商城"
    body = "付款后发放激活码或下载链接，数字商品不支持无理由退款，无物流。"
    spec = _spec("DOM-SHOP", title, body)
    assert DIGITAL_GOODS_CAP in (spec.get("capabilities") or [])
    order = (spec["schema"].get("entities") or {}).get("order") or {}
    assert order.get("fulfillMode") == "digital"
    assert "shipped" not in (order.get("states") or {})
    assert spec["schema"].get("noCasualRefund") is True
    user = [m.get("key") for m in (spec["schema"].get("menus") or {}).get("user") or []]
    admin = [m.get("key") for m in (spec["schema"].get("menus") or {}).get("admin") or []]
    assert "my_digital" in user
    assert "digital_codes" in admin
    sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=body)
    assert "CREATE TABLE IF NOT EXISTS digital_delivery" in sql
    assert "CREATE TABLE IF NOT EXISTS digital_code" in sql
    assert "DEMO-ACTIVATE-1001" in sql


def test_plain_shop_stays_physical() -> None:
    spec = _spec("DOM-SHOP", "日用百货商城", "购物车下单后发货。")
    assert DIGITAL_GOODS_CAP not in (spec.get("capabilities") or [])
    sql = domain_sql("DOM-SHOP", "t", title="日用百货商城", proposal_text="购物车下单后发货。")
    assert "CREATE TABLE IF NOT EXISTS digital_delivery" not in sql
    order = (spec["schema"].get("entities") or {}).get("order") or {}
    assert order.get("fulfillMode") != "digital"
