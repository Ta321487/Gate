"""单 TaskUnit 的 LLM 执行。"""

from __future__ import annotations

from typing import Any

from app.llm.client import chat, format_usage_detail
from app.llm.runtime import LlmRuntime
from app.llm.unit_flow.models import DeliveryPlan, TaskUnit
from app.llm.unit_flow.prompts import build_unit_messages


def repair_hints(issues: list[str]) -> list[dict[str, str]]:
    if not issues:
        return []
    return [{"role": "user", "content": "上次输出有问题，请修正：\n" + "\n".join(f"- {x}" for x in issues[:5])}]


async def execute_unit_llm(
    rt: LlmRuntime,
    plan: DeliveryPlan,
    unit: TaskUnit,
    *,
    base_schema: dict[str, Any],
    repair_messages: list[dict[str, str]] | None = None,
) -> tuple[dict[str, Any] | None, int, str]:
    """返回 (patch, tokens, detail)。"""
    _ = base_schema  # validate 阶段使用
    messages, temperature = build_unit_messages(plan, unit, repair_messages=repair_messages)
    res = await chat(rt, messages, json_mode=True, temperature=temperature)
    detail = format_usage_detail(res)
    if not res.ok or not isinstance(res.data, dict):
        return None, res.tokens, detail
    return res.data, res.tokens, detail
