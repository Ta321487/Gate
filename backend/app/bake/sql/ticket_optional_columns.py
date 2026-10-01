"""Moved from fragments.py — SQL ensure helpers."""

from __future__ import annotations

import re

from app.bake.sql.ddl_edit import (
    CREATE_TABLE_RE as _CREATE_TABLE_RE,
    inject_missing_columns as _inject_missing_columns,
    prune_columns as _prune_columns,
    strip_trailing_comma_before_close as _strip_trailing_comma,
)


_TICKET_PROGRESS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_progress_ticket (ticket_id, id)
);
"""

TICKET_OPTIONAL_COLUMNS: list[tuple[str, str]] = [
    ("attach_url", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("rating", "INT NULL"),
    ("rating_remark", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("rated_at", "DATETIME NULL"),
    ("rating_dims_json", "VARCHAR(1024) DEFAULT ''"),
    ("rating_anonymous", "TINYINT NOT NULL DEFAULT 0"),
    ("priority", "VARCHAR(16) DEFAULT '普通'"),
    ("contact_phone", "VARCHAR(20) DEFAULT ''"),
    ("fine_status", "VARCHAR(16) DEFAULT 'none'"),
    ("pickup_at", "DATETIME NULL"),
    ("pickup_place", "VARCHAR(128) DEFAULT ''"),
    ("actual_qty", "INT NULL"),
    ("contact_channel", "VARCHAR(32) DEFAULT ''"),
    ("next_follow_at", "DATETIME NULL"),
    ("checked_in_at", "DATETIME NULL"),
    ("pass_code", "VARCHAR(32) DEFAULT ''"),
    ("renew_count", "INT NOT NULL DEFAULT 0"),
    ("hold_expire_at", "DATETIME NULL"),
    ("qty", "INT NOT NULL DEFAULT 1"),
    ("period_start", "DATETIME NULL"),
    ("period_end", "DATETIME NULL"),
    ("leave_days", "INT NULL"),
    ("week_no", "INT NULL"),
    ("interview_place", "VARCHAR(128) DEFAULT ''"),
    ("proxy_name", "VARCHAR(64) DEFAULT ''"),
    ("proxy_phone", "VARCHAR(20) DEFAULT ''"),
    ("exception_reason", "VARCHAR(128) DEFAULT ''"),
    ("damage_claim_note", "VARCHAR(255) DEFAULT ''"),
    ("deposit_yuan", "DECIMAL(10,2) NULL"),
    ("notice_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("emergency_contact", "VARCHAR(64) DEFAULT ''"),
    ("emergency_phone", "VARCHAR(20) DEFAULT ''"),
    ("due_soon_notified_at", "DATETIME NULL"),
    ("ever_overdue", "TINYINT NOT NULL DEFAULT 0"),
    ("project_no", "VARCHAR(64) DEFAULT ''"),
    ("procure_ref_no", "VARCHAR(64) DEFAULT ''"),
    ("dual_reviewer_a", "VARCHAR(64) DEFAULT ''"),
    ("dual_reviewer_b", "VARCHAR(64) DEFAULT ''"),
    ("ship_fee_yuan", "DECIMAL(10,2) NULL"),
    ("utility_note", "VARCHAR(255) DEFAULT ''"),
    ("insurance_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("meeting_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("owner_meeting_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("price_note_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("sponsor_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("plan_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("prereq_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("late_minutes", "INT NULL"),
    ("peer_username", "VARCHAR(64) DEFAULT ''"),
    ("peer_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("interview_result", "VARCHAR(16) DEFAULT ''"),
    ("written_score", "DECIMAL(10,2) NULL"),
    ("bg_check_note", "VARCHAR(255) DEFAULT ''"),
    ("deal_amount_yuan", "DECIMAL(12,2) NULL"),
    ("next_action", "VARCHAR(255) DEFAULT ''"),
    ("next_action_done", "TINYINT NOT NULL DEFAULT 0"),
    ("return_date", "VARCHAR(32) DEFAULT ''"),
    ("defense_result", "VARCHAR(32) DEFAULT ''"),
    ("bank_account", "VARCHAR(64) DEFAULT ''"),
    ("disburse_batch", "VARCHAR(64) DEFAULT ''"),
    ("close_attach_url", "VARCHAR(255) DEFAULT ''"),
    ("assign_dept", "VARCHAR(64) DEFAULT ''"),
    ("confidential", "TINYINT NOT NULL DEFAULT 0"),
    ("appraisal_comment", "VARCHAR(512) DEFAULT ''"),
    ("appraisal_grade", "VARCHAR(16) DEFAULT ''"),
    ("company_eval", "VARCHAR(512) DEFAULT ''"),
    ("excellent_mark", "TINYINT NOT NULL DEFAULT 0"),
    ("revise_count", "INT NOT NULL DEFAULT 0"),
    ("feedback_interest", "VARCHAR(128) DEFAULT ''"),
    ("feedback_concern", "VARCHAR(255) DEFAULT ''"),
    ("feedback_next", "VARCHAR(255) DEFAULT ''"),
    ("record_url", "VARCHAR(255) DEFAULT ''"),
    ("follow_soon_notified_at", "DATETIME NULL"),
    ("urge_at", "DATETIME NULL"),
    ("urge_count", "INT NOT NULL DEFAULT 0"),
    ("urge_cancelled", "TINYINT NOT NULL DEFAULT 0"),
    ("fault_reason", "VARCHAR(64) DEFAULT ''"),
    ("close_summary", "VARCHAR(512) DEFAULT ''"),
    ("preferred_slot", "VARCHAR(64) DEFAULT ''"),
    ("response_due_at", "DATETIME NULL"),
    ("night_urgent", "TINYINT NOT NULL DEFAULT 0"),
    ("address_type", "VARCHAR(16) DEFAULT ''"),
    ("helper_username", "VARCHAR(64) DEFAULT ''"),
    ("quote_yuan", "DECIMAL(10,2) NULL"),
    ("quote_confirmed", "TINYINT NOT NULL DEFAULT 0"),
    ("material_fee_yuan", "DECIMAL(10,2) NULL"),
    ("material_paid", "TINYINT NOT NULL DEFAULT 0"),
    ("hold_reason", "VARCHAR(255) DEFAULT ''"),
    ("asset_code", "VARCHAR(64) DEFAULT ''"),
    ("remote_url", "VARCHAR(255) DEFAULT ''"),
    ("skill_tag", "VARCHAR(64) DEFAULT ''"),
    ("route_note", "VARCHAR(255) DEFAULT ''"),
    ("parent_ticket_id", "BIGINT NULL"),
    ("subscribe_progress", "TINYINT NOT NULL DEFAULT 0"),
    ("audio_url", "VARCHAR(255) DEFAULT ''"),
    ("rating_tags", "VARCHAR(255) DEFAULT ''"),
    ("follow_rated", "TINYINT NOT NULL DEFAULT 0"),
    ("parts_note", "VARCHAR(255) DEFAULT ''"),
    ("serial_no", "VARCHAR(64) DEFAULT ''"),
    ("visit_due_at", "DATETIME NULL"),
    ("knowledge_deposit", "TINYINT NOT NULL DEFAULT 0"),
    ("rank_scope", "VARCHAR(16) DEFAULT ''"),
    ("objection_due_at", "DATETIME NULL"),
    ("objection_note", "VARCHAR(255) DEFAULT ''"),
    ("objection_at", "DATETIME NULL"),
]

_TICKET_OPTIONAL_NAMES = {n.lower() for n, _ in TICKET_OPTIONAL_COLUMNS}

_TICKET_COL_DDL = {n.lower(): ddl for n, ddl in TICKET_OPTIONAL_COLUMNS}

TICKET_DOMAIN_COLUMNS: dict[str, list[str]] = {
    "DOM-LIBRARY": ["fine_status", "due_soon_notified_at", "ever_overdue", "notice_ack"],
    "DOM-EQUIP": ["fine_status", "deposit_yuan", "notice_ack", "due_soon_notified_at", "ever_overdue", "insurance_ack", "asset_code"],
    "DOM-ASSET": ["pickup_at", "pickup_place", "actual_qty", "project_no", "procure_ref_no", "dual_reviewer_a", "dual_reviewer_b"],
    "DOM-CRM": ["contact_channel", "next_follow_at", "deal_amount_yuan", "next_action", "next_action_done", "follow_soon_notified_at"],
    "DOM-ATTEND": ["contact_channel", "next_follow_at", "leave_days", "return_date", "proxy_name"],
    "DOM-FUND": ["contact_channel", "next_follow_at", "defense_result", "bank_account", "disburse_batch"],
    "DOM-LABSAFE": ["contact_channel", "next_follow_at"],
    "DOM-RECRUIT": ["contact_channel", "next_follow_at", "interview_place", "interview_result", "written_score", "bg_check_note"],
    "DOM-DATING": ["contact_channel", "next_follow_at"],
    "DOM-GRADE": ["contact_channel", "next_follow_at", "notice_ack", "rank_scope"],
    "DOM-INTERN": [
        "contact_channel", "next_follow_at", "week_no",
        "appraisal_comment", "appraisal_grade", "company_eval", "excellent_mark", "revise_count",
    ],
    "DOM-SEAL": ["contact_channel", "next_follow_at"],
    "DOM-FLEET": ["contact_channel", "next_follow_at"],
    "DOM-CERT": ["contact_channel", "next_follow_at"],
    "DOM-PROMO": ["contact_channel", "next_follow_at"],
    "DOM-FITOUT": ["contact_channel", "next_follow_at"],
    "DOM-ACAD": ["contact_channel", "next_follow_at"],
    "DOM-TRIP": ["contact_channel", "next_follow_at"],
    "DOM-EXPENSE": ["contact_channel", "next_follow_at"],
    "DOM-CREDIT": ["contact_channel", "next_follow_at"],
    "DOM-LABOR": ["contact_channel", "next_follow_at"],
    "DOM-EVAL": [
        "contact_channel", "next_follow_at",
        "rating", "rating_remark", "rated_at", "rating_dims_json", "rating_anonymous",
    ],
    "DOM-MORAL": ["contact_channel", "next_follow_at"],
    "DOM-AWARD": ["contact_channel", "next_follow_at"],
    "DOM-BED": [
        "contact_channel",
        "next_follow_at",
        "notice_ack",
        "deposit_yuan",
        "utility_note",
        "peer_username",
        "peer_ack",
    ],
    "DOM-CHECKIN": ["contact_channel", "next_follow_at"],
    "DOM-MUTUAL-TUTOR": ["contact_channel", "next_follow_at"],
    "DOM-MUTUAL-TOPIC": ["contact_channel", "next_follow_at"],
    "DOM-MUTUAL-TEAM": ["contact_channel", "next_follow_at"],
    "DOM-VISITOR": ["contact_channel", "next_follow_at"],
    "DOM-CARPASS": ["contact_channel", "next_follow_at"],
    "DOM-LISTING": [
        "contact_channel", "next_follow_at", "follow_soon_notified_at",
        "feedback_interest", "feedback_concern", "feedback_next", "record_url",
    ],
    "DOM-CARPOOL": ["contact_channel", "next_follow_at"],
    "DOM-TOUR": [
        "contact_channel",
        "next_follow_at",
        "notice_ack",
        "emergency_contact",
        "emergency_phone",
    ],
    "DOM-TIMEBANK": ["contact_channel", "next_follow_at"],
    "DOM-PROCURE": ["contact_channel", "next_follow_at"],
    "DOM-CLUB": ["contact_channel", "next_follow_at"],
    "DOM-PROJ": ["contact_channel", "next_follow_at"],
    "DOM-ETHIC": ["contact_channel", "next_follow_at"],
    "DOM-PARTY": ["contact_channel", "next_follow_at"],
    "DOM-CONTRACT": ["contact_channel", "next_follow_at"],
    "DOM-INSTRUMENT": ["contact_channel", "next_follow_at", "fine_status"],
    "DOM-EVENT": [
        "contact_channel", "next_follow_at", "close_attach_url", "assign_dept", "confidential",
    ],
    "DOM-DORM": [
        "priority", "contact_phone",
        "urge_at", "urge_count", "urge_cancelled",
        "fault_reason", "close_summary", "preferred_slot", "response_due_at",
        "night_urgent", "address_type", "helper_username",
        "hold_reason", "subscribe_progress", "audio_url", "rating_tags",
        "follow_rated", "route_note", "skill_tag", "visit_due_at",
        "close_attach_url",
    ],
    "DOM-PROPERTY": [
        "priority", "contact_phone",
        "urge_at", "urge_count", "urge_cancelled",
        "fault_reason", "close_summary", "preferred_slot", "response_due_at",
        "night_urgent", "address_type", "helper_username",
        "hold_reason", "subscribe_progress", "audio_url", "rating_tags",
        "follow_rated", "route_note", "skill_tag", "visit_due_at",
        "parts_note", "serial_no", "close_attach_url",
    ],
    "DOM-IT": [
        "priority", "contact_phone",
        "urge_at", "urge_count", "urge_cancelled",
        "fault_reason", "close_summary", "preferred_slot", "response_due_at",
        "night_urgent", "helper_username",
        "hold_reason", "subscribe_progress", "audio_url", "rating_tags",
        "follow_rated", "route_note", "skill_tag", "visit_due_at",
        "parts_note", "serial_no", "asset_code", "remote_url", "close_attach_url",
    ],
    "DOM-LOST": ["fine_status", "pickup_at", "pickup_place", "preferred_slot", "notice_ack"],
    "DOM-PARCEL": [
        "fine_status",
        "pickup_at",
        "pickup_place",
        "proxy_name",
        "proxy_phone",
        "exception_reason",
        "damage_claim_note",
        "notice_ack",
        "ship_fee_yuan",
    ],
    "DOM-ACTIVITY": ["notice_ack"],
    "DOM-COURSE": ["notice_ack"],
    "DOM-FORUM": [],
}

def _ticket_flag_column_names(flags: dict | None) -> list[str]:
    """由 schema.entities.ticket 能力开关推导列名。"""
    f = flags or {}
    names: list[str] = []
    if f.get("requireAttach"):
        names.append("attach_url")
    if f.get("allowRating"):
        names.extend(["rating", "rating_remark", "rated_at"])
        if f.get("ratingDims"):
            names.extend(["rating_dims_json", "rating_anonymous"])
    if f.get("allowQty"):
        names.append("qty")
    if f.get("pickDateRange"):
        names.extend(["period_start", "period_end"])
    if f.get("allowCheckin"):
        names.append("checked_in_at")
    if f.get("issuePassCode"):
        names.append("pass_code")
    if f.get("allowRenew"):
        names.append("renew_count")
    if f.get("allowBookHold"):
        names.append("hold_expire_at")
    if f.get("noShowAfterEnd") or f.get("fineLabel"):
        names.append("fine_status")
    if f.get("allowProxyPickup"):
        names.extend(["proxy_name", "proxy_phone"])
    if f.get("allowExceptionClose"):
        names.extend(["exception_reason", "damage_claim_note"])
    if f.get("allowDeposit"):
        names.append("deposit_yuan")
    if f.get("requireNoticeAck"):
        names.append("notice_ack")
    if f.get("preferredSlot"):
        names.append("preferred_slot")
    if f.get("allowEmergencyContact"):
        names.extend(["emergency_contact", "emergency_phone"])
    if f.get("requireInsuranceAck"):
        names.append("insurance_ack")
    if f.get("requireMeetingAck"):
        names.extend(["meeting_ack", "owner_meeting_ack"])
    if f.get("requirePriceNoteAck"):
        names.append("price_note_ack")
    if f.get("requireSponsorAck"):
        names.append("sponsor_ack")
    if f.get("requirePlanAck"):
        names.append("plan_ack")
    if f.get("requirePrereqAck"):
        names.append("prereq_ack")
    if f.get("allowLateMinutes"):
        names.append("late_minutes")
    if f.get("allowProjectNo"):
        names.append("project_no")
    if f.get("allowProcureRef"):
        names.append("procure_ref_no")
    if f.get("allowDualReview"):
        names.extend(["dual_reviewer_a", "dual_reviewer_b"])
    if f.get("allowShipFee"):
        names.append("ship_fee_yuan")
    if f.get("allowUtilityNote"):
        names.append("utility_note")
    if f.get("requirePeerConfirm"):
        names.extend(["peer_username", "peer_ack"])
    if int(f.get("dueSoonDays") or 0) > 0:
        names.append("due_soon_notified_at")
    if int(f.get("maxOverdueTimes") or 0) > 0:
        names.append("ever_overdue")
    if int(f.get("followRemindDays") or 0) > 0:
        names.append("follow_soon_notified_at")
    if f.get("allowDealAmount"):
        names.append("deal_amount_yuan")
    if f.get("allowNextAction"):
        names.extend(["next_action", "next_action_done"])
    if f.get("requireCloseAttach"):
        names.append("close_attach_url")
    if f.get("requireReturnDate"):
        names.append("return_date")
    if f.get("allowLeaveProxy"):
        names.append("proxy_name")
    if f.get("allowInterviewResult"):
        names.append("interview_result")
    if f.get("allowWrittenScore"):
        names.append("written_score")
    if f.get("allowBgCheckNote"):
        names.append("bg_check_note")
    if f.get("allowDefenseResult"):
        names.append("defense_result")
    if f.get("maskBankAccount"):
        names.append("bank_account")
    if f.get("allowDisburseBatch"):
        names.append("disburse_batch")
    if f.get("allowConfidential"):
        names.append("confidential")
    if f.get("allowAssignDept"):
        names.append("assign_dept")
    if f.get("requireAppraisal"):
        names.extend(["appraisal_comment", "appraisal_grade"])
    if f.get("allowCompanyEval"):
        names.append("company_eval")
    if f.get("allowExcellentMark"):
        names.append("excellent_mark")
    if int(f.get("maxReviseTimes") or 0) > 0:
        names.append("revise_count")
    if f.get("allowObjectionWindow") or int(f.get("objectionDays") or 0) > 0:
        names.extend(["objection_due_at", "objection_note", "objection_at"])
    if f.get("requireFeedbackSet"):
        names.extend(["feedback_interest", "feedback_concern", "feedback_next"])
    if f.get("allowRecordUrl"):
        names.append("record_url")
    if f.get("repairThicken") or f.get("allowUserUrge"):
        names.extend(
            [
                "urge_at",
                "urge_count",
                "urge_cancelled",
                "fault_reason",
                "close_summary",
                "preferred_slot",
                "response_due_at",
                "night_urgent",
                "address_type",
                "helper_username",
                "hold_reason",
                "subscribe_progress",
                "audio_url",
                "rating_tags",
                "follow_rated",
                "route_note",
                "skill_tag",
                "visit_due_at",
            ]
        )
    if f.get("allowPartsNote"):
        names.append("parts_note")
    if f.get("allowSerialNo"):
        names.append("serial_no")
    if f.get("allowQuote"):
        names.extend(["quote_yuan", "quote_confirmed", "material_fee_yuan", "material_paid"])
    if f.get("allowAssetCode"):
        names.append("asset_code")
    if f.get("allowRemoteUrl"):
        names.append("remote_url")
    if f.get("allowTicketMerge"):
        names.append("parent_ticket_id")
    if f.get("allowKnowledgeDeposit"):
        names.append("knowledge_deposit")
    # 去重保序
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out

def resolve_ticket_flags(
    domain: str,
    *,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    ticket_flags: dict | None = None,
) -> dict:
    """优先用 bake 传入的 ticket 实体；否则回落域默认 schema。"""
    if isinstance(ticket_flags, dict) and ticket_flags:
        return ticket_flags
    d = (domain or "").strip()
    try:
        from app.bake.schema.templates import SCHEMA_BUILDERS

        builder = SCHEMA_BUILDERS.get(d)
        if builder:
            schema = builder("thesis")
            ent = ((schema.get("entities") or {}).get("ticket") or {})
            if isinstance(ent, dict):
                return ent
    except Exception:
        pass
    if d == "DOM-GENERIC":
        try:
            from app.bake.archetype_shells import build_generic_shell_schema

            schema = build_generic_shell_schema(
                "thesis",
                archetype=archetype,
                archetypes=archetypes,
            )
            ent = ((schema.get("entities") or {}).get("ticket") or {})
            if isinstance(ent, dict):
                return ent
        except Exception:
            pass
    return {}

def ticket_optional_columns_for(
    domain: str,
    *,
    ticket_flags: dict | None = None,
) -> list[tuple[str, str]]:
    names: list[str] = []
    names.extend(TICKET_DOMAIN_COLUMNS.get(domain or "", []))
    names.extend(_ticket_flag_column_names(ticket_flags))
    seen: set[str] = set()
    cols: list[tuple[str, str]] = []
    for n in names:
        key = n.lower()
        if key in seen:
            continue
        for cat_name, cat_ddl in TICKET_OPTIONAL_COLUMNS:
            if cat_name.lower() == key:
                seen.add(key)
                cols.append((cat_name, cat_ddl))
                break
    return cols

def ensure_ticket_extra_sql(
    sql: str,
    *,
    domain: str,
    ticket_table: str | None,
    ticket_flags: dict | None = None,
) -> str:
    """对单据主表按域/能力补齐扩展列，并剔除跨域 L1 超集。"""
    t = (ticket_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql
    want = ticket_optional_columns_for(domain, ticket_flags=ticket_flags)
    allow = {n.lower() for n, _ in want}

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _prune_columns(body, allow=allow, known=_TICKET_OPTIONAL_NAMES)
        if want:
            body = _inject_missing_columns(body, want)
        body = _strip_trailing_comma(body)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)

_CREDIT_LEDGER_DDL = """
CREATE TABLE IF NOT EXISTS credit_ledger (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  delta INT NOT NULL,
  score_after INT NOT NULL DEFAULT 0,
  reason VARCHAR(128) DEFAULT '',
  ref_type VARCHAR(32) DEFAULT '',
  ref_id BIGINT NULL,
  operator VARCHAR(64) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_credit_user (username, id)
);
"""

SYS_USER_CREDIT_COLUMNS: list[tuple[str, str]] = [
    ("credit_score", "INT NOT NULL DEFAULT 100"),
]

def ensure_borrow_credit_sql(
    sql: str,
    *,
    enabled: bool,
    initial: int = 100,
) -> str:
    """信誉分物理列：sys_user.credit_score + credit_ledger 流水。"""
    init = max(1, min(999, int(initial or 100)))
    cols = [("credit_score", f"INT NOT NULL DEFAULT {init}")]
    out = sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "sys_user":
            return m.group(0)
        if not enabled:
            body = _prune_columns(body, allow=set(), known={"credit_score"})
        else:
            body = _inject_missing_columns(body, cols)
        body = _strip_trailing_comma(body)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, out)
    if not enabled:
        out = re.sub(
            r"CREATE TABLE IF NOT EXISTS\s+`?credit_ledger`?\s*\((?:.|\n)*?\);\s*",
            "",
            out,
            flags=re.IGNORECASE,
        )
    elif "credit_ledger" not in out.lower():
        out = out.rstrip() + "\n" + _CREDIT_LEDGER_DDL
    return out

def ensure_ticket_progress_sql(sql: str, ticket_table: str | None) -> str:
    """单据进度统一为 {ticket}_progress；去掉同域闲置的 {ticket}_log，避免双表语义。"""
    t = (ticket_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql
    progress = f"{t}_progress"
    log_name = f"{t}_log"
    out = re.sub(
        rf"CREATE TABLE IF NOT EXISTS\s+`?{re.escape(log_name)}`?\s*\((?:.|\n)*?\);\s*",
        "",
        sql,
        count=1,
        flags=re.IGNORECASE,
    )
    if re.search(rf"CREATE TABLE IF NOT EXISTS\s+`?{re.escape(progress)}`?\b", out, re.I):
        return out
    return out.rstrip() + "\n" + _TICKET_PROGRESS_DDL.format(table=progress)
