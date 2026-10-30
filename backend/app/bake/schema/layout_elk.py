"""论文图初局：用 pyelk（ELK layered）只算坐标，不经 PlantUML / Graphviz。"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("app.bake.layout_elk")

# 常见选题应远低于此；超时仍返回已算结果并打标，禁止回退全环自研。
_DEFAULT_OPTIONS: dict[str, str] = {
    "elk.algorithm": "layered",
    "elk.direction": "RIGHT",
    "elk.edgeRouting": "ORTHOGONAL",
    "elk.spacing.nodeNode": "48.0",
    "elk.layered.spacing.nodeNodeBetweenLayers": "80.0",
    "elk.spacing.edgeNode": "24.0",
    "elk.spacing.edgeEdge": "16.0",
    "org.eclipse.elk.json.shapeCoords": "ROOT",
    "org.eclipse.elk.json.edgeCoords": "ROOT",
}


class ElkLayoutError(RuntimeError):
    """pyelk 不可用或布局失败。"""


def _elk() -> Any:
    try:
        from pyelk import ELK
    except ImportError as e:
        raise ElkLayoutError(
            "缺少 pyelk：请在工厂 backend 环境安装 pyelk（纯 Python ELK）"
        ) from e
    return ELK()


def layout_graph(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    layout_options: dict[str, str] | None = None,
) -> dict[str, Any]:
    """对节点/边跑 ELK layered。

    nodes: [{id, width, height}, ...]
    edges: [{id, sources:[id], targets:[id]}, ...]
    返回 {positions: {id:(x,y,w,h)}, edge_paths: {id:[(x,y),...]}, elapsed_ms, algo}
    """
    if not nodes:
        return {
            "positions": {},
            "edge_paths": {},
            "elapsed_ms": 0.0,
            "algo": "elk-layered",
        }

    opts = dict(_DEFAULT_OPTIONS)
    if layout_options:
        opts.update({str(k): str(v) for k, v in layout_options.items()})

    children = []
    for n in nodes:
        nid = str(n.get("id") or "")
        if not nid:
            continue
        children.append(
            {
                "id": nid,
                "width": float(n.get("width") or 80),
                "height": float(n.get("height") or 40),
            }
        )
    if not children:
        return {
            "positions": {},
            "edge_paths": {},
            "elapsed_ms": 0.0,
            "algo": "elk-layered",
        }

    elk_edges = []
    for e in edges:
        eid = str(e.get("id") or "")
        srcs = [str(x) for x in (e.get("sources") or []) if x is not None]
        tgts = [str(x) for x in (e.get("targets") or []) if x is not None]
        if not eid or not srcs or not tgts:
            continue
        elk_edges.append({"id": eid, "sources": srcs, "targets": tgts})

    graph: dict[str, Any] = {
        "id": "root",
        "layoutOptions": opts,
        "children": children,
        "edges": elk_edges,
    }

    t0 = time.perf_counter()
    try:
        result = _elk().layout(graph)
    except ElkLayoutError:
        raise
    except Exception as e:
        raise ElkLayoutError(f"ELK 布局失败: {e}") from e
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    positions: dict[str, tuple[float, float, float, float]] = {}
    for c in result.get("children") or []:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "")
        if not cid:
            continue
        positions[cid] = (
            float(c.get("x") or 0.0),
            float(c.get("y") or 0.0),
            float(c.get("width") or 80.0),
            float(c.get("height") or 40.0),
        )

    edge_paths: dict[str, list[tuple[float, float]]] = {}
    for ed in result.get("edges") or []:
        if not isinstance(ed, dict):
            continue
        eid = str(ed.get("id") or "")
        if not eid:
            continue
        pts: list[tuple[float, float]] = []
        for sec in ed.get("sections") or []:
            if not isinstance(sec, dict):
                continue
            sp = sec.get("startPoint") or {}
            pts.append((float(sp.get("x") or 0.0), float(sp.get("y") or 0.0)))
            for bp in sec.get("bendPoints") or []:
                if isinstance(bp, dict):
                    pts.append((float(bp.get("x") or 0.0), float(bp.get("y") or 0.0)))
            ep = sec.get("endPoint") or {}
            pts.append((float(ep.get("x") or 0.0), float(ep.get("y") or 0.0)))
        # 去连续重复点
        cleaned: list[tuple[float, float]] = []
        for p in pts:
            if not cleaned or abs(cleaned[-1][0] - p[0]) > 1e-6 or abs(cleaned[-1][1] - p[1]) > 1e-6:
                cleaned.append(p)
        if len(cleaned) >= 2:
            edge_paths[eid] = cleaned

    logger.info(
        "elk layout nodes=%s edges=%s elapsed_ms=%.1f",
        len(positions),
        len(edge_paths),
        elapsed_ms,
    )
    return {
        "positions": positions,
        "edge_paths": edge_paths,
        "elapsed_ms": elapsed_ms,
        "algo": "elk-layered",
    }


def is_approx_circular(
    positions: dict[str, tuple[float, float]],
    *,
    min_n: int = 5,
    radius_cv_max: float = 0.12,
    angle_gap_cv_max: float = 0.35,
) -> bool:
    """启发式：点是否近似均匀落在同一圆周（防 E-R 全环回归）。"""
    if len(positions) < min_n:
        return False
    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    import math

    rs = [math.hypot(x - cx, y - cy) for x, y in positions.values()]
    mean_r = sum(rs) / len(rs)
    if mean_r < 40.0:
        return False
    var_r = sum((r - mean_r) ** 2 for r in rs) / len(rs)
    cv_r = (var_r**0.5) / mean_r
    if cv_r > radius_cv_max:
        return False
    angs = sorted(math.atan2(y - cy, x - cx) for x, y in positions.values())
    gaps = []
    for i, a in enumerate(angs):
        b = angs[(i + 1) % len(angs)]
        gap = b - a if i + 1 < len(angs) else (b + 2 * math.pi - a)
        gaps.append(gap)
    mean_g = sum(gaps) / len(gaps)
    if mean_g <= 0:
        return False
    var_g = sum((g - mean_g) ** 2 for g in gaps) / len(gaps)
    cv_g = (var_g**0.5) / mean_g
    return cv_g <= angle_gap_cv_max
