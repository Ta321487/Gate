"""多维分类 multi_category：开题写两组以上分类维度才挂；DOM-SHOP / FOOD / CINEMA。

开岛后分类走 item↔category 关联表；category_id 列可留，运行时不当分类来源。
未开岛：保持单 FK category_id，不改表形态。
"""

from __future__ import annotations

from app.bake.sql.ddl_edit import (
    CREATE_TABLE_RE as _CREATE_TABLE_RE,
    inject_missing_columns as _inject_missing_columns,
    prune_columns as _prune_columns,
)

import re
from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

MULTI_CATEGORY_CAP = "multi_category"

_MULTI_CATEGORY_DOMAINS = frozenset({"DOM-SHOP", "DOM-FOOD", "DOM-CINEMA"})

# 明确「多维 / 多条件」话术。「双维度」与「多维分类」同级，不要求再写「按…分类」。
_MULTI_TERMS = (
    "多条件筛选",
    "多维分类",
    "按维度分类",
    "多维度分类",
    "按多个维度",
    "多个维度分类",
    "双维度",
    "两个维度",
    "两维分类",
    "二维分类",
)

# 「按训练目标：增肌/减脂」这种带取值的轴，出现两组即多维
_AXIS_VALUE_RE = re.compile(
    r"按([\u4e00-\u9fffA-Za-z0-9]{1,12})[：:]([^。；;\n）)]{1,80})"
)

# 单个维度轴（须凑满两组才挂）
_AXIS_TERMS = (
    "按用途",
    "按材质",
    "按品牌",
    "按目标",
    "按部位",
    "按功能",
    "按场景",
    "按风格",
    "按价位",
)

# 「按…分类」出现两次以上
_BY_CLASSIFY_RE = re.compile(r"按[\u4e00-\u9fffA-Za-z0-9]{1,12}分类")

# 「按口味和荤素分类」「按类型和评分分类」——一句里两个维
_AND_CLASSIFY_RE = re.compile(
    r"按([\u4e00-\u9fffA-Za-z0-9]{1,12})(?:和|与|及)([\u4e00-\u9fffA-Za-z0-9]{1,12})分类"
)


def scan_multi_category(text: str, title: str = "") -> bool:
    blob = f"{title or ''}\n{text or ''}"
    if not blob.strip():
        return False
    if any(keyword_mentioned(blob, kw, ignore_contrast=True) for kw in _MULTI_TERMS):
        return True
    if _AND_CLASSIFY_RE.search(blob):
        return True
    axes = sum(1 for kw in _AXIS_TERMS if keyword_mentioned(blob, kw, ignore_contrast=True))
    if axes >= 2:
        return True
    if len(_BY_CLASSIFY_RE.findall(blob)) >= 2:
        return True
    if len(_AXIS_VALUE_RE.findall(blob)) >= 2:
        return True
    return False


def _clean_axis_token(text: str) -> str:
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text or "")[:16]


def parse_category_axes(text: str, title: str = "") -> list[tuple[str, list[str]]]:
    """从「按某维：甲/乙/丙」抽出维度名和取值，供分类种子换掉默认「热销/日用」。

    「按口味和荤素分类」无取值时，每维用维名自身占位，保证至少两维种子。
    """
    blob = f"{title or ''}\n{text or ''}"
    axes: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for match in _AXIS_VALUE_RE.finditer(blob):
        dim = _clean_axis_token(match.group(1))
        if dim.endswith("分类"):
            dim = dim[:-2]
        if not dim or dim in seen:
            continue
        names: list[str] = []
        for part in re.split(r"[/／、,，]", match.group(2)):
            name = _clean_axis_token(part.strip().strip("等"))
            if name and name not in names:
                names.append(name)
        if len(names) < 2:
            continue
        seen.add(dim)
        axes.append((dim, names[:8]))
        if len(axes) >= 4:
            break
    if len(axes) < 2:
        for match in _AND_CLASSIFY_RE.finditer(blob):
            for raw in (match.group(1), match.group(2)):
                dim = _clean_axis_token(raw)
                if not dim or dim in seen:
                    continue
                seen.add(dim)
                axes.append((dim, [dim]))
                if len(axes) >= 4:
                    break
            if len(axes) >= 2:
                break
    return axes


def multi_category_axis_seed_sql(
    axes: list[tuple[str, list[str]]],
    item_table: str,
    junction_table: str,
) -> str:
    """有解析出的轴时，用开题取值替换默认分类名。没有轴则返回空，调用方保留原种子。"""
    rows: list[tuple[str, str]] = []
    for dim, names in axes:
        if not dim:
            continue
        for name in names:
            if name:
                rows.append((dim, name))
    if len(rows) < 2:
        return ""
    item = item_table if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", item_table or "") else "product"
    junc = (
        junction_table
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", junction_table or "")
        else "product_category"
    )
    lines: list[str] = []
    first_of_dim: dict[str, int] = {}
    for index, (dim, name) in enumerate(rows, start=1):
        first_of_dim.setdefault(dim, index)
        if index <= 3:
            lines.append(
                f"UPDATE category SET name='{name}', dimension='{dim}' WHERE id={index};"
            )
        else:
            lines.append(
                "INSERT IGNORE INTO category (id, name, dimension) VALUES "
                f"({index}, '{name}', '{dim}');"
            )
    lines.append(
        f"INSERT IGNORE INTO {junc} (item_id, category_id)\n"
        f"SELECT id, category_id FROM {item} "
        "WHERE category_id IS NOT NULL AND category_id > 0;"
    )
    for cid in first_of_dim.values():
        lines.append(
            f"INSERT IGNORE INTO {junc} (item_id, category_id) VALUES (1, {cid});"
        )
    return "\n".join(lines) + "\n"


def merge_multi_category_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if MULTI_CATEGORY_CAP in out:
        return out
    if (domain or "") not in _MULTI_CATEGORY_DOMAINS:
        return out
    if "archive" not in out:
        return out
    if not scan_multi_category(proposal_text or "", title):
        return out
    out.append(MULTI_CATEGORY_CAP)
    return out


def attach_multi_category_fields(schema: dict[str, Any]) -> None:
    ents = schema.setdefault("entities", {})
    archive = ents.setdefault("archive", {})
    if not isinstance(archive, dict):
        return
    archive["multiCategory"] = True
    # 浏览/表单改走 categoryIds；单列 category 字段改为多选语义
    fields = list(archive.get("fields") or [])
    new_fields: list[dict[str, Any]] = []
    has_ids = False
    for field in fields:
        if not isinstance(field, dict):
            continue
        row = dict(field)
        if row.get("key") == "category":
            row["key"] = "categoryIds"
            row["type"] = "multi-select"
            row.setdefault("label", row.get("label") or "分类")
            has_ids = True
        new_fields.append(row)
    if not has_ids:
        new_fields.append(
            {"key": "categoryIds", "label": "分类", "type": "multi-select"}
        )
    archive["fields"] = new_fields
    labels = schema.setdefault("labels", {})
    labels.setdefault("multiCategoryHint", "可按多个维度勾选分类筛选。")


def apply_multi_category_to_spec(
    spec: dict[str, Any], proposal_text: str = ""
) -> dict[str, Any]:
    title = str(spec.get("title") or "")
    caps = merge_multi_category_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text or "",
        domain=spec.get("domain"),
        title=title,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if MULTI_CATEGORY_CAP not in caps:
        return {**spec, "schema": schema}

    attach_multi_category_fields(schema)
    runtime = dict(spec.get("runtime") or {})
    runtime.setdefault("archive_item_category_table", "product_category")
    spec["runtime"] = runtime

    features = list(spec.get("features") or [])
    names = {f.get("name") for f in features if isinstance(f, dict)}
    if "多维分类" not in names:
        features.append({"name": "多维分类", "status": "module"})
    spec["features"] = features
    spec["schema"] = schema
    return spec


# --- SQL ensure (moved from fragments.py) ---

CATEGORY_DIMENSION_COLUMNS: list[tuple[str, str]] = [
    ("dimension", "VARCHAR(64) NOT NULL DEFAULT ''"),
]

def ensure_multi_category_sql(
    sql: str,
    *,
    enabled: bool,
    item_table: str | None = "product",
    junction_table: str = "product_category",
    axis_seed_sql: str = "",
) -> str:
    """多维分类：category.dimension + 条目-分类关联表。未开不加。"""
    if not enabled:
        return sql
    t = (item_table or "product").strip()
    junc = (junction_table or "product_category").strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", junc):
        junc = "product_category"

    def cat_repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "category":
            return m.group(0)
        body = _inject_missing_columns(body, CATEGORY_DIMENSION_COLUMNS)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(cat_repl, sql)
    if not re.search(
        rf"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?{re.escape(junc)}`?\b", out
    ):
        ddl = f"""
CREATE TABLE IF NOT EXISTS {junc} (
  item_id BIGINT NOT NULL,
  category_id BIGINT NOT NULL,
  PRIMARY KEY (item_id, category_id),
  KEY idx_{junc}_cat (category_id)
);
"""
        out = out.rstrip() + "\n" + ddl
    # 种子：开题解析出维度取值时换掉默认分类名；否则补通用维度演示行
    if (axis_seed_sql or "").strip():
        seed = axis_seed_sql if axis_seed_sql.endswith("\n") else axis_seed_sql + "\n"
    else:
        seed = """
UPDATE category SET dimension='品类' WHERE (dimension IS NULL OR dimension='') AND id IN (1,2,3);
INSERT IGNORE INTO category (id, name, dimension) VALUES
(10, '自用', '用途'), (11, '练手', '用途'),
(12, '入门', '目标'), (13, '进阶', '目标');
"""
        if t and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
            seed += f"""
INSERT IGNORE INTO {junc} (item_id, category_id)
SELECT id, category_id FROM {t} WHERE category_id IS NOT NULL AND category_id > 0;
INSERT IGNORE INTO {junc} (item_id, category_id) VALUES (1, 10), (1, 12), (2, 11), (2, 13);
"""
    out = out.rstrip() + "\n" + seed
    return out
