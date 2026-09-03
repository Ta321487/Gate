"""业务指纹：计入 bake/合卷/栈/菜单/模块/用例/E-R/开题；不计 PPT 换皮。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.models import Project

from .deck_io import load_deck, save_deck
from .evidence import collect_context
from .themes import ensure_ppt_dirs, ppt_root


def _stable(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def compute_biz_fingerprint(project: Project) -> str:
    ctx = collect_context(project)
    payload = {
        "title": ctx.get("title"),
        "proposal": (ctx.get("proposal") or "")[:8000],
        "menus": ctx.get("menus"),
        "features": ctx.get("features"),
        "entities": ctx.get("entities"),
        "persistence": ctx.get("persistence"),
        "spring_security": ctx.get("spring_security"),
        "domain": ctx.get("domain"),
        "archetype": ctx.get("archetype"),
        "modules_groups": _module_digest(ctx.get("modules")),
        "er_tables": _er_digest(ctx.get("er")),
        "test_digest": _test_digest(ctx.get("testcases")),
    }
    return hashlib.sha256(_stable(payload).encode("utf-8")).hexdigest()


def _module_digest(modules: Any) -> Any:
    if not isinstance(modules, dict):
        return None
    groups = modules.get("groups") or modules.get("nodes") or modules.get("tree")
    if isinstance(groups, list):
        out = []
        for g in groups[:40]:
            if not isinstance(g, dict):
                continue
            out.append(
                {
                    "id": g.get("id") or g.get("key"),
                    "label": g.get("label") or g.get("title") or g.get("name"),
                    "children": [
                        c.get("label") or c.get("title") or c.get("name") or c.get("key")
                        for c in (g.get("children") or g.get("items") or [])[:20]
                        if isinstance(c, dict)
                    ],
                }
            )
        return out
    return None


def _er_digest(er: Any) -> Any:
    if not isinstance(er, dict):
        return None
    tables = er.get("tables") or er.get("entities") or []
    names = []
    for t in tables[:80]:
        if isinstance(t, dict):
            names.append(t.get("zh") or t.get("label") or t.get("name") or t.get("id"))
        else:
            names.append(str(t))
    return names


def _test_digest(tc: Any) -> Any:
    if not isinstance(tc, dict):
        return None
    rows = tc.get("rows") or tc.get("cases") or tc.get("items") or []
    out = []
    for r in rows[:40]:
        if isinstance(r, dict):
            out.append(r.get("name") or r.get("title") or r.get("id") or list(r.values())[:2])
        elif isinstance(r, (list, tuple)):
            out.append(list(r)[:3])
    return out


def fingerprint_path(project: Project) -> Path | None:
    root = ppt_root(project)
    return (root / "fingerprint.json") if root else None


def load_stored_fingerprint(project: Project) -> str | None:
    path = fingerprint_path(project)
    if not path or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return str(data.get("hash") or "") or None
        return None
    except Exception:  # noqa: BLE001
        return None


def save_fingerprint(project: Project, digest: str | None = None) -> str:
    ensure_ppt_dirs(project)
    digest = digest or compute_biz_fingerprint(project)
    path = fingerprint_path(project)
    assert path is not None
    path.write_text(
        json.dumps({"hash": digest}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return digest


def is_biz_dirty(project: Project) -> bool:
    deck = load_deck(project)
    if not deck:
        return False
    if deck.get("biz_dirty"):
        return True
    stored = load_stored_fingerprint(project)
    if not stored:
        return False
    return stored != compute_biz_fingerprint(project)


def mark_biz_dirty_if_changed(project: Project) -> bool:
    """bake/合卷成功后调用：有 deck 且指纹变则标脏，保留 deck。

    尚无历史指纹时只写入基线，不标脏。
    """
    deck = load_deck(project)
    if not deck:
        return False
    stored = load_stored_fingerprint(project)
    current = compute_biz_fingerprint(project)
    if not stored:
        save_fingerprint(project, current)
        return False
    if stored == current:
        return False
    deck["biz_dirty"] = True
    save_deck(project, deck)
    return True


def clear_biz_dirty(project: Project) -> None:
    deck = load_deck(project)
    if deck:
        deck["biz_dirty"] = False
        save_deck(project, deck)
    save_fingerprint(project)
