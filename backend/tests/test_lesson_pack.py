"""课时包：私教预约开，美发、时间银行、选课不开。

约课扣 1 节。未开始前取消退回。只写私教预约不加表。
"""

from __future__ import annotations

from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import count_create_tables, domain_sql
from app.bake.features.lesson_pack import LESSON_PACK_CAP


def _spec(domain: str, title: str, body: str) -> dict:
    return attach_accept(
        {"domain": domain, "title": title, "capabilities": []},
        body,
    )


def test_lesson_pack_on_coach() -> None:
    title = "健身房私教课时包"
    body = "购买课时包后约课消课，会员能看剩余课时。"
    hit = match_text(f"{title}\n{body}", title)
    assert hit.domain == "DOM-SALON"
    spec = _spec("DOM-SALON", title, body)
    assert LESSON_PACK_CAP in (spec.get("capabilities") or [])
    admin = [m.get("key") for m in (spec["schema"].get("menus") or {}).get("admin") or []]
    user = [m.get("key") for m in (spec["schema"].get("menus") or {}).get("user") or []]
    assert "lesson_packs" in admin
    assert "lesson_uses" in user or "lesson_uses" in admin
    assert "my_lessons" in user
    sql = domain_sql("DOM-SALON", "t", title=title, proposal_text=body)
    assert count_create_tables(sql) <= 15
    assert "CREATE TABLE IF NOT EXISTS lesson_pack" in sql
    assert "CREATE TABLE IF NOT EXISTS lesson_wallet" in sql
    assert "4, 3, '2026-12-31'" in sql
    assert "'user', 1, 0, 0" in sql
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    for rel in (
        "skeletons/baseline/backend/src/main/java/com/thesis/capability/LessonStore.java",
        "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/LessonStore.java",
        "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/LessonStore.java",
    ):
        src = (root / rel).read_text(encoding="utf-8")
        assert "剩余课时不足" in src
    for rel in (
        "skeletons/baseline/backend/src/main/java/com/thesis/capability/SlotStore.java",
        "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/SlotStore.java",
        "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/SlotStore.java",
    ):
        src = (root / rel).read_text(encoding="utf-8")
        assert "LessonStore.assertRemain" in src
        assert "LessonStore.spend" in src
        assert "LessonStore.refund" in src
        assert "if (!isPastSlot(m)) LessonStore.refund" in src


def test_hair_timebank_course_stay_off() -> None:
    hair = domain_sql("DOM-SALON", "t", title="美发造型预约", proposal_text="到店剪发烫染。")
    assert "CREATE TABLE IF NOT EXISTS lesson_pack" not in hair
    coach = domain_sql("DOM-SALON", "t", title="健身房私教预约", proposal_text="选择教练和时段。")
    assert "CREATE TABLE IF NOT EXISTS lesson_pack" not in coach
    bank = domain_sql("DOM-TIMEBANK", "t", title="社区时间银行", proposal_text="志愿时长存取核销。")
    assert "CREATE TABLE IF NOT EXISTS lesson_pack" not in bank
    assert match_text("社区时间银行\n志愿时长存取核销。", "社区时间银行").domain == "DOM-TIMEBANK"
    course = domain_sql("DOM-COURSE", "t", title="学生选课系统", proposal_text="选课与学分名额。")
    assert "CREATE TABLE IF NOT EXISTS lesson_pack" not in course
    assert match_text("学生选课系统\n选课与学分名额。", "学生选课系统").domain == "DOM-COURSE"
