"""后端按 cap 硬拦 ↔ schema 收集旗标必真（工厂通用合同）。

不限申请 / 预约 / 下单 / 核验：凡「能力开了就 Store.assert*、前端须有收集控件」
都登记在此。路径为 schema 点号键（可落 ticket / reservation / order 等）。
域皮浅字段、菜单实体补齐仍由各 feature 的 sync_*_surface_from_caps 自己做。
"""

from __future__ import annotations

from typing import Any

# cap → 必须为真的 schema 路径（点号自 schema 根）
HARD_ASSERT_UI_FROM_CAPS: dict[str, tuple[str, ...]] = {
    "material_check": (
        "entities.ticket.requireMaterialChecklist",
        "entities.ticket.requireAttach",
    ),
    "claim_proof": ("entities.ticket.requireClaimProof",),
}


def _ensure_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
    cur = parent.get(key)
    if not isinstance(cur, dict):
        cur = {}
        parent[key] = cur
    return cur


def _set_true(schema: dict[str, Any], dotted: str) -> None:
    parts = [p for p in dotted.split(".") if p]
    if not parts:
        return
    cur: dict[str, Any] = schema
    for key in parts[:-1]:
        cur = _ensure_dict(cur, key)
    cur[parts[-1]] = True


def _is_true(schema: dict[str, Any], dotted: str) -> bool:
    cur: Any = schema
    for key in dotted.split("."):
        if not key:
            continue
        if not isinstance(cur, dict):
            return False
        cur = cur.get(key)
    return bool(cur)


def sync_hard_assert_ui_from_caps(schema: dict[str, Any]) -> None:
    """能力已开且后端硬拦时，对应收集旗标必须真（防填岛/壳重写漏挂）。"""
    if not isinstance(schema, dict):
        return
    caps = set(schema.get("capabilities") or [])
    if not caps.intersection(HARD_ASSERT_UI_FROM_CAPS):
        return
    for cap, paths in HARD_ASSERT_UI_FROM_CAPS.items():
        if cap not in caps:
            continue
        for path in paths:
            _set_true(schema, path)


def check_hard_assert_ui_aligned(
    schema: dict[str, Any] | None,
    *,
    capabilities: list[str] | None = None,
) -> list[str]:
    """硬拦 cap 已开但收集旗标未真 → 工厂侧问题列表（空=齐）。"""
    if not isinstance(schema, dict):
        schema = {}
    caps = set(
        capabilities if capabilities is not None else (schema.get("capabilities") or [])
    )
    issues: list[str] = []
    for cap, paths in HARD_ASSERT_UI_FROM_CAPS.items():
        if cap not in caps:
            continue
        missing = [p for p in paths if not _is_true(schema, p)]
        if missing:
            issues.append(
                f"能力 {cap} 已开（后端硬拦）但 schema 缺少收集旗标 {missing}；"
                f"用户无控件却会被拒（须收束 sync 或 feature attach）"
            )
    return issues


def assert_hard_assert_ui_aligned(
    schema: dict[str, Any] | None,
    *,
    capabilities: list[str] | None = None,
    domain: str = "",
) -> None:
    """bake / 冒烟硬闸：硬拦无收集旗标直接失败，禁止带病包出炉。"""
    issues = check_hard_assert_ui_aligned(schema, capabilities=capabilities)
    if issues:
        tag = f" [{domain}]" if domain else ""
        raise ValueError(f"硬拦与收集 UI 未对齐{tag}: " + "; ".join(issues))
