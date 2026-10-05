"""bake 出包：禁止用 JSON / 逗号串装业务规则。"""

from __future__ import annotations

from pathlib import Path

from app.bake.gates.schema_nf import (
    assert_schema_nf,
    find_forbidden_add_column_json,
    find_schema_nf_issues,
)

REPO = Path(__file__).resolve().parents[2]
BAKE = REPO / "backend" / "app" / "bake"
SKEL_JAVA = (
    REPO / "skeletons" / "baseline" / "backend" / "src" / "main" / "java",
    REPO / "skeletons" / "overlays" / "persistence-jpa" / "backend" / "src" / "main" / "java",
    REPO / "skeletons" / "overlays" / "persistence-mybatis" / "backend" / "src" / "main" / "java",
)


def test_allowlist_json_passes() -> None:
    sql = """
CREATE TABLE IF NOT EXISTS sys_user (
  username VARCHAR(64) PRIMARY KEY,
  profile_json VARCHAR(2048) DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS archive_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  payload_json TEXT
);
CREATE TABLE IF NOT EXISTS book (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  gallery_json TEXT NULL
);
"""
    assert find_schema_nf_issues(sql) == []
    assert_schema_nf(sql)


def test_business_json_fails() -> None:
    sql = """
CREATE TABLE IF NOT EXISTS ticket (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  rating_dims_json VARCHAR(1024) DEFAULT '',
  companion_names VARCHAR(255) DEFAULT ''
);
"""
    issues = find_schema_nf_issues(sql)
    assert any("rating_dims_json" in i for i in issues)
    assert any("companion_names" in i for i in issues)


def test_bake_sql_sources_have_no_forbidden_json() -> None:
    bad: list[str] = []
    roots = [
        BAKE / "sql" / "templates",
        BAKE / "sql" / "fragments.py",
        BAKE / "sql" / "ticket_optional_columns.py",
        BAKE / "features",
    ]
    for root in roots:
        paths = [root] if root.is_file() else list(root.rglob("*"))
        for path in paths:
            if not path.is_file() or path.suffix not in {".sql", ".py"}:
                continue
            text = path.read_text(encoding="utf-8")
            issues = find_schema_nf_issues(text)
            if issues:
                bad.append(f"{path.relative_to(REPO)}: {issues[0]}")
    assert not bad, "bake SQL 含非白名单 JSON/逗号集合列:\n" + "\n".join(bad[:20])


def test_skeletons_do_not_alter_add_business_json() -> None:
    bad: list[str] = []
    for root in SKEL_JAVA:
        if not root.is_dir():
            continue
        for path in root.rglob("*.java"):
            hits = find_forbidden_add_column_json(path.read_text(encoding="utf-8"))
            for col in hits:
                bad.append(f"{path.relative_to(REPO)}: ADD COLUMN {col}")
    assert not bad, "骨架不得 ALTER 补业务 JSON 列:\n" + "\n".join(bad[:20])
