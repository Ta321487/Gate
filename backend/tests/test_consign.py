"""寄卖：商城开，普通商城、图书馆、多商家入驻不开。

未质检的种子没有商品编号。成交账按抽成后的应得入账。
成色列仍只在校园二手皮，不从寄卖注入。
"""

from __future__ import annotations

from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import domain_sql
from app.bake.features.consign import CONSIGN_CAP


def _spec(domain: str, title: str, body: str) -> dict:
    return attach_accept(
        {"domain": domain, "title": title, "capabilities": []},
        body,
    )


def test_consign_opening_seed_and_ledger() -> None:
    title = "社区寄卖商城"
    body = "用户提交寄卖，质检上架后买家才能购买。平台抽成，寄卖人可以提现。"
    spec = _spec("DOM-SHOP", title, body)
    assert CONSIGN_CAP in (spec.get("capabilities") or [])
    schema = spec["schema"]
    assert schema.get("consign") is True
    admin = [m.get("key") for m in (schema.get("menus") or {}).get("admin") or []]
    user = [m.get("key") for m in (schema.get("menus") or {}).get("user") or []]
    assert "consigns" in admin
    assert "my_consigns" in user
    sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=body)
    assert "CREATE TABLE IF NOT EXISTS consign_item" in sql
    assert "CREATE TABLE IF NOT EXISTS consign_ledger" in sql
    assert "condition_grade" not in sql
    assert "'pending'" in sql
    pending = sql.split("SELECT 1, 'user', '耳机'", 1)[1].split(";", 1)[0]
    assert "product_id" not in pending
    assert "90.00" in sql
    assert "0.1000" in sql
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    for rel in (
        "skeletons/baseline/backend/src/main/java/com/thesis/capability/ConsignStore.java",
        "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/ConsignStore.java",
        "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/ConsignStore.java",
    ):
        src = (root / rel).read_text(encoding="utf-8")
        assert "这件还没通过质检，不能购买" in src
        assert "BigDecimal.ONE.subtract(rate)" in src


def test_plain_shop_library_and_marketplace_stay_off() -> None:
    plain = _spec("DOM-SHOP", "日用百货商城", "购物车下单。")
    assert CONSIGN_CAP not in (plain.get("capabilities") or [])
    sql = domain_sql("DOM-SHOP", "t", title="日用百货商城", proposal_text="购物车下单。")
    assert "CREATE TABLE IF NOT EXISTS consign_item" not in sql

    library = domain_sql(
        "DOM-LIBRARY",
        "t",
        title="校园图书借阅",
        proposal_text="图书寄卖与质检上架不在借阅范围内。",
    )
    assert "CREATE TABLE IF NOT EXISTS consign_item" not in library

    market = domain_sql(
        "DOM-SHOP",
        "t",
        title="多商家入驻商城",
        proposal_text="商家入驻后各自开店，买家下单。",
    )
    assert "CREATE TABLE IF NOT EXISTS consign_item" not in market
