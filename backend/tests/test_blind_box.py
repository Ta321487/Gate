"""盲盒：商城开，普通商城、活动抽奖、影院选座不开。

权重和为种子配置值。保底次数写在盒子上（种子 pity_n=3），
第 N 次必出尚未抽中的隐藏款由 BlindBoxStore.drawAll 执行，不写死在页面。
"""

from __future__ import annotations

import re

from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import domain_sql
from app.bake.features.blind_box import BLIND_BOX_CAP


def _spec(domain: str, title: str, body: str) -> dict:
    return attach_accept(
        {"domain": domain, "title": title, "capabilities": []},
        body,
    )


def test_blind_opening_weights_and_pity() -> None:
    title = "潮玩盲盒商城"
    body = "用户购买盲盒，按概率抽取，抽满保底必出隐藏款。"
    spec = _spec("DOM-SHOP", title, body)
    assert BLIND_BOX_CAP in (spec.get("capabilities") or [])
    schema = spec["schema"]
    assert schema.get("blindBox") is True
    fields = (schema.get("entities") or {}).get("archive", {}).get("fields") or []
    assert any(f.get("key") == "pityN" and f.get("type") == "number" for f in fields)
    keys = [m.get("key") for m in (schema.get("menus") or {}).get("admin") or []]
    assert "blind_pools" in keys
    sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=body)
    assert "CREATE TABLE IF NOT EXISTS blind_pool" in sql
    assert "CREATE TABLE IF NOT EXISTS blind_pity" in sql
    assert "pity_n" in sql
    assert "draw_title" in sql
    found = re.findall(r"SELECT 1, \d+, (\d+), (\d+), 1 FROM DUAL", sql)
    weights = [(int(w), int(h)) for w, h in found]
    assert weights == [(70, 0), (25, 0), (5, 1)]
    assert sum(w for w, _ in weights) == 100
    assert "pity_n=3" in sql


def test_plain_shop_activity_and_cinema_stay_off() -> None:
    plain = _spec("DOM-SHOP", "日用百货商城", "购物车下单。")
    assert BLIND_BOX_CAP not in (plain.get("capabilities") or [])
    sql = domain_sql("DOM-SHOP", "t", title="日用百货商城", proposal_text="购物车下单。")
    assert "CREATE TABLE IF NOT EXISTS blind_pool" not in sql

    activity = domain_sql(
        "DOM-ACTIVITY",
        "t",
        title="校园活动抽奖",
        proposal_text="按概率抽取隐藏款。",
    )
    assert "CREATE TABLE IF NOT EXISTS blind_pool" not in activity

    cinema = domain_sql(
        "DOM-CINEMA",
        "t",
        title="校园影院选座",
        proposal_text="在线选座购票，不涉及盲盒概率。",
    )
    assert "CREATE TABLE IF NOT EXISTS blind_pool" not in cinema
