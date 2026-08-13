"""四类角色中的岗位：子管理(clerk) / 业务员工(worker)。全领域通用框架，岗位按域配置。"""

from __future__ import annotations

import re
from typing import Any

# 办理岗：裁剪 Admin 菜单 key
PACK_ADMIN_MENUS: dict[str, frozenset[str]] = {
    "ticket_ops": frozenset({"dashboard", "ticket_pending", "ticket_records", "deadline", "archive_logs"}),
    "order_ops": frozenset({"dashboard", "orders"}),
    "slot_ops": frozenset({"dashboard", "reservations"}),
    # 内容流编辑：维护档案与公告（无单据审核队列）
    "content_ops": frozenset({"dashboard", "archive", "content"}),
    "exam_ops": frozenset(
        {"dashboard", "archive", "content", "exam_questions", "exam_papers"}
    ),
    "survey_ops": frozenset(
        {"dashboard", "archive", "content", "survey_forms", "survey_stats"}
    ),
    "vote_ops": frozenset(
        {"dashboard", "archive", "content", "vote_candidates", "vote_results"}
    ),
    "doclib_ops": frozenset(
        {"dashboard", "archive", "content", "doc_files", "doc_logs"}
    ),
}

# 作业岗：员工端页面 id（前端路由用）
PACK_WORK_PAGES: dict[str, frozenset[str]] = {
    "ticket_work": frozenset({"tickets"}),
    "order_work": frozenset({"orders"}),
    "slot_work": frozenset({"slots"}),
}

CLERK_PACKS = frozenset(PACK_ADMIN_MENUS)
WORKER_PACKS = frozenset(PACK_WORK_PAGES)
ALL_PACKS = CLERK_PACKS | WORKER_PACKS


def _post(pid: str, label: str, kind: str, packs: list[str]) -> dict[str, Any]:
    return {"id": pid, "label": label, "kind": kind, "packs": list(packs)}


def _clerk(pid: str, label: str, *packs: str) -> dict[str, Any]:
    return _post(pid, label, "clerk", list(packs))


def _worker(pid: str, label: str, *packs: str) -> dict[str, Any]:
    return _post(pid, label, "worker", list(packs))


# 岗位按域配置：clerk / worker 均可选；无岗位 = 仅门户用户 + 总管
STAFF_POSTS_BY_DOMAIN: dict[str, list[dict[str, Any]]] = {
    "DOM-LIBRARY": [_clerk("librarian", "馆员", "ticket_ops")],
    "DOM-EQUIP": [_clerk("keeper", "器材管理员", "ticket_ops")],
    "DOM-ASSET": [_clerk("storekeeper", "库管员", "ticket_ops")],
    # CRM / EVAL：主流程门户一次办完 → 双角色（业务员|学生 + 总管），不挂空转办理岗
    "DOM-CRM": [],
    "DOM-EVENT": [_clerk("duty_clerk", "值班员", "ticket_ops")],
    "DOM-ATTEND": [_clerk("attend_clerk", "考勤员", "ticket_ops")],
    "DOM-FUND": [_clerk("fund_clerk", "资助专员", "ticket_ops")],
    "DOM-LABSAFE": [_clerk("lab_safety", "安全员", "ticket_ops")],
    "DOM-RECRUIT": [_clerk("hr_clerk", "HR专员", "ticket_ops")],
    "DOM-DATING": [_clerk("matchmaker", "红娘专员", "ticket_ops")],
    "DOM-GRADE": [_clerk("grade_clerk", "教务员", "ticket_ops")],
    "DOM-INTERN": [_clerk("intern_tutor", "实习辅导员", "ticket_ops")],
    "DOM-PARCEL": [_clerk("parcel_clerk", "驿站店员", "ticket_ops")],
    "DOM-SEAL": [_clerk("seal_clerk", "用章管理员", "ticket_ops")],
    "DOM-FLEET": [_clerk("fleet_clerk", "调度员", "ticket_ops")],
    "DOM-CERT": [_clerk("cert_clerk", "证明专员", "ticket_ops")],
    "DOM-PROMO": [_clerk("promo_clerk", "宣传员", "ticket_ops")],
    "DOM-FITOUT": [_clerk("fitout_clerk", "备案员", "ticket_ops")],
    "DOM-ACAD": [_clerk("acad_clerk", "教务员", "ticket_ops")],
    "DOM-TRIP": [_clerk("trip_clerk", "考勤员", "ticket_ops")],
    "DOM-EXPENSE": [_clerk("expense_clerk", "报销审核员", "ticket_ops")],
    "DOM-CREDIT": [_clerk("credit_clerk", "认定专员", "ticket_ops")],
    "DOM-LABOR": [_clerk("labor_clerk", "劳动专员", "ticket_ops")],
    "DOM-EVAL": [],
    "DOM-MORAL": [_clerk("moral_clerk", "综测专员", "ticket_ops")],
    "DOM-AWARD": [_clerk("award_clerk", "成果专员", "ticket_ops")],
    "DOM-BED": [_clerk("bed_clerk", "宿管员", "ticket_ops")],
    # 查寝：归寝登记待审；查寝员审单 + 维护寝室/签到码
    "DOM-CHECKIN": [_clerk("checkin_clerk", "查寝员", "ticket_ops", "content_ops")],
    "DOM-MUTUAL-TUTOR": [_clerk("tutor_clerk", "导师秘书", "ticket_ops")],
    "DOM-MUTUAL-TOPIC": [_clerk("topic_clerk", "选题秘书", "ticket_ops")],
    "DOM-MUTUAL-TEAM": [_clerk("team_clerk", "组队协调员", "ticket_ops")],
    "DOM-VISITOR": [_clerk("visitor_clerk", "接待员", "ticket_ops")],
    "DOM-CARPASS": [_clerk("carpass_clerk", "车证管理员", "ticket_ops")],
    "DOM-LISTING": [_clerk("listing_clerk", "置业顾问", "ticket_ops")],
    "DOM-PROCURE": [_clerk("procure_clerk", "采购专员", "ticket_ops")],
    "DOM-CLUB": [_clerk("club_clerk", "社团专员", "ticket_ops")],
    "DOM-PROJ": [_clerk("proj_clerk", "项目专员", "ticket_ops")],
    "DOM-ETHIC": [_clerk("ethic_clerk", "审核秘书", "ticket_ops")],
    "DOM-PARTY": [_clerk("party_clerk", "组织员", "ticket_ops")],
    "DOM-CONTRACT": [_clerk("contract_clerk", "合同专员", "ticket_ops")],
    "DOM-INSTRUMENT": [_clerk("instrument_clerk", "仪器管理员", "ticket_ops")],
    "DOM-EXAM": [_clerk("exam_clerk", "教务员", "exam_ops")],
    "DOM-SURVEY": [_clerk("survey_clerk", "调研员", "survey_ops")],
    "DOM-VOTE": [_clerk("vote_clerk", "评选员", "vote_ops")],
    "DOM-DOCLIB": [_clerk("doc_clerk", "资料员", "doclib_ops")],
    "DOM-CARPOOL": [_clerk("carpool_clerk", "对接员", "ticket_ops")],
    "DOM-TOUR": [_clerk("tour_clerk", "计调员", "ticket_ops")],
    "DOM-TIMEBANK": [_clerk("tb_clerk", "核销员", "ticket_ops")],
    "DOM-CINEMA": [_clerk("cinema_clerk", "售票员", "order_ops")],
    "DOM-DORM": [
        _clerk("dorm_mgr", "楼管", "ticket_ops"),
        # 维修员：默认不挂；开题写到才追加（与骑手/拣货同口径）
    ],
    "DOM-PROPERTY": [
        _clerk("dispatcher", "物业调度", "ticket_ops"),
        # 维修员：默认不挂；开题写到才追加
    ],
    "DOM-IT": [_clerk("ops", "运维员", "ticket_ops")],
    "DOM-ACTIVITY": [_clerk("assistant", "活动助理", "ticket_ops")],
    "DOM-LOST": [_clerk("claim_clerk", "招领管理员", "ticket_ops")],
    "DOM-COURSE": [_clerk("course_clerk", "选课管理员", "ticket_ops")],
    "DOM-SHOP": [
        _clerk("order_clerk", "订单管理员", "order_ops"),
        # 拣货员：默认不挂；开题写到才追加（见 _OPTIONAL_WORKERS）
    ],
    "DOM-FOOD": [
        # 默认社会餐饮「店员」；食堂档在 attach 里按 food_product_kind 改成档口店员
        _clerk("counter", "店员", "order_ops"),
        # 骑手：默认不挂；开题写到才追加
    ],
    "DOM-HOSPITAL": [_clerk("registrar", "挂号员", "slot_ops")],
    "DOM-PARKING": [_clerk("lot_clerk", "车场管理员", "slot_ops")],
    "DOM-MEETING": [_clerk("booking_clerk", "预约管理员", "slot_ops")],
    "DOM-SALON": [
        _clerk("front", "前台", "slot_ops"),
        # 技师：默认不挂；开题写到才追加（预约「偏好技师」文案仍可有，≠员工账号）
    ],
    "DOM-HOTEL": [
        _clerk("front", "前台", "slot_ops", "order_ops"),
        # 客房服务：默认不挂；开题写到才追加
    ],
    "DOM-MEDIA": [_clerk("editor", "运营编辑", "content_ops")],
    "DOM-MUSIC": [_clerk("editor", "运营编辑", "content_ops")],
    "DOM-FORUM": [_clerk("moderator", "版主", "ticket_ops")],
    "DOM-BLOG": [_clerk("editor", "编辑", "content_ops")],
    "DOM-GENERIC": [_clerk("clerk", "业务办理员", "ticket_ops")],
}

# 门户身份强绑定（服务对象 / 对方当事人）：岗位靠种子账号，禁止把业务用户「任命」成岗
NO_APPOINT_FROM_USERS: frozenset[str] = frozenset({
    # 预约 / 交易：患者、车主、预约人、顾客、住客…
    "DOM-HOSPITAL",
    "DOM-PARKING",
    "DOM-MEETING",
    "DOM-SALON",
    "DOM-HOTEL",
    "DOM-SHOP",
    "DOM-FOOD",
    # 门户＝求职方 / 会员 / 实习生 / 取件人 / 报名者 / 借用人 / 申领人
    "DOM-RECRUIT",
    "DOM-DATING",
    "DOM-INTERN",
    "DOM-PARCEL",
    "DOM-ACTIVITY",
    "DOM-EQUIP",
    "DOM-ASSET",
})

# 按 scene_for 再禁：仅当该档门户明显是服务对象时（校园师生可升岗的档不进表）
_SCENE_NO_APPOINT: dict[str, frozenset[str]] = {
    "DOM-PROPERTY": frozenset({"community", "commercial"}),  # 业主/住户
    "DOM-MEDIA": frozenset({"commercial"}),  # 观众
    "DOM-MUSIC": frozenset({"commercial"}),  # 听众
    "DOM-BLOG": frozenset({"commercial"}),  # 读者（商业站）
    "DOM-EVENT": frozenset({"default", "institution"}),  # 随访对象 / 家属
    "DOM-LOST": frozenset({"community", "adopt"}),  # 居民 / 领养申请人
    "DOM-FORUM": frozenset({"community"}),  # 居民 ≠ 版主（校园师生可升版主）
}

# schema.roles 元数据键 / 门户别名（与 user 同槽，禁止并列进 Spec）
_ROLE_META_KEYS = frozenset({"staff_posts", "allowAppointFromUsers"})
_PORTAL_ROLE_ALIASES = frozenset({"reader", "student", "patient", "buyer"})

# 可选 worker：默认不进岗位表；开题命中词才追加（keyword_mentioned，同 guestbook/loyalty）
# 现场岗易空挂：报修维修员 / 骑手 / 拣货 / 技师 / 客房 / 派件 / 上门运维 / 导诊护士 — 均开题写到才挂
_OPTIONAL_WORKERS: dict[str, list[tuple[dict[str, Any], tuple[str, ...]]]] = {
    "DOM-FOOD": [
        (
            _worker("rider", "骑手", "order_work"),
            (
                "骑手",
                "配送员",
                "外卖配送",
                "送餐上门",
                "配送到寝",
                "配送到宿舍",
                "骑手配送",
                "外卖骑手",
            ),
        ),
    ],
    "DOM-SHOP": [
        (
            _worker("picker", "拣货员", "order_work"),
            (
                "拣货员",
                "配货员",
                "仓库拣货",
                "拣配",
                "拣货",
                "配货",
                "仓配",
                "分拣发货",
            ),
        ),
    ],
    "DOM-SALON": [
        (
            _worker("stylist", "技师", "slot_work"),
            (
                "发型师",
                "美发师",
                "美容师",
                "理发师",
                "造型师",
                "技师",
                "美容技师",
                "私教教练",
                "健身教练",
            ),
        ),
    ],
    "DOM-HOTEL": [
        (
            _worker("housekeeping", "客房服务", "slot_work"),
            (
                "客房服务",
                "客房保洁",
                "客房打扫",
                "客房整理",
                "楼层服务员",
                "保洁员",
                "客房服务员",
            ),
        ),
    ],
    "DOM-DORM": [
        (
            _worker("repairer", "维修员", "ticket_work"),
            (
                "维修员",
                "维修师傅",
                "维修人员",
                "维修班组",
                "上门维修",
                "水电维修",
                "报修派工",
                "派单",
                "派工",
            ),
        ),
    ],
    "DOM-PROPERTY": [
        (
            _worker("repairer", "维修员", "ticket_work"),
            (
                "维修员",
                "维修师傅",
                "维修人员",
                "维修班组",
                "上门维修",
                "水电维修",
                "报修派工",
                "派单",
                "派工",
            ),
        ),
    ],
    "DOM-IT": [
        (
            _worker("field_tech", "上门运维", "ticket_work"),
            (
                "上门运维",
                "现场工程师",
                "驻场运维",
                "上门排障",
                "现场排障",
                "IT上门",
                "派单",
                "派工",
            ),
        ),
    ],
    "DOM-PARCEL": [
        (
            _worker("courier", "派件员", "ticket_work"),
            (
                "派件员",
                "送件员",
                "快递小哥",
                "快递员上门",
                "上门派件",
                "派送员",
            ),
        ),
    ],
    "DOM-HOSPITAL": [
        (
            _worker("nurse", "导诊护士", "slot_work"),
            (
                "导诊护士",
                "分诊护士",
                "接诊护士",
                "门诊护士",
                "护士分诊",
            ),
        ),
    ],
}

# CRM/EVAL：默认双角色；开题出现「要第三角」的流程信号才挂办理岗（不靠猜岗名全表）
_OPTIONAL_FLOW_CLERKS: dict[str, dict[str, Any]] = {
    "DOM-CRM": {
        "post": _clerk("account_mgr", "客户经理", "ticket_ops"),
        "yes": (
            "三角色",
            "三种角色",
            "三类角色",
            "三个角色",
            "三级角色",
            "子管理员",
            "子管理端",
            "管理端审核",
            "管理端审批",
            "管理员审核",
            "管理员审批",
            "主管审核",
            "跟进审核",
            "审核跟进",
            "跟进确认",
            "审核完结",
            "审批完结",
            "待审核",
            "待审批",
        ),
        "no": (
            "双角色",
            "两种角色",
            "两类角色",
            "无需审核",
            "无需审批",
            "不设审核",
            "不设审批",
            "无审批环节",
            "无审核环节",
        ),
    },
    "DOM-EVAL": {
        "post": _clerk("eval_clerk", "评教员", "content_ops"),
        "yes": (
            "三角色",
            "三种角色",
            "三类角色",
            "三个角色",
            "三级角色",
            "子管理员",
            "子管理端",
            "管理端审核",
            "管理端审批",
            "管理员审核",
            "管理员审批",
            "评教审核",
            "审核评教",
            "审批评教",
            "审核完结",
            "审批完结",
            "待审核",
            "待审批",
        ),
        "no": (
            "双角色",
            "两种角色",
            "两类角色",
            "无需审核",
            "无需审批",
            "不设审核",
            "不设审批",
            "提交即完结",
            "提交即生效",
        ),
    },
}

# 「由××审核/确认」：流程上有第三方办理，且可抠岗名
_THIRD_ROLE_ACTOR_RE = re.compile(
    r"(?:由|经|交由|请)([\u4e00-\u9fff]{2,10}?)(?:审核|审批|确认|复核|核销)"
)
_THIRD_ROLE_SKIP_LABELS = frozenset(
    {
        "管理",
        "管理员",
        "系统",
        "用户",
        "学生",
        "业务员",
        "本人",
        "人工",
        "后台",
        "平台",
        "本系统",
        "本课题",
        "对方",
        "相关",
        "有关",
    }
)


def _proposal_wants_any(proposal_text: str, hints: tuple[str, ...]) -> bool:
    from app.bake.proposal_lexicon import keyword_mentioned

    raw = proposal_text or ""
    return any(keyword_mentioned(raw, h) for h in hints)


def _extract_third_role_label(blob: str) -> str | None:
    """从「由××审核/确认」抠办理人称呼；抠不出返回 None。"""
    raw = blob or ""
    if not raw:
        return None
    for m in _THIRD_ROLE_ACTOR_RE.finditer(raw):
        lab = str(m.group(1) or "").strip()
        if len(lab) < 2 or lab in _THIRD_ROLE_SKIP_LABELS:
            continue
        # 去掉尾缀「进行/予以」等开题套话
        for suf in ("进行", "予以", "负责", "统一"):
            if lab.endswith(suf) and len(lab) - len(suf) >= 2:
                lab = lab[: -len(suf)]
        if lab in _THIRD_ROLE_SKIP_LABELS or len(lab) < 2:
            continue
        return lab[:24]
    return None


def _wants_flow_clerk(domain: str, blob: str) -> bool:
    """开题是否要第三角：流程信号、「由××审核」、或点名常见办理岗称呼。"""
    spec = _OPTIONAL_FLOW_CLERKS.get(domain)
    if not spec:
        return False
    raw = blob or ""
    no = tuple(spec.get("no") or ())
    if no and _proposal_wants_any(raw, no):
        return False
    yes = tuple(spec.get("yes") or ())
    if yes and _proposal_wants_any(raw, yes):
        return True
    if _extract_third_role_label(raw) is not None:
        return True
    # 点名已知办理岗称呼也挂（可选增强，不依赖穷举开题用词）
    pid = str((spec.get("post") or {}).get("id") or "")
    aliases = _POST_LABEL_ALIASES.get(pid) or ()
    return bool(aliases and _proposal_wants_any(raw, aliases))


def _flow_clerk_label(domain: str, blob: str, default: str) -> str:
    """岗名：已知别名 > 由××审核抠词 > 域默认。"""
    aliases = ()
    post = (_OPTIONAL_FLOW_CLERKS.get(domain) or {}).get("post") or {}
    pid = str((post or {}).get("id") or "")
    if pid:
        aliases = _POST_LABEL_ALIASES.get(pid) or ()
    picked = _pick_label_from_proposal(blob, aliases) if aliases else None
    if picked:
        return picked
    extracted = _extract_third_role_label(blob)
    if extracted:
        return extracted
    return (default or "经办员")[:24]


def _pick_label_from_proposal(
    proposal_text: str,
    aliases: tuple[str, ...],
    *,
    min_len: int = 2,
) -> str | None:
    """开题正向命中的称呼原样作 label；按 aliases 声明顺序优先（非新匹配旁路）。"""
    raw = proposal_text or ""
    if not raw or not aliases:
        return None
    for alias in aliases:
        a = str(alias or "").strip()
        if len(a) < min_len:
            continue
        if _proposal_wants_any(raw, (a,)):
            return a[:24]
    return None


# 已挂岗位的显示名：开题写到的称呼原样替换目录默认（禁光杆「导师」等开题套话）
_POST_LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "intern_tutor": (
        "企业导师",
        "带教导师",
        "校内导师",
        "实习导师",
        "指导教师",
        "指导老师",
        "实习辅导员",
        "辅导员",
    ),
    "duty_clerk": (
        "随访员",
        "随访专员",
        "晨检员",
        "照护员",
        "护士",
        # 网格员=门户一线填报（见 _USER_LABEL_ALIASES），勿扫进值班子管
        "流调员",
        "防控专员",
        "值班员",
        "卫生员",
    ),
    "attend_clerk": ("辅导员", "班主任", "考勤管理员", "考勤员"),
    "fund_clerk": ("资助专员", "资助管理员", "奖助专员"),
    "lab_safety": ("安全员", "实验室安全员", "准入管理员"),
    "hr_clerk": ("招聘专员", "人事专员", "HR专员", "HR"),
    "grade_clerk": ("成绩管理员", "教务员", "任课教师"),
    "parcel_clerk": ("驿站管理员", "驿站店员", "取件员"),
    "dorm_mgr": ("宿舍管理员", "楼管", "宿管"),
    "dispatcher": ("物业管理员", "物业调度", "客服"),
    "counter": ("档口店员", "窗口服务员", "食堂窗口", "档口"),
    "order_clerk": ("订单管理员", "店铺管理员", "客服"),
    "front": ("前台接待", "前台", "接待员"),
    "registrar": ("挂号员", "导诊", "分诊台"),
    "librarian": ("图书管理员", "馆员"),
    "keeper": (
        "器材管理员",
        "器材员",
        "物资管理员",
        "道具管理员",
        "服装管理员",
        "乐器管理员",
        "教具管理员",
        "装备管理员",
    ),
    "storekeeper": ("库管员", "仓管"),
    "eval_clerk": (
        "评教员",
        "评教管理员",
        "评教专员",
        "教学督导",
        "督导员",
        "督导老师",
        "教务管理员",
    ),
    "account_mgr": (
        "客户经理",
        "客户专员",
        "客户管理员",
        "销售经理",
        "跟进专员",
        "项目负责人",
        "案件秘书",
        "项目对接人",
        "辅导员",
    ),
    "ops": ("运维员", "运维工程师"),
    "field_tech": ("上门运维", "现场工程师", "驻场运维"),
    "courier": ("派件员", "送件员", "派送员"),
    "nurse": ("导诊护士", "分诊护士", "接诊护士", "门诊护士"),
    "assistant": ("活动助理", "活动管理员"),
    "claim_clerk": ("招领管理员", "失物管理员", "领养专员", "领养管理员"),
    "course_clerk": ("选课管理员", "教务员"),
    "booking_clerk": ("预约管理员", "预约办理员"),
    "editor": ("运营编辑", "内容编辑", "编辑"),
    "moderator": ("版主", "论坛管理员"),
    "clerk": ("业务办理员", "经办员", "业务员"),
}

# 门户 user 槽：开题写到才替换（短泛词如「学生」不进表，避免开题套话误伤）
_USER_LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "DOM-INTERN": ("实习生", "实习学生"),
    # 照护员/随访员是 duty_clerk；门户 user 用场景预设，勿用「老人」盖掉家属
    "DOM-EVENT": ("随访对象", "上报人", "家属", "网格员", "居民", "员工"),
    "DOM-FOOD": ("就餐用户", "就餐者"),
    "DOM-HOSPITAL": ("宠主", "接种人", "就诊人", "患者"),
    "DOM-LOST": ("失主", "认领人", "申请人"),
    "DOM-PARKING": ("车主",),
    "DOM-ATTEND": ("考勤对象", "员工"),
    "DOM-FUND": ("受助学生", "申请学生"),
    "DOM-SEAL": ("申请人", "办理人"),
    "DOM-FLEET": ("用车人", "申请人"),
    "DOM-CERT": ("申请人", "办理人"),
    "DOM-PROMO": ("申报人", "申请人"),
    "DOM-FITOUT": ("申报人", "申请人"),
    "DOM-ACAD": ("学生", "申请人"),
    "DOM-TRIP": ("申请人", "出差人"),
    "DOM-EXPENSE": ("报销人", "申请人"),
    "DOM-CREDIT": ("学生", "申请人"),
    "DOM-LABOR": ("学生", "申请人"),
    "DOM-EVAL": ("学生", "申请人"),
    "DOM-MORAL": ("学生", "申请人"),
    "DOM-AWARD": ("学生", "申请人"),
    "DOM-BED": ("学生", "住宿学生"),
    "DOM-CHECKIN": ("学生", "住宿学生"),
    "DOM-MUTUAL-TUTOR": ("学生", "申请人"),
    "DOM-MUTUAL-TOPIC": ("学生", "申请人"),
    "DOM-MUTUAL-TEAM": ("学生", "申请人"),
    "DOM-VISITOR": ("来访人", "访客"),
    "DOM-CARPASS": ("申请人", "用户"),
    "DOM-LISTING": ("看房客户", "客户", "用户"),
    "DOM-PROCURE": ("申购人", "用户"),
    "DOM-CLUB": ("社团负责人", "学生", "用户"),
    "DOM-PROJ": ("申报人", "学生", "用户"),
    "DOM-ETHIC": ("送审人", "学生", "用户"),
    "DOM-PARTY": ("入党申请人", "学生", "用户"),
    "DOM-CONTRACT": ("经办人", "用户"),
    "DOM-INSTRUMENT": ("使用人", "用户"),
    "DOM-EXAM": ("考生", "用户"),
    "DOM-SURVEY": ("受访者", "用户"),
    "DOM-VOTE": ("投票人", "用户"),
    "DOM-DOCLIB": ("读者", "用户"),
    "DOM-CARPOOL": ("拼车用户", "同行者", "用户"),
    "DOM-TOUR": ("游客", "用户"),
    "DOM-TIMEBANK": ("志愿者", "用户"),
    "DOM-CINEMA": ("观影者", "用户"),
    "DOM-LABSAFE": ("实验人员", "申请人"),
    "DOM-RECRUIT": ("求职者", "应聘者"),
    "DOM-DATING": ("会员", "征婚者", "同学"),
    "DOM-DORM": ("宿舍学生", "住户"),
    "DOM-PROPERTY": ("业主", "住户"),
}


def _catalog_default_label(domain: str, post_id: str) -> str | None:
    for p in STAFF_POSTS_BY_DOMAIN.get(domain) or []:
        if isinstance(p, dict) and str(p.get("id")) == post_id:
            lab = str(p.get("label") or "").strip()
            return lab or None
    for post, _hints in _OPTIONAL_WORKERS.get(domain) or []:
        if isinstance(post, dict) and str(post.get("id")) == post_id:
            lab = str(post.get("label") or "").strip()
            return lab or None
    flow = _OPTIONAL_FLOW_CLERKS.get(domain) or {}
    post = flow.get("post")
    if isinstance(post, dict) and str(post.get("id")) == post_id:
        lab = str(post.get("label") or "").strip()
        return lab or None
    return None


def food_wants_rider(proposal_text: str = "") -> bool:
    """兼容旧测试名；等价于 FOOD 可选骑手扫词。"""
    for post, hints in _OPTIONAL_WORKERS.get("DOM-FOOD") or []:
        if post.get("id") == "rider":
            return _proposal_wants_any(proposal_text, hints)
    return False


def roles_for_spec(domain_roles: list | None, schema: dict | None) -> list[str]:
    """以 schema.roles 的 user/admin 为准；展开 staff_posts；去掉与 user 重复的门户别名。"""
    schema_roles = schema.get("roles") if isinstance(schema, dict) else None
    keys = list(schema_roles.keys()) if isinstance(schema_roles, dict) else []
    posts = schema_roles.get("staff_posts") if isinstance(schema_roles, dict) else None
    posts_declared = isinstance(posts, list)
    has_user_slot = isinstance(schema_roles, dict) and isinstance(
        schema_roles.get("user"), dict
    )
    out: list[str] = []
    for r in domain_roles or []:
        if not r:
            continue
        if posts_declared and str(r) == "subadmin":
            continue
        if has_user_slot and str(r) in _PORTAL_ROLE_ALIASES:
            continue
        if str(r) not in out:
            out.append(str(r))
    if posts_declared:
        for p in posts:
            if isinstance(p, dict) and p.get("id"):
                pid = str(p["id"])
                if pid not in out:
                    out.append(pid)
    for r in keys:
        if r in _ROLE_META_KEYS or r == "subadmin":
            continue
        val = schema_roles.get(r) if isinstance(schema_roles, dict) else None
        if not isinstance(val, dict):
            continue
        if r and r not in out:
            out.append(str(r))
    if not posts_declared and isinstance(schema_roles, dict) and "subadmin" in schema_roles:
        if "subadmin" not in out:
            out.append("subadmin")
    return out or ["user", "admin"]


def _generic_arch_flags(
    archetype: str | None = None,
    archetypes: list[str] | None = None,
) -> tuple[bool, bool, bool]:
    """GENERIC 按能力路径取岗位；交叉并集，不抄行业域的 worker。"""
    from app.bake.archetype_shells import path_flags

    return path_flags(list(archetypes or ([archetype] if archetype else ["ARCH-CRUD"])))


def allow_appoint_from_users(
    domain: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    *,
    proposal_text: str = "",
    title: str = "",
) -> bool:
    """是否允许把门户业务用户升为岗位；无岗位表时亦为 False。"""
    if domain in NO_APPOINT_FROM_USERS:
        return False
    if domain == "DOM-GENERIC":
        _flow, need_trade, need_reserve = _generic_arch_flags(archetype, archetypes)
        if need_trade or need_reserve:
            return False
    blocked = _SCENE_NO_APPOINT.get(domain)
    if blocked:
        from app.bake.scene_scan import scene_for

        if scene_for(domain, title, proposal_text) in blocked:
            return False
    return bool(
        staff_posts_for_domain(
            domain,
            archetype,
            archetypes,
            proposal_text=proposal_text,
            title=title,
        )
    )


def _apply_scene_post_labels(
    posts: list[dict[str, Any]],
    domain: str,
    *,
    title: str = "",
    proposal_text: str = "",
) -> list[dict[str, Any]]:
    """场景档岗位显示名：与 domain_scene_seed / builder 同判，避免 append 盖回目录默认。"""
    out = [dict(p) for p in posts if isinstance(p, dict) and p.get("id")]
    if domain == "DOM-FOOD":
        from app.bake.scene_scan import food_product_kind

        canteen = food_product_kind(title, proposal_text) == "canteen"
        _canteen_counter = ("档口店员", "窗口服务员", "食堂窗口", "档口")
        for p in out:
            if str(p.get("id") or "") != "counter":
                continue
            lab = str(p.get("label") or "").strip()
            if canteen:
                # 开题扫到裸「档口」时升成完整岗名，与食堂种子一致
                if lab in ("", "店员", *_canteen_counter):
                    p["label"] = "档口店员"
            elif lab in ("", "店员", *_canteen_counter):
                p["label"] = "店员"
    elif domain == "DOM-FUND":
        from app.bake.scene_scan import scene_for

        if scene_for("DOM-FUND", title, proposal_text) == "enterprise":
            for p in out:
                if str(p.get("id") or "") == "fund_clerk":
                    p["label"] = "人事专员"
    elif domain == "DOM-INTERN":
        from app.bake.scene_scan import scene_for

        if scene_for("DOM-INTERN", title, proposal_text) == "enterprise":
            for p in out:
                if str(p.get("id") or "") != "intern_tutor":
                    continue
                lab = str(p.get("label") or "").strip()
                if lab in ("", "实习辅导员", "辅导员", "带教导师"):
                    p["label"] = "企业导师"
    elif domain == "DOM-HOSPITAL":
        from app.bake.scene_scan import hospital_product_kind

        kind = hospital_product_kind(title, proposal_text)
        want = {
            "vaccine": "预约管理员",
            "pet": "挂号员",
            "clinic": "挂号员",
        }.get(kind, "挂号员")
        for p in out:
            if str(p.get("id") or "") != "registrar":
                continue
            lab = str(p.get("label") or "").strip()
            if lab in ("", "挂号员", "预约管理员", "导诊", "分诊台"):
                p["label"] = want
    elif domain == "DOM-EQUIP":
        from app.bake.scene_scan import equip_product_kind

        kind = equip_product_kind(title, proposal_text)
        want = {
            "light": "物资管理员",
            "costume": "道具管理员",
            "music": "乐器管理员",
            "teach": "教具管理员",
            "outdoor": "装备管理员",
        }.get(kind, "器材管理员")
        for p in out:
            if str(p.get("id") or "") != "keeper":
                continue
            lab = str(p.get("label") or "").strip()
            if lab in (
                "",
                "器材管理员",
                "器材员",
                "物资管理员",
                "道具管理员",
                "服装管理员",
                "乐器管理员",
                "教具管理员",
                "装备管理员",
            ):
                p["label"] = want
    return out


def staff_posts_for_domain(
    domain: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    *,
    proposal_text: str = "",
    title: str = "",
) -> list[dict[str, Any]]:
    if domain == "DOM-GENERIC":
        need_flow, need_trade, need_reserve = _generic_arch_flags(archetype, archetypes)
        posts: list[dict[str, Any]] = []
        # 按路径并集挂 clerk；配送员/骑手等 worker 只在具体行业域（FOOD/SHOP…）
        if need_flow:
            posts.append(_clerk("clerk", "业务办理员", "ticket_ops"))
        if need_trade:
            posts.append(_clerk("order_clerk", "订单办理员", "order_ops"))
        if need_reserve:
            posts.append(_clerk("booking_clerk", "预约办理员", "slot_ops"))
        if not posts:
            posts = [_clerk("operator", "业务员")]  # packs 空 → 仅工作台
        posts = _apply_post_labels_from_proposal(posts, domain, proposal_text)
        return _apply_scene_post_labels(
            posts, domain, title=title, proposal_text=proposal_text
        )
    posts = [dict(p) for p in (STAFF_POSTS_BY_DOMAIN.get(domain) or []) if isinstance(p, dict)]
    have = {str(p.get("id")) for p in posts if p.get("id")}
    scan_blob = f"{title or ''}\n{proposal_text or ''}"
    for post, hints in _OPTIONAL_WORKERS.get(domain) or []:
        pid = str(post.get("id") or "")
        if not pid or pid in have:
            continue
        if _proposal_wants_any(scan_blob, hints):
            row = dict(post)
            # 可选岗：命中词里最长称呼作显示名（写「配送员」就显示配送员）
            picked = _pick_label_from_proposal(scan_blob, hints)
            if picked:
                row["label"] = picked
            posts.append(row)
            have.add(pid)
    # CRM/EVAL：流程信号挂第三角（岗名可抠则抠，否则用默认）
    flow = _OPTIONAL_FLOW_CLERKS.get(domain)
    if flow and _wants_flow_clerk(domain, scan_blob):
        base = dict(flow.get("post") or {})
        pid = str(base.get("id") or "")
        if pid and pid not in have:
            default_lab = str(base.get("label") or "经办员")
            base["label"] = _flow_clerk_label(domain, scan_blob, default_lab)
            posts.append(base)
            have.add(pid)
    posts = _apply_post_labels_from_proposal(posts, domain, scan_blob)
    return _apply_scene_post_labels(
        posts, domain, title=title, proposal_text=proposal_text
    )


def _apply_post_labels_from_proposal(
    posts: list[dict[str, Any]],
    domain: str,
    proposal_text: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in posts:
        if not isinstance(p, dict) or not p.get("id"):
            continue
        row = dict(p)
        pid = str(row["id"])
        aliases = _POST_LABEL_ALIASES.get(pid) or ()
        picked = _pick_label_from_proposal(proposal_text, aliases)
        if picked:
            row["label"] = picked
        out.append(row)
    return out


def validate_staff_posts(posts: list[dict[str, Any]]) -> list[str]:
    """返回错误列表；空列表合法（该项目无子管理/员工岗）。"""
    errs: list[str] = []
    if not posts:
        return errs
    ids: set[str] = set()
    for p in posts:
        if not isinstance(p, dict):
            errs.append("staff_post 须为对象")
            continue
        pid = str(p.get("id") or "").strip()
        kind = str(p.get("kind") or "").strip()
        label = str(p.get("label") or "").strip()
        packs = p.get("packs") or []
        if not pid:
            errs.append("staff_post 缺少 id")
        elif pid in ids:
            errs.append(f"重复 staff_post id: {pid}")
        else:
            ids.add(pid)
        if kind not in ("clerk", "worker"):
            errs.append(f"staff_post {pid}: kind 须为 clerk|worker")
        if not label:
            errs.append(f"staff_post {pid}: 缺少 label")
        if not isinstance(packs, list):
            errs.append(f"staff_post {pid}: packs 须为数组")
            continue
        allowed = CLERK_PACKS if kind == "clerk" else WORKER_PACKS
        for pk in packs:
            if pk not in ALL_PACKS:
                errs.append(f"staff_post {pid}: 未知 pack {pk}")
            elif pk not in allowed:
                errs.append(f"staff_post {pid}: pack {pk} 与 kind={kind} 不匹配")
    return errs


def _restore_crm_pending_when_account_mgr(
    schema: dict[str, Any],
    clerks: list[dict[str, Any]],
) -> None:
    """开题挂上客户经理后恢复待审，避免 auto_approve 下第三角空转。"""
    if not any(str(c.get("id") or "") == "account_mgr" for c in clerks):
        return
    ents = dict(schema.get("entities") or {})
    ticket = dict(ents.get("ticket") or {})
    if ticket.get("autoApprove") is False:
        return
    ticket["autoApprove"] = False
    ents["ticket"] = ticket
    schema["entities"] = ents
    pending_label = str(
        ((schema.get("labels") or {}).get("pendingLabel"))
        or ticket.get("pendingLabel")
        or "跟进审核"
    ).strip() or "跟进审核"
    menus = dict(schema.get("menus") or {})
    admin = list(menus.get("admin") or [])
    if any(isinstance(m, dict) and m.get("key") == "ticket_pending" for m in admin):
        return
    out: list[Any] = []
    inserted = False
    for m in admin:
        if (
            not inserted
            and isinstance(m, dict)
            and m.get("key") == "ticket_records"
        ):
            out.append({"key": "ticket_pending", "label": pending_label})
            inserted = True
        out.append(m)
    if not inserted:
        out.append({"key": "ticket_pending", "label": pending_label})
    menus["admin"] = out
    schema["menus"] = menus


def attach_staff_posts(
    schema: dict[str, Any],
    domain: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    *,
    proposal_text: str = "",
    title: str = "",
) -> dict[str, Any]:
    """写入 roles.staff_posts；有 clerk 时同步 subadmin（兼容旧前端），否则去掉。

    开题扫到的称呼原样进 label；重绑时保留 Island/先前已定文案（勿被目录默认盖掉）。
    """
    prev_roles = dict(schema.get("roles") or {})
    prev_posts = {
        str(p.get("id")): p
        for p in (prev_roles.get("staff_posts") or [])
        if isinstance(p, dict) and p.get("id")
    }
    posts = staff_posts_for_domain(
        domain,
        archetype,
        archetypes,
        proposal_text=proposal_text,
        title=title,
    )
    merged_posts: list[dict[str, Any]] = []
    for p in posts:
        row = dict(p)
        pid = str(row.get("id") or "")
        old = prev_posts.get(pid)
        old_lab = str((old or {}).get("label") or "").strip()
        new_lab = str(row.get("label") or "").strip()
        default_lab = _catalog_default_label(domain, pid) or ""
        # 开题未改 label（仍是目录默认）且先前已有非默认文案 → 保留先前
        if (
            old_lab
            and old_lab != new_lab
            and (not new_lab or new_lab == default_lab)
        ):
            row["label"] = old_lab
        merged_posts.append(row)
    for e in validate_staff_posts(merged_posts):
        raise ValueError(f"{domain}: {e}")
    roles = dict(prev_roles)
    roles["staff_posts"] = merged_posts
    roles["allowAppointFromUsers"] = allow_appoint_from_users(
        domain,
        archetype,
        archetypes,
        proposal_text=proposal_text,
        title=title,
    )
    # 门户 user：开题写到才替换；否则保留 schema 原 label
    user_aliases = _USER_LABEL_ALIASES.get(domain) or ()
    title_hit = _pick_label_from_proposal(title, user_aliases)
    body_hit = _pick_label_from_proposal(proposal_text, user_aliases)
    user_picked = title_hit or body_hit
    prev_user_lab = str((roles.get("user") or {}).get("label") or "").strip()
    generic_user = user_aliases[-1] if user_aliases else ""
    # 题名未写称呼时：
    # - builder 已是特称（宠主/接种人）→ 正文别名不得改
    # - 正文仅命中泛称（患者）→ 不得盖掉 builder 已有别名
    if user_picked and not title_hit and prev_user_lab in user_aliases:
        if prev_user_lab != generic_user and user_picked != prev_user_lab:
            user_picked = None
        elif user_picked == generic_user and user_picked != prev_user_lab:
            user_picked = None
    if user_picked and isinstance(roles.get("user"), dict):
        roles["user"] = {**roles["user"], "label": user_picked}
    clerks = [p for p in merged_posts if p.get("kind") == "clerk"]
    if clerks:
        first = clerks[0]
        prev_sub = prev_roles.get("subadmin") if isinstance(prev_roles.get("subadmin"), dict) else {}
        # 子管文案：优先本轮 clerk label；若 clerk 仍是默认且 subadmin 曾被 Island 改过则保留
        clerk_lab = str(first.get("label") or "").strip()
        default_clerk = _catalog_default_label(domain, str(first.get("id") or "")) or ""
        prev_sub_lab = str(prev_sub.get("label") or "").strip()
        if (
            prev_sub_lab
            and clerk_lab == default_clerk
            and prev_sub_lab != default_clerk
            and not _pick_label_from_proposal(
                proposal_text, _POST_LABEL_ALIASES.get(str(first.get("id") or ""), ())
            )
        ):
            sub_lab = prev_sub_lab
            # 与保留的子管文案对齐，避免 SQL 种子 nickname 再盖回目录默认
            for p in merged_posts:
                if p.get("id") == first.get("id"):
                    p["label"] = sub_lab
                    break
        else:
            sub_lab = clerk_lab or prev_sub_lab or "经办员"
        roles["subadmin"] = {
            "id": "subadmin",
            "label": sub_lab,
            "staffPostId": first.get("id"),
        }
        # EVENT：档案「责任*」列跟一线岗——社区网格员在门户 user，其余跟子管
        if domain == "DOM-EVENT" and sub_lab:
            user_lab = str((roles.get("user") or {}).get("label") or "").strip()
            author_lab = user_lab if user_lab == "网格员" else sub_lab
            arch = ((schema.get("entities") or {}).get("archive") or {})
            fields = arch.get("fields")
            if isinstance(fields, list):
                new_fields = []
                for f in fields:
                    if isinstance(f, dict) and f.get("key") == "author":
                        new_fields.append({**f, "label": author_lab})
                    else:
                        new_fields.append(f)
                ents = dict(schema.get("entities") or {})
                ents["archive"] = {**arch, "fields": new_fields}
                schema["entities"] = ents
        _restore_crm_pending_when_account_mgr(schema, clerks)
    else:
        roles.pop("subadmin", None)
    schema["roles"] = roles
    # 只下发本域岗位实际挂到的 pack，避免把 slot_ops/reservations 等空壳写进无关域
    used_packs: set[str] = set()
    for p in merged_posts:
        for pk in p.get("packs") or []:
            if isinstance(pk, str) and pk.strip():
                used_packs.add(pk.strip())
    schema["staffPackMenus"] = {
        k: sorted(v) for k, v in PACK_ADMIN_MENUS.items() if k in used_packs
    }
    schema["staffPackPages"] = {
        k: sorted(v) for k, v in PACK_WORK_PAGES.items() if k in used_packs
    }
    _ensure_category_entity(schema)
    return schema


def _ensure_category_entity(schema: dict[str, Any]) -> None:
    """菜单有 category 时补薄实体，避免 QA/论文口径「菜单有、entities 无」。"""
    admin = (schema.get("menus") or {}).get("admin") or []
    if not isinstance(admin, list):
        return
    cat_menu = next(
        (m for m in admin if isinstance(m, dict) and m.get("key") == "category"),
        None,
    )
    if not cat_menu:
        return
    ents = schema.setdefault("entities", {})
    if not isinstance(ents, dict) or "category" in ents:
        return
    lab = str(cat_menu.get("label") or "分类").removesuffix("管理").strip() or "分类"
    arch = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
    for f in arch.get("fields") or []:
        if isinstance(f, dict) and f.get("key") == "category" and f.get("label"):
            lab = str(f["label"]).strip() or lab
            break
    ents["category"] = {"key": "category", "label": lab, "labelPlural": lab}


def domain_has_workers(
    domain: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    *,
    proposal_text: str = "",
) -> bool:
    return any(
        p.get("kind") == "worker"
        for p in staff_posts_for_domain(
            domain, archetype, archetypes, proposal_text=proposal_text
        )
    )


def append_staff_seed_sql(
    sql: str,
    domain: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    *,
    proposal_text: str = "",
    title: str = "",
    posts: list[dict[str, Any]] | None = None,
) -> str:
    """幂等补岗位种子：首个 clerk 绑 subadmin；其余 clerk / 全部 worker 各一账号。

    posts 优先用 schema.roles.staff_posts（含开题/Island 文案）；缺省再按域+开题合成。
    """
    if isinstance(posts, list) and posts:
        use_posts = [dict(p) for p in posts if isinstance(p, dict) and p.get("id")]
        use_posts = _apply_scene_post_labels(
            use_posts, domain, title=title, proposal_text=proposal_text
        )
    else:
        use_posts = staff_posts_for_domain(
            domain,
            archetype,
            archetypes,
            proposal_text=proposal_text,
            title=title,
        )
    clerks = [p for p in use_posts if p.get("kind") == "clerk"]
    workers = [p for p in use_posts if p.get("kind") == "worker"]
    if not clerks and not workers:
        return sql
    lines = [
        "",
        "-- staff posts (clerk / worker)",
        "UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;",
    ]
    phone_base = 13800000010
    phone_i = 0

    def _insert_staff(pid: str, label: str, kind: str) -> None:
        nonlocal phone_i
        safe = str(label or pid).replace("'", "''")
        pwd = f"{pid}123"
        phone = str(phone_base + phone_i)
        phone_i += 1
        lines.append(
            "INSERT INTO sys_user "
            "(username, password, role, nickname, phone, profile_json, "
            "super_admin, profile_editable, enabled, staff_post, staff_kind) "
            f"VALUES ('{pid}', '{pwd}', 'admin', '{safe}', '{phone}', '{{}}', "
            f"0, 1, 1, '{pid}', '{kind}') "
            "ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), "
            "staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), "
            "role='admin', super_admin=0;"
        )

    if clerks:
        c0 = clerks[0]
        cid = str(c0["id"])
        clabel = str(c0.get("label") or cid).replace("'", "''")
        # 双角色模板可能无 subadmin 行：开题挂岗时幂等补账号
        lines.append(
            "INSERT INTO sys_user "
            "(username, password, role, nickname, phone, profile_json, "
            "super_admin, profile_editable, enabled, staff_post, staff_kind) "
            f"VALUES ('subadmin', 'sub123', 'admin', '{clabel}', '13800000001', '{{}}', "
            f"0, 1, 1, '{cid}', 'clerk') "
            "ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), "
            "staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), "
            "role='admin', super_admin=0;"
        )
        for c in clerks[1:]:
            _insert_staff(str(c["id"]), str(c.get("label") or c["id"]), "clerk")
    for w in workers:
        _insert_staff(str(w["id"]), str(w.get("label") or w["id"]), "worker")
    return sql.rstrip() + "\n" + "\n".join(lines) + "\n"
