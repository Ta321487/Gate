"""Bake：SQL 装载与表数量门禁。"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.bake.catalog import (
    normalize_auth_entry_mode,
    normalize_auth_role_widget,
    normalize_auth_template,
    normalize_chrome,
    normalize_layout,
    normalize_typeface,
)
from app.bake.domain_schema import (
    deterministic_llm_patch,
    merge_schema,
    product_name_from_title,
    validate_schema,
    write_schema_artifacts,
)

# 答辩/开题常见硬约束：交付库表不宜过少或灌水过多
TABLE_COUNT_MIN = 6
# 含 L0 平台表 sys_message；论坛等顶格域可达 15
TABLE_COUNT_MAX = 15

# GENERIC 壳：bake/sql/DOM-GENERIC*.sql；具名域：sql_domain_templates（唯一路径，无散文件）
_SQL_DIR = Path(__file__).resolve().parent / "sql"
_FALLBACK_SQL = "DOM-GENERIC.sql"

def count_create_tables(sql: str) -> int:
    return len(re.findall(r"(?i)create\s+table\b", sql))

def assert_table_budget(sql: str, domain: str) -> None:
    n = count_create_tables(sql)
    if not (TABLE_COUNT_MIN <= n <= TABLE_COUNT_MAX):
        raise ValueError(
            f"{domain} schema 表数量={n}，必须在 {TABLE_COUNT_MIN}~{TABLE_COUNT_MAX} 之间"
        )

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def _patch_student_readme(
    dest: Path, *, app_name: str, db_name: str, java_package: str = "com.thesis"
) -> None:
    """ZIP 根目录 README：写入课题名、库名与 Java 包路径。"""
    path = dest / "README.md"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    text = text.replace("${APP_NAME}", app_name or "毕设系统")
    text = text.replace("${DB_NAME}", db_name or "thesis_app")
    text = text.replace("${JAVA_PACKAGE_PATH}", java_package.replace(".", "/"))
    text = text.replace("${JAVA_PACKAGE}", java_package)
    path.write_text(text, encoding="utf-8")

def _merge_tree(src: Path, dest: Path) -> None:
    """将 src 覆盖合并到 dest（文件覆盖，目录递归）。"""
    if not src.exists():
        return
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        target = dest / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)

def _sql_template_path(domain: str, archetype: str | None = None) -> Path:
    """GENERIC 壳仍读 bake/sql/DOM-GENERIC*.sql；具名域见 DOMAIN_SQL_TEMPLATES。"""
    if domain == "DOM-GENERIC":
        from app.bake.archetype_shells import shell_sql_filename

        path = _SQL_DIR / shell_sql_filename(archetype)
        if path.is_file():
            return path
    fallback = _SQL_DIR / _FALLBACK_SQL
    if not fallback.is_file():
        raise FileNotFoundError(f"缺少 SQL 模板: {_FALLBACK_SQL}")
    return fallback

def _load_named_domain_sql(domain: str) -> str:
    """具名域唯一路径：见 sql.compose.compose_named_domain_sql。"""
    from app.bake.sql.compose import compose_named_domain_sql

    return compose_named_domain_sql(domain)

def domain_sql(
    domain: str,
    db_name: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    *,
    ticket_table: str | None = None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
    ticket_flags: dict | None = None,
    staff_posts: list | None = None,
) -> str:
    """按领域加载 SQL；GENERIC 多主路径从已有模板拼装。"""
    if domain == "DOM-GENERIC":
        from app.bake.archetype_shells import path_flags, shell_sql_filename
        from app.bake.sql.compose import compose_generic_sql

        arches = list(archetypes or ([archetype] if archetype else ["ARCH-CRUD"]))
        need_flow, need_trade, need_reserve = path_flags(arches)
        if sum([need_flow, need_trade, need_reserve]) >= 2:
            text = compose_generic_sql(
                need_flow=need_flow,
                need_trade=need_trade,
                need_reserve=need_reserve,
                db_name=db_name,
                table_min=TABLE_COUNT_MIN,
                table_max=TABLE_COUNT_MAX,
            )
        else:
            fname = shell_sql_filename(archetypes=arches)
            path = _SQL_DIR / fname
            if not path.is_file():
                path = _sql_template_path(domain, archetype)
            text = path.read_text(encoding="utf-8")
    else:
        text = _load_named_domain_sql(domain)
    from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
    from app.bake.features.favorites import FAVORITES_CAP
    from app.bake.features.guestbook import GUESTBOOK_CAP
    from app.bake.features.ux_scan import BROWSE_HISTORY_CAP, GALLERY_CAP
    from app.bake.features.archive_log import ARCHIVE_LOG_CAP
    from app.bake.features.order_extras import ORDER_REVIEW_CAP
    from app.bake.features.loyalty import LOYALTY_CAPS
    from app.bake.features.proposal_caps import merge_proposal_capabilities
    from app.bake.archive_columns import apply_archive_semantic_columns
    from app.bake.ticket_columns import apply_ticket_shell_sql
    from app.bake.sql.fragments import (
        ensure_archive_flag_columns,
        ensure_archive_log_sql,
        ensure_browse_history_sql,
        ensure_coupon_lifecycle_sql,
        ensure_favorites_sql,
        ensure_gallery_sql,
        ensure_guestbook_sql,
        ensure_order_review_sql,
        ensure_shared_sql_columns,
        ensure_ticket_extra_sql,
        ensure_ticket_progress_sql,
        resolve_ticket_flags,
    )
    from app.bake.staff_posts import append_staff_seed_sql

    arches_for_sql = list(
        archetypes or ([archetype] if archetype else [])
    )
    # 与 attach_accept 同一条能力合并链（避免 schema/SQL 双轨）
    caps = merge_proposal_capabilities(
        capabilities
        if capabilities is not None
        else (DOMAIN_CAPABILITIES.get(domain) or []),
        proposal_text or "",
        domain=domain,
        archetype=archetype,
        archetypes=arches_for_sql,
    )
    loyalty_on = bool(set(caps) & set(LOYALTY_CAPS))
    # 有子管/岗位任命的域保留 staff 列；预约/订单履约列按域拆分；忠诚度按能力
    text = ensure_shared_sql_columns(
        text,
        domain=domain or "",
        archetypes=arches_for_sql,
        staff=True,
        loyalty=loyalty_on,
    )
    runtime = ((DOMAINS.get(domain) or {}).get("runtime") or {})
    resolved_ticket = ticket_table or runtime.get("ticket_table")
    resolved_item = runtime.get("archive_item_table")
    if domain == "DOM-GENERIC" and (not resolved_ticket or not resolved_item):
        from app.bake.archetype_shells import shell_runtime

        shell_rt = shell_runtime(archetype, archetypes=archetypes) or {}
        if not resolved_ticket:
            resolved_ticket = shell_rt.get("ticket_table")
        if not resolved_item:
            resolved_item = shell_rt.get("archive_item_table") or "biz_item"
    flags = resolve_ticket_flags(
        domain or "",
        archetype=archetype,
        archetypes=archetypes,
        ticket_flags=ticket_flags,
    )
    text = ensure_ticket_extra_sql(
        text,
        domain=domain or "",
        ticket_table=resolved_ticket,
        ticket_flags=flags,
    )
    text = apply_ticket_shell_sql(
        text,
        domain=domain or "",
        ticket_table=resolved_ticket,
        ticket_flags=flags,
    )
    text = ensure_archive_flag_columns(
        text,
        item_table=resolved_item,
        allow_checkin=bool(flags.get("allowCheckin")),
        check_mutex=bool(flags.get("checkMutex")),
    )
    text = apply_archive_semantic_columns(
        text,
        domain=domain or "",
        item_table=resolved_item,
        archetypes=arches_for_sql,
    )
    text = ensure_ticket_progress_sql(text, resolved_ticket)
    text = ensure_guestbook_sql(
        text,
        enabled=GUESTBOOK_CAP in caps,
    )
    text = ensure_favorites_sql(
        text,
        enabled=FAVORITES_CAP in caps,
    )
    text = ensure_browse_history_sql(
        text,
        enabled=BROWSE_HISTORY_CAP in caps,
    )
    text = ensure_archive_log_sql(
        text,
        enabled=ARCHIVE_LOG_CAP in caps,
    )
    text = ensure_gallery_sql(
        text,
        enabled=GALLERY_CAP in caps,
        item_table=resolved_item,
    )
    text = ensure_coupon_lifecycle_sql(
        text,
        enabled="coupon" in caps,
    )
    text = ensure_order_review_sql(
        text,
        enabled=ORDER_REVIEW_CAP in caps,
    )
    text = append_staff_seed_sql(
        text,
        domain,
        archetype,
        archetypes,
        proposal_text=proposal_text or "",
        posts=staff_posts,
    )
    # 演示日历不在 bake 时写死「今天」：交付后隔月答辩仍靠启动时 SeedCalendarAligner 平移
    return (
        text.replace("${DB_NAME}", db_name)
        .replace("${DOMAIN}", domain)
        .replace("${TABLE_COUNT_MIN}", str(TABLE_COUNT_MIN))
        .replace("${TABLE_COUNT_MAX}", str(TABLE_COUNT_MAX))
    )

