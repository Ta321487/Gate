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

from app.bake.engine import bake_project
from app.bake.gates import evaluate_domain_gates
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.llm.agents import (
    run_er_label_agent,
    run_fix_agent,
    run_island_agent,
    run_module_label_agent,
    run_testcase_label_agent,
    run_qa_agent,
    run_spec_agent,
)
from app.llm.runtime import load_llm_runtime
from app.models import Job, JobStatus, Project, ProjectStatus
from app.services.projects import MSG_DOWNLOAD_GATES
from app.services.proposal import load_merged_proposal_text

logger = logging.getLogger("gf.job")

STEP_DEFS = [
    ("parse_merge", "解析开题 · 合并 Spec"),
    ("copy_bake", "复制骨架 · 领域 SQL"),
    ("island_fill", "业务配置填充"),
    ("build_verify", "构建验证"),
    ("gate_e2e", "门禁：登录 + 主流程"),
    ("pack", "开题对照 · 打包 ZIP"),
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


# 工厂内部产物，不进学生交付 ZIP
_ZIP_EXCLUDE_NAMES = frozenset({"spec.json", "domain.schema.json"})
_ZIP_EXCLUDE_DIRS = frozenset({"node_modules", "target", ".git", "islands", ".vite"})


def pack_zip(workspace: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in workspace.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(workspace)
            parts = set(rel.parts)
            if parts & _ZIP_EXCLUDE_DIRS:
                continue
            if rel.name in _ZIP_EXCLUDE_NAMES:
                continue
            zf.write(path, rel.as_posix())


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
        job.status = JobStatus.running.value
        job.started_at = datetime.now()
        job.error = None
        job.steps = _default_steps()
        project.status = ProjectStatus.generating.value
        project.zip_ready = False
        project.delivery_mark = "none"
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
            from sqlalchemy.orm.attributes import flag_modified

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
                project.backend_running = False
                project.frontend_running = False

                project.theme = normalize_theme(project.theme, project.domain)
                if isinstance(project.spec, dict):
                    project.spec = ensure_spec_schema({**project.spec, "theme": project.theme})
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

            # 3 Island Agent + ER Label Agent
            if from_step <= 2:
                await set_step(2, "run", "业务配置填充")
                filled, island_mode = await run_island_agent(
                    db,
                    llm_rt,
                    project_id=project.id,
                    workspace=workspace,
                    spec=project.spec,
                    llm_enabled=bool(project.llm_enabled),
                )
                flag_modified(project, "spec")
                er_meta = ""
                try:
                    er = await run_er_label_agent(
                        db,
                        llm_rt,
                        project_id=project.id,
                        workspace=workspace,
                        spec=project.spec if isinstance(project.spec, dict) else None,
                        llm_enabled=bool(project.llm_enabled),
                    )
                    er_meta = (
                        f" · E-R={_mode_zh(er.get('mode'))}"
                        f" 缺口={er.get('gaps', 0)}"
                        f" 已填={er.get('filled', 0)}"
                    )
                    await append_log(
                        project.id,
                        f"ER Label · mode={er.get('mode')} gaps={er.get('gaps')} "
                        f"filled={er.get('filled')} remain={er.get('remain', 0)}",
                    )
                    try:
                        raw_prop = await asyncio.to_thread(
                            load_merged_proposal_text, project.source_path
                        )
                    except Exception:
                        raw_prop = ""
                    mod = await run_module_label_agent(
                        db,
                        llm_rt,
                        project_id=project.id,
                        workspace=workspace,
                        spec=project.spec if isinstance(project.spec, dict) else None,
                        proposal_text=raw_prop or "",
                        llm_enabled=bool(project.llm_enabled),
                    )
                    er_meta += (
                        f" · 模块图={_mode_zh(mod.get('mode'))}"
                        f" 已填={mod.get('filled', 0)}"
                    )
                    await append_log(
                        project.id,
                        f"Module Label · mode={mod.get('mode')} filled={mod.get('filled')} "
                        f"scope={mod.get('scope', '')}",
                    )
                    tc = await run_testcase_label_agent(
                        db,
                        llm_rt,
                        project_id=project.id,
                        workspace=workspace,
                        spec=project.spec if isinstance(project.spec, dict) else None,
                        proposal_text=raw_prop or "",
                        llm_enabled=bool(project.llm_enabled),
                    )
                    er_meta += (
                        f" · 用例={_mode_zh(tc.get('mode'))}"
                        f" 已填={tc.get('filled', 0)}"
                    )
                    await append_log(
                        project.id,
                        f"Testcase Label · mode={tc.get('mode')} rows={tc.get('rows')} "
                        f"filled={tc.get('filled')}",
                    )
                except Exception as e:
                    er_meta = f" · 标签补全跳过：{e}"
                    await append_log(project.id, f"ER/Module/Testcase Label skip · {e}")
                await set_step(
                    2,
                    "done",
                    f"{_mode_zh(island_mode)} · 写入={len(filled)}"
                    f" · 验收={project.spec.get('accept')}{er_meta}",
                )
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
                gates = await asyncio.to_thread(evaluate_domain_gates, workspace, gate_spec)
                project.gates = {k: v for k, v in gates.items() if k != "checklist"}
                project.checklist = gates.get("checklist") or []

                if not gates.get("overall"):
                    detail = _short_error(
                        (gates.get("p2") or {}).get("detail")
                        or (gates.get("p0") or {}).get("detail")
                        or "主流程或功能清单未通过",
                        limit=200,
                    )
                    await set_step(4, "fail", detail)
                    job.status = JobStatus.failed.value
                    job.error = f"{MSG_DOWNLOAD_GATES} · {detail}"
                    job.finished_at = datetime.now()
                    project.status = ProjectStatus.failed.value
                    project.zip_ready = False
                    await db.commit()
                    await append_log(project.id, f"GATE FAIL · {detail}")
                    return

                await set_step(4, "done", "门禁全过")
                await asyncio.sleep(0.2)

                # QA Agent（不挡打包）
                try:
                    qa = await run_qa_agent(
                        db,
                        llm_rt,
                        project_id=project.id,
                        workspace=workspace,
                        spec=project.spec,
                    )
                    await append_log(
                        project.id,
                        f"QA · ok={qa.get('ok')} · {qa.get('summary', '')[:120]}",
                    )
                except Exception as qe:  # noqa: BLE001
                    await append_log(project.id, f"QA skip · {qe}")

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
                await asyncio.to_thread(pack_zip, workspace, zip_path)
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


_running: dict[int, asyncio.Task] = {}


async def start_job(
    db: AsyncSession,
    project: Project,
    *,
    from_step: int = 0,
) -> Job:
    # cancel previous running for same project
    q = await db.execute(
        select(Job).where(
            Job.project_id == project.id,
            Job.status.in_([JobStatus.queued.value, JobStatus.running.value]),
        )
    )
    for old in q.scalars().all():
        old.status = JobStatus.cancelled.value
        t = _running.pop(old.id, None)
        if t:
            t.cancel()

    from_step = max(0, min(int(from_step or 0), len(STEP_DEFS) - 1))
    job = Job(
        project_id=project.id,
        status=JobStatus.queued.value,
        step="queued" if from_step == 0 else f"resume:{STEP_DEFS[from_step][0]}",
        progress=0,
        steps=_default_steps(),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    task = asyncio.create_task(run_job(job.id, from_step=from_step))
    _running[job.id] = task
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
    project = await db.get(Project, job.project_id)
    if project and project.status == ProjectStatus.generating.value:
        project.status = ProjectStatus.ready.value
    await db.commit()
    return True
