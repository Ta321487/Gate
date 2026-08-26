"""单元输出校验（micro-loop 的 check 节点）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.bake.domain_schema import merge_schema, validate_schema
from app.bake.schema.er import sanitize_er_label_patch
from app.bake.schema.modules import sanitize_module_label_patch
from app.bake.schema.testcases import sanitize_testcase_label_patch
from app.llm.unit_flow.models import TaskUnit, UnitKind


@dataclass
class ValidationIssue:
    level: str  # error | warn
    message: str


@dataclass
class ValidationResult:
    issues: list[ValidationIssue]

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_unit_patch(
    unit: TaskUnit,
    patch: dict[str, Any] | None,
    *,
    base_schema: dict[str, Any] | None = None,
) -> ValidationResult:
    if not patch:
        return ValidationResult([ValidationIssue("error", "空 patch")])

    issues: list[ValidationIssue] = []

    if unit.kind in (
        UnitKind.island_labels,
        UnitKind.island_seeds,
        UnitKind.island_entities,
        UnitKind.island_roles,
    ):
        forbidden = {"menus", "capabilities", "routes", "entities_keys"}
        for k in patch:
            if k in forbidden:
                issues.append(ValidationIssue("error", f"禁止字段 {k}"))
        if base_schema and any(k in patch for k in ("labels", "seeds", "entities", "roles", "title")):
            try:
                from app.llm.agents_island import _sanitize_island_patch

                labels = dict(base_schema.get("labels") or {})
                seeds = dict(base_schema.get("seeds") or {})
                roles = dict(base_schema.get("roles") or {})
                sanitized = _sanitize_island_patch(patch, labels, seeds, roles)
                if not sanitized:
                    issues.append(ValidationIssue("error", "sanitize 后为空"))
                else:
                    merged = merge_schema(base_schema, sanitized)
                    ok, errs = validate_schema(merged)
                    if not ok:
                        issues.extend(ValidationIssue("error", e) for e in errs[:3])
            except Exception as e:  # noqa: BLE001
                issues.append(ValidationIssue("error", f"schema 合并失败: {e}"))

    elif unit.kind == UnitKind.er_labels:
        gaps = (unit.payload.get("gaps") or {}) if isinstance(unit.payload, dict) else {}
        sanitized = sanitize_er_label_patch(patch, gaps)
        if not sanitized.get("tables") and not sanitized.get("columns") and not sanitized.get("relations"):
            if patch.get("tables") or patch.get("columns") or patch.get("relations"):
                issues.append(ValidationIssue("warn", "ER patch 经 sanitize 后为空"))

    elif unit.kind == UnitKind.module_labels:
        target = unit.payload.get("target") or []
        allowed = {str(t.get("id") or "") for t in target if isinstance(t, dict)}
        gap_like = [{"id": i, "label": "", "source": ""} for i in allowed if i]
        sanitized = sanitize_module_label_patch(patch, gap_like)
        nodes = sanitized.get("nodes") or {}
        extra = set(nodes) - allowed
        if extra:
            issues.append(ValidationIssue("error", f"多余节点 id: {sorted(extra)[:5]}"))

    elif unit.kind == UnitKind.testcase_labels:
        target = unit.payload.get("target") or []
        allowed = {str(r.get("id") or "") for r in target if isinstance(r, dict)}
        sanitized = sanitize_testcase_label_patch(patch, allowed)
        cases = sanitized.get("cases") or {}
        extra = set(cases) - allowed
        if extra:
            issues.append(ValidationIssue("error", f"多余用例 id: {sorted(extra)[:5]}"))

    return ValidationResult(issues)
