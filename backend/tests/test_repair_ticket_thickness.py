"""报修三域：催办域默认 + 高频扫词可命中。"""

from __future__ import annotations

from pathlib import Path

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.features.guestbook import GUESTBOOK_CAP, scan_guestbook
from app.bake.features.proposal_caps import merge_proposal_capabilities
from app.bake.features.staff_roster import STAFF_ROSTER_CAP, scan_staff_roster
from app.bake.proposal_role_modules import resolve_role_modules
from app.bake.staff_posts import staff_posts_for_domain

_SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples" / "域开题样例近五年"


def _sample(name: str) -> str:
    return (_SAMPLES / name).read_text(encoding="utf-8")


def test_sample_dorm_scans_islands() -> None:
    text = _sample("11-DOM-DORM-学生宿舍报修管理系统.txt")
    assert scan_guestbook(text)
    assert scan_staff_roster(text)
    posts = {p["id"] for p in staff_posts_for_domain("DOM-DORM", proposal_text=text)}
    assert "repairer" in posts
    caps = merge_proposal_capabilities(
        list(DOMAIN_CAPABILITIES["DOM-DORM"]), text, domain="DOM-DORM"
    )
    assert "deadline" in caps
    assert GUESTBOOK_CAP in caps
    assert STAFF_ROSTER_CAP in caps


def test_sample_property_scans_islands() -> None:
    text = _sample("12-DOM-PROPERTY-智慧社区物业报修管理系统.txt")
    assert scan_guestbook(text)
    assert scan_staff_roster(text)
    posts = {p["id"] for p in staff_posts_for_domain("DOM-PROPERTY", proposal_text=text)}
    assert "repairer" in posts
    caps = merge_proposal_capabilities(
        list(DOMAIN_CAPABILITIES["DOM-PROPERTY"]), text, domain="DOM-PROPERTY"
    )
    assert "deadline" in caps
    assert GUESTBOOK_CAP in caps
    assert STAFF_ROSTER_CAP in caps


def test_sample_it_scans_islands() -> None:
    text = _sample("13-DOM-IT-校园网故障报修与 IT 运维工单系统.txt")
    assert scan_guestbook(text)
    assert scan_staff_roster(text)
    posts = {p["id"] for p in staff_posts_for_domain("DOM-IT", proposal_text=text)}
    assert "field_tech" in posts
    caps = merge_proposal_capabilities(
        list(DOMAIN_CAPABILITIES["DOM-IT"]), text, domain="DOM-IT"
    )
    assert "deadline" in caps
    assert GUESTBOOK_CAP in caps
    assert STAFF_ROSTER_CAP in caps


def test_guestbook_synonyms() -> None:
    assert scan_guestbook("提供意见反馈与在线留言入口。")
    assert scan_guestbook("用户可提交用户反馈。")


def test_roster_synonyms() -> None:
    assert scan_staff_roster("维护维修值班与轮班表。")
    assert scan_staff_roster("运维排班管理。")


def test_repair_tree_trims_when_caps_known() -> None:
    pack = {
        "anchor_domain": "DOM-DORM",
        "user_role": "学生",
        "admin_role": "宿管",
        "capabilities": ["ticket_flow", "deadline", "content", "org_users"],
        "has_worker": False,
    }
    blob = "".join(
        f"{n}{d}"
        for r in resolve_role_modules(pack)
        for n, d in (r.get("modules") or [])
    )
    assert "催办" in blob or "超时" in blob
    assert "留言" not in blob
    assert "排班" not in blob
    titles = [str(r.get("title") or "") for r in resolve_role_modules(pack)]
    assert not any("维修" in t for t in titles)


def test_attach_accept_sample_dorm_full() -> None:
    text = _sample("11-DOM-DORM-学生宿舍报修管理系统.txt")
    spec = attach_accept(
        {
            "domain": "DOM-DORM",
            "title": "学生宿舍报修管理系统",
            "capabilities": list(DOMAIN_CAPABILITIES["DOM-DORM"]),
            "features": [],
        },
        text,
    )
    caps = set(spec.get("capabilities") or [])
    assert "deadline" in caps
    assert GUESTBOOK_CAP in caps
    assert STAFF_ROSTER_CAP in caps
    ticket = ((spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
    assert ticket.get("slaDeadline") is True
