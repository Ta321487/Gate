"""phase / 状态摘要。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, JobKind, JobStatus, Project

from .deck_io import load_cover, load_deck, load_skin
from .evidence import assemble_evidence, evidence_ready
from .fingerprint import is_biz_dirty
from .themes import seed_theme_for_project


def map_job_status(status: str | None) -> str:
    """对外：success → succeeded（与前端 mock 对齐）。"""
    s = str(status or "")
    if s == JobStatus.success.value:
        return "succeeded"
    return s


def job_to_public(job: Job | None) -> dict[str, Any] | None:
    if not job:
        return None
    return {
        "id": job.id,
        "progress": int(job.progress or 0),
        "status": map_job_status(job.status),
        "error": job.error,
        "steps": list(job.steps or []),
        "units": list(getattr(job, "units", None) or []),
    }


async def latest_ppt_job(db: AsyncSession, project_id: str) -> Job | None:
    q = await db.execute(
        select(Job)
        .where(Job.project_id == project_id, Job.kind == JobKind.defense_ppt.value)
        .order_by(Job.id.desc())
        .limit(1)
    )
    return q.scalar_one_or_none()


async def active_ppt_job(db: AsyncSession, project_id: str) -> Job | None:
    q = await db.execute(
        select(Job)
        .where(
            Job.project_id == project_id,
            Job.kind == JobKind.defense_ppt.value,
            Job.status.in_([JobStatus.queued.value, JobStatus.running.value]),
        )
        .order_by(Job.id.desc())
        .limit(1)
    )
    return q.scalar_one_or_none()


def derive_phase(
    project: Project,
    *,
    evidence: dict[str, bool],
    has_deck: bool,
    biz_dirty: bool,
    active_job: bool,
) -> str:
    if active_job:
        return "generating"
    if not evidence_ready(evidence):
        return "locked"
    if has_deck:
        return "dirty" if biz_dirty else "done"
    return "ready"


async def build_status(db: AsyncSession, project: Project) -> dict[str, Any]:
    evidence = assemble_evidence(project)
    deck = load_deck(project)
    has_deck = bool(deck)
    cover = load_cover(project)
    skin = load_skin(project)
    if not has_deck:
        seed = seed_theme_for_project(project.id)
        skin = {
            "theme": skin.get("theme") or seed["theme"],
            "layout_family": skin.get("layout_family") or seed["layout_family"],
            "master": skin.get("master") or seed["master"],
        }
    biz_dirty = bool(deck.get("biz_dirty")) if deck else False
    if has_deck and not biz_dirty:
        biz_dirty = is_biz_dirty(project)
    active = await active_ppt_job(db, project.id)
    latest = active or await latest_ppt_job(db, project.id)
    phase = derive_phase(
        project,
        evidence=evidence,
        has_deck=has_deck,
        biz_dirty=biz_dirty,
        active_job=bool(active),
    )
    pages = (deck or {}).get("pages") or []
    theme = skin["theme"]
    layout = skin["layout_family"]
    return {
        "phase": phase,
        "evidence": evidence,
        "cover": cover,
        "theme": theme,
        "layout_family": layout,
        "master": skin["master"],
        "biz_dirty": biz_dirty,
        "has_deck": has_deck,
        "page_count": len(pages) if isinstance(pages, list) else 0,
        "job": job_to_public(latest) if latest else None,
        "title": project.title or "",
        "deck_summary": f"{len(pages)}页 · {theme} · {layout}" if has_deck else "",
    }
