"""system_deepseek.py — 由 system 聚合。"""

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

def _clamp_token_budgets(s, cfg: dict) -> None:
    """项目级预算不得超过月度预算。"""
    monthly = int(cfg.get("monthly_token_budget", s.monthly_token_budget))
    project = int(cfg.get("project_token_budget", s.project_token_budget))
    if project > monthly:
        project = monthly
    s.monthly_token_budget = monthly
    s.project_token_budget = project
    cfg["monthly_token_budget"] = monthly
    cfg["project_token_budget"] = project


async def _get_ds_row(db: AsyncSession) -> dict:
    row = await db.get(SettingRow, "deepseek")
    if not row:
        row = SettingRow(key="deepseek", value=dict(DEFAULT_DS))
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return dict(row.value or {})


def _hydrate_ds_settings(s, cfg: dict) -> None:
    """把 DB 中的 DeepSeek 配置写回内存 settings，供生成任务读取。"""
    if cfg.get("base_url"):
        s.deepseek_base_url = str(cfg["base_url"])
    if cfg.get("model"):
        s.deepseek_model = str(cfg["model"])
    if "project_token_budget" in cfg:
        s.project_token_budget = int(cfg["project_token_budget"])
    if "monthly_token_budget" in cfg:
        s.monthly_token_budget = int(cfg["monthly_token_budget"])
    if "fix_rounds_max" in cfg:
        s.fix_rounds_max = int(cfg["fix_rounds_max"])


@router.get("/deepseek", response_model=DeepSeekSettings, tags=["DeepSeek"], summary="读取 DeepSeek 配置")
async def get_deepseek(db: AsyncSession = Depends(get_db)):
    s = get_settings()
    cfg = await _get_ds_row(db)
    _hydrate_ds_settings(s, cfg)
    tokens_bd = await monthly_tokens_breakdown(db)
    flags = await get_llm_flags(db)
    return DeepSeekSettings(
        base_url=str(cfg.get("base_url") or s.deepseek_base_url),
        model=str(cfg.get("model") or s.deepseek_model),
        thinking=bool(cfg.get("thinking", True)),
        key_configured=bool(s.deepseek_api_key),
        key_masked=mask_key(s.deepseek_api_key, env_name="DEEPSEEK_API_KEY", hint_prefix="sk-"),
        parse_spec=bool(cfg.get("parse_spec", True)),
        match_recommend=bool(cfg.get("match_recommend", True)),
        island_fill=bool(cfg.get("island_fill", True)),
        er_labels=bool(cfg.get("er_labels", True)),
        module_labels=bool(cfg.get("module_labels", True)),
        testcase_labels=bool(cfg.get("testcase_labels", True)),
        auto_fix=bool(cfg.get("auto_fix", True)),
        qa_report=bool(cfg.get("qa_report", False)),
        project_token_budget=int(cfg.get("project_token_budget", s.project_token_budget)),
        monthly_token_budget=int(cfg.get("monthly_token_budget", s.monthly_token_budget)),
        fix_rounds_max=int(cfg.get("fix_rounds_max", s.fix_rounds_max)),
        monthly_tokens_used=int(tokens_bd["total"]),
        monthly_tokens_pipeline=int(tokens_bd["pipeline"]),
        monthly_tokens_support=int(tokens_bd["support"]),
        project_usages=[],
        deepseek_enabled=flags["deepseek_enabled"],
        gemini_enabled=flags["gemini_enabled"],
        preferred=flags["preferred"],
    )


@router.put("/deepseek", response_model=DeepSeekSettings, tags=["DeepSeek"], summary="保存 DeepSeek 配置")
async def put_deepseek(body: DeepSeekUpdate, db: AsyncSession = Depends(get_db)):
    s = get_settings()
    row = await db.get(SettingRow, "deepseek")
    if not row:
        row = SettingRow(key="deepseek", value=dict(DEFAULT_DS))
        db.add(row)
    cfg = dict(row.value or DEFAULT_DS)
    data = body.model_dump(exclude_none=True)
    for k in (
        "thinking",
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
            cfg[k] = data[k]
    if "base_url" in data:
        cfg["base_url"] = data["base_url"]
        s.deepseek_base_url = data["base_url"]
    if "model" in data:
        cfg["model"] = data["model"]
        s.deepseek_model = data["model"]
    if "project_token_budget" in data:
        s.project_token_budget = data["project_token_budget"]
        cfg["project_token_budget"] = data["project_token_budget"]
    if "monthly_token_budget" in data:
        s.monthly_token_budget = data["monthly_token_budget"]
        cfg["monthly_token_budget"] = data["monthly_token_budget"]
    if "project_token_budget" in data or "monthly_token_budget" in data:
        _clamp_token_budgets(s, cfg)
    if "fix_rounds_max" in data:
        s.fix_rounds_max = data["fix_rounds_max"]
        cfg["fix_rounds_max"] = data["fix_rounds_max"]
    row.value = cfg
    await db.commit()
    flag_keys = ("deepseek_enabled", "gemini_enabled", "preferred")
    if any(k in data for k in flag_keys):
        await set_llm_flags(
            db,
            deepseek_enabled=data.get("deepseek_enabled"),
            gemini_enabled=data.get("gemini_enabled"),
            preferred=data.get("preferred"),
        )
    return await get_deepseek(db)


@router.post("/deepseek/test", response_model=ApiOk, tags=["DeepSeek"], summary="测试 DeepSeek 连通")
async def test_deepseek():
    s = get_settings()
    if not s.deepseek_api_key:
        return ApiOk(ok=False, message="未配置 DEEPSEEK_API_KEY")
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{s.deepseek_base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {s.deepseek_api_key}"},
            )
        ms = int((time.perf_counter() - t0) * 1000)
        if r.status_code >= 400:
            return ApiOk(ok=False, message=f"HTTP {r.status_code} · {ms} ms")
        return ApiOk(ok=True, message=f"延迟 {ms} ms · 模型可用", data={"latency_ms": ms})
    except Exception as e:  # noqa: BLE001
        return ApiOk(ok=False, message=str(e))


async def _get_gemini_row(db: AsyncSession) -> dict:
    row = await db.get(SettingRow, "gemini")
    if not row:
        row = SettingRow(key="gemini", value={})
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return dict(row.value or {})

