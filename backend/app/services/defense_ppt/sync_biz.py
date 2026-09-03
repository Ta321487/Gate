"""按工程更新业务页：复用 unit_flow 填页；跳过 locked。与填岛同款传 db Session。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project

from .deck_io import load_deck, load_skin, save_deck
from .evidence import collect_context
from .fingerprint import clear_biz_dirty
from .job_fill import fill_deck_via_unit_flow


async def sync_biz(db: AsyncSession, project: Project) -> dict[str, Any]:
    """未锁定块按开题∪实包重填；保留皮与 locked 要点。"""
    deck = load_deck(project)
    if not deck:
        raise FileNotFoundError("尚无答辩 PPT")

    skin = load_skin(project)
    cover = deck.get("cover") if isinstance(deck.get("cover"), dict) else {}
    ctx = collect_context(project)

    kept = 0
    for page in deck.get("pages") or []:
        if not isinstance(page, dict):
            continue
        for b in page.get("bullets") or []:
            if isinstance(b, dict) and b.get("locked"):
                kept += 1

    fresh, summary = await fill_deck_via_unit_flow(
        db,
        project,
        ctx,
        cover=cover,
        theme=skin["theme"],
        layout_family=skin["layout_family"],
        master=skin["master"],
        llm_enabled=True,
        on_event=None,
        old_deck=deck,
    )

    fresh["theme"] = skin["theme"]
    fresh["layout_family"] = skin["layout_family"]
    fresh["master"] = skin["master"]
    fresh["biz_dirty"] = False
    save_deck(project, fresh)
    clear_biz_dirty(project)
    updated = max(0, int(summary.done or 0))
    return {
        "updated": updated,
        "kept": kept,
        "message": f"已更新 {updated} 处 Unit；保留人工锁定 {kept} 处",
    }
