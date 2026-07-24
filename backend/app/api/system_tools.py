"""system_tools.py — 由 system 聚合。"""

from __future__ import annotations

import asyncio
import subprocess
import time
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.llm.client import (
    monthly_tokens_breakdown,
    project_lifetime_token_rows,
    project_usage_chart,
    project_usage_rows,
    support_usage,
)
from app.llm.runtime import DEFAULT_DS, get_llm_flags, set_llm_flags
from app.models import LlmCall, Project, ProjectStatus, SettingRow
from app.schemas import (
    ApiOk,
    DeepSeekBalance,
    DeepSeekBalanceInfo,
    DeepSeekSettings,
    DeepSeekUpdate,
    GeminiSettings,
    GeminiUpdate,
    SampleProposalRequest,
    SampleProposalResult,
    SystemInfo,
    UnsplashSettings,
)
from app.services import runtime as rt
from app.services.projects import mask_key, reclaim_idle_ports

from app.api.system_router import router  # noqa: E402

@router.get("/tools/sample-proposal/packs", tags=["工具"], summary="列出测试开题选题包")
async def list_sample_proposal_packs():
    from app.bake.sample_proposal import list_packs

    return {"packs": list_packs()}


@router.post(
    "/tools/sample-proposal",
    response_model=SampleProposalResult,
    tags=["工具"],
    summary="生成测试开题（可 LLM 润色）",
)
async def create_sample_proposal(
    body: SampleProposalRequest,
    db: AsyncSession = Depends(get_db),
):
    """随机/指定选题 → 模板拼装 → 可选 DeepSeek/Gemini 润色。仅返回正文，由前端下载 txt。"""
    from app.bake.sample_proposal import build_sample_proposal
    from app.llm.agents import run_sample_proposal_agent
    from app.llm.runtime import load_llm_runtime

    try:
        sample = build_sample_proposal(
            domain=body.domain,
            seed=body.seed,
            pack_id=body.pack_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    used_llm = False
    text = sample.text
    if body.use_llm:
        rt = await load_llm_runtime(db)
        text, used_llm = await run_sample_proposal_agent(
            db,
            rt,
            draft_text=sample.text,
            title=sample.title,
            anchor_domain=sample.anchor_domain,
        )

    return SampleProposalResult(
        pack_id=sample.pack_id,
        anchor_domain=sample.anchor_domain,
        title=sample.title,
        filename=sample.filename,
        text=text,
        used_llm=used_llm,
        digressions=list(sample.digressions or []),
        l1_extras=list(sample.l1_extras or []),
    )

