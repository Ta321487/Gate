"""论文图 → Mermaid，只读 pack_* 叠补丁后的 model（与 SVG / Draw.io 同源）。

供粘贴 diagrams.net 出结构参考；几何精调认 .drawio。
"""

from __future__ import annotations

import re
from typing import Any

from app.bake.schema.diagram_export import er_own_column_names, stable_cell_id

_ID_SAFE = re.compile(r"[^A-Za-z0-9_]+")


def mermaid_id(raw: str, *, prefix: str = "") -> str:
    base = _ID_SAFE.sub("_", str(raw or "").strip()) or "x"
    if base[0].isdigit():
        base = f"n_{base}"
    out = f"{prefix}{base}" if prefix else base
    return out[:80]


def mermaid_label(text: str) -> str:
    """节点/消息可见字：去会打断 Mermaid 的字符。"""
    t = str(text or "").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    t = t.replace('"', "'").replace("#", "").strip()
    return t or "-"


def _header(kind: str, title: str) -> list[str]:
    lines = [f"%% {mermaid_label(title)}", f"%% graduate-factory homologous export"]
    lines.append(kind)
    return lines


def sequence_diagram_to_mermaid(diagram: dict[str, Any] | None) -> str:
    """单张序列图 → sequenceDiagram。"""
    d = diagram if isinstance(diagram, dict) else {}
    title = str(d.get("figure_title") or d.get("title") or "序列图")
    lines = _header("sequenceDiagram", title)
    parts = [p for p in (d.get("participants") or []) if isinstance(p, dict) and p.get("id")]
    id_map: dict[str, str] = {}
    for p in parts:
        pid = str(p.get("id") or "")
        mid = mermaid_id(pid)
        id_map[pid] = mid
        lab = mermaid_label(str(p.get("label") or pid))
        lines.append(f"  participant {mid} as {lab}")
    if not parts:
        for pid, lab in (
            ("actor", "角色"),
            ("page", "页面"),
            ("controller", "控制器"),
            ("db", "数据库"),
        ):
            id_map[pid] = mermaid_id(pid)
            lines.append(f"  participant {id_map[pid]} as {lab}")

    for m in d.get("messages") or []:
        if not isinstance(m, dict):
            continue
        frm = id_map.get(str(m.get("from") or "")) or mermaid_id(str(m.get("from") or "x"))
        to = id_map.get(str(m.get("to") or "")) or mermaid_id(str(m.get("to") or "x"))
        text = mermaid_label(str(m.get("text") or ""))
        direction = str(m.get("dir") or "request").strip().lower()
        if direction == "response":
            lines.append(f"  {frm}-->>{to}: {text}")
        elif direction == "self":
            lines.append(f"  {frm}->{frm}: {text}")
        else:
            lines.append(f"  {frm}->>{to}: {text}")
    return "\n".join(lines) + "\n"


def sequence_model_to_mermaid(model: dict[str, Any] | None, *, index: int = 0) -> str:
    model = model if isinstance(model, dict) else {}
    diagrams = [x for x in (model.get("diagrams") or []) if isinstance(x, dict)]
    if not diagrams:
        return sequence_diagram_to_mermaid({})
    i = max(0, min(int(index), len(diagrams) - 1))
    return sequence_diagram_to_mermaid(diagrams[i])


def activity_diagram_to_mermaid(diagram: dict[str, Any] | None) -> str:
    """单张活动图 → flowchart TD。"""
    d = diagram if isinstance(diagram, dict) else {}
    title = str(d.get("figure_title") or d.get("title") or "活动图")
    lines = _header("flowchart TD", title)
    nodes = [n for n in (d.get("nodes") or []) if isinstance(n, dict) and n.get("id")]
    for n in nodes:
        nid = mermaid_id(str(n.get("id")))
        kind = str(n.get("kind") or "action")
        if kind == "start":
            lines.append(f"  {nid}((开始))")
        elif kind == "end":
            lines.append(f"  {nid}((结束))")
        elif kind == "decision":
            q = mermaid_label(str(n.get("decision_of") or n.get("text") or "?"))
            lines.append(f'  {nid}{{"{q}"}}')
        else:
            lab = mermaid_label(str(n.get("text") or n.get("id") or ""))
            lines.append(f'  {nid}["{lab}"]')
    for e in d.get("edges") or []:
        if not isinstance(e, dict):
            continue
        frm = mermaid_id(str(e.get("from") or e.get("frm") or ""))
        to = mermaid_id(str(e.get("to") or ""))
        if not frm or not to or frm == "x" or to == "x":
            continue
        guard = mermaid_label(str(e.get("guard") or e.get("label") or ""))
        if guard and guard != "-":
            lines.append(f"  {frm} -->|{guard}| {to}")
        else:
            lines.append(f"  {frm} --> {to}")
    return "\n".join(lines) + "\n"


def activity_model_to_mermaid(model: dict[str, Any] | None, *, index: int = 0) -> str:
    model = model if isinstance(model, dict) else {}
    diagrams = [x for x in (model.get("diagrams") or []) if isinstance(x, dict)]
    if not diagrams:
        return activity_diagram_to_mermaid({})
    i = max(0, min(int(index), len(diagrams) - 1))
    return activity_diagram_to_mermaid(diagrams[i])


def class_model_to_mermaid(model: dict[str, Any] | None) -> str:
    model = model if isinstance(model, dict) else {}
    title = str(model.get("figure_title") or model.get("title") or "系统类图")
    lines = _header("classDiagram", title)
    classes = [c for c in (model.get("classes") or []) if isinstance(c, dict) and c.get("id")]
    id_map: dict[str, str] = {}
    for c in classes:
        tid = str(c.get("id") or "")
        mid = mermaid_id(tid, prefix="C_")
        id_map[tid] = mid
        name = mermaid_label(str(c.get("name") or c.get("label") or tid))
        lines.append(f"  class {mid} {{")
        lines.append(f"    {name}")
        for a in (c.get("attributes") or [])[:12]:
            if not isinstance(a, dict):
                continue
            disp = mermaid_label(str(a.get("display") or a.get("name") or ""))
            if disp and disp != "-":
                lines.append(f"    {disp}")
        for m in (c.get("methods") or [])[:8]:
            if not isinstance(m, dict):
                continue
            disp = mermaid_label(str(m.get("display") or m.get("name") or ""))
            if disp and disp != "-":
                lines.append(f"    {disp}")
        lines.append("  }")

    for a in model.get("associations") or []:
        if not isinstance(a, dict):
            continue
        frm = str(a.get("from") or a.get("from_class") or "")
        to = str(a.get("to") or a.get("to_class") or "")
        src = id_map.get(frm)
        tgt = id_map.get(to)
        if not src or not tgt:
            for tid, mid in id_map.items():
                c = next((x for x in classes if str(x.get("id")) == tid), None)
                if c and str(c.get("name") or "") == frm:
                    src = mid
                if c and str(c.get("name") or "") == to:
                    tgt = mid
        if not src or not tgt:
            continue
        kind = str(a.get("kind") or "association")
        if kind == "inheritance":
            lines.append(f"  {tgt} <|-- {src}")
        elif kind == "implementation":
            lines.append(f"  {tgt} <|.. {src}")
        elif kind == "composition":
            lines.append(f"  {src} *-- {tgt}")
        elif kind == "aggregation":
            lines.append(f"  {src} o-- {tgt}")
        elif kind == "dependency":
            lines.append(f"  {src} ..> {tgt}")
        else:
            lab = mermaid_label(str(a.get("label") or ""))
            if lab and lab != "-":
                lines.append(f"  {src} --> {tgt} : {lab}")
            else:
                lines.append(f"  {src} --> {tgt}")
    return "\n".join(lines) + "\n"


def er_model_to_mermaid(
    model: dict[str, Any] | None,
    *,
    mode: str = "total",
    entity: str | None = None,
) -> str:
    model = model if isinstance(model, dict) else {}
    mode_n = (mode or "total").strip().lower()
    if mode_n == "part":
        return _er_part_mermaid(model, entity=entity)
    return _er_total_mermaid(model)


def _er_total_mermaid(model: dict[str, Any]) -> str:
    title = str(model.get("title") or "E-R图")
    lines = _header("erDiagram", title)
    tables = [
        t
        for t in (model.get("tables") or [])
        if isinstance(t, dict)
        and t.get("name")
        and not t.get("assoc_link")
    ]
    for t in tables:
        name = mermaid_id(str(t.get("name")))
        lab = mermaid_label(str(t.get("label") or t.get("name") or ""))
        lines.append(f"  {name} {{")
        lines.append(f"    string label \"{lab}\"")
        lines.append("  }")
    for r in model.get("relations") or []:
        if not isinstance(r, dict):
            continue
        left = mermaid_id(str(r.get("left") or ""))
        right = mermaid_id(str(r.get("right") or ""))
        if left == "x" or right == "x":
            continue
        lab = mermaid_label(str(r.get("label") or r.get("via") or "关联"))
        cl = str(r.get("card_left") or "1").upper()
        cr = str(r.get("card_right") or "N").upper()
        # Mermaid ER: ||--o{ 等；简化用 }o--o{
        left_c = "||" if cl in ("1", "ONE") else "}o"
        right_c = "||" if cr in ("1", "ONE") else "o{"
        lines.append(f"  {left} {left_c}--{right_c} {right} : {lab}")
    return "\n".join(lines) + "\n"


def _er_part_mermaid(model: dict[str, Any], *, entity: str | None) -> str:
    ent = (entity or str(model.get("er_entity") or "")).strip()
    table = None
    for t in model.get("tables") or []:
        if isinstance(t, dict) and str(t.get("name") or "") == ent:
            table = t
            break
    title = str((table or {}).get("label") or ent or "实体属性")
    lines = _header("erDiagram", f"{title}-实体属性")
    if not table:
        return "\n".join(lines) + "\n"
    name = mermaid_id(ent)
    lines.append(f"  {name} {{")
    for c in table.get("own_columns") or []:
        if not isinstance(c, dict) or c.get("fk"):
            continue
        cn = mermaid_id(str(c.get("name") or "col"))
        cl = mermaid_label(str(c.get("label") or c.get("name") or ""))
        lines.append(f"    string {cn} \"{cl}\"")
    if not any(
        isinstance(c, dict) and not c.get("fk") for c in (table.get("own_columns") or [])
    ):
        for cn in er_own_column_names(table):
            lines.append(f"    string {mermaid_id(cn)}")
    lines.append("  }")
    body = "\n".join(lines) + "\n"
    # 同源：不得出现 FK 列名
    for c in table.get("columns") or []:
        if isinstance(c, dict) and c.get("fk"):
            fk = str(c.get("name") or "").strip()
            if fk and fk in body and f" {mermaid_id(fk)}" in body:
                # 若误写入会在测试里红；此处不静默删包外结构
                pass
    return body


def module_model_to_mermaid(model: dict[str, Any] | None) -> str:
    from app.bake.schema.modules import iter_nodes

    model = model if isinstance(model, dict) else {}
    title = str(model.get("title") or "功能模块图")
    lines = _header("flowchart TB", title)
    nodes = [
        n
        for n in iter_nodes(model)
        if isinstance(n, dict) and n.get("id") and not n.get("hidden")
    ]
    id_map: dict[str, str] = {}
    for n in nodes:
        nid = str(n.get("id") or "")
        mid = mermaid_id(nid, prefix="M_")
        id_map[nid] = mid
        lab = mermaid_label(str(n.get("label") or nid))
        lines.append(f'  {mid}["{lab}"]')
    for n in nodes:
        nid = str(n.get("id") or "")
        src = id_map.get(nid)
        if not src:
            continue
        for ch in n.get("children") or []:
            if not isinstance(ch, dict) or ch.get("hidden"):
                continue
            cid = str(ch.get("id") or "")
            tgt = id_map.get(cid)
            if tgt:
                lines.append(f"  {src} --> {tgt}")
    return "\n".join(lines) + "\n"


def usecase_model_to_mermaid(model: dict[str, Any] | None) -> str:
    model = model if isinstance(model, dict) else {}
    title = str(model.get("title") or "用例图")
    lines = _header("flowchart LR", title)
    actor = model.get("actor") if isinstance(model.get("actor"), dict) else {}
    actor_id = str(actor.get("id") or "actor")
    aid = mermaid_id(actor_id, prefix="A_")
    lines.append(f'  {aid}["{mermaid_label(str(actor.get("label") or actor_id))}"]')
    for uc in model.get("level1") or []:
        if not isinstance(uc, dict) or not uc.get("id"):
            continue
        uid = str(uc.get("id") or "")
        umid = mermaid_id(uid, prefix="U_")
        lines.append(f'  {umid}(["{mermaid_label(str(uc.get("label") or uid))}"])')
        lines.append(f"  {aid} --> {umid}")
        for kid in uc.get("includes") or []:
            if not isinstance(kid, dict) or not kid.get("id") or kid.get("hidden"):
                continue
            kid_id = str(kid.get("id") or "")
            kmid = mermaid_id(kid_id, prefix="U_")
            rel = mermaid_label(str(kid.get("relation") or "include"))
            lines.append(f'  {kmid}(["{mermaid_label(str(kid.get("label") or kid_id))}"])')
            lines.append(f"  {umid} -.->|{rel}| {kmid}")
    return "\n".join(lines) + "\n"


def architecture_model_to_mermaid(model: dict[str, Any] | None) -> str:
    model = model if isinstance(model, dict) else {}
    title = str(model.get("title") or "系统逻辑架构图")
    lines = _header("flowchart TB", title)
    roles = [r for r in (model.get("roles") or []) if isinstance(r, dict) and r.get("id")]
    if not roles:
        roles = [{"id": "user", "label": "用户"}]
    for r in roles:
        rid = mermaid_id(str(r.get("id")), prefix="R_")
        lines.append(f'  {rid}["{mermaid_label(str(r.get("label") or r.get("id")))}"]')
    layers = [
        ("ui", "界面"),
        ("vue", "Vue"),
        ("spring", "SpringBoot"),
        ("mysql", "MySQL"),
    ]
    prev = None
    for lid, lab in layers:
        mid = mermaid_id(lid, prefix="L_")
        lines.append(f'  {mid}["{lab}"]')
        if prev:
            lines.append(f"  {prev} --> {mid}")
        prev = mid
    ui = mermaid_id("ui", prefix="L_")
    for r in roles:
        rid = mermaid_id(str(r.get("id")), prefix="R_")
        lines.append(f"  {rid} --> {ui}")
    return "\n".join(lines) + "\n"


def collect_mermaid_labels(text: str) -> set[str]:
    """粗提取可见中文/词，供同源抽检（非完整解析）。"""
    out: set[str] = set()
    for m in re.finditer(r"[\u4e00-\u9fffA-Za-z0-9_（）()]{2,}", text or ""):
        out.add(m.group(0))
    return out


# 稳定 id 与 Draw.io 对照用（测试）
def expected_er_part_has_no_fk_names(mermaid: str, table: dict[str, Any]) -> None:
    for c in table.get("columns") or []:
        if not isinstance(c, dict) or not c.get("fk"):
            continue
        name = str(c.get("name") or "").strip()
        lab = str(c.get("label") or "").strip()
        if name and re.search(rf"\b{re.escape(name)}\b", mermaid):
            raise AssertionError(f"mermaid er part contains fk name: {name}")
        if lab and lab in mermaid:
            raise AssertionError(f"mermaid er part contains fk label: {lab}")


__all__ = [
    "activity_diagram_to_mermaid",
    "activity_model_to_mermaid",
    "architecture_model_to_mermaid",
    "class_model_to_mermaid",
    "collect_mermaid_labels",
    "er_model_to_mermaid",
    "expected_er_part_has_no_fk_names",
    "mermaid_id",
    "mermaid_label",
    "module_model_to_mermaid",
    "sequence_diagram_to_mermaid",
    "sequence_model_to_mermaid",
    "stable_cell_id",
    "usecase_model_to_mermaid",
]
