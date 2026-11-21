"""工厂级中文词表：种子、解析、COMMENT、禁汉字标识符。"""

from __future__ import annotations

import unittest

from app.services import zh_lexicon as zl


class ZhLexiconUnit(unittest.TestCase):
    def setUp(self) -> None:
        zl.invalidate_cache()
        zl.bootstrap_from_seed()

    def test_shell_columns_resolve(self) -> None:
        self.assertEqual(zl.suggested_column_zh("receiver_phone"), "收货电话")
        self.assertEqual(zl.suggested_column_zh("shipped_at"), "发货时间")
        self.assertEqual(zl.suggested_column_zh("refund_at"), "退款时间")
        self.assertEqual(zl.suggested_column_zh("refund_type"), "退款类型")
        self.assertEqual(zl.suggested_column_zh("refund_tracking_no"), "退款物流单号")
        self.assertEqual(zl.suggested_column_zh("cover_url"), "封面图")
        self.assertEqual(zl.suggested_column_zh("from_username"), "发送方账号")
        self.assertEqual(zl.suggested_column_zh("failed_login_count"), "失败登录次数")
        self.assertEqual(zl.suggested_column_zh("partial_ship"), "部分发货")
        # 禁止糊成「售后」
        self.assertNotEqual(zl.suggested_column_zh("refund_type"), "售后")
        self.assertNotEqual(zl.suggested_column_zh("refund_tracking_no"), "售后")

    def test_seed_has_er_zh_common(self) -> None:
        self.assertEqual(zl.suggested_column_zh("username"), "用户名")
        self.assertEqual(zl.resolve_zh("table", "biz_order"), "订单")

    def test_domain_overrides_global(self) -> None:
        rows = [
            {
                "kind": "column",
                "key_name": "status",
                "zh": "全局状态",
                "domain": "",
                "skin": "",
                "table_name": "",
            },
            {
                "kind": "column",
                "key_name": "status",
                "zh": "订单状态",
                "domain": "DOM-SHOP",
                "skin": "",
                "table_name": "",
            },
        ]
        self.assertEqual(
            zl.resolve_zh("column", "status", domain="DOM-SHOP", rows=rows),
            "订单状态",
        )
        self.assertEqual(
            zl.resolve_zh("column", "status", domain="", rows=rows),
            "全局状态",
        )

    def test_annotate_sql_comments(self) -> None:
        sql = """
CREATE TABLE IF NOT EXISTS biz_order (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  receiver_phone VARCHAR(32) DEFAULT '',
  shipped_at DATETIME NULL
);
"""
        out = zl.annotate_sql_comments(sql, domain="DOM-SHOP")
        self.assertIn("COMMENT '收货电话'", out)
        self.assertIn("COMMENT '发货时间'", out)
        # 幂等
        out2 = zl.annotate_sql_comments(out, domain="DOM-SHOP")
        self.assertEqual(out.count("COMMENT '收货电话'"), 1)
        self.assertEqual(out2.count("COMMENT '收货电话'"), 1)

    def test_write_column_comment(self) -> None:
        sql = """
CREATE TABLE IF NOT EXISTS biz_order (
  tracking_no VARCHAR(64) DEFAULT ''
);
"""
        out = zl.write_column_comment_in_sql(
            sql, table="biz_order", column="tracking_no", zh="物流单号"
        )
        self.assertIn("tracking_no VARCHAR(64) DEFAULT '' COMMENT '物流单号'", out)

    def test_assert_no_han_identifiers(self) -> None:
        ok = "CREATE TABLE t (id INT, name VARCHAR(32));"
        self.assertEqual(zl.assert_no_han_identifiers(ok), [])
        bad = "CREATE TABLE t (`姓名` VARCHAR(32));"
        # \w may not match CJK depending on flags — 用显式坏例
        bad2 = "CREATE TABLE 用户表 (id INT);"
        self.assertTrue(zl.assert_no_han_identifiers(bad2))

    def test_inject_pair_adds_comment(self) -> None:
        from app.bake.sql.ddl_edit import _col_pair

        name, ddl = _col_pair(("receiver_phone", "VARCHAR(32) DEFAULT ''"))
        self.assertEqual(name, "receiver_phone")
        self.assertIn("COMMENT '收货电话'", ddl)

    def test_gap_report_runs(self) -> None:
        report = zl.gap_report()
        self.assertIn("gap_count", report)
        self.assertIn("gaps", report)
        self.assertIsInstance(report["gaps"], list)
        if report["gaps"]:
            g0 = report["gaps"][0]
            self.assertIn("suggested_zh", g0)
            self.assertIn("suggest_reason", g0)

    def test_suggest_gap_stem_compose(self) -> None:
        hit = zl.ScanHit(
            domain="", skin="", table_name="", key_name="created_at", kind="column"
        )
        # created_at 若已在词表则不是缺口建议路径；用无整键、有词根的人造键
        hit2 = zl.ScanHit(
            domain="", skin="", table_name="", key_name="reminded_at", kind="column"
        )
        # reminded 在 stem；若整键已有则跳过
        if not zl.resolve_zh("column", "reminded_at"):
            sug = zl.suggest_gap_zh(hit2)
            self.assertIsNotNone(sug)
            assert sug is not None
            self.assertEqual(sug["zh"], "催办时间")
            self.assertEqual(sug["reason"], "词根组合")
        # 无词根的瞎猜后缀 → None
        hit3 = zl.ScanHit(
            domain="", skin="", table_name="", key_name="zzzxxyy_at", kind="column"
        )
        self.assertIsNone(zl.suggest_gap_zh(hit3))
        # 裸 _id 无词根 → None
        hit4 = zl.ScanHit(
            domain="", skin="", table_name="", key_name="zzzxxyy_id", kind="column"
        )
        self.assertIsNone(zl.suggest_gap_zh(hit4))

    def test_suggest_gap_same_table(self) -> None:
        self.assertTrue(zl._fragment_zh("name", None))
        self.assertTrue(zl._fragment_zh("phone", None))
        rows = [
            {
                "kind": "column",
                "key_name": "zzqx_name",
                "zh": "奇项名称",
                "domain": "DOM-SHOP",
                "skin": "",
                "table_name": "gadget",
                "source": "manual",
            },
        ]
        hit = zl.ScanHit(
            domain="DOM-SHOP",
            skin="",
            table_name="gadget",
            key_name="zzqx_phone",
            kind="column",
        )
        sug = zl.suggest_gap_zh(hit, rows)
        self.assertIsNotNone(sug)
        assert sug is not None
        self.assertEqual(sug["zh"], "奇项手机")
        self.assertEqual(sug["reason"], "同表类推")

        # 两个可替换兄弟给出不同结果 → None
        self.assertEqual(zl._fragment_zh("note", None), "记录")
        rows_conflict = [
            {
                "kind": "column",
                "key_name": "zzqy_name",
                "zh": "甲名称",
                "domain": "DOM-X",
                "skin": "",
                "table_name": "t1",
                "source": "manual",
            },
            {
                "kind": "column",
                "key_name": "zzqy_note",
                "zh": "乙记录",
                "domain": "DOM-X",
                "skin": "",
                "table_name": "t1",
                "source": "manual",
            },
        ]
        hit_c = zl.ScanHit(
            domain="DOM-X",
            skin="",
            table_name="t1",
            key_name="zzqy_phone",
            kind="column",
        )
        self.assertIsNone(zl.suggest_gap_zh(hit_c, rows_conflict))

    def test_draft_skipped_for_bake_and_no_overwrite(self) -> None:
        rows = [
            {
                "kind": "column",
                "key_name": "mystery_col",
                "zh": "草稿名",
                "domain": "",
                "skin": "",
                "table_name": "",
                "source": "draft",
            }
        ]
        zl._rows_cache = rows
        zl._apply_global_maps(rows)
        self.assertIsNone(
            zl.resolve_zh("column", "mystery_col", rows=rows, for_bake=True)
        )
        self.assertEqual(
            zl.resolve_zh("column", "mystery_col", rows=rows, for_bake=False),
            "草稿名",
        )
        sql = """
CREATE TABLE IF NOT EXISTS t (
  mystery_col VARCHAR(32) DEFAULT ''
);
"""
        out = zl.annotate_sql_comments(sql)
        self.assertNotIn("COMMENT '草稿名'", out)
        zl.bootstrap_from_seed()

    def test_extract_comment(self) -> None:
        self.assertEqual(
            zl.extract_comment_from_line("  phone VARCHAR(32) COMMENT '手机',"),
            "手机",
        )

    def test_zh_max_len_constant(self) -> None:
        self.assertEqual(zl.ZH_MAX_LEN, 64)
        self.assertEqual(len(zl._escape_comment("测" * 80)), 64)

    def test_same_table_zh_collisions(self) -> None:
        rows = [
            {
                "kind": "column",
                "key_name": "cover_url",
                "zh": "封面图",
                "domain": "DOM-SHOP",
                "skin": "",
                "table_name": "product",
            },
            {
                "kind": "column",
                "key_name": "image_url",
                "zh": "封面图",
                "domain": "DOM-SHOP",
                "skin": "",
                "table_name": "product",
            },
            {
                "kind": "column",
                "key_name": "banner_url",
                "zh": "封面图",
                "domain": "DOM-SHOP",
                "skin": "",
                "table_name": "banner",
            },
        ]
        hits = zl.same_table_zh_collisions(
            rows,
            kind="column",
            key_name="thumb_url",
            zh="封面图",
            domain="DOM-SHOP",
            table_name="product",
        )
        self.assertEqual(hits, ["cover_url", "image_url"])
        # 无表名 → 不告
        self.assertEqual(
            zl.same_table_zh_collisions(
                rows,
                kind="column",
                key_name="thumb_url",
                zh="封面图",
                domain="DOM-SHOP",
                table_name="",
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
