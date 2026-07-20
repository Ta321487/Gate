from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Job, Project
from app.schemas import ApiOk, JobOut
from app.services.jobs import cancel_job, resume_step_index, start_job

router = APIRouter(prefix="/api/jobs", tags=["任务"])


@router.get("", response_model=list[JobOut], summary="任务列表")
async def list_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).order_by(Job.id.desc()).limit(100))
    jobs = list(result.scalars().all())
    out = []
    for j in jobs:
        item = JobOut.model_validate(j)
        p = await db.get(Project, j.project_id)
        item.project_title = p.title if p else None
        out.append(item)
    return out


@router.post("/purge-orphans", response_model=ApiOk, summary="清理孤儿任务")
async def purge_orphans(db: AsyncSession = Depends(get_db)):
    """删除 project_id 已不存在对应项目的任务。"""
    result = await db.execute(
        delete(Job).where(Job.project_id.notin_(select(Project.id)))
    )
    await db.commit()
    n = result.rowcount or 0
    return ApiOk(message=f"已清空 {n} 条孤儿任务", data={"deleted": n})


@router.get("/{job_id}", response_model=JobOut, summary="任务详情")
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    j = await db.get(Job, job_id)
    if not j:
        raise HTTPException(404, "任务不存在")
    item = JobOut.model_validate(j)
    p = await db.get(Project, j.project_id)
    item.project_title = p.title if p else None
    return item


@router.post("/{job_id}/cancel", response_model=ApiOk, summary="取消任务")
async def cancel(job_id: int, db: AsyncSession = Depends(get_db)):
    ok = await cancel_job(db, job_id)
    if not ok:
        raise HTTPException(404, "任务不存在")
    return ApiOk(message="已取消")


@router.post("/{job_id}/retry", response_model=ApiOk, summary="重试任务")
async def retry(job_id: int, db: AsyncSession = Depends(get_db)):
    old = await db.get(Job, job_id)
    if not old:
        raise HTTPException(404, "任务不存在")
    p = await db.get(Project, old.project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if not p.match_confirmed:
        raise HTTPException(400, "请先确认匹配")
    from_step = resume_step_index(old.steps if isinstance(old.steps, list) else None)
    # 工作区没了则无法跳过 bake
    if from_step > 1 and (not p.workspace_path or not Path(p.workspace_path).exists()):
        from_step = 1
    job = await start_job(db, p, from_step=from_step)
    step_name = (old.steps or [{}])[from_step].get("title") if from_step else "开头"
    if from_step and isinstance(old.steps, list) and from_step < len(old.steps):
        step_name = old.steps[from_step].get("title") or step_name
    return ApiOk(
        message=f"已从「{step_name}」续跑 · Job #{job.id}",
        data={"job_id": job.id, "from_step": from_step},
    )
