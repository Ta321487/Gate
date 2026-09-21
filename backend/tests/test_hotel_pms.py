"""酒店 PMS 三岛：扫词挂载 / 民宿与客房预约不挂 / 表预算（选题必需表不计入硬顶）。"""

from __future__ import annotations

from pathlib import Path

from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import assert_table_budget, count_create_tables, domain_sql
from app.bake.features.front_desk import FRONT_DESK_CAP
from app.bake.features.housekeeping_cap import HOUSEKEEPING_CAP
from app.bake.features.room_board import ROOM_BOARD_CAP
from app.bake.schema.er import schema_model


ROOT = Path(__file__).resolve().parents[2]


def _spec(domain: str, title: str, body: str) -> dict:
    return attach_accept(
        {"domain": domain, "title": title, "capabilities": []},
        body,
    )


def _admin_keys(spec: dict) -> list[str]:
    return [m.get("key") for m in (spec["schema"].get("menus") or {}).get("admin") or []]


def test_room_booking_title_keeps_pms_off() -> None:
    title = "客房预约系统"
    body = "选择房型与入住时段预订，前台办理入住离店。"
    hit = match_text(f"{title}\n{body}", title)
    assert hit.domain == "DOM-HOTEL"
    spec = _spec("DOM-HOTEL", title, body)
    caps = set(spec.get("capabilities") or [])
    assert ROOM_BOARD_CAP not in caps
    assert FRONT_DESK_CAP not in caps
    assert HOUSEKEEPING_CAP not in caps
    sql = domain_sql("DOM-HOTEL", "t_hotel", title=title, proposal_text=body)
    assert "room_instance" not in sql
    assert "CREATE TABLE IF NOT EXISTS checkin" not in sql
    assert count_create_tables(sql) <= 15
    assert_table_budget(sql, "DOM-HOTEL", caps=list(caps))
    model = schema_model(sql)
    tables = {t.get("name") for t in (model.get("tables") or [])}
    assert "room_instance" not in tables


def test_hotel_management_umbrella_opens_three() -> None:
    title = "酒店管理系统"
    body = "房态图、前台登记、退房结算、客房保洁与消费挂账。"
    hit = match_text(f"{title}\n{body}", title)
    assert hit.domain == "DOM-HOTEL"
    spec = _spec("DOM-HOTEL", title, body)
    caps = set(spec.get("capabilities") or [])
    assert {ROOM_BOARD_CAP, FRONT_DESK_CAP, HOUSEKEEPING_CAP} <= caps
    keys = _admin_keys(spec)
    assert "room_board" in keys
    assert "front_checkin" in keys
    assert "front_checkout" in keys
    assert "clean_tasks" in keys
    sql = domain_sql(
        "DOM-HOTEL",
        "t_pms",
        title=title,
        proposal_text=body,
        capabilities=list(caps),
    )
    assert "room_instance" in sql
    assert "room_status_log" in sql
    assert "CREATE TABLE IF NOT EXISTS checkin" in sql
    assert "CREATE TABLE IF NOT EXISTS checkout" in sql
    assert "CREATE TABLE IF NOT EXISTS consumption" in sql
    n = count_create_tables(sql)
    assert n <= 20
    assert_table_budget(sql, "DOM-HOTEL", caps=list(caps))
    er = schema_model(sql)
    tables = {t.get("name") for t in (er.get("tables") or [])}
    assert "room_instance" in tables
    assert "checkin" in tables
    room = next(t for t in er["tables"] if t["name"] == "room_instance")
    assert room.get("label") == "房间实例"
    posts = (spec["schema"].get("roles") or {}).get("staff_posts") or []
    hk = [p for p in posts if p.get("id") == "housekeeping"]
    assert hk, "伞扫应挂清洁岗"
    assert "room_clean_work" in (hk[0].get("packs") or [])


def test_homestay_keeps_pms_off() -> None:
    title = "民宿预订系统"
    body = "乡村民宿客房预订，选择房型入住。"
    hit = match_text(f"{title}\n{body}", title)
    assert hit.domain == "DOM-HOTEL"
    spec = _spec("DOM-HOTEL", title, body)
    caps = set(spec.get("capabilities") or [])
    assert ROOM_BOARD_CAP not in caps
    assert FRONT_DESK_CAP not in caps
    assert HOUSEKEEPING_CAP not in caps
    sql = domain_sql("DOM-HOTEL", "t_home", title=title, proposal_text=body)
    assert "room_instance" not in sql


def test_room_board_only() -> None:
    title = "宾馆客房预约"
    body = "管理端提供房态图，按空房与维修房着色。"
    spec = _spec("DOM-HOTEL", title, body)
    caps = set(spec.get("capabilities") or [])
    assert ROOM_BOARD_CAP in caps
    assert FRONT_DESK_CAP not in caps
    assert HOUSEKEEPING_CAP not in caps
    assert "room_board" in _admin_keys(spec)
    assert "front_checkin" not in _admin_keys(spec)


def test_front_desk_pulls_room_board() -> None:
    title = "宾馆客房预约"
    body = "前台登记入住，收取押金，退房结算与消费挂账。"
    spec = _spec("DOM-HOTEL", title, body)
    caps = set(spec.get("capabilities") or [])
    assert FRONT_DESK_CAP in caps
    assert ROOM_BOARD_CAP in caps
    assert "front_checkin" in _admin_keys(spec)
    assert "front_checkout" in _admin_keys(spec)


def test_housekeeping_pulls_room_board() -> None:
    title = "宾馆客房预约"
    body = "客房保洁每日跟进，清洁任务列表。"
    spec = _spec("DOM-HOTEL", title, body)
    caps = set(spec.get("capabilities") or [])
    assert HOUSEKEEPING_CAP in caps
    assert ROOM_BOARD_CAP in caps
    assert "clean_tasks" in _admin_keys(spec)


def test_gym_cleaner_does_not_open_hotel_pms() -> None:
    title = "健身房私教预约系统"
    body = "会员约私教，清洁工负责场馆打扫。"
    hit = match_text(f"{title}\n{body}", title)
    assert hit.domain == "DOM-SALON"
    spec = _spec("DOM-SALON", title, body)
    caps = set(spec.get("capabilities") or [])
    assert ROOM_BOARD_CAP not in caps
    assert FRONT_DESK_CAP not in caps
    assert HOUSEKEEPING_CAP not in caps
    from app.bake.features.venue_clean import VENUE_CLEAN_CAP

    assert VENUE_CLEAN_CAP not in caps
    sql = domain_sql("DOM-SALON", "t_salon", title=title, proposal_text=body)
    assert "room_instance" not in sql


def test_bare_cleaner_word_not_enough_on_hotel() -> None:
    title = "宾馆客房预约"
    body = "系统支持清洁工登录。"
    spec = _spec("DOM-HOTEL", title, body)
    caps = set(spec.get("capabilities") or [])
    assert HOUSEKEEPING_CAP not in caps


def test_baseline_pms_files_exist() -> None:
    be = ROOT / "skeletons/baseline/backend/src/main/java/com/thesis"
    fe = ROOT / "skeletons/baseline/frontend/src"
    assert (be / "capability/RoomBoardStore.java").is_file()
    assert (be / "capability/FrontDeskStore.java").is_file()
    assert (be / "controller/HotelPmsController.java").is_file()
    assert (fe / "views/admin/RoomBoardAdmin.vue").is_file()
    assert (fe / "views/admin/FrontCheckinAdmin.vue").is_file()
    assert (fe / "views/admin/FrontCheckoutAdmin.vue").is_file()
    assert (fe / "views/admin/CleanTasksAdmin.vue").is_file()
    assert (fe / "views/staff/StaffClean.vue").is_file()
    ctrl = (be / "controller/HotelPmsController.java").read_text(encoding="utf-8")
    assert "forbidCleanerWriteFront" in ctrl
    assert "FORBIDDEN" in ctrl
