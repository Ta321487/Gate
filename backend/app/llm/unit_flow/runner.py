"""TaskUnit 并发编排 + micro-loop（prepare → generate → check → repair）。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import append_deepseek_log, budget_ok, record_call
from app.llm.runtime import LlmRuntime
from app.llm.unit_flow.executors import execute_unit_llm, repair_hints
from app.llm.unit_flow.models import DeliveryPlan, FlowRunSummary, TaskUnit, UnitKind, UnitResult, UnitStatus
from app.llm.unit_flow.validators import validate_unit_patch

EventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


async def _emit(on_event: EventCallback | None, payload: dict[str, Any]) -> None:
    if not on_event:
        return
    maybe = on_event(payload)
    if asyncio.iscoroutine(maybe):
        await maybe


async def run_single_unit(
    db: AsyncSession,
    rt: LlmRuntime,
    plan: DeliveryPlan,
    unit: TaskUnit,
    *,
    project_id: str,
    base_schema: dict[str, Any],
    llm_enabled: bool,
) -> UnitResult:
    """单单元 micro-loop：最多 max_attempts 轮，带 issues 重试。"""
    # 封面/目录等确定性页：不调 LLM，直接交 payload.patch
    if unit.kind == UnitKind.ppt_page and unit.payload.get("deterministic"):
        patch = unit.payload.get("patch")
        if isinstance(patch, dict):
            return UnitResult(
                unit.id,
                UnitStatus.done,
                patch=dict(patch),
                attempts=0,
                context=dict(unit.payload),
            )
        return UnitResult(unit.id, UnitStatus.skipped, attempts=0)

    if unit.id.startswith("ppt."):
        stage = "defense_ppt"
    elif unit.id.startswith("island."):
        stage = "island_fill"
    elif unit.id.startswith("er."):
        stage = "er_labels"
    elif unit.id.startswith("module."):
        stage = "module_labels"
    elif unit.id.startswith("testcase."):
        stage = "testcase_labels"
    else:
        stage = "island_fill"

    # 答辩 PPT：LLM 关/未配/预算尽 → 用确定性 fallback_patch（仍算 done，避免整页空白）
    if unit.kind == UnitKind.ppt_page:
        fallback = unit.payload.get("fallback_patch")
        use_fallback = (
            not llm_enabled
            or not rt.configured
            or not rt.stage_on(stage)
            or not await budget_ok(db, project_id, rt)
        )
        if use_fallback:
            if isinstance(fallback, dict):
                return UnitResult(
                    unit.id,
                    UnitStatus.done,
                    patch=dict(fallback),
                    attempts=0,
                    context=dict(unit.payload),
                )
            return UnitResult(unit.id, UnitStatus.skipped, attempts=0)

    if not llm_enabled or not rt.configured:
        return UnitResult(unit.id, UnitStatus.skipped, attempts=0)

    if not rt.stage_on(stage):
        return UnitResult(unit.id, UnitStatus.skipped, attempts=0)

    if not await budget_ok(db, project_id, rt):
        append_deepseek_log(project_id, f"unit_flow {unit.id} skip · budget exceeded")
        return UnitResult(unit.id, UnitStatus.skipped, attempts=0)

    repair_msgs: list[dict[str, str]] = []
    total_tokens = 0
    last_error = ""

    for attempt in range(unit.max_attempts):
        unit.attempts = attempt + 1
        patch, tokens, detail = await execute_unit_llm(
            rt,
            plan,
            unit,
            base_schema=base_schema,
            repair_messages=repair_msgs,
        )
        total_tokens += tokens
        vr = validate_unit_patch(unit, patch, base_schema=base_schema)
        if patch and vr.ok:
            await record_call(
                db,
                project_id=project_id,
                stage=f"unit:{unit.id}",
                tokens=tokens,
                ok=True,
                detail=detail,
            )
            append_deepseek_log(project_id, f"unit {unit.id} ok attempt={attempt + 1} {detail}")
            return UnitResult(
                unit.id,
                UnitStatus.done,
                patch=patch,
                tokens=total_tokens,
                attempts=attempt + 1,
                context=dict(unit.payload),
            )

        last_error = detail if not patch else "; ".join(i.message for i in vr.errors[:3])
        # PPT：校验失败且有 fallback 时，末轮兜底，避免整页空白
        if (
            unit.kind == UnitKind.ppt_page
            and attempt + 1 >= unit.max_attempts
            and isinstance(unit.payload.get("fallback_patch"), dict)
        ):
            append_deepseek_log(
                project_id, f"unit {unit.id} fallback after fail · {last_error}"
            )
            return UnitResult(
                unit.id,
                UnitStatus.done,
                patch=dict(unit.payload["fallback_patch"]),
                tokens=total_tokens,
                attempts=attempt + 1,
                context=dict(unit.payload),
            )
        repair_msgs = repair_hints([last_error] if last_error else ["输出无效"])
        append_deepseek_log(project_id, f"unit {unit.id} retry attempt={attempt + 1} · {last_error}")

    await record_call(
        db,
        project_id=project_id,
        stage=f"unit:{unit.id}",
        tokens=total_tokens,
        ok=False,
        detail=last_error or "failed",
    )
    return UnitResult(
        unit.id,
        UnitStatus.failed,
        tokens=total_tokens,
        error=last_error or "failed",
        attempts=unit.max_attempts,
    )


async def run_plan_units(
    db: AsyncSession,
    rt: LlmRuntime,
    plan: DeliveryPlan,
    *,
    project_id: str,
    spec: dict[str, Any],
    llm_enabled: bool = True,
    concurrency: int = 3,
    on_event: EventCallback | None = None,
) -> FlowRunSummary:
    """并发执行 plan 内全部 unit（Semaphore 限流，对标 ai-ppt ARQ + Semaphore）。"""
    base_schema = dict(spec.get("schema") or {})
    sem = asyncio.Semaphore(max(1, concurrency))
    results: list[UnitResult] = []

    async def _run_one(unit: TaskUnit) -> UnitResult:
        async with sem:
            await _emit(
                on_event,
                {"type": "unit_started", "unit_id": unit.id, "kind": unit.kind.value},
            )
            res = await run_single_unit(
                db,
                rt,
                plan,
                unit,
                project_id=project_id,
                base_schema=base_schema,
                llm_enabled=llm_enabled,
            )
            if res.status == UnitStatus.skipped:
                await _emit(
                    on_event,
                    {
                        "type": "unit_skipped",
                        "unit_id": unit.id,
                        "status": res.status.value,
                    },
                )
            elif res.status == UnitStatus.done:
                await _emit(
                    on_event,
                    {
                        "type": "unit_done",
                        "unit_id": unit.id,
                        "status": res.status.value,
                        "error": res.error,
                    },
                )
            else:
                await _emit(
                    on_event,
                    {
                        "type": "unit_failed",
                        "unit_id": unit.id,
                        "status": res.status.value,
                        "error": res.error,
                    },
                )
            return res

    tasks = [_run_one(u) for u in plan.units]
    if tasks:
        results = list(await asyncio.gather(*tasks))

    return FlowRunSummary(plan=plan, results=results)


def save_plan_artifact(workspace: Path, plan: DeliveryPlan) -> Path:
    out_dir = workspace / "islands" / "unit_flow"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "plan.json"
    path.write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def save_run_artifact(workspace: Path, summary: FlowRunSummary) -> Path:
    out_dir = workspace / "islands" / "unit_flow"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "run.json"
    payload = {
        **summary.to_dict(),
        "plan_frozen": summary.plan.frozen.to_dict(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
