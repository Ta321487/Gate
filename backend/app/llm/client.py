from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.llm.runtime import LlmRuntime, ProviderEndpoint
from app.models import LlmCall, Project

logger = logging.getLogger("gf.llm")

_JSON_BLOCK = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.I)

# 2026-07-24 起 deepseek-chat / deepseek-reasoner 停用；reasoner 语义用 thinking 开关表达
_LEGACY_MODELS = {
    "deepseek-chat": "deepseek-v4-flash",
    "deepseek-reasoner": "deepseek-v4-flash",
}


@dataclass
class ChatResult:
    text: str
    tokens: int
    ok: bool
    error: str = ""
    data: dict[str, Any] | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    model: str = ""
    provider: str = ""


def resolve_model(model: str, *, provider: str = "deepseek") -> str:
    m = (model or "").strip()
    if provider == "gemini":
        return m or "gemini-2.5-flash"
    m = m or "deepseek-v4-flash"
    return _LEGACY_MODELS.get(m, m)


def format_usage_detail(res: ChatResult, note: str = "") -> str:
    if res.error:
        return res.error
    parts = [note or "ok"]
    parts.append(f"输入={res.prompt_tokens}")
    parts.append(f"输出={res.completion_tokens}")
    if res.reasoning_tokens:
        parts.append(f"思考={res.reasoning_tokens}")
    if res.provider:
        parts.append(res.provider)
    if res.model:
        parts.append(res.model)
    return " · ".join(p for p in parts if p)


async def project_tokens_used(db: AsyncSession, project_id: str) -> int:
    n = await db.scalar(
        select(func.coalesce(func.sum(LlmCall.tokens), 0)).where(LlmCall.project_id == project_id)
    )
    return int(n or 0)


async def project_lifetime_token_rows(db: AsyncSession) -> list[dict[str, Any]]:
    """库内全部项目的全期 Token（与 budget_ok 的项目闸一致，无时间窗）。"""
    usage_sq = (
        select(
            LlmCall.project_id.label("project_id"),
            func.coalesce(func.sum(LlmCall.tokens), 0).label("tokens"),
        )
        .where(LlmCall.project_id.is_not(None))
        .group_by(LlmCall.project_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(Project.id, func.coalesce(usage_sq.c.tokens, 0))
            .outerjoin(usage_sq, Project.id == usage_sq.c.project_id)
            .order_by(Project.id)
        )
    ).all()
    return [{"project_id": pid, "tokens": int(tokens or 0)} for pid, tokens in rows]


# 工厂侧辅助调用（上传分堆、样例开题等），仍服务毕设场景，但与项目生成流水线分开统计
SUPPORT_STAGES = frozenset({"upload_cluster", "sample_proposal"})


def call_kind(stage: str | None) -> str:
    """返回 support | pipeline。"""
    return "support" if (stage or "").strip() in SUPPORT_STAGES else "pipeline"


async def monthly_tokens_used(db: AsyncSession) -> int:
    """当前自然月累计 token（工厂侧记账，含流水线 + 系统支持）。"""
    start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    n = await db.scalar(
        select(func.coalesce(func.sum(LlmCall.tokens), 0)).where(LlmCall.created_at >= start)
    )
    return int(n or 0)


async def monthly_tokens_breakdown(db: AsyncSession) -> dict[str, Any]:
    """本月 Token 拆分：合计 / 项目流水线 / 系统支持（含按 stage）。"""
    start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = (
        await db.execute(
            select(
                LlmCall.stage,
                func.coalesce(func.sum(LlmCall.tokens), 0).label("tokens"),
                func.count(LlmCall.id).label("calls"),
            )
            .where(LlmCall.created_at >= start)
            .group_by(LlmCall.stage)
        )
    ).all()
    pipeline = 0
    support = 0
    support_by_stage: list[dict[str, Any]] = []
    for stage, tokens, calls in rows:
        n = int(tokens or 0)
        c = int(calls or 0)
        st = str(stage or "")
        if st in SUPPORT_STAGES:
            support += n
            support_by_stage.append({"stage": st, "tokens": n, "calls": c})
        else:
            pipeline += n
    support_by_stage.sort(key=lambda x: (-int(x["tokens"]), str(x["stage"])))
    return {
        "total": pipeline + support,
        "pipeline": pipeline,
        "support": support,
        "support_by_stage": support_by_stage,
    }


_USAGE_SORT_COLS = {
    "tokens": func.sum(LlmCall.tokens),
    "calls": func.count(LlmCall.id),
    "last_at": func.max(LlmCall.created_at),
    # 预算全局一致时，占比与 tokens 同序
    "pct": func.sum(LlmCall.tokens),
}


async def project_usage_rows(
    db: AsyncSession,
    *,
    q: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 10,
    limit: int | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    presence: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """按项目汇总用量（仅流水线，不含系统支持）；支持时间范围、项目 ID 模糊查、排序与分页。

    presence: all | alive | deleted（默认 alive，隐藏已删项目）
    """
    start = date_from or datetime.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    base = (
        select(
            LlmCall.project_id,
            func.coalesce(func.sum(LlmCall.tokens), 0).label("tokens"),
            func.count(LlmCall.id).label("calls"),
            func.max(LlmCall.created_at).label("last_at"),
        )
        .where(LlmCall.created_at >= start)
        .where(LlmCall.project_id.is_not(None))
        .where(LlmCall.stage.notin_(SUPPORT_STAGES))
    )
    if date_to is not None:
        base = base.where(LlmCall.created_at <= date_to)
    needle = (q or "").strip()
    if needle:
        base = base.where(LlmCall.project_id.ilike(f"%{needle}%"))
    alive_exists = exists().where(Project.id == LlmCall.project_id)
    mode = (presence or "alive").strip().lower()
    if mode == "deleted":
        base = base.where(~alive_exists)
    elif mode != "all":
        base = base.where(alive_exists)
    base = base.group_by(LlmCall.project_id)
    # 分组后总数：子查询计数
    count_q = select(func.count()).select_from(base.subquery())
    total = int((await db.scalar(count_q)) or 0)
    page = max(1, int(page))
    if limit is not None:
        page_size = max(1, int(limit))
        offset = 0
    else:
        page_size = max(1, min(100, int(page_size)))
        offset = (page - 1) * page_size
    sort_col = _USAGE_SORT_COLS.get((sort_by or "").strip(), func.sum(LlmCall.tokens))
    ascending = (sort_order or "").strip().lower() in ("asc", "ascend", "ascending")
    order_expr = sort_col.asc() if ascending else sort_col.desc()
    rows_q = base.order_by(order_expr).offset(offset).limit(page_size)
    rows = (await db.execute(rows_q)).all()
    ids = [r.project_id for r in rows if r.project_id]
    titles: dict[str, str] = {}
    if ids:
        for pid, title in (
            await db.execute(select(Project.id, Project.title).where(Project.id.in_(ids)))
        ).all():
            titles[pid] = title or ""
    alive = set(titles)
    items = [
        {
            "project_id": r.project_id or "",
            "title": titles.get(r.project_id or "", ""),
            "tokens": int(r.tokens or 0),
            "calls": int(r.calls or 0),
            "last_at": r.last_at,
            "deleted": (r.project_id or "") not in alive,
        }
        for r in rows
    ]
    return items, total


def _fill_daily_series(
    by_day: dict[str, dict[str, int]],
    *,
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    daily: list[dict[str, Any]] = []
    cursor = start.date()
    last = end.date()
    span_days = (last - cursor).days + 1
    if span_days > 120:
        for key in sorted(by_day.keys()):
            hit = by_day[key]
            daily.append({"date": key, "tokens": hit["tokens"], "calls": hit["calls"]})
        return daily
    while cursor <= last:
        key = cursor.isoformat()
        hit = by_day.get(key) or {"tokens": 0, "calls": 0}
        daily.append({"date": key, "tokens": hit["tokens"], "calls": hit["calls"]})
        cursor = cursor + timedelta(days=1)
    return daily


async def project_usage_chart(
    db: AsyncSession,
    *,
    q: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    presence: str | None = None,
) -> dict[str, Any]:
    """用量透视：按日 Token 合计（折线，仅流水线）。"""
    start = date_from or datetime.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    end = date_to or datetime.now()
    if end < start:
        start, end = end, start

    filters = [
        LlmCall.created_at >= start,
        LlmCall.created_at <= end,
        LlmCall.project_id.is_not(None),
        LlmCall.stage.notin_(SUPPORT_STAGES),
    ]
    needle = (q or "").strip()
    if needle:
        filters.append(LlmCall.project_id.ilike(f"%{needle}%"))
    alive_exists = exists().where(Project.id == LlmCall.project_id)
    mode = (presence or "alive").strip().lower()
    if mode == "deleted":
        filters.append(~alive_exists)
    elif mode != "all":
        filters.append(alive_exists)

    day_expr = func.date(LlmCall.created_at)
    daily_rows = (
        await db.execute(
            select(
                day_expr.label("day"),
                func.coalesce(func.sum(LlmCall.tokens), 0).label("tokens"),
                func.count(LlmCall.id).label("calls"),
            )
            .where(*filters)
            .group_by(day_expr)
            .order_by(day_expr)
        )
    ).all()
    by_day: dict[str, dict[str, int]] = {}
    for r in daily_rows:
        key = str(r.day)[:10]
        by_day[key] = {"tokens": int(r.tokens or 0), "calls": int(r.calls or 0)}

    return {
        "daily": _fill_daily_series(by_day, start=start, end=end),
        "date_from": start,
        "date_to": end,
    }


async def support_usage(
    db: AsyncSession,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    """系统支持用量：按 stage 汇总 + 按日折线。"""
    start = date_from or datetime.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    end = date_to or datetime.now()
    if end < start:
        start, end = end, start

    filters = [
        LlmCall.created_at >= start,
        LlmCall.created_at <= end,
        LlmCall.stage.in_(SUPPORT_STAGES),
    ]
    stage_rows = (
        await db.execute(
            select(
                LlmCall.stage,
                func.coalesce(func.sum(LlmCall.tokens), 0).label("tokens"),
                func.count(LlmCall.id).label("calls"),
                func.max(LlmCall.created_at).label("last_at"),
            )
            .where(*filters)
            .group_by(LlmCall.stage)
            .order_by(func.sum(LlmCall.tokens).desc())
        )
    ).all()
    by_stage = [
        {
            "stage": str(r.stage or ""),
            "tokens": int(r.tokens or 0),
            "calls": int(r.calls or 0),
            "last_at": r.last_at,
        }
        for r in stage_rows
    ]
    # 保证已知 stage 也出现（零用量）
    seen = {x["stage"] for x in by_stage}
    for st in sorted(SUPPORT_STAGES):
        if st not in seen:
            by_stage.append({"stage": st, "tokens": 0, "calls": 0, "last_at": None})

    day_expr = func.date(LlmCall.created_at)
    daily_rows = (
        await db.execute(
            select(
                day_expr.label("day"),
                func.coalesce(func.sum(LlmCall.tokens), 0).label("tokens"),
                func.count(LlmCall.id).label("calls"),
            )
            .where(*filters)
            .group_by(day_expr)
            .order_by(day_expr)
        )
    ).all()
    by_day: dict[str, dict[str, int]] = {}
    for r in daily_rows:
        key = str(r.day)[:10]
        by_day[key] = {"tokens": int(r.tokens or 0), "calls": int(r.calls or 0)}

    total_tokens = sum(int(x["tokens"]) for x in by_stage)
    total_calls = sum(int(x["calls"]) for x in by_stage)
    return {
        "tokens": total_tokens,
        "calls": total_calls,
        "by_stage": by_stage,
        "daily": _fill_daily_series(by_day, start=start, end=end),
        "date_from": start,
        "date_to": end,
    }


async def budget_ok(db: AsyncSession, project_id: str, rt: LlmRuntime) -> bool:
    used = await project_tokens_used(db, project_id)
    if used >= rt.project_token_budget:
        return False
    monthly = await monthly_tokens_used(db)
    if monthly >= rt.monthly_token_budget:
        return False
    return True


async def record_call(
    db: AsyncSession,
    *,
    project_id: str | None,
    stage: str,
    tokens: int,
    ok: bool,
    detail: str,
) -> None:
    db.add(
        LlmCall(
            project_id=project_id,
            stage=stage,
            tokens=max(0, int(tokens)),
            ok=ok,
            detail=(detail or "")[:2000],
        )
    )
    await db.commit()


def append_deepseek_log(project_id: str, line: str) -> None:
    settings = get_settings()
    path = settings.logs_dir / project_id / "deepseek.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {line}\n")


def extract_json(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    m = _JSON_BLOCK.search(raw)
    if m:
        raw = m.group(1).strip()
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        # 截取首尾大括号
        a, b = raw.find("{"), raw.rfind("}")
        if a >= 0 and b > a:
            try:
                obj = json.loads(raw[a : b + 1])
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError:
                return None
    return None


async def chat(
    rt: LlmRuntime,
    messages: list[dict[str, str]],
    *,
    json_mode: bool = False,
    temperature: float = 0.3,
    timeout: float = 90.0,
) -> ChatResult:
    """按启用链调用：优先厂商失败或 JSON 不可用时自动换下一家。"""
    chain = rt.endpoint_chain()
    if not chain:
        return ChatResult(
            text="",
            tokens=0,
            ok=False,
            error="未启用或未配置任何 LLM（DeepSeek / Gemini）",
        )
    last = ChatResult(text="", tokens=0, ok=False, error="无可用结果")
    for i, ep in enumerate(chain):
        res = await _chat_endpoint(
            ep,
            messages,
            json_mode=json_mode,
            temperature=temperature,
            timeout=timeout,
        )
        # 成功且（非 JSON 模式，或已解析出对象）→ 采用
        if res.ok and (not json_mode or res.data is not None):
            if i > 0:
                logger.info("llm failover ok · %s after %s", ep.name, chain[0].name)
            return res
        # 成功但 JSON 解析失败 → 记下来，试下一家
        if res.ok and json_mode and res.data is None:
            last = ChatResult(
                text=res.text,
                tokens=res.tokens,
                ok=False,
                error=f"{ep.name}: JSON 解析失败",
                prompt_tokens=res.prompt_tokens,
                completion_tokens=res.completion_tokens,
                reasoning_tokens=res.reasoning_tokens,
                model=res.model,
                provider=ep.name,
            )
            continue
        last = res
    return last


async def _chat_endpoint(
    ep: ProviderEndpoint,
    messages: list[dict[str, str]],
    *,
    json_mode: bool,
    temperature: float,
    timeout: float,
) -> ChatResult:
    provider = (ep.name or "deepseek").strip().lower() or "deepseek"
    if not ep.configured:
        key_env = "GEMINI_API_KEY" if provider == "gemini" else "DEEPSEEK_API_KEY"
        return ChatResult(
            text="",
            tokens=0,
            ok=False,
            error=f"未配置 {key_env}",
            provider=provider,
        )
    model = resolve_model(ep.model, provider=provider)
    url = f"{ep.base_url.rstrip('/')}/chat/completions"
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if provider == "deepseek":
        body["thinking"] = {"type": "enabled" if ep.thinking else "disabled"}
        if not ep.thinking:
            body["temperature"] = temperature
    else:
        body["temperature"] = temperature
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    headers = {
        "Authorization": f"Bearer {ep.api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, headers=headers, json=body)
        if r.status_code >= 400:
            return ChatResult(
                text="",
                tokens=0,
                ok=False,
                error=f"HTTP {r.status_code}: {r.text[:300]}",
                model=model,
                provider=provider,
            )
        payload = r.json()
        choice = (payload.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        text = str(msg.get("content") or "")
        usage = payload.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        details = usage.get("completion_tokens_details") or {}
        reasoning_tokens = int(details.get("reasoning_tokens") or 0)
        tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens) or 0)
        data = extract_json(text) if json_mode or text.strip().startswith("{") else None
        if json_mode and data is None:
            data = extract_json(text)
        return ChatResult(
            text=text,
            tokens=tokens,
            ok=True,
            data=data,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
            model=model,
            provider=provider,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("llm chat failed · %s", provider)
        return ChatResult(
            text="",
            tokens=0,
            ok=False,
            error=str(e),
            model=model,
            provider=provider,
        )


def write_qa_report(workspace: Path, report: dict[str, Any]) -> Path:
    islands = workspace / "islands"
    islands.mkdir(parents=True, exist_ok=True)
    path = islands / "qa_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
