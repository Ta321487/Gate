"""薄领域注册表：索引 domain → 能力 / schema builder / SQL 模板键。

不复制 DOMAINS / SCHEMA_BUILDERS 业务数据；只提供统一查询入口。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.schema.templates import SCHEMA_BUILDERS
from app.bake.sql.domain_templates import DOMAIN_SQL_TEMPLATES


def listed_domains() -> list[str]:
    """目录中的具名域（含 GENERIC）。"""
    return sorted(DOMAINS.keys())


def has_sql_template(domain: str) -> bool:
    if domain == "DOM-GENERIC":
        return True
    return domain in DOMAIN_SQL_TEMPLATES


def schema_builder(domain: str) -> Callable[[str], dict[str, Any]] | None:
    return SCHEMA_BUILDERS.get(domain)


def capabilities(domain: str) -> list[str]:
    return list(DOMAIN_CAPABILITIES.get(domain) or DOMAIN_CAPABILITIES.get("DOM-GENERIC") or [])


def domain_entry(domain: str) -> dict[str, Any] | None:
    """单域摘要；未知域返回 None。"""
    from app.bake.domain_entities import entity_for

    if domain not in DOMAINS and domain != "DOM-GENERIC":
        # DOMAINS 应含 GENERIC；兜底仍查能力表
        if domain not in DOMAIN_CAPABILITIES and domain not in DOMAIN_SQL_TEMPLATES:
            return None
    ent = entity_for(domain)
    return {
        "domain": domain,
        "capabilities": capabilities(domain),
        "has_schema_builder": domain in SCHEMA_BUILDERS,
        "has_sql_template": has_sql_template(domain),
        "in_catalog": domain in DOMAINS,
        "archive_table": ent.archive_table if ent else None,
        "ticket_table": ent.ticket_table if ent else None,
        "item_fk": ent.item_fk if ent else None,
    }
