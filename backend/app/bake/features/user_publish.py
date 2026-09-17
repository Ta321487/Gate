"""内容壳用户投稿/上传：archive.userPublish 扫词开（非独立 cap）。

与论坛发帖同路径：即时上架，管理员 soft-delete 下架。
仅 DOM-BLOG / MEDIA；MUSIC 须点名「用户上传」才开。≠ guestbook ≠ item_comment。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

_BLOG_MEDIA_TERMS = (
    "用户投稿",
    "读者投稿",
    "投稿发布",
    "投稿审核",
    "上传投稿",
    "用户上传",
    "用户发布",
    "公开投稿",
    "在线投稿",
    "投稿功能",
)

_MUSIC_UPLOAD_TERMS = (
    "用户上传",
    "听众上传",
    "用户投稿",
    "上传曲目",
    "上传歌曲",
)


def scan_user_publish(text: str, *, domain: str | None = None) -> bool:
    raw = text or ""
    d = (domain or "").strip().upper()
    if d == "DOM-MUSIC":
        return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _MUSIC_UPLOAD_TERMS)
    if d in ("DOM-BLOG", "DOM-MEDIA") or not d:
        if any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _BLOG_MEDIA_TERMS):
            return True
        # 裸「投稿」：博客/影音常见；MUSIC 不认裸投稿（易与征稿公告混淆）
        if d != "DOM-MUSIC" and keyword_mentioned(raw, "投稿", ignore_contrast=True):
            return True
    return False


def apply_user_publish_gate_to_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """schema 已带 userPublish 时，补 my-archive 路由与 publish API 门禁。"""
    schema = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
    arch = (schema.get("entities") or {}).get("archive") or {}
    if not arch.get("userPublish"):
        return spec
    domain = str(spec.get("domain") or "").upper()
    feature = "用户发帖" if domain == "DOM-FORUM" else "用户投稿"
    from app.bake.gate_contracts import merge_user_publish_gate

    gate = dict(spec.get("gate") or {})
    spec = {**spec, "gate": merge_user_publish_gate(gate, enabled=True, publish_feature=feature)}
    return spec
