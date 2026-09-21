"""E-R：从 schema.sql 解析表/FK，组装模型。

毕设口径：
- 概念实体 vs 纯 M:N 中间表（assoc link）
- 中间表在总图塌成 N:M 菱形，不进实体属性图清单
- UNIQUE 外键 → 1:1
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.bake.schema.er_labels import (
    _COMMON_COL_ZH,
    _INFRA_TABLE_ZH,
    _col_zh,
    _labels_from_domain_schema,
    _rel_zh,
    _table_zh,
    apply_er_label_patch,
    expand_user_role_entities,
    load_er_label_patch,
    scrub_relation_labels,
)

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
# UNIQUE KEY `uk` (`user_id`) / UNIQUE (`a`, `b`)
UNIQUE_PAREN_RE = re.compile(
    r"UNIQUE(?:\s+(?:KEY|INDEX)\s+`?\w+`?)?\s*\(([^)]+)\)",
    re.IGNORECASE,
)

# 中间表允许保留的「行项目/元数据」列（除此之外有业务列则不当 link）
_LINK_OWN_ALLOW = frozenset(
    {
        "qty",
        "quantity",
        "num",
        "count",
        "price",
        "amount",
        "unit_price",
        "line_price",
        "total",
        "total_price",
        "created_at",
        "updated_at",
        "remark",
        "note",
        "sort_order",
        "ord",
        "seq",
    }
)


@dataclass
class Column:
    name: str
    type: str
    pk: bool = False
    fk: bool = False
    fk_table: str | None = None
    not_null: bool = False
    unique: bool = False


@dataclass
class Table:
    name: str
    columns: list[Column] = field(default_factory=list)


@dataclass
class Relation:
    name: str
    left: str
    right: str
    card_left: str  # "1" | "n" | "m"
    card_right: str
    via: str


def parse_schema_sql(
    sql: str,
    fk_aliases: dict[str, str] | None = None,
) -> list[Table]:
    tables: list[Table] = []
    for m in CREATE_RE.finditer(sql or ""):
        tname = m.group(1)
        body = m.group(2)
        cols: list[Column] = []
        pk_names: set[str] = set()
        fk_map: dict[str, str] = {}
        unique_cols: set[str] = set()

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
            um = UNIQUE_PAREN_RE.search(line)
            if um:
                for c in re.findall(r"`?(\w+)`?", um.group(1)):
                    unique_cols.add(c)
                continue
            if upper.startswith("KEY") or upper.startswith("INDEX") or upper.startswith(
                "CONSTRAINT"
            ):
                continue
            if upper.startswith("UNIQUE") and "(" not in line:
                continue
            cm = COL_RE.match(line)
            if not cm:
                continue
            cname, ctype = cm.group(1), cm.group(2)
            is_pk = "PRIMARY KEY" in upper
            if is_pk:
                pk_names.add(cname)
            is_unique = "UNIQUE" in upper
            if is_unique:
                unique_cols.add(cname)
            cols.append(
                Column(
                    name=cname,
                    type=ctype,
                    pk=is_pk,
                    not_null="NOT NULL" in upper,
                    unique=is_unique,
                )
            )

        for c in cols:
            if c.name in pk_names:
                c.pk = True
            if c.name in fk_map:
                c.fk = True
                c.fk_table = fk_map[c.name]
            if c.name in unique_cols:
                c.unique = True

        tables.append(Table(name=tname, columns=cols))

    _infer_fk_by_name(tables, fk_aliases)
    return tables


def _infer_fk_by_name(
    tables: list[Table],
    fk_aliases: dict[str, str] | None = None,
) -> None:
    """按列名推断外键；fk_aliases 把 book/item 等别名映射到领域档案表。"""
    names = {t.name for t in tables}
    aliases = {k: v for k, v in (fk_aliases or {}).items() if v}
    archive = aliases.get("archive") or aliases.get("book") or aliases.get("item") or ""
    for t in tables:
        for c in t.columns:
            if c.fk or c.pk:
                continue
            if c.name.endswith("_id") and len(c.name) > 3:
                base = c.name[:-3]
                candidates: list[str] = []
                if base in aliases:
                    candidates.append(aliases[base])
                if c.name in ("book_id", "item_id", "box_id", "prize_id") and archive:
                    candidates.append(archive)
                if c.name == "slot_id" and "resource_slot" in names:
                    candidates.append("resource_slot")
                elif c.name == "slot_id" and "delivery_slot" in names:
                    candidates.append("delivery_slot")
                if c.name == "campaign_id":
                    if t.name.startswith("group") and "group_campaign" in names:
                        candidates.append("group_campaign")
                    elif t.name.startswith("vote") and "vote_campaign" in names:
                        candidates.append("vote_campaign")
                    elif "group_campaign" in names:
                        candidates.append("group_campaign")
                    elif "vote_campaign" in names:
                        candidates.append("vote_campaign")
                if c.name == "consign_id" and "consign_item" in names:
                    candidates.append("consign_item")
                if c.name == "bundle_id" and "service_bundle" in names:
                    candidates.append("service_bundle")
                # 单据进度 / 上传附件：ticket_id → 父单据表
                if c.name == "ticket_id" and len(t.name) > 8:
                    if t.name.endswith("_progress"):
                        candidates.append(t.name[: -len("_progress")])
                    elif t.name.endswith("_attach"):
                        candidates.append(t.name[: -len("_attach")])
                candidates.extend([base, f"sys_{base}", f"{base}s"])
                if base == "order" and "biz_order" in names:
                    candidates.append("biz_order")
                seen_cand: set[str] = set()
                for cand in candidates:
                    if not cand or cand in seen_cand:
                        continue
                    seen_cand.add(cand)
                    if cand in names and cand != t.name:
                        c.fk = True
                        c.fk_table = cand
                        break
            elif c.name == "username" and "sys_user" in names and t.name != "sys_user":
                c.fk = True
                c.fk_table = "sys_user"
            elif (
                c.name.endswith("_username")
                and len(c.name) > 9
                and "sys_user" in names
                and t.name != "sys_user"
            ):
                # publisher_username / assignee_username → 用户
                c.fk = True
                c.fk_table = "sys_user"
            elif (
                c.name in ("uploaded_by", "uploader", "operator")
                and "sys_user" in names
                and t.name != "sys_user"
            ):
                # 上传人 / 流水登记人
                c.fk = True
                c.fk_table = "sys_user"


def _short_name(table: str) -> str:
    return table.replace("sys_", "")


def _rel_label(parent: str, child: str, via: str, by_name: dict[str, Table]) -> str:
    """联系内部名：必须唯一（含 via），避免多条联系都叫 user 被补丁盖成「用户」。"""
    _ = parent
    _ = by_name
    if child.endswith("_progress"):
        return f"{child}:progress"
    if child.endswith("_attach"):
        return f"{child}:attach"
    if via:
        return f"{child}:{via}"
    return child


def _fk_parents(t: Table) -> list[str]:
    """去重后的外键父表（保序）。"""
    out: list[str] = []
    seen: set[str] = set()
    for c in t.columns:
        if not c.fk or not c.fk_table:
            continue
        if c.fk_table in seen or c.fk_table == t.name:
            continue
        seen.add(c.fk_table)
        out.append(c.fk_table)
    return out


def _is_referenced_as_parent(tname: str, tables: list[Table]) -> bool:
    for other in tables:
        if other.name == tname:
            continue
        for c in other.columns:
            if c.fk and c.fk_table == tname:
                return True
    return False


def is_assoc_link(t: Table, tables: list[Table]) -> bool:
    """纯 M:N 抽离中间表：恰好两父、叶子、自身列仅限行项目/时间戳。"""
    parents = _fk_parents(t)
    if len(parents) != 2:
        return False
    if _is_referenced_as_parent(t.name, tables):
        return False
    own = [c for c in t.columns if not c.pk and not c.fk]
    if any(c.name.lower() not in _LINK_OWN_ALLOW for c in own):
        return False
    return True


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
            card_right = "1" if c.unique else "n"
            rels.append(
                Relation(
                    name=_rel_label(parent, child, c.name, by_name),
                    left=parent,
                    right=child,
                    card_left="1",
                    card_right=card_right,
                    via=c.name,
                )
            )
    return collapse_assoc_link_relations(tables, rels)


def collapse_assoc_link_relations(
    tables: list[Table], relations: list[Relation]
) -> list[Relation]:
    """去掉「父→中间表」边，改为两父实体之间的 N:M。"""
    link_names = {t.name for t in tables if is_assoc_link(t, tables)}
    if not link_names:
        return relations
    by_name = {t.name: t for t in tables}
    kept: list[Relation] = []
    for r in relations:
        if r.right in link_names or r.left in link_names:
            continue
        kept.append(r)
    seen_nm: set[tuple[str, str, str]] = set()
    for tname in sorted(link_names):
        t = by_name.get(tname)
        if not t:
            continue
        parents = _fk_parents(t)
        if len(parents) != 2:
            continue
        a, b = parents[0], parents[1]
        # 稳定左右：字典序，避免同对重复
        left, right = (a, b) if a <= b else (b, a)
        key = (left, right, tname)
        if key in seen_nm:
            continue
        seen_nm.add(key)
        kept.append(
            Relation(
                name=f"{tname}:nm",
                left=left,
                right=right,
                card_left="n",
                card_right="m",
                via=tname,
            )
        )
    return kept


def pick_core_attrs(cols: list[Column], limit: int = 5) -> list[Column]:
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
        "name",
        "title",
        "username",
        "status",
        "role",
        "nickname",
        "isbn",
        "author",
        "stock",
        "content",
        "phone",
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


def _own_attr_columns(cols: list[Column]) -> list[Column]:
    """实体属性图：自身属性（去外键）。"""
    return [c for c in cols if not c.fk]


def conceptual_entity_names(model: dict) -> list[str]:
    """分图/属性图可选实体：非中间表、非角色拆分逻辑实体。"""
    out: list[str] = []
    for t in model.get("tables") or []:
        if not isinstance(t, dict):
            continue
        if t.get("assoc_link"):
            continue
        if t.get("role_of"):
            continue
        name = str(t.get("name") or "").strip()
        if name:
            out.append(name)
    return out


def annotate_assoc_links(model: dict, tables: list[Table]) -> dict:
    """给 model.tables 打 assoc_link，并写 link_tables / conceptual_entities。"""
    link_names = {t.name for t in tables if is_assoc_link(t, tables)}
    out_tables: list[dict] = []
    for t in model.get("tables") or []:
        if not isinstance(t, dict):
            continue
        row = dict(t)
        name = str(row.get("name") or "")
        # 角色实体不是中间表
        if row.get("role_of"):
            row["assoc_link"] = False
        else:
            row["assoc_link"] = name in link_names
        out_tables.append(row)
    model = {**model, "tables": out_tables}
    model["link_tables"] = sorted(link_names)
    model["conceptual_entities"] = conceptual_entity_names(model)
    return model


def schema_model(
    sql: str,
    extra_table_zh: dict[str, str] | None = None,
    extra_col_zh: dict[str, str] | None = None,
    extra_table_cols: dict[str, dict[str, str]] | None = None,
    extra_rel_zh: dict[str, str] | None = None,
    fk_aliases: dict[str, str] | None = None,
) -> dict:
    tables = parse_schema_sql(sql, fk_aliases=fk_aliases)
    relations = infer_relations(tables)
    tzh = {**_INFRA_TABLE_ZH, **(extra_table_zh or {})}
    czh = {**_COMMON_COL_ZH, **(extra_col_zh or {})}
    tcols = dict(extra_table_cols or {})
    rzh = dict(extra_rel_zh or {})
    link_names = {t.name for t in tables if is_assoc_link(t, tables)}
    model = {
        "tables": [
            {
                "name": t.name,
                "label": _table_zh(t.name, tzh),
                "assoc_link": t.name in link_names,
                "columns": [
                    {
                        **asdict(c),
                        "label": _col_zh(c.name, t.name, czh, tcols, tzh),
                    }
                    for c in t.columns
                ],
                "core_columns": [
                    {
                        **asdict(c),
                        "label": _col_zh(c.name, t.name, czh, tcols, tzh),
                    }
                    for c in pick_core_attrs(t.columns)
                ],
                "own_columns": [
                    {
                        **asdict(c),
                        "label": _col_zh(c.name, t.name, czh, tcols, tzh),
                    }
                    for c in _own_attr_columns(t.columns)
                ],
            }
            for t in tables
        ],
        "relations": [
            {
                **asdict(r),
                "label": _rel_zh(r.name, r.via, r.left, r.right, tzh, rzh),
            }
            for r in relations
        ],
        "link_tables": sorted(link_names),
    }
    model["conceptual_entities"] = conceptual_entity_names(model)
    # 唯一闸门：联系名不得与实体中文名撞车
    return scrub_relation_labels(model, tzh, rzh)


def build_schema_model(workspace: Path, *, with_er_patch: bool = True) -> dict | None:
    """从工作区 schema.sql 建 E-R 模型；with_er_patch=False 时仅确定性映射。"""
    path = workspace / "sql" / "schema.sql"
    if not path.exists():
        return None
    domain_path = workspace / "domain.schema.json"
    tzh, czh, tcols, rzh, fk_aliases = _labels_from_domain_schema(domain_path)
    sql = path.read_text(encoding="utf-8", errors="ignore")
    raw_tables = parse_schema_sql(sql, fk_aliases=fk_aliases)
    model = schema_model(
        sql,
        extra_table_zh=tzh,
        extra_col_zh=czh,
        extra_table_cols=tcols,
        extra_rel_zh=rzh,
        fk_aliases=fk_aliases,
    )
    from app.bake.schema.page_columns import (
        apply_page_column_labels,
        mark_page_missing,
        page_column_index,
    )

    page_index = page_column_index(workspace, model=model)
    model = apply_page_column_labels(model, page_index, czh=czh)
    patch = load_er_label_patch(workspace) if with_er_patch else None
    if with_er_patch:
        # 先盖物理表（含 sys_user 列），再拆角色实体
        model = apply_er_label_patch(model, patch)
    # 同一张用户表按 JSON roles 拆逻辑实体（申领人 / 库管员…），总图不再只写「用户」
    model = expand_user_role_entities(model, domain_path)
    if with_er_patch:
        # 再盖一次：角色实体表名（sys_user:user）与展开后的联系名
        model = apply_er_label_patch(model, patch)
    # 角色展开后重算概念实体清单（中间表标记保留）
    model = annotate_assoc_links(model, raw_tables)
    return mark_page_missing(model, page_index)


def load_schema_model(workspace: Path) -> dict | None:
    return build_schema_model(workspace, with_er_patch=True)
