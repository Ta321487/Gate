"""档案主表 author/isbn 物理列按域语义化（API 仍用逻辑键 author/isbn）。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.bake.sql.ddl_edit import (
    map_create_table,
    rewrite_col_def,
    rewrite_insert_col_names,
    rewrite_update_col_names,
    valid_ident,
)

# logical → (physical_name, ddl_type)
ArchiveCol = tuple[str, str]

# domain -> (author_phys, author_ddl, isbn_phys, isbn_ddl)
ARCHIVE_COLUMN_SPEC: dict[str, tuple[ArchiveCol, ArchiveCol]] = {
    "DOM-LIBRARY": (
        ("author", "VARCHAR(100)"),
        ("isbn", "VARCHAR(32)"),
    ),
    "DOM-EQUIP": (
        ("brand_model", "VARCHAR(100)"),
        ("asset_no", "VARCHAR(64)"),
    ),
    "DOM-ASSET": (
        ("spec_model", "VARCHAR(100)"),
        ("asset_no", "VARCHAR(64)"),
    ),
    "DOM-CRM": (
        ("contact_name", "VARCHAR(100)"),
        ("contact_note", "VARCHAR(255)"),
    ),
    "DOM-EVENT": (
        ("handler_name", "VARCHAR(100)"),
        ("case_summary", "VARCHAR(255)"),
    ),
    "DOM-ATTEND": (
        ("scope_note", "VARCHAR(100)"),
        ("apply_note", "VARCHAR(255)"),
    ),
    "DOM-FUND": (
        ("own_unit", "VARCHAR(100)"),
        ("quota_note", "VARCHAR(255)"),
    ),
    "DOM-LABSAFE": (
        ("building_lead", "VARCHAR(100)"),
        ("safety_note", "VARCHAR(255)"),
    ),
    "DOM-RECRUIT": (
        ("hire_dept", "VARCHAR(100)"),
        ("salary_note", "VARCHAR(255)"),
    ),
    "DOM-DATING": (
        ("city_name", "VARCHAR(100)"),
        ("intent_note", "VARCHAR(255)"),
    ),
    "DOM-GRADE": (
        ("teacher_name", "VARCHAR(100)"),
        ("course_code", "VARCHAR(255)"),
    ),
    "DOM-INTERN": (
        ("mentor_name", "VARCHAR(100)"),
        ("org_note", "VARCHAR(255)"),
    ),
    "DOM-PARCEL": (
        ("station_name", "VARCHAR(100)"),
        ("pickup_code", "VARCHAR(255)"),
    ),
    "DOM-SEAL": (
        ("keeper_dept", "VARCHAR(100)"),
        ("seal_scope", "VARCHAR(255)"),
    ),
    "DOM-FLEET": (
        ("driver_name", "VARCHAR(100)"),
        ("vehicle_note", "VARCHAR(255)"),
    ),
    "DOM-CERT": (
        ("issue_dept", "VARCHAR(100)"),
        ("purpose_note", "VARCHAR(255)"),
    ),
    "DOM-PROMO": (
        ("apply_unit", "VARCHAR(100)"),
        ("post_place", "VARCHAR(255)"),
    ),
    "DOM-FITOUT": (
        ("contractor", "VARCHAR(100)"),
        ("work_req", "VARCHAR(255)"),
    ),
    "DOM-ACAD": (
        ("accept_dept", "VARCHAR(100)"),
        ("material_note", "VARCHAR(255)"),
    ),
    "DOM-TRIP": (
        ("own_dept", "VARCHAR(100)"),
        ("fill_note", "VARCHAR(255)"),
    ),
    "DOM-EXPENSE": (
        ("own_dept", "VARCHAR(100)"),
        ("budget_note", "VARCHAR(255)"),
    ),
    "DOM-CREDIT": (
        ("dept_name", "VARCHAR(100)"),
        ("note_hint", "VARCHAR(255)"),
    ),
    "DOM-LABOR": (
        ("dept_name", "VARCHAR(100)"),
        ("note_hint", "VARCHAR(255)"),
    ),
    "DOM-EVAL": (
        ("lecturer_name", "VARCHAR(100)"),
        ("course_note", "VARCHAR(255)"),
    ),
    "DOM-MORAL": (
        ("dept_name", "VARCHAR(100)"),
        ("note_hint", "VARCHAR(255)"),
    ),
    "DOM-AWARD": (
        ("dept_name", "VARCHAR(100)"),
        ("note_hint", "VARCHAR(255)"),
    ),
    "DOM-BED": (
        ("building_name", "VARCHAR(100)"),
        ("layout_note", "VARCHAR(255)"),
    ),
    "DOM-CHECKIN": (
        ("building_name", "VARCHAR(100)"),
        ("room_note", "VARCHAR(255)"),
    ),
    "DOM-INSTRUMENT": (
        ("lab_name", "VARCHAR(100)"),
        ("model_note", "VARCHAR(255)"),
    ),
    "DOM-MUTUAL-TUTOR": (
        ("college_name", "VARCHAR(100)"),
        ("research_note", "VARCHAR(255)"),
    ),
    "DOM-MUTUAL-TOPIC": (
        ("college_name", "VARCHAR(100)"),
        ("research_note", "VARCHAR(255)"),
    ),
    "DOM-MUTUAL-TEAM": (
        ("college_name", "VARCHAR(100)"),
        ("skill_note", "VARCHAR(255)"),
    ),
    "DOM-VISITOR": (
        ("zone_place", "VARCHAR(100)"),
        ("receive_note", "VARCHAR(255)"),
    ),
    "DOM-CARPASS": (
        ("dept_name", "VARCHAR(100)"),
        ("note_hint", "VARCHAR(255)"),
    ),
    "DOM-LISTING": (
        ("estate_area", "VARCHAR(100)"),
        ("house_type_note", "VARCHAR(255)"),
    ),
    "DOM-PROCURE": (
        ("own_dept", "VARCHAR(100)"),
        ("item_spec", "VARCHAR(255)"),
    ),
    "DOM-CLUB": (
        ("guide_unit", "VARCHAR(100)"),
        ("matter_note", "VARCHAR(255)"),
    ),
    "DOM-PROJ": (
        ("own_unit", "VARCHAR(100)"),
        ("declare_note", "VARCHAR(255)"),
    ),
    "DOM-ETHIC": (
        ("own_unit", "VARCHAR(100)"),
        ("material_brief", "VARCHAR(255)"),
    ),
    "DOM-PARTY": (
        ("party_org", "VARCHAR(100)"),
        ("material_brief", "VARCHAR(255)"),
    ),
    "DOM-CONTRACT": (
        ("own_dept", "VARCHAR(100)"),
        ("approve_note", "VARCHAR(255)"),
    ),
    "DOM-EXAM": (
        ("course_unit", "VARCHAR(100)"),
        ("note_hint", "VARCHAR(255)"),
    ),
    "DOM-SURVEY": (
        ("publish_unit", "VARCHAR(100)"),
        ("note_hint", "VARCHAR(255)"),
    ),
    "DOM-VOTE": (
        ("host_unit", "VARCHAR(100)"),
        ("rule_note", "VARCHAR(255)"),
    ),
    "DOM-DOCLIB": (
        ("publish_unit", "VARCHAR(100)"),
        ("summary_note", "VARCHAR(255)"),
    ),
    "DOM-CARPOOL": (
        ("publisher_name", "VARCHAR(100)"),
        ("route_note", "VARCHAR(255)"),
    ),
    "DOM-TIMEBANK": (
        ("organizer", "VARCHAR(100)"),
        ("service_note", "VARCHAR(255)"),
    ),
    "DOM-CINEMA": (
        ("price_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("hall_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-MEDIA": (
        ("cast_info", "VARCHAR(100)"),
        ("play_url", "VARCHAR(255)"),
    ),
    "DOM-MUSIC": (
        ("artist", "VARCHAR(100)"),
        ("play_url", "VARCHAR(255)"),
    ),
    "DOM-FORUM": (
        ("author", "VARCHAR(100)"),
        ("body_html", "TEXT"),
    ),
    "DOM-BLOG": (
        ("author", "VARCHAR(100)"),
        ("body_html", "TEXT"),
    ),
    "DOM-ACTIVITY": (
        ("organizer", "VARCHAR(100)"),
        ("venue", "VARCHAR(128)"),
    ),
    "DOM-LOST": (
        ("registrant", "VARCHAR(100)"),
        ("feature_note", "VARCHAR(255)"),
    ),
    "DOM-COURSE": (
        ("teacher", "VARCHAR(100)"),
        ("course_code", "VARCHAR(128)"),
    ),
    "DOM-TOUR": (
        ("planner", "VARCHAR(100)"),
        ("highlight_note", "VARCHAR(255)"),
    ),
    "DOM-SHOP": (
        ("price_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("sku", "VARCHAR(64) DEFAULT ''"),
    ),
    "DOM-FOOD": (
        ("price_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("spec_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-PARKING": (
        ("fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("location_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-HOSPITAL": (
        ("fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("title_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-MEETING": (
        ("fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("location_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-SALON": (
        ("price_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("duration_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-HOTEL": (
        ("price_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("room_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-CARRENT": (
        ("price_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ("vehicle_note", "VARCHAR(128) DEFAULT ''"),
    ),
    "DOM-GENERIC": (
        ("subtitle", "VARCHAR(100)"),
        ("detail", "VARCHAR(255)"),
    ),
}

_GENERIC_TRADE: tuple[ArchiveCol, ArchiveCol] = (
    ("price_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("sku", "VARCHAR(64) DEFAULT ''"),
)


def archive_column_spec_for(
    domain: str,
    *,
    archetypes: list[str] | None = None,
) -> tuple[ArchiveCol, ArchiveCol]:
    d = (domain or "").strip()
    if d == "DOM-GENERIC":
        arches = {a for a in (archetypes or []) if a}
        if "ARCH-TRADE" in arches:
            return _GENERIC_TRADE
        return ARCHIVE_COLUMN_SPEC["DOM-GENERIC"]
    return ARCHIVE_COLUMN_SPEC.get(
        d,
        (("subtitle", "VARCHAR(100)"), ("detail", "VARCHAR(255)")),
    )


def archive_column_payload(
    domain: str,
    *,
    archetypes: list[str] | None = None,
    item_table: str | None = None,
) -> dict[str, Any]:
    (a_name, a_ddl), (i_name, i_ddl) = archive_column_spec_for(
        domain, archetypes=archetypes
    )
    return {
        "itemTable": (item_table or "").strip(),
        "authorColumn": a_name,
        "isbnColumn": i_name,
        "authorDdl": a_ddl,
        "isbnDdl": i_ddl,
    }


def apply_archive_semantic_columns(
    sql: str,
    *,
    domain: str,
    item_table: str | None,
    archetypes: list[str] | None = None,
) -> str:
    """将档案主表物理列 author/isbn 改为域语义名，并同步 INSERT/UPDATE。"""
    t = (item_table or "").strip()
    if not valid_ident(t):
        return sql
    (a_name, a_ddl), (i_name, i_ddl) = archive_column_spec_for(
        domain, archetypes=archetypes
    )

    def transform(body: str) -> str:
        body = rewrite_col_def(body, "author", a_name, a_ddl)
        return rewrite_col_def(body, "isbn", i_name, i_ddl)

    rename = {"author": a_name, "isbn": i_name}
    out = map_create_table(sql, t, transform)
    out = rewrite_insert_col_names(out, t, rename)
    return rewrite_update_col_names(out, t, rename)


def repair_archive_logical_col_leaks(
    sql: str,
    *,
    domain: str,
    item_table: str | None,
    archetypes: list[str] | None = None,
) -> str:
    """修复：档案主表仍写逻辑列 author/isbn 的 CREATE/INSERT/UPDATE。"""
    return apply_archive_semantic_columns(
        sql,
        domain=domain,
        item_table=item_table,
        archetypes=archetypes,
    )


def find_archive_logical_col_leaks(
    sql: str,
    *,
    domain: str,
    item_table: str | None,
    archetypes: list[str] | None = None,
) -> list[str]:
    """扫档案主表：物理列已语义化后，DML/DDL 仍残留逻辑名 author/isbn。"""
    t = (item_table or "").strip()
    if not valid_ident(t) or not (sql or "").strip():
        return []
    (a_name, _), (i_name, _) = archive_column_spec_for(
        domain, archetypes=archetypes
    )
    rename = {
        k: v
        for k, v in (("author", a_name), ("isbn", i_name))
        if k.lower() != (v or "").lower()
    }
    if not rename:
        return []

    issues: list[str] = []
    # CREATE 体仍留逻辑列名
    for m in re.finditer(
        rf"(?is)CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?{re.escape(t)}`?\s*\((.*?)\)\s*;",
        sql,
    ):
        body = m.group(1) or ""
        for old in rename:
            if re.search(rf"(?m)^\s*`?{re.escape(old)}`?\s+", body, re.IGNORECASE):
                issues.append(f"{t}.CREATE 仍含逻辑列 {old}（应为 {rename[old]}）")

    # INSERT 列清单
    for m in re.finditer(
        rf"(?i)INSERT\s+(?:IGNORE\s+)?INTO\s+`?{re.escape(t)}`?\s*\(([^)]+)\)",
        sql,
    ):
        cols = {p.strip().lower() for p in m.group(1).split(",") if p.strip()}
        for old, new in rename.items():
            if old.lower() in cols:
                issues.append(f"{t}.INSERT 仍用逻辑列 {old}（应为 {new}）")

    # UPDATE 体
    for m in re.finditer(
        rf"(?is)UPDATE\s+`?{re.escape(t)}`?\b.*?;",
        sql,
    ):
        body = m.group(0)
        for old, new in rename.items():
            if re.search(rf"\b{re.escape(old)}\b", body, re.IGNORECASE):
                issues.append(f"{t}.UPDATE 仍用逻辑列 {old}（应为 {new}）")

    # 去重保序
    seen: set[str] = set()
    out: list[str] = []
    for issue in issues:
        if issue not in seen:
            seen.add(issue)
            out.append(issue)
    return out


def assert_archive_semantic_columns(
    sql: str,
    *,
    domain: str,
    item_table: str | None,
    archetypes: list[str] | None = None,
) -> None:
    """门禁：语义列对齐；残留逻辑列名则硬失败。"""
    issues = find_archive_logical_col_leaks(
        sql,
        domain=domain,
        item_table=item_table,
        archetypes=archetypes,
    )
    if issues:
        raise ValueError(
            "档案语义列未对齐（逻辑 author/isbn 与物理列不一致，落库会 1054）："
            + "；".join(issues[:12])
        )


def ensure_archive_semantic_columns(
    sql: str,
    *,
    domain: str,
    item_table: str | None,
    archetypes: list[str] | None = None,
) -> str:
    """先修后验：改写逻辑列残留，再门禁硬失败。"""
    fixed = repair_archive_logical_col_leaks(
        sql,
        domain=domain,
        item_table=item_table,
        archetypes=archetypes,
    )
    assert_archive_semantic_columns(
        fixed,
        domain=domain,
        item_table=item_table,
        archetypes=archetypes,
    )
    return fixed


def repair_workspace_schema_semantic_columns(workspace: Path) -> bool:
    """落库前修复 workspace/sql/schema.sql 的逻辑列残留；改写了返回 True。"""
    import json

    schema_path = Path(workspace) / "sql" / "schema.sql"
    if not schema_path.is_file():
        return False
    domain = ""
    item_table: str | None = None
    archetypes: list[str] | None = None
    spec_path = Path(workspace) / "spec.json"
    if spec_path.is_file():
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            spec = {}
        if isinstance(spec, dict):
            domain = str(spec.get("domain") or "")
            arches = spec.get("archetypes")
            if isinstance(arches, list):
                archetypes = [str(a) for a in arches if a]
            elif spec.get("archetype"):
                archetypes = [str(spec.get("archetype"))]
            runtime = spec.get("runtime") if isinstance(spec.get("runtime"), dict) else {}
            item_table = runtime.get("archive_item_table")
    if not item_table:
        cols_path = (
            Path(workspace)
            / "backend"
            / "src"
            / "main"
            / "resources"
            / "domain-archive-columns.json"
        )
        if cols_path.is_file():
            try:
                payload = json.loads(cols_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                payload = {}
            if isinstance(payload, dict):
                item_table = payload.get("itemTable") or item_table
                # 无 domain 时用资源文件反推改名
                a_phys = str(payload.get("authorColumn") or "author")
                i_phys = str(payload.get("isbnColumn") or "isbn")
                if not domain and (a_phys != "author" or i_phys != "isbn"):
                    raw = schema_path.read_text(encoding="utf-8", errors="replace")
                    t = (item_table or "").strip()
                    if not valid_ident(t):
                        return False
                    fixed = rewrite_insert_col_names(
                        raw, t, {"author": a_phys, "isbn": i_phys}
                    )
                    fixed = rewrite_update_col_names(
                        fixed, t, {"author": a_phys, "isbn": i_phys}
                    )

                    def transform(body: str) -> str:
                        body = rewrite_col_def(body, "author", a_phys, None)
                        return rewrite_col_def(body, "isbn", i_phys, None)

                    fixed = map_create_table(fixed, t, transform)
                    if fixed != raw:
                        schema_path.write_text(fixed, encoding="utf-8")
                        return True
                    return False
    if not domain or not item_table:
        return False
    raw = schema_path.read_text(encoding="utf-8", errors="replace")
    if not find_archive_logical_col_leaks(
        raw, domain=domain, item_table=item_table, archetypes=archetypes
    ):
        return False
    fixed = repair_archive_logical_col_leaks(
        raw,
        domain=domain,
        item_table=item_table,
        archetypes=archetypes,
    )
    if fixed == raw:
        return False
    schema_path.write_text(fixed, encoding="utf-8")
    return True


def evaluate_workspace_archive_semantic_columns(workspace: Path) -> dict[str, Any]:
    """工作区门禁：可先 repair 再评；ok=无残留。"""
    schema_path = Path(workspace) / "sql" / "schema.sql"
    if not schema_path.is_file():
        return {
            "ok": False,
            "label": "档案语义列",
            "desc": "缺少 sql/schema.sql",
            "issues": ["missing sql/schema.sql"],
            "repaired": False,
        }
    repaired = repair_workspace_schema_semantic_columns(workspace)
    import json

    domain = ""
    item_table = None
    archetypes = None
    spec_path = Path(workspace) / "spec.json"
    if spec_path.is_file():
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            spec = {}
        if isinstance(spec, dict):
            domain = str(spec.get("domain") or "")
            arches = spec.get("archetypes")
            if isinstance(arches, list):
                archetypes = [str(a) for a in arches if a]
            runtime = spec.get("runtime") if isinstance(spec.get("runtime"), dict) else {}
            item_table = runtime.get("archive_item_table")
    sql = schema_path.read_text(encoding="utf-8", errors="replace")
    issues = (
        find_archive_logical_col_leaks(
            sql, domain=domain, item_table=item_table, archetypes=archetypes
        )
        if domain and item_table
        else []
    )
    return {
        "ok": not issues,
        "label": "档案语义列",
        "desc": (
            ("已自动改写逻辑列；" if repaired else "")
            + ("；".join(issues[:8]) if issues else "author/isbn 与物理列一致")
        ),
        "issues": issues,
        "repaired": repaired,
    }
