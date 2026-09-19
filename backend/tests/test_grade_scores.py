"""教务成绩登记：域默认菜单、yml 开关、三套叠层都能打开。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.domain_schema import build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"
MYBATIS = ROOT / "skeletons" / "overlays" / "persistence-mybatis"
JPA = ROOT / "skeletons" / "overlays" / "persistence-jpa"


class GradeScoreTests(unittest.TestCase):
    def test_schema_menus_and_yml(self) -> None:
        schema = build_domain_schema("教务成绩管理系统", "DOM-GRADE")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        self.assertTrue(schema.get("gradeScores"))
        user_keys = {m.get("key") for m in (schema.get("menus") or {}).get("user") or []}
        admin_keys = {m.get("key") for m in (schema.get("menus") or {}).get("admin") or []}
        self.assertIn("grade_scores_mine", user_keys)
        self.assertIn("grade_scores_admin", admin_keys)
        spec = {
            "domain": "DOM-GRADE",
            "capabilities": list(DOMAIN_CAPABILITIES["DOM-GRADE"]),
            "schema": schema,
        }
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-GRADE", spec)
        self.assertIn("grade-scores-enabled: true", yml)

    def test_sql_seed_has_scores(self) -> None:
        sql = domain_sql("DOM-GRADE", "t_grade", title="教务成绩", proposal_text="成绩录入查询")
        self.assertIn("grade_score", sql)
        self.assertIn("86.00", sql)

    def test_three_stacks_wire_store(self) -> None:
        self.assertTrue(
            (BASELINE / "backend/src/main/java/com/thesis/service/GradeScoreStore.java").is_file()
        )
        self.assertTrue(
            (BASELINE / "backend/src/main/java/com/thesis/controller/GradeScoreController.java").is_file()
        )
        for root in (MYBATIS, JPA):
            binder = (root / "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java").read_text(
                encoding="utf-8"
            )
            self.assertIn("grade-scores-enabled", binder, msg=str(root))
            self.assertIn("GradeScoreStore.configure", binder, msg=str(root))
            store = (root / "backend/src/main/java/com/thesis/service/GradeScoreStore.java").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("import org.springframework.jdbc.core.JdbcTemplate", store, msg=str(root))
        baseline_binder = (
            BASELINE / "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java"
        ).read_text(encoding="utf-8")
        self.assertIn("GradeScoreStore.configure", baseline_binder)
        mb = (MYBATIS / "backend/src/main/java/com/thesis/service/GradeScoreStore.java").read_text(
            encoding="utf-8"
        )
        self.assertIn("MybatisSupport", mb)
        jpa = (JPA / "backend/src/main/java/com/thesis/service/GradeScoreStore.java").read_text(
            encoding="utf-8"
        )
        self.assertIn("JpaSupport", jpa)

    def test_labsafe_subjective_is_not_keyword_grade(self) -> None:
        from app.bake.sql.fragments import _EXAM_LABSAFE_GATE_SEED

        self.assertNotIn("报警|撤离|灭火器", _EXAM_LABSAFE_GATE_SEED)
        self.assertNotIn("自动判分", _EXAM_LABSAFE_GATE_SEED)
        self.assertIn("参考答案供教师阅卷", _EXAM_LABSAFE_GATE_SEED)
