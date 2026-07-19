"""学生项目库：按 workspace/sql/schema.sql 建库建表（幂等）。"""

from __future__ import annotations

import re
from pathlib import Path

import pymysql

from app.core.config import get_settings

_CREATE_TABLE_RE = re.compile(
    r"^CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\((.*)\)\s*$",
    re.IGNORECASE | re.DOTALL,
)
_COL_LINE_RE = re.compile(r"^`?(\w+)`?\s+(.+)$", re.IGNORECASE)
_SKIP_TABLE_LINE = re.compile(
    r"^(PRIMARY\s+KEY|UNIQUE|KEY|INDEX|CONSTRAINT|FOREIGN\s+KEY|CHECK)\b",
    re.IGNORECASE,
)


def _split_sql(script: str) -> list[str]:
    """去掉注释后按分号切语句。"""
    lines: list[str] = []
    for line in script.splitlines():
        s = line.strip()
        if s.startswith("--"):
            continue
        lines.append(line)
    text = "\n".join(lines)
    parts = [p.strip() for p in re.split(r";\s*\n", text) if p.strip()]
    out: list[str] = []
    for p in parts:
        p = p.strip().rstrip(";").strip()
        if p:
            out.append(p)
    return out


def _read_sql_text(path: Path) -> str:
    """读 schema.sql；优先 UTF-8，兼容被错误编码写坏的历史文件。"""
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    # 最后兜底：替换非法字节，避免启动整条链路崩溃
    return raw.decode("utf-8", errors="replace")


def _parse_create_columns(stmt: str) -> tuple[str, list[tuple[str, str]]] | None:
    """从 CREATE TABLE 抽出 (表名, [(列名, 列定义)...])。"""
    m = _CREATE_TABLE_RE.match(stmt.strip())
    if not m:
        return None
    table, body = m.group(1), m.group(2)
    cols: list[tuple[str, str]] = []
    for raw in body.split("\n"):
        line = raw.strip().rstrip(",").strip()
        if not line or _SKIP_TABLE_LINE.match(line):
            continue
        cm = _COL_LINE_RE.match(line)
        if not cm:
            continue
        cols.append((cm.group(1), cm.group(2).strip()))
    return table, cols


def _ensure_table_columns(cur, db_name: str, table: str, columns: list[tuple[str, str]]) -> None:
    """旧库 CREATE IF NOT EXISTS 会跳过建表；按 schema 定义补齐缺失列。"""
    cur.execute(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
        (db_name, table),
    )
    existing = {row[0] for row in cur.fetchall()}
    if not existing:
        return
    for cname, cdef in columns:
        if cname in existing:
            continue
        try:
            cur.execute(f"ALTER TABLE `{db_name}`.`{table}` ADD COLUMN `{cname}` {cdef}")
            existing.add(cname)
        except Exception:  # noqa: BLE001
            # 并发/已存在/不兼容类型：忽略，后续 INSERT 仍会暴露真实问题
            pass


def ensure_student_schema(workspace: Path, db_name: str) -> None:
    """连接本机 MySQL，执行项目 schema.sql。失败抛 RuntimeError。"""
    if not db_name or not re.match(r"^[a-zA-Z0-9_]+$", db_name):
        raise RuntimeError(f"非法库名: {db_name!r}")
    schema_path = workspace / "sql" / "schema.sql"
    if not schema_path.exists():
        raise RuntimeError(f"缺少 {schema_path}")

    settings = get_settings()
    script = _read_sql_text(schema_path)
    # 若 bake 后库名与文件内不一致，以项目 db_name 为准
    if f"`{db_name}`" not in script and "CREATE DATABASE" in script:
        script = re.sub(
            r"CREATE DATABASE IF NOT EXISTS `[^`]+`",
            f"CREATE DATABASE IF NOT EXISTS `{db_name}`",
            script,
            count=1,
        )
        script = re.sub(r"USE `[^`]+`", f"USE `{db_name}`", script, count=1)

    try:
        conn = pymysql.connect(
            host=settings.gf_student_mysql_host,
            port=settings.gf_student_mysql_port,
            user=settings.gf_student_mysql_user,
            password=settings.gf_student_mysql_password,
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=5,
        )
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            f"无法连接学生 MySQL "
            f"({settings.gf_student_mysql_user}@{settings.gf_student_mysql_host}:"
            f"{settings.gf_student_mysql_port}): {e}"
        ) from e

    try:
        with conn.cursor() as cur:
            for stmt in _split_sql(script):
                parsed = _parse_create_columns(stmt)
                cur.execute(stmt)
                # 必须在 INSERT 之前补列，否则旧表缺 start_at 等会 1054
                if parsed:
                    table, columns = parsed
                    _ensure_table_columns(cur, db_name, table, columns)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"执行 schema.sql 失败: {e}") from e
    finally:
        conn.close()


def datasource_env(db_name: str) -> dict[str, str]:
    """注入 Spring Boot 数据源环境变量。"""
    settings = get_settings()
    url = (
        f"jdbc:mysql://{settings.gf_student_mysql_host}:{settings.gf_student_mysql_port}/"
        f"{db_name}?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai"
        f"&allowPublicKeyRetrieval=true&useSSL=false"
    )
    return {
        "SPRING_DATASOURCE_URL": url,
        "SPRING_DATASOURCE_USERNAME": settings.gf_student_mysql_user,
        "SPRING_DATASOURCE_PASSWORD": settings.gf_student_mysql_password,
        "DB_NAME": db_name,
    }


_SAFE_DB_NAME = re.compile(r"^[a-zA-Z0-9_]+$")
_STUDENT_DB_PREFIX = "gf_thesis_"


def drop_student_database(db_name: str) -> None:
    """删除学生项目库。仅允许 gf_thesis_* 库名；失败抛 RuntimeError。"""
    if not db_name or not _SAFE_DB_NAME.match(db_name):
        raise RuntimeError(f"非法库名: {db_name!r}")
    if not db_name.startswith(_STUDENT_DB_PREFIX):
        raise RuntimeError(f"拒绝删除非学生库: {db_name!r}")

    settings = get_settings()
    try:
        conn = pymysql.connect(
            host=settings.gf_student_mysql_host,
            port=settings.gf_student_mysql_port,
            user=settings.gf_student_mysql_user,
            password=settings.gf_student_mysql_password,
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=5,
        )
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            f"无法连接学生 MySQL "
            f"({settings.gf_student_mysql_user}@{settings.gf_student_mysql_host}:"
            f"{settings.gf_student_mysql_port}): {e}"
        ) from e

    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"删除库 {db_name} 失败: {e}") from e
    finally:
        conn.close()
