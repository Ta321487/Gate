"""终稿吸收：论文库表章 → draft schema.sql（L1 正文主矿）。"""

from __future__ import annotations

import unittest

from app.services.thesis_absorb_schema import (
    assert_schema_homology,
    extract_draft_schema,
    mine_columns_from_text_block,
    parse_anchored_field_line,
    parse_field_table_rows,
    parse_physical_captions,
    render_schema_sql,
)


_EIGHT_HEADER = ["序号", "列名", "说明", "数据类型", "长度", "允许空", "自增", "主外键"]

# 力固/冠清真实正文片段（类型词锚定）
_LIGU_YONGHU = """
表 4.1 用户表 yonghu
序号 字段 说明 数据类型 长度 自增 主外键 允许空
1 yonghu_id 用户 ID bigint 默认 √ 主键 ×
2 addtime 创建时间 timestamp 默认 × × ×
3 yonghuzhanghao 用户账号 varchar 200 × × ×
4 mima 密码 varchar 200 × × ×
"""

# 冠清：枚举题注 + 如表所示 + 折行表头
_GUANQING_CANGKU = """
（3）仓库管理员表 cangkuguanliyuan，仓库管理员的信息存储在该表中，具体内
容如表 4.3所示。
序号 字段 说明 数据类型 长度 自
增
主外
键
允许空
1 cangkuguanliyuan_id 仓库管理员 ID bigint 默认 √ 主键 ×
2 addtime 创建时间 timestamp 默认 × × ×
3 cangguanzhanghao 仓管账号 varchar 200 × × ×
"""

# 小羽：折行表头 + 外键
_XIAOYU_BACK = """
表 4.1 管理员表 backstage
序号 字段 说明 数据类型 长度 自增 主外
键
允许空
1 ht_id 后台 ID int 1000 √ 主键 ×
2 name 账户 varchar 1000 × × √
3 Pwd 密码 varchar 1000 × × √
（2）收藏表 collect，用于记录用户收藏的商品或内容。
具体内容如表 4.2所示。
表 4.2 收藏表 collect
序号 字段 说明 数据类型 长度 自增 主外
键
允许空
1 sc_id 收藏 ID int 默认 √ 主键 ×
2 p_id 用户 ID int 默认 × 外键 √
"""


def _yonghu_rows() -> list[list[str]]:
    return [
        _EIGHT_HEADER,
        ["1", "id", "用户ID", "int", "", "×", "√", "主键"],
        ["2", "username", "用户账号", "varchar", "64", "×", "×", "×"],
        ["3", "password", "密码", "varchar", "64", "√", "×", "×"],
        ["4", "addtime", "创建时间", "datetime", "", "√", "×", "×"],
    ]


class ThesisAbsorbSchemaTests(unittest.TestCase):
    def test_parse_captions_need_english(self) -> None:
        text = (
            "表 4.1 用户表 yonghu\n"
            "表 4.2 订单表 orders\n"
            "表 4.3 关于我们表\n"
            "表 4.4所示。\n"
        )
        caps = parse_physical_captions(text)
        ens = [c["en"] for c in caps]
        self.assertEqual(ens, ["yonghu", "orders"])

    def test_enum_caption_guanqing_form(self) -> None:
        caps = parse_physical_captions(_GUANQING_CANGKU)
        self.assertEqual(len(caps), 1)
        self.assertEqual(caps[0]["en"], "cangkuguanliyuan")
        self.assertEqual(caps[0]["zh"], "仓库管理员表")
        self.assertEqual(caps[0]["no"], "4.3")

    def test_enum_caption_glued_en_and_split_shown(self) -> None:
        text = (
            "（5）材料商城表cailiaoshangcheng，材料商城的信息存储在该表中，具体内容如\n"
            "表4.5 所示。\n"
            "序号 字段 说明 数据类型 长度 自增 主外键 允许空\n"
            "1 cailiaoshangcheng_id 材料商城ID bigint 默认 √ 主键 ×\n"
            "（6）材料类型表cailiaoleixing，材料类型的信息存储在该表中，具体内容如表\n"
            "4.6 所示。\n"
            "序号 字段 说明 数据类型 长度 自增 主外键 允许空\n"
            "1 cailiaoleixing_id 材料类型ID bigint 默认 √ 主键 ×\n"
        )
        caps = parse_physical_captions(text)
        ens = [c["en"] for c in caps]
        self.assertEqual(ens, ["cailiaoshangcheng", "cailiaoleixing"])
        self.assertEqual(caps[0]["no"], "4.5")
        self.assertEqual(caps[1]["no"], "4.6")
        pack = extract_draft_schema(text)
        self.assertEqual(pack["schema_extract_meta"]["table_count"], 2)

    def test_anchored_line_label_with_spaces(self) -> None:
        col = parse_anchored_field_line("1 yonghu_id 用户 ID bigint 默认 √ 主键 ×")
        assert col is not None
        self.assertEqual(col["name"], "yonghu_id")
        self.assertEqual(col["label"], "用户 ID")
        self.assertEqual(col["type"], "bigint")
        self.assertTrue(col["pk"])
        self.assertTrue(col["auto_increment"])

    def test_parse_eight_col_and_sql(self) -> None:
        cols = parse_field_table_rows(_yonghu_rows())
        self.assertEqual([c["name"] for c in cols], ["id", "username", "password", "addtime"])
        sql = render_schema_sql(
            [{"name": "yonghu", "label": "用户表", "no": "4.1", "columns": cols}]
        )
        self.assertIn("CREATE TABLE IF NOT EXISTS `yonghu`", sql)
        assert_schema_homology(sql, [{"name": "yonghu", "columns": cols}])

    def test_l1_ligu_snippet(self) -> None:
        pack = extract_draft_schema(_LIGU_YONGHU)
        self.assertIn("`yonghu`", pack["draft_schema_sql"])
        self.assertIn("`yonghu_id`", pack["draft_schema_sql"])
        self.assertIn("varchar(200)", pack["draft_schema_sql"])
        self.assertEqual(pack["schema_extract_meta"]["table_count"], 1)
        self.assertTrue(pack["schema_extract_meta"]["homology_ok"])

    def test_l1_guanqing_enum_snippet(self) -> None:
        pack = extract_draft_schema(_GUANQING_CANGKU)
        sql = pack["draft_schema_sql"]
        self.assertIn("`cangkuguanliyuan`", sql)
        self.assertIn("`cangguanzhanghao`", sql)
        self.assertEqual(pack["schema_extract_meta"]["table_count"], 1)

    def test_l1_xiaoyu_two_tables(self) -> None:
        pack = extract_draft_schema(_XIAOYU_BACK)
        sql = pack["draft_schema_sql"]
        self.assertIn("`backstage`", sql)
        self.assertIn("`collect`", sql)
        self.assertIn("`ht_id`", sql)
        self.assertIn("`sc_id`", sql)
        self.assertEqual(pack["schema_extract_meta"]["table_count"], 2)
        # 不串台：backstage 体不含 sc_id
        i = sql.find("CREATE TABLE IF NOT EXISTS `backstage`")
        j = sql.find("CREATE TABLE IF NOT EXISTS `collect`")
        self.assertNotIn("`sc_id`", sql[i:j])

    def test_no_invent_columns(self) -> None:
        text = (
            "第4章 数据库设计\n"
            "表 4.1 用户表 yonghu\n"
            "用户（用户 ID、用户账号、密码）\n"
        )
        pack = extract_draft_schema(text, plumber_tables=[])
        self.assertEqual(pack["draft_schema_sql"], "")
        self.assertEqual(pack["schema_extract_meta"]["table_count"], 0)
        self.assertTrue(pack["schema_extract_meta"]["warnings"])

    def test_plumber_bind_produces_sql(self) -> None:
        text = "数据库物理设计\n表 4.1 用户表 yonghu\n"
        plumber = [{"page": 33, "index": 0, "rows": _yonghu_rows()}]
        pack = extract_draft_schema(text, plumber_tables=plumber)
        # L1 空则 L2 补
        self.assertIn("`yonghu`", pack["draft_schema_sql"])
        self.assertNotIn("`email`", pack["draft_schema_sql"])

    def test_homology_rejects_invented(self) -> None:
        cols = parse_field_table_rows(_yonghu_rows())
        fake = (
            "CREATE TABLE IF NOT EXISTS `yonghu` (\n"
            "  `id` int,\n  `ghost` int\n) ENGINE=InnoDB;\n"
        )
        with self.assertRaises(AssertionError):
            assert_schema_homology(fake, [{"name": "yonghu", "columns": cols}])

    def test_same_material_same_sql(self) -> None:
        a = extract_draft_schema(_LIGU_YONGHU)
        b = extract_draft_schema(_LIGU_YONGHU)
        self.assertEqual(a["draft_schema_sql"], b["draft_schema_sql"])

    def test_caption_paren_en_and_dash_no(self) -> None:
        text = "表 4－1 用户表（yonghu）\n序号 字段 说明 数据类型 长度 自增 主外键 允许空\n1 yonghu_id 编号 int 默认 √ 主键 ×\n"
        caps = parse_physical_captions(text)
        self.assertTrue(any(c["en"] == "yonghu" for c in caps))
        pack = extract_draft_schema(text)
        self.assertIn("`yonghu`", pack["draft_schema_sql"])

    def test_zh_types_and_zh_then_en_name(self) -> None:
        col = parse_anchored_field_line(
            "1 用户编号 user_id 整型 默认 主键 否"
        )
        assert col is not None
        self.assertEqual(col["name"], "user_id")
        self.assertEqual(col["label"], "用户编号")
        self.assertEqual(col["type"], "int")
        self.assertTrue(col["pk"])
        col2 = parse_anchored_field_line("title 书名 字符型(50) NOT NULL")
        assert col2 is not None
        self.assertEqual(col2["type"], "varchar(50)")
        self.assertFalse(col2["nullable"])

    def test_attr_header_and_inline_decimal(self) -> None:
        pack = extract_draft_schema(
            "表 4.1 订单表 orders\n"
            "序号 属性名 说明 类型 长度 主外键 允许空\n"
            "1 order_id 订单号 bigint 默认 √ 主键 ×\n"
            "2 amount 金额 decimal(10,2) 默认 × × √\n"
        )
        self.assertIn("`orders`", pack["draft_schema_sql"])
        self.assertIn("decimal(10,2)", pack["draft_schema_sql"])

    def test_oracle_number_token(self) -> None:
        col = parse_anchored_field_line(
            "1 amount 金额 number(10,2) 默认 × × √"
        )
        assert col is not None
        self.assertEqual(col["type"], "decimal(10,2)")

    def test_tab_separated_rows(self) -> None:
        text = (
            "表 4.1 图书表 book\n"
            "序号\t字段名称\t说明\t数据类型\t长度\t自增\t主外键\t允许空\n"
            "1\tbook_id\t图书编号\tint\t默认\t√\t主键\t×\n"
            "2\ttitle\t书名\tvarchar\t100\t×\t×\t√\n"
        )
        pack = extract_draft_schema(text)
        self.assertIn("`book`", pack["draft_schema_sql"])
        self.assertIn("`book_id`", pack["draft_schema_sql"])
        self.assertIn("varchar(100)", pack["draft_schema_sql"])

    def test_usecase_table_not_caption(self) -> None:
        text = (
            '表 3.1 “添加购物车”的用例文档\n'
            "参与者 用户\n"
            "表 4.1 购物车表 cart\n"
            "序号 字段 说明 数据类型 长度 自增 主外键 允许空\n"
            "1 cart_id 购物车 ID bigint 默认 √ 主键 ×\n"
        )
        caps = parse_physical_captions(text)
        self.assertEqual([c["en"] for c in caps], ["cart"])

    def test_cell_per_line_pdf_dump(self) -> None:
        """PyMuPDF 字段表常一格一行，不能靠空格切列。"""
        text = (
            "表 4.1 用户表 yonghu\n"
            "序号\n字段\n说明\n数据类型\n长度\n自增\n主外键\n允许空\n"
            "1\nyonghu_id\n用户ID\nbigint\n默认\n√\n主键\n×\n"
            "2\naddtime\n创建时间\ntimestamp\n默认\n×\n×\n×\n"
            "3\nyonghuzhanghao\n用户账号\nvarchar\n200\n×\n×\n×\n"
        )
        pack = extract_draft_schema(text)
        sql = pack["draft_schema_sql"]
        self.assertIn("`yonghu_id`", sql)
        self.assertIn("`addtime`", sql)
        self.assertIn("timestamp", sql)
        self.assertIn("varchar(200)", sql)
        self.assertEqual(pack["schema_extract_meta"]["table_count"], 1)

    def test_enum_then_table_caption_same_en(self) -> None:
        """枚举行后再写「表4.n …」不得截断字段块。"""
        text = (
            "（1）后台管理员表backstage，用于存储账号。具体\n"
            "内容如表4.1 所示。\n"
            "表4.1 管理员表backstage\n"
            "序号\n字段\n说明\n数据类型\n长度\n自增\n主外\n键\n允许空\n"
            "1\nht_id\n后台ID\nint\n1000\n√\n主键\n×\n"
            "2\nname\n账户\nvarchar\n1000\n×\n×\n√\n"
        )
        pack = extract_draft_schema(text)
        self.assertIn("`ht_id`", pack["draft_schema_sql"])
        self.assertIn("`name`", pack["draft_schema_sql"])
        self.assertEqual(pack["schema_extract_meta"]["table_count"], 1)


if __name__ == "__main__":
    unittest.main()
