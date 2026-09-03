"""答辩 PPT 填页：骨架 + unit_flow.run_plan_units + 合并 patch。"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.runtime import load_llm_runtime
from app.llm.unit_flow.models import DeliveryPlan, FlowRunSummary, UnitResult, UnitStatus
from app.llm.unit_flow.orchestrator import fill_unit_concurrency
from app.llm.unit_flow.runner import run_plan_units
from app.models import Project

from .figures import materialize_artifact_figures
from .planner import build_fallback_pages, build_ppt_plan
from .themes import ensure_ppt_dirs

EventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


def build_skeleton_deck(
    project: Project,
    ctx: dict[str, Any],
    *,
    cover: dict[str, Any],
    theme: str,
    layout_family: str,
    master: str,
) -> dict[str, Any]:
    """大纲骨架（页序固定）；文案由 Unit patch 填入。"""
    title = str(ctx.get("title") or project.title or "毕业设计答辩")
    fb = build_fallback_pages(project, ctx, cover=cover)
    pages = [
        {"id": "cover", "title": "封面", "role": "cover", "cover": dict(cover)},
        {
            "id": "toc",
            "title": "目录",
            "role": "toc",
            "toc_items": list((fb["toc"].get("toc_items") or [])),
        },
        {"id": "background", "title": "背景与需求", "role": "bullets", "bullets": []},
        {"id": "tech", "title": "技术选型", "role": "table", "bullets": [], "table": None},
        {"id": "arch", "title": "系统架构", "role": "bullets", "bullets": []},
        {"id": "modules", "title": "功能模块", "role": "modules", "bullets": [], "figure": {}},
        {"id": "er", "title": "E-R 图", "role": "er", "bullets": [], "figure": {}},
        {"id": "demo", "title": "实现与演示", "role": "demo", "bullets": [], "figure": {}},
        {"id": "test", "title": "测试", "role": "table", "bullets": [], "table": None},
        {"id": "summary", "title": "总结与致谢", "role": "summary", "bullets": []},
    ]
    deck = {
        "version": "1",
        "title": title,
        "theme": theme,
        "layout_family": layout_family,
        "master": master,
        "cover": dict(cover),
        "biz_dirty": False,
        "pages": pages,
    }
    return materialize_artifact_figures(project, deck, ctx)


def apply_unit_patches_to_deck(
    deck: dict[str, Any],
    results: list[UnitResult],
    *,
    preserve_locked: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """把 Unit patch 合并进 deck 页；preserve_locked: page_id → {bullet_id: bullet}。"""
    by_id = {
        p.get("id"): p
        for p in (deck.get("pages") or [])
        if isinstance(p, dict) and p.get("id")
    }
    locked_map = preserve_locked or {}

    for res in results:
        if res.status not in (UnitStatus.done, UnitStatus.skipped):
            continue
        patch = res.patch
        if not isinstance(patch, dict):
            continue
        page_id = str(patch.get("page_id") or "")
        page = by_id.get(page_id)
        if not page:
            continue
        if patch.get("title"):
            page["title"] = str(patch["title"])
        if isinstance(patch.get("cover"), dict):
            page["cover"] = dict(patch["cover"])
            deck["cover"] = dict(patch["cover"])
        if isinstance(patch.get("toc_items"), list):
            page["toc_items"] = list(patch["toc_items"])
        if isinstance(patch.get("table"), dict):
            page["table"] = patch["table"]
        if isinstance(patch.get("bullets"), list):
            old_locked = locked_map.get(page_id) or {}
            merged = []
            for b in patch["bullets"]:
                if not isinstance(b, dict):
                    continue
                bid = str(b.get("id") or "")
                if bid and bid in old_locked:
                    merged.append(dict(old_locked[bid]))
                else:
                    merged.append(
                        {
                            "id": bid,
                            "text": str(b.get("text") or ""),
                            "locked": bool(b.get("locked")),
                            "source_refs": list(b.get("source_refs") or []),
                        }
                    )
            for bid, ob in old_locked.items():
                if bid not in {x.get("id") for x in merged}:
                    merged.append(dict(ob))
            page["bullets"] = merged
    return deck


def _locked_bullets_from_deck(deck: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not deck:
        return out
    for page in deck.get("pages") or []:
        if not isinstance(page, dict):
            continue
        pid = str(page.get("id") or "")
        locked = {
            str(b.get("id")): dict(b)
            for b in (page.get("bullets") or [])
            if isinstance(b, dict) and b.get("locked") and b.get("id")
        }
        if locked:
            out[pid] = locked
    return out


def _save_plan_debug(project: Project, plan: DeliveryPlan, summary: FlowRunSummary | None = None) -> None:
    try:
        root = ensure_ppt_dirs(project)
        debug = root / "debug"
        debug.mkdir(parents=True, exist_ok=True)
        (debug / "plan.json").write_text(
            json.dumps(plan.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if summary is not None:
            (debug / "run.json").write_text(
                json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    except Exception:  # noqa: BLE001
        pass


async def fill_deck_via_unit_flow(
    db: AsyncSession,
    project: Project,
    ctx: dict[str, Any],
    *,
    cover: dict[str, Any],
    theme: str,
    layout_family: str,
    master: str,
    llm_enabled: bool = True,
    on_event: EventCallback | None = None,
    old_deck: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], FlowRunSummary]:
    """与填岛同款：Plan → Semaphore 并发 Unit → 合并。进度事件走 on_event。"""
    deck = build_skeleton_deck(
        project,
        ctx,
        cover=cover,
        theme=theme,
        layout_family=layout_family,
        master=master,
    )
    # 保留旧演示截图
    if old_deck:
        old_demo = next(
            (
                p
                for p in (old_deck.get("pages") or [])
                if isinstance(p, dict) and p.get("role") == "demo"
            ),
            None,
        )
        new_demo = next(
            (
                p
                for p in (deck.get("pages") or [])
                if isinstance(p, dict) and p.get("role") == "demo"
            ),
            None,
        )
        if (
            old_demo
            and new_demo
            and isinstance(old_demo.get("figure"), dict)
            and old_demo["figure"].get("available")
        ):
            new_demo["figure"] = old_demo["figure"]

    plan = build_ppt_plan(project, ctx, cover=cover)
    if on_event:
        await on_event(
            {
                "type": "ppt_plan",
                "total": len(plan.units),
                "units": [
                    {
                        "id": u.id,
                        "key": u.id,
                        "kind": u.kind.value,
                        "title": (u.payload or {}).get("page_title") or u.id,
                        "budget_chars": u.budget_chars,
                        "source_refs": u.source_refs,
                    }
                    for u in plan.units
                ],
            }
        )

    rt = await load_llm_runtime(db)
    # base_schema 给校验器用；PPT 主要靠 unit.payload.allowlist
    spec = {
        "schema": ctx.get("features") and {"features": ctx.get("features")} or {},
        "title": ctx.get("title"),
        "domain": ctx.get("domain"),
    }
    summary = await run_plan_units(
        db,
        rt,
        plan,
        project_id=project.id,
        spec=spec,
        llm_enabled=llm_enabled,
        concurrency=fill_unit_concurrency(rt),
        on_event=on_event,
    )
    locked = _locked_bullets_from_deck(old_deck)
    deck = apply_unit_patches_to_deck(deck, summary.results, preserve_locked=locked)
    _save_plan_debug(project, plan, summary)
    return deck, summary


# 兼容旧调用名（确定性整 deck，无 LLM）
def build_deck_from_context(
    project: Project,
    ctx: dict[str, Any],
    *,
    cover: dict[str, Any],
    theme: str,
    layout_family: str,
    master: str,
) -> dict[str, Any]:
    deck = build_skeleton_deck(
        project,
        ctx,
        cover=cover,
        theme=theme,
        layout_family=layout_family,
        master=master,
    )
    fb = build_fallback_pages(project, ctx, cover=cover)
    fake_results = [
        UnitResult(
            unit_id=f"ppt.{pid}",
            status=UnitStatus.done,
            patch=patch,
        )
        for pid, patch in fb.items()
    ]
    return apply_unit_patches_to_deck(deck, fake_results)
