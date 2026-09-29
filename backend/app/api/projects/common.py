"""项目 API 共享：router、详情拼装、工作区门禁。"""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["项目"])

# 与前端 uploadMaterials.MAX_UPLOAD_MATERIALS 保持一致（按展开后材料份数）
MAX_UPLOAD_MATERIALS = 8


def _detail(p: Project) -> ProjectDetail:
    from app.bake.catalog import normalize_theme
    from app.services.delivery_review import build_review_payload

    project_svc.ensure_proposal_in_spec(p)
    d = ProjectDetail.model_validate(p)
    d.theme = normalize_theme(p.theme or "", p.domain)
    d.delivery_mark = project_svc.normalize_delivery_mark(getattr(p, "delivery_mark", None))
    d.download_blocked_reason = project_svc.delivery_block_reason(p)
    d.preview_blocked_reason = project_svc.preview_start_block_reason(p)
    ws, _ = project_svc.workspace_or_reason(p)
    d.delivery_review = build_review_payload(p, ws)
    return d


def _workspace_or_400(p: Project) -> Path:
    ws, reason = project_svc.workspace_or_reason(p)
    if reason:
        raise HTTPException(400, reason)
    assert ws is not None
    return ws

