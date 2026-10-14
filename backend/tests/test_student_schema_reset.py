"""重 bake 洗库：reset=True 必须先 drop，预览启停不得默认洗库。"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class StudentSchemaResetTests(unittest.TestCase):
    def test_reset_true_drops_before_apply(self) -> None:
        from app.services import student_db as sdb

        ws = Path("/tmp/ws-fake")
        calls: list[str] = []

        def _drop(name: str) -> None:
            calls.append(f"drop:{name}")

        fake_conn = MagicMock()
        fake_cur = MagicMock()
        fake_conn.cursor.return_value.__enter__.return_value = fake_cur
        fake_conn.cursor.return_value.__exit__.return_value = False

        with (
            patch.object(sdb, "drop_student_database", side_effect=_drop),
            patch.object(sdb, "_read_sql_text", return_value="CREATE DATABASE IF NOT EXISTS `x`;\nUSE `x`;"),
            patch.object(sdb, "_split_sql", return_value=["CREATE DATABASE IF NOT EXISTS `x`", "USE `x`"]),
            patch.object(sdb, "_post_schema_demo_repair"),
            patch.object(sdb, "get_settings") as gs,
            patch.object(sdb.pymysql, "connect", return_value=fake_conn),
            patch.object(Path, "exists", return_value=True),
        ):
            gs.return_value = MagicMock(
                gf_student_mysql_host="127.0.0.1",
                gf_student_mysql_port=3306,
                gf_student_mysql_user="root",
                gf_student_mysql_password="x",
            )
            sdb.ensure_student_schema(ws, "fitness_gear_shop", reset=True)

        self.assertEqual(calls, ["drop:fitness_gear_shop"])
        self.assertTrue(fake_cur.execute.called)

    def test_default_ensure_does_not_drop(self) -> None:
        from app.services import student_db as sdb

        with patch.object(sdb, "drop_student_database") as drop:
            with (
                patch.object(sdb, "_read_sql_text", return_value="USE `x`;"),
                patch.object(sdb, "_split_sql", return_value=["USE `x`"]),
                patch.object(sdb, "_post_schema_demo_repair"),
                patch.object(sdb, "get_settings") as gs,
                patch.object(sdb.pymysql, "connect") as connect,
                patch.object(Path, "exists", return_value=True),
            ):
                gs.return_value = MagicMock(
                    gf_student_mysql_host="127.0.0.1",
                    gf_student_mysql_port=3306,
                    gf_student_mysql_user="root",
                    gf_student_mysql_password="x",
                )
                fake_conn = MagicMock()
                connect.return_value = fake_conn
                fake_cur = MagicMock()
                fake_conn.cursor.return_value.__enter__.return_value = fake_cur
                fake_conn.cursor.return_value.__exit__.return_value = False
                sdb.ensure_student_schema(Path("/tmp/ws"), "fitness_gear_shop")
        drop.assert_not_called()

    def test_reset_student_schema_wrapper_passes_reset(self) -> None:
        from app.services import student_db as sdb

        with patch.object(sdb, "ensure_student_schema") as ens:
            sdb.reset_student_schema(Path("/tmp/ws"), "fitness_gear_shop")
        ens.assert_called_once_with(Path("/tmp/ws"), "fitness_gear_shop", reset=True)

    def test_bake_job_calls_reset_not_plain_ensure(self) -> None:
        """jobs 重 bake 路径必须走 reset_student_schema。"""
        from pathlib import Path as P

        src = (P(__file__).resolve().parents[1] / "app" / "services" / "jobs.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("reset_student_schema", src)
        # 避免回归成无 reset 的 ensure
        self.assertNotRegex(
            src,
            r"ensure_student_schema,\s*\n\s*workspace,\s*\n\s*project\.db_name,\s*\n\s*\)",
        )


if __name__ == "__main__":
    unittest.main()
