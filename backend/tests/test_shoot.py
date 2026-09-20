"""约拍：服务预约开，美发、摄影欣赏、选座、点播、场地不开交片表。

同一摄影师同一时段靠现有占用拒绝。未交片不返回文件地址。
"""

from __future__ import annotations

from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import domain_sql
from app.bake.features.shoot import SHOOT_CAP


def _spec(domain: str, title: str, body: str) -> dict:
    return attach_accept(
        {"domain": domain, "title": title, "capabilities": []},
        body,
    )


def test_shoot_bundles_conflict_and_files() -> None:
    title = "校园约拍预约"
    body = "用户选择摄影师和套餐，预约时段。交片后才能查看成片。"
    hit = match_text(f"{title}\n{body}", title)
    assert hit.domain == "DOM-SALON"
    spec = _spec("DOM-SALON", title, body)
    assert SHOOT_CAP in (spec.get("capabilities") or [])
    admin = [m.get("key") for m in (spec["schema"].get("menus") or {}).get("admin") or []]
    assert "shoot_bundles" in admin
    sql = domain_sql("DOM-SALON", "t", title=title, proposal_text=body)
    assert "CREATE TABLE IF NOT EXISTS service_bundle" in sql
    assert "CREATE TABLE IF NOT EXISTS deliverable" in sql
    assert "证件照" in sql
    assert "写真" in sql
    assert "'林可'" in sql
    assert "'周宁'" in sql
    assert ", 1, 0)" in sql
    assert "该时段已约满" in (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "skeletons/baseline/backend/src/main/java/com/thesis/capability/SlotStore.java"
    ).read_text(encoding="utf-8")
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    for rel in (
        "skeletons/baseline/backend/src/main/java/com/thesis/capability/ShootStore.java",
        "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/ShootStore.java",
        "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/ShootStore.java",
    ):
        src = (root / rel).read_text(encoding="utf-8")
        assert 'put("fileUrl", "")' in src or "put(\"fileUrl\", \"\")" in src


def test_hair_appreciate_cinema_media_meeting_stay_off() -> None:
    hair = domain_sql("DOM-SALON", "t", title="校园美发预约", proposal_text="选择技师和时段到店。")
    assert "CREATE TABLE IF NOT EXISTS deliverable" not in hair

    appreciate = domain_sql("DOM-SALON", "t", title="摄影欣赏", proposal_text="浏览摄影作品。")
    assert "CREATE TABLE IF NOT EXISTS deliverable" not in appreciate

    for domain, title, body in (
        ("DOM-CINEMA", "校园影院选座", "在线选座购票。"),
        ("DOM-MEDIA", "影视点播", "在线观看影视。"),
        ("DOM-MEETING", "会议室预约", "预约场地座位时段。"),
    ):
        sql = domain_sql(domain, "t", title=title, proposal_text=body)
        assert "CREATE TABLE IF NOT EXISTS deliverable" not in sql
