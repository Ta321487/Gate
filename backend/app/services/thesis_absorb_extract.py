"""终稿吸收：分桶裁证据 + 形态钳子（同材同果）。

真源：docs/thesis-absorb.md §2.3 / §3。
三栏主路径是 LLM（agents_thesis_absorb）；本模块：
- 分桶/题注裁【P1～P4】证据包；
- 无 Key 时弱抽兜底（实体仅题注，角色/功能空）；
- 形态钳子（空壳、岗名剥壳、××类、叙述残片）——**禁止为客户遣词加专线**。
同一正文 + 同一 EXTRACTOR_VERSION → 同一弱抽/证据包。
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.services.proposal import (
    extract_module_lines,
    extract_role_labels,
    extract_table_features,
    strip_non_dev_sections,
    summarize_proposal,
    _SECTION,
    _BULLET,
)

# v20：按 docs/thesis-absorb.md §3 重写分桶与采矿优先级（禁止再叠旧启发式）
# v21：各端「其中包含」全量按形态回收（首项可不带管理/模块）；不写死业务名
# v22：测试章只验货；步骤/开题 summarize 的 out 不得进「不做」碎片
# v23：实体只认库表题注/××表；禁止掐「××管理」词干充数（§3.2）
# v24：实体禁「列表」假表名、序列图句子、表名后拼音
# v25：实体去掉业务/界面固定词表，只靠库表题注+表名形态+行长
# v26：题注必须含「××表」；表名前禁助词/「存储在该」；不用图侧 table_labels
# v27：加厚数据库章表名采矿（小节标题/表名：/枚举）；实体上限 24
# v28：打开详情若实体仍是功能词干假草稿 → 强制重抽并落盘纠正
# v29：库表实体与角色可同名并存（用户表既是角色也是实体，不得互剔）
# v30：三栏 + 覆盖改 LLM 主抽；正则只切证据/拼装结果；无 LLM 仅表题注实体
# v34：题注实体压过导航/过程钳子；空壳功能仍掐；角色不吃功能模块；假红「角色与端」清掉
# v35：忠于原文——功能须「设计提到 + 实现/图交叉有实义」；禁把「系统管理员」剥成「系统管理」
# v36：写法多变只认稳形态——功能主收「××管理/模块」；拒 UML「××类」与口语残片
# v37：产品跟合同不跟措辞——三栏以 LLM 为主；正则只形态钳子，禁止为遣词加专线
# v38：无模型也回填合同角色（××端/角色包括）；禁止角色栏空白却实体里已有管理员/用户
# v39：禁「仓库管理←仓库管理员」岗名剥壳；禁假菜单「首页管理」（真名常为系统首页/系统首页管理）
# v40：物理/逻辑库表章 → draft_schema_sql 落库（忠于原文，禁脑补列）
# v41：L1 正文主矿（类型词锚定切列）；plumber 仅补空；材料有而抽空=工厂漏挖
# v42：表头/类型/题注/行首形态加固（中文类型、制表符、括号英文名、Y/N·PRI）
EXTRACTOR_VERSION = "42"

THIN_FEATURE_THRESHOLD = 3

_CHAPTER_BREAK = re.compile(
    r"([^\n])(第\s*[一二三四五六七八九十百零〇\d]+\s*[章节部分])"
)
_CHAPTER_HEAD = re.compile(
    r"^第\s*[一二三四五六七八九十百零〇\d]+\s*[章节部分]"
)
_ENUM_BREAK = re.compile(r"([^\n])([一二三四五六七八九十百]+[、．.])")
_NUM_ITEM_BREAK = re.compile(r"([^\n])([（(]?\d{1,2}[)）.、])(?!\d)")
# 不在「第X章/节」后切开；不拆「系统需求分析」等词中命中
_FEATURE_HEAD_BREAK = re.compile(
    r"(?<![章节部分])(?<!系统)(?<!的)("
    r"主要功能|功能清单|功能需求|非功能需求|研究内容|主要工作|"
    r"需求分析|系统设计|系统实现|系统测试|研究背景|非本期|不交范围|"
    r"系统总体设计|模块设计|数据库设计"
    r")"
)
_TITLE_KW = (
    r"系统总体设计|系统设计|总体设计|详细设计|数据库设计|架构设计|概要设计|"
    r"模块设计|功能设计|功能结构|需求分析|系统分析|系统实现|系统测试|"
    r"绪论|引言|主要工作|研究内容|研究背景"
)
_PEEL_CHAPTER = re.compile(
    rf"^(第\s*[一二三四五六七八九十百零〇\d]+\s*[章节部分])"
    rf"((?:[^\n]{{0,20}}?)(?:{_TITLE_KW}))"
    rf"(.*)$"
)
_PEEL_KW = re.compile(rf"^({_TITLE_KW})(.+)$")
_INLINE_MODULE = re.compile(r"([\u4e00-\u9fffA-Za-z0-9/与及]{2,12}模块)")
_SKIP_MODULE_NAMES = frozenset(
    {
        "功能模块",
        "系统模块",
        "业务模块",
        "各个模块",
        "相关模块",
        "主要模块",
        "以下模块",
        "上述模块",
        "本模块",
        "子模块",
        "各模块",
        "等模块",
        "模块",
        "关键模块",
        "核心模块",
    }
)
_TOC_DOT_LEADERS = re.compile(r"[\.·．…‥]{2,}\s*\d*\s*$")

# 标题语义 → 桶（章号不固定；顺序：先丢弃/测试，再摘要/绪论，再需求/设计/实现）
_BUCKET_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "discard",
        re.compile(
            r"(?:^|\s)(?:目录|CONTENTS)\s*$|"
            r"(?:相关技术|技术综述|开发工具|技术及环境|框架介绍|关键环境|"
            r"(?:Flask|Django|Spring|Vue|MySQL|Redis).{0,12}简介|"
            r"文献综述|国内外研究|研究现状|"
            r"可行性分析|经济可行性|技术可行性|操作可行性|"
            r"结论|总结与展望|展望|致谢|参考文献|参考资料|附录)"
        ),
    ),
    (
        "test",
        re.compile(
            r"(?:系统测试|功能测试|测试用例|软件测试|测试方案|测试结果|测试概述|"
            r"测试的背景|测试的意义)"
        ),
    ),
    (
        "abstract",
        re.compile(r"(?:摘要|Abstract)\b", re.I),
    ),
    (
        "intro",
        re.compile(
            r"(?:绪论|引言|选题背景|研究意义|研究内容|主要工作|研究目标|本文主要|课题意义|"
            r"论文主要结构|(?<!测试)概述)"
        ),
    ),
    (
        "req",
        re.compile(
            r"(?:需求分析|需求规格|功能需求|非功能需求|用例分析|需求描述|系统分析|"
            r"用例说明|用例图)"
        ),
    ),
    (
        "design",
        re.compile(
            r"(?:系统总体设计|系统设计|总体设计|详细设计|数据库设计|架构设计|概要设计|"
            r"模块设计|功能设计|功能结构|系统功能模块|"
            r"物理结构|逻辑设计|表设计|"
            r"[\u4e00-\u9fff]{0,8}端功能设计)"
        ),
    ),
    (
        "impl",
        re.compile(
            r"(?:系统实现|功能实现|详细实现|编码实现|界面实现|模块实现|关键实现)"
        ),
    ),
]

_OTHER_HAS = re.compile(
    r"(?:现有|传统|同类|其他|别人|市面|常见).{0,24}(?:系统|方案|软件|平台|产品)"
    r".{0,40}(?:具有|支持|已实现|可以|能够|提供|具备)"
)
_LACK_SIDE = re.compile(
    r"(?:现有|传统|同类|其他).{0,40}(?:缺乏|缺少|无法|不能|没有|不支持|难以)"
)
_OUT_SCOPE_HINT = re.compile(
    r"(?:不包含|暂不|超出范围|不做|未实现|不涉及|不在本文|本期不|不支持)"
)
_SELF_CLAIM = re.compile(
    r"(?:本文|本系统|本课题|本研究).{0,20}(?:实现|完成|设计|开发|提供|支持|包括)"
)
_WORK_HEAD = re.compile(
    r"(?:本文主要工作|主要研究内容|研究内容|主要工作|本文完成|本文实现|本文设计)"
)
# 「包含 A、B管理、C…」：顿号清单；项可为裸名或 ××管理/模块（不写死业务词）
_INCLUDE_MGMT_LIST = re.compile(
    r"(?:其中)?(?:包含|包括)(?:[：:，,]|了)?"
    r"((?:[\u4e00-\u9fff]{2,12}(?:管理|模块)?)"
    r"(?:[、，,/][\u4e00-\u9fff]{2,12}(?:管理|模块)?){1,24})"
)
_LEADING_FEAT_NUM = re.compile(
    r"^(?:"
    r"\d{1,2}(?:\.\d{1,2}){0,3}\.?\s*"
    r"|[一二三四五六七八九十百]+[、．.]\s*"
    r"|[（(]\d{1,2}[)）]\s*"
    r")"
)
_NOISE_FEAT_TAIL = re.compile(
    r"(?:"
    r"操作可行性|经济可行性|技术可行性|可行性分析|"
    r"用例说明|安全需求|非功能需求|"
    r"功能设计|总体设计|详细设计|"
    r"序列图|时序图|用例图|类图|活动图|流程图|"
    r"本章小结|研究背景|研究现状|研究意义|"
    r"测试背景|测试意义|测试概述|系统测试概述|"
    r"系统功能模块|^功能模块$"
    r")"
)
_KEEP_FEAT_TAIL = re.compile(r"(?:管理|模块|商城|入库|出库|充值|订单|支付|审核)$")
_FEAT_CHROME = re.compile(
    r"(?:"
    r"(?:测试|研究)?背景|(?:测试|研究)?意义|概述|现状|目的及意义|"
    r"首页界面|界面$"
    r")$"
)
# 只认常见尾巴/壳形态，不点业务题名
_BUSINESS_HINT = re.compile(r"(?:管理|模块|首页|中心)")
# 角色栏跳过壳词（身份名，不是实体业务词表）
_ENTITY_SKIP = frozenset(
    {
        "首页",
        "登录",
        "注册",
        "后台",
        "系统",
        "个人中心",
        "密码",
    }
)
# 库表元词：抽到「数据表/字段表」也不当业务实体
_ENTITY_META = frozenset({"数据", "数据库", "字段", "主键", "外键", "系统"})
# 导航/壳页名，不是库表
_ENTITY_NAV = frozenset(
    {"关于我们", "个人中心", "首页", "系统首页", "登录页", "欢迎页", "帮助中心"}
)
_ENTITY_PROCESS_TAIL = re.compile(
    r"(?:处理|查询|维护|审核|统计|分析|配置|登录|注册|纠纷|反馈|互动|交流)$"
)
_FEATURE_SHELL = frozenset(
    {
        "系统管理",
        "基础管理",
        "功能管理",
        "模块管理",
        "业务管理",
        "信息管理",
        "数据管理",
        # 导航壳：正文多写「系统首页/首页展示」；裸「首页管理」常是胡编
        "首页管理",
    }
)
# 匹配「××管理」时不得吃进「××管理员」岗名（管理(?!员)）
_MGMT_OR_MODULE_TAIL = r"(?:管理(?!员)|模块)"
_FEATURE_JUNK = re.compile(
    r"(?:"
    r"^[图表]\s*[0-9０-９一二三四五六七八九十]|"  # 图题/表题误进功能
    r"进入|点击|填写|登录后|如图|所示|"  # 叙述步骤 ≠ 菜单名
    r"^为|^在(?!线)|"  # 「为/在厂商管理」叙述残片；勿伤「在线客服」
    r"这些功能|可以进行|进行操作|操作和管理|等信息|"  # 口语清单尾巴
    r"通过.+模块|"
    r"功能结构设计图|结构设计图|"
    r"管理等$|等$"
    r")"
)
# 题注行：表 4.1 / 表4-1 / 表4．1
_TABLE_CAPTION_LINE = re.compile(
    r"表\s*[0-9０-９.．\-—﹣一二三四五六七八九十]+"
)
# 真表名：连续名词+「表」。名内不得含助词/「表」字本身
_TABLE_NAME_CHAR = (
    r"(?![的在是有了着过与和及或将为被把从到该其如示表])[\u4e00-\u9fff]"
)
# 「表」后不得接 列表/如下/所示…
_TABLE_NAME_TAIL = r"(?!列表|示|面|达|现|格|情|述|如)"
_TABLE_NAME_INLINE = re.compile(
    rf"((?:{_TABLE_NAME_CHAR}){{2,8}})表{_TABLE_NAME_TAIL}"
)
_TABLE_NAME_AT_LINE_START = re.compile(
    rf"^((?:{_TABLE_NAME_CHAR}){{2,8}})表{_TABLE_NAME_TAIL}"
)
# 4.3.1 用户信息表 / （1）订单表
_TABLE_NAME_AFTER_ENUM = re.compile(
    rf"^(?:[（(]?\d+(?:\.\d+){{0,3}}[)）.、]|\d+(?:\.\d+){{1,3}})\s*"
    rf"((?:{_TABLE_NAME_CHAR}){{2,8}})表{_TABLE_NAME_TAIL}"
)
# 表名：用户信息表（必须带表字，且表不进捕获组）
_TABLE_NAME_LABEL = re.compile(
    rf"表名(?:称|为)?[：:为]?\s*"
    rf"((?:{_TABLE_NAME_CHAR}){{2,8}})表"
)
# 表定义行形态（有字段线索才信长行里的××表）
_LINE_TABLE_DEF = re.compile(
    r"(?:字段|主键|外键|数据类型|varchar|char\s*\(|int\s*\(|COMMENT)",
    re.I,
)
_SECTION_TOC_NOISE = re.compile(
    r"(?:"
    r"可行性|用例图|序列图|时序图|类图|活动图|流程图|"
    r"研究背景|研究现状|研究意义|论文主要结构|系统测试概述|"
    r"逻辑架构|总体设计|详细设计|功能设计|"
    r"国内外?研究现状|课题研究的目的"
    r")"
)
_ROMAN_PAGE = re.compile(r"^[ⅣⅢⅡⅠivxlcdmIVXLCDM]+$")
_BARE_SEC_NUM = re.compile(r"^\d{1,2}(?:\.\d{1,2}){0,3}\.?$")
_USEFUL_SEC = re.compile(
    r"(?:管理|模块|登录|注册|订单|支付|审核|入库|出库|商城|预约|借阅|查询|统计)"
)
_BARE_ENUM = re.compile(
    r"^(?:"
    r"\d{1,2}(?:\.\d{1,2}){0,3}\.?"
    r"|[一二三四五六七八九十百]+[、．.]"
    r"|[（(]\d{1,2}[)）]"
    r")$"
)
_IMPL_SHELL = re.compile(
    r"(?:登录|注册|首页界面|界面实现|密码修改|退出登录)$"
)


def content_sha256(raw: bytes | str) -> str:
    if isinstance(raw, str):
        data = raw.encode("utf-8")
    else:
        data = raw
    return hashlib.sha256(data).hexdigest()


def collapse_pdf_glyph_spaces(text: str) -> str:
    """捏合 PDF 抽字常见的汉字间空格：绪 论→绪论，第 1 章→第1章；顿号旁空格一并去掉。"""
    t = text or ""
    t = re.sub(r"(?<=[\u4e00-\u9fff])[ \t]+(?=[\u4e00-\u9fff])", "", t)
    t = re.sub(r"\s*([、，,；;])\s*", r"\1", t)
    t = re.sub(r"[ \t]+([。．.])", r"\1", t)
    t = re.sub(
        r"第[ \t]*([一二三四五六七八九十百零〇\d]+)[ \t]*章",
        r"第\1章",
        t,
    )
    return t


def _peel_heading_body(cand: str) -> tuple[str, str]:
    """粘连行：章/节标题留给 heading，其后正文进 body。"""
    s = (cand or "").strip()
    if not s:
        return "", ""
    m = _PEEL_CHAPTER.match(s)
    if m:
        head = f"{m.group(1)}{m.group(2) or ''}".strip()
        rest = (m.group(3) or "").strip()
        return head, rest
    m2 = _PEEL_KW.match(s)
    if m2:
        head = (m2.group(1) or "").strip()
        rest = (m2.group(2) or "").strip()
        if rest:
            return head, rest
    return s, ""


def clean_heading_candidate(ln: str) -> str:
    s = (ln or "").strip()
    s = _TOC_DOT_LEADERS.sub("", s).strip()
    s = collapse_pdf_glyph_spaces(s)
    return s


def normalize_thesis_text(text: str) -> str:
    """粘连/PDF 抽字 → 可分行文本（确定性·不看题名）。"""
    t = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    t = collapse_pdf_glyph_spaces(t)
    t = _CHAPTER_BREAK.sub(r"\1\n\2", t)
    t = _FEATURE_HEAD_BREAK.sub(r"\n\1", t)
    t = _ENUM_BREAK.sub(r"\1\n\2", t)
    t = _NUM_ITEM_BREAK.sub(r"\1\n\2", t)
    nlen = max(len(t), 1)
    if t.count("\n") < max(8, nlen // 800):
        t = re.sub(r"。\s*", "。\n", t)
        t = re.sub(r"；\s*", "；\n", t)
    return t


def coalesce_broken_lines(lines: list[str]) -> list[str]:
    """合并 PDF 把「1.1」与「研究背景」拆成两行的情况。"""
    out: list[str] = []
    i = 0
    n = len(lines or [])
    while i < n:
        ln = (lines[i] or "").strip()
        if not ln:
            i += 1
            continue
        if _BARE_ENUM.fullmatch(ln) and i + 1 < n:
            nxt = (lines[i + 1] or "").strip()
            if nxt and not _BARE_ENUM.fullmatch(nxt) and not _is_heading_line(nxt):
                out.append(f"{ln} {nxt}")
                i += 2
                continue
        out.append(ln)
        i += 1
    return out


def extract_inline_modules(text: str, limit: int = 20) -> list[str]:
    """全文找「××模块」，不要求独占一行。"""
    body = _collapse_ws(strip_non_dev_sections(text or ""))
    out: list[str] = []
    seen: set[str] = set()
    for m in _INLINE_MODULE.finditer(body):
        name = (m.group(1) or "").strip()
        name = re.sub(r"^[\d\.、)）（\s]+", "", name)
        if not name or name in _SKIP_MODULE_NAMES or len(name) < 4:
            continue
        if name[0] in "各等其该本每此0123456789":
            continue
        if re.search(
            r"(?:分为|包含|其中|以及|定制|使得|采用|集成|自身|代码|更加|便于|分明)",
            name,
        ):
            continue
        if re.search(r"[在的上等]|各类|[a-z]", name):
            continue
        if re.search(r"(?:核心)?功能模块$", name):
            continue
        if "、" in name or "，" in name or len(name) > 14:
            continue
        if name not in seen:
            seen.add(name)
            out.append(name)
        if len(out) >= limit:
            break
    return out[:limit]


def _classify_heading(heading: str) -> str:
    h = (heading or "").strip()
    if not h:
        return "other"
    for name, pat in _BUCKET_RULES:
        if pat.search(h):
            return name
    return "other"


def _is_heading_line(ln: str) -> bool:
    s = clean_heading_candidate(ln)
    if not s or len(s) > 48:
        return False
    if _SECTION.match(s):
        return True
    if _CHAPTER_HEAD.match(s):
        return True
    return False


def split_buckets(text: str) -> dict[str, list[tuple[str, list[str]]]]:
    """按标题切分 → {bucket: [(heading, lines), ...]}。"""
    body = strip_non_dev_sections(normalize_thesis_text(text or ""))
    lines = [ln.rstrip() for ln in body.splitlines()]
    buckets: dict[str, list[tuple[str, list[str]]]] = {
        k: []
        for k in (
            "abstract",
            "intro",
            "req",
            "design",
            "impl",
            "test",
            "discard",
            "other",
        )
    }
    cur_bucket = "other"
    cur_heading = ""
    cur_body: list[str] = []

    def flush() -> None:
        nonlocal cur_heading, cur_body
        if cur_heading or cur_body:
            buckets.setdefault(cur_bucket, []).append((cur_heading, list(cur_body)))
        cur_heading = ""
        cur_body = []

    for raw in lines:
        ln = raw.strip()
        if not ln:
            continue
        cand = clean_heading_candidate(ln)
        if not cand:
            continue
        if re.search(r"届本科毕业设计|届本科毕业论文", cand) and len(cand) <= 40:
            continue
        # 纯目录点线行丢弃
        if _TOC_DOT_LEADERS.search(ln) and len(cand) <= 40:
            continue
        # 图/表题注不当章题
        if re.match(r"^[图表]\s*[0-9０-９一二三四五六七八九十]", cand):
            if cur_bucket != "discard":
                cur_body.append(cand if cand != ln else ln)
            continue
        head, rest = _peel_heading_body(cand)
        # 「需求分析，开发…」是 peel 误伤，整行当正文
        if rest and rest[:1] in "，、。；：":
            head, rest = "", ""
        cls_head = _classify_heading(head) if head else "other"
        cls_cand = _classify_heading(cand)
        cls = cls_head if cls_head != "other" else cls_cand
        long_glued = bool(
            rest
            and cls in ("design", "req", "impl", "intro", "test", "abstract")
        )
        # 叙述句里夹关键词不当章题
        narrative = ("、" in cand or "，" in cand or "。" in cand) and not head
        if _is_heading_line(cand) or _is_heading_line(head) or (
            cls != "other"
            and not _BULLET.match(cand)
            and (len(cand) <= 28 or long_glued)
            and not narrative
        ):
            flush()
            cur_heading = head or cand
            cur_bucket = cls
            if rest:
                cur_body.append(rest)
            continue
        if cur_bucket == "discard":
            continue
        cur_body.append(cand if cand != ln else ln)
    flush()
    return buckets


def _intro_line_ok(ln: str) -> bool:
    s = ln.strip()
    if not s or len(s) < 4:
        return False
    if _OUT_SCOPE_HINT.search(s) and not _SELF_CLAIM.search(s):
        return False
    if _OTHER_HAS.search(s):
        return False
    if _LACK_SIDE.search(s) and not _SELF_CLAIM.search(s):
        return False
    if _OTHER_HAS.search(s) and _SELF_CLAIM.search(s):
        if re.search(r"(?:现有|传统).{0,30}(?:具有|支持).{0,40}(?:本文|本系统)", s):
            return False
    return True


def _collapse_ws(text: str) -> str:
    """PDF 常在词中换行（材\\n料商城）——采矿前捏合空白。"""
    return re.sub(r"\s+", "", text or "")


def extract_included_mgmt_items(text: str, *, limit: int = 40) -> list[str]:
    """从「包含/包括 …」抠功能点。

    写法会变（查重），但稳形态是「××管理 / ××模块」。
    不收 UML「××类」、口语「这些功能 / 可以进行操作和管理」。
    """
    out: list[str] = []
    seen: set[str] = set()
    flat = _collapse_ws(text)
    for m in _INCLUDE_MGMT_LIST.finditer(flat):
        chunk = m.group(1) or ""
        for part in re.split(r"[、，,/]", chunk):
            item = (part or "").strip()
            if not item or item in seen:
                continue
            if item in ("系统功能模块", "功能模块"):
                continue
            if re.search(
                r"(?:包含|其中|分为|以及|定制|[一二三四五六七八九十两\d]+大)",
                item,
            ):
                continue
            # UML / 叙述：用户类、管理员类、这些功能、可以进行操作和管理
            if item.endswith("类") or item.endswith("类等"):
                continue
            if re.search(
                r"(?:这些|可以|进行|操作和|等信息|若不|将回|匹配)",
                item,
            ):
                continue
            # 稳形态：××管理 / ××模块（含个人中心管理）；短裸名仅首页/商城等入口
            if item.endswith("管理") or item.endswith("模块"):
                ok = 4 <= len(item) <= 16 and item not in ("管理", "模块")
            else:
                ok = bool(
                    2 <= len(item) <= 6
                    and re.fullmatch(r"[\u4e00-\u9fff]+", item)
                    and re.search(r"(?:首页|商城|中心|论坛|资讯)$", item)
                    and not re.search(
                        r"(?:根据|进行|实现|开发|本文|本系统|采用|使得|类)",
                        item,
                    )
                )
            if not ok:
                continue
            cleaned = clean_feature_label(item)
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            out.append(cleaned)
            if len(out) >= limit:
                return out
    return out


def _lines_to_features(lines: list[str], *, intro: bool = False) -> list[str]:
    blob = "\n".join(lines)
    out: list[str] = []
    seen: set[str] = set()
    for src in (
        extract_included_mgmt_items(blob),
        extract_module_lines(blob),
        extract_inline_modules(blob),
        extract_table_features(blob),
    ):
        for x in src:
            if x not in seen:
                seen.add(x)
                out.append(x)
    for ln in lines:
        s = _BULLET.sub("", ln.strip()).strip()
        s = re.sub(r"[。；;]+$", "", s)
        if intro and not _intro_line_ok(ln):
            continue
        if intro and not (
            _SELF_CLAIM.search(ln)
            or _WORK_HEAD.search(ln)
            or "模块" in s
            or re.match(r"^[（(]?\d", ln.strip())
        ):
            if "模块" not in s and len(s) > 40:
                continue
        if "模块" in s and ("、" in s or "，" in s):
            continue
        if re.match(r"^\d+(\.\d+)*\s+\S{1,16}$", s) and "模块" not in s:
            continue
        if re.search(r"(?:活动图|时序图|用例图|类图|流程图)$", s):
            continue
        if re.search(r"的实现$", s) and len(s) <= 24:
            continue
        if s in ("研究背景", "研究意义", "本章小结", "可行性分析", "需求分析"):
            continue
        if re.search(r"(?:核心)?角色[：:]", s) or re.search(
            r"(?:划分为|分为).{0,12}角色", s
        ):
            continue
        if re.search(r"(?:其中)?包含.+(?:管理|模块)", s) and ("、" in s or "，" in s):
            continue
        if 4 <= len(s) <= 80 and s not in seen:
            if re.match(r"^[随着目前近年来]", s):
                continue
            seen.add(s)
            out.append(s)
        if len(out) >= 40:
            break
    return out[:30]


def _out_scope_from_intro(lines: list[str]) -> list[str]:
    out: list[str] = []
    for ln in lines:
        if _OUT_SCOPE_HINT.search(ln):
            cleaned = _BULLET.sub("", ln.strip())
            cleaned = re.sub(r"\s+", "", cleaned)[:80]
            if cleaned and cleaned not in out and not _looks_like_test_prose(cleaned):
                out.append(cleaned)
    return out[:8]


_TEST_PROSE = re.compile(
    r"(?:"
    r"点击|填写|选择|输入|登录后|进入|打开|页面|界面|按钮|提交|"
    r"预期|实际结果|测试步骤|用例|通过|失败|是否|"
    r"与预期|阻止|合法的|非法"
    r")"
)
_CAPABILITY_TAIL = re.compile(r"(?:管理|模块)$")


def _looks_like_test_prose(s: str) -> bool:
    """测试步骤/操作说明：验货用，不是「不做」项。"""
    t = (s or "").strip()
    if not t:
        return False
    if _TEST_PROSE.search(t):
        return True
    # PDF 折行碎句：有逗号/引号或过长叙述
    if re.search(r"[，。；;“”\"：:]", t) and not _CAPABILITY_TAIL.search(t):
        return True
    return False


def _test_capability_labels(lines: list[str]) -> list[str]:
    """P3 测试：只抽 ××管理/××模块 能力名做交叉，不收步骤句。"""
    blob = "\n".join(lines or [])
    compact = _collapse_ws(blob)
    raw = (
        extract_included_mgmt_items(compact)
        + extract_module_lines(blob)
        + extract_inline_modules(compact)
    )
    shaped = [
        x
        for x in raw
        if x and _CAPABILITY_TAIL.search(str(x)) and not _looks_like_test_prose(str(x))
    ]
    return finalize_feature_lines(shaped, limit=12)


def _normalize_feat(s: str) -> str:
    t = re.sub(r"\s+", "", s or "")
    t = re.sub(r"[：:].*$", "", t)
    t = t.replace("模块", "").replace("管理", "")
    return t.lower()


def clean_feature_label(s: str) -> str | None:
    """剥目录编号，丢掉非功能噪声；同材同果。

    「系统管理/首页管理」等空壳一律掐；「××管理员」是岗名，禁止剥成「××管理」。
    """
    t = _BULLET.sub("", (s or "").strip())
    t = re.sub(r"[。；;]+$", "", t).strip()
    for _ in range(2):
        nxt = _LEADING_FEAT_NUM.sub("", t).strip()
        if nxt == t:
            break
        t = nxt
    t = re.sub(r"\s+", " ", t).strip()
    if not t or len(t) < 2 or len(t) > 40:
        return None
    if t in ("系统功能模块", "功能模块", "管理", "模块") or t in _FEATURE_SHELL:
        return None
    # 岗名：系统管理员 / ××管理员 —— 不是「××管理」菜单
    if re.search(r"管理员$", t) and not t.endswith("管理"):
        return None
    # UML 类名不是功能菜单（写法多变时常见）
    if re.search(r"类等?$", t) and not t.endswith(("管理", "模块")):
        return None
    # 图题/「进入××模块」/口语尾巴——换开题仍会中的假功能
    if _FEATURE_JUNK.search(t):
        return None
    if re.search(r"[，、。；;！!？?]", t):
        return None
    if re.search(
        r"(?:注入|防御|攻击|加密算法|便于|分明|着重|展示前后|"
        r"使得|采用|集成|自身|代码|更加|各类|核心功能|"
        r"这些|可以|进行操作|操作和)",
        t,
    ):
        return None
    if re.search(r"[在的上等]|[a-z]", t) and t.endswith("模块"):
        return None
    if re.search(r"(?:功能)?测试$", t) or "测试的" in t:
        return None
    if re.search(r"(?:登录|注册)$", t) and not re.search(r"(?:管理|模块)$", t):
        return None
    if _IMPL_SHELL.search(t):
        return None
    if _FEAT_CHROME.search(t):
        return None
    if _NOISE_FEAT_TAIL.search(t):
        if _KEEP_FEAT_TAIL.search(t) and not re.search(
            r"(可行性|用例说明|安全需求|功能设计|序列图|时序图|用例图|类图|活动图|流程图|"
            r"背景|意义|概述)$",
            t,
        ):
            return t
        return None
    # 稳形态优先：××管理 / ××模块；入口短名次之
    if re.search(r"(?:管理|模块)$", t) and 4 <= len(t) <= 28:
        return t
    if re.search(r"(?:商城|入库|出库|订单|支付|审核|预约|借阅|首页|中心)$", t):
        return t
    if (
        2 <= len(t) <= 8
        and re.fullmatch(r"[\u4e00-\u9fff]+", t)
        and _BUSINESS_HINT.search(t)
    ):
        return t
    if _BUSINESS_HINT.search(t) and 4 <= len(t) <= 28:
        return t
    return None


def _feat_stem(s: str) -> str:
    return re.sub(r"(?:模块|管理|端)$", "", s or "").strip()


def _feat_rank(s: str) -> int:
    if s.endswith("管理"):
        return 3
    if s.endswith("模块"):
        return 2
    return 1


def finalize_feature_lines(items: list[str], *, limit: int = 16) -> list[str]:
    """清洗 + 同词干去重（厂商模块/厂商管理只留管理）。"""
    best: dict[str, str] = {}
    order: list[str] = []
    for raw in items or []:
        cleaned = clean_feature_label(raw)
        if not cleaned:
            continue
        stem = _feat_stem(cleaned) or cleaned
        prev = best.get(stem)
        if prev is None:
            best[stem] = cleaned
            order.append(stem)
            continue
        if _feat_rank(cleaned) > _feat_rank(prev):
            best[stem] = cleaned
    out = [best[s] for s in order if s in best]
    return out[:limit]


def clean_section_line(s: str) -> str | None:
    t = _BULLET.sub("", (s or "").strip())
    t = re.sub(r"\s+", " ", t).strip()
    if not t or _ROMAN_PAGE.fullmatch(t) or _BARE_SEC_NUM.fullmatch(t):
        return None
    if re.search(
        r"(?:可行性|用例图|序列图|时序图|类图|活动图|流程图|研究背景|研究现状|"
        r"研究意义|论文主要结构|系统测试概述|逻辑架构)$",
        t,
    ):
        return None
    if _SECTION_TOC_NOISE.search(t) and not _USEFUL_SEC.search(t):
        return None
    t = _LEADING_FEAT_NUM.sub("", t).strip()
    if not t or len(t) < 2 or len(t) > 40:
        return None
    return t


def finalize_section_lines(lines: list[str], *, limit: int = 8) -> list[str]:
    merged = coalesce_broken_lines([x for x in (lines or []) if isinstance(x, str)])
    out: list[str] = []
    seen: set[str] = set()
    for raw in merged:
        cleaned = clean_section_line(raw)
        if not cleaned:
            continue
        key = re.sub(r"\s+", "", cleaned)
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
        if len(out) >= limit:
            break
    return out


def _section_is_introish(heading: str) -> bool:
    h = collapse_pdf_glyph_spaces((heading or "").strip())
    return bool(
        re.search(r"绪论|摘要|引言|研究背景|国内外?研究", h)
        or re.match(r"^第\s*[1一]\s*章", h)
    )


def finalize_sections(
    sections: list[dict[str, Any]] | None,
    *,
    limit: int = 8,
    skip_intro: bool = True,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in sections or []:
        if not isinstance(s, dict):
            continue
        heading = collapse_pdf_glyph_spaces(str(s.get("heading") or "").strip())
        if not heading:
            continue
        if skip_intro and _section_is_introish(heading):
            continue
        lines = finalize_section_lines(
            s.get("lines") if isinstance(s.get("lines"), list) else [],
            limit=8,
        )
        if not lines:
            continue
        if not any(_USEFUL_SEC.search(x) for x in lines) and not _USEFUL_SEC.search(
            heading
        ):
            if not re.search(r"(?:实现|需求|功能|管理|模块|图注)", heading):
                continue
        out.append({"heading": heading, "lines": lines})
        if len(out) >= limit:
            break
    return out


def clean_background(text: str) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if not t or len(t) < 12:
        return ""
    if _BARE_SEC_NUM.match(t) or _SECTION_TOC_NOISE.search(t):
        return ""
    if re.match(r"^\d+(\.\d+)+\s*\S{0,24}$", t):
        return ""
    if re.match(r"^第.+[章节]", t):
        return ""
    return t[:240]


def _is_role_partition_module(label: str, roles: set[str]) -> bool:
    """仅「管理员模块/用户模块」这类端分区壳；设计清单里的「用户管理」要留。"""
    if not (label or "").endswith("模块"):
        return False
    stem = _feat_stem(label)
    return bool(stem) and stem in roles


def _finalize_entity_stem(stem: str, *, table_evidence: bool = False) -> str | None:
    """表名短词干。

    table_evidence=True：来自「××表」题注/库表采矿，允许「关于我们/投诉纠纷/系统简介」等真表名。
    无证据时仍禁导航壳与过程尾巴，避免 LLM/叙述发明。
    """
    t = (stem or "").strip()
    if t.endswith("表") and len(t) > 2:
        t = t[:-1]
    if t.endswith("管理") and len(t) > 2:
        t = t[: -len("管理")]
    if not t or len(t) < 2 or len(t) > 8:
        return None
    if t in _ENTITY_META:
        return None
    if t.endswith("数据") or t.startswith("本"):
        return None
    if not table_evidence:
        if t in _ENTITY_NAV:
            return None
        # 库表元叙述（本系统主要数据表如下）
        if "系统" in t:
            return None
        # 过程/动作尾巴不是表名
        if _ENTITY_PROCESS_TAIL.search(t):
            return None
    # 须整段符合表名词干形态（无助词、无「表」字）
    if not re.fullmatch(rf"(?:{_TABLE_NAME_CHAR}){{2,8}}", t):
        return None
    return t


def _normalize_table_title_to_entity(
    raw: str,
    *,
    table_evidence: bool | None = None,
) -> str | None:
    """从「××表」或已剥好的短词干收实体；禁止给叙述句末尾硬补「表」。

    命中「××表」构词 → 自动按题注证据放行；裸词干默认无证据（除非调用方声明）。
    """
    t = re.sub(r"\s+", "", (raw or "").strip())
    t = re.sub(r"[A-Za-z][A-Za-z0-9_]*", "", t)
    t = re.sub(r"（[^）]*）|\([^)]*\)", "", t)
    m2 = _TABLE_NAME_INLINE.search(t)
    if m2:
        ev = True if table_evidence is None else bool(table_evidence)
        return _finalize_entity_stem(m2.group(1), table_evidence=ev)
    # entity_hints 已是短词干：整段须已是合格名词形态
    if re.fullmatch(rf"(?:{_TABLE_NAME_CHAR}){{2,8}}", t):
        ev = bool(table_evidence) if table_evidence is not None else False
        return _finalize_entity_stem(t, table_evidence=ev)
    return None


def _db_design_text_slice(text: str) -> str:
    """只保留数据库/表设计附近正文，躲开序列图长叙述。"""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return ""
    keep: list[str] = []
    on = False
    for ln in lines:
        if re.search(
            r"(?:数据库设计|物理结构|逻辑设计|表设计|数据字典|数据表设计|"
            r"概念结构|逻辑结构|数据库实现)",
            ln,
        ):
            on = True
        if on and re.search(
            r"(?:^第.{1,8}[章节]|系统实现|功能实现|序列图|时序图|类图|活动图|系统测试)",
            ln,
        ):
            if not re.search(r"(?:数据库|表设计|物理结构|逻辑结构|概念结构)", ln):
                on = False
                continue
        if on:
            keep.append(ln)
    captions = [ln for ln in lines if _TABLE_CAPTION_LINE.search(ln)]
    if keep:
        # 题注可能在切片外，并入
        extra = [ln for ln in captions if ln not in keep]
        return "\n".join(keep + extra)
    return "\n".join(captions)


def _line_allows_inline_table_name(line: str) -> bool:
    """长叙述行不扫行首「××表」；短行、枚举行或表定义行才信。"""
    s = (line or "").strip()
    if not s:
        return False
    if len(s) <= 48:
        return True
    if _TABLE_NAME_AFTER_ENUM.match(re.sub(r"\s+", "", s)):
        return True
    return bool(_LINE_TABLE_DEF.search(s))


def extract_entity_labels_from_text(text: str, *, limit: int = 32) -> list[str]:
    """P1：数据库章表题注 / 小节标题 / 表名： / 行首××表 → 实体。"""
    db_body = _db_design_text_slice(text) or ""
    lines_all = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    # 优先在库表切片内挖；切片为空则退回全篇题注
    scan_lines = (
        [ln.strip() for ln in db_body.splitlines() if ln.strip()]
        if db_body
        else [ln for ln in lines_all if _TABLE_CAPTION_LINE.search(ln)]
    )
    out: list[str] = []
    seen: set[str] = set()

    def _push(raw: str) -> bool:
        ent = _normalize_table_title_to_entity(raw)
        if not ent or ent in seen:
            return len(out) >= limit
        seen.add(ent)
        out.append(ent)
        return len(out) >= limit

    for ln in scan_lines:
        collapsed = re.sub(r"\s+", "", ln)
        # 1) 表 4.x 题注
        if _TABLE_CAPTION_LINE.search(collapsed):
            rest = _TABLE_CAPTION_LINE.sub("", collapsed, count=1)
            m = _TABLE_NAME_AT_LINE_START.match(rest) or _TABLE_NAME_INLINE.search(rest)
            if m and _push(m.group(1) + "表"):
                return out
            continue
        # 2) 表名：…
        m_lab = _TABLE_NAME_LABEL.search(collapsed)
        if m_lab and _push(m_lab.group(1) + "表"):
            return out
        # 3) 4.3.1 用户信息表 / （1）订单表
        m_en = _TABLE_NAME_AFTER_ENUM.match(collapsed)
        if m_en and _push(m_en.group(1) + "表"):
            return out
        # 4) 行首 ××表…（××表包含字段）
        if not _line_allows_inline_table_name(ln):
            continue
        m_st = _TABLE_NAME_AT_LINE_START.match(collapsed)
        if m_st and _push(m_st.group(1) + "表"):
            return out
    return out


def suggest_drafts_from_proposal(proposal: dict[str, Any] | None) -> dict[str, list[str]]:
    """角色 / 实体 / 功能三分法（结构线索，禁行业私榜）。

    功能 = 设计各端清单原样（去端分区壳）；角色进 roles；
    实体 = 库表题注/××表（§3.2），禁止掐「××管理」词干充数。
    """
    prop = proposal or {}
    raw_feats = [x for x in list(prop.get("feature_lines") or []) if isinstance(x, str)]
    module_hints = [
        x for x in list(prop.get("module_hints") or []) if isinstance(x, str)
    ]
    feats = finalize_feature_lines(raw_feats + module_hints, limit=32)

    role_hints = [
        str(x).strip()
        for x in list(prop.get("role_hints") or [])
        if isinstance(x, str) and str(x).strip()
    ]
    if not role_hints:
        blob = str(prop.get("excerpt") or prop.get("background") or "")
        role_hints = extract_role_labels(
            blob,
            module_names=[m for m in module_hints if str(m).endswith("模块")]
            + [f for f in raw_feats + feats if str(f).endswith("模块")],
        )
    roles: list[str] = []
    seen_r: set[str] = set()
    for stem in role_hints:
        if stem and stem not in seen_r and stem not in _ENTITY_SKIP:
            seen_r.add(stem)
            roles.append(stem)

    # 保留设计「××管理」；只去掉「××模块」端分区
    biz_feats = [f for f in feats if f and not _is_role_partition_module(f, seen_r)]

    # 实体：只认库表 entity_hints。与角色同名（用户表/厂商表）仍进实体，禁止互剔
    entities: list[str] = []
    seen_e: set[str] = set()

    def _add_entity(raw: str) -> None:
        # hints 来自题注采矿，按证据放行
        ent = _normalize_table_title_to_entity(raw, table_evidence=True)
        if not ent or ent in seen_e:
            return
        seen_e.add(ent)
        entities.append(ent)

    for lab in list(prop.get("entity_hints") or []):
        if isinstance(lab, str):
            _add_entity(lab)
    return {
        "draft_roles": roles[:8],
        "draft_entities": entities[:24],
        "draft_features": biz_feats[:32],
    }


_DRAFT_BAN = re.compile(
    r"(?:前端|后端|协议|传输|回传|控制器|可进入|点击|填写|登录后|如图|所示|"
    r"标准化并|反馈给|作为前|作为后|注重模块|与基础|与个性化)"
)


def contract_roles_from_proposal(proposal: dict[str, Any] | None) -> list[str]:
    """合同形态角色：××端 / 已清洗 role_hints / 结构端名。

    不是遣词穷举；无 LLM 时也不该角色全空（管理员端·用户端写在材料里）。
    """
    from app.services.proposal import _normalize_role_stem

    prop = proposal or {}
    out: list[str] = []
    seen: set[str] = set()

    def _push(raw: str) -> None:
        stem = _normalize_role_stem(raw)
        if not stem or stem in seen or stem in _ENTITY_SKIP:
            return
        seen.add(stem)
        out.append(stem)

    for raw in list(prop.get("role_hints") or []):
        if isinstance(raw, str):
            _push(raw)
    for raw in list(prop.get("structure_ends") or []):
        if isinstance(raw, str):
            _push(raw)
    # 实体里已有岗名壳且角色仍空时，补合同壳（用户/管理员）
    if not out:
        for raw in list(prop.get("entity_hints") or []):
            if not isinstance(raw, str):
                continue
            ent = _normalize_table_title_to_entity(raw, table_evidence=True) or raw.strip()
            if ent in ("用户", "管理员", "超级管理员", "厂商", "经销商"):
                _push(ent)
    return out[:8]


def fallback_drafts_no_llm(proposal: dict[str, Any] | None) -> dict[str, list[str]]:
    """无 LLM：实体仅表题注；角色回填合同端名；功能空（功能交给有模型时主抽）。"""
    prop = proposal or {}
    entities: list[str] = []
    seen: set[str] = set()
    for lab in list(prop.get("entity_hints") or []):
        if not isinstance(lab, str):
            continue
        ent = _normalize_table_title_to_entity(lab, table_evidence=True)
        if ent and ent not in seen:
            seen.add(ent)
            entities.append(ent)
    return {
        "draft_roles": contract_roles_from_proposal(prop),
        "draft_entities": entities[:24],
        "draft_features": [],
    }


def _seed_entities_from_evidence(
    *,
    table_captions: list[str] | None = None,
    entity_hints: list[str] | None = None,
    limit: int = 24,
) -> list[str]:
    """题注 / entity_hints 并入实体栏（证据优先，换开题不用手擦漏表）。"""
    out: list[str] = []
    seen: set[str] = set()
    for raw in list(entity_hints or []) + list(table_captions or []):
        if not isinstance(raw, str):
            continue
        ent = _normalize_table_title_to_entity(raw, table_evidence=True)
        if not ent or ent in seen:
            continue
        seen.add(ent)
        out.append(ent)
        if len(out) >= limit:
            break
    return out


def normalize_llm_drafts(
    roles: Any,
    entities: Any,
    features: Any,
    *,
    table_captions: list[str] | None = None,
    entity_hints: list[str] | None = None,
    design_features: list[str] | None = None,
    confirm_features: list[str] | None = None,
) -> dict[str, list[str]]:
    """形态钳子：清洗 LLM 短名；实体以题注为底。

    不跟正则采矿的「遣词清单」绑死——写法由 LLM 读；
    design_features 仅兼容旧调用，不作硬门闩。
    有厚实现/图交叉时，用 confirm 挡胡编，不挡换说法。
    """
    seeded = _seed_entities_from_evidence(
        table_captions=table_captions,
        entity_hints=entity_hints,
        limit=24,
    )
    cap_set = set(seeded)
    _ = design_features  # 兼容保留；产品不跟正则遣词清单走
    confirm_anchors = finalize_feature_lines(
        [str(x) for x in (confirm_features or []) if str(x).strip()],
        limit=48,
    )

    def _clean_list(
        raw: Any,
        *,
        limit: int,
        as_entity: bool = False,
        as_feature: bool = False,
    ) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        if not isinstance(raw, list):
            return out
        for x in raw:
            s = re.sub(r"\s+", "", str(x or "").strip())
            if not s:
                continue
            if as_entity:
                ent = _normalize_table_title_to_entity(s, table_evidence=False)
                if not ent:
                    continue
                s = ent
            if len(s) < 2 or len(s) > 12:
                continue
            if _DRAFT_BAN.search(s):
                continue
            if s.startswith(("与", "及", "和")):
                continue
            if not re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9]+", s):
                continue
            if as_feature:
                cleaned = clean_feature_label(s)
                if not cleaned:
                    continue
                s = cleaned
            elif not as_entity:
                # 角色：轻洗，禁止套功能 clean（会误杀「用户」）
                if s.endswith("类") and len(s) <= 5:
                    continue
            if as_entity and cap_set and s not in cap_set:
                if not any(s in c or c in s for c in cap_set):
                    continue
            if s in seen:
                continue
            seen.add(s)
            out.append(s)
            if len(out) >= limit:
                break
        return out

    llm_ents = _clean_list(entities, limit=24, as_entity=True)
    merged_ents: list[str] = []
    seen_e: set[str] = set()
    for e in seeded + llm_ents:
        if e and e not in seen_e:
            seen_e.add(e)
            merged_ents.append(e)
            if len(merged_ents) >= 24:
                break

    llm_feats = finalize_feature_lines(
        _clean_list(features, limit=32, as_feature=True),
        limit=32,
    )
    if confirm_anchors and _confirm_is_substantial(confirm_anchors):
        kept = [
            f for f in llm_feats if _feat_confirmed_strict(f, confirm_anchors)
        ]
        feats_out = finalize_feature_lines(kept or llm_feats, limit=32)
    else:
        feats_out = llm_feats

    return {
        "draft_roles": _clean_list(roles, limit=8),
        "draft_entities": merged_ents,
        "draft_features": feats_out,
    }


def _pack_text(lines: list[str], *, limit: int) -> str:
    blob = "\n".join(ln.strip() for ln in lines if ln and str(ln).strip())
    blob = _collapse_ws(blob) if blob else ""
    if len(blob) <= limit:
        return blob
    return blob[: limit - 1] + "…"


def build_absorb_evidence(
    text: str,
    *,
    proposal: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """章节温度证据包：原文切片 + 表题注；供 LLM，不发明三栏。"""
    raw = normalize_thesis_text((text or "").strip())
    buckets = split_buckets(raw)
    prop = proposal or {}
    title = str(prop.get("title") or "").strip()

    def _bucket_lines(name: str) -> list[str]:
        out: list[str] = []
        for _h, lines in buckets.get(name) or []:
            out.extend(coalesce_broken_lines(lines))
        return out

    req = _bucket_lines("req")
    design = _bucket_lines("design")
    impl = _bucket_lines("impl")
    test = _bucket_lines("test")

    # 设计桶拆：库表段 vs 模块段（库表命中行优先进 P1-tables）
    db_lines: list[str] = []
    mod_lines: list[str] = []
    on_db = False
    for ln in design:
        if re.search(
            r"(?:数据库设计|物理结构|逻辑设计|表设计|数据字典|概念结构)",
            ln,
        ):
            on_db = True
        if on_db and re.search(
            r"(?:系统实现|功能实现|序列图|时序图|类图|系统测试|^第.{1,8}[章节])",
            ln,
        ):
            on_db = False
        (db_lines if on_db else mod_lines).append(ln)

    captions = list(prop.get("entity_hints") or [])
    if not captions:
        captions = extract_entity_labels_from_text("\n".join(design), limit=24)
    # 题注原行（带「表」）供展示
    cap_rows: list[str] = []
    for ln in design:
        collapsed = re.sub(r"\s+", "", ln)
        if _TABLE_CAPTION_LINE.search(collapsed) and "表" in collapsed:
            cap_rows.append(ln.strip()[:80])
    fig_labs = [
        str(x) for x in list(prop.get("figure_labels") or []) if isinstance(x, str)
    ]

    packs: list[dict[str, str]] = []
    if title:
        packs.append({"grade": "P0", "title": "题名", "text": title})
    packs.append(
        {
            "grade": "P2",
            "title": "需求用例",
            "text": _pack_text(req, limit=3500),
        }
    )
    packs.append(
        {
            "grade": "P1-modules",
            "title": "模块设计",
            "text": _pack_text(mod_lines or design, limit=4000),
        }
    )
    packs.append(
        {
            "grade": "P1-tables",
            "title": "库表设计",
            "text": _pack_text(db_lines or design[-80:], limit=3000),
        }
    )
    p3 = _pack_text(impl[:40] + test[:20], limit=1500)
    if p3:
        packs.append({"grade": "P3", "title": "实现测试", "text": p3})
    if fig_labs:
        packs.append(
            {
                "grade": "P4",
                "title": "图标签",
                "text": "、".join(fig_labs[:40]),
            }
        )

    return {
        "title": title,
        "packs": packs,
        "table_captions": [c for c in captions if c][:24],
        "table_caption_rows": cap_rows[:24],
        "thin_p1": not bool(design),
        "thin_p2": not bool(req),
    }


def _feat_confirmed(cand: str, anchors: list[str]) -> bool:
    n = _normalize_feat(cand)
    if not n or len(n) < 2:
        return False
    for a in anchors:
        m = _normalize_feat(a)
        if m and (n in m or m in n):
            return True
    return False


# 过短词干互配会把「用户管理」和任意「用户××」糊在一起
_FEAT_WEAK_STEM = frozenset(
    {"用户", "订单", "系统", "管理", "信息", "数据", "个人", "首页", "公告"}
)


def _admin_title_peel_collision(short: str, long: str) -> bool:
    """短词干是长岗名「××员…」前缀 → 不算同实义（仓库管理 ⊄ 仓库管理员）。"""
    if not short or not long or short == long:
        return False
    if long.startswith(short + "员") or short.startswith(long + "员"):
        return True
    return False


def _feat_confirmed_strict(cand: str, anchors: list[str]) -> bool:
    """交叉验证：同实义才算对上；禁止过短光杆乱配、岗名剥壳假交叉。"""
    n = _normalize_feat(cand)
    if not n or len(n) < 2:
        return False
    for a in anchors:
        m = _normalize_feat(a)
        if not m:
            continue
        if _admin_title_peel_collision(n, m) or _admin_title_peel_collision(m, n):
            continue
        if n == m:
            return True
        if n in _FEAT_WEAK_STEM or m in _FEAT_WEAK_STEM:
            # 弱词干：要求更长一侧包含，且两端都不是纯弱词干互啄
            if n in _FEAT_WEAK_STEM and m in _FEAT_WEAK_STEM:
                continue
            longer, shorter = (m, n) if len(m) >= len(n) else (n, m)
            if _admin_title_peel_collision(shorter, longer):
                continue
            # 「首页」弱干不得凭「系统首页」放行假菜单「首页管理」
            if shorter == "首页" and "首页" in longer and shorter != longer:
                continue
            if len(shorter) >= 2 and shorter in longer and len(longer) >= len(shorter) + 2:
                return True
            continue
        if n in m or m in n:
            return True
    return False


_ACTOR_FEAT_PREFIX = re.compile(
    r"^(?:系统)?(?:管理员|用户端|厂商端|经销商端|仓库管理员|馆员|用户|厂商|经销商)"
)


def _strip_actor_feature_prefix(label: str) -> str | None:
    """管理员用户管理 → 用户管理；不把系统管理员剥成系统管理。"""
    t = re.sub(r"\s+", "", (label or "").strip())
    if not t:
        return None
    if re.search(r"管理员$", t) and not t.endswith("管理"):
        return None
    t2 = _ACTOR_FEAT_PREFIX.sub("", t)
    if not t2 or t2 == t:
        return None
    if t2 in _FEATURE_SHELL or t2 in ("管理", "模块"):
        return None
    # 剥完只剩空壳尾巴（经销商管理→管理）→ 丢掉，保留原标签由调用方决定
    if len(t2) < 4:
        return None
    return clean_feature_label(t2) or (
        t2 if t2.endswith(("管理", "模块")) and 4 <= len(t2) <= 16 else None
    )


def _impl_confirm_labels(lines: list[str], *, limit: int = 40) -> list[str]:
    """P3 实现章：具体菜单/小节名作交叉锚（含去角色前缀）。"""
    raw = _lines_to_features(lines, intro=False)
    extra: list[str] = []
    for ln in lines or []:
        collapsed = _collapse_ws(ln)
        collapsed = _LEADING_FEAT_NUM.sub("", collapsed)
        # 只信短行/小节标题，躲开「厂商进入钢材管理界面」长叙述
        if len(collapsed) > 28 and not re.match(
            r"^(?:\d+(?:\.\d+){1,3})?",
            collapsed,
        ):
            # 有 5.4.x 小节号仍收；纯长叙述跳过
            if not re.match(r"^\d+(?:\.\d+){1,3}", collapsed):
                continue
        for m in re.finditer(
            rf"((?:系统)?(?:管理员|用户|厂商|经销商))?([\u4e00-\u9fff]{{2,12}}{_MGMT_OR_MODULE_TAIL})",
            collapsed,
        ):
            full = ((m.group(1) or "") + m.group(2)).strip()
            if "进入" in full or full.startswith("通过"):
                continue
            # 岗名正文「仓库管理员」不得截成「仓库管理」
            end = m.end()
            if end < len(collapsed) and collapsed[end] == "员":
                continue
            cleaned = clean_feature_label(full)
            if cleaned:
                extra.append(cleaned)
            stripped = _strip_actor_feature_prefix(full)
            if stripped:
                extra.append(stripped)
            bare = clean_feature_label(m.group(2))
            if bare:
                extra.append(bare)
    for x in list(raw):
        if "进入" in str(x) or str(x).startswith("通过"):
            continue
        stripped = _strip_actor_feature_prefix(x)
        if stripped:
            extra.append(stripped)
    return finalize_feature_lines(raw + extra, limit=limit)


def _confirm_is_substantial(confirms: list[str]) -> bool:
    """实现/图交叉锚够厚才启用「提到∩实义」硬收；一句实现带过不算。"""
    cleaned = finalize_feature_lines(list(confirms or []), limit=48)
    solid = [
        c
        for c in cleaned
        if c.endswith(("管理", "模块")) and c not in _FEATURE_SHELL and len(c) >= 4
    ]
    return len(solid) >= 3


def admit_features_faithful(
    mentions: list[str],
    confirms: list[str],
    *,
    limit: int = 32,
    require_substantial: bool = True,
) -> list[str]:
    """忠于原文：设计提到 ∩ 实现/图交叉有实义 → 才进功能栏。

    交叉锚不够厚时退回设计清单（仍掐空壳），由上层告警弱抽。
    """
    mentioned = finalize_feature_lines(list(mentions or []), limit=48)
    confirmed = finalize_feature_lines(list(confirms or []), limit=48)
    if not confirmed:
        return mentioned[:limit]
    if require_substantial and not _confirm_is_substantial(confirmed):
        return mentioned[:limit]
    out: list[str] = []
    seen: set[str] = set()

    def _push(lab: str) -> None:
        if not lab or lab in seen or lab in _FEATURE_SHELL:
            return
        seen.add(lab)
        out.append(lab)

    # 设计点名且能在实现/图对上 → 用设计名
    for m in mentioned:
        if _feat_confirmed_strict(m, confirmed):
            _push(m)
    # 实现/图具体菜单且能在设计对上 → 优先去角色前缀后的短名
    for c in confirmed:
        if not _feat_confirmed_strict(c, mentioned):
            continue
        stripped = _strip_actor_feature_prefix(c)
        _push(stripped or c)
    return finalize_feature_lines(out, limit=limit)


def _cross_check_warnings(
    *,
    roles: list[str],
    design_ends: list[str],
    design_feats: list[str],
    figure_labels: list[str],
    impl_feats: list[str],
    test_feats: list[str],
) -> list[str]:
    """§3.0b 交叉验证告警（不脑补改清单）。"""
    warnings: list[str] = []
    role_set = {_normalize_feat(r) for r in roles if _normalize_feat(r)}
    end_set = {_normalize_feat(e) for e in design_ends if _normalize_feat(e)}
    if role_set and end_set:
        only_role = [r for r in roles if _normalize_feat(r) not in end_set
                     and not any(_normalize_feat(r) in e or e in _normalize_feat(r) for e in end_set)]
        only_end = [e for e in design_ends if _normalize_feat(e) not in role_set
                    and not any(_normalize_feat(e) in r or r in _normalize_feat(e) for r in role_set)]
        if only_role or only_end:
            warnings.append("角色与端不一致")

    if figure_labels and design_feats:
        fig_n = {_normalize_feat(x) for x in figure_labels if _normalize_feat(x)}
        des_n = {_normalize_feat(x) for x in design_feats if _normalize_feat(x)}
        only_fig = [
            x
            for x in figure_labels
            if not any(
                _normalize_feat(x) in d or d in _normalize_feat(x) for d in des_n if d
            )
        ]
        only_des = [
            x
            for x in design_feats
            if not any(
                _normalize_feat(x) in f or f in _normalize_feat(x) for f in fig_n if f
            )
        ]
        if only_fig and not only_des:
            warnings.append(
                "结构图有、文字清单无：" + "、".join(only_fig[:4]) + "（待确认，不自动进主清单）"
            )
        elif only_des and not only_fig:
            warnings.append(
                "文字清单有、结构图未读到：" + "、".join(only_des[:4]) + "（待确认）"
            )
        elif only_fig and only_des:
            warnings.append("结构图标签与文字模块清单仅部分重合，待确认")
    elif design_feats and not figure_labels:
        # 有设计功能但无图侧标签：可能未 OCR；上层会另告题注
        pass

    if design_feats and impl_feats:
        missing_impl = [
            f for f in design_feats
            if not _feat_confirmed(f, impl_feats)
        ]
        if len(missing_impl) >= max(2, len(design_feats) // 2):
            warnings.append("设计有实现无：" + "、".join(missing_impl[:4]))
        extra_impl = [
            f for f in impl_feats
            if not _feat_confirmed(f, design_feats) and not _IMPL_SHELL.search(f)
        ]
        # 实现多出来的不进主清单；只告警
        if extra_impl and len(extra_impl) >= 3:
            warnings.append("实现有设计未列的入口，未写入功能主清单")

    if design_feats and test_feats:
        extra_test = [
            f
            for f in test_feats
            if not _feat_confirmed(f, design_feats) and not _looks_like_test_prose(f)
        ]
        if extra_test:
            warnings.append(
                "测试用例提到设计未列的能力名（仅告警，不进不做清单）："
                + "、".join(extra_test[:4])
            )

    return warnings


def _design_end_labels(design_blob: str) -> list[str]:
    """设计章「××端」列举，供与 P2 角色交叉。"""
    out: list[str] = []
    seen: set[str] = set()
    # 优先完整「××端功能/模块/设计」；裸「端」易吞叙述
    for m in re.finditer(
        r"([\u4e00-\u9fff]{2,6})端(?:功能|模块|用户|界面|设计)",
        design_blob or "",
    ):
        stem = m.group(1)
        if stem in ("前", "后", "客户", "服务", "移动", "管理系") or stem in seen:
            continue
        if stem in ("系统", "功能", "业务"):
            continue
        # 叙述粘连（数据返回至经销商端…）
        if re.search(r"(?:传递|返回|充当|协议|界面|渲染|控制)", stem):
            continue
        if len(stem) > 4 and not stem.endswith(("员", "户", "商", "师", "者", "理")):
            # 过长且不像岗名：只留常见短端
            if stem not in ("管理", "用户", "厂商", "经销商", "买家", "卖家"):
                continue
        seen.add(stem)
        out.append(stem)
    return out[:8]


def extract_thesis_proposal(text: str) -> dict[str, Any]:
    """确定性抽取终稿 → proposal 同名形状 + 告警（§3 梯子）。"""
    raw = normalize_thesis_text((text or "").strip())
    buckets = split_buckets(raw)

    abstract_lines: list[str] = []
    for _h, lines in buckets.get("abstract") or []:
        abstract_lines.extend(lines)

    intro_lines: list[str] = []
    for _h, lines in buckets.get("intro") or []:
        intro_lines.extend(lines)

    bucket_lines: dict[str, list[str]] = {
        k: [] for k in ("req", "design", "impl", "test")
    }
    sections: list[dict[str, Any]] = []
    for bucket in ("req", "design", "impl", "test"):
        for heading, lines in buckets.get(bucket) or []:
            merged = coalesce_broken_lines(lines)
            bucket_lines[bucket].extend(merged)
            if heading and merged:
                sections.append({"heading": heading, "lines": merged[:12]})
    sections = finalize_sections(sections, limit=8, skip_intro=True)

    # —— P1 功能主矿：仅设计桶（含「包含××管理」清单）——
    # 采矿用捏合空白后的 blob（抗 PDF 词中换行）；展示仍用原行
    design_blob = "\n".join(bucket_lines["design"])
    design_compact = _collapse_ws(design_blob)
    # P2 正文先拼上，供设计清单误进需求时回收
    req_blob = "\n".join(bucket_lines["req"])
    req_compact = _collapse_ws(req_blob)
    design_feats = _lines_to_features(bucket_lines["design"], intro=False)
    design_includes = extract_included_mgmt_items(design_compact)
    # 「××端分为…其中包含」是设计腔；分桶误进需求时仍回收，不扫实现章
    if not design_includes:
        design_includes = extract_included_mgmt_items(req_compact)
    design_modules = (
        extract_inline_modules(design_compact)
        + extract_module_lines(design_blob)
    )

    # P2：需求桶只服务角色（不当功能主矿）
    req_modules = extract_inline_modules(req_compact) + extract_module_lines(req_blob)

    # P3：交叉锚（具体菜单）；禁止用实现章单独灌满主清单
    impl_feats = _impl_confirm_labels(bucket_lines["impl"], limit=40)
    # 测试只抽能力名做交叉验货；步骤句不进功能、不进不做
    test_feats = _test_capability_labels(bucket_lines["test"])

    # §3.1 绪论例外：仅当后文设计/需求有对应才收
    intro_cands = _lines_to_features(intro_lines, intro=True)
    later_anchor = design_feats + design_includes + design_modules + req_modules
    intro_ok = [f for f in intro_cands if _feat_confirmed(f, later_anchor)]

    module_hints: list[str] = []
    seen_m: set[str] = set()
    for x in design_includes + design_modules + req_modules:
        if x not in seen_m and x not in ("系统功能模块", "功能模块"):
            seen_m.add(x)
            module_hints.append(x)

    # 忠于原文：交叉锚够厚时「设计提到 ∩ 实现实义」；否则设计弱抽（仍掐空壳/岗名）
    mention_pool = design_includes + design_feats + design_modules + intro_ok
    confirm_pool = impl_feats + test_feats
    feature_lines = admit_features_faithful(
        mention_pool,
        confirm_pool,
        limit=32,
        require_substantial=True,
    )

    # 「不做」只收绪论明确否定；测试是实现验货，禁止把用例步骤标成不做
    out_scope = _out_scope_from_intro(intro_lines)

    base = summarize_proposal(raw, hits=[])
    base["hits"] = []
    # 开题 summarize 的 out_scope 易把测试折行/正文误收成碎片；终稿吸收不用
    base["out_scope_lines"] = out_scope[:12]

    # P5 摘要优先作 background
    abs_bg = ""
    for ln in abstract_lines:
        cand = clean_background(ln)
        if len(cand) >= 12:
            abs_bg = cand
            break
    base["background"] = abs_bg or clean_background(str(base.get("background") or ""))

    if feature_lines:
        base["feature_lines"] = feature_lines
    else:
        # 缺 P1 → 弱抽；禁止用实现章顶替
        base["feature_lines"] = []

    base["module_hints"] = module_hints[:12]
    # P1 库表实体线索（设计桶正文）；图侧 table_labels 另合，不在此掐功能词干
    base["entity_hints"] = extract_entity_labels_from_text(
        design_blob + "\n" + "\n".join(bucket_lines.get("design") or []),
        limit=24,
    )

    # 角色：P2 需求正文优先，设计「××端」+ 列举句补齐
    role_scan_blob = req_blob + "\n" + design_blob
    if not role_scan_blob.strip():
        role_scan_blob = raw
    design_ends = _design_end_labels(design_blob)
    # 角色模块线索：只认设计「××端」；禁止把「交流论坛模块」等功能模块充角色
    role_module_names: list[str] = []
    seen_rm: set[str] = set()
    for x in design_ends:
        if not x:
            continue
        name = f"{x}模块" if not str(x).endswith("模块") else str(x)
        if name not in seen_rm:
            seen_rm.add(name)
            role_module_names.append(name)
    base["role_hints"] = extract_role_labels(
        role_scan_blob,
        module_names=role_module_names,
    )

    by_h: dict[str, dict[str, Any]] = {}
    for s in sections:
        by_h[s["heading"]] = s
    for s in base.get("sections") or []:
        if isinstance(s, dict) and s.get("heading") and s["heading"] not in by_h:
            by_h[s["heading"]] = s
    base["sections"] = finalize_sections(list(by_h.values()), limit=8, skip_intro=True)

    figure_labels = [
        str(x) for x in list(base.get("figure_labels") or []) if isinstance(x, str)
    ]
    warnings = _cross_check_warnings(
        roles=list(base["role_hints"]),
        design_ends=design_ends,
        design_feats=feature_lines,
        figure_labels=figure_labels,
        impl_feats=impl_feats,
        test_feats=test_feats,
    )

    # 缺 P1 各端清单 → 弱抽
    fl = base.get("feature_lines") or []
    thin = len(fl) < THIN_FEATURE_THRESHOLD
    if thin and not any("缺" in w for w in warnings):
        if not bucket_lines["design"]:
            warnings.append("未采到总体设计各端功能清单（P1），禁止用实现章顶替")
    # 有设计但交叉锚不够厚 → 功能弱抽（未达「提到+实义」）
    if (
        bucket_lines["design"]
        and fl
        and not _confirm_is_substantial(confirm_pool)
        and not figure_labels
        and not any("缺实现" in w or "交叉" in w for w in warnings)
    ):
        warnings.append("缺实现/结构图交叉，功能仅按设计清单弱抽")

    return {
        "proposal": base,
        "warnings": warnings,
        "thin_features": thin,
        "ok_to_feed": not thin,
        "extract_warning": "thin_features" if thin else (
            "cross_check" if warnings else None
        ),
        "extractor_version": EXTRACTOR_VERSION,
        "bucket_stats": {
            k: sum(len(lines) for _h, lines in (buckets.get(k) or []))
            for k in ("abstract", "intro", "req", "design", "impl", "test", "discard")
        },
    }


def _roles_ends_aligned(roles: list[str], ends: list[str]) -> bool:
    if not roles or not ends:
        return False
    role_n = [_normalize_feat(r) for r in roles if _normalize_feat(r)]
    end_n = [_normalize_feat(e) for e in ends if _normalize_feat(e)]
    for r in role_n:
        if not any(r == e or r in e or e in r for e in end_n):
            return False
    for e in end_n:
        if not any(e == r or e in r or r in e for r in role_n):
            return False
    return True


def apply_figure_cross_check(
    result: dict[str, Any],
    figure_labels: list[str],
    *,
    structure_ends: list[str] | None = None,
) -> dict[str, Any]:
    """图侧标签/端名并入交叉告警。只在一边 → 待确认；不砍 feature_lines。"""
    prop = dict(result.get("proposal") or {})
    feats = list(prop.get("feature_lines") or [])
    roles = list(prop.get("role_hints") or [])
    ends = list(structure_ends or prop.get("structure_ends") or [])
    fig_labs = [str(x) for x in (figure_labels or []) if str(x).strip()]
    # 只用图题端名重算角色交叉（覆盖正文误抽端导致的假红）
    extra = _cross_check_warnings(
        roles=roles,
        design_ends=list(ends),
        design_feats=feats,
        figure_labels=fig_labs,
        impl_feats=[],
        test_feats=[],
    )
    warns = [w for w in list(result.get("warnings") or []) if w != "角色与端不一致"]
    if ends and _roles_ends_aligned(roles, ends):
        extra = [w for w in extra if w != "角色与端不一致"]
    for w in extra:
        if w not in warns:
            warns.append(w)
    result["warnings"] = warns
    if fig_labs:
        prop["figure_labels"] = fig_labs[:40]
    if ends:
        prop["structure_ends"] = ends[:8]
    result["proposal"] = prop
    return result


def build_feed_markdown(
    *,
    record_id: int | str,
    coverage: str,
    proposal: dict[str, Any],
    draft_roles: list[str] | None = None,
    draft_entities: list[str] | None = None,
    draft_features: list[str] | None = None,
) -> str:
    cov = (coverage or "unknown").strip() or "unknown"
    heads = {
        "covered": (
            "验证工厂已覆盖；勿新开域；可协助第 2 刀回归；"
            "本稿来自终稿吸收，不是出包订单。"
        ),
        "skin_gap": (
            "修工厂·只补皮；能皮就皮；禁止只擦当面 ZIP；"
            "本稿来自终稿吸收，不是出包订单。"
        ),
        "domain_gap": (
            "修工厂·挂 cap 或薄开 DOM；禁止平行旁路与只擦 ZIP；"
            "本稿来自终稿吸收，不是出包订单。"
        ),
        "unknown": (
            "先做覆盖判断（已齐/差皮/差域），再动手；"
            "本稿来自终稿吸收，不是出包订单。"
        ),
    }
    head = heads.get(cov, heads["unknown"])
    feats = finalize_feature_lines(list(proposal.get("feature_lines") or []), limit=20)
    outs = proposal.get("out_scope_lines") or []
    secs = finalize_sections(
        [s for s in (proposal.get("sections") or []) if isinstance(s, dict)],
        limit=6,
        skip_intro=True,
    )
    roles = [str(x).strip() for x in (draft_roles or []) if str(x).strip()]
    entities = [str(x).strip() for x in (draft_entities or []) if str(x).strip()]
    dfeats = [str(x).strip() for x in (draft_features or []) if str(x).strip()]
    if not roles and not entities and not dfeats:
        sug = suggest_drafts_from_proposal(proposal)
        roles = sug["draft_roles"]
        entities = sug["draft_entities"]
        dfeats = sug["draft_features"]

    lines = [
        "【给助手】",
        head,
        "",
        "【要点】",
        "功能/模块：",
    ]
    if feats:
        lines.extend(f"- {x}" for x in feats)
    else:
        lines.append("- （无）")
    lines.append("")
    lines.append("不交/双显：")
    if outs:
        lines.extend(f"- {x}" for x in outs)
    else:
        lines.append("- （无）")
    lines.append("")
    lines.append("【补齐建议】")
    lines.append("角色：" + ("、".join(roles) if roles else "（无）"))
    lines.append("实体：" + ("、".join(entities) if entities else "（无）"))
    lines.append("功能：")
    if dfeats:
        lines.extend(f"- {x}" for x in dfeats)
    else:
        lines.append("- （无）")
    if secs:
        lines.append("")
        lines.append("实现相关摘句：")
        for sec in secs:
            h = sec.get("heading") or "（无标题）"
            lines.append(f"· {h}")
            for ln in (sec.get("lines") or [])[:6]:
                lines.append(f"  - {ln}")
    lines.extend(
        [
            "",
            "【指针】",
            "对照 docs/domain-skin-onboarding.md、docs/domain-skin-gap-analysis.md。",
            f"本稿来自终稿吸收 id={record_id}；不是出包订单。",
            "",
            "【禁令】",
            "不得发明未出现的能力；不得将本稿当作已匹配出包；"
            "不交项见上，禁止假交。",
        ]
    )
    return "\n".join(lines)


def build_opening_draft(proposal: dict[str, Any]) -> str:
    """第 1 刀：由结构反推开题稿（不含原题名/届次）。"""
    feats = finalize_feature_lines(list(proposal.get("feature_lines") or []), limit=20)
    bg = clean_background(str(proposal.get("background") or ""))
    lines = [
        "某业务系统开题（由终稿吸收结构反推，非原题名）",
        "",
        "一、研究意义",
        bg or "（结构中未抽到背景短摘）",
        "",
        "二、主要功能",
    ]
    if feats:
        lines.extend(f"- {f}" for f in feats)
    else:
        lines.append("（模块条目过少，请先重新抽取）")
    outs = proposal.get("out_scope_lines") or []
    if outs:
        lines.extend(["", "三、范围外 / 不交", *[f"- {x}" for x in outs]])
    return "\n".join(lines)
