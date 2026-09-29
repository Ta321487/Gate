"""图书丢失申报 book_lost：LIBRARY 域默认。

借出中/逾期可申报丢失 → lost；馆员登记赔偿完成 → compensated。
库存不回补（书已不在架）；≠ 逾期罚款登记；≠ 租车验损。
"""

from __future__ import annotations

from typing import Any

BOOK_LOST_CAP = "book_lost"

_BOOK_LOST_DOMAINS = frozenset({"DOM-LIBRARY"})


def merge_book_lost_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    """丢失赔偿：LIBRARY 域默认；只增不减。"""
    del proposal_text
    out = list(caps or [])
    if BOOK_LOST_CAP in out:
        return out
    if "ticket_flow" not in out:
        return out
    if (domain or "") not in _BOOK_LOST_DOMAINS:
        return out
    out.append(BOOK_LOST_CAP)
    return out


def attach_book_lost_schema(schema: dict[str, Any]) -> None:
    ents = schema.setdefault("entities", {})
    ticket = ents.get("ticket")
    if not isinstance(ticket, dict):
        ticket = {}
        ents["ticket"] = ticket
    ticket["allowBookLost"] = True

    states = ticket.get("states")
    if isinstance(states, dict):
        ordered: dict[str, str] = {}
        for k, v in states.items():
            ordered[k] = v
            if k == "overdue":
                if "lost" not in states:
                    ordered["lost"] = "丢失申报"
                if "compensated" not in states:
                    ordered["compensated"] = "赔偿完成"
        if "lost" not in ordered:
            ordered["lost"] = "丢失申报"
        if "compensated" not in ordered:
            ordered["compensated"] = "赔偿完成"
        ticket["states"] = ordered

    labels = schema.setdefault("labels", {})
    labels.setdefault("bookLostVerb", "申报丢失")
    labels.setdefault("bookLostOkMessage", "已登记丢失申报，请按馆规办理赔偿")
    labels.setdefault("bookCompensateVerb", "登记赔偿完成")
    labels.setdefault("bookCompensateOkMessage", "赔偿已登记完成")

    verbs = ticket.setdefault("verbs", {}) if isinstance(ticket, dict) else {}
    if isinstance(verbs, dict):
        verbs.setdefault("reportLost", labels.get("bookLostVerb") or "申报丢失")
        verbs.setdefault("compensate", labels.get("bookCompensateVerb") or "登记赔偿完成")


def apply_book_lost_to_spec(
    spec: dict[str, Any], proposal_text: str = ""
) -> dict[str, Any]:
    caps = merge_book_lost_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=spec.get("domain"),
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if BOOK_LOST_CAP in caps:
        attach_book_lost_schema(schema)
        from app.bake.gate_contracts import merge_book_lost_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_book_lost_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "丢失申报与赔偿" not in names:
            features.append({"name": "丢失申报与赔偿", "status": "flow"})
        spec["features"] = features
    spec["schema"] = schema
    return spec
