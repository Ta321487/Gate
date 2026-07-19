from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models import Project, ProjectStatus
from app.schemas import (
    ApiOk,
    MatchUpdate,
    ProjectDetail,
    ProjectSummary,
    RuntimeState,
    StatsOut,
)
from app.services import projects as project_svc
from app.services import runtime as rt
from app.services.jobs import start_job
from app.services.student_db import drop_student_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["projects"])


def _detail(p: Project) -> ProjectDetail:
    from app.bake.catalog import normalize_theme

    project_svc.ensure_proposal_in_spec(p)
    d = ProjectDetail.model_validate(p)
    d.theme = normalize_theme(p.theme or "", p.domain)
    return d


@router.get("/stats", response_model=StatsOut)
async def project_stats(db: AsyncSession = Depends(get_db)):
    return StatsOut(**(await project_svc.stats(db)))


@router.get("", response_model=list[ProjectSummary])
async def list_projects(
    q: str = "",
    filter: str = Query("all", alias="filter"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).order_by(Project.updated_at.desc()))
    items = list(result.scalars().all())
    if q:
        items = [p for p in items if q in p.title or q in p.id]
    if filter == "active":
        items = [p for p in items if p.status in ("needs_confirm", "generating", "running", "ready")]
    elif filter == "done":
        # 可交付 = 已生成/运行中且 ZIP 仍解锁（门禁回退后 zip_ready=False）
        items = [
            p
            for p in items
            if p.status in ("generated", "running") and p.zip_ready
        ]
    elif filter == "fail":
        items = [p for p in items if p.status == "failed"]
    # 运行态以进程为准，纠正库内陈旧标记（列表「运行」列）
    dirty = False
    for p in items:
        be = rt.backend_running(p.id)
        fe = rt.frontend_running(p.id)
        if p.backend_running != be or p.frontend_running != fe:
            p.backend_running = be
            p.frontend_running = fe
            dirty = True
        if be or fe:
            if p.status not in (ProjectStatus.running.value, ProjectStatus.generating.value):
                p.status = ProjectStatus.running.value
                dirty = True
        elif p.status == ProjectStatus.running.value and not be and not fe:
            p.status = ProjectStatus.generated.value
            dirty = True
    # 须在 commit 前物化：commit 后 ORM 过期，Pydantic 再读字段会触发 MissingGreenlet
    summaries = [ProjectSummary.model_validate(p) for p in items]
    if dirty:
        await db.commit()
    return summaries


@router.post("/upload", response_model=ProjectDetail)
async def upload_proposal(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    suffix = Path(file.filename or "proposal.txt").suffix.lower()
    if suffix not in {".pdf", ".doc", ".docx", ".txt"}:
        raise HTTPException(400, "仅支持 PDF / Word / TXT")
    dest_dir = settings.uploads_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "proposal.txt").name
    dest = dest_dir / f"{datetime_stamp()}_{safe_name}"
    content = await file.read()
    dest.write_bytes(content)
    project = await project_svc.create_from_upload(db, dest, safe_name, len(content))
    return _detail(project)


def datetime_stamp() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d%H%M%S")


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if project_svc.sync_checklist_from_workspace(p):
        await db.commit()
        await db.refresh(p)
    p.backend_running = rt.backend_running(project_id)
    p.frontend_running = rt.frontend_running(project_id)
    return _detail(p)


@router.patch("/{project_id}/match", response_model=ProjectDetail)
async def patch_match(project_id: str, body: MatchUpdate, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    try:
        p = await project_svc.update_match(db, p, body)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _detail(p)


@router.post("/{project_id}/generate", response_model=ApiOk)
async def generate(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if not p.match_confirmed:
        raise HTTPException(400, "请先确认匹配")
    job = await start_job(db, p)
    return ApiOk(message=f"Job #{job.id} 已启动", data={"job_id": job.id})


@router.delete("/{project_id}", response_model=ApiOk)
async def delete_project(
    project_id: str,
    keep_db: bool = Query(False, description="为 true 时保留学生 MySQL 库"),
    db: AsyncSession = Depends(get_db),
):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    be = rt.backend_running(project_id)
    fe = rt.frontend_running(project_id)
    if (
        p.status in (ProjectStatus.running.value, ProjectStatus.generating.value)
        or be
        or fe
    ):
        raise HTTPException(400, "项目运行中或正在生成，请先停止后再删除")
    rt.stop_backend(project_id, p.backend_port)
    rt.stop_frontend(project_id, p.frontend_port)
    settings = get_settings()
    ws = settings.workspace_dir / project_id
    if ws.exists():
        rt.detach_frontend_deps(ws)
        shutil.rmtree(ws, ignore_errors=True)
    zip_path = settings.workspace_dir / f"{project_id}-thesis-app.zip"
    if zip_path.exists():
        zip_path.unlink()

    db_note = ""
    if not keep_db and p.db_name:
        try:
            drop_student_database(p.db_name)
            db_note = f"，已删除库 {p.db_name}"
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "删除项目 %s 时删库失败（仍继续删项目）: %s", project_id, e
            )
            db_note = f"，库 {p.db_name} 删除失败（已跳过）"
    elif keep_db and p.db_name:
        db_note = f"，已保留库 {p.db_name}"

    await db.delete(p)
    await db.commit()
    return ApiOk(message=f"已删除{db_note}")


@router.get("/{project_id}/download")
async def download_zip(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    gates = p.gates or {}
    if not (p.zip_ready and gates.get("zip_allowed") and gates.get("overall")):
        raise HTTPException(403, "门禁未过 · 禁止下载 ZIP")
    if not p.zip_path or not Path(p.zip_path).exists():
        raise HTTPException(404, "ZIP 不存在")
    return FileResponse(
        p.zip_path,
        filename="thesis-app.zip",
        media_type="application/zip",
    )


@router.get("/{project_id}/schema")
async def get_schema(project_id: str, db: AsyncSession = Depends(get_db)):
    """表结构 + 推断联系（供产物页展示）。"""
    from app.bake.schema_er import load_schema_model

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if not p.workspace_path:
        raise HTTPException(400, "尚未生成工作区")
    model = load_schema_model(Path(p.workspace_path))
    if not model:
        raise HTTPException(404, "未找到 sql/schema.sql")
    return {
        "db_name": p.db_name,
        "path": "sql/schema.sql",
        **model,
    }


@router.get("/{project_id}/schema/er.svg")
async def download_er_svg(project_id: str, db: AsyncSession = Depends(get_db)):
    from fastapi.responses import Response

    from app.bake.schema_er import load_schema_model, render_er_svg

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if not p.workspace_path:
        raise HTTPException(400, "尚未生成工作区")
    model = load_schema_model(Path(p.workspace_path))
    if not model:
        raise HTTPException(404, "未找到 sql/schema.sql")
    svg = render_er_svg(model, title=f"E-R · {p.db_name or project_id}")
    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{project_id}-er.svg"',
        },
    )


@router.get("/{project_id}/runtime", response_model=RuntimeState)
async def get_runtime(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    be_st = rt.backend_status(project_id, p.backend_port)
    fe_st = rt.frontend_status(project_id, p.frontend_port)
    # 列表用的进程标记：跟 status 对齐，不另搞一套「假健康」
    p.backend_running = be_st in ("starting", "healthy")
    p.frontend_running = fe_st in ("starting", "healthy")
    return RuntimeState(
        backend_status=be_st,
        frontend_status=fe_st,
        backend_port=p.backend_port,
        frontend_port=p.frontend_port,
        preview_url=f"http://127.0.0.1:{p.frontend_port}" if fe_st == "healthy" else None,
        backend_url=f"http://127.0.0.1:{p.backend_port}" if be_st == "healthy" else None,
        backend_log_tail=rt.backend_log(project_id),
        frontend_log_tail=rt.frontend_log(project_id),
    )


@router.post("/{project_id}/runtime/{side}/{action}", response_model=ApiOk)
async def runtime_action(
    project_id: str,
    side: str,
    action: str,
    db: AsyncSession = Depends(get_db),
):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if not p.workspace_path:
        raise HTTPException(400, "尚未生成工作区")
    ws = Path(p.workspace_path)
    if not ws.exists():
        raise HTTPException(400, "工作区目录不存在")

    try:
        if side == "all":
            if action == "start":
                rt.start_backend(project_id, ws, p.backend_port, p.db_name or "")
                rt.start_frontend(project_id, ws, p.frontend_port, p.backend_port)
                p.status = ProjectStatus.running.value
            elif action == "stop":
                rt.stop_all(project_id, p.backend_port, p.frontend_port)
                if p.status == ProjectStatus.running.value:
                    p.status = ProjectStatus.generated.value
            elif action == "restart":
                rt.stop_all(project_id, p.backend_port, p.frontend_port)
                rt.start_backend(project_id, ws, p.backend_port, p.db_name or "")
                rt.start_frontend(project_id, ws, p.frontend_port, p.backend_port)
                p.status = ProjectStatus.running.value
            else:
                raise HTTPException(400, "未知动作")
        elif side == "backend":
            if action == "start":
                rt.start_backend(project_id, ws, p.backend_port, p.db_name or "")
            elif action == "stop":
                rt.stop_backend(project_id, p.backend_port)
            elif action == "restart":
                rt.stop_backend(project_id, p.backend_port)
                rt.start_backend(project_id, ws, p.backend_port, p.db_name or "")
            else:
                raise HTTPException(400, "未知动作")
        elif side == "frontend":
            if action == "start":
                rt.start_frontend(project_id, ws, p.frontend_port, p.backend_port)
            elif action == "stop":
                rt.stop_frontend(project_id, p.frontend_port)
            elif action == "restart":
                rt.stop_frontend(project_id, p.frontend_port)
                rt.start_frontend(project_id, ws, p.frontend_port, p.backend_port)
            else:
                raise HTTPException(400, "未知动作")
        else:
            raise HTTPException(400, "未知侧别")
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from e

    # 停完稍等端口释放，再读 status
    if action == "stop":
        time.sleep(0.6)
    p.backend_running = rt.backend_status(project_id, p.backend_port) in ("starting", "healthy")
    p.frontend_running = rt.frontend_status(project_id, p.frontend_port) in ("starting", "healthy")
    await db.commit()
    return ApiOk(message=f"{side}/{action} 完成")


@router.get("/{project_id}/logs/{side}")
async def get_logs(project_id: str, side: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if side == "job":
        text = rt.job_log(project_id)
    elif side == "backend":
        text = rt.backend_log(project_id)
    elif side == "frontend":
        text = rt.frontend_log(project_id)
    elif side == "deepseek":
        settings = get_settings()
        path = settings.logs_dir / project_id / "deepseek.log"
        text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else "暂无 DeepSeek 调用日志"
    else:
        raise HTTPException(400, "未知日志侧别")
    return {"side": side, "content": text}
