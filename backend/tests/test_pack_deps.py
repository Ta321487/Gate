"""出包死依赖瘦身 + 库名/单启动类 + README 假表门禁。"""

from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from app.bake.catalog import build_spec
from app.bake.engine import bake_project
from app.bake.pack_deps import (
    scan_dead_declared_deps,
    scan_delivery_identity_issues,
    scan_readme_schema_phantoms,
    scrub_application_yml_ai,
    scrub_pom_unused_deps,
    scrub_student_pack_deps,
)
from app.bake.pack_prune import evaluate_pack_lean_gate
from app.core.config import get_settings


class TestPackDepsUnit(unittest.TestCase):
    def test_scrub_pom_drops_lombok_validation_and_ai_when_off(self) -> None:
        raw = """
  <properties>
    <spring-ai.version>1.0.0</spring-ai.version>
  </properties>
  <dependencyManagement>
    <dependencies>
      <dependency>
        <groupId>org.springframework.ai</groupId>
        <artifactId>spring-ai-bom</artifactId>
        <version>${spring-ai.version}</version>
        <type>pom</type>
        <scope>import</scope>
      </dependency>
    </dependencies>
  </dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.ai</groupId>
      <artifactId>spring-ai-deepseek</artifactId>
    </dependency>
    <dependency>
      <groupId>org.projectlombok</groupId>
      <artifactId>lombok</artifactId>
      <optional>true</optional>
    </dependency>
  </dependencies>
"""
        off = scrub_pom_unused_deps(raw, ai_on=False)
        self.assertNotIn("lombok", off)
        self.assertNotIn("spring-boot-starter-validation", off)
        self.assertNotIn("spring-ai-deepseek", off)
        self.assertNotIn("spring-ai-bom", off)
        on = scrub_pom_unused_deps(raw, ai_on=True)
        self.assertIn("spring-ai-deepseek", on)
        self.assertNotIn("lombok", on)

    def test_scrub_yml_ai_block(self) -> None:
        yml = """spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/demo
  # AI 助手：Spring AI + DeepSeek
  ai:
    deepseek:
      api-key: ${DEEPSEEK_API_KEY:}
      base-url: https://api.deepseek.com

management:
  endpoints:
    web:
      exposure:
        include: health
"""
        out = scrub_application_yml_ai(yml, ai_on=False)
        self.assertNotIn("deepseek", out.lower())
        self.assertNotRegex(out, r"(?m)^\s*ai:\s*$")
        self.assertIn("management:", out)

    def test_identity_db_mismatch_and_multi_app(self) -> None:
        root = Path(get_settings().workspace_dir) / "gf-ut-pack-deps-id"
        if root.exists():
            shutil.rmtree(root)
        (root / "sql").mkdir(parents=True)
        (root / "backend" / "src" / "main" / "resources").mkdir(parents=True)
        (root / "backend" / "src" / "main" / "java" / "com" / "campus" / "a").mkdir(
            parents=True
        )
        (root / "backend" / "src" / "main" / "java" / "com" / "campus" / "b").mkdir(
            parents=True
        )
        (root / "sql" / "schema.sql").write_text(
            "CREATE DATABASE IF NOT EXISTS `alpha`;\nUSE `alpha`;\n",
            encoding="utf-8",
        )
        (root / "backend" / "src" / "main" / "resources" / "application.yml").write_text(
            "spring:\n  datasource:\n    url: jdbc:mysql://127.0.0.1:3306/beta?x=1\n",
            encoding="utf-8",
        )
        (
            root / "backend" / "src" / "main" / "java" / "com" / "campus" / "a" / "AApplication.java"
        ).write_text("class A {}", encoding="utf-8")
        (
            root / "backend" / "src" / "main" / "java" / "com" / "campus" / "b" / "BApplication.java"
        ).write_text("class B {}", encoding="utf-8")
        (root / "README.md").write_text("# x\n", encoding="utf-8")
        hits = scan_delivery_identity_issues(root)
        self.assertTrue(any(h.startswith("db_mismatch:") for h in hits))
        self.assertTrue(any(h.startswith("multi_application:") for h in hits))

    def test_readme_phantom_signup(self) -> None:
        root = Path(get_settings().workspace_dir) / "gf-ut-pack-deps-readme"
        if root.exists():
            shutil.rmtree(root)
        (root / "sql").mkdir(parents=True)
        (root / "sql" / "schema.sql").write_text(
            "CREATE TABLE IF NOT EXISTS product (id BIGINT);\n",
            encoding="utf-8",
        )
        (root / "README.md").write_text(
            "FROM signup\nJOIN activity a\ntaste_note\n",
            encoding="utf-8",
        )
        hits = scan_readme_schema_phantoms(root)
        self.assertIn("readme:signup", hits)
        self.assertIn("readme:activity", hits)
        self.assertIn("readme:taste_note", hits)


class TestPackDepsBake(unittest.TestCase):
    def test_shop_ai_off_no_dead_deps_no_readme_phantoms(self) -> None:
        settings = get_settings()
        pid = "gf-ut-pack-deps-shop"
        dest = settings.workspace_dir / pid
        if dest.exists():
            shutil.rmtree(dest)
        spec = build_spec(
            title="农产品商城",
            archetype="ARCH-CRUD",
            domain="DOM-SHOP",
            theme="gen-ink",
            llm_enabled=False,
            match_mode="recommended",
            confidence=0.9,
            ai_assistant=False,
            proposal={"excerpt": "农产品在线销售与订单"},
        )
        # 题目语义短名，贴近真单 agri_produce_mall
        spec["delivery_slug"] = "agri_produce_mall"
        ws = bake_project(pid, spec, "agri_produce_mall")
        pom = (ws / "backend" / "pom.xml").read_text(encoding="utf-8")
        self.assertNotIn("spring-ai-deepseek", pom)
        self.assertNotIn("lombok", pom)
        self.assertNotIn("spring-boot-starter-validation", pom)
        yml = (ws / "backend" / "src" / "main" / "resources" / "application.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("deepseek", yml.lower())
        pkg = json.loads((ws / "frontend" / "package.json").read_text(encoding="utf-8"))
        self.assertNotIn("@ctrl/tinycolor", pkg.get("dependencies") or {})
        readme = (ws / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("signup", readme)
        self.assertNotIn("taste_note", readme)
        self.assertIn("agri_produce_mall", readme)
        self.assertEqual(scan_dead_declared_deps(ws, spec), [])
        self.assertEqual(scan_readme_schema_phantoms(ws), [])
        lean = evaluate_pack_lean_gate(ws, json.loads((ws / "spec.json").read_text(encoding="utf-8")))
        self.assertTrue(lean["ok"], lean.get("desc"))

    def test_scrub_idempotent_on_workspace(self) -> None:
        settings = get_settings()
        root_sk = Path(__file__).resolve().parents[2] / "skeletons" / "baseline"
        dest = settings.workspace_dir / "gf-ut-pack-deps-idem"
        if dest.exists():
            shutil.rmtree(dest)
        (dest / "backend" / "src" / "main" / "resources").mkdir(parents=True)
        (dest / "frontend").mkdir(parents=True)
        shutil.copy(root_sk / "backend" / "pom.xml", dest / "backend" / "pom.xml")
        shutil.copy(
            root_sk / "backend" / "src" / "main" / "resources" / "application.yml",
            dest / "backend" / "src" / "main" / "resources" / "application.yml",
        )
        shutil.copy(root_sk / "frontend" / "package.json", dest / "frontend" / "package.json")
        (dest / "spec.json").write_text(
            json.dumps({"ai_assistant": False, "capabilities": []}),
            encoding="utf-8",
        )
        notes = scrub_student_pack_deps(dest, {"ai_assistant": False})
        self.assertTrue(any("pom:" in n or "yml:" in n for n in notes))
        self.assertEqual(scan_dead_declared_deps(dest, {"ai_assistant": False}), [])
        self.assertEqual(scrub_student_pack_deps(dest, {"ai_assistant": False}), [])


if __name__ == "__main__":
    unittest.main()
