"""门户 UX 扫词：仅材料命中才挂；无词保持原样。"""

from __future__ import annotations

import re
import unittest

from app.bake.domain_schema import attach_accept
from app.bake.engine import count_create_tables, domain_sql
from app.bake.ux_scan import (
    BROWSE_HISTORY_CAP,
    GALLERY_CAP,
    SEARCH_ASSIST_CAP,
    merge_ux_capabilities,
    scan_browse_history,
    scan_gallery,
    scan_search_assist,
)
from tests._normalize import normalize_sql


class UxScanTests(unittest.TestCase):
    def test_scan_keywords(self) -> None:
        self.assertTrue(scan_search_assist("支持搜索联想与热搜榜"))
        self.assertTrue(scan_browse_history("记录用户浏览历史"))
        self.assertTrue(scan_gallery("商品详情多图轮播"))
        self.assertFalse(scan_search_assist("仅分类检索"))
        self.assertFalse(scan_browse_history("仅收藏夹"))
        self.assertFalse(scan_gallery("单封面展示"))

    def test_no_keyword_keeps_caps(self) -> None:
        caps = merge_ux_capabilities(
            ["archive", "order_lines", "content"],
            "商城购物车与订单管理",
        )
        self.assertNotIn(SEARCH_ASSIST_CAP, caps)
        self.assertNotIn(BROWSE_HISTORY_CAP, caps)
        self.assertNotIn(GALLERY_CAP, caps)

    def test_keywords_add_caps(self) -> None:
        caps = merge_ux_capabilities(
            ["archive", "order_lines"],
            "支持搜索联想、热搜、浏览历史与商品多图",
        )
        self.assertIn(SEARCH_ASSIST_CAP, caps)
        self.assertIn(BROWSE_HISTORY_CAP, caps)
        self.assertIn(GALLERY_CAP, caps)

    def test_requires_archive(self) -> None:
        caps = merge_ux_capabilities(
            ["ticket_flow", "content"],
            "搜索联想与浏览历史",
        )
        self.assertNotIn(SEARCH_ASSIST_CAP, caps)

    def test_shop_without_keyword_no_browse_table(self) -> None:
        sql = normalize_sql(domain_sql("DOM-SHOP", "thesis_test"))
        self.assertNotIn("user_browse_history", sql)
        self.assertNotIn("gallery_json", sql)

    def test_attach_accept_with_proposal(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-SHOP",
                "capabilities": ["archive", "order_lines", "quota", "content", "org_users"],
                "schema": {"menus": {"user": [{"key": "archive", "label": "商品"}]}},
            },
            "鲜花商城支持搜索联想、热搜词、浏览足迹与详情多图轮播",
        )
        caps = out.get("capabilities") or []
        self.assertIn(SEARCH_ASSIST_CAP, caps)
        self.assertIn(BROWSE_HISTORY_CAP, caps)
        self.assertIn(GALLERY_CAP, caps)
        search = (out.get("schema") or {}).get("search") or {}
        self.assertTrue(search.get("suggestEnabled"))
        self.assertTrue(search.get("hotKeywords"))

    def test_browse_sql_within_budget(self) -> None:
        sql = domain_sql(
            "DOM-SHOP",
            "thesis_test",
            capabilities=["archive", "order_lines", "guestbook", "favorites", "browse_history"],
            proposal_text="浏览历史",
        )
        self.assertIn("user_browse_history", sql)
        self.assertLessEqual(count_create_tables(sql), 13)

    def test_gallery_column_on_product(self) -> None:
        sql = normalize_sql(
            domain_sql(
                "DOM-SHOP",
                "thesis_test",
                capabilities=["archive", "order_lines", "gallery"],
                proposal_text="商品多图轮播",
            )
        )
        self.assertIn("gallery_json", sql)
        # 落在 product 表 CREATE 内，而非独立表
        self.assertNotIn("create table if not exists gallery", sql)
        m = re.search(
            r"create table if not exists product\s*\((.*?)\);",
            sql,
            re.I | re.S,
        )
        self.assertIsNotNone(m)
        self.assertIn("gallery_json", m.group(1))


if __name__ == "__main__":
    unittest.main()
