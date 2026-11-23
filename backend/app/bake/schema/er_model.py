"""E-R：从 schema.sql 解析表/FK，组装模型。

毕设口径：
- 概念实体 vs 纯 M:N 中间表（assoc link）
- 中间表在总图塌成 N:M 菱形，不进实体属性图清单
- UNIQUE 外键 → 1:1
"""

from __future__ import annotations

import json
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
    auto_increment: bool = False
    comment: str | None = None


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
                # 联合 UNIQUE 只保证组合不重复，不能把单列当成 1:1
                names = [c for c in re.findall(r"`?(\w+)`?", um.group(1)) if c]
                if len(names) == 1:
                    unique_cols.add(names[0])
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
            comment = None
            try:
                from app.services.zh_lexicon import extract_comment_from_line

                comment = extract_comment_from_line(line)
            except Exception:  # noqa: BLE001
                comment = None
            cols.append(
                Column(
                    name=cname,
                    type=ctype,
                    pk=is_pk,
                    not_null="NOT NULL" in upper,
                    unique=is_unique,
                    auto_increment="AUTO_INCREMENT" in upper,
                    comment=comment,
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
                # 单据进度 / 上传附件 / 报销明细 / 出差行程：ticket_id → 父单据表
                if c.name == "ticket_id":
                    if t.name.endswith("_progress") and len(t.name) > 8:
                        candidates.append(t.name[: -len("_progress")])
                    elif t.name.endswith("_attach") and len(t.name) > 8:
                        candidates.append(t.name[: -len("_attach")])
                    elif t.name in ("ticket_expense_line", "ticket_trip_leg", "ticket_club_member", "ticket_attach_rev"):
                        for n in names:
                            if n.endswith("_apply"):
                                candidates.append(n)
                if c.name == "task_id" and t.name == "checkin_spot_member":
                    candidates.append("checkin_spot_task")
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


def infer_relations(
    tables: list[Table],
    *,
    collapse_links: bool = True,
) -> list[Relation]:
    """从表 FK 抽联系。

    ``collapse_links=True``（E-R 总图）：纯 M:N 中间表塌成两父 N:M。
    ``False``（类图）：保留中间表外键边，禁止再画 User↔Product 这类塌缩边。
    """
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
    if collapse_links:
        return collapse_assoc_link_relations(tables, rels)
    return rels


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


# 论文概念总图不画：登录/会话/审计壳与纯 M:N 中间表矩形（物理表仍在 schema / 4.6.3）
# 与类图 sample 壳表对齐，保证各开题概念图密度接近样例论文
_ER_SAMPLE_SHELL_TABLES: frozenset[str] = frozenset(
    {
        "sys_auth_session",
        "sys_login_log",
        "sys_account_cancel",
        "sys_notice_ack",
        "sys_banner",
        "sys_site_stat",
        "sys_audit_log",
        "sys_message_template",
        "product_category",
    }
)

ER_DISPLAY_MODES: tuple[tuple[str, str], ...] = (
    ("sample", "论文概念（精简）"),
    ("full", "全量（含角色拆分/壳表）"),
)


def normalize_er_display(raw: str | None) -> str:
    m = str(raw or "sample").strip().lower()
    return "full" if m == "full" else "sample"


def _collapse_role_side(name: str) -> str:
    n = str(name or "").strip()
    if n.startswith("sys_user:"):
        return "sys_user"
    return n


def sample_omit_tables_from_schema(domain: dict | None) -> list[str]:
    """论文概念图按交付菜单藏表：用户端未挂 addresses → 概念图不画 user_address。

    跟能力名解耦：seat_select / 酒店 / 租车等凡摘掉地址簿菜单的，同一规则；
    full 模式与物理 SQL 仍保留表。
    """
    if not isinstance(domain, dict):
        return []
    menus = domain.get("menus") if isinstance(domain.get("menus"), dict) else {}
    user = menus.get("user") if isinstance(menus.get("user"), list) else []
    keys = {
        str(m.get("key") or "").strip()
        for m in user
        if isinstance(m, dict) and m.get("key")
    }
    omit: list[str] = []
    if "addresses" not in keys:
        omit.append("user_address")
    return omit


def _is_sample_shell_table(name: str, extra: set[str] | frozenset[str] | None = None) -> bool:
    n = str(name or "").strip()
    if not n:
        return False
    bag = _ER_SAMPLE_SHELL_TABLES | (set(extra) if extra else set())
    if n in bag:
        return True
    base = n.split(":", 1)[0]
    return base in bag


def apply_er_display_mode(
    model: dict,
    mode: str | None = "sample",
) -> dict:
    """论文概念精简：藏壳表、角色拆分收回单一「用户」、去掉角色间虚边。

    full=现网全量（角色拆分 + 壳表联系仍可见）。
    不改 schema.sql；只影响论文 E-R 图面与导出。
    ``sample_omit_tables``：按交付菜单藏表（如用户端无 addresses → 藏 user_address）。
    """
    mode_n = normalize_er_display(mode)
    out = dict(model) if isinstance(model, dict) else {}
    out["er_display"] = mode_n
    if mode_n == "full":
        out["tables_omitted_sample"] = []
        out["conceptual_entities"] = conceptual_entity_names(out)
        return out

    extra_omit = {
        str(x).strip()
        for x in (out.get("sample_omit_tables") or [])
        if str(x).strip()
    }
    omitted: list[str] = []
    tables: list[dict] = []
    for t in out.get("tables") or []:
        if not isinstance(t, dict):
            continue
        name = str(t.get("name") or "").strip()
        if not name:
            continue
        if t.get("role_of"):
            omitted.append(name)
            continue
        if _is_sample_shell_table(name, extra_omit):
            omitted.append(name)
            continue
        tables.append(dict(t))

    kept = {str(t.get("name") or "") for t in tables}
    # 角色边收回 sys_user 后，确保物理用户表仍在图上
    if "sys_user" not in kept:
        raw_user = next(
            (
                t
                for t in (model.get("tables") or [])
                if isinstance(t, dict) and str(t.get("name") or "") == "sys_user"
            ),
            None,
        )
        if raw_user:
            row = dict(raw_user)
            row.pop("role_of", None)
            row.pop("role_id", None)
            tables.append(row)
            kept.add("sys_user")

    seen_rel: set[tuple[str, str, str]] = set()
    relations: list[dict] = []
    for r in out.get("relations") or []:
        if not isinstance(r, dict):
            continue
        left = _collapse_role_side(str(r.get("left") or ""))
        right = _collapse_role_side(str(r.get("right") or ""))
        if not left or not right or left == right:
            continue
        if left not in kept or right not in kept:
            continue
        if _is_sample_shell_table(left, extra_omit) or _is_sample_shell_table(
            right, extra_omit
        ):
            continue
        via = str(r.get("via") or "")
        key = (left, right, via)
        if key in seen_rel:
            continue
        seen_rel.add(key)
        row = dict(r)
        row["left"] = left
        row["right"] = right
        relations.append(row)

    out["tables"] = tables
    out["relations"] = relations
    out["tables_omitted_sample"] = omitted
    out["conceptual_entities"] = conceptual_entity_names(out)
    return out


def conceptual_entity_names(model: dict) -> list[str]:
    """分图/属性图可选实体：非中间表、非角色拆分逻辑实体、非论文壳表。"""
    extra_omit = {
        str(x).strip()
        for x in (model.get("sample_omit_tables") or [])
        if str(x).strip()
    }
    out: list[str] = []
    for t in model.get("tables") or []:
        if not isinstance(t, dict):
            continue
        if t.get("assoc_link"):
            continue
        if t.get("role_of"):
            continue
        name = str(t.get("name") or "").strip()
        if not name:
            continue
        if _is_sample_shell_table(name, extra_omit):
            continue
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


def _column_display_label(
    col: Column,
    table_name: str,
    czh: dict[str, str],
    tcols: dict[str, dict[str, str]],
    tzh: dict[str, str],
) -> str:
    """展示用中文：COMMON/域表精确键优先于 SQL COMMENT，避免旧注释锁死论文稿。"""
    name = str(col.name or "")
    if name and name in czh:
        return czh[name]
    scoped = (tcols.get(table_name) or {}).get(name) if name else None
    if scoped:
        return str(scoped)
    comment = (col.comment or "").strip()
    if comment:
        return comment
    return _col_zh(name, table_name, czh, tcols, tzh)


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
                        "label": _column_display_label(c, t.name, czh, tcols, tzh),
                        "suggested_zh": _col_zh(c.name, t.name, czh, tcols, tzh),
                    }
                    for c in t.columns
                ],
                "core_columns": [
                    {
                        **asdict(c),
                        "label": _column_display_label(c, t.name, czh, tcols, tzh),
                        "suggested_zh": _col_zh(c.name, t.name, czh, tcols, tzh),
                    }
                    for c in pick_core_attrs(t.columns)
                ],
                "own_columns": [
                    {
                        **asdict(c),
                        "label": _column_display_label(c, t.name, czh, tcols, tzh),
                        "suggested_zh": _col_zh(c.name, t.name, czh, tcols, tzh),
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
    try:
        domain = json.loads(domain_path.read_text(encoding="utf-8")) if domain_path.is_file() else {}
    except Exception:  # noqa: BLE001
        domain = {}
    omit = sample_omit_tables_from_schema(domain if isinstance(domain, dict) else None)
    if omit:
        model["sample_omit_tables"] = sorted(
            set(model.get("sample_omit_tables") or []) | set(omit)
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
        # 先盖物理表（含 sys_user 列），再拆角色实体；交付列词优先于 COMMON
        model = apply_er_label_patch(model, patch, col_zh_priority=czh)
    # 同一张用户表按 JSON roles 拆逻辑实体（申领人 / 库管员…），总图不再只写「用户」
    model = expand_user_role_entities(model, domain_path)
    if with_er_patch:
        # 再盖一次：角色实体表名（sys_user:user）与展开后的联系名
        model = apply_er_label_patch(model, patch, col_zh_priority=czh)
    # 角色展开后重算概念实体清单（中间表标记保留）
    model = annotate_assoc_links(model, raw_tables)
    return mark_page_missing(model, page_index)


def load_schema_model(workspace: Path) -> dict | None:
    return build_schema_model(workspace, with_er_patch=True)
