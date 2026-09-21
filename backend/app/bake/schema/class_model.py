"""论文「类图」：从 schema.sql + Java 组装 UML 类图模型。

真源（相互印证，禁止臆造）：
- 表/外键关联 ← bake 包 ``sql/schema.sql``
- 属性/方法/类型 ← bake 包 Java（*Store/*Controller 行映射与方法签名）；
  无行映射时属性回退 SQL→Java 类型（仍属交付包）
- 表义、领域实体 key、题名 ← ``domain.schema.json``（开题匹配）

布局/折线见 ``class_layout``；SVG 见 ``class_svg``。
"""

from __future__ import annotations

import copy
import html
import json
import re
from pathlib import Path
from typing import Any

from app.bake.schema.class_code import (
    enrich_classes_from_java,
    infer_dependency_relations,
    merge_oo_relations_into_model,
    scan_java_oo_relations,
)
from app.bake.schema.er_labels import (
    _col_zh,
    _labels_from_domain_schema,
    _table_zh,
    apply_er_label_patch,
    load_er_label_patch,
)
from app.bake.schema.er_model import infer_relations, parse_schema_sql
from app.bake.schema.er_zh import _COMMON_COL_ZH, _INFRA_TABLE_ZH

_FONT = "Microsoft YaHei, SimSun, serif"
_FONT_CODE = "Consolas, Courier New, monospace"
_STROKE = 1.2
_PAD = 48.0
# 出图边距：外绕折线 + 箭头 marker 不贴 viewBox；默认 fit 也不裁线头
_EDGE_MARGIN = 120.0
_ROW_H = 20.0
_HEADER_H = 28.0
_H_PAD = 12.0
_FONT_TITLE = 14.0
_FONT_BODY = 12.0
# 单框过宽时仍完整显示（不截断签名）；仅作布局参考上限提示用，不裁切正文
_MIN_BOX_W = 148.0

# 零交叉选边时优先保留强关系（论文更常画组合/聚合/继承）
_KIND_DRAW_PRIORITY: dict[str, int] = {
    "composition": 0,
    "aggregation": 1,
    "inheritance": 2,
    "implementation": 3,
    "association": 4,
    "dependency": 5,
}

_SQL_TYPE_JAVA: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^(tinyint\s*\(\s*1\s*\)|boolean|bool|bit)\b", re.I), "Boolean"),
    (re.compile(r"^(tinyint|smallint|mediumint|int|integer)\b", re.I), "Integer"),
    (re.compile(r"^bigint\b", re.I), "Long"),
    (re.compile(r"^(decimal|numeric|dec)\b", re.I), "BigDecimal"),
    (re.compile(r"^(double|float|real)\b", re.I), "Double"),
    (re.compile(r"^datetime\b|^timestamp\b", re.I), "LocalDateTime"),
    (re.compile(r"^date\b", re.I), "LocalDate"),
    (re.compile(r"^time\b", re.I), "LocalTime"),
    (re.compile(r"^(blob|binary|varbinary|bytea)\b", re.I), "byte[]"),
    (re.compile(r".*", re.I), "String"),
)


def _esc(s: str) -> str:
    return html.escape(str(s or ""), quote=True)


def _f(v: float) -> str:
    return f"{v:.1f}"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def sql_type_to_java(sql_type: str) -> str:
    raw = str(sql_type or "").strip()
    if not raw:
        return "String"
    for pat, java in _SQL_TYPE_JAVA:
        if pat.search(raw):
            return java
    return "String"


def table_to_class_name(table: str) -> str:
    """物理表名 → UML 类名（PascalCase）；``sys_user`` → ``User``。"""
    name = str(table or "").strip()
    if not name:
        return "Entity"
    if ":" in name:
        name = name.split(":", 1)[0]
    if name.startswith("sys_"):
        name = name[4:]
    parts = [p for p in re.split(r"[^a-zA-Z0-9]+", name) if p]
    if not parts:
        return "Entity"
    return "".join(p[:1].upper() + p[1:] for p in parts)


def _camel_attr(col: str) -> str:
    parts = [p for p in re.split(r"[^a-zA-Z0-9]+", str(col or "")) if p]
    if not parts:
        return "field"
    head, *rest = parts
    return head[:1].lower() + head[1:] + "".join(r[:1].upper() + r[1:] for r in rest)


def _text_w(s: str, px: float = 12.0, *, mono: bool = False) -> float:
    """估测 SVG 文本宽度；等宽略偏宽，避免字画出框。"""
    # Consolas 约 0.6em，实测渲染常略宽；中文按全角
    ascii_r = 0.72 if mono else 0.62
    cjk_r = 1.05
    w = 0.0
    for ch in s:
        w += px * (cjk_r if ord(ch) > 127 else ascii_r)
    return w


def _domain_entity_keys(domain: dict[str, Any] | None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(domain, dict):
        return out
    ents = domain.get("entities")
    if not isinstance(ents, dict):
        return out
    for slot, ent in ents.items():
        if not isinstance(ent, dict):
            continue
        key = str(ent.get("key") or "").strip()
        label = str(ent.get("label") or "").strip()
        if not key and not label:
            continue
        out.append({"slot": str(slot), "key": key or str(slot), "label": label or key})
    return out


def _table_name_aliases(name: str) -> set[str]:
    """物理表名 ↔ 开题实体 key 的常见别名（sys_/biz_ 前缀、去前缀）。"""
    n = str(name or "").strip()
    if not n:
        return set()
    out = {n}
    for pref in ("sys_", "biz_"):
        if n.startswith(pref) and len(n) > len(pref):
            out.add(n[len(pref) :])
        else:
            out.add(f"{pref}{n}")
    return out


def _table_name_set(tables: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()
    for t in tables:
        if not isinstance(t, dict):
            continue
        n = str(t.get("name") or "").strip()
        if n:
            names |= _table_name_aliases(n)
    return names


def _entity_key_aliases(key: str, slot: str = "") -> set[str]:
    aliases = _table_name_aliases(key)
    if slot:
        aliases |= _table_name_aliases(slot)
    return aliases


def _cross_check(
    tables: list[dict[str, Any]],
    domain_ents: list[dict[str, str]],
) -> dict[str, Any]:
    names = _table_name_set(tables)
    matched: list[str] = []
    missing: list[str] = []
    for e in domain_ents:
        key = e["key"]
        aliases = _entity_key_aliases(key, e.get("slot") or "")
        if aliases & names:
            matched.append(key)
        else:
            missing.append(key)
    return {
        "entity_keys_matched": matched,
        "entity_keys_missing_in_sql": missing,
        "table_count": len(tables),
        "ok": len(missing) == 0,
    }


def _entity_key_by_table(
    tables: list[dict[str, Any]], domain_ents: list[dict[str, str]]
) -> dict[str, str]:
    names = {str(t.get("name") or "") for t in tables if isinstance(t, dict)}
    out: dict[str, str] = {}
    for e in domain_ents:
        key = e["key"]
        for cand in _entity_key_aliases(key, e.get("slot") or ""):
            if cand in names:
                out[cand] = key
    return out


# 共享字典/账号类：外键多为普通关联，不作「整体—部分」
_LOOKUP_TABLE_HINTS = frozenset(
    {
        "user",
        "sys_user",
        "role",
        "sys_role",
        "admin",
        "dict",
        "sys_dict",
        "category",
        "sys_category",
        "config",
        "sys_config",
        "menu",
        "sys_menu",
        "permission",
        "sys_permission",
    }
)
# 子表名暗示强依附 → 组合；否则非空 FK → 聚合
_COMPOSITION_CHILD_HINTS = (
    "item",
    "detail",
    "line",
    "entry",
    "attachment",
    "attach",
    "file",
    "image",
    "photo",
    "record",
    "log",
    "sku",
    "spec",
)


def _classify_fk_relation_kind(
    parent: str,
    child: str,
    via: str,
    *,
    child_cls: dict[str, Any] | None = None,
    cascade: bool = False,
) -> str:
    """外键 → 关联 / 聚合 / 组合（论文六种关系中 FK 能落到的三种）。"""
    p = str(parent or "").strip().lower()
    c = str(child or "").strip().lower()
    if not p or not c:
        return "association"
    if p in _LOOKUP_TABLE_HINTS or p.removeprefix("sys_") in _LOOKUP_TABLE_HINTS:
        return "association"
    fk_nn = False
    if isinstance(child_cls, dict):
        for a in child_cls.get("attributes") or []:
            if not isinstance(a, dict):
                continue
            col = str(a.get("column") or a.get("name") or "").lower()
            via_l = str(via or "").lower()
            if via_l and (col == via_l or col.replace("_", "") == via_l.replace("_", "")):
                fk_nn = bool(a.get("not_null")) or bool(a.get("pk"))
                break
            if a.get("fk") and via_l and via_l in col:
                fk_nn = bool(a.get("not_null")) or bool(a.get("pk"))
                break
    child_stem = c.removeprefix("sys_")
    strong_name = any(h in child_stem for h in _COMPOSITION_CHILD_HINTS)
    if cascade or (fk_nn and strong_name):
        return "composition"
    if fk_nn or strong_name:
        return "aggregation"
    return "association"


def class_model_from_er_tables(
    tables_raw: list[dict[str, Any]],
    relations_raw: list[dict[str, Any]],
    *,
    title: str,
    domain_ents: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """把已解析的表/联系（与 E-R 同源）转成类图骨架（方法待 Java 补全）。"""
    classes: list[dict[str, Any]] = []
    used_names: set[str] = set()
    for t in tables_raw:
        if not isinstance(t, dict):
            continue
        tname = str(t.get("name") or "").strip()
        if not tname:
            continue
        cname = table_to_class_name(tname)
        base = cname
        n = 2
        while cname in used_names:
            cname = f"{base}{n}"
            n += 1
        used_names.add(cname)

        attrs: list[dict[str, Any]] = []
        for c in t.get("columns") or []:
            if not isinstance(c, dict):
                continue
            col = str(c.get("name") or "").strip()
            if not col:
                continue
            java = sql_type_to_java(str(c.get("type") or ""))
            aname = _camel_attr(col)
            attrs.append(
                {
                    "name": aname,
                    "column": col,
                    "type": java,
                    "sql_type": str(c.get("type") or ""),
                    # 实体字段论文惯例为私有；全量模式若命中 Java field 会改写
                    "visibility": "-",
                    "label": str(c.get("label") or col),
                    "pk": bool(c.get("pk")),
                    "fk": bool(c.get("fk")),
                    "not_null": bool(c.get("not_null")),
                    "source": "sql",
                    "display": f"- {aname}: {java}",
                }
            )

        classes.append(
            {
                "id": tname,
                "name": cname,
                "table": tname,
                "label": str(t.get("label") or tname),
                "attributes": attrs,
                "methods": [],
                "attr_source": "sql",
                "method_source": "none",
            }
        )

    id_by_table = {c["id"]: c["name"] for c in classes}
    table_by_id = {c["id"]: c for c in classes}
    associations: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for r in relations_raw:
        if not isinstance(r, dict):
            continue
        parent = str(r.get("left") or "").strip()
        child = str(r.get("right") or "").strip()
        via = str(r.get("via") or "").strip()
        if not parent or not child or parent not in id_by_table or child not in id_by_table:
            continue
        key = (child, parent, via)
        if key in seen:
            continue
        seen.add(key)
        kind = _classify_fk_relation_kind(
            parent,
            child,
            via,
            child_cls=table_by_id.get(child),
            cascade=bool(r.get("cascade")),
        )
        # 关联/依赖：箭头指向被引用端（父）；聚合/组合：菱形在整体（父）、箭头指向部分（子）
        if kind in ("aggregation", "composition"):
            frm, to = parent, child
        else:
            frm, to = child, parent
        associations.append(
            {
                "from": frm,
                "to": to,
                "from_class": id_by_table[frm],
                "to_class": id_by_table[to],
                "via": via,
                "kind": kind,
                "label": str(r.get("label") or via or ""),
            }
        )

    evidence = _cross_check(tables_raw, domain_ents or [])
    evidence["relation_count"] = len(associations)
    evidence["schema_sql"] = True
    evidence["domain_schema"] = bool(domain_ents is not None)

    return {
        "title": title,
        "figure_title": f"{title}类图" if title else "系统类图",
        "source_note": (
            "关联/聚合/组合来自 sql/schema.sql 外键；继承/实现来自 Java extends/implements；"
            "依赖来自方法/属性类型引用；属性/方法优先取自 bake 包 Java（含可见性 +/#/-）；"
            "无行映射时属性回退 SQL 列类型；与 domain.schema.json 开题实体对照。"
        ),
        "evidence": evidence,
        "classes": classes,
        "associations": associations,
        "zero_crossing": True,
    }

_CLASS_LAYOUT_REL = Path("islands") / "class_layout.json"


def load_class_layout_patch(workspace: Path) -> dict[str, dict[str, float]]:
    """读取人工拖拽落盘的类框位置（仅 x/y；w/h 仍按当前内容重算）。"""
    layout, _mode = load_class_layout_bundle(workspace)
    return layout


def load_class_layout_bundle(
    workspace: Path,
) -> tuple[dict[str, dict[str, float]], str | None]:
    """返回 (layout, 落盘时的 display_mode)。"""
    path = workspace / _CLASS_LAYOUT_REL
    if not path.is_file():
        return {}, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}, None
    if not isinstance(data, dict):
        return {}, None
    raw = data.get("layout")
    if not isinstance(raw, dict):
        return {}, None
    out: dict[str, dict[str, float]] = {}
    for k, v in raw.items():
        if not isinstance(v, dict):
            continue
        try:
            out[str(k)] = {"x": float(v["x"]), "y": float(v["y"])}
        except (KeyError, TypeError, ValueError):
            continue
    mode_raw = data.get("display_mode")
    mode = str(mode_raw).strip().lower() if mode_raw is not None else None
    if mode not in ("sample", "full"):
        mode = None
    return out, mode


def save_class_layout_patch(
    workspace: Path,
    layout: dict[str, Any],
    *,
    display_mode: str | None = None,
) -> dict[str, Any]:
    """保存类框位置到 islands/class_layout.json。"""
    cleaned: dict[str, dict[str, float]] = {}
    for k, v in (layout or {}).items():
        if not isinstance(v, dict):
            continue
        try:
            cleaned[str(k)] = {
                "x": round(float(v["x"]), 1),
                "y": round(float(v["y"]), 1),
            }
            if "w" in v:
                cleaned[str(k)]["w"] = round(float(v["w"]), 1)
            if "h" in v:
                cleaned[str(k)]["h"] = round(float(v["h"]), 1)
        except (KeyError, TypeError, ValueError):
            continue
    path = workspace / _CLASS_LAYOUT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"version": 1, "layout": cleaned}
    if display_mode:
        payload["display_mode"] = (
            "full" if str(display_mode).strip().lower() == "full" else "sample"
        )
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _CLASS_MODEL_CACHE.pop(str(workspace.resolve()), None)
    return payload


def clear_class_layout_patch(workspace: Path) -> bool:
    path = workspace / _CLASS_LAYOUT_REL
    if path.is_file():
        path.unlink()
        _CLASS_MODEL_CACHE.pop(str(workspace.resolve()), None)
        return True
    return False


def refine_and_persist_class_layout(
    workspace: Path,
    *,
    display_mode: str | None = None,
    title_fallback: str = "",
) -> dict[str, Any]:
    """人工坐标落盘后：按零交叉挪框精炼，并把精炼后的 x/y 写回。

    零交叉/挪框只在后端做；前端拖完回拉 SVG 即可。
    """
    mode = normalize_class_display_mode(display_mode)
    model = load_class_model(
        workspace,
        title_fallback=title_fallback,
        display_mode=mode,
    )
    if not model:
        return {"ok": False, "message": "未找到类图模型"}
    layout = model.get("layout") or {}
    cleaned: dict[str, dict[str, float]] = {}
    for k, v in layout.items():
        if not isinstance(v, dict):
            continue
        try:
            cleaned[str(k)] = {
                "x": round(float(v["x"]), 1),
                "y": round(float(v["y"]), 1),
            }
        except (KeyError, TypeError, ValueError):
            continue
    saved = save_class_layout_patch(workspace, cleaned, display_mode=mode)
    # 写盘会清缓存；把刚算好的 model 立刻回填，避免随后 model+svg 再排两遍
    _seed_class_model_cache(
        workspace,
        model,
        display_mode=mode,
        title_fallback=title_fallback,
    )
    ev = model.get("evidence") if isinstance(model.get("evidence"), dict) else {}
    return {
        "ok": True,
        "layout": saved.get("layout") or cleaned,
        "assoc_drawn": int(ev.get("assoc_drawn") or 0),
        "assoc_omitted": int(ev.get("assoc_omitted") or 0),
        "layout_nudged": bool(ev.get("layout_nudged")),
        "source_note": model.get("source_note") or "",
        "message": "类图布局已保存并按零交叉精炼",
    }



def apply_class_layout_patch(
    model: dict[str, Any],
    patch: dict[str, dict[str, float]],
    *,
    compact: bool = False,
) -> bool:
    """用已存 x/y 覆盖自动布局；保留当前 w/h（内容可能已变）。

    compact=True：按相对左右/上下收紧间距（切 sample/full 时用）。
    同显示规则下保持拖拽绝对坐标，避免松手后被重排「拖了等于没拖」。
    """
    if not patch or not isinstance(model.get("layout"), dict):
        return False
    layout = model["layout"]
    hit = 0
    for tid, box in patch.items():
        if tid not in layout or not isinstance(layout[tid], dict):
            continue
        layout[tid] = {
            **layout[tid],
            "x": round(float(box["x"]), 1),
            "y": round(float(box["y"]), 1),
        }
        hit += 1
    if not hit:
        return False
    model["layout_manual"] = True
    if compact and len(layout) >= 2:
        pos = {
            tid: (
                float(box["x"]),
                float(box["y"]),
                float(box["w"]),
                float(box["h"]),
            )
            for tid, box in layout.items()
            if isinstance(box, dict) and all(k in box for k in ("x", "y", "w", "h"))
        }
        if len(pos) >= 2:
            from app.bake.schema.class_layout import (
                _repack_layout_preserving_order,
            )

            pos = _repack_layout_preserving_order(pos)
            model["layout"] = {
                tid: {
                    "x": round(x, 1),
                    "y": round(y, 1),
                    "w": round(w, 1),
                    "h": round(h, 1),
                }
                for tid, (x, y, w, h) in pos.items()
            }
    return True


_DISPLAY_MODES: tuple[tuple[str, str], ...] = (
    ("sample", "论文示例（精简方法）"),
    ("full", "代码全量"),
)

# sample 优先保留的业务方法（仅当代码里真实存在才收录；禁止无代码填空）
_SAMPLE_METHOD_PREF: tuple[str, ...] = (
    "page",
    "list",
    "getlist",
    "get",
    "detail",
    "find",
    "query",
    "add",
    "create",
    "insert",
    "save",
    "update",
    "edit",
    "modify",
    "delete",
    "remove",
    "del",
    "approve",
    "reject",
    "complete",
    "withdraw",
    "cancel",
)
_SAMPLE_METHOD_LIMIT = 6


def normalize_class_display_mode(raw: str | None) -> str:
    m = str(raw or "sample").strip().lower()
    if m in ("full", "code", "java", "all"):
        return "full"
    return "sample"


def _clone_members(items: list[Any] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for it in items or []:
        if isinstance(it, dict):
            out.append(dict(it))
    return out


def _format_attr_display(a: dict[str, Any], *, force_vis: str | None = None) -> str:
    name = str(a.get("name") or "").strip()
    typ = str(a.get("type") or "Object")
    vis = force_vis or str(a.get("visibility") or "-")
    if vis not in ("+", "#", "-"):
        vis = "-"
    return f"{vis} {name}: {typ}"


def _format_method_display(m: dict[str, Any]) -> str:
    """论文格式：+ name(ParamTypes) : ReturnType（无参也写 ()）。"""
    name = str(m.get("name") or "").strip() or "method"
    vis = str(m.get("visibility") or "+")
    if vis not in ("+", "#", "-"):
        vis = "+"
    ret = str(m.get("return") or "void").strip() or "void"
    raw = str(m.get("params") or "").strip()
    if not raw:
        arg = "()"
    else:
        parts: list[str] = []
        for p in raw.split(","):
            p = p.strip()
            if not p:
                continue
            toks = p.replace("...", " ").split()
            typ = toks[0] if toks else "Object"
            parts.append(typ)
        arg = "(" + ", ".join(parts) + ")"
    existing = str(m.get("display") or "")
    if (
        existing.startswith(vis)
        and name in existing
        and "(" in existing
        and ")" in existing
        and ":" in existing
    ):
        return existing
    return f"{vis} {name}{arg} : {ret}"


def _sample_attributes(attrs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """论文示例：属性尽量全保留；可见性跟代码（SQL/行映射默认 -，Java field 保留 +/#/-）。"""
    out: list[dict[str, Any]] = []
    for a in attrs:
        name = str(a.get("name") or "").strip()
        if not name or name.startswith("_"):
            continue
        row = dict(a)
        vis = str(row.get("visibility") or "-")
        if vis not in ("+", "#", "-"):
            vis = "-"
        row["visibility"] = vis
        row["display"] = _format_attr_display(row)
        out.append(row)
    return out


def _sample_methods(methods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """论文精简：只展示代码里真实存在的方法，优先 CRUD 名，带 ()：返回类型；禁止模板填空。"""
    real: list[dict[str, Any]] = []
    for m in methods:
        if not isinstance(m, dict):
            continue
        n = str(m.get("name") or "").strip()
        if not n:
            continue
        real.append(dict(m))
    if not real:
        return []

    pref_rank = {n: i for i, n in enumerate(_SAMPLE_METHOD_PREF)}

    def sort_key(m: dict[str, Any]) -> tuple[int, str]:
        n = str(m.get("name") or "")
        return (pref_rank.get(n.lower(), 100), n.lower())

    ranked = sorted(real, key=sort_key)
    picked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in ranked:
        n = str(m.get("name") or "")
        key = n.lower()
        if key in seen:
            continue
        seen.add(key)
        row = dict(m)
        if str(row.get("visibility") or "") not in ("+", "#", "-"):
            row["visibility"] = "+"
        if row.get("visibility") == "-":
            continue
        row["display"] = _format_method_display(row)
        row["source"] = str(row.get("source") or "java")
        picked.append(row)
        if len(picked) >= _SAMPLE_METHOD_LIMIT:
            break
    return picked


def apply_class_display_mode(model: dict[str, Any], mode: str | None = "sample") -> dict[str, Any]:
    """就地切换类框属性/方法展示；须在 attach_layout 之前调用（影响框高）。"""
    mode_n = normalize_class_display_mode(mode)
    model["display_mode"] = mode_n
    model["display_modes"] = [{"id": i, "label": lab} for i, lab in _DISPLAY_MODES]
    for cls in model.get("classes") or []:
        if not isinstance(cls, dict):
            continue
        if "_attrs_full" not in cls:
            cls["_attrs_full"] = _clone_members(cls.get("attributes"))
            cls["_methods_full"] = _clone_members(cls.get("methods"))
        full_a = _clone_members(cls.get("_attrs_full"))
        full_m = _clone_members(cls.get("_methods_full"))
        if mode_n == "sample":
            cls["attributes"] = _sample_attributes(full_a)
            cls["methods"] = _sample_methods(full_m)
            cls["display_skin"] = "sample"
        else:
            for a in full_a:
                a["display"] = _format_attr_display(a)
            for m in full_m:
                m["display"] = _format_method_display(m)
            cls["attributes"] = full_a
            cls["methods"] = full_m
            cls["display_skin"] = "full"
    model["_display_mode_note"] = (
        "显示规则：论文示例（属性 name: Type 含 +/#/-；方法取自实包写作 name() : 返回类型，无代码不填空；私有方法精简不展示）。"
        if mode_n == "sample"
        else "显示规则：代码全量（属性与方法签名含 public+/protected#/private-）。"
    )
    return model



def build_class_model(
    workspace: Path,
    *,
    title_fallback: str = "",
    display_mode: str = "sample",
    assoc_mode: str = "zero",
) -> dict[str, Any] | None:
    from app.bake.schema.class_layout import (
        _apply_manual_zero_cross,
        _sized_layout_stub,
        attach_layout,
    )

    path = workspace / "sql" / "schema.sql"
    if not path.is_file():
        return None
    domain_path = workspace / "domain.schema.json"
    domain = _read_json(domain_path)
    tzh, czh, tcols, _rzh, fk_aliases = _labels_from_domain_schema(domain_path)
    tzh = {**_INFRA_TABLE_ZH, **tzh}
    czh = {**_COMMON_COL_ZH, **czh}

    sql = path.read_text(encoding="utf-8", errors="ignore")
    parsed = parse_schema_sql(sql, fk_aliases=fk_aliases)
    relations = infer_relations(parsed)

    tables: list[dict[str, Any]] = []
    for t in parsed:
        tables.append(
            {
                "name": t.name,
                "label": _table_zh(t.name, tzh),
                "columns": [
                    {
                        "name": c.name,
                        "type": c.type,
                        "pk": c.pk,
                        "fk": c.fk,
                        "fk_table": c.fk_table,
                        "not_null": bool(getattr(c, "not_null", False)),
                        "label": _col_zh(c.name, t.name, czh, tcols, tzh),
                    }
                    for c in t.columns
                ],
            }
        )
    rels = [
        {
            "name": r.name,
            "left": r.left,
            "right": r.right,
            "via": r.via,
            "label": r.via,
            "cascade": bool(getattr(r, "cascade", False)),
        }
        for r in relations
    ]

    er_like = {"tables": tables, "relations": rels}
    from app.bake.schema.page_columns import apply_page_column_labels, page_column_index

    er_like = apply_page_column_labels(
        er_like, page_column_index(workspace, model=er_like), czh=czh
    )
    patch = load_er_label_patch(workspace)
    er_like = apply_er_label_patch(er_like, patch)

    title = ""
    domain_ents = _domain_entity_keys(domain)
    if isinstance(domain, dict):
        title = str(domain.get("title") or "").strip()
        labels = domain.get("labels") if isinstance(domain.get("labels"), dict) else {}
        if not title:
            title = str(labels.get("appName") or "").strip()
    if not title:
        title = str(title_fallback or "").strip() or "管理系统"

    model = class_model_from_er_tables(
        er_like.get("tables") or [],
        er_like.get("relations") or [],
        title=title,
        domain_ents=domain_ents,
    )
    model["evidence"]["domain_schema"] = domain_path.is_file()
    java_stats = enrich_classes_from_java(
        model["classes"],
        workspace,
        entity_key_by_table=_entity_key_by_table(er_like.get("tables") or [], domain_ents),
    )
    model["evidence"].update(java_stats)
    oo_added = merge_oo_relations_into_model(model, scan_java_oo_relations(workspace))
    model["evidence"]["oo_relations_added"] = oo_added
    dep_added = infer_dependency_relations(model)
    model["evidence"]["dependency_relations_added"] = dep_added
    apply_class_display_mode(model, display_mode)
    patch, saved_mode = load_class_layout_bundle(workspace)
    # 仅当落盘显示规则与当前不同时收紧间距（切 sample/full）；同规则保持拖拽坐标
    compact = bool(saved_mode) and saved_mode != normalize_class_display_mode(display_mode)
    auto_layout_fresh = False
    if patch and not compact:
        # 快路径：已有落盘坐标时跳过 hub/tree 竞赛，只算框高 + 零交叉选边
        _sized_layout_stub(model)
        if apply_class_layout_patch(model, patch, compact=False):
            _apply_manual_zero_cross(model, max_rounds=8)
        else:
            attach_layout(model)
            auto_layout_fresh = True
    else:
        attach_layout(model)
        if apply_class_layout_patch(model, patch, compact=compact):
            _apply_manual_zero_cross(model, max_rounds=8)
        else:
            auto_layout_fresh = True

    # 首次自动排版落盘：下次打开走快路径，避免重复竞赛拖死接口
    if auto_layout_fresh and isinstance(model.get("layout"), dict) and model["layout"]:
        try:
            save_class_layout_patch(
                workspace,
                model["layout"],
                display_mode=normalize_class_display_mode(display_mode),
            )
            model["layout_auto_persisted"] = True
        except OSError:
            pass
    return model


_CLASS_MODEL_CACHE: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] = {}
# 改选边/路由算法时递增，避免短缓存继续吐旧 omitted
_CLASS_ROUTE_VER = 4


def _class_model_fingerprint(
    workspace: Path,
    *,
    display_mode: str,
    title_fallback: str,
    assoc_mode: str,
) -> tuple[Any, ...]:
    ws = Path(workspace)
    fp_parts: list[Any] = [
        str(ws.resolve()),
        display_mode,
        title_fallback,
        assoc_mode,
        _CLASS_ROUTE_VER,
    ]
    for rel in ("sql/schema.sql", "domain.schema.json", "islands/class_layout.json"):
        p = ws / rel
        try:
            st = p.stat()
            fp_parts.append((st.st_mtime_ns, st.st_size))
        except OSError:
            fp_parts.append((0, 0))
    return tuple(fp_parts)


def _seed_class_model_cache(
    workspace: Path,
    model: dict[str, Any],
    *,
    display_mode: str = "sample",
    title_fallback: str = "",
    assoc_mode: str = "zero",
) -> None:
    ws = Path(workspace)
    fp = _class_model_fingerprint(
        ws,
        display_mode=display_mode,
        title_fallback=title_fallback,
        assoc_mode=assoc_mode,
    )
    _CLASS_MODEL_CACHE[str(ws.resolve())] = (fp, copy.deepcopy(model))


def load_class_model(
    workspace: Path,
    *,
    title_fallback: str = "",
    display_mode: str = "sample",
    assoc_mode: str = "zero",
) -> dict[str, Any] | None:
    """短缓存：打开类图会连打 model + svg 两次，避免重复竞赛排版。"""
    ws = Path(workspace)
    fp = _class_model_fingerprint(
        ws,
        display_mode=display_mode,
        title_fallback=title_fallback,
        assoc_mode=assoc_mode,
    )
    cache_key = str(ws.resolve())
    hit = _CLASS_MODEL_CACHE.get(cache_key)
    if hit and hit[0] == fp:
        return copy.deepcopy(hit[1])
    model = build_class_model(
        ws,
        title_fallback=title_fallback,
        display_mode=display_mode,
        assoc_mode=assoc_mode,
    )
    if model is not None:
        _CLASS_MODEL_CACHE[cache_key] = (fp, model)
        return copy.deepcopy(model)
    return None


def _box_size(cls: dict[str, Any]) -> tuple[float, float]:
    name = str(cls.get("name") or "")
    attr_lines = [
        str(a.get("display") or f"+ {a.get('name')}: {a.get('type')}")
        for a in (cls.get("attributes") or [])
        if isinstance(a, dict)
    ]
    meth_lines = [
        str(m.get("display") or "")
        for m in (cls.get("methods") or [])
        if isinstance(m, dict)
    ]
    widths = [_text_w(name, _FONT_TITLE, mono=False)]
    widths.extend(_text_w(x, _FONT_BODY, mono=True) for x in attr_lines)
    widths.extend(_text_w(x, _FONT_BODY, mono=True) for x in meth_lines)
    max_w = max(widths, default=80.0)
    # 框随全文加宽：不截断、不省略，保证签名完整可读
    w = max(_MIN_BOX_W, max_w + 2 * _H_PAD)
    n_attr = len(attr_lines)
    n_meth = len(meth_lines)
    h = _HEADER_H + 2 + n_attr * _ROW_H + 2 + n_meth * _ROW_H + 8
    return w, h


def _normalize_rel_kind(raw: str | None) -> str:
    k = str(raw or "association").strip().lower()
    aliases = {
        "assoc": "association",
        "association": "association",
        "dep": "dependency",
        "dependency": "dependency",
        "inherit": "inheritance",
        "inheritance": "inheritance",
        "generalization": "inheritance",
        "extends": "inheritance",
        "impl": "implementation",
        "implementation": "implementation",
        "realize": "implementation",
        "realization": "implementation",
        "implements": "implementation",
        "agg": "aggregation",
        "aggregation": "aggregation",
        "comp": "composition",
        "composition": "composition",
    }
    return aliases.get(k, "association")
