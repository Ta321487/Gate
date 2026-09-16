"""论文「类图」：UML 类框与关联 SVG 渲染。"""

from __future__ import annotations

from typing import Any

from app.bake.schema.class_layout import (
    _assoc_route,
    _finalize_canvas_extent,
    _iter_hv_segments,
    _layout_classes,
    _path_d,
    _paths_conflict,
    _select_crossing_free_assocs,
)
from app.bake.schema.class_model import (
    _FONT,
    _FONT_BODY,
    _FONT_CODE,
    _FONT_TITLE,
    _H_PAD,
    _HEADER_H,
    _PAD,
    _ROW_H,
    _STROKE,
    _esc,
    _f,
    _normalize_rel_kind,
)

_BRIDGE_R = 5.5


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


def _ortho_cross_points(
    edge_paths: list[tuple[str, str, list[tuple[float, float]]]],
) -> dict[int, list[tuple[float, float]]]:
    """边下标 → 该边水平段上需画过桥的交叉点（竖线从下方穿过）。"""
    bridges: dict[int, list[tuple[float, float]]] = {}
    segs_by_edge: list[list[tuple[str, float, float, float, float]]] = [
        _iter_hv_segments(pts) for _, _, pts in edge_paths
    ]
    for i, segs_i in enumerate(segs_by_edge):
        for j, segs_j in enumerate(segs_by_edge):
            if j <= i:
                continue
            for si in segs_i:
                for sj in segs_j:
                    h = v = None
                    hi = hj = -1
                    if si[0] == "H" and sj[0] == "V":
                        h, v, hi = si, sj, i
                    elif si[0] == "V" and sj[0] == "H":
                        h, v, hi = sj, si, j
                    else:
                        continue
                    assert h is not None and v is not None
                    _, x0, x1, y, _ = h
                    _, x, _, y0, y1 = v
                    # 开交叉：交点不在端点
                    if not (x0 + 1 < x < x1 - 1 and y0 + 1 < y < y1 - 1):
                        continue
                    bridges.setdefault(hi, []).append((x, y))
    # 去重并排序（沿水平方向）
    for ei, pts in list(bridges.items()):
        uniq: list[tuple[float, float]] = []
        for p in sorted(pts, key=lambda t: t[0]):
            if not uniq or abs(uniq[-1][0] - p[0]) > 1 or abs(uniq[-1][1] - p[1]) > 1:
                uniq.append(p)
        bridges[ei] = uniq
    return bridges


def _path_d_with_bridges(
    pts: list[tuple[float, float]],
    bridges: list[tuple[float, float]] | None,
) -> str:
    """水平段遇到交叉点画半圆弧过桥（电路图习惯，交叉可读）。"""
    if not pts:
        return ""
    if not bridges:
        return _path_d(pts)
    r = _BRIDGE_R
    parts: list[str] = [f"M {_f(pts[0][0])} {_f(pts[0][1])}"]
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        if abs(y0 - y1) < 0.5 and abs(x0 - x1) >= 1:
            # 水平：插入过桥
            y = y0
            going_right = x1 >= x0
            xs = sorted(
                [
                    bx
                    for bx, by in bridges
                    if abs(by - y) < 1.0 and min(x0, x1) + r < bx < max(x0, x1) - r
                ]
            )
            if not going_right:
                xs = list(reversed(xs))
            cur = x0
            for bx in xs:
                parts.append(f"L {_f(bx - r if going_right else bx + r)} {_f(y)}")
                # 向上拱的半圆：sweep-flag 随方向
                if going_right:
                    parts.append(
                        f"A {_f(r)} {_f(r)} 0 0 1 {_f(bx + r)} {_f(y)}"
                    )
                else:
                    parts.append(
                        f"A {_f(r)} {_f(r)} 0 0 0 {_f(bx - r)} {_f(y)}"
                    )
                cur = bx + r if going_right else bx - r
            parts.append(f"L {_f(x1)} {_f(y1)}")
        else:
            parts.append(f"L {_f(x1)} {_f(y1)}")
    return " ".join(parts)


def _marker_defs() -> str:
    """六种 UML 关系端点（对齐论文关系线条表）。"""
    # 开口箭头 / 空心三角 / 空心菱形 / 实心菱形；hot 仅用于悬停高亮关联类
    return (
        "<defs>"
        # 关联 / 依赖 / 聚合·组合 的开口箭头（朝 to）
        '<marker id="uml-open" markerWidth="12" markerHeight="10" '
        'refX="10" refY="5" orient="auto" markerUnits="userSpaceOnUse">'
        '<path d="M1,1 L10,5 L1,9" fill="none" stroke="#000" stroke-width="1.2"/>'
        "</marker>"
        '<marker id="uml-open-hot" markerWidth="12" markerHeight="10" '
        'refX="10" refY="5" orient="auto" markerUnits="userSpaceOnUse">'
        '<path d="M1,1 L10,5 L1,9" fill="none" stroke="#0d9488" stroke-width="1.2"/>'
        "</marker>"
        # 兼容旧 id（悬停脚本可能仍写 uml-assoc）
        '<marker id="uml-assoc" markerWidth="12" markerHeight="10" '
        'refX="10" refY="5" orient="auto" markerUnits="userSpaceOnUse">'
        '<path d="M1,1 L10,5 L1,9" fill="none" stroke="#000" stroke-width="1.2"/>'
        "</marker>"
        '<marker id="uml-assoc-hot" markerWidth="12" markerHeight="10" '
        'refX="10" refY="5" orient="auto" markerUnits="userSpaceOnUse">'
        '<path d="M1,1 L10,5 L1,9" fill="none" stroke="#0d9488" stroke-width="1.2"/>'
        "</marker>"
        # 继承 / 实现：空心三角（朝父类 / 接口）
        '<marker id="uml-tri" markerWidth="14" markerHeight="12" '
        'refX="12" refY="6" orient="auto" markerUnits="userSpaceOnUse">'
        '<path d="M1,1 L12,6 L1,11 Z" fill="#fff" stroke="#000" stroke-width="1.2"/>'
        "</marker>"
        '<marker id="uml-tri-hot" markerWidth="14" markerHeight="12" '
        'refX="12" refY="6" orient="auto" markerUnits="userSpaceOnUse">'
        '<path d="M1,1 L12,6 L1,11 Z" fill="#fff" stroke="#0d9488" stroke-width="1.2"/>'
        "</marker>"
        # 聚合：空心菱形（在整体端 = path 起点）
        '<marker id="uml-agg" markerWidth="14" markerHeight="10" '
        'refX="1" refY="5" orient="auto" markerUnits="userSpaceOnUse">'
        '<path d="M1,5 L7,1 L13,5 L7,9 Z" fill="#fff" stroke="#000" stroke-width="1.2"/>'
        "</marker>"
        '<marker id="uml-agg-hot" markerWidth="14" markerHeight="10" '
        'refX="1" refY="5" orient="auto" markerUnits="userSpaceOnUse">'
        '<path d="M1,5 L7,1 L13,5 L7,9 Z" fill="#fff" stroke="#0d9488" stroke-width="1.2"/>'
        "</marker>"
        # 组合：实心菱形
        '<marker id="uml-comp" markerWidth="14" markerHeight="10" '
        'refX="1" refY="5" orient="auto" markerUnits="userSpaceOnUse">'
        '<path d="M1,5 L7,1 L13,5 L7,9 Z" fill="#000" stroke="#000" stroke-width="1.2"/>'
        "</marker>"
        '<marker id="uml-comp-hot" markerWidth="14" markerHeight="10" '
        'refX="1" refY="5" orient="auto" markerUnits="userSpaceOnUse">'
        '<path d="M1,5 L7,1 L13,5 L7,9 Z" fill="#0d9488" stroke="#0d9488" stroke-width="1.2"/>'
        "</marker>"
        "</defs>"
    )


def _edge_marker_attrs(kind: str, *, hot: bool = False) -> tuple[str, str, str]:
    """返回 (stroke_dash, marker_start, marker_end)。"""
    k = _normalize_rel_kind(kind)
    suf = "-hot" if hot else ""
    if k == "dependency":
        return (' stroke-dasharray="6 4"', "", f' marker-end="url(#uml-open{suf})"')
    if k == "inheritance":
        return ("", "", f' marker-end="url(#uml-tri{suf})"')
    if k == "implementation":
        return (' stroke-dasharray="6 4"', "", f' marker-end="url(#uml-tri{suf})"')
    if k == "aggregation":
        return (
            "",
            f' marker-start="url(#uml-agg{suf})"',
            f' marker-end="url(#uml-open{suf})"',
        )
    if k == "composition":
        return (
            "",
            f' marker-start="url(#uml-comp{suf})"',
            f' marker-end="url(#uml-open{suf})"',
        )
    # association
    return ("", "", f' marker-end="url(#uml-open{suf})"')


def _draw_assoc_path(
    frm: str,
    to: str,
    pts: list[tuple[float, float]],
    kind: str = "association",
) -> str:
    d = _path_d(pts)
    k = _normalize_rel_kind(kind)
    dash, m_start, m_end = _edge_marker_attrs(k)
    tip = {
        "association": "关联",
        "dependency": "依赖",
        "inheritance": "继承",
        "implementation": "实现",
        "aggregation": "聚合",
        "composition": "组合",
    }.get(k, "关联")
    return (
        f'<path class="uml-assoc" data-from="{_esc(frm)}" data-to="{_esc(to)}" '
        f'data-kind="{_esc(k)}" data-tip="{_esc(tip)}" '
        f'd="{d}" fill="none" stroke="#000" '
        f'stroke-width="{_STROKE}"{dash}{m_start}{m_end}/>'
    )


def _draw_class_box(x: float, y: float, w: float, h: float, cls: dict[str, Any]) -> str:
    """可拖节点：与 E-R ``.er-node`` 同口径的 data-cx/cy/hw/hh。"""
    parts: list[str] = []
    tid = _esc(str(cls.get("id") or ""))
    cx, cy = x + w / 2, y + h / 2
    hw, hh = w / 2, h / 2
    parts.append(
        f'<g class="uml-node" data-id="{tid}" data-kind="class" data-shape="rect" '
        f'data-cx="{_f(cx)}" data-cy="{_f(cy)}" data-hw="{_f(hw)}" data-hh="{_f(hh)}">'
        f'<rect class="uml-class" x="{_f(x)}" y="{_f(y)}" width="{_f(w)}" height="{_f(h)}" '
        f'fill="#fff" stroke="#000" stroke-width="{_STROKE}"/>'
    )
    name = str(cls.get("name") or "")
    attrs = list(cls.get("attributes") or [])
    methods = list(cls.get("methods") or [])
    y1 = y + _HEADER_H
    y2 = y1 + len(attrs) * _ROW_H + 2
    parts.append(
        f'<line x1="{_f(x)}" y1="{_f(y1)}" x2="{_f(x + w)}" y2="{_f(y1)}" '
        f'stroke="#000" stroke-width="{_STROKE}"/>'
    )
    parts.append(
        f'<line x1="{_f(x)}" y1="{_f(y2)}" x2="{_f(x + w)}" y2="{_f(y2)}" '
        f'stroke="#000" stroke-width="{_STROKE}"/>'
    )
    # 类名垂直居中于标题区
    name_y = y + _HEADER_H * 0.72
    parts.append(
        f'<text x="{_f(x + w / 2)}" y="{_f(name_y)}" text-anchor="middle" '
        f'font-size="{_f(_FONT_TITLE)}" font-weight="700" fill="#000" '
        f'font-family="{_FONT}" text-rendering="geometricPrecision">{_esc(name)}</text>'
    )
    ty = y1 + _ROW_H - 5
    for a in attrs:
        line = str(a.get("display") or f"+ {a.get('name')}: {a.get('type')}")
        parts.append(
            f'<text class="uml-attr" x="{_f(x + _H_PAD)}" y="{_f(ty)}" '
            f'font-size="{_f(_FONT_BODY)}" fill="#000" font-family="{_FONT_CODE}" '
            f'text-rendering="geometricPrecision">{_esc(line)}</text>'
        )
        ty += _ROW_H
    ty = y2 + _ROW_H - 5
    for m in methods:
        line = str(m.get("display") or "")
        parts.append(
            f'<text class="uml-meth" x="{_f(x + _H_PAD)}" y="{_f(ty)}" '
            f'font-size="{_f(_FONT_BODY)}" fill="#000" font-family="{_FONT_CODE}" '
            f'text-rendering="geometricPrecision">{_esc(line)}</text>'
        )
        ty += _ROW_H
    parts.append("</g>")
    return "".join(parts)


def _positions_from_model(
    model: dict[str, Any],
) -> dict[str, tuple[float, float, float, float]]:
    layout = model.get("layout")
    if isinstance(layout, dict) and layout:
        out: dict[str, tuple[float, float, float, float]] = {}
        for k, v in layout.items():
            if not isinstance(v, dict):
                continue
            out[str(k)] = (
                float(v.get("x") or 0),
                float(v.get("y") or 0),
                float(v.get("w") or 120),
                float(v.get("h") or 80),
            )
        if out:
            return out
    return _layout_classes(model)


def render_class_svg(
    model: dict[str, Any] | None,
    *,
    layout_override: dict[str, Any] | None = None,
) -> str:
    if not model or not isinstance(model.get("classes"), list) or not model["classes"]:
        body = (
            f'<text x="24" y="64" fill="#000" font-family="{_FONT}">'
            "暂无类图数据（需 bake 后 sql/schema.sql）</text>"
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="420" height="100" viewBox="0 0 420 100">'
            f"{body}</svg>"
        )

    work = dict(model)
    if layout_override:
        work["layout"] = layout_override
    pos = _positions_from_model(work)
    # 平移进正坐标（绝对坐标，便于前端 data-cx 拖拽，不用外层 <g transform>）
    min_x = min((x for x, y, w, h in pos.values()), default=0.0)
    min_y = min((y for x, y, w, h in pos.values()), default=0.0)
    shift_x = _PAD - min_x if min_x < _PAD else 0.0
    shift_y = _PAD - min_y if min_y < _PAD else 0.0
    if shift_x or shift_y:
        pos = {
            k: (x + shift_x, y + shift_y, w, h) for k, (x, y, w, h) in pos.items()
        }
        cached0 = work.get("_assoc_paths")
        if isinstance(cached0, list):
            work["_assoc_paths"] = [
                [(float(x) + shift_x, float(y) + shift_y) for x, y in p]
                if isinstance(p, list) and p and isinstance(p[0], (list, tuple))
                else p
                for p in cached0
            ]

    obstacles = [(tid, x, y, w, h) for tid, (x, y, w, h) in pos.items()]
    parents = {str(k): str(v) for k, v in (work.get("tree_parents") or {}).items()}
    zero = bool(work.get("zero_crossing"))

    edge_paths: list[tuple[str, str, list[tuple[float, float]], str]] = []
    cached = work.get("_assoc_paths")
    drawable = [
        a
        for a in (work.get("associations") or [])
        if isinstance(a, dict)
        and str(a.get("from") or "") in pos
        and str(a.get("to") or "") in pos
    ]
    n_lanes = max(1, len(drawable))
    cache_ok = (
        isinstance(cached, list)
        and len(cached) == len(drawable)
        and all(isinstance(p, list) and len(p) >= 2 for p in cached)
    )
    if cache_ok and zero:
        # 保险丝：缓存若仍冲突则整表重选
        for i in range(len(cached)):
            for j in range(i + 1, len(cached)):
                if _paths_conflict(cached[i], cached[j]):
                    cache_ok = False
                    break
            if not cache_ok:
                break
    if cache_ok:
        for a, pts in zip(drawable, cached):
            frm, to = str(a.get("from") or ""), str(a.get("to") or "")
            kind = _normalize_rel_kind(str(a.get("kind") or "association"))
            edge_paths.append((frm, to, pts, kind))
    elif zero:
        _select_crossing_free_assocs(work, pos)
        drawable = [
            a
            for a in (work.get("associations") or [])
            if isinstance(a, dict)
            and str(a.get("from") or "") in pos
            and str(a.get("to") or "") in pos
        ]
        cached = work.get("_assoc_paths") or []
        for a, pts in zip(drawable, cached):
            if not isinstance(pts, list) or len(pts) < 2:
                continue
            frm, to = str(a.get("from") or ""), str(a.get("to") or "")
            kind = _normalize_rel_kind(str(a.get("kind") or "association"))
            edge_paths.append((frm, to, pts, kind))
    else:
        for i, a in enumerate(drawable):
            frm, to = str(a.get("from") or ""), str(a.get("to") or "")
            kind = _normalize_rel_kind(str(a.get("kind") or "association"))
            pts = _assoc_route(
                frm, to, pos, parents, obstacles, lane=i, n_lanes=n_lanes
            )
            edge_paths.append((frm, to, pts, kind))

    # 出图前最后一道：任何仍冲突的边直接丢掉（禁止画出交叉线）
    if zero and edge_paths:
        kept: list[tuple[str, str, list[tuple[float, float]], str]] = []
        for frm, to, pts, kind in edge_paths:
            if any(_paths_conflict(pts, p) for _, _, p, _ in kept):
                continue
            kept.append((frm, to, pts, kind))
        edge_paths = kept

    # 框+折线统一入边距，避免外绕线贴边被默认视口裁掉
    pos, edge_paths, max_x, max_y = _finalize_canvas_extent(pos, edge_paths)

    parts: list[str] = [
        f'<rect class="uml-paper" x="0" y="0" width="{_f(max_x)}" height="{_f(max_y)}" '
        f'fill="#ffffff" stroke="none"/>',
        _marker_defs(),
    ]

    for frm, to, pts, kind in edge_paths:
        parts.append(_draw_assoc_path(frm, to, pts, kind))

    for c in work["classes"]:
        if not isinstance(c, dict):
            continue
        tid = str(c.get("id") or "")
        if tid not in pos:
            continue
        x, y, w, h = pos[tid]
        parts.append(_draw_class_box(x, y, w, h, c))

    inner = "".join(parts)
    zattr = ' data-zero-crossing="1"' if zero else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(max_x)}" height="{int(max_y)}" '
        f'viewBox="0 0 {_f(max_x)} {_f(max_y)}" data-figure="class-diagram"{zattr}>'
        f"{inner}</svg>"
    )
