"""论文图 SVG 共用小工具：转义 / 一位小数 / 读缓存 JSON / 中西文估宽。

各 *schema 图模块原先各写一套 ``_esc`` / ``_f`` / ``_read_json``；收成一处，避免漂移。
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def svg_esc(s: str) -> str:
    """属性/文本节点转义（双引号也转）。"""
    return html.escape(str(s or ""), quote=True)


def fmt1(v: float) -> str:
    return f"{float(v):.1f}"


def read_json_dict(path: Path, *, missing: dict | None = None) -> dict[str, Any] | None:
    """读 JSON 对象。

    - ``missing=None``（默认）：文件缺失/坏 → ``None``（架构/类图/序列）
    - ``missing={}``：文件缺失/坏 → 空 dict（用例/模块/测例）
    """
    default: dict[str, Any] | None = missing
    if not path.is_file():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return data if isinstance(data, dict) else default


def text_w_cjk(s: str, px: float = 12.0) -> float:
    """粗估中西文混排宽度（模块图 / ER 同口径）。"""
    w = 0.0
    for ch in s or "":
        w += px if ord(ch) > 127 else px * 0.55
    return w
