"""domain_registry 薄索引冒烟。"""

from __future__ import annotations

import unittest

from app.bake.domain_registry import (
    capabilities,
    domain_entry,
    has_sql_template,
    listed_domains,
    schema_builder,
)
from app.bake.schema.templates import SCHEMA_BUILDERS


class DomainRegistryTests(unittest.TestCase):
    def test_listed_includes_library(self) -> None:
        domains = listed_domains()
        self.assertIn("DOM-LIBRARY", domains)
        self.assertIn("DOM-GENERIC", domains)

    def test_sql_and_schema_index(self) -> None:
        self.assertTrue(has_sql_template("DOM-LIBRARY"))
        self.assertTrue(has_sql_template("DOM-GENERIC"))
        self.assertIs(schema_builder("DOM-LIBRARY"), SCHEMA_BUILDERS["DOM-LIBRARY"])
        self.assertIn("archive", capabilities("DOM-LIBRARY"))
        entry = domain_entry("DOM-LIBRARY")
        assert entry is not None
        self.assertTrue(entry["has_sql_template"])
        self.assertTrue(entry["has_schema_builder"])

    def test_domain_groups_cover_catalog(self) -> None:
        from app.bake.domains import DOMAIN_GROUPS, DOMAINS

        grouped = [d for _g, _l, members in DOMAIN_GROUPS for d in members]
        self.assertEqual(sorted(grouped), sorted(DOMAINS))
        self.assertEqual(len(grouped), len(set(grouped)))

    def test_display_group_does_not_change_borrow_family(self) -> None:
        """级联把客户跟进等挪出「借用/占用」后，出包厚度仍算借用族。"""
        from app.bake.domains import BORROW_FAMILY_DOMAINS, DOMAIN_GROUPS
        from app.bake.engine_sql import table_budget_floor

        groups = {gid: members for gid, _label, members in DOMAIN_GROUPS}
        self.assertIn("DOM-CRM", groups["follow"])
        self.assertNotIn("DOM-CRM", groups["borrow"])
        self.assertIn("DOM-EVENT", groups["follow"])
        self.assertIn("DOM-LIBRARY", groups["borrow"])
        self.assertIn("DOM-CRM", BORROW_FAMILY_DOMAINS)
        self.assertEqual(table_budget_floor("DOM-CRM"), 10)
        self.assertEqual(table_budget_floor("DOM-DORM"), 6)


if __name__ == "__main__":
    unittest.main()
