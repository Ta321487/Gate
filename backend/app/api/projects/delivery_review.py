"""项目 API 子路由：挂到 common.router（prefix=/api/projects）。"""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from pathlib import Path
from typing import Optional

from fastapi import Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models import Job, Project, ProjectStatus
from app.schemas import (
    ApiOk,
    ClassLayoutUpdate,
    DeliveryMarkUpdate,
    DeliveryQaOut,
    DeliveryReviewPanelOut,
    DeliveryVerifyOut,
    ErLabelsUpdate,
    ErViewUpdate,
    FixNoteCreate,
    FixNoteResolve,
    MatchUpdate,
    ProjectDetail,
    ProjectSummary,
    ProposalDiffOut,
    RuntimeBatchIn,
    RuntimeState,
    StatsOut,
    UploadConfirmIn,
    UploadConfirmOut,
    UploadPlanOut,
)
from app.services import projects as project_svc
from app.services import runtime as rt
from app.services.jobs import start_job
from app.services.student_db import drop_student_database

from app.api.projects.common import (
    MAX_UPLOAD_MATERIALS,
    _detail,
    _workspace_or_400,
    logger,
    router,
)

@router.get("/{project_id}/proposal-diff", response_model=ProposalDiffOut, summary="生成前 · 开题措辞核对")
async def get_proposal_diff(project_id: str, db: AsyncSession = Depends(get_db)):
    from app.services.proposal import load_merged_proposal_text
    from app.services.proposal_diff import build_proposal_diff

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    proposal = ""
    if p.source_path:
        try:
            proposal = load_merged_proposal_text(p.source_path) or ""
        except Exception:  # noqa: BLE001
            proposal = ""
    diff = build_proposal_diff(dict(p.spec or {}), proposal)
    from app.services.delivery_review import get_review_state

    st = get_review_state(p)
    return ProposalDiffOut(**{**diff, "pre_generate_ack_at": st.get("pre_generate_ack_at")})


@router.post("/{project_id}/delivery-review/ack-pre-generate", response_model=ApiOk, summary="确认开题 diff")
async def ack_pre_generate_review(project_id: str, db: AsyncSession = Depends(get_db)):
    from app.services.delivery_review import ack_pre_generate

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    st = ack_pre_generate(p)
    await db.commit()
    return ApiOk(message="已确认开题措辞核对 · 可启动一键生成", data={"review": st})


@router.get("/{project_id}/delivery-review", response_model=DeliveryReviewPanelOut, summary="交付复审状态")
async def get_delivery_review(project_id: str, db: AsyncSession = Depends(get_db)):
    from app.services.delivery_review import build_review_payload

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws, reason = project_svc.workspace_or_reason(p)
    if reason and not ws:
        raise HTTPException(400, reason)
    return build_review_payload(p, ws)


@router.post("/{project_id}/delivery-review/start", response_model=ApiOk, summary="进入交付复审")
async def start_delivery_review(project_id: str, db: AsyncSession = Depends(get_db)):
    from app.services.delivery_review import start_review

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if not p.workspace_path:
        raise HTTPException(400, "尚未生成工作区")
    st = start_review(p)
    project_svc.reset_delivery_mark(p)
    p.zip_ready = False
    await db.commit()
    return ApiOk(message="已进入交付复审 · 请登记偏差并完成验圈", data={"review": st})


@router.post("/{project_id}/delivery-review/close", response_model=ApiOk, summary="结束交付复审")
async def close_delivery_review(project_id: str, db: AsyncSession = Depends(get_db)):
    from app.services.delivery_review import close_review

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    st = close_review(p)
    await db.commit()
    return ApiOk(message="已结束交付复审", data={"review": st})


@router.post("/{project_id}/delivery-review/notes", response_model=ApiOk, summary="登记复审偏差")
async def add_delivery_fix_note(
    project_id: str,
    body: FixNoteCreate,
    db: AsyncSession = Depends(get_db),
):
    from app.services.delivery_review import add_fix_note

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    note = add_fix_note(p, body.text)
    project_svc.reset_delivery_mark(p)
    await db.commit()
    return ApiOk(message="已登记复审偏差", data={"note": note})


@router.patch(
    "/{project_id}/delivery-review/notes/{note_id}",
    response_model=ApiOk,
    summary="更新复审偏差状态",
)
async def resolve_delivery_fix_note(
    project_id: str,
    note_id: str,
    body: FixNoteResolve,
    db: AsyncSession = Depends(get_db),
):
    from app.services.delivery_review import resolve_fix_note

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if not resolve_fix_note(p, note_id, done=body.done):
        raise HTTPException(404, "未找到该偏差项")
    await db.commit()
    return ApiOk(message="已更新偏差状态")


@router.post("/{project_id}/delivery-review/verify", response_model=DeliveryVerifyOut, summary="验圈（重跑门禁与单调性）")
async def verify_delivery_review(project_id: str, db: AsyncSession = Depends(get_db)):
    from app.llm.agents import run_qa_agent
    from app.llm.runtime import load_llm_runtime
    from app.services.delivery_review import (
        get_review_state,
        is_zip_stale,
        open_fix_notes,
        save_review_state,
        verify_round,
    )

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    if p.status == ProjectStatus.generating.value:
        raise HTTPException(409, "生成中 · 请稍后再验圈")
    llm_rt = await load_llm_runtime(db)
    try:
        qa = await run_qa_agent(
            db,
            llm_rt,
            project_id=p.id,
            workspace=ws,
            spec=p.spec if isinstance(p.spec, dict) else {},
        )
        st = get_review_state(p)
        st["last_qa"] = qa
        save_review_state(p, st)
    except Exception as qe:  # noqa: BLE001
        logger.debug("verify QA skip · %s", qe)
    result = verify_round(p, ws)
    # 勿经 delivery_block_reason 反推：它自身依赖 zip_ready，会形成「永远升不上去」
    zip_exists = bool(p.zip_path and Path(str(p.zip_path)).exists())
    st = get_review_state(p)
    ready = (
        bool(result.get("round_pass"))
        and bool(result.get("monotonic_ok"))
        and project_svc.gates_allow_delivery(p.gates)
        and zip_exists
        and not is_zip_stale(p, ws)
        and not open_fix_notes(st)
    )
    if not result.get("monotonic_ok"):
        project_svc.reset_delivery_mark(p)
    p.zip_ready = ready
    await db.commit()
    await db.refresh(p)
    result["download_blocked_reason"] = project_svc.delivery_block_reason(p)
    result["zip_ready"] = p.zip_ready
    return DeliveryVerifyOut(**result)


@router.post("/{project_id}/delivery-review/repack", response_model=ApiOk, summary="合卷（重打学生 ZIP）")
async def repack_delivery_review(project_id: str, db: AsyncSession = Depends(get_db)):
    from app.bake.naming import resolve_slug_from_spec, zip_storage_name
    from app.services.delivery_review import can_repack_after_verify, repack_project, verify_round

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    last = verify_round(p, ws)
    ok, msg = can_repack_after_verify(last, last.get("review") or {})
    if not ok:
        await db.commit()
        raise HTTPException(400, msg)
    if not project_svc.gates_allow_delivery(p.gates):
        await db.commit()
        raise HTTPException(400, "质量检查未通过 · 暂不可合卷")
    settings = get_settings()
    slug = resolve_slug_from_spec(p.spec, p.domain)
    zip_path = settings.workspace_dir / zip_storage_name(p.id, slug)
    meta = repack_project(p, ws, zip_path)
    p.zip_path = str(zip_path)
    p.zip_ready = True
    p.status = ProjectStatus.generated.value
    await db.commit()
    return ApiOk(message="合卷完成 · 交付包已与当前工程同步", data=meta)


@router.post("/{project_id}/delivery-review/qa", response_model=DeliveryQaOut, summary="重跑交付质量摘要")
async def run_delivery_qa(project_id: str, db: AsyncSession = Depends(get_db)):
    from app.llm.agents import run_qa_agent
    from app.llm.runtime import load_llm_runtime
    from app.services.delivery_review import get_review_state, save_review_state, verify_round

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    llm_rt = await load_llm_runtime(db)
    qa = await run_qa_agent(
        db,
        llm_rt,
        project_id=p.id,
        workspace=ws,
        spec=p.spec if isinstance(p.spec, dict) else {},
    )
    st = get_review_state(p)
    st["last_qa"] = qa
    save_review_state(p, st)
    verify_round(p, ws)
    project_svc.reset_delivery_mark(p)
    p.zip_ready = False
    await db.commit()
    return DeliveryQaOut(
        qa=qa,
        gates=p.gates or {},
        download_blocked_reason=project_svc.delivery_block_reason(p),
    )


@router.post("/{project_id}/scrub-student-copy", response_model=ApiOk, summary="清洗学生可见工厂腔")
async def scrub_student_copy(project_id: str, db: AsyncSession = Depends(get_db)):
    """复用 bake 同源 scrub，回写 schema / appDelivered；不手改业务源码。"""
    from app.services.student_copy import scrub_project_student_copy

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if p.status == ProjectStatus.generating.value:
        raise HTTPException(409, "生成中 · 请稍后再清洗文案")
    try:
        result = scrub_project_student_copy(p)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    project_svc.reset_delivery_mark(p)
    await db.commit()
    await db.refresh(p)
    return ApiOk(
        message="已清洗学生可见文案 · 请验圈后合卷"
        if result.get("copy_ok") and result.get("semantic_ok", True)
        else "已尝试清洗 · 仍有残留（见命中路径；请确认后端已加载最新 scrub）",
        data=result,
    )


@router.get("/{project_id}/delivery-review/handoff", summary="导出运营交接包")
async def export_delivery_handoff(project_id: str, db: AsyncSession = Depends(get_db)):
    from fastapi.responses import Response

    from app.services.delivery_review import build_operator_handoff_zip

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws, _ = project_svc.workspace_or_reason(p)
    data = build_operator_handoff_zip(p, ws)
    fname = f"{p.id}-handoff.zip"
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
