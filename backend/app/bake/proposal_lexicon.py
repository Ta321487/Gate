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
    r"不涉及|不对接|不绑定|不接|无需|不必|不能|不可|无法|"
    r"仅作展望|仅参考|非本课题|本期不|范围外|不强制|非必交|非必演示|不作为必|"
    r"非本期|不在本期|不做范围|并非|"
    # 口语假支付 / 模拟支付（开题常写在支付宝微信前）
    r"假支付|假的支付|模拟支付|无真支付|非真支付|不用真支付|不做真支付|"
    # 「非传染病晨检」：仅左侧前缀用；右侧见 RIGHT_NEGATION_TERMS
    r"非(?!常|法|洲|遗|物质)"
)
# 右侧「先提能力再写本期不」：不含光杆「非」，避免「物资领用，非公卫上报」误杀
# 亦收「选支付宝/微信…假的就行」——老师口语不等于真商户清算
RIGHT_NEGATION_TERMS = (
    r"不要求|不实现|不做|不作为|不纳入|不属于|不扩展|不包含|不包括|不含|不以|"
    r"不涉及|不对接|不绑定|不接|无需|不必|不能|不可|无法|"
    r"仅作展望|仅参考|非本课题|本期不|范围外|不强制|非必交|非必演示|不作为必|"
    r"非本期|不在本期|不做范围|并非|不能替代|不可替代|"
    r"假的就行|假的即可|假的就好|假的就行了|假支付|假的支付|"
    r"模拟支付|无真支付|非真支付|不用真支付|不做真支付|密码即可|输密码即可"
)
# 对比/扩展语境：关键词出现在「容易涉及的扩展」里，不应抬升拟实现主路径
CONTRAST_TERMS = (
    r"扩展性|扩展能力|背景对比|仅作对比|作为对比|未来展望|调研阶段|"
    r"容易将|容易出现|往往超出|超出.{0,8}规模|庞大模块|商业属性|"
    r"再扩展|分阶段交付|先实现单仓|后续扩展|可作为后续|"
    r"商业方案|商业系统|三甲医院|大型单位|功能完善|功能完整|实施成本|"
    r"本科毕设适合|本科.*?聚焦|本科.*?即可|本科.*?不做|"
    r"勿与|不要与|区别于|区分于|不同于|与.?区分|区分|勿和|不要和|不要当成|勿当成|混淆|"
    r"不做成|勿做成|不要做成|不成[为做]|"
    r"常通过|仍需人工|信息分散"
)
# 文献转述：某人等引入/提出 X…[n] —— 不是本课题功能承诺
LITERATURE_ATTR_TERMS = (
    r"等人?(?:引入|提出|采用|设计|研究|构建|实现|开发|基于)|"
    r"等(?:引入|提出|采用|设计|研究|构建)|"
    r"(?:学者|文献|既有研究|已有研究|相关研究)(?:表明|指出|认为|多)|"
    r"(?:例如|比如|如)[\u4e00-\u9fff]{0,12}(?:引入|提出|采用)"
)
# 角标引用：[1] / [12]（开题研究现状常见）
CITATION_MARK_RE = re.compile(r"\[\d{1,3}\]")

FEATURE_HEAD_RE = re.compile(rf"({FEATURE_HEAD_TERMS})")
RESEARCH_WITH_IMPL_RE = re.compile(r"研究内容.{0,12}拟实现|拟实现.{0,12}功能")
OUT_HEAD_RE = re.compile(rf"({NEGATION_TERMS})")
NEGATION_RE = re.compile(rf"(?:{NEGATION_TERMS})")
RIGHT_NEGATION_RE = re.compile(rf"(?:{RIGHT_NEGATION_TERMS})")
CONTRAST_RE = re.compile(rf"(?:{CONTRAST_TERMS})")
LITERATURE_ATTR_RE = re.compile(rf"(?:{LITERATURE_ATTR_TERMS})")

_CLAUSE_SEPS = ("。", "；", ";", "！", "!", "？", "?", "\n")
# 右侧否定只在同一分句内生效：逗号后另起一题（如「设置申报截止日期，逾期不可申请」）
# 的「不可」否定的是别的动作，不是前面的能力，故不计。
_RIGHT_CLAUSE_SEPS = ("，", ",", "、")
# 但只豁免「逾期/过期…不可…」这类「截止后动作」否定；其余跨逗号否定仍照旧生效。
_POST_DEADLINE_HEAD_RE = re.compile(r"逾期|过期|超期|到期|过时")
# 「报名截止后不可再报」是截止本身的后果表述（不是否定该功能），且常在无逗号时出现：
# 时间/承接连接词紧贴否定词时同样豁免。
_POST_ACTION_HEAD_RE = re.compile(r"(?:后|之后|以后|则|即|起)$")


def _right_negated(raw: str) -> bool:
    """右侧窗口是否真的否定了前面的能力（「逾期不可申请」「截止后不可再报」不算否定能力）。"""
    for m in RIGHT_NEGATION_RE.finditer(raw):
        head = raw[max(0, m.start() - 8) : m.start()]
        if _POST_ACTION_HEAD_RE.search(head):
            continue
        if any(sep in raw[: m.start()] for sep in _RIGHT_CLAUSE_SEPS) and (
            _POST_DEADLINE_HEAD_RE.search(head)
        ):
            continue
        return True
    return False


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
    return pattern_mentioned(
        text,
        re.compile(re.escape(kw), flags),
        window=window,
        ignore_contrast=ignore_contrast,
    )


def _literature_paraphrase(left: str, right: str) -> bool:
    """研究现状转述他人工作（含角标引用）≠ 本课题拟交付承诺。"""
    if LITERATURE_ATTR_RE.search(left) or LITERATURE_ATTR_RE.search(right):
        return True
    # 「…协同过滤…能力[2]」：同句右侧近邻角标
    if CITATION_MARK_RE.search(right[:32]):
        return True
    return False


def pattern_mentioned(
    text: str,
    pattern: re.Pattern[str] | re.Pattern[bytes],
    *,
    window: int = 48,
    ignore_contrast: bool = False,
) -> bool:
    """正则命中且同句无「不在本期/不做」等否定时才算正向提及。

    能力扫词应走本函数，避免开题「非本期：电子签/影院选座」误挂能力。
    ignore_contrast=True 时一并忽略对比/展望与文献转述（含 [n] 角标）。
    """
    if not text or pattern is None:
        return False
    for m in pattern.finditer(text):
        left = max(0, m.start() - window)
        chunk = _left_clause(text[left : m.start()])
        if NEGATION_RE.search(chunk):
            continue
        right = _right_clause(text[m.end() : m.end() + window])
        if _right_negated(right):
            continue
        if ignore_contrast:
            if CONTRAST_RE.search(chunk) or CONTRAST_RE.search(right):
                continue
            if _literature_paraphrase(chunk, right):
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


def hints_mentioned(
    text: str,
    hints: tuple[str, ...],
    *,
    window: int = 48,
    ignore_contrast: bool = True,
) -> bool:
    """任一 hint 在正文里「正向提及」（否定/对比/文献转述语境不计）。

    场景 / 口径扫描一律走本函数；不要退回裸子串 ``any(k in text)``，
    否则开题里的对比句与「不做 X」会被当成承诺。
    """
    for hint in hints or ():
        if keyword_mentioned(text, hint, window=window, ignore_contrast=ignore_contrast):
            return True
    return False


# --- 结算边界（维度判定，不是逐功能词）----------------------------------------
# 工厂口径：毕设交付「系统内支付」（选渠道 + 支付密码 + 扣账户余额）；
# 只有材料**承诺对外资金清算**（商户 / 支付接口 / 分账 / 真实扣款）才超范围。
# 判据看「渠道词附近的语境」，不为每个同义写法补一条否定词。
SETTLEMENT_CHANNEL_RE = re.compile(
    r"支付宝|微信支付|微信\s*支付|银联|财付通|第三方支付|支付接口|支付平台|银行卡支付"
)
# 渠道附近出现「对外清算」证据 → settlement=external
SETTLEMENT_EXTERNAL_NEAR_RE = re.compile(
    r"对接|接入|调用|开通|申请.{0,6}接口|商户|清算|分账|真实扣款|真实支付|"
    r"支付接口|SDK|回调|对账|结算|打款|直连|聚合支付|收款码"
)
# 渠道附近出现「系统内记账」证据 → settlement=in_system
SETTLEMENT_IN_SYSTEM_NEAR_RE = re.compile(
    r"系统内|账户余额|余额|扣减|模拟|假(?:的|支付)|虚拟|演示|不接入|不对接|"
    r"不用真|无真|非真|密码即可|输密码即可|本地|账号内"
)
# 无渠道词时的直接证据（「本系统采用模拟支付」「不对接第三方商户清算」等）
SETTLEMENT_IN_SYSTEM_DIRECT_RE = re.compile(
    r"模拟支付|假的就行|假的即可|假支付|虚拟支付|系统内支付|系统内扣款|系统内余额|"
    r"不接入第三方|不对接第三方|不对接微信|不对接支付宝|不对接商户|无真支付|非真支付"
)


def settlement_mode(text: str, *, window: int = 64) -> str:
    """材料承诺的结算边界：``external`` / ``in_system`` / ``unknown``。

    - 只看渠道词附近的语境，不要求材料写「模拟」二字：
      选支付宝/微信 + 支付密码 / 账户余额 = ``in_system``；
      对接商户 / 支付接口 / 分账 / 清算 = ``external``。
    - 否定语境（「不对接微信支付商户」）不算对外承诺。
    - accept / 超范围判定共用；新增同义写法请改本维度，不要逐条加否定词。
    """
    t = (text or "").strip()
    if not t:
        return "unknown"
    external = False
    in_system = False
    for m in SETTLEMENT_CHANNEL_RE.finditer(t):
        left = _left_clause(t[max(0, m.start() - window) : m.start()])
        right = _right_clause(t[m.end() : m.end() + window])
        near = f"{left}{right}"
        negated = bool(NEGATION_RE.search(left) or RIGHT_NEGATION_RE.search(right))
        if not negated and SETTLEMENT_EXTERNAL_NEAR_RE.search(near):
            external = True
        if negated or SETTLEMENT_IN_SYSTEM_NEAR_RE.search(near):
            in_system = True
    if external:
        return "external"
    if in_system or SETTLEMENT_IN_SYSTEM_DIRECT_RE.search(t):
        return "in_system"
    if SETTLEMENT_CHANNEL_RE.search(t):
        # 只点名渠道、未承诺对外清算 → 演示级系统内支付（demoPay 口径）
        return "in_system"
    return "unknown"
