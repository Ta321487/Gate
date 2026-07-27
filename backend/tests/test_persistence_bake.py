"""persistence=jdbc|mybatis|jpa bake 洁净契约冒烟。"""

from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from app.bake.catalog import build_spec
from app.bake.engine import bake_project
from app.core.config import get_settings


def _bake(
    persistence: str,
    pid: str,
    *,
    title: str = "学生请假销假管理系统",
    domain: str = "DOM-ATTEND",
    archetype: str = "ARCH-FLOW",
) -> Path:
    settings = get_settings()
    dest = settings.workspace_dir / pid
    if dest.exists():
        shutil.rmtree(dest)
    spec = build_spec(
        title=title,
        archetype=archetype,
        domain=domain,
        theme="gen-ink",
        llm_enabled=False,
        match_mode="recommended",
        confidence=0.9,
        persistence=persistence,
    )
    return bake_project(pid, spec, f"smoke_{persistence}")


class TestPersistenceBake(unittest.TestCase):
    def test_jdbc_package_clean(self) -> None:
        ws = _bake("jdbc", "gf-ut-jdbc")
        readme = (ws / "README.md").read_text(encoding="utf-8")
        self.assertIn("JdbcTemplate", readme)
        self.assertTrue(any((ws / "backend").rglob("JdbcSupport.java")))
        self.assertFalse((ws / "backend" / "src" / "main" / "resources" / "mapper").exists())
        pom = (ws / "backend" / "pom.xml").read_text(encoding="utf-8")
        self.assertNotIn("mybatis-spring-boot-starter", pom)
        self.assertNotIn("spring-boot-starter-data-jpa", pom)

    def test_mybatis_package_clean(self) -> None:
        ws = _bake("mybatis", "gf-ut-mybatis")
        readme = (ws / "README.md").read_text(encoding="utf-8")
        self.assertIn("MyBatis", readme)
        self.assertNotIn("没有使用 MyBatis", readme)
        self.assertFalse(any((ws / "backend").rglob("JdbcSupport.java")))
        self.assertFalse(any((ws / "backend").rglob("MbBridge.java")))
        java_files = list((ws / "backend" / "src" / "main" / "java").rglob("*.java"))
        for p in java_files:
            text = p.read_text(encoding="utf-8")
            self.assertNotIn(
                "import org.springframework.jdbc.core.JdbcTemplate",
                text,
                msg=str(p),
            )
            self.assertNotIn("import com.thesis.config.MbBridge", text, msg=str(p))
            self.assertNotIn("MbBridge.", text, msg=str(p))
        self.assertTrue(any((ws / "backend").rglob("NoticeMapper.java")))
        self.assertTrue(any((ws / "backend").rglob("TicketMapper.java")))
        self.assertTrue(any((ws / "backend").rglob("ArchiveMapper.java")))
        self.assertTrue(any((ws / "backend").rglob("OrderMapper.java")))
        self.assertTrue(any((ws / "backend").rglob("MybatisSupport.java")))
        mapper_xml = list((ws / "backend" / "src" / "main" / "resources" / "mapper").glob("*.xml"))
        self.assertGreaterEqual(len(mapper_xml), 8)
        pom = (ws / "backend" / "pom.xml").read_text(encoding="utf-8")
        self.assertIn("mybatis-spring-boot-starter", pom)
        self.assertIn("pagehelper", pom)
        self.assertNotIn("MbBridge", pom)
        yml = (ws / "backend" / "src" / "main" / "resources" / "application.yml").read_text(
            encoding="utf-8"
        )
        self.assertRegex(yml, r"(?m)^mybatis:\s*$")
        self.assertIn("mapper-locations: classpath:mapper/*.xml", yml)
        self.assertRegex(yml, r"(?m)^pagehelper:\s*$")
        # thesis 重写不得吞掉 mybatis 段
        self.assertLess(yml.index("\nthesis:"), yml.index("\nmybatis:"))

    def test_jpa_package_clean(self) -> None:
        ws = _bake("jpa", "gf-ut-jpa")
        readme = (ws / "README.md").read_text(encoding="utf-8")
        self.assertIn("Spring Data JPA", readme)
        self.assertNotIn("没有使用 MyBatis / Mapper", readme)
        self.assertFalse(any((ws / "backend").rglob("JdbcSupport.java")))
        self.assertFalse(any((ws / "backend").rglob("MybatisSupport.java")))
        self.assertFalse(any((ws / "backend").rglob("MbBridge.java")))
        self.assertTrue(any((ws / "backend").rglob("JpaSupport.java")))
        self.assertTrue(any((ws / "backend").rglob("NoticeRepository.java")))
        self.assertTrue(any((ws / "backend").rglob("NoticeEntity.java")))
        self.assertTrue(any((ws / "backend").rglob("NoticeStore.java")))
        java_files = list((ws / "backend" / "src" / "main" / "java").rglob("*.java"))
        for p in java_files:
            text = p.read_text(encoding="utf-8")
            self.assertNotIn(
                "import org.springframework.jdbc.core.JdbcTemplate",
                text,
                msg=str(p),
            )
            self.assertNotIn("import com.github.pagehelper", text, msg=str(p))
            self.assertNotIn("MybatisSupport.mapper", text, msg=str(p))
        pom = (ws / "backend" / "pom.xml").read_text(encoding="utf-8")
        self.assertIn("spring-boot-starter-data-jpa", pom)
        self.assertNotIn("mybatis-spring-boot-starter", pom)
        self.assertFalse((ws / "backend" / "src" / "main" / "resources" / "mapper").exists())
        yml = (ws / "backend" / "src" / "main" / "resources" / "application.yml").read_text(
            encoding="utf-8"
        )
        self.assertRegex(yml, r"(?m)^  jpa:\s*$")
        self.assertIn("ddl-auto: none", yml)
        # thesis 与 spring.jpa 共存；datasource 不得被吞
        self.assertIn("datasource:", yml)
        self.assertIn("\nthesis:", yml)

    def test_mybatis_trade_domain_order_store(self) -> None:
        """交易域也须叠上 OrderStore 状态机，不能只冒烟 ATTEND。"""
        ws = _bake(
            "mybatis",
            "gf-ut-mybatis-food",
            title="小型餐厅点餐系统",
            domain="DOM-FOOD",
            archetype="ARCH-TRADE",
        )
        order_stores = list((ws / "backend").rglob("OrderStore.java"))
        self.assertTrue(order_stores)
        text = order_stores[0].read_text(encoding="utf-8")
        self.assertIn('"ship".equals(act) && "confirmed".equals(st)', text)
        self.assertIn('"complete".equals(act) && "shipped".equals(st)', text)
        self.assertIn("售后处理中，不可完成订单", text)
        self.assertIn("CouponStore.releaseByOrder", text)
        self.assertIn("LoyaltyStore.clawbackOrderCompleted", text)
        # 调用方有方法名不够：Store 本体也必须定义，否则 mvn 报「找不到符号」
        coupon = next((ws / "backend").rglob("CouponStore.java"))
        loyalty = next((ws / "backend").rglob("LoyaltyStore.java"))
        user = next((ws / "backend").rglob("UserStore.java"))
        self.assertIn("public static void releaseByOrder(long orderId)", coupon.read_text(encoding="utf-8"))
        self.assertIn(
            "public static void clawbackOrderCompleted(",
            loyalty.read_text(encoding="utf-8"),
        )
        self.assertIn(
            "public static boolean passwordMatches(Profile p, String password)",
            user.read_text(encoding="utf-8"),
        )

    def test_jpa_trade_domain_order_store(self) -> None:
        ws = _bake(
            "jpa",
            "gf-ut-jpa-food",
            title="小型餐厅点餐系统",
            domain="DOM-FOOD",
            archetype="ARCH-TRADE",
        )
        order = next((ws / "backend").rglob("OrderStore.java"))
        text = order.read_text(encoding="utf-8")
        self.assertIn("JpaSupport", text)
        self.assertIn('"ship".equals(act) && "confirmed".equals(st)', text)
        self.assertIn("CouponStore.releaseByOrder", text)


if __name__ == "__main__":
    unittest.main()
