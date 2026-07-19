"""生成 Job：bake 为主，LLM 分岛，门禁后打包。"""

from __future__ import annotations

import asyncio
import logging
import shutil
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
from app.llm.agents import run_fix_agent, run_island_agent, run_qa_agent, run_spec_agent
from app.llm.runtime import load_llm_runtime
from app.models import Job, JobStatus, Project, ProjectStatus
from app.services.proposal import read_proposal

logger = logging.getLogger("gf.job")

STEP_DEFS = [
    ("parse_merge", "解析开题 · 合并 Spec"),
    ("copy_bake", "复制骨架 · 领域 SQL"),
    ("island_fill", "业务岛 emit · LLM 填缺口"),
    ("build_verify", "构建验证"),
    ("gate_e2e", "门禁：登录 + 主流程"),
    ("pack", "开题对照 · 打包 ZIP"),
]


def _default_steps() -> list[dict[str, Any]]:
    return [{"key": k, "title": t, "status": "wait", "meta": ""} for k, t in STEP_DEFS]


async def append_log(project_id: str, line: str) -> None:
    settings = get_settings()
    log_file = settings.logs_dir / project_id / "job.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {line}\n")


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


async def run_job(job_id: int) -> None:
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
        job.steps = _default_steps()
        project.status = ProjectStatus.generating.value
        project.zip_ready = False
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

            # 1 Spec Agent（上传时可能已跑；生成时再补强一次）
            await set_step(0, "run", "Spec Agent")
            raw = ""
            if project.source_path and Path(project.source_path).exists():
                raw = read_proposal(Path(project.source_path))
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
                "LLM Spec" if llm_rt.stage_on("parse_spec") and llm_rt.configured else "关键词匹配",
            )
            await asyncio.sleep(0.2)

            # 2 bake
            await set_step(1, "run")
            rt.stop_all(project.id, project.backend_port, project.frontend_port)
            project.backend_running = False
            project.frontend_running = False

            project.theme = normalize_theme(project.theme, project.domain)
            if isinstance(project.spec, dict):
                project.spec = ensure_spec_schema({**project.spec, "theme": project.theme})
                flag_modified(project, "spec")
            workspace = bake_project(project.id, project.spec, project.db_name)
            project.workspace_path = str(workspace)
            try:
                from app.services.student_db import ensure_student_schema

                ensure_student_schema(workspace, project.db_name)
                await set_step(1, "done", "bake ok · db ready")
            except RuntimeError as e:
                await set_step(1, "done", f"bake ok · db skip: {e}")
            await asyncio.sleep(0.2)

            # 3 Island Agent
            await set_step(2, "run", "Island Agent")
            filled, island_mode = await run_island_agent(
                db,
                llm_rt,
                project_id=project.id,
                workspace=workspace,
                spec=project.spec,
                llm_enabled=bool(project.llm_enabled),
            )
            flag_modified(project, "spec")
            await set_step(
                2,
                "done",
                f"{island_mode} · slots={len(filled)} · accept={project.spec.get('accept')}",
            )
            await asyncio.sleep(0.2)

            # 4 构建验证 + Fix Agent
            await set_step(3, "run", "Build / Fix")
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

            # 5 gates
            await set_step(4, "run")
            gates = evaluate_gates(project, workspace)
            project.gates = {k: v for k, v in gates.items() if k != "checklist"}
            project.checklist = gates.get("checklist") or []

            if not gates.get("overall"):
                await set_step(4, "fail", "P2/功能清单未过")
                job.status = JobStatus.failed.value
                detail = gates.get("p2", {}).get("detail")
                job.error = f"门禁未通过 · 禁止打包 ZIP · {detail or ''}"
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
            await set_step(5, "run")
            settings = get_settings()
            zip_path = settings.workspace_dir / f"{project.id}-thesis-app.zip"
            pack_zip(workspace, zip_path)
            project.zip_path = str(zip_path)
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
            job.finished_at = datetime.now()
            project.status = ProjectStatus.ready.value
            await db.commit()
            raise
        except Exception as e:  # noqa: BLE001
            logger.exception("job failed")
            job.status = JobStatus.failed.value
            job.error = str(e)
            job.finished_at = datetime.now()
            project.status = ProjectStatus.failed.value
            project.zip_ready = False
            await db.commit()
            await append_log(project.id, f"ERROR {e}")


_running: dict[int, asyncio.Task] = {}


async def start_job(db: AsyncSession, project: Project) -> Job:
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

    job = Job(
        project_id=project.id,
        status=JobStatus.queued.value,
        step="queued",
        progress=0,
        steps=_default_steps(),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    task = asyncio.create_task(run_job(job.id))
    _running[job.id] = task
    return job


async def cancel_job(db: AsyncSession, job_id: int) -> bool:
    job = await db.get(Job, job_id)
    if not job:
        return False
    t = _running.pop(job_id, None)
    if t:
        t.cancel()
    job.status = JobStatus.cancelled.value
    job.finished_at = datetime.now()
    project = await db.get(Project, job.project_id)
    if project and project.status == ProjectStatus.generating.value:
        project.status = ProjectStatus.ready.value
    await db.commit()
    return True
