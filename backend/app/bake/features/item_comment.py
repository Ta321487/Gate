"""档案条下评论（item_comment）：挂在影音/曲目/文章详情下。

与门户留言 guestbook、论坛跟帖 ticket reply、商城 order_review 分离。
仅 DOM-MEDIA / MUSIC / BLOG；开题写「评论」等才挂（无域默认）。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

ITEM_COMMENT_CAP = "item_comment"

# 条下评论；刻意不含「留言/留言板」（guestbook）与「评价/商品评论」（order_review）
_COMMENT_TERMS = (
    "条下评论",
    "片下评论",
    "文下评论",
    "曲下评论",
    "用户评论",
    "发表评论",
    "评论功能",
    "评论区",
    "影评",
    "曲评",
    "书评",
    "评论模块",
    "评论管理",
    "详情评论",
    "下方评论",
    "底部评论",
    "视频评论",
    "文章评论",
    "观影评论",
    "读后评论",
    "在线点评",
    "互动点评",
)

_ALLOW_DOMAINS = frozenset({"DOM-MEDIA", "DOM-MUSIC", "DOM-BLOG"})


def scan_item_comment(text: str) -> bool:
    raw = text or ""
    if any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _COMMENT_TERMS):
        return True
    # 裸「评论」：排除「无需评论」「不做评论」等对比句由 lexicon 处理
    return keyword_mentioned(raw, "评论", ignore_contrast=True)


def merge_item_comment_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    force: bool = False,
) -> list[str]:
    out = list(caps or [])
    domain = (domain or "").strip().upper()
    if domain and domain not in _ALLOW_DOMAINS:
        return [c for c in out if c != ITEM_COMMENT_CAP]
    if ITEM_COMMENT_CAP in out:
        return out
    if "archive" not in out:
        return out
    want = force or scan_item_comment(proposal_text)
    if want:
        out.append(ITEM_COMMENT_CAP)
    return out


def attach_item_comment_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    ensure_menu(
        admin,
        "item_comments",
        {"key": "item_comments", "label": "评论管理", "superOnly": False},
        before_key="guestbook",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("itemCommentSectionTitle", "用户评论")
    labels.setdefault("itemCommentSubmitLabel", "发表评论")
    labels.setdefault("itemCommentEmpty", "暂无评论")
    ents = schema.setdefault("entities", {})
    if "item_comment" not in ents:
        ents["item_comment"] = {
            "key": "item_comment",
            "label": "评论",
            "labelPlural": "评论",
        }


def apply_item_comment_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain")
    caps = merge_item_comment_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if ITEM_COMMENT_CAP in caps:
        attach_item_comment_menus(schema)
        from app.bake.gate_contracts import merge_item_comment_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_item_comment_gate(gate, caps)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "条下评论" not in names:
            features.append({"name": "条下评论", "status": "module"})
        spec["features"] = features

        ents = list(spec.get("entities") or [])
        if "ItemComment" not in ents:
            if "Guestbook" in ents:
                ents.insert(ents.index("Guestbook"), "ItemComment")
            else:
                ents.append("ItemComment")
            spec["entities"] = ents

    spec["schema"] = schema
    return spec
