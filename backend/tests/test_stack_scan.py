"""stack_scan：开题技术栈推荐（与 scene 独立）。"""

from __future__ import annotations

import unittest

from app.bake.stack_scan import normalize_persistence, normalize_spine, scan_stack


class TestStackScan(unittest.TestCase):
    def test_default_jdbc_when_unclear(self) -> None:
        r = scan_stack("学生请假管理系统", "实现请假审批与销假。")
        self.assertEqual(r["persistence"], "jdbc")
        self.assertEqual(r["spine"], "spa")
        self.assertFalse(r["warnings"])

    def test_mybatis_named(self) -> None:
        r = scan_stack(
            "图书管理系统",
            "技术路线：Spring Boot + Vue + MyBatis + MySQL，分页用 PageHelper。",
        )
        self.assertEqual(r["persistence"], "mybatis")
        self.assertIn("MyBatis", r["hits"])

    def test_jdbc_named(self) -> None:
        r = scan_stack("商城系统", "后端采用 Spring Boot 与 JdbcTemplate 访问 MySQL。")
        self.assertEqual(r["persistence"], "jdbc")
        self.assertIn("JdbcTemplate", r["hits"])

    def test_mybatis_wins_when_both(self) -> None:
        r = scan_stack("系统", "可用 JdbcTemplate 或 MyBatis。")
        self.assertEqual(r["persistence"], "mybatis")

    def test_unsupported_django(self) -> None:
        r = scan_stack("系统", "技术路线 Django + Vue。")
        self.assertTrue(any("Django" in w for w in r["warnings"]))
        self.assertEqual(r["persistence"], "jdbc")

    def test_security_hint_deliverable(self) -> None:
        r = scan_stack("系统", "集成 Spring Security 做登录鉴权。")
        self.assertIn("spring_security", r["addons"])
        self.assertTrue(r["addons"]["spring_security"]["deliverable"])
        self.assertTrue(r["spring_security"])
        self.assertTrue(r["recommended_spring_security"])
        self.assertFalse(any("尚未提供" in w for w in r["warnings"]))

    def test_security_default_off(self) -> None:
        r = scan_stack("系统", "实现登录与业务审批。")
        self.assertFalse(r["spring_security"])
        self.assertNotIn("spring_security", r["addons"])

    def test_echarts_named_ok(self) -> None:
        r = scan_stack("系统", "工作台用 ECharts 做统计图。")
        self.assertTrue(r["addons"]["echarts"]["deliverable"])

    def test_undelivered_ssr_thymeleaf_warns(self) -> None:
        r = scan_stack(
            "图书管理系统",
            "技术路线：Spring Boot + Thymeleaf + AdminLTE，服务端渲染。",
        )
        self.assertTrue(any("Thymeleaf" in w for w in r["warnings"]))
        self.assertTrue(any("AdminLTE" in w for w in r["warnings"]))
        self.assertEqual(r["spine"], "spa")  # 未落地仍落 spa，但不得静默

    def test_jpa_named(self) -> None:
        r = scan_stack("商城系统", "持久层采用 Spring Data JPA / Hibernate。")
        self.assertEqual(r["persistence"], "jpa")
        self.assertIn("JPA", r["hits"])
        self.assertFalse(any("未落地" in w for w in r["warnings"]))

    def test_jpa_wins_over_mybatis_when_both(self) -> None:
        r = scan_stack("系统", "可用 MyBatis 或 Spring Data JPA。")
        self.assertEqual(r["persistence"], "jpa")

    def test_normalize(self) -> None:
        self.assertEqual(normalize_persistence("jpa"), "jpa")
        self.assertEqual(normalize_persistence("hibernate"), "jpa")
        self.assertEqual(normalize_persistence("mybatis"), "mybatis")
        self.assertEqual(normalize_persistence("nope"), "jdbc")
        self.assertEqual(normalize_spine("ssr"), "spa")
        self.assertEqual(normalize_spine("spa"), "spa")


if __name__ == "__main__":
    unittest.main()
