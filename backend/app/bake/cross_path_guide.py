"""GENERIC / Path B 交叉导引（文档与壳文案，不是 *_thicken）。

供 README 注入、门户 lead、菜单分区标签、工厂匹配页口径共用。
"""

from __future__ import annotations

from typing import Any, Iterable

from app.bake.archetype_shells import normalize_archetypes, path_flags
from app.bake.cross_paths import evaluate_cross_path, path_key_from_flags

# 菜单 key → 分区（仅真交叉多路径时写入 navSection）
_FLOW_KEYS = frozenset({"my_tickets", "ticket_pending", "ticket_records"})
_TRADE_KEYS = frozenset(
    {"cart", "my_orders", "addresses", "guestbook", "orders", "favorites"}
)
_RESERVE_KEYS = frozenset({"my_reservations", "reservations", "slots"})

_SECTION_TITLE = {
    "flow": "申请办理",
    "trade": "购物下单",
    "reserve": "时段预约",
}


def is_multi_path(archetypes: Iterable[str] | str | None, primary: str | None = None) -> bool:
    arches = normalize_archetypes(
        list(archetypes) if not isinstance(archetypes, str) else archetypes,
        primary=primary,
    )
    return sum(path_flags(arches)) >= 2


def path_demo_lines(need_flow: bool, need_trade: bool, need_reserve: bool) -> list[str]:
    lines: list[str] = []
    if need_flow:
        lines.append("申请办理：选择事项并提交申请，审核通过后办结。")
    if need_trade:
        lines.append("购物下单：选择商品加入购物车，提交订单后办理。")
    if need_reserve:
        lines.append("时段预约：选择可预约时段，可取消或办结。")
    return lines


def _join_businesses(bits: list[str]) -> str:
    if not bits:
        return "业务办理"
    if len(bits) == 1:
        return bits[0]
    if len(bits) == 2:
        return f"{bits[0]}和{bits[1]}"
    return "、".join(bits[:-1]) + "和" + bits[-1]


def portal_cross_lead(
    *,
    need_flow: bool,
    need_trade: bool,
    need_reserve: bool,
    path_label: str = "",
) -> str:
    del path_label
    bits = []
    if need_flow:
        bits.append("申请审核")
    if need_trade:
        bits.append("购物下单")
    if need_reserve:
        bits.append("时段预约")
    return f"本系统提供{_join_businesses(bits)}。请从对应菜单进入。"


def readme_cross_guide_section(
    *,
    need_flow: bool,
    need_trade: bool,
    need_reserve: bool,
    path_label: str = "",
    path_note: str = "",
) -> str:
    """学生包 README 固定段；非交叉时返回空串。

    path_label / path_note 只给工厂内部对照，不写入学生包。
    """
    del path_label, path_note
    if sum([need_flow, need_trade, need_reserve]) < 2:
        return ""
    lines = path_demo_lines(need_flow, need_trade, need_reserve)
    body = "\n".join(f"- {ln}" for ln in lines)
    return f"""## 业务说明

本系统同时提供以下业务，请从对应菜单进入。各项业务分别办理。

{body}
"""


def factory_generic_match_tip() -> str:
    """工厂匹配页：禁止静默改 Dom + ARCH/DOM 优先级短提示。"""
    return (
        "通用壳（DOM-GENERIC）：能落到具名 DOM 时优先具名；盖不住多主路径时才降通用并保留 ARCH 并集。"
        "禁止为「看起来更行业」而静默改 Dom 标签冒充具名域；行业词浅替换只改可见文案，不改 domain。"
    )


def apply_cross_guide_to_schema(
    schema: dict[str, Any],
    *,
    archetypes: list[str] | str | None = None,
    primary: str | None = None,
) -> None:
    """写入门户 lead + 菜单 navSection（仅 GENERIC 真交叉多路径）。"""
    arches = normalize_archetypes(
        list(archetypes) if not isinstance(archetypes, str) else archetypes,
        primary=primary,
    )
    need_flow, need_trade, need_reserve = path_flags(arches)
    if sum([need_flow, need_trade, need_reserve]) < 2:
        return
    key, entry, _ = evaluate_cross_path(arches, primary=primary, domain="DOM-GENERIC")
    labels = schema.setdefault("labels", {})
    if not str(labels.get("portalHomeLead") or "").strip():
        labels["portalHomeLead"] = portal_cross_lead(
            need_flow=need_flow,
            need_trade=need_trade,
            need_reserve=need_reserve,
            path_label=(entry.label if entry else key),
        )
    labels.setdefault("crossPathGuideTitle", "业务说明")
    labels.setdefault(
        "crossPathGuideBody",
        "".join(path_demo_lines(need_flow, need_trade, need_reserve)),
    )
    labels.setdefault(
        "industrySkinHint",
        "不同业务从对应菜单进入，记录分别保存。",
    )
    _tag_menu_nav_sections(
        schema,
        need_flow=need_flow,
        need_trade=need_trade,
        need_reserve=need_reserve,
    )


def _section_for_key(key: str, *, need_flow: bool, need_trade: bool, need_reserve: bool) -> str | None:
    if need_flow and key in _FLOW_KEYS:
        return _SECTION_TITLE["flow"]
    if need_trade and key in _TRADE_KEYS:
        return _SECTION_TITLE["trade"]
    if need_reserve and key in _RESERVE_KEYS:
        return _SECTION_TITLE["reserve"]
    return None


def _tag_menu_nav_sections(
    schema: dict[str, Any],
    *,
    need_flow: bool,
    need_trade: bool,
    need_reserve: bool,
) -> None:
    menus = schema.get("menus")
    if not isinstance(menus, dict):
        return
    for side in ("user", "admin"):
        items = menus.get(side)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "")
            sec = _section_for_key(
                key, need_flow=need_flow, need_trade=need_trade, need_reserve=need_reserve
            )
            if sec:
                item["navSection"] = sec


def readme_bits_from_spec(spec: dict[str, Any] | None) -> str:
    """供 _patch_student_readme 替换 ${CROSS_PATH_GUIDE}。"""
    if not isinstance(spec, dict):
        return ""
    if (spec.get("domain") or "") != "DOM-GENERIC":
        return ""
    arches = normalize_archetypes(spec.get("archetypes"), primary=spec.get("archetype"))
    need_flow, need_trade, need_reserve = path_flags(arches)
    if sum([need_flow, need_trade, need_reserve]) < 2:
        return ""
    _key, entry, _ = evaluate_cross_path(
        arches, primary=spec.get("archetype"), domain="DOM-GENERIC"
    )
    return readme_cross_guide_section(
        need_flow=need_flow,
        need_trade=need_trade,
        need_reserve=need_reserve,
        path_label=(entry.label if entry else path_key_from_flags(need_flow, need_trade, need_reserve)),
        path_note=(entry.note if entry else ""),
    )
