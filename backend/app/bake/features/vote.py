"""投票评选（vote）：候选档案、一票/限票、结果公示（C-04）；ACTIVITY∩投票见 C-11。"""

from __future__ import annotations

from app.bake.sql.ddl_edit import (
    CREATE_TABLE_RE as _CREATE_TABLE_RE,
    inject_missing_columns as _inject_missing_columns,
    prune_columns as _prune_columns,
)

import re
from typing import Any

from app.bake.proposal_lexicon import pattern_mentioned

VOTE_CAP = "vote"

_VOTE_SIGNALS = re.compile(
    r"投票|评选|十佳|选票|投票评选|在线投票|候选人投票|评选投票|网络投票"
)
_SIGNUP_SIGNALS = re.compile(
    r"报名|占名额|报名审核|活动报名|志愿报名|讲座报名|赛事报名"
)


def scan_vote(text: str) -> bool:
    return pattern_mentioned(text or "", _VOTE_SIGNALS, ignore_contrast=True)


def scan_signup(text: str) -> bool:
    return pattern_mentioned(text or "", _SIGNUP_SIGNALS, ignore_contrast=True)


def scan_vote_signup_composite(text: str) -> bool:
    """C-11：开题同时写投票计票 + 报名占名额。"""
    t = text or ""
    return scan_vote(t) and scan_signup(t)


def vote_wanted(
    *,
    domain: str | None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
) -> bool:
    caps = list(capabilities or [])
    if VOTE_CAP in caps:
        return True
    if (domain or "") == "DOM-VOTE":
        return True
    # C-11：活动报名域开题写到投票 → 挂 vote
    if (domain or "") == "DOM-ACTIVITY" and scan_vote(proposal_text):
        return True
    return scan_vote(proposal_text)


def merge_vote_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
    force: bool = False,
) -> list[str]:
    out = list(caps or [])
    want = force or vote_wanted(
        domain=domain,
        capabilities=out,
        proposal_text=proposal_text,
    )
    if want and VOTE_CAP not in out:
        out.append(VOTE_CAP)
    return out


def attach_vote_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    user = menus.setdefault("user", [])
    ensure_menu(
        admin,
        "vote_candidates",
        {"key": "vote_candidates", "label": "候选人管理", "superOnly": True},
        before_key="content",
    )
    ensure_menu(
        admin,
        "vote_results",
        {"key": "vote_results", "label": "计票公示", "superOnly": True},
        before_key="content",
    )
    ensure_menu(
        user,
        "vote_campaigns",
        {"key": "vote_campaigns", "label": "参与投票"},
        before_key="content",
    )
    ensure_menu(
        user,
        "vote_mine",
        {"key": "vote_mine", "label": "我的选票"},
        before_key="content",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("voteCampaignsTitle", "参与投票")
    labels.setdefault(
        "voteCampaignsLead",
        "选择开放中的评选活动，按限票数投给候选人；可查看结果公示。",
    )
    labels.setdefault("voteMineTitle", "我的选票")
    ents = schema.setdefault("entities", {})
    if "vote" not in ents:
        ents["vote"] = {"key": "vote", "label": "评选", "labelPlural": "评选"}


def apply_vote_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain")
    caps = merge_vote_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if VOTE_CAP in caps:
        attach_vote_menus(schema)
        from app.bake.gate_contracts import merge_vote_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_vote_gate(gate, caps)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "投票与计票" not in names:
            features.append({"name": "投票与计票", "status": "flow"})
        spec["features"] = features

        ents = list(spec.get("entities") or [])
        if "Vote" not in ents:
            if "Notice" in ents:
                ents.insert(ents.index("Notice"), "Vote")
            else:
                ents.append("Vote")
            spec["entities"] = ents

        if (domain or "") == "DOM-ACTIVITY" and scan_vote_signup_composite(
            proposal_text
        ):
            labels = schema.setdefault("labels", {})
            labels.setdefault(
                "voteCampaignsLead",
                "活动报名之外的评选投票：按限票数投给候选人，可查看结果公示。",
            )

    spec["schema"] = schema
    return spec


# --- SQL ensure (moved from fragments.py) ---

_VOTE_CORE_DDL = """
CREATE TABLE IF NOT EXISTS vote_campaign (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(256),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vote_candidate (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  campaign_id BIGINT NOT NULL,
  name VARCHAR(128) NOT NULL,
  intro VARCHAR(1000) DEFAULT '',
  sort_no INT NOT NULL DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  avatar_url VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_vote_cand_camp (campaign_id)
);

CREATE TABLE IF NOT EXISTS vote_ballot (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  campaign_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  candidate_id BIGINT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_vote_user_cand (campaign_id, username, candidate_id),
  KEY idx_vote_ball_user (campaign_id, username)
);
"""

_VOTE_ACTIVITY_SEED = """
INSERT IGNORE INTO vote_campaign (id, title, author, isbn, category_id, stock, status) VALUES
(1, '活动优秀个人评选', '主办方', '每人限投 1 票；与活动报名并行', 1, 1, 'available');
INSERT IGNORE INTO vote_candidate (id, campaign_id, name, intro, sort_no, status) VALUES
(1, 1, '候选人甲', '活动积极分子', 1, 'available'),
(2, 1, '候选人乙', '志愿服务突出', 2, 'available'),
(3, 1, '候选人丙', '组织协调得力', 3, 'available');
"""

VOTE_CANDIDATE_COLUMNS: list[tuple[str, str]] = [
    ("avatar_url", "VARCHAR(255) DEFAULT ''"),
]

def ensure_vote_sql(sql: str, *, enabled: bool, seed_activity: bool = False) -> str:
    """vote 能力开启时幂等补评选表；表已存在时仍补 avatar_url（DOM-VOTE 模板曾漏列）。"""
    if not enabled:
        return sql
    out = sql
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?vote_ballot`?\b", out):
        out = out.rstrip() + "\n" + _VOTE_CORE_DDL

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "vote_candidate":
            return m.group(0)
        body = _inject_missing_columns(body, VOTE_CANDIDATE_COLUMNS)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, out)
    if seed_activity and "活动优秀个人评选" not in out:
        out = out.rstrip() + "\n" + _VOTE_ACTIVITY_SEED
    return out
