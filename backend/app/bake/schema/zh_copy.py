"""学生可见论文/材料中文句：数字与字母两侧不留空格。

例：表 3.1 → 表3.1；见表 3.1 所示 → 见表3.1所示；共设计 12 张 → 共设计12张；
使用 Vue 框架 → 使用Vue框架。拉丁词之间空格保留（Spring Boot）。
"""

from __future__ import annotations

import re
from typing import Any

_CJK = r"\u4e00-\u9fff"
_ALNUM = r"A-Za-z0-9"


def squeeze_cjk_alnum_spaces(text: str) -> str:
    """去掉汉字与拉丁字母/数字之间的空格（含小数点编号两侧）。"""
    t = text or ""
    t = re.sub(rf"([{_CJK}])[ \t]+(?=[{_ALNUM}])", r"\1", t)
    t = re.sub(rf"([{_ALNUM}.])[ \t]+(?=[{_CJK}])", r"\1", t)
    return t


def squeeze_material(value: Any) -> Any:
    """递归：str 贴边；list/tuple/dict 深入；其余原样。用于出稿末段。"""
    if isinstance(value, str):
        return squeeze_cjk_alnum_spaces(value)
    if isinstance(value, list):
        return [squeeze_material(x) for x in value]
    if isinstance(value, tuple):
        return tuple(squeeze_material(x) for x in value)
    if isinstance(value, dict):
        return {k: squeeze_material(v) for k, v in value.items()}
    return value
