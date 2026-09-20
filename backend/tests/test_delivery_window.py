"""配送时段：鲜花/当日达开，普通商城、宾馆、会议室不开。"""

from __future__ import annotations

import re

from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import domain_sql
from app.bake.features.delivery_window import DELIVERY_WINDOW_CAP


def _spec(domain: str, title: str, body: str) -> dict:
    return attach_accept(
        {"domain": domain, "title": title, "capabilities": []},
        body,
    )


def test_flower_opening_enables_windows() -> None:
    title = "基于 Spring Boot 的鲜花预订商城"
    body = "下单选择配送日期和配送时段，支持当日达，节日涨价。"
    spec = _spec("DOM-SHOP", title, body)
    assert DELIVERY_WINDOW_CAP in (spec.get("capabilities") or [])
    schema = spec["schema"]
    assert schema.get("deliveryWindow") is True
    keys = [m.get("key") for m in (schema.get("menus") or {}).get("admin") or []]
    assert "delivery_slots" in keys
    assert "price_spans" in keys
    sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=body)
    assert "CREATE TABLE IF NOT EXISTS delivery_slot" in sql
    assert "CREATE TABLE IF NOT EXISTS price_span" in sql
    assert "delivery_on" in sql
    assert "上午档" in sql
    assert "1.50" in sql
    assert "鲜切花" in sql


def test_same_day_fresh_is_not_flower_skin() -> None:
    title = "生鲜果蔬商城"
    body = "支持当日达。"
    spec = _spec("DOM-SHOP", title, body)
    assert DELIVERY_WINDOW_CAP in (spec.get("capabilities") or [])
    sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=body)
    assert "delivery_slot" in sql
    assert "鲜切花" not in sql
    assert "康乃馨" not in sql


def test_plain_shop_and_neighbors_stay_off() -> None:
    plain = _spec("DOM-SHOP", "日用百货商城", "购物车下单。")
    assert DELIVERY_WINDOW_CAP not in (plain.get("capabilities") or [])
    sql = domain_sql("DOM-SHOP", "t", title="日用百货商城", proposal_text="购物车下单。")
    create = re.search(
        r"CREATE TABLE IF NOT EXISTS\s+biz_order\s*\((.*?)\)\s*;",
        sql,
        re.I | re.S,
    )
    assert create is not None
    assert "delivery_on" not in create.group(1)
    assert "CREATE TABLE IF NOT EXISTS delivery_slot" not in sql

    hotel = domain_sql("DOM-HOTEL", "t", title="宾馆客房预订系统", proposal_text="入住与离店。")
    assert "CREATE TABLE IF NOT EXISTS delivery_slot" not in hotel

    meeting = domain_sql("DOM-MEETING", "t", title="会议室预约系统", proposal_text="按时段预约会议室。")
    assert "CREATE TABLE IF NOT EXISTS delivery_slot" not in meeting
