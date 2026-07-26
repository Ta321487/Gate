"""DDL 补列不得在 CREATE 体末尾留下多余逗号。"""

from __future__ import annotations

import re
import unittest

from app.bake.engine_sql import domain_sql
from app.bake.sql.ddl_edit import inject_missing_columns, map_create_table


class DdlTrailingCommaTests(unittest.TestCase):
    def test_inject_at_end_no_trailing_comma(self) -> None:
        body = "\n  id BIGINT PRIMARY KEY,\n  status VARCHAR(32)\n"
        out = inject_missing_columns(
            body,
            [("rating", "INT NULL"), ("rated_at", "DATETIME NULL")],
        )
        self.assertIn("rating INT NULL,", out)
        self.assertIn("rated_at DATETIME NULL", out)
        self.assertNotRegex(out.rstrip(), r",\s*$")

    def test_inject_before_created_at_keeps_commas(self) -> None:
        body = "\n  id BIGINT PRIMARY KEY,\n  created_at DATETIME\n"
        out = inject_missing_columns(body, [("rating", "INT NULL")])
        self.assertIn("rating INT NULL,", out)
        self.assertIn("created_at DATETIME", out)

    def test_lost_claim_create_valid(self) -> None:
        sql = domain_sql(
            "DOM-LOST",
            "thesis_test",
            title="校园失物招领管理系统",
            proposal_text="",
        )
        self.assertNotRegex(sql, r",\s*\)")
        m = re.search(
            r"CREATE TABLE IF NOT EXISTS claim\s*\((.*?)\);",
            sql,
            re.S | re.I,
        )
        self.assertIsNotNone(m)
        assert m is not None
        self.assertIn("rated_at", m.group(1))
        self.assertNotRegex(m.group(1).rstrip(), r",\s*$")

    def test_rating_domains_no_trailing_comma(self) -> None:
        for dom in (
            "DOM-LOST",
            "DOM-PARCEL",
            "DOM-DORM",
            "DOM-IT",
            "DOM-PROPERTY",
            "DOM-ACTIVITY",
        ):
            with self.subTest(dom=dom):
                sql = domain_sql(dom, "thesis_test", title="测试课题", proposal_text="")
                self.assertNotRegex(sql, r",\s*\)", msg=dom)

    def test_map_create_strips_after_prune(self) -> None:
        sql = """
CREATE TABLE IF NOT EXISTS claim (
  id BIGINT PRIMARY KEY,
  rated_at DATETIME NULL,
);
"""
        out = map_create_table(sql, "claim", lambda b: b)
        self.assertNotRegex(out, r",\s*\)")


if __name__ == "__main__":
    unittest.main()
