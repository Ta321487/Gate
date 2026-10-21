"""档案语义列门禁：能扫到逻辑列残留，也能先修后验。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.bake.archive_columns import (
    assert_archive_semantic_columns,
    ensure_archive_semantic_columns,
    find_archive_logical_col_leaks,
    repair_archive_logical_col_leaks,
    repair_workspace_schema_semantic_columns,
)
from app.bake.engine_sql import domain_sql
from app.bake.domains import DOMAIN_CAPABILITIES


class ArchiveSemanticGateTests(unittest.TestCase):
    def test_find_and_repair_flash_update_author(self) -> None:
        leaked = """
CREATE TABLE IF NOT EXISTS product (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  price_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  sku VARCHAR(64) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
UPDATE product SET
  promo_price = ROUND(CAST(author AS DECIMAL(10,2)) * 0.85, 2)
WHERE id IN (1, 2)
  AND CAST(author AS DECIMAL(10,2)) > 0;
"""
        issues = find_archive_logical_col_leaks(
            leaked, domain="DOM-SHOP", item_table="product"
        )
        self.assertTrue(any("UPDATE" in i and "author" in i for i in issues))
        fixed = repair_archive_logical_col_leaks(
            leaked, domain="DOM-SHOP", item_table="product"
        )
        self.assertIn("CAST(price_yuan AS DECIMAL(10,2))", fixed)
        self.assertNotIn("CAST(author AS DECIMAL(10,2))", fixed)
        assert_archive_semantic_columns(
            fixed, domain="DOM-SHOP", item_table="product"
        )

    def test_ensure_repairs_insert_then_passes(self) -> None:
        leaked = """
CREATE TABLE IF NOT EXISTS product (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(64) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
INSERT IGNORE INTO product (id, title, author, isbn, category_id, stock, status) VALUES
(5, '台灯', '45.00', 'CS-05', 2, 1, 'available');
"""
        out = ensure_archive_semantic_columns(
            leaked, domain="DOM-SHOP", item_table="product"
        )
        self.assertIn("price_yuan", out)
        self.assertIn("sku", out)
        self.assertNotIn(
            "INSERT IGNORE INTO product (id, title, author, isbn,", out
        )

    def test_domain_sql_shop_flash_passes_gate(self) -> None:
        caps = list(DOMAIN_CAPABILITIES["DOM-SHOP"]) + ["flash_price"]
        sql = domain_sql(
            "DOM-SHOP",
            "thesis_shop",
            capabilities=caps,
            proposal_text="商品浏览；支持限时购与活动价。",
        )
        assert_archive_semantic_columns(
            sql, domain="DOM-SHOP", item_table="product"
        )
        self.assertFalse(
            find_archive_logical_col_leaks(
                sql, domain="DOM-SHOP", item_table="product"
            )
        )

    def test_workspace_repair_rewrites_schema(self) -> None:
        import tempfile

        # Windows 下后端 reload 监视会占住临时目录句柄，cleanup 失败不阻塞断言
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            root = Path(tmp)
            (root / "sql").mkdir()
            (root / "spec.json").write_text(
                json.dumps(
                    {
                        "domain": "DOM-SHOP",
                        "archetype": "ARCH-TRADE",
                        "runtime": {"archive_item_table": "product"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            schema = root / "sql" / "schema.sql"
            schema.write_text(
                """
CREATE TABLE IF NOT EXISTS product (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  price_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  sku VARCHAR(64) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
UPDATE product SET promo_price = CAST(author AS DECIMAL(10,2)) * 0.85 WHERE id=1;
""",
                encoding="utf-8",
            )
            self.assertTrue(repair_workspace_schema_semantic_columns(root))
            text = schema.read_text(encoding="utf-8")
            self.assertIn("price_yuan", text)
            self.assertNotIn("CAST(author", text)


if __name__ == "__main__":
    unittest.main()
