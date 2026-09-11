"""Bake 列契约：能力/开关开了则 SQL 须有对应列（复用 fragments.ensure_*）。"""

from __future__ import annotations

import re
import unittest

from app.bake.engine_sql import domain_sql
from app.bake.sql.fragments import (
    ensure_guestbook_sql,
    ensure_notice_pinned_column,
    ensure_soft_delete_columns,
    ensure_vote_sql,
)


def _create_body(sql: str, table: str) -> str:
    m = re.search(
        rf"CREATE TABLE IF NOT EXISTS\s+`?{re.escape(table)}`?\s*\((.*?)\);",
        sql,
        re.S | re.I,
    )
    assert m, f"missing CREATE {table}"
    return m.group(1)


class SoftFailColumnEnsureTests(unittest.TestCase):
    def test_vote_injects_avatar_when_template_lacks(self) -> None:
        raw = """
CREATE TABLE IF NOT EXISTS vote_candidate (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  campaign_id BIGINT NOT NULL,
  name VARCHAR(128) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS vote_ballot (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  campaign_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  candidate_id BIGINT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""
        out = ensure_vote_sql(raw, enabled=True)
        body = _create_body(out, "vote_candidate")
        self.assertIn("avatar_url", body.lower())

    def test_dom_vote_bake_has_avatar(self) -> None:
        sql = domain_sql("DOM-VOTE", "thesis_vote", title="校园评选投票系统")
        body = _create_body(sql, "vote_candidate")
        self.assertIn("avatar_url", body.lower())

    def test_guestbook_channel_via_ensure_not_regex(self) -> None:
        raw = """
CREATE TABLE IF NOT EXISTS sys_guestbook (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  nickname VARCHAR(64) DEFAULT '',
  body VARCHAR(500) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""
        plain = ensure_guestbook_sql(raw, enabled=True, with_channel=False)
        self.assertNotIn("channel", _create_body(plain, "sys_guestbook").lower())
        with_ch = ensure_guestbook_sql(raw, enabled=True, with_channel=True)
        self.assertIn("channel", _create_body(with_ch, "sys_guestbook").lower())

    def test_marketplace_shop_guestbook_channel(self) -> None:
        sql = domain_sql(
            "DOM-SHOP",
            "thesis_shop",
            title="校园二手交易平台",
            proposal_text="多商家入驻，买家与商家均可留言沟通，支持上下架。",
        )
        self.assertRegex(
            sql,
            re.compile(
                r"CREATE TABLE IF NOT EXISTS\s+sys_guestbook\s*\([^;]*\bchannel\b",
                re.I | re.S,
            ),
        )

    def test_soft_delete_injects_deleted_at(self) -> None:
        raw = """
CREATE TABLE IF NOT EXISTS product (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""
        out = ensure_soft_delete_columns(raw, enabled=True, item_table="product")
        self.assertIn("deleted_at", _create_body(out, "product").lower())
        skip = ensure_soft_delete_columns(raw, enabled=False, item_table="product")
        self.assertNotIn("deleted_at", _create_body(skip, "product").lower())

    def test_shop_bake_soft_delete_column(self) -> None:
        sql = domain_sql("DOM-SHOP", "thesis_shop", title="校园商城管理系统")
        body = _create_body(sql, "product")
        self.assertIn("deleted_at", body.lower())

    def test_notice_pinned_injected(self) -> None:
        raw = """
CREATE TABLE IF NOT EXISTS sys_notice (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(128) NOT NULL,
  content TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""
        out = ensure_notice_pinned_column(raw)
        self.assertIn("pinned", _create_body(out, "sys_notice").lower())

    def test_library_bake_notice_pinned(self) -> None:
        sql = domain_sql("DOM-LIBRARY", "thesis_lib", title="图书借阅管理系统")
        body = _create_body(sql, "sys_notice")
        self.assertIn("pinned", body.lower())


if __name__ == "__main__":
    unittest.main()
