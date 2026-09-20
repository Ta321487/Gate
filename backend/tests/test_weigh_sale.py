"""按重量：商城开，日用百货和生鲜皮不开。

2.3 斤按单价相乘。次日达不能选今天。赔付不超过上限并记入余额。
"""

from __future__ import annotations

from decimal import Decimal

from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import domain_sql
from app.bake.features.weigh_sale import WEIGH_SALE_CAP, line_yuan


def _spec(domain: str, title: str, body: str) -> dict:
    return attach_accept(
        {"domain": domain, "title": title, "capabilities": []},
        body,
    )


def test_weigh_price_next_day_and_payout() -> None:
    title = "生鲜按重量商城"
    body = "商品按重量销售，标价元/斤。支持次日达。到货损耗可申请赔付。"
    spec = _spec("DOM-SHOP", title, body)
    assert WEIGH_SALE_CAP in (spec.get("capabilities") or [])
    assert "delivery_window" in (spec.get("capabilities") or [])
    schema = spec["schema"]
    fields = (schema.get("entities") or {}).get("archive", {}).get("fields") or []
    assert any(f.get("key") == "sellByWeight" and f.get("type") == "switch" for f in fields)
    unit = next(f for f in fields if f.get("key") == "weightUnit")
    assert unit.get("type") == "select"
    assert unit.get("options") == ["斤", "公斤"]
    admin = [m.get("key") for m in (schema.get("menus") or {}).get("admin") or []]
    assert "loss_claims" in admin
    assert "delivery_slots" in admin
    sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=body)
    assert "weight_qty" in sql
    assert "sell_by_weight" in sql
    assert "next_day" in sql
    assert "20.00" in sql
    assert line_yuan(10, Decimal("2.3")) == Decimal("23.00")
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    for rel in (
        "skeletons/baseline/backend/src/main/java/com/thesis/capability/WeighSaleStore.java",
        "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/WeighSaleStore.java",
        "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/mapper/WeighSaleMapper.java",
    ):
        src = (root / rel).read_text(encoding="utf-8")
        assert "balance_yuan" in src
    for rel in (
        "skeletons/baseline/backend/src/main/java/com/thesis/capability/WeighSaleStore.java",
        "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/WeighSaleStore.java",
        "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/WeighSaleStore.java",
    ):
        src = (root / rel).read_text(encoding="utf-8")
        assert "unit.multiply(weight)" in src
        assert "ask.min(cap)" in src
    for rel in (
        "skeletons/baseline/backend/src/main/java/com/thesis/capability/DeliveryWindowStore.java",
        "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/DeliveryWindowStore.java",
        "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/DeliveryWindowStore.java",
    ):
        src = (root / rel).read_text(encoding="utf-8")
        assert "次日达只能选明天" in src


def test_plain_shop_and_fresh_skin_stay_off() -> None:
    plain = domain_sql("DOM-SHOP", "t", title="日用百货商城", proposal_text="购物车下单。")
    assert "weight_qty" not in plain
    assert "loss_policy" not in plain

    fresh = domain_sql("DOM-SHOP", "t", title="社区生鲜商城", proposal_text="果蔬分类浏览后下单。")
    assert "weight_qty" not in fresh
    assert "loss_policy" not in fresh
