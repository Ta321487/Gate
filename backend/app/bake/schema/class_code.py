"""从 bake 包 Java（*Store / *Controller）抽取类图属性与方法。

属性：以 ``schema.sql`` 列为真源（调用方已写入）；Java 行映射仅在无 SQL 列时补全。
方法：按类名/主表亲和度绑到对应实体 Store·Controller，禁止多表上帝类串台。
无代码命中时方法栏留空，禁止臆造 getList/add/del/edit。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_CLASS_RE = re.compile(r"(?:public\s+|final\s+)*class\s+(\w+)\b")
_EXTENDS_RE = re.compile(
    r"(?:public\s+|final\s+|abstract\s+)*class\s+(\w+)\s+extends\s+(\w+)\b"
)
_IMPLEMENTS_RE = re.compile(
    r"(?:public\s+|final\s+|abstract\s+)*class\s+(\w+)\s+(?:extends\s+\w+\s+)?"
    r"implements\s+([^{]+)"
)
_INTERFACE_EXTENDS_RE = re.compile(
    r"interface\s+(\w+)\s+extends\s+([^{]+)"
)
_PUT_RS_RE = re.compile(
    r'\.put\(\s*"(\w+)"\s*,\s*(fmt\s*\(\s*)?rs\.get(\w+)\s*\(',
    re.MULTILINE,
)
# Map 行：m.put("x", str(...)) / num(...) / first(...) 等，类型保守为 Object/String
_PUT_HELPER_RE = re.compile(
    r'\.put\(\s*"(\w+)"\s*,\s*(str|num|fmt|safeStr|toStr)\s*\(',
    re.MULTILINE,
)
_FIELD_RE = re.compile(
    r"(public|protected|private)\s+(?:static\s+)?(?:final\s+)?"
    r"([\w.<>,\[\]\s?]+?)\s+(\w+)\s*(?:=|;)",
    re.MULTILINE,
)
_METHOD_RE = re.compile(
    r"(public|protected|private)\s+"
    r"(?:static\s+)?(?:synchronized\s+)?"
    r"([\w.<>,\[\]\s?]+?)\s+"
    r"(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[^{;]+)?\s*\{",
    re.MULTILINE,
)
_TABLE_LIT_RE = re.compile(
    r"""(?:FROM|INTO|UPDATE|JOIN|TABLE)\s+`?([a-z][a-z0-9_]*)`?"""
    r"""|`([a-z][a-z0-9_]*)`"""
    r"""|=\s*"([a-z][a-z0-9_]*)\"""",
    re.IGNORECASE,
)
_STR_ASSIGN_RE = re.compile(
    r'(?:String\s+)?(?:CAT|ITEM|TABLE|tableName)\s*=\s*"([a-z][a-z0-9_]*)"',
    re.IGNORECASE,
)

_RS_GET_TO_JAVA = {
    "Long": "Long",
    "Int": "Integer",
    "Integer": "Integer",
    "String": "String",
    "Boolean": "Boolean",
    "BigDecimal": "BigDecimal",
    "Double": "Double",
    "Float": "Float",
    "Date": "LocalDate",
    "Time": "LocalTime",
    "Timestamp": "LocalDateTime",
    "Object": "Object",
    "Bytes": "byte[]",
}

_SKIP_METHODS = frozenset(
    {
        "db",
        "fmt",
        "row",
        "main",
        "configure",
        "bind",
        "unbind",
        "enabled",
        "resetCache",
        "toString",
        "hashCode",
        "equals",
        "wait",
        "notify",
        "notifyAll",
        "getClass",
        "bool",
        "str",
        "boolOrNull",
        "nz",
        "requireTable",
    }
)

_SKIP_PREFIXES = (
    "has",
    "ensure",
    "configure",
    "bind",
    "init",
    "make",
    "buildSql",
    "sql",
    "col",
    "mapRow",
    "seed",
    "canon",
    "parse",
)

# Store/Controller 去后缀后的主表归属：动态 bind 的表名不在源码字面量里，靠此收口，
# 避免 LoyaltyStore 抢 sys_user、ArchiveStore 抢 category 属性等串台。
_TYPE_SUFFIXES = (
    "Store",
    "Controller",
    "Service",
    "Mapper",
    "Repository",
    "Entity",
    "RowMaps",
)

_STEM_OWNED_TABLES: dict[str, frozenset[str]] = {
    "order": frozenset(
        {
            "order",
            "orders",
            "biz_order",
            "sys_order",
            "cart",
            "cart_line",
            "order_line",
            "order_item",
        }
    ),
    "archive": frozenset(
        {
            "archive",
            "sys_archive",
            "category",
            "book",
            "product",
            "item",
        }
    ),
    "loyalty": frozenset({"loyalty", "sys_loyalty", "user_ledger"}),
    "address": frozenset({"address", "user_address"}),
    "order_review": frozenset({"order_review"}),
    "favorite": frozenset({"favorite", "user_favorite", "sys_favorite"}),
    "dm": frozenset({"dm", "dm_message", "sys_dm_message"}),
    "guestbook": frozenset({"guestbook", "sys_guestbook"}),
    "message": frozenset({"message", "sys_message"}),
    "notice": frozenset({"notice", "sys_notice"}),
    "banner": frozenset({"banner", "sys_banner"}),
    "site_stat": frozenset({"site_stat", "sys_site_stat"}),
    "login_log": frozenset({"login_log", "sys_login_log"}),
    "auth_session": frozenset({"auth_session", "sys_auth_session"}),
    "account_cancel": frozenset({"account_cancel", "sys_account_cancel"}),
    "user": frozenset({"user", "sys_user"}),
    "category": frozenset({"category", "sys_category"}),
}


def _strip_java_noise(src: str) -> str:
    out: list[str] = []
    i, n = 0, len(src)
    while i < n:
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src[i] in "\"'":
            q = src[i]
            out.append(q)
            i += 1
            while i < n:
                ch = src[i]
                out.append(ch)
                i += 1
                if ch == "\\":
                    if i < n:
                        out.append(src[i])
                        i += 1
                    continue
                if ch == q:
                    break
            continue
        out.append(src[i])
        i += 1
    return "".join(out)


def _camel_to_snake(name: str) -> str:
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower()


def _class_stem(classname: str) -> str:
    base = (classname or "").strip()
    for suf in _TYPE_SUFFIXES:
        if base.endswith(suf) and len(base) > len(suf):
            base = base[: -len(suf)]
            break
    return _camel_to_snake(base) if base else ""


def _table_name_keys(table: str, entity_key: str | None = None) -> set[str]:
    keys = {table, table.removeprefix("sys_"), table.removeprefix("biz_")}
    if entity_key:
        keys.add(entity_key)
        keys.add(f"sys_{entity_key}")
        keys.add(f"biz_{entity_key}")
    return {k for k in keys if k}


def _affinity_score(
    classname: str,
    table: str,
    *,
    entity_key: str | None = None,
    owned: bool = False,
) -> int:
    """类名主表命中优先；bind 归属次之；仅字面量蹭表为 0。"""
    stem = _class_stem(classname)
    targets = _table_name_keys(table, entity_key)
    if not stem:
        return 10 if owned else 0
    if stem in targets or f"sys_{stem}" in targets or f"biz_{stem}" in targets:
        return 100
    for t in targets:
        if not t:
            continue
        if stem == t or t.endswith(f"_{stem}") or stem.endswith(f"_{t}"):
            return 90
        if stem in t or t in stem:
            return 70
    if owned:
        # OrderStore↔cart_line 等：主表组内但类名不含该表
        return 55
    return 0


def _simplify_return(ret: str) -> str:
    t = re.sub(r"\s+", " ", (ret or "").strip())
    t = t.replace("java.util.", "").replace("java.lang.", "")
    t = t.replace("java.time.", "")
    if t.startswith("R<") and t.endswith(">"):
        inner = t[2:-1].strip()
        return inner or "Object"
    return t or "void"


def _vis_mark(mod: str) -> str:
    m = (mod or "").strip()
    if m == "private":
        return "-"
    if m == "protected":
        return "#"
    return "+"


# 跨域骨架残留方法名：商城包也会编译进 ArchiveStore，论文类图不应展示
_SKIP_METHOD_MARKERS = (
    "trainhour",
    "carpool",
    "forumpost",
    "forumdaily",
    "userpost",
    "checkincode",
    "mutexcode",
    "isbn",
    "borrow",
)

def _should_skip_method(name: str) -> bool:
    if name in _SKIP_METHODS:
        return True
    low = name.lower()
    if any(low.startswith(p.lower()) for p in _SKIP_PREFIXES):
        return True
    return any(m in low for m in _SKIP_METHOD_MARKERS)


def _method_display(vis: str, name: str, params: str, ret: str) -> str:
    raw = (params or "").strip()
    if not raw:
        arg = "()"
    else:
        # 保留全部形参类型（已 simplify）；不截断、不加省略号，避免学校格式争议
        parts: list[str] = []
        for p in raw.split(","):
            p = p.strip()
            if not p:
                continue
            toks = p.replace("...", " ").split()
            typ = toks[0] if toks else "Object"
            typ = _simplify_return(typ)
            parts.append(typ)
        arg = "(" + ", ".join(parts) + ")"
    return f"{vis} {name}{arg} : {ret}"


def parse_java_type_members(src: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """返回 (attributes, methods)。"""
    clean = _strip_java_noise(src)
    attrs: list[dict[str, Any]] = []
    seen_a: set[str] = set()

    def add_attr(name: str, java: str, source: str, vis: str = "-") -> None:
        """行映射字段按论文惯例作私有属性（-）；显式 Java 字段另走 _FIELD_RE。"""
        if not name or name in seen_a:
            return
        seen_a.add(name)
        mark = vis if vis in ("+", "#", "-") else "-"
        attrs.append(
            {
                "name": name,
                "type": java,
                "visibility": mark,
                "source": source,
                "display": f"{mark} {name}: {java}",
            }
        )

    for m in _PUT_RS_RE.finditer(clean):
        name, wrapped, getter = m.group(1), m.group(2), m.group(3)
        java = _RS_GET_TO_JAVA.get(getter, "Object")
        # fmt(rs.getTimestamp) 运行时是格式化字符串
        if wrapped and getter in ("Timestamp", "Date", "Time"):
            java = "String"
        add_attr(name, java, "java_row")

    for m in _PUT_HELPER_RE.finditer(clean):
        name, helper = m.group(1), m.group(2)
        java = "String" if helper in ("str", "fmt", "safeStr", "toStr") else "Object"
        if helper == "num":
            java = "Number"
        add_attr(name, java, "java_row")

    # @Entity / POJO 字段（无 m.put 时）
    if not attrs:
        for m in _FIELD_RE.finditer(clean):
            mod, typ, name = m.group(1), m.group(2), m.group(3)
            if name in seen_a or name in _SKIP_METHODS:
                continue
            if name.startswith("has") and len(name) > 3:
                continue
            vis = _vis_mark(mod)
            java = _simplify_return(typ)
            seen_a.add(name)
            attrs.append(
                {
                    "name": name,
                    "type": java,
                    "visibility": vis,
                    "source": "java_field",
                    "display": f"{vis} {name}: {java}",
                }
            )

    methods: list[dict[str, Any]] = []
    seen_m: set[str] = set()
    for m in _METHOD_RE.finditer(clean):
        mod, ret_raw, name, params = m.group(1), m.group(2), m.group(3), m.group(4)
        if _should_skip_method(name):
            continue
        ret = _simplify_return(ret_raw)
        if name.startswith("has") and ret in ("boolean", "Boolean"):
            continue
        key = f"{name}/{ret}"
        if key in seen_m:
            continue
        seen_m.add(key)
        vis = _vis_mark(mod)
        methods.append(
            {
                "name": name,
                "return": ret,
                "params": (params or "").strip(),
                "visibility": vis,
                "source": "java",
                "display": _method_display(vis, name, params, ret),
            }
        )
    prio = {
        "page": 0,
        "list": 1,
        "get": 2,
        "detail": 3,
        "add": 4,
        "create": 5,
        "apply": 6,
        "update": 7,
        "edit": 8,
        "delete": 9,
        "remove": 10,
        "approve": 11,
        "reject": 12,
        "complete": 13,
        "withdraw": 14,
    }

    def sort_key(d: dict[str, Any]) -> tuple[int, str]:
        n = str(d.get("name") or "")
        return (prio.get(n, 50), n)

    methods.sort(key=sort_key)
    return attrs, methods


def _tables_mentioned(src: str, classname: str) -> set[str]:
    clean = _strip_java_noise(src)
    found: set[str] = set()
    for m in _TABLE_LIT_RE.finditer(clean):
        for g in m.groups():
            if g and not g.startswith("http"):
                found.add(g.lower())
    for m in _STR_ASSIGN_RE.finditer(clean):
        found.add(m.group(1).lower())
    stem = _class_stem(classname)
    if stem:
        found.add(stem)
        found.add(f"sys_{stem}")
        found.add(f"biz_{stem}")
    noise = {
        "string",
        "select",
        "from",
        "where",
        "set",
        "null",
        "all",
        "if",
        "year",
        "normal",
        "spend",
        "false",
        "true",
        "admin",
        "information_schema",
    }
    return {t for t in found if t and t not in noise}


def _index_tables_for_class(classname: str, mentioned: set[str]) -> set[str]:
    """有主表清单的能力类只挂清单内表，避免 SQL 字面量蹭绑。"""
    stem = _class_stem(classname)
    owned = _STEM_OWNED_TABLES.get(stem)
    if owned is not None:
        return set(owned)
    return set(mentioned)


def index_java_sources(workspace: Path) -> dict[str, list[dict[str, Any]]]:
    """table_name → [{path, class, attrs, methods, score}]。"""
    root = workspace / "backend" / "src" / "main" / "java"
    if not root.is_dir():
        return {}
    by_table: dict[str, list[dict[str, Any]]] = {}
    for path in root.rglob("*.java"):
        name = path.name
        if not (
            name.endswith("Store.java")
            or name.endswith("Controller.java")
            or name.endswith("Entity.java")
            or name.endswith("RowMaps.java")
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        cm = _CLASS_RE.search(text)
        classname = cm.group(1) if cm else path.stem
        attrs, methods = parse_java_type_members(text)
        mentioned = _tables_mentioned(text, classname)
        # TicketRowMaps → ticket / borrow 等：类名去 RowMaps
        if name.endswith("RowMaps.java") and classname.endswith("RowMaps"):
            base = classname[: -len("RowMaps")]
            if base:
                snake = _camel_to_snake(base)
                mentioned.add(snake)
                mentioned.add(f"sys_{snake}")
        tables = _index_tables_for_class(classname, mentioned)
        rel = str(path.relative_to(workspace)).replace("\\", "/")
        if name.endswith("Entity.java"):
            kind = "entity"
        elif name.endswith("Store.java"):
            kind = "store"
        elif name.endswith("RowMaps.java"):
            kind = "rowmaps"
        else:
            kind = "controller"
        score = {"entity": 28, "store": 22, "rowmaps": 18, "controller": 10}.get(kind, 0)
        if attrs:
            score += 8
        if methods:
            score += 4
        stem = _class_stem(classname)
        entry = {
            "path": rel,
            "class": classname,
            "kind": kind,
            "attrs": attrs,
            "methods": methods,
            "score": score,
            "stem": stem,
            "owned_stem": stem in _STEM_OWNED_TABLES,
        }
        for t in tables:
            by_table.setdefault(t, []).append(entry)
    return by_table


def resolve_code_bundle_for_table(
    table: str,
    index: dict[str, list[dict[str, Any]]],
    *,
    entity_key: str | None = None,
) -> dict[str, Any] | None:
    """为物理表合并多源：属性仅高亲和度源；方法按亲和度优先 Controller/Store。"""
    keys = _table_name_keys(table, entity_key)
    cands: list[dict[str, Any]] = []
    for k in keys:
        cands.extend(index.get(k) or [])
    if not cands:
        return None

    best: dict[str, dict[str, Any]] = {}
    for c in cands:
        p = c["path"]
        owned = bool(c.get("owned_stem")) and table in (
            _STEM_OWNED_TABLES.get(str(c.get("stem") or "")) or frozenset()
        )
        aff = _affinity_score(
            str(c.get("class") or ""),
            table,
            entity_key=entity_key,
            owned=owned,
        )
        row = dict(c)
        row["affinity"] = aff
        prev = best.get(p)
        if prev is None or (aff, row["score"]) > (prev.get("affinity", 0), prev["score"]):
            best[p] = row

    ranked = sorted(
        best.values(),
        key=lambda x: (-int(x.get("affinity") or 0), -x["score"], x["path"]),
    )
    # 论文类图：无亲和度的蹭绑源直接丢弃
    ranked = [c for c in ranked if int(c.get("affinity") or 0) >= 55]
    if not ranked:
        return None

    attrs: list[dict[str, Any]] = []
    attr_from = ""
    attr_aff = 0
    for kind in ("entity", "rowmaps", "store", "controller"):
        for c in ranked:
            if c["kind"] != kind or not c["attrs"]:
                continue
            # 属性更严：要类名对得上，避免 ArchiveStore 行映射盖掉 category SQL 列
            if int(c.get("affinity") or 0) < 70:
                continue
            attrs = list(c["attrs"])
            attr_from = c["path"]
            attr_aff = int(c.get("affinity") or 0)
            break
        if attrs:
            break

    methods: list[dict[str, Any]] = []
    meth_from = ""
    meth_class = ""
    # 方法：亲和度优先，同档 Store > Controller（业务方法名更稳；错表已靠亲和度挡掉）
    meth_ranked = sorted(
        [c for c in ranked if c.get("methods")],
        key=lambda x: (
            -int(x.get("affinity") or 0),
            0 if x["kind"] == "store" else 1 if x["kind"] == "controller" else 2,
            x["path"],
        ),
    )
    if meth_ranked:
        pick = meth_ranked[0]
        methods = list(pick["methods"])
        meth_from = pick["path"]
        meth_class = pick["class"]

    primary = ranked[0]
    return {
        "path": meth_from or attr_from or primary["path"],
        "class": meth_class or primary["class"],
        "kind": primary["kind"],
        "attrs": attrs,
        "methods": methods,
        "attr_path": attr_from,
        "method_path": meth_from,
        "score": primary["score"],
        "attr_affinity": attr_aff,
        "method_affinity": int((meth_ranked[0].get("affinity") if meth_ranked else 0) or 0),
    }


def resolve_code_for_table(
    table: str,
    index: dict[str, list[dict[str, Any]]],
    *,
    entity_key: str | None = None,
) -> dict[str, Any] | None:
    return resolve_code_bundle_for_table(table, index, entity_key=entity_key)


def enrich_classes_from_java(
    classes: list[dict[str, Any]],
    workspace: Path,
    *,
    entity_key_by_table: dict[str, str] | None = None,
) -> dict[str, Any]:
    """就地补全 attributes/methods；返回统计。

    SQL 列已在骨架里时保持不动（论文属性跟表）；仅无列时才用 Java 行映射。
    """
    index = index_java_sources(workspace)
    keyed = entity_key_by_table or {}
    hit_attr = 0
    hit_meth = 0
    linked = 0
    for cls in classes:
        if not isinstance(cls, dict):
            continue
        table = str(cls.get("table") or cls.get("id") or "")
        code = resolve_code_bundle_for_table(table, index, entity_key=keyed.get(table))
        sql_attrs = [
            a
            for a in (cls.get("attributes") or [])
            if isinstance(a, dict) and str(a.get("source") or "") in ("sql", "")
        ]
        has_sql_cols = any(str(a.get("column") or "").strip() for a in sql_attrs) or (
            bool(sql_attrs) and str(cls.get("attr_source") or "") == "sql"
        )
        if not code:
            cls["code_path"] = ""
            cls["code_class"] = ""
            cls["attr_source"] = "sql" if (cls.get("attributes") or has_sql_cols) else "none"
            cls["method_source"] = "none"
            continue
        linked += 1
        cls["code_path"] = code["path"]
        cls["code_class"] = code["class"]
        if has_sql_cols:
            for a in cls.get("attributes") or []:
                if isinstance(a, dict):
                    a.setdefault("source", "sql")
                    a.setdefault("visibility", "-")
                    if not a.get("display"):
                        a["display"] = f"- {a.get('name')}: {a.get('type')}"
            cls["attr_source"] = "sql"
        elif code["attrs"]:
            cls["attributes"] = code["attrs"]
            cls["attr_source"] = "java"
            hit_attr += 1
        else:
            cls["attr_source"] = "none"
        if code["methods"]:
            cls["methods"] = code["methods"]
            cls["method_source"] = "java"
            hit_meth += 1
        else:
            cls["methods"] = []
            cls["method_source"] = "none"
    return {
        "java_index_tables": len(index),
        "classes_linked_java": linked,
        "classes_attrs_from_java": hit_attr,
        "classes_methods_from_java": hit_meth,
    }


def scan_java_oo_relations(workspace: Path) -> list[dict[str, str]]:
    """扫描 bake 包 Java 的 extends / implements，供类图补继承与实现边。"""
    root = workspace / "backend" / "src" / "main" / "java"
    if not root.is_dir():
        return []
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def add(frm: str, to: str, kind: str) -> None:
        frm, to = frm.strip(), to.strip()
        if not frm or not to or frm == to:
            return
        key = (frm, to, kind)
        if key in seen:
            return
        seen.add(key)
        out.append({"from_class": frm, "to_class": to, "kind": kind})

    for path in root.rglob("*.java"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        clean = _strip_java_noise(text)
        for m in _EXTENDS_RE.finditer(clean):
            add(m.group(1), m.group(2), "inheritance")
        for m in _IMPLEMENTS_RE.finditer(clean):
            child = m.group(1)
            for iface in re.split(r"[,\s]+", m.group(2)):
                iface = iface.strip().strip(",")
                if iface and iface.isidentifier():
                    add(child, iface, "implementation")
        for m in _INTERFACE_EXTENDS_RE.finditer(clean):
            child = m.group(1)
            for parent in re.split(r"[,\s]+", m.group(2)):
                parent = parent.strip().strip(",")
                if parent and parent.isidentifier():
                    add(child, parent, "inheritance")
    return out


def merge_oo_relations_into_model(
    model: dict[str, Any],
    oo_rels: list[dict[str, str]],
) -> int:
    """按类名把继承/实现并入 associations；两端须已在类图中。返回新增条数。"""
    if not oo_rels:
        return 0
    classes = [c for c in (model.get("classes") or []) if isinstance(c, dict)]
    by_name: dict[str, str] = {}
    for c in classes:
        name = str(c.get("name") or "").strip()
        tid = str(c.get("id") or "").strip()
        if name and tid:
            by_name[name] = tid
            # Store/Controller 类名偶发与实体同词干
            code_cls = str(c.get("code_class") or "").strip()
            if code_cls and code_cls not in by_name:
                by_name[code_cls] = tid
    assocs = [a for a in (model.get("associations") or []) if isinstance(a, dict)]
    existing = {
        (
            str(a.get("from")),
            str(a.get("to")),
            str(a.get("kind") or "association"),
        )
        for a in assocs
    }
    added = 0
    for r in oo_rels:
        frm_n = str(r.get("from_class") or "")
        to_n = str(r.get("to_class") or "")
        kind = str(r.get("kind") or "inheritance")
        frm = by_name.get(frm_n)
        to = by_name.get(to_n)
        if not frm or not to:
            continue
        key = (frm, to, kind)
        if key in existing:
            continue
        existing.add(key)
        assocs.append(
            {
                "from": frm,
                "to": to,
                "from_class": frm_n,
                "to_class": to_n,
                "via": kind,
                "kind": kind,
                "label": "",
            }
        )
        added += 1
    if added:
        model["associations"] = assocs
    return added


# 依赖边：方法/属性类型里出现的其它类名（排除常见 JDK / 框架类型）
_DEP_SKIP_TYPES = frozenset(
    {
        "String",
        "Integer",
        "Long",
        "Boolean",
        "Double",
        "Float",
        "Object",
        "Number",
        "Void",
        "void",
        "Map",
        "List",
        "Set",
        "Collection",
        "Optional",
        "BigDecimal",
        "LocalDate",
        "LocalTime",
        "LocalDateTime",
        "Date",
        "Time",
        "Timestamp",
        "UUID",
        "byte",
        "Byte",
        "Character",
        "char",
        "short",
        "Short",
        "int",
        "long",
        "boolean",
        "double",
        "float",
        "R",
        "Response",
        "Request",
        "HttpServletRequest",
        "HttpServletResponse",
        "Model",
        "Page",
        "Result",
        "JSONObject",
        "JSONArray",
    }
)


def _type_name_tokens(raw: str) -> list[str]:
    """从 ``Map<String, Book>`` / ``Book[]`` 等抽出 PascalCase 类型名。"""
    return re.findall(r"\b([A-Z][A-Za-z0-9_]*)\b", str(raw or ""))


def infer_dependency_relations(model: dict[str, Any]) -> int:
    """方法参数/返回值或属性类型引用其它类 → 依赖（虚线开口箭头）。

    若两端已有关联/聚合/组合/继承/实现，不再叠加依赖。
    """
    classes = [c for c in (model.get("classes") or []) if isinstance(c, dict)]
    by_name: dict[str, str] = {}
    for c in classes:
        name = str(c.get("name") or "").strip()
        tid = str(c.get("id") or "").strip()
        if name and tid:
            by_name[name] = tid

    assocs = [a for a in (model.get("associations") or []) if isinstance(a, dict)]
    linked: set[tuple[str, str]] = set()
    for a in assocs:
        u, v = str(a.get("from") or ""), str(a.get("to") or "")
        if not u or not v or u == v:
            continue
        linked.add((u, v) if u < v else (v, u))

    existing_dep = {
        (str(a.get("from")), str(a.get("to")))
        for a in assocs
        if str(a.get("kind") or "") == "dependency"
    }
    added = 0
    for cls in classes:
        frm = str(cls.get("id") or "")
        frm_name = str(cls.get("name") or "")
        if not frm or not frm_name:
            continue
        blobs: list[str] = []
        for m in cls.get("methods") or []:
            if not isinstance(m, dict):
                continue
            blobs.append(str(m.get("params") or ""))
            blobs.append(str(m.get("return") or ""))
        for a in cls.get("attributes") or []:
            if isinstance(a, dict):
                blobs.append(str(a.get("type") or ""))
        refs: set[str] = set()
        for blob in blobs:
            for tok in _type_name_tokens(blob):
                if tok in _DEP_SKIP_TYPES or tok == frm_name:
                    continue
                if tok in by_name:
                    refs.add(tok)
        for to_name in sorted(refs):
            to = by_name[to_name]
            if to == frm:
                continue
            pair = (frm, to) if frm < to else (to, frm)
            if pair in linked:
                continue
            if (frm, to) in existing_dep:
                continue
            existing_dep.add((frm, to))
            linked.add(pair)
            assocs.append(
                {
                    "from": frm,
                    "to": to,
                    "from_class": frm_name,
                    "to_class": to_name,
                    "via": "type_ref",
                    "kind": "dependency",
                    "label": "",
                }
            )
            added += 1
    if added:
        model["associations"] = assocs
    return added
