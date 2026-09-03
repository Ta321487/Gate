"""封面校验（校徽存储见 deck_io）。"""

from __future__ import annotations

from typing import Any

from .themes import cover_complete, empty_cover


def normalize_cover(raw: dict[str, Any] | None) -> dict[str, Any]:
    out = empty_cover()
    if isinstance(raw, dict):
        for k in out:
            if k in raw:
                out[k] = raw[k]
    return out


def require_cover_complete(cover: dict[str, Any] | None) -> dict[str, Any]:
    c = normalize_cover(cover)
    if not cover_complete(c):
        raise ValueError("封面信息未齐（含校徽）")
    return c
