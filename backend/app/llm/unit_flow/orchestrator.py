"""填岛/标签拆解流水线：Plan → Unit 并发 → Merge。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.llm.runtime import LlmRuntime, load_llm_runtime
from app.llm.unit_flow.merge import FillMergeResult, apply_unit_results_to_workspace
from app.llm.unit_flow.models import DeliveryPlan, FlowRunSummary, UnitStatus
from app.llm.unit_flow.planner import build_delivery_plan
from app.llm.unit_flow.runner import _emit, run_plan_units, save_plan_artifact, save_run_artifact
from app.services.proposal import load_merged_proposal_text

EventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


def fill_unit_concurrency(rt: LlmRuntime | None = None) -> int:
    if rt is not None:
        return max(1, min(8, int(rt.fill_unit_concurrency)))
    return max(1, min(8, int(get_settings().gf_fill_unit_concurrency)))


def build_plan_only(
    workspace: Path,
    spec: dict[str, Any],
    proposal_text: str = "",
) -> DeliveryPlan:
    return build_delivery_plan(workspace, spec, proposal_text)


def format_fill_step_meta(summary: FlowRunSummary, *, accept: Any = None) -> str:
    """Job step 2 进度文案。"""
    total = len(summary.results)
    mode = summary.merge_result.mode if summary.merge_result else "unit_flow"
    parts = [
        f"拆解填岛 · {summary.done}/{total} 单元",
        f"模式={mode}",
    ]
    if accept is not None:
        parts.append(f"验收={accept}")
    mr = summary.merge_result
    if mr:
        if mr.er_filled:
            parts.append(f"E-R={mr.er_filled}")
        if mr.module_filled:
            parts.append(f"模块图={mr.module_filled}")
        if mr.testcase_filled:
            parts.append(f"用例={mr.testcase_filled}")
        if summary.failed:
            parts.append(f"失败={summary.failed}")
    return " · ".join(parts)


async def run_fill_pipeline(
    db: AsyncSession,
    *,
    project_id: str,
    workspace: Path,
    spec: dict[str, Any],
    source_path: str | None = None,
    llm_enabled: bool = True,
    merge: bool = True,
    concurrency: int | None = None,
    on_event: EventCallback | None = None,
    llm_rt: LlmRuntime | None = None,
) -> FlowRunSummary:
    """一键生成 step「业务配置填充」唯一实现。"""
    proposal_text = ""
    if source_path:
        try:
            proposal_text = load_merged_proposal_text(source_path)
        except Exception:  # noqa: BLE001
            proposal_text = ""

    plan = build_delivery_plan(workspace, spec, proposal_text)
    save_plan_artifact(workspace, plan)
    await _emit(
        on_event,
        {
            "type": "fill_plan",
            "total": len(plan.units),
            "units": [
                {
                    "id": u.id,
                    "kind": u.kind.value,
                    "budget_chars": u.budget_chars,
                    "source_refs": u.source_refs,
                }
                for u in plan.units
            ],
        },
    )

    rt = await load_llm_runtime(db)
    summary = await run_plan_units(
        db,
        rt,
        plan,
        project_id=project_id,
        spec=spec,
        llm_enabled=llm_enabled,
        concurrency=concurrency or fill_unit_concurrency(llm_rt),
        on_event=on_event,
    )

    merge_result: FillMergeResult | None = None
    if merge:
        merge_result = apply_unit_results_to_workspace(
            workspace,
            spec,
            summary.results,
            llm_enabled=llm_enabled,
        )
        summary.merged = merge_result.ok
        summary.merge_result = merge_result
        summary.merge_detail = merge_result.detail

    save_run_artifact(workspace, summary)
    return summary


# 别名，便于脚本/测试
run_unit_flow = run_fill_pipeline
