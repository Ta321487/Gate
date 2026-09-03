"""deck.json 读写。"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from app.models import Project

from .themes import empty_cover, ensure_ppt_dirs, ppt_root


def deck_path(project: Project) -> Path | None:
    root = ppt_root(project)
    return (root / "deck.json") if root else None


def cover_path(project: Project) -> Path | None:
    root = ppt_root(project)
    return (root / "cover.json") if root else None


def skin_path(project: Project) -> Path | None:
    root = ppt_root(project)
    return (root / "skin.json") if root else None


def _atomic_write(path: Path, data: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(prefix=".deck_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read(path: Path | None) -> dict[str, Any] | None:
    if not path or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None


def load_deck(project: Project) -> dict[str, Any] | None:
    return _read(deck_path(project))


def save_deck(project: Project, deck: dict[str, Any]) -> Path:
    ensure_ppt_dirs(project)
    path = deck_path(project)
    assert path is not None
    _atomic_write(path, deck)
    return path


def load_cover(project: Project) -> dict[str, Any]:
    data = _read(cover_path(project))
    if data:
        out = empty_cover()
        out.update({k: data.get(k, out.get(k)) for k in out})
        # badge may live on disk
        root = ppt_root(project)
        if root and not out.get("badge_data_url"):
            badge = root / "badge" / "current.png"
            if badge.is_file():
                import base64

                b64 = base64.b64encode(badge.read_bytes()).decode("ascii")
                out["badge_data_url"] = f"data:image/png;base64,{b64}"
        return out
    deck = load_deck(project)
    if deck and isinstance(deck.get("cover"), dict):
        out = empty_cover()
        out.update(deck["cover"])
        return out
    return empty_cover()


def save_cover(project: Project, cover: dict[str, Any]) -> dict[str, Any]:
    ensure_ppt_dirs(project)
    out = empty_cover()
    out.update({k: cover.get(k, out.get(k)) for k in out})
    path = cover_path(project)
    assert path is not None
    # persist badge bytes when data URL present
    badge_url = out.get("badge_data_url")
    if isinstance(badge_url, str) and badge_url.startswith("data:"):
        _save_badge_data_url(project, badge_url)
    _atomic_write(path, out)
    deck = load_deck(project)
    if deck:
        deck["cover"] = dict(out)
        for page in deck.get("pages") or []:
            if isinstance(page, dict) and page.get("role") == "cover":
                page["cover"] = dict(out)
        save_deck(project, deck)
    return out


def _save_badge_data_url(project: Project, data_url: str) -> None:
    import base64
    import re

    root = ppt_root(project)
    if not root:
        return
    m = re.match(r"^data:([^;,]+)?(;base64)?,(.*)$", data_url, re.DOTALL)
    if not m:
        return
    payload = m.group(3) or ""
    try:
        raw = base64.b64decode(payload)
    except Exception:  # noqa: BLE001
        return
    badge_dir = root / "badge"
    badge_dir.mkdir(parents=True, exist_ok=True)
    original = badge_dir / "original.png"
    current = badge_dir / "current.png"
    if not original.exists():
        original.write_bytes(raw)
    current.write_bytes(raw)


def load_skin(project: Project) -> dict[str, str]:
    from .themes import seed_theme_for_project

    seed = seed_theme_for_project(project.id)
    data = _read(skin_path(project))
    if data:
        return {
            "theme": str(data.get("theme") or seed["theme"]),
            "layout_family": str(data.get("layout_family") or seed["layout_family"]),
            "master": str(data.get("master") or seed["master"]),
        }
    deck = load_deck(project)
    if deck:
        return {
            "theme": str(deck.get("theme") or seed["theme"]),
            "layout_family": str(deck.get("layout_family") or seed["layout_family"]),
            "master": str(deck.get("master") or seed["master"]),
        }
    return seed


def save_skin(project: Project, skin: dict[str, Any]) -> dict[str, str]:
    from .themes import normalize_layout, normalize_master, normalize_theme

    ensure_ppt_dirs(project)
    out = {
        "theme": normalize_theme(skin.get("theme"), project.id),
        "layout_family": normalize_layout(skin.get("layout_family"), project.id),
        "master": normalize_master(skin.get("master")),
    }
    path = skin_path(project)
    assert path is not None
    _atomic_write(path, out)
    deck = load_deck(project)
    if deck:
        deck["theme"] = out["theme"]
        deck["layout_family"] = out["layout_family"]
        deck["master"] = out["master"]
        save_deck(project, deck)
    return out


def patch_page(project: Project, page_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    deck = load_deck(project)
    if not deck:
        raise FileNotFoundError("尚无答辩 PPT")
    pages = deck.get("pages") or []
    page = next((p for p in pages if isinstance(p, dict) and p.get("id") == page_id), None)
    if not page:
        raise FileNotFoundError("页不存在")
    if "bullets" in patch and isinstance(patch["bullets"], list):
        page["bullets"] = patch["bullets"]
    if "title" in patch and patch["title"] is not None:
        page["title"] = str(patch["title"])
    if isinstance(patch.get("cover"), dict):
        page["cover"] = {**(page.get("cover") or {}), **patch["cover"]}
        deck["cover"] = {**(deck.get("cover") or {}), **patch["cover"]}
        save_cover(project, deck["cover"])
    if isinstance(patch.get("figure"), dict):
        page["figure"] = {**(page.get("figure") or {}), **patch["figure"]}
    if "toc_items" in patch and isinstance(patch["toc_items"], list):
        page["toc_items"] = patch["toc_items"]
    if isinstance(patch.get("table"), dict):
        page["table"] = patch["table"]
    save_deck(project, deck)
    return page
