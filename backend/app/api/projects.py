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
router = APIRouter(prefix="/api/projects", tags=["项目"])


def _detail(p: Project) -> ProjectDetail:
    from app.bake.catalog import normalize_theme

    project_svc.ensure_proposal_in_spec(p)
    d = ProjectDetail.model_validate(p)
    d.theme = normalize_theme(p.theme or "", p.domain)
    return d


@router.get("/stats", response_model=StatsOut, summary="项目统计")
async def project_stats(db: AsyncSession = Depends(get_db)):
    return StatsOut(**(await project_svc.stats(db)))


@router.get("", response_model=list[ProjectSummary], summary="项目列表")
async def list_projects(
    q: str = Query("", description="标题或 ID 关键字"),
    filter: str = Query("all", alias="filter", description="all | active | done | fail"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).order_by(Project.updated_at.desc()))
    items = list(result.scalars().all())
    if q:
        items = [p for p in items if q in p.title or q in p.id]
    # 先纠正运行态，再按筛选过滤（避免 generated 实已在跑却被漏掉）
    dirty = False
    for p in items:
        _, _, changed = project_svc.sync_project_runtime(p)
        if changed:
            dirty = True
    if filter == "active":
        # 「运行中」= 预览进程在跑（与列表「运行」列一致）
        items = [
            p
            for p in items
            if p.status == "running" or p.backend_running or p.frontend_running
        ]
    elif filter == "done":
        # 可交付 = 已生成/运行中且 ZIP 仍解锁（门禁回退后 zip_ready=False）
        items = [
            p
            for p in items
            if p.status in ("generated", "running") and p.zip_ready
        ]
    elif filter == "fail":
        items = [p for p in items if p.status == "failed"]
    # 须在 commit 前物化：commit 后 ORM 过期，Pydantic 再读字段会触发 MissingGreenlet
    summaries = [ProjectSummary.model_validate(p) for p in items]
    if dirty:
        await db.commit()
    return summaries


@router.post("/upload", response_model=ProjectDetail, summary="上传开题")
async def upload_proposal(file: UploadFile = File(..., description="开题文件 PDF / Word / TXT"), db: AsyncSession = Depends(get_db)):
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


@router.get("/{project_id}", response_model=ProjectDetail, summary="项目详情")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if project_svc.sync_checklist_from_workspace(p):
        await db.commit()
        await db.refresh(p)
    _, _, dirty = project_svc.sync_project_runtime(p)
    if dirty:
        await db.commit()
        await db.refresh(p)
    return _detail(p)


@router.patch("/{project_id}/match", response_model=ProjectDetail, summary="更新匹配")
async def patch_match(project_id: str, body: MatchUpdate, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    try:
        p = await project_svc.update_match(db, p, body)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _detail(p)


@router.post("/{project_id}/generate", response_model=ApiOk, summary="启动生成")
async def generate(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if not p.match_confirmed:
        raise HTTPException(400, "请先确认匹配")
    job = await start_job(db, p)
    return ApiOk(message=f"Job #{job.id} 已启动", data={"job_id": job.id})


@router.delete("/{project_id}", response_model=ApiOk, summary="删除项目")
async def delete_project(
    project_id: str,
    keep_db: bool = Query(False, description="为 true 时保留学生 MySQL 库"),
    db: AsyncSession = Depends(get_db),
):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    project_svc.sync_project_runtime(p)
    if p.status == ProjectStatus.generating.value or p.backend_running or p.frontend_running:
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


@router.get("/{project_id}/download", summary="下载 ZIP")
async def download_zip(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if p.status == "generating":
        raise HTTPException(403, "生成中 · 请等待打包完成后再下载")
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


@router.get("/{project_id}/schema", summary="库表结构")
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


@router.get("/{project_id}/apis", summary="学生端 API 清单")
async def get_apis(project_id: str, db: AsyncSession = Depends(get_db)):
    """学生端 REST 映射清单（静态扫描 Controller，供产物页对照）。"""
    from app.bake.api_inventory import load_api_inventory

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if not p.workspace_path:
        raise HTTPException(400, "尚未生成工作区")
    inv = load_api_inventory(Path(p.workspace_path), p.spec if isinstance(p.spec, dict) else None)
    if not inv:
        raise HTTPException(404, "未找到 Controller")
    return inv


@router.get("/{project_id}/schema/er.svg", summary="下载 E-R 图 SVG")
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
    svg = render_er_svg(model, title=f"实体联系图 · {p.db_name or project_id}")
    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{project_id}-er.svg"',
        },
    )


@router.get("/{project_id}/runtime", response_model=RuntimeState, summary="预览运行状态")
async def get_runtime(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    be_st, fe_st, dirty = project_svc.sync_project_runtime(p)
    if dirty:
        await db.commit()
        await db.refresh(p)
    s = get_settings()
    be_url = s.public_url(p.backend_port) if p.backend_port else None
    fe_url = s.public_url(p.frontend_port) if p.frontend_port else None
    return RuntimeState(
        backend_status=be_st,
        frontend_status=fe_st,
        backend_port=p.backend_port or 0,
        frontend_port=p.frontend_port or 0,
        public_host=s.public_host,
        project_status=p.status,
        preview_url=fe_url,
        backend_url=be_url,
        backend_log_tail=rt.backend_log(project_id),
        frontend_log_tail=rt.frontend_log(project_id),
    )


@router.post("/{project_id}/runtime/{side}/{action}", response_model=ApiOk, summary="预览启停")
async def runtime_action(
    project_id: str,
    side: str,
    action: str,
    db: AsyncSession = Depends(get_db),
):
    """side：all / backend / frontend；action：start / stop / restart。"""
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if not p.workspace_path:
        raise HTTPException(400, "尚未生成工作区")
    ws = Path(p.workspace_path)
    if not ws.exists():
        raise HTTPException(400, "工作区目录不存在")

    try:
        if action in ("start", "restart"):
            await project_svc.ensure_project_ports(db, p)

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
    project_svc.sync_project_runtime(p)
    await db.commit()
    return ApiOk(
        message=f"{side}/{action} 完成",
        data={
            "backend_port": p.backend_port,
            "frontend_port": p.frontend_port,
            "project_status": p.status,
        },
    )


@router.get("/{project_id}/logs/{side}", summary="读取日志")
async def get_logs(project_id: str, side: str, db: AsyncSession = Depends(get_db)):
    """side：job / backend / frontend / deepseek。"""
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
