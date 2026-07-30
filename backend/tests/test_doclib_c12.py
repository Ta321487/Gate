"""泳道 E · C-12：文库下载台账 doclib + DOM-DOCLIB。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES, resolve_accept
from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept, build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.doclib import DOCLIB_CAP
from app.bake.menu_routes import shell_kind
from app.bake.schema.templates import SCHEMA_BUILDERS

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "samples" / "能力预设开题"
BASELINE = ROOT / "skeletons" / "baseline"


class DoclibC12Tests(unittest.TestCase):
    def test_capability_and_domain(self) -> None:
        self.assertIn("doclib", CAPABILITIES)
        self.assertEqual(CAPABILITIES["doclib"]["status"], "implemented")
        self.assertIn("DOM-DOCLIB", DOMAINS)
        self.assertIn(DOCLIB_CAP, DOMAIN_CAPABILITIES["DOM-DOCLIB"])
        self.assertNotIn("ticket_flow", DOMAIN_CAPABILITIES["DOM-DOCLIB"])
        self.assertIn("DOM-DOCLIB", SCHEMA_BUILDERS)

    def test_match(self) -> None:
        got = match_text(
            "基于 Spring Boot 的高校制度文件文库下载台账管理系统的设计与实现。"
            "主要功能：资料条目、附件权限、下载记录台账。"
        )
        self.assertEqual(got.domain, "DOM-DOCLIB", f"hits={got.hits[:12]}")

    def test_neighbors(self) -> None:
        cases = [
            ("制度文件文库资料下载台账", "DOM-DOCLIB", "DOM-LIBRARY"),
            ("图书借阅归还审核管理", "DOM-LIBRARY", "DOM-DOCLIB"),
            ("校园资讯院刊发布收藏", "DOM-BLOG", "DOM-DOCLIB"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")
                self.assertNotEqual(got.domain, avoid)

    def test_schema_and_shell(self) -> None:
        schema = build_domain_schema("高校制度文件文库下载台账管理系统", "DOM-DOCLIB")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        self.assertEqual(shell_kind(DOMAIN_CAPABILITIES["DOM-DOCLIB"]), "archive_only")
        spec = attach_accept(
            {
                "domain": "DOM-DOCLIB",
                "title": "高校制度文件文库下载台账管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-DOCLIB"]),
                "archetype": "ARCH-CRUD",
            },
            "资料条目、附件权限、下载记录台账。",
        )
        sch = spec.get("schema") or {}
        user_keys = {m.get("key") for m in (sch.get("menus") or {}).get("user") or []}
        admin_keys = {m.get("key") for m in (sch.get("menus") or {}).get("admin") or []}
        self.assertIn("doc_browse", user_keys)
        self.assertIn("doc_mine", user_keys)
        self.assertIn("doc_files", admin_keys)
        self.assertIn("doc_logs", admin_keys)

    def test_sql_yml_accept(self) -> None:
        sql = domain_sql(
            "DOM-DOCLIB",
            "t_doc",
            title="高校制度文件文库下载台账管理系统",
            proposal_text="知识库资料下载台账",
        )
        for t in ("doc_item", "download_log", "file_url", "access_level"):
            self.assertIn(t, sql)
        spec = attach_accept(
            {
                "domain": "DOM-DOCLIB",
                "title": "高校制度文件文库下载台账管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-DOCLIB"]),
                "archetype": "ARCH-CRUD",
            },
            "文库下载",
        )
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-DOCLIB", spec)
        self.assertIn("doclib-enabled: true", yml)
        self.assertIn("enable-ticket: false", yml)
        d = resolve_accept(
            list(DOMAIN_CAPABILITIES["DOM-DOCLIB"]),
            "资料下载；附件权限；下载台账。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-CRUD"],
            domain="DOM-DOCLIB",
            primary_archetype="ARCH-CRUD",
        )
        self.assertEqual(d["accept"], "full", d)

    def test_runtime_files(self) -> None:
        self.assertTrue((BASELINE / "backend/src/main/java/com/thesis/service/DoclibStore.java").is_file())
        self.assertTrue((BASELINE / "backend/src/main/java/com/thesis/controller/DoclibController.java").is_file())
        self.assertTrue((BASELINE / "frontend/src/views/DocBrowse.vue").is_file())
        self.assertTrue((BASELINE / "frontend/src/views/admin/DocLogsAdmin.vue").is_file())

    def test_sample(self) -> None:
        path = SAMPLES / "C-12-DOM-DOCLIB-高校制度文件文库下载台账管理系统.txt"
        self.assertTrue(path.is_file(), path)


if __name__ == "__main__":
    unittest.main()
