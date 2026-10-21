"""失败分析：聚合统计与按需处理建议。

相关位置只读码表；处理建议草稿不写码表、不写 Job。
"""

from __future__ import annotations

import re
import time
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import chat
from app.llm.runtime import load_llm_runtime
from app.models import Job, JobKind, JobStatus, Project
from app.services.bake_fail_classify import (
    CODES,
    FIX_LOCUS,
    LABELS,
    catalog_payload,
    classify_bake_error,
    error_fingerprint,
    fix_locus_for,
    label_for,
)

# job_id -> {"payload": draft, "at": epoch}；进程内，TTL / 上限回收，亦可主动丢弃
_FIX_DRAFTS: dict[int, dict[str, Any]] = {}
_DRAFT_TTL_SEC = 2 * 3600
_DRAFT_MAX = 32


def _prune_fix_drafts() -> None:
    now = time.time()
    expired = [jid for jid, ent in _FIX_DRAFTS.items() if now - float(ent.get("at") or 0) > _DRAFT_TTL_SEC]
    for jid in expired:
        _FIX_DRAFTS.pop(jid, None)
    overflow = len(_FIX_DRAFTS) - _DRAFT_MAX
    if overflow <= 0:
        return
    oldest = sorted(_FIX_DRAFTS.items(), key=lambda kv: float(kv[1].get("at") or 0))[:overflow]
    for jid, _ in oldest:
        _FIX_DRAFTS.pop(jid, None)


def _draft_store_get(job_id: int) -> dict[str, Any] | None:
    _prune_fix_drafts()
    ent = _FIX_DRAFTS.get(int(job_id))
    if not ent:
        return None
    payload = ent.get("payload")
    if not isinstance(payload, dict) or not payload.get("draft"):
        _FIX_DRAFTS.pop(int(job_id), None)
        return None
    ent["at"] = time.time()
    return payload


def _draft_store_set(job_id: int, payload: dict[str, Any]) -> None:
    _FIX_DRAFTS[int(job_id)] = {"payload": payload, "at": time.time()}
    _prune_fix_drafts()


def draft_cache_has(job_id: int) -> bool:
    return _draft_store_get(int(job_id)) is not None


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _job_when(job: Job) -> datetime | None:
    return job.finished_at or job.started_at or job.created_at


def ensure_error_code(
    job: Job,
    *,
    gates: dict[str, Any] | None = None,
) -> str:
    """历史行无 code 时即时分类（不强制写库）。"""
    code = str(getattr(job, "error_code", None) or "").strip()
    if code and code in LABELS:
        return code
    result = classify_bake_error(
        job.error,
        step=job.step,
        steps=job.steps if isinstance(job.steps, list) else None,
        gates=gates,
    )
    return result.code


def _resolve_hint_payload(
    *,
    later_ok_id: int | None,
    later_same_id: int | None,
) -> dict[str, Any]:
    if not later_ok_id:
        return {"maybe_resolved": False, "resolve_stale": False, "resolve_note": ""}
    if later_same_id:
        return {
            "maybe_resolved": False,
            "resolve_stale": True,
            "resolve_note": "本条为历史失败样本；该项目此后再次出现同类失败，请以更新样本为准。",
        }
    return {
        "maybe_resolved": True,
        "resolve_stale": False,
        "resolve_note": "该项目此后已有出包成功，本条可能已失效，建议优先查看更新记录。",
    }


async def _annotate_samples_resolve(
    db: AsyncSession,
    samples: list[dict[str, Any]],
) -> None:
    """批量为样本挂 maybe_resolved / resolve_stale（与处理建议同源判据）。"""
    if not samples:
        return
    pids = list({s["project_id"] for s in samples if s.get("project_id")})
    min_jid = min(int(s["job_id"]) for s in samples)
    if not pids:
        return

    ok_rows = (
        await db.execute(
            select(Job.project_id, Job.id).where(
                Job.project_id.in_(pids),
                Job.kind == JobKind.bake.value,
                Job.status == JobStatus.success.value,
                Job.id > min_jid,
            )
        )
    ).all()
    ok_by_proj: dict[str, list[int]] = {}
    for pid, jid in ok_rows:
        ok_by_proj.setdefault(str(pid), []).append(int(jid))

    codes = list({str(s.get("code") or "") for s in samples if s.get("code")})
    fail_by_proj: dict[str, list[tuple[int, str]]] = {}
    if codes:
        fail_rows = (
            await db.execute(
                select(Job.project_id, Job.id, Job.error_code).where(
                    Job.project_id.in_(pids),
                    Job.kind == JobKind.bake.value,
                    Job.status == JobStatus.failed.value,
                    Job.id > min_jid,
                    Job.error_code.in_(codes),
                )
            )
        ).all()
        for pid, jid, ec in fail_rows:
            fail_by_proj.setdefault(str(pid), []).append((int(jid), str(ec or "")))

    for s in samples:
        jid = int(s["job_id"])
        pid = str(s.get("project_id") or "")
        ec = str(s.get("code") or "")
        later_oks = [x for x in ok_by_proj.get(pid, []) if x > jid]
        later_ok = max(later_oks) if later_oks else None
        later_same = None
        if later_ok and ec:
            for fid, fec in fail_by_proj.get(pid, []):
                if fid > later_ok and fec == ec:
                    later_same = fid
                    break
        s.update(_resolve_hint_payload(later_ok_id=later_ok, later_same_id=later_same))


async def build_fail_analysis(
    db: AsyncSession,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    domain: str | None = None,
    step: str | None = None,
    code: str | None = None,
    sample_page: int = 1,
    sample_page_size: int = 10,
) -> dict[str, Any]:
    dt_from = _parse_dt(date_from)
    dt_to = _parse_dt(date_to)
    if dt_from is None and dt_to is None:
        dt_from = datetime.now() - timedelta(days=7)

    q = await db.execute(
        select(Job)
        .where(
            Job.kind == JobKind.bake.value,
            Job.status == JobStatus.failed.value,
        )
        .order_by(Job.id.desc())
        .limit(5000)
    )
    jobs = list(q.scalars().all())

    project_ids = {j.project_id for j in jobs}
    projects: dict[str, Project] = {}
    if project_ids:
        pr = await db.execute(select(Project).where(Project.id.in_(list(project_ids))))
        projects = {p.id: p for p in pr.scalars().all()}

    dom_filter = (domain or "").strip()
    step_filter = (step or "").strip()
    code_filter = (code or "").strip()

    by_code: Counter[str] = Counter()
    by_step: Counter[str] = Counter()
    by_domain: Counter[str] = Counter()
    by_persistence: Counter[str] = Counter()
    sample_rows: list[dict[str, Any]] = []
    # fingerprint -> count for UNKNOWN 并族
    unknown_fp: Counter[str] = Counter()
    unknown_fp_like: dict[str, str | None] = {}

    for job in jobs:
        when = _job_when(job)
        if dt_from and when and when < dt_from:
            continue
        if dt_to and when and when > dt_to:
            continue
        proj = projects.get(job.project_id)
        dom = (proj.domain if proj else None) or "—"
        persist = (proj.persistence if proj else None) or "—"
        if dom_filter and dom != dom_filter:
            continue

        gates = proj.gates if proj and isinstance(proj.gates, dict) else None
        ec = ensure_error_code(job, gates=gates)
        fail_step = str(job.step or "")
        if isinstance(job.steps, list):
            for s in job.steps:
                if isinstance(s, dict) and str(s.get("status") or "") == "fail":
                    fail_step = str(s.get("key") or fail_step)
                    break
        if step_filter and fail_step != step_filter and job.step != step_filter:
            continue
        if code_filter and ec != code_filter:
            continue

        by_code[ec] += 1
        by_step[fail_step or "—"] += 1
        by_domain[dom] += 1
        by_persistence[persist] += 1

        if ec == "UNKNOWN":
            fp = error_fingerprint(job.error)
            unknown_fp[fp] += 1
            if fp not in unknown_fp_like:
                unknown_fp_like[fp] = classify_bake_error(job.error).looks_like_code

        sample_rows.append(
            {
                "job_id": job.id,
                "project_id": job.project_id,
                "project_title": proj.title if proj else None,
                "domain": dom,
                "persistence": persist,
                "code": ec,
                "label": label_for(ec),
                "fix_locus": fix_locus_for(ec),
                "step": fail_step,
                "error": (job.error or "")[:280],
                "finished_at": when.isoformat(sep=" ", timespec="seconds")
                if when
                else None,
                "has_draft": int(job.id) in _FIX_DRAFTS,
            }
        )

    page = max(1, int(sample_page or 1))
    size = min(100, max(1, int(sample_page_size or 10)))
    samples_total = len(sample_rows)
    start = (page - 1) * size
    samples = sample_rows[start : start + size]
    await _annotate_samples_resolve(db, samples)

    priorities = []
    for ec, n in by_code.most_common(12):
        priorities.append(
            {
                "code": ec,
                "count": n,
                "label": label_for(ec),
                "fix_locus": fix_locus_for(ec),
                "hint": f"建议优先处理：{label_for(ec)} · {fix_locus_for(ec)}"
                if dt_from and (datetime.now() - dt_from).days <= 8
                else f"建议处理：{label_for(ec)} · {fix_locus_for(ec)}",
            }
        )

    unknown_clusters = [
        {
            "fingerprint": fp,
            "count": n,
            "looks_like_code": unknown_fp_like.get(fp),
        }
        for fp, n in unknown_fp.most_common(20)
        if n >= 2
    ]

    return {
        "totals": {
            "failed": sum(by_code.values()),
            "codes": len(by_code),
        },
        "range": {
            "from": dt_from.isoformat(sep=" ", timespec="seconds") if dt_from else None,
            "to": dt_to.isoformat(sep=" ", timespec="seconds") if dt_to else None,
        },
        "by_code": [
            {
                "code": c,
                "count": n,
                "label": label_for(c),
                "fix_locus": fix_locus_for(c),
            }
            for c, n in by_code.most_common()
        ],
        "by_step": [{"step": s, "count": n} for s, n in by_step.most_common()],
        "by_domain": [{"domain": d, "count": n} for d, n in by_domain.most_common()],
        "by_persistence": [
            {"persistence": p, "count": n} for p, n in by_persistence.most_common()
        ],
        "priorities": priorities,
        "samples": samples,
        "samples_total": samples_total,
        "sample_page": page,
        "sample_page_size": size,
        "unknown_clusters": unknown_clusters,
        "catalog": catalog_payload(),
    }


def _allowed_path_hint(fix_locus: str) -> str:
    """从 A 档落点抽出允许改动的目录提示。"""
    m = re.match(r"(backend/app/[^\s·]+)", fix_locus or "")
    if m:
        return m.group(1)
    return "backend/app/bake/ 或 backend/app/services/"


async def classify_assist(
    db: AsyncSession,
    *,
    error: str,
    step: str | None = None,
) -> dict[str, Any]:
    """助归：只返回已有码；不含修法正文。"""
    rt = await load_llm_runtime(db)
    if not rt.endpoint_chain():
        raise RuntimeError("尚未配置大模型，暂时无法给出类型建议")

    local = classify_bake_error(error, step=step)
    code_lines = "\n".join(f"- {c}: {LABELS[c]}" for c in CODES if c != "UNKNOWN")
    messages = [
        {
            "role": "system",
            "content": (
                "你是工厂 bake 失败归码助手。只能从给定码列表中选一个 code。"
                "只输出 JSON：{\"code\":string,\"reason\":string}。"
                "禁止发明新码；禁止输出修法、路径建议、fix 字段。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"可选码：\n{code_lines}\n\n"
                f"失败步骤：{step or '—'}\n"
                f"错误原文：{error[:800]}\n"
                f"规则初判：{local.code}（仅供参考，可推翻）"
            ),
        },
    ]
    res = await chat(rt, messages, json_mode=True, temperature=0.1, timeout=60.0)
    if not res.ok:
        raise RuntimeError(res.error or "类型建议生成失败，请稍后重试")
    data = res.data if isinstance(res.data, dict) else {}
    code = str(data.get("code") or "").strip()
    if code not in CODES or code == "UNKNOWN":
        raise RuntimeError("未能识别出有效类型，请稍后重试")
    reason = str(data.get("reason") or "")[:200]
    # 故意不返回 fix_locus / 修法
    return {"code": code, "reason": reason, "label": label_for(code)}


async def job_fix_resolve_hint(
    db: AsyncSession,
    *,
    job_id: int | None,
    code: str | None = None,
) -> dict[str, Any]:
    """看该失败任务之后项目是否已成功出包 / 又同类失败，给「怎么修」过时提示。"""
    empty = _resolve_hint_payload(later_ok_id=None, later_same_id=None)
    if job_id is None:
        return empty
    job = await db.get(Job, int(job_id))
    if not job or str(job.kind or "") != JobKind.bake.value:
        return empty

    later_ok = (
        await db.execute(
            select(Job.id)
            .where(
                Job.project_id == job.project_id,
                Job.kind == JobKind.bake.value,
                Job.status == JobStatus.success.value,
                Job.id > job.id,
            )
            .order_by(Job.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not later_ok:
        return empty

    ec = (code or job.error_code or "").strip()
    later_same = None
    if ec and ec in CODES:
        later_same = (
            await db.execute(
                select(Job.id)
                .where(
                    Job.project_id == job.project_id,
                    Job.kind == JobKind.bake.value,
                    Job.status == JobStatus.failed.value,
                    Job.error_code == ec,
                    Job.id > int(later_ok),
                )
                .order_by(Job.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    return _resolve_hint_payload(
        later_ok_id=int(later_ok),
        later_same_id=int(later_same) if later_same else None,
    )


async def create_fix_draft(
    db: AsyncSession,
    *,
    job_id: int | None,
    error: str,
    code: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """处理建议草稿：按 job_id 缓存；同任务默认复用，force 才重生成。不写码表。"""
    if job_id is not None and not force:
        cached = _draft_store_get(int(job_id))
        if cached:
            hint = await job_fix_resolve_hint(db, job_id=job_id, code=cached.get("code") or code)
            return {**cached, "cached": True, **hint}

    rt = await load_llm_runtime(db)
    if not rt.endpoint_chain():
        raise RuntimeError("尚未配置大模型，暂时无法生成处理建议")

    ec = (code or "").strip()
    if ec not in CODES:
        ec = classify_bake_error(error).code
    locus = fix_locus_for(ec)
    allow = _allowed_path_hint(locus)
    messages = [
        {
            "role": "system",
            "content": (
                "你是工厂（非学生包）修法草稿助手。输出 JSON："
                "{\"draft\":string,\"paths\":[string]}。"
                "draft 用中文短段说明可能改法；paths 为建议改动的仓库相对路径。"
                "必须围绕给定权威落点，禁止改 skeletons/ 学生包，禁止声称已核实。"
                "这是未核对草稿，不是最终修法。"
                "同一错误应给出稳定、可复核的建议，避免随意换说法。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"失败码：{ec}（{label_for(ec)}）\n"
                f"权威落点（A 档，必须尊重）：{locus}\n"
                f"允许改动范围提示：{allow}\n"
                f"错误原文：{error[:800]}\n"
                "请给出未核对的修法草稿。"
            ),
        },
    ]
    res = await chat(rt, messages, json_mode=True, temperature=0.0, timeout=90.0)
    if not res.ok:
        raise RuntimeError(res.error or "处理建议生成失败，请稍后重试")
    data = res.data if isinstance(res.data, dict) else {}
    draft = str(data.get("draft") or "").strip()
    if not draft:
        raise RuntimeError("未能生成处理建议，请稍后重试")
    paths = data.get("paths") if isinstance(data.get("paths"), list) else []
    path_strs = [str(p) for p in paths if p][:8]
    suspect = False
    if path_strs:
        bad = any(
            p.replace("\\", "/").startswith("skeletons/")
            or "/skeletons/" in p.replace("\\", "/")
            for p in path_strs
        )
        if bad:
            suspect = True
        allow_root = allow.split()[0] if allow else "backend/app/"
        if not any(allow_root.split("·")[0].strip() in p.replace("\\", "/") for p in path_strs):
            # 路径完全不沾 A 档目录 → 可疑
            if locus != FIX_LOCUS["UNKNOWN"] and not any(
                "backend/app/" in p.replace("\\", "/") for p in path_strs
            ):
                suspect = True

    out = {
        "code": ec,
        "label": label_for(ec),
        "fix_locus": locus,
        "draft": draft,
        "paths": path_strs,
        "status": "unverified",
        "draft_suspect": suspect,
        "job_id": job_id,
        "cached": False,
    }
    if job_id is not None:
        _draft_store_set(int(job_id), out)
    hint = await job_fix_resolve_hint(db, job_id=job_id, code=ec)
    return {**out, **hint}


def get_fix_draft(job_id: int) -> dict[str, Any] | None:
    return _draft_store_get(int(job_id))


def discard_fix_draft(job_id: int) -> bool:
    return _FIX_DRAFTS.pop(int(job_id), None) is not None
