from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Job, Project
from app.schemas import (
    ApiOk,
    FailAnalysisClassifyIn,
    FailAnalysisFixDraftIn,
    JobOut,
)
from app.services.bake_fail_analysis import (
    build_fail_analysis,
    classify_assist,
    create_fix_draft,
    discard_fix_draft,
    ensure_error_code,
    get_fix_draft,
)
from app.services.bake_fail_classify import catalog_payload
from app.services.jobs import cancel_job, resume_step_index, start_job

router = APIRouter(prefix="/api/jobs", tags=["任务"])


def _job_out(j: Job, title: str | None = None) -> JobOut:
    item = JobOut.model_validate(j)
    if not item.error_code and j.error:
        item.error_code = ensure_error_code(j)
    item.project_title = title
    return item


@router.get("", response_model=list[JobOut], summary="任务列表")
async def list_jobs(db: AsyncSession = Depends(get_db)):
    """仅列出程序生成（bake）任务；答辩 PPT 走 /defense-ppt/job。"""
    result = await db.execute(select(Job).order_by(Job.id.desc()).limit(200))
    jobs = [
        j
        for j in result.scalars().all()
        if str(getattr(j, "kind", None) or "bake") == "bake"
    ][:100]
    out = []
    for j in jobs:
        p = await db.get(Project, j.project_id)
        out.append(_job_out(j, p.title if p else None))
    return out


@router.get("/fail-analysis", summary="失败分析")
async def fail_analysis(
    db: AsyncSession = Depends(get_db),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    domain: Optional[str] = None,
    step: Optional[str] = None,
    code: Optional[str] = None,
    sample_page: int = Query(1, ge=1),
    sample_page_size: int = Query(10, ge=1, le=100),
) -> dict[str, Any]:
    """出包失败分布、优先处理项与样本（样本服务端分页）。"""
    return await build_fail_analysis(
        db,
        date_from=date_from,
        date_to=date_to,
        domain=domain,
        step=step,
        code=code,
        sample_page=sample_page,
        sample_page_size=sample_page_size,
    )


@router.get("/fail-analysis/catalog", summary="失败分析·类型对照表")
async def fail_analysis_catalog() -> list[dict[str, str]]:
    """失败类型索引（与码表同源），供帮助页对照查询。"""
    return catalog_payload()


@router.post("/fail-analysis/classify-assist", summary="失败分析·类型建议")
async def fail_analysis_classify_assist(
    body: FailAnalysisClassifyIn,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """按需给出失败类型建议；只回已有类型，不含修法。"""
    try:
        return await classify_assist(db, error=body.error, step=body.step)
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/fail-analysis/fix-draft", summary="失败分析·处理建议")
async def fail_analysis_fix_draft(
    body: FailAnalysisFixDraftIn,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """按需生成处理建议草稿；不写入类型表。"""
    try:
        return await create_fix_draft(
            db,
            job_id=body.job_id,
            error=body.error,
            code=body.code,
            force=body.force,
        )
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/fail-analysis/fix-draft/{job_id}", summary="失败分析·读取建议")
async def fail_analysis_get_draft(job_id: int) -> dict[str, Any]:
    draft = get_fix_draft(job_id)
    if not draft:
        raise HTTPException(404, "暂无处理建议")
    return draft


@router.delete("/fail-analysis/fix-draft/{job_id}", response_model=ApiOk, summary="失败分析·清除建议")
async def fail_analysis_discard_draft(job_id: int):
    ok = discard_fix_draft(job_id)
    if not ok:
        raise HTTPException(404, "暂无处理建议")
    return ApiOk(message="已清除处理建议", data={"job_id": job_id})


@router.post("/purge-orphans", response_model=ApiOk, summary="清理失效任务")
async def purge_orphans(db: AsyncSession = Depends(get_db)):
    """删除项目已不存在的失效任务。"""
    result = await db.execute(
        delete(Job).where(Job.project_id.notin_(select(Project.id)))
    )
    await db.commit()
    n = result.rowcount or 0
    return ApiOk(message=f"已清理 {n} 条失效任务", data={"deleted": n})


@router.post("/purge-finished", response_model=ApiOk, summary="清空历史任务")
async def purge_finished(db: AsyncSession = Depends(get_db)):
    """删除 bake 的 success / failed / cancelled；不影响进行中，也不清答辩 PPT 任务。"""
    result = await db.execute(
        delete(Job).where(
            Job.status.in_(("success", "failed", "cancelled")),
            Job.kind == "bake",
        )
    )
    await db.commit()
    n = result.rowcount or 0
    return ApiOk(message=f"已清空 {n} 条历史任务", data={"deleted": n})


@router.delete("/{job_id}", response_model=ApiOk, summary="删除单条任务")
async def delete_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """删除已结束任务；进行中须先取消。"""
    j = await db.get(Job, job_id)
    if not j:
        raise HTTPException(404, "任务不存在")
    if j.status in ("queued", "running"):
        raise HTTPException(400, "请先取消进行中的任务，再删除")
    await db.delete(j)
    await db.commit()
    return ApiOk(message=f"已删除任务 #{job_id}", data={"deleted": 1})


@router.get("/{job_id}", response_model=JobOut, summary="任务详情")
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    j = await db.get(Job, job_id)
    if not j:
        raise HTTPException(404, "任务不存在")
    p = await db.get(Project, j.project_id)
    return _job_out(j, p.title if p else None)


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
    if old.status in ("queued", "running"):
        raise HTTPException(400, "任务进行中 · 请先取消再重试")
    p = await db.get(Project, old.project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if not p.match_confirmed:
        raise HTTPException(400, "请先确认匹配")
    from_step = resume_step_index(old.steps if isinstance(old.steps, list) else None)
    # 工作区没了则无法跳过 bake
    if from_step > 1 and (not p.workspace_path or not Path(p.workspace_path).exists()):
        from_step = 1
    try:
        job = await start_job(db, p, from_step=from_step)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    step_name = (old.steps or [{}])[from_step].get("title") if from_step else "开头"
    if from_step and isinstance(old.steps, list) and from_step < len(old.steps):
        step_name = old.steps[from_step].get("title") or step_name
    return ApiOk(
        message=f"已从「{step_name}」续跑 · Job #{job.id}",
        data={"job_id": job.id, "from_step": from_step},
    )
