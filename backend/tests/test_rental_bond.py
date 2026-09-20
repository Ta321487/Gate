"""租赁押金：租车开，普通商城和设备借用不开。"""

from __future__ import annotations

from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import domain_sql
from app.bake.features.rental_bond import RENTAL_BOND_CAP


def _spec(domain: str, title: str, body: str) -> dict:
    return attach_accept(
        {"domain": domain, "title": title, "capabilities": []},
        body,
    )


def test_carrent_bond_opens_three_amounts() -> None:
    title = "汽车租赁管理系统"
    body = "选车后支付押金和租金，还车验损后退押金。逾期另计逾期费。"
    hit = match_text(f"{title}\n{body}", title)
    assert hit.domain == "DOM-CARRENT"
    spec = _spec("DOM-CARRENT", title, body)
    assert RENTAL_BOND_CAP in (spec.get("capabilities") or [])
    admin = [m.get("key") for m in (spec["schema"].get("menus") or {}).get("admin") or []]
    assert "rental_inspect" in admin
    fields = (spec["schema"].get("entities") or {}).get("archive", {}).get("fields") or []
    keys = {f.get("key") for f in fields}
    assert "depositYuan" in keys
    assert "rentStage" in keys
    sql = domain_sql("DOM-CARRENT", "t", title=title, proposal_text=body)
    assert "deposit_yuan" in sql
    assert "rent_yuan" in sql
    assert "late_fee_yuan" in sql
    assert "deposit_status" in sql
    assert "rent_stage" in sql
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    src = (
        root / "skeletons/baseline/backend/src/main/java/com/thesis/capability/RentalBondStore.java"
    ).read_text(encoding="utf-8")
    assert "deposit_status='inspecting'" in src
    assert "refunded" in src
    assert "维修" not in src or "repair" in src


def test_shop_and_equip_borrow_stay_off() -> None:
    shop = domain_sql("DOM-SHOP", "t", title="日用百货商城", proposal_text="购物车下单。")
    assert "deposit_status" not in shop
    equip = domain_sql("DOM-EQUIP", "t", title="实验室设备借用", proposal_text="申请借用后审核归还。")
    assert "deposit_status" not in equip
    spec = _spec("DOM-EQUIP", "实验室设备借用", "申请借用后审核归还。")
    assert RENTAL_BOND_CAP not in (spec.get("capabilities") or [])


def test_clothes_skin_keeps_rental_domain() -> None:
    title = "服装租赁商城"
    body = "选服装，付押金和日租金，归还验损。"
    hit = match_text(f"{title}\n{body}", title)
    assert hit.domain == "DOM-CARRENT"
    spec = _spec("DOM-CARRENT", title, body)
    assert spec["schema"].get("rentalBondSkin") == "clothes"
