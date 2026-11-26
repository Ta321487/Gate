"""论文「数据库逻辑设计 / 物理设计」正文导出。

真源：交付包 ``sql/schema.sql`` 经 ``load_schema_model`` 的表与列；
禁止编造表名、列名或外键。角色拆分逻辑实体（``role_of`` / ``sys_user:…``）不进物理清单。

行文对齐样例论文（柚子动漫周边）：
- 4.6.2 逻辑：``表名(属性、…)`` 一行一表；引言说明横线=主键、波浪线=外键
- 4.6.3 物理：``（n）表：…如表4.n所示`` + ``表4.n…`` + 制表符八列，可贴 Word 转表格
- HTML 表样式：校模板「三线 + 轻网格」（见 ``thesis_table_html``），与用例描述/测例同源
"""

from __future__ import annotations

import re
from typing import Any

from app.bake.schema.er_model import (
    _ER_SAMPLE_SHELL_TABLES,
    _is_sample_shell_table,
    apply_er_display_mode,
)
from app.bake.schema.thesis_table_html import (
    WORD_P as _WORD_P,
    html_body_inner,
    html_esc as _html_esc,
    rows_to_html_table as _rows_to_html_table,
    wrap_word_html as _wrap_word_html,
)

_CREATE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?",
    re.IGNORECASE,
)

# 物理表粘贴 Word「文本转换成表格」用；与样例列序一致
_PHYS_HEADER = ["序号", "列名", "说明", "数据类型", "长度", "允许空", "自增", "主外键"]


def physical_tables(model: dict[str, Any] | None) -> list[dict[str, Any]]:
    """物理表：仅 schema 真表，排除角色拆分框。"""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for t in (model or {}).get("tables") or []:
        if not isinstance(t, dict):
            continue
        name = str(t.get("name") or "").strip()
        if not name or name in seen:
            continue
        if t.get("role_of") or ":" in name:
            continue
        seen.add(name)
        out.append(t)
    return out


def parse_mysql_type(raw: str) -> tuple[str, str, str]:
    """返回 (base, len, full)。"""
    s = str(raw or "").strip()
    m = re.match(r"^(\w+)\s*(?:\(([^)]*)\))?", s, re.I)
    if not m:
        return s.lower(), "", s.lower()
    base = m.group(1).lower()
    length = (m.group(2) or "").replace(" ", "").strip()
    full = f"{base}({length})" if length else base
    return base, length, full


def _zh_table_name(table: dict[str, Any]) -> str:
    name = str(table.get("name") or "").strip()
    label = str(table.get("label") or name).strip() or name
    if label.endswith("表"):
        return label
    return f"{label}表"


def _logical_attr_plain(col: dict[str, Any]) -> str:
    name = str(col.get("name") or "").strip()
    return str(col.get("label") or name).strip() or name


def _logical_attr_marked(col: dict[str, Any], *, kind: str) -> str:
    """主键横线、外键波浪线。

    - ``md``：内嵌 HTML（``<u>`` / ``.thesis-fk``），下载 .md + markdown-it 预览
    - ``html``：内联 style，复制可贴 Word
    - ``plain``：无标记（text/plain 后备）
    不用 Unicode 组合字符（中文字体易变 □）。
    """
    label = _html_esc(_logical_attr_plain(col))
    plain = _logical_attr_plain(col)
    if kind == "plain":
        return plain
    if col.get("pk"):
        if kind == "html":
            return (
                f'<span style="text-decoration:underline;color:#000;'
                f'background:#fff">{label}</span>'
            )
        return f'<u class="thesis-pk">{label}</u>'
    if col.get("fk"):
        if kind == "html":
            return (
                f'<span style="text-decoration:underline wavy;color:#000;'
                f'background:#fff">{label}</span>'
            )
        return f'<span class="thesis-fk">{label}</span>'
    return label if kind != "plain" else plain


def _logical_tables(model: dict[str, Any] | None) -> list[dict[str, Any]]:
    """逻辑设计表序：论文概念实体对应物理表；藏壳表与纯中间表。"""
    raw = model if isinstance(model, dict) else {}
    phys = {str(t.get("name") or ""): t for t in physical_tables(raw)}
    sample = apply_er_display_mode(raw, "sample")
    names = [
        str(x).strip()
        for x in (sample.get("conceptual_entities") or [])
        if str(x).strip() and str(x).strip() in phys
    ]
    if not names:
        for t in physical_tables(sample):
            name = str(t.get("name") or "")
            if t.get("assoc_link") or _is_sample_shell_table(name):
                continue
            names.append(name)
    return [phys[n] for n in names if n in phys]


def _logical_intro() -> str:
    return (
        "数据库中对逻辑结构进行设计，先需要进行E-R图的绘制，通过绘制E-R图将E-R图转化为"
        "DBMS所接受的数据模型的逻辑结构，E-R图中逻辑结构如下所示，"
        "带有波浪线为外键，带有横线为主键。"
    )


def _render_logical_lines(model: dict[str, Any] | None, *, kind: str) -> list[str]:
    tables = _logical_tables(model)
    lines: list[str] = [
        "4.6.2  数据库逻辑设计",
        _logical_intro(),
    ]
    for t in tables:
        cols = [c for c in (t.get("columns") or []) if isinstance(c, dict) and c.get("name")]
        attrs = (
            "、".join(_logical_attr_marked(c, kind=kind) for c in cols) if cols else "（无列）"
        )
        # 表名在 md/html 里也 escape
        zh = _zh_table_name(t)
        if kind != "plain":
            zh = _html_esc(zh)
        lines.append(f"{zh}({attrs})")
    return lines


def render_logical_design(model: dict[str, Any] | None) -> str:
    """4.6.2 逻辑设计纯文本（无下划线标记，作 text/plain）。"""
    return "\n".join(_render_logical_lines(model, kind="plain")).rstrip() + "\n"


def _mark_yn(ok: bool) -> str:
    return "√" if ok else "×"


def _pk_fk_cell(col: dict[str, Any]) -> str:
    if col.get("pk"):
        return "主键"
    if col.get("fk"):
        return "外键"
    return "×"


def _phys_col_rows(table: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = [_PHYS_HEADER]
    for i, c in enumerate(table.get("columns") or [], start=1):
        if not isinstance(c, dict):
            continue
        name = str(c.get("name") or "").strip()
        if not name:
            continue
        label = str(c.get("label") or name).strip() or name
        base, length, _full = parse_mysql_type(str(c.get("type") or ""))
        # 主键默认非空；与样例「允许空 / 自增」同源列约束，不臆造
        not_null = bool(c.get("not_null")) or bool(c.get("pk"))
        auto_inc = bool(c.get("auto_increment"))
        rows.append(
            [
                str(i),
                name,
                label,
                base,
                length,
                _mark_yn(not not_null),  # 允许空
                _mark_yn(auto_inc),
                _pk_fk_cell(c),
            ]
        )
    return rows


def _table_purpose(table: dict[str, Any]) -> str:
    label = str(table.get("label") or table.get("name") or "本").strip()
    if label.endswith("表"):
        label = label[:-1]
    return f"用来存储{label}的相关信息"


def _ordered_physical_tables(
    model: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    tables = physical_tables(model)
    biz = [t for t in tables if not _is_sample_shell_table(str(t.get("name") or ""))]
    shells = [t for t in tables if _is_sample_shell_table(str(t.get("name") or ""))]
    return biz + shells, biz, shells


def _physical_intro(
    *,
    db_name: str,
    ordered: list[dict[str, Any]],
    biz: list[dict[str, Any]],
    shells: list[dict[str, Any]],
) -> str:
    n = len(ordered)
    db = (db_name or "").strip() or "本系统"
    main_names = "、".join(_zh_table_name(t) for t in biz[:8])
    if len(biz) > 8:
        main_names += "等"
    elif not main_names:
        main_names = "业务数据表"
    return (
        f"考虑到{db}的数据存储需求，最终选定 MySQL 作为数据库系统。"
        "MySQL 具备传输速度快、性能优越等特点，能够很好地满足系统运行需要。"
        f"围绕不同功能模块，共设计 {n} 张数据表"
        f"（业务表{len(biz)}张"
        + (f"，辅助表{len(shells)}张" if shells else "")
        + f"），主要包括：{main_names}。"
        "以下表结构均来自交付包 sql/schema.sql，未增删表或字段。表格的结构如下"
    )


def render_physical_design(
    model: dict[str, Any] | None,
    *,
    db_name: str = "",
    type_paren: bool = True,
) -> str:
    """4.6.3 物理设计纯文本（制表符）；预览/粘贴 Word 优先用 HTML 版。"""
    del type_paren
    ordered, biz, shells = _ordered_physical_tables(model)
    lines: list[str] = [
        "4.6.3  数据库物理设计",
        _physical_intro(db_name=db_name, ordered=ordered, biz=biz, shells=shells),
        "",
    ]
    for i, t in enumerate(ordered, start=1):
        zh = _zh_table_name(t)
        en = str(t.get("name") or "")
        shell = "（辅助表）" if _is_sample_shell_table(en) else ""
        lines.append(f"（{i}）{zh}：{_table_purpose(t)}，如表4.{i}所示。{shell}")
        lines.append(f"表4.{i} {zh}{en}")
        rows = _phys_col_rows(t)
        lines.append("\n".join("\t".join(r) for r in rows))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_physical_design_html(
    model: dict[str, Any] | None,
    *,
    db_name: str = "",
) -> str:
    """4.6.3 物理设计 HTML：校模板三线+轻网格，复制可贴 Word 成表。"""
    ordered, biz, shells = _ordered_physical_tables(model)
    parts: list[str] = [
        f'<p style="{_WORD_P}"><b>4.6.3  数据库物理设计</b></p>',
        f'<p style="{_WORD_P}">{_html_esc(_physical_intro(db_name=db_name, ordered=ordered, biz=biz, shells=shells))}</p>',
    ]
    for i, t in enumerate(ordered, start=1):
        zh = _zh_table_name(t)
        en = str(t.get("name") or "")
        shell = "（辅助表）" if _is_sample_shell_table(en) else ""
        parts.append(
            f'<p style="{_WORD_P}">（{i}）{_html_esc(zh)}：{_html_esc(_table_purpose(t))}，'
            f"如表4.{i}所示。{_html_esc(shell)}</p>"
        )
        parts.append(
            f'<p style="{_WORD_P};text-align:center"><b>表4.{i} {_html_esc(zh)}{_html_esc(en)}</b></p>'
        )
        parts.append(_rows_to_html_table(_phys_col_rows(t)))
    return _wrap_word_html("\n".join(parts))


def render_logical_design_html(model: dict[str, Any] | None) -> str:
    """逻辑设计 HTML：主键下划线、外键波浪线；白底黑字可贴 Word。"""
    lines = _render_logical_lines(model, kind="html")
    if not lines:
        return ""
    parts = [f'<p style="{_WORD_P}"><b>{_html_esc(lines[0])}</b></p>']
    # 引言纯文本；其后行已含标记 span，不可再整体 escape
    parts.append(f'<p style="{_WORD_P}">{_html_esc(lines[1])}</p>')
    for ln in lines[2:]:
        parts.append(f'<p style="{_WORD_P}">{ln}</p>')
    return _wrap_word_html("\n".join(parts))


def _md_cell(s: str) -> str:
    return str(s or "").replace("|", "\\|").replace("\n", " ").strip()


def _rows_to_md_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    head, *body = rows
    line = "| " + " | ".join(_md_cell(c) for c in head) + " |"
    sep = "| " + " | ".join("---" for _ in head) + " |"
    out = [line, sep]
    for r in body:
        cells = list(r) + [""] * max(0, len(head) - len(r))
        out.append("| " + " | ".join(_md_cell(c) for c in cells[: len(head)]) + " |")
    return "\n".join(out)


def render_logical_design_md(model: dict[str, Any] | None) -> str:
    """逻辑设计 Markdown：内嵌 <u>/<span class=thesis-fk>，下载与预览同源。"""
    lines = _render_logical_lines(model, kind="md")
    if not lines:
        return ""
    parts = [f"## {lines[0]}", "", lines[1], ""]
    for ln in lines[2:]:
        parts.append(ln)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def render_physical_design_md(
    model: dict[str, Any] | None,
    *,
    db_name: str = "",
) -> str:
    """物理设计 Markdown 表（下载用；复制 Word 仍走 HTML）。"""
    ordered, biz, shells = _ordered_physical_tables(model)
    parts: list[str] = [
        "## 4.6.3  数据库物理设计",
        "",
        _physical_intro(db_name=db_name, ordered=ordered, biz=biz, shells=shells),
        "",
    ]
    for i, t in enumerate(ordered, start=1):
        zh = _zh_table_name(t)
        en = str(t.get("name") or "")
        shell = "（辅助表）" if _is_sample_shell_table(en) else ""
        parts.append(f"（{i}）{zh}：{_table_purpose(t)}，如表4.{i}所示。{shell}")
        parts.append("")
        parts.append(f"**表4.{i} {zh}{en}**")
        parts.append("")
        parts.append(_rows_to_md_table(_phys_col_rows(t)))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def schema_table_summary(model: dict[str, Any] | None) -> dict[str, Any]:
    """物理全量 vs 业务/辅助 vs 概念实体：供产物页分开展示，禁止混用 6～15。"""
    tables = physical_tables(model)
    shells = [
        str(t.get("name") or "")
        for t in tables
        if _is_sample_shell_table(str(t.get("name") or ""))
    ]
    biz_n = len(tables) - len(shells)
    conceptual = [
        str(x)
        for x in ((model or {}).get("conceptual_entities") or [])
        if str(x).strip()
    ]
    comfort_n = len(conceptual) if conceptual else biz_n
    comfort_min, comfort_max = 6, 15
    return {
        "physical": len(tables),
        "business": biz_n,
        "shell": len(shells),
        "shell_tables": shells,
        "conceptual": len(conceptual),
        "comfort_n": comfort_n,
        "comfort_min": comfort_min,
        "comfort_max": comfort_max,
        "comfort_ok": comfort_min <= comfort_n <= comfort_max,
        "comfort_basis": "conceptual" if conceptual else "business",
    }


def render_thesis_db_export(
    model: dict[str, Any] | None,
    *,
    db_name: str = "",
    type_paren: bool = True,
) -> dict[str, Any]:
    from app.bake.schema.zh_copy import squeeze_cjk_alnum_spaces

    tables = physical_tables(model)
    summary = schema_table_summary(model)
    shells = list(summary.get("shell_tables") or [])
    logical = squeeze_cjk_alnum_spaces(render_logical_design(model))
    physical = squeeze_cjk_alnum_spaces(
        render_physical_design(model, db_name=db_name, type_paren=type_paren)
    )
    logical_html = squeeze_cjk_alnum_spaces(render_logical_design_html(model))
    physical_html = squeeze_cjk_alnum_spaces(
        render_physical_design_html(model, db_name=db_name)
    )
    logical_md = squeeze_cjk_alnum_spaces(render_logical_design_md(model))
    physical_md = squeeze_cjk_alnum_spaces(
        render_physical_design_md(model, db_name=db_name)
    )
    combined = logical.rstrip() + "\n\n" + physical
    combined_html = _wrap_word_html(
        html_body_inner(logical_html) + "\n" + html_body_inner(physical_html)
    )
    combined_md = logical_md.rstrip() + "\n\n" + physical_md
    return {
        "logical": logical,
        "physical": physical,
        "combined": combined,
        "logical_html": logical_html,
        "physical_html": physical_html,
        "combined_html": squeeze_cjk_alnum_spaces(combined_html),
        "logical_md": logical_md,
        "physical_md": physical_md,
        "combined_md": combined_md,
        "table_count": len(tables),
        "shell_tables": shells,
        "table_names": [str(t.get("name") or "") for t in tables],
        "shell_table_names": list(_ER_SAMPLE_SHELL_TABLES),
        "table_summary": summary,
    }


def sql_table_names(sql: str) -> set[str]:
    return {m.group(1) for m in _CREATE_RE.finditer(sql or "")}


def assert_export_homology(
    export: dict[str, Any],
    *,
    sql: str,
) -> None:
    """导出表名必须 ⊆ schema.sql；禁止出现 role 逻辑名。"""
    sql_names = sql_table_names(sql)
    names = [str(x) for x in (export.get("table_names") or [])]
    if not names:
        raise AssertionError("thesis db export has no tables")
    extra = [n for n in names if n not in sql_names]
    if extra:
        raise AssertionError(f"export invents tables not in sql: {extra[:20]}")
    for n in names:
        if ":" in n:
            raise AssertionError(f"export must not include role entity: {n}")
