from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models import Project, ProjectStatus
from app.schemas import (
    ApiOk,
    MatchUpdate,
    ProjectDetail,
    ProjectSummary,
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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["项目"])

# 与前端 uploadMaterials.MAX_UPLOAD_MATERIALS 保持一致（按展开后材料份数）
MAX_UPLOAD_MATERIALS = 8


def _detail(p: Project) -> ProjectDetail:
    from app.bake.catalog import normalize_theme

    project_svc.ensure_proposal_in_spec(p)
    d = ProjectDetail.model_validate(p)
    d.theme = normalize_theme(p.theme or "", p.domain)
    d.download_blocked_reason = project_svc.delivery_block_reason(p)
    d.preview_blocked_reason = project_svc.preview_start_block_reason(p)
    return d


def _workspace_or_400(p: Project) -> Path:
    ws, reason = project_svc.workspace_or_reason(p)
    if reason:
        raise HTTPException(400, reason)
    assert ws is not None
    return ws


@router.get("/stats", response_model=StatsOut, summary="项目统计")
async def project_stats(db: AsyncSession = Depends(get_db)):
    return StatsOut(**(await project_svc.stats(db)))


@router.get("", response_model=list[ProjectSummary], summary="项目列表")
async def list_projects(
    q: str = Query("", description="标题或 ID 关键字"),
    filter: str = Query(
        "all",
        alias="filter",
        description="all | active | generating | done | fail",
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).order_by(Project.updated_at.desc()))
    items = list(result.scalars().all())
    if q:
        items = [p for p in items if q in p.title or q in p.id]
    # 先纠正运行态与门禁/zip_ready，再按筛选过滤（避免须进详情才刷新）
    dirty = False
    for p in items:
        if project_svc.sync_checklist_from_workspace(p):
            dirty = True
        _, _, changed = project_svc.sync_project_runtime(p)
        if changed:
            dirty = True
    if filter == "active":
        # 「运行中」= 预览进程在跑（与列表「运行」列一致）
        items = [
            p
            for p in items
            if p.status == "running" or p.backend_running or p.frontend_running
        ]
    elif filter == "generating":
        items = [p for p in items if p.status == "generating"]
    elif filter == "done":
        # 可交付 = 已生成/运行中且 ZIP 仍解锁（门禁回退后 zip_ready=False）
        items = [
            p
            for p in items
            if p.status in ("generated", "running") and p.zip_ready
        ]
    elif filter == "fail":
        # 质检未过：生成任务失败，或已生成但门禁/ZIP 未解锁
        items = [
            p
            for p in items
            if p.status == "failed"
            or (p.status in ("generated", "running") and not p.zip_ready)
        ]
    # 须在 commit 前物化：commit 后 ORM 过期，Pydantic 再读字段会触发 MissingGreenlet
    summaries = [ProjectSummary.model_validate(p) for p in items]
    if dirty:
        await db.commit()
    return summaries


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
    from app.services.upload_cluster import apply_overrides, load_plan_bundle

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

    settings = get_settings()
    projects: list[ProjectDetail] = []
    for ci, cl in enumerate(plan.get("clusters") or []):
        idxs = [int(f["index"]) for f in cl.get("files") or []]
        bundle_src = [idx_to_tuple[i] for i in idxs if i in idx_to_tuple]
        if not bundle_src:
            continue
        # 每簇拷到独立目录，避免多项目共享 plan 目录写崩 manifest
        dest_dir = settings.uploads_dir / f"{datetime_stamp()}_{ci}_bundle"
        dest_dir.mkdir(parents=True, exist_ok=True)
        bundle: list[tuple[Path, str, int]] = []
        used: set[str] = set()
        for path, name, size in bundle_src:
            candidate = name
            base, ext = Path(name).stem, Path(name).suffix
            n = 2
            while candidate.lower() in used:
                candidate = f"{base}_{n}{ext}"
                n += 1
            used.add(candidate.lower())
            dest = dest_dir / candidate
            shutil.copy2(path, dest)
            bundle.append((dest, candidate, size))
        try:
            project = await project_svc.create_from_uploads(db, bundle)
            projects.append(_detail(project))
        except ValueError as e:
            raise HTTPException(400, f"创建失败（{cl.get('label') or idxs}）：{e}") from e

    discarded = plan.get("discard") or []
    return UploadConfirmOut(
        projects=projects,
        discarded=discarded,
        notes=str(plan.get("notes") or ""),
    )


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


@router.post("/{project_id}/generate", response_model=ApiOk, summary="启动生成")
async def generate(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if not p.match_confirmed:
        raise HTTPException(400, "请先确认匹配")
    job = await start_job(db, p)
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
    project_svc.sync_project_runtime(p)
    if p.status == ProjectStatus.generating.value or p.backend_running or p.frontend_running:
        raise HTTPException(400, "项目运行中或正在生成，请先停止后再删除")
    rt.stop_backend(project_id, p.backend_port)
    rt.stop_frontend(project_id, p.frontend_port)
    settings = get_settings()
    ws = settings.workspace_dir / project_id
    if ws.exists():
        rt.detach_frontend_deps(ws)
        shutil.rmtree(ws, ignore_errors=True)
    zip_path = settings.workspace_dir / f"{project_id}-thesis-app.zip"
    if zip_path.exists():
        zip_path.unlink()
    # 新命名：{id}-{slug}.zip
    for zp in settings.workspace_dir.glob(f"{project_id}-*.zip"):
        try:
            zp.unlink()
        except OSError:
            pass
    if p.zip_path:
        try:
            Path(p.zip_path).unlink(missing_ok=True)
        except OSError:
            pass

    db_note = ""
    if not keep_db and p.db_name:
        try:
            drop_student_database(p.db_name)
            db_note = f"，已删除库 {p.db_name}"
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "删除项目 %s 时删库失败（仍继续删项目）: %s", project_id, e
            )
            db_note = f"，库 {p.db_name} 删除失败（已跳过）"
    elif keep_db and p.db_name:
        db_note = f"，已保留库 {p.db_name}"

    await db.delete(p)
    await db.commit()
    return ApiOk(message=f"已删除{db_note}")


@router.get("/{project_id}/download", summary="下载 ZIP")
async def download_zip(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
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


@router.get("/{project_id}/schema", summary="库表结构")
async def get_schema(project_id: str, db: AsyncSession = Depends(get_db)):
    """表结构 + 推断联系（供产物页展示）。"""
    from app.bake.schema.er import load_schema_model

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = load_schema_model(ws)
    if not model:
        raise HTTPException(404, "未找到 sql/schema.sql")
    return {
        "db_name": p.db_name,
        "path": "sql/schema.sql",
        **model,
    }


@router.get("/{project_id}/apis", summary="学生端 API 清单")
async def get_apis(project_id: str, db: AsyncSession = Depends(get_db)):
    """学生端 REST 映射清单（静态扫描 Controller，供产物页对照）。"""
    from app.bake.api_inventory import load_api_inventory

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    inv = load_api_inventory(ws, p.spec if isinstance(p.spec, dict) else None)
    if not inv:
        raise HTTPException(404, "未找到 Controller")
    return inv


@router.get("/{project_id}/schema/er.svg", summary="下载 E-R 图 SVG")
async def download_er_svg(
    project_id: str,
    mode: str = Query("total", description="total=总图 part=分图"),
    entity: str | None = Query(None, description="分图实体表名"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.er import load_schema_model, render_er_svg

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = load_schema_model(ws)
    if not model:
        raise HTTPException(404, "未找到 sql/schema.sql")
    m = (mode or "total").strip().lower()
    if m not in ("total", "part"):
        m = "total"
    ent = (entity or "").strip() or None
    if m == "part" and not ent:
        tables = model.get("tables") or []
        ent = str((tables[0] or {}).get("name") or "") if tables else None
    svg = render_er_svg(model, mode=m, entity=ent)
    suffix = f"part-{(ent or 'entity')}" if m == "part" else "total"
    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{project_id}-er-{suffix}.svg"',
        },
    )


@router.get("/{project_id}/schema/modules", summary="功能模块树")
async def get_modules(
    project_id: str,
    layout: str = Query("biz", description="biz=按业务拆 · side=按端拆"),
    db: AsyncSession = Depends(get_db),
):
    """菜单 + features 推导的功能模块树（供产物页 / 论文模块图）。"""
    from app.bake.schema.modules import load_module_model, normalize_module_layout
    from app.services.proposal import load_merged_proposal_text

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    prop = ""
    try:
        if p.source_path:
            prop = load_merged_proposal_text(p.source_path) or ""
    except Exception:
        prop = ""
    model = load_module_model(
        ws, proposal_text=prop, layout=normalize_module_layout(layout)
    )
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    return model


@router.get("/{project_id}/schema/modules.svg", summary="下载功能模块图 SVG")
async def download_modules_svg(
    project_id: str,
    layout: str = Query("biz", description="biz=按业务拆 · side=按端拆"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.modules import (
        load_module_model,
        normalize_module_layout,
        render_module_svg,
    )
    from app.services.proposal import load_merged_proposal_text

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    prop = ""
    try:
        if p.source_path:
            prop = load_merged_proposal_text(p.source_path) or ""
    except Exception:
        prop = ""
    layout_n = normalize_module_layout(layout)
    model = load_module_model(ws, proposal_text=prop, layout=layout_n)
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    svg = render_module_svg(model)
    # Content-Disposition 必须是 latin-1；中文名仅给前端下载时自行命名
    fname = f"{project_id}-modules-{layout_n}.svg"
    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/testcases", summary="论文测试用例表")
async def get_testcases(
    project_id: str,
    fields: int = Query(6, description="5|6|7|8|9 列模板"),
    db: AsyncSession = Depends(get_db),
):
    """由交付 menus/roles/entities 推导；不发明未实现功能。"""
    from app.bake.schema.testcases import load_testcase_model, normalize_testcase_fields

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = load_testcase_model(
        ws, fields=normalize_testcase_fields(fields)
    )
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    return model


@router.get("/{project_id}/schema/testcases.md", summary="下载测试用例 Markdown")
async def download_testcases_md(
    project_id: str,
    fields: int = Query(6, description="5|6|7|8|9 列模板"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.testcases import load_testcase_model, normalize_testcase_fields

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = load_testcase_model(
        ws, fields=normalize_testcase_fields(fields)
    )
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    body = str(model.get("markdown") or "")
    fname = f"{project_id}-testcases-{model.get('fields')}.md"
    return Response(
        content=body.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{fname}"',
        },
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
