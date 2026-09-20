"""失物招领加厚：认领凭证核验 + 路人线索。仅 DOM-LOST 域默认，不扫进邻域。

认领：待交凭证 → 提交凭证（verifying）→ 核验通过 → 审核通过。
线索：lost_message.user_id 可空，游客只填称呼，不建账号。
"""

from __future__ import annotations

import re
from typing import Any

CLAIM_PROOF_CAP = "claim_proof"
LOST_CLUE_CAP = "lost_clue"
_LOST_DOMAIN = "DOM-LOST"

_PROOF_DDL = """
CREATE TABLE IF NOT EXISTS lost_claim_proof (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  claim_id BIGINT NOT NULL,
  proof_type VARCHAR(16) NOT NULL,
  proof_content VARCHAR(500) NOT NULL,
  verify_status VARCHAR(16) NOT NULL DEFAULT 'pending',
  verifier_id VARCHAR(64) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_proof_claim (claim_id, id)
);
INSERT IGNORE INTO lost_claim_proof (id, claim_id, proof_type, proof_content, verify_status) VALUES
(1, 1, 'desc', '耳机盒内侧有划痕，与本人描述一致', 'pending');
UPDATE claim SET status='verifying' WHERE id=1 AND status='pending';
"""

_CLUE_DDL = """
CREATE TABLE IF NOT EXISTS lost_message (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  lost_item_id BIGINT NOT NULL,
  user_id VARCHAR(64) NULL,
  guest_name VARCHAR(64) NULL,
  guest_contact VARCHAR(64) NULL,
  content VARCHAR(500) NOT NULL,
  msg_type VARCHAR(16) NOT NULL DEFAULT 'clue',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_lost_msg_item (lost_item_id, id)
);
INSERT IGNORE INTO lost_message (id, lost_item_id, guest_name, content, msg_type) VALUES
(1, 1, '路过同学', '昨天在一食堂窗口见过类似物品', 'clue');
"""


def merge_lostfound_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    """只给失物招领补两张表；其它域保持原样。"""
    del proposal_text
    out = list(caps or [])
    if domain != _LOST_DOMAIN:
        return [c for c in out if c not in (CLAIM_PROOF_CAP, LOST_CLUE_CAP)]
    for cap in (CLAIM_PROOF_CAP, LOST_CLUE_CAP):
        if cap not in out:
            out.append(cap)
    return out


def ensure_lostfound_sql(
    sql: str,
    *,
    claim_proof: bool,
    lost_clue: bool,
) -> str:
    out = sql
    if claim_proof and not re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?lost_claim_proof`?\b", out
    ):
        out = out.rstrip() + "\n" + _PROOF_DDL
    if lost_clue and not re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?lost_message`?\b", out
    ):
        out = out.rstrip() + "\n" + _CLUE_DDL
    return out


def attach_lostfound_schema(schema: dict[str, Any], caps: list[str]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    cap_set = set(caps or [])
    if CLAIM_PROOF_CAP not in cap_set and LOST_CLUE_CAP not in cap_set:
        return
    ents = schema.setdefault("entities", {})
    labels = schema.setdefault("labels", {})
    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])

    if CLAIM_PROOF_CAP in cap_set:
        ticket = ents.setdefault("ticket", {})
        if isinstance(ticket, dict):
            states = ticket.setdefault("states", {})
            if isinstance(states, dict):
                states["pending"] = "待交凭证"
                states["verifying"] = "待核验"
            ticket["requireClaimProof"] = True
        ents["lost_claim_proof"] = {
            "key": "lost_claim_proof",
            "label": "认领凭证",
            "labelPlural": "认领凭证",
            "fields": [
                {"key": "claimId", "label": "认领单"},
                {"key": "proofType", "label": "凭证类型"},
                {"key": "proofContent", "label": "凭证内容"},
                {"key": "verifyStatus", "label": "核验状态"},
                {"key": "verifierId", "label": "核验人"},
            ],
        }
        lead = str(labels.get("authLead") or "")
        extra = "提交认领只填说明；进入待交凭证后补交凭证，核验通过管理员才能办结。凭证未通过退回待交凭证，可重交。"
        if extra not in lead:
            labels["authLead"] = (lead + extra).strip()

    if LOST_CLUE_CAP in cap_set:
        ents["lost_message"] = {
            "key": "lost_message",
            "label": "线索留言",
            "labelPlural": "线索留言",
            "fields": [
                {"key": "lostItemId", "label": "启事"},
                {"key": "userId", "label": "登录用户"},
                {"key": "guestName", "label": "游客称呼"},
                {"key": "guestContact", "label": "联系方式"},
                {"key": "content", "label": "内容"},
                {"key": "type", "label": "类型"},
            ],
        }
        labels.setdefault("lostCluePageTitle", "线索留言")
        labels.setdefault(
            "lostCluePageLead",
            "路人可留线索或询问，不必注册；登录用户会记到本人名下。",
        )
        ensure_menu(
            admin,
            "lost_clues",
            {"key": "lost_clues", "label": "线索留言", "superOnly": False},
            before_key="content",
        )


def apply_lostfound_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = str(spec.get("domain") or "")
    caps = merge_lostfound_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if domain == _LOST_DOMAIN:
        attach_lostfound_schema(schema, caps)
        from app.bake.gate_contracts import merge_lostfound_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_lostfound_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if CLAIM_PROOF_CAP in caps and "认领凭证核验" not in names:
            features.append({"name": "认领凭证核验", "status": "flow"})
        if LOST_CLUE_CAP in caps and "路人线索" not in names:
            features.append({"name": "路人线索", "status": "module"})
        spec["features"] = features
        ents = list(spec.get("entities") or [])
        for name in ("ClaimProof", "LostMessage"):
            if name not in ents:
                ents.append(name)
        spec["entities"] = ents
    spec["schema"] = schema
    return spec
