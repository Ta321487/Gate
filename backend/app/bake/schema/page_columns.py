"""从学生页上写明了字段名的绑定取列中文名。

打开路由挂到的每个 Vue：用页内 `/api/...` 对上 schema 表名；对不上再用列集合唯一命中。
不在整个前端里盲搜列名，不读旁边的句子，不读脚本变量。
词表里已经是中文的不改。同一列多个中文若一个包住另一个，用长的那个；否则不用。
页面上没有绑定、又只是后缀猜出来的「时间」，改回列名并标 page_missing，不交给补全去编。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from app.bake.schema.er_labels import looks_latin
from app.bake.schema.er_zh import _COL_SUFFIX_RULES, _COMMON_COL_ZH, _STEM_ZH

# 表头挤出来的字，不是字段含义
_CHROME = frozenset({"时间", "操作"})
_ATTR_MAX = 8
_COL_LISTS = ("columns", "core_columns", "own_columns")
# 多表共有，不能单独拿来认表
_GENERIC_COLS = frozenset(
    {
        "id",
        "username",
        "created_at",
        "updated_at",
        "status",
        "body",
        "remark",
        "note",
        "title",
        "content",
    }
)

_ROUTE_PATH = re.compile(r"""path:\s*['"]([a-z0-9/-]+)['"]""")
_IMPORT = re.compile(r"""import\(\s*['"](\.\./views/[^'"]+\.vue)['"]""")
_NEXT_PATH = re.compile(r"""\bpath:\s*['"]""")
_TEMPLATE = re.compile(
    r"<template[^>]*>([\s\S]*)</template>\s*<script",
    re.IGNORECASE,
)
_TEMPLATE_LOOSE = re.compile(r"<template[^>]*>([\s\S]*)</template>", re.IGNORECASE)
_COL_BLOCK = re.compile(
    r"<el-table-column\b([^>]*?)(?:/>|>([\s\S]*?)</el-table-column>)",
    re.IGNORECASE,
)
_LITERAL_ATTR = re.compile(
    r"""(?<![:\w-])(prop|label)\s*=\s*(?P<q>['"])(?P<v>.*?)(?P=q)"""
)
_FIELD_REF = re.compile(r"""\b(?:row|n|rv|item|it)\.([A-Za-z_][A-Za-z0-9_]*)""")
_CLASS_TAG = re.compile(
    r"""<([a-zA-Z0-9-]+)\b[^>]*\bclass=(?P<q>['"])(?P<cls>.*?)(?P=q)[^>]*>(?P<text>[^<{]{1,24})</\1>""",
    re.IGNORECASE,
)
_ZH = re.compile(r"[\u4e00-\u9fff]+")
_API_STEM = re.compile(r"""['"`]/api/(?:admin/)?([a-z0-9-]+)""")


def _camel_to_snake(name: str) -> str:
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", (name or "").strip())
    return s.replace("-", "_").lower()


def _pure_zh(raw: str) -> str | None:
    s = re.sub(r"\s+", "", raw or "")
    if not s or len(s) > _ATTR_MAX or s in _CHROME:
        return None
    if looks_latin(s) or not _ZH.fullmatch(s):
        return None
    return s


@dataclass
class PageColumnIndex:
    scanned: set[str] = field(default_factory=set)
    labels: dict[str, dict[str, str]] = field(default_factory=dict)


def pick_page_label(candidates: set[str]) -> str | None:
    """一个包住另一个就用长的；谁也不包含谁则不用。"""
    xs = sorted({c for c in candidates if c}, key=lambda s: (-len(s), s))
    if not xs:
        return None
    longest = xs[0]
    if all(other in longest for other in xs[1:]):
        return longest
    return None


def is_weak_suffix_label(name: str, label: str, czh: dict[str, str] | None = None) -> bool:
    """词根不认识时后缀规则吐出的默认词（如 replied_at → 时间）。"""
    extra = czh or {}
    for suffix, default, _fmt in _COL_SUFFIX_RULES:
        if not name.endswith(suffix) or len(name) <= len(suffix) or label != default:
            continue
        stem = name[: -len(suffix)]
        if extra.get(stem) or _COMMON_COL_ZH.get(stem) or _STEM_ZH.get(stem):
            continue
        return True
    return False


def _template_of(src: str) -> str:
    m = _TEMPLATE.search(src or "")
    if m:
        return m.group(1)
    m2 = _TEMPLATE_LOOSE.search(src or "")
    return m2.group(1) if m2 else ""


def _literal_attrs(attrs: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _LITERAL_ATTR.finditer(attrs or ""):
        out[m.group(1)] = m.group("v")
    return out


def bindings_in_template(template: str) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}

    def add(col: str, label: str | None) -> None:
        if col and label:
            found.setdefault(col, set()).add(label)

    for m in _COL_BLOCK.finditer(template or ""):
        attrs = _literal_attrs(m.group(1) or "")
        inner = m.group(2) or ""
        label = _pure_zh(attrs.get("label") or "")
        prop = (attrs.get("prop") or "").strip()
        if prop and label:
            add(_camel_to_snake(prop), label)
        if label and inner:
            for ref in _FIELD_REF.findall(inner):
                add(_camel_to_snake(ref), label)

    for m in _CLASS_TAG.finditer(template or ""):
        label = _pure_zh(m.group("text") or "")
        if not label:
            continue
        for token in (m.group("cls") or "").split():
            if not token.endswith("-tag") or len(token) <= 4:
                continue
            stem = token[: -len("-tag")]
            col = _camel_to_snake(stem)
            if not col:
                continue
            if re.search(rf"\.{re.escape(stem)}\b", template) or re.search(
                rf"\.{re.escape(col)}\b", template
            ):
                add(col, label)
    return found


def _vue_paths(router_src: str) -> list[str]:
    """路由里挂到的全部 Vue，去重保序。"""
    seen: set[str] = set()
    out: list[str] = []
    for m in _ROUTE_PATH.finditer(router_src or ""):
        window = router_src[m.end() : m.end() + 500]
        stop = _NEXT_PATH.search(window)
        chunk = window[: stop.start()] if stop else window
        im = _IMPORT.search(chunk)
        if not im:
            continue
        rel = im.group(1)
        if rel in seen:
            continue
        seen.add(rel)
        out.append(rel)
    return out


def _api_stems(src: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in _API_STEM.finditer(src or ""):
        stem = m.group(1)
        if stem in {"upload", "auth", "profile"} or stem in seen:
            continue
        seen.add(stem)
        out.append(stem)
    return out


def _stem_forms(stem: str) -> list[str]:
    snake = (stem or "").replace("-", "_").strip("_")
    if not snake:
        return []
    forms = [snake]
    if snake.endswith("ies") and len(snake) > 3:
        forms.append(snake[:-3] + "y")
    if snake.endswith(("sses", "xes", "zes", "ches", "shes")):
        forms.append(snake[:-2])
    elif snake.endswith("oes") and len(snake) > 3:
        forms.append(snake[:-2])
    elif snake.endswith("es") and len(snake) > 4:
        forms.append(snake[:-2])
    if snake.endswith("s") and not snake.endswith("ss") and len(snake) > 2:
        forms.append(snake[:-1])
    seen: set[str] = set()
    out: list[str] = []
    for f in forms:
        if f and f not in seen:
            seen.add(f)
            out.append(f)
    return out


def resolve_api_stem(stem: str, tables: set[str]) -> str | None:
    """把 /api/order-reviews 这类资源名唯一落到物理表。"""
    if not stem or not tables:
        return None
    hits: list[str] = []
    for form in _stem_forms(stem):
        for t in tables:
            if t == form or t.endswith("_" + form):
                hits.append(t)
    # 保序去重
    uniq: list[str] = []
    seen: set[str] = set()
    for h in hits:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    if len(uniq) == 1:
        return uniq[0]
    return None


def resolve_by_columns(
    bound_cols: set[str],
    table_columns: dict[str, set[str]],
) -> str | None:
    """绑定列集合只被一张表完整盖住，或特色列只命中一张表。"""
    if not bound_cols or not table_columns:
        return None
    distinctive = {c for c in bound_cols if c not in _GENERIC_COLS}
    full: list[str] = []
    for name, cols in table_columns.items():
        if bound_cols <= cols:
            full.append(name)
    if len(full) == 1:
        return full[0]
    if distinctive:
        owners: list[str] = []
        for name, cols in table_columns.items():
            if distinctive <= cols:
                owners.append(name)
        if len(owners) == 1:
            return owners[0]
    return None


def resolve_page_table(
    src: str,
    bound_cols: set[str],
    tables: set[str],
    table_columns: dict[str, set[str]] | None = None,
) -> str | None:
    """一页对多张表 API 时：能唯一认主表才认，否则放弃。"""
    stems = _api_stems(src)
    resolved: list[str] = []
    seen: set[str] = set()
    for stem in stems:
        hit = resolve_api_stem(stem, tables)
        if hit and hit not in seen:
            seen.add(hit)
            resolved.append(hit)
    if len(resolved) == 1:
        return resolved[0]
    cols_map = table_columns or {}
    if len(resolved) > 1 and cols_map:
        # 多资源页：看绑定列更贴哪张已解析表
        best: list[str] = []
        best_score = 0
        for t in resolved:
            cols = cols_map.get(t) or set()
            score = len(bound_cols & cols)
            distinct = len((bound_cols & cols) - _GENERIC_COLS)
            score = score * 10 + distinct
            if score > best_score:
                best_score = score
                best = [t]
            elif score == best_score and score > 0:
                best.append(t)
        if len(best) == 1 and best_score >= 12:
            return best[0]
        return None
    if not resolved:
        return resolve_by_columns(bound_cols, cols_map)
    return None


def _table_columns_from_model(model: dict | None) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    if not isinstance(model, dict):
        return out
    for t in model.get("tables") or []:
        if not isinstance(t, dict):
            continue
        name = str(t.get("name") or "")
        if not name:
            continue
        cols: set[str] = set()
        for key in _COL_LISTS:
            for c in t.get(key) or []:
                if isinstance(c, dict) and c.get("name"):
                    cols.add(str(c["name"]))
        if cols:
            out[name] = cols
    return out


def page_column_index(
    workspace: Path,
    *,
    tables: set[str] | None = None,
    table_columns: dict[str, set[str]] | None = None,
    model: dict | None = None,
) -> PageColumnIndex:
    router = workspace / "frontend" / "src" / "router" / "index.js"
    if not router.is_file():
        return PageColumnIndex()
    try:
        src = router.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return PageColumnIndex()

    cols_map = table_columns or _table_columns_from_model(model)
    table_names = set(tables or ()) or set(cols_map) or set()
    if not table_names:
        # 无 schema 时仍读页，但无法认表
        return PageColumnIndex()

    scanned: set[str] = set()
    buckets: dict[str, dict[str, set[str]]] = {}
    root = workspace / "frontend" / "src"
    for rel in _vue_paths(src):
        rel_path = rel[3:] if rel.startswith("../") else rel
        path = (root / rel_path).resolve()
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        found = bindings_in_template(_template_of(text))
        if not found:
            continue
        table = resolve_page_table(
            text,
            set(found),
            table_names,
            cols_map,
        )
        if not table:
            continue
        scanned.add(table)
        acc = buckets.setdefault(table, {})
        for col, labels in found.items():
            acc.setdefault(col, set()).update(labels)

    labels: dict[str, dict[str, str]] = {}
    for table, cols in buckets.items():
        picked = {
            col: lab
            for col, cands in cols.items()
            if (lab := pick_page_label(cands))
        }
        if picked:
            labels[table] = picked
    return PageColumnIndex(scanned=scanned, labels=labels)


def apply_page_column_labels(
    model: dict,
    index: PageColumnIndex,
    *,
    czh: dict[str, str] | None = None,
) -> dict:
    """词表中文保持不动。只填仍是英文、或只是弱后缀的列。"""
    if not index.scanned or not isinstance(model, dict):
        return model
    merged = {**_COMMON_COL_ZH, **(czh or {})}
    for t in model.get("tables") or []:
        if not isinstance(t, dict) or str(t.get("name") or "") not in index.scanned:
            continue
        picked = index.labels.get(str(t.get("name") or "")) or {}
        for key in _COL_LISTS:
            for c in t.get(key) or []:
                if not isinstance(c, dict):
                    continue
                name = str(c.get("name") or "")
                label = str(c.get("label") or "")
                weak = is_weak_suffix_label(name, label, merged)
                if label and not looks_latin(label) and not weak:
                    continue
                page = picked.get(name)
                if page:
                    c["label"] = page
                elif weak:
                    c["label"] = name
    return model


def mark_page_missing(model: dict, index: PageColumnIndex) -> dict:
    """扫过的表上仍是英文的列：页面没有可用绑定。"""
    if not index.scanned or not isinstance(model, dict):
        return model
    for t in model.get("tables") or []:
        if not isinstance(t, dict) or str(t.get("name") or "") not in index.scanned:
            continue
        for key in _COL_LISTS:
            for c in t.get(key) or []:
                if not isinstance(c, dict):
                    continue
                label = str(c.get("label") or c.get("name") or "")
                if looks_latin(label):
                    c["page_missing"] = True
                else:
                    c.pop("page_missing", None)
    return model
