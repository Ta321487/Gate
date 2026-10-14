"""数字商品：电子书商城开，普通日用商城不开。"""

from __future__ import annotations

from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import domain_sql
from app.bake.features.digital_goods import (
    DIGITAL_GOODS_CAP,
    ensure_digital_goods_sql,
)


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
    fields = [
        f.get("key")
        for f in ((spec["schema"].get("entities") or {}).get("archive") or {}).get("fields") or []
    ]
    assert "digitalKind" in fields
    sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=body)
    assert "CREATE TABLE IF NOT EXISTS digital_delivery" in sql
    assert "CREATE TABLE IF NOT EXISTS digital_code" in sql
    assert "DEMO-ACTIVATE-1001" in sql


def test_plain_shop_stays_physical() -> None:
    spec = _spec("DOM-SHOP", "日用百货商城", "购物车下单后发货。")
    assert DIGITAL_GOODS_CAP not in (spec.get("capabilities") or [])
    sql = domain_sql("DOM-SHOP", "t", title="日用百货商城", proposal_text="购物车下单后发货。")
    assert "CREATE TABLE IF NOT EXISTS digital_delivery" not in sql
    assert "digital_kind" not in sql
    order = (spec["schema"].get("entities") or {}).get("order") or {}
    assert order.get("fulfillMode") != "digital"
    fields = [
        f.get("key")
        for f in ((spec["schema"].get("entities") or {}).get("archive") or {}).get("fields") or []
    ]
    assert "digitalKind" not in fields


def test_agri_ecommerce_not_digital_goods() -> None:
    """「电子商务」不得误开数字码池。"""
    title = "超新农产品销售网站"
    body = (
        "当前农产品电子商务发展迅速，建设农产品电商信息系统，"
        "将水果蔬菜货架、购物车下单、订单办理与发货集中管理。"
    )
    spec = _spec("DOM-SHOP", title, body)
    assert DIGITAL_GOODS_CAP not in (spec.get("capabilities") or [])
    admin = [m.get("key") for m in (spec["schema"].get("menus") or {}).get("admin") or []]
    assert "digital_codes" not in admin
    fields = [
        f.get("key")
        for f in ((spec["schema"].get("entities") or {}).get("archive") or {}).get("fields") or []
    ]
    assert "digitalKind" not in fields
    sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=body)
    assert "CREATE TABLE IF NOT EXISTS digital_delivery" not in sql
    assert "digital_kind" not in sql
    assert "DEMO-ACTIVATE" not in sql


def test_agri_stale_cap_cleared_via_ensure_spec_schema() -> None:
    """旧 spec 粘着 digital_goods；accept 已定稿时 locked 并集也不得救回。"""
    from app.bake.domain_schema import ensure_spec_schema

    spec = ensure_spec_schema(
        {
            "domain": "DOM-SHOP",
            "title": "超新农产品销售网站",
            "accept": True,
            "capabilities": [
                "archive",
                "order_lines",
                "digital_goods",
                "content",
                "org_users",
            ],
            "proposal": {
                "summary": "农产品销售网站",
                "feature_lines": [
                    "农产品电子商务货架与购物车",
                    "订单办理与发货",
                ],
                "background": "当前农产品电子商务发展迅速。",
            },
        }
    )
    assert DIGITAL_GOODS_CAP not in (spec.get("capabilities") or [])
    archive = ((spec.get("schema") or {}).get("entities") or {}).get("archive") or {}
    fields = [f.get("key") for f in (archive.get("fields") or [])]
    assert "digitalKind" not in fields


def test_stale_digital_cap_dropped_without_opening_hit() -> None:
    """旧包粘着的 digital_goods，开题未写数字履约时必须摘掉。"""
    from app.bake.features.digital_goods import merge_digital_goods_capabilities

    caps = merge_digital_goods_capabilities(
        ["archive", "order_lines", "digital_goods", "favorites"],
        "购物车下单后发货。",
        domain="DOM-SHOP",
        title="日用百货商城",
    )
    assert DIGITAL_GOODS_CAP not in caps
    assert "order_lines" in caps


def test_strip_stale_digital_sql_when_disabled() -> None:
    dirty = """
CREATE TABLE IF NOT EXISTS product (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  digital_kind VARCHAR(16) NOT NULL DEFAULT 'code',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS digital_code (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  code_value VARCHAR(128) NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS digital_delivery (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL
);
UPDATE product SET digital_kind='code' WHERE id=1;
INSERT INTO digital_code (id, item_id, code_value, kind, enabled)
SELECT 1, 1, 'DEMO-ACTIVATE-1001', 'code', 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM digital_code WHERE id=1);
"""
    clean = ensure_digital_goods_sql(dirty, enabled=False, item_table="product")
    assert "digital_code" not in clean
    assert "digital_delivery" not in clean
    assert "digital_kind" not in clean
    assert "DEMO-ACTIVATE" not in clean
    assert "CREATE TABLE IF NOT EXISTS product" in clean
