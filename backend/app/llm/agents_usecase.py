"""用例图段落描述润色：只改目的语，禁止改动「」内 L1/L2 名与序号结构。

无 Key / 预算不足 / 校验失败 → 回退确定性草稿。不进学生 ZIP。
"""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.bake.schema.usecases import (
    _description_paragraph,
    assert_usecase_invariants,
)
from app.llm.client import (
    append_deepseek_log,
    budget_ok,
    chat,
    format_usage_detail,
    record_call,
)
from app.llm.runtime import LlmRuntime

_QUOTE_RE = re.compile(r"「([^」]+)」")


def _required_quotes(level1: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for uc in level1:
        if not isinstance(uc, dict):
            continue
        lab = str(uc.get("label") or "").strip()
        if lab:
            out.append(lab)
        for kid in uc.get("includes") or []:
            if not isinstance(kid, dict):
                continue
            klab = str(kid.get("label") or "").strip()
            if klab:
                out.append(klab)
    return out


def accept_polished_description(
    polished: str,
    *,
    draft: str,
    actor: str,
    level1: list[dict[str, Any]],
    n_l1: int,
) -> str | None:
    """校验润色稿；不合规则返回 None。"""
    text = (polished or "").strip()
    if not text or "\n" in text:
        return None
    if "完成相关操作" in text:
        return None
    for i in range(1, n_l1 + 1):
        if text.count(f"（{i}）") != 1:
            return None
    if f"（{n_l1 + 1}）" in text:
        return None
    # 草稿中全部「」用例名必须原样出现（允许增删连接词，不许改圈名）
    for name in _required_quotes(level1):
        if f"「{name}」" not in text:
            return None
    # 禁止发明新的「」圈名
    draft_names = set(_QUOTE_RE.findall(draft))
    for name in _QUOTE_RE.findall(text):
        if name not in draft_names:
            return None
    if actor and actor not in text:
        return None
    return text


async def polish_usecase_description(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    model: dict[str, Any],
    title: str = "",
) -> tuple[dict[str, Any], bool]:
    """润色 model['description']。返回 (model, used_llm)。"""
    out = dict(model)
    level1 = out.get("level1") if isinstance(out.get("level1"), list) else []
    actor = str((out.get("actor") or {}).get("label") or "")
    draft = str(out.get("description") or "").strip() or _description_paragraph(actor, level1)
    out["description"] = draft
    n_l1 = len(level1)
    if not rt.configured or n_l1 < 1:
        return out, False
    ok_budget = await budget_ok(db, project_id, rt)
    if not ok_budget:
        append_deepseek_log(project_id, "usecase_prose skip · budget")
        return out, False

    payload = {
        "title": title or str(out.get("title") or ""),
        "actor": actor,
        "level1": [
            {
                "label": uc.get("label"),
                "includes": [
                    {"label": k.get("label"), "relation": k.get("relation")}
                    for k in (uc.get("includes") or [])
                    if isinstance(k, dict)
                ],
            }
            for uc in level1
            if isinstance(uc, dict)
        ],
        "draft": draft,
    }
    messages = [
        {
            "role": "system",
            "content": (
                "你是本科毕设论文「用例图文字说明」润色助手。只输出一段中文（禁止换行、禁止 Markdown）。\n"
                "硬约束：\n"
                "1) 必须保留全部（1）（2）…序号，个数与一级用例一致；\n"
                "2) 草稿里所有「…」用例名必须原样出现，禁止改名/增删用例名；\n"
                "3) 可改「完成…」目的语与连接词，使读感自然；禁止写空壳「完成相关操作」；\n"
                "4) 不要发明未出现在草稿中的功能。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False),
        },
    ]
    res = await chat(rt, messages, json_mode=False, temperature=0.3, timeout=60.0)
    accepted = accept_polished_description(
        (res.text or "").strip(),
        draft=draft,
        actor=actor,
        level1=level1,
        n_l1=n_l1,
    )
    used = bool(res.ok and accepted)
    await record_call(
        db,
        project_id=project_id,
        stage="usecase_prose",
        tokens=res.tokens,
        ok=used,
        detail=format_usage_detail(res, "用例描述润色" if used else "用例描述润色回退"),
    )
    append_deepseek_log(
        project_id,
        f"usecase_prose {'ok' if used else 'fallback'} · {format_usage_detail(res)}",
    )
    if used and accepted:
        out["description"] = accepted
        out["description_polished"] = True
    else:
        out["description_polished"] = False
    return out, used


async def polish_usecase_model_safe(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    model: dict[str, Any],
    schema: dict[str, Any] | None = None,
    title: str = "",
) -> dict[str, Any]:
    """润色后若破坏不变量则回退。"""
    polished, _used = await polish_usecase_description(
        db, rt, project_id=project_id, model=model, title=title
    )
    try:
        assert_usecase_invariants(
            polished,
            schema=schema,
            actor=str((polished.get("actor") or {}).get("id") or ""),
        )
        return polished
    except ValueError:
        fallback = dict(model)
        fallback["description_polished"] = False
        return fallback
