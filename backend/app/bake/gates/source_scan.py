"""门禁扫源码前去注释（evaluate / semantic 共用，避免两套口径）。"""

from __future__ import annotations

import re

_VUE_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_VUE_LINE_COMMENT_RE = re.compile(r"(?<!:)//.*?$", re.M)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def strip_vue_comments(text: str) -> str:
    """去掉 HTML / 块注释 / 行注释（``://`` 不误伤）。"""
    t = _VUE_BLOCK_COMMENT_RE.sub(" ", text)
    t = _HTML_COMMENT_RE.sub(" ", t)
    t = _VUE_LINE_COMMENT_RE.sub(" ", t)
    return t


def strip_js_comments(text: str) -> str:
    """扫 JS 展示字符串前去掉注释。"""
    t = _VUE_BLOCK_COMMENT_RE.sub(" ", text)
    t = _VUE_LINE_COMMENT_RE.sub(" ", t)
    return t
