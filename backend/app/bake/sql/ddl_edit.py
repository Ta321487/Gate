"""SQL DDL 文本改写公共工具：CREATE 体补列/剔列/改名，INSERT 列清单同步。"""

from __future__ import annotations

import re
from collections.abc import Callable

CREATE_TABLE_RE = re.compile(
    r"(CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\()((?:.|\n)*?)(\);)",
    re.IGNORECASE,
)


def inject_missing_columns(body: str, columns: list[tuple[str, str]]) -> str:
    lower = body.lower()
    missing = [(name, ddl) for name, ddl in columns if name.lower() not in lower]
    if not missing:
        return body
    m = re.search(r"(?m)^(\s*created_at\b)", body)
    if m:
        # created_at 仍在后面：每一行都要逗号
        lines = [f"  {name} {ddl}," for name, ddl in missing]
        return body[: m.start()] + "\n".join(lines) + "\n" + body[m.start() :]
    # 追加到表尾：末列不得带逗号，否则 MySQL 1064 near ')'
    lines = [f"  {name} {ddl}," for name, ddl in missing[:-1]]
    last_name, last_ddl = missing[-1]
    lines.append(f"  {last_name} {last_ddl}")
    trimmed = body.rstrip()
    if not trimmed.endswith(","):
        trimmed += ","
    return trimmed + "\n" + "\n".join(lines) + "\n"


def strip_trailing_comma_before_close(body: str) -> str:
    """去掉 CREATE 体末尾多余逗号（补列/剔列后的兜底）。"""
    return re.sub(r",(\s*)$", r"\1", body.rstrip() + ("\n" if body.endswith("\n") else ""))


def prune_columns(body: str, *, allow: set[str], known: set[str]) -> str:
    """去掉 known 中不在 allow 的列定义。"""
    if not known:
        return body
    allow_l = {a.lower() for a in allow}
    known_l = {k.lower() for k in known}
    out: list[str] = []
    for line in body.splitlines(keepends=True):
        m = re.match(r"^(\s*)(\w+)\s+", line)
        if m:
            name = m.group(2).lower()
            if name in known_l and name not in allow_l:
                continue
        out.append(line)
    return strip_trailing_comma_before_close("".join(out))


def rewrite_col_def(body: str, old: str, new_name: str, new_ddl: str | None = None) -> str:
    """替换 CREATE 体中单列：可只改名保留原类型，或同时换 ddl。"""
    if new_ddl is None:
        pat = re.compile(
            rf"(?m)^(\s*){re.escape(old)}\s+([^,\n]+)(,)?\s*$",
            re.IGNORECASE,
        )

        def repl_keep(m: re.Match[str]) -> str:
            comma = m.group(3) or ""
            return f"{m.group(1)}{new_name} {m.group(2).rstrip()}{comma}"

        return pat.sub(repl_keep, body, count=1)

    pat = re.compile(
        rf"(?m)^(\s*){re.escape(old)}\s+[^,\n]+(,)?\s*$",
        re.IGNORECASE,
    )

    def repl(m: re.Match[str]) -> str:
        comma = m.group(2) or ""
        return f"{m.group(1)}{new_name} {new_ddl}{comma}"

    return pat.sub(repl, body, count=1)


def rewrite_insert_col_names(
    sql: str,
    table: str,
    rename: dict[str, str],
) -> str:
    """INSERT INTO table (...) 列清单按 rename（小写键）替换。"""
    if not rename:
        return sql
    mapping = {k.lower(): v for k, v in rename.items()}

    def repl(m: re.Match[str]) -> str:
        prefix, cols, suffix = m.group(1), m.group(2), m.group(3)
        parts = [p.strip() for p in cols.split(",")]
        new_parts = [mapping.get(p.lower(), p) for p in parts]
        return prefix + ", ".join(new_parts) + suffix

    return re.sub(
        rf"(INSERT\s+(?:IGNORE\s+)?INTO\s+`?{re.escape(table)}`?\s*\()([^)]+)(\))",
        repl,
        sql,
        flags=re.IGNORECASE,
    )


def map_create_table(
    sql: str,
    table: str,
    transform: Callable[[str], str],
) -> str:
    """对指定表的 CREATE 体做 transform。"""
    t = table.lower()

    def repl(m: re.Match[str]) -> str:
        head, name, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if name.lower() != t:
            return m.group(0)
        new_body = strip_trailing_comma_before_close(transform(body))
        return f"{head}{new_body}{tail}"

    return CREATE_TABLE_RE.sub(repl, sql)


def valid_ident(name: str | None) -> bool:
    s = (name or "").strip()
    return bool(s and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", s))
