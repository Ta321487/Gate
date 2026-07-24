"""system_gemini.py — 由 system 聚合。"""

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
from app.api.system_deepseek import (  # noqa: E402
    _clamp_token_budgets,
    _get_ds_row,
    _hydrate_ds_settings,
)

def _hydrate_gemini_settings(s, cfg: dict) -> None:
    if cfg.get("base_url"):
        s.gemini_base_url = str(cfg["base_url"])
    if cfg.get("model"):
        s.gemini_model = str(cfg["model"])


@router.get("/gemini", response_model=GeminiSettings, tags=["Gemini"], summary="读取 Gemini 配置")
async def get_gemini(db: AsyncSession = Depends(get_db)):
    s = get_settings()
    cfg = await _get_gemini_row(db)
    _hydrate_gemini_settings(s, cfg)
    ds = await _get_ds_row(db)
    _hydrate_ds_settings(s, ds)
    tokens_bd = await monthly_tokens_breakdown(db)
    flags = await get_llm_flags(db)
    return GeminiSettings(
        base_url=str(cfg.get("base_url") or s.gemini_base_url),
        model=str(cfg.get("model") or s.gemini_model),
        key_configured=bool((s.gemini_api_key or "").strip()),
        key_masked=mask_key(s.gemini_api_key, env_name="GEMINI_API_KEY"),
        match_recommend=bool(ds.get("match_recommend", True)),
        parse_spec=bool(ds.get("parse_spec", True)),
        island_fill=bool(ds.get("island_fill", True)),
        er_labels=bool(ds.get("er_labels", True)),
        module_labels=bool(ds.get("module_labels", True)),
        testcase_labels=bool(ds.get("testcase_labels", True)),
        auto_fix=bool(ds.get("auto_fix", True)),
        qa_report=bool(ds.get("qa_report", False)),
        project_token_budget=int(ds.get("project_token_budget", s.project_token_budget)),
        monthly_token_budget=int(ds.get("monthly_token_budget", s.monthly_token_budget)),
        fix_rounds_max=int(ds.get("fix_rounds_max", s.fix_rounds_max)),
        monthly_tokens_used=int(tokens_bd["total"]),
        monthly_tokens_pipeline=int(tokens_bd["pipeline"]),
        monthly_tokens_support=int(tokens_bd["support"]),
        deepseek_enabled=flags["deepseek_enabled"],
        gemini_enabled=flags["gemini_enabled"],
        preferred=flags["preferred"],
    )


@router.put("/gemini", response_model=GeminiSettings, tags=["Gemini"], summary="保存 Gemini 配置")
async def put_gemini(body: GeminiUpdate, db: AsyncSession = Depends(get_db)):
    s = get_settings()
    row = await db.get(SettingRow, "gemini")
    if not row:
        row = SettingRow(key="gemini", value={})
        db.add(row)
    cfg = dict(row.value or {})
    data = body.model_dump(exclude_none=True)
    if "base_url" in data:
        cfg["base_url"] = data["base_url"]
        s.gemini_base_url = data["base_url"]
    if "model" in data:
        cfg["model"] = data["model"]
        s.gemini_model = data["model"]
    row.value = cfg
    await db.commit()

    # 阶段开关 / 预算与 DeepSeek 页共用 deepseek settings 行
    pipeline_keys = (
        "match_recommend",
        "parse_spec",
        "island_fill",
        "er_labels",
        "module_labels",
        "testcase_labels",
        "auto_fix",
        "qa_report",
        "project_token_budget",
        "monthly_token_budget",
        "fix_rounds_max",
    )
    if any(k in data for k in pipeline_keys):
        ds_row = await db.get(SettingRow, "deepseek")
        if not ds_row:
            ds_row = SettingRow(key="deepseek", value=dict(DEFAULT_DS))
            db.add(ds_row)
        ds_cfg = dict(ds_row.value or DEFAULT_DS)
        for k in (
            "match_recommend",
            "parse_spec",
            "island_fill",
            "er_labels",
            "module_labels",
            "testcase_labels",
            "auto_fix",
            "qa_report",
        ):
            if k in data:
                ds_cfg[k] = data[k]
        if "project_token_budget" in data:
            s.project_token_budget = data["project_token_budget"]
            ds_cfg["project_token_budget"] = data["project_token_budget"]
        if "monthly_token_budget" in data:
            s.monthly_token_budget = data["monthly_token_budget"]
            ds_cfg["monthly_token_budget"] = data["monthly_token_budget"]
        if "project_token_budget" in data or "monthly_token_budget" in data:
            _clamp_token_budgets(s, ds_cfg)
        if "fix_rounds_max" in data:
            s.fix_rounds_max = data["fix_rounds_max"]
            ds_cfg["fix_rounds_max"] = data["fix_rounds_max"]
        ds_row.value = ds_cfg
        await db.commit()

    if any(k in data for k in ("deepseek_enabled", "gemini_enabled", "preferred")):
        await set_llm_flags(
            db,
            deepseek_enabled=data.get("deepseek_enabled"),
            gemini_enabled=data.get("gemini_enabled"),
            preferred=data.get("preferred"),
        )
    return await get_gemini(db)


@router.post("/gemini/test", response_model=ApiOk, tags=["Gemini"], summary="测试 Gemini 连通")
async def test_gemini(db: AsyncSession = Depends(get_db)):
    s = get_settings()
    if not (s.gemini_api_key or "").strip():
        return ApiOk(ok=False, message="未配置 GEMINI_API_KEY")
    cfg = await _get_gemini_row(db)
    _hydrate_gemini_settings(s, cfg)
    base = str(cfg.get("base_url") or s.gemini_base_url).rstrip("/")
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{base}/models",
                headers={"Authorization": f"Bearer {s.gemini_api_key}"},
            )
        ms = int((time.perf_counter() - t0) * 1000)
        if r.status_code >= 400:
            return ApiOk(ok=False, message=f"HTTP {r.status_code} · {ms} ms")
        return ApiOk(ok=True, message=f"延迟 {ms} ms · 模型可用", data={"latency_ms": ms})
    except Exception as e:  # noqa: BLE001
        return ApiOk(ok=False, message=str(e))

