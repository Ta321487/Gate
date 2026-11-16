"""论文图同源导出合同：三档（SVG / Mermaid / Draw.io）共用同一 model。

真源见 docs/thesis-diagram-export.md。本模块只提供转义、mxFile 壳与同源断言；
各图 to_drawio / to_mermaid 放在 diagram_drawio.py / diagram_mermaid.py。
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any, Iterable
from xml.sax.saxutils import escape as _xml_escape

# 导出能力声明（给 API / UI / 测试共用）
EXPORT_KINDS = (
    "er",
    "modules",
    "architecture",
    "classes",
    "sequences",
    "activities",
    "usecases",
)

# M1 优先 Draw.io 的种类
DRAWIO_M1_KINDS = ("er", "classes", "modules", "usecases")


def xml_escape(text: str) -> str:
    return _xml_escape(str(text or ""), {"'": "&apos;", '"': "&quot;"})


def mx_value_escape(text: str) -> str:
    """draw.io cell value：先 XML 再保留换行用 &#xa;。"""
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    return xml_escape(raw).replace("\n", "&#xa;")


def _mx_diagram_block(
    cells: list[str],
    *,
    diagram_id: str,
    diagram_name: str,
    page_w: int,
    page_h: int,
) -> str:
    name = xml_escape(diagram_name or "diagram")
    did = xml_escape(diagram_id or "gf")
    body = "\n".join(cells)
    return (
        f'  <diagram id="{did}" name="{name}">\n'
        f'    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" '
        f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" '
        f'pageScale="1" pageWidth="{int(page_w)}" pageHeight="{int(page_h)}" '
        f'math="0" shadow="0">\n'
        "      <root>\n"
        '        <mxCell id="0"/>\n'
        '        <mxCell id="1" parent="0"/>\n'
        f"{body}\n"
        "      </root>\n"
        "    </mxGraphModel>\n"
        "  </diagram>"
    )


def build_mxfile(
    cells: list[str],
    *,
    diagram_name: str = "diagram",
    page_w: int = 1200,
    page_h: int = 900,
    diagram_id: str = "gf",
) -> str:
    """拼合法 .drawio（mxfile）正文。cells 为已转义的 <mxCell .../> 片段。"""
    block = _mx_diagram_block(
        cells,
        diagram_id=diagram_id,
        diagram_name=diagram_name,
        page_w=page_w,
        page_h=page_h,
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxfile host="app.diagrams.net" agent="graduate-factory" version="22.0.0">\n'
        f"{block}\n"
        "</mxfile>\n"
    )


def build_mxfile_pages(pages: list[dict[str, Any]]) -> str:
    """多页 .drawio：每页独立 diagram（实体属性图批量导出）。

    pages 项：name / cells / page_w / page_h / 可选 id。
    """
    blocks: list[str] = []
    for i, page in enumerate(pages or []):
        if not isinstance(page, dict):
            continue
        cells = page.get("cells") or []
        if not isinstance(cells, list):
            cells = []
        blocks.append(
            _mx_diagram_block(
                cells,
                diagram_id=str(page.get("id") or f"gf-{i}"),
                diagram_name=str(page.get("name") or f"page-{i + 1}"),
                page_w=int(page.get("page_w") or 1200),
                page_h=int(page.get("page_h") or 900),
            )
        )
    if not blocks:
        blocks.append(
            _mx_diagram_block(
                [],
                diagram_id="gf-0",
                diagram_name="空",
                page_w=600,
                page_h=400,
            )
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxfile host="app.diagrams.net" agent="graduate-factory" version="22.0.0">\n'
        + "\n".join(blocks)
        + "\n</mxfile>\n"
    )


def mx_vertex(
    cell_id: str,
    value: str,
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    style: str,
    parent: str = "1",
) -> str:
    cid = xml_escape(cell_id)
    val = mx_value_escape(value)
    st = xml_escape(style)
    return (
        f'        <mxCell id="{cid}" value="{val}" style="{st}" vertex="1" '
        f'parent="{xml_escape(parent)}">'
        f'<mxGeometry x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'as="geometry"/></mxCell>'
    )


def mx_edge(
    cell_id: str,
    *,
    source: str,
    target: str,
    value: str = "",
    style: str = "endArrow=block;html=1;rounded=0;",
    parent: str = "1",
) -> str:
    cid = xml_escape(cell_id)
    val = mx_value_escape(value)
    st = xml_escape(style)
    return (
        f'        <mxCell id="{cid}" value="{val}" style="{st}" edge="1" '
        f'parent="{xml_escape(parent)}" source="{xml_escape(source)}" '
        f'target="{xml_escape(target)}">'
        f'<mxGeometry relative="1" as="geometry"/></mxCell>'
    )


_ID_SAFE = re.compile(r"[^A-Za-z0-9_\-:.]+")


def stable_cell_id(prefix: str, raw: str) -> str:
    base = _ID_SAFE.sub("_", str(raw or "").strip()) or "x"
    return f"{prefix}_{base}"[:120]


def parse_drawio_vertex_ids(xml_text: str) -> set[str]:
    """从 .drawio XML 收集 vertex 的 id（同源测试用）。"""
    root = ET.fromstring(xml_text)
    out: set[str] = set()
    for cell in root.iter("mxCell"):
        if cell.get("vertex") == "1":
            cid = cell.get("id")
            if cid:
                out.add(cid)
    return out


def parse_drawio_edge_endpoints(xml_text: str) -> set[tuple[str, str]]:
    root = ET.fromstring(xml_text)
    out: set[tuple[str, str]] = set()
    for cell in root.iter("mxCell"):
        if cell.get("edge") == "1":
            s, t = cell.get("source"), cell.get("target")
            if s and t:
                out.add((s, t))
    return out


def assert_drawio_ids_subset(
    xml_text: str,
    *,
    expected_vertex_ids: Iterable[str],
    expected_edge_pairs: Iterable[tuple[str, str]] | None = None,
) -> None:
    """导出顶点/边必须能在期望集合中找到（允许稳定 id 前缀策略由调用方给定）。"""
    verts = parse_drawio_vertex_ids(xml_text)
    expect_v = set(expected_vertex_ids)
    missing_v = expect_v - verts
    if missing_v:
        raise AssertionError(f"drawio missing vertices: {sorted(missing_v)[:20]}")
    if expected_edge_pairs is not None:
        edges = parse_drawio_edge_endpoints(xml_text)
        expect_e = set(expected_edge_pairs)
        missing_e = expect_e - edges
        if missing_e:
            raise AssertionError(f"drawio missing edges: {list(missing_e)[:20]}")


def er_own_column_names(table: dict[str, Any]) -> list[str]:
    """实体属性图列名：优先 own_columns，否则过滤 fk。"""
    own = table.get("own_columns")
    if isinstance(own, list) and own:
        return [
            str(c.get("name") or "").strip()
            for c in own
            if isinstance(c, dict) and str(c.get("name") or "").strip()
        ]
    out: list[str] = []
    for c in table.get("columns") or []:
        if not isinstance(c, dict) or c.get("fk"):
            continue
        n = str(c.get("name") or "").strip()
        if n:
            out.append(n)
    return out


def assert_er_part_no_fk(model: dict[str, Any], *, entity: str) -> None:
    """分图属性不得含外键列（老师 4.6.1）。"""
    ent = (entity or "").strip()
    for t in model.get("tables") or []:
        if not isinstance(t, dict):
            continue
        if str(t.get("name") or "") != ent:
            continue
        for c in t.get("own_columns") or []:
            if isinstance(c, dict) and c.get("fk"):
                raise AssertionError(
                    f"er part own_columns still has fk: {c.get('name')}"
                )
        for c in t.get("columns") or []:
            if not isinstance(c, dict) or not c.get("fk"):
                continue
            # 允许 columns 全量保留 FK；导出文本不得出现这些名
            pass
        return
    raise AssertionError(f"er entity not found: {ent}")
