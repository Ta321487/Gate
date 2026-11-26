"""论文图统一字体：一篇论文里所有图共用一套（禁止各图各字体）。

- 中文正文/图内文字：宋体（SimSun；macOS 回退 Songti SC）。参考往届样例，图内均为宋体、字号偏小。
- 西文/数字：宋体自带西文字形与 Times 同族，直接跟在 SimSun 后面即可，不另立字体。
- 代码行（类图属性/方法）：保留等宽，读代码更清楚。

图注一律写 Word（图内不画标题），字体只管 font-family，不管字号。
"""

from __future__ import annotations

FONT_CN = "SimSun, Songti SC, Times New Roman, serif"
FONT_TECH = "Times New Roman, SimSun, serif"
FONT_MONO = "Consolas, Courier New, monospace"

__all__ = ["FONT_CN", "FONT_MONO", "FONT_TECH"]
