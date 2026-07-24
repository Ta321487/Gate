"""开题解析共用词表（唯一来源；提示词勿再抄长规则）。"""

from __future__ import annotations

import re

FEATURE_HEAD_TERMS = (
    # 勿用光杆「系统实现」：开题「研究内容→（3）系统实现」是技术栈小节，
    # 会吞掉后续功能需求段（焦点最多 3500 字），导致商城等题只剩标题词。
    r"主要功能|功能需求|功能模块|功能清单|实现内容|系统功能|核心功能|"
    r"拟实现(?:功能)?|主要任务|任务与要求|实现下列功能|答辩必演示"
)
NEGATION_TERMS = (
    r"不要求|不实现|不做|不作为|不纳入|不属于|不扩展|不包含|不包括|不含|不以|"
    r"不涉及|不对接|不绑定|无需|不必|"
    r"仅作展望|仅参考|非本课题|本期不|范围外|不强制|非必交|非必演示|不作为必|"
    r"非本期|不在本期|不做范围|并非|"
    # 「非传染病晨检」：仅左侧前缀用；右侧见 RIGHT_NEGATION_TERMS
    r"非(?!常|法|洲|遗|物质)"
)
# 右侧「先提能力再写本期不」：不含光杆「非」，避免「物资领用，非公卫上报」误杀
RIGHT_NEGATION_TERMS = (
    r"不要求|不实现|不做|不作为|不纳入|不属于|不扩展|不包含|不包括|不含|不以|"
    r"不涉及|不对接|不绑定|无需|不必|"
    r"仅作展望|仅参考|非本课题|本期不|范围外|不强制|非必交|非必演示|不作为必|"
    r"非本期|不在本期|不做范围|并非"
)
# 对比/扩展语境：关键词出现在「容易涉及的扩展」里，不应抬升拟实现主路径
CONTRAST_TERMS = (
    r"扩展性|扩展能力|背景对比|仅作对比|作为对比|未来展望|调研阶段|"
    r"容易将|容易出现|往往超出|超出.{0,8}规模|庞大模块|商业属性|"
    r"再扩展|分阶段交付|先实现单仓|后续扩展|可作为后续|"
    r"商业方案|商业系统|三甲医院|大型单位|功能完善|功能完整|实施成本|"
    r"本科毕设适合|本科.*?聚焦|本科.*?即可|本科.*?不做"
)

FEATURE_HEAD_RE = re.compile(rf"({FEATURE_HEAD_TERMS})")
RESEARCH_WITH_IMPL_RE = re.compile(r"研究内容.{0,12}拟实现|拟实现.{0,12}功能")
OUT_HEAD_RE = re.compile(rf"({NEGATION_TERMS})")
NEGATION_RE = re.compile(rf"(?:{NEGATION_TERMS})")
RIGHT_NEGATION_RE = re.compile(rf"(?:{RIGHT_NEGATION_TERMS})")
CONTRAST_RE = re.compile(rf"(?:{CONTRAST_TERMS})")

_CLAUSE_SEPS = ("。", "；", ";", "！", "!", "？", "?", "\n")


def _left_clause(text: str) -> str:
    """取最近分句边界之后的左侧片段。"""
    cut = -1
    for sep in _CLAUSE_SEPS:
        i = text.rfind(sep)
        if i >= 0:
            cut = max(cut, i)
    return text[cut + 1 :] if cut >= 0 else text


def _right_clause(text: str) -> str:
    """取最近分句边界之前的右侧片段。"""
    cut = len(text)
    for sep in _CLAUSE_SEPS:
        i = text.find(sep)
        if i >= 0:
            cut = min(cut, i)
    return text[:cut]


def keyword_mentioned(
    text: str,
    kw: str,
    *,
    window: int = 48,
    ignore_contrast: bool = False,
) -> bool:
    """正文是否正向提及关键词；同一分句前缀含否定词则不计（匹配 / 超范围扫描共用）。

    ignore_contrast=True（目录匹配）：扩展/对比/展望语境也不计，避免范围外词抬主路径。
    """
    if not text or not kw:
        return False
    flags = re.IGNORECASE if kw.isascii() else 0
    for m in re.finditer(re.escape(kw), text, flags):
        left = max(0, m.start() - window)
        chunk = _left_clause(text[left : m.start()])
        if NEGATION_RE.search(chunk):
            continue
        if ignore_contrast and CONTRAST_RE.search(chunk):
            continue
        # 同句右侧短窗：先提能力再写「本期不」（不含光杆「非」）
        right = _right_clause(text[m.end() : m.end() + window])
        if RIGHT_NEGATION_RE.search(right):
            continue
        return True
    return False


def dedupe_out_scope_vs_features(
    feature_lines: list[str] | None,
    out_scope_lines: list[str] | None,
    *,
    limit: int = 5,
) -> list[str]:
    """功能点与「不在本期」互斥；开题要做的不得进排除列表。"""
    feats = [str(x).strip() for x in (feature_lines or []) if str(x).strip()]
    outs: list[str] = []
    for raw in out_scope_lines or []:
        line = str(raw).strip()
        if not line:
            continue
        if any(line in f or f in line for f in feats):
            continue
        outs.append(line[:80])
        if len(outs) >= limit:
            break
    return outs
