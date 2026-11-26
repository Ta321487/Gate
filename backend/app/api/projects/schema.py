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


def _ensure_diagram_export_ok(model: dict | None) -> None:
    """rubric_gate / 模块 label_gate 红则禁可交导出（打开图仍可看 findings）。"""
    from app.bake.schema.diagram_rubric import raise_if_export_blocked

    try:
        raise_if_export_blocked(model)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/{project_id}/schema", summary="库表结构")
async def get_schema(project_id: str, db: AsyncSession = Depends(get_db)):
    """表结构 + 推断联系（供产物页展示）。"""
    from app.bake.schema.er import collect_english_gaps, count_er_gaps, load_schema_model

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    from app.bake.schema.schema_thesis_export import schema_table_summary

    model = load_schema_model(ws)
    if not model:
        raise HTTPException(404, "未找到 sql/schema.sql")
    return {
        "db_name": p.db_name,
        "path": "sql/schema.sql",
        "er_gap_count": count_er_gaps(collect_english_gaps(model)),
        "table_summary": schema_table_summary(model),
        **model,
    }


@router.get(
    "/{project_id}/schema/thesis-db-export",
    summary="论文库表逻辑/物理设计正文（同源）",
)
async def get_thesis_db_export(
    project_id: str,
    type_paren: bool = Query(True, description="True=类型合并 varchar(64)"),
    db: AsyncSession = Depends(get_db),
):
    """由 sql/schema.sql 生成可贴 Word 的逻辑设计 + 物理设计；禁止编造表/列。"""
    from app.bake.schema.er import load_schema_model
    from app.bake.schema.schema_thesis_export import (
        assert_export_homology,
        render_thesis_db_export,
    )

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = load_schema_model(ws)
    if not model:
        raise HTTPException(404, "未找到 sql/schema.sql")
    sql_path = ws / "sql" / "schema.sql"
    sql = sql_path.read_text(encoding="utf-8", errors="ignore") if sql_path.is_file() else ""
    payload = render_thesis_db_export(
        model, db_name=str(p.db_name or ""), type_paren=bool(type_paren)
    )
    try:
        assert_export_homology(payload, sql=sql)
    except AssertionError as e:
        raise HTTPException(500, f"库表论文导出同源失败：{e}") from e
    return {
        "db_name": p.db_name,
        "path": "sql/schema.sql",
        **payload,
    }


@router.get("/{project_id}/schema/er", summary="E-R 图模型+SVG")
async def get_er(
    project_id: str,
    mode: str = Query("total", description="total=总图 part=分图"),
    entity: str | None = Query(None, description="分图实体表名"),
    display: str = Query(
        "sample",
        description="sample=论文概念精简（默认可交）· full=全量含角色拆分/壳表",
    ),
    db: AsyncSession = Depends(get_db),
):
    """一次返回表结构 meta + ``svg``；优先读 ``islands/diagram_cache``。"""
    from app.bake.schema.diagram_pack import pack_er

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = pack_er(ws, mode=mode, entity=entity, display=display)
    if not model:
        raise HTTPException(404, "未找到 sql/schema.sql")
    return {
        "db_name": p.db_name,
        "path": "sql/schema.sql",
        **model,
    }


@router.put("/{project_id}/schema/er-view", summary="保存/复位人工 E-R 图")
async def put_er_view(
    project_id: str,
    body: ErViewUpdate,
    db: AsyncSession = Depends(get_db),
):
    """把当前 E-R 图落盘。表结构变了再打开会回到自动排版。"""
    from app.bake.schema.er_view import clear_user_svg, save_user_svg

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if p.status == ProjectStatus.generating.value:
        raise HTTPException(400, "工程正在生成，请稍后再改图")
    ws = _workspace_or_400(p)
    mode = "part" if (body.mode or "").strip().lower() == "part" else "total"
    entity = (body.entity or "").strip() or None
    display = "full" if str(getattr(body, "display", None) or "").strip().lower() == "full" else "sample"
    if body.reset:
        clear_user_svg(ws, mode, entity, display=display)
        return {"ok": True, "reset": True, "message": "已恢复自动排版"}
    try:
        saved = save_user_svg(ws, mode, entity, body.svg, display=display)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True, "reset": False, **saved}


@router.put("/{project_id}/schema/er-labels", summary="人工补 E-R 中文名")
async def put_er_labels(
    project_id: str,
    body: ErLabelsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """保存中文名：er_labels + 回写 schema.sql 的 COMMENT；英文列名不动。"""
    from app.bake.schema.diagram_cache import invalidate as invalidate_diagram_cache
    from app.bake.schema.er import apply_manual_er_labels

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if p.status == ProjectStatus.generating.value:
        raise HTTPException(400, "工程正在生成，请稍后再改中文名")
    ws = _workspace_or_400(p)
    try:
        result = apply_manual_er_labels(
            ws,
            {
                "tables": body.tables,
                "columns": body.columns,
                "relations": body.relations,
            },
        )
    except FileNotFoundError:
        raise HTTPException(404, "未找到 sql/schema.sql") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    invalidate_diagram_cache(ws, "er")
    model = result["model"]
    return {
        "db_name": p.db_name,
        "path": "sql/schema.sql",
        "er_gap_count": result["er_gap_count"],
        "filled": result["filled"],
        "message": "已保存中文名（已写入库表 COMMENT，未改英文列名）",
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


@router.post("/{project_id}/apis/smoke", summary="学生端 API 全量冒烟")
async def smoke_apis(project_id: str, db: AsyncSession = Depends(get_db)):
    """探测已启动预览上的全部 inventory 路径 + 主流程业务链；不启停进程。"""
    from app.services.student_api_smoke import FactorySmokeError, run_student_api_smoke

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    be_st, fe_st, dirty = project_svc.sync_project_runtime(p)
    if dirty:
        await db.commit()
        await db.refresh(p)
    s = get_settings()
    be_url = s.public_url(p.backend_port) if p.backend_port else None
    fe_url = s.public_url(p.frontend_port) if p.frontend_port else None
    if not be_url or not fe_url:
        raise HTTPException(
            409,
            detail={
                "message": "请先到运行页启动前后端预览",
                "error_source": "factory",
                "need_runtime": True,
                "backend_status": be_st,
                "frontend_status": fe_st,
            },
        )
    try:
        if p.db_name:
            from app.services.student_db import repair_student_demo_data

            await asyncio.to_thread(repair_student_demo_data, ws, p.db_name)
        return await asyncio.to_thread(
            run_student_api_smoke,
            project_id=project_id,
            workspace=ws,
            spec=p.spec if isinstance(p.spec, dict) else None,
            backend_url=be_url,
            frontend_url=fe_url,
            backend_status=be_st,
            frontend_status=fe_st,
        )
    except FactorySmokeError as e:
        detail = {"message": e.detail, "error_source": "factory", **(e.payload or {})}
        raise HTTPException(409, detail=detail) from e


@router.get("/{project_id}/schema/er.svg", summary="下载 E-R 图 SVG")
async def download_er_svg(
    project_id: str,
    mode: str = Query("total", description="total=总图 part=分图"),
    entity: str | None = Query(None, description="分图实体表名"),
    display: str = Query("sample", description="sample=论文概念精简 · full=全量"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.diagram_pack import pack_er

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = pack_er(ws, mode=mode, entity=entity, display=display)
    if not model:
        raise HTTPException(404, "未找到 sql/schema.sql")
    _ensure_diagram_export_ok(model)
    m = str(model.get("er_mode") or mode or "total").strip().lower()
    ent = model.get("er_entity") or entity
    svg = str(model.get("svg") or "")
    suffix = f"part-{(ent or 'entity')}" if m == "part" else "total"
    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{project_id}-er-{suffix}.svg"',
        },
    )


@router.get("/{project_id}/schema/er.drawio", summary="下载 E-R 图 Draw.io")
async def download_er_drawio(
    project_id: str,
    mode: str = Query("total", description="total=总图 part=分图"),
    entity: str | None = Query(None, description="分图实体表名"),
    display: str = Query("sample", description="sample=论文概念精简 · full=全量"),
    db: AsyncSession = Depends(get_db),
):
    """同源 model → .drawio，供 diagrams.net 手调；不替代厂内几何刀。"""
    from fastapi.responses import Response

    from app.bake.schema.diagram_drawio import er_model_to_drawio
    from app.bake.schema.diagram_pack import pack_er

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = pack_er(ws, mode=mode, entity=entity, display=display)
    if not model:
        raise HTTPException(404, "未找到 sql/schema.sql")
    _ensure_diagram_export_ok(model)
    m = str(model.get("er_mode") or mode or "total").strip().lower()
    ent = model.get("er_entity") or entity
    body = er_model_to_drawio(model, mode=m, entity=str(ent) if ent else None)
    suffix = f"part-{(ent or 'entity')}" if m == "part" else "total"
    return Response(
        content=body.encode("utf-8"),
        media_type="application/xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{project_id}-er-{suffix}.drawio"',
        },
    )


@router.get(
    "/{project_id}/schema/er-parts.drawio",
    summary="下载全部实体属性图（多页 Draw.io）",
)
async def download_er_parts_drawio(
    project_id: str,
    display: str = Query("sample", description="sample=论文概念精简 · full=全量"),
    db: AsyncSession = Depends(get_db),
):
    """每个概念实体一页，合成一个 .drawio；diagrams.net 左侧切页手调。"""
    from fastapi.responses import Response

    from app.bake.schema.diagram_drawio import er_parts_bundle_to_drawio
    from app.bake.schema.diagram_pack import pack_er

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    seed = pack_er(ws, mode="total", display=display)
    if not seed:
        raise HTTPException(404, "未找到 sql/schema.sql")
    _ensure_diagram_export_ok(seed)
    entities = [
        str(x).strip()
        for x in (seed.get("conceptual_entities") or [])
        if str(x).strip()
    ]
    if not entities:
        tables = [
            t
            for t in (seed.get("tables") or [])
            if isinstance(t, dict)
            and t.get("name")
            and not t.get("assoc_link")
            and not t.get("role_of")
        ]
        entities = [str(t.get("name")) for t in tables if t.get("name")]
    if not entities:
        raise HTTPException(404, "没有可导出的概念实体")
    models: list[dict] = []
    for ent in entities:
        model = pack_er(ws, mode="part", entity=ent, display=display)
        if not model:
            continue
        _ensure_diagram_export_ok(model)
        models.append(model)
    if not models:
        raise HTTPException(404, "未能打包实体属性图")
    body = er_parts_bundle_to_drawio(models)
    return Response(
        content=body.encode("utf-8"),
        media_type="application/xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": (
                f'attachment; filename="{project_id}-er-parts.drawio"'
            ),
        },
    )


@router.get("/{project_id}/schema/er.mmd", summary="下载 E-R 图 Mermaid")
async def download_er_mmd(
    project_id: str,
    mode: str = Query("total", description="total=总图 part=分图"),
    entity: str | None = Query(None, description="分图实体表名"),
    display: str = Query("sample", description="sample=论文概念精简 · full=全量"),
    db: AsyncSession = Depends(get_db),
):
    """同源 model → Mermaid；与 SVG/Draw.io 同一 pack_er。"""
    from fastapi.responses import Response

    from app.bake.schema.diagram_mermaid import er_model_to_mermaid
    from app.bake.schema.diagram_pack import pack_er

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = pack_er(ws, mode=mode, entity=entity, display=display)
    if not model:
        raise HTTPException(404, "未找到 sql/schema.sql")
    _ensure_diagram_export_ok(model)
    m = str(model.get("er_mode") or mode or "total").strip().lower()
    ent = model.get("er_entity") or entity
    body = er_model_to_mermaid(model, mode=m, entity=str(ent) if ent else None)
    suffix = f"part-{(ent or 'entity')}" if m == "part" else "total"
    return Response(
        content=body.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{project_id}-er-{suffix}.mmd"',
        },
    )


@router.get("/{project_id}/schema/modules", summary="功能模块树")
async def get_modules(
    project_id: str,
    layout: str = Query("identity", description="identity=按身份 · biz=按业务"),
    expand_details: bool = Query(False, description="展开【】（）内细节为下一层"),
    force: bool = Query(
        False,
        description="强制重算（绕过图缓存；修 modules.py 清洗后须 true）",
    ),
    db: AsyncSession = Depends(get_db),
):
    """按身份（材料优先）或按业务推导功能模块树；响应含 ``svg``（单请求）。"""
    from app.bake.schema.diagram_pack import pack_modules
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
    model = pack_modules(
        ws,
        layout=layout,
        expand_details=expand_details,
        proposal_text=prop,
        force=force,
    )
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    return model


@router.get("/{project_id}/schema/modules.svg", summary="下载功能模块图 SVG")
async def download_modules_svg(
    project_id: str,
    layout: str = Query("identity", description="identity=按身份 · biz=按业务"),
    expand_details: bool = Query(False, description="展开【】（）内细节为下一层"),
    force: bool = Query(False, description="强制重算（绕过图缓存）"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.diagram_pack import pack_modules
    from app.bake.schema.modules import normalize_module_layout
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
    model = pack_modules(
        ws,
        layout=layout_n,
        expand_details=expand_details,
        proposal_text=prop,
        force=force,
    )
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    _ensure_diagram_export_ok(model)
    svg = str(model.get("svg") or "")
    fname = f"{project_id}-modules-{layout_n}.svg"
    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/modules.drawio", summary="下载功能模块图 Draw.io")
async def download_modules_drawio(
    project_id: str,
    layout: str = Query("identity", description="identity=按身份 · biz=按业务"),
    expand_details: bool = Query(False, description="展开【】（）内细节为下一层"),
    force: bool = Query(False, description="强制重算（绕过图缓存）"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.diagram_drawio import module_model_to_drawio
    from app.bake.schema.diagram_pack import pack_modules
    from app.bake.schema.modules import normalize_module_layout
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
    model = pack_modules(
        ws,
        layout=layout_n,
        expand_details=expand_details,
        proposal_text=prop,
        force=force,
    )
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    _ensure_diagram_export_ok(model)
    body = module_model_to_drawio(model)
    fname = f"{project_id}-modules-{layout_n}.drawio"
    return Response(
        content=body.encode("utf-8"),
        media_type="application/xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/modules.mmd", summary="下载功能模块图 Mermaid")
async def download_modules_mmd(
    project_id: str,
    layout: str = Query("identity", description="identity=按身份 · biz=按业务"),
    expand_details: bool = Query(False, description="展开【】（）内细节为下一层"),
    force: bool = Query(False, description="强制重算（绕过图缓存）"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.diagram_mermaid import module_model_to_mermaid
    from app.bake.schema.diagram_pack import pack_modules
    from app.bake.schema.modules import normalize_module_layout
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
    model = pack_modules(
        ws,
        layout=layout_n,
        expand_details=expand_details,
        proposal_text=prop,
        force=force,
    )
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    _ensure_diagram_export_ok(model)
    body = module_model_to_mermaid(model)
    fname = f"{project_id}-modules-{layout_n}.mmd"
    return Response(
        content=body.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/architecture", summary="系统逻辑架构图模型")
async def get_architecture(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """B/S 分层架构图模型；角色取自交付门户/岗位；响应含 ``svg``。"""
    from app.bake.schema.diagram_pack import pack_architecture

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = pack_architecture(ws, title_fallback=p.title or "管理系统")
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    return model


@router.get("/{project_id}/schema/architecture.svg", summary="下载系统逻辑架构图 SVG")
async def download_architecture_svg(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.diagram_pack import pack_architecture

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = pack_architecture(ws, title_fallback=p.title or "管理系统")
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    _ensure_diagram_export_ok(model)
    svg = str(model.get("svg") or "")
    fname = f"{project_id}-architecture.svg"
    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/architecture.drawio", summary="下载系统逻辑架构图 Draw.io")
async def download_architecture_drawio(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.diagram_drawio import architecture_model_to_drawio
    from app.bake.schema.diagram_pack import pack_architecture

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = pack_architecture(ws, title_fallback=p.title or "管理系统")
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    _ensure_diagram_export_ok(model)
    body = architecture_model_to_drawio(model)
    fname = f"{project_id}-architecture.drawio"
    return Response(
        content=body.encode("utf-8"),
        media_type="application/xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/architecture.mmd", summary="下载系统逻辑架构图 Mermaid")
async def download_architecture_mmd(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.diagram_mermaid import architecture_model_to_mermaid
    from app.bake.schema.diagram_pack import pack_architecture

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = pack_architecture(ws, title_fallback=p.title or "管理系统")
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    _ensure_diagram_export_ok(model)
    body = architecture_model_to_mermaid(model)
    fname = f"{project_id}-architecture.mmd"
    return Response(
        content=body.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/activities", summary="系统活动图模型")
async def get_activities(
    project_id: str,
    ids: str | None = Query(None, description="恰好 3 个候选 id，逗号分隔；省略则默认核心三选"),
    db: AsyncSession = Depends(get_db),
):
    """固定 3 张核心功能活动图；每张 diagram 含 ``svg``（单请求）。"""
    from app.bake.schema.activity import parse_selection_ids
    from app.bake.schema.diagram_pack import pack_activities
    from app.services.proposal import load_merged_proposal_text

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    prop = ""
    try:
        prop = load_merged_proposal_text(p.source_path) or ""
    except Exception:
        prop = ""
    try:
        selection = parse_selection_ids(ids)
        model = pack_activities(
            ws,
            selection=selection,
            proposal_text=prop,
            title_fallback=p.title or "管理系统",
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    return model


@router.get("/{project_id}/schema/activities.svg", summary="下载系统活动图 SVG")
async def download_activities_svg(
    project_id: str,
    index: int = Query(0, ge=0, le=2, description="第几张活动图 0..2"),
    ids: str | None = Query(None, description="恰好 3 个候选 id，逗号分隔"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.activity import parse_selection_ids
    from app.bake.schema.diagram_pack import pack_activities
    from app.services.proposal import load_merged_proposal_text

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    prop = ""
    try:
        prop = load_merged_proposal_text(p.source_path) or ""
    except Exception:
        prop = ""
    try:
        selection = parse_selection_ids(ids)
        model = pack_activities(
            ws,
            selection=selection,
            proposal_text=prop,
            title_fallback=p.title or "管理系统",
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    _ensure_diagram_export_ok(model)
    diagrams = model.get("diagrams") or []
    if index >= len(diagrams):
        raise HTTPException(404, "活动图索引超出范围")
    svg = str((diagrams[index] or {}).get("svg") or model.get("svg") or "")
    fname = f"{project_id}-activity-{index}.svg"
    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/activities.mmd", summary="下载系统活动图 Mermaid")
async def download_activities_mmd(
    project_id: str,
    index: int = Query(0, ge=0, le=2, description="第几张活动图 0..2"),
    ids: str | None = Query(None, description="恰好 3 个候选 id，逗号分隔"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.activity import parse_selection_ids
    from app.bake.schema.diagram_mermaid import activity_model_to_mermaid
    from app.bake.schema.diagram_pack import pack_activities
    from app.services.proposal import load_merged_proposal_text

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    prop = ""
    try:
        prop = load_merged_proposal_text(p.source_path) or ""
    except Exception:
        prop = ""
    try:
        selection = parse_selection_ids(ids)
        model = pack_activities(
            ws,
            selection=selection,
            proposal_text=prop,
            title_fallback=p.title or "管理系统",
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    _ensure_diagram_export_ok(model)
    diagrams = model.get("diagrams") or []
    if index >= len(diagrams):
        raise HTTPException(404, "活动图索引超出范围")
    body = activity_model_to_mermaid(model, index=index)
    fname = f"{project_id}-activity-{index}.mmd"
    return Response(
        content=body.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/sequences", summary="系统序列图模型")
async def get_sequences(
    project_id: str,
    ids: str | None = Query(None, description="恰好 3 个候选 id，逗号分隔；省略则默认核心三选"),
    db: AsyncSession = Depends(get_db),
):
    """固定 3 张核心功能序列图；每张 diagram 含 ``svg``（单请求）。"""
    from app.bake.schema.diagram_pack import pack_sequences
    from app.bake.schema.sequence import parse_selection_ids
    from app.services.proposal import load_merged_proposal_text

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    prop = ""
    try:
        prop = load_merged_proposal_text(p.source_path) or ""
    except Exception:
        prop = ""
    try:
        selection = parse_selection_ids(ids)
        model = pack_sequences(
            ws,
            selection=selection,
            proposal_text=prop,
            title_fallback=p.title or "管理系统",
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    return model


@router.get("/{project_id}/schema/sequences.svg", summary="下载系统序列图 SVG")
async def download_sequences_svg(
    project_id: str,
    index: int = Query(0, ge=0, le=2, description="第几张序列图 0..2"),
    ids: str | None = Query(None, description="恰好 3 个候选 id，逗号分隔"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.diagram_pack import pack_sequences
    from app.bake.schema.sequence import parse_selection_ids
    from app.services.proposal import load_merged_proposal_text

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    prop = ""
    try:
        prop = load_merged_proposal_text(p.source_path) or ""
    except Exception:
        prop = ""
    try:
        selection = parse_selection_ids(ids)
        model = pack_sequences(
            ws,
            selection=selection,
            proposal_text=prop,
            title_fallback=p.title or "管理系统",
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    _ensure_diagram_export_ok(model)
    diagrams = model.get("diagrams") or []
    if index >= len(diagrams):
        raise HTTPException(404, "序列图索引超出范围")
    svg = str((diagrams[index] or {}).get("svg") or model.get("svg") or "")
    fname = f"{project_id}-sequence-{index}.svg"
    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/sequences.mmd", summary="下载系统序列图 Mermaid")
async def download_sequences_mmd(
    project_id: str,
    index: int = Query(0, ge=0, le=2, description="第几张序列图 0..2"),
    ids: str | None = Query(None, description="恰好 3 个候选 id，逗号分隔"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.diagram_mermaid import sequence_model_to_mermaid
    from app.bake.schema.diagram_pack import pack_sequences
    from app.bake.schema.sequence import parse_selection_ids
    from app.services.proposal import load_merged_proposal_text

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    prop = ""
    try:
        prop = load_merged_proposal_text(p.source_path) or ""
    except Exception:
        prop = ""
    try:
        selection = parse_selection_ids(ids)
        model = pack_sequences(
            ws,
            selection=selection,
            proposal_text=prop,
            title_fallback=p.title or "管理系统",
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    _ensure_diagram_export_ok(model)
    diagrams = model.get("diagrams") or []
    if index >= len(diagrams):
        raise HTTPException(404, "序列图索引超出范围")
    body = sequence_model_to_mermaid(model, index=index)
    fname = f"{project_id}-sequence-{index}.mmd"
    return Response(
        content=body.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/classes", summary="系统类图模型")
async def get_classes(
    project_id: str,
    display: str = Query("sample", description="sample=论文示例精简方法 · full=代码全量"),
    force: bool = Query(False, description="强制重算（绕过图缓存）"),
    db: AsyncSession = Depends(get_db),
):
    """系统类图模型（论文交付默认 display=sample）。

    一次返回 model + svg（字段 ``svg``），避免前端连打 model/svg 双请求。
    优先读 bake 预热/打开落盘的 ``islands/diagram_cache``。
    """
    from app.bake.schema.diagram_pack import pack_classes

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = pack_classes(
        ws,
        display=display,
        title_fallback=p.title or "管理系统",
        force=force,
    )
    if not model:
        raise HTTPException(404, "未找到 sql/schema.sql")
    return model


@router.get("/{project_id}/schema/classes.svg", summary="下载系统类图 SVG")
async def download_classes_svg(
    project_id: str,
    display: str = Query("sample", description="sample=论文示例精简方法 · full=代码全量"),
    force: bool = Query(False, description="强制重算（绕过图缓存）"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.diagram_pack import pack_classes

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = pack_classes(
        ws,
        display=display,
        title_fallback=p.title or "管理系统",
        force=force,
    )
    if not model:
        raise HTTPException(404, "未找到 sql/schema.sql")
    _ensure_diagram_export_ok(model)
    svg = str(model.get("svg") or "")
    fname = f"{project_id}-classes.svg"
    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/classes.drawio", summary="下载系统类图 Draw.io")
async def download_classes_drawio(
    project_id: str,
    display: str = Query("sample", description="sample=论文示例精简方法 · full=代码全量"),
    force: bool = Query(False, description="强制重算（绕过图缓存）"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.diagram_drawio import class_model_to_drawio
    from app.bake.schema.diagram_pack import pack_classes

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = pack_classes(
        ws,
        display=display,
        title_fallback=p.title or "管理系统",
        force=force,
    )
    if not model:
        raise HTTPException(404, "未找到 sql/schema.sql")
    _ensure_diagram_export_ok(model)
    body = class_model_to_drawio(model)
    fname = f"{project_id}-classes.drawio"
    return Response(
        content=body.encode("utf-8"),
        media_type="application/xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/classes.mmd", summary="下载系统类图 Mermaid")
async def download_classes_mmd(
    project_id: str,
    display: str = Query("sample", description="sample=论文示例精简方法 · full=代码全量"),
    force: bool = Query(False, description="强制重算（绕过图缓存）"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.diagram_mermaid import class_model_to_mermaid
    from app.bake.schema.diagram_pack import pack_classes

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    model = pack_classes(
        ws,
        display=display,
        title_fallback=p.title or "管理系统",
        force=force,
    )
    if not model:
        raise HTTPException(404, "未找到 sql/schema.sql")
    _ensure_diagram_export_ok(model)
    body = class_model_to_mermaid(model)
    fname = f"{project_id}-classes.mmd"
    return Response(
        content=body.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{fname}"',
        },
    )


@router.put("/{project_id}/schema/classes-layout", summary="保存/复位系统类图布局")
async def put_classes_layout(
    project_id: str,
    body: ClassLayoutUpdate,
    db: AsyncSession = Depends(get_db),
):
    """保存/复位类图框坐标（islands/class_layout.json）。

    本接口只落盘坐标，不挪其它框、不在此做整图精炼。
    客户端保存后应重拉 GET classes：服务端按人工坐标
    零交叉重选折线（可补回少画的边），仍不挪未拖动的框。
    """
    from app.bake.schema.classes import (
        clear_class_layout_patch,
        save_class_layout_patch,
    )
    from app.bake.schema.diagram_cache import invalidate as invalidate_diagram_cache

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if p.status == ProjectStatus.generating.value:
        raise HTTPException(400, "工程正在生成，请稍后再改布局")
    ws = _workspace_or_400(p)
    if body.reset:
        clear_class_layout_patch(ws)
        invalidate_diagram_cache(ws, "classes")
        return {"ok": True, "reset": True, "message": "已清除人工布局，将恢复自动排版"}
    if not body.layout:
        raise HTTPException(400, "layout 为空")
    saved = save_class_layout_patch(
        ws, body.layout, display_mode=body.display_mode, manual=True
    )
    # 拖动只表达「换行/换列/换序」：立刻按槽位吸附+重布线，落盘规整坐标，
    # 保证刷新前后一致、且线线交叉为 0（吸附是幂等的，不会越刷越飘）。
    zero_left = None
    try:
        from app.bake.schema.class_model import load_class_model

        model = load_class_model(ws, display_mode=body.display_mode)
        if isinstance(model, dict) and model.get("layout"):
            zero_left = model.get("layout_zero_cross_left")
            saved = save_class_layout_patch(
                ws,
                model["layout"],
                display_mode=body.display_mode,
                manual=True,
            )
    except Exception as e:  # noqa: BLE001
        # 吸附失败时仍保留用户拖拽落盘，刷新时再走 GET 吸附；勿静默当成功零交叉
        logger.warning("class layout snap-after-save failed project=%s: %s", project_id, e)
        zero_left = None
    invalidate_diagram_cache(ws, "classes")
    return {
        "ok": True,
        "reset": False,
        "count": len(saved.get("layout") or {}),
        # 槽位吸附 + 重布线已在本接口内完成（幂等）；失败时 layout_zero_cross_left=null
        "layout_nudged": False,
        "layout_zero_cross_left": zero_left,
        "message": (
            "类图布局已按槽位吸附并重布线；重拉 SVG 即与保存结果一致"
            if zero_left is not None
            else "类图布局已保存；吸附重布线未完成，请重拉模型与 SVG"
        ),
    }


@router.get("/{project_id}/schema/usecases", summary="用例图模型")
async def get_usecases(
    project_id: str,
    actor: str = Query("user", description="user|admin|staff:岗位id|subadmin"),
    polish: bool = Query(False, description="可选：LLM 润色描述目的语（失败回退规则稿）"),
    db: AsyncSession = Depends(get_db),
):
    """按角色从交付 menus / 岗位 pack 归纳；响应含 ``svg``（单请求）。"""
    from app.bake.schema.diagram_pack import pack_usecases
    from app.bake.schema.usecases import list_usecase_actors, _normalize_actor_id, render_usecase_svg
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
    side = _normalize_actor_id(actor or "user")
    schema_path = ws / "domain.schema.json"
    if not schema_path.is_file():
        raise HTTPException(404, "未找到 domain.schema.json")
    try:
        import json as _json

        schema = _json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(404, "未找到 domain.schema.json")
    actors = list_usecase_actors(schema if isinstance(schema, dict) else {})
    if side not in {a["id"] for a in actors}:
        raise HTTPException(400, f"当前工程无角色 {side}")
    try:
        # 默认视图走缓存；polish 开时在缓存稿上再润色并重渲 svg（不写 polish 缓存）
        model = pack_usecases(
            ws, actor=side, proposal_text=prop, polish=False
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    model = dict(model)
    if polish:
        from app.llm.agents_usecase import polish_usecase_model_safe
        from app.llm.runtime import load_llm_runtime

        rt = await load_llm_runtime(db)
        model = await polish_usecase_model_safe(
            db,
            rt,
            project_id=project_id,
            model=model,
            schema=schema if isinstance(schema, dict) else None,
            title=str(model.get("title") or p.title or ""),
        )
        model = dict(model)
        model["svg"] = render_usecase_svg(model)
        model["diagram_cache"] = "bypass_polish"
    model["actors"] = actors
    return model


@router.get("/{project_id}/schema/usecases.svg", summary="下载用例图 SVG")
async def download_usecases_svg(
    project_id: str,
    actor: str = Query("user", description="user|admin|staff:岗位id|subadmin"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.diagram_pack import pack_usecases
    from app.bake.schema.usecases import _normalize_actor_id
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
    side = _normalize_actor_id(actor or "user")
    try:
        model = pack_usecases(ws, actor=side, proposal_text=prop, polish=False)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    _ensure_diagram_export_ok(model)
    svg = str(model.get("svg") or "")
    safe = side.replace(":", "-")
    fname = f"{project_id}-usecases-{safe}.svg"
    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/usecases.mdj", summary="下载用例图 StarUML .mdj")
async def download_usecases_mdj(
    project_id: str,
    actor: str = Query("user", description="user|admin|staff:岗位id|subadmin"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.usecases import _normalize_actor_id, export_staruml_mdj, load_usecase_model
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
    side = _normalize_actor_id(actor or "user")
    try:
        model = load_usecase_model(ws, actor=side, proposal_text=prop)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    _ensure_diagram_export_ok(model)
    body = export_staruml_mdj(model)
    safe = side.replace(":", "-")
    fname = f"{project_id}-usecases-{safe}.mdj"
    return Response(
        content=body.encode("utf-8"),
        media_type="application/json; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/usecases.drawio", summary="下载用例图 Draw.io")
async def download_usecases_drawio(
    project_id: str,
    actor: str = Query("user", description="user|admin|staff:岗位id|subadmin"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.diagram_drawio import usecase_model_to_drawio
    from app.bake.schema.diagram_pack import pack_usecases
    from app.bake.schema.usecases import _normalize_actor_id
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
    side = _normalize_actor_id(actor or "user")
    try:
        model = pack_usecases(ws, actor=side, proposal_text=prop, polish=False)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    _ensure_diagram_export_ok(model)
    body = usecase_model_to_drawio(model)
    safe = side.replace(":", "-")
    fname = f"{project_id}-usecases-{safe}.drawio"
    return Response(
        content=body.encode("utf-8"),
        media_type="application/xml; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/usecases.mmd", summary="下载用例图 Mermaid")
async def download_usecases_mmd(
    project_id: str,
    actor: str = Query("user", description="user|admin|staff:岗位id|subadmin"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.diagram_mermaid import usecase_model_to_mermaid
    from app.bake.schema.diagram_pack import pack_usecases
    from app.bake.schema.usecases import _normalize_actor_id
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
    side = _normalize_actor_id(actor or "user")
    try:
        model = pack_usecases(ws, actor=side, proposal_text=prop, polish=False)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    _ensure_diagram_export_ok(model)
    body = usecase_model_to_mermaid(model)
    safe = side.replace(":", "-")
    fname = f"{project_id}-usecases-{safe}.mmd"
    return Response(
        content=body.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{fname}"',
        },
    )


@router.get("/{project_id}/schema/usecase-descriptions", summary="论文用例描述表")
async def get_usecase_descriptions(
    project_id: str,
    count: int = Query(4, description="阐述用例数 1～8，默认 4"),
    table_start: str = Query("3.1", description="首张表号，如 3.1"),
    db: AsyncSession = Depends(get_db),
):
    """由交付 menus + 开题正文选用；事件流对照已交付菜单，不发明功能。"""
    from app.bake.schema.usecase_descriptions import (
        load_usecase_description_model,
        normalize_desc_count,
        normalize_table_start,
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
    from app.bake.schema.diagram_rubric import attach_rubric_gate

    model = load_usecase_description_model(
        ws,
        proposal_text=prop,
        count=normalize_desc_count(count),
        table_start=normalize_table_start(table_start),
    )
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    return attach_rubric_gate(model, kind="usecase_desc")


@router.get("/{project_id}/schema/usecase-descriptions.md", summary="下载用例描述 Markdown")
async def download_usecase_descriptions_md(
    project_id: str,
    count: int = Query(4, description="阐述用例数 1～8，默认 4"),
    table_start: str = Query("3.1", description="首张表号，如 3.1"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.bake.schema.usecase_descriptions import (
        load_usecase_description_model,
        normalize_desc_count,
        normalize_table_start,
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
    from app.bake.schema.diagram_rubric import attach_rubric_gate

    model = load_usecase_description_model(
        ws,
        proposal_text=prop,
        count=normalize_desc_count(count),
        table_start=normalize_table_start(table_start),
    )
    if not model:
        raise HTTPException(404, "未找到 domain.schema.json")
    model = attach_rubric_gate(model, kind="usecase_desc")
    _ensure_diagram_export_ok(model)
    body = str(model.get("markdown") or "")
    fname = f"{project_id}-usecase-descriptions.md"
    return Response(
        content=body.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{fname}"',
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
    _ensure_diagram_export_ok(model)
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


@router.post(
    "/{project_id}/schema/thesis-diagram-audit",
    response_model=ApiOk,
    summary="论文图对账（确定性 + 可选 LLM）",
)
async def run_thesis_diagram_audit_api(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """手动触发：只审不改。无 Key/预算不足 → 仅 rubric 确定性；有 Key → 补假宣称扫描。"""
    from app.llm.agents_thesis_diagrams import run_thesis_diagram_audit
    from app.llm.runtime import load_llm_runtime

    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    ws = _workspace_or_400(p)
    llm_rt = await load_llm_runtime(db)
    report = await run_thesis_diagram_audit(
        db,
        llm_rt,
        project_id=p.id,
        workspace=ws,
    )
    return ApiOk(message=str(report.get("summary") or "论文图对账完成"), data=report)

