"""生成 Job：bake 为主，LLM 分岛，门禁后打包。"""

from __future__ import annotations

import asyncio
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.bake.engine import bake_project
from app.bake.gates import evaluate_domain_gates
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.llm.agents import (
    run_fix_agent,
    run_qa_agent,
    run_spec_agent,
)
from app.llm.unit_flow import format_fill_step_meta, run_fill_pipeline
from app.llm.runtime import load_llm_runtime
from app.models import Job, JobKind, JobStatus, Project, ProjectStatus
from app.services.projects import MSG_DOWNLOAD_GATES
from app.services.proposal import load_merged_proposal_text
from app.services.delivery_review import (
    apply_qa_to_gates,
    evaluate_workspace_gates,
    finalize_pack,
    forbid_full_rebake,
)

logger = logging.getLogger("gf.job")

STEP_DEFS = [
    ("parse_merge", "解析开题 · 合并 Spec"),
    ("copy_bake", "复制骨架 · 领域 SQL"),
    ("island_fill", "业务配置填充"),
    ("build_verify", "构建验证"),
    ("gate_e2e", "门禁：登录 + 主流程"),
    ("pack", "清单验收 · 打包 ZIP"),
]


def _default_steps() -> list[dict[str, Any]]:
    # pending 与前端 step-rail CSS 对齐（旧数据 wait 由前端兼容）
    return [{"key": k, "title": t, "status": "pending", "meta": ""} for k, t in STEP_DEFS]


def resume_step_index(steps: list[dict[str, Any]] | None) -> int:
    """失败/中断续跑起点：首个非 done 的步骤；全成功则 0。"""
    if not steps:
        return 0
    for i, s in enumerate(steps):
        st = str((s or {}).get("status") or "pending")
        if st != "done":
            return i
    return 0


def _short_error(exc: BaseException | str, *, limit: int = 280) -> str:
    text = str(exc).strip() or "未知错误"
    text = " ".join(text.split())
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def _gate_fail_summary(gates: dict[str, Any] | None) -> str:
    """优先可接题边界 / 首个未过项文案；勿把已通过的 p2.detail 整包甩进日志。"""
    g = gates or {}
    acc = g.get("accept")
    if isinstance(acc, dict) and acc.get("ok") is False:
        return _short_error(acc.get("desc") or acc.get("label") or "可接题边界未通过", limit=200)
    # 含 p3q（QA）/ p3s（语义）；漏列时 overall=False 会落到笼统「主流程或功能清单未通过」
    for k in ("p3c", "p3d", "p3t", "p3q", "p3s", "p3a", "p3b", "p2", "p1", "p0b", "p0a"):
        item = g.get(k)
        if not isinstance(item, dict) or item.get("ok") is not False:
            continue
        label = item.get("label") or k
        desc = item.get("desc")
        if desc:
            return _short_error(f"{label} · {desc}", limit=200)
        detail = item.get("detail")
        if isinstance(detail, dict):
            bad = []
            if detail.get("files_ok") is False:
                bad.append("缺文件")
            if detail.get("missing"):
                bad.append("missing=" + ",".join(str(x) for x in detail["missing"][:6]))
            if detail.get("missing_routes"):
                bad.append("缺路由")
            if detail.get("logic") is False:
                bad.append("主路径逻辑")
            if detail.get("routes") is False:
                bad.append("路由")
            if bad:
                return _short_error(f"{label} · " + "；".join(bad), limit=200)
        return _short_error(label, limit=200)
    return "主流程或功能清单未通过"


_MODE_ZH = {
    "llm": "大模型",
    "deterministic": "确定性",
    "deterministic_recover": "确定性恢复",
    "deterministic_only": "仅确定性",
    "llm_fallback_deterministic": "大模型回退·确定性",
    "llm_failed": "大模型失败",
    "llm_failed_keep_old": "大模型失败·保留旧值",
    "clean": "无需补全",
    "skip": "跳过",
    "gaps_only": "仅补缺口",
    "branch_refine": "分支精炼",
}


def _mode_zh(mode: Any) -> str:
    key = str(mode or "").strip()
    return _MODE_ZH.get(key, key or "—")


def _fail_running_step(steps: list[dict[str, Any]] | None, meta: str) -> list[dict[str, Any]]:
    """把当前 run 步标为 fail；若无 run 则标首个非 done。"""
    out = [dict(s or {}) for s in (steps or [])]
    if not out:
        return out
    for s in out:
        if str(s.get("status") or "") == "run":
            s["status"] = "fail"
            s["meta"] = meta
            return out
    for s in out:
        if str(s.get("status") or "") != "done":
            s["status"] = "fail"
            s["meta"] = meta
            return out
    return out


def _append_log_sync(project_id: str, line: str) -> None:
    settings = get_settings()
    log_file = settings.logs_dir / project_id / "job.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {line}\n")


async def append_log(project_id: str, line: str) -> None:
    await asyncio.to_thread(_append_log_sync, project_id, line)


def evaluate_gates(project: Project, workspace: Path) -> dict[str, Any]:
    """按领域跑门禁；Library 校验文件契约 + 主路径逻辑。"""
    return evaluate_domain_gates(workspace, project.spec or {})


# 工厂内部产物，不进学生交付 ZIP（含 .factory/defense-ppt 旁路）
_ZIP_EXCLUDE_NAMES = frozenset({"spec.json", "domain.schema.json"})
_ZIP_EXCLUDE_DIRS = frozenset({"node_modules", "target", ".git", "islands", ".vite", ".factory"})


def pack_zip(workspace: Path, zip_path: Path) -> None:
    """打包学生交付 ZIP：跳过排除目录；先写临时文件再替换，避免中断留下坏包。"""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = zip_path.with_suffix(zip_path.suffix + ".packing")
    if tmp_path.exists():
        try:
            tmp_path.unlink()
        except OSError:
            pass
    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in workspace.walk():
            # 原地剪枝，避免扫进 node_modules / target
            dirnames[:] = [d for d in dirnames if d not in _ZIP_EXCLUDE_DIRS]
            base = Path(dirpath)
            for name in filenames:
                if name in _ZIP_EXCLUDE_NAMES:
                    continue
                path = base / name
                if not path.is_file():
                    continue
                rel = path.relative_to(workspace)
                if set(rel.parts) & _ZIP_EXCLUDE_DIRS:
                    continue
                zf.write(path, rel.as_posix())
    if zip_path.exists():
        zip_path.unlink()
    tmp_path.replace(zip_path)


async def fail_orphaned_jobs() -> int:
    """进程重启后，DB 里仍 running/queued 的任务已无内存 Task，标失败避免进度条卡死。"""
    from app.core.database import SessionLocal

    n = 0
    async with SessionLocal() as db:
        q = await db.execute(
            select(Job).where(
                Job.status.in_([JobStatus.queued.value, JobStatus.running.value])
            )
        )
        for job in q.scalars().all():
            job.status = JobStatus.failed.value
            job.error = "服务重启，任务中断 · 请从失败步骤重试"
            job.steps = _fail_running_step(job.steps, "服务重启中断")
            job.finished_at = datetime.now()
            kind = str(getattr(job, "kind", None) or JobKind.bake.value)
            # 答辩 PPT 旁路不得动 project.status / zip_ready
            if kind == JobKind.bake.value:
                project = await db.get(Project, job.project_id)
                if project and project.status == ProjectStatus.generating.value:
                    project.status = ProjectStatus.ready.value
                    project.zip_ready = False
            n += 1
        if n:
            await db.commit()
    return n


async def run_job(job_id: int, from_step: int = 0) -> None:
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

        from_step = max(0, min(int(from_step or 0), len(STEP_DEFS) - 1))
        resolved = forbid_full_rebake(project, from_step)
        if resolved is None:
            job.status = JobStatus.failed.value
            job.error = "交付复审进行中 · 请先结束复审或仅使用验圈/合卷，不可重跑生成"
            job.finished_at = datetime.now()
            await db.commit()
            return
        from_step = resolved
        job.status = JobStatus.running.value
        job.started_at = datetime.now()
        job.error = None
        job.steps = _default_steps()
        project.status = ProjectStatus.generating.value
        project.zip_ready = False
        project.delivery_mark = "none"
        if from_step <= 1:
            from app.services.delivery_review import empty_review_state

            project.delivery_review = empty_review_state()
            flag_modified(project, "delivery_review")
        await db.commit()

        async def set_step(idx: int, status: str, meta: str = "") -> None:
            steps = list(job.steps or [])
            if idx < len(steps):
                steps[idx] = {**steps[idx], "status": status, "meta": meta}
            job.steps = steps
            job.step = steps[idx]["key"] if idx < len(steps) else job.step
            job.progress = int((idx + (1 if status == "done" else 0.5)) / len(STEP_DEFS) * 100)
            await db.commit()
            await append_log(project.id, f"{steps[idx]['key']} {status} {meta}".strip())

        try:
            from app.bake.catalog import normalize_theme
            from app.bake.domain_schema import ensure_spec_schema
            from app.services import runtime as rt

            llm_rt = await load_llm_runtime(db)

            workspace: Path | None = None
            if project.workspace_path:
                wp = Path(project.workspace_path)
                if wp.exists():
                    workspace = wp

            # 一点生成就停预览，避免 Spec 阶段仍挂着旧前端（列表「生成中+运行中」误导）
            await asyncio.to_thread(
                rt.stop_all, project.id, project.backend_port, project.frontend_port
            )
            project.backend_running = False
            project.frontend_running = False
            await db.commit()
            await append_log(project.id, "preview stopped · 生成前已停旧进程")

            # 续跑若工作区没了，至少从 bake 重来
            if from_step > 1 and workspace is None:
                await append_log(project.id, "RESUME · workspace missing → bake")
                from_step = 1

            if from_step > 0:
                await append_log(project.id, f"RESUME from step[{from_step}] {STEP_DEFS[from_step][0]}")
                for i in range(from_step):
                    await set_step(i, "done", "跳过 · 续跑")

            # 1 Spec Agent（上传时可能已跑；生成时再补强一次）
            if from_step <= 0:
                await set_step(0, "run", "解析与匹配")
                raw = ""
                if project.source_path:
                    # 读开题可能较慢（PDF / 多文件），勿堵事件循环
                    raw = await asyncio.to_thread(load_merged_proposal_text, project.source_path)
                if isinstance(project.spec, dict):
                    project.spec = await run_spec_agent(
                        db, llm_rt, project_id=project.id, raw_text=raw, spec=dict(project.spec)
                    )
                    if project.spec.get("title"):
                        project.title = str(project.spec["title"])[:200]
                    flag_modified(project, "spec")
                await set_step(
                    0,
                    "done",
                    "大模型润色"
                    if llm_rt.stage_on("parse_spec") and llm_rt.configured
                    else "关键词匹配",
                )
                await asyncio.sleep(0.2)

            # 2 bake —— copytree / 下图 / 灌库都是同步重活，必须进线程，否则整站 API 假死
            if from_step <= 1:
                await set_step(1, "run", "复制骨架")
                # 再停一次：防 Spec 期间又有人点了启动；rmtree 前必须空端口
                await asyncio.to_thread(
                    rt.stop_all, project.id, project.backend_port, project.frontend_port
                )
                # 与删项目同口径：等到 STORE/端口空闲，再给 Windows 句柄释放缓冲
                await asyncio.to_thread(
                    rt.wait_runtime_cleared,
                    project.id,
                    project.backend_port,
                    project.frontend_port,
                )
                project.backend_running = False
                project.frontend_running = False

                project.theme = normalize_theme(project.theme, project.domain)
                if isinstance(project.spec, dict):
                    from app.bake.stack_scan import (
                        normalize_ai_assistant,
                        normalize_persistence,
                        normalize_spring_security,
                    )

                    pers = normalize_persistence(
                        getattr(project, "persistence", None)
                        or project.spec.get("persistence")
                    )
                    sec = normalize_spring_security(
                        getattr(project, "spring_security", None)
                        if getattr(project, "spring_security", None) is not None
                        else project.spec.get("spring_security")
                    )
                    ai = normalize_ai_assistant(
                        getattr(project, "ai_assistant", None)
                        if getattr(project, "ai_assistant", None) is not None
                        else project.spec.get("ai_assistant")
                    )
                    project.persistence = pers
                    project.spring_security = sec
                    project.ai_assistant = ai
                    project.spec = ensure_spec_schema(
                        {
                            **project.spec,
                            "theme": project.theme,
                            "persistence": pers,
                            "spine": "spa",
                            "spring_security": sec,
                            "ai_assistant": ai,
                            "addons": {
                                **(project.spec.get("addons") or {}),
                                "spring_security": sec,
                                "ai_assistant": ai,
                            },
                        }
                    )
                    flag_modified(project, "spec")
                # 快照进线程，避免 ORM 对象跨线程
                bake_id, bake_spec, bake_db = project.id, dict(project.spec or {}), project.db_name
                workspace = await asyncio.to_thread(bake_project, bake_id, bake_spec, bake_db)
                project.workspace_path = str(workspace)
                try:
                    from app.services.student_db import ensure_student_schema

                    await asyncio.to_thread(ensure_student_schema, workspace, project.db_name)
                    await set_step(1, "done", "骨架就绪 · 库表已准备")
                except RuntimeError as e:
                    await set_step(1, "done", f"骨架就绪 · 库表跳过：{e}")
                await asyncio.sleep(0.2)
            elif workspace is None:
                raise RuntimeError("工作区不存在，无法续跑，请重新一键生成")

            # 3 拆解式填岛：Plan → Unit 并发 → Merge（ island / ER / 模块 / 用例 ）
            if from_step <= 2:
                await set_step(2, "run", "业务配置填充")
                from app.services.fill_events import fill_event_hub

                await fill_event_hub.reset(project.id)

                async def _fill_event(ev: dict) -> None:
                    await fill_event_hub.handle(project.id, ev)
                    t = ev.get("type", "")
                    uid = ev.get("unit_id", "")
                    if t == "unit_started":
                        await append_log(project.id, f"unit · start {uid}")
                    elif t == "unit_skipped":
                        await append_log(project.id, f"unit · skipped {uid}")
                    elif t in ("unit_done", "unit_failed"):
                        await append_log(
                            project.id,
                            f"unit · {t} {uid} {ev.get('error', '')}".strip(),
                        )

                spec_fill = dict(project.spec or {}) if isinstance(project.spec, dict) else {}
                summary = await run_fill_pipeline(
                    db,
                    project_id=project.id,
                    workspace=workspace,
                    spec=spec_fill,
                    source_path=project.source_path,
                    llm_enabled=bool(project.llm_enabled),
                    merge=True,
                    on_event=_fill_event,
                    llm_rt=llm_rt,
                )
                project.spec = spec_fill
                if isinstance(project.spec, dict) and summary.merge_result and not summary.merge_result.ok:
                    raise RuntimeError(summary.merge_result.detail or "填岛合并失败")
                flag_modified(project, "spec")
                accept = (project.spec or {}).get("accept") if isinstance(project.spec, dict) else None
                meta = format_fill_step_meta(summary, accept=accept)
                written_n = len(summary.merge_result.written_paths()) if summary.merge_result else 0
                await fill_event_hub.handle(
                    project.id,
                    {
                        "type": "fill_complete",
                        "done": summary.done,
                        "total": len(summary.results),
                    },
                )
                await set_step(2, "done", f"{meta} · 写入={written_n}")
                await asyncio.sleep(0.2)

            # 4 构建验证 + Fix Agent
            if from_step <= 3:
                await set_step(3, "run", "构建与修复")
                build_ok, build_meta = await run_fix_agent(
                    db,
                    llm_rt,
                    project_id=project.id,
                    workspace=workspace,
                    spec=project.spec,
                )
                if not build_ok:
                    raise RuntimeError(build_meta or "构建验证失败")
                await set_step(3, "done", build_meta)
                await asyncio.sleep(0.2)

            # 5 gates（只传 spec 快照，勿把 ORM 丢进线程）
            if from_step <= 4:
                await set_step(4, "run", "门禁验收")
                gate_spec = dict(project.spec or {})
                gates = await asyncio.to_thread(evaluate_workspace_gates, workspace, gate_spec)
                project.gates = {k: v for k, v in gates.items() if k != "checklist"}
                project.checklist = gates.get("checklist") or []

                qa_ok = True
                try:
                    qa = await run_qa_agent(
                        db,
                        llm_rt,
                        project_id=project.id,
                        workspace=workspace,
                        spec=project.spec,
                    )
                    apply_qa_to_gates(gates, qa)
                    project.gates = {k: v for k, v in gates.items() if k != "checklist"}
                    qa_ok = bool(qa.get("ok"))
                    await append_log(
                        project.id,
                        f"QA · ok={qa_ok} · {qa.get('summary', '')[:120]}",
                    )
                except Exception as qe:  # noqa: BLE001
                    await append_log(project.id, f"QA skip · {qe}")

                if not gates.get("overall"):
                    detail = _gate_fail_summary(gates)
                    await set_step(4, "fail", detail)
                    job.status = JobStatus.failed.value
                    job.error = f"{MSG_DOWNLOAD_GATES} · {detail}"
                    job.finished_at = datetime.now()
                    project.status = ProjectStatus.failed.value
                    project.zip_ready = False
                    await db.commit()
                    await append_log(project.id, f"GATE FAIL · {detail}")
                    return

                await set_step(4, "done", "门禁与质量摘要通过")
                await asyncio.sleep(0.2)

            # 6 pack
            if from_step <= 5:
                await set_step(5, "run", "打包交付")
                settings = get_settings()
                from app.bake.naming import resolve_slug_from_spec, zip_storage_name

                slug = resolve_slug_from_spec(project.spec, project.domain)
                zip_path = settings.workspace_dir / zip_storage_name(project.id, slug)
                # 清理旧固定名，避免残留
                legacy = settings.workspace_dir / f"{project.id}-thesis-app.zip"
                if legacy.exists() and legacy != zip_path:
                    try:
                        legacy.unlink()
                    except OSError:
                        pass
                await asyncio.to_thread(finalize_pack, project, workspace, zip_path, is_repack=False)
                flag_modified(project, "delivery_review")
                project.zip_path = str(zip_path)
                if isinstance(project.spec, dict):
                    from app.bake.naming import zip_download_name

                    project.spec["delivery_slug"] = slug
                    project.spec["zip_name"] = zip_download_name(slug, project.id)
                    meta = project.spec.get("match_meta")
                    if isinstance(meta, dict):
                        meta["delivery_slug"] = slug
                        meta["zip_name"] = project.spec["zip_name"]
                    flag_modified(project, "spec")
                project.zip_ready = True
                project.status = ProjectStatus.generated.value
                await set_step(5, "done", zip_path.name)

            job.status = JobStatus.success.value
            job.progress = 100
            job.finished_at = datetime.now()
            await db.commit()
            await append_log(project.id, "SUCCESS · zip unlocked")
        except asyncio.CancelledError:
            job.status = JobStatus.cancelled.value
            job.error = "已取消"
            job.steps = _fail_running_step(job.steps, "已取消")
            job.finished_at = datetime.now()
            project.status = ProjectStatus.ready.value
            await db.commit()
            raise
        except Exception as e:  # noqa: BLE001
            logger.exception("job failed")
            err = _short_error(e)
            job.status = JobStatus.failed.value
            job.error = err
            job.steps = _fail_running_step(job.steps, err)
            job.finished_at = datetime.now()
            project.status = ProjectStatus.failed.value
            project.zip_ready = False
            project.delivery_mark = "none"
            await db.commit()
            await append_log(project.id, f"ERROR {err}")
            try:
                from app.services.fill_events import fill_event_hub

                snap = fill_event_hub.snapshot(project.id)
                if snap.get("phase") == "running":
                    await fill_event_hub.handle(
                        project.id,
                        {"type": "fill_failed", "error": err},
                    )
            except Exception:  # noqa: BLE001
                pass


_running: dict[int, asyncio.Task] = {}


async def start_job(
    db: AsyncSession,
    project: Project,
    *,
    from_step: int = 0,
) -> Job:
    # 只取消同项目 bake 任务；答辩 PPT（kind=defense_ppt）互不干扰
    q = await db.execute(
        select(Job).where(
            Job.project_id == project.id,
            Job.status.in_([JobStatus.queued.value, JobStatus.running.value]),
        )
    )
    for old in q.scalars().all():
        kind = str(getattr(old, "kind", None) or JobKind.bake.value)
        if kind != JobKind.bake.value:
            continue
        old.status = JobStatus.cancelled.value
        t = _running.pop(old.id, None)
        if t:
            t.cancel()

    from_step = max(0, min(int(from_step or 0), len(STEP_DEFS) - 1))
    resolved = forbid_full_rebake(project, from_step)
    if resolved is None:
        raise ValueError("交付复审进行中 · 不可重跑生成，请使用验圈/合卷")
    from_step = resolved
    if (
        from_step == 0
        and project.workspace_path
        and Path(project.workspace_path).exists()
        and project.status in (ProjectStatus.generated.value, ProjectStatus.running.value)
    ):
        from_step = 4
    job = Job(
        project_id=project.id,
        kind=JobKind.bake.value,
        status=JobStatus.queued.value,
        step="queued" if from_step == 0 else f"resume:{STEP_DEFS[from_step][0]}",
        progress=0,
        steps=_default_steps(),
        units=[],
    )
    db.add(job)
    project.status = ProjectStatus.generating.value
    project.zip_ready = False
    project.delivery_mark = "none"
    if from_step <= 1:
        from app.services.delivery_review import empty_review_state

        project.delivery_review = empty_review_state()
        flag_modified(project, "delivery_review")
    await db.commit()
    await db.refresh(job)

    task = asyncio.create_task(run_job(job.id, from_step=from_step))
    _running[job.id] = task

    def _log_task_crash(t: asyncio.Task, jid: int = job.id) -> None:
        try:
            exc = t.exception()
        except asyncio.CancelledError:
            return
        if exc is not None:
            logger.exception("run_job 后台任务异常 · job #%s", jid, exc_info=exc)

    task.add_done_callback(_log_task_crash)
    return job


async def cancel_job(db: AsyncSession, job_id: int) -> bool:
    job = await db.get(Job, job_id)
    if not job:
        return False
    if job.status not in (JobStatus.queued.value, JobStatus.running.value):
        return True
    t = _running.pop(job_id, None)
    if t:
        t.cancel()
    job.status = JobStatus.cancelled.value
    job.error = "已取消"
    job.steps = _fail_running_step(job.steps, "已取消")
    job.finished_at = datetime.now()
    kind = str(getattr(job, "kind", None) or JobKind.bake.value)
    # 答辩 PPT 取消不得改 project.status
    if kind == JobKind.bake.value:
        project = await db.get(Project, job.project_id)
        if project and project.status == ProjectStatus.generating.value:
            project.status = ProjectStatus.ready.value
    await db.commit()
    return True


def register_running_task(job_id: int, task: asyncio.Task) -> None:
    """供旁路 runner（如答辩 PPT）登记内存 Task，便于 cancel。"""
    _running[job_id] = task


def pop_running_task(job_id: int) -> asyncio.Task | None:
    return _running.pop(job_id, None)
