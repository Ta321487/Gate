"""工厂能力说明卡维护 API。"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.system_router import router
from app.core.database import get_db
from app.services import cap_cards as cc


class CapCardUpsert(BaseModel):
    cap_id: str
    title_zh: str = ""
    body_zh: str = ""
    auth_line_on: str = ""
    auth_line_off: str = ""
    backend_suffix: str = ""
    menu_ids: str = ""
    claim_needles: list[str] = Field(default_factory=list)
    readme_slot: str = ""
    sort: int = 0
    source: str = "manual"


@router.get("/system/cap-cards/meta", summary="能力说明卡·选项")
async def cap_cards_meta(db: AsyncSession = Depends(get_db)):
    rows = await cc.load_all_rows(db)
    caps = [
        {"id": r["cap_id"], "label": r.get("title_zh") or r["cap_id"]}
        for r in rows
        if r.get("cap_id")
    ]
    slot_labels = {
        "AI_ASSISTANT_FAQ": "AI 助手 FAQ",
        "SECURITY_FAQ": "鉴权 FAQ",
    }
    slots = sorted({r.get("readme_slot") for r in rows if r.get("readme_slot")})
    for s in slot_labels:
        if s not in slots:
            slots.append(s)
    slots = sorted(set(slots))
    return {
        "ok": True,
        "caps": caps,
        "readme_slots": slots,
        "readme_slot_options": [
            {"value": s, "label": slot_labels.get(s, s)} for s in slots
        ],
    }


@router.get("/system/cap-cards", summary="能力说明卡列表")
async def list_cap_cards(
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    rows = await cc.load_all_rows(db)
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in (r["cap_id"] or "").lower()
            or qq in (r["title_zh"] or "").lower()
            or qq in (r["body_zh"] or "").lower()
        ]
    return {"ok": True, "total": len(rows), "items": rows}


@router.post("/system/cap-cards/migrate", summary="迁入/补齐能力说明卡种子")
async def migrate_cap_cards(db: AsyncSession = Depends(get_db)):
    stats = await cc.migrate_seed_if_empty(db)
    return {"ok": True, **stats}


@router.get("/system/cap-cards/gaps", summary="缺少说明卡的能力")
async def cap_cards_gaps(db: AsyncSession = Depends(get_db)):
    rows = await cc.load_all_rows(db)
    report = cc.gap_report(rows=rows)
    return {"ok": True, **report}


@router.put("/system/cap-cards", summary="新增或更新说明卡")
async def upsert_cap_card(body: CapCardUpsert, db: AsyncSession = Depends(get_db)):
    try:
        row = await cc.upsert_entry(
            db,
            cap_id=body.cap_id,
            title_zh=body.title_zh,
            body_zh=body.body_zh,
            auth_line_on=body.auth_line_on,
            auth_line_off=body.auth_line_off,
            backend_suffix=body.backend_suffix,
            menu_ids=body.menu_ids,
            claim_needles=body.claim_needles,
            readme_slot=body.readme_slot,
            sort=body.sort,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "item": row}


@router.delete("/system/cap-cards/{entry_id}", summary="删除说明卡")
async def delete_cap_card(entry_id: int, db: AsyncSession = Depends(get_db)):
    ok = await cc.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="未找到")
    return {"ok": True}
