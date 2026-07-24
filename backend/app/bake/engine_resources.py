"""engine_resources.py"""

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
from app.bake.engine_sql import (  # noqa: F401
    TABLE_COUNT_MAX,
    TABLE_COUNT_MIN,
    _SQL_DIR,
    _FALLBACK_SQL,
    _load_named_domain_sql,
    _merge_tree,
    _patch_student_readme,
    _sql_template_path,
    _write,
    assert_table_budget,
    count_create_tables,
    domain_sql,
)

def _write_profile_fields_resource(dest: Path, schema: dict[str, Any]) -> None:
    """学生端后端读取，注册/资料必填校验。"""
    fields = schema.get("profileFields") or []
    path = dest / "backend" / "src" / "main" / "resources" / "domain-profile-fields.json"
    _write(path, json.dumps(fields, ensure_ascii=False, indent=2))

def _write_loyalty_resource(dest: Path, schema: dict[str, Any]) -> None:
    """学生端 LoyaltyStore 读取会员档等配置。"""
    loyalty = schema.get("loyalty") or {}
    path = dest / "backend" / "src" / "main" / "resources" / "domain-loyalty.json"
    _write(path, json.dumps(loyalty, ensure_ascii=False, indent=2))

def _write_ticket_columns_resource(
    dest: Path,
    *,
    domain: str,
    ticket_table: str | None,
    ticket_flags: dict | None,
) -> None:
    from app.bake.ticket_columns import ticket_column_payload

    path = dest / "backend" / "src" / "main" / "resources" / "domain-ticket-columns.json"
    _write(
        path,
        json.dumps(
            ticket_column_payload(
                domain, ticket_table=ticket_table, ticket_flags=ticket_flags
            ),
            ensure_ascii=False,
            indent=2,
        ),
    )

def _write_archive_columns_resource(
    dest: Path,
    *,
    domain: str,
    archetypes: list[str] | None,
    item_table: str | None,
) -> None:
    """学生端 ArchiveStore 读取：逻辑键 author/isbn → 物理列名。"""
    from app.bake.archive_columns import archive_column_payload

    path = dest / "backend" / "src" / "main" / "resources" / "domain-archive-columns.json"
    _write(
        path,
        json.dumps(
            archive_column_payload(
                domain, archetypes=archetypes, item_table=item_table
            ),
            ensure_ascii=False,
            indent=2,
        ),
    )

def _write_ticket_copy_resource(dest: Path, schema: dict[str, Any]) -> None:
    """学生端 TicketStore 进度/提示文案：来自 schema.entities.ticket（及 archive 名）。"""
    from app.bake.ticket_copy_text import sibling_reject_tip, stock_unavailable_label

    ticket = ((schema.get("entities") or {}).get("ticket") or {}) if isinstance(schema, dict) else {}
    archive = ((schema.get("entities") or {}).get("archive") or {}) if isinstance(schema, dict) else {}
    apply_deadline_label = "报名截止"
    stock_label = "库存"
    for f in archive.get("fields") or []:
        if not isinstance(f, dict):
            continue
        key = f.get("key")
        lab = str(f.get("label") or "").strip()
        if key == "applyDeadlineAt" and lab:
            apply_deadline_label = lab
        if key == "stock" and lab:
            stock_label = lab
    verbs = ticket.get("verbs") if isinstance(ticket.get("verbs"), dict) else {}
    apply_verb = str(verbs.get("apply") or "")
    archive_label = str(archive.get("label") or "")
    stock_gone = archive.get("stockUnavailableLabel") or stock_unavailable_label(stock_label)
    payload = {
        "states": ticket.get("states") if isinstance(ticket.get("states"), dict) else {},
        "verbs": verbs,
        "checkinLabel": ticket.get("checkinLabel") or "签到",
        "finePaidLabel": ticket.get("finePaidLabel") or "费用已结清",
        "archiveLabel": archive_label,
        "applyDeadlineLabel": apply_deadline_label,
        "stockLabel": stock_label,
        "stockUnavailableLabel": stock_gone,
        "siblingRejectTip": sibling_reject_tip(archive_label, apply_verb),
    }
    path = dest / "backend" / "src" / "main" / "resources" / "domain-ticket-copy.json"
    _write(path, json.dumps(payload, ensure_ascii=False, indent=2))

def _write_factory_delivered(
    dest: Path,
    title: str,
    theme: str,
    auth_tpl: str,
    schema: dict[str, Any],
    accept: str | None = None,
    auth_hero: str = "",
    portal_banners: list | None = None,
    domain: str = "DOM-GENERIC",
    auth_entry_mode: str = "role_pick",
    auth_role_widget: str = "radio",
    chrome: str = "soft",
    layout: str = "topbar",
    typeface: str = "clean",
    seed: str = "",
) -> None:
    if not auth_hero:
        from app.bake.auth_hero import auth_hero_public_path

        auth_hero = auth_hero_public_path(dest)
    if portal_banners is None:
        from app.bake.portal_banners import portal_banners_from_workspace

        portal_banners = portal_banners_from_workspace(dest, schema)
    from app.bake.catalog import DOMAINS
    from app.bake.guest_cta import (
        GUEST_TEASER_LIMIT,
        pick_guest_login_cta,
        portal_guest_browse_enabled,
    )

    from app.bake.domain_skin import student_skin_payload

    domain_label = (DOMAINS.get(domain) or {}).get("label") or "通用"
    dom_meta = DOMAINS.get(domain) or {}
    guest_on = portal_guest_browse_enabled(domain, dom_meta)
    guest_cta = pick_guest_login_cta(domain, seed or dest.name or title)
    # 便于页面用 schemaLabels 读取
    labels = dict((schema.get("labels") or {}))
    if guest_on and guest_cta:
        labels["guestLoginCta"] = guest_cta
        schema = {**schema, "labels": labels}
    skin = student_skin_payload(domain, domain_label)
    payload = {
        "title": title,
        "theme": theme,
        "chrome": normalize_chrome(chrome),
        "layout": normalize_layout(layout),
        "typeface": normalize_typeface(typeface),
        "flavor": skin["flavor"],
        "domainLabel": skin["domainLabel"],
        "traits": skin["traits"],
        "authTemplate": auth_tpl,
        "authEntryMode": normalize_auth_entry_mode(auth_entry_mode),
        "authRoleWidget": normalize_auth_role_widget(auth_role_widget),
        "authHero": auth_hero or "",
        "portalBanners": portal_banners or [],
        "portalGuestBrowse": guest_on,
        "guestTeaserLimit": GUEST_TEASER_LIMIT,
        "guestLoginCta": guest_cta if guest_on else "",
        "accept": accept or schema.get("accept") or "reject",
        "schema": schema,
    }
    delivered = dest / "frontend" / "src" / "appDelivered.js"
    # 兼容旧文件名（若存在则删掉，避免双份）
    legacy = dest / "frontend" / "src" / "factoryDelivered.js"
    if legacy.exists():
        legacy.unlink()
    delivered.write_text(
        "/**\n"
        " * 课题交付配置（文案 / 菜单 / 能力）。由生成写入，一般无需手改。\n"
        " */\n"
        f"export const APP_DELIVERED = {json.dumps(payload, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
    )
    _write_profile_fields_resource(dest, schema)
    _write_loyalty_resource(dest, schema)
    _write_ticket_copy_resource(dest, schema)
    arches = None
    item_table = ((dom_meta.get("runtime") or {}).get("archive_item_table"))
    spec_path = dest / "spec.json"
    if spec_path.is_file():
        try:
            spec_obj = json.loads(spec_path.read_text(encoding="utf-8"))
            arches = spec_obj.get("archetypes")
            if not arches and spec_obj.get("archetype"):
                arches = [spec_obj.get("archetype")]
            rt = spec_obj.get("runtime") or {}
            if rt.get("archive_item_table"):
                item_table = rt.get("archive_item_table")
        except Exception:
            pass
    if not item_table and domain == "DOM-GENERIC":
        from app.bake.archetype_shells import shell_runtime

        item_table = (shell_runtime(archetypes=arches) or {}).get(
            "archive_item_table"
        ) or "biz_item"
    _write_archive_columns_resource(
        dest,
        domain=domain,
        archetypes=arches if isinstance(arches, list) else None,
        item_table=item_table,
    )
    ticket_table = ((dom_meta.get("runtime") or {}).get("ticket_table"))
    ticket_flags = ((schema.get("entities") or {}).get("ticket")) if isinstance(schema, dict) else None
    if spec_path.is_file():
        try:
            spec_obj = json.loads(spec_path.read_text(encoding="utf-8"))
            rt = spec_obj.get("runtime") or {}
            if rt.get("ticket_table"):
                ticket_table = rt.get("ticket_table")
            ent = ((spec_obj.get("schema") or {}).get("entities") or {}).get("ticket")
            if isinstance(ent, dict):
                ticket_flags = ent
        except Exception:
            pass
    if ticket_table:
        _write_ticket_columns_resource(
            dest,
            domain=domain,
            ticket_table=ticket_table,
            ticket_flags=ticket_flags if isinstance(ticket_flags, dict) else None,
        )

