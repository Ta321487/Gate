"""persistence=jdbc|mybatis bake 洁净契约冒烟。"""

from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from app.bake.catalog import build_spec
from app.bake.engine import bake_project
from app.core.config import get_settings


def _bake(persistence: str, pid: str) -> Path:
    settings = get_settings()
    dest = settings.workspace_dir / pid
    if dest.exists():
        shutil.rmtree(dest)
    spec = build_spec(
        title="学生请假销假管理系统",
        archetype="ARCH-FLOW",
        domain="DOM-ATTEND",
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


if __name__ == "__main__":
    unittest.main()
