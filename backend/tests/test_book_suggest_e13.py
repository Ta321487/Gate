"""能力扩岛 E-13：图书荐购 book_suggest（开题扫词才挂，无域默认）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.book_suggest import (
    BOOK_SUGGEST_CAP,
    merge_book_suggest_capabilities,
    scan_book_suggest,
)
from tests.helpers.normalize import normalize_sql

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class BookSuggestE13Tests(unittest.TestCase):
    def test_capability_registered_no_domain_default(self) -> None:
        self.assertEqual(CAPABILITIES[BOOK_SUGGEST_CAP]["status"], "implemented")
        self.assertNotIn(BOOK_SUGGEST_CAP, DOMAIN_CAPABILITIES.get("DOM-LIBRARY") or [])
        self.assertNotIn(BOOK_SUGGEST_CAP, DOMAIN_CAPABILITIES.get("DOM-PROCURE") or [])

    def test_scan_terms(self) -> None:
        self.assertTrue(scan_book_suggest("支持图书荐购与读者荐购。"))
        self.assertTrue(scan_book_suggest("推荐购书功能。"))
        self.assertFalse(scan_book_suggest("图书借还催还统计。"))

    def test_merge_only_library_when_scanned(self) -> None:
        base = list(DOMAIN_CAPABILITIES["DOM-LIBRARY"])
        no = merge_book_suggest_capabilities(base, "图书借还催还。", domain="DOM-LIBRARY")
        self.assertNotIn(BOOK_SUGGEST_CAP, no)
        yes = merge_book_suggest_capabilities(
            base, "图书借还；支持读者荐购。", domain="DOM-LIBRARY"
        )
        self.assertIn(BOOK_SUGGEST_CAP, yes)
        # PROCURE 即使写荐购也不挂本 cap（期刊遴选另壳）
        procure = merge_book_suggest_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-PROCURE"]),
            "期刊荐购与遴选。",
            domain="DOM-PROCURE",
        )
        self.assertNotIn(BOOK_SUGGEST_CAP, procure)

    def test_attach_accept_sql_yml_menus(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "archetype": "ARCH-FLOW",
            },
            "图书借还催还管理。",
        )
        self.assertNotIn(BOOK_SUGGEST_CAP, plain.get("capabilities") or [])
        menus0 = (plain.get("schema") or {}).get("menus", {})
        self.assertFalse(
            any(m.get("key") == "book_suggest" for m in (menus0.get("user") or []))
        )

        rich = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "archetype": "ARCH-FLOW",
            },
            "图书借还；支持图书荐购与读者荐购。",
        )
        caps = rich.get("capabilities") or []
        self.assertIn(BOOK_SUGGEST_CAP, caps)
        menus = (rich.get("schema") or {}).get("menus", {})
        self.assertTrue(
            any(m.get("key") == "book_suggest" for m in (menus.get("user") or []))
        )
        self.assertTrue(
            any(m.get("key") == "book_suggest" for m in (menus.get("admin") or []))
        )
        lead = ((rich.get("schema") or {}).get("labels") or {}).get(
            "bookSuggestPageLead"
        ) or ""
        self.assertNotIn("演示", str(lead))
        self.assertIn("book_suggest", (rich.get("gate") or {}).get("flow_api") or {})

        yml = _patch_thesis_yml("thesis:\n  domain: DOM-LIBRARY\n", "DOM-LIBRARY", rich)
        self.assertIn("book-suggest-enabled: true", yml)

        sql = domain_sql(
            "DOM-LIBRARY",
            "thesis_lib",
            capabilities=caps,
            proposal_text="图书借还；支持图书荐购。",
        )
        self.assertIn("book_suggest", normalize_sql(sql))

    def test_unmounted_no_table(self) -> None:
        plain = attach_accept(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "archetype": "ARCH-FLOW",
            },
            "图书借还催还。",
        )
        sql = domain_sql(
            "DOM-LIBRARY",
            "thesis_lib",
            capabilities=plain.get("capabilities") or [],
            proposal_text="图书借还催还。",
        )
        self.assertNotIn("book_suggest", normalize_sql(sql))

    def test_journal_procure_still_matches(self) -> None:
        got = match_text(
            "基于 Spring Boot 的外文学术期刊遴选服务平台。"
            "主要功能：期刊品目、提交遴选荐购、管理员审批。"
        )
        self.assertEqual(got.domain, "DOM-PROCURE", f"hits={got.hits[:12]}")

    def test_baseline_files_and_routes(self) -> None:
        store = (
            BASELINE
            / "backend/src/main/java/com/thesis/capability/BookSuggestStore.java"
        )
        ctrl = (
            BASELINE
            / "backend/src/main/java/com/thesis/controller/BookSuggestController.java"
        )
        user = BASELINE / "frontend/src/views/user/BookSuggest.vue"
        admin = BASELINE / "frontend/src/views/admin/BookSuggestAdmin.vue"
        self.assertTrue(store.is_file())
        self.assertTrue(ctrl.is_file())
        self.assertTrue(user.is_file())
        self.assertTrue(admin.is_file())
        stext = store.read_text(encoding="utf-8")
        self.assertIn("submit", stext)
        self.assertIn("resolve", stext)
        self.assertIn("请填写书名", stext)
        self.assertIn("/api/book-suggest", ctrl.read_text(encoding="utf-8"))
        router = (BASELINE / "frontend/src/router/index.js").read_text(encoding="utf-8")
        self.assertIn("withBookSuggestRoutes", router)
        self.assertIn("BookSuggest.vue", router)
        self.assertIn("BookSuggestAdmin.vue", router)


if __name__ == "__main__":
    unittest.main()
