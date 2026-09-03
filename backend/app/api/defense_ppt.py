"""答辩 PPT API：/api/projects/{id}/defense-ppt/*"""

from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Project
from app.services.defense_ppt.check import run_check
from app.services.defense_ppt.cover import require_cover_complete
from app.services.defense_ppt.deck_io import (
    load_deck,
    patch_page,
    save_cover,
    save_skin,
)
from app.services.defense_ppt.export_pptx import export_filename, export_pptx
from app.services.defense_ppt.job_runner import cancel_ppt_job, start_ppt_job
from app.services.defense_ppt.screenshots import capture_current, upload_screenshot
from app.services.defense_ppt.status import (
    active_ppt_job,
    build_status,
    job_to_public,
    latest_ppt_job,
)
from app.services.defense_ppt.sync_biz import sync_biz
from app.services.fill_events import fill_event_hub

router = APIRouter(tags=["答辩PPT"])


class CoverBody(BaseModel):
    school: str = ""
    college: str = ""
    class_name: str = ""
    student_name: str = ""
    student_id: str = ""
    advisor: str = ""
    badge_data_url: Optional[str] = None


class GenerateBody(BaseModel):
    cover: Optional[CoverBody] = None
    theme: Optional[str] = None
    layout_family: Optional[str] = None
    master: Optional[str] = None


class SkinBody(BaseModel):
    theme: Optional[str] = None
    layout_family: Optional[str] = None
    master: Optional[str] = None


class PagePatchBody(BaseModel):
    bullets: Optional[list[Any]] = None
    title: Optional[str] = None
    cover: Optional[dict[str, Any]] = None
    figure: Optional[dict[str, Any]] = None
    toc_items: Optional[list[Any]] = None
    table: Optional[dict[str, Any]] = None


class ShotCaptureBody(BaseModel):
    page_id: Optional[str] = Field(default=None, alias="pageId")
    pageId: Optional[str] = None

    def resolved_page_id(self) -> str | None:
        return self.page_id or self.pageId


class ShotUploadBody(BaseModel):
    page_id: Optional[str] = Field(default=None, alias="pageId")
    pageId: Optional[str] = None
    data_url: Optional[str] = Field(default=None, alias="dataUrl")
    dataUrl: Optional[str] = None

    def resolved_page_id(self) -> str | None:
        return self.page_id or self.pageId

    def resolved_data_url(self) -> str:
        return self.data_url or self.dataUrl or ""


async def _project(db: AsyncSession, project_id: str) -> Project:
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    return p


@router.get("/{project_id}/defense-ppt", summary="答辩 PPT 状态")
async def get_defense_ppt(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await _project(db, project_id)
    return await build_status(db, p)


@router.put("/{project_id}/defense-ppt/cover", summary="保存封面")
async def put_cover(
    project_id: str, body: CoverBody, db: AsyncSession = Depends(get_db)
):
    p = await _project(db, project_id)
    try:
        cover = require_cover_complete(body.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    save_cover(p, cover)
    return await build_status(db, p)


@router.post("/{project_id}/defense-ppt/generate", summary="生成答辩 PPT")
async def generate(
    project_id: str, body: GenerateBody = GenerateBody(), db: AsyncSession = Depends(get_db)
):
    p = await _project(db, project_id)
    cover = body.cover.model_dump() if body.cover else None
    try:
        if cover:
            require_cover_complete(cover)
        job = await start_ppt_job(
            db,
            p,
            cover=cover,
            theme=body.theme,
            layout_family=body.layout_family,
            master=body.master,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except PermissionError as e:
        raise HTTPException(409, str(e)) from e
    st = await build_status(db, p)
    st["job_id"] = job.id
    st["phase"] = "generating"
    return st


@router.get("/{project_id}/defense-ppt/job", summary="PPT 任务进度")
async def get_job(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await _project(db, project_id)
    job = await active_ppt_job(db, p.id) or await latest_ppt_job(db, p.id)
    return job_to_public(job)


@router.post("/{project_id}/defense-ppt/cancel", summary="取消 PPT 任务")
async def cancel(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await _project(db, project_id)
    await cancel_ppt_job(db, p)
    return await build_status(db, p)


@router.get("/{project_id}/defense-ppt/events", summary="PPT 进度 SSE")
async def stream_events(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    await _project(db, project_id)

    async def events():
        async for event in fill_event_hub.subscribe(project_id, channel="defense_ppt"):
            if await request.is_disconnected():
                break
            if event.get("type") == "heartbeat":
                yield ": heartbeat\n\n"
                continue
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{project_id}/defense-ppt/deck", summary="读取 deck.json")
async def get_deck(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await _project(db, project_id)
    deck = load_deck(p)
    if not deck:
        raise HTTPException(404, "尚无答辩 PPT")
    return deck


@router.patch("/{project_id}/defense-ppt/deck/pages/{page_id}", summary="局部更新页")
async def patch_deck_page(
    project_id: str,
    page_id: str,
    body: PagePatchBody,
    db: AsyncSession = Depends(get_db),
):
    p = await _project(db, project_id)
    try:
        return patch_page(p, page_id, body.model_dump(exclude_none=True))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@router.patch("/{project_id}/defense-ppt/skin", summary="换皮（不标脏）")
async def patch_skin(
    project_id: str, body: SkinBody, db: AsyncSession = Depends(get_db)
):
    p = await _project(db, project_id)
    save_skin(p, body.model_dump(exclude_none=True))
    return await build_status(db, p)


@router.post("/{project_id}/defense-ppt/sync-biz", summary="按工程更新业务页")
async def post_sync_biz(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await _project(db, project_id)
    try:
        result = await sync_biz(db, p)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    st = await build_status(db, p)
    st.update(result)
    return st


@router.post("/{project_id}/defense-ppt/check", summary="导出门闩检查")
async def post_check(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await _project(db, project_id)
    return run_check(p)


@router.get("/{project_id}/defense-ppt/export", summary="导出 PPTX")
async def get_export(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await _project(db, project_id)
    try:
        path = export_pptx(p)
    except PermissionError as e:
        raise HTTPException(409, str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"导出失败：{e}") from e
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=export_filename(p),
    )


@router.get("/{project_id}/defense-ppt/figures/{file_path:path}", summary="旁路图文件")
async def get_figure(project_id: str, file_path: str, db: AsyncSession = Depends(get_db)):
    from fastapi.responses import FileResponse

    from app.services.defense_ppt.figures import figure_file

    p = await _project(db, project_id)
    path = figure_file(p, file_path)
    if not path:
        raise HTTPException(404, "图文件不存在")
    media = "image/svg+xml" if path.suffix.lower() == ".svg" else "application/octet-stream"
    if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        media = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(path.suffix.lower(), media)
    return FileResponse(path, media_type=media)


@router.post("/{project_id}/defense-ppt/screenshots/capture-current", summary="半自动采图")
async def post_capture(
    project_id: str,
    body: ShotCaptureBody = ShotCaptureBody(),
    db: AsyncSession = Depends(get_db),
):
    p = await _project(db, project_id)
    try:
        return await capture_current(p, page_id=body.resolved_page_id())
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@router.post("/{project_id}/defense-ppt/screenshots/upload", summary="上传截图")
async def post_upload(
    project_id: str,
    body: ShotUploadBody,
    db: AsyncSession = Depends(get_db),
):
    p = await _project(db, project_id)
    data_url = body.resolved_data_url()
    if not data_url:
        raise HTTPException(400, "缺少 data_url")
    try:
        return upload_screenshot(p, page_id=body.resolved_page_id(), data_url=data_url)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
