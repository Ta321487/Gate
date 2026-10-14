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
        lines.append("A. 申请办理：浏览资源 → 提交申请 → 管理端审核完结")
    if need_trade:
        letter = "B" if need_flow else "A"
        lines.append(f"{letter}. 购物下单：浏览商品 → 加购 → 提交订单 → 履约")
    if need_reserve:
        n = sum([need_flow, need_trade])
        letter = chr(ord("A") + n)
        lines.append(f"{letter}. 时段预约：选资源 → 占坑 → 取消或办结")
    return lines


def portal_cross_lead(
    *,
    need_flow: bool,
    need_trade: bool,
    need_reserve: bool,
    path_label: str = "",
) -> str:
    bits = []
    if need_flow:
        bits.append("申请审核")
    if need_trade:
        bits.append("购物下单")
    if need_reserve:
        bits.append("时段预约")
    joined = "与".join(bits) if bits else "业务办理"
    label = f"「{path_label}」" if path_label else ""
    return (
        f"本系统为交叉壳{label}，含{joined}两条（或以上）主路径；"
        "答辩时按路径分别演示，勿说成单一行业站。"
    )


def readme_cross_guide_section(
    *,
    need_flow: bool,
    need_trade: bool,
    need_reserve: bool,
    path_label: str = "",
    path_note: str = "",
) -> str:
    """学生包 README 固定段；非交叉时返回空串。"""
    if sum([need_flow, need_trade, need_reserve]) < 2:
        return ""
    title = path_label or "双主路径交叉壳"
    lines = path_demo_lines(need_flow, need_trade, need_reserve)
    body = "\n".join(f"- {ln}" for ln in lines)
    note = f"\n\n白名单说明：{path_note}" if path_note else ""
    return f"""## 交叉主路径答辩导引

本包落在通用壳（`DOM-GENERIC`）+ 行为并集，对应交叉组合：**{title}**。
系统里同时有两套路玩法，答辩时请**分路径演示**，不要说成某单一行业站。

{body}

### 答辩话术要点

1. 先说明「开题写了两套玩法，工厂用通用壳保留路径并集，而不是硬塞进某一个具名行业域」。
2. 演示顺序建议：先走完一条主路径的用户端→管理端闭环，再走另一条。
3. 通用壳上的行业词（题名里的业务称呼）只是浅文案替换，**不等于**已换成具名 `DOM-*` 行业皮。
4. 匹配页上的领域标签以扫描结果为准；不要在出包后静默改成看起来「更行业」的 Dom 标签冒充具名域。
{note}
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
    labels.setdefault("crossPathGuideTitle", "交叉主路径说明")
    labels.setdefault(
        "crossPathGuideBody",
        "；".join(path_demo_lines(need_flow, need_trade, need_reserve)),
    )
    labels.setdefault(
        "industrySkinHint",
        "题名中的业务称呼仅作通用壳浅文案；未改 Dom 标签，勿当作具名行业域。",
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
