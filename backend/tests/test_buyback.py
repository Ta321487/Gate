"""旧书回收：商城上架开，图书借阅不开。

未上架不能加购。回收开题不是借阅域。
"""

from __future__ import annotations

from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import count_create_tables, domain_sql
from app.bake.features.buyback import BUYBACK_CAP


def _spec(domain: str, title: str, body: str) -> dict:
    return attach_accept(
        {"domain": domain, "title": title, "capabilities": []},
        body,
    )


def test_buyback_quote_and_unlist() -> None:
    title = "校园二手旧书回收"
    body = "二手教材上门回收，先估价再同意。入库后上架才能购买。"
    hit = match_text(f"{title}\n{body}", title)
    assert hit.domain == "DOM-SHOP"
    spec = _spec("DOM-SHOP", title, body)
    assert BUYBACK_CAP in (spec.get("capabilities") or [])
    admin = [m.get("key") for m in (spec["schema"].get("menus") or {}).get("admin") or []]
    user = [m.get("key") for m in (spec["schema"].get("menus") or {}).get("user") or []]
    assert "buybacks" in admin
    assert "buyback_slots" in admin
    assert "my_buybacks" in user
    sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=body)
    assert count_create_tables(sql) <= 15
    assert "CREATE TABLE IF NOT EXISTS buyback_order" in sql
    assert "CREATE TABLE IF NOT EXISTS buyback_slot" in sql
    assert "线性代数" in sql
    assert "'pending'" in sql
    assert "操作系统" in sql
    assert "'listed'" in sql
    assert "condition_grade" in sql
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    for rel in (
        "skeletons/baseline/backend/src/main/java/com/thesis/capability/BuybackStore.java",
        "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/BuybackStore.java",
        "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/BuybackStore.java",
    ):
        src = (root / rel).read_text(encoding="utf-8")
        assert "还没上架，不能购买" in src
    jdbc = (
        root / "skeletons/baseline/backend/src/main/java/com/thesis/capability/BuybackStore.java"
    ).read_text(encoding="utf-8")
    assert "condition_grade" in jdbc
    mapper = (
        root / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/mapper/BuybackMapper.java"
    ).read_text(encoding="utf-8")
    assert "condition_grade" in mapper
    order = (
        root / "skeletons/baseline/backend/src/main/java/com/thesis/capability/OrderStore.java"
    ).read_text(encoding="utf-8")
    assert "BuybackStore.assertListed" in order


def test_library_borrow_stays_off() -> None:
    sql = domain_sql("DOM-LIBRARY", "t", title="图书借阅管理系统", proposal_text="借还与逾期提醒。")
    assert "CREATE TABLE IF NOT EXISTS buyback_order" not in sql
    hit = match_text("图书借阅管理系统\n借还与逾期提醒。", "图书借阅管理系统")
    assert hit.domain == "DOM-LIBRARY"
    recycle = match_text("校园旧书回收\n上门回收并估价。", "校园旧书回收")
    assert recycle.domain != "DOM-LIBRARY"


def test_plain_shop_and_repair_stay_off() -> None:
    shop = domain_sql("DOM-SHOP", "t", title="日用百货商城", proposal_text="购物车下单。")
    assert "CREATE TABLE IF NOT EXISTS buyback_order" not in shop
    repair = match_text("上门维修预约\n家电上门维修。", "上门维修预约")
    assert repair.domain != "DOM-SHOP"
