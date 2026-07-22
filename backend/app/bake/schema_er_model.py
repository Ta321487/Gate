"""E-R：从 schema.sql 解析表/FK，组装模型。"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.bake.schema_er_labels import (
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
                if c.name in ("book_id", "item_id") and archive:
                    candidates.append(archive)
                if c.name == "slot_id" and "resource_slot" in names:
                    candidates.append("resource_slot")
                # 单据进度 / 上传附件：ticket_id → 父单据表
                if c.name == "ticket_id" and len(t.name) > 8:
                    if t.name.endswith("_progress"):
                        candidates.append(t.name[: -len("_progress")])
                    elif t.name.endswith("_attach"):
                        candidates.append(t.name[: -len("_attach")])
                candidates.extend([base, f"sys_{base}", f"{base}s"])
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
            elif c.name in ("uploaded_by", "uploader", "operator") and "sys_user" in names and t.name != "sys_user":
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
                    name=_rel_label(parent, child, c.name, by_name),
                    left=parent,
                    right=child,
                    card_left="1",
                    card_right="n",
                    via=c.name,
                )
            )
    return rels


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
    model = {
        "tables": [
            {
                "name": t.name,
                "label": _table_zh(t.name, tzh),
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
    }
    # 唯一闸门：联系名不得与实体中文名撞车
    return scrub_relation_labels(model, tzh, rzh)


def build_schema_model(workspace: Path, *, with_er_patch: bool = True) -> dict | None:
    """从工作区 schema.sql 建 E-R 模型；with_er_patch=False 时仅确定性映射。"""
    path = workspace / "sql" / "schema.sql"
    if not path.exists():
        return None
    domain_path = workspace / "domain.schema.json"
    tzh, czh, tcols, rzh, fk_aliases = _labels_from_domain_schema(domain_path)
    model = schema_model(
        path.read_text(encoding="utf-8", errors="ignore"),
        extra_table_zh=tzh,
        extra_col_zh=czh,
        extra_table_cols=tcols,
        extra_rel_zh=rzh,
        fk_aliases=fk_aliases,
    )
    if with_er_patch:
        model = apply_er_label_patch(model, load_er_label_patch(workspace))
    # 同一张用户表按 JSON roles 拆逻辑实体（申领人 / 库管员…），总图不再只写「用户」
    return expand_user_role_entities(model, domain_path)


def load_schema_model(workspace: Path) -> dict | None:
    return build_schema_model(workspace, with_er_patch=True)
