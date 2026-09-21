"""人工拖过的 E-R 图：按当前表结构指纹存整张 SVG。

指纹对得上才在打开时盖过自动排版。网格不在这张 SVG 里。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.bake.schema.diagram_cache import param_key, source_fingerprint

_DIR = Path("islands") / "er_view"
_MAX_SVG = 1_500_000
_SVG_RE = re.compile(r"<svg\b", re.I)


def view_params(mode: str, entity: str | None) -> dict[str, str]:
    mode_n = "part" if (mode or "").strip().lower() == "part" else "total"
    ent = (entity or "").strip() if mode_n == "part" else ""
    return {"mode": mode_n, "entity": ent}


def _path(workspace: Path, mode: str, entity: str | None) -> Path:
    return Path(workspace) / _DIR / f"{param_key(view_params(mode, entity))}.json"


def load_user_svg(workspace: Path, mode: str, entity: str | None) -> str | None:
    """指纹一致才返回用户 SVG，否则当没存过。"""
    path = _path(workspace, mode, entity)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("fingerprint") != source_fingerprint(workspace, "er"):
        return None
    svg = data.get("svg")
    if not isinstance(svg, str) or not _SVG_RE.search(svg):
        return None
    if "<script" in svg.lower():
        return None
    return svg


def save_user_svg(workspace: Path, mode: str, entity: str | None, svg: str) -> dict[str, Any]:
    text = (svg or "").strip()
    if len(text) > _MAX_SVG or not _SVG_RE.search(text) or "<script" in text.lower():
        raise ValueError("不是可保存的 E-R 图")
    path = _path(workspace, mode, entity)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "fingerprint": source_fingerprint(workspace, "er"),
        "svg": text,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "bytes": len(text)}


def clear_user_svg(workspace: Path, mode: str, entity: str | None) -> bool:
    path = _path(workspace, mode, entity)
    if not path.is_file():
        return False
    path.unlink()
    return True
