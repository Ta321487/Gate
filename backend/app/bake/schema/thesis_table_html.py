"""论文材料表 HTML：校模板常见「三线 + 轻网格」。

口径（与多数学校 Word 模板粘出的表一致）：
- 表顶、表头下、表底：粗横线
- 数据行间、竖向分隔：细线
- 白底黑字、宋体；禁止 ``border="1"`` 全框线（Word 会压成杂表）

仅服务论文材料导出 / 粘贴 Word，不进学生包业务 UI。
"""

from __future__ import annotations

import re
from typing import Literal

THICK = "1.5pt solid #000"
THIN = "0.5pt solid #000"

WORD_P = (
    "margin:0 0 8pt;color:#000;background:#fff;"
    "font-size:12pt;font-family:宋体,SimSun,serif;line-height:1.5;"
)

WORD_TABLE = (
    "border-collapse:collapse;border:none;width:100%;"
    "font-size:10.5pt;font-family:宋体,SimSun,serif;color:#000;background:#fff;"
    "margin:0 0 12pt;"
)

Align = Literal["left", "center", "right"]


def html_esc(s: str) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _cell_border_css(*, is_header_row: bool, is_first_row: bool, is_last_row: bool) -> str:
    top = THICK if (is_header_row or is_first_row) else THIN
    if is_header_row:
        bottom = THICK
    elif is_last_row:
        bottom = THICK
    else:
        bottom = THIN
    return (
        f"border-top:{top};border-bottom:{bottom};"
        f"border-left:{THIN};border-right:{THIN};"
    )


def th_style(
    *,
    is_header_row: bool = True,
    is_first_row: bool = True,
    is_last_row: bool = False,
    align: Align = "center",
    nowrap: bool = True,
    width: str = "",
    font_size: str = "10.5pt",
) -> str:
    parts = [
        _cell_border_css(
            is_header_row=is_header_row,
            is_first_row=is_first_row,
            is_last_row=is_last_row,
        ),
        "padding:4pt 6pt;vertical-align:middle;",
        f"text-align:{align};font-weight:bold;color:#000;background:#fff;",
        f"font-size:{font_size};font-family:宋体,SimSun,serif;",
    ]
    if nowrap:
        parts.append("white-space:nowrap;")
    if width:
        parts.append(f"width:{width};")
    return "".join(parts)


def td_style(
    *,
    is_header_row: bool = False,
    is_first_row: bool = False,
    is_last_row: bool = False,
    align: Align = "center",
    font_size: str = "10.5pt",
    vertical: str = "middle",
) -> str:
    return (
        _cell_border_css(
            is_header_row=is_header_row,
            is_first_row=is_first_row,
            is_last_row=is_last_row,
        )
        + f"padding:4pt 6pt;vertical-align:{vertical};text-align:{align};"
        + "font-weight:normal;color:#000;background:#fff;"
        + f"font-size:{font_size};font-family:宋体,SimSun,serif;"
    )


def table_open(*, font_size: str = "10.5pt") -> str:
    style = WORD_TABLE.replace("font-size:10.5pt", f"font-size:{font_size}")
    return f'<table border="0" cellspacing="0" cellpadding="0" style="{style}">'


def rows_to_html_table(
    rows: list[list[str]],
    *,
    td_align: Align = "center",
    th_align: Align = "center",
    font_size: str = "10.5pt",
    escape: bool = True,
) -> str:
    """首行表头的网格表（测例 / 物理设计等）。"""
    if not rows:
        return ""
    head, *body = rows
    th_css = th_style(font_size=font_size, align=th_align)
    th = "".join(
        f'<th style="{th_css}">{html_esc(c) if escape else c}</th>' for c in head
    )
    trs = [f"<tr>{th}</tr>"]
    n = len(body)
    for i, r in enumerate(body):
        last = i == n - 1
        td_css = td_style(is_last_row=last, align=td_align, font_size=font_size)
        tds = "".join(
            f'<td style="{td_css}">{html_esc(c) if escape else c}</td>' for c in r
        )
        trs.append(f"<tr>{tds}</tr>")
    return table_open(font_size=font_size) + "".join(trs) + "</table>"


def kv_rows_to_html_table(
    pairs: list[tuple[str, str]],
    *,
    label_width: str = "88pt",
    font_size: str = "12pt",
    value_align: Align = "left",
) -> str:
    """左右「字段名 | 内容」表（用例描述表）。无独立表头行：仅顶/底粗线 + 轻网格。"""
    if not pairs:
        return ""
    trs: list[str] = []
    n = len(pairs)
    for i, (label, value) in enumerate(pairs):
        first = i == 0
        last = i == n - 1
        th_css = th_style(
            is_header_row=False,
            is_first_row=first,
            is_last_row=last,
            align="center",
            width=label_width,
            font_size=font_size,
        )
        td_css = td_style(
            is_first_row=first,
            is_last_row=last,
            align=value_align,
            font_size=font_size,
            vertical="top",
        )
        trs.append(
            f"<tr><th style=\"{th_css}\">{html_esc(label)}</th>"
            f'<td style="{td_css}">{value}</td></tr>'
        )
    return table_open(font_size=font_size) + "<tbody>" + "".join(trs) + "</tbody></table>"


def wrap_word_html(inner: str) -> str:
    """整页白底黑字，避免粘贴时吃到工厂深色容器样式。"""
    return (
        "<html><head><meta charset=\"utf-8\"></head>"
        '<body style="color:#000;background:#fff;margin:12pt;">'
        f"{inner}</body></html>"
    )


_BODY_INNER_RE = re.compile(r"<body[^>]*>(.*)</body>", re.I | re.S)


def html_body_inner(doc: str) -> str:
    """预览用：去掉 html/body 壳，只取正文。"""
    s = str(doc or "")
    m = _BODY_INNER_RE.search(s)
    return (m.group(1) if m else s).strip()
