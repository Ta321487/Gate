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


if __name__ == "__main__":
    unittest.main()
