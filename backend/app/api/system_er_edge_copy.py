"""工厂表关系叙事句维护 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["表关系叙事"])
from app.core.database import get_db
from app.services import er_edge_copy as eec


class ErEdgeCopyUpsert(BaseModel):
    table_a: str
    table_b: str
    sentence_zh: str = Field(..., max_length=eec.SENTENCE_MAX)
    sort: int = 0
    source: str = "manual"


@router.get("/system/er-edge-copy/meta", summary="表关系叙事·选项")
async def er_edge_copy_meta(db: AsyncSession = Depends(get_db)):
    rows = await eec.load_all_rows(db)
    tables: set[str] = set()
    for r in rows:
        if r.get("table_a"):
            tables.add(r["table_a"])
        if r.get("table_b"):
            tables.add(r["table_b"])
    for item in eec._seed_payload():
        a = (item.get("table_a") or "").strip()
        b = (item.get("table_b") or "").strip()
        if a:
            tables.add(a)
        if b:
            tables.add(b)
    table_list = sorted(tables)
    return {
        "ok": True,
        "tables": table_list,
        "table_options": [{"value": t, "label": t} for t in table_list],
        "sentence_max": eec.SENTENCE_MAX,
    }


@router.get("/system/er-edge-copy", summary="表关系叙事列表")
async def list_er_edge_copy(
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    rows = await eec.load_all_rows(db)
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in (r["table_a"] or "").lower()
            or qq in (r["table_b"] or "").lower()
            or qq in (r["sentence_zh"] or "").lower()
        ]
    return {"ok": True, "total": len(rows), "items": rows}


@router.post("/system/er-edge-copy/migrate", summary="迁入/补齐表关系叙事种子")
async def migrate_er_edge_copy(db: AsyncSession = Depends(get_db)):
    stats = await eec.migrate_seed_if_empty(db)
    return {"ok": True, **stats}


@router.get("/system/er-edge-copy/gaps", summary="缺少的表关系叙事")
async def er_edge_copy_gaps(db: AsyncSession = Depends(get_db)):
    rows = await eec.load_all_rows(db)
    return {"ok": True, **eec.gap_report(rows=rows)}


@router.put("/system/er-edge-copy", summary="新增或更新叙事句")
async def upsert_er_edge_copy(body: ErEdgeCopyUpsert, db: AsyncSession = Depends(get_db)):
    try:
        row = await eec.upsert_entry(
            db,
            table_a=body.table_a,
            table_b=body.table_b,
            sentence_zh=body.sentence_zh,
            sort=body.sort,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "item": row}


@router.delete("/system/er-edge-copy/{entry_id}", summary="删除叙事句")
async def delete_er_edge_copy(entry_id: int, db: AsyncSession = Depends(get_db)):
    ok = await eec.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="未找到")
    return {"ok": True}
