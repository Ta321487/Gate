# -*- coding: utf-8 -*-
"""单据业务参数与能力开关 → 交付包内 Java 策略类（bake 生成，不再写 thesis.ticket-*）。

口径沿革：
- 2026-07-25（commit 86c9649）前：各 DOM-*.sql 模板内置 ``sys_config`` 表 + 种子行；
- 2026-07-25 起：去掉生侧 ``sys_config``，参数经 ``application.yml`` 的 ``thesis.ticket-*`` 注入；
- 本模块起：单据整段不再进 yml，由 bake 直接生成 ``config/TicketPolicy.java``。

学生看到的是一个正常的业务策略常量类（可读、可改、答辩能讲），交付物里不再出现
成排的工厂腔配置键。``thesis.use-quota`` 仍留在 yml：它还喂 ``OrderStore.bind(...)``，
不是单据专属，故不随单据一起下沉。

``FIELDS`` 是唯一真源：骨架 ``TicketPolicy.java`` 与 bake 生成物都由它渲染，
``backend/tests/test_ticket_rules_bake.py`` 校验三者一致。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# ---------------------------------------------------------------- 常量与位置
POLICY_CLASS = "TicketPolicy"
POLICY_PACKAGE = "com.thesis.config"
POLICY_REL = Path("backend/src/main/java/com/thesis/config") / f"{POLICY_CLASS}.java"
#: 仍留在 yml 的共享键（非单据专属），不得产成 TicketPolicy 常量
SHARED_YML_KEYS: tuple[str, ...] = ("use-quota",)

# (yml 键, Java 常量, Java 类型, 默认字面量, binder 字段名, 渲染分组)
FIELDS: tuple[tuple[str, str, str, str, str, str], ...] = (
    # ---------- 单据主流程 ----------
    ("enable-ticket", "ENABLED", "boolean", "true", "enableTicket", "flow"),
    ("ticket-mode", "MODE", "String", '"archive"', "ticketMode", "flow"),
    ("ticket-table", "TABLE", "String", '"borrow"', "ticketTable", "flow"),
    ("use-deadline", "USE_DEADLINE", "boolean", "true", "useDeadline", "flow"),
    ("allow-multi-ticket", "ALLOW_MULTI", "boolean", "false", "allowMultiTicket", "flow"),
    ("check-time-conflict", "CHECK_TIME_CONFLICT", "boolean", "false", "checkTimeConflict", "flow"),
    # ---------- 借阅 / 罚金 / 爽约 ----------
    ("ticket-loan-days", "LOAN_DAYS", "int", "0", "ticketLoanDays", "biz"),
    ("ticket-max-active", "MAX_ACTIVE", "int", "0", "ticketMaxActive", "biz"),
    ("ticket-fine-per-day", "FINE_PER_DAY", "double", "-1", "ticketFinePerDay", "biz"),
    ("ticket-pickup-place", "PICKUP_PLACE", "String", '""', "ticketPickupPlace", "biz"),
    ("ticket-no-show-after-end", "NO_SHOW_AFTER_END", "boolean", "false", "ticketNoShowAfterEnd", "biz"),
    ("ticket-no-show-penalty-yuan", "NO_SHOW_PENALTY_YUAN", "double", "0", "ticketNoShowPenaltyYuan", "biz"),
    ("ticket-hold-hours", "HOLD_HOURS", "int", "48", "ticketHoldHours", "biz"),
    ("ticket-max-cancel-holds", "MAX_CANCEL_HOLDS", "int", "0", "ticketMaxCancelHolds", "biz"),
    # ---------- 时限 / SLA ----------
    ("ticket-follow-remind-days", "FOLLOW_REMIND_DAYS", "int", "0", "ticketFollowRemindDays", "sla"),
    ("ticket-stale-follow-days", "STALE_FOLLOW_DAYS", "int", "0", "ticketStaleFollowDays", "sla"),
    ("ticket-level-sla-high-days", "LEVEL_SLA_HIGH_DAYS", "int", "0", "ticketLevelSlaHighDays", "sla"),
    ("ticket-level-sla-mid-days", "LEVEL_SLA_MID_DAYS", "int", "0", "ticketLevelSlaMidDays", "sla"),
    ("ticket-level-sla-low-days", "LEVEL_SLA_LOW_DAYS", "int", "0", "ticketLevelSlaLowDays", "sla"),
    ("ticket-due-soon-days", "DUE_SOON_DAYS", "int", "0", "ticketDueSoonDays", "sla"),
    ("ticket-max-overdue-times", "MAX_OVERDUE_TIMES", "int", "0", "ticketMaxOverdueTimes", "sla"),
    ("ticket-objection-days", "OBJECTION_DAYS", "int", "0", "ticketObjectionDays", "sla"),
    ("ticket-week-report-deadline-day", "WEEK_REPORT_DEADLINE_DAY", "int", "0", "ticketWeekReportDeadlineDay", "sla"),
    ("ticket-urge-cooldown-minutes", "URGE_COOLDOWN_MINUTES", "int", "0", "ticketUrgeCooldownMinutes", "sla"),
    ("ticket-cancel-before-hours", "CANCEL_BEFORE_HOURS", "int", "0", "ticketCancelBeforeHours", "sla"),
    ("ticket-claim-cooldown-hours", "CLAIM_COOLDOWN_HOURS", "int", "0", "ticketClaimCooldownHours", "sla"),
    # ---------- 续借 / 修改 / 信用 ----------
    ("ticket-max-renew", "MAX_RENEW", "int", "1", "ticketMaxRenew", "rule"),
    ("ticket-renew-days", "RENEW_DAYS", "int", "0", "ticketRenewDays", "rule"),
    ("ticket-category-limit", "CATEGORY_LIMIT", "int", "0", "ticketCategoryLimit", "rule"),
    ("ticket-min-remark-words", "MIN_REMARK_WORDS", "int", "0", "ticketMinRemarkWords", "rule"),
    ("ticket-max-revise-times", "MAX_REVISE_TIMES", "int", "0", "ticketMaxReviseTimes", "rule"),
    ("ticket-max-drop-times", "MAX_DROP_TIMES", "int", "0", "ticketMaxDropTimes", "rule"),
    ("ticket-semester-credit-cap", "SEMESTER_CREDIT_CAP", "int", "0", "ticketSemesterCreditCap", "rule"),
    ("ticket-credit-warn-remaining", "CREDIT_WARN_REMAINING", "int", "0", "ticketCreditWarnRemaining", "rule"),
    ("ticket-credit-initial", "CREDIT_INITIAL", "int", "100", "ticketCreditInitial", "rule"),
    ("ticket-credit-overdue-delta", "CREDIT_OVERDUE_DELTA", "int", "5", "ticketCreditOverdueDelta", "rule"),
    ("ticket-credit-block-below", "CREDIT_BLOCK_BELOW", "int", "60", "ticketCreditBlockBelow", "rule"),
    # ---------- 匹配 / 床位口径文案 ----------
    ("ticket-match-profile-building-key", "MATCH_PROFILE_BUILDING_KEY", "String", '""', "ticketMatchProfileBuildingKey", "message"),
    ("ticket-match-profile-room-key", "MATCH_PROFILE_ROOM_KEY", "String", '""', "ticketMatchProfileRoomKey", "message"),
    ("ticket-match-profile-building-field", "MATCH_PROFILE_BUILDING_FIELD", "String", '""', "ticketMatchProfileBuildingField", "message"),
    ("ticket-match-profile-room-field", "MATCH_PROFILE_ROOM_FIELD", "String", '""', "ticketMatchProfileRoomField", "message"),
    ("ticket-match-profile-need-message", "MATCH_PROFILE_NEED_MESSAGE", "String", '""', "ticketMatchProfileNeedMessage", "message"),
    ("ticket-match-profile-deny-message", "MATCH_PROFILE_DENY_MESSAGE", "String", '""', "ticketMatchProfileDenyMessage", "message"),
    ("ticket-bed-constraint-need-message", "BED_CONSTRAINT_NEED_MESSAGE", "String", '""', "ticketBedConstraintNeedMessage", "message"),
    ("ticket-bed-constraint-deny-message", "BED_CONSTRAINT_DENY_MESSAGE", "String", '""', "ticketBedConstraintDenyMessage", "message"),
    ("ticket-age-constraint-need-message", "AGE_CONSTRAINT_NEED_MESSAGE", "String", '""', "ticketAgeConstraintNeedMessage", "message"),
    ("ticket-age-constraint-deny-message", "AGE_CONSTRAINT_DENY_MESSAGE", "String", '""', "ticketAgeConstraintDenyMessage", "message"),
)

#: 扩展能力开关：(yml 键, Java 常量)。类型固定 boolean、默认 false；
#: binder 字段名一律由 "ticket" + PascalCase(常量) 推出（测试会对骨架做机械校验）。
FLAG_KEYS: tuple[tuple[str, str], ...] = (
    ("ticket-two-level", "TWO_LEVEL"),
    ("ticket-three-level", "THREE_LEVEL"),
    ("ticket-require-attach", "REQUIRE_ATTACH"),
    ("ticket-allow-rating", "ALLOW_RATING"),
    ("ticket-allow-rating-tags", "ALLOW_RATING_TAGS"),
    ("ticket-check-mutex", "CHECK_MUTEX"),
    ("ticket-week-calendar", "WEEK_CALENDAR"),
    ("ticket-allow-checkin", "ALLOW_CHECKIN"),
    ("ticket-peer-accept", "PEER_ACCEPT"),
    ("ticket-issue-pass-code", "ISSUE_PASS_CODE"),
    ("ticket-allow-renew", "ALLOW_RENEW"),
    ("ticket-allow-waitlist", "ALLOW_WAITLIST"),
    ("ticket-allow-book-hold", "ALLOW_BOOK_HOLD"),
    ("ticket-allow-book-lost", "ALLOW_BOOK_LOST"),
    ("ticket-require-return-attach", "REQUIRE_RETURN_ATTACH"),
    ("ticket-pick-loan-period", "PICK_LOAN_PERIOD"),
    ("ticket-allow-qty", "ALLOW_QTY"),
    ("ticket-require-remark", "REQUIRE_REMARK"),
    ("ticket-pick-date-range", "PICK_DATE_RANGE"),
    ("ticket-approve-ends-flow", "APPROVE_ENDS_FLOW"),
    ("ticket-auto-approve", "AUTO_APPROVE"),
    ("ticket-require-claim-code", "REQUIRE_CLAIM_CODE"),
    ("ticket-match-profile-room", "MATCH_PROFILE_ROOM"),
    ("ticket-match-profile-loose-building", "MATCH_PROFILE_LOOSE_BUILDING"),
    ("ticket-applicant-complete-only", "APPLICANT_COMPLETE_ONLY"),
    ("ticket-allow-proxy-pickup", "ALLOW_PROXY_PICKUP"),
    ("ticket-bed-constraint", "BED_CONSTRAINT"),
    ("ticket-arrival-notify", "ARRIVAL_NOTIFY"),
    ("ticket-require-notice-ack", "REQUIRE_NOTICE_ACK"),
    ("ticket-allow-deposit", "ALLOW_DEPOSIT"),
    ("ticket-allow-exception-close", "ALLOW_EXCEPTION_CLOSE"),
    ("ticket-require-training-ack", "REQUIRE_TRAINING_ACK"),
    ("ticket-require-insurance-ack", "REQUIRE_INSURANCE_ACK"),
    ("ticket-require-meeting-ack", "REQUIRE_MEETING_ACK"),
    ("ticket-require-apply-invite", "REQUIRE_APPLY_INVITE"),
    ("ticket-require-price-note-ack", "REQUIRE_PRICE_NOTE_ACK"),
    ("ticket-require-sponsor-ack", "REQUIRE_SPONSOR_ACK"),
    ("ticket-require-plan-ack", "REQUIRE_PLAN_ACK"),
    ("ticket-require-prereq-ack", "REQUIRE_PREREQ_ACK"),
    ("ticket-age-constraint", "AGE_CONSTRAINT"),
    ("ticket-allow-late-minutes", "ALLOW_LATE_MINUTES"),
    ("ticket-block-if-calib-expired", "BLOCK_IF_CALIB_EXPIRED"),
    ("ticket-allow-project-no", "ALLOW_PROJECT_NO"),
    ("ticket-allow-procure-ref", "ALLOW_PROCURE_REF"),
    ("ticket-procure-to-stock-in", "PROCURE_TO_STOCK_IN"),
    ("ticket-allow-dual-review", "ALLOW_DUAL_REVIEW"),
    ("ticket-allow-ship-fee", "ALLOW_SHIP_FEE"),
    ("ticket-allow-utility-note", "ALLOW_UTILITY_NOTE"),
    ("ticket-overdue-auto-compensate", "OVERDUE_AUTO_COMPENSATE"),
    ("ticket-allow-fine-waive", "ALLOW_FINE_WAIVE"),
    ("ticket-renew-block-if-held", "RENEW_BLOCK_IF_HELD"),
    ("ticket-require-peer-confirm", "REQUIRE_PEER_CONFIRM"),
    ("ticket-require-abandon-dual", "REQUIRE_ABANDON_DUAL"),
    ("ticket-phone-dup-check", "PHONE_DUP_CHECK"),
    ("ticket-level-affects-deadline", "LEVEL_AFFECTS_DEADLINE"),
    ("ticket-notify-duty-on-report", "NOTIFY_DUTY_ON_REPORT"),
    ("ticket-allow-objection-window", "ALLOW_OBJECTION_WINDOW"),
    ("ticket-allow-deal-amount", "ALLOW_DEAL_AMOUNT"),
    ("ticket-allow-next-action", "ALLOW_NEXT_ACTION"),
    ("ticket-require-close-attach", "REQUIRE_CLOSE_ATTACH"),
    ("ticket-require-return-date", "REQUIRE_RETURN_DATE"),
    ("ticket-attach-by-leave-type", "ATTACH_BY_LEAVE_TYPE"),
    ("ticket-allow-leave-proxy", "ALLOW_LEAVE_PROXY"),
    ("ticket-allow-interview-result", "ALLOW_INTERVIEW_RESULT"),
    ("ticket-allow-batch-hire", "ALLOW_BATCH_HIRE"),
    ("ticket-allow-written-score", "ALLOW_WRITTEN_SCORE"),
    ("ticket-allow-bg-check-note", "ALLOW_BG_CHECK_NOTE"),
    ("ticket-allow-defense-result", "ALLOW_DEFENSE_RESULT"),
    ("ticket-mask-bank-account", "MASK_BANK_ACCOUNT"),
    ("ticket-allow-disburse-batch", "ALLOW_DISBURSE_BATCH"),
    ("ticket-week-report-remind", "WEEK_REPORT_REMIND"),
    ("ticket-require-appraisal", "REQUIRE_APPRAISAL"),
    ("ticket-allow-company-eval", "ALLOW_COMPANY_EVAL"),
    ("ticket-allow-excellent-mark", "ALLOW_EXCELLENT_MARK"),
    ("ticket-require-feedback-set", "REQUIRE_FEEDBACK_SET"),
    ("ticket-allow-record-url", "ALLOW_RECORD_URL"),
    ("ticket-allow-makeup-apply", "ALLOW_MAKEUP_APPLY"),
    ("ticket-home-visit-template", "HOME_VISIT_TEMPLATE"),
    ("ticket-allow-confidential", "ALLOW_CONFIDENTIAL"),
    ("ticket-allow-assign-dept", "ALLOW_ASSIGN_DEPT"),
    ("ticket-credit-on-overdue", "CREDIT_ON_OVERDUE"),
    ("ticket-allow-user-urge", "ALLOW_USER_URGE"),
    ("ticket-lock-urge-after-rate", "LOCK_URGE_AFTER_RATE"),
    ("ticket-allow-cancel-urge", "ALLOW_CANCEL_URGE"),
    ("ticket-require-fault-reason", "REQUIRE_FAULT_REASON"),
    ("ticket-require-close-summary", "REQUIRE_CLOSE_SUMMARY"),
    ("ticket-require-low-rating-remark", "REQUIRE_LOW_RATING_REMARK"),
    ("ticket-sla-split", "SLA_SPLIT"),
    ("ticket-escalate-on-overdue", "ESCALATE_ON_OVERDUE"),
    ("ticket-notify-supervisor-on-overdue", "NOTIFY_SUPERVISOR_ON_OVERDUE"),
    ("ticket-allow-hold-resume", "ALLOW_HOLD_RESUME"),
    ("ticket-allow-cancel-dispatched", "ALLOW_CANCEL_DISPATCHED"),
    ("ticket-allow-ticket-draft", "ALLOW_TICKET_DRAFT"),
    ("ticket-allow-follow-rate", "ALLOW_FOLLOW_RATE"),
    ("ticket-preferred-slot", "PREFERRED_SLOT"),
    ("ticket-progress-subscribe", "PROGRESS_SUBSCRIBE"),
    ("ticket-night-urgent", "NIGHT_URGENT"),
    ("ticket-allow-parts-note", "ALLOW_PARTS_NOTE"),
    ("ticket-allow-quote", "ALLOW_QUOTE"),
    ("ticket-allow-public-area", "ALLOW_PUBLIC_AREA"),
    ("ticket-dup-room-check", "DUP_ROOM_CHECK"),
    ("ticket-allow-asset-code", "ALLOW_ASSET_CODE"),
    ("ticket-allow-remote-url", "ALLOW_REMOTE_URL"),
    ("ticket-allow-serial-no", "ALLOW_SERIAL_NO"),
    ("ticket-allow-helper", "ALLOW_HELPER"),
    ("ticket-today-board", "TODAY_BOARD"),
    ("ticket-print-ticket", "PRINT_TICKET"),
    # 注：ticket-address-reuse / export-attach-urls / allow-audio-remark / allow-route-note /
    # visit-followup / allow-skill-tag / allow-ticket-merge / allow-knowledge-deposit /
    # category-color-hint 这 9 个键历史上会写进 yml 但交付链路无人读取
    # （对应前端开关由接口载荷的 ticket.* 携带），属无效写参，故不随本轮下沉。
    ("ticket-repair-thicken", "REPAIR_THICKEN"),
    ("ticket-apply-thicken", "APPLY_THICKEN"),
    ("ticket-notify-on-apply-success", "NOTIFY_ON_APPLY_SUCCESS"),
    ("ticket-allow-meeting-place", "ALLOW_MEETING_PLACE"),
    ("ticket-allow-emergency-contact", "ALLOW_EMERGENCY_CONTACT"),
)


def _pascal(const: str) -> str:
    """常量名 → 小驼峰（ALLOW_RATING → AllowRating）。"""
    return "".join(p[:1] + p[1:].lower() for p in const.split("_"))


def all_fields() -> tuple[tuple[str, str, str, str, str, str], ...]:
    """全表：(yml 键, Java 常量, 类型, 默认字面量, binder 字段, 分组)。"""
    flags = tuple(
        (key, const, "boolean", "false", "ticket" + _pascal(const), "flag")
        for key, const in FLAG_KEYS
    )
    return FIELDS + flags


FIELD_BY_KEY: dict[str, tuple[str, str, str, str, str, str]] = {f[0]: f for f in all_fields()}
CONST_BY_KEY: dict[str, str] = {f[0]: f[1] for f in all_fields()}
FIELD_BY_FIELD: dict[str, tuple[str, str, str, str, str, str]] = {f[4]: f for f in all_fields()}

#: 开关在 ticket_ent 上的来源键；默认按 yml 键去 ticket- 转小驼峰，例外在此显式列出。
FLAG_ENTITY_OVERRIDES: dict[str, tuple[str, ...]] = {
    "ticket-two-level": ("twoLevelApprove", "threeLevelApprove"),
    "ticket-three-level": ("threeLevelApprove",),
}


def entity_keys_for(yml_key: str) -> tuple[str, ...]:
    """能力开关 → ticket_ent 上的实体键（任一为真即开）。"""
    if yml_key in FLAG_ENTITY_OVERRIDES:
        return FLAG_ENTITY_OVERRIDES[yml_key]
    assert yml_key.startswith("ticket-"), yml_key
    parts = yml_key[len("ticket-") :].split("-")
    return ("".join([parts[0]] + [p[:1].upper() + p[1:] for p in parts[1:]]),)


def _int_or(raw: Any, default: int) -> int:
    """与原 yml 发射逻辑同义：空值/非法值回落默认。"""
    try:
        return int(raw or default)
    except (TypeError, ValueError):
        return default


def _float_or(raw: Any, default: float) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def _pos(raw: Any) -> int | None:
    """>0 才生效（沿用原逻辑：<=0 视为未配置）。"""
    n = _int_or(raw, 0)
    return n if n > 0 else None


def _ticket_context(domain: str, spec: dict[str, Any]) -> dict[str, Any]:
    """与 _patch_thesis_yml 同源解析 runtime / caps / 单据结构位。"""
    from app.bake.catalog import DOMAINS
    from app.bake.domains import DOMAIN_CAPABILITIES

    runtime = dict(spec.get("runtime") or {})
    if not runtime:
        runtime = dict((DOMAINS.get(domain) or {}).get("runtime") or {})
    caps = set(spec.get("capabilities") or DOMAIN_CAPABILITIES.get(domain) or [])
    ent = ((spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
    return {"runtime": runtime, "caps": caps, "ent": ent}


def collect(domain: str, spec: dict[str, Any]) -> dict[str, Any]:
    """按开题收集单据策略值（常量 → 值）；未出现者渲染时回落到类内默认值。"""
    ctx = _ticket_context(domain, spec)
    runtime, caps, ent = ctx["runtime"], ctx["caps"], ctx["ent"]
    out: dict[str, Any] = {}

    enable_ticket = runtime.get("enable_ticket")
    if enable_ticket is None:
        enable_ticket = "ticket_flow" in caps
    use_deadline = runtime.get("use_deadline")
    if use_deadline is None:
        use_deadline = "deadline" in caps
    check_conflict = runtime.get("check_time_conflict")
    if check_conflict is None:
        check_conflict = "time_conflict" in caps

    out["ENABLED"] = bool(enable_ticket)
    out["USE_DEADLINE"] = bool(use_deadline)
    out["ALLOW_MULTI"] = bool(runtime.get("allow_multi_ticket") or False)
    out["CHECK_TIME_CONFLICT"] = bool(check_conflict)
    out["MODE"] = str(runtime.get("ticket_mode") or "archive")
    out["TABLE"] = str(runtime.get("ticket_table") or "borrow")
    if not enable_ticket:
        return out

    # ---- 扩展能力开关：开题命中才为 true ----
    for key, _const in FLAG_KEYS:
        out[_const] = any(bool(ent.get(k)) for k in entity_keys_for(key))

    # ---- 借阅 / 罚金 ----
    from app.bake.ticket_rules import rules_for

    rules = rules_for(
        domain,
        title=str(spec.get("title") or ""),
        proposal_text=str(spec.get("proposal_text") or ""),
    )
    loan_n = _pos(rules.get("loan_days"))
    if loan_n is not None:
        out["LOAN_DAYS"] = loan_n
    max_n = _pos(rules.get("max_active"))
    if max_n is not None:
        out["MAX_ACTIVE"] = max_n
    if "fine_per_day" in rules:
        fine_n = _float_or(rules.get("fine_per_day"), -1.0)
        if fine_n >= 0:
            out["FINE_PER_DAY"] = fine_n
    place = str(rules.get("pickup_place") or "").strip()
    if place:
        out["PICKUP_PLACE"] = place
    if ent.get("noShowAfterEnd") and ent.get("allowCheckin"):
        out["NO_SHOW_AFTER_END"] = True
        pen = _float_or(ent.get("noShowPenaltyYuan"), 0.0)
        if pen > 0:
            out["NO_SHOW_PENALTY_YUAN"] = pen
    if ent.get("allowBookHold"):
        out["HOLD_HOURS"] = _clamp(_int_or(ent.get("holdHours"), 48), 1, 168)
    max_cancel = _pos(ent.get("maxCancelHolds"))
    if max_cancel is not None:
        out["MAX_CANCEL_HOLDS"] = _clamp(max_cancel, 1, 20)

    # ---- 跟进 / 时限 ----
    follow_remind = _pos(ent.get("followRemindDays"))
    if follow_remind is not None:
        out["FOLLOW_REMIND_DAYS"] = _clamp(follow_remind, 1, 14)
    stale_days = _pos(ent.get("staleFollowDays"))
    if stale_days is not None:
        out["STALE_FOLLOW_DAYS"] = _clamp(stale_days, 1, 90)
    for const, field in (
        ("LEVEL_SLA_HIGH_DAYS", "levelSlaHighDays"),
        ("LEVEL_SLA_MID_DAYS", "levelSlaMidDays"),
        ("LEVEL_SLA_LOW_DAYS", "levelSlaLowDays"),
        ("OBJECTION_DAYS", "objectionDays"),
    ):
        days = _pos(ent.get(field))
        if days is not None:
            out[const] = _clamp(days, 1, 60)
    week_dl = _pos(ent.get("weekReportDeadlineDay"))
    if week_dl is not None:
        out["WEEK_REPORT_DEADLINE_DAY"] = _clamp(week_dl, 1, 28)
    urge_cd = _pos(ent.get("urgeCooldownMinutes"))
    if urge_cd is not None and ent.get("allowUserUrge"):
        out["URGE_COOLDOWN_MINUTES"] = _clamp(urge_cd, 1, 1440)
    due_soon = _pos(ent.get("dueSoonDays"))
    if due_soon is not None and not ent.get("slaDeadline") and not ent.get("applicantCompleteOnly"):
        out["DUE_SOON_DAYS"] = _clamp(due_soon, 1, 14)
    max_od = _pos(ent.get("maxOverdueTimes"))
    if max_od is not None:
        out["MAX_OVERDUE_TIMES"] = _clamp(max_od, 1, 20)
    cancel_before = _pos(ent.get("cancelBeforeHours"))
    if cancel_before is not None:
        out["CANCEL_BEFORE_HOURS"] = _clamp(cancel_before, 1, 720)
    claim_cd = _pos(ent.get("claimCooldownHours"))
    if claim_cd is not None:
        out["CLAIM_COOLDOWN_HOURS"] = _clamp(claim_cd, 1, 168)

    # ---- 续借 / 修改 / 信用 ----
    if ent.get("allowRenew"):
        out["MAX_RENEW"] = _clamp(_int_or(ent.get("maxRenew"), 1), 1, 5)
        renew_days = _pos(ent.get("renewDays"))
        if renew_days is not None:
            out["RENEW_DAYS"] = renew_days
    cat_limit_n = _pos(ent.get("categoryLimit"))
    if cat_limit_n is not None:
        out["CATEGORY_LIMIT"] = cat_limit_n
    min_words = _pos(ent.get("minRemarkWords"))
    if min_words is not None:
        out["MIN_REMARK_WORDS"] = _clamp(min_words, 1, 5000)
    max_revise = _pos(ent.get("maxReviseTimes"))
    if max_revise is not None:
        out["MAX_REVISE_TIMES"] = _clamp(max_revise, 1, 20)
    max_drop = _pos(ent.get("maxDropTimes"))
    if max_drop is not None:
        out["MAX_DROP_TIMES"] = _clamp(max_drop, 1, 30)
    credit_cap = _pos(ent.get("semesterCreditCap"))
    if credit_cap is not None:
        out["SEMESTER_CREDIT_CAP"] = _clamp(credit_cap, 1, 200)
    credit_warn = _pos(ent.get("creditWarnRemaining"))
    if credit_warn is not None:
        out["CREDIT_WARN_REMAINING"] = _clamp(credit_warn, 1, 50)
    if ent.get("creditOnOverdue"):
        out["CREDIT_INITIAL"] = _clamp(_int_or(ent.get("creditInitial"), 100), 1, 999)
        out["CREDIT_OVERDUE_DELTA"] = _clamp(_int_or(ent.get("creditOverdueDelta"), 5), 1, 100)
        out["CREDIT_BLOCK_BELOW"] = _clamp(_int_or(ent.get("creditBlockBelow"), 60), 0, 999)

    # ---- 匹配 / 床位口径文案 ----
    if ent.get("matchProfileRoom"):
        for key, ent_key in (
            ("ticket-match-profile-building-key", "matchProfileBuildingKey"),
            ("ticket-match-profile-room-key", "matchProfileRoomKey"),
            ("ticket-match-profile-building-field", "matchProfileBuildingField"),
            ("ticket-match-profile-room-field", "matchProfileRoomField"),
            ("ticket-match-profile-need-message", "matchProfileNeedMessage"),
            ("ticket-match-profile-deny-message", "matchProfileDenyMessage"),
        ):
            val = str(ent.get(ent_key) or "").strip()
            if val:
                out[CONST_BY_KEY[key]] = val
    if ent.get("bedConstraint"):
        labels = (spec.get("schema") or {}).get("labels") or {}
        for key, lab_key in (
            ("ticket-bed-constraint-need-message", "bedConstraintNeedMessage"),
            ("ticket-bed-constraint-deny-message", "bedConstraintDenyMessage"),
        ):
            val = str(labels.get(lab_key) or "").strip()
            if val:
                out[CONST_BY_KEY[key]] = val
    if ent.get("ageConstraint"):
        labels = (spec.get("schema") or {}).get("labels") or {}
        for key, lab_key in (
            ("ticket-age-constraint-need-message", "ageConstraintNeedMessage"),
            ("ticket-age-constraint-deny-message", "ageConstraintDenyMessage"),
        ):
            val = str(labels.get(lab_key) or "").strip()
            if val:
                out[CONST_BY_KEY[key]] = val

    return out


#: 语义字段的中文注释（渲染进 Java，便于学生/老师阅读）
COMMENTS: dict[str, str] = {
    "ENABLED": "是否启用单据主流程",
    "MODE": "单据模式：archive（关联档案、占库存）/ standalone（自由填写）",
    "TABLE": "单据主表名",
    "USE_DEADLINE": "是否按截止日管理（应还 / 处理时限）",
    "ALLOW_MULTI": "是否允许同一人同时开多张单",
    "CHECK_TIME_CONFLICT": "申请时检测本人已占用时段是否冲突",
    "LOAN_DAYS": "默认借期 / 处理时限天数；0 表示不按天",
    "MAX_ACTIVE": "每人同时在手的单据上限；0 表示不限",
    "FINE_PER_DAY": "逾期每天罚金（元）；-1 沿用代码默认，0 表示不收罚金",
    "PICKUP_PLACE": "取件 / 送达地点文案",
    "NO_SHOW_AFTER_END": "活动结束仍未签到记爽约",
    "NO_SHOW_PENALTY_YUAN": "爽约固定费用（元）；0 只改状态",
    "HOLD_HOURS": "预约到货后保留的小时数",
    "MAX_CANCEL_HOLDS": "允许取消占用的次数上限；0 表示不限",
    "FOLLOW_REMIND_DAYS": "跟进提醒间隔天数",
    "STALE_FOLLOW_DAYS": "超过 N 天无跟进视为停滞",
    "LEVEL_SLA_HIGH_DAYS": "高优先级单据的处理时限（天）",
    "LEVEL_SLA_MID_DAYS": "中优先级单据的处理时限（天）",
    "LEVEL_SLA_LOW_DAYS": "低优先级单据的处理时限（天）",
    "LEVEL_AFFECTS_DEADLINE": "按优先级套用不同处理时限",
    "DUE_SOON_DAYS": "到期前 N 天提醒",
    "MAX_OVERDUE_TIMES": "历史逾期达 N 次限制再借",
    "OBJECTION_DAYS": "结果公示后的异议登记窗口天数",
    "WEEK_REPORT_DEADLINE_DAY": "每周汇报的提交截止日（周内第几天）",
    "URGE_COOLDOWN_MINUTES": "用户催办的冷却分钟数",
    "CANCEL_BEFORE_HOURS": "活动开始前可取消报名的最少提前小时数；0 表示不限制",
    "CLAIM_COOLDOWN_HOURS": "失物启事发布后可认领的冷却小时数；0 表示不限制",
    "MAX_DROP_TIMES": "本学期退选次数上限；0 表示不限制",
    "SEMESTER_CREDIT_CAP": "学期已选学分上限；0 表示不限制",
    "CREDIT_WARN_REMAINING": "剩余学分低于该值时提示接近上限；0 表示不提示",
    "MAX_RENEW": "单次借出最多续借次数",
    "RENEW_DAYS": "每次续借延长的天数；0 表示跟默认天数",
    "CATEGORY_LIMIT": "同一分类下进行中单据上限；0 表示不限",
    "MIN_REMARK_WORDS": "申请说明的最少字数",
    "MAX_REVISE_TIMES": "被驳回后可修改重提的次数",
    "CREDIT_INITIAL": "初始信用分",
    "CREDIT_OVERDUE_DELTA": "每次逾期扣减的信用分",
    "CREDIT_BLOCK_BELOW": "信用分低于该值限制再借",
    "MATCH_PROFILE_ROOM": "按楼栋 / 房间匹配（同楼栋才能接单）",
    "MATCH_PROFILE_LOOSE_BUILDING": "只按楼栋匹配、不校验房间",
    "BED_CONSTRAINT": "床位占用约束（一人一床）",
    "MATCH_PROFILE_BUILDING_KEY": "匹配用的楼栋字段键",
    "MATCH_PROFILE_ROOM_KEY": "匹配用的房间字段键",
    "MATCH_PROFILE_BUILDING_FIELD": "用户资料里的楼栋字段名",
    "MATCH_PROFILE_ROOM_FIELD": "用户资料里的房间字段名",
    "MATCH_PROFILE_NEED_MESSAGE": "资料不全时的提示文案",
    "MATCH_PROFILE_DENY_MESSAGE": "匹配不通过的提示文案",
    "BED_CONSTRAINT_NEED_MESSAGE": "床位约束提示文案",
    "BED_CONSTRAINT_DENY_MESSAGE": "床位冲突拒绝文案",
    "AGE_CONSTRAINT": "线路年龄上下限对照资料",
    "AGE_CONSTRAINT_NEED_MESSAGE": "年龄限制缺资料提示",
    "AGE_CONSTRAINT_DENY_MESSAGE": "年龄不符合拒绝文案",
    "REQUIRE_PREREQ_ACK": "有先修提示码时须勾选确认",
    "ALLOW_LATE_MINUTES": "签到可登记迟到分钟数",
}

GROUP_TITLES: dict[str, str] = {
    "flow": "单据主流程",
    "biz": "借阅 / 罚金 / 爽约",
    "sla": "跟进与时限（SLA）",
    "rule": "续借 / 修改 / 信用",
    "message": "匹配与床位口径文案",
    "flag": "扩展能力开关（按开题启用）",
}

_ESCAPE = str.maketrans({"\\": "\\\\", '"': '\\"'})


def _literal(jtype: str, value: Any) -> str:
    if jtype == "String":
        return '"' + str(value).translate(_ESCAPE) + '"'
    if jtype == "boolean":
        return "true" if value else "false"
    if jtype == "double":
        return f"{float(value):g}"
    return str(int(value))


def _literal_from_default(jtype: str, default: str) -> Any:
    """把表中的默认字面量还原成可再渲染的值。"""
    if jtype == "boolean":
        return default.strip().lower() == "true"
    if jtype == "String":
        return default.strip().strip('"')
    if jtype == "double":
        return float(default)
    return int(default)


def default_values() -> dict[str, Any]:
    return {f[1]: _literal_from_default(f[2], f[3]) for f in all_fields()}


def render(values: dict[str, Any] | None = None) -> str:
    """渲染 TicketPolicy.java（未给出的常量回落到类内默认值）。"""
    given = dict(values or {})
    lines = [
        f"package {POLICY_PACKAGE};",
        "",
        "/**",
        " * 单据（申请 / 审核 / 跟进）业务规则与功能开关。",
        " * <p>按本系统开题口径生成，集中保存单据流程用到的天数、上限、文案与开关；",
        " * 需要调整业务口径时改这里的常量即可。</p>",
        " */",
        f"public final class {POLICY_CLASS} {{",
        "",
        f"    private {POLICY_CLASS}() {{}}",
    ]
    for group in ("flow", "biz", "sla", "rule", "message", "flag"):
        rows = [f for f in all_fields() if f[5] == group]
        if not rows:
            continue
        lines.append("")
        lines.append(f"    // ---------- {GROUP_TITLES[group]} ----------")
        for _key, const, jtype, default, _field, _grp in rows:
            cm = COMMENTS.get(const)
            if cm:
                lines.append(f"    /** {cm} */")
            value = given[const] if const in given else _literal_from_default(jtype, default)
            lines.append(f"    public static final {jtype} {const} = {_literal(jtype, value)};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_policy(dest: Path | str, domain: str, spec: dict[str, Any]) -> Path | None:
    """把本项目的单据策略写成 Java 类；骨架缺目录时跳过（非 Java 交付）。"""
    path = Path(dest) / POLICY_REL
    if not path.parent.is_dir():
        return None
    path.write_text(render(collect(domain, spec)), encoding="utf-8")
    return path


def policy_preview(domain: str, spec: dict[str, Any]) -> str:
    """把生成的策略按旧 yml 键值形式回显（仅门禁/用例核对，不参与交付）。

    交付物里这些键已不存在于 application.yml；本函数让「开题命中 → 参数落地」的
    断言仍能锚定在同一份真源（TicketPolicy 的取值）上。
    """
    values = {**default_values(), **collect(domain, spec)}
    lines = []
    for key, const, jtype, _default, _field, _grp in all_fields():
        if key in SHARED_YML_KEYS:
            continue
        lines.append(f"  {key}: {_literal(jtype, values[const]).strip('\"')}")
    return "\n".join(lines) + "\n"

