"""投票评选（vote）：候选档案、一票/限票、结果公示（C-04）；ACTIVITY∩投票见 C-11。"""

from __future__ import annotations

import re
from typing import Any

VOTE_CAP = "vote"

_VOTE_SIGNALS = re.compile(
    r"投票|评选|十佳|选票|投票评选|在线投票|候选人投票|评选投票|网络投票"
)
_SIGNUP_SIGNALS = re.compile(
    r"报名|占名额|报名审核|活动报名|志愿报名|讲座报名|赛事报名"
)


def scan_vote(text: str) -> bool:
    return bool(_VOTE_SIGNALS.search(text or ""))


def scan_signup(text: str) -> bool:
    return bool(_SIGNUP_SIGNALS.search(text or ""))


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
