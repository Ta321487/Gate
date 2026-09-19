"""DOM-LOST 失物加厚：认领凭证 + 路人线索两表默认挂上。"""

from __future__ import annotations

from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import domain_sql
from app.bake.features.lostfound import CLAIM_PROOF_CAP, LOST_CLUE_CAP


def test_lostfound_caps_and_sql_tables():
    spec = attach_accept(
        {"domain": "DOM-LOST", "title": "校园失物招领管理系统", "capabilities": []},
        "失物招领启事登记与认领审核。",
    )
    caps = set(spec.get("capabilities") or [])
    assert CLAIM_PROOF_CAP in caps
    assert LOST_CLUE_CAP in caps
    ticket = (spec.get("schema") or {}).get("entities", {}).get("ticket") or {}
    assert ticket.get("requireClaimProof") is True
    assert "verifying" in (ticket.get("states") or {})

    sql = domain_sql(
        domain="DOM-LOST",
        db_name="thesis_lost",
        title="校园失物招领管理系统",
        proposal_text="失物招领启事登记与认领审核。",
    )
    assert "CREATE TABLE IF NOT EXISTS lost_claim_proof" in sql
    assert "CREATE TABLE IF NOT EXISTS lost_message" in sql
    # 游客列可空
    assert "user_id VARCHAR(64) NULL" in sql
    assert "guest_name VARCHAR(64) NULL" in sql


def test_lostfound_not_leaked_to_activity():
    spec = attach_accept(
        {"domain": "DOM-ACTIVITY", "title": "社团活动报名系统", "capabilities": []},
        "社团活动报名与签到。",
    )
    caps = set(spec.get("capabilities") or [])
    assert CLAIM_PROOF_CAP not in caps
    assert LOST_CLUE_CAP not in caps
    sql = domain_sql(
        domain="DOM-ACTIVITY",
        db_name="thesis_act",
        title="社团活动报名系统",
        proposal_text="社团活动报名与签到。",
    )
    assert "lost_claim_proof" not in sql
    assert "lost_message" not in sql
