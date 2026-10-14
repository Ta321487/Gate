"""演示封面：SQL 补 cover_url + 工作区落真实上传文件。"""

from __future__ import annotations

from pathlib import Path

from app.bake.demo_covers import (
    COVER_COUNT,
    collect_upload_refs,
    cover_url_for_index,
    ensure_demo_cover_urls_sql,
    materialize_demo_uploads,
)
from app.bake.engine_sql import domain_sql


_SHOP_DDL = """
CREATE TABLE IF NOT EXISTS product (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  cover_url VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
INSERT IGNORE INTO product (id, title) VALUES (1, '红富士'), (2, '生菜');
"""


def test_cover_url_round_robin():
    assert cover_url_for_index(1) == "/uploads/demo/cover-01.jpg"
    assert cover_url_for_index(COVER_COUNT) == f"/uploads/demo/cover-{COVER_COUNT:02d}.jpg"
    assert cover_url_for_index(COVER_COUNT + 1) == "/uploads/demo/cover-01.jpg"


def test_ensure_demo_cover_urls_sql_updates_empty():
    out = ensure_demo_cover_urls_sql(_SHOP_DDL, item_table="product")
    assert "gf demo covers for product" in out
    assert "UPDATE `product` SET cover_url = ELT" in out
    assert "/uploads/demo/cover-01.jpg" in out
    # 幂等
    again = ensure_demo_cover_urls_sql(out, item_table="product")
    assert again.count("gf demo covers for product") == 1


def test_ensure_skips_when_no_cover_column():
    ddl = """
CREATE TABLE IF NOT EXISTS biz_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL
);
"""
    assert "gf demo covers" not in ensure_demo_cover_urls_sql(ddl, item_table="biz_item")


def test_collect_refs_includes_sql_and_standard_covers():
    sql = "VALUES (1, '/uploads/demo/monitor.jpg', 'x'), (2, '/uploads/seed-permit.png', 'y')"
    refs = collect_upload_refs(sql)
    assert "demo/monitor.jpg" in refs
    assert "seed-permit.png" in refs
    assert "demo/cover-01.jpg" in refs


def test_materialize_writes_real_files(tmp_path: Path):
    sql = (
        _SHOP_DDL
        + "\nINSERT INTO post_attach (url) VALUES ('/uploads/demo/monitor.jpg');\n"
        + ensure_demo_cover_urls_sql(_SHOP_DDL, item_table="product")
    )
    written = materialize_demo_uploads(
        tmp_path, sql, domain="DOM-SHOP", theme="shop-coral"
    )
    assert "demo/cover-01.jpg" in written
    assert "demo/monitor.jpg" in written
    cover = tmp_path / "backend" / "uploads" / "demo" / "cover-01.jpg"
    monitor = tmp_path / "backend" / "uploads" / "demo" / "monitor.jpg"
    assert cover.is_file() and cover.stat().st_size > 64
    assert monitor.is_file() and monitor.stat().st_size > 64


def test_domain_sql_shop_gets_cover_update():
    sql = domain_sql(
        "DOM-SHOP",
        "agri_mall_test",
        "ARCH-TRADE",
        archetypes=["ARCH-TRADE"],
        capabilities=["archive", "order_lines"],
        title="超新农产品销售网站",
        proposal_text="农产品商城上下架订单",
    )
    assert "gf demo covers for product" in sql
    assert "/uploads/demo/cover-01.jpg" in sql
