"""陈氏 E-R：零交叉布局 + SVG 渲染。"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from itertools import permutations

ENTITY_HH = 22
ATTR_RH = 14


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _text_w(s: str, px: float = 12.0) -> float:
    """粗估中西文混排宽度。"""
    w = 0.0
    for ch in s:
        w += px if ord(ch) > 127 else px * 0.55
    return w


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


def _refine_order_relocate(order: list[str], edges: list[tuple[str, str]]) -> list[str]:
    """顶点重插局部搜索，压低环上交叉。"""
    order = list(order)
    n = len(order)
    if n <= 2:
        return order
    improved = True
    rounds = 0
    while improved and rounds < 60:
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


def _order_minimize_crossings(names: list[str], edges: list[tuple[str, str]]) -> list[str]:
    """多起点 + 重插，尽量把环上交叉压到 0（可外平面时）。"""
    names = list(names)
    n = len(names)
    if n <= 2:
        return names
    seeds: list[list[str]] = [list(names), list(reversed(names))]
    for start in names:
        seeds.append(_dfs_order(names, edges, start))
    # 小图穷举旋转代表（固定首点）；n<=8 → 7! =5040
    if n <= 8:
        base = names[0]
        rest = names[1:]
        best_o = list(names)
        best = _circular_crossings(best_o, edges)
        if best == 0:
            return best_o
        for perm in permutations(rest):
            order = [base, *perm]
            c = _circular_crossings(order, edges)
            if c < best:
                best = c
                best_o = order
                if best == 0:
                    return best_o
        return best_o

    rng = random.Random(0xE12)
    for _ in range(48):
        s = list(names)
        rng.shuffle(s)
        seeds.append(s)

    best_o = list(names)
    best = _circular_crossings(best_o, edges)
    for seed in seeds:
        order = _refine_order_relocate(seed, edges)
        c = _circular_crossings(order, edges)
        if c < best:
            best = c
            best_o = order
            if best == 0:
                return best_o
    return best_o


def _two_page_partition(
    order: list[str], edges: list[tuple[str, str]]
) -> tuple[bool, set[tuple[str, str]], set[tuple[str, str]]]:
    """把无向边分成环内/环外两页，同页内弦不交叉。"""
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
        return False, set(), set()
    return True, set(inner), set(outer)


def _book_embedding(
    names: list[str], edges: list[tuple[str, str]]
) -> tuple[list[str], set[tuple[str, str]], set[tuple[str, str]]]:
    """求环序 + 双页划分，优先无外页、其次外页尽量少。"""
    names = list(names)
    if len(names) <= 1:
        return names, set(), set()

    candidates: list[list[str]] = []
    primary = _order_minimize_crossings(names, edges)
    candidates.append(primary)
    for start in names:
        candidates.append(_refine_order_relocate(_dfs_order(names, edges, start), edges))
    rng = random.Random(0xB00C)
    for _ in range(24):
        s = list(names)
        rng.shuffle(s)
        candidates.append(_refine_order_relocate(s, edges))

    best: tuple[int, int, list[str], set[tuple[str, str]], set[tuple[str, str]]] | None = None
    seen_ord: set[tuple[str, ...]] = set()
    for order in candidates:
        key = tuple(order)
        if key in seen_ord:
            continue
        seen_ord.add(key)
        ok, inner, outer = _two_page_partition(order, edges)
        if not ok:
            continue
        score = (len(outer), _circular_crossings(order, edges))
        if best is None or score < (best[0], best[1]):
            best = (score[0], score[1], order, inner, outer)
            if score == (0, 0):
                break
    if best is not None:
        return best[2], best[3], best[4]

    # 极端兜底：全放内页（可能仍有交叉，但保持旧行为可画）
    order = primary
    pairs = set(_undirected_pairs(edges))
    return order, pairs, set()


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
) -> tuple[list[str], dict[str, tuple[float, float]]] | None:
    """尝试 1 个内点 + 其余环排，全直线且几何零交叉（你拖拽能修好的那种）。"""
    if len(names) < 4:
        return None
    deg = _degree_map(names, edges)
    # 度数高的优先；同度保持稳定顺序
    hubs = sorted(names, key=lambda n: (-deg[n], n))
    for hub in hubs:
        rest = [n for n in names if n != hub]
        rest_edges = [(a, b) for a, b in edges if a != hub and b != hub]
        rest_order = _order_minimize_crossings(rest, rest_edges)
        if _circular_crossings(rest_order, rest_edges) > 0:
            # 环上仍交叉则该 hub 无望（外环本身画不平）
            continue
        pos = {hub: (cx, cy)}
        pos.update(_circle_positions(rest_order, cx, cy, ring_r))
        if _straight_layout_crossings(pos, edges) == 0:
            # order：内点放最后，便于调试；环序在前
            return rest_order + [hub], pos
    return None


def _layout_entities(
    names: list[str],
    edges: list[tuple[str, str]],
    cx: float,
    cy: float,
    ring_r: float,
) -> tuple[list[str], dict[str, tuple[float, float]], set[tuple[str, str]]]:
    """实体坐标：优先全环零交叉 → 内点直线零交叉 → 环 + 环外折线。"""
    names = list(names)
    if not names:
        return [], {}, set()
    if len(names) == 1:
        return names, {names[0]: (cx, cy)}, set()

    order, _inner, outer = _book_embedding(names, edges)
    if not outer:
        return order, _circle_positions(order, cx, cy, ring_r), set()

    # 环上不得不交叉时：优先把一点放进环内（论文图更干净，也接近手动拖拽结果）
    hubbed = _try_hub_layout(names, edges, cx, cy, ring_r)
    if hubbed is not None:
        return hubbed[0], hubbed[1], set()

    return order, _circle_positions(order, cx, cy, ring_r), outer


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


def _outer_arc_polyline(
    lp: tuple[float, float],
    rp: tuple[float, float],
    cx: float,
    cy: float,
    ring_r: float,
    nest: int,
) -> tuple[list[tuple[float, float]], tuple[float, float]]:
    """环外弧折点 + 菱形位置。

    折点落在足够大的同心圆上，相邻圆心角 ≤ π/8，使弦也在实体环外侧。
    """
    a1 = math.atan2(lp[1] - cy, lp[0] - cx)
    a2 = math.atan2(rp[1] - cy, rp[0] - cx)
    da = _ang_norm(a2 - a1)
    step = math.pi / 8
    n_steps = max(2, int(math.ceil(abs(da) / step)))
    half = abs(da) / n_steps / 2.0
    cos_h = math.cos(half) if half < math.pi / 2 else 0.2
    r_out = (ring_r + 44.0) / max(cos_h, 0.35) + 18.0 + nest * 30.0

    arc: list[tuple[float, float]] = []
    for i in range(n_steps + 1):
        t = i / n_steps
        a = a1 + da * t
        arc.append((cx + r_out * math.cos(a), cy + r_out * math.sin(a)))
    mid_a = a1 + da / 2.0
    diamond = (
        cx + (r_out + 22.0) * math.cos(mid_a),
        cy + (r_out + 22.0) * math.sin(mid_a),
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

    mode=total：总图（实体 + 联系 + 基数，不含属性，贴合论文总 E-R）。
    mode=part：分图（单个实体 + 全部属性，不含联系）。
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
        ent_name = (entity or "").strip() or str(tables[0].get("name") or "")
        tables = [t for t in tables if t.get("name") == ent_name]
        if not tables:
            return _svg_wrap(480, 200, '<text x="24" y="100" font-size="14">未找到该实体</text>')
        relations = []
    else:
        # 总图：去掉无联系的悬空实体（如纯配置表），让图成连通业务网
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
        # 分图用全列；总图不画属性
        return list(t.get("columns") or [])

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
    if n <= 1:
        ring_r = 0.0
    else:
        pair_need = 2 * max_cloud + (64 if not show_attrs else 120)
        ring_r = pair_need / (2 * math.sin(math.pi / n))
        # 总图实体少时不必撑到很大，避免预览一大块空底
        ring_r = max(ring_r, 120.0 if not show_attrs else 200.0)
        # 内点布局时环上少 1 点，略放大以免挤
        if n >= 4:
            ring_r = max(ring_r, pair_need / (2 * math.sin(math.pi / max(n - 1, 2))))

    # 先按可能走环外预留边距；若改用内点直线则 outer 为空，多留无妨
    _, _, outer_hint = _book_embedding(names, edges)
    outer_nest_pad = 0.0
    if outer_hint and n > 1:
        outer_nest_pad = ring_r * 0.65 + 100.0 + max(0, len(outer_hint) - 1) * 32.0

    pad = (56.0 if not show_attrs else 72.0) + (12.0 if outer_hint else 0.0)
    content_r = ring_r + max_cloud + outer_nest_pad
    w = int(2 * content_r + 2 * pad)
    h = int(2 * content_r + 2 * pad)
    w, h = max(w, 360), max(h, 280)
    cx, cy = w / 2.0, h / 2.0

    order, entity_pos, outer_pairs = _layout_entities(names, edges, cx, cy, ring_r)
    ordered_tables = [by_name[nm] for nm in order if nm in by_name]
    # 内点布局成功则无需环外垫
    if not outer_pairs:
        outer_nest_pad = 0.0

    # 同对联系计数，便于垂线错开
    pair_keys: list[tuple[str, str]] = []
    for r in relations:
        a, b = r["left"], r["right"]
        pair_keys.append((a, b) if a <= b else (b, a))
    pair_totals: dict[tuple[str, str], int] = {}
    for pk in pair_keys:
        pair_totals[pk] = pair_totals.get(pk, 0) + 1
    pair_seen: dict[tuple[str, str], int] = {}

    # 外页边按跨度排序，决定环外嵌套层级
    pos_idx = {name: i for i, name in enumerate(order)}

    def _span_of(pk: tuple[str, str]) -> int:
        if pk[0] not in pos_idx or pk[1] not in pos_idx:
            return 0
        i, j = pos_idx[pk[0]], pos_idx[pk[1]]
        d = abs(i - j)
        return min(d, n - d) if n else d

    outer_sorted = sorted(outer_pairs, key=_span_of)
    outer_nest: dict[tuple[str, str], int] = {e: i for i, e in enumerate(outer_sorted)}

    edge_parts: list[str] = []
    node_parts: list[str] = []
    card_parts: list[str] = []

    def _card_pos(
        a: tuple[float, float], b: tuple[float, float], t: float = 0.35
    ) -> tuple[float, float]:
        px = a[0] * (1 - t) + b[0] * t
        py = a[1] * (1 - t) + b[1] * t
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        return px - dy / L * 12, py + dx / L * 12

    # 联系：环内弦 或 环外折线（仅总图）
    for ri, r in enumerate(relations):
        lp = entity_pos.get(r["left"])
        rp = entity_pos.get(r["right"])
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

        if use_outer:
            nest = outer_nest.get(pk, 0)
            arc_pts, (mx, my) = _outer_arc_polyline(lp, rp, cx, cy, ring_r, nest)
            if pair_totals[pk] > 1:
                ox, oy = _pair_offset(arc_pts[0], arc_pts[-1], pi, pair_totals[pk])
                mx += ox
                my += oy
                arc_pts = [(p[0] + ox * 0.2, p[1] + oy * 0.2) for p in arc_pts]
            e1 = _rect_edge(lp[0], lp[1], arc_pts[0][0], arc_pts[0][1], hw1, ENTITY_HH)
            e2 = _rect_edge(rp[0], rp[1], arc_pts[-1][0], arc_pts[-1][1], hw2, ENTITY_HH)
            mid = len(arc_pts) // 2
            left_chain = [e1, *arc_pts[: mid + 1]]
            d1 = _diamond_edge(mx, my, dw, dh, left_chain[-1][0], left_chain[-1][1])
            left_chain.append(d1)
            right_chain = [
                _diamond_edge(mx, my, dw, dh, arc_pts[mid][0], arc_pts[mid][1]),
                *arc_pts[mid:],
                e2,
            ]
            for i in range(len(left_chain) - 1):
                x1, y1 = left_chain[i]
                x2, y2 = left_chain[i + 1]
                edge_parts.append(
                    f'<line class="er-edge" data-from="{_esc(left_id)}" data-to="{_esc(rel_id)}" '
                    f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                    f'stroke="#000" stroke-width="1" fill="none"/>'
                )
            for i in range(len(right_chain) - 1):
                x1, y1 = right_chain[i]
                x2, y2 = right_chain[i + 1]
                edge_parts.append(
                    f'<line class="er-edge" data-from="{_esc(rel_id)}" data-to="{_esc(right_id)}" '
                    f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                    f'stroke="#000" stroke-width="1" fill="none"/>'
                )
            c1 = _card_pos(e1, arc_pts[0])
            c2 = _card_pos(e2, arc_pts[-1])
        else:
            ox, oy = _pair_offset(lp, rp, pi, pair_totals[pk])
            mx = (lp[0] + rp[0]) / 2 + ox
            my = (lp[1] + rp[1]) / 2 + oy
            e1 = _rect_edge(lp[0], lp[1], mx, my, hw1, ENTITY_HH)
            d1 = _diamond_edge(mx, my, dw, dh, lp[0], lp[1])
            d2 = _diamond_edge(mx, my, dw, dh, rp[0], rp[1])
            e2 = _rect_edge(rp[0], rp[1], mx, my, hw2, ENTITY_HH)
            edge_parts.append(
                f'<line class="er-edge" data-from="{_esc(left_id)}" data-to="{_esc(rel_id)}" '
                f'x1="{e1[0]:.1f}" y1="{e1[1]:.1f}" x2="{d1[0]:.1f}" y2="{d1[1]:.1f}" '
                f'stroke="#000" stroke-width="1" fill="none"/>'
            )
            edge_parts.append(
                f'<line class="er-edge" data-from="{_esc(rel_id)}" data-to="{_esc(right_id)}" '
                f'x1="{d2[0]:.1f}" y1="{d2[1]:.1f}" x2="{e2[0]:.1f}" y2="{e2[1]:.1f}" '
                f'stroke="#000" stroke-width="1" fill="none"/>'
            )
            c1 = _card_pos(e1, d1)
            c2 = _card_pos(e2, d2)

        diamond = (
            f"{mx:.1f},{my - dh:.1f} {mx + dw:.1f},{my:.1f} "
            f"{mx:.1f},{my + dh:.1f} {mx - dw:.1f},{my:.1f}"
        )
        node_parts.append(
            f'<g class="er-node" data-kind="rel" data-id="{_esc(rel_id)}" data-shape="diamond" '
            f'data-cx="{mx:.1f}" data-cy="{my:.1f}" data-hw="{dw:.1f}" data-hh="{dh:.1f}">'
            f'<polygon points="{diamond}" fill="#fff" stroke="#000" stroke-width="1.2"/>'
            f'<text x="{mx:.1f}" y="{my + 4:.1f}" text-anchor="middle" '
            f'font-family="Microsoft YaHei, SimSun, serif" font-size="12">{_esc(rel_label)}</text>'
            f"</g>"
        )

        card_parts.append(
            f'<text class="er-card" data-from="{_esc(left_id)}" data-to="{_esc(rel_id)}" '
            f'x="{c1[0]:.1f}" y="{c1[1]:.1f}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="12">{_esc(r["card_left"])}</text>'
        )
        card_parts.append(
            f'<text class="er-card" data-from="{_esc(right_id)}" data-to="{_esc(rel_id)}" '
            f'x="{c2[0]:.1f}" y="{c2[1]:.1f}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="12">{_esc(r["card_right"])}</text>'
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
            f'font-family="Microsoft YaHei, SimSun, serif" font-size="13" font-weight="600">'
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
            elif col.get("fk"):
                wave = []
                x0 = ax - tw / 2
                steps = max(4, int(tw / 6))
                for si in range(steps + 1):
                    wx = x0 + tw * si / steps
                    wy = ay + 8 + (2 if si % 2 else -2)
                    wave.append(f"{wx:.1f},{wy:.1f}")
                deco = (
                    f'<polyline points="{" ".join(wave)}" fill="none" stroke="#000" stroke-width="1"/>'
                )
            node_parts.append(
                f'<g class="er-node" data-kind="attr" data-id="{_esc(attr_id)}" '
                f'data-parent="{_esc(ent_id)}" data-shape="ellipse" '
                f'data-cx="{ax:.1f}" data-cy="{ay:.1f}" data-rx="{rx:.1f}" data-ry="{ATTR_RH:.1f}">'
                f'<ellipse cx="{ax:.1f}" cy="{ay:.1f}" rx="{rx:.1f}" ry="{ATTR_RH:.1f}" '
                f'fill="#fff" stroke="#000" stroke-width="1"/>'
                f'<text x="{ax:.1f}" y="{ay + 4:.1f}" text-anchor="middle" '
                f'font-family="Microsoft YaHei, sans-serif" font-size="10">{_esc(alabel)}</text>'
                f"{deco}</g>"
            )

    parts = (
        ['<g class="er-edges">']
        + edge_parts
        + card_parts
        + ["</g>"]
        + ['<g class="er-nodes">']
        + node_parts
        + ["</g>"]
    )
    return _svg_wrap(w, h, "\n".join(parts))



def _svg_wrap(w: int, h: int, inner: str) -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">\n'
        f'<rect class="er-paper" width="100%" height="100%" fill="#fff"/>\n'
        f"{inner}\n</svg>\n"
    )
