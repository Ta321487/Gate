"""寄养：客房按天入住开，酒店、挂号、领养、宠物咖啡不开日志。

3 天是 3 倍日价。重叠日期容量满则拒绝。反馈照片用户可见。
"""

from __future__ import annotations

from decimal import Decimal

from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import count_create_tables, domain_sql
from app.bake.features.boarding import BOARDING_CAP, stay_yuan


def _spec(domain: str, title: str, body: str) -> dict:
    return attach_accept(
        {"domain": domain, "title": title, "capabilities": []},
        body,
    )


def test_boarding_price_capacity_and_photo() -> None:
    title = "宠物寄养预约"
    body = "按天寄养，选择寄养位和日期。每日反馈给主人看。"
    hit = match_text(f"{title}\n{body}", title)
    assert hit.domain == "DOM-HOTEL"
    spec = _spec("DOM-HOTEL", title, body)
    assert BOARDING_CAP in (spec.get("capabilities") or [])
    fields = (spec["schema"].get("entities") or {}).get("archive", {}).get("fields") or []
    assert any(f.get("key") == "author" and f.get("label") == "日价(元)" for f in fields)
    admin = [m.get("key") for m in (spec["schema"].get("menus") or {}).get("admin") or []]
    user = [m.get("key") for m in (spec["schema"].get("menus") or {}).get("user") or []]
    assert "care_options" in admin
    assert "stay_logs" in admin
    assert "my_stay" in user
    sql = domain_sql("DOM-HOTEL", "t", title=title, proposal_text=body)
    assert count_create_tables(sql) <= 15
    assert "CREATE TABLE IF NOT EXISTS stay_log" in sql
    assert "喂药" in sql
    assert "遛弯" in sql
    assert "/files/pet-1.jpg" in sql
    assert "小单间" in sql
    assert "240.00" in sql
    assert stay_yuan(80, 3) == Decimal("240.00")
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    for rel in (
        "skeletons/baseline/backend/src/main/java/com/thesis/capability/BoardingStore.java",
        "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/BoardingStore.java",
        "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/BoardingStore.java",
    ):
        src = (root / rel).read_text(encoding="utf-8")
        assert "这些日期已满" in src
        assert "unit.multiply(BigDecimal.valueOf(days))" in src
        assert "photoUrl" in src
    page = (
        root / "skeletons/baseline/frontend/src/views/user/MyStay.vue"
    ).read_text(encoding="utf-8")
    assert "row.photoUrl" in page


def test_hotel_clinic_adopt_cafe_stay_off() -> None:
    hotel = domain_sql("DOM-HOTEL", "t", title="宾馆客房预订系统", proposal_text="入住与离店。")
    assert "CREATE TABLE IF NOT EXISTS stay_log" not in hotel

    clinic = domain_sql("DOM-HOSPITAL", "t", title="宠物医院挂号", proposal_text="选择医生和时段挂号。")
    assert "CREATE TABLE IF NOT EXISTS stay_log" not in clinic

    adopt = domain_sql("DOM-LOST", "t", title="宠物领养", proposal_text="提交领养申请后审核。")
    assert "CREATE TABLE IF NOT EXISTS stay_log" not in adopt
    assert match_text("宠物领养\n提交领养申请", "宠物领养").domain == "DOM-LOST"

    cafe = domain_sql("DOM-SALON", "t", title="宠物咖啡", proposal_text="到店预约座位。")
    assert "CREATE TABLE IF NOT EXISTS stay_log" not in cafe
    assert match_text("宠物咖啡\n到店预约座位", "宠物咖啡").domain == "DOM-SALON"
