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

@router.get("/stats", response_model=StatsOut, summary="项目统计")
async def project_stats(db: AsyncSession = Depends(get_db)):
    # 只读库计数；运行态/checklist 由后台 runtime_reconcile 投影
    from app.core.database import begin_sql_count, end_sql_count

    t0 = time.perf_counter()
    bucket = begin_sql_count()
    try:
        out = StatsOut(**(await project_svc.stats(db)))
    finally:
        n = end_sql_count(bucket)
        logger.info(
            "timing route=stats ms=%.1f db_queries=%s",
            (time.perf_counter() - t0) * 1000.0,
            n,
        )
    return out


@router.post(
    "/purge-orphan-disk",
    response_model=ApiOk,
    summary="受理清理孤儿工程目录与日志",
)
async def purge_orphan_disk(db: AsyncSession = Depends(get_db)):
    """受理式：立刻返回，后台删 data/workspace、data/logs 孤儿目录与 ZIP。不动 cache。

    已在清理中则返回 already_running，不重复开跑。进度见 GET 同路径。
    """
    from app.services import orphan_disk_purge as orphan_purge

    result = await db.execute(select(Project.id))
    alive = set(result.scalars().all())
    data = await orphan_purge.enqueue_full(alive)
    msg = data.get("message") or (
        "清理进行中" if data.get("already_running") else "磁盘清理已开始"
    )
    return ApiOk(message=msg, data=data)


@router.get(
    "/purge-orphan-disk",
    response_model=ApiOk,
    summary="孤儿磁盘清理状态",
)
async def purge_orphan_disk_status():
    """进程内清理状态（idle / running / done / error），供前端轮询。"""
    from app.services import orphan_disk_purge as orphan_purge

    data = orphan_purge.snapshot()
    return ApiOk(message=data.get("message") or "", data=data)


@router.get("", response_model=list[ProjectSummary], summary="项目列表")
async def list_projects(
    q: str = Query("", description="标题或 ID 关键字"),
    filter: str = Query(
        "all",
        alias="filter",
        description="all | active | generating | done | pending | ready | delivered | fail",
    ),
    db: AsyncSession = Depends(get_db),
):
    """只读库投影；运行态/checklist 由后台 runtime_reconcile 收敛（启停/详情仍当场写）。"""
    from app.core.database import begin_sql_count, end_sql_count

    t0 = time.perf_counter()
    bucket = begin_sql_count()
    items: list = []
    select_ms = -1.0
    try:
        t_sel = time.perf_counter()
        result = await db.execute(select(Project).order_by(Project.updated_at.desc()))
        items = list(result.scalars().all())
        select_ms = (time.perf_counter() - t_sel) * 1000.0
        if q:
            items = [p for p in items if q in p.title or q in p.id]
        if filter == "active":
            # 「运行中」= 库内投影（与列表「运行」列一致；后台对账收敛）
            items = [
                p
                for p in items
                if p.status == "running" or p.backend_running or p.frontend_running
            ]
        elif filter == "generating":
            items = [p for p in items if p.status == "generating"]
        elif filter == "done":
            # 可下载 = 已生成/运行中且机器质检仍解锁（与人工履约标记分离；与详情同源）
            # verify_stale=False：只读后台投影缓存，不现场遍历工作区（列表是高频只读投影）
            items = [
                p
                for p in items
                if p.status in ("generated", "running")
                and project_svc.is_zip_downloadable(p, verify_stale=False)
            ]
        elif filter == "pending":
            # 待审 = 质检可下、尚未人工标记（履约 backlog）
            items = [
                p
                for p in items
                if p.status in ("generated", "running")
                and project_svc.is_zip_downloadable(p, verify_stale=False)
                and project_svc.normalize_delivery_mark(
                    getattr(p, "delivery_mark", None)
                )
                == "none"
            ]
        elif filter == "ready":
            items = [
                p
                for p in items
                if project_svc.normalize_delivery_mark(
                    getattr(p, "delivery_mark", None)
                )
                == "ready"
            ]
        elif filter == "delivered":
            items = [
                p
                for p in items
                if project_svc.normalize_delivery_mark(
                    getattr(p, "delivery_mark", None)
                )
                == "delivered"
            ]
        elif filter == "fail":
            # 质检未过：生成任务失败，或已生成但门禁/ZIP 未解锁
            items = [
                p
                for p in items
                if p.status == "failed"
                or (
                    p.status in ("generated", "running")
                    and not project_svc.is_zip_downloadable(p, verify_stale=False)
                )
            ]
        summaries = []
        from app.services.delivery_review import review_status_of

        for p in items:
            s = ProjectSummary.model_validate(p)
            s.delivery_mark = project_svc.normalize_delivery_mark(
                getattr(p, "delivery_mark", None)
            )
            s.download_blocked_reason = project_svc.delivery_block_reason(
                p, verify_stale=False
            )
            s.review_status = review_status_of(p)
            summaries.append(s)
        return summaries
    finally:
        n = end_sql_count(bucket)
        logger.info(
            "timing route=projects filter=%s ms=%.1f db_queries=%s items=%s select_ms=%.1f",
            filter,
            (time.perf_counter() - t0) * 1000.0,
            n,
            len(items),
            select_ms,
        )


@router.post("/upload", response_model=ProjectDetail, summary="上传开题/任务书等材料")
async def upload_proposal(
    files: list[UploadFile] | None = File(
        default=None,
        description="一份或多份材料（PDF / Word / TXT）；至少一份",
    ),
    file: UploadFile | None = File(
        default=None,
        description="兼容旧客户端单文件字段名 file",
    ),
    db: AsyncSession = Depends(get_db),
):
    """单次直接建一个项目（兼容旧客户端）。多课题请走 /upload/plan → /upload/confirm。"""
    saved = await _save_upload_bundle(files, file)
    try:
        project = await project_svc.create_from_uploads(db, saved)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _detail(project)


@router.post("/upload/plan", response_model=UploadPlanOut, summary="上传材料并生成分堆方案（待确认）")
async def upload_plan(
    files: list[UploadFile] | None = File(
        default=None,
        description=f"一份或多份材料；最多 {MAX_UPLOAD_MATERIALS} 份",
    ),
    file: UploadFile | None = File(default=None, description="兼容单文件字段"),
    db: AsyncSession = Depends(get_db),
):
    """解析材料 → 规则/LLM 结构分堆 → 返回方案；确认前不建项目。"""
    from app.llm.runtime import load_llm_runtime
    from app.services.upload_cluster import build_upload_plan, save_plan_bundle

    settings = get_settings()
    uploaded = _require_uploads(files, file)

    # 先落到临时目录读文本，再迁入 plan 目录
    stamp = datetime_stamp()
    tmp = settings.uploads_dir / f"{stamp}_plan_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        saved = await _write_uploads(tmp, uploaded)
        llm_rt = None
        try:
            llm_rt = await load_llm_runtime(db)
        except Exception:  # noqa: BLE001
            llm_rt = None
        plan = await build_upload_plan(saved, db=db, llm_rt=llm_rt)
        plan_dir = settings.uploads_dir / "plans" / plan.plan_id
        plan_dir.mkdir(parents=True, exist_ok=True)
        relocated: list[tuple[Path, str, int]] = []
        for path, name, size in saved:
            dest = plan_dir / path.name
            if path.resolve() != dest.resolve():
                shutil.move(str(path), str(dest))
            relocated.append((dest, name, size))
        save_plan_bundle(relocated, plan)
        return UploadPlanOut.model_validate(plan.to_dict())
    finally:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)


@router.post("/upload/confirm", response_model=UploadConfirmOut, summary="确认分堆并创建项目")
async def upload_confirm(body: UploadConfirmIn, db: AsyncSession = Depends(get_db)):
    from app.services.upload_cluster import (
        apply_overrides,
        delete_plan_bundle,
        load_plan_bundle,
        mark_plan_status,
    )

    try:
        _root, data, all_files = load_plan_bundle(body.plan_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e

    plan = data.get("plan") or {}
    try:
        plan = apply_overrides(plan, clusters=body.clusters, discard=body.discard)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    by_name = {name: (path, name, size) for path, name, size in all_files}
    file_meta = plan.get("files") or []
    idx_to_tuple: dict[int, tuple[Path, str, int]] = {}
    for row in file_meta:
        i = int(row.get("index", -1))
        name = str(row.get("name") or "")
        if name in by_name:
            idx_to_tuple[i] = by_name[name]
    for i, tup in enumerate(all_files):
        idx_to_tuple.setdefault(i, tup)

    # 锁定方案：建项（含 LLM）可能数分钟；期间刷新列表不得删盘
    mark_plan_status(body.plan_id, "confirming")

    settings = get_settings()
    # 先把各簇材料拷出 plan 目录，再慢建项——避免中途 drop_covered / 清方案导致 copy 失败
    stamp = datetime_stamp()
    prepared: list[tuple[dict, list[tuple[Path, str, int]]]] = []
    try:
        for ci, cl in enumerate(plan.get("clusters") or []):
            idxs = [int(f["index"]) for f in cl.get("files") or []]
            bundle_src = [idx_to_tuple[i] for i in idxs if i in idx_to_tuple]
            if not bundle_src:
                continue
            dest_dir = settings.uploads_dir / f"{stamp}_{ci}_bundle"
            dest_dir.mkdir(parents=True, exist_ok=True)
            bundle: list[tuple[Path, str, int]] = []
            used: set[str] = set()
            for path, name, size in bundle_src:
                if not Path(path).is_file():
                    raise HTTPException(400, f"材料缺失：{name}（请重新上传分堆）")
                candidate = Path(name).name or f"file_{len(used)}"
                base, ext = Path(candidate).stem, Path(candidate).suffix
                n = 2
                while candidate.lower() in used:
                    candidate = f"{base}_{n}{ext}"
                    n += 1
                used.add(candidate.lower())
                dest = dest_dir / candidate
                try:
                    shutil.copy2(path, dest)
                except FileNotFoundError as e:
                    raise HTTPException(400, f"材料缺失：{name}（请重新上传分堆）") from e
                bundle.append((dest, candidate, size))
            prepared.append((cl, bundle))

        projects: list[ProjectDetail] = []
        for cl, bundle in prepared:
            try:
                project = await project_svc.create_from_uploads(db, bundle)
                projects.append(_detail(project))
            except ValueError as e:
                label = cl.get("label") or [n for _, n, _ in bundle]
                raise HTTPException(400, f"创建失败（{label}）：{e}") from e
    except Exception:
        # 失败时解开锁定，便于重试或刷新恢复
        mark_plan_status(body.plan_id, "pending")
        raise

    discarded = plan.get("discard") or []
    delete_plan_bundle(body.plan_id)
    return UploadConfirmOut(
        projects=projects,
        discarded=discarded,
        notes=str(plan.get("notes") or ""),
    )


@router.get("/upload/plans", summary="列出未确认的分堆方案（刷新恢复）")
async def list_upload_plans(db: AsyncSession = Depends(get_db)):
    from app.services.upload_cluster import list_pending_plans, normalize_title_key

    # 已是「待确认匹配」的课题不要再进分堆恢复队列
    result = await db.execute(
        select(Project.title).where(Project.status == ProjectStatus.needs_confirm.value)
    )
    title_keys = {
        k
        for (title,) in result.all()
        if (k := normalize_title_key(str(title or ""))) and len(k) >= 4
    }
    items = list_pending_plans(
        exclude_title_keys=title_keys,
        drop_covered=True,
        drop_empty=True,
    )
    return {"items": [UploadPlanOut.model_validate(p) for p in items]}


@router.delete("/upload/plans/{plan_id}", summary="丢弃未确认的分堆方案")
async def delete_upload_plan(plan_id: str):
    from app.services.upload_cluster import delete_plan_bundle

    if not delete_plan_bundle(plan_id):
        raise HTTPException(404, "分堆方案不存在或已清理")
    return {"ok": True}


def _collect_uploads(
    files: list[UploadFile] | None,
    file: UploadFile | None,
) -> list[UploadFile]:
    uploaded: list[UploadFile] = []
    if files:
        uploaded.extend([f for f in files if f and (f.filename or "").strip()])
    if file and (file.filename or "").strip():
        uploaded.append(file)
    return uploaded


async def _write_uploads(
    dest_dir: Path,
    uploaded: list[UploadFile],
) -> list[tuple[Path, str, int]]:
    allowed = {".pdf", ".doc", ".docx", ".txt"}
    saved: list[tuple[Path, str, int]] = []
    used_names: set[str] = set()
    for uf in uploaded:
        suffix = Path(uf.filename or "proposal.txt").suffix.lower()
        if suffix not in allowed:
            raise HTTPException(400, f"不支持 {uf.filename or ''}，仅 PDF / Word / TXT")
        safe_name = Path(uf.filename or "proposal.txt").name
        base, ext = Path(safe_name).stem, Path(safe_name).suffix
        candidate = safe_name
        n = 2
        while candidate.lower() in used_names:
            candidate = f"{base}_{n}{ext}"
            n += 1
        used_names.add(candidate.lower())
        dest = dest_dir / candidate
        content = await uf.read()
        if not content:
            raise HTTPException(400, f"文件为空：{safe_name}")
        dest.write_bytes(content)
        saved.append((dest, candidate, len(content)))
    return saved


async def _save_upload_bundle(
    files: list[UploadFile] | None,
    file: UploadFile | None,
) -> list[tuple[Path, str, int]]:
    uploaded = _require_uploads(
        files, file, empty_msg="请至少上传一份材料（开题 / 任务书 / 功能清单等）"
    )
    settings = get_settings()
    dest_dir = settings.uploads_dir / f"{datetime_stamp()}_bundle"
    dest_dir.mkdir(parents=True, exist_ok=True)
    return await _write_uploads(dest_dir, uploaded)


def _require_uploads(
    files: list[UploadFile] | None,
    file: UploadFile | None,
    *,
    empty_msg: str = "请至少上传一份材料",
) -> list[UploadFile]:
    uploaded = _collect_uploads(files, file)
    if not uploaded:
        raise HTTPException(400, empty_msg)
    if len(uploaded) > MAX_UPLOAD_MATERIALS:
        raise HTTPException(400, f"单次最多 {MAX_UPLOAD_MATERIALS} 份材料")
    return uploaded


def datetime_stamp() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d%H%M%S")


@router.get("/{project_id}", response_model=ProjectDetail, summary="项目详情")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if project_svc.sync_checklist_from_workspace(p):
        await db.commit()
        await db.refresh(p)
    _, _, dirty = project_svc.sync_project_runtime(p)
    if dirty:
        await db.commit()
        await db.refresh(p)
    return _detail(p)


@router.patch("/{project_id}/match", response_model=ProjectDetail, summary="更新匹配")
async def patch_match(project_id: str, body: MatchUpdate, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    try:
        p = await project_svc.update_match(db, p, body)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _detail(p)


@router.patch("/{project_id}/delivery", response_model=ProjectDetail, summary="人工交付标记")
async def patch_delivery(
    project_id: str, body: DeliveryMarkUpdate, db: AsyncSession = Depends(get_db)
):
    """none → ready（已审待发）→ delivered（已发出）；与机器质检 zip_ready 分离。"""
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    try:
        p = await project_svc.set_delivery_mark(db, p, body.mark)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _detail(p)


@router.post("/{project_id}/generate", response_model=ApiOk, summary="启动生成")
async def generate(
    project_id: str,
    confirm_diff: bool = Query(
        False,
        description="开题措辞核对弹窗点「确认并启动生成」时传 true，与启动同事务写入确认",
    ),
    db: AsyncSession = Depends(get_db),
):
    from app.services.delivery_review import ack_pre_generate, require_pre_generate_ack

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if not p.match_confirmed:
        raise HTTPException(400, "请先确认匹配")
    if confirm_diff:
        from app.services.delivery_review import has_proposal_material

        if has_proposal_material(p):
            ack_pre_generate(p)
    ack_msg = require_pre_generate_ack(p)
    if ack_msg:
        raise HTTPException(400, ack_msg)
    try:
        job = await start_job(db, p)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return ApiOk(message=f"Job #{job.id} 已启动", data={"job_id": job.id})


@router.delete("/{project_id}", response_model=ApiOk, summary="删除项目")
async def delete_project(
    project_id: str,
    keep_db: bool = Query(False, description="为 true 时保留学生 MySQL 库"),
    db: AsyncSession = Depends(get_db),
):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    be_st, fe_st, _ = project_svc.sync_project_runtime(p)
    busy = (
        p.status == ProjectStatus.generating.value
        or p.backend_running
        or p.frontend_running
        or be_st in ("starting", "healthy")
        or fe_st in ("starting", "healthy")
    )
    if busy:
        raise HTTPException(400, "项目运行中或正在生成，请先停止后再删除")

    # 再停一次 + 等到端口空闲，降低 Windows 下 rmtree 撞锁概率
    rt.stop_backend(project_id, p.backend_port or None)
    rt.stop_frontend(project_id, p.frontend_port or None)
    await asyncio.to_thread(
        rt.wait_runtime_cleared,
        project_id,
        p.backend_port or None,
        p.frontend_port or None,
    )

    try:
        await asyncio.to_thread(project_svc.purge_project_disk, p)
    except RuntimeError as e:
        raise HTTPException(400, f"工程目录清理失败，请确认已停止预览后重试：{e}") from e

    # 开题材料：无其它项目共用才清
    source_shared = False
    if p.source_path:
        shared_q = await db.execute(
            select(Project.id).where(
                Project.source_path == p.source_path,
                Project.id != project_id,
            ).limit(1)
        )
        source_shared = shared_q.scalar_one_or_none() is not None
    await asyncio.to_thread(
        project_svc.remove_project_source_if_owned,
        p.source_path,
        shared=source_shared,
    )

    db_note = ""
    if not keep_db and p.db_name:
        try:
            await asyncio.to_thread(drop_student_database, p.db_name)
            db_note = f"，已删除库 {p.db_name}"
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "删除项目 %s 时删库失败（仍继续删项目）: %s", project_id, e
            )
            db_note = f"，库 {p.db_name} 删除失败（已跳过）"
    elif keep_db and p.db_name:
        db_note = f"，已保留库 {p.db_name}"

    await db.execute(delete(Job).where(Job.project_id == project_id))
    await db.delete(p)
    await db.commit()
    return ApiOk(message=f"已删除{db_note}")


@router.get("/{project_id}/download", summary="下载 ZIP")
async def download_zip(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if project_svc.sync_checklist_from_workspace(p):
        await db.commit()
        await db.refresh(p)
    blocked = project_svc.delivery_block_reason(p)
    if blocked:
        raise HTTPException(403, blocked)
    if not p.zip_path or not Path(p.zip_path).exists():
        raise HTTPException(404, "ZIP 文件不存在 · 请重新生成")
    from app.bake.naming import resolve_slug_from_spec, zip_download_name

    slug = resolve_slug_from_spec(p.spec if isinstance(p.spec, dict) else {}, p.domain)
    download_name = ""
    if isinstance(p.spec, dict):
        download_name = str(p.spec.get("zip_name") or "").strip()
    if not download_name.endswith(".zip"):
        download_name = zip_download_name(slug, project_id)
    return FileResponse(
        p.zip_path,
        filename=download_name,
        media_type="application/zip",
    )

