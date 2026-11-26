"""论文库表逻辑/物理导出：同源、不编造、对齐样例行文。"""

from __future__ import annotations

import unittest

from app.bake.schema.er_model import schema_model
from app.bake.schema.schema_thesis_export import (
    assert_export_homology,
    physical_tables,
    render_logical_design,
    render_physical_design,
    render_thesis_db_export,
    schema_table_summary,
)

_SQL = """
CREATE TABLE `sys_user` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(64) NOT NULL,
  PRIMARY KEY (`id`)
);
CREATE TABLE `category` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(64),
  PRIMARY KEY (`id`)
);
CREATE TABLE `product` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(128),
  `category_id` INT,
  PRIMARY KEY (`id`),
  FOREIGN KEY (`category_id`) REFERENCES `category`(`id`)
);
CREATE TABLE `sys_auth_session` (
  `id` INT PRIMARY KEY,
  `username` VARCHAR(64)
);
CREATE TABLE `sys_login_log` (
  `id` INT PRIMARY KEY,
  `username` VARCHAR(64)
);
"""


class SchemaThesisExportTests(unittest.TestCase):
    def test_physical_lists_sql_tables_only_and_marks_shells(self) -> None:
        m = schema_model(_SQL)
        m["tables"] = list(m["tables"]) + [
            {
                "name": "sys_user:user",
                "label": "买家",
                "role_of": "sys_user",
                "columns": [{"name": "id", "pk": True}],
            }
        ]
        export = render_thesis_db_export(m, db_name="demo_db")
        assert_export_homology(export, sql=_SQL)
        names = set(export["table_names"])
        self.assertEqual(
            names,
            {"sys_user", "category", "product", "sys_auth_session", "sys_login_log"},
        )
        self.assertNotIn("sys_user:user", names)
        phys = export["physical"]
        self.assertIn("共设计5张数据表", phys)
        self.assertIn("辅助表", phys)
        self.assertIn("sys_auth_session", phys)
        self.assertIn("category_id", phys)
        self.assertNotIn("sys_user:user", phys)
        self.assertNotIn("fake_col", phys)
        # 样例八列
        self.assertIn("序号\t列名\t说明\t数据类型\t长度\t允许空\t自增\t主外键", phys)
        self.assertIn("表4.1", phys)
        self.assertIn("主键", phys)
        html = export["physical_html"]
        self.assertIn("<table", html)
        self.assertIn('border="0"', html)
        self.assertNotIn('border="1"', html)
        self.assertIn("1.5pt solid #000", html)
        self.assertIn("0.5pt solid #000", html)
        self.assertIn("列名", html)
        self.assertIn("category_id", html)
        self.assertIn("background:#fff", html)
        self.assertIn("color:#000", html)
        self.assertIn("<body", html)

    def test_logical_uses_real_fk_and_hides_shells(self) -> None:
        m = schema_model(_SQL)
        logical = render_logical_design(m)
        self.assertIn("4.6.2", logical)
        self.assertIn("带有波浪线为外键", logical)
        self.assertIn("商品表(", logical)
        self.assertIn("分类表(", logical)
        self.assertNotIn("sys_auth_session", logical)
        self.assertNotIn("sys_login_log", logical)
        # 不再用「一、实体 / 二、联系」旧写法
        self.assertNotIn("一、实体与属性", logical)
        self.assertNotIn("二、实体联系", logical)
        self.assertNotIn("外键→", logical)

    def test_dm_from_to_username_not_same_zh(self) -> None:
        """私信两端列不得都叫「用户账号」，否则逻辑设计会诡异撞名。"""
        sql = """
CREATE TABLE `sys_user` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(64) NOT NULL,
  PRIMARY KEY (`id`)
);
CREATE TABLE `sys_dm_message` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `from_username` VARCHAR(64) NOT NULL,
  `to_username` VARCHAR(64) NOT NULL,
  `body` VARCHAR(512),
  PRIMARY KEY (`id`),
  FOREIGN KEY (`from_username`) REFERENCES `sys_user`(`username`),
  FOREIGN KEY (`to_username`) REFERENCES `sys_user`(`username`)
);
"""
        m = schema_model(sql)
        logical = render_logical_design(m)
        self.assertIn("私信表(", logical)
        self.assertNotIn("用户账号、用户账号", logical)
        self.assertIn("发送方账号", logical)
        self.assertIn("接收方账号", logical)

    def test_thesis_urgent_zh_no_english_shell_keys(self) -> None:
        """急贴论文：常见壳列/弱后缀不得露英文键或糊成「链接」。"""
        from app.bake.schema.er_zh import _COMMON_COL_ZH

        self.assertEqual(_COMMON_COL_ZH.get("cover_url"), "封面图")
        self.assertEqual(_COMMON_COL_ZH.get("failed_login_count"), "失败登录次数")
        self.assertEqual(_COMMON_COL_ZH.get("partial_ship"), "部分发货")
        self.assertEqual(_COMMON_COL_ZH.get("owner_username"), "店主账号")
        self.assertEqual(_COMMON_COL_ZH.get("replied_at"), "回复时间")
        sql = """
CREATE TABLE `product` (
  `id` INT PRIMARY KEY,
  `cover_url` VARCHAR(255),
  `owner_username` VARCHAR(64),
  `partial_ship` TINYINT
);
CREATE TABLE `sys_user` (
  `id` INT PRIMARY KEY,
  `failed_login_count` INT,
  `lock_until` DATETIME,
  `must_change_password` TINYINT,
  `real_name_acked` TINYINT
);
"""
        logical = render_logical_design(schema_model(sql))
        self.assertIn("封面图", logical)
        self.assertIn("店主账号", logical)
        self.assertIn("失败登录次数", logical)
        self.assertNotIn("failed_login_count", logical)
        self.assertNotIn("cover_url", logical)

    def test_common_zh_overrides_stale_sql_comment(self) -> None:
        """COMMON 精确键优先于过时 COMMENT（急贴论文不被旧注释锁死）。"""
        sql = """
CREATE TABLE `sys_user` (
  `id` INT PRIMARY KEY,
  `email_activated` TINYINT COMMENT '验证邮箱',
  `activation_code` VARCHAR(16) COMMENT '验证编码',
  `admin_tags` VARCHAR(255) COMMENT '管理员编号'
);
"""
        logical = render_logical_design(schema_model(sql))
        self.assertIn("邮箱已激活", logical)
        self.assertIn("激活码", logical)
        self.assertIn("管理标签", logical)
        self.assertNotIn("验证邮箱", logical)
        self.assertNotIn("管理员编号", logical)

    def test_physical_tables_skips_role_entities(self) -> None:
        m = {
            "tables": [
                {"name": "orders", "label": "订单", "columns": [{"name": "id", "pk": True}]},
                {
                    "name": "sys_user:admin",
                    "role_of": "sys_user",
                    "columns": [{"name": "id"}],
                },
            ]
        }
        names = [t["name"] for t in physical_tables(m)]
        self.assertEqual(names, ["orders"])

    def test_table_summary_splits_physical_and_comfort(self) -> None:
        m = schema_model(_SQL)
        s = schema_table_summary(m)
        self.assertEqual(s["physical"], 5)
        self.assertEqual(s["shell"], 2)
        self.assertEqual(s["business"], 3)
        self.assertNotEqual(s["comfort_n"], s["physical"])
        self.assertEqual(s["comfort_n"], s["conceptual"] or s["business"])
        self.assertFalse(s["comfort_ok"])

    def test_homology_rejects_invented_table(self) -> None:
        with self.assertRaises(AssertionError):
            assert_export_homology(
                {"table_names": ["no_such_table"]},
                sql=_SQL,
            )

    def test_agri_mall_pack_sql_homology(self) -> None:
        from pathlib import Path

        from app.bake.schema.er_model import schema_model as build

        pack = Path(r"D:\2027届大连科技学院毕设\李锐莹\agri-mall-app\sql\schema.sql")
        if not pack.is_file():
            self.skipTest("agri-mall-app schema.sql not on disk")
        sql = pack.read_text(encoding="utf-8", errors="ignore")
        m = build(sql)
        export = render_thesis_db_export(m, db_name="agri_produce_mall")
        assert_export_homology(export, sql=sql)
        self.assertGreaterEqual(export["table_count"], 14)
        self.assertIn("sys_auth_session", export["table_names"])
        self.assertIn("product", export["table_names"])
        self.assertNotIn("sys_auth_session", export["logical"])
        self.assertIn("序号\t列名\t说明\t数据类型\t长度\t允许空\t自增\t主外键", export["physical"])
        self.assertIn("商品表(", export["logical"])
        self.assertNotIn("\u0332", export["logical"])
        self.assertNotIn("\u0330", export["logical"])
        self.assertIn("| 列名 |", export["combined_md"])
        self.assertIn("## 4.6.3", export["combined_md"])
        # MD/HTML 带主键下划线、外键波浪线标记（非组合字符）
        self.assertIn('class="thesis-fk"', export["logical_md"])
        self.assertIn("<u class=\"thesis-pk\">", export["logical_md"])
        self.assertIn("text-decoration:underline wavy", export["logical_html"])
        self.assertIn("text-decoration:underline;", export["logical_html"])


if __name__ == "__main__":
    unittest.main()
