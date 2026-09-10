"""图书荐购 book_suggest：开题扫词才挂；无域默认。

读者提交荐购单（书名/ISBN/理由）→ 管理审核通过/驳回；通过记台账，不自动建档入库。
≠ DOM-PROCURE 期刊遴选（题名含期刊遴选仍走 PROCURE）。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

BOOK_SUGGEST_CAP = "book_suggest"

_TERMS = ("图书荐购", "读者荐购", "推荐购书", "图书推荐购买", "荐购")
_SUGGEST_DOMAINS = frozenset({"DOM-LIBRARY"})


def scan_book_suggest(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _TERMS)


def merge_book_suggest_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    out = list(caps or [])
    if BOOK_SUGGEST_CAP in out:
        return out
    if (domain or "") not in _SUGGEST_DOMAINS:
        return out
    if not scan_book_suggest(proposal_text or ""):
        return out
    out.append(BOOK_SUGGEST_CAP)
    return out


def attach_book_suggest_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
    admin = menus.setdefault("admin", [])
    ensure_menu(
        user,
        "book_suggest",
        {"key": "book_suggest", "label": "图书荐购"},
        before_key="my_tickets",
    )
    ensure_menu(
        admin,
        "book_suggest",
        {"key": "book_suggest", "label": "荐购审核", "superOnly": False},
        before_key="ticket_pending",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("bookSuggestPageTitle", "图书荐购")
    labels.setdefault(
        "bookSuggestPageLead",
        "填写拟购书目与理由提交荐购；管理员审核通过后记入台账（不自动建档入库）。",
    )
    labels.setdefault("bookSuggestAdminTitle", "荐购审核")
    labels.setdefault(
        "bookSuggestAdminLead",
        "审核读者荐购申请：通过记台账，驳回须填写说明。",
    )
    labels.setdefault("bookSuggestOkMessage", "荐购已提交，请等待审核")
    ents = schema.setdefault("entities", {})
    ents.setdefault(
        "bookSuggest",
        {"key": "book_suggest", "label": "荐购单", "labelPlural": "荐购单"},
    )


def apply_book_suggest_to_spec(
    spec: dict[str, Any], proposal_text: str = ""
) -> dict[str, Any]:
    text = proposal_text or ""
    caps = merge_book_suggest_capabilities(
        list(spec.get("capabilities") or []),
        text,
        domain=spec.get("domain"),
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if BOOK_SUGGEST_CAP in caps:
        attach_book_suggest_menus(schema)
        from app.bake.gate_contracts import merge_book_suggest_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_book_suggest_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "图书荐购" not in names:
            features.append({"name": "图书荐购", "status": "module"})
        spec["features"] = features
    spec["schema"] = schema
    return spec
