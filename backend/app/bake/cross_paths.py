"""交叉主路径白名单（Path B：专科/本科·课设开题全文可答辩才 full）。

路径键由 ARCH 并集归一：F=单据流族 / T=交易 / R=预约。
具名单域单路径不走本表；GENERIC 多路径必须命中白名单且 defense_ready。
硕博课题、真实业务全流程不在接题范围（见 HANDOFF「接题边界」）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.bake.archetype_shells import normalize_archetypes, path_flags


@dataclass(frozen=True)
class CrossPath:
    """一条允许的交叉（或单路径）组合。"""

    key: str
    label: str
    # 运行时 SQL/壳已能拼
    runtime_ok: bool
    # 已有 golden + 演示剧本，可承诺开题全文答辩
    defense_ready: bool
    note: str = ""


def path_key_from_flags(need_flow: bool, need_trade: bool, need_reserve: bool) -> str:
    parts: list[str] = []
    if need_flow:
        parts.append("F")
    if need_trade:
        parts.append("T")
    if need_reserve:
        parts.append("R")
    return "".join(parts) or "C"  # C = CRUD-only


def path_key_from_archetypes(archetypes: Iterable[str] | str | None, primary: str | None = None) -> str:
    arches = normalize_archetypes(list(archetypes) if not isinstance(archetypes, str) else archetypes, primary=primary)
    return path_key_from_flags(*path_flags(arches))


# 白名单：未列出 = 禁止 full（reject）。扩组合先改这里再补 golden/冒烟。
# 白话：借用+下单 / 借用+预约 / 下单+预约 三条都做；三合一仍未就绪。
CROSS_PATHS: dict[str, CrossPath] = {
    "C": CrossPath("C", "纯档案", True, True, "CRUD 单路径"),
    "F": CrossPath("F", "单据流", True, True, "FLOW/STOCK/CONTENT"),
    "T": CrossPath("T", "交易", True, True, "购物车订单"),
    "R": CrossPath("R", "预约占坑", True, True, "时段容量"),
    "FT": CrossPath(
        "FT",
        "借用/申请+下单",
        True,
        True,
        "golden: DOM-GENERIC__ARCH-FLOW_ARCH-TRADE；HANDOFF 组 H · X-BORROW-SHOP",
    ),
    "FR": CrossPath(
        "FR",
        "借用/申请+预约",
        True,
        True,
        "golden: DOM-GENERIC__ARCH-FLOW_ARCH-RESERVE；HANDOFF 组 H · X-BORROW-RESERVE",
    ),
    "TR": CrossPath(
        "TR",
        "下单+预约",
        True,
        True,
        "golden: DOM-GENERIC__ARCH-TRADE_ARCH-RESERVE；HANDOFF 组 H · X-SHOP-RESERVE；宾馆优先 DOM-HOTEL",
    ),
    # 三交叉：开题三条主路径仍不承诺全文答辩
    "FTR": CrossPath(
        "FTR",
        "借用+下单+预约三合一",
        True,
        False,
        "可拼 SQL，但不接智慧校园式全文；请裁成上面三条之一",
    ),
}


def lookup_cross_path(key: str) -> CrossPath | None:
    return CROSS_PATHS.get(key)


def evaluate_cross_path(
    archetypes: Iterable[str] | str | None,
    *,
    primary: str | None = None,
    domain: str | None = None,
) -> tuple[str, CrossPath | None, str | None]:
    """返回 (path_key, entry|None, reject_reason|None)。

    具名单域且单路径键（C/F/T/R）→ 不拦截（由域门禁负责）。
    多路径或 GENERIC 多路径 → 必须白名单且 defense_ready。
    """
    key = path_key_from_archetypes(archetypes, primary=primary)
    entry = lookup_cross_path(key)
    multi = len(key) > 1  # FT/FR/TR/FTR
    named = (domain or "") not in ("", "DOM-GENERIC")

    if not multi:
        # 单路径：具名或 GENERIC 均可
        if entry and entry.defense_ready:
            return key, entry, None
        if entry and not entry.defense_ready:
            return key, entry, f"路径「{entry.label}」尚未 defense_ready：{entry.note}"
        return key, None, f"未知路径键 {key}"

    # 多路径交叉
    if named and multi:
        # 具名域不应残留多 ARCH（reconcile 应已降 GENERIC）；仍拦一道
        return (
            key,
            entry,
            f"具名域不可夹带多主路径（{key}）；请降 GENERIC 或改开题为单路径",
        )
    if entry is None:
        return key, None, f"交叉路径 {key} 不在白名单"
    if not entry.runtime_ok:
        return key, entry, f"交叉「{entry.label}」运行时未齐：{entry.note}"
    if not entry.defense_ready:
        return (
            key,
            entry,
            f"交叉「{entry.label}」尚未达到全文答辩就绪（{entry.note}）。"
            "补齐 golden/演示剧本并将 defense_ready=true 前不可 full",
        )
    return key, entry, None
