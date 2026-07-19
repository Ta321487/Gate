"""从 schema.sql 解析表结构，推断联系，输出陈氏 E-R 线框图 SVG。"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path


CREATE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\((.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)
FK_INLINE_RE = re.compile(
    r"FOREIGN\s+KEY\s*\(`?(\w+)`?\)\s*REFERENCES\s*`?(\w+)`?\s*\(`?(\w+)`?\)",
    re.IGNORECASE,
)
COL_RE = re.compile(
    r"^`?(\w+)`?\s+(\w+(?:\([^)]*\))?)",
    re.IGNORECASE,
)

@dataclass
class Column:
    name: str
    type: str
    pk: bool = False
    fk: bool = False
    fk_table: str | None = None
    not_null: bool = False


@dataclass
class Table:
    name: str
    columns: list[Column] = field(default_factory=list)


@dataclass
class Relation:
    name: str
    left: str
    right: str
    card_left: str  # "1" | "n"
    card_right: str
    via: str


def parse_schema_sql(sql: str) -> list[Table]:
    tables: list[Table] = []
    for m in CREATE_RE.finditer(sql or ""):
        tname = m.group(1)
        body = m.group(2)
        cols: list[Column] = []
        pk_names: set[str] = set()
        fk_map: dict[str, str] = {}

        for raw in body.split("\n"):
            line = raw.strip().rstrip(",")
            if not line or line.startswith("--"):
                continue
            upper = line.upper()
            if upper.startswith("PRIMARY KEY"):
                for c in re.findall(r"`?(\w+)`?", line):
                    if c.upper() != "PRIMARY" and c.upper() != "KEY":
                        pk_names.add(c)
                continue
            fk = FK_INLINE_RE.search(line)
            if fk:
                fk_map[fk.group(1)] = fk.group(2)
                continue
            if upper.startswith("UNIQUE") or upper.startswith("KEY") or upper.startswith("INDEX") or upper.startswith("CONSTRAINT"):
                continue
            cm = COL_RE.match(line)
            if not cm:
                continue
            cname, ctype = cm.group(1), cm.group(2)
            is_pk = "PRIMARY KEY" in upper
            if is_pk:
                pk_names.add(cname)
            cols.append(
                Column(
                    name=cname,
                    type=ctype,
                    pk=is_pk,
                    not_null="NOT NULL" in upper,
                )
            )

        for c in cols:
            if c.name in pk_names:
                c.pk = True
            if c.name in fk_map:
                c.fk = True
                c.fk_table = fk_map[c.name]

        tables.append(Table(name=tname, columns=cols))

    _infer_fk_by_name(tables)
    return tables


def _infer_fk_by_name(tables: list[Table]) -> None:
    names = {t.name for t in tables}
    # id 表名映射：book ← book_id；sys_user ← user_id / username(弱)
    for t in tables:
        for c in t.columns:
            if c.fk or c.pk:
                continue
            if c.name.endswith("_id") and len(c.name) > 3:
                base = c.name[:-3]
                candidates = [base, f"sys_{base}", f"{base}s"]
                for cand in candidates:
                    if cand in names and cand != t.name:
                        c.fk = True
                        c.fk_table = cand
                        break
            elif c.name == "username" and "sys_user" in names and t.name != "sys_user":
                c.fk = True
                c.fk_table = "sys_user"


def _short_name(table: str) -> str:
    return table.replace("sys_", "")


def _rel_label(parent: str, child: str, by_name: dict[str, Table]) -> str:
    """从结构推断菱形名：多外键子表用子表名；字典/分类父表用父表名；否则用子表名。"""
    child_t = by_name.get(child)
    parent_t = by_name.get(parent)
    child_fk_n = sum(1 for c in (child_t.columns if child_t else []) if c.fk)
    if child_fk_n >= 2:
        return _short_name(child)
    if parent_t and len(parent_t.columns) <= 3:
        return _short_name(parent)
    return _short_name(child)


def infer_relations(tables: list[Table]) -> list[Relation]:
    by_name = {t.name: t for t in tables}
    rels: list[Relation] = []
    seen: set[tuple[str, str, str]] = set()
    for t in tables:
        for c in t.columns:
            if not c.fk or not c.fk_table:
                continue
            parent, child = c.fk_table, t.name
            key = (parent, child, c.name)
            if key in seen:
                continue
            seen.add(key)
            rels.append(
                Relation(
                    name=_rel_label(parent, child, by_name),
                    left=parent,
                    right=child,
                    card_left="1",
                    card_right="n",
                    via=c.name,
                )
            )
    return rels


def pick_core_attrs(cols: list[Column], limit: int = 5) -> list[Column]:
    """属性 >8 时取核心：PK + FK + 业务字段，最多 limit 个。"""
    if len(cols) <= 8:
        return cols
    picked: list[Column] = []
    used: set[str] = set()

    def add(c: Column) -> None:
        if c.name in used or len(picked) >= limit:
            return
        used.add(c.name)
        picked.append(c)

    for c in cols:
        if c.pk:
            add(c)
    for c in cols:
        if c.fk:
            add(c)

    prefer = (
        "name", "title", "username", "status", "role", "nickname",
        "isbn", "author", "stock", "content", "phone",
    )
    by_name = {c.name: c for c in cols}
    for n in prefer:
        if n in by_name:
            add(by_name[n])

    for c in cols:
        if c.not_null and not c.name.endswith("_at"):
            add(c)

    for c in cols:
        add(c)

    return picked


def schema_model(sql: str) -> dict:
    tables = parse_schema_sql(sql)
    relations = infer_relations(tables)
    return {
        "tables": [
            {
                "name": t.name,
                "columns": [asdict(c) for c in t.columns],
                "core_columns": [asdict(c) for c in pick_core_attrs(t.columns)],
            }
            for t in tables
        ],
        "relations": [asdict(r) for r in relations],
    }


def load_schema_model(workspace: Path) -> dict | None:
    path = workspace / "sql" / "schema.sql"
    if not path.exists():
        return None
    return schema_model(path.read_text(encoding="utf-8", errors="ignore"))


# —— SVG 陈氏 E-R（线框、无填色强调）——

ENTITY_HW, ENTITY_HH = 52, 22  # 实体框半宽/半高
ATTR_RH = 13  # 属性椭圆半高


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _attr_rx(name: str) -> float:
    return max(26.0, len(name) * 4.0 + 10)


def _attr_cloud_radius(attrs: list[dict]) -> float:
    """属性均匀绕实体一圈时，保证相邻椭圆不重叠的最小半径。"""
    m = len(attrs)
    if m == 0:
        return 0.0
    max_rx = max((_attr_rx(c["name"]) for c in attrs), default=26.0)
    clear_box = math.hypot(ENTITY_HW, ENTITY_HH) + max_rx + 28
    if m == 1:
        return clear_box
    # 弦长 ≥ 两椭圆宽 + 间距
    need = (2 * max_rx + 18) / (2 * math.sin(math.pi / m))
    return max(clear_box, need)


def _rect_edge(cx: float, cy: float, tx: float, ty: float, hw: float, hh: float) -> tuple[float, float]:
    """从矩形中心到目标点的连线与矩形边交点。"""
    dx, dy = tx - cx, ty - cy
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return cx, cy - hh
    # 与四边求最近交点
    sx = hw / abs(dx) if abs(dx) > 1e-9 else float("inf")
    sy = hh / abs(dy) if abs(dy) > 1e-9 else float("inf")
    t = min(sx, sy)
    return cx + dx * t, cy + dy * t


def _ellipse_edge(cx: float, cy: float, rx: float, ry: float, fx: float, fy: float) -> tuple[float, float]:
    """椭圆上朝向外点 (fx,fy) 的边界点（属性连线落点）。"""
    ox, oy = fx - cx, fy - cy
    if abs(ox) < 1e-9 and abs(oy) < 1e-9:
        return cx, cy - ry
    s = math.hypot(ox / rx, oy / ry) or 1.0
    return cx + ox / s, cy + oy / s


def render_er_svg(model: dict, title: str = "E-R") -> str:
    tables = model.get("tables") or []
    relations = model.get("relations") or []
    if not tables:
        return _svg_wrap(480, 200, '<text x="24" y="100" font-size="14">无表结构</text>')

    n = len(tables)
    clouds = {
        t["name"]: _attr_cloud_radius(t.get("core_columns") or t.get("columns") or [])
        for t in tables
    }
    # 实体中心间距 ≥ 两属性云半径之和
    max_cloud = max(clouds.values()) if clouds else 80
    if n <= 1:
        ring_r = 0.0
    else:
        # 相邻弦长 ≥ 两云半径 + 菱形空隙
        pair_need = 2 * max_cloud + 100
        ring_r = pair_need / (2 * math.sin(math.pi / n))
        ring_r = max(ring_r, 260.0)

    margin = max_cloud + 80
    w = int(2 * (ring_r + margin) + 80)
    h = int(2 * (ring_r + margin) + 100)
    w, h = max(w, 900), max(h, 720)
    cx, cy = w / 2, h / 2 + 10

    entity_pos: dict[str, tuple[float, float]] = {}
    for i, t in enumerate(tables):
        if n == 1:
            entity_pos[t["name"]] = (cx, cy)
        else:
            ang = -math.pi / 2 + 2 * math.pi * i / n
            entity_pos[t["name"]] = (cx + ring_r * math.cos(ang), cy + ring_r * math.sin(ang))

    parts: list[str] = []
    parts.append(
        f'<text x="24" y="28" font-family="serif" font-size="16">{_esc(title)}</text>'
    )
    parts.append(
        '<text x="24" y="48" font-family="sans-serif" font-size="11" fill="#333">'
        "方框=实体 · 菱形=联系 · 椭圆=属性 · 下划线=主键 · 波浪线=外键 · 基数标在连线一侧"
        "</text>"
    )

    # 联系：线接到实体框边，菱形放中点并向圆心略偏，避免贴实体
    for ri, r in enumerate(relations):
        lp = entity_pos.get(r["left"])
        rp = entity_pos.get(r["right"])
        if not lp or not rp:
            continue
        mx, my = (lp[0] + rp[0]) / 2, (lp[1] + rp[1]) / 2
        dx, dy = rp[0] - lp[0], rp[1] - lp[1]
        length = math.hypot(dx, dy) or 1
        # 垂直偏移，多条联系错开
        nx, ny = -dy / length, dx / length
        off = ((ri % 5) - 2) * 28
        mx, my = mx + nx * off, my + ny * off
        # 略向图心拉，躲开实体框
        toward = math.hypot(cx - mx, cy - my) or 1
        mx += (cx - mx) / toward * 12
        my += (cy - my) / toward * 12

        e1 = _rect_edge(lp[0], lp[1], mx, my, ENTITY_HW, ENTITY_HH)
        e2 = _rect_edge(rp[0], rp[1], mx, my, ENTITY_HW, ENTITY_HH)
        parts.append(
            f'<line x1="{e1[0]:.1f}" y1="{e1[1]:.1f}" x2="{mx:.1f}" y2="{my:.1f}" '
            f'stroke="#000" stroke-width="1" fill="none"/>'
        )
        parts.append(
            f'<line x1="{mx:.1f}" y1="{my:.1f}" x2="{e2[0]:.1f}" y2="{e2[1]:.1f}" '
            f'stroke="#000" stroke-width="1" fill="none"/>'
        )
        # 基数靠近实体一侧（框边与菱形之间）
        c1x, c1y = e1[0] * 0.55 + mx * 0.45, e1[1] * 0.55 + my * 0.45
        cnx, cny = e2[0] * 0.55 + mx * 0.45, e2[1] * 0.55 + my * 0.45
        # 再垂直微移，避免压在线上
        parts.append(
            f'<text x="{c1x + nx * 10:.1f}" y="{c1y + ny * 10:.1f}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="12">{_esc(r["card_left"])}</text>'
        )
        parts.append(
            f'<text x="{cnx + nx * 10:.1f}" y="{cny + ny * 10:.1f}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="12">{_esc(r["card_right"])}</text>'
        )
        dw, dh = 48, 24
        diamond = (
            f"{mx:.1f},{my - dh:.1f} {mx + dw:.1f},{my:.1f} "
            f"{mx:.1f},{my + dh:.1f} {mx - dw:.1f},{my:.1f}"
        )
        parts.append(
            f'<polygon points="{diamond}" fill="#fff" stroke="#000" stroke-width="1.2"/>'
        )
        parts.append(
            f'<text x="{mx:.1f}" y="{my + 4:.1f}" text-anchor="middle" '
            f'font-family="serif" font-size="12">{_esc(r["name"])}</text>'
        )

    # 实体 + 属性：均匀满周分布，半径按云尺寸计算；连线框边→椭圆边
    for t in tables:
        name = t["name"]
        x, y = entity_pos[name]
        parts.append(
            f'<rect x="{x - ENTITY_HW:.1f}" y="{y - ENTITY_HH:.1f}" '
            f'width="{ENTITY_HW * 2:.1f}" height="{ENTITY_HH * 2:.1f}" '
            f'fill="#fff" stroke="#000" stroke-width="1.5"/>'
        )
        label = name.replace("sys_", "")
        parts.append(
            f'<text x="{x:.1f}" y="{y + 5:.1f}" text-anchor="middle" '
            f'font-family="serif" font-size="13" font-weight="600">{_esc(label)}</text>'
        )

        attrs = t.get("core_columns") or t.get("columns") or []
        m = len(attrs)
        if m == 0:
            continue
        ar = clouds[name]
        # 从「背离图心」方向起排，视觉上属性在外侧更清晰
        base = math.atan2(y - cy, x - cx) if n > 1 else -math.pi / 2
        for ai, col in enumerate(attrs):
            ang = base + 2 * math.pi * ai / m
            ax = x + ar * math.cos(ang)
            ay = y + ar * math.sin(ang)
            rx = _attr_rx(col["name"])
            p0 = _rect_edge(x, y, ax, ay, ENTITY_HW, ENTITY_HH)
            p1 = _ellipse_edge(ax, ay, rx, ATTR_RH, p0[0], p0[1])
            parts.append(
                f'<line x1="{p0[0]:.1f}" y1="{p0[1]:.1f}" x2="{p1[0]:.1f}" y2="{p1[1]:.1f}" '
                f'stroke="#000" stroke-width="0.8" fill="none"/>'
            )
            parts.append(
                f'<ellipse cx="{ax:.1f}" cy="{ay:.1f}" rx="{rx:.1f}" ry="{ATTR_RH:.1f}" '
                f'fill="#fff" stroke="#000" stroke-width="1"/>'
            )
            tw = min(rx * 1.6, len(col["name"]) * 5.2)
            deco = ""
            if col.get("pk"):
                deco = (
                    f'<line x1="{ax - tw / 2:.1f}" y1="{ay + 7:.1f}" '
                    f'x2="{ax + tw / 2:.1f}" y2="{ay + 7:.1f}" stroke="#000" stroke-width="1"/>'
                )
            elif col.get("fk"):
                wave = []
                x0 = ax - tw / 2
                steps = max(4, int(tw / 6))
                for si in range(steps + 1):
                    wx = x0 + tw * si / steps
                    wy = ay + 7 + (2 if si % 2 else -2)
                    wave.append(f"{wx:.1f},{wy:.1f}")
                deco = (
                    f'<polyline points="{" ".join(wave)}" fill="none" stroke="#000" stroke-width="1"/>'
                )
            parts.append(
                f'<text x="{ax:.1f}" y="{ay + 4:.1f}" text-anchor="middle" '
                f'font-family="sans-serif" font-size="10">{_esc(col["name"])}</text>'
            )
            if deco:
                parts.append(deco)

    return _svg_wrap(w, h, "\n".join(parts))


def _svg_wrap(w: int, h: int, inner: str) -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">\n'
        f'<rect width="100%" height="100%" fill="#fff"/>\n'
        f"{inner}\n</svg>\n"
    )
