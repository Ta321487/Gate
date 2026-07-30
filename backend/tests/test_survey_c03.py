"""泳道 E · C-03：简易问卷 survey + DOM-SURVEY。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES, resolve_accept
from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept, build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.survey import SURVEY_CAP
from app.bake.menu_routes import shell_kind
from app.bake.schema.templates import SCHEMA_BUILDERS

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "samples" / "能力预设开题"
BASELINE = ROOT / "skeletons" / "baseline"


class SurveyC03Tests(unittest.TestCase):
    def test_capability_and_domain(self) -> None:
        self.assertIn("survey", CAPABILITIES)
        self.assertEqual(CAPABILITIES["survey"]["status"], "implemented")
        self.assertIn("DOM-SURVEY", DOMAINS)
        self.assertIn(SURVEY_CAP, DOMAIN_CAPABILITIES["DOM-SURVEY"])
        self.assertNotIn("ticket_flow", DOMAIN_CAPABILITIES["DOM-SURVEY"])
        self.assertIn("DOM-SURVEY", SCHEMA_BUILDERS)

    def test_match(self) -> None:
        got = match_text(
            "基于 Spring Boot 的高校学生满意度问卷调查系统的设计与实现。"
            "主要功能：问卷配置、在线填写、回收统计。"
        )
        self.assertEqual(got.domain, "DOM-SURVEY", f"hits={got.hits[:12]}")

    def test_neighbors(self) -> None:
        cases = [
            ("满意度问卷调查填写回收统计", "DOM-SURVEY", "DOM-EVAL"),
            ("学期末学生网上评教多维打分", "DOM-EVAL", "DOM-SURVEY"),
            ("在线考试题库组卷自动判分", "DOM-EXAM", "DOM-SURVEY"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")
                self.assertNotEqual(got.domain, avoid)

    def test_schema_and_shell(self) -> None:
        schema = build_domain_schema("高校学生满意度问卷调查系统", "DOM-SURVEY")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        self.assertEqual(shell_kind(DOMAIN_CAPABILITIES["DOM-SURVEY"]), "archive_only")
        spec = attach_accept(
            {
                "domain": "DOM-SURVEY",
                "title": "高校学生满意度问卷调查系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SURVEY"]),
                "archetype": "ARCH-CRUD",
            },
            "问卷配置、填写、回收与选项计数统计。",
        )
        sch = spec.get("schema") or {}
        user_keys = {m.get("key") for m in (sch.get("menus") or {}).get("user") or []}
        admin_keys = {m.get("key") for m in (sch.get("menus") or {}).get("admin") or []}
        self.assertIn("survey_forms", user_keys)
        self.assertIn("survey_mine", user_keys)
        self.assertIn("survey_forms", admin_keys)
        self.assertIn("survey_stats", admin_keys)

    def test_sql_yml_accept(self) -> None:
        sql = domain_sql(
            "DOM-SURVEY",
            "t_survey",
            title="高校学生满意度问卷调查系统",
            proposal_text="问卷配置填写回收统计",
        )
        for t in ("survey_form", "survey_question", "survey_response", "survey_answer"):
            self.assertIn(t, sql)
        spec = attach_accept(
            {
                "domain": "DOM-SURVEY",
                "title": "高校学生满意度问卷调查系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SURVEY"]),
                "archetype": "ARCH-CRUD",
            },
            "问卷调研",
        )
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-SURVEY", spec)
        self.assertIn("survey-enabled: true", yml)
        self.assertIn("enable-ticket: false", yml)
        d = resolve_accept(
            list(DOMAIN_CAPABILITIES["DOM-SURVEY"]),
            "问卷配置；在线填写；回收统计。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-CRUD"],
            domain="DOM-SURVEY",
            primary_archetype="ARCH-CRUD",
        )
        self.assertEqual(d["accept"], "full", d)

    def test_runtime_files(self) -> None:
        self.assertTrue((BASELINE / "backend/src/main/java/com/thesis/service/SurveyStore.java").is_file())
        self.assertTrue((BASELINE / "backend/src/main/java/com/thesis/controller/SurveyController.java").is_file())
        self.assertTrue((BASELINE / "frontend/src/views/SurveyForms.vue").is_file())
        self.assertTrue((BASELINE / "frontend/src/views/admin/SurveyStatsAdmin.vue").is_file())

    def test_sample(self) -> None:
        path = SAMPLES / "C-03-DOM-SURVEY-高校学生满意度问卷调查系统.txt"
        self.assertTrue(path.is_file(), path)

    def test_literature_research_not_survey(self) -> None:
        """开题进度「文献调研」不得误挂问卷能力（民宿样例即踩坑）。"""
        from app.bake.features.survey import merge_survey_capabilities, scan_survey

        hotel = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "samples"
            / "域开题样例近五年"
            / "23-DOM-HOTEL-乡村民宿客房预订管理系统.txt"
        )
        text = hotel.read_text(encoding="utf-8")
        self.assertIn("文献调研", text)
        self.assertFalse(scan_survey(text))
        caps = merge_survey_capabilities(
            list(DOMAIN_CAPABILITIES["DOM-HOTEL"]),
            text,
            domain="DOM-HOTEL",
        )
        self.assertNotIn(SURVEY_CAP, caps)
        # 真问卷题仍要扫到
        self.assertTrue(scan_survey("问卷配置、在线填写与回收统计"))
        self.assertTrue(scan_survey("用户调研与问卷回收"))
        self.assertFalse(scan_survey("学生通过邮箱、问卷或现场投递简历"))


if __name__ == "__main__":
    unittest.main()
