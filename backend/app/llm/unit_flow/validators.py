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

    elif unit.kind == UnitKind.ppt_page:
        issues.extend(_validate_ppt_page_patch(unit, patch))

    return ValidationResult(issues)


_FORBIDDEN_STACK = (
    "redis",
    "kafka",
    "rabbitmq",
    "mongodb",
    "elasticsearch",
    "docker",
    "kubernetes",
    "django",
    "flask",
    ".net",
    "android",
)


def _validate_ppt_page_patch(unit: TaskUnit, patch: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    page_id = str(unit.payload.get("page_id") or "")
    if str(patch.get("page_id") or "") != page_id:
        issues.append(ValidationIssue("error", f"page_id 必须为 {page_id}"))

    bullet_ids = [str(x) for x in (unit.payload.get("bullet_ids") or [])]
    bullets = patch.get("bullets")
    if bullet_ids:
        if not isinstance(bullets, list):
            issues.append(ValidationIssue("error", "缺少 bullets"))
        else:
            got = [str(b.get("id") or "") for b in bullets if isinstance(b, dict)]
            if set(got) != set(bullet_ids) or len(got) != len(bullet_ids):
                issues.append(ValidationIssue("error", "bullets id 必须与 bullet_ids 对齐"))
            for b in bullets:
                if not isinstance(b, dict):
                    continue
                text = str(b.get("text") or "").strip()
                if not text:
                    issues.append(ValidationIssue("error", f"空要点 {b.get('id')}"))
                elif len(text) > 96:
                    issues.append(ValidationIssue("error", f"要点过长 {b.get('id')}"))
                refs = b.get("source_refs") or []
                allowed_refs = {str(x) for x in (unit.payload.get("allowed_refs") or [])}
                if allowed_refs and isinstance(refs, list):
                    bad = [str(r) for r in refs if str(r) not in allowed_refs]
                    if bad:
                        issues.append(ValidationIssue("error", f"非法 source_refs: {bad[:3]}"))

    allow = unit.payload.get("allowlist") if isinstance(unit.payload.get("allowlist"), dict) else {}
    tech_allow = {str(x).lower() for x in (allow.get("tech") or [])}
    blob_parts: list[str] = []
    for b in bullets or []:
        if isinstance(b, dict):
            blob_parts.append(str(b.get("text") or ""))
    table = patch.get("table")
    if isinstance(table, dict):
        for row in table.get("rows") or []:
            if isinstance(row, (list, tuple)):
                blob_parts.extend(str(x) for x in row)
            else:
                blob_parts.append(str(row))
        shape = unit.payload.get("table_shape") if isinstance(unit.payload.get("table_shape"), dict) else {}
        want_cols = int(shape.get("cols") or 0)
        want_rows = int(shape.get("rows") or 0)
        rows = table.get("rows") or []
        if want_rows and len(rows) != want_rows:
            issues.append(ValidationIssue("error", f"table 行数须为 {want_rows}"))
        if want_cols and rows:
            for row in rows:
                if isinstance(row, (list, tuple)) and len(row) != want_cols:
                    issues.append(ValidationIssue("error", f"table 列数须为 {want_cols}"))
                    break
    blob = "\n".join(blob_parts).lower()
    for word in _FORBIDDEN_STACK:
        if word in blob and word not in tech_allow:
            issues.append(ValidationIssue("error", f"技术名不在实包 allowlist: {word}"))
            break

    return issues
