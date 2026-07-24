"""system_usage.py — 由 system 聚合。"""

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
from app.api.system_deepseek import _get_ds_row, _hydrate_ds_settings  # noqa: E402

@router.get("/deepseek/balance", response_model=DeepSeekBalance, tags=["DeepSeek"], summary="查询账户余额")
async def deepseek_balance(db: AsyncSession = Depends(get_db)):
    """查询 DeepSeek 官方账户余额：GET /user/balance。"""
    s = get_settings()
    cfg = await _get_ds_row(db)
    _hydrate_ds_settings(s, cfg)
    if not s.deepseek_api_key:
        return DeepSeekBalance(ok=False, message="未配置 DEEPSEEK_API_KEY")
    base = (cfg.get("base_url") or s.deepseek_base_url or "https://api.deepseek.com").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{base}/user/balance",
                headers={
                    "Authorization": f"Bearer {s.deepseek_api_key}",
                    "Accept": "application/json",
                },
            )
        if r.status_code >= 400:
            return DeepSeekBalance(
                ok=False,
                message=f"查询失败 HTTP {r.status_code}：{(r.text or '')[:200]}",
            )
        data = r.json() if r.content else {}
        infos = [
            DeepSeekBalanceInfo(
                currency=str(x.get("currency") or "CNY"),
                total_balance=str(x.get("total_balance") or "0"),
                granted_balance=str(x.get("granted_balance") or "0"),
                topped_up_balance=str(x.get("topped_up_balance") or "0"),
            )
            for x in (data.get("balance_infos") or [])
            if isinstance(x, dict)
        ]
        avail = data.get("is_available")
        return DeepSeekBalance(
            ok=True,
            message="ok",
            is_available=bool(avail) if avail is not None else None,
            balance_infos=infos,
        )
    except Exception as e:  # noqa: BLE001
        return DeepSeekBalance(ok=False, message=str(e))


def _parse_dt(value: str | None, *, end: bool = False) -> datetime | None:
    """解析查询时间：支持 YYYY-MM-DD / ISO；end=True 时日期落在当日末。"""
    if not value:
        return None
    raw = value.strip()
    try:
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            dt = datetime.strptime(raw, "%Y-%m-%d")
            if end:
                return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            return dt
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"时间格式无效: {value}") from e


# 调用关键字搜索：中文名 / 明细 note / stage key → stage
_CALL_STAGE_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("match_recommend", ("匹配推荐", "match recommend", "match_recommend")),
    ("parse_spec", ("摘要润色", "spec enrich", "parse_spec")),
    ("island_fill", ("业务配置填充", "业务填充", "island_fill", "island")),
    ("er_labels", ("E-R 中文补全", "ER中文", "er_labels")),
    ("module_labels", ("模块图命名", "module_labels")),
    ("testcase_labels", ("测试用例文案", "testcase_labels")),
    ("auto_fix", ("编译修复", "auto_fix", "fix")),
    ("qa_report", ("质量摘要", "qa llm failed", "qa_report", "fallback structural only", "仅结构扫描")),
    ("emit", ("配置写出", "emit")),
    ("upload_cluster", ("上传分堆", "upload cluster", "upload_cluster", "分堆")),
    ("sample_proposal", ("样例开题", "sample proposal", "sample_proposal")),
)


def _stages_matching_query(needle: str) -> list[str]:
    """关键字命中中文名或明细英文 note 时，映射到 stage key，便于搜中文。"""
    n = (needle or "").strip().lower()
    if len(n) < 2:
        return []
    hit: list[str] = []
    for key, aliases in _CALL_STAGE_ALIASES:
        for alias in aliases:
            a = alias.lower()
            if n in a or a in n:
                hit.append(key)
                break
    return hit


@router.get("/llm/usage", tags=["LLM"], summary="按项目用量")
async def list_usage(
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str | None = None,
    sort_order: str | None = None,
    presence: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """按项目用量（项目流水线，不含系统支持）：时间范围 + 项目 ID 模糊查询 + 排序 + 分页。

    presence: all | alive | deleted（默认 alive）
    """
    items, total = await project_usage_rows(
        db,
        q=q,
        date_from=_parse_dt(date_from),
        date_to=_parse_dt(date_to, end=True),
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        presence=presence,
    )
    return {
        "items": items,
        "total": total,
        "page": max(1, int(page)),
        "page_size": max(1, min(100, int(page_size))),
    }


@router.get("/llm/usage/project-tokens", tags=["LLM"], summary="库内项目全期 Token")
async def list_project_lifetime_tokens(db: AsyncSession = Depends(get_db)):
    """全部项目全期用量（两家合计），供项目预算档位汇总。"""
    items = await project_lifetime_token_rows(db)
    return {"items": items, "total": len(items)}


@router.get("/llm/usage/chart", tags=["LLM"], summary="用量折线图")
async def usage_chart(
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    presence: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """用量透视：按日 Token 折线（项目流水线，不含系统支持）。"""
    return await project_usage_chart(
        db,
        q=q,
        date_from=_parse_dt(date_from),
        date_to=_parse_dt(date_to, end=True),
        presence=presence,
    )


@router.get("/llm/usage/support", tags=["LLM"], summary="系统支持用量")
async def usage_support(
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """系统支持用量（上传分堆、样例开题等）：按 stage 汇总 + 按日折线。"""
    return await support_usage(
        db,
        date_from=_parse_dt(date_from),
        date_to=_parse_dt(date_to, end=True),
    )


@router.get("/llm/calls", tags=["LLM"], summary="最近调用记录")
async def list_calls(
    project_id: str | None = None,
    stage: str | None = None,
    ok: bool | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """最近调用（两家合计）：项目 / 阶段 / 结果 / 时间 / 关键字 + 分页。"""
    stmt = select(LlmCall)
    count_stmt = select(func.count()).select_from(LlmCall)
    pid = (project_id or "").strip()
    if pid:
        stmt = stmt.where(LlmCall.project_id == pid)
        count_stmt = count_stmt.where(LlmCall.project_id == pid)
    st = (stage or "").strip()
    if st:
        stmt = stmt.where(LlmCall.stage == st)
        count_stmt = count_stmt.where(LlmCall.stage == st)
    if ok is not None:
        stmt = stmt.where(LlmCall.ok == ok)
        count_stmt = count_stmt.where(LlmCall.ok == ok)
    df = _parse_dt(date_from)
    if df is not None:
        stmt = stmt.where(LlmCall.created_at >= df)
        count_stmt = count_stmt.where(LlmCall.created_at >= df)
    dt = _parse_dt(date_to, end=True)
    if dt is not None:
        stmt = stmt.where(LlmCall.created_at <= dt)
        count_stmt = count_stmt.where(LlmCall.created_at <= dt)
    needle = (q or "").strip()
    if needle:
        like = f"%{needle}%"
        parts = [
            LlmCall.project_id.ilike(like),
            LlmCall.detail.ilike(like),
            LlmCall.stage.ilike(like),
        ]
        stage_keys = _stages_matching_query(needle)
        if stage_keys:
            parts.append(LlmCall.stage.in_(stage_keys))
        cond = or_(*parts)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    total = int((await db.scalar(count_stmt)) or 0)
    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))
    offset = (page - 1) * page_size
    result = await db.execute(stmt.order_by(LlmCall.id.desc()).offset(offset).limit(page_size))
    rows = result.scalars().all()
    return {
        "items": [
            {
                "id": r.id,
                "project_id": r.project_id,
                "stage": r.stage,
                "tokens": r.tokens,
                "ok": r.ok,
                "detail": (r.detail or "")[:240],
                "created_at": r.created_at,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


_TOOL_VER_CACHE: dict[str, tuple[float, str]] = {}
_TOOL_VER_TTL = 60.0

