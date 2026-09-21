"""论文「类图」：零交叉摆框、选边与正交折线。"""

from __future__ import annotations

import math
import time
from typing import Any

from app.bake.schema.class_model import (
    _EDGE_MARGIN,
    _KIND_DRAW_PRIORITY,
    _PAD,
    _box_size,
    _f,
    _normalize_rel_kind,
)

# 打开类图接口有 axios 60s 上限；稠密依赖边时旧选边/挪框会拖死。
# 预算内尽量画满，超时则少画进 omitted（仍保证已画边零交叉）。
_ATTACH_BUDGET_SEC = 5.0
_SELECT_BUDGET_SEC = 2.0
_NUDGE_BUDGET_SEC = 2.0
_RECOVER_LANE_SOFT = 8
_RECOVER_LANE_HARD = 12

def _pad_positions(
    pos: dict[str, tuple[float, float, float, float]],
) -> dict[str, tuple[float, float, float, float]]:
    if not pos:
        return pos
    min_x = min(x for x, y, w, h in pos.values())
    min_y = min(y for x, y, w, h in pos.values())
    shift_x = _PAD - min_x if min_x < _PAD else 0.0
    shift_y = _PAD - min_y if min_y < _PAD else 0.0
    if not shift_x and not shift_y:
        return pos
    return {
        k: (x + shift_x, y + shift_y, w, h) for k, (x, y, w, h) in pos.items()
    }


def _trial_zero_crossing(
    all_a: list[dict[str, Any]],
    pos: dict[str, tuple[float, float, float, float]],
    parents: dict[str, str],
    *,
    deadline: float | None = None,
) -> tuple[int, float, dict[str, Any]]:
    """在给定摆框下跑零交叉选边，返回 (已画条数, 总路径长, 局部 model 字段)。"""
    trial: dict[str, Any] = {
        "associations_all": all_a,
        "associations": list(all_a),
        "associations_omitted": [],
        "tree_parents": dict(parents),
        "zero_crossing": True,
        "evidence": {},
    }
    pos_p = _pad_positions(pos)
    if pos_p:
        _select_crossing_free_assocs(trial, pos_p, deadline=deadline)
    drawn = trial.get("associations") or []
    paths = trial.get("_assoc_paths") or []
    n = len(drawn)
    plen = sum(_path_len(p) for p in paths if isinstance(p, list) and len(p) >= 2)
    trial["_pos"] = pos_p
    return n, plen, trial


def _nudge_layout_for_zero_cross(
    pos: dict[str, tuple[float, float, float, float]],
    all_a: list[dict[str, Any]],
    parents: dict[str, str] | None = None,
    *,
    pinned: set[str] | None = None,
    max_rounds: int = 8,
    deadline: float | None = None,
) -> tuple[dict[str, tuple[float, float, float, float]], dict[str, Any]]:
    """为零交叉主动挪框：在固定拓扑下微调/拉开类框，尽量画满全部关联。

    人类零交叉靠的是挪框开槽，不是硬画交叉线。此处对「当前画不上的边」做
    端点推开、垂直让槽、整体膨胀；每步后 _separate_boxes 防叠。
    候选故意收紧：每轮全量试路径很贵，优先短位移 + 早停 + 墙钟预算。
    """
    parents = {str(k): str(v) for k, v in (parents or {}).items()}
    pinned = {str(x) for x in (pinned or set())}
    n_total = len(all_a)
    nudge_deadline = deadline
    if nudge_deadline is None:
        nudge_deadline = time.monotonic() + _NUDGE_BUDGET_SEC
    if not pos or n_total == 0:
        n, plen, trial = _trial_zero_crossing(
            all_a, pos, parents, deadline=nudge_deadline
        )
        return trial.get("_pos") or pos, trial

    cur = dict(pos)
    best_n, best_plen, best_trial = _trial_zero_crossing(
        all_a, cur, parents, deadline=nudge_deadline
    )
    best_pos = best_trial.get("_pos") or _pad_positions(cur)
    if best_n >= n_total:
        return best_pos, best_trial

    dirs = (
        (1.0, 0.0),
        (-1.0, 0.0),
        (0.0, 1.0),
        (0.0, -1.0),
        (0.7, 0.7),
        (-0.7, -0.7),
    )
    steps = (_BOX_GAP * 0.7, _BOX_GAP * 1.4)

    def _movable(tid: str) -> bool:
        return tid in cur and tid not in pinned

    def _apply_delta(
        base: dict[str, tuple[float, float, float, float]],
        deltas: dict[str, tuple[float, float]],
    ) -> dict[str, tuple[float, float, float, float]]:
        out: dict[str, list[float]] = {
            k: [float(x), float(y), float(w), float(h)] for k, (x, y, w, h) in base.items()
        }
        for tid, (dx, dy) in deltas.items():
            if tid not in out or not _movable(tid):
                continue
            out[tid][0] += dx
            out[tid][1] += dy
        separated = _separate_boxes(
            {k: (v[0], v[1], v[2], v[3]) for k, v in out.items()},
            gap=_BOX_GAP * 0.85,
        )
        return _pad_positions(separated)

    def _score(
        trial_pos: dict[str, tuple[float, float, float, float]],
    ) -> tuple[int, float, dict[str, Any]]:
        return _trial_zero_crossing(
            all_a, trial_pos, parents, deadline=nudge_deadline
        )

    for _round in range(max_rounds):
        if best_n >= n_total or time.monotonic() >= nudge_deadline:
            break
        omitted = [
            a
            for a in (best_trial.get("associations_omitted") or [])
            if isinstance(a, dict)
        ]
        if not omitted:
            break

        candidates: list[dict[str, tuple[float, float]]] = []

        # 1) 整体相对质心轻微膨胀（开槽）
        if len(best_pos) >= 2:
            cx = sum(x + w / 2 for x, y, w, h in best_pos.values()) / len(best_pos)
            cy = sum(y + h / 2 for x, y, w, h in best_pos.values()) / len(best_pos)
            for factor in (1.15, 1.3):
                deltas: dict[str, tuple[float, float]] = {}
                for tid, (x, y, w, h) in best_pos.items():
                    if not _movable(tid):
                        continue
                    mx, my = x + w / 2, y + h / 2
                    deltas[tid] = ((mx - cx) * (factor - 1.0), (my - cy) * (factor - 1.0))
                if deltas:
                    candidates.append(deltas)

        # 2) 针对漏边：端点互推 / 定向挪 / 垂直让槽（漏边与位移候选都收紧）
        for a in omitted[:2]:
            u, v = str(a.get("from")), str(a.get("to"))
            if u not in best_pos or v not in best_pos:
                continue
            ux, uy, uw, uh = best_pos[u]
            vx, vy, vw, vh = best_pos[v]
            ucx, ucy = ux + uw / 2, uy + uh / 2
            vcx, vcy = vx + vw / 2, vy + vh / 2
            dx, dy = vcx - ucx, vcy - ucy
            dist = math.hypot(dx, dy) or 1.0
            ux_n, uy_n = dx / dist, dy / dist
            px_n, py_n = -uy_n, ux_n
            for step in steps:
                if _movable(u) and _movable(v):
                    candidates.append(
                        {
                            u: (-ux_n * step * 0.5, -uy_n * step * 0.5),
                            v: (ux_n * step * 0.5, uy_n * step * 0.5),
                        }
                    )
                    candidates.append(
                        {
                            u: (px_n * step * 0.5, py_n * step * 0.5),
                            v: (-px_n * step * 0.5, -py_n * step * 0.5),
                        }
                    )
                for tid in (u, v):
                    if not _movable(tid):
                        continue
                    for ddx, ddy in dirs[:4]:
                        candidates.append({tid: (ddx * step, ddy * step)})

            lo_x, hi_x = sorted((ucx, vcx))
            lo_y, hi_y = sorted((ucy, vcy))
            for tid, (x, y, w, h) in best_pos.items():
                if tid in (u, v) or not _movable(tid):
                    continue
                mx, my = x + w / 2, y + h / 2
                on_seg = (lo_x - w <= mx <= hi_x + w) and (lo_y - h <= my <= hi_y + h)
                if not on_seg:
                    continue
                for step in steps:
                    candidates.append({tid: (px_n * step, py_n * step)})
                    candidates.append({tid: (-px_n * step, -py_n * step)})

        improved = False
        # 每候选都要跑一遍选边，上限压紧以免拖死接口
        for deltas in candidates[:16]:
            if time.monotonic() >= nudge_deadline:
                break
            trial_pos = _apply_delta(best_pos, deltas)
            n, plen, trial = _score(trial_pos)
            key = (n, -plen)
            best_key = (best_n, -best_plen)
            if key > best_key:
                best_n, best_plen, best_trial = n, plen, trial
                best_pos = trial.get("_pos") or trial_pos
                improved = True
                if best_n >= n_total:
                    break
        if not improved:
            break

    return best_pos, best_trial


def _commit_zero_cross_layout(
    model: dict[str, Any],
    *,
    pos: dict[str, tuple[float, float, float, float]],
    trial: dict[str, Any],
    parents: dict[str, str],
    layout_algo: str,
) -> None:
    model["associations"] = trial.get("associations") or []
    model["associations_omitted"] = trial.get("associations_omitted") or []
    model["_assoc_paths"] = trial.get("_assoc_paths") or []
    model["tree_parents"] = dict(parents)
    model["layout_algo"] = layout_algo
    use_pos = trial.get("_pos") or pos
    model["layout"] = {
        k: {"x": round(x, 1), "y": round(y, 1), "w": round(w, 1), "h": round(h, 1)}
        for k, (x, y, w, h) in use_pos.items()
    }
    ev = model.setdefault("evidence", {})
    if isinstance(ev, dict):
        ev["assoc_drawn"] = len(model["associations"])
        ev["assoc_omitted"] = len(model["associations_omitted"])
        ev["layout_algo"] = layout_algo
        ev["zero_crossing"] = True


def attach_layout(model: dict[str, Any], *, assoc_mode: str | None = None) -> dict[str, Any]:
    """零交叉硬约束：多套摆框竞赛 + 挪框精炼，选「无交叉下画出最多关联」的方案。

    assoc_mode 参数保留兼容，一律按零交叉处理（全关联凑线已取消）。
    """
    del assoc_mode  # 兼容旧调用；产品口径只有零交叉
    deadline = time.monotonic() + _ATTACH_BUDGET_SEC
    all_a = [a for a in (model.get("associations") or []) if isinstance(a, dict)]
    model["associations_all"] = all_a
    model["associations"] = list(all_a)
    model["associations_omitted"] = []
    model["tree_parents"] = {}
    model["zero_crossing"] = True
    model["assoc_mode"] = "zero"
    ev = model.setdefault("evidence", {})
    if isinstance(ev, dict):
        ev["assoc_mode"] = "zero"
        ev["assoc_total"] = len(all_a)
        ev["zero_crossing"] = True

    classes = [c for c in (model.get("classes") or []) if isinstance(c, dict)]
    if not classes:
        model["layout"] = {}
        _refresh_assoc_note(model)
        return model

    sizes = {str(c["id"]): _box_size(c) for c in classes}
    names = [str(c["id"]) for c in classes]
    edges = [
        (str(a.get("from")), str(a.get("to")))
        for a in all_a
        if isinstance(a, dict)
    ]

    layout_cands: list[tuple[str, dict[str, tuple[float, float, float, float]], dict[str, str]]] = []
    if len(names) == 1:
        w, h = sizes[names[0]]
        layout_cands.append(("single", {names[0]: (_PAD, _PAD, w, h)}, {}))
    else:
        # 只比 2 套：枢纽（观感）+ 树（树边易零交叉）；避免多根重复全量选边卡死
        layout_cands.append(("hub", _hub_column_layout(names, sizes, edges), {}))
        pos_t, par_t = _tree_forest_layout(names, sizes, edges)
        layout_cands.append(("tree", pos_t, par_t))

    best_key: tuple[int, float] | None = None
    best_trial: dict[str, Any] | None = None
    best_name = "hub"
    best_pos: dict[str, tuple[float, float, float, float]] = {}
    best_parents: dict[str, str] = {}
    n_total = len(all_a)

    for name, pos, parents in layout_cands:
        if not pos:
            continue
        if time.monotonic() >= deadline:
            break
        trial_deadline = min(deadline, time.monotonic() + _SELECT_BUDGET_SEC)
        n_draw, plen, trial = _trial_zero_crossing(
            all_a, pos, parents, deadline=trial_deadline
        )
        key = (n_draw, -plen)
        if best_key is None or key > best_key:
            best_key = key
            best_trial = trial
            best_name = name
            best_pos = trial.get("_pos") or _pad_positions(pos)
            best_parents = dict(parents)
        # 已能画满全部外键则不必再赛
        if n_total and n_draw >= n_total:
            break

    if best_trial is None:
        model["layout"] = {}
        model["associations"] = []
        model["_assoc_paths"] = []
        _refresh_assoc_note(model)
        return model

    # 竞赛后再挪框开槽，尽量把漏边补回来（仍保证零交叉）
    # 缺边很少或已画大半时挪框性价比低；挪框再单独给短预算，避免顶满 12s
    remain = deadline - time.monotonic()
    drawn_n = len(best_trial.get("associations") or [])
    missing = n_total - drawn_n
    if n_total and missing >= 3 and remain > 1.0:
        nudge_deadline = min(deadline, time.monotonic() + min(2.5, remain))
        nudged_pos, nudged_trial = _nudge_layout_for_zero_cross(
            best_pos,
            all_a,
            best_parents,
            deadline=nudge_deadline,
            max_rounds=4,
        )
        n2 = len(nudged_trial.get("associations") or [])
        plen2 = sum(
            _path_len(p)
            for p in (nudged_trial.get("_assoc_paths") or [])
            if isinstance(p, list) and len(p) >= 2
        )
        n1 = len(best_trial.get("associations") or [])
        plen1 = sum(
            _path_len(p)
            for p in (best_trial.get("_assoc_paths") or [])
            if isinstance(p, list) and len(p) >= 2
        )
        if (n2, -plen2) > (n1, -plen1):
            best_pos, best_trial = nudged_pos, nudged_trial
            best_name = f"{best_name}+nudge"

    _commit_zero_cross_layout(
        model,
        pos=best_pos,
        trial=best_trial,
        parents=best_parents,
        layout_algo=best_name.split(":", 1)[0].split("+", 1)[0],
    )
    if "+nudge" in best_name and isinstance(ev, dict):
        ev["layout_nudged"] = True
    if isinstance(ev, dict) and time.monotonic() >= deadline - 0.05:
        ev["layout_budget_hit"] = True
    _refresh_assoc_note(model)
    return model


def _apply_manual_zero_cross(model: dict[str, Any], *, max_rounds: int = 0) -> None:
    """人工坐标：框位不动（对齐 draw.io），只在当前摆放下选零交叉折线。

    max_rounds 保留兼容；人工拖拽路径不再挪其它框。
    """
    del max_rounds
    layout = model.get("layout") or {}
    pos = {
        str(k): (
            float(v["x"]),
            float(v["y"]),
            float(v["w"]),
            float(v["h"]),
        )
        for k, v in layout.items()
        if isinstance(v, dict) and all(x in v for x in ("x", "y", "w", "h"))
    }
    if not pos:
        return
    all_a = [
        a
        for a in (model.get("associations_all") or model.get("associations") or [])
        if isinstance(a, dict)
    ]
    if not all_a:
        model["associations_all"] = []
        model["associations"] = []
        model["associations_omitted"] = []
        model["_assoc_paths"] = []
        return
    model["associations_all"] = all_a
    model["zero_crossing"] = True
    model["assoc_mode"] = "zero"
    model["tree_parents"] = {
        str(k): str(v) for k, v in (model.get("tree_parents") or {}).items()
    }
    _select_crossing_free_assocs(
        model,
        _pad_positions(pos),
        deadline=time.monotonic() + _SELECT_BUDGET_SEC,
    )
    # 选边可能 pad 平移了障碍坐标；把 layout 与路径对齐
    # _select 不改 pos；pad 仅在 trial 内。这里用原 pos 写回。
    use_pos = _pad_positions(pos)
    model["layout"] = {
        tid: {
            "x": round(x, 1),
            "y": round(y, 1),
            "w": round(w, 1),
            "h": round(h, 1),
        }
        for tid, (x, y, w, h) in use_pos.items()
    }
    model["layout_manual"] = True
    ev = model.setdefault("evidence", {})
    if isinstance(ev, dict):
        ev["assoc_drawn"] = len(model.get("associations") or [])
        ev["assoc_omitted"] = len(model.get("associations_omitted") or [])
        ev["assoc_total"] = len(all_a)
        ev["zero_crossing"] = True
        ev["layout_algo"] = "manual"
        ev.pop("layout_nudged", None)
    _refresh_assoc_note(model)


def _sized_layout_stub(model: dict[str, Any]) -> None:
    """只算框尺寸占位，不做竞赛排版（人工坐标会覆盖 x/y）。"""
    classes = [c for c in (model.get("classes") or []) if isinstance(c, dict)]
    all_a = [a for a in (model.get("associations") or []) if isinstance(a, dict)]
    model["associations_all"] = all_a
    model["associations"] = list(all_a)
    model["associations_omitted"] = []
    model["tree_parents"] = {}
    model["zero_crossing"] = True
    model["assoc_mode"] = "zero"
    layout: dict[str, dict[str, float]] = {}
    x = _PAD
    for c in classes:
        tid = str(c.get("id") or "")
        if not tid:
            continue
        w, h = _box_size(c)
        layout[tid] = {"x": x, "y": _PAD, "w": float(w), "h": float(h)}
        x += float(w) + 40.0
    model["layout"] = layout
    ev = model.setdefault("evidence", {})
    if isinstance(ev, dict):
        ev["assoc_mode"] = "zero"
        ev["assoc_total"] = len(all_a)
        ev["zero_crossing"] = True
        ev["layout_algo"] = "manual"



def _repack_layout_preserving_order(
    pos: dict[str, tuple[float, float, float, float]],
) -> dict[str, tuple[float, float, float, float]]:
    """按原相对列/行关系重排，间距跟当前框尺寸走（切 sample/full 不留大空）。"""
    if len(pos) <= 1:
        return pos
    items = [(tid, x, y, w, h) for tid, (x, y, w, h) in pos.items()]
    items.sort(key=lambda t: (t[1] + t[3] / 2.0, t[2], t[0]))
    cols: list[list[tuple[str, float, float, float, float]]] = []
    col_cx: list[float] = []
    # 列宽聚类：中心距超过阈值视为新列（保留手动左右顺序）
    thresh = max(96.0, _COL_GUTTER * 0.5)
    for tid, x, y, w, h in items:
        cx = x + w / 2.0
        if not cols or abs(cx - col_cx[-1]) > thresh:
            cols.append([(tid, x, y, w, h)])
            col_cx.append(cx)
        else:
            cols[-1].append((tid, x, y, w, h))
            n = len(cols[-1])
            col_cx[-1] = (col_cx[-1] * (n - 1) + cx) / n

    for col in cols:
        col.sort(key=lambda t: (t[2], t[0]))

    out: dict[str, tuple[float, float, float, float]] = {}
    x_cursor = _PAD
    for col in cols:
        col_w = max(t[3] for t in col)
        y_cursor = _PAD
        for tid, _x, _y, w, h in col:
            out[tid] = (x_cursor + (col_w - w) / 2.0, y_cursor, w, h)
            y_cursor += h + _BOX_GAP
        x_cursor += col_w + _COL_GUTTER
    return out

def _circular_crossings(order: list[str], edges: list[tuple[str, str]]) -> int:
    idx = {n: i for i, n in enumerate(order)}
    pairs: list[tuple[int, int]] = []
    for a, b in edges:
        if a not in idx or b not in idx or a == b:
            continue
        i, j = idx[a], idx[b]
        if i > j:
            i, j = j, i
        pairs.append((i, j))
    cross = 0
    for i, (a, b) in enumerate(pairs):
        for c, d in pairs[i + 1 :]:
            if len({a, b, c, d}) < 4:
                continue
            if a < c < b < d or c < a < d < b:
                cross += 1
    return cross


def _best_ring_order(names: list[str], edges: list[tuple[str, str]]) -> list[str]:
    if len(names) <= 1:
        return list(names)
    deg: dict[str, int] = {n: 0 for n in names}
    for a, b in edges:
        if a in deg and b in deg:
            deg[a] += 1
            deg[b] += 1
    seed = sorted(names, key=lambda x: (-deg[x], x))
    best = list(seed)
    best_c = _circular_crossings(best, edges)
    improved = True
    guard = 0
    while improved and guard < 200:
        improved = False
        guard += 1
        for i in range(len(best)):
            j = (i + 1) % len(best)
            trial = list(best)
            trial[i], trial[j] = trial[j], trial[i]
            c = _circular_crossings(trial, edges)
            if c < best_c:
                best, best_c = trial, c
                improved = True
                break
    return best


_BOX_GAP = 72.0  # 框间距（示例图槽道较宽）
_COL_GUTTER = 160.0  # 列间走线槽（加宽，减少跨列折线打架）
_CHANNEL = 56.0  # 外绕槽宽
_LANE_GAP = 12.0  # 并行关联线车道间距


def _lane_t(lane: int, n_lanes: int) -> float:
    """边上锚点比例 ∈ (0.2, 0.8)，多条线错开出框。"""
    if n_lanes <= 1:
        return 0.5
    return 0.2 + 0.6 * lane / (n_lanes - 1)


def _lane_offset(lane: int, n_lanes: int) -> float:
    """相对中心的车道偏移（可正可负）。"""
    if n_lanes <= 1:
        return 0.0
    return (lane - (n_lanes - 1) / 2.0) * _LANE_GAP


def _clamp_mid(lo: float, hi: float, mid: float, margin: float = 6.0) -> float:
    a, b = (lo, hi) if lo <= hi else (hi, lo)
    if b - a < margin * 2 + 1:
        return (a + b) / 2
    return max(a + margin, min(b - margin, mid))


def _rects_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    gap: float = _BOX_GAP,
) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (
        ax + aw + gap <= bx
        or bx + bw + gap <= ax
        or ay + ah + gap <= by
        or by + bh + gap <= ay
    )


def _separate_boxes(
    pos: dict[str, tuple[float, float, float, float]],
    *,
    gap: float = _BOX_GAP,
    rounds: int = 100,
) -> dict[str, tuple[float, float, float, float]]:
    """推开重叠框，直到间距 ≥ gap。"""
    ids = list(pos.keys())
    cur = {k: list(v) for k, v in pos.items()}
    for _ in range(rounds):
        moved = False
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                ax, ay, aw, ah = cur[a]
                bx, by, bw, bh = cur[b]
                if not _rects_overlap((ax, ay, aw, ah), (bx, by, bw, bh), gap):
                    continue
                acx, acy = ax + aw / 2, ay + ah / 2
                bcx, bcy = bx + bw / 2, by + bh / 2
                dx, dy = bcx - acx, bcy - acy
                if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                    dx, dy = 1.0, 0.0
                need_x = (aw + bw) / 2 + gap
                need_y = (ah + bh) / 2 + gap
                ox = need_x - abs(dx)
                oy = need_y - abs(dy)
                if ox <= 0 and oy <= 0:
                    continue
                if ox * abs(dx) >= oy * abs(dy) and ox > 0:
                    push = (ox / 2 + 1.0) * (1 if dx >= 0 else -1)
                    cur[a][0] -= push
                    cur[b][0] += push
                else:
                    push = (oy / 2 + 1.0) * (1 if dy >= 0 else -1)
                    cur[a][1] -= push
                    cur[b][1] += push
                moved = True
        if not moved:
            break
    min_x = min(v[0] for v in cur.values())
    min_y = min(v[1] for v in cur.values())
    sx = _PAD - min_x if min_x < _PAD else 0.0
    sy = _PAD - min_y if min_y < _PAD else 0.0
    return {
        k: (v[0] + sx, v[1] + sy, v[2], v[3]) for k, v in cur.items()
    }


def _graph_deg_nbrs(
    names: list[str],
    edges: list[tuple[str, str]],
) -> tuple[dict[str, int], dict[str, list[str]]]:
    deg: dict[str, int] = {n: 0 for n in names}
    nbrs: dict[str, list[str]] = {n: [] for n in names}
    seen: set[tuple[str, str]] = set()
    for a, b in edges:
        if a not in deg or b not in deg or a == b:
            continue
        key = (a, b) if a < b else (b, a)
        if key in seen:
            continue
        seen.add(key)
        deg[a] += 1
        deg[b] += 1
        nbrs[a].append(b)
        nbrs[b].append(a)
    return deg, nbrs


def _bfs_dist(hub: str, nbrs: dict[str, list[str]], names: list[str]) -> dict[str, int]:
    dist: dict[str, int] = {hub: 0}
    q = [hub]
    i = 0
    while i < len(q):
        u = q[i]
        i += 1
        for v in nbrs.get(u) or []:
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    for n in names:
        dist.setdefault(n, 10_000)
    return dist


def _hub_column_layout(
    names: list[str],
    sizes: dict[str, tuple[float, float]],
    edges: list[tuple[str, str]],
) -> dict[str, tuple[float, float, float, float]]:
    """枢纽分栏：高度数靠左上，邻居环绕，列间宽槽 — 贴近示例「摆得好」。"""
    if not names:
        return {}
    if len(names) == 1:
        w, h = sizes[names[0]]
        return {names[0]: (_PAD, _PAD, w, h)}

    deg, nbrs = _graph_deg_nbrs(names, edges)
    hub = max(names, key=lambda n: (deg[n], n))
    dist = _bfs_dist(hub, nbrs, names)

    n = len(names)
    n_cols = 3 if n >= 6 else (2 if n >= 3 else 1)
    cols: list[list[str]] = [[] for _ in range(n_cols)]
    placed: set[str] = set()

    cols[0].append(hub)
    placed.add(hub)

    layer1 = sorted(
        [x for x in names if dist[x] == 1],
        key=lambda x: (-deg[x], x),
    )
    rest = sorted(
        [x for x in names if x not in placed and dist[x] != 1],
        key=lambda x: (dist[x], -deg[x], x),
    )

    if n_cols >= 3:
        for i, tid in enumerate(layer1):
            if deg[tid] >= 3 and len(cols[1]) < max(2, n // 4):
                cols[1].append(tid)
            else:
                cols[1 + (i % 2)].append(tid)
            placed.add(tid)
        for i, tid in enumerate(rest):
            if tid in placed:
                continue
            if deg[tid] >= 2:
                cols[1].append(tid)
            else:
                cols[2 if i % 2 else 0].append(tid)
            placed.add(tid)
    elif n_cols == 2:
        for i, tid in enumerate(layer1 + rest):
            if tid in placed:
                continue
            cols[1 if i % 2 == 0 else 0].append(tid)
            placed.add(tid)

    for tid in names:
        if tid not in placed:
            cols[-1].append(tid)

    def place(cols_in: list[list[str]]) -> dict[str, tuple[float, float, float, float]]:
        widths = [
            max((sizes[t][0] for t in col), default=120.0) if col else 120.0 for col in cols_in
        ]
        out: dict[str, tuple[float, float, float, float]] = {}
        x = _PAD
        for ci, col in enumerate(cols_in):
            y = _PAD
            cw = widths[ci]
            for tid in col:
                w, h = sizes[tid]
                out[tid] = (x + (cw - w) / 2, y, w, h)
                y += h + _BOX_GAP
            x += cw + _COL_GUTTER
        return out

    for _ in range(16):
        pos = place(cols)
        cy = {k: y + h / 2 for k, (x, y, w, h) in pos.items()}
        new_cols: list[list[str]] = []
        for col in cols:
            col_set = set(col)

            def bary(tid: str, _cs: set[str] = col_set) -> float:
                ys = [cy[nb] for nb in nbrs[tid] if nb in cy and nb not in _cs]
                if not ys:
                    return cy.get(tid, 0.0)
                return sum(ys) / len(ys)

            if hub in col:
                others = [t for t in col if t != hub]
                others.sort(key=lambda t: (bary(t), t))
                new_cols.append([hub] + others)
            else:
                new_cols.append(sorted(col, key=lambda t: (bary(t), t)))
        if new_cols == cols:
            break
        cols = new_cols

    return _separate_boxes(place(cols), gap=_BOX_GAP * 0.85)


def _column_pack_layout(
    names: list[str],
    sizes: dict[str, tuple[float, float]],
    edges: list[tuple[str, str]],
) -> dict[str, tuple[float, float, float, float]]:
    """分栏兜底：与枢纽分栏同一实现。"""
    return _hub_column_layout(names, sizes, edges)


_TREE_V_GAP = 72.0
_TREE_H_GAP = 48.0
_FOREST_GAP = 80.0


def _uf_find(parent: dict[str, str], x: str) -> str:
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def _uf_union(parent: dict[str, str], a: str, b: str) -> bool:
    ra, rb = _uf_find(parent, a), _uf_find(parent, b)
    if ra == rb:
        return False
    parent[rb] = ra
    return True


def _max_spanning_forest(
    nodes: list[str],
    edges: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """按端点度数和优先保留枢纽边，得到连通生成森林（必平面）。"""
    node_set = set(nodes)
    deg: dict[str, int] = {n: 0 for n in nodes}
    uniq: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for a, b in edges:
        if a not in node_set or b not in node_set or a == b:
            continue
        key = (a, b) if a < b else (b, a)
        if key in seen:
            continue
        seen.add(key)
        uniq.append((a, b))
        deg[a] += 1
        deg[b] += 1
    ranked = sorted(uniq, key=lambda e: (-(deg[e[0]] + deg[e[1]]), e[0], e[1]))
    parent = {n: n for n in nodes}
    forest: list[tuple[str, str]] = []
    for a, b in ranked:
        if _uf_union(parent, a, b):
            forest.append((a, b))
    return forest


def _orient_forest(
    nodes: list[str],
    forest: list[tuple[str, str]],
    *,
    prefer_root: str | None = None,
) -> tuple[list[str], dict[str, list[str]], dict[str, str]]:
    """选各连通分量根节点，得到 children / parent。prefer_root 可强制某分量的根。"""
    adj: dict[str, list[str]] = {n: [] for n in nodes}
    for a, b in forest:
        adj[a].append(b)
        adj[b].append(a)
    deg = {n: len(adj[n]) for n in nodes}
    visited: set[str] = set()
    roots: list[str] = []
    children: dict[str, list[str]] = {n: [] for n in nodes}
    parent: dict[str, str] = {}

    def orient(u: str, p: str | None) -> None:
        visited.add(u)
        for v in sorted(adj[u]):
            if v == p:
                continue
            parent[v] = u
            children[u].append(v)
            orient(v, u)

    for start in sorted(nodes, key=lambda n: (-deg[n], n)):
        if start in visited:
            continue
        stack = [start]
        comp: list[str] = []
        seen_c: set[str] = set()
        while stack:
            u = stack.pop()
            if u in seen_c:
                continue
            seen_c.add(u)
            comp.append(u)
            stack.extend(adj[u])
        if prefer_root and prefer_root in seen_c:
            root = prefer_root
        else:
            root = max(comp, key=lambda n: (deg[n], n))
        roots.append(root)
        orient(root, None)
    return roots, children, parent


def _tree_forest_layout(
    names: list[str],
    sizes: dict[str, tuple[float, float]],
    edges: list[tuple[str, str]],
    *,
    prefer_root: str | None = None,
) -> tuple[dict[str, tuple[float, float, float, float]], dict[str, str]]:
    """分层树布局：父子边可用无交叉直角折线。"""
    if not names:
        return {}, {}
    if len(names) == 1:
        w, h = sizes[names[0]]
        return {names[0]: (_PAD, _PAD, w, h)}, {}

    forest = _max_spanning_forest(names, edges)
    roots, children, parent = _orient_forest(names, forest, prefer_root=prefer_root)
    # 孤立点也要画
    placed_roots = set(roots)
    for n in names:
        if n not in parent and n not in placed_roots:
            roots.append(n)
            placed_roots.add(n)

    def subtree_width(u: str) -> float:
        w, _ = sizes[u]
        kids = children.get(u) or []
        if not kids:
            return w
        return max(
            w,
            sum(subtree_width(c) for c in kids) + _TREE_H_GAP * (len(kids) - 1),
        )

    pos: dict[str, tuple[float, float, float, float]] = {}

    def place(u: str, x_left: float, y: float) -> None:
        w, h = sizes[u]
        sw = subtree_width(u)
        pos[u] = (x_left + (sw - w) / 2.0, y, w, h)
        kids = children.get(u) or []
        if not kids:
            return
        cy = y + h + _TREE_V_GAP
        cx = x_left
        for c in kids:
            cw = subtree_width(c)
            place(c, cx, cy)
            cx += cw + _TREE_H_GAP

    x = _PAD
    for r in roots:
        sw = subtree_width(r)
        place(r, x, _PAD)
        x += sw + _FOREST_GAP

    for n in names:
        if n not in pos:
            w, h = sizes[n]
            pos[n] = (x, _PAD, w, h)
            x += w + _FOREST_GAP

    # 不跑 _separate_boxes：避免打乱「父在上、子在下」导致树边交叉
    return pos, parent


def _refresh_assoc_note(model: dict[str, Any]) -> None:
    omitted = model.get("associations_omitted") or []
    n_omit = len(omitted) if isinstance(omitted, list) else 0
    n_draw = len(model.get("associations") or [])
    n_total = len(model.get("associations_all") or []) or n_draw
    algo = str(model.get("layout_algo") or "hub")
    base = (
        "关联/聚合/组合来自 sql/schema.sql 外键；继承/实现来自 Java extends/implements；"
        "依赖来自方法/属性类型引用；属性/方法优先取自 Java（可见性 +/#/-）；"
        "无行映射时属性回退 SQL 列类型；与 domain.schema.json 开题实体对照。"
    )
    skin = str(model.get("_display_mode_note") or "")
    extra = (
        f" 连线规则：同图零交叉、不过桥（多套摆框竞赛选画线最多）；"
        f"布局={algo}；已画 {n_draw}/{n_total} 条"
        + (
            f"；未画 {n_omit} 条外键仍保留在类属性中（可拖开后复位再试）。"
            if n_omit
            else "。"
        )
    )
    model["source_note"] = base + (" " + skin if skin else "") + extra
    model.pop("assoc_modes", None)


def _hv_proper_cross(
    ha: tuple[float, float, float],
    va: tuple[float, float, float],
) -> bool:
    """水平段 (x0,x1,y) 与竖直段 (x,y0,y1) 是否开交叉（含贴边近交叉）。"""
    x0, x1, y = ha
    x, y0, y1 = va
    eps = 0.25
    return x0 + eps < x < x1 - eps and y0 + eps < y < y1 - eps


def _seg_overlap_1d(a0: float, a1: float, b0: float, b1: float, eps: float = 0.5) -> bool:
    lo_a, hi_a = sorted((a0, a1))
    lo_b, hi_b = sorted((b0, b1))
    return hi_a - eps > lo_b and hi_b - eps > lo_a


def _paths_conflict(
    a: list[tuple[float, float]],
    b: list[tuple[float, float]],
) -> bool:
    """两折线是否开交叉（水平×竖直）。

    同槽共线重叠允许（共用外框总线 / T 接），否则稠密星型图会系统性少画边。
    """
    sa, sb = _iter_hv_segments(a), _iter_hv_segments(b)
    for si in sa:
        for sj in sb:
            if si[0] == "H" and sj[0] == "V":
                if _hv_proper_cross((si[1], si[2], si[3]), (sj[1], sj[3], sj[4])):
                    return True
            elif si[0] == "V" and sj[0] == "H":
                if _hv_proper_cross((sj[1], sj[2], sj[3]), (si[1], si[3], si[4])):
                    return True
    return False


def _paths_proper_cross(
    a: list[tuple[float, float]],
    b: list[tuple[float, float]],
) -> bool:
    """兼容旧名：现含共线重叠检测。"""
    return _paths_conflict(a, b)


def _route_tree_edge(
    x1: float,
    y1: float,
    w1: float,
    h1: float,
    x2: float,
    y2: float,
    w2: float,
    h2: float,
    *,
    lane: int = 0,
    n_lanes: int = 1,
) -> list[tuple[float, float]]:
    """父子树边：上方框底边 → 下方框顶边；多边时锚点+中槽错开，避免叠线。"""
    c1x, c1y = x1 + w1 / 2, y1 + h1 / 2
    c2x, c2y = x2 + w2 / 2, y2 + h2 / 2
    t = _lane_t(lane, n_lanes)
    off = _lane_offset(lane, n_lanes)

    def down_path(
        ux: float, uy: float, uw: float, uh: float,
        lx: float, ly: float, lw: float, lh: float,
    ) -> list[tuple[float, float]]:
        # 出/入锚点沿边错开；中槽 y 再按车道偏移
        sx = ux + uw * t
        ex = lx + lw * t
        sy = uy + uh
        ey = ly
        midy = _clamp_mid(sy, ey, (sy + ey) / 2 + off)
        if abs(sx - ex) < 1:
            return [(sx, sy), (ex, ey)]
        return [(sx, sy), (sx, midy), (ex, midy), (ex, ey)]

    # 明显上下关系
    if y1 + h1 <= y2 + 2:
        return down_path(x1, y1, w1, h1, x2, y2, w2, h2)
    if y2 + h2 <= y1 + 2:
        return list(reversed(down_path(x2, y2, w2, h2, x1, y1, w1, h1)))

    # 同层：左右中线槽（兄弟边）— 竖槽 x 按车道错开
    if c1x <= c2x:
        sx, sy = x1 + w1, y1 + h1 * t
        ex, ey = x2, y2 + h2 * t
        midx = _clamp_mid(sx, ex, (sx + ex) / 2 + off)
        if abs(sy - ey) < 1:
            return [(sx, sy), (ex, ey)]
        return [(sx, sy), (midx, sy), (midx, ey), (ex, ey)]
    sx, sy = x1, y1 + h1 * t
    ex, ey = x2 + w2, y2 + h2 * t
    midx = _clamp_mid(sx, ex, (sx + ex) / 2 + off)
    if abs(sy - ey) < 1:
        return [(sx, sy), (ex, ey)]
    return [(sx, sy), (midx, sy), (midx, ey), (ex, ey)]


def _assoc_route(
    frm: str,
    to: str,
    pos: dict[str, tuple[float, float, float, float]],
    parents: dict[str, str],
    obstacles: list[tuple[str, float, float, float, float]],
    *,
    lane: int = 0,
    n_lanes: int = 1,
) -> list[tuple[float, float]]:
    x1, y1, w1, h1 = pos[frm]
    x2, y2, w2, h2 = pos[to]
    # 树边路由仅作窄场景兜底；主路径用外绕正交（绕得开）
    if parents.get(frm) == to or parents.get(to) == frm:
        return _route_tree_edge(
            x1, y1, w1, h1, x2, y2, w2, h2, lane=lane, n_lanes=n_lanes
        )
    return ortho_path(
        x1, y1, w1, h1, x2, y2, w2, h2,
        obstacles=obstacles,
        from_id=frm,
        to_id=to,
        lane=lane,
        n_lanes=n_lanes,
        prefer_outer=True,
    )


def _frame_bounds(
    obstacles: list[tuple[str, float, float, float, float]],
) -> tuple[float, float, float, float]:
    xs = [o[1] for o in obstacles] + [o[1] + o[3] for o in obstacles]
    ys = [o[2] for o in obstacles] + [o[2] + o[4] for o in obstacles]
    return min(xs), max(xs), min(ys), max(ys)


def _local_obstacles_for_edge(
    frm: str,
    to: str,
    pos: dict[str, tuple[float, float, float, float]],
    obstacles: list[tuple[str, float, float, float, float]],
) -> list[tuple[str, float, float, float, float]]:
    """两端类框 AABB 扩一圈内的障碍；避免小关联却绕全图外框。"""
    if frm not in pos or to not in pos:
        return list(obstacles)
    ax, ay, aw, ah = pos[frm]
    bx, by, bw, bh = pos[to]
    pad = _CHANNEL * 1.25
    x0 = min(ax, bx) - pad
    x1 = max(ax + aw, bx + bw) + pad
    y0 = min(ay, by) - pad
    y1 = max(ay + ah, by + bh) + pad
    local = [
        o
        for o in obstacles
        if not (o[1] + o[3] < x0 or o[1] > x1 or o[2] + o[4] < y0 or o[2] > y1)
    ]
    # 至少含两端；过稀则退回全图
    ids = {o[0] for o in local}
    if frm not in ids or to not in ids or len(local) < 2:
        return list(obstacles)
    return local


def _exclusive_outer_paths(
    frm: str,
    to: str,
    pos: dict[str, tuple[float, float, float, float]],
    obstacles: list[tuple[str, float, float, float, float]],
    lane: int,
) -> list[list[tuple[float, float]]]:
    """独占外框车道（先局部外框、再全图；同侧端口 + 四向总线）。"""
    ax, ay, aw, ah = pos[frm]
    bx, by, bw, bh = pos[to]
    t = _lane_t(lane % 7, 7)
    gap = _CHANNEL + lane * (_LANE_GAP + 2.0)
    # 每端只取中点四向端口
    ar, al = (ax + aw, ay + ah * t), (ax, ay + ah * t)
    at, ab = (ax + aw * t, ay), (ax + aw * t, ay + ah)
    br, bl = (bx + bw, by + bh * t), (bx, by + bh * t)
    bt, bb = (bx + bw * t, by), (bx + bw * t, by + bh)

    def paths_for_frame(
        L0: float, R0: float, T0: float, B0: float
    ) -> list[list[tuple[float, float]]]:
        L, R, T, B = L0 - gap, R0 + gap, T0 - gap, B0 + gap
        return [
            [ar, (R, ar[1]), (R, br[1]), br],
            [al, (L, al[1]), (L, bl[1]), bl],
            [at, (at[0], T), (bt[0], T), bt],
            [ab, (ab[0], B), (bb[0], B), bb],
            [ar, (R, ar[1]), (R, B), (bb[0], B), bb],
            [al, (L, al[1]), (L, B), (bb[0], B), bb],
            [ar, (R, ar[1]), (R, T), (bt[0], T), bt],
            [al, (L, al[1]), (L, T), (bt[0], T), bt],
            [ab, (ab[0], B), (L, B), (L, bl[1]), bl],
            [ab, (ab[0], B), (R, B), (R, br[1]), br],
            [at, (at[0], T), (L, T), (L, bl[1]), bl],
            [at, (at[0], T), (R, T), (R, br[1]), br],
        ]

    out: list[list[tuple[float, float]]] = []
    local = _local_obstacles_for_edge(frm, to, pos, obstacles)
    seen_frame: set[tuple[float, float, float, float]] = set()
    for obs in (local, obstacles):
        fr = _frame_bounds(obs)
        key = tuple(round(v, 1) for v in fr)
        if key in seen_frame:
            continue
        seen_frame.add(key)
        out.extend(paths_for_frame(*fr))
    # 短路径优先，减少「绕全图一圈贴边」
    out.sort(key=_path_len)
    return out


def _dedupe_path_pts(
    pts: list[tuple[float, float]], *, eps: float = 0.5
) -> list[tuple[float, float]]:
    """去掉零长度段（外绕候选偶发重复点，箭头顶在半空像断线）。"""
    if not pts:
        return []
    out: list[tuple[float, float]] = [pts[0]]
    for p in pts[1:]:
        q = out[-1]
        if abs(p[0] - q[0]) > eps or abs(p[1] - q[1]) > eps:
            out.append(p)
    return out


def _port_leaves_outward(
    p0: tuple[float, float],
    p1: tuple[float, float],
    box: tuple[float, float, float, float],
) -> bool:
    """端口出发的第一段必须朝框外，禁止穿回自身框内（否则线被白底盖住只剩框外断头）。"""
    x0, y0 = p0
    x1, y1 = p1
    bx, by, bw, bh = box
    tol = 2.5
    on_r = abs(x0 - (bx + bw)) <= tol and by - tol <= y0 <= by + bh + tol
    on_l = abs(x0 - bx) <= tol and by - tol <= y0 <= by + bh + tol
    on_t = abs(y0 - by) <= tol and bx - tol <= x0 <= bx + bw + tol
    on_b = abs(y0 - (by + bh)) <= tol and bx - tol <= x0 <= bx + bw + tol
    if on_r and x1 < x0 - 1.0:
        return False
    if on_l and x1 > x0 + 1.0:
        return False
    if on_t and y1 > y0 + 1.0:
        return False
    if on_b and y1 < y0 - 1.0:
        return False
    return True


def _path_cuts_box_interior(
    pts: list[tuple[float, float]],
    box: tuple[float, float, float, float],
    *,
    eps: float = 1.0,
) -> bool:
    """折线是否穿过框的严格内部（贴边/端口不算）。"""
    bx, by, bw, bh = box
    ix0, iy0 = bx + eps, by + eps
    ix1, iy1 = bx + bw - eps, by + bh - eps
    if ix1 <= ix0 or iy1 <= iy0:
        return False
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        if abs(y0 - y1) < 0.5:
            y = y0
            if iy0 < y < iy1:
                lo, hi = sorted((x0, x1))
                if lo < ix1 - 0.1 and hi > ix0 + 0.1:
                    return True
        elif abs(x0 - x1) < 0.5:
            x = x0
            if ix0 < x < ix1:
                lo, hi = sorted((y0, y1))
                if lo < iy1 - 0.1 and hi > iy0 + 0.1:
                    return True
    return False


def _path_respects_endpoint_ports(
    pts: list[tuple[float, float]],
    box_from: tuple[float, float, float, float] | None,
    box_to: tuple[float, float, float, float] | None,
) -> bool:
    if len(pts) < 2:
        return False
    if box_from:
        if not _port_leaves_outward(pts[0], pts[1], box_from):
            return False
        if _path_cuts_box_interior(pts, box_from):
            return False
    if box_to:
        # 到达端：末段反向应是「离开 to」，即从框外走进端口
        if not _port_leaves_outward(pts[-1], pts[-2], box_to):
            return False
        if _path_cuts_box_interior(pts, box_to):
            return False
    return True


def _path_ok(
    pts: list[tuple[float, float]],
    obstacles: list[tuple[str, float, float, float, float]],
    ignore: set[str],
    existing: list[list[tuple[float, float]]],
    *,
    box_from: tuple[float, float, float, float] | None = None,
    box_to: tuple[float, float, float, float] | None = None,
) -> bool:
    pts = _dedupe_path_pts(pts)
    if len(pts) < 2:
        return False
    if not _path_respects_endpoint_ports(pts, box_from, box_to):
        return False
    if _path_obstacle_hits(pts, obstacles, ignore) > 0:
        return False
    return not any(_paths_conflict(pts, p) for p in existing)


def _route_nocross_candidate(
    frm: str,
    to: str,
    pos: dict[str, tuple[float, float, float, float]],
    obstacles: list[tuple[str, float, float, float, float]],
    existing: list[list[tuple[float, float]]],
    *,
    lane: int,
    n_lanes: int,
    parents: dict[str, str] | None = None,
    strict_lane: bool = False,
) -> list[tuple[float, float]] | None:
    """树边 / 外绕 / 独占外框；找到第一条合法路径即返回（避免海量候选扫描）。

    strict_lane=True：调用方已在扫车道时只试本车道（±0），避免 recover 二次笛卡尔积。
    """
    parents = parents or {}
    ignore = {frm, to}
    box_from = pos.get(frm)
    box_to = pos.get(to)

    def ok(pts: list[tuple[float, float]]) -> bool:
        return _path_ok(
            pts,
            obstacles,
            ignore,
            existing,
            box_from=box_from,
            box_to=box_to,
        )

    if parents.get(frm) == to or parents.get(to) == frm:
        pts = _route_tree_edge(*pos[frm], *pos[to], lane=lane, n_lanes=n_lanes)
        if ok(pts):
            return _dedupe_path_pts(pts)

    if strict_lane:
        lane_try = [lane]
        outer_lanes = [lane]
    else:
        # 首轮选边：本车道及邻近 + 少量低车道兜底（不再扫到 n_lanes 全宽）
        lane_try = list(range(lane, lane + min(3, max(2, n_lanes))))
        for low in range(0, min(4, max(lane, 1))):
            if low not in lane_try:
                lane_try.append(low)
        outer_lanes = list(range(lane, lane + min(4, max(3, n_lanes))))
        for low in range(0, min(3, max(lane, 1))):
            if low not in outer_lanes:
                outer_lanes.append(low)

    for use_lane in lane_try:
        pts = ortho_path(
            *pos[frm],
            *pos[to],
            obstacles=obstacles,
            from_id=frm,
            to_id=to,
            lane=use_lane,
            n_lanes=max(n_lanes, use_lane + 1),
            prefer_outer=True,
            fast=True,
        )
        if ok(pts):
            return _dedupe_path_pts(pts)

    # 独占外框（较贵）：每车道只试最短若干条
    for use_lane in outer_lanes:
        for pts in _exclusive_outer_paths(frm, to, pos, obstacles, use_lane)[:8]:
            if ok(pts):
                return _dedupe_path_pts(pts)
    return None


def _finalize_canvas_extent(
    pos: dict[str, tuple[float, float, float, float]],
    edge_paths: list[tuple[str, str, list[tuple[float, float]], str]],
    *,
    margin: float = _EDGE_MARGIN,
) -> tuple[
    dict[str, tuple[float, float, float, float]],
    list[tuple[str, str, list[tuple[float, float]], str]],
    float,
    float,
]:
    """框+折线整体入边距，避免默认视口裁掉外绕线头。"""
    xs: list[float] = []
    ys: list[float] = []
    for x, y, w, h in pos.values():
        xs.extend((x, x + w))
        ys.extend((y, y + h))
    for _f, _t, pts, _k in edge_paths:
        for px, py in pts:
            xs.append(float(px))
            ys.append(float(py))
    if not xs:
        return pos, edge_paths, 400.0, 300.0
    min_x, max_x0 = min(xs), max(xs)
    min_y, max_y0 = min(ys), max(ys)
    sx = margin - min_x if min_x < margin else 0.0
    sy = margin - min_y if min_y < margin else 0.0
    if sx or sy:
        pos = {k: (x + sx, y + sy, w, h) for k, (x, y, w, h) in pos.items()}
        edge_paths = [
            (f, t, [(x + sx, y + sy) for x, y in pts], kind)
            for f, t, pts, kind in edge_paths
        ]
        max_x0 += sx
        max_y0 += sy
    return pos, edge_paths, max_x0 + margin, max_y0 + margin


def _purge_crossing_paths(
    drawn: list[dict[str, Any]],
    paths: list[list[tuple[float, float]]],
) -> tuple[list[dict[str, Any]], list[list[tuple[float, float]]]]:
    """最终保险丝：仍冲突则丢掉后加入的边。"""
    keep_a: list[dict[str, Any]] = []
    keep_p: list[list[tuple[float, float]]] = []
    for a, pts in zip(drawn, paths):
        if any(_paths_conflict(pts, p) for p in keep_p):
            continue
        keep_a.append(a)
        keep_p.append(pts)
    return keep_a, keep_p


def _select_crossing_free_assocs(
    model: dict[str, Any],
    pos: dict[str, tuple[float, float, float, float]],
    *,
    deadline: float | None = None,
) -> None:
    """摆好框后：先连通生成树，再尽量外绕补边；画不上的进 omitted。"""
    all_a = [a for a in (model.get("associations_all") or []) if isinstance(a, dict)]
    if not all_a:
        model["associations"] = []
        model["associations_omitted"] = []
        model["_assoc_paths"] = []
        return
    select_deadline = deadline
    if select_deadline is None:
        select_deadline = time.monotonic() + _SELECT_BUDGET_SEC
    nodes = list(pos.keys())
    deg, _ = _graph_deg_nbrs(
        nodes,
        [(str(a.get("from")), str(a.get("to"))) for a in all_a],
    )
    ranked = sorted(
        all_a,
        key=lambda a: (
            _KIND_DRAW_PRIORITY.get(
                _normalize_rel_kind(str(a.get("kind") or "association")), 4
            ),
            -(deg.get(str(a.get("from")), 0) + deg.get(str(a.get("to")), 0)),
            str(a.get("from")),
            str(a.get("to")),
        ),
    )
    edge_pairs = [(str(a.get("from")), str(a.get("to"))) for a in ranked]
    forest = _max_spanning_forest(nodes, edge_pairs)
    forest_set = {(a, b) if a < b else (b, a) for a, b in forest}

    obstacles = [(tid, x, y, w, h) for tid, (x, y, w, h) in pos.items()]
    n_lanes = max(1, min(len(ranked), _RECOVER_LANE_HARD))
    drawn: list[dict[str, Any]] = []
    paths: list[list[tuple[float, float]]] = []
    drawn_undir: set[tuple[str, str]] = set()
    parents = {str(k): str(v) for k, v in (model.get("tree_parents") or {}).items()}

    def try_add(
        a: dict[str, Any], force_lane: int, *, strict_lane: bool = False
    ) -> bool:
        frm, to = str(a.get("from")), str(a.get("to"))
        if frm not in pos or to not in pos or frm == to:
            return False
        key = (frm, to) if frm < to else (to, frm)
        if key in drawn_undir:
            return False
        pts = _route_nocross_candidate(
            frm,
            to,
            pos,
            obstacles,
            paths,
            lane=force_lane,
            n_lanes=max(n_lanes, force_lane + 1),
            parents=parents,
            strict_lane=strict_lane,
        )
        if pts is None:
            return False
        drawn.append(a)
        paths.append(pts)
        drawn_undir.add(key)
        return True

    def _undir_key(a: dict[str, Any]) -> tuple[str, str]:
        u, v = str(a.get("from")), str(a.get("to"))
        return (u, v) if u < v else (v, u)

    def _recover_pending(start_lanes: list[int]) -> None:
        """漏边补画：按车道扫；strict_lane 避免与路由内部再笛卡尔积。"""
        pending = [a for a in ranked if _undir_key(a) not in drawn_undir]
        for lane0 in start_lanes:
            if not pending or time.monotonic() >= select_deadline:
                break
            still: list[dict[str, Any]] = []
            for idx, a in enumerate(pending):
                if time.monotonic() >= select_deadline:
                    still.extend(pending[idx:])
                    break
                if try_add(a, lane0, strict_lane=True):
                    continue
                still.append(a)
            pending = [x for x in still if _undir_key(x) not in drawn_undir]

    lane_i = 0
    for a in ranked:
        if time.monotonic() >= select_deadline:
            break
        key = _undir_key(a)
        if key not in forest_set:
            continue
        if try_add(a, lane_i, strict_lane=False):
            lane_i += 1

    for a in ranked:
        if time.monotonic() >= select_deadline:
            break
        if _undir_key(a) in drawn_undir:
            continue
        if try_add(a, lane_i, strict_lane=False):
            lane_i += 1

    soft = min(_RECOVER_LANE_SOFT, max(6, n_lanes))
    hard = min(_RECOVER_LANE_HARD, max(soft + 4, n_lanes))
    _recover_pending(list(range(0, soft)))
    if time.monotonic() < select_deadline:
        _recover_pending(list(range(soft, hard)))

    drawn, paths = _purge_crossing_paths(drawn, paths)
    drawn_undir = {
        (str(a.get("from")), str(a.get("to")))
        if str(a.get("from")) < str(a.get("to"))
        else (str(a.get("to")), str(a.get("from")))
        for a in drawn
    }
    if time.monotonic() < select_deadline:
        _recover_pending(list(range(0, soft)))
    drawn, paths = _purge_crossing_paths(drawn, paths)

    drawn_ids = {id(a) for a in drawn}
    omitted = [a for a in all_a if id(a) not in drawn_ids]
    model["associations"] = drawn
    model["associations_omitted"] = omitted
    model["_assoc_paths"] = paths
    ev = model.setdefault("evidence", {})
    if isinstance(ev, dict):
        ev["assoc_drawn"] = len(drawn)
        ev["assoc_omitted"] = len(omitted)
        ev["zero_crossing"] = True
        if time.monotonic() >= select_deadline - 0.05:
            ev["select_budget_hit"] = True


def _layout_classes(model: dict[str, Any]) -> dict[str, tuple[float, float, float, float]]:
    classes = [c for c in (model.get("classes") or []) if isinstance(c, dict)]
    if not classes:
        return {}
    sizes = {str(c["id"]): _box_size(c) for c in classes}
    names = [str(c["id"]) for c in classes]
    all_a = model.get("associations_all") or model.get("associations") or []
    edges = [
        (str(a.get("from")), str(a.get("to")))
        for a in all_a
        if isinstance(a, dict)
    ]
    if len(names) == 1:
        w, h = sizes[names[0]]
        return {names[0]: (_PAD, _PAD, w, h)}
    # 默认枢纽分栏（摆得好）；不再用树形竖排
    model["tree_parents"] = {}
    return _hub_column_layout(names, sizes, edges)


def _seg_hits_box(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    bx: float,
    by: float,
    bw: float,
    bh: float,
    pad: float = 6.0,
) -> bool:
    """轴对齐线段是否穿过（膨胀后的）矩形内部。端点贴边不算穿心。"""
    left, right = bx - pad, bx + bw + pad
    top, bottom = by - pad, by + bh + pad
    # 水平
    if abs(y0 - y1) < 1e-6:
        y = y0
        if y <= top or y >= bottom:
            return False
        lo, hi = sorted((x0, x1))
        # 线段穿过矩形左右之间且有重叠区间
        return lo < right - 1 and hi > left + 1
    # 竖直
    if abs(x0 - x1) < 1e-6:
        x = x0
        if x <= left or x >= right:
            return False
        lo, hi = sorted((y0, y1))
        return lo < bottom - 1 and hi > top + 1
    return False


def _path_obstacle_hits(
    pts: list[tuple[float, float]],
    obstacles: list[tuple[str, float, float, float, float]],
    ignore: set[str],
) -> int:
    hits = 0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        for oid, bx, by, bw, bh in obstacles:
            if oid in ignore:
                continue
            if _seg_hits_box(x0, y0, x1, y1, bx, by, bw, bh):
                hits += 1
    return hits


def _path_len(pts: list[tuple[float, float]]) -> float:
    s = 0.0
    for i in range(len(pts) - 1):
        s += abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1])
    return s


def ortho_path(
    x1: float,
    y1: float,
    w1: float,
    h1: float,
    x2: float,
    y2: float,
    w2: float,
    h2: float,
    *,
    obstacles: list[tuple[str, float, float, float, float]] | None = None,
    from_id: str = "",
    to_id: str = "",
    lane: int = 0,
    n_lanes: int = 1,
    prefer_outer: bool = False,
    fast: bool = False,
) -> list[tuple[float, float]]:
    """直角折线；prefer_outer 时优先外圈槽（示例：绕得开、不过桥）。

    fast=True：少候选（零交叉选边热路径），跳过列间槽笛卡尔积。
    """
    c1x, c1y = x1 + w1 / 2, y1 + h1 / 2
    c2x, c2y = x2 + w2 / 2, y2 + h2 / 2
    t = _lane_t(lane, n_lanes)
    off = _lane_offset(lane, n_lanes)

    def side_ports() -> list[tuple[float, float, float, float]]:
        ports = [
            (x1 + w1, y1 + h1 * t, x2, y2 + h2 * t),
            (x1, y1 + h1 * t, x2 + w2, y2 + h2 * t),
            (x1 + w1 * t, y1 + h1, x2 + w2 * t, y2),
            (x1 + w1 * t, y1, x2 + w2 * t, y2 + h2),
        ]
        if fast:
            return ports
        return ports + [
            (x1 + w1, y1 + h1 * t, x2 + w2, y2 + h2 * t),
            (x1, y1 + h1 * t, x2, y2 + h2 * t),
            (x1 + w1 * t, y1 + h1, x2 + w2 * t, y2 + h2),
            (x1 + w1 * t, y1, x2 + w2 * t, y2),
        ]

    def z_via_mid(sx: float, sy: float, ex: float, ey: float) -> list[tuple[float, float]]:
        if abs(sy - ey) < 1.0:
            return [(sx, sy), (ex, ey)]
        if abs(sx - ex) < 1.0:
            return [(sx, sy), (ex, ey)]
        return [(sx, sy), (ex, sy), (ex, ey)]

    def z_via_mid_v(sx: float, sy: float, ex: float, ey: float) -> list[tuple[float, float]]:
        if abs(sx - ex) < 1.0 or abs(sy - ey) < 1.0:
            return [(sx, sy), (ex, ey)]
        return [(sx, sy), (sx, ey), (ex, ey)]

    candidates: list[tuple[list[tuple[float, float]], bool]] = []

    def add(pts: list[tuple[float, float]], outer: bool = False) -> None:
        if pts and len(pts) >= 2:
            candidates.append((pts, outer))

    for sx, sy, ex, ey in side_ports():
        add(z_via_mid(sx, sy, ex, ey))
        add(z_via_mid_v(sx, sy, ex, ey))
        mid = _clamp_mid(sx, ex, (sx + ex) / 2 + off)
        if abs(sy - ey) >= 1.0:
            add([(sx, sy), (mid, sy), (mid, ey), (ex, ey)])
        midy = _clamp_mid(sy, ey, (sy + ey) / 2 + off)
        if abs(sx - ex) >= 1.0:
            add([(sx, sy), (sx, midy), (ex, midy), (ex, ey)])

    obs = obstacles or []
    if obs:
        xs = [o[1] for o in obs] + [o[1] + o[3] for o in obs]
        ys = [o[2] for o in obs] + [o[2] + o[4] for o in obs]
        L = min(xs) - _CHANNEL - lane * _LANE_GAP
        R = max(xs) + _CHANNEL + lane * _LANE_GAP
        T = min(ys) - _CHANNEL - lane * _LANE_GAP
        B = max(ys) + _CHANNEL + lane * _LANE_GAP
        for sx, sy, ex, ey in side_ports()[:4]:
            add([(sx, sy), (L, sy), (L, ey), (ex, ey)], True)
            add([(sx, sy), (R, sy), (R, ey), (ex, ey)], True)
            add([(sx, sy), (sx, T), (ex, T), (ex, ey)], True)
            add([(sx, sy), (sx, B), (ex, B), (ex, ey)], True)
            if not fast:
                add([(sx, sy), (L, sy), (L, B), (ex, B), (ex, ey)], True)
                add([(sx, sy), (R, sy), (R, B), (ex, B), (ex, ey)], True)
                add([(sx, sy), (L, sy), (L, T), (ex, T), (ex, ey)], True)
                add([(sx, sy), (R, sy), (R, T), (ex, T), (ex, ey)], True)
        if not fast:
            rights = sorted({o[1] + o[3] for o in obs})
            lefts = sorted({o[1] for o in obs})
            bottoms = sorted({o[2] + o[4] for o in obs})
            tops = sorted({o[2] for o in obs})
            gutters_x: list[float] = []
            for r in rights:
                for Lft in lefts:
                    if Lft - r >= _BOX_GAP * 0.6:
                        gutters_x.append((r + Lft) / 2 + off)
                        break
            gutters_y: list[float] = []
            for bt in bottoms:
                for tp in tops:
                    if tp - bt >= _BOX_GAP * 0.6:
                        gutters_y.append((bt + tp) / 2 + off)
                        break
            for gx in gutters_x[:8]:
                for sx, sy, ex, ey in side_ports()[:4]:
                    add([(sx, sy), (gx, sy), (gx, ey), (ex, ey)])
            for gy in gutters_y[:8]:
                for sx, sy, ex, ey in side_ports()[:4]:
                    add([(sx, sy), (sx, gy), (ex, gy), (ex, ey)])

    ignore = {from_id, to_id}
    box_from = (x1, y1, w1, h1)
    box_to = (x2, y2, w2, h2)
    best: list[tuple[float, float]] | None = None
    best_key: tuple[int, int, int, int, float] | None = None
    for pts, outer in candidates:
        pts_n = _dedupe_path_pts(pts)
        if len(pts_n) < 2:
            continue
        # 穿回自身框 → 重罚（等同不可用）；勿当 hits=0 赢家
        port_bad = 0 if _path_respects_endpoint_ports(pts_n, box_from, box_to) else 1
        hits = _path_obstacle_hits(pts_n, obs, ignore) if obs else 0
        bends = max(0, len(pts_n) - 2)
        length = _path_len(pts_n)
        outer_pen = 0 if (outer or not prefer_outer) else 1
        key = (port_bad, hits, outer_pen, bends, length)
        if best_key is None or key < best_key:
            best_key = key
            best = pts_n
    if best and best_key and best_key[0] == 0:
        return best
    # 全部穿框则退回直连侧端口（保证朝外）
    dx, dy = c2x - c1x, c2y - c1y
    if abs(dx) >= abs(dy):
        if dx >= 0:
            sx, sy, ex, ey = x1 + w1, y1 + h1 * t, x2, y2 + h2 * t
        else:
            sx, sy, ex, ey = x1, y1 + h1 * t, x2 + w2, y2 + h2 * t
        mid = _clamp_mid(sx, ex, (sx + ex) / 2 + off)
        if abs(sy - ey) < 1.0:
            return [(sx, sy), (ex, ey)]
        return [(sx, sy), (mid, sy), (mid, ey), (ex, ey)]
    if dy >= 0:
        sx, sy, ex, ey = x1 + w1 * t, y1 + h1, x2 + w2 * t, y2
    else:
        sx, sy, ex, ey = x1 + w1 * t, y1, x2 + w2 * t, y2 + h2
    mid = _clamp_mid(sy, ey, (sy + ey) / 2 + off)
    if abs(sx - ex) < 1.0:
        return [(sx, sy), (ex, ey)]
    return [(sx, sy), (sx, mid), (ex, mid), (ex, ey)]


def _path_d(pts: list[tuple[float, float]]) -> str:
    pts = _dedupe_path_pts(pts)
    if not pts:
        return ""
    parts = [f"M {_f(pts[0][0])} {_f(pts[0][1])}"]
    for x, y in pts[1:]:
        parts.append(f"L {_f(x)} {_f(y)}")
    return " ".join(parts)


def _iter_hv_segments(
    pts: list[tuple[float, float]],
) -> list[tuple[str, float, float, float, float]]:
    """返回 [('H', x0, x1, y, y) | ('V', x, x, y0, y1), ...]。"""
    out: list[tuple[str, float, float, float, float]] = []
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        if abs(y0 - y1) < 0.5 and abs(x0 - x1) >= 0.5:
            out.append(("H", min(x0, x1), max(x0, x1), y0, y0))
        elif abs(x0 - x1) < 0.5 and abs(y0 - y1) >= 0.5:
            out.append(("V", x0, x0, min(y0, y1), max(y0, y1)))
    return out
