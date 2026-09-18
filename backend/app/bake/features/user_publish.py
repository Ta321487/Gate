"""内容壳用户投稿/上传：archive.userPublish 扫词开（非独立 cap）。

默认即时上架，管理员 soft-delete 下架。
开题写「投稿审核 / 先审后发」等才改路径：待审后公开展示，驳回不进目录。
仅 DOM-BLOG / MEDIA；MUSIC 须点名「用户上传」才开。论坛发帖默认已开 userPublish。
≠ guestbook ≠ item_comment。
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
    "投稿入口",
    "我要投稿",
    "用户发文",
    "读者发布",
    "用户发布文章",
    "读者发布文章",
    "自行发布",
    "上传视频",
    "上传片源",
    "用户上传视频",
)

_MUSIC_UPLOAD_TERMS = (
    "用户上传",
    "听众上传",
    "用户投稿",
    "上传曲目",
    "上传歌曲",
    "上传音乐",
    "上传音频",
    "传歌",
    "听众传歌",
)

# 先审后发：只认明确说法。裸「审核 / 内容审核 / 管理员审核」会撞 OA 与论坛回帖，不在此列。
_PUBLISH_REVIEW_TERMS = (
    "投稿审核",
    "投稿需审核",
    "上传需审核",
    "先审后发",
    "先审后上架",
    "审核后上架",
    "审核后发布",
    "审核后展示",
    "审核通过后上架",
    "审核通过后发布",
    "审核通过后展示",
    "审核通过后可见",
    "审核通过后公开",
    "审核通过方可上架",
    "审核通过方可发布",
    "审核通过方可展示",
    "发布需审核",
    "发布前审核",
    "发布前须审核",
    "发帖需审核",
    "发帖审核",
    "帖子审核",
    "主帖审核",
    "发文审核",
    "稿件审核",
    "上架前审核",
    "预审后发布",
    "待审后展示",
    "人工审核后发布",
    "人工审核后上架",
    "管理员审核后发布",
    "管理员审核后上架",
    "审核后方可展示",
    "审核后方可上架",
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


def scan_publish_review(text: str) -> bool:
    """开题是否要求投稿/发帖先审后发。未写则保持即时上架。"""
    raw = text or ""
    return any(
        keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _PUBLISH_REVIEW_TERMS
    )


def _apply_publish_review_copy(schema: dict[str, Any], arch: dict[str, Any]) -> dict[str, Any]:
    noun = str(arch.get("label") or "内容").strip() or "内容"
    labels = dict(schema.get("labels") or {})
    labels["publishTip"] = (
        f"提交后进入待审核，通过后才公开展示；驳回或下架可在「我的{noun}」查看。"
    )
    labels["publishSubmitLabel"] = "提交审核"
    labels["myArchivePageLead"] = (
        f"本人提交的{noun}须管理员审核通过后公开展示；驳回或下架仍可在此查看状态。"
    )
    seeds = dict(schema.get("seeds") or {})
    notice = str(seeds.get("noticeBody") or "")
    swapped = notice.replace(
        "用户投稿即时可见，违规由管理员下架。",
        "用户投稿须审核通过后公开展示；未通过由管理员驳回。",
    )
    if swapped != notice:
        seeds["noticeBody"] = swapped
    return {**schema, "labels": labels, "seeds": seeds}


def apply_user_publish_gate_to_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """schema 已带 userPublish 时，补 my-archive 路由与 publish API 门禁。

    开题点名先审后发时写 archive.publishReview（不新开能力、不加列）。
    """
    schema = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
    entities = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}
    arch = dict(entities.get("archive") or {})
    if not arch.get("userPublish"):
        return spec
    blob = f"{spec.get('title') or ''}\n{spec.get('proposal_text') or ''}"
    if scan_publish_review(blob):
        arch["publishReview"] = True
        schema = _apply_publish_review_copy(
            {**schema, "entities": {**entities, "archive": arch}},
            arch,
        )
        spec = {**spec, "schema": schema}
    domain = str(spec.get("domain") or "").upper()
    feature = "用户发帖" if domain == "DOM-FORUM" else "用户投稿"
    from app.bake.gate_contracts import merge_user_publish_gate

    gate = dict(spec.get("gate") or {})
    spec = {**spec, "gate": merge_user_publish_gate(gate, enabled=True, publish_feature=feature)}
    return spec
