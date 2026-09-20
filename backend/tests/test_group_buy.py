"""拼团：商城开，普通商城、活动报名、拼车不开。"""

from __future__ import annotations

from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import domain_sql
from app.bake.features.group_buy import GROUP_BUY_CAP


def _spec(domain: str, title: str, body: str) -> dict:
    return attach_accept(
        {"domain": domain, "title": title, "capabilities": []},
        body,
    )


def test_group_opening_enables_tables() -> None:
    title = "社区团购商城"
    body = "用户可以拼团，人齐成团，未成团退款。"
    spec = _spec("DOM-SHOP", title, body)
    assert GROUP_BUY_CAP in (spec.get("capabilities") or [])
    schema = spec["schema"]
    assert schema.get("groupBuy") is True
    assert schema["entities"]["order"]["states"]["grouping"] == "待成团"
    keys = [m.get("key") for m in (schema.get("menus") or {}).get("admin") or []]
    assert "group_campaigns" in keys
    sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=body)
    assert "CREATE TABLE IF NOT EXISTS group_campaign" in sql
    assert "CREATE TABLE IF NOT EXISTS group_member" in sql
    assert "'open'" in sql
    assert "'failed'" in sql


def test_plain_shop_activity_and_carpool_stay_off() -> None:
    plain = _spec("DOM-SHOP", "日用百货商城", "购物车下单。")
    assert GROUP_BUY_CAP not in (plain.get("capabilities") or [])
    sql = domain_sql("DOM-SHOP", "t", title="日用百货商城", proposal_text="购物车下单。")
    assert "CREATE TABLE IF NOT EXISTS group_campaign" not in sql

    activity = domain_sql("DOM-ACTIVITY", "t", title="校园活动报名系统", proposal_text="学生在线报名活动。")
    assert "CREATE TABLE IF NOT EXISTS group_campaign" not in activity

    carpool = domain_sql("DOM-CARPOOL", "t", title="校园拼车系统", proposal_text="发布行程并匹配同行。")
    assert "CREATE TABLE IF NOT EXISTS group_campaign" not in carpool
