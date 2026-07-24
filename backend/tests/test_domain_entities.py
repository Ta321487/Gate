"""domain_entities 与 domains.runtime / schema archive_key·ticket_key 对齐。"""

from __future__ import annotations

from app.bake.domain_entities import DOMAIN_ENTITIES
from app.bake.domains import DOMAINS
from app.bake.schema.followup_presets import FOLLOWUP_PRESETS
from app.bake.schema.templates import SCHEMA_BUILDERS


def test_entities_cover_catalog_domains():
    for dom in DOMAINS:
        assert dom in DOMAIN_ENTITIES, f"missing entity spec: {dom}"


def test_runtime_tables_bound_from_entities():
    for dom, ent in DOMAIN_ENTITIES.items():
        if dom not in DOMAINS:
            continue
        rt = (DOMAINS[dom].get("runtime") or {})
        if ent.archive_table:
            assert rt.get("archive_item_table") == ent.archive_table, dom
        if ent.ticket_table:
            assert rt.get("ticket_table") == ent.ticket_table, dom
        if ent.ticket_mode:
            assert rt.get("ticket_mode") == ent.ticket_mode, dom


def test_followup_presets_match_schema_keys():
    for dom, preset in FOLLOWUP_PRESETS.items():
        assert dom in SCHEMA_BUILDERS
        ent = DOMAIN_ENTITIES[dom]
        assert preset["archive_key"] == ent.archive_table, dom
        assert preset["ticket_key"] == ent.ticket_table, dom


def test_followup_builders_smoke():
    for dom in FOLLOWUP_PRESETS:
        schema = SCHEMA_BUILDERS[dom]("测试系统")
        assert schema.get("domain") == dom or schema.get("entities")
        arch = (schema.get("entities") or {}).get("archive") or {}
        assert arch.get("key") == FOLLOWUP_PRESETS[dom]["archive_key"]
