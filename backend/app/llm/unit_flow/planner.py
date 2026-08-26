"""从 workspace + spec 确定性生成 DeliveryPlan（不调 LLM）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.bake.schema.er import build_schema_model, collect_english_gaps, count_er_gaps
from app.bake.schema.modules import build_module_model, collect_module_label_gaps
from app.bake.schema.testcases import build_testcase_skeleton
from app.llm.agents_common import _LABEL_KEYS, _SEED_KEYS
from app.llm.unit_flow.context_budget import proposal_excerpt
from app.llm.unit_flow.models import DeliveryPlan, FrozenSpec, TaskUnit, UnitKind

# 对标 ai-ppt：单元越小，失败面越小、可并发越高
LABEL_BATCH = 4
ER_BATCH = 8
MODULE_BATCH = 5
TESTCASE_BATCH = 4


def _chunk(items: list[Any], size: int) -> list[list[Any]]:
    if size <= 0:
        return [items] if items else []
    return [items[i : i + size] for i in range(0, len(items), size)]


def _frozen_from_spec(spec: dict[str, Any]) -> FrozenSpec:
    schema = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
    caps = schema.get("capabilities") if isinstance(schema.get("capabilities"), list) else []
    arches = spec.get("archetypes") if isinstance(spec.get("archetypes"), list) else []
    if not arches and spec.get("archetype"):
        arches = [str(spec["archetype"])]
    return FrozenSpec(
        domain=str(spec.get("domain") or ""),
        title=str(spec.get("title") or ""),
        accept=str(schema.get("accept") or spec.get("accept") or ""),
        scene=str(schema.get("scene") or ""),
        persistence=str(spec.get("persistence") or "jdbc"),
        spring_security=bool(spec.get("spring_security")),
        capabilities=[str(c) for c in caps],
        archetypes=[str(a) for a in arches],
    )


def _plan_island_units(base: dict[str, Any], proposal: str) -> list[TaskUnit]:
    labels = dict(base.get("labels") or {})
    seeds = dict(base.get("seeds") or {})
    entities = dict(base.get("entities") or {})
    roles = dict(base.get("roles") or {})
    units: list[TaskUnit] = []

    label_keys = [k for k in _LABEL_KEYS if k in labels or k in ("authLead", "authEyebrow", "appName")]
    for i, batch in enumerate(_chunk(label_keys, LABEL_BATCH)):
        units.append(
            TaskUnit(
                id=f"island.labels.{i}",
                kind=UnitKind.island_labels,
                payload={
                    "keys": batch,
                    "current": {k: labels.get(k) for k in batch},
                },
                source_refs=["proposal:features"],
                budget_chars=1800,
            )
        )

    seed_keys = [k for k in _SEED_KEYS if k in seeds or k == "noticeTitle"]
    if seed_keys:
        units.append(
            TaskUnit(
                id="island.seeds",
                kind=UnitKind.island_seeds,
                payload={
                    "keys": seed_keys,
                    "current": {k: seeds.get(k) for k in seed_keys},
                },
                source_refs=["proposal:background"],
                budget_chars=1500,
            )
        )

    ent_keys = [k for k in entities if isinstance(entities.get(k), dict)]
    if ent_keys:
        units.append(
            TaskUnit(
                id="island.entities",
                kind=UnitKind.island_entities,
                payload={
                    "keys": ent_keys,
                    "current": {
                        k: {
                            kk: entities[k].get(kk)
                            for kk in ("label", "labelPlural", "verbs", "states")
                            if isinstance(entities[k], dict) and entities[k].get(kk) is not None
                        }
                        for k in ent_keys
                    },
                },
                source_refs=["proposal:features"],
                budget_chars=2000,
            )
        )

    has_roles = bool(roles.get("staff_posts")) or any(
        w in proposal for w in ("岗位", "角色", "管理员", "用户", "馆员", "辅导员")
    )
    if has_roles and roles:
        units.append(
            TaskUnit(
                id="island.roles",
                kind=UnitKind.island_roles,
                payload={
                    "current_roles": {
                        "user": (roles.get("user") or {}).get("label") if isinstance(roles.get("user"), dict) else None,
                        "admin": (roles.get("admin") or {}).get("label") if isinstance(roles.get("admin"), dict) else None,
                        "subadmin": (roles.get("subadmin") or {}).get("label")
                        if isinstance(roles.get("subadmin"), dict)
                        else None,
                        "staff_posts": [
                            {"id": p.get("id"), "label": p.get("label"), "kind": p.get("kind")}
                            for p in (roles.get("staff_posts") or [])
                            if isinstance(p, dict) and p.get("id")
                        ],
                    },
                },
                source_refs=["proposal:roles"],
                budget_chars=1200,
            )
        )
    return units


def _plan_er_units(workspace: Path) -> list[TaskUnit]:
    fresh = build_schema_model(workspace, with_er_patch=False)
    if not fresh:
        return []
    gaps = collect_english_gaps(fresh)
    if count_er_gaps(gaps) == 0:
        return []

    flat: list[tuple[str, dict[str, Any]]] = []
    for row in gaps.get("tables") or []:
        flat.append(("table", row))
    for row in gaps.get("columns") or []:
        flat.append(("column", row))
    for row in gaps.get("relations") or []:
        flat.append(("relation", row))

    units: list[TaskUnit] = []
    for i, batch in enumerate(_chunk(flat, ER_BATCH)):
        payload: dict[str, Any] = {"tables": [], "columns": [], "relations": []}
        for kind, row in batch:
            if kind == "table":
                payload["tables"].append(row)
            elif kind == "column":
                payload["columns"].append(row)
            else:
                payload["relations"].append(row)
        units.append(
            TaskUnit(
                id=f"er.{i}",
                kind=UnitKind.er_labels,
                payload={"gaps": payload},
                source_refs=[f"schema:{r.get('name', i)}" for _, r in batch[:3]],
                budget_chars=3000,
            )
        )
    return units


def _plan_module_units(workspace: Path, proposal_text: str) -> list[TaskUnit]:
    fresh_biz = build_module_model(workspace, with_label_patch=False, proposal_text=proposal_text, layout="biz")
    fresh_side = build_module_model(workspace, with_label_patch=False, proposal_text=proposal_text, layout="side")
    gaps_by_id: dict[str, dict[str, str]] = {}
    for m in (fresh_biz, fresh_side):
        if not m:
            continue
        for g in collect_module_label_gaps(m):
            gid = str(g.get("id") or "")
            if gid and gid not in gaps_by_id:
                gaps_by_id[gid] = g

    has_latin_gaps = bool(gaps_by_id)
    gaps = list(gaps_by_id.values())
    if not gaps:
        # branch_refine：无拉丁缺口时仍允许 1 个单元按开题微调一级分支
        flat: list[dict[str, str]] = []

        def _walk(n: dict, acc: list) -> None:
            acc.append({"id": str(n.get("id") or ""), "label": str(n.get("label") or ""), "source": str(n.get("source") or "")})
            for c in n.get("children") or []:
                if isinstance(c, dict):
                    _walk(c, acc)

        for m in (fresh_biz, fresh_side):
            if isinstance(m, dict) and isinstance(m.get("root"), dict):
                _walk(m["root"], flat)
        branch = [x for x in flat if x.get("source") in ("branch", "system") and x.get("id")]
        if not branch:
            return []
        gaps = branch[:MODULE_BATCH]

    units: list[TaskUnit] = []
    for i, batch in enumerate(_chunk(gaps, MODULE_BATCH)):
        scope = "gaps_only" if has_latin_gaps else "branch_refine"
        units.append(
            TaskUnit(
                id=f"module.{i}",
                kind=UnitKind.module_labels,
                payload={"target": batch, "scope": scope},
                source_refs=["proposal:modules"],
                budget_chars=3500,
            )
        )
    return units


def _plan_testcase_units(workspace: Path) -> list[TaskUnit]:
    skeleton_model = build_testcase_skeleton(workspace)
    if not skeleton_model:
        return []
    rows = skeleton_model.get("skeleton") or []
    if not rows:
        return []

    slim = [
        {
            "id": r.get("id"),
            "module": r.get("module"),
            "item": r.get("item"),
            "key": r.get("key"),
            "side": r.get("side"),
            "precondition": r.get("precondition"),
            "steps": r.get("steps"),
            "input": r.get("input"),
            "expected": r.get("expected"),
        }
        for r in rows
    ]
    units: list[TaskUnit] = []
    for i, batch in enumerate(_chunk(slim, TESTCASE_BATCH)):
        units.append(
            TaskUnit(
                id=f"testcase.{i}",
                kind=UnitKind.testcase_labels,
                payload={"target": batch},
                source_refs=[str(r.get("id") or "") for r in batch],
                budget_chars=4000,
            )
        )
    return units


def build_delivery_plan(
    workspace: Path,
    spec: dict[str, Any],
    proposal_text: str = "",
) -> DeliveryPlan:
    """扫描 workspace 产出全部 TaskUnit；不含 LLM 调用。"""
    excerpt = proposal_excerpt(spec, limit=2400)
    if proposal_text:
        excerpt = (excerpt + "\n" + proposal_text)[:2400]

    base = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
    units: list[TaskUnit] = []
    units.extend(_plan_island_units(base, excerpt))
    units.extend(_plan_er_units(workspace))
    units.extend(_plan_module_units(workspace, excerpt))
    units.extend(_plan_testcase_units(workspace))

    return DeliveryPlan(
        frozen=_frozen_from_spec(spec),
        units=units,
        proposal_excerpt=excerpt,
    )
