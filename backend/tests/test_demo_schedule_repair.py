"""演示日程/档案落库修复。"""

import unittest

from app.bake.sql.demo_schedule_repair import (
    archive_item_tables_in_sql,
    replay_archive_inserts_if_empty,
)


def test_archive_item_tables_in_sql_finds_start_at():
    sql = """
    CREATE TABLE IF NOT EXISTS activity (
      id BIGINT PRIMARY KEY,
      start_at DATETIME NULL
    );
    CREATE TABLE IF NOT EXISTS category (id BIGINT PRIMARY KEY);
    """
    assert archive_item_tables_in_sql(sql) == ["activity"]


class ReplayArchiveInsertsTests(unittest.TestCase):
    def test_replays_when_table_empty(self):
        executed: list[str] = []

        class Cur:
            def execute(self, sql, args=None):
                executed.append(sql.strip())

            def fetchone(self):
                return (0,)

        replay_archive_inserts_if_empty(
            Cur(),
            "demo_db",
            "INSERT IGNORE INTO leave_type (id, title) VALUES (1, '事假');",
            item_table="leave_type",
            split_sql=lambda s: [x.strip() for x in s.split(";") if x.strip()],
        )
        self.assertEqual(len(executed), 2)
        self.assertTrue(executed[0].startswith("SELECT COUNT"))
        self.assertIn("INSERT IGNORE INTO leave_type", executed[1])

    def test_skips_when_table_has_rows(self):
        executed: list[str] = []

        class Cur:
            def execute(self, sql, args=None):
                executed.append(sql)

            def fetchone(self):
                return (3,)

        replay_archive_inserts_if_empty(
            Cur(),
            "demo_db",
            "INSERT IGNORE INTO leave_type (id, title) VALUES (1, '事假');",
            item_table="leave_type",
            split_sql=lambda s: [s],
        )
        self.assertEqual(len(executed), 1)
