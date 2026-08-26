"""将各 Unit patch 合并回 workspace。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.bake.domain_schema import deterministic_llm_patch, merge_schema, validate_schema
from app.bake.engine import emit_schema_to_workspace, llm_fill_islands
from app.bake.schema.er import (
    count_er_patch_fills,
    load_er_label_patch,
    merge_er_label_patch,
    sanitize_er_label_patch,
    save_er_label_patch,
)
from app.bake.schema.modules import (
    load_module_label_patch,
    sanitize_module_label_patch,
    save_module_label_patch,
)
from app.bake.schema.testcases import (
    build_testcase_skeleton,
    load_testcase_label_patch,
    sanitize_testcase_label_patch,
    save_testcase_label_patch,
)
from app.llm.agents_island import _sanitize_island_patch
from app.llm.unit_flow.models import UnitResult, UnitStatus


@dataclass
class FillMergeResult:
    ok: bool
    written: list[str] = field(default_factory=list)
    mode: str = "unit_flow"
    er_filled: int = 0
    module_filled: int = 0
    testcase_filled: int = 0
    detail: str = ""

    def written_paths(self) -> list[str]:
        return [w for w in self.written if "/" in w or w.endswith(".json")]


def _merge_island_patches(results: list[UnitResult], base_schema: dict[str, Any]) -> dict[str, Any]:
    labels = dict(base_schema.get("labels") or {})
    seeds = dict(base_schema.get("seeds") or {})
    roles = dict(base_schema.get("roles") or {})
    combined: dict[str, Any] = {"mode": "unit_flow", "labels": {}, "seeds": {}}

    for r in results:
        if r.status != UnitStatus.done or not r.patch:
            continue
        piece = _sanitize_island_patch(r.patch, labels, seeds, roles) or {}
        for k in ("labels", "seeds", "entities", "roles", "title"):
            if k in piece and piece[k]:
                if isinstance(piece[k], dict):
                    combined.setdefault(k, {})
                    if isinstance(combined.get(k), dict):
                        combined[k].update(piece[k])
                else:
                    combined[k] = piece[k]
    return combined


def apply_unit_results_to_workspace(
    workspace: Path,
    spec: dict[str, Any],
    results: list[UnitResult],
    *,
    llm_enabled: bool,
) -> FillMergeResult:
    base = dict(spec.get("schema") or {})
    island_results = [r for r in results if r.unit_id.startswith("island.")]
    er_results = [r for r in results if r.unit_id.startswith("er.")]
    mod_results = [r for r in results if r.unit_id.startswith("module.")]
    tc_results = [r for r in results if r.unit_id.startswith("testcase.")]

    out = FillMergeResult(ok=True)
    any_llm_done = any(r.status == UnitStatus.done for r in results)

    if island_results:
        patch = _merge_island_patches(island_results, base)
        if not any(patch.get(k) for k in ("labels", "seeds", "entities", "roles", "title")):
            patch = deterministic_llm_patch(spec, llm_enabled)
            out.mode = "deterministic"
        merged = merge_schema(base, patch)
        for k in ("accept", "missing_capabilities", "out_of_mvp_signals", "capabilities"):
            if k in base:
                merged[k] = base[k]
        ok, errors = validate_schema(merged)
        if not ok:
            patch = deterministic_llm_patch(spec, False)
            merged = merge_schema(base, patch)
            for k in ("accept", "missing_capabilities", "out_of_mvp_signals", "capabilities"):
                if k in base:
                    merged[k] = base[k]
            ok, errors = validate_schema(merged)
            if not ok:
                return FillMergeResult(ok=False, detail="island merge: " + "; ".join(errors[:3]))
            out.mode = "deterministic_recover"
        spec["schema"] = merged
        if patch.get("title"):
            spec["title"] = patch["title"]
        out.written.extend(emit_schema_to_workspace(workspace, spec))

    if er_results:
        acc = sanitize_er_label_patch(load_er_label_patch(workspace))
        for r in er_results:
            if r.status != UnitStatus.done or not r.patch:
                continue
            gaps = (r.context or {}).get("gaps") if isinstance(r.context, dict) else None
            acc = merge_er_label_patch(
                acc,
                sanitize_er_label_patch(r.patch, gaps),
                mode="unit_flow",
            )
        acc["mode"] = "unit_flow"
        save_er_label_patch(workspace, acc)
        out.written.append("islands/er_labels.json")
        out.er_filled = count_er_patch_fills(acc)

    if mod_results:
        acc = sanitize_module_label_patch(load_module_label_patch(workspace))
        nodes = dict(acc.get("nodes") or {})
        for r in mod_results:
            if r.status != UnitStatus.done or not r.patch:
                continue
            target = (r.context or {}).get("target") if isinstance(r.context, dict) else []
            allowed_ids = {str(t.get("id") or "") for t in target if isinstance(t, dict)}
            gap_like = [{"id": i, "label": "", "source": ""} for i in allowed_ids if i]
            piece = sanitize_module_label_patch(r.patch, gap_like).get("nodes") or {}
            nodes.update(piece)
        save_module_label_patch(workspace, {"mode": "unit_flow", "nodes": nodes})
        out.written.append("islands/module_labels.json")
        out.module_filled = len(nodes)

    if tc_results:
        skeleton = build_testcase_skeleton(workspace)
        rows = (skeleton or {}).get("skeleton") or []
        allowed = {str(r.get("id") or "") for r in rows if r.get("id")}
        acc = sanitize_testcase_label_patch(load_testcase_label_patch(workspace), allowed)
        cases = dict(acc.get("cases") or {})
        for r in tc_results:
            if r.status != UnitStatus.done or not r.patch:
                continue
            piece = sanitize_testcase_label_patch(r.patch, allowed).get("cases") or {}
            cases.update(piece)
        save_testcase_label_patch(workspace, {"mode": "unit_flow", "cases": cases})
        out.written.append("islands/testcase_labels.json")
        out.testcase_filled = len(cases)

    if not out.written and not any_llm_done:
        paths = llm_fill_islands(workspace, spec, llm_enabled)
        out.written.extend(paths)
        out.mode = "deterministic_only"
        out.detail = "deterministic_only"
        return out

    parts = [out.mode]
    if out.er_filled:
        parts.append(f"er={out.er_filled}")
    if out.module_filled:
        parts.append(f"mod={out.module_filled}")
    if out.testcase_filled:
        parts.append(f"tc={out.testcase_filled}")
    out.detail = " · ".join(parts)
    return out
