"""答辩 PPT Job：start_ppt_job / run_ppt_job / cancel_ppt_job。

旁路挂在现网 Job 表 + FillEventHub + unit_flow（与填岛同级）：
- 禁止调用 bake 的 start_job；不得改 project.status / zip_ready
- 填页：unit_flow.run_plan_units（同 Semaphore / 预算 / 校验）
- 进度：Job 行真源；SSE channel=defense_ppt；日志写 append_log
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import SessionLocal
from app.models import Job, JobKind, JobStatus, Project
from app.services.fill_events import fill_event_hub
from app.services.jobs import (
    _fail_running_step,
    append_log,
    pop_running_task,
    register_running_task,
)

from .check import job_hard_failures, run_check_on_deck
from .cover import require_cover_complete
from .deck_io import load_cover, load_deck, load_skin, save_cover, save_deck, save_skin
from .evidence import assemble_evidence, collect_context, evidence_ready
from .fingerprint import clear_biz_dirty, save_fingerprint
from .job_fill import fill_deck_via_unit_flow
from .screenshots import capture_into_deck
from .themes import (
    default_steps,
    default_units,
    normalize_layout,
    normalize_master,
    normalize_theme,
)

logger = logging.getLogger("gf.defense_ppt")

_PPT_CHANNEL = "defense_ppt"


async def _emit(project_id: str, event: dict[str, Any]) -> None:
    await fill_event_hub.handle(project_id, event, channel=_PPT_CHANNEL)


async def start_ppt_job(
    db: AsyncSession,
    project: Project,
    *,
    cover: dict[str, Any] | None = None,
    theme: str | None = None,
    layout_family: str | None = None,
    master: str | None = None,
) -> Job:
    evidence = assemble_evidence(project)
    if not evidence_ready(evidence):
        raise PermissionError("程序未就绪或证据不全（与 ZIP 可下载同口径）")

    if cover:
        c = require_cover_complete(cover)
        save_cover(project, c)
    else:
        c = require_cover_complete(load_cover(project))

    skin = {
        "theme": normalize_theme(theme, project.id),
        "layout_family": normalize_layout(layout_family, project.id),
        "master": normalize_master(master),
    }
    save_skin(project, skin)

    q = await db.execute(
        select(Job).where(
            Job.project_id == project.id,
            Job.kind == JobKind.defense_ppt.value,
            Job.status.in_([JobStatus.queued.value, JobStatus.running.value]),
        )
    )
    for old in q.scalars().all():
        old.status = JobStatus.cancelled.value
        old.error = "已被新任务取代"
        old.finished_at = datetime.now()
        t = pop_running_task(old.id)
        if t:
            t.cancel()

    job = Job(
        project_id=project.id,
        kind=JobKind.defense_ppt.value,
        status=JobStatus.queued.value,
        step="queued",
        progress=0,
        steps=default_steps(),
        units=default_units(),
        error=None,
    )
    db.add(job)
    # 明确：不改 project.status / zip_ready
    await db.commit()
    await db.refresh(job)

    task = asyncio.create_task(run_ppt_job(job.id))
    register_running_task(job.id, task)

    def _on_done(t: asyncio.Task, jid: int = job.id) -> None:
        pop_running_task(jid)
        try:
            exc = t.exception()
        except asyncio.CancelledError:
            return
        if exc is not None:
            logger.exception("run_ppt_job 异常 · job #%s", jid, exc_info=exc)

    task.add_done_callback(_on_done)
    await append_log(project.id, f"defense_ppt · queued job #{job.id}")
    return job


async def cancel_ppt_job(db: AsyncSession, project: Project) -> Job | None:
    q = await db.execute(
        select(Job).where(
            Job.project_id == project.id,
            Job.kind == JobKind.defense_ppt.value,
            Job.status.in_([JobStatus.queued.value, JobStatus.running.value]),
        )
    )
    jobs = list(q.scalars().all())
    if not jobs:
        return None
    last = None
    for job in jobs:
        t = pop_running_task(job.id)
        if t:
            t.cancel()
        job.status = JobStatus.cancelled.value
        job.error = "已取消"
        job.steps = _fail_running_step(job.steps, "已取消")
        job.finished_at = datetime.now()
        last = job
    await db.commit()
    await append_log(project.id, "defense_ppt · cancelled")
    return last


def _unit_index(units: list[dict[str, Any]], unit_id: str) -> int:
    for i, u in enumerate(units):
        if u.get("key") == unit_id or u.get("id") == unit_id:
            return i
    return -1


async def run_ppt_job(job_id: int) -> None:
    async with SessionLocal() as db:
        job = await db.get(Job, job_id)
        if not job:
            return
        project = await db.get(Project, job.project_id)
        if not project:
            job.status = JobStatus.failed.value
            job.error = "项目不存在"
            await db.commit()
            return

        job.status = JobStatus.running.value
        job.started_at = datetime.now()
        job.error = None
        job.steps = default_steps()
        job.units = default_units()
        await db.commit()
        await append_log(project.id, f"defense_ppt · running job #{job_id}")

        deck: dict[str, Any] | None = None

        async def set_step(idx: int, status: str, meta: str = "") -> None:
            steps = list(job.steps or [])
            if idx < len(steps):
                steps[idx] = {**steps[idx], "status": status, "meta": meta}
            job.steps = steps
            flag_modified(job, "steps")
            job.step = steps[idx]["key"] if idx < len(steps) else job.step
            job.progress = int((idx + (1 if status == "done" else 0.4)) / max(len(steps), 1) * 90)
            await db.commit()
            await append_log(
                project.id,
                f"defense_ppt · {steps[idx]['key'] if idx < len(steps) else '?'} {status} {meta}".strip(),
            )

        async def sync_unit_from_event(event: dict[str, Any]) -> None:
            et = str(event.get("type") or "")
            uid = str(event.get("unit_id") or event.get("key") or "")
            units = list(job.units or [])
            if et == "ppt_plan":
                by_id = {
                    str(u.get("id") or u.get("key")): u
                    for u in (event.get("units") or [])
                    if isinstance(u, dict)
                }
                for u in units:
                    key = str(u.get("key") or "")
                    info = by_id.get(key) or {}
                    if info.get("title"):
                        u["title"] = info["title"]
                    u["status"] = "queued"
                job.units = units
                flag_modified(job, "units")
                await db.commit()
                return
            if not uid:
                return
            idx = _unit_index(units, uid)
            if idx < 0:
                return
            if et == "unit_started":
                units[idx] = {**units[idx], "status": "generating", "meta": ""}
                await append_log(project.id, f"defense_ppt · unit start {uid}")
            elif et == "unit_done":
                units[idx] = {**units[idx], "status": "done", "meta": ""}
            elif et == "unit_skipped":
                units[idx] = {**units[idx], "status": "done", "meta": "确定性/跳过"}
                await append_log(project.id, f"defense_ppt · unit skipped {uid}")
            elif et == "unit_failed":
                err = str(event.get("error") or "")[:80]
                units[idx] = {**units[idx], "status": "failed", "meta": err}
                await append_log(project.id, f"defense_ppt · unit failed {uid} · {err}")
            job.units = units
            flag_modified(job, "units")
            done_n = sum(1 for u in units if u.get("status") in ("done", "failed"))
            job.progress = min(85, 20 + int(done_n / max(len(units), 1) * 55))
            await db.commit()

        async def persist_partial(reason: str) -> None:
            """部分 Unit 失败 / 硬错误：仍落盘已成功页（指南 §6）。"""
            if not deck:
                return
            try:
                deck["biz_dirty"] = False
                await asyncio.to_thread(save_deck, project, deck)
                await asyncio.to_thread(clear_biz_dirty, project)
                await append_log(project.id, f"defense_ppt · partial deck saved · {reason}")
            except Exception as e:  # noqa: BLE001
                logger.warning("partial deck save failed: %s", e)

        try:
            await fill_event_hub.reset(project.id, channel=_PPT_CHANNEL)

            # 1 collect
            await set_step(0, "running", "组装证据")
            ctx = await asyncio.to_thread(collect_context, project)
            await asyncio.to_thread(save_fingerprint, project)
            await set_step(0, "done", "证据已齐")

            # 2 fill（unit_flow，与填岛同预算/并发）
            await set_step(1, "running", "填页 Unit")
            cover = load_cover(project)
            skin = load_skin(project)
            old = load_deck(project)

            async def on_event(event: dict[str, Any]) -> None:
                await _emit(project.id, event)
                await sync_unit_from_event(event)

            deck, summary = await fill_deck_via_unit_flow(
                db,
                project,
                ctx,
                cover=cover,
                theme=skin["theme"],
                layout_family=skin["layout_family"],
                master=skin["master"],
                llm_enabled=True,
                on_event=on_event,
                old_deck=old,
            )
            meta = (
                f"{summary.done}/{len(summary.results)} 单元"
                + (f" · 失败 {summary.failed}" if summary.failed else "")
            )
            await set_step(1, "done", meta)

            # 3 screenshots（半自动主路径；失败标 missing，不阻断写盘）
            await set_step(2, "running", "半自动采图")
            demo = next(
                (
                    p
                    for p in (deck.get("pages") or [])
                    if isinstance(p, dict) and p.get("role") == "demo"
                ),
                None,
            )
            already = (
                isinstance((demo or {}).get("figure"), dict)
                and demo["figure"].get("available")
                and not demo["figure"].get("missing")
            )
            if already:
                await set_step(2, "done", "已有截图")
            else:
                cap = await capture_into_deck(project, deck)
                if cap.get("ok"):
                    await set_step(2, "done", "已采截图")
                else:
                    hint = (cap.get("figure") or {}).get("hint") or "待上传截图"
                    await set_step(2, "done", str(hint)[:80])

            # 4 check（与导出门闩同源；demo_shot 不阻生成成功）
            await set_step(3, "running", "瞎写/结构检查")
            check_result = run_check_on_deck(project, deck)
            hard = job_hard_failures(check_result)
            soft_errs = [
                i["message"]
                for i in (check_result.get("items") or [])
                if i.get("level") == "error" and i.get("code") not in (
                    "structure",
                    "hallucination",
                    "no_deck",
                    "gates",
                )
            ]
            if hard:
                await set_step(3, "done", hard[0][:80])
                await persist_partial(hard[0])
                job.status = JobStatus.failed.value
                job.error = hard[0][:280]
                job.progress = 100
                job.finished_at = datetime.now()
                await db.commit()
                await _emit(project.id, {"type": "ppt_failed", "error": job.error})
                await append_log(project.id, f"defense_ppt · FAILED · {job.error}")
                return
            note = soft_errs[0] if soft_errs else "结构通过"
            await set_step(3, "done", note[:80])

            # 5 write
            await set_step(4, "running", "写 deck.json")
            deck["biz_dirty"] = False
            await asyncio.to_thread(save_deck, project, deck)
            await asyncio.to_thread(clear_biz_dirty, project)
            await set_step(4, "done", "已写入")

            job.status = JobStatus.success.value
            job.progress = 100
            job.finished_at = datetime.now()
            if summary.failed:
                job.error = f"部分页失败 {summary.failed}（已保留成功页）"
            await db.commit()
            await _emit(project.id, {"type": "ppt_complete"})
            await append_log(project.id, "defense_ppt · SUCCESS")
        except asyncio.CancelledError:
            await persist_partial("cancelled")
            job.status = JobStatus.cancelled.value
            job.error = "已取消"
            job.steps = _fail_running_step(job.steps, "已取消")
            job.finished_at = datetime.now()
            await db.commit()
            await _emit(project.id, {"type": "ppt_failed", "error": "已取消"})
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("defense_ppt job #%s failed", job_id)
            await persist_partial(str(exc)[:80])
            job.status = JobStatus.failed.value
            job.error = str(exc)[:280]
            job.steps = _fail_running_step(job.steps, job.error)
            job.finished_at = datetime.now()
            await db.commit()
            await _emit(project.id, {"type": "ppt_failed", "error": job.error})
            await append_log(project.id, f"defense_ppt · ERROR {job.error}")
