"""工厂论文图题模板维护 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["论文图题"])
from app.core.database import get_db
from app.services import diagram_titles as dt


class DiagramTitleUpsert(BaseModel):
    diagram_kind: str
    domain_id: str = Field("*", description="DOM-* 或 *")
    title_tpl: str = Field(..., max_length=128)
    sort: int = 0
    source: str = "manual"


@router.get("/system/diagram-titles/meta", summary="论文图题·选项")
async def diagram_titles_meta(db: AsyncSession = Depends(get_db)):
    from app.bake.catalog import DOMAINS

    await dt.load_all_rows(db)
    kinds = sorted(dt.DIAGRAM_KINDS)
    domains = [
        {"id": "*", "name": "跨域壳默认"},
        *[
            {"id": k, "name": (DOMAINS.get(k) or {}).get("label") or k}
            for k in DOMAINS
        ],
    ]
    return {
        "ok": True,
        "domains": domains,
        "kinds": kinds,
        "kind_options": [
            {"value": k, "label": dt.KIND_LABELS_ZH.get(k, k)} for k in kinds
        ],
    }


@router.get("/system/diagram-titles", summary="论文图题列表")
async def list_diagram_titles(
    diagram_kind: Optional[str] = Query(None),
    domain_id: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    rows = await dt.load_all_rows(db)
    if diagram_kind:
        rows = [r for r in rows if r["diagram_kind"] == diagram_kind]
    if domain_id is not None:
        rows = [r for r in rows if r["domain_id"] == domain_id]
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in (r["title_tpl"] or "").lower()
            or qq in (r["diagram_kind"] or "").lower()
            or qq in (r["domain_id"] or "").lower()
        ]
    return {"ok": True, "total": len(rows), "items": rows}


@router.post("/system/diagram-titles/migrate", summary="迁入/补齐图题种子")
async def migrate_diagram_titles(db: AsyncSession = Depends(get_db)):
    stats = await dt.migrate_seed_if_empty(db)
    return {"ok": True, **stats}


@router.get("/system/diagram-titles/gaps", summary="缺少的图题模板")
async def diagram_titles_gaps(db: AsyncSession = Depends(get_db)):
    rows = await dt.load_all_rows(db)
    return {"ok": True, **dt.gap_report(rows=rows)}


@router.put("/system/diagram-titles", summary="新增或更新图题模板")
async def upsert_diagram_title(body: DiagramTitleUpsert, db: AsyncSession = Depends(get_db)):
    try:
        row = await dt.upsert_entry(
            db,
            diagram_kind=body.diagram_kind,
            domain_id=body.domain_id,
            title_tpl=body.title_tpl,
            sort=body.sort,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "item": row}


@router.delete("/system/diagram-titles/{entry_id}", summary="删除图题模板")
async def delete_diagram_title(entry_id: int, db: AsyncSession = Depends(get_db)):
    ok = await dt.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="未找到")
    return {"ok": True}
