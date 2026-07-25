"""Spring Security 按需开关 bake 冒烟。"""

from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from app.bake.catalog import build_spec
from app.bake.engine import bake_project
from app.core.config import get_settings


def _bake(*, spring_security: bool, persistence: str, pid: str) -> Path:
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
        spring_security=spring_security,
    )
    return bake_project(pid, spec, f"smoke_sec_{persistence}")


class TestSpringSecurityBake(unittest.TestCase):
    def test_security_off_stays_crypto(self) -> None:
        ws = _bake(spring_security=False, persistence="jdbc", pid="gf-ut-sec-off")
        pom = (ws / "backend" / "pom.xml").read_text(encoding="utf-8")
        self.assertIn("spring-security-crypto", pom)
        self.assertNotIn("spring-boot-starter-security", pom)
        self.assertFalse(any((ws / "backend").rglob("SecurityConfig.java")))
        readme = (ws / "README.md").read_text(encoding="utf-8")
        self.assertIn("未启用 Spring Security", readme)
        self.assertNotIn("SessionAuthFilter", readme)

    def test_security_on_jdbc(self) -> None:
        ws = _bake(spring_security=True, persistence="jdbc", pid="gf-ut-sec-jdbc")
        pom = (ws / "backend" / "pom.xml").read_text(encoding="utf-8")
        self.assertIn("spring-boot-starter-security", pom)
        self.assertNotIn("spring-security-crypto", pom)
        self.assertTrue(any((ws / "backend").rglob("SecurityConfig.java")))
        self.assertTrue(any((ws / "backend").rglob("SessionAuthFilter.java")))
        cfg = next((ws / "backend").rglob("SecurityConfig.java")).read_text(encoding="utf-8")
        self.assertIn("SecurityFilterChain", cfg)
        # 禁用默认 session fixation，避免 SPA 并发请求换 JSESSIONID 后被踢
        self.assertIn("sessionFixation(sf -> sf.none())", cfg)
        readme = (ws / "README.md").read_text(encoding="utf-8")
        self.assertIn("Spring Security", readme)
        self.assertIn("过滤器链", readme)

    def test_security_on_mybatis(self) -> None:
        ws = _bake(spring_security=True, persistence="mybatis", pid="gf-ut-sec-mybatis")
        pom = (ws / "backend" / "pom.xml").read_text(encoding="utf-8")
        self.assertIn("spring-boot-starter-security", pom)
        self.assertIn("mybatis-spring-boot-starter", pom)
        self.assertTrue(any((ws / "backend").rglob("SecurityConfig.java")))
        self.assertTrue(any((ws / "backend").rglob("MybatisSupport.java")))
        readme = (ws / "README.md").read_text(encoding="utf-8")
        self.assertIn("MyBatis", readme)
        self.assertIn("Spring Security", readme)


if __name__ == "__main__":
    unittest.main()
