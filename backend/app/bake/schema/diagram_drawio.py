"""论文图 → Draw.io（.drawio / mxGraph），只读 pack_* 叠补丁后的 model。

几何允许丑；必须可拖。结构 id 与 model 对齐，供同源测试。
"""

from __future__ import annotations

from typing import Any

from app.bake.schema.diagram_export import (
    build_mxfile,
    er_own_column_names,
    mx_edge,
    mx_vertex,
    stable_cell_id,
)

_ENT_STYLE = (
    "rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;"
    "fontColor=#000000;align=center;verticalAlign=middle;"
)
_DIAMOND_STYLE = (
    "rhombus;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;"
    "fontColor=#000000;"
)
_CLASS_STYLE = (
    "swimlane;fontStyle=1;align=center;verticalAlign=top;childLayout=stackLayout;"
    "horizontal=1;startSize=26;horizontalStack=0;resizeParent=1;resizeParentMax=0;"
    "resizeLast=0;collapsible=0;marginBottom=0;fillColor=#ffffff;strokeColor=#000000;"
)
_ATTR_STYLE = (
    "text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;"
    "spacingLeft=4;spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];"
    "portConstraint=eastwest;fontSize=11;"
)
_MODULE_STYLE = _ENT_STYLE
_ACTOR_STYLE = (
    "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;"
    "outlineConnect=0;fillColor=#ffffff;strokeColor=#000000;"
)
_UC_STYLE = (
    "ellipse;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;"
    "fontColor=#000000;"
)
_EDGE = "endArrow=block;html=1;rounded=0;strokeColor=#000000;fontSize=10;"
_EDGE_CARD = (
    "endArrow=none;html=1;rounded=0;strokeColor=#000000;fontSize=10;"
    "startArrow=none;"
)


def er_model_to_drawio(
    model: dict[str, Any] | None,
    *,
    mode: str = "total",
    entity: str | None = None,
) -> str:
    """E-R 总图或实体属性分图。"""
    model = model if isinstance(model, dict) else {}
    mode_n = (mode or "total").strip().lower()
    if mode_n == "part":
        return _er_part_drawio(model, entity=entity)
    return _er_total_drawio(model)


def _er_total_drawio(model: dict[str, Any]) -> str:
    tables = [
        t
        for t in (model.get("tables") or [])
        if isinstance(t, dict)
        and t.get("name")
        and not t.get("assoc_link")
        and not t.get("role_of")
    ]
    # 角色拆分实体也要进总图
    role_tables = [
        t
        for t in (model.get("tables") or [])
        if isinstance(t, dict) and t.get("name") and t.get("role_of")
    ]
    tables = tables + role_tables
    rels = [r for r in (model.get("relations") or []) if isinstance(r, dict)]

    cells: list[str] = []
    id_by_name: dict[str, str] = {}
    cols = max(1, int(len(tables) ** 0.5 + 0.99))
    for i, t in enumerate(tables):
        name = str(t.get("name") or "")
        lab = str(t.get("label") or name)
        cid = stable_cell_id("er", name)
        id_by_name[name] = cid
        x = (i % cols) * 200 + 40
        y = (i // cols) * 120 + 40
        cells.append(
            mx_vertex(cid, lab, x=x, y=y, w=140, h=48, style=_ENT_STYLE)
        )

    for j, r in enumerate(rels):
        left = str(r.get("left") or "")
        right = str(r.get("right") or "")
        if left not in id_by_name or right not in id_by_name:
            continue
        rid = stable_cell_id("err", str(r.get("name") or f"r{j}"))
        lab = str(r.get("label") or r.get("via") or "关联")
        # 菱形放两实体中间偏上
        # 粗排：跟边序号走
        dx = 80 + (j % cols) * 200
        dy = 80 + (j // cols) * 120 + 60
        cells.append(
            mx_vertex(rid, lab, x=dx, y=dy, w=100, h=56, style=_DIAMOND_STYLE)
        )
        cl = str(r.get("card_left") or "1")
        cr = str(r.get("card_right") or "n")
        cells.append(
            mx_edge(
                f"{rid}_l",
                source=id_by_name[left],
                target=rid,
                value=cl,
                style=_EDGE_CARD,
            )
        )
        cells.append(
            mx_edge(
                f"{rid}_r",
                source=rid,
                target=id_by_name[right],
                value=cr,
                style=_EDGE_CARD,
            )
        )

    title = str(model.get("title") or "E-R图")
    rows = max(1, (len(tables) + cols - 1) // cols)
    return build_mxfile(
        cells,
        diagram_name=title,
        page_w=max(1200, cols * 220),
        page_h=max(900, rows * 160 + 200),
    )


def _er_part_drawio(model: dict[str, Any], *, entity: str | None) -> str:
    ent = (entity or str(model.get("er_entity") or "")).strip()
    table = None
    for t in model.get("tables") or []:
        if isinstance(t, dict) and str(t.get("name") or "") == ent:
            table = t
            break
    if not table:
        return build_mxfile([], diagram_name=ent or "实体属性")

    title = str(table.get("label") or ent)
    names = er_own_column_names(table)
    cells: list[str] = []
    box_id = stable_cell_id("erp", ent)
    attr_lines: list[str] = [title]
    for c in table.get("own_columns") or []:
        if not isinstance(c, dict) or c.get("fk"):
            continue
        attr_lines.append(str(c.get("label") or c.get("name") or "").strip())
    if len(attr_lines) == 1:
        attr_lines.extend(names)
    value = "\n".join(x for x in attr_lines if x)
    h = max(80, 28 + len(attr_lines) * 22)
    cells.append(
        mx_vertex(box_id, value, x=80, y=60, w=240, h=h, style=_ENT_STYLE)
    )
    return build_mxfile(cells, diagram_name=f"{title}-实体属性", page_w=600, page_h=max(400, h + 120))


def class_model_to_drawio(model: dict[str, Any] | None) -> str:
    from app.bake.schema.class_model import class_box_title

    model = model if isinstance(model, dict) else {}
    classes = [c for c in (model.get("classes") or []) if isinstance(c, dict) and c.get("id")]
    assocs = [a for a in (model.get("associations") or []) if isinstance(a, dict)]

    cells: list[str] = []
    id_map: dict[str, str] = {}
    cols = max(1, int(len(classes) ** 0.5 + 0.99))
    for i, cls in enumerate(classes):
        tid = str(cls.get("id") or "")
        cid = stable_cell_id("cls", tid)
        id_map[tid] = cid
        name = class_box_title(cls) or str(cls.get("name") or cls.get("label") or tid)
        attrs = [
            str(a.get("display") or a.get("name") or "")
            for a in (cls.get("attributes") or [])
            if isinstance(a, dict)
        ][:12]
        methods = [
            str(m.get("display") or m.get("name") or "")
            for m in (cls.get("methods") or [])
            if isinstance(m, dict)
        ][:8]
        lines = [name] + [x for x in attrs if x] + [x for x in methods if x]
        value = "\n".join(lines)
        x = (i % cols) * 220 + 40
        y = (i // cols) * 200 + 40
        h = max(72, 28 + len(lines) * 16)
        cells.append(
            mx_vertex(cid, value, x=x, y=y, w=180, h=h, style=_CLASS_STYLE)
        )

    for j, a in enumerate(assocs):
        frm = str(a.get("from") or a.get("from_class") or "")
        to = str(a.get("to") or a.get("to_class") or "")
        # associations 里 from/to 是表 id
        src = id_map.get(frm) or id_map.get(str(a.get("from_class") or ""))
        tgt = id_map.get(to) or id_map.get(str(a.get("to_class") or ""))
        if not src or not tgt:
            # from_class 可能是类名不是表 id
            for tid, cid in id_map.items():
                c = next((x for x in classes if str(x.get("id")) == tid), None)
                if c and str(c.get("name") or "") == frm:
                    src = cid
                if c and str(c.get("name") or "") == to:
                    tgt = cid
        if not src or not tgt:
            continue
        kind = str(a.get("kind") or "association")
        style = _EDGE
        if kind == "inheritance":
            style = "endArrow=block;endFill=0;html=1;strokeColor=#000000;"
        elif kind == "implementation":
            style = "endArrow=block;endFill=0;dashed=1;html=1;strokeColor=#000000;"
        elif kind == "composition":
            style = "startArrow=diamondThin;startFill=1;endArrow=none;html=1;strokeColor=#000000;"
        elif kind == "aggregation":
            style = "startArrow=diamondThin;startFill=0;endArrow=none;html=1;strokeColor=#000000;"
        elif kind == "dependency":
            style = "endArrow=open;dashed=1;html=1;strokeColor=#000000;"
        eid = stable_cell_id("clse", f"{frm}_{to}_{j}")
        cells.append(
            mx_edge(
                eid,
                source=src,
                target=tgt,
                value=str(a.get("label") or ""),
                style=style,
            )
        )

    title = str(model.get("figure_title") or model.get("title") or "系统类图")
    rows = max(1, (len(classes) + cols - 1) // cols)
    return build_mxfile(
        cells,
        diagram_name=title,
        page_w=max(1200, cols * 240),
        page_h=max(900, rows * 220),
    )


def module_model_to_drawio(model: dict[str, Any] | None) -> str:
    from app.bake.schema.modules import iter_nodes

    model = model if isinstance(model, dict) else {}
    nodes = [n for n in iter_nodes(model) if isinstance(n, dict) and n.get("id")]
    # 隐藏节点跳过
    nodes = [n for n in nodes if not n.get("hidden")]

    cells: list[str] = []
    id_map: dict[str, str] = {}
    # 按深度粗排
    by_depth: dict[int, list[dict[str, Any]]] = {}
    for n in nodes:
        d = int(n.get("depth") or 0)
        by_depth.setdefault(d, []).append(n)

    for depth in sorted(by_depth.keys()):
        row = by_depth[depth]
        for i, n in enumerate(row):
            nid = str(n.get("id") or "")
            cid = stable_cell_id("mod", nid)
            id_map[nid] = cid
            lab = str(n.get("label") or nid)
            x = i * 180 + 40
            y = depth * 100 + 40
            cells.append(
                mx_vertex(cid, lab, x=x, y=y, w=150, h=44, style=_MODULE_STYLE)
            )

    # 父子边
    for n in nodes:
        nid = str(n.get("id") or "")
        pid = str(n.get("parent") or "")
        if not pid or pid not in id_map or nid not in id_map:
            # 从 children 反推
            continue
        cells.append(
            mx_edge(
                stable_cell_id("mode", f"{pid}_{nid}"),
                source=id_map[pid],
                target=id_map[nid],
                style=_EDGE_CARD,
            )
        )
    # children 边（若无 parent 字段）
    for n in nodes:
        nid = str(n.get("id") or "")
        if nid not in id_map:
            continue
        for ch in n.get("children") or []:
            if not isinstance(ch, dict):
                continue
            cid = str(ch.get("id") or "")
            if cid not in id_map:
                continue
            cells.append(
                mx_edge(
                    stable_cell_id("mode", f"{nid}_{cid}"),
                    source=id_map[nid],
                    target=id_map[cid],
                    style=_EDGE_CARD,
                )
            )

    title = str(model.get("title") or "功能模块图")
    return build_mxfile(cells, diagram_name=title)


def usecase_model_to_drawio(model: dict[str, Any] | None) -> str:
    model = model if isinstance(model, dict) else {}
    actor = model.get("actor") if isinstance(model.get("actor"), dict) else {}
    actor_id = str(actor.get("id") or "actor")
    actor_lab = str(actor.get("label") or actor_id)
    level1 = [u for u in (model.get("level1") or []) if isinstance(u, dict)]

    cells: list[str] = []
    aid = stable_cell_id("uca", actor_id)
    cells.append(
        mx_vertex(aid, actor_lab, x=40, y=200, w=60, h=100, style=_ACTOR_STYLE)
    )

    for i, uc in enumerate(level1):
        uid = str(uc.get("id") or f"uc{i}")
        ulab = str(uc.get("label") or uid)
        cid = stable_cell_id("ucu", uid)
        x = 220
        y = 40 + i * 110
        cells.append(mx_vertex(cid, ulab, x=x, y=y, w=160, h=70, style=_UC_STYLE))
        cells.append(
            mx_edge(
                stable_cell_id("uce", f"{actor_id}_{uid}"),
                source=aid,
                target=cid,
                style=_EDGE_CARD,
            )
        )
        kids = [k for k in (uc.get("includes") or []) if isinstance(k, dict)]
        for j, kid in enumerate(kids):
            if kid.get("hidden"):
                continue
            kid_id = str(kid.get("id") or f"{uid}_k{j}")
            kid_lab = str(kid.get("label") or kid_id)
            kid_cid = stable_cell_id("ucu", kid_id)
            cells.append(
                mx_vertex(
                    kid_cid,
                    kid_lab,
                    x=440,
                    y=y + j * 50,
                    w=150,
                    h=50,
                    style=_UC_STYLE,
                )
            )
            rel = str(kid.get("relation") or "include")
            cells.append(
                mx_edge(
                    stable_cell_id("uce", f"{uid}_{kid_id}"),
                    source=cid,
                    target=kid_cid,
                    value=f"«{rel}»",
                    style="endArrow=open;dashed=1;html=1;strokeColor=#000000;",
                )
            )

    title = str(model.get("title") or "用例图")
    return build_mxfile(
        cells,
        diagram_name=title,
        page_w=900,
        page_h=max(700, 80 + len(level1) * 120),
    )


def architecture_model_to_drawio(model: dict[str, Any] | None) -> str:
    """逻辑架构图：角色 → 界面 → Vue → SpringBoot → MySQL，可拖。"""
    model = model if isinstance(model, dict) else {}
    roles = [r for r in (model.get("roles") or []) if isinstance(r, dict) and r.get("id")]
    if not roles:
        roles = [{"id": "user", "label": "用户"}]
    cells: list[str] = []
    layer_ids = [
        ("ui", "界面"),
        ("vue", "Vue"),
        ("spring", "SpringBoot"),
        ("mysql", "MySQL"),
    ]
    n = max(1, len(roles))
    role_w = 120.0
    gap = 24.0
    total_w = n * role_w + (n - 1) * gap
    start_x = 80.0
    for i, r in enumerate(roles):
        rid = str(r.get("id") or f"r{i}")
        cid = stable_cell_id("arch", rid)
        x = start_x + i * (role_w + gap)
        cells.append(
            mx_vertex(
                cid,
                str(r.get("label") or rid),
                x=x,
                y=40,
                w=role_w,
                h=44,
                style=_ENT_STYLE,
            )
        )
    layer_cids: list[str] = []
    layer_y0 = 140.0
    layer_h = 48.0
    layer_gap = 70.0
    layer_w = max(220.0, total_w)
    layer_x = start_x + (total_w - layer_w) / 2.0
    for j, (lid, lab) in enumerate(layer_ids):
        cid = stable_cell_id("arch", lid)
        layer_cids.append(cid)
        y = layer_y0 + j * (layer_h + layer_gap)
        cells.append(
            mx_vertex(cid, lab, x=layer_x, y=y, w=layer_w, h=layer_h, style=_ENT_STYLE)
        )
        if j > 0:
            edge_lab = "HTTPS / 发起请求" if j == 1 else ""
            cells.append(
                mx_edge(
                    stable_cell_id("arche", f"{layer_ids[j - 1][0]}_{lid}"),
                    source=layer_cids[j - 1],
                    target=cid,
                    value=edge_lab,
                    style=_EDGE,
                )
            )
    ui_cid = layer_cids[0]
    for r in roles:
        rid = str(r.get("id") or "")
        cells.append(
            mx_edge(
                stable_cell_id("arche", f"{rid}_ui"),
                source=stable_cell_id("arch", rid),
                target=ui_cid,
                style=_EDGE,
            )
        )
    title = str(model.get("figure_title") or model.get("title") or "系统逻辑架构图")
    return build_mxfile(
        cells,
        diagram_name=title,
        page_w=int(max(900, start_x * 2 + total_w + 80)),
        page_h=int(layer_y0 + len(layer_ids) * (layer_h + layer_gap) + 80),
    )


def expected_architecture_vertex_ids(model: dict[str, Any]) -> set[str]:
    out: set[str] = {
        stable_cell_id("arch", lid) for lid in ("ui", "vue", "spring", "mysql")
    }
    roles = [r for r in (model.get("roles") or []) if isinstance(r, dict) and r.get("id")]
    if not roles:
        out.add(stable_cell_id("arch", "user"))
    else:
        for r in roles:
            out.add(stable_cell_id("arch", str(r.get("id"))))
    return out


def expected_er_vertex_ids(model: dict[str, Any], *, mode: str = "total", entity: str | None = None) -> set[str]:
    mode_n = (mode or "total").strip().lower()
    if mode_n == "part":
        ent = (entity or str(model.get("er_entity") or "")).strip()
        return {stable_cell_id("erp", ent)} if ent else set()
    out: set[str] = set()
    for t in model.get("tables") or []:
        if not isinstance(t, dict) or not t.get("name"):
            continue
        if t.get("assoc_link"):
            continue
        out.add(stable_cell_id("er", str(t.get("name"))))
    return out


def expected_class_vertex_ids(model: dict[str, Any]) -> set[str]:
    return {
        stable_cell_id("cls", str(c.get("id")))
        for c in (model.get("classes") or [])
        if isinstance(c, dict) and c.get("id")
    }


def expected_usecase_vertex_ids(model: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    actor = model.get("actor") if isinstance(model.get("actor"), dict) else {}
    if actor.get("id"):
        out.add(stable_cell_id("uca", str(actor.get("id"))))
    for uc in model.get("level1") or []:
        if not isinstance(uc, dict) or not uc.get("id"):
            continue
        out.add(stable_cell_id("ucu", str(uc.get("id"))))
        for kid in uc.get("includes") or []:
            if isinstance(kid, dict) and kid.get("id") and not kid.get("hidden"):
                out.add(stable_cell_id("ucu", str(kid.get("id"))))
    return out
