"""工厂开关建议扫词维护 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.system_router import router
from app.core.database import get_db
from app.services import addon_suggest as ads


class AddonSuggestUpsert(BaseModel):
    addon_id: str
    hint: str
    addon_label: str = ""
    evidence_zh: str = ""
    summary_zh: str = ""
    recommend: bool = True
    deliverable: bool = True
    sort: int = 0
    source: str = "manual"


@router.get("/system/addon-suggest/meta", summary="开关建议·addon 选项")
async def addon_suggest_meta(db: AsyncSession = Depends(get_db)):
    rows = await ads.load_all_rows(db)
    addons = sorted({r["addon_id"] for r in rows if r.get("addon_id")})
    labels = {
        r["addon_id"]: r.get("addon_label") or r["addon_id"]
        for r in rows
        if r.get("addon_id")
    }
    return {
        "ok": True,
        "addons": [{"id": a, "label": labels.get(a) or a} for a in addons],
    }


@router.get("/system/addon-suggest", summary="开关建议扫词列表")
async def list_addon_suggest(
    addon_id: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    rows = await ads.load_all_rows(db)
    if addon_id:
        rows = [r for r in rows if r["addon_id"] == addon_id]
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in (r["hint"] or "").lower()
            or qq in (r["addon_id"] or "").lower()
            or qq in (r["evidence_zh"] or "").lower()
        ]
    return {"ok": True, "total": len(rows), "items": rows}


@router.post("/system/addon-suggest/migrate", summary="迁入/补齐开关建议种子")
async def migrate_addon_suggest(db: AsyncSession = Depends(get_db)):
    stats = await ads.migrate_seed_if_empty(db)
    return {"ok": True, **stats}


@router.get("/system/addon-suggest/gaps", summary="缺少扫词的开关")
async def addon_suggest_gaps(db: AsyncSession = Depends(get_db)):
    rows = await ads.load_all_rows(db)
    report = ads.gap_report(rows=rows)
    return {"ok": True, **report}


@router.put("/system/addon-suggest", summary="新增或更新扫词")
async def upsert_addon_suggest(
    body: AddonSuggestUpsert,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await ads.upsert_entry(
            db,
            addon_id=body.addon_id,
            hint=body.hint,
            addon_label=body.addon_label,
            evidence_zh=body.evidence_zh,
            summary_zh=body.summary_zh,
            recommend=body.recommend,
            deliverable=body.deliverable,
            sort=body.sort,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "item": row}


@router.delete("/system/addon-suggest/{entry_id}", summary="删除扫词")
async def delete_addon_suggest(entry_id: int, db: AsyncSession = Depends(get_db)):
    ok = await ads.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="未找到")
    return {"ok": True}
