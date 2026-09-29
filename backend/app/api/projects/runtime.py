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
    preview_blocked = project_svc.preview_start_block_reason(p)
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
        preview_allowed=preview_blocked is None,
        preview_blocked_reason=preview_blocked,
    )


def _project_brief(p: Project) -> dict:
    return {"id": p.id, "title": p.title}


async def _batch_stop(
    db: AsyncSession,
    targets: list[Project],
    side: str,
    items: list[dict],
) -> dict:
    """批量停止（双证据）：STORE 句柄 taskkill /T + 现探 LISTENING 端口。

    整批只做一次 netstat 快照（避免逐端口重复探测）；收敛用停止后的新快照
    （probe_http=False），全部阻塞动作都在 to_thread 里，不冻结事件循环。
    """
    snap = await asyncio.to_thread(rt.listening_ports_with_pids)
    listening = set(snap)
    plan: list[tuple[Project, bool, bool]] = []
    for p in targets:
        be_on = rt.side_active(p.id, p.backend_port or None, "backend", listening)
        fe_on = rt.side_active(p.id, p.frontend_port or None, "frontend", listening)
        touch_be = side in ("all", "backend") and be_on
        touch_fe = side in ("all", "frontend") and fe_on
        if not touch_be and not touch_fe:
            items.append(
                {**_project_brief(p), "action": "stop", "ok": False, "reason": "未在运行"}
            )
            continue
        plan.append((p, touch_be, touch_fe))
        items.append({**_project_brief(p), "action": "stop", "ok": True, "reason": ""})

    def _kill_them() -> None:
        for p, touch_be, touch_fe in plan:
            if touch_be:
                rt.stop_backend(p.id, p.backend_port or None, listening_pids=snap)
            if touch_fe:
                rt.stop_frontend(p.id, p.frontend_port or None, listening_pids=snap)
        if plan:
            # 等端口/句柄释放，避免随后收敛读到 kill 之前的 LISTENING
            time.sleep(0.6)

    if plan:
        await asyncio.to_thread(_kill_them)
    after = await asyncio.to_thread(rt.listening_tcp_ports)
    still = 0
    for p, _be, _fe in plan:
        if rt.side_active(p.id, p.backend_port or None, "backend", after) or rt.side_active(
            p.id, p.frontend_port or None, "frontend", after
        ):
            still += 1
    for p, _be, _fe in plan:
        project_svc.sync_project_runtime(p, listening=after, probe_http=False)
    await db.commit()
    return {"stopped": len(plan), "still_running": still}


async def _batch_start(
    db: AsyncSession,
    targets: list[Project],
    action: str,
    side: str,
    items: list[dict],
) -> dict:
    """批量启动/重启：两道闸门 + 并发额度 + 可用内存预检 + 相邻错峰。

    start_backend/start_frontend 内部先 stop，故 start 对运行中的项目等价「重启」。
    """
    settings = get_settings()
    result = await db.execute(select(Project))
    all_projects = list(result.scalars().all())

    def _running_count() -> int:
        listening = rt.listening_tcp_ports()
        return sum(
            1
            for q in all_projects
            if rt.side_active(q.id, q.backend_port or None, "backend", listening)
            or rt.side_active(q.id, q.frontend_port or None, "frontend", listening)
        )

    running, avail = await asyncio.gather(
        asyncio.to_thread(_running_count), asyncio.to_thread(rt.available_memory_mb)
    )
    budget = max(0, settings.gf_preview_max_running - running)
    # 单预览实测 ≈1.1 GB（含 Maven 启动器 JVM）；可用内存不够时不硬起
    mem_cap = None if avail is None else max(0, avail // 1100)
    allow = budget if mem_cap is None else min(budget, mem_cap)

    todo: list[Project] = []
    for p in targets:
        blocked = project_svc.preview_start_block_reason(p)
        if blocked:
            items.append(
                {**_project_brief(p), "action": action, "ok": False, "reason": blocked}
            )
            continue
        if len(todo) >= allow:
            if mem_cap is not None and mem_cap < budget:
                reason = f"可用内存不足（空闲约 {avail} MB，单预览约 1.1 GB）"
            else:
                reason = (
                    f"并发额度已满（上限 {settings.gf_preview_max_running}，"
                    f"当前已运行 {running}）"
                )
            items.append(
                {
                    **_project_brief(p),
                    "action": action,
                    "ok": False,
                    "reason": reason,
                    "deferred": True,
                }
            )
            continue
        try:
            await project_svc.ensure_project_ports(db, p)
        except RuntimeError as e:
            items.append(
                {**_project_brief(p), "action": action, "ok": False, "reason": str(e)}
            )
            continue
        items.append({**_project_brief(p), "action": action, "ok": True, "reason": ""})
        todo.append(p)

    stagger = max(0.0, settings.gf_preview_start_stagger_sec)

    def _start_them() -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
        errs: dict[str, str] = {}
        statuses: dict[str, tuple[str, str]] = {}
        for i, p in enumerate(todo):
            if i and stagger:
                time.sleep(stagger)
            ws = project_svc.resolve_workspace_dir(p)
            try:
                if side in ("all", "backend"):
                    rt.start_backend(p.id, ws, p.backend_port, p.db_name or "")
                if side in ("all", "frontend"):
                    rt.start_frontend(p.id, ws, p.frontend_port, p.backend_port)
            except Exception as e:  # noqa: BLE001
                errs[p.id] = str(e)
                continue
            statuses[p.id] = (
                rt.backend_status(p.id, p.backend_port),
                rt.frontend_status(p.id, p.frontend_port),
            )
        return errs, statuses

    if todo:
        errs, statuses = await asyncio.to_thread(_start_them)
    else:
        errs, statuses = {}, {}
    for p in todo:
        if p.id in errs:
            for it in items:
                if it["id"] == p.id and it["action"] == action:
                    it["ok"] = False
                    it["reason"] = errs[p.id][:200]
            continue
        st = statuses.get(p.id)
        if st:
            project_svc.sync_project_runtime(p, statuses=st)
    await db.commit()
    return {"failed": len(errs), "available_memory_mb": avail}


@router.post("/runtime/batch", response_model=ApiOk, summary="批量预览启停")
async def runtime_batch(body: RuntimeBatchIn, db: AsyncSession = Depends(get_db)):
    """批量启停预览；整批阻塞动作全部跑在 to_thread，工厂 API 不冻结。

    - action=stop：双证据清理（STORE 句柄 taskkill /T + 现探 LISTENING），未在跑的项目跳过；
      未传 ids 时作用域 =「运行中」口径 + 真实占用探测。
    - action=start / restart：须显式选择项目；逐项过 preview_start_block_reason 与
      并发额度 / 可用内存闸门，超出额度的项目返回 deferred（不硬起）。
      注意 start 对运行中的项目等价重启（start_backend/start_frontend 内部先停）。
    """
    action, side = body.action, body.side
    ids = [i for i in (body.ids or []) if i]
    if action in ("start", "restart") and not ids:
        raise HTTPException(400, "批量启动需要先选择项目")

    result = await db.execute(select(Project))
    all_projects = list(result.scalars().all())
    by_id = {p.id: p for p in all_projects}
    items: list[dict] = []
    if ids:
        targets = [by_id[i] for i in ids if i in by_id]
        for i in ids:
            if i not in by_id:
                items.append(
                    {
                        "id": i,
                        "title": "",
                        "action": action,
                        "ok": False,
                        "reason": "项目不存在",
                    }
                )
    else:
        # 「运行中」口径（列表 filter=active）+ 端口仍被占用：库内标记漂移时也不漏
        targets = [
            p
            for p in all_projects
            if p.status == ProjectStatus.running.value
            or p.backend_running
            or p.frontend_running
            or p.backend_port
            or p.frontend_port
        ]

    if not targets and not items:
        return ApiOk(
            message="当前没有运行中的预览" if action == "stop" else "没有可执行的项目",
            data={
                "action": action,
                "side": side,
                "total": 0,
                "done": 0,
                "skipped": 0,
                "items": [],
            },
        )

    if action == "stop":
        stats = await _batch_stop(db, targets, side, items)
    else:
        stats = await _batch_start(db, targets, action, side, items)

    done = sum(1 for it in items if it.get("ok"))
    skipped = len(items) - done
    head = "已关闭" if action == "stop" else ("已重启" if action == "restart" else "已启动")
    message = f"{head} {done} 个项目"
    if action == "stop" and stats.get("still_running"):
        message += f"；{stats['still_running']} 个仍占用端口（可稍后重试）"
    if skipped:
        message += f"；跳过 {skipped} 个（见明细）"
    if action != "stop" and stats.get("available_memory_mb") is not None:
        message += f" · 空闲内存约 {stats['available_memory_mb']} MB"
    return ApiOk(
        message=message,
        data={
            "action": action,
            "side": side,
            "total": len(items),
            "done": done,
            "skipped": skipped,
            "items": items,
            **stats,
        },
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
    if action in ("start", "restart"):
        blocked = project_svc.preview_start_block_reason(p)
        if blocked:
            raise HTTPException(400, blocked)
    ws = _workspace_or_400(p)

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


@router.get("/{project_id}/fill-plan", summary="填岛拆解计划（不调 LLM）")
async def get_fill_plan(project_id: str, db: AsyncSession = Depends(get_db)):
    """返回 DeliveryPlan：各 Unit 任务列表，供运营核对拆解粒度。"""
    from pathlib import Path

    from app.llm.unit_flow import build_plan_only
    from app.services.proposal import load_merged_proposal_text

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if not p.workspace_path:
        raise HTTPException(400, "请先生成工作区")
    ws = Path(p.workspace_path)
    if not ws.is_dir():
        raise HTTPException(400, "工作区不存在")
    spec = dict(p.spec or {})
    proposal = ""
    if p.source_path:
        try:
            proposal = load_merged_proposal_text(p.source_path)
        except Exception:  # noqa: BLE001
            proposal = ""
    plan = build_plan_only(ws, spec, proposal)
    return ApiOk(
        message=f"共 {len(plan.units)} 个 Unit",
        data={"plan": plan.to_dict(), "artifact": "islands/unit_flow/plan.json"},
    )


@router.get("/{project_id}/fill-events", summary="填岛进度 SSE")
async def stream_fill_events(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """业务配置填充阶段的 Unit 实时进度；首帧为快照，断线可重连恢复。"""
    import json

    from app.services.fill_events import fill_event_hub

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")

    async def events():
        async for event in fill_event_hub.subscribe(project_id):
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

