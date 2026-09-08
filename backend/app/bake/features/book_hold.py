"""图书预约 book_hold：开题扫词才挂；无域默认。

在借/无库存可预约；还书后到书站内信；限时来借，超时取消下一顺位。
≠ 报名候补 waitlist（E-02）；勿混词表。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

BOOK_HOLD_CAP = "book_hold"

_TERMS = (
    "图书预约",
    "预约借阅",
    "到书通知",
    "借阅预约",
    "图书预订",
)

_BOOK_HOLD_DOMAINS = frozenset({"DOM-LIBRARY"})


def scan_book_hold(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _TERMS)


def merge_book_hold_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    """图书预约：开题写到 + LIBRARY + ticket_flow + quota；只增不减。"""
    out = list(caps or [])
    if BOOK_HOLD_CAP in out:
        return out
    if "ticket_flow" not in out or "quota" not in out:
        return out
    if (domain or "") not in _BOOK_HOLD_DOMAINS:
        return out
    if not scan_book_hold(proposal_text or ""):
        return out
    out.append(BOOK_HOLD_CAP)
    return out


def attach_book_hold_schema(schema: dict[str, Any]) -> None:
    ents = schema.setdefault("entities", {})
    ticket = ents.get("ticket")
    if not isinstance(ticket, dict):
        ticket = {}
        ents["ticket"] = ticket
    ticket["allowBookHold"] = True
    try:
        hours = int(ticket.get("holdHours") or 48)
    except (TypeError, ValueError):
        hours = 48
    ticket["holdHours"] = max(1, min(168, hours))

    states = ticket.get("states")
    if isinstance(states, dict):
        ordered: dict[str, str] = {}
        for k, v in states.items():
            ordered[k] = v
            if k == "pending":
                if "held" not in states:
                    ordered["held"] = "预约中"
                if "hold_ready" not in states:
                    ordered["hold_ready"] = "待取书"
        if "held" not in ordered:
            ordered["held"] = "预约中"
        if "hold_ready" not in ordered:
            ordered["hold_ready"] = "待取书"
        ticket["states"] = ordered

    labels = schema.setdefault("labels", {})
    labels.setdefault("bookHoldVerb", "预约")
    labels.setdefault("bookHoldOkMessage", "暂无库存，已加入预约队列")
    labels.setdefault("bookHoldReadyMessage", "图书已到，请在时限内确认借阅")
    labels.setdefault("bookHoldClaimVerb", "确认借阅")
    labels.setdefault("bookHoldClaimOkMessage", "已确认借阅")
    labels.setdefault("bookHoldExpireHint", "请在截止前确认借阅，逾期自动取消并顺延下一位")

    verbs = schema.setdefault("verbs", {})
    verbs.setdefault("bookHold", labels.get("bookHoldVerb") or "预约")
    verbs.setdefault("claimHold", labels.get("bookHoldClaimVerb") or "确认借阅")


def apply_book_hold_to_spec(
    spec: dict[str, Any], proposal_text: str = ""
) -> dict[str, Any]:
    text = proposal_text or ""
    caps = merge_book_hold_capabilities(
        list(spec.get("capabilities") or []),
        text,
        domain=spec.get("domain"),
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if BOOK_HOLD_CAP in caps:
        attach_book_hold_schema(schema)
        from app.bake.gate_contracts import merge_book_hold_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_book_hold_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "图书预约" not in names and scan_book_hold(text):
            features.append({"name": "图书预约", "status": "module"})
        spec["features"] = features
    spec["schema"] = schema
    return spec
