"""审批/填报组加厚：撤回/退回再提、意见短语、审意见字数、时限催办、抄送知会；
第二批：转审一跳、请假代审、审意见附件、抄送评论、限时自动通过（默认关）；
第三批：CERT/SEAL/FLEET/EXPENSE/VISITOR 域皮字段（含办结闸补厚）；
第四批：访客黑名单、学分上限、一人一课、证书查重、比价 N 家、合同/许可到期提醒；
第五批：评教开放窗口、加班核定小时、用车驾乘人、劳动/查寝必附、伦理批件编号有效期；
第六批：通行码到期失效、回场油量、劳动地点、宣传尺寸悬挂、伦理会议决议、学籍生效日；
第七批：证明流水号、用车过路附件、宣传反馈照、合同版本号、装修禁噪窗、访客邀约码；
第八批：用印现场照、证明份数上限、合同签署方、准入学时累计、车辆年检到期、大创成员变更；
第九批：采购预算闸、查寝异常类型、访客来访目的、用车违章责任人、装修整改说明、大创材料节点提醒；
第十批：社团复制上年、采购退货登记、综测异议、大创经费使用、评教维度权重、访客时段余量。
第十一批：大创查重外链、查寝连续未归预警、党员阶段登记、督导听课、学籍课表影响说明、合同金额大写。
第十二批：报销明细子表、出差行程子表、评教结果对学生不可见、合同意见对签署方可见、大创变更日志、证明真伪查询码。
第十三批：访客现场补录、查寝楼栋长代登记、社团成员名册子表、车辆通行证车位互斥、评教未评催评、合同续签。
第十四批：合同到期续签提醒加深、证明领取核销码、准入考试成绩门槛、查寝抽查任务、评教先评后查分、审批人均耗时简表。
第十五批：申请附件覆盖留旧、证明领取二维码、真伪页加深、访客通行证打印、查寝楼长日报、评教院系汇总导出。
第十六批：用印台账 CSV、综测证据材料清单、党员阶段材料清单模板、思想汇报/心得清单项。
第十七批：证明/用印/大创中期/伦理意见书套打页、报销影像张数提示、用车驾驶员资质清单；PROCURE 一键入库以 borrow_thicken 为准不重做。

硬约束
------
- 只挂 APPROVE_DOMAINS（23 域）；不改 apply/repair/follow/borrow thicken 共享语义。
- 撤回 / 退回再提 / dueSoon / reassign：调用既有 Store，不收紧共享状态机。
- 审意见字数 ≠ 申请正文 minRemarkWords；抄送默认关，非本组不发信。
- 限时自动通过默认 hours=0；扫词才打开，禁止默认自动审过。
- 意见短语为 schema 字面量，无独立短语表。
- 黑名单复用 apply_blacklist 表/Store；不把 VISITOR 塞进 APPLY_DOMAINS。
- 第五批：LABOR/CHECKIN 只复用 requireAttach；评教窗口对齐 applyDeadline 闸；不做人脸/排班引擎。
- 第六批：通行码失效只展示+软闸，不改审批状态机；LABOR 地点不再叠 requireAttach；FLEET 油量不改里程/驾乘人语义。
- 第七批：CERT 流水号≠ serial_no/award_cert_no；FLEET 附件不改油量/驾乘；PROMO 只开本域 requireCloseAttach；VISITOR 不进 APPLY_DOMAINS。
- 第八批：SEAL 结案附件不改份数/监印；CARPASS 年检不改通行码软闸；LABSAFE 学时不叠 exam；VISITOR 不进 APPLY_DOMAINS。
- 第九批：FLEET 违章不改附件/油量/驾乘；CHECKIN/VISITOR 字典只写本域选项列；PROCURE 预算不改比价行；FITOUT 整改不改禁噪窗；PROJ 节点提醒不改成员变更。不新开附件槽。
- 第十批：CLUB 复制只回填已有说明/附件；PROCURE 退货不改预算闸；MORAL 异议不挂资助公示、不写 allowObjectionWindow；PROJ 经费不改节点/成员；EVAL 权重不改报修/面试维度皮；VISITOR 日余量不复用 occupy_span。不新开附件槽。
- 第十一批：PROJ 外链不改经费/成员/节点；CHECKIN 预警只读异常类型、不叠必附；PARTY 不上 material_check；EVAL 听课不改维度权重；ACAD 不影响生效日；CONTRACT 不改签署方/版本号/到期提醒。不新开附件槽。
- 第十二批：EXPENSE 明细走 ticket_expense_line 子表（禁止 JSON 列）；TRIP 行程走 ticket_trip_leg 子表；不改发票张数/必附/加班小时。EVAL 隐藏结果不改权重/听课；CONTRACT 可见性不改金额/签署方/版本号；PROJ 变更日志不改成员/经费/查重；CERT 查伪码≠流水号/领取码/code_qr。不新开附件槽。
- 第十三批：VISITOR 现场补录不改黑名单/邀约/日余量；CHECKIN 代登记不叠必附/连续未归、不复用 proxy_name；CLUB 名册走 ticket_club_member 子表，不改复制上年；CARPASS 车位互斥不改通行码软闸/年检；EVAL 催评不改权重/听课/隐藏结果；CONTRACT 续签另列，不改到期提醒/金额/签署方/意见可见。不新开附件槽。
- 第十四批：CONTRACT 到期提醒只加深站内信对象/文案，不改 renew_on；CERT 领取核销码≠真伪码/流水号；LABSAFE 门槛复用 ExamStore，不改学时；CHECKIN 抽查浅抽样，不叠代登记/连续未归；EVAL 先评后查分只挡成绩读取，不改 GRADE 写库；人均耗时只读统计。不新开附件槽。
- 第十五批：申请附件覆盖写入子表 ticket_attach_rev，不改办结附件槽/报修附件语义；CERT 领取码出示二维码≠套打/真伪码；真伪页只加深展示；VISITOR 打印通行码≠道闸；CHECKIN 日报只读汇总不叠抽查；EVAL 院系导出不改先评后查分。不新开附件槽。
- 第十六批：SEAL 台账只加深记录导出，不改份数/监印/现场照/套打 PDF；MORAL/PARTY 只复用 material_check 种子，不新开附件槽、不挂资助公示、不改 party_stage/stage_on。
- 第十七批：套打只走共用 print 壳+四套公文版式，≠ CA/真 PDF 引擎；EXPENSE 张数只加深提示不新开多文件槽；FLEET 资质复用 material_check，不叠过路费 requireAttach 语义；PROCURE 入库不在本组重写（borrow_thicken）。
"""

from __future__ import annotations

import re
from typing import Any

APPROVE_DOMAINS = frozenset(
    {
        "DOM-LABSAFE",
        "DOM-SEAL",
        "DOM-FLEET",
        "DOM-CERT",
        "DOM-PROMO",
        "DOM-FITOUT",
        "DOM-ACAD",
        "DOM-TRIP",
        "DOM-EXPENSE",
        "DOM-CREDIT",
        "DOM-LABOR",
        "DOM-EVAL",
        "DOM-MORAL",
        "DOM-AWARD",
        "DOM-PROCURE",
        "DOM-CLUB",
        "DOM-PROJ",
        "DOM-ETHIC",
        "DOM-PARTY",
        "DOM-CONTRACT",
        "DOM-CARPASS",
        "DOM-VISITOR",
        "DOM-CHECKIN",
    }
)

_DEFAULT_APPROVE_PHRASES = (
    "同意，按申请办理。",
    "材料齐全，予以通过。",
    "情况属实，准予办理。",
    "材料不全，请补充后重新提交。",
    "不符合规定，不予通过。",
)

_AUTO_PASS_TERMS = re.compile(
    r"限时自动通过|超时自动通过|审批超时自动|到期自动通过|自动审过"
)

_APPROVE_DELEGATE_DDL = """
CREATE TABLE IF NOT EXISTS approve_delegate (
  username VARCHAR(64) PRIMARY KEY,
  delegate_username VARCHAR(64) NOT NULL,
  until_at DATETIME NOT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_approve_delegate_to (delegate_username, until_at)
);
"""


def ensure_approve_delegate_sql(sql: str, *, enabled: bool) -> str:
    """请假代审浅表；仅审批组 allowApproveDelegate 时注入。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?approve_delegate`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _APPROVE_DELEGATE_DDL


def _ticket_fk_clause(ticket_table: str | None, constraint: str) -> str:
    """子表挂单据：ticket_id 指向本域申请表，方便论文里画 1:N 并讲外键。"""
    t = (ticket_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return ""
    return (
        f",\n  CONSTRAINT {constraint} FOREIGN KEY (ticket_id) "
        f"REFERENCES `{t}` (id) ON DELETE CASCADE"
    )


_TICKET_EXPENSE_LINE_DDL = """
CREATE TABLE IF NOT EXISTS ticket_expense_line (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  line_no INT NOT NULL,
  category VARCHAR(32) NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  note VARCHAR(128) NOT NULL DEFAULT '',
  UNIQUE KEY uk_ticket_expense_line (ticket_id, line_no),
  KEY idx_ticket_expense_line_ticket (ticket_id){fk}
);
"""

_TICKET_TRIP_LEG_DDL = """
CREATE TABLE IF NOT EXISTS ticket_trip_leg (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  line_no INT NOT NULL,
  from_place VARCHAR(64) NOT NULL,
  via_place VARCHAR(64) NOT NULL DEFAULT '',
  to_place VARCHAR(64) NOT NULL,
  on_date VARCHAR(32) NOT NULL,
  UNIQUE KEY uk_ticket_trip_leg (ticket_id, line_no),
  KEY idx_ticket_trip_leg_ticket (ticket_id){fk}
);
"""


def ensure_ticket_expense_line_sql(
    sql: str, *, enabled: bool, ticket_table: str | None
) -> str:
    """报销一行一类费用；开 allowExpenseLines 才建表，不用 JSON 塞进申请单。"""
    if not enabled:
        return sql
    if re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?ticket_expense_line`?\b", sql
    ):
        return sql
    fk = _ticket_fk_clause(ticket_table, "fk_ticket_expense_line_ticket")
    return sql.rstrip() + "\n" + _TICKET_EXPENSE_LINE_DDL.format(fk=fk)


def ensure_ticket_trip_leg_sql(
    sql: str, *, enabled: bool, ticket_table: str | None
) -> str:
    """出差一段一行；开 allowTripLegs 才建表，不用 JSON 塞进申请单。"""
    if not enabled:
        return sql
    if re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?ticket_trip_leg`?\b", sql
    ):
        return sql
    fk = _ticket_fk_clause(ticket_table, "fk_ticket_trip_leg_ticket")
    return sql.rstrip() + "\n" + _TICKET_TRIP_LEG_DDL.format(fk=fk)


_TICKET_CLUB_MEMBER_DDL = """
CREATE TABLE IF NOT EXISTS ticket_club_member (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  line_no INT NOT NULL,
  member_name VARCHAR(64) NOT NULL,
  student_no VARCHAR(32) NOT NULL DEFAULT '',
  UNIQUE KEY uk_ticket_club_member (ticket_id, line_no),
  KEY idx_ticket_club_member_ticket (ticket_id){fk}
);
"""


_CHECKIN_SPOT_TASK_DDL = """
CREATE TABLE IF NOT EXISTS checkin_spot_task (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  on_date VARCHAR(32) NOT NULL,
  sample_n INT NOT NULL,
  created_by VARCHAR(64) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_checkin_spot_task_item (item_id, on_date)
);
"""

_CHECKIN_SPOT_MEMBER_DDL = """
CREATE TABLE IF NOT EXISTS checkin_spot_member (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  task_id BIGINT NOT NULL,
  line_no INT NOT NULL,
  username VARCHAR(64) NOT NULL,
  UNIQUE KEY uk_checkin_spot_member (task_id, line_no),
  KEY idx_checkin_spot_member_user (username),
  CONSTRAINT fk_checkin_spot_member_task FOREIGN KEY (task_id) REFERENCES checkin_spot_task (id) ON DELETE CASCADE
);
"""


_TICKET_ATTACH_REV_DDL = """
CREATE TABLE IF NOT EXISTS ticket_attach_rev (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  line_no INT NOT NULL,
  attach_url VARCHAR(255) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ticket_attach_rev (ticket_id, line_no),
  KEY idx_ticket_attach_rev_ticket (ticket_id){fk}
);
"""


def ensure_ticket_attach_rev_sql(
    sql: str, *, enabled: bool, ticket_table: str | None
) -> str:
    """申请附件覆盖留旧：一行一版历史；开 allowAttachKeepOld 才建，不改 attach_url 当前指针。"""
    if not enabled:
        return sql
    if re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?ticket_attach_rev`?\b", sql
    ):
        return sql
    fk = _ticket_fk_clause(ticket_table, "fk_ticket_attach_rev_ticket")
    return sql.rstrip() + "\n" + _TICKET_ATTACH_REV_DDL.format(fk=fk)


def ensure_checkin_spot_sql(sql: str, *, enabled: bool) -> str:
    """查寝抽查：任务头 + 名册子表；开 allowCheckinSpot 才建。"""
    if not enabled:
        return sql
    out = sql
    if not re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?checkin_spot_task`?\b", out
    ):
        out = out.rstrip() + "\n" + _CHECKIN_SPOT_TASK_DDL
    if not re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?checkin_spot_member`?\b", out
    ):
        out = out.rstrip() + "\n" + _CHECKIN_SPOT_MEMBER_DDL
    return out


def ensure_ticket_club_member_sql(
    sql: str, *, enabled: bool, ticket_table: str | None
) -> str:
    """社团年审一行一人；开 allowClubRoster 才建表。"""
    if not enabled:
        return sql
    if re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?ticket_club_member`?\b", sql
    ):
        return sql
    fk = _ticket_fk_clause(ticket_table, "fk_ticket_club_member_ticket")
    return sql.rstrip() + "\n" + _TICKET_CLUB_MEMBER_DDL.format(fk=fk)


_TICKET_RATING_DIM_DDL = """
CREATE TABLE IF NOT EXISTS ticket_rating_dim (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  dim_key VARCHAR(64) NOT NULL,
  score INT NOT NULL,
  UNIQUE KEY uk_ticket_rating_dim (ticket_id, dim_key),
  KEY idx_ticket_rating_dim_ticket (ticket_id){fk}
);
"""

_TICKET_COMPANION_DDL = """
CREATE TABLE IF NOT EXISTS ticket_companion (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  line_no INT NOT NULL,
  name VARCHAR(64) NOT NULL,
  UNIQUE KEY uk_ticket_companion (ticket_id, line_no),
  KEY idx_ticket_companion_ticket (ticket_id){fk}
);
"""


def ensure_ticket_rating_dim_sql(
    sql: str, *, enabled: bool, ticket_table: str | None
) -> str:
    """多维评分一行一维度；不用 rating_dims_json。"""
    if not enabled:
        return sql
    if re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?ticket_rating_dim`?\b", sql
    ):
        return sql
    fk = _ticket_fk_clause(ticket_table, "fk_ticket_rating_dim_ticket")
    return sql.rstrip() + "\n" + _TICKET_RATING_DIM_DDL.format(fk=fk)


def ensure_ticket_companion_sql(
    sql: str, *, enabled: bool, ticket_table: str | None
) -> str:
    """随行人员一行一名；不用 companion_names 逗号串。"""
    if not enabled:
        return sql
    if re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?ticket_companion`?\b", sql
    ):
        return sql
    fk = _ticket_fk_clause(ticket_table, "fk_ticket_companion_ticket")
    return sql.rstrip() + "\n" + _TICKET_COMPANION_DDL.format(fk=fk)


#: 审批域档案浅列（只增不减）
APPROVE_ARCHIVE_COLUMNS_BY_DOMAIN: dict[str, list[tuple[str, str]]] = {
    "DOM-CREDIT": [("credit", "DECIMAL(10,2) NULL")],
    "DOM-CERT": [("max_issue_copies", "INT NULL")],
    "DOM-CONTRACT": [
        ("expire_on", "VARCHAR(32) DEFAULT ''"),
        ("expire_soon_notified_at", "DATETIME NULL"),
        ("sign_remark_visible", "TINYINT NOT NULL DEFAULT 1"),
    ],
    "DOM-LABSAFE": [
        ("expire_on", "VARCHAR(32) DEFAULT ''"),
        ("expire_soon_notified_at", "DATETIME NULL"),
        ("train_hours_total", "DECIMAL(10,1) NULL"),
        ("exam_pass_min", "INT NULL"),
    ],
    "DOM-CARPASS": [
        ("inspect_expire_on", "VARCHAR(32) DEFAULT ''"),
        ("expire_soon_notified_at", "DATETIME NULL"),
        ("parking_mutex", "TINYINT NOT NULL DEFAULT 0"),
    ],
    "DOM-EVAL": [
        ("eval_open_on", "VARCHAR(32) DEFAULT ''"),
        ("eval_close_on", "VARCHAR(32) DEFAULT ''"),
        ("teaching_weight", "DECIMAL(10,1) NULL"),
        ("attitude_weight", "DECIMAL(10,1) NULL"),
        ("content_weight", "DECIMAL(10,1) NULL"),
        ("hide_eval_result", "TINYINT NOT NULL DEFAULT 0"),
        ("college", "VARCHAR(64) DEFAULT ''"),
    ],
    "DOM-ETHIC": [
        ("batch_no", "VARCHAR(64) DEFAULT ''"),
        ("expire_on", "VARCHAR(32) DEFAULT ''"),
        ("meeting_on", "VARCHAR(32) DEFAULT ''"),
        ("resolution_note", "VARCHAR(512) DEFAULT ''"),
    ],
    "DOM-PROMO": [
        ("promo_size", "VARCHAR(64) DEFAULT ''"),
        ("hang_place", "VARCHAR(128) DEFAULT ''"),
    ],
    "DOM-FITOUT": [
        ("quiet_start", "VARCHAR(8) DEFAULT ''"),
        ("quiet_end", "VARCHAR(8) DEFAULT ''"),
    ],
    "DOM-VISITOR": [
        ("apply_invite_code", "VARCHAR(64) DEFAULT ''"),
        ("visit_slot_cap", "INT NULL"),
    ],
    "DOM-PROCURE": [("budget_total", "DECIMAL(12,2) NULL")],
    "DOM-PROJ": [
        ("mid_due_on", "VARCHAR(32) DEFAULT ''"),
        ("final_due_on", "VARCHAR(32) DEFAULT ''"),
        ("expire_soon_notified_at", "DATETIME NULL"),
    ],
    "DOM-CHECKIN": [("absent_warn_n", "INT NULL")],
}


def ensure_approve_archive_columns(
    sql: str,
    *,
    domain: str | None,
    item_table: str | None,
) -> str:
    """审批组档案浅字段注入（学分/到期日等）。"""
    from app.bake.sql.fragments import _CREATE_TABLE_RE, _inject_missing_columns

    cols = APPROVE_ARCHIVE_COLUMNS_BY_DOMAIN.get(domain or "")
    if not cols:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, cols)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


def scan_approve_auto_pass(text: str) -> bool:
    return bool(_AUTO_PASS_TERMS.search(text or ""))


def _live_schema(spec: dict[str, Any]) -> dict[str, Any]:
    schema = spec.get("schema")
    if not isinstance(schema, dict):
        schema = {}
        spec["schema"] = schema
    return schema


def _add_feature(spec: dict[str, Any], name: str, status: str = "flow") -> None:
    features = list(spec.get("features") or [])
    names = {f.get("name") for f in features if isinstance(f, dict)}
    if name not in names:
        features.append({"name": name, "status": status})
        spec["features"] = features


def _ensure_cap(spec: dict[str, Any], cap: str) -> None:
    caps = list(spec.get("capabilities") or [])
    if cap not in caps:
        caps.append(cap)
        spec["capabilities"] = caps


def _force_deadline(spec: dict[str, Any], *, menu_label: str) -> None:
    """挂 deadline 能力 + slaDeadline；催办文案走审批皮，不改借还 dueSoon 默认句。"""
    from app.bake.features.core_cap_scan import DEADLINE_CAP

    _ensure_cap(spec, DEADLINE_CAP)
    schema = _live_schema(spec)
    ents = schema.setdefault("entities", {})
    ticket = ents.get("ticket") if isinstance(ents.get("ticket"), dict) else {}
    if not isinstance(ticket, dict):
        ticket = {}
    ticket["slaDeadline"] = True
    ticket["pickLoanPeriod"] = False
    ticket.setdefault("dueLabel", menu_label)
    ents["ticket"] = ticket
    labels = schema.setdefault("labels", {})
    labels["deadlineMenuLabel"] = menu_label
    labels.setdefault("deadlineLabel", menu_label)
    spec["schema"] = schema
    _add_feature(spec, f"{menu_label}催办")


def apply_approve_thicken_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """按域默认加厚审批组 schema（只增不减；非本组原样返回）。"""
    domain = str(spec.get("domain") or "")
    if domain not in APPROVE_DOMAINS:
        return spec
    text = proposal_text or ""

    schema = _live_schema(spec)
    ents = schema.setdefault("entities", {})
    ticket = ents.get("ticket") if isinstance(ents.get("ticket"), dict) else {}
    if not isinstance(ticket, dict):
        ticket = {}
    labels = schema.setdefault("labels", {})
    thicken = schema.get("approveThicken") if isinstance(schema.get("approveThicken"), dict) else {}

    ticket["approveThicken"] = True
    thicken["core"] = True

    # —— 第一批 ——
    labels.setdefault(
        "withdrawHint",
        "待审单据可撤销；撤销后不可再改，如需继续请重新提交。",
    )
    thicken["withdraw"] = True
    _add_feature(spec, "申请人撤回未审单据")

    if not int(ticket.get("maxReviseTimes") or 0):
        ticket["maxReviseTimes"] = 3
    labels.setdefault(
        "maxReviseHint",
        "退回修改有次数上限；达上限后请联系管理员处理或重新发起。",
    )
    thicken["returnRevise"] = True
    _add_feature(spec, "审批退回修改后再提")

    if not isinstance(ticket.get("approvePhrases"), list) or not ticket.get("approvePhrases"):
        ticket["approvePhrases"] = list(_DEFAULT_APPROVE_PHRASES)
    labels.setdefault("approvePhraseLabel", "常用意见")
    labels.setdefault("approvePhraseHint", "点选后填入审核意见，仍可再改。")
    thicken["phrases"] = True
    _add_feature(spec, "审批常用意见短语")

    if not int(ticket.get("minApproveRemarkWords") or 0):
        ticket["minApproveRemarkWords"] = 4
    labels.setdefault(
        "minApproveRemarkHint",
        "通过或驳回时请填写审核意见（不少于设定字数）。",
    )
    thicken["minApproveRemark"] = True
    _add_feature(spec, "审批意见最少字数")

    _force_deadline(spec, menu_label="审批时限")
    if not int(ticket.get("dueSoonDays") or 0):
        ticket["dueSoonDays"] = 3
    labels.setdefault(
        "approveDueSoonHint",
        "临近办理时限时，系统向申请人发送站内提醒；管理端也可手动催办。",
    )
    thicken["dueSoon"] = True
    _add_feature(spec, "审批时限超时催办站内信")

    ticket["allowApproveCc"] = True
    labels.setdefault("approveCcLabel", "抄送知会")
    labels.setdefault(
        "approveCcHint",
        "抄送人将收到站内通知，可查看结果，不参与审批。",
    )
    thicken["approveCc"] = True
    _add_feature(spec, "审批抄送知会")

    ticket["allowApproveDurationStats"] = True
    labels.setdefault("approveDurationStatsLabel", "人均办理耗时")
    labels.setdefault(
        "approveDurationStatsHint",
        "按办理人统计从提交到审过的平均分钟数，仅供查看。",
    )
    thicken["approveDurationStats"] = True
    _add_feature(spec, "审批统计（人均耗时）简表")

    ticket["allowAttachKeepOld"] = True
    labels.setdefault("attachKeepOldLabel", "历史附件")
    labels.setdefault(
        "attachKeepOldHint",
        "更换附件后，原先的文件仍会保留在本单历史里，可随时查看。",
    )
    thicken["attachKeepOld"] = True
    _add_feature(spec, "审批附件版本覆盖留旧")

    # —— 第二批 ——
    ticket["allowApproveTransfer"] = True
    labels.setdefault("approveTransferLabel", "转审")
    labels.setdefault(
        "approveTransferHint",
        "可将本单转给其他审核人继续办理。",
    )
    thicken["transfer"] = True
    _add_feature(spec, "加签/转审（仅一跳）")

    ticket["allowApproveDelegate"] = True
    labels.setdefault("approveDelegateLabel", "请假代审")
    labels.setdefault(
        "approveDelegateHint",
        "可指定代审人与截止日期；代审人可代你办理待审单据。",
    )
    thicken["delegate"] = True
    _add_feature(spec, "审批委托（请假期间代审）")

    ticket["allowApproveRemarkAttach"] = True
    labels.setdefault("approveRemarkAttachLabel", "审核意见附件")
    labels.setdefault(
        "approveRemarkAttachHint",
        "审核时可上传说明附件，申请人可在单据中查看。",
    )
    thicken["remarkAttach"] = True
    _add_feature(spec, "审批意见附件（审时上传）")

    ticket["allowApproveCcComment"] = True
    labels.setdefault("approveCcCommentLabel", "知会评论")
    labels.setdefault(
        "approveCcCommentHint",
        "被抄送人可追加一条知会评论，不改变审批结果。",
    )
    thicken["ccComment"] = True
    _add_feature(spec, "审批抄送人可追加评论")

    # 限时自动通过：默认关；开题扫词才设小时数
    ticket.setdefault("approveAutoPassHours", 0)
    labels.setdefault(
        "approveAutoPassHint",
        "开启后，待审超过设定小时将自动通过；默认关闭，请谨慎使用。",
    )
    if scan_approve_auto_pass(text) and not int(ticket.get("approveAutoPassHours") or 0):
        ticket["approveAutoPassHours"] = 72
        ticket["allowApproveAutoPass"] = True
        thicken["autoPass"] = True
        _add_feature(spec, "审批限时自动通过")
    else:
        ticket.setdefault("allowApproveAutoPass", False)
        thicken.setdefault("autoPass", False)
        _add_feature(spec, "审批限时自动通过（默认关）")

    # —— 第三批域皮（只增本域；不改报名/报修已有字段语义）——
    # 补厚：字段须挂规则/办结闸/管理回填，禁止只打标。
    if domain == "DOM-CERT":
        ticket["allowCertPickup"] = True
        labels.setdefault("certPickupLabel", "领取方式")
        labels.setdefault(
            "certPickupHint",
            "选择自取或邮寄；邮寄须填收件地址，办结前由工作人员回填快递单号。",
        )
        labels.setdefault("mailAddressLabel", "邮寄地址")
        labels.setdefault("expressNoLabel", "快递单号")
        labels.setdefault("expressNoHint", "邮寄件办结前须回填快递单号，申请人可在进度中查看。")
        thicken["certPickup"] = True
        _add_feature(spec, "证明领取方式（自取/邮寄地址）")
        ticket["allowCertUrgent"] = True
        labels.setdefault("certUrgentLabel", "加急件")
        labels.setdefault(
            "certUrgentHint",
            "加急件在待办列表优先展示，仍须按审批流程办完。",
        )
        thicken["certUrgent"] = True
        _add_feature(spec, "证明加急件标记")
    elif domain == "DOM-SEAL":
        ticket["allowSealCopies"] = True
        labels.setdefault("sealCopiesLabel", "用印份数")
        labels.setdefault("bindNoteLabel", "装订说明")
        labels.setdefault(
            "sealCopiesHint",
            "申请时填写用印份数与装订说明；办结时回填份号并勾选监印确认。",
        )
        labels.setdefault("sealCopyNosLabel", "用印份号")
        labels.setdefault("sealWitnessAckLabel", "监印人已确认")
        labels.setdefault("sealWitnessHint", "办结前须填写份号并勾选监印确认。")
        thicken["sealCopies"] = True
        _add_feature(spec, "用印文件份数与装订说明")
    elif domain == "DOM-FLEET":
        ticket["allowFleetMileage"] = True
        labels.setdefault("mileageLabel", "行驶里程（公里）")
        labels.setdefault("fuelNoteLabel", "油耗备注")
        labels.setdefault(
            "fleetMileageHint",
            "办结时须回填实际里程（大于 0）与油耗说明，缺一不可。",
        )
        thicken["fleetMileage"] = True
        _add_feature(spec, "用车里程回填与油耗备注")
    elif domain == "DOM-EXPENSE":
        ticket["allowExpenseInvoice"] = True
        ticket["requireAttach"] = True
        labels.setdefault("invoiceCountLabel", "发票张数")
        labels.setdefault("expenseAmountLabel", "报销金额（元）")
        labels.setdefault(
            "expenseInvoiceHint",
            "请填写发票张数与报销金额，并上传票据影像；张数至少 1 张，金额须大于 0。",
        )
        thicken["expenseInvoice"] = True
        _add_feature(spec, "报销发票张数/金额校验规则")
    elif domain == "DOM-VISITOR":
        ticket["allowVisitorCount"] = True
        labels.setdefault("visitorCountLabel", "随行人数")
        labels.setdefault(
            "visitorCountHint",
            "不含被访人；无随行填 0。有随行须填写同行人姓名。",
        )
        labels.setdefault("companionNamesLabel", "随行人姓名")
        labels.setdefault("companionNamesHint", "随行人数大于 0 时必填，多人用逗号分隔。")
        thicken["visitorCount"] = True
        _add_feature(spec, "访客随行人数字段")

    # —— 第四批：规则/管理动作（复用既有闸，域皮文案隔离）——
    if domain == "DOM-VISITOR":
        from app.bake.features.apply_thicken import _attach_apply_blacklist_menus

        schema["applyBlacklist"] = True
        ticket["allowApplyBlacklist"] = True
        labels.setdefault("applyBlacklistMenuLabel", "访客黑名单")
        labels.setdefault("applyBlacklistTitle", "访客黑名单")
        labels.setdefault(
            "applyBlacklistLead",
            "维护禁止预约的账号；名单内用户提交访客预约时将被拒绝。",
        )
        labels.setdefault("applyBlacklistDenyMessage", "当前账号暂不可预约访客，请联系管理员。")
        _attach_apply_blacklist_menus(schema)
        thicken["visitorBlacklist"] = True
        _add_feature(spec, "访客黑名单（禁止预约）")
    if domain == "DOM-CREDIT":
        ticket["semesterCreditCap"] = int(ticket.get("semesterCreditCap") or 0) or 30
        ticket["creditWarnRemaining"] = int(ticket.get("creditWarnRemaining") or 0) or 4
        labels.setdefault(
            "creditCapHint",
            "已认定学分合计不可超过学期上限；接近上限时会提示剩余额度。",
        )
        labels.setdefault("semesterCreditCapHint", labels["creditCapHint"])
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list) and not any(
                isinstance(f, dict) and f.get("key") == "credit" for f in fields
            ):
                fields.append({"key": "credit", "label": "认定学分", "type": "number"})
        thicken["creditCap"] = True
        _add_feature(spec, "第二课堂学分上限校验")
    if domain == "DOM-EVAL":
        ticket["forceOnePerArchive"] = True
        ticket["allowMultiTicket"] = False
        labels.setdefault(
            "onePerArchiveDenyMessage",
            "同一课程仅可提交一次评教，请勿重复提交。",
        )
        labels.setdefault(
            "evalOnePerCourseHint",
            "一人一课：同一门课进行中或已评单据不可再提。",
        )
        thicken["evalOnePerCourse"] = True
        _add_feature(spec, "评教一人一课防重复提交")
    if domain == "DOM-AWARD":
        ticket["allowAwardCertNo"] = True
        labels.setdefault("awardCertNoLabel", "证书编号")
        labels.setdefault(
            "awardCertNoHint",
            "请填写证书编号；系统将查重，相同编号不可重复登记。",
        )
        thicken["awardCertNo"] = True
        _add_feature(spec, "获奖证书编号查重")
    if domain == "DOM-PROCURE":
        ticket["minVendorQuotes"] = int(ticket.get("minVendorQuotes") or 0) or 3
        ticket["allowVendorQuotes"] = True
        labels.setdefault("vendorQuotesLabel", "比价供应商")
        labels.setdefault(
            "vendorQuotesHint",
            "每行一家供应商名称；至少填写规定家数后才能提交。",
        )
        labels.setdefault(
            "minVendorQuotesHint",
            "采购比价至少 " + str(ticket["minVendorQuotes"]) + " 家供应商。",
        )
        thicken["minVendorQuotes"] = True
        _add_feature(spec, "采购比价至少 N 家供应商校验")
    if domain in ("DOM-CONTRACT", "DOM-LABSAFE"):
        ticket["notifyArchiveExpireDays"] = int(ticket.get("notifyArchiveExpireDays") or 0) or 7
        labels.setdefault(
            "archiveExpireNotifyHint",
            "合同/许可临近到期将发站内信提醒；到期日请在档案中维护。",
        )
        labels.setdefault("expireOnLabel", "到期日")
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list) and not any(
                isinstance(f, dict) and f.get("key") == "expireOn" for f in fields
            ):
                fields.append({"key": "expireOn", "label": "到期日", "type": "date"})
        thicken["archiveExpireNotify"] = True
        _add_feature(spec, "合同/许可到期站内信提醒")

    # —— 第五批：域皮字段/附件闸/办结核定（深浅分档；仍只挂本域）——
    if domain == "DOM-EVAL":
        ticket["allowEvalOpenWindow"] = True
        labels.setdefault("evalOpenOnLabel", "评教开放日")
        labels.setdefault("evalCloseOnLabel", "评教截止日")
        labels.setdefault(
            "evalOpenWindowHint",
            "仅在开放日内可提交评教；开放日与截止日由管理端在课程档案中维护。",
        )
        labels.setdefault("evalOpenWindowDenyMessage", "当前不在评教开放时间内，暂不可提交。")
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list):
                if not any(isinstance(f, dict) and f.get("key") == "evalOpenOn" for f in fields):
                    fields.append({"key": "evalOpenOn", "label": "评教开放日", "type": "date"})
                if not any(isinstance(f, dict) and f.get("key") == "evalCloseOn" for f in fields):
                    fields.append({"key": "evalCloseOn", "label": "评教截止日", "type": "date"})
        thicken["evalOpenWindow"] = True
        _add_feature(spec, "评教开放窗口（起止日期）")
    if domain == "DOM-TRIP":
        ticket["allowCompHours"] = True
        labels.setdefault("compHoursLabel", "核定调休小时")
        labels.setdefault(
            "compHoursHint",
            "办结时须回填核定调休小时数（大于 0）；申请人可在进度中查看。",
        )
        thicken["compHours"] = True
        _add_feature(spec, "加班调休核定小时数")
    if domain == "DOM-FLEET":
        ticket["allowFleetCrew"] = True
        labels.setdefault("driverNameLabel", "驾驶员")
        labels.setdefault("passengerNamesLabel", "随车人")
        labels.setdefault(
            "fleetCrewHint",
            "请填写驾驶员；有随车人时填写姓名，多人用逗号分隔。",
        )
        thicken["fleetCrew"] = True
        _add_feature(spec, "用车驾驶员/随车人登记")
    if domain == "DOM-LABOR":
        ticket["requireAttach"] = True
        labels.setdefault("laborAttachLabel", "劳动时长证明")
        labels.setdefault(
            "laborAttachHint",
            "请上传劳动时长证明附件后再提交。",
        )
        thicken["laborAttach"] = True
        _add_feature(spec, "劳动时长证明附件")
    if domain == "DOM-ETHIC":
        ticket["allowEthicBatch"] = True
        labels.setdefault("batchNoLabel", "批件编号")
        labels.setdefault("expireOnLabel", "批件有效期")
        labels.setdefault(
            "ethicBatchHint",
            "批件编号与有效期由管理端在审查事项档案中维护；申请人可在详情中查看。",
        )
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list):
                if not any(isinstance(f, dict) and f.get("key") == "batchNo" for f in fields):
                    fields.append({"key": "batchNo", "label": "批件编号", "type": "text"})
                if not any(isinstance(f, dict) and f.get("key") == "expireOn" for f in fields):
                    fields.append({"key": "expireOn", "label": "批件有效期", "type": "date"})
        thicken["ethicBatch"] = True
        _add_feature(spec, "伦理批件编号与有效期")
    if domain == "DOM-CHECKIN":
        ticket["requireAttach"] = True
        labels.setdefault("checkinPhotoLabel", "查寝照片")
        labels.setdefault(
            "checkinPhotoHint",
            "请上传查寝现场照片后再提交。",
        )
        thicken["checkinPhoto"] = True
        _add_feature(spec, "查寝照片必传")

    # —— 第六批：通行码失效/办结油量/申请字段/档案浅列（仍只挂本域）——
    if domain in ("DOM-VISITOR", "DOM-CARPASS"):
        ticket["allowPassExpire"] = True
        ticket["passExpireDays"] = int(ticket.get("passExpireDays") or 0) or 1
        labels.setdefault("passExpireAtLabel", "通行码有效至")
        labels.setdefault("passExpiredLabel", "已失效")
        labels.setdefault(
            "passExpireHint",
            "通行码自审过之日起 " + str(ticket["passExpireDays"]) + " 日内有效；过期后不可再出示或签到。",
        )
        thicken["passExpire"] = True
        _add_feature(spec, "访客通行码到期自动失效展示")
    if domain == "DOM-FLEET":
        ticket["allowReturnFuel"] = True
        labels.setdefault("returnFuelLabel", "回场油量")
        labels.setdefault(
            "returnFuelHint",
            "办结时须回填回场油量（0–100）；与油耗备注分开填写。",
        )
        thicken["returnFuel"] = True
        _add_feature(spec, "用车回场油量登记")
    if domain == "DOM-LABOR":
        ticket["allowLaborPlace"] = True
        labels.setdefault("laborPlaceLabel", "劳动地点")
        labels.setdefault(
            "laborPlaceHint",
            "请填写本次劳动地点后再提交。",
        )
        thicken["laborPlace"] = True
        _add_feature(spec, "劳动时长地点字段")
    if domain == "DOM-PROMO":
        ticket["allowPromoPlace"] = True
        labels.setdefault("promoSizeLabel", "尺寸")
        labels.setdefault("hangPlaceLabel", "悬挂位置")
        labels.setdefault(
            "promoPlaceHint",
            "宣传品尺寸与悬挂位置由管理端在档案中维护；申请人可在详情中查看。",
        )
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list):
                if not any(isinstance(f, dict) and f.get("key") == "promoSize" for f in fields):
                    fields.append({"key": "promoSize", "label": "尺寸", "type": "text"})
                if not any(isinstance(f, dict) and f.get("key") == "hangPlace" for f in fields):
                    fields.append({"key": "hangPlace", "label": "悬挂位置", "type": "text"})
        thicken["promoPlace"] = True
        _add_feature(spec, "宣传品尺寸/悬挂位置字段")
    if domain == "DOM-ETHIC":
        ticket["allowEthicMeeting"] = True
        labels.setdefault("meetingOnLabel", "会议日期")
        labels.setdefault("resolutionNoteLabel", "决议摘要")
        labels.setdefault(
            "ethicMeetingHint",
            "会议日期与决议摘要由管理端在审查事项档案中维护；申请人可在详情中查看。",
        )
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list):
                if not any(isinstance(f, dict) and f.get("key") == "meetingOn" for f in fields):
                    fields.append({"key": "meetingOn", "label": "会议日期", "type": "date"})
                if not any(isinstance(f, dict) and f.get("key") == "resolutionNote" for f in fields):
                    fields.append({"key": "resolutionNote", "label": "决议摘要", "type": "textarea"})
        thicken["ethicMeeting"] = True
        _add_feature(spec, "伦理会议日期与决议摘要")
    if domain == "DOM-ACAD":
        ticket["allowEffectiveOn"] = True
        labels.setdefault("effectiveOnLabel", "生效日期")
        labels.setdefault(
            "effectiveOnHint",
            "请选择学籍异动生效日期后再提交。",
        )
        thicken["effectiveOn"] = True
        _add_feature(spec, "学籍异动生效日期")

    # —— 第七批：流水号/过路附件/反馈照/版本号/禁噪窗/邀约码（仍只挂本域）——
    if domain == "DOM-CERT":
        ticket["allowCertIssueNo"] = True
        labels.setdefault("certIssueNoLabel", "开具流水号")
        labels.setdefault(
            "certIssueNoHint",
            "审核通过后自动生成开具流水号，可在详情中查看。",
        )
        thicken["certIssueNo"] = True
        _add_feature(spec, "证明开具流水号规则")
    if domain == "DOM-FLEET":
        ticket["requireAttach"] = True
        labels.setdefault("fleetTollAttachLabel", "加油票/过路费")
        labels.setdefault(
            "fleetTollAttachHint",
            "请上传加油票或过路费凭证后再提交。",
        )
        thicken["fleetTollAttach"] = True
        _add_feature(spec, "用车加油票/过路费附件")
    if domain == "DOM-PROMO":
        ticket["requireCloseAttach"] = True
        ticket["allowPromoFeedback"] = True
        labels.setdefault("promoFeedbackLabel", "投放反馈照片")
        labels.setdefault(
            "promoFeedbackHint",
            "办结前请上传投放现场反馈照片。",
        )
        thicken["promoFeedback"] = True
        _add_feature(spec, "宣传品投放反馈照片")
    if domain == "DOM-CONTRACT":
        ticket["allowDocRev"] = True
        labels.setdefault("docRevLabel", "正文版本号")
        labels.setdefault(
            "docRevHint",
            "请填写本次提交的合同正文版本号后再提交。",
        )
        thicken["docRev"] = True
        _add_feature(spec, "合同正文附件版本号")
    if domain == "DOM-FITOUT":
        ticket["allowFitoutQuiet"] = True
        labels.setdefault("fitoutWindowLabel", "施工时段")
        labels.setdefault(
            "fitoutQuietHint",
            "施工开始与结束时刻不得落在禁噪时段内。",
        )
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list):
                if not any(isinstance(f, dict) and f.get("key") == "quietStart" for f in fields):
                    fields.append({"key": "quietStart", "label": "禁噪开始", "type": "time"})
                if not any(isinstance(f, dict) and f.get("key") == "quietEnd" for f in fields):
                    fields.append({"key": "quietEnd", "label": "禁噪结束", "type": "time"})
        thicken["fitoutQuiet"] = True
        _add_feature(spec, "装修噪音时段约束提示")
    if domain == "DOM-VISITOR":
        ticket["requireApplyInvite"] = True
        labels.setdefault("visitorInviteLabel", "邀约码")
        labels.setdefault(
            "visitorInviteHint",
            "请填写被访人提供的邀约码后再提交。",
        )
        labels.setdefault("applyInviteLabel", labels["visitorInviteLabel"])
        labels.setdefault("applyInviteHint", labels["visitorInviteHint"])
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list):
                if not any(isinstance(f, dict) and f.get("key") == "applyInviteCode" for f in fields):
                    fields.append({"key": "applyInviteCode", "label": "邀约码", "type": "text"})
        thicken["visitorInvite"] = True
        _add_feature(spec, "访客邀约码（被访人生成）")

    # —— 第八批：用印现场照/份数上限/签署方/学时累计/年检到期/成员变更（仍只挂本域）——
    if domain == "DOM-SEAL":
        ticket["requireCloseAttach"] = True
        ticket["allowSealClosePhoto"] = True
        labels.setdefault("sealPhotoLabel", "用印现场照片")
        labels.setdefault(
            "sealPhotoHint",
            "办结前请上传用印现场照片。",
        )
        thicken["sealClosePhoto"] = True
        _add_feature(spec, "用印登记拍摄回传")
    if domain == "DOM-CERT":
        ticket["allowIssueCopies"] = True
        labels.setdefault("issueCopiesLabel", "开具份数")
        labels.setdefault(
            "issueCopiesHint",
            "请填写开具份数；不可超过该证明类型的份数上限。",
        )
        labels.setdefault("maxIssueCopiesLabel", "开具份数上限")
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list) and not any(
                isinstance(f, dict) and f.get("key") == "maxIssueCopies" for f in fields
            ):
                fields.append({"key": "maxIssueCopies", "label": "开具份数上限", "type": "number"})
        thicken["issueCopies"] = True
        _add_feature(spec, "证明开具份数上限")
    if domain == "DOM-CONTRACT":
        ticket["allowSignParties"] = True
        labels.setdefault("signPartiesLabel", "签署方")
        labels.setdefault(
            "signPartiesHint",
            "请勾选本次合同的签署方后再提交。",
        )
        thicken["signParties"] = True
        _add_feature(spec, "合同签署方多方勾选")
    if domain == "DOM-LABSAFE":
        ticket["allowTrainHours"] = True
        labels.setdefault("trainHoursLabel", "本次培训学时")
        labels.setdefault(
            "trainHoursHint",
            "请填写本次培训学时（大于 0）；审核通过后计入累计学时。",
        )
        labels.setdefault("trainHoursTotalLabel", "累计培训学时")
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list) and not any(
                isinstance(f, dict) and f.get("key") == "trainHoursTotal" for f in fields
            ):
                fields.append({"key": "trainHoursTotal", "label": "累计培训学时", "type": "number"})
        thicken["trainHours"] = True
        _add_feature(spec, "准入培训学时累计")
    if domain == "DOM-CARPASS":
        ticket["allowInspectExpire"] = True
        ticket["notifyArchiveExpireDays"] = int(ticket.get("notifyArchiveExpireDays") or 0) or 7
        labels.setdefault("inspectExpireOnLabel", "年检到期日")
        labels.setdefault(
            "inspectExpireHint",
            "年检临近到期将发站内信提醒；到期日请在车辆档案中维护。",
        )
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list) and not any(
                isinstance(f, dict) and f.get("key") == "inspectExpireOn" for f in fields
            ):
                fields.append({"key": "inspectExpireOn", "label": "年检到期日", "type": "date"})
        thicken["inspectExpire"] = True
        _add_feature(spec, "车辆通行证年检到期提醒")
    if domain == "DOM-PROJ":
        ticket["allowMemberChange"] = True
        labels.setdefault("memberChangeNoteLabel", "成员变更说明")
        labels.setdefault(
            "memberChangeNoteHint",
            "请说明本次成员变更（增补或退出）后再提交。",
        )
        thicken["memberChange"] = True
        _add_feature(spec, "大创项目成员变更申请")

    # —— 第九批：预算闸/异常类型/来访目的/违章责任人/整改说明/材料节点（仍只挂本域）——
    if domain == "DOM-PROCURE":
        ticket["allowProcureBudget"] = True
        labels.setdefault("procureAmountLabel", "本次申购金额（元）")
        labels.setdefault(
            "procureBudgetHint",
            "请填写申购金额；合计不可超过该采购项的预算余额。",
        )
        labels.setdefault("budgetTotalLabel", "预算总额（元）")
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list) and not any(
                isinstance(f, dict) and f.get("key") == "budgetTotal" for f in fields
            ):
                fields.append({"key": "budgetTotal", "label": "预算总额（元）", "type": "number"})
        thicken["procureBudget"] = True
        _add_feature(spec, "采购预算余额校验")
    if domain == "DOM-CHECKIN":
        ticket["allowCheckinException"] = True
        ticket["exceptionTypeOptions"] = list(
            ticket.get("exceptionTypeOptions")
            or ["未归", "晚归", "未熄灯", "其他"]
        )
        labels.setdefault("exceptionTypeLabel", "异常类型")
        labels.setdefault(
            "exceptionTypeHint",
            "请选择本次查寝异常类型后再提交。",
        )
        thicken["checkinException"] = True
        _add_feature(spec, "查寝异常类型字典")
    if domain == "DOM-VISITOR":
        ticket["allowVisitPurpose"] = True
        ticket["visitPurposeOptions"] = list(
            ticket.get("visitPurposeOptions")
            or ["公务", "参观", "面试", "其他"]
        )
        labels.setdefault("visitPurposeLabel", "来访目的")
        labels.setdefault(
            "visitPurposeHint",
            "请选择来访目的后再提交。",
        )
        thicken["visitPurpose"] = True
        _add_feature(spec, "访客来访目的字典")
    if domain == "DOM-FLEET":
        ticket["allowFleetViolation"] = True
        labels.setdefault("violationPersonLabel", "违章责任人")
        labels.setdefault(
            "violationPersonHint",
            "办结前请登记违章责任人；无违章可填无。",
        )
        thicken["fleetViolation"] = True
        _add_feature(spec, "用车违章责任人登记")
    if domain == "DOM-FITOUT":
        ticket["allowFitoutRectify"] = True
        labels.setdefault("rectifyNoteLabel", "整改说明")
        labels.setdefault(
            "rectifyNoteHint",
            "验收不合格时请填写整改说明后再提交。",
        )
        thicken["fitoutRectify"] = True
        _add_feature(spec, "装修验收不合格整改单")
    if domain == "DOM-PROJ":
        ticket["allowProjNodeRemind"] = True
        ticket["notifyArchiveExpireDays"] = int(ticket.get("notifyArchiveExpireDays") or 0) or 7
        labels.setdefault("midDueOnLabel", "中期材料节点")
        labels.setdefault("finalDueOnLabel", "结题材料节点")
        labels.setdefault(
            "projNodeRemindHint",
            "中期或结题材料节点临近将发站内信；日期请在项目档案中维护。",
        )
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list):
                if not any(isinstance(f, dict) and f.get("key") == "midDueOn" for f in fields):
                    fields.append({"key": "midDueOn", "label": "中期材料节点", "type": "date"})
                if not any(isinstance(f, dict) and f.get("key") == "finalDueOn" for f in fields):
                    fields.append({"key": "finalDueOn", "label": "结题材料节点", "type": "date"})
        thicken["projNodeRemind"] = True
        _add_feature(spec, "大创中期/结题材料节点提醒")

    # —— 第十批：复制上年/退货/综测异议/经费使用/评教权重/访客余量（仍只挂本域）——
    if domain == "DOM-CLUB":
        ticket["allowClubCopyLast"] = True
        labels.setdefault("clubCopyLastLabel", "复制上年材料")
        labels.setdefault(
            "clubCopyLastHint",
            "可一键带入上年已通过年审的说明和附件，核对后再提交。",
        )
        thicken["clubCopyLast"] = True
        _add_feature(spec, "社团年审材料复制上年")
    if domain == "DOM-PROCURE":
        ticket["allowProcureReturn"] = True
        labels.setdefault("procureReturnFailLabel", "验收不合格")
        labels.setdefault("returnNoteLabel", "退货说明")
        labels.setdefault(
            "procureReturnHint",
            "办结时请确认验收是否合格；不合格须填写退货说明。",
        )
        thicken["procureReturn"] = True
        _add_feature(spec, "采购验收不合格退货登记")
    if domain == "DOM-MORAL":
        ticket["allowMoralObjection"] = True
        labels.setdefault("moralObjectionLabel", "异议说明")
        labels.setdefault(
            "moralObjectionHint",
            "公示期内可对已通过的综测结果提出异议。",
        )
        thicken["moralObjection"] = True
        _add_feature(spec, "综测公示期异议入口")
    if domain == "DOM-PROJ":
        ticket["allowProjFundUse"] = True
        labels.setdefault("fundUseYuanLabel", "本次使用经费（元）")
        labels.setdefault("fundUseNoteLabel", "经费使用说明")
        labels.setdefault(
            "fundUseHint",
            "请填写本次使用金额和说明后再提交。",
        )
        thicken["projFundUse"] = True
        _add_feature(spec, "大创经费使用登记")
    if domain == "DOM-EVAL":
        ticket["allowEvalDimWeight"] = True
        dims = ticket.get("ratingDims")
        if not isinstance(dims, list) or not any(
            isinstance(d, dict) and d.get("key") and d.get("label") for d in dims
        ):
            ticket["ratingDims"] = [
                {"key": "teaching", "label": "教学内容", "weight": 40},
                {"key": "attitude", "label": "教学态度", "weight": 30},
                {"key": "content", "label": "课程收获", "weight": 30},
            ]
        else:
            for d in dims:
                if isinstance(d, dict) and d.get("key") and d.get("weight") is None:
                    d["weight"] = 1
        labels.setdefault("evalDimWeightHint", "请按各维度打分；综合分按课程档案中的权重计算。")
        labels.setdefault("teachingWeightLabel", "教学内容权重")
        labels.setdefault("attitudeWeightLabel", "教学态度权重")
        labels.setdefault("contentWeightLabel", "课程收获权重")
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list):
                for key, lab in (
                    ("teachingWeight", "教学内容权重"),
                    ("attitudeWeight", "教学态度权重"),
                    ("contentWeight", "课程收获权重"),
                ):
                    if not any(isinstance(f, dict) and f.get("key") == key for f in fields):
                        fields.append({"key": key, "label": lab, "type": "number"})
        thicken["evalDimWeight"] = True
        _add_feature(spec, "评教课程维度权重")
    if domain == "DOM-VISITOR":
        ticket["allowVisitSlotRemain"] = True
        labels.setdefault("visitOnLabel", "来访日期")
        labels.setdefault(
            "visitSlotRemainHint",
            "请选择来访日期；当天名额已满时无法再约。",
        )
        labels.setdefault("visitSlotCapLabel", "每日预约上限")
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list) and not any(
                isinstance(f, dict) and f.get("key") == "visitSlotCap" for f in fields
            ):
                fields.append({"key": "visitSlotCap", "label": "每日预约上限", "type": "number"})
        thicken["visitSlotRemain"] = True
        _add_feature(spec, "访客预约时段余量")

    # —— 第十一批：查重外链/连续未归/党员阶段/督导听课/课表影响/合同金额（仍只挂本域）——
    if domain == "DOM-PROJ":
        ticket["allowPlagiarismUrl"] = True
        labels.setdefault("plagiarismUrlLabel", "查重报告链接")
        labels.setdefault(
            "plagiarismUrlHint",
            "请填写查重报告的网页地址，核对后再提交。",
        )
        thicken["plagiarismUrl"] = True
        _add_feature(spec, "大创结题查重说明（外链）")
    if domain == "DOM-CHECKIN":
        ticket["allowAbsentStreak"] = True
        labels.setdefault("absentWarnNLabel", "连续未归预警次数")
        labels.setdefault(
            "absentStreakHint",
            "请选择异常类型；连续未归达到楼栋设定次数后，暂不能再提交未归。",
        )
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list) and not any(
                isinstance(f, dict) and f.get("key") == "absentWarnN" for f in fields
            ):
                fields.append({"key": "absentWarnN", "label": "连续未归预警次数", "type": "number"})
        thicken["absentStreak"] = True
        _add_feature(spec, "查寝缺勤连续 N 次预警名单")
    if domain == "DOM-PARTY":
        ticket["allowPartyStage"] = True
        ticket["partyStageOptions"] = list(
            ticket.get("partyStageOptions")
            or ["入党积极分子", "发展对象", "预备党员", "正式党员"]
        )
        labels.setdefault("partyStageLabel", "当前发展阶段")
        labels.setdefault("stageOnLabel", "进入该阶段日期")
        labels.setdefault(
            "partyStageHint",
            "请选择当前发展阶段并填写进入该阶段的日期。",
        )
        thicken["partyStage"] = True
        _add_feature(spec, "党员发展阶段时间轴展示")
    if domain == "DOM-EVAL":
        ticket["allowEvalObserve"] = True
        labels.setdefault("observeOnLabel", "听课日期")
        labels.setdefault("observeNoteLabel", "听课记录")
        labels.setdefault(
            "evalObserveHint",
            "请填写听课日期和记录后再提交。",
        )
        thicken["evalObserve"] = True
        _add_feature(spec, "评教督导听课记录")
    if domain == "DOM-ACAD":
        ticket["allowScheduleImpact"] = True
        labels.setdefault("scheduleImpactNoteLabel", "对课表的影响")
        labels.setdefault(
            "scheduleImpactHint",
            "请说明本次异动对课表的影响，工作人员不会自动改课表。",
        )
        thicken["scheduleImpact"] = True
        _add_feature(spec, "学籍异动影响课表提示（只读说明）")
    if domain == "DOM-CONTRACT":
        ticket["allowContractAmount"] = True
        labels.setdefault("contractAmountLabel", "合同金额（元）")
        labels.setdefault("contractAmountCnLabel", "金额大写")
        labels.setdefault(
            "contractAmountHint",
            "请填写合同金额，页面会同时显示大写。",
        )
        thicken["contractAmount"] = True
        _add_feature(spec, "合同金额大写展示")

    # —— 第十二批：报销多行/行程多段/评教隐藏/签署可见/变更日志/查伪码（仍只挂本域）——
    if domain == "DOM-EXPENSE":
        ticket["allowExpenseLines"] = True
        ticket["expenseLineCategoryOptions"] = list(
            ticket.get("expenseLineCategoryOptions")
            or ["交通", "住宿", "餐饮", "办公", "其他"]
        )
        labels.setdefault("expenseLinesLabel", "报销明细")
        labels.setdefault("expenseLineCategoryLabel", "费用类别")
        labels.setdefault("expenseLineAmountLabel", "金额（元）")
        labels.setdefault("expenseLineNoteLabel", "说明")
        labels.setdefault(
            "expenseLinesHint",
            "请按行填写差旅等费用明细后再提交。",
        )
        thicken["expenseLines"] = True
        _add_feature(spec, "报销单明细多行（差旅交通住宿分行）")
    if domain == "DOM-TRIP":
        ticket["allowTripLegs"] = True
        labels.setdefault("tripLegsLabel", "出差行程")
        labels.setdefault("tripLegFromLabel", "出发地")
        labels.setdefault("tripLegViaLabel", "途经")
        labels.setdefault("tripLegToLabel", "到达地")
        labels.setdefault("tripLegOnLabel", "行程日期")
        labels.setdefault(
            "tripLegsHint",
            "请按段填写出发、途经、返回行程后再提交。",
        )
        thicken["tripLegs"] = True
        _add_feature(spec, "出差行程多段（出发/途经/返回）")
    if domain == "DOM-EVAL":
        ticket["allowHideEvalResult"] = True
        labels.setdefault("hideEvalResultLabel", "结果对学生不可见")
        labels.setdefault(
            "hideEvalResultHint",
            "开启后，学生端不展示本课评教综合分与维度分；管理端仍可查看。",
        )
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list) and not any(
                isinstance(f, dict) and f.get("key") == "hideEvalResult" for f in fields
            ):
                fields.append({"key": "hideEvalResult", "label": "结果对学生不可见", "type": "boolean"})
        thicken["hideEvalResult"] = True
        _add_feature(spec, "评教结果对学生不可见开关")
    if domain == "DOM-CONTRACT":
        ticket["allowSignRemarkVisible"] = True
        labels.setdefault("signRemarkVisibleLabel", "审批意见对签署方可见")
        labels.setdefault("signApproveRemarkLabel", "审批意见")
        labels.setdefault(
            "signRemarkVisibleHint",
            "开启后，申请人可在进度中查看审批意见；关闭则只显示办理结果。",
        )
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list) and not any(
                isinstance(f, dict) and f.get("key") == "signRemarkVisible" for f in fields
            ):
                fields.append({"key": "signRemarkVisible", "label": "审批意见对签署方可见", "type": "boolean"})
        thicken["signRemarkVisible"] = True
        _add_feature(spec, "合同审批意见对签署方可见开关")
    if domain == "DOM-PROJ":
        ticket["allowProjChangeLog"] = True
        labels.setdefault("changeLogNoteLabel", "变更摘要")
        labels.setdefault(
            "projChangeLogHint",
            "请填写本次项目变更摘要，便于对照历史记录。",
        )
        thicken["projChangeLog"] = True
        _add_feature(spec, "大创项目变更日志")
    if domain == "DOM-CERT":
        ticket["allowCertVerify"] = True
        labels.setdefault("certVerifyCodeLabel", "真伪查询码")
        labels.setdefault(
            "certVerifyHint",
            "审过后将签发查询码，可在真伪查询页核对。",
        )
        labels.setdefault("certVerifyPageTitle", "证明真伪查询")
        labels.setdefault("certVerifyPageLead", "请输入查询码，核对证明是否由本系统开具。")
        labels.setdefault("certVerifyOkText", "查得该证明，信息属实。")
        labels.setdefault("certVerifyMissText", "未查到对应证明，请核对查询码。")
        thicken["certVerify"] = True
        _add_feature(spec, "证明真伪查询码（公开页）")

    # —— 第十三批：现场补录/代登记/名册/车位互斥/催评/续签（仍只挂本域）——
    if domain == "DOM-VISITOR":
        ticket["allowVisitWalkIn"] = True
        labels.setdefault("visitWalkInLabel", "现场补录")
        labels.setdefault("visitWalkInForLabel", "被访人账号")
        labels.setdefault(
            "visitWalkInHint",
            "前台可为被访人补录来访；补录后在对方的申请列表中可见。",
        )
        thicken["visitWalkIn"] = True
        _add_feature(spec, "访客到访登记（现场补录）")
    if domain == "DOM-CHECKIN":
        ticket["allowCheckinProxy"] = True
        labels.setdefault("checkinProxyLabel", "楼栋长代登记")
        labels.setdefault("checkinProxyForLabel", "学生账号")
        labels.setdefault("checkinProxyByLabel", "代登人")
        labels.setdefault(
            "checkinProxyHint",
            "楼栋长可替学生登记归寝；记录会写在该学生名下。",
        )
        thicken["checkinProxy"] = True
        _add_feature(spec, "查寝楼栋长代登记")
    if domain == "DOM-CLUB":
        ticket["allowClubRoster"] = True
        labels.setdefault("clubRosterLabel", "成员名册")
        labels.setdefault("clubMemberNameLabel", "姓名")
        labels.setdefault("clubMemberNoLabel", "学号")
        labels.setdefault(
            "clubRosterHint",
            "请按行填写本社团成员姓名，学号可空；也可导入表格。",
        )
        thicken["clubRoster"] = True
        _add_feature(spec, "社团成员名册导入")
    if domain == "DOM-CARPASS":
        ticket["allowCarpassParkingMutex"] = True
        labels.setdefault("parkingOnLabel", "占用车位日期")
        labels.setdefault("parkingMutexLabel", "同车位同日互斥")
        labels.setdefault(
            "carpassParkingMutexHint",
            "开启后，同一车位同一日只接受一张通行申请。",
        )
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list) and not any(
                isinstance(f, dict) and f.get("key") == "parkingMutex" for f in fields
            ):
                fields.append({"key": "parkingMutex", "label": "同车位同日互斥", "type": "boolean"})
        thicken["carpassParkingMutex"] = True
        _add_feature(spec, "车辆通行证与车位预约互斥提示")
    if domain == "DOM-EVAL":
        ticket["allowEvalUrge"] = True
        labels.setdefault("evalUrgeLabel", "催评")
        labels.setdefault(
            "evalUrgeHint",
            "尚未评教的同学可在此提交；管理端可发送催评提醒。",
        )
        thicken["evalUrge"] = True
        _add_feature(spec, "评教未评名单导出催评")
    if domain == "DOM-CONTRACT":
        ticket["allowContractRenew"] = True
        labels.setdefault("renewOnLabel", "续签日期")
        labels.setdefault("renewNoteLabel", "续签说明")
        labels.setdefault(
            "contractRenewHint",
            "请填写拟续签日期和说明后再提交。",
        )
        thicken["contractRenew"] = True
        _add_feature(spec, "合同续签（拟续签日期与说明）")

    # —— 第十四批：到期提醒加深/领取核销/考试门槛/抽查任务/先评后查分（人均耗时已在核心）——
    if domain == "DOM-CONTRACT":
        ticket["allowContractExpireRemind"] = True
        ticket["notifyArchiveExpireDays"] = int(ticket.get("notifyArchiveExpireDays") or 0) or 7
        labels.setdefault(
            "contractExpireRemindHint",
            "合同临近到期时，将向管理员和相关申请人发送续签提醒。",
        )
        labels.setdefault("contractExpireRemindTitle", "合同续签提醒")
        thicken["contractExpireRemind"] = True
        _add_feature(spec, "合同续签提醒（到期前）")
    if domain == "DOM-CERT":
        ticket["allowCertPickupRedeem"] = True
        labels.setdefault("pickupRedeemCodeLabel", "领取核销码")
        labels.setdefault("pickupRedeemedLabel", "已核销")
        labels.setdefault(
            "pickupRedeemHint",
            "审过后将签发领取核销码；到现场领取时由工作人员核销。",
        )
        thicken["certPickupRedeem"] = True
        _add_feature(spec, "证明领取核销码")
    if domain == "DOM-LABSAFE":
        ticket["allowExamPassMin"] = True
        labels.setdefault("examPassMinLabel", "准入考试及格分")
        labels.setdefault(
            "examPassMinHint",
            "未达到档案中设定的及格分前，不能提交准入申请。",
        )
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list) and not any(
                isinstance(f, dict) and f.get("key") == "examPassMin" for f in fields
            ):
                fields.append({"key": "examPassMin", "label": "准入考试及格分", "type": "number"})
        thicken["examPassMin"] = True
        _add_feature(spec, "实验室准入考试成绩门槛")
    if domain == "DOM-CHECKIN":
        ticket["allowCheckinSpot"] = True
        labels.setdefault("checkinSpotLabel", "抽查任务")
        labels.setdefault("checkinSpotSampleLabel", "抽查人数")
        labels.setdefault("checkinSpotOnLabel", "抽查日期")
        labels.setdefault(
            "checkinSpotHint",
            "可按日期从在册学生中抽出若干人形成待查名单；被抽中的同学仍按日常查寝登记。",
        )
        thicken["checkinSpot"] = True
        _add_feature(spec, "查寝抽查任务生成")
    if domain == "DOM-EVAL":
        ticket["allowEvalBeforeGrade"] = True
        labels.setdefault(
            "evalBeforeGradeHint",
            "请先完成本学期评教，再查看成绩。",
        )
        thicken["evalBeforeGrade"] = True
        _add_feature(spec, "评教强制顺序（先评后查分）")

    # —— 第十五批：附件留旧/领取二维码/真伪页加深/通行证打印/查寝日报/评教院系导出 ——
    if domain == "DOM-CERT":
        ticket["allowCertPickupQr"] = True
        labels.setdefault("pickupQrLabel", "领取二维码")
        labels.setdefault(
            "pickupQrHint",
            "审过后可出示领取核销码的二维码，现场扫码核对。",
        )
        thicken["certPickupQr"] = True
        _add_feature(spec, "证明开具领取二维码")
        ticket["allowCertVerifyPage"] = True
        labels.setdefault("certVerifyStatusLabel", "办理状态")
        labels.setdefault("certVerifyAtLabel", "办结时间")
        labels.setdefault("certVerifyIssueNoLabel", "开具流水号")
        labels.setdefault(
            "certVerifyPageDeepenHint",
            "查得后可核对照类型、办理状态和开具流水号。",
        )
        thicken["certVerifyPage"] = True
        _add_feature(spec, "证明真伪公开查询页已齐钉口径")
    if domain == "DOM-VISITOR":
        ticket["allowVisitorPassPrint"] = True
        labels.setdefault("visitorPassPrintLabel", "打印通行证")
        labels.setdefault(
            "visitorPassPrintHint",
            "审过并签发通行码后，可打印本页出示。",
        )
        thicken["visitorPassPrint"] = True
        _add_feature(spec, "访客通行证打印")
    if domain == "DOM-CHECKIN":
        ticket["allowCheckinDailyReport"] = True
        labels.setdefault("checkinDailyLabel", "楼长日报")
        labels.setdefault("checkinDailyOnLabel", "汇总日期")
        labels.setdefault(
            "checkinDailyHint",
            "按登记日期汇总已提交人数，可导出当日名单。",
        )
        thicken["checkinDailyReport"] = True
        _add_feature(spec, "查寝楼长日报汇总")
    if domain == "DOM-EVAL":
        ticket["allowEvalCollegeExport"] = True
        labels.setdefault("evalCollegeExportLabel", "院系汇总导出")
        labels.setdefault("evalCollegeLabel", "开课学院")
        labels.setdefault(
            "evalCollegeExportHint",
            "按开课学院汇总已评份数，可导出表格。",
        )
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            fields = archive.setdefault("fields", [])
            if isinstance(fields, list) and not any(
                isinstance(f, dict) and f.get("key") == "college" for f in fields
            ):
                fields.append({"key": "college", "label": "开课学院", "type": "string"})
        thicken["evalCollegeExport"] = True
        _add_feature(spec, "评教结果院系汇总导出")

    # —— 第十六批：用印台账导出 / 综测证据清单 / 党员阶段清单模板 / 思想汇报节点 ——
    if domain == "DOM-SEAL":
        ticket["allowSealLedgerExport"] = True
        labels.setdefault("sealLedgerExportLabel", "导出用印台账")
        labels.setdefault(
            "sealLedgerExportHint",
            "可按当前筛选导出用印份数、装订说明、份号与监印确认，便于台账留存。",
        )
        thicken["sealLedgerExport"] = True
        _add_feature(spec, "用印台账导出")
    if domain == "DOM-MORAL":
        _force_approve_material_check(
            spec,
            schema,
            title="综测加减分证据材料",
            lead="维护加减分证据项；申请人须按清单上传证明材料，缺件不可提交。",
        )
        ticket["allowMoralMaterialCheck"] = True
        labels.setdefault(
            "moralMaterialHint",
            "请按清单上传加分证明、减分说明等证据材料；缺件不可提交。",
        )
        thicken["moralMaterialCheck"] = True
        _add_feature(spec, "综测加减分证据材料清单")
    if domain == "DOM-PARTY":
        _force_approve_material_check(
            spec,
            schema,
            title="党员发展材料清单",
            lead="按发展阶段维护材料项与思想汇报节点；申请人须按清单上传，缺件不可提交。",
        )
        ticket["allowPartyMaterialTemplate"] = True
        labels.setdefault(
            "partyMaterialHint",
            "请按当前发展阶段上传对应材料；清单项由管理员按阶段模板维护。",
        )
        thicken["partyMaterialTemplate"] = True
        _add_feature(spec, "党员发展阶段材料清单模板")
        ticket["allowPartyThoughtAttach"] = True
        labels.setdefault(
            "partyThoughtHint",
            "须上传思想汇报与心得体会（清单必传项），缺件不可提交。",
        )
        thicken["partyThoughtAttach"] = True
        _add_feature(spec, "思想汇报/心得附件节点")

    # —— 第十七批：四套公文套打 / 报销影像张数提示 / 用车资质清单（PROCURE 入库不重写）——
    if domain == "DOM-CERT":
        ticket["printTicket"] = True
        ticket["allowCertFormPrint"] = True
        labels.setdefault("printTicketLabel", "开具证明")
        labels.setdefault(
            "certFormPrintHint",
            "审过后可打印在读/成绩类证明页（浏览器套打，非电子签章）。",
        )
        thicken["certFormPrint"] = True
        _add_feature(spec, "证明开具套打页")
    if domain == "DOM-SEAL":
        ticket["printTicket"] = True
        ticket["allowSealFormPrint"] = True
        labels.setdefault("printTicketLabel", "打印用印审批单")
        labels.setdefault(
            "sealFormPrintHint",
            "可打印用印审批登记表，含份数、份号与监印栏。",
        )
        thicken["sealFormPrint"] = True
        _add_feature(spec, "用印审批单套打")
    if domain == "DOM-PROJ":
        ticket["printTicket"] = True
        ticket["allowProjMidFormPrint"] = True
        labels.setdefault("printTicketLabel", "中期检查表")
        labels.setdefault(
            "projMidFormPrintHint",
            "可打印大创中期检查表，供导师与学院签署。",
        )
        thicken["projMidFormPrint"] = True
        _add_feature(spec, "大创中期检查表套打")
    if domain == "DOM-ETHIC":
        ticket["printTicket"] = True
        ticket["allowEthicOpinionPrint"] = True
        labels.setdefault("printTicketLabel", "伦理审查意见书")
        labels.setdefault(
            "ethicOpinionPrintHint",
            "可打印伦理审查意见书（浏览器套打，非 CA）。",
        )
        thicken["ethicOpinionPrint"] = True
        _add_feature(spec, "伦理审查意见书模板下载")
    if domain == "DOM-EXPENSE":
        ticket["allowExpenseAttachCount"] = True
        ticket["requireAttach"] = True
        labels.setdefault(
            "expenseAttachCountHint",
            "请确保上传的票据影像张数与填写的发票张数一致；缺影像不可提交。",
        )
        thicken["expenseAttachCount"] = True
        _add_feature(spec, "报销票据影像必传张数")
    if domain == "DOM-FLEET":
        _force_approve_material_check(
            spec,
            schema,
            title="驾驶员资质材料",
            lead="维护驾驶证/从业资格等资质项；申请人须按清单上传，缺件不可提交。",
        )
        ticket["allowFleetDriverCert"] = True
        labels.setdefault(
            "fleetDriverCertHint",
            "请按清单上传驾驶证与从业资格证明；与加油票/过路费附件相互独立。",
        )
        thicken["fleetDriverCert"] = True
        _add_feature(spec, "用车驾驶员资质附件")

    ents["ticket"] = ticket
    schema["approveThicken"] = thicken
    schema["labels"] = labels
    spec["schema"] = schema
    return spec


def _force_approve_material_check(
    spec: dict[str, Any],
    schema: dict[str, Any],
    *,
    title: str,
    lead: str,
) -> None:
    """审批域默认挂材料清单：复用 material_check，不新开附件槽。"""
    from app.bake.features.ticket_flow_opts import (
        attach_material_check_menus,
        merge_material_check_capabilities,
    )
    from app.bake.gate_contracts import merge_material_check_gate

    caps = merge_material_check_capabilities(
        list(spec.get("capabilities") or []),
        force=True,
        domain=str(spec.get("domain") or ""),
    )
    spec["capabilities"] = caps
    schema["capabilities"] = caps
    attach_material_check_menus(schema)
    labels = schema.setdefault("labels", {})
    labels["materialChecklistTitle"] = title
    labels["materialChecklistLead"] = lead
    gate = spec.get("gate") if isinstance(spec.get("gate"), dict) else {}
    spec["gate"] = merge_material_check_gate(gate, caps)


_MORAL_MATERIAL_SEED_SQL = """
INSERT IGNORE INTO material_checklist (id, title, required, sort_order, status) VALUES
(101, '加分证明材料', 1, 10, 'available'),
(102, '减分说明材料', 1, 11, 'available'),
(103, '佐证附件（证书/通报）', 1, 12, 'available');
"""

_PARTY_MATERIAL_SEED_SQL = """
INSERT IGNORE INTO material_checklist (id, title, required, sort_order, status) VALUES
(201, '入党积极分子阶段材料', 1, 20, 'available'),
(202, '发展对象阶段材料', 1, 21, 'available'),
(203, '预备党员阶段材料', 1, 22, 'available'),
(204, '正式党员阶段材料', 0, 23, 'available'),
(205, '思想汇报', 1, 24, 'available'),
(206, '心得体会', 1, 25, 'available');
INSERT IGNORE INTO material_template (id, title, remark) VALUES
(201, '入党积极分子材料清单', '按积极分子阶段准备考察表与证明材料'),
(202, '发展对象材料清单', '按发展对象阶段准备政审与培训材料'),
(203, '预备党员材料清单', '按预备期准备转正申请与考察材料'),
(204, '思想汇报/心得节点', '思想汇报与心得体会为必传清单项');
"""


_FLEET_DRIVER_CERT_SEED_SQL = """
INSERT IGNORE INTO material_checklist (id, title, required, sort_order, status) VALUES
(301, '驾驶证', 1, 30, 'available'),
(302, '从业资格证', 1, 31, 'available');
"""


def ensure_approve_material_seed_sql(
    sql: str,
    *,
    allow_moral: bool = False,
    allow_party_template: bool = False,
    allow_party_thought: bool = False,
    allow_fleet_driver: bool = False,
) -> str:
    """MORAL/PARTY/FLEET 材料清单种子；开对应 flag 才追加，不改建表。"""
    if not (
        allow_moral
        or allow_party_template
        or allow_party_thought
        or allow_fleet_driver
    ):
        return sql
    out = sql
    if allow_moral and "加分证明材料" not in out:
        out = out.rstrip() + "\n" + _MORAL_MATERIAL_SEED_SQL
    # 哨兵用阶段材料名：域档案种子里可能已有「思想汇报」字样
    if (allow_party_template or allow_party_thought) and "入党积极分子阶段材料" not in out:
        out = out.rstrip() + "\n" + _PARTY_MATERIAL_SEED_SQL
    if allow_fleet_driver and "从业资格证" not in out:
        out = out.rstrip() + "\n" + _FLEET_DRIVER_CERT_SEED_SQL
    return out
