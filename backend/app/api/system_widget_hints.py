"""工厂控件语义提示维护 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.system_router import router
from app.core.database import get_db
from app.services import widget_hints as wh


class WidgetHintUpsert(BaseModel):
    rule_key: str
    match_scope: str = "label_contains"
    match_pattern: str = ""
    when_type: str = ""
    widget: str = "text"
    note_zh: str = ""
    sort: int = 0
    enabled: bool = True
    source: str = "manual"


@router.get("/system/widget-hints/meta", summary="控件语义·选项")
async def widget_hints_meta(db: AsyncSession = Depends(get_db)):
    await wh.load_all_rows(db)
    widgets = sorted(wh.WIDGET_KINDS)
    scopes = sorted(wh.MATCH_SCOPES)
    when_types = sorted(t for t in wh.WHEN_TYPES if t)
    return {
        "ok": True,
        "widgets": widgets,
        "scopes": scopes,
        "when_types": when_types,
        "widget_options": [
            {"value": w, "label": wh.WIDGET_LABELS_ZH.get(w, w)} for w in widgets
        ],
        "scope_options": [
            {"value": s, "label": wh.MATCH_SCOPE_LABELS_ZH.get(s, s)} for s in scopes
        ],
        "when_type_options": [
            {"value": t, "label": wh.WHEN_TYPE_LABELS_ZH.get(t, t)} for t in when_types
        ],
    }


@router.get("/system/widget-hints", summary="控件语义规则列表")
async def list_widget_hints(
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    rows = await wh.load_all_rows(db)
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in (r["rule_key"] or "").lower()
            or qq in (r["match_pattern"] or "").lower()
            or qq in (r["note_zh"] or "").lower()
            or qq in (r["widget"] or "").lower()
        ]
    return {"ok": True, "total": len(rows), "items": rows}


@router.post("/system/widget-hints/migrate", summary="迁入/补齐控件语义种子")
async def migrate_widget_hints(db: AsyncSession = Depends(get_db)):
    stats = await wh.migrate_seed_if_empty(db)
    return {"ok": True, **stats}


@router.get("/system/widget-hints/gaps", summary="缺少的控件语义规则")
async def widget_hints_gaps(db: AsyncSession = Depends(get_db)):
    rows = await wh.load_all_rows(db)
    return {"ok": True, **wh.gap_report(rows=rows)}


@router.put("/system/widget-hints", summary="新增或更新规则")
async def upsert_widget_hint(body: WidgetHintUpsert, db: AsyncSession = Depends(get_db)):
    try:
        row = await wh.upsert_entry(
            db,
            rule_key=body.rule_key,
            match_scope=body.match_scope,
            match_pattern=body.match_pattern,
            when_type=body.when_type,
            widget=body.widget,
            note_zh=body.note_zh,
            sort=body.sort,
            enabled=body.enabled,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "item": row}


@router.delete("/system/widget-hints/{entry_id}", summary="删除规则")
async def delete_widget_hint(entry_id: int, db: AsyncSession = Depends(get_db)):
    ok = await wh.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="未找到")
    return {"ok": True}
