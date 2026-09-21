"""场馆保洁 venue_clean：窄扫 / 裸词不挂 / 不串酒店 PMS。"""

from __future__ import annotations

from pathlib import Path

from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import domain_sql
from app.bake.features.housekeeping_cap import HOUSEKEEPING_CAP
from app.bake.features.room_board import ROOM_BOARD_CAP
from app.bake.features.venue_clean import VENUE_CLEAN_CAP, scan_venue_clean
from app.bake.staff_posts import staff_posts_for_domain


ROOT = Path(__file__).resolve().parents[2]


def _spec(domain: str, title: str, body: str) -> dict:
    return attach_accept(
        {"domain": domain, "title": title, "capabilities": []},
        body,
    )


def _admin_keys(spec: dict) -> list[str]:
    return [m.get("key") for m in (spec["schema"].get("menus") or {}).get("admin") or []]


def _post_ids(spec: dict) -> list[str]:
    posts = (spec["schema"].get("roles") or {}).get("staff_posts") or []
    return [str(p.get("id") or "") for p in posts if isinstance(p, dict)]


def test_scan_positive_terms() -> None:
    assert scan_venue_clean("管理端提供保洁任务列表，打扫完成后回可用。")
    assert scan_venue_clean("会议室清洁与预约办结联动。")
    assert scan_venue_clean("", title="场馆保洁管理系统")


def test_scan_bare_cleaner_off() -> None:
    assert not scan_venue_clean("清洁工负责场馆打扫。")
    assert not scan_venue_clean("系统支持保洁员登录。")


def test_gym_bare_cleaner_no_venue_clean_no_hotel_pms() -> None:
    title = "健身房私教预约系统"
    body = "会员约私教，清洁工负责场馆打扫。"
    hit = match_text(f"{title}\n{body}", title)
    assert hit.domain == "DOM-SALON"
    spec = _spec("DOM-SALON", title, body)
    caps = set(spec.get("capabilities") or [])
    assert VENUE_CLEAN_CAP not in caps
    assert HOUSEKEEPING_CAP not in caps
    assert ROOM_BOARD_CAP not in caps
    assert "clean_tasks" not in _admin_keys(spec)
    assert "venue_cleaner" not in _post_ids(spec)
    sql = domain_sql("DOM-SALON", "t_gym", title=title, proposal_text=body)
    assert "room_instance" not in sql
    assert "clean_status" not in sql


def test_gym_full_clean_tasks_opens_venue_clean() -> None:
    title = "健身房预约系统"
    body = "会员约私教。管理端维护保洁任务：待清洁场地列表，打扫完成后标已清洁。"
    hit = match_text(f"{title}\n{body}", title)
    assert hit.domain == "DOM-SALON"
    spec = _spec("DOM-SALON", title, body)
    caps = set(spec.get("capabilities") or [])
    assert VENUE_CLEAN_CAP in caps
    assert HOUSEKEEPING_CAP not in caps
    assert ROOM_BOARD_CAP not in caps
    assert "clean_tasks" in _admin_keys(spec)
    assert "venue_cleaner" in _post_ids(spec)
    posts = (spec["schema"].get("roles") or {}).get("staff_posts") or []
    vc = next(p for p in posts if p.get("id") == "venue_cleaner")
    assert "venue_clean_work" in (vc.get("packs") or [])
    sql = domain_sql(
        "DOM-SALON",
        "t_gym2",
        title=title,
        proposal_text=body,
        capabilities=list(caps),
    )
    assert "clean_status" in sql
    assert "room_instance" not in sql


def test_meeting_clean_opens() -> None:
    title = "会议室预约系统"
    body = "会议室冲突预约。提供会议室清洁任务：用毕标待清洁，保洁完成回已清洁。"
    spec = _spec("DOM-MEETING", title, body)
    caps = set(spec.get("capabilities") or [])
    assert VENUE_CLEAN_CAP in caps
    assert "clean_tasks" in _admin_keys(spec)
    assert "venue_cleaner" in _post_ids(spec)


def test_property_clean_opens() -> None:
    title = "物业报修系统"
    body = "业主报修派单。另有场馆保洁：清洁管理任务列表。"
    spec = _spec("DOM-PROPERTY", title, body)
    caps = set(spec.get("capabilities") or [])
    assert VENUE_CLEAN_CAP in caps
    assert "venue_cleaner" in _post_ids(spec)


def test_hotel_never_gets_venue_clean() -> None:
    title = "酒店管理系统"
    body = "房态图、客房保洁与保洁任务、清洁管理。"
    spec = _spec("DOM-HOTEL", title, body)
    caps = set(spec.get("capabilities") or [])
    assert VENUE_CLEAN_CAP not in caps
    assert HOUSEKEEPING_CAP in caps


def test_optional_worker_bare_cleaner_off() -> None:
    ids = [
        p["id"]
        for p in staff_posts_for_domain("DOM-SALON", proposal_text="清洁工登录打扫。")
    ]
    assert "venue_cleaner" not in ids


def test_baseline_venue_clean_files_exist() -> None:
    be = ROOT / "skeletons/baseline/backend/src/main/java/com/thesis"
    fe = ROOT / "skeletons/baseline/frontend/src"
    assert (be / "capability/VenueCleanStore.java").is_file()
    assert (be / "controller/VenueCleanController.java").is_file()
    assert (fe / "views/admin/CleanTasksAdmin.vue").is_file()
    store = (be / "capability/VenueCleanStore.java").read_text(encoding="utf-8")
    assert "UPDATE" in store and "clean_status" in store
    assert "UPDATE room_instance" not in store
    assert "FROM room_instance" not in store
    vue = (fe / "views/admin/CleanTasksAdmin.vue").read_text(encoding="utf-8")
    assert "venue_clean" in vue
    assert "/api/venue-clean/" in vue
