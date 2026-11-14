"""出包依赖瘦身：声明了但本题用不到的 pom / yml / package.json 项裁掉。

关 AI 仍留 spring-ai、骨架常驻 lombok/validation/tinycolor → 论文会写成「用了」却零引用。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.bake.addons import resolve_ai_assistant

_DEP_BLOCK = re.compile(
    r"\s*<!--[^>]*-->\s*"
    r"<dependency>\s*"
    r"(?:(?!</dependency>).)*?"
    r"<artifactId>%s</artifactId>"
    r"(?:(?!</dependency>).)*?"
    r"</dependency>",
    re.DOTALL,
)

_DEP_BLOCK_PLAIN = re.compile(
    r"\s*<dependency>\s*"
    r"(?:(?!</dependency>).)*?"
    r"<artifactId>%s</artifactId>"
    r"(?:(?!</dependency>).)*?"
    r"</dependency>",
    re.DOTALL,
)

_BOM_IMPORT = re.compile(
    r"\s*<dependency>\s*"
    r"<groupId>org\.springframework\.ai</groupId>\s*"
    r"<artifactId>spring-ai-bom</artifactId>\s*"
    r"(?:(?!</dependency>).)*?"
    r"</dependency>",
    re.DOTALL,
)

_SPRING_AI_PROP = re.compile(r"\s*<spring-ai\.version>.*?</spring-ai\.version>\s*")

_DEP_MGMT_EMPTY = re.compile(
    r"\s*<dependencyManagement>\s*<dependencies>\s*</dependencies>\s*</dependencyManagement>\s*",
    re.DOTALL,
)

_SPRING_AI_YML = re.compile(
    r"(?m)^([ \t]*)#\s*AI 助手[^\n]*\n"
    r"(?:^[ \t]*ai:\n(?:^[ \t]+.*\n)+)?",
)

_SPRING_AI_YML_BARE = re.compile(
    r"(?m)^([ \t]*)ai:\n"
    r"(?:^[ \t]+.*\n)*?"
    r"(?=^[ \t]*(?:management|thesis|server|spring|mybatis|jpa|[a-z])|\Z)",
)


def _strip_pom_artifact(text: str, artifact_id: str) -> str:
    pat = re.compile(_DEP_BLOCK.pattern % re.escape(artifact_id), _DEP_BLOCK.flags)
    out = pat.sub("\n", text)
    if out == text:
        pat2 = re.compile(
            _DEP_BLOCK_PLAIN.pattern % re.escape(artifact_id), _DEP_BLOCK_PLAIN.flags
        )
        out = pat2.sub("\n", text)
    return out


def scrub_pom_unused_deps(pom_text: str, *, ai_on: bool) -> str:
    """去掉未使用的 Maven 依赖；AI 关则连 spring-ai 一起裁。"""
    text = pom_text
    for art in ("lombok", "spring-boot-starter-validation"):
        text = _strip_pom_artifact(text, art)
    if not ai_on:
        text = _strip_pom_artifact(text, "spring-ai-deepseek")
        text = _strip_pom_artifact(text, "spring-ai-starter-model-deepseek")
        text = _BOM_IMPORT.sub("\n", text)
        text = _SPRING_AI_PROP.sub("\n", text)
        text = _DEP_MGMT_EMPTY.sub("\n", text)
    # 压缩多余空行
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def scrub_application_yml_ai(yml_text: str, *, ai_on: bool) -> str:
    """AI 关：去掉 spring.ai / DeepSeek 配置块（thesis.ai-reply-polish 由 _patch_thesis_yml 管）。"""
    if ai_on:
        return yml_text
    text = _SPRING_AI_YML.sub("\n", yml_text)
    if "ai:\n" in text and "deepseek" in text.lower():
        text = _SPRING_AI_YML_BARE.sub("\n", text)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def scrub_package_json_unused(pkg_text: str) -> str:
    """去掉前端未引用的直声明依赖。"""
    try:
        data = json.loads(pkg_text)
    except (TypeError, ValueError):
        return pkg_text
    deps = data.get("dependencies")
    if not isinstance(deps, dict):
        return pkg_text
    changed = False
    for name in ("@ctrl/tinycolor",):
        if name in deps:
            deps.pop(name, None)
            changed = True
    if not changed:
        return pkg_text
    data["dependencies"] = deps
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def scrub_student_pack_deps(workspace: Path, spec: dict[str, Any] | None = None) -> list[str]:
    """对工作区执行依赖瘦身；返回改动摘要。"""
    workspace = Path(workspace)
    if spec is None:
        sp = workspace / "spec.json"
        if sp.is_file():
            spec = json.loads(sp.read_text(encoding="utf-8"))
        else:
            spec = {}
    assert isinstance(spec, dict)
    ai_on = resolve_ai_assistant(spec)
    notes: list[str] = []

    for rel in (
        "backend/pom.xml",
        # overlays 合并后只剩一份 pom；兼容误拷
    ):
        pom = workspace / rel
        if not pom.is_file():
            continue
        raw = pom.read_text(encoding="utf-8")
        new = scrub_pom_unused_deps(raw, ai_on=ai_on)
        if new != raw:
            pom.write_text(new, encoding="utf-8")
            notes.append(f"pom:scrub-unused(ai_on={ai_on})")

    yml = workspace / "backend" / "src" / "main" / "resources" / "application.yml"
    if yml.is_file():
        raw = yml.read_text(encoding="utf-8")
        new = scrub_application_yml_ai(raw, ai_on=ai_on)
        if new != raw:
            yml.write_text(new, encoding="utf-8")
            notes.append("yml:scrub-spring-ai")

    pkg = workspace / "frontend" / "package.json"
    if pkg.is_file():
        raw = pkg.read_text(encoding="utf-8")
        new = scrub_package_json_unused(raw)
        if new != raw:
            pkg.write_text(new, encoding="utf-8")
            notes.append("package.json:drop-tinycolor")

    return notes


def scan_dead_declared_deps(
    workspace: Path, spec: dict[str, Any] | None = None
) -> list[str]:
    """门禁：关 AI 仍声明 spring-ai；或 lombok/validation/tinycolor 仍直声明。"""
    workspace = Path(workspace)
    if spec is None:
        sp = workspace / "spec.json"
        if sp.is_file():
            spec = json.loads(sp.read_text(encoding="utf-8"))
        else:
            spec = {}
    assert isinstance(spec, dict)
    ai_on = resolve_ai_assistant(spec)
    hits: list[str] = []

    pom = workspace / "backend" / "pom.xml"
    if pom.is_file():
        txt = pom.read_text(encoding="utf-8")
        if "<artifactId>lombok</artifactId>" in txt:
            hits.append("pom:lombok")
        if "<artifactId>spring-boot-starter-validation</artifactId>" in txt:
            hits.append("pom:spring-boot-starter-validation")
        if not ai_on:
            if "spring-ai-deepseek" in txt or "spring-ai-starter-model-deepseek" in txt:
                hits.append("pom:spring-ai-deepseek(ai_off)")
            if "spring-ai-bom" in txt:
                hits.append("pom:spring-ai-bom(ai_off)")

    if not ai_on:
        yml = workspace / "backend" / "src" / "main" / "resources" / "application.yml"
        if yml.is_file():
            ytxt = yml.read_text(encoding="utf-8")
            if re.search(r"(?m)^\s*ai:\s*$", ytxt) and "deepseek" in ytxt.lower():
                hits.append("yml:spring.ai(ai_off)")

    pkg = workspace / "frontend" / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        deps = data.get("dependencies") if isinstance(data, dict) else None
        if isinstance(deps, dict) and "@ctrl/tinycolor" in deps:
            hits.append("package.json:@ctrl/tinycolor")

    return hits


# 库名允许连字符（测试 pid / 历史落盘），与 student_db_name 下划线语义并存
_DB_FROM_SQL = re.compile(
    r"(?i)create\s+database(?:\s+if\s+not\s+exists)?\s+`?([A-Za-z_][A-Za-z0-9_-]*)`?"
)
_DB_FROM_JDBC = re.compile(
    r"jdbc:mysql://[^/\s]+/([A-Za-z_][A-Za-z0-9_-]*)(?:\?|/|\s|$)"
)
_APP_JAVA = re.compile(r".*Application\.java$")


def scan_delivery_identity_issues(workspace: Path) -> list[str]:
    """库名三面一致 + 仅一个 Spring Boot 启动类。"""
    workspace = Path(workspace)
    hits: list[str] = []

    sql_path = workspace / "sql" / "schema.sql"
    yml_path = workspace / "backend" / "src" / "main" / "resources" / "application.yml"
    sql_db = ""
    yml_db = ""
    if sql_path.is_file():
        m = _DB_FROM_SQL.search(sql_path.read_text(encoding="utf-8"))
        sql_db = (m.group(1) if m else "").strip()
    if yml_path.is_file():
        m = _DB_FROM_JDBC.search(yml_path.read_text(encoding="utf-8"))
        yml_db = (m.group(1) if m else "").strip()
    if sql_db and yml_db and sql_db != yml_db:
        hits.append(f"db_mismatch:schema={sql_db},yml={yml_db}")
    elif sql_db and not yml_db:
        hits.append(f"db_missing:yml(expected={sql_db})")
    elif yml_db and not sql_db:
        hits.append(f"db_missing:schema(expected={yml_db})")

    if sql_db:
        readme = workspace / "README.md"
        if readme.is_file():
            rtxt = readme.read_text(encoding="utf-8")
            if sql_db not in rtxt:
                hits.append(f"db_missing:readme({sql_db})")

    java_root = workspace / "backend" / "src" / "main" / "java"
    pom = workspace / "backend" / "pom.xml"
    if java_root.is_dir():
        apps = sorted(p for p in java_root.rglob("*Application.java") if p.is_file())
        if len(apps) > 1:
            names = [p.relative_to(java_root).as_posix() for p in apps[:6]]
            hits.append("multi_application:" + ",".join(names))
        elif len(apps) == 0 and pom.is_file():
            # 完整学生包必有 pom；裁剪单测夹具常无启动类，勿误报
            hits.append("missing_application")

    return hits


_README_PHANTOM_TABLES = (
    "signup",
    "activity",
    "slot",
    "taste_note",
)


def scan_readme_schema_phantoms(workspace: Path) -> list[str]:
    """README 点名的表/列若不在 schema.sql → 论文素材不可用。"""
    from app.bake.engine_sql import list_create_table_names

    workspace = Path(workspace)
    readme = workspace / "README.md"
    sql_path = workspace / "sql" / "schema.sql"
    if not readme.is_file() or not sql_path.is_file():
        return []
    sql = sql_path.read_text(encoding="utf-8")
    tables = set(list_create_table_names(sql))
    sql_l = sql.lower()
    rtxt = readme.read_text(encoding="utf-8")
    hits: list[str] = []
    for name in _README_PHANTOM_TABLES:
        if name not in rtxt:
            continue
        if name == "taste_note":
            if "taste_note" not in sql_l:
                hits.append("readme:taste_note")
            continue
        if name not in tables:
            hits.append(f"readme:{name}")
    return hits
