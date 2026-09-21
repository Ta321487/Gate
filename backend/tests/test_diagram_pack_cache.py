"""论文图：单请求 pack + 磁盘缓存 + bake 预热。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.bake.schema.diagram_cache import invalidate, read_cache
from app.bake.schema.diagram_pack import pack_classes, warm_default_diagrams

_MINI_SQL = """
CREATE TABLE `sys_user` (
  `id` INT PRIMARY KEY,
  `username` VARCHAR(64)
);
CREATE TABLE `book` (
  `id` INT PRIMARY KEY,
  `title` VARCHAR(128),
  `owner_id` INT,
  FOREIGN KEY (`owner_id`) REFERENCES `sys_user`(`id`)
);
"""

_DOMAIN = {
    "title": "图书借阅",
    "labels": {"appName": "图书借阅"},
    "roles": {"user": {"label": "读者"}, "admin": {"label": "管理员"}},
    "menus": {
        "user": [{"id": "books", "label": "图书浏览"}],
        "admin": [{"id": "books_admin", "label": "图书管理"}],
    },
}


class DiagramPackCacheTests(unittest.TestCase):
    def test_pack_classes_single_response_has_svg_and_cache_hit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sql").mkdir()
            (root / "sql" / "schema.sql").write_text(_MINI_SQL, encoding="utf-8")
            (root / "domain.schema.json").write_text(
                __import__("json").dumps(_DOMAIN, ensure_ascii=False),
                encoding="utf-8",
            )
            m1 = pack_classes(root, display="sample", title_fallback="图书")
            self.assertIsNotNone(m1)
            assert m1 is not None
            self.assertIn("svg", m1)
            self.assertTrue(str(m1["svg"]).startswith("<svg") or "<svg" in str(m1["svg"]))
            self.assertEqual(m1.get("diagram_cache"), "miss")
            self.assertIn("timing", m1)
            for k in ("model_ms", "layout_ms", "svg_ms", "total_ms"):
                self.assertIn(k, m1["timing"])

            hit = read_cache(root, "classes", {"display": "sample"})
            self.assertIsNotNone(hit)

            m2 = pack_classes(root, display="sample", title_fallback="图书")
            assert m2 is not None
            self.assertEqual(m2.get("diagram_cache"), "hit")
            self.assertEqual(m2.get("svg"), m1.get("svg"))

    def test_layout_change_invalidates_class_cache(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sql").mkdir()
            (root / "sql" / "schema.sql").write_text(_MINI_SQL, encoding="utf-8")
            (root / "domain.schema.json").write_text(
                __import__("json").dumps(_DOMAIN, ensure_ascii=False),
                encoding="utf-8",
            )
            pack_classes(root, display="sample")
            n = invalidate(root, "classes")
            self.assertGreaterEqual(n, 1)
            m = pack_classes(root, display="sample")
            assert m is not None
            self.assertEqual(m.get("diagram_cache"), "miss")

    def test_warm_writes_default_caches(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sql").mkdir()
            (root / "sql" / "schema.sql").write_text(_MINI_SQL, encoding="utf-8")
            (root / "domain.schema.json").write_text(
                __import__("json").dumps(_DOMAIN, ensure_ascii=False),
                encoding="utf-8",
            )
            (root / "spec.json").write_text("{}", encoding="utf-8")
            summary = warm_default_diagrams(root, title_fallback="图书")
            self.assertTrue(summary.get("items", {}).get("classes", {}).get("ok"))
            self.assertTrue(summary.get("items", {}).get("er", {}).get("ok"))
            m = pack_classes(root, display="sample")
            assert m is not None
            self.assertEqual(m.get("diagram_cache"), "hit")

    def test_pack_er_cache_hit(self) -> None:
        from app.bake.schema.diagram_pack import pack_er

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sql").mkdir()
            (root / "sql" / "schema.sql").write_text(_MINI_SQL, encoding="utf-8")
            (root / "domain.schema.json").write_text(
                __import__("json").dumps(_DOMAIN, ensure_ascii=False),
                encoding="utf-8",
            )
            m1 = pack_er(root, mode="total")
            self.assertIsNotNone(m1)
            assert m1 is not None
            self.assertIn("svg", m1)
            self.assertEqual(m1.get("diagram_cache"), "miss")
            m2 = pack_er(root, mode="total")
            assert m2 is not None
            self.assertEqual(m2.get("diagram_cache"), "hit")
            self.assertEqual(m2.get("svg"), m1.get("svg"))

    def test_er_user_view_overrides_until_reset_or_schema_change(self) -> None:
        from app.bake.schema.diagram_pack import pack_er
        from app.bake.schema.er_view import clear_user_svg, save_user_svg

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sql").mkdir()
            sql = root / "sql" / "schema.sql"
            sql.write_text(_MINI_SQL, encoding="utf-8")
            (root / "domain.schema.json").write_text(
                __import__("json").dumps(_DOMAIN, ensure_ascii=False),
                encoding="utf-8",
            )
            auto = pack_er(root, mode="total")
            assert auto is not None
            user = '<svg xmlns="http://www.w3.org/2000/svg" id="user-placed"></svg>'
            save_user_svg(root, "total", None, user)
            shown = pack_er(root, mode="total")
            assert shown is not None
            self.assertEqual(shown.get("diagram_cache"), "hit")
            self.assertIn("user-placed", shown.get("svg") or "")
            self.assertEqual(shown.get("er_view"), "user")
            sql.write_text(_MINI_SQL + "\n-- changed\n", encoding="utf-8")
            after = pack_er(root, mode="total")
            assert after is not None
            self.assertNotIn("user-placed", after.get("svg") or "")
            save_user_svg(root, "total", None, user)
            clear_user_svg(root, "total", None)
            reset = pack_er(root, mode="total")
            assert reset is not None
            self.assertNotIn("user-placed", reset.get("svg") or "")


if __name__ == "__main__":
    unittest.main()
