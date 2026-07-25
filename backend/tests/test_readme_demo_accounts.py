"""学生 README 演示账号占位：与 schema.sql 种子对齐。"""

from __future__ import annotations

from pathlib import Path

from app.bake.engine_sql import (
    _demo_portal_desc,
    _demo_portal_from_sql,
    _patch_student_readme,
)


def test_demo_portal_from_sql_student():
    sql = "('student', 'student123', 'student', '学生甲'"
    assert _demo_portal_from_sql(sql) == ("student", "student123")


def test_demo_portal_from_sql_reader():
    sql = "('reader', 'reader123', 'reader', '读者甲'"
    assert _demo_portal_from_sql(sql) == ("reader", "reader123")


def test_demo_portal_from_sql_user_default():
    sql = "('user', 'user123', 'user', '买家甲'"
    assert _demo_portal_from_sql(sql) == ("user", "user123")


def test_demo_portal_desc_uses_schema_label():
    spec = {"schema": {"roles": {"user": {"id": "reader", "label": "读者"}}}}
    assert "读者" in _demo_portal_desc(spec, "reader")


def test_demo_portal_desc_fallback():
    assert "学生" in _demo_portal_desc({}, "student")


def test_patch_student_readme_fills_portal(tmp_path: Path):
    src = Path(__file__).resolve().parents[2] / "skeletons" / "baseline" / "README.md"
    dest = tmp_path / "proj"
    dest.mkdir()
    (dest / "README.md").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    _patch_student_readme(
        dest,
        app_name="宿舍报修管理系统",
        db_name="dorm_demo",
        schema_sql="('student', 'student123', 'student', '学生甲'",
        spec={"schema": {"roles": {"user": {"id": "student", "label": "学生"}}}},
    )
    text = (dest / "README.md").read_text(encoding="utf-8")
    assert "`student`" in text
    assert "`student123`" in text
    assert "学生" in text
    assert "${DEMO_" not in text
    assert "给学生" not in text
    assert "多数课题" not in text
