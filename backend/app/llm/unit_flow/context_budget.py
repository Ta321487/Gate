"""上下文裁剪（对标 ai-ppt prepare_outline_input / prepare_slide_input）。"""

from __future__ import annotations

import re
from typing import Any

_WS = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    return _WS.sub(" ", (text or "").strip())


def clip_text(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    t = normalize_text(text)
    return t[:limit] if len(t) > limit else t


def proposal_excerpt(spec: dict[str, Any], *, limit: int = 2400) -> str:
    parts: list[str] = []
    prop = spec.get("proposal")
    if isinstance(prop, dict):
        for key in ("title", "background", "summary"):
            v = prop.get(key)
            if v:
                parts.append(str(v))
        for line in prop.get("feature_lines") or []:
            parts.append(str(line))
        ex = prop.get("excerpt")
        if ex:
            parts.append(str(ex))
    elif prop:
        parts.append(str(prop))
    return clip_text("\n".join(parts), limit)


def prepare_unit_user_payload(
    base: dict[str, Any],
    *,
    budget_chars: int,
    extra_keys: tuple[str, ...] = ("proposal_excerpt",),
) -> dict[str, Any]:
    """按单元预算裁剪 user JSON，优先保留结构化字段。"""
    out = dict(base)
    used = len(str(out))  # rough; refined below
    for key in extra_keys:
        if key not in out:
            continue
        raw = str(out.get(key) or "")
        room = max(0, budget_chars - used + len(raw))
        out[key] = clip_text(raw, min(room, budget_chars // 2))
        used = sum(len(str(v)) for v in out.values())
    return out
