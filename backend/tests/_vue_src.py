"""骨架 Vue 拆分后合读：.vue + 同名 .setup.js + .css（若存在）。"""

from __future__ import annotations

from pathlib import Path


def vue_src(path: Path) -> str:
    """读页面源码；已外提 setup/css 时拼接，避免断言假绿。"""
    p = Path(path)
    parts = [p.read_text(encoding="utf-8")]
    setup = p.with_name(f"{p.stem}.setup.js")
    if setup.is_file():
        parts.append(setup.read_text(encoding="utf-8"))
    css = p.with_name(f"{p.stem}.css")
    if css.is_file():
        parts.append(css.read_text(encoding="utf-8"))
    return "".join(parts)
