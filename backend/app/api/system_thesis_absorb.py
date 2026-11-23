"""终稿吸收 API：厂库入库 / 重抽 / 覆盖 / 喂助手稿。不出包、不匹配。"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.system_router import router
from app.core.database import get_db
from app.services import thesis_absorb as ta
from app.services.thesis_absorb_extract import EXTRACTOR_VERSION
from app.services.thesis_absorb_figures import figure_libs_ready


class ThesisAbsorbPatch(BaseModel):
    coverage: Optional[str] = None
    coverage_note: Optional[str] = Field(None, max_length=512)
    status: Optional[str] = None
    proposal: Optional[dict[str, Any]] = None
    draft_roles: Optional[list] = None
    draft_entities: Optional[list] = None
    draft_features: Optional[list] = None
    trial_project_id: Optional[str] = None
    mark_fed: bool = False


async def _resolve_id(db: AsyncSession, record_key: str) -> int:
    rid = await ta.resolve_record_key(db, record_key)
    if rid is None:
        raise HTTPException(status_code=404, detail="未找到")
    return rid


@router.get("/system/thesis-absorb/meta", summary="终稿吸收·元信息")
async def thesis_absorb_meta():
    return {
        "ok": True,
        "extractor_version": EXTRACTOR_VERSION,
        "coverages": [
            {"value": "unknown", "label": "待判断"},
            {"value": "covered", "label": "已齐"},
            {"value": "skin_gap", "label": "差说法"},
            {"value": "domain_gap", "label": "差能力"},
        ],
        "statuses": list(ta.STATUS_VALUES),
        "figure_extract_ready": (_fig := figure_libs_ready())[0],
        "figure_extract_hint": _fig[1],
        "copy": {
            "title": "终稿吸收",
            "desc": "从终稿抽出要点，对照能力补齐",
            "success": "已抽取，请先标覆盖，再复制给助手",
        },
    }


@router.get("/system/thesis-absorb", summary="终稿吸收列表")
async def list_thesis_absorb(
    q: Optional[str] = Query(None),
    coverage: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    items = await ta.list_records(db, q=q, coverage=coverage)
    return {"ok": True, "total": len(items), "items": items}


@router.get("/system/thesis-absorb/{record_key}", summary="终稿吸收详情")
async def get_thesis_absorb(record_key: str, db: AsyncSession = Depends(get_db)):
    rid = await _resolve_id(db, record_key)
    item = await ta.get_record(db, rid)
    if not item:
        raise HTTPException(status_code=404, detail="未找到")
    return {"ok": True, "item": item}


@router.post("/system/thesis-absorb/upload", summary="上传终稿并入库")
async def upload_thesis_absorb(
    file: UploadFile = File(..., description="终稿 PDF/Word/TXT"),
    db: AsyncSession = Depends(get_db),
):
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="空文件")
    if len(raw) > 40 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大（上限 40MB）")
    try:
        item = await ta.create_from_upload(
            db, filename=file.filename or "thesis.txt", raw=raw
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "ok": True,
        "item": item,
        "message": "已抽取，请先标覆盖，再复制给助手",
    }


@router.post("/system/thesis-absorb/{record_key}/reextract", summary="重新抽取")
async def reextract_thesis_absorb(record_key: str, db: AsyncSession = Depends(get_db)):
    rid = await _resolve_id(db, record_key)
    try:
        item = await ta.reextract(db, rid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "item": item}


@router.patch("/system/thesis-absorb/{record_key}", summary="更新覆盖/结构/状态")
async def patch_thesis_absorb(
    record_key: str,
    body: ThesisAbsorbPatch,
    db: AsyncSession = Depends(get_db),
):
    rid = await _resolve_id(db, record_key)
    try:
        item = await ta.update_record(
            db,
            rid,
            coverage=body.coverage,
            coverage_note=body.coverage_note,
            status=body.status,
            proposal=body.proposal,
            draft_roles=body.draft_roles,
            draft_entities=body.draft_entities,
            draft_features=body.draft_features,
            trial_project_id=body.trial_project_id,
            mark_fed=body.mark_fed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "item": item}


@router.post(
    "/system/thesis-absorb/{record_key}/feed",
    summary="标记已导出喂助手稿并返回正文",
)
async def feed_thesis_absorb(record_key: str, db: AsyncSession = Depends(get_db)):
    rid = await _resolve_id(db, record_key)
    try:
        item = await ta.update_record(db, rid, mark_fed=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "ok": True,
        "item": item,
        "feed_markdown": item.get("feed_markdown"),
    }


@router.delete("/system/thesis-absorb/{record_key}", summary="删除吸收记录")
async def delete_thesis_absorb(record_key: str, db: AsyncSession = Depends(get_db)):
    rid = await _resolve_id(db, record_key)
    ok = await ta.delete_record(db, rid)
    if not ok:
        raise HTTPException(status_code=404, detail="未找到")
    return {"ok": True}
