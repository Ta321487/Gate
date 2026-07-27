"""泳道 E · C-01：在线考试 / 题库；DOM-EXAM + exam 能力。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES, resolve_accept
from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept, build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.exam import EXAM_CAP, scan_exam_opts, scan_exam_skin
from app.bake.menu_routes import shell_kind
from app.bake.schema.templates import SCHEMA_BUILDERS

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "samples" / "考试预设开题"
BASELINE = ROOT / "skeletons" / "baseline"


class ExamC01Tests(unittest.TestCase):
    def test_capability_and_domain(self) -> None:
        self.assertIn("exam", CAPABILITIES)
        self.assertEqual(CAPABILITIES["exam"]["status"], "implemented")
        self.assertIn("DOM-EXAM", DOMAINS)
        caps = DOMAIN_CAPABILITIES["DOM-EXAM"]
        self.assertIn("archive", caps)
        self.assertIn(EXAM_CAP, caps)
        self.assertNotIn("ticket_flow", caps)
        self.assertIn("DOM-EXAM", SCHEMA_BUILDERS)

    def test_match_general(self) -> None:
        title = "高校在线考试与题库管理系统"
        got = match_text(
            f"基于 Spring Boot 的{title}的设计与实现。"
            f"主要功能：题库管理、组卷发布、在线答题与自动判分。"
        )
        self.assertEqual(got.domain, "DOM-EXAM", f"hits={got.hits[:12]}")

    def test_neighbors(self) -> None:
        cases = [
            ("在线考试题库组卷自动判分", "DOM-EXAM", "DOM-FORUM"),
            ("党建答题党史专题组卷", "DOM-EXAM", "DOM-PARTY"),
            ("网上评教多维打分", "DOM-EVAL", "DOM-EXAM"),
            ("实验室安全准入申请审批", "DOM-LABSAFE", "DOM-EXAM"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase, avoid=avoid):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")
                self.assertNotEqual(got.domain, avoid)

    def test_schema_menus_and_shell(self) -> None:
        schema = build_domain_schema("高校在线考试与题库管理系统", "DOM-EXAM")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        user_keys = {m.get("key") for m in (schema.get("menus") or {}).get("user") or []}
        # 菜单在 attach_accept 后挂 exam_*；builder 本身为科目壳
        self.assertIn("archive", user_keys)
        self.assertEqual(shell_kind(DOMAIN_CAPABILITIES["DOM-EXAM"]), "archive_only")

        spec = attach_accept(
            {
                "domain": "DOM-EXAM",
                "title": "高校在线考试与题库管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-EXAM"]),
                "archetype": "ARCH-CRUD",
            },
            "题库组卷、在线考试、刷题练习、错题本与成绩排行榜。",
        )
        sch = spec.get("schema") or {}
        user_keys2 = {m.get("key") for m in (sch.get("menus") or {}).get("user") or []}
        admin_keys = {m.get("key") for m in (sch.get("menus") or {}).get("admin") or []}
        self.assertIn("exam_papers", user_keys2)
        self.assertIn("exam_attempts", user_keys2)
        self.assertIn("exam_practice", user_keys2)
        self.assertIn("exam_wrongbook", user_keys2)
        self.assertIn("exam_rank", user_keys2)
        self.assertIn("exam_questions", admin_keys)
        self.assertIn(EXAM_CAP, spec.get("capabilities") or [])

    def test_opts_and_skin(self) -> None:
        opts = scan_exam_opts("刷题练习、答案解析、限时考试、考试次数、排行榜、错题本")
        self.assertTrue(opts["practice"])
        self.assertTrue(opts["explain"])
        self.assertTrue(opts["timer"])
        self.assertTrue(opts["attempt_limit"])
        self.assertTrue(opts["rank"])
        self.assertTrue(opts["wrongbook"])
        self.assertEqual(scan_exam_skin("党建党史答题"), "party")
        self.assertEqual(scan_exam_skin("科目一驾校理论"), "drive")
        self.assertEqual(scan_exam_skin("入职安全教育考试"), "safety")
        self.assertEqual(scan_exam_skin("课程结业测验"), "grad")
        self.assertEqual(scan_exam_skin("普通在线考试"), "general")

    def test_sql_core_tables(self) -> None:
        sql = domain_sql(
            "DOM-EXAM",
            "t_exam",
            title="高校在线考试与题库管理系统",
            proposal_text="题库组卷在线答题自动判分，含错题本",
        )
        for t in (
            "exam_subject",
            "exam_question",
            "exam_paper",
            "exam_paper_question",
            "exam_attempt",
            "exam_answer",
            "exam_wrongbook",
        ):
            self.assertIn(t, sql)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS borrow", sql)

    def test_yml_flags(self) -> None:
        spec = attach_accept(
            {
                "domain": "DOM-EXAM",
                "title": "高校在线考试与题库管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-EXAM"]),
                "archetype": "ARCH-CRUD",
            },
            "在线考试与刷题练习、成绩排行榜。",
        )
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-EXAM", spec)
        self.assertIn("exam-enabled: true", yml)
        self.assertIn("exam-practice-enabled: true", yml)
        self.assertIn("exam-rank-enabled: true", yml)
        self.assertIn("enable-ticket: false", yml)

    def test_accept_full(self) -> None:
        d = resolve_accept(
            list(DOMAIN_CAPABILITIES["DOM-EXAM"]),
            "主要功能：考试科目；题库管理；组卷；在线作答；自动判分。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-CRUD"],
            domain="DOM-EXAM",
            primary_archetype="ARCH-CRUD",
        )
        self.assertEqual(d["accept"], "full", d)

    def test_runtime_files(self) -> None:
        self.assertTrue((BASELINE / "backend/src/main/java/com/thesis/service/ExamStore.java").is_file())
        self.assertTrue((BASELINE / "backend/src/main/java/com/thesis/controller/ExamController.java").is_file())
        self.assertTrue((BASELINE / "frontend/src/views/ExamPapers.vue").is_file())
        self.assertTrue((BASELINE / "frontend/src/views/admin/ExamQuestionsAdmin.vue").is_file())
        store = (BASELINE / "backend/src/main/java/com/thesis/service/ExamStore.java").read_text(
            encoding="utf-8"
        )
        self.assertIn("answer_key", store)
        # 开考取题路径不得默认带出答案键
        self.assertIn("take: no answer key", store)

    def test_samples(self) -> None:
        for name in (
            "C-01-DOM-EXAM-高校在线考试与题库管理系统.txt",
            "C-01-DOM-EXAM-党建党史专题答题系统.txt",
            "C-01-DOM-EXAM-驾校科目一理论题库系统.txt",
        ):
            path = SAMPLES / name
            self.assertTrue(path.is_file(), path)


if __name__ == "__main__":
    unittest.main()
