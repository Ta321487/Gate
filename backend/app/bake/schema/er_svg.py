"""陈氏 E-R：ELK layered 初局坐标 + 几何外页弯线（禁实体全环）。"""

from __future__ import annotations

import math
import random
import time
from collections import defaultdict
from itertools import permutations

from app.bake.schema.diagram_style import FONT_CN, FONT_TECH
from app.bake.schema.diagram_svg_util import svg_esc, text_w_cjk
from app.bake.schema.layout_elk import ElkLayoutError, layout_graph

_esc = svg_esc
_text_w = text_w_cjk

ENTITY_HH = 22
ATTR_RH = 14

# 旧环序/双页工具仍保留供单测对照；总图默认不再走环。
_LAYOUT_BUDGET_SEC = 2.5
_ORDER_SHARE = 0.25
_REFINE_ROUNDS = 12
_REFINE_ROUNDS_LIGHT = 3
_ORDER_RANDOM_SEEDS = 8
_BOOK_RANDOM_SEEDS = 20
_HUB_TRY_LIMIT = 3
_PERM_N_MAX = 7
_OUTER_NEST_GAP = 56.0
_ELK_PAD = 56.0


def _entity_hw(label: str) -> float:
    return max(40.0, _text_w(label, 13) / 2 + 14)


def _attr_rx(label: str) -> float:
    return max(28.0, _text_w(label, 10) / 2 + 12)


def _attr_cloud_radius(attrs: list[dict], entity_hw: float) -> float:
    m = len(attrs)
    if m == 0:
        return 0.0
    max_rx = max((_attr_rx(c.get("label") or c["name"]) for c in attrs), default=28.0)
    clear_box = math.hypot(entity_hw, ENTITY_HH) + max_rx + 30
    if m == 1:
        return clear_box
    need = (2 * max_rx + 20) / (2 * math.sin(math.pi / m))
    return max(clear_box, need)


def _rect_edge(cx: float, cy: float, tx: float, ty: float, hw: float, hh: float) -> tuple[float, float]:
    dx, dy = tx - cx, ty - cy
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return cx, cy - hh
    sx = hw / abs(dx) if abs(dx) > 1e-9 else float("inf")
    sy = hh / abs(dy) if abs(dy) > 1e-9 else float("inf")
    t = min(sx, sy)
    return cx + dx * t, cy + dy * t


def _ellipse_edge(cx: float, cy: float, rx: float, ry: float, fx: float, fy: float) -> tuple[float, float]:
    ox, oy = fx - cx, fy - cy
    if abs(ox) < 1e-9 and abs(oy) < 1e-9:
        return cx, cy - ry
    s = math.hypot(ox / rx, oy / ry) or 1.0
    return cx + ox / s, cy + oy / s


def _diamond_edge(cx: float, cy: float, hw: float, hh: float, tx: float, ty: float) -> tuple[float, float]:
    """菱形 |dx|/hw + |dy|/hh = 1 与中心→目标射线的交点。"""
    ox, oy = tx - cx, ty - cy
    if abs(ox) < 1e-9 and abs(oy) < 1e-9:
        return cx, cy - hh
    denom = abs(ox) / hw + abs(oy) / hh
    if denom < 1e-9:
        return cx, cy - hh
    t = 1.0 / denom
    return cx + ox * t, cy + oy * t


def _undirected_pairs(edges: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """去重无向边 (a<=b)。"""
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for a, b in edges:
        if not a or not b or a == b:
            continue
        e = (a, b) if a <= b else (b, a)
        if e in seen:
            continue
        seen.add(e)
        out.append(e)
    return out


def _circular_pair_crosses(a: int, b: int, c: int, d: int) -> bool:
    """环上两弦是否交错（共享端点不算）。"""
    if a > b:
        a, b = b, a
    if c > d:
        c, d = d, c
    if len({a, b, c, d}) < 4:
        return False
    return (a < c < b < d) or (c < a < d < b)


def _circular_crossings(order: list[str], edges: list[tuple[str, str]]) -> int:
    """环上弦交叉数（四端点交错）。"""
    pos = {name: i for i, name in enumerate(order)}
    idx_edges: list[tuple[int, int]] = []
    for a, b in _undirected_pairs(edges):
        if a not in pos or b not in pos:
            continue
        i, j = pos[a], pos[b]
        if i > j:
            i, j = j, i
        idx_edges.append((i, j))
    count = 0
    for i, (a, b) in enumerate(idx_edges):
        for c, d in idx_edges[i + 1 :]:
            if _circular_pair_crosses(a, b, c, d):
                count += 1
    return count


def _pair_crosses_on_order(
    order: list[str], e1: tuple[str, str], e2: tuple[str, str]
) -> bool:
    pos = {name: i for i, name in enumerate(order)}
    if e1[0] not in pos or e1[1] not in pos or e2[0] not in pos or e2[1] not in pos:
        return False
    return _circular_pair_crosses(pos[e1[0]], pos[e1[1]], pos[e2[0]], pos[e2[1]])


def _dfs_order(names: list[str], edges: list[tuple[str, str]], start: str) -> list[str]:
    adj: dict[str, list[str]] = defaultdict(list)
    for a, b in _undirected_pairs(edges):
        adj[a].append(b)
        adj[b].append(a)
    for k in adj:
        adj[k].sort()
    seen = {start}
    order = [start]
    stack = [start]
    while stack:
        u = stack[-1]
        nxt = next((v for v in adj[u] if v not in seen), None)
        if nxt is None:
            stack.pop()
            continue
        seen.add(nxt)
        order.append(nxt)
        stack.append(nxt)
    for x in names:
        if x not in seen:
            order.append(x)
    return order


def _refine_order_relocate(
    order: list[str],
    edges: list[tuple[str, str]],
    *,
    deadline: float | None = None,
) -> list[str]:
    """顶点重插局部搜索，压低环上交叉。"""
    order = list(order)
    n = len(order)
    if n <= 2:
        return order
    improved = True
    rounds = 0
    while improved and rounds < _REFINE_ROUNDS:
        if deadline is not None and time.monotonic() >= deadline:
            break
        improved = False
        rounds += 1
        cur = _circular_crossings(order, edges)
        if cur == 0:
            return order
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                node = order.pop(i)
                order.insert(j, node)
                c = _circular_crossings(order, edges)
                if c < cur:
                    improved = True
                    break
                order.pop(j)
                order.insert(i, node)
            if improved:
                break
    return order


def _order_minimize_crossings(
    names: list[str],
    edges: list[tuple[str, str]],
    *,
    deadline: float | None = None,
) -> list[str]:
    """多起点 + 重插，尽量把环上交叉压到 0（可外平面时）。"""
    names = list(names)
    n = len(names)
    if n <= 2:
        return names
    seeds: list[list[str]] = [list(names), list(reversed(names))]
    # 度数高的当 DFS 起点更易出好环序；不必每个点都扫一遍
    deg = _degree_map(names, edges)
    starts = sorted(names, key=lambda x: (-deg.get(x, 0), x))[: min(4, n)]
    for start in starts:
        seeds.append(_dfs_order(names, edges, start))
    # 小图穷举旋转代表（固定首点）；n<=7 → 6! =720
    if n <= _PERM_N_MAX:
        base = names[0]
        rest = names[1:]
        best_o = list(names)
        best = _circular_crossings(best_o, edges)
        if best == 0:
            return best_o
        for perm in permutations(rest):
            if deadline is not None and time.monotonic() >= deadline:
                break
            order = [base, *perm]
            c = _circular_crossings(order, edges)
            if c < best:
                best = c
                best_o = order
                if best == 0:
                    return best_o
        return best_o

    rng = random.Random(0xE12)
    for _ in range(_ORDER_RANDOM_SEEDS):
        s = list(names)
        rng.shuffle(s)
        seeds.append(s)

    best_o = list(names)
    best = _circular_crossings(best_o, edges)
    for seed in seeds:
        if deadline is not None and time.monotonic() >= deadline:
            break
        order = _refine_order_relocate(seed, edges, deadline=deadline)
        c = _circular_crossings(order, edges)
        if c < best:
            best = c
            best_o = order
            if best == 0:
                return best_o
    return best_o


def _two_page_partition(
    order: list[str],
    edges: list[tuple[str, str]],
    *,
    force: bool = False,
) -> tuple[bool, set[tuple[str, str]], set[tuple[str, str]]]:
    """把无向边分成环内/环外两页，同页内弦不交叉。

    force=True：放不下的边一律进外页（保证总能出图，且内页零交叉）。
    """
    pos = {name: i for i, name in enumerate(order)}
    n = len(order)
    pairs = [e for e in _undirected_pairs(edges) if e[0] in pos and e[1] in pos]

    def span(e: tuple[str, str]) -> int:
        i, j = pos[e[0]], pos[e[1]]
        d = abs(i - j)
        return min(d, n - d)

    pairs.sort(key=span)
    inner: list[tuple[str, str]] = []
    outer: list[tuple[str, str]] = []
    for e in pairs:
        if all(not _pair_crosses_on_order(order, e, f) for f in inner):
            inner.append(e)
            continue
        if all(not _pair_crosses_on_order(order, e, f) for f in outer):
            outer.append(e)
            continue
        if force:
            outer.append(e)
            continue
        return False, set(), set()
    return True, set(inner), set(outer)


def _book_embedding(
    names: list[str],
    edges: list[tuple[str, str]],
    *,
    deadline: float | None = None,
) -> tuple[list[str], set[tuple[str, str]], set[tuple[str, str]]]:
    """求环序 + 双页划分，优先无外页、其次外页尽量少。

    旧实现把整段预算耗在压环交叉上，双页评分几乎跑不到 → 外页偏多、几何易交叉。
    现拆成：短时粗环序 + 大量轻量候选按外页数评分 + 剩余时间精炼优胜者。
    """
    names = list(names)
    if len(names) <= 1:
        return names, set(), set()

    now = time.monotonic()
    order_deadline = deadline
    if deadline is not None:
        remain = max(0.0, deadline - now)
        order_deadline = now + remain * _ORDER_SHARE

    primary = _order_minimize_crossings(names, edges, deadline=order_deadline)

    # 先堆大量「未精炼」候选：双页评分 O(E²) 很便宜，重插才贵
    candidates: list[list[str]] = [primary]
    deg = _degree_map(names, edges)
    for start in sorted(names, key=lambda x: (-deg.get(x, 0), x))[: min(8, len(names))]:
        candidates.append(_dfs_order(names, edges, start))
    rng = random.Random(0xB00C)
    for _ in range(_BOOK_RANDOM_SEEDS):
        s = list(names)
        rng.shuffle(s)
        candidates.append(s)

    best: tuple[int, int, list[str], set[tuple[str, str]], set[tuple[str, str]]] | None = None
    seen_ord: set[tuple[str, ...]] = set()

    def _consider(order: list[str]) -> bool:
        """更新 best；若已零外页零环交叉返回 True（可早停）。"""
        nonlocal best
        key = tuple(order)
        if key in seen_ord:
            return False
        seen_ord.add(key)
        ok, inner, outer = _two_page_partition(order, edges)
        if not ok:
            return False
        score = (len(outer), _circular_crossings(order, edges))
        if best is None or score < (best[0], best[1]):
            best = (score[0], score[1], order, inner, outer)
            return score == (0, 0)
        return False

    for order in candidates:
        if _consider(order):
            return best[2], best[3], best[4]  # type: ignore[index]

    # 剩余时间：浅精炼 + 邻域扰动，继续压外页数
    if best is not None and (deadline is None or time.monotonic() < deadline):
        refined = _refine_order_relocate_limited(
            list(best[2]), edges, rounds=_REFINE_ROUNDS_LIGHT, deadline=deadline
        )
        if _consider(refined):
            return best[2], best[3], best[4]
        full = _refine_order_relocate(list(best[2]), edges, deadline=deadline)
        if _consider(full):
            return best[2], best[3], best[4]
        rng2 = random.Random(0xB0B0)
        for _ in range(8):
            if deadline is not None and time.monotonic() >= deadline:
                break
            s = list(best[2])
            if len(s) >= 4:
                i, j = rng2.randrange(len(s)), rng2.randrange(len(s))
                s[i], s[j] = s[j], s[i]
            s = _refine_order_relocate_limited(
                s, edges, rounds=_REFINE_ROUNDS_LIGHT, deadline=deadline
            )
            if _consider(s):
                return best[2], best[3], best[4]

    if best is not None:
        return best[2], best[3], best[4]

    # 兜底：强制双页（放不下的进外页），禁止「全内页带交叉」
    order = primary
    _ok, inner, outer = _two_page_partition(order, edges, force=True)
    return order, inner, outer


def _refine_order_relocate_limited(
    order: list[str],
    edges: list[tuple[str, str]],
    *,
    rounds: int,
    deadline: float | None = None,
) -> list[str]:
    """浅重插：与 _refine_order_relocate 相同，但轮数上限独立。"""
    order = list(order)
    n = len(order)
    if n <= 2:
        return order
    improved = True
    done = 0
    while improved and done < rounds:
        if deadline is not None and time.monotonic() >= deadline:
            break
        improved = False
        done += 1
        cur = _circular_crossings(order, edges)
        if cur == 0:
            return order
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                node = order.pop(i)
                order.insert(j, node)
                c = _circular_crossings(order, edges)
                if c < cur:
                    improved = True
                    break
                order.pop(j)
                order.insert(i, node)
            if improved:
                break
    return order


def _orient3(
    ax: float, ay: float, bx: float, by: float, cx: float, cy: float
) -> float:
    return (by - ay) * (cx - bx) - (bx - ax) * (cy - by)


def _segments_proper_cross(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    """开线段真交叉（端点相接不算）。"""
    o1 = _orient3(a[0], a[1], b[0], b[1], c[0], c[1])
    o2 = _orient3(a[0], a[1], b[0], b[1], d[0], d[1])
    o3 = _orient3(c[0], c[1], d[0], d[1], a[0], a[1])
    o4 = _orient3(c[0], c[1], d[0], d[1], b[0], b[1])
    return o1 * o2 < 0 and o3 * o4 < 0


def _straight_layout_crossings(
    pos: dict[str, tuple[float, float]], edges: list[tuple[str, str]]
) -> int:
    """实体中心连直线的交叉数（布局优选用）。"""
    segs: list[tuple[tuple[float, float], tuple[float, float], str, str]] = []
    for a, b in _undirected_pairs(edges):
        if a not in pos or b not in pos:
            continue
        segs.append((pos[a], pos[b], a, b))
    count = 0
    for i, (p, q, a, b) in enumerate(segs):
        for r, s, c, d in segs[i + 1 :]:
            if len({a, b, c, d}) < 4:
                continue
            if _segments_proper_cross(p, q, r, s):
                count += 1
    return count


def _degree_map(names: list[str], edges: list[tuple[str, str]]) -> dict[str, int]:
    deg = {n: 0 for n in names}
    for a, b in _undirected_pairs(edges):
        if a in deg:
            deg[a] += 1
        if b in deg:
            deg[b] += 1
    return deg


def _circle_positions(
    order: list[str], cx: float, cy: float, ring_r: float
) -> dict[str, tuple[float, float]]:
    n = len(order)
    pos: dict[str, tuple[float, float]] = {}
    if n == 0:
        return pos
    if n == 1:
        pos[order[0]] = (cx, cy)
        return pos
    for i, name in enumerate(order):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        pos[name] = (cx + ring_r * math.cos(ang), cy + ring_r * math.sin(ang))
    return pos


def _try_hub_layout(
    names: list[str],
    edges: list[tuple[str, str]],
    cx: float,
    cy: float,
    ring_r: float,
    *,
    deadline: float | None = None,
) -> tuple[list[str], dict[str, tuple[float, float]]] | None:
    """尝试 1 个内点 + 其余环排，全直线且几何零交叉（你拖拽能修好的那种）。"""
    if len(names) < 4:
        return None
    deg = _degree_map(names, edges)
    # 度数高的优先；同度保持稳定顺序；只试前几名，避免每 hub 再跑一遍环序搜索
    hubs = sorted(names, key=lambda n: (-deg[n], n))[:_HUB_TRY_LIMIT]
    for hub in hubs:
        if deadline is not None and time.monotonic() >= deadline:
            break
        rest = [n for n in names if n != hub]
        rest_edges = [(a, b) for a, b in edges if a != hub and b != hub]
        rest_order = _order_minimize_crossings(rest, rest_edges, deadline=deadline)
        if _circular_crossings(rest_order, rest_edges) > 0:
            # 环上仍交叉则该 hub 无望（外环本身画不平）
            continue
        pos = {hub: (cx, cy)}
        pos.update(_circle_positions(rest_order, cx, cy, ring_r))
        if _straight_layout_crossings(pos, edges) == 0:
            # order：内点放最后，便于调试；环序在前
            return rest_order + [hub], pos
    return None


def _partition_geometric_outer(
    pos: dict[str, tuple[float, float]],
    edges: list[tuple[str, str]],
) -> set[tuple[str, str]]:
    """ELK 坐标上贪心拆页：短弦优先直线；与已有直线真交叉则进外页。

    不移动实体、不围环；外页仅改画线路径。
    """
    scored: list[tuple[float, tuple[str, str]]] = []
    for a, b in _undirected_pairs(edges):
        if a not in pos or b not in pos or a == b:
            continue
        pa, pb = pos[a], pos[b]
        scored.append((math.hypot(pb[0] - pa[0], pb[1] - pa[1]), (a, b)))
    scored.sort(key=lambda t: (t[0], t[1][0], t[1][1]))
    inner: list[tuple[str, str]] = []
    outer: set[tuple[str, str]] = set()
    for _len, e in scored:
        ea, eb = pos[e[0]], pos[e[1]]
        if all(
            not _segments_proper_cross(ea, eb, pos[f[0]], pos[f[1]]) for f in inner
        ):
            inner.append(e)
        else:
            outer.add(e)
    return outer


def _layout_hull(
    pos: dict[str, tuple[float, float]],
) -> tuple[float, float, float]:
    """实体包围中心 + 外接半径（外页弧的虚拟圆心/半径，实体本身不落环）。"""
    if not pos:
        return 0.0, 0.0, 120.0
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    r = 0.0
    for x, y in pos.values():
        r = max(r, math.hypot(x - cx, y - cy))
    return cx, cy, max(r, 80.0)


def _layout_entities(
    names: list[str],
    edges: list[tuple[str, str]],
    cx: float,
    cy: float,
    ring_r: float,
    *,
    entity_hw: dict[str, float] | None = None,
) -> tuple[list[str], dict[str, tuple[float, float]], set[tuple[str, str]]]:
    """实体坐标：ELK layered 分层（禁全环）。

    返回的 outer 为几何上直线会交叉、须走外页弯线的无向对。
    cx/cy/ring_r 保留兼容旧调用；分层结果再平移，实体不围环。
    """
    _ = ring_r
    names = list(names)
    if not names:
        return [], {}, set()
    if len(names) == 1:
        return names, {names[0]: (cx, cy)}, set()

    hw = entity_hw or {}
    nodes = [
        {
            "id": n,
            "width": max(80.0, float(hw.get(n, 40.0)) * 2 + 8.0),
            "height": float(ENTITY_HH * 2 + 8.0),
        }
        for n in names
    ]
    # 无向联系：按名字定向喂 layered，避免环图无方向
    elk_edges = []
    for i, (a, b) in enumerate(_undirected_pairs(edges)):
        src, tgt = (a, b) if a <= b else (b, a)
        elk_edges.append({"id": f"e{i}", "sources": [src], "targets": [tgt]})

    try:
        laid = layout_graph(nodes, elk_edges)
    except ElkLayoutError:
        # 显式失败：禁止静默退回全环。保底网格以便单测不崩。
        pos = {
            n: (cx + (i % 4) * 180.0, cy + (i // 4) * 100.0) for i, n in enumerate(names)
        }
        order = list(names)
        return order, pos, _partition_geometric_outer(pos, edges)

    positions = laid.get("positions") or {}
    pos: dict[str, tuple[float, float]] = {}
    for n in names:
        box = positions.get(n)
        if not box:
            continue
        x, y, w, h = box
        pos[n] = (x + w / 2.0, y + h / 2.0)
    for i, n in enumerate(names):
        if n not in pos:
            pos[n] = (cx + (i % 4) * 180.0, cy + (i // 4) * 100.0)

    order = sorted(names, key=lambda n: (pos[n][0], pos[n][1], n))
    outer = _partition_geometric_outer(pos, edges)
    return order, pos, outer


def _grid_layout(
    names: list[str],
    edges: list[tuple[str, str]],
    entity_hw: dict[str, float],
) -> tuple[list[str], dict[str, tuple[float, float]]]:
    """蛇形栅格：按「度数优先 BFS」排序后按行列摆放，行列间距留出菱形与通道。

    样例 ER 的观感：实体成排，联系菱形落在行/列之间的空档里，连线走正交折线。
    """
    names = list(names)
    if not names:
        return [], {}
    deg: dict[str, int] = {nm: 0 for nm in names}
    adj: dict[str, list[str]] = {nm: [] for nm in names}
    for a, b in edges:
        if a in deg and b in deg:
            deg[a] += 1
            deg[b] += 1
            if b not in adj[a]:
                adj[a].append(b)
            if a not in adj[b]:
                adj[b].append(a)
    # BFS（起点取度数最大者），保证相关实体相邻
    def _bfs_order(st: str) -> list[str]:
        order: list[str] = [st]
        seen = {st}
        queue = [st]
        while queue:
            cur = queue.pop(0)
            for nxt in sorted(adj[cur], key=lambda nm: (-deg[nm], nm)):
                if nxt not in seen:
                    seen.add(nxt)
                    order.append(nxt)
                    queue.append(nxt)
        order += [nm for nm in sorted(names, key=lambda nm: (-deg[nm], nm)) if nm not in seen]
        return order

    hubs = sorted(names, key=lambda nm: (-deg[nm], nm))[:3]
    base = _bfs_order(hubs[0])
    n = len(base)
    ncol_cands = sorted(
        {
            max(2, int(math.ceil(math.sqrt(n * 1.2)))),
            max(2, int(math.ceil(math.sqrt(n * 1.2))) + 1),
            max(2, int(math.ceil(math.sqrt(n * 1.2))) - 1),
        }
    )

    def _build(order: list[str], ncols: int) -> dict[str, tuple[float, float]]:
        nrows = int(math.ceil(n / ncols))
        col_w: list[float] = []
        for j in range(ncols):
            width = max(
                (entity_hw.get(order[i], 40.0) for i in range(n) if i % ncols == j),
                default=40.0,
            )
            col_w.append(max(2 * width + 210.0, 272.0))
        row_h = float(2 * ENTITY_HH + 140)
        total_w = sum(col_w)
        pos: dict[str, tuple[float, float]] = {}
        for idx, nm in enumerate(order):
            r, c0 = divmod(idx, ncols)
            c = ncols - 1 - c0 if r % 2 else c0
            x = sum(col_w[:c]) + col_w[c] / 2.0 - total_w / 2.0
            pos[nm] = (x, r * row_h)
        _ = nrows
        return pos

    # 多起点 / 多列数 / 少量随机洗牌：取「直线交叉最少」的排布（相等再看跨度）
    orders: list[list[str]] = []
    for h in hubs:
        o = _bfs_order(h)
        orders.append(o)
        orders.append(list(reversed(o)))
    rnd = random.Random(20261125)
    for _ in range(8):
        o = list(base)
        rnd.shuffle(o)
        orders.append(o)

    best: tuple[int, float, list[str], dict[str, tuple[float, float]]] | None = None
    for o in orders:
        for nc in ncol_cands:
            pos = _build(o, nc)
            cr = _straight_layout_crossings(pos, edges)
            span = 0.0
            for a, b in _undirected_pairs(edges):
                if a in pos and b in pos:
                    span += math.hypot(pos[b][0] - pos[a][0], pos[b][1] - pos[a][1])
            key = (cr, round(span / max(1, len(edges)), 1))
            if best is None or key < (best[0], best[1]):
                best = (cr, key[1], o, pos)
    if best is None:
        return base, _build(base, ncol_cands[0])
    return best[2], best[3]


def _pair_offset(lp: tuple[float, float], rp: tuple[float, float], index: int, total: int) -> tuple[float, float]:
    """同对多联系时，菱形沿弦垂线错开。"""
    if total <= 1:
        return 0.0, 0.0
    dx, dy = rp[0] - lp[0], rp[1] - lp[1]
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    mid = (total - 1) / 2
    dist = (index - mid) * 36.0
    return nx * dist, ny * dist


def _ang_norm(a: float) -> float:
    while a <= -math.pi:
        a += 2 * math.pi
    while a > math.pi:
        a -= 2 * math.pi
    return a


# —— 正交（Manhattan）路由：对齐样例 ER，连线走折线、不穿实体框 ——

_BOX_CLEAR = 12.0  # 连线与实体框的最小净距


def _seg_cross_xy(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> bool:
    """两段（各自轴对齐或任意）在内部相交；共享端点不算。"""
    p, q = (a[0], a[1]), (a[2], a[3])
    r, s = (b[0], b[1]), (b[2], b[3])
    if p == r or p == s or q == r or q == s:
        return False

    def orient(o, u, v) -> float:
        return (u[1] - o[1]) * (v[0] - u[0]) - (u[0] - o[0]) * (v[1] - u[1])

    d1 = orient(p, q, r)
    d2 = orient(p, q, s)
    d3 = orient(r, s, p)
    d4 = orient(r, s, q)
    return d1 * d2 < 0 and d3 * d4 < 0


def _seg_hits_boxes(
    p: tuple[float, float],
    q: tuple[float, float],
    boxes: list[tuple[str, float, float, float, float]],
    skip: set[str],
) -> bool:
    """线段是否穿过实体框（含净距）。boxes: (name, cx, cy, hw, hh)。"""
    x1, y1 = p
    x2, y2 = q
    for nm, cx, cy, hw, hh in boxes:
        if nm in skip:
            continue
        left, right = cx - hw - _BOX_CLEAR, cx + hw + _BOX_CLEAR
        top, bot = cy - hh - _BOX_CLEAR, cy + hh + _BOX_CLEAR
        if abs(y1 - y2) <= 0.5:  # 水平段
            if top < y1 < bot and max(x1, x2) > left and min(x1, x2) < right:
                return True
        elif abs(x1 - x2) <= 0.5:  # 垂直段
            if left < x1 < right and max(y1, y2) > top and min(y1, y2) < bot:
                return True
        else:  # 斜段：按包围盒粗判
            if not (
                max(x1, x2) <= left
                or min(x1, x2) >= right
                or max(y1, y2) <= top
                or min(y1, y2) >= bot
            ):
                return True
    return False


def _free_channels(
    positions: dict[str, tuple[float, float]],
    hw: dict[str, float],
    *,
    axis: str,
) -> list[float]:
    """布局空档中线：把所有实体在某轴上的占位合并后，取每段空隙的中点。

    连线只要落在这些通道上，就天然不会穿过实体框。
    """
    if not positions:
        return []
    if axis == "x":
        ivs = sorted(
            (x - hw.get(nm, 40.0) - 10.0, x + hw.get(nm, 40.0) + 10.0)
            for nm, (x, _y) in positions.items()
        )
    else:
        ivs = sorted(
            (y - ENTITY_HH - 10.0, y + ENTITY_HH + 10.0)
            for _x, y in positions.values()
        )
    merged: list[list[float]] = []
    for lo, hi in ivs:
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    chans: list[float] = [(merged[0][0] - 46.0), (merged[-1][1] + 46.0)]
    for i in range(len(merged) - 1):
        lo, hi = merged[i][1], merged[i + 1][0]
        if hi - lo >= 24.0:
            chans.append((lo + hi) / 2)
    return chans


def _diamond_free(
    cx: float,
    cy: float,
    dw: float,
    dh: float,
    placed: list[tuple[float, float, float]],
    boxes: list[tuple[str, float, float, float, float]] | None = None,
    pad: float = 10.0,
) -> bool:
    """菱形与已放菱形、实体框都要留净距（避免「菱形压框/贴框」）。"""
    for px, py, pw in placed:
        if abs(cx - px) < dw + pw + 8 and abs(cy - py) < 2 * dh + 8:
            return False
    for _nm, ex, ey, ehw, ehh in boxes or []:
        if abs(cx - ex) < dw + ehw + pad and abs(cy - ey) < dh + ehh + pad:
            return False
    return True


def _route_ortho(
    lp: tuple[float, float],
    rp: tuple[float, float],
    hw1: float,
    hw2: float,
    boxes: list[tuple[str, float, float, float, float]],
    vchans: list[float],
    hchans: list[float],
    *,
    left_name: str,
    right_name: str,
    dw: float,
    dh: float,
    fan: float = 0.0,
    placed: list[tuple[float, float, float]] | None = None,
    placed_segs: list[tuple[float, float, float, float]] | None = None,
) -> dict[str, object] | None:
    """两实体间的正交折线（菱形落在中段）。

    先试短折线（同行直连 / 竖空档 / 横空档）；都会压实体框时改走
    「横空档 → 竖空档 → 横空档」的绕行——空档本身不含实体，天然不压框。
    placed 为已放菱形，用于错开避免叠加。
    """
    ax, ay = lp
    bx, by = rp
    skip = {left_name, right_name}
    placed = placed or []
    placed_segs = placed_segs or []

    def _chain_hits(chain: list[tuple[float, float]]) -> int:
        return sum(
            1
            for i in range(len(chain) - 1)
            if _seg_hits_boxes(chain[i], chain[i + 1], boxes, skip)
        )

    def _seg_cross(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float], s: tuple[float, float]) -> bool:
        """轴对齐段交叉（一横一竖），端点相接不算。"""
        if abs(p[1] - q[1]) <= 0.5 and abs(r[0] - s[0]) <= 0.5:
            hy, vx = p[1], r[0]
            hx1, hx2 = min(p[0], q[0]), max(p[0], q[0])
            vy1, vy2 = min(r[1], s[1]), max(r[1], s[1])
        elif abs(p[0] - q[0]) <= 0.5 and abs(r[1] - s[1]) <= 0.5:
            vx, hy = p[0], r[1]
            vy1, vy2 = min(p[1], q[1]), max(p[1], q[1])
            hx1, hx2 = min(r[0], s[0]), max(r[0], s[0])
        else:
            return False
        if not (hx1 + 1.0 < vx < hx2 - 1.0):
            return False
        return vy1 + 1.0 < hy < vy2 - 1.0

    def _chain_cross(chain: list[tuple[float, float]]) -> int:
        cnt = 0
        for i in range(len(chain) - 1):
            for seg in placed_segs:
                if _seg_cross(chain[i], chain[i + 1], (seg[0], seg[1]), (seg[2], seg[3])):
                    cnt += 1
        return cnt

    cands: list[tuple[float, int, dict[str, object]]] = []

    def _add(left: list[tuple[float, float]], right: list[tuple[float, float]], extra: dict[str, object]) -> None:
        hits = _chain_hits(left) + _chain_hits(right)
        seg_len = sum(
            math.hypot(left[i + 1][0] - left[i][0], left[i + 1][1] - left[i][1])
            for i in range(len(left) - 1)
        ) + sum(
            math.hypot(right[i + 1][0] - right[i][0], right[i + 1][1] - right[i][1])
            for i in range(len(right) - 1)
        )
        route: dict[str, object] = {"left": left, "right": right}
        route.update(extra)
        cross = _chain_cross(left) + _chain_cross(right)
        # 菱形撞已放菱形/实体只当软惩罚：宁可贴近，也不让整条线去交叉
        dm0 = route.get("diamond")
        collide = 0.0
        if isinstance(dm0, tuple) and not _diamond_free(dm0[0], dm0[1], dw, dh, placed, boxes):
            collide = 70.0
        cands.append((hits * 20.0 + cross * 60.0 + seg_len * 0.02 + collide, hits, route))

    # A. 同一行 → 直横线
    if abs(by - ay) <= 6.0 and abs(bx - ax) > hw1 + hw2 + 2 * dw + 24:
        y = ay + max(-(ENTITY_HH - 8.0), min(ENTITY_HH - 8.0, fan * 26.0))
        mx = (ax + bx) / 2
        p1 = (ax + hw1, y) if bx > ax else (ax - hw1, y)
        p2 = (bx - hw2, y) if bx > ax else (bx + hw2, y)
        # 直线整段是否压框（菱形两段合起来判定）
        straight_hit = 1 if _seg_hits_boxes(p1, p2, boxes, skip) else 0
        route_a: dict[str, object] = {
            "left": [p1],
            "right": [p2],
            "diamond": (mx, y),
            "axis": "h",
            "chan": y,
            "span": (min(ax, bx), max(ax, bx)),
        }
        cands.append((straight_hit * 20.0 + abs(bx - ax) * 0.02, straight_hit, route_a))
    # B. 竖空档折线：A→通道→B
    if abs(by - ay) >= 2 * dh + 16:
        for c in vchans:
            p1 = (ax + hw1, ay) if c > ax else (ax - hw1, ay)
            p2 = (bx - hw2, by) if c < bx else (bx + hw2, by)
            _add(
                [p1, (c, ay)],
                [(c, by), p2],
                {"diamond": (c, (ay + by) / 2), "axis": "v", "chan": c, "span": (min(ay, by), max(ay, by))},
            )
    # C. 横空档折线：A→通道→B
    if abs(bx - ax) >= 2 * dw + 16:
        for y in hchans:
            p1 = (ax, ay + ENTITY_HH) if y > ay else (ax, ay - ENTITY_HH)
            p2 = (bx, by - ENTITY_HH) if y < by else (bx, by + ENTITY_HH)
            _add(
                [p1, (ax, y)],
                [(bx, y), p2],
                {"diamond": ((ax + bx) / 2, y), "axis": "h", "chan": y, "span": (min(ax, bx), max(ax, bx))},
            )

    # E. 竖出竖入：同源多条走同一竖脊，再各自在独立横空档分支（星形枢纽零交叉）
    for y in hchans:
        if y > ay + ENTITY_HH and y > by + ENTITY_HH:
            sy = 1.0
        elif y < ay - ENTITY_HH and y < by - ENTITY_HH:
            sy = -1.0
        else:
            continue
        if abs(bx - ax) < 2 * dw + 16:
            continue
        p1 = (ax, ay + ENTITY_HH * sy)
        p2 = (bx, by + ENTITY_HH * sy)
        _add(
            [p1, (ax, y)],
            [(bx, y), p2],
            {"diamond": ((ax + bx) / 2, y), "axis": "h", "chan": y, "span": (min(ax, bx), max(ax, bx))},
        )

    # F. 外侧母线：绕到全部实体上方/下方走长横线，长距离关系不再穿过中部
    if boxes:
        top_y = min(y - hh for _nm, _x, y, _hw, hh in boxes) - 36.0
        bot_y = max(y + hh for _nm, _x, y, _hw, hh in boxes) + 36.0
        for outer_y in (top_y, bot_y):
            sy1 = -1.0 if outer_y < ay else 1.0
            sy2 = -1.0 if outer_y < by else 1.0
            p1 = (ax, ay + ENTITY_HH * sy1)
            p2 = (bx, by + ENTITY_HH * sy2)
            mx = (ax + bx) / 2
            _add(
                [p1, (ax, outer_y), (mx, outer_y)],
                [(mx, outer_y), (bx, outer_y), p2],
                {
                    "diamond": (mx, outer_y),
                    "axis": "h",
                    "chan": outer_y,
                    "span": (min(ax, bx), max(ax, bx)),
                },
            )

    # G. 外侧竖母线：绕到全部实体左侧/右侧走长竖线，同 F 的竖向版本
    if boxes:
        left_x = min(x - hw for _nm, x, _y, hw, _hh in boxes) - 44.0
        right_x = max(x + hw for _nm, x, _y, hw, _hh in boxes) + 44.0
        for outer_x in (left_x, right_x):
            sx1 = -1.0 if outer_x < ax else 1.0
            sx2 = -1.0 if outer_x < bx else 1.0
            p1 = (ax + hw1 * sx1, ay)
            p2 = (bx + hw2 * sx2, by)
            my2 = (ay + by) / 2
            _add(
                [p1, (outer_x, ay), (outer_x, my2)],
                [(outer_x, my2), (outer_x, by), p2],
                {
                    "diamond": (outer_x, my2),
                    "axis": "v",
                    "chan": outer_x,
                    "span": (min(ay, by), max(ay, by)),
                },
            )

    # F2. 外侧母线 + 空档下车：绕到外侧长横线，再从最近空档竖下、横入目标（目标列有别的框时用）
    if boxes and vchans:
        top_y2 = min(y - hh for _nm, _x, y, _hw, hh in boxes) - 36.0
        bot_y2 = max(y + hh for _nm, _x, y, _hw, hh in boxes) + 36.0
        for outer_y in (top_y2, bot_y2):
            sy1 = -1.0 if outer_y < ay else 1.0
            sy2 = -1.0 if outer_y < by else 1.0
            for c in vchans:
                if abs(c - bx) < hw2 + 12:
                    continue
                p1 = (ax, ay + ENTITY_HH * sy1)
                end_y = by - ENTITY_HH if sy2 < 0 else by + ENTITY_HH
                my = (outer_y + end_y) / 2
                _add(
                    [p1, (ax, outer_y), (c, outer_y), (c, my)],
                    [(c, my), (c, end_y), (bx, end_y)],
                    {
                        "diamond": (c, my),
                        "axis": "v",
                        "chan": c,
                        "span": (min(outer_y, end_y), max(outer_y, end_y)),
                    },
                )

    # D. 5 段绕行（横空档 + 竖空档 + 横空档）
    if vchans and hchans:
        above = [y for y in hchans if y < ay]
        below = [y for y in hchans if y > ay]
        pick_a = max(above) if above else (min(below) if below else None)
        above_b = [y for y in hchans if y < by]
        below_b = [y for y in hchans if y > by]
        pick_b = max(above_b) if above_b else (min(below_b) if below_b else None)
        if pick_a is not None and pick_b is not None:
            p1 = (ax, ay - ENTITY_HH) if pick_a < ay else (ax, ay + ENTITY_HH)
            p2 = (bx, by - ENTITY_HH) if pick_b < by else (bx, by + ENTITY_HH)
            best_c = min(vchans, key=lambda c: abs(c - (ax + bx) / 2))
            left: list[tuple[float, float]] = [p1, (ax, pick_a), (best_c, pick_a)]
            right: list[tuple[float, float]] = [(best_c, pick_b), (bx, pick_b), p2]
            if abs(pick_a - pick_b) >= 2 * dh + 16:
                _add(
                    left,
                    right,
                    {"diamond": (best_c, (pick_a + pick_b) / 2), "axis": "v", "chan": best_c, "span": (min(pick_a, pick_b), max(pick_a, pick_b))},
                )
            else:
                # 两端空档太近：菱形放到横空档段上
                left = [p1, (ax, pick_a)]
                right = [(bx, pick_a), p2]
                _add(
                    left,
                    right,
                    {"diamond": ((ax + bx) / 2, pick_a), "axis": "h", "chan": pick_a, "span": (min(ax, bx), max(ax, bx))},
                )

    cands.sort(key=lambda t: t[0])
    # 字典序择优：先要求不压实体框（max_hits=0），无解才放宽到 1、2
    for max_hits in (0, 1, 2):
        for _score, hits, route in cands:
            if hits > max_hits:
                continue
            dm = route["diamond"]  # type: ignore[assignment]
            axis = route.get("axis")
            chan = route.get("chan")
            span = route.get("span")
            if not _diamond_free(dm[0], dm[1], dw, dh, placed, boxes):
                fixed = None
                if isinstance(chan, (int, float)) and isinstance(span, tuple):
                    for k in (1, -1, 2, -2, 3, -3):
                        shift = k * (2 * dh + 12)
                        ny = dm[1] + shift if axis == "v" else dm[1]
                        nx = dm[0] if axis == "v" else dm[0] + shift
                        lo, hi = span
                        if axis == "v":
                            if not (lo + dh + 6 <= ny <= hi - dh - 6):
                                continue
                        else:
                            if not (lo + dw + 6 <= nx <= hi - dw - 6):
                                continue
                        if not _diamond_free(nx, ny, dw, dh, placed, boxes):
                            continue
                        fixed = (nx, ny)
                        break
                if fixed is None:
                    continue
                dm = fixed
            left_pts = list(route["left"])  # type: ignore[arg-type]
            right_pts = list(route["right"])  # type: ignore[arg-type]
            if axis == "v":
                up = dm[1] - dh if right_pts[0][1] > left_pts[-1][1] else dm[1] + dh
                dn = dm[1] + dh if right_pts[0][1] > left_pts[-1][1] else dm[1] - dh
                left_pts = [*left_pts, (dm[0], up)]
                right_pts = [(dm[0], dn), *right_pts]
            else:
                lx = dm[0] - dw if right_pts[0][0] > left_pts[-1][0] else dm[0] + dw
                rx = dm[0] + dw if right_pts[0][0] > left_pts[-1][0] else dm[0] - dw
                left_pts = [*left_pts, (lx, dm[1])]
                right_pts = [(rx, dm[1]), *right_pts]
            route["left"] = left_pts
            route["right"] = right_pts
            route["diamond"] = dm
            return route
    return None


def _outward_rect_port(
    ex: float,
    ey: float,
    ring_cx: float,
    ring_cy: float,
    hw: float,
    hh: float,
) -> tuple[tuple[float, float], float]:
    """实体朝环外的矩形接驳点 + 方位角（沿圆心→实体射线）。"""
    ang = math.atan2(ey - ring_cy, ex - ring_cx)
    far = (ex + math.cos(ang) * 1000.0, ey + math.sin(ang) * 1000.0)
    return _rect_edge(ex, ey, far[0], far[1], hw, hh), ang


def _outer_arc_polyline(
    lp: tuple[float, float],
    rp: tuple[float, float],
    cx: float,
    cy: float,
    ring_r: float,
    nest: int,
    *,
    inset1: float = 0.0,
    inset2: float = 0.0,
) -> tuple[list[tuple[float, float]], tuple[float, float]]:
    """环外弧折点 + 菱形位置。

    折点落在足够大的同心圆上，相邻圆心角 ≤ π/8，使弦也在实体环外侧。
    inset1/inset2：端点沿弧向内收一点，避免同实体更高 nest 的径向穿过本层弧端点。
    """
    a1 = math.atan2(lp[1] - cy, lp[0] - cx)
    a2 = math.atan2(rp[1] - cy, rp[0] - cx)
    da = _ang_norm(a2 - a1)
    if abs(da) > 1e-9:
        sgn = 1.0 if da > 0 else -1.0
        a1 = a1 + sgn * inset1
        a2 = a2 - sgn * inset2
        da = _ang_norm(a2 - a1)
    step = math.pi / 8
    n_steps = max(2, int(math.ceil(abs(da) / step)))
    half = abs(da) / n_steps / 2.0
    cos_h = math.cos(half) if half < math.pi / 2 else 0.2
    r_out = (ring_r + 44.0) / max(cos_h, 0.35) + 18.0 + nest * _OUTER_NEST_GAP

    arc: list[tuple[float, float]] = []
    for i in range(n_steps + 1):
        t = i / n_steps
        a = a1 + da * t
        arc.append((cx + r_out * math.cos(a), cy + r_out * math.sin(a)))
    mid_a = a1 + da / 2.0
    # 菱形略外于本层弧；层距 _OUTER_NEST_GAP 须大于此外伸，避免穿邻层
    diamond = (
        cx + (r_out + 18.0) * math.cos(mid_a),
        cy + (r_out + 18.0) * math.sin(mid_a),
    )
    return arc, diamond


def render_er_svg(
    model: dict,
    title: str = "E-R",
    *,
    mode: str = "total",
    entity: str | None = None,
) -> str:
    """陈氏 E-R 线框图。

    mode=total：概念 E-R（实体 + 联系 + 基数，不含属性；中间表已塌成 N:M）。
    mode=part：实体属性图（单个概念实体 + 自身属性，无外键、无联系）。
    图内不放标题/图例（图注写 Word）。
    """
    _ = title
    mode = (mode or "total").strip().lower()
    if mode not in ("total", "part"):
        mode = "total"

    tables = list(model.get("tables") or [])
    relations = list(model.get("relations") or [])
    if not tables:
        return _svg_wrap(480, 200, '<text x="24" y="100" font-size="14">无表结构</text>')

    show_attrs = mode == "part"
    if mode == "part":
        # 分图默认落到第一个概念实体（跳过中间表与角色拆分逻辑实体）
        conceptual = [
            str(t.get("name") or "")
            for t in tables
            if isinstance(t, dict)
            and not t.get("assoc_link")
            and not t.get("role_of")
            and t.get("name")
        ]
        if not conceptual:
            conceptual = [
                str(t.get("name") or "")
                for t in tables
                if isinstance(t, dict) and t.get("name") and not t.get("assoc_link")
            ]
        ent_name = (entity or "").strip() or (conceptual[0] if conceptual else "")
        tables = [t for t in tables if t.get("name") == ent_name]
        if not tables:
            return _svg_wrap(480, 200, '<text x="24" y="100" font-size="14">未找到该实体</text>')
        if tables[0].get("assoc_link"):
            return _svg_wrap(
                480,
                200,
                '<text x="24" y="100" font-size="14">中间表不绘制实体属性图</text>',
            )
        relations = []
    else:
        # 总图：排除 M:N 中间表矩形；去掉无联系的悬空实体
        tables = [t for t in tables if isinstance(t, dict) and not t.get("assoc_link")]
        linked: set[str] = set()
        for r in relations:
            if isinstance(r, dict):
                linked.add(str(r.get("left") or ""))
                linked.add(str(r.get("right") or ""))
        linked.discard("")
        if linked:
            tables = [t for t in tables if t.get("name") in linked]
            kept = {t.get("name") for t in tables}
            relations = [
                r
                for r in relations
                if isinstance(r, dict)
                and r.get("left") in kept
                and r.get("right") in kept
            ]

    names = [t["name"] for t in tables]
    edges = [(r["left"], r["right"]) for r in relations]
    by_name = {t["name"]: t for t in tables}

    entity_hw: dict[str, float] = {
        t["name"]: _entity_hw(t.get("label") or t["name"]) for t in tables
    }

    def _attrs_for(t: dict) -> list:
        if not show_attrs:
            return []
        # 实体属性图：自身属性（去外键）；优先 own_columns
        own = t.get("own_columns")
        if isinstance(own, list) and own:
            return list(own)
        return [c for c in (t.get("columns") or []) if isinstance(c, dict) and not c.get("fk")]

    clouds = {
        t["name"]: (
            _attr_cloud_radius(_attrs_for(t), entity_hw[t["name"]])
            if show_attrs
            else max(48.0, entity_hw[t["name"]] + 24)
        )
        for t in tables
    }
    max_cloud = max(clouds.values()) if clouds else 80
    n = len(names)

    # 总图：ELK 分层 + 几何外页；分图单实体仍居中
    outer_pairs: set[tuple[str, str]] = set()
    if show_attrs or n <= 1:
        order = list(names)
        entity_pos = {names[0]: (0.0, 0.0)} if names else {}
    else:
        # 总图：蛇形栅格（样例观感：实体成排、菱形落在行列空档）
        order, entity_pos = _grid_layout(names, edges, entity_hw)
        outer_pairs = set()

    hull_cx, hull_cy, hull_r = _layout_hull(entity_pos)

    # 画布：实体包围盒 + 属性云（总图走正交折线，不再为外页弧预留大片空白）
    pad = 72.0 if show_attrs else _ELK_PAD
    if entity_pos:
        xs = [p[0] for p in entity_pos.values()]
        ys = [p[1] for p in entity_pos.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
    else:
        min_x = max_x = min_y = max_y = 0.0
    margin = max_cloud + 48.0
    shift_x = pad + margin - min_x
    shift_y = pad + margin - min_y
    entity_pos = {k: (x + shift_x, y + shift_y) for k, (x, y) in entity_pos.items()}
    cx = hull_cx + shift_x
    cy = hull_cy + shift_y
    ring_r = hull_r + 28.0
    w = int(max_x - min_x + 2 * (pad + margin))
    h = int(max_y - min_y + 2 * (pad + margin))
    w, h = max(w, 360), max(h, 280)
    ordered_tables = [by_name[nm] for nm in order if nm in by_name]

    # 同对联系计数，便于垂线错开
    pair_keys: list[tuple[str, str]] = []
    for r in relations:
        a, b = r["left"], r["right"]
        pair_keys.append((a, b) if a <= b else (b, a))
    pair_totals: dict[tuple[str, str], int] = {}
    for pk in pair_keys:
        pair_totals[pk] = pair_totals.get(pk, 0) + 1
    pair_seen: dict[tuple[str, str], int] = {}

    def _span_of(pk: tuple[str, str]) -> int:
        if pk[0] not in entity_pos or pk[1] not in entity_pos:
            return 0
        # 外页嵌套：按弦长粗排，短的靠内层
        p0, p1 = entity_pos[pk[0]], entity_pos[pk[1]]
        return int(math.hypot(p1[0] - p0[0], p1[1] - p0[1]))

    outer_sorted = sorted(outer_pairs, key=lambda e: (_span_of(e), e))
    outer_nest: dict[tuple[str, str], int] = {e: i for i, e in enumerate(outer_sorted)}
    outer_fan: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for e in outer_sorted:
        if e not in outer_fan[e[0]]:
            outer_fan[e[0]].append(e)
        if e not in outer_fan[e[1]]:
            outer_fan[e[1]].append(e)

    def _need_inset(ent: str, pk: tuple[str, str]) -> bool:
        group = outer_fan.get(ent) or []
        if len(group) <= 1:
            return False
        my_nest = outer_nest.get(pk, 0)
        return any(outer_nest.get(o, 0) > my_nest for o in group if o != pk)

    edge_parts: list[str] = []
    node_parts: list[str] = []
    card_parts: list[str] = []
    records: list[dict[str, object]] = []
    # 正交路由避让用：全部实体框（含净距）+ 布局空档通道
    boxes: list[tuple[str, float, float, float, float]] = []
    vchans: list[float] = []
    hchans: list[float] = []
    placed_diamonds: list[tuple[float, float, float]] = []
    placed_segs: list[tuple[float, float, float, float]] = []
    card_boxes: list[tuple[float, float, float, float]] = []

    def _rec_segs(rec: dict[str, object]) -> list[tuple[float, float, float, float]]:
        if rec["kind"] != "ortho":
            return [
                (rec["e1"][0], rec["e1"][1], rec["d1"][0], rec["d1"][1]),  # type: ignore[index]
                (rec["d2"][0], rec["d2"][1], rec["e2"][0], rec["e2"][1]),  # type: ignore[index]
            ]
        out: list[tuple[float, float, float, float]] = []
        for key in ("chain_l", "chain_r"):
            chn = rec[key]  # type: ignore[index]
            for k in range(len(chn) - 1):
                out.append((chn[k][0], chn[k][1], chn[k + 1][0], chn[k + 1][1]))
        return out

    def _xcount(recs: list[dict[str, object]]) -> int:
        segs = [(i, s) for i, rec in enumerate(recs) for s in _rec_segs(rec)]
        n = 0
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                if segs[i][0] == segs[j][0]:
                    continue
                if _seg_cross_xy(segs[i][1], segs[j][1]):
                    n += 1
        return n

    def _card_pos(
        a: tuple[float, float],
        b: tuple[float, float],
        t: float = 0.35,
        side: float = 1.0,
        dist: float = 12.0,
    ) -> tuple[float, float]:
        px = a[0] * (1 - t) + b[0] * t
        py = a[1] * (1 - t) + b[1] * t
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        return px - dy / L * dist * side, py + dx / L * dist * side

    def _card_clear(
        p: tuple[float, float],
        boxes_: list[tuple[str, float, float, float, float]],
        diamonds_: list[tuple[float, float, float]],
        cards_: list[tuple[float, float]],
    ) -> float:
        """1/n 标签的净距（px）：<0 表示已压住别的东西；标签之间留足行距。"""
        hw, hh = 6.5, 7.5
        worst = 1e9
        for nm, ex, ey, ehw, ehh in boxes_:
            gx = abs(p[0] - ex) - (ehw + hw + 4)
            gy = abs(p[1] - ey) - (ehh + hh + 4)
            worst = min(worst, max(gx, gy))
        for dx_, dy_, dhw in diamonds_:
            gx = abs(p[0] - dx_) - (dhw + hw + 4)
            gy = abs(p[1] - dy_) - (22 + hh + 4)
            worst = min(worst, max(gx, gy))
        for bx in cards_:
            gx = abs(p[0] - bx[0]) - (hw + 11.0)
            gy = abs(p[1] - bx[1]) - (hh + 13.0)
            worst = min(worst, max(gx, gy))
        return worst

    def _poly_card_pos(
        pts: list[tuple[float, float]],
        f_from_end: float,
        side: float,
        dist: float,
    ) -> tuple[float, float]:
        """沿整条折线找点：f_from_end=1 在菱形端、0 在实体端，再按垂线偏移 dist。"""
        if len(pts) < 2:
            return pts[-1]
        segs = [(pts[i], pts[i + 1], math.dist(pts[i], pts[i + 1])) for i in range(len(pts) - 1)]
        total = sum(s[2] for s in segs) or 1.0
        target = total * (1.0 - f_from_end)
        acc = 0.0
        for a, b, L in segs:
            if acc + L >= target or (a, b, L) is segs[-1]:
                r = ((target - acc) / L) if L else 0.0
                px, py = a[0] + (b[0] - a[0]) * r, a[1] + (b[1] - a[1]) * r
                dx, dy = b[0] - a[0], b[1] - a[1]
                L2 = math.hypot(dx, dy) or 1.0
                return px - dy / L2 * dist * side, py + dx / L2 * dist * side
            acc += L
        return pts[-1]

    def _place_card(
        pts: list[tuple[float, float]],
        boxes_: list[tuple[str, float, float, float, float]],
        diamonds_: list[tuple[float, float, float]],
        cards_: list[tuple[float, float]],
    ) -> tuple[float, float]:
        """沿整条折线挑净距最大的位置；优先靠菱形端，其次往中间挪开挤堆。"""
        best_p = _poly_card_pos(pts, 0.35, 1.0, 12.0)
        best_c = _card_clear(best_p, boxes_, diamonds_, cards_)
        for f in (0.95, 0.9, 0.85, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3):
            for dist in (9.0, 13.0, 18.0, 23.0, 28.0):
                for side in (1.0, -1.0):
                    p = _poly_card_pos(pts, f, side, dist)
                    c = _card_clear(p, boxes_, diamonds_, cards_)
                    if c >= 2.0:
                        cards_.append(p)
                        return p
                    if c > best_c:
                        best_c, best_p = c, p
        if best_c < 2.0:
            # 兜底：净距不足时放宽到更长偏移，只求不压
            for f in (0.95, 0.8, 0.65, 0.5, 0.35, 0.2):
                for dist in (34.0, 44.0, 56.0):
                    for side in (1.0, -1.0):
                        p = _poly_card_pos(pts, f, side, dist)
                        c = _card_clear(p, boxes_, diamonds_, cards_)
                        if c >= 2.0:
                            cards_.append(p)
                            return p
                        if c > best_c:
                            best_c, best_p = c, p
        cards_.append(best_p)
        return best_p

    def build(pos_map: dict[str, tuple[float, float]]) -> tuple[list[dict[str, object]], int]:
        """按给定实体坐标布一遍线，返回 (关系记录, 交叉数)。"""
        nonlocal boxes, vchans, hchans, placed_diamonds, placed_segs, card_boxes, records
        boxes = [(nm, x, y, entity_hw[nm], ENTITY_HH) for nm, (x, y) in pos_map.items()]
        vchans = _free_channels(pos_map, entity_hw, axis="x")
        hchans = _free_channels(pos_map, entity_hw, axis="y")
        placed_diamonds = []
        placed_segs = []
        card_boxes = []
        records = []

        # 联系：内页直线；外页绕布局包围弧（实体不落环）
        deg: dict[str, int] = {}
        for r0 in relations:
            deg[r0["left"]] = deg.get(r0["left"], 0) + 1
            deg[r0["right"]] = deg.get(r0["right"], 0) + 1
        # 先给枢纽（度数高）布线：枢纽腿占住空档后，低度联系的绕法自然避开
        order = sorted(
            range(len(relations)),
            key=lambda i: (-max(deg.get(relations[i]["left"], 0), deg.get(relations[i]["right"], 0)), i),
        )
        for ri in order:
            r = relations[ri]
            lp = pos_map.get(r["left"])
            rp = pos_map.get(r["right"])
            if not lp or not rp:
                continue
            left_id = f"entity:{r['left']}"
            right_id = f"entity:{r['right']}"
            rel_id = f"rel:{ri}"
            pk = pair_keys[ri]
            pi = pair_seen.get(pk, 0)
            pair_seen[pk] = pi + 1
            use_outer = pk in outer_pairs

            hw1 = entity_hw.get(r["left"], 40)
            hw2 = entity_hw.get(r["right"], 40)
            rel_label = r.get("label") or r["name"]
            dw = max(36.0, _text_w(rel_label, 12) / 2 + 16)
            dh = 22.0

            fan = pi - (pair_totals[pk] - 1) / 2.0
            route = _route_ortho(
                lp,
                rp,
                hw1,
                hw2,
                boxes,
                vchans,
                hchans,
                left_name=r["left"],
                right_name=r["right"],
                dw=dw,
                dh=dh,
                fan=fan,
                placed=placed_diamonds,
                placed_segs=placed_segs,
            )
            if route:
                chain_l = [(float(p[0]), float(p[1])) for p in route["left"]]  # type: ignore[index]
                chain_r = [(float(p[0]), float(p[1])) for p in route["right"]]  # type: ignore[index]
                for chn in (chain_l, chain_r):
                    for k in range(len(chn) - 1):
                        placed_segs.append((chn[k][0], chn[k][1], chn[k + 1][0], chn[k + 1][1]))
                mx, my = float(route["diamond"][0]), float(route["diamond"][1])  # type: ignore[index]
                placed_diamonds.append((mx, my, dw))
                records.append(
                    {
                        "kind": "ortho",
                        "ri": ri, "lp": lp, "rp": rp, "hw1": hw1, "hw2": hw2,
                        "dw": dw, "dh": dh, "fan": fan, "label": rel_label,
                        "left_id": left_id, "right_id": right_id, "rel_id": rel_id,
                        "card_left": r["card_left"], "card_right": r["card_right"],
                        "chain_l": chain_l, "chain_r": chain_r, "mx": mx, "my": my,
                        "anchor_l": (chain_l[0], chain_l[1]),
                        "anchor_r": (chain_r[-1], chain_r[-2]),
                    }
                )
            else:
                ox, oy = _pair_offset(lp, rp, pi, pair_totals[pk])
                mx = (lp[0] + rp[0]) / 2 + ox
                my = (lp[1] + rp[1]) / 2 + oy
                # 兜底直线也要避开已放菱形：沿弦换位，取第一个不压的
                if not _diamond_free(mx, my, dw, dh, placed_diamonds, boxes):
                    for _t in (0.36, 0.64, 0.24, 0.76, 0.15, 0.85):
                        cand_x = lp[0] * (1 - _t) + rp[0] * _t + ox
                        cand_y = lp[1] * (1 - _t) + rp[1] * _t + oy
                        if _diamond_free(cand_x, cand_y, dw, dh, placed_diamonds, boxes):
                            mx, my = cand_x, cand_y
                            break
                placed_diamonds.append((mx, my, dw))
                e1 = _rect_edge(lp[0], lp[1], mx, my, hw1, ENTITY_HH)
                d1 = _diamond_edge(mx, my, dw, dh, lp[0], lp[1])
                d2 = _diamond_edge(mx, my, dw, dh, rp[0], rp[1])
                e2 = _rect_edge(rp[0], rp[1], mx, my, hw2, ENTITY_HH)
                records.append(
                    {
                        "kind": "straight",
                        "ri": ri, "lp": lp, "rp": rp, "hw1": hw1, "hw2": hw2,
                        "dw": dw, "dh": dh, "fan": fan, "label": rel_label,
                        "left_id": left_id, "right_id": right_id, "rel_id": rel_id,
                        "card_left": r["card_left"], "card_right": r["card_right"],
                        "e1": e1, "d1": d1, "d2": d2, "e2": e2, "mx": mx, "my": my,
                        "anchor_l": (e1, d1), "anchor_r": (e2, d2),
                    }
                )

        # 全局复检：逐条重选折线，只接受交叉数下降的重选（顺序无关）
        best_x = _xcount(records)
        for _round in range(8):
            if best_x == 0:
                break
            improved = False
            for idx, rec in enumerate(records):
                if rec["kind"] != "ortho":
                    continue
                others_d = [
                    (r2["mx"], r2["my"], r2["dw"])  # type: ignore[index]
                    for j, r2 in enumerate(records)
                    if j != idx
                ]
                others_s = [s for j, r2 in enumerate(records) if j != idx for s in _rec_segs(r2)]
                new_route = _route_ortho(
                    rec["lp"],  # type: ignore[arg-type]
                    rec["rp"],  # type: ignore[arg-type]
                    rec["hw1"],  # type: ignore[arg-type]
                    rec["hw2"],  # type: ignore[arg-type]
                    boxes,
                    vchans,
                    hchans,
                    left_name=str(rec["left_id"])[7:],
                    right_name=str(rec["right_id"])[7:],
                    dw=rec["dw"],  # type: ignore[arg-type]
                    dh=rec["dh"],  # type: ignore[arg-type]
                    fan=rec["fan"],  # type: ignore[arg-type]
                    placed=others_d,
                    placed_segs=others_s,
                )
                if not new_route:
                    continue
                cand_l = [(float(p[0]), float(p[1])) for p in new_route["left"]]  # type: ignore[index]
                cand_r = [(float(p[0]), float(p[1])) for p in new_route["right"]]  # type: ignore[index]
                if cand_l == rec["chain_l"] and cand_r == rec["chain_r"]:
                    continue
                trial = [dict(r) for r in records]
                trial[idx]["chain_l"] = cand_l
                trial[idx]["chain_r"] = cand_r
                trial[idx]["mx"] = float(new_route["diamond"][0])  # type: ignore[index]
                trial[idx]["my"] = float(new_route["diamond"][1])  # type: ignore[index]
                got = _xcount(trial)
                if got < best_x:
                    records, best_x, improved = trial, got, True
            if not improved:
                break

        return records, best_x

    # 间距自适应：同样排布按不同留白缩放，取布线后交叉最少的那个（通用，不针对单域）
    cx0 = sum(x for x, _y in entity_pos.values()) / max(1, len(entity_pos))
    cy0 = sum(y for _x, y in entity_pos.values()) / max(1, len(entity_pos))
    _scale_cands: list[tuple[int, dict[str, tuple[float, float]]]] = []
    for sx, sy in ((1.0, 1.0), (1.18, 1.0), (1.0, 1.18), (1.18, 1.18), (1.35, 1.24), (1.5, 1.0)):
        cand_pos = {
            nm: (cx0 + (x - cx0) * sx, cy0 + (y - cy0) * sy) for nm, (x, y) in entity_pos.items()
        }
        _scale_cands.append((build(cand_pos)[1], cand_pos))
    entity_pos = min(_scale_cands, key=lambda t: t[0])[1]
    records, best_x = build(entity_pos)

    for _round in range(80):
        if best_x == 0:
            break
        segs = [(i, s) for i, rec in enumerate(records) for s in _rec_segs(rec)]
        hot: list[tuple[str, str]] = []
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                if segs[i][0] == segs[j][0]:
                    continue
                if not _seg_cross_xy(segs[i][1], segs[j][1]):
                    continue
                for ra, rb in ((records[segs[i][0]], records[segs[j][0]]),):
                    for ka in ("left_id", "right_id"):
                        for kb in ("left_id", "right_id"):
                            a, b = str(ra[ka])[7:], str(rb[kb])[7:]
                            if a != b and (a, b) not in hot and (b, a) not in hot:
                                hot.append((a, b))
        improved = False
        for a, b in hot[:40]:
            if a not in entity_pos or b not in entity_pos:
                continue
            cand = dict(entity_pos)
            cand[a], cand[b] = entity_pos[b], entity_pos[a]
            base_records = records
            new_records, got = build(cand)
            if got < best_x:
                entity_pos[a], entity_pos[b] = entity_pos[b], entity_pos[a]
                best_x = got
                improved = True
            else:
                records = base_records
        if not improved:
            break

    records, best_x = build(entity_pos)

    # 1/n 标签最后统一落位：此时全部菱形已就位，避开菱形、实体框与其他标签
    card_boxes = []
    for rec in records:
        if rec["kind"] == "ortho":
            poly_l = [(float(p[0]), float(p[1])) for p in rec["chain_l"]]  # type: ignore[index]
            poly_r = [(float(p[0]), float(p[1])) for p in reversed(rec["chain_r"])]  # type: ignore[arg-type]
        else:
            poly_l = [(float(rec["e1"][0]), float(rec["e1"][1])), (float(rec["d1"][0]), float(rec["d1"][1]))]  # type: ignore[index]
            poly_r = [(float(rec["e2"][0]), float(rec["e2"][1])), (float(rec["d2"][0]), float(rec["d2"][1]))]  # type: ignore[index]
        rec["c1"] = _place_card(poly_l, boxes, placed_diamonds, card_boxes)
        rec["c2"] = _place_card(poly_r, boxes, placed_diamonds, card_boxes)

    for rec in records:
        mx, my = float(rec["mx"]), float(rec["my"])
        dw, dh = float(rec["dw"]), float(rec["dh"])
        if rec["kind"] == "ortho":
            for chain, fid, tid in (
                (rec["chain_l"], rec["left_id"], rec["rel_id"]),
                (rec["chain_r"], rec["rel_id"], rec["right_id"]),
            ):
                for i in range(len(chain) - 1):
                    x1, y1 = chain[i]
                    x2, y2 = chain[i + 1]
                    edge_parts.append(
                        f'<line class="er-edge" data-from="{_esc(fid)}" data-to="{_esc(tid)}" '
                        f'data-route="ortho" '
                        f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                        f'stroke="#000" stroke-width="1" fill="none"/>'
                    )
        else:
            e1, d1, d2, e2 = rec["e1"], rec["d1"], rec["d2"], rec["e2"]
            edge_parts.append(
                f'<line class="er-edge" data-from="{_esc(rec["left_id"])}" data-to="{_esc(rec["rel_id"])}" '
                f'data-route="straight" '
                f'x1="{e1[0]:.1f}" y1="{e1[1]:.1f}" x2="{d1[0]:.1f}" y2="{d1[1]:.1f}" '
                f'stroke="#000" stroke-width="1" fill="none"/>'
            )
            edge_parts.append(
                f'<line class="er-edge" data-from="{_esc(rec["rel_id"])}" data-to="{_esc(rec["right_id"])}" '
                f'data-route="straight" '
                f'x1="{d2[0]:.1f}" y1="{d2[1]:.1f}" x2="{e2[0]:.1f}" y2="{e2[1]:.1f}" '
                f'stroke="#000" stroke-width="1" fill="none"/>'
            )

        diamond = (
            f"{mx:.1f},{my - dh:.1f} {mx + dw:.1f},{my:.1f} "
            f"{mx:.1f},{my + dh:.1f} {mx - dw:.1f},{my:.1f}"
        )
        node_parts.append(
            f'<g class="er-node" data-kind="rel" data-id="{_esc(rec["rel_id"])}" data-shape="diamond" '
            f'data-left="{_esc(rec["left_id"])}" data-right="{_esc(rec["right_id"])}" '
            f'data-cx="{mx:.1f}" data-cy="{my:.1f}" data-hw="{dw:.1f}" data-hh="{dh:.1f}">'
            f'<polygon points="{diamond}" fill="#fff" stroke="#000" stroke-width="1.2"/>'
            f'<text x="{mx:.1f}" y="{my + 4:.1f}" text-anchor="middle" '
            f'font-family="{FONT_CN}" font-size="12">{_esc(str(rec["label"]))}</text>'
            f"</g>"
        )
        c1, c2 = rec["c1"], rec["c2"]
        card_parts.append(
            f'<text class="er-card" data-from="{_esc(rec["left_id"])}" data-to="{_esc(rec["rel_id"])}" '
            f'x="{c1[0]:.1f}" y="{c1[1]:.1f}" text-anchor="middle" '
            f'font-family="{FONT_TECH}" font-size="12">{_esc(str(rec["card_left"]))}</text>'
        )
        card_parts.append(
            f'<text class="er-card" data-from="{_esc(rec["right_id"])}" data-to="{_esc(rec["rel_id"])}" '
            f'x="{c2[0]:.1f}" y="{c2[1]:.1f}" text-anchor="middle" '
            f'font-family="{FONT_TECH}" font-size="12">{_esc(str(rec["card_right"]))}</text>'
        )

    # 实体 +（分图）属性
    for t in ordered_tables:
        name = t["name"]
        label = t.get("label") or name
        x, y = entity_pos[name]
        hw = entity_hw[name]
        ent_id = f"entity:{name}"
        node_parts.append(
            f'<g class="er-node" data-kind="entity" data-id="{_esc(ent_id)}" data-shape="rect" '
            f'data-cx="{x:.1f}" data-cy="{y:.1f}" data-hw="{hw:.1f}" data-hh="{ENTITY_HH:.1f}">'
            f'<rect x="{x - hw:.1f}" y="{y - ENTITY_HH:.1f}" '
            f'width="{hw * 2:.1f}" height="{ENTITY_HH * 2:.1f}" '
            f'fill="#fff" stroke="#000" stroke-width="1.5"/>'
            f'<text x="{x:.1f}" y="{y + 5:.1f}" text-anchor="middle" '
            f'font-family="{FONT_CN}" font-size="13" font-weight="600">'
            f"{_esc(label)}</text>"
            f"</g>"
        )

        attrs = _attrs_for(t)
        m = len(attrs)
        if m == 0:
            continue
        ar = clouds[name]
        base = math.atan2(y - cy, x - cx) if n > 1 else -math.pi / 2
        for ai, col in enumerate(attrs):
            ang = base + 2 * math.pi * ai / m
            ax = x + ar * math.cos(ang)
            ay = y + ar * math.sin(ang)
            alabel = col.get("label") or col["name"]
            rx = _attr_rx(alabel)
            attr_id = f"attr:{name}.{col['name']}"
            p0 = _rect_edge(x, y, ax, ay, hw, ENTITY_HH)
            p1 = _ellipse_edge(ax, ay, rx, ATTR_RH, x, y)
            edge_parts.append(
                f'<line class="er-edge" data-from="{_esc(ent_id)}" data-to="{_esc(attr_id)}" '
                f'x1="{p0[0]:.1f}" y1="{p0[1]:.1f}" x2="{p1[0]:.1f}" y2="{p1[1]:.1f}" '
                f'stroke="#000" stroke-width="0.8" fill="none"/>'
            )
            tw = min(rx * 1.7, _text_w(alabel, 10))
            deco = ""
            if col.get("pk"):
                deco = (
                    f'<line x1="{ax - tw / 2:.1f}" y1="{ay + 8:.1f}" '
                    f'x2="{ax + tw / 2:.1f}" y2="{ay + 8:.1f}" stroke="#000" stroke-width="1"/>'
                )
            # 实体属性图不含外键，不再画 FK 波浪线
            node_parts.append(
                f'<g class="er-node" data-kind="attr" data-id="{_esc(attr_id)}" '
                f'data-parent="{_esc(ent_id)}" data-shape="ellipse" '
                f'data-cx="{ax:.1f}" data-cy="{ay:.1f}" data-rx="{rx:.1f}" data-ry="{ATTR_RH:.1f}">'
                f'<ellipse cx="{ax:.1f}" cy="{ay:.1f}" rx="{rx:.1f}" ry="{ATTR_RH:.1f}" '
                f'fill="#fff" stroke="#000" stroke-width="1"/>'
                f'<text x="{ax:.1f}" y="{ay + 4:.1f}" text-anchor="middle" '
                f'font-family="{FONT_CN}" font-size="10">{_esc(alabel)}</text>'
                f"{deco}</g>"
            )

    # 画布兜底：把连线/菱形/基数标签也算进边界，外侧母线不能跑出画布
    bx_lo: list[float] = []
    bx_hi: list[float] = []
    by_lo: list[float] = []
    by_hi: list[float] = []
    for nm, (x, y) in entity_pos.items():
        hw = entity_hw.get(nm, 40.0)
        bx_lo.append(x - hw)
        bx_hi.append(x + hw)
        by_lo.append(y - ENTITY_HH)
        by_hi.append(y + ENTITY_HH)
    for rec in records:
        for key in ("chain_l", "chain_r"):
            chn = rec.get(key) or []
            for p in chn:  # type: ignore[union-attr]
                bx_lo.append(float(p[0]))
                bx_hi.append(float(p[0]))
                by_lo.append(float(p[1]))
                by_hi.append(float(p[1]))
        if rec.get("e1") is not None:
            for pt in (rec["e1"], rec["d1"], rec["d2"], rec["e2"]):  # type: ignore[union-attr]
                bx_lo.append(float(pt[0]))
                bx_hi.append(float(pt[0]))
                by_lo.append(float(pt[1]))
                by_hi.append(float(pt[1]))
        mx_, my_ = float(rec["mx"]), float(rec["my"])  # type: ignore[arg-type]
        dw_, dh_ = float(rec["dw"]), float(rec["dh"])  # type: ignore[arg-type]
        bx_lo.append(mx_ - dw_)
        bx_hi.append(mx_ + dw_)
        by_lo.append(my_ - dh_)
        by_hi.append(my_ + dh_)
        for ck in ("c1", "c2"):
            cp = rec[ck]  # type: ignore[index]
            bx_lo.append(float(cp[0]) - 9.0)
            bx_hi.append(float(cp[0]) + 9.0)
            by_lo.append(float(cp[1]) - 9.0)
            by_hi.append(float(cp[1]) + 9.0)
    if bx_lo:
        vx = min(0.0, min(bx_lo) - 10.0)
        vy = min(0.0, min(by_lo) - 10.0)
        vw = int(max(float(w), max(bx_hi) + 10.0) - vx)
        vh = int(max(float(h), max(by_hi) + 10.0) - vy)
    else:
        vx, vy, vw, vh = 0.0, 0.0, w, h

    parts = (
        ['<g class="er-edges">']
        + edge_parts
        + card_parts
        + ["</g>"]
        + ['<g class="er-nodes">']
        + node_parts
        + ["</g>"]
    )
    return _svg_wrap(vw, vh, "\n".join(parts), vx=vx, vy=vy)


def _svg_wrap(w: int, h: int, inner: str, *, vx: float = 0.0, vy: float = 0.0) -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="{vx:.1f} {vy:.1f} {w} {h}">\n'
        f'<rect class="er-paper" x="{vx:.1f}" y="{vy:.1f}" width="{w}" height="{h}" fill="#fff"/>\n'
        f"{inner}\n</svg>\n"
    )





