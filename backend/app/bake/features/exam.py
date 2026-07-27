"""在线考试（exam）：题库 / 组卷 / 作答 / 自动判分（C-01）。

挂 DOM-EXAM；按需 opts（刷题/解析/限时/次数/排行/错题本）仅开题写到才开。
exam_skin：同域换文案与种子，不新开 DOM。
"""

from __future__ import annotations

import re
from typing import Any

EXAM_CAP = "exam"

_EXAM_SIGNALS = re.compile(
    r"在线考试|题库|组卷|刷题|结业考试|自动判分|在线答题|考试系统|题库管理|"
    r"党建答题|党史答题|科目一|驾校理论|驾照题库|入职安全考|安全教育考试|"
    r"岗前安全答题|培训结业考|课程结业测验"
)

# C-02：LABSAFE 开题点名「先考后申」才挂闸门（并强制挂 exam）
_LABSAFE_EXAM_GATE = re.compile(
    r"准入考试|先考试|安全考试|培训考核|考试通过|先考后申|考试后申请|考后申请"
)

_OPT_PATTERNS: dict[str, re.Pattern[str]] = {
    "practice": re.compile(r"刷题|练习模式|练习卷|模拟练习"),
    "explain": re.compile(r"解析|答案解析|题目解析|错题解析"),
    "timer": re.compile(r"限时|倒计时|考试时长|答题时限"),
    "attempt_limit": re.compile(r"考试次数|重考次数|最多.*次|次数限制|限考"),
    "rank": re.compile(r"排行榜|成绩排行|分数排名|榜单"),
    "wrongbook": re.compile(r"错题本|错题集|错题复习"),
}

_SKIN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("party", re.compile(r"党建|党史|党章|党员|两学一做|主题党日")),
    ("drive", re.compile(r"科目一|驾校|驾照|驾驶证|机动车理论")),
    ("safety", re.compile(r"入职安全|安全教育|岗前安全|安全生产|消防安全考")),
    ("grad", re.compile(r"结业|课程测验|期末测验|培训结业|课程考试")),
]

_SKIN_COPY: dict[str, dict[str, str]] = {
    "general": {
        "auth_eyebrow": "在线考试",
        "archive_label": "考试科目",
        "archive_menu_admin": "科目管理",
        "archive_menu_user": "考试科目",
        "papers_title": "在线考试",
        "papers_lead": "选择已发布试卷开考；提交后自动判分。",
        "notice_title": "考试须知",
        "notice_body": "请独立完成作答；客观题自动判分，主观题按关键词/正则自动判分。",
    },
    "party": {
        "auth_eyebrow": "党建答题",
        "archive_label": "答题专题",
        "archive_menu_admin": "专题管理",
        "archive_menu_user": "答题专题",
        "papers_title": "党建答题",
        "papers_lead": "选择专题试卷作答；提交后查看成绩。",
        "notice_title": "答题须知",
        "notice_body": "请认真学习后作答；本期为自动判分，非真机考监考。",
    },
    "drive": {
        "auth_eyebrow": "理论题库",
        "archive_label": "题库科目",
        "archive_menu_admin": "科目管理",
        "archive_menu_user": "题库科目",
        "papers_title": "理论考试",
        "papers_lead": "选择已发布试卷模拟作答；提交后自动判分。",
        "notice_title": "理论考试须知",
        "notice_body": "题库非官方题库；客观题自动判分，主观题按关键词匹配。",
    },
    "safety": {
        "auth_eyebrow": "安全考试",
        "archive_label": "培训科目",
        "archive_menu_admin": "科目管理",
        "archive_menu_user": "培训科目",
        "papers_title": "安全教育考试",
        "papers_lead": "完成岗前/入职安全试卷；提交后自动判分。",
        "notice_title": "安全考试须知",
        "notice_body": "请结合培训材料作答；本期无真人监考与证书打印。",
    },
    "grad": {
        "auth_eyebrow": "结业测验",
        "archive_label": "课程科目",
        "archive_menu_admin": "课程科目",
        "archive_menu_user": "课程科目",
        "papers_title": "结业测验",
        "papers_lead": "选择课程试卷完成测验；提交后自动判分。",
        "notice_title": "测验须知",
        "notice_body": "请在规定时限内完成；客观题自动判分，主观题按关键词匹配。",
    },
}

# SQL 种子替换：(旧串, 新串)；仅替换演示文案
_SKIN_SEED_REPLACES: dict[str, list[tuple[str, str]]] = {
    "party": [
        ("高等数学", "党史学习"),
        ("大学英语", "党章党规"),
        ("线性代数基础", "新民主主义革命基本史实"),
        ("英语阅读理解", "党的二十大精神要点"),
        ("期中测验卷", "党史专题答题卷"),
        ("考试须知", "答题须知"),
    ],
    "drive": [
        ("高等数学", "交通法规"),
        ("大学英语", "安全文明驾驶"),
        ("线性代数基础", "道路交通信号灯含义"),
        ("英语阅读理解", "机动车通行规则要点"),
        ("期中测验卷", "科目一模拟卷"),
        ("考试须知", "理论考试须知"),
    ],
    "safety": [
        ("高等数学", "实验室安全"),
        ("大学英语", "消防应急"),
        ("线性代数基础", "危化品存放基本要求"),
        ("英语阅读理解", "灭火器使用要点"),
        ("期中测验卷", "入职安全考试卷"),
        ("考试须知", "安全考试须知"),
    ],
    "grad": [
        ("高等数学", "专业导论"),
        ("大学英语", "实践环节"),
        ("线性代数基础", "课程核心概念辨析"),
        ("英语阅读理解", "实践报告写作要点"),
        ("期中测验卷", "课程结业测验卷"),
        ("考试须知", "测验须知"),
    ],
}


def scan_exam(text: str) -> bool:
    return bool(_EXAM_SIGNALS.search(text or ""))


def scan_exam_opts(text: str) -> dict[str, bool]:
    body = text or ""
    return {k: bool(p.search(body)) for k, p in _OPT_PATTERNS.items()}


def scan_exam_skin(text: str) -> str:
    body = text or ""
    for skin, pat in _SKIN_PATTERNS:
        if pat.search(body):
            return skin
    return "general"


def scan_exam_gate_ticket(text: str, domain: str | None = None) -> bool:
    """LABSAFE 准入闸门：开题写到先考后申类措辞。"""
    if (domain or "") != "DOM-LABSAFE":
        return False
    return bool(_LABSAFE_EXAM_GATE.search(text or ""))


def exam_wanted(
    *,
    domain: str | None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
) -> bool:
    caps = list(capabilities or [])
    if EXAM_CAP in caps:
        return True
    if (domain or "") == "DOM-EXAM":
        return True
    if scan_exam_gate_ticket(proposal_text, domain):
        return True
    return scan_exam(proposal_text)


def merge_exam_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
    force: bool = False,
) -> list[str]:
    out = list(caps or [])
    want = force or exam_wanted(
        domain=domain,
        capabilities=out,
        proposal_text=proposal_text,
    )
    if want and EXAM_CAP not in out:
        out.append(EXAM_CAP)
    return out


def attach_exam_menus(schema: dict[str, Any], *, opts: dict[str, bool] | None = None) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    opts = opts or {}
    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    user = menus.setdefault("user", [])
    ensure_menu(
        admin,
        "exam_questions",
        {"key": "exam_questions", "label": "题库管理", "superOnly": True},
        before_key="content",
    )
    ensure_menu(
        admin,
        "exam_papers",
        {"key": "exam_papers", "label": "试卷管理", "superOnly": True},
        before_key="content",
    )
    ensure_menu(
        user,
        "exam_papers",
        {"key": "exam_papers", "label": "在线考试"},
        before_key="content",
    )
    ensure_menu(
        user,
        "exam_attempts",
        {"key": "exam_attempts", "label": "我的成绩"},
        before_key="content",
    )
    if opts.get("practice"):
        ensure_menu(
            user,
            "exam_practice",
            {"key": "exam_practice", "label": "刷题练习"},
            before_key="content",
        )
    if opts.get("rank"):
        ensure_menu(
            user,
            "exam_rank",
            {"key": "exam_rank", "label": "成绩排行"},
            before_key="profile",
        )
    if opts.get("wrongbook"):
        ensure_menu(
            user,
            "exam_wrongbook",
            {"key": "exam_wrongbook", "label": "错题本"},
            before_key="profile",
        )

    labels = schema.setdefault("labels", {})
    skin = str(schema.get("examSkin") or "general")
    copy = _SKIN_COPY.get(skin) or _SKIN_COPY["general"]
    labels.setdefault("examPapersTitle", copy["papers_title"])
    labels.setdefault("examPapersLead", copy["papers_lead"])
    labels.setdefault("examPracticeTitle", "刷题练习")
    labels.setdefault("examPracticeLead", "练习模式不计排行；可反复作答。")
    labels.setdefault("examAttemptsTitle", "我的成绩")
    labels.setdefault("examWrongbookTitle", "错题本")
    labels.setdefault("examRankTitle", "成绩排行")

    ents = schema.setdefault("entities", {})
    if "exam" not in ents:
        ents["exam"] = {
            "key": "exam",
            "label": "考试",
            "labelPlural": "考试",
            "opts": {
                "practice": bool(opts.get("practice")),
                "explain": bool(opts.get("explain")),
                "timer": bool(opts.get("timer")),
                "attemptLimit": bool(opts.get("attempt_limit")),
                "rank": bool(opts.get("rank")),
                "wrongbook": bool(opts.get("wrongbook")),
            },
        }


def apply_exam_skin_labels(schema: dict[str, Any], skin: str) -> None:
    copy = _SKIN_COPY.get(skin) or _SKIN_COPY["general"]
    labels = schema.setdefault("labels", {})
    labels["authEyebrow"] = copy["auth_eyebrow"]
    labels["examPapersTitle"] = copy["papers_title"]
    labels["examPapersLead"] = copy["papers_lead"]
    arch = (schema.get("entities") or {}).get("archive")
    if isinstance(arch, dict):
        arch["label"] = copy["archive_label"]
        arch["labelPlural"] = copy["archive_label"]
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    for side in ("admin", "user"):
        for m in menus.get(side) or []:
            if not isinstance(m, dict):
                continue
            if m.get("key") == "archive":
                m["label"] = (
                    copy["archive_menu_admin"]
                    if side == "admin"
                    else copy["archive_menu_user"]
                )
            if m.get("key") == "exam_papers" and side == "user":
                m["label"] = copy["papers_title"]
    seeds = schema.setdefault("seeds", {})
    seeds["noticeTitle"] = copy["notice_title"]
    seeds["noticeBody"] = copy["notice_body"]


def apply_exam_skin_sql(sql: str, skin: str) -> str:
    if not sql or skin in ("", "general"):
        return sql
    out = sql
    for old, new in _SKIN_SEED_REPLACES.get(skin) or []:
        out = out.replace(old, new)
    return out


def apply_exam_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain")
    caps = merge_exam_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if EXAM_CAP in caps:
        opts = scan_exam_opts(proposal_text)
        gate_ticket = scan_exam_gate_ticket(proposal_text, domain)
        # 仅当 exam 已在能力中时 opts 才生效（避免错域误开）
        skin = "safety" if gate_ticket else scan_exam_skin(proposal_text)
        schema["examSkin"] = skin
        schema["examOpts"] = opts
        schema["examGateTicket"] = gate_ticket
        apply_exam_skin_labels(schema, skin)
        attach_exam_menus(schema, opts=opts)
        ticket_ent = schema.setdefault("entities", {}).setdefault("ticket", {})
        if isinstance(ticket_ent, dict) and gate_ticket:
            ticket_ent["requireExamPass"] = True
        from app.bake.gate_contracts import merge_exam_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_exam_gate(gate, caps)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "题库与组卷" not in names:
            features.append({"name": "题库与组卷", "status": "flow"})
        if "在线作答与判分" not in names:
            features.append({"name": "在线作答与判分", "status": "flow"})
        if gate_ticket and "先考后申" not in names:
            features.append({"name": "先考后申", "status": "flow"})
        spec["features"] = features

        ents = list(spec.get("entities") or [])
        if "Exam" not in ents:
            if "Notice" in ents:
                ents.insert(ents.index("Notice"), "Exam")
            else:
                ents.append("Exam")
            spec["entities"] = ents

    spec["schema"] = schema
    return spec
