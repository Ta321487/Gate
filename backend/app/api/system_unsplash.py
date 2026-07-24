"""system_unsplash.py — 由 system 聚合。"""

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

@router.get("/unsplash", response_model=UnsplashSettings, tags=["Unsplash"], summary="读取 Unsplash 配置")
async def get_unsplash():
    s = get_settings()
    key = (s.unsplash_access_key or "").strip()
    return UnsplashSettings(
        key_configured=bool(key),
        key_masked=mask_key(key, env_name="UNSPLASH_ACCESS_KEY"),
    )


@router.post("/unsplash/test", response_model=ApiOk, tags=["Unsplash"], summary="测试 Unsplash 连通")
async def test_unsplash():
    """探测 Access Key：GET /photos（公开列表，无需检索词）。"""
    s = get_settings()
    key = (s.unsplash_access_key or "").strip()
    if not key:
        return ApiOk(ok=False, message="未配置 UNSPLASH_ACCESS_KEY")
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                "https://api.unsplash.com/photos",
                params={"per_page": 1},
                headers={
                    "Authorization": f"Client-ID {key}",
                    "Accept-Version": "v1",
                },
            )
        ms = int((time.perf_counter() - t0) * 1000)
        if r.status_code == 401:
            return ApiOk(ok=False, message=f"Key 无效 · {ms} ms")
        if r.status_code == 403:
            return ApiOk(ok=False, message=f"配额或权限不足 · {ms} ms")
        if r.status_code >= 400:
            return ApiOk(ok=False, message=f"HTTP {r.status_code} · {ms} ms")
        return ApiOk(ok=True, message=f"延迟 {ms} ms · 检索可用", data={"latency_ms": ms})
    except Exception as e:  # noqa: BLE001
        return ApiOk(ok=False, message=str(e))

