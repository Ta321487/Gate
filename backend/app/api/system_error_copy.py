"""工厂错误码中文维护 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["错误码中文"])
from app.core.database import get_db
from app.services import error_copy as ec


class ErrorCopyUpsert(BaseModel):
    error_code: str
    message_zh: str
    code_num: int = 0
    sort: int = 0
    source: str = "manual"


@router.get("/system/error-copy/meta", summary="错误码中文·选项")
async def error_copy_meta(db: AsyncSession = Depends(get_db)):
    rows = await ec.load_all_rows(db)
    codes = [
        {
            "id": r["error_code"],
            "label": r["error_code"],
            "code_num": r.get("code_num") or 0,
        }
        for r in rows
        if r.get("error_code")
    ]
    expected = [
        {"id": c, "label": c, "code_num": n} for c, n in ec.EXPECTED_ERROR_CODES
    ]
    return {"ok": True, "codes": codes or expected, "expected": expected}


@router.get("/system/error-copy", summary="错误码中文列表")
async def list_error_copy(
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    rows = await ec.load_all_rows(db)
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in (r["error_code"] or "").lower()
            or qq in (r["message_zh"] or "").lower()
            or qq in str(r.get("code_num") or "")
        ]
    return {"ok": True, "total": len(rows), "items": rows}


@router.post("/system/error-copy/migrate", summary="迁入/补齐错误码种子")
async def migrate_error_copy(db: AsyncSession = Depends(get_db)):
    stats = await ec.migrate_seed_if_empty(db)
    return {"ok": True, **stats}


@router.get("/system/error-copy/gaps", summary="缺少中文的错误码")
async def error_copy_gaps(db: AsyncSession = Depends(get_db)):
    rows = await ec.load_all_rows(db)
    report = ec.gap_report(rows=rows)
    return {"ok": True, **report}


@router.put("/system/error-copy", summary="新增或更新错误码中文")
async def upsert_error_copy(body: ErrorCopyUpsert, db: AsyncSession = Depends(get_db)):
    try:
        row = await ec.upsert_entry(
            db,
            error_code=body.error_code,
            message_zh=body.message_zh,
            code_num=body.code_num,
            sort=body.sort,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "item": row}


@router.delete("/system/error-copy/{entry_id}", summary="删除错误码中文")
async def delete_error_copy(entry_id: int, db: AsyncSession = Depends(get_db)):
    ok = await ec.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="未找到")
    return {"ok": True}
