"""出包微调 Overrides API（docs/pack-overrides.md P0）。"""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.projects.common import _workspace_or_400, router
from app.bake.overrides import (
    OverridesValidationError,
    apply_overrides_to_workspace,
    empty_payload,
    sanitize_overrides_payload,
)
from app.core.database import get_db
from app.models import Project, ProjectOverrides, ProjectStatus
from app.schemas import OverridesOut, OverridesSaveIn


def _proposal_text_for(project: Project) -> str:
    try:
        from app.services.proposal import load_merged_proposal_text

        return load_merged_proposal_text(project.source_path) or ""
    except Exception:  # noqa: BLE001
        return ""


def _module_nodes_for_ui(workspace: Path, *, proposal_text: str = "") -> list[dict[str, str]]:
    # 与材料图同开题 + 展开细节；原词不叠手调（手调只在 payload.module_labels）
    from app.bake.overrides import list_module_nodes_for_overrides_ui

    return list_module_nodes_for_overrides_ui(workspace, proposal_text=proposal_text)


def _out(
    project_id: str,
    row: ProjectOverrides | None,
    workspace: Path | None,
    *,
    proposal_text: str = "",
) -> OverridesOut:
    payload = empty_payload()
    version = 0
    updated_at = None
    if row is not None:
        try:
            payload = sanitize_overrides_payload(row.payload if isinstance(row.payload, dict) else {})
        except OverridesValidationError:
            payload = empty_payload()
        version = int(row.version or 0)
        updated_at = row.updated_at
    nodes: list[dict[str, str]] = []
    if workspace is not None:
        try:
            nodes = _module_nodes_for_ui(workspace, proposal_text=proposal_text)
        except Exception:  # noqa: BLE001
            nodes = []
    return OverridesOut(
        project_id=project_id,
        version=version,
        payload=payload,
        updated_at=updated_at,
        module_nodes=nodes,
    )


@router.get("/{project_id}/overrides", response_model=OverridesOut, summary="出包微调 Overrides")
async def get_overrides(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    row = await db.get(ProjectOverrides, project_id)
    ws = None
    try:
        ws = _workspace_or_400(p)
    except HTTPException:
        ws = None
    return _out(project_id, row, ws, proposal_text=_proposal_text_for(p))


@router.put("/{project_id}/overrides", response_model=OverridesOut, summary="保存出包微调")
async def put_overrides(
    project_id: str,
    body: OverridesSaveIn,
    db: AsyncSession = Depends(get_db),
):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    if p.status == ProjectStatus.generating.value:
        raise HTTPException(400, "工程正在生成，请稍后再保存微调")

    try:
        clean = sanitize_overrides_payload(body.payload)
    except OverridesValidationError as e:
        raise HTTPException(400, str(e)) from e

    row = await db.get(ProjectOverrides, project_id)
    if row is None:
        if body.version is not None and body.version != 0:
            raise HTTPException(409, "微调记录已变更，请刷新后重试")
        row = ProjectOverrides(project_id=project_id, version=1, payload=clean)
        db.add(row)
    else:
        if body.version is not None and int(body.version) != int(row.version or 0):
            raise HTTPException(409, "微调记录已变更，请刷新后重试")
        row.payload = clean
        row.version = int(row.version or 0) + 1

    ws = None
    if body.apply:
        try:
            ws = _workspace_or_400(p)
        except HTTPException as e:
            await db.commit()
            await db.refresh(row)
            raise HTTPException(
                400,
                f"已写入元库，但工作区不可用故未叠图：{e.detail}",
            ) from e
        applied = apply_overrides_to_workspace(
            ws, clean, proposal_text=_proposal_text_for(p)
        )
        row.payload = applied

    await db.commit()
    await db.refresh(row)
    if ws is None:
        try:
            ws = _workspace_or_400(p)
        except HTTPException:
            ws = None
    return _out(project_id, row, ws, proposal_text=_proposal_text_for(p))


@router.post(
    "/{project_id}/overrides/clear-stale",
    response_model=OverridesOut,
    summary="清理失效 Overrides 补丁",
)
async def clear_stale_overrides(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    row = await db.get(ProjectOverrides, project_id)
    if row is None:
        return _out(project_id, None, None, proposal_text=_proposal_text_for(p))
    try:
        clean = sanitize_overrides_payload(row.payload if isinstance(row.payload, dict) else {})
    except OverridesValidationError as e:
        raise HTTPException(400, str(e)) from e
    clean["_stale"] = []
    row.payload = clean
    row.version = int(row.version or 0) + 1
    ws = None
    try:
        ws = _workspace_or_400(p)
        apply_overrides_to_workspace(
            ws, clean, refresh_stale=False, proposal_text=_proposal_text_for(p)
        )
    except HTTPException:
        ws = None
    await db.commit()
    await db.refresh(row)
    return _out(project_id, row, ws, proposal_text=_proposal_text_for(p))
