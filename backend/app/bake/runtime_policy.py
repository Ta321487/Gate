# -*- coding: utf-8 -*-
"""非单据业务参数与能力开关 → 交付包内 Java 策略类（bake 生成，不再写对应 thesis.*）。

与 ``ticket_policy.TicketPolicy`` 分工写死：
- TicketPolicy：单据主流程 / 借阅罚金 / SLA / 续借信用 / 匹配文案 / ticket-* 开关；
- AppPolicy：档案表位、下拉主数据、订单表位、预约表位、数值阈值、非单据能力开关。

``thesis.use-quota`` / 启动期身份键 / 门户访客键 / allow-appoint-from-users 仍留在 yml，
不得产成 AppPolicy 常量（见 ``KEEP_YML_KEYS``）。

``FIELDS`` + ``FLAG_KEYS`` 是唯一真源：骨架 ``AppPolicy.java`` 与 bake 生成物都由它渲染。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# ---------------------------------------------------------------- 常量与位置
POLICY_CLASS = "AppPolicy"
POLICY_PACKAGE = "com.thesis.config"
POLICY_REL = Path("backend/src/main/java/com/thesis/config") / f"{POLICY_CLASS}.java"

#: 必须留在 yml 的键（启动期 / 门户 / 门禁 / 与订单共用），不得下沉
KEEP_YML_KEYS: tuple[str, ...] = (
    "title",
    "register-role",
    "password-hash",
    "portal-guest-browse",
    "guest-teaser-limit",
    "allow-appoint-from-users",
    "use-quota",
)

# (yml 键, Java 常量, Java 类型, 默认字面量, binder 字段名, 渲染分组)
FIELDS: tuple[tuple[str, str, str, str, str, str], ...] = (
    # ---------- 档案 / 订单 / 预约表位 ----------
    ("archive-category-table", "ARCHIVE_CATEGORY_TABLE", "String", '"category"', "archiveCategoryTable", "table"),
    ("archive-item-table", "ARCHIVE_ITEM_TABLE", "String", '"book"', "archiveItemTable", "table"),
    ("archive-tag-table", "ARCHIVE_TAG_TABLE", "String", '""', "archiveTagTable", "table"),
    ("archive-item-tag-table", "ARCHIVE_ITEM_TAG_TABLE", "String", '""', "archiveItemTagTable", "table"),
    ("order-cart-table", "ORDER_CART_TABLE", "String", '""', "orderCartTable", "table"),
    ("order-table", "ORDER_TABLE", "String", '""', "orderTable", "table"),
    ("order-line-table", "ORDER_LINE_TABLE", "String", '""', "orderLineTable", "table"),
    ("slot-table", "SLOT_TABLE", "String", '""', "slotTable", "table"),
    ("reservation-table", "RESERVATION_TABLE", "String", '""', "reservationTable", "table"),
    ("lookup-site-table", "LOOKUP_SITE_TABLE", "String", '""', "lookupSiteTable", "table"),
    ("lookup-unit-table", "LOOKUP_UNIT_TABLE", "String", '""', "lookupUnitTable", "table"),
    ("lookup-type-table", "LOOKUP_TYPE_TABLE", "String", '""', "lookupTypeTable", "table"),
    # ---------- 下拉展示标签 ----------
    ("lookup-site-label", "LOOKUP_SITE_LABEL", "String", '"楼栋"', "lookupSiteLabel", "label"),
    ("lookup-unit-label", "LOOKUP_UNIT_LABEL", "String", '"房间"', "lookupUnitLabel", "label"),
    ("lookup-unit-capacity-label", "LOOKUP_UNIT_CAPACITY_LABEL", "String", '"容量"', "lookupUnitCapacityLabel", "label"),
    ("lookup-type-label", "LOOKUP_TYPE_LABEL", "String", '"类型"', "lookupTypeLabel", "label"),
    # ---------- 数值阈值 ----------
    ("stock-warn-below", "STOCK_WARN_BELOW", "int", "10", "stockWarnBelow", "numeric"),
    ("points-earn-per-yuan", "POINTS_EARN_PER_YUAN", "int", "1", "pointsEarnPerYuan", "numeric"),
    ("cancel-free-hours", "CANCEL_FREE_HOURS", "int", "0", "cancelFreeHours", "numeric"),
    ("reschedule-max-times", "RESCHEDULE_MAX_TIMES", "int", "0", "rescheduleMaxTimes", "numeric"),
    ("remind-ahead-minutes", "REMIND_AHEAD_MINUTES", "int", "0", "remindAheadMinutes", "numeric"),
    ("no-show-limit", "NO_SHOW_LIMIT", "int", "0", "noShowLimit", "numeric"),
    ("late-grace-minutes", "LATE_GRACE_MINUTES", "int", "15", "lateGraceMinutes", "numeric"),
    (
        "hospital-cancel-cutoff-minutes",
        "HOSPITAL_CANCEL_CUTOFF_MINUTES",
        "int",
        "0",
        "hospitalCancelCutoffMinutes",
        "numeric",
    ),
    (
        "hospital-id-limit-per-day",
        "HOSPITAL_ID_LIMIT_PER_DAY",
        "int",
        "0",
        "hospitalIdLimitPerDay",
        "numeric",
    ),
    ("parking-hourly-yuan", "PARKING_HOURLY_YUAN", "int", "0", "parkingHourlyYuan", "numeric"),
    ("parking-overtime-yuan", "PARKING_OVERTIME_YUAN", "int", "0", "parkingOvertimeYuan", "numeric"),
    (
        "meeting-min-duration-minutes",
        "MEETING_MIN_DURATION_MINUTES",
        "int",
        "0",
        "meetingMinDurationMinutes",
        "numeric",
    ),
    ("salon-reschedule-fee-yuan", "SALON_RESCHEDULE_FEE_YUAN", "int", "0", "salonRescheduleFeeYuan", "numeric"),
    (
        "hotel-late-checkout-fee-yuan",
        "HOTEL_LATE_CHECKOUT_FEE_YUAN",
        "int",
        "0",
        "hotelLateCheckoutFeeYuan",
        "numeric",
    ),
    (
        "carrent-mileage-over-fee-yuan",
        "CARRENT_MILEAGE_OVER_FEE_YUAN",
        "int",
        "0",
        "carrentMileageOverFeeYuan",
        "numeric",
    ),
    (
        "instrument-overtime-yuan",
        "INSTRUMENT_OVERTIME_YUAN",
        "int",
        "0",
        "instrumentOvertimeYuan",
        "numeric",
    ),
)

#: 能力开关：(yml 键, Java 常量)。类型固定 boolean、默认 false；
#: binder 字段名由 yml 键转小驼峰（测试会对骨架做机械校验）。
FLAG_KEYS: tuple[tuple[str, str], ...] = (
    ("archive-soft-delete", "ARCHIVE_SOFT_DELETE"),
    ("archive-user-publish", "ARCHIVE_USER_PUBLISH"),
    ("archive-publish-review", "ARCHIVE_PUBLISH_REVIEW"),
    ("archive-log-enabled", "ARCHIVE_LOG_ENABLED"),
    ("shop-marketplace", "SHOP_MARKETPLACE"),
    ("stock-warn-notify", "STOCK_WARN_NOTIFY"),
    ("stock-io-enabled", "STOCK_IO_ENABLED"),
    ("wallet-enabled", "WALLET_ENABLED"),
    ("points-enabled", "POINTS_ENABLED"),
    ("points-pay-enabled", "POINTS_PAY_ENABLED"),
    ("order-review-enabled", "ORDER_REVIEW_ENABLED"),
    ("favorites-enabled", "FAVORITES_ENABLED"),
    ("material-check-enabled", "MATERIAL_CHECK_ENABLED"),
    ("occupy-span-enabled", "OCCUPY_SPAN_ENABLED"),
    ("seat-select-enabled", "SEAT_SELECT_ENABLED"),
    ("parcel-shelf-enabled", "PARCEL_SHELF_ENABLED"),
    ("claim-proof-enabled", "CLAIM_PROOF_ENABLED"),
    ("lost-clue-enabled", "LOST_CLUE_ENABLED"),
    ("post-mute-enabled", "POST_MUTE_ENABLED"),
    ("content-report-enabled", "CONTENT_REPORT_ENABLED"),
    ("dm-shop-cs", "DM_SHOP_CS"),
    ("e-sign-enabled", "E_SIGN_ENABLED"),
    ("exam-enabled", "EXAM_ENABLED"),
    ("doclib-enabled", "DOCLIB_ENABLED"),
    ("survey-enabled", "SURVEY_ENABLED"),
    ("vote-enabled", "VOTE_ENABLED"),
    ("timebank-enabled", "TIMEBANK_ENABLED"),
    ("timebank-redeem-on-approve", "TIMEBANK_REDEEM_ON_APPROVE"),
    ("grade-scores-enabled", "GRADE_SCORES_ENABLED"),
    ("balance-ledger-enabled", "BALANCE_LEDGER_ENABLED"),
    ("balance-ledger-debit-on-approve", "BALANCE_LEDGER_DEBIT_ON_APPROVE"),
    ("slot-require-remark", "SLOT_REQUIRE_REMARK"),
    ("slot-require-confirm", "SLOT_REQUIRE_CONFIRM"),
    ("slot-allow-rating", "SLOT_ALLOW_RATING"),
    ("reserve-blacklist-enabled", "RESERVE_BLACKLIST_ENABLED"),
    ("hospital-waitlist-enabled", "HOSPITAL_WAITLIST_ENABLED"),
    ("patient-profile-enabled", "PATIENT_PROFILE_ENABLED"),
    ("parking-pass-enabled", "PARKING_PASS_ENABLED"),
    ("meeting-minutes-required", "MEETING_MINUTES_REQUIRED"),
    ("hotel-notice-required", "HOTEL_NOTICE_REQUIRED"),
    ("instrument-training-required", "INSTRUMENT_TRAINING_REQUIRED"),
)


def _yml_to_field(yml_key: str) -> str:
    """yml 键 → binder 小驼峰（archive-soft-delete → archiveSoftDelete）。"""
    parts = yml_key.split("-")
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def all_fields() -> tuple[tuple[str, str, str, str, str, str], ...]:
    """全表：(yml 键, Java 常量, 类型, 默认字面量, binder 字段, 分组)。"""
    flags = tuple(
        (key, const, "boolean", "false", _yml_to_field(key), "flag")
        for key, const in FLAG_KEYS
    )
    return FIELDS + flags


FIELD_BY_KEY: dict[str, tuple[str, str, str, str, str, str]] = {f[0]: f for f in all_fields()}
CONST_BY_KEY: dict[str, str] = {f[0]: f[1] for f in all_fields()}
FIELD_BY_FIELD: dict[str, tuple[str, str, str, str, str, str]] = {f[4]: f for f in all_fields()}

#: AppPolicy 下沉的全部 yml 键（验收差分用）
SINK_YML_KEYS: tuple[str, ...] = tuple(f[0] for f in all_fields())


def _int_or(raw: Any, default: int) -> int:
    try:
        return int(raw or default)
    except (TypeError, ValueError):
        return default


def _clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def _runtime_context(domain: str, spec: dict[str, Any]) -> dict[str, Any]:
    """与 _patch_thesis_yml 同源解析 runtime / caps / 实体。"""
    from app.bake.catalog import DOMAINS
    from app.bake.domains import DOMAIN_CAPABILITIES

    runtime = dict(spec.get("runtime") or {})
    if not runtime:
        runtime = dict((DOMAINS.get(domain) or {}).get("runtime") or {})
    caps = set(spec.get("capabilities") or DOMAIN_CAPABILITIES.get(domain) or [])
    schema = spec.get("schema") or {}
    archive_ent = (schema.get("entities") or {}).get("archive") or {}
    return {"runtime": runtime, "caps": caps, "schema": schema, "archive_ent": archive_ent}


def collect(domain: str, spec: dict[str, Any]) -> dict[str, Any]:
    """按开题收集 AppPolicy 取值（常量 → 值）；未出现者渲染时回落到类内默认值。"""
    ctx = _runtime_context(domain, spec)
    runtime, caps, schema, archive_ent = (
        ctx["runtime"],
        ctx["caps"],
        ctx["schema"],
        ctx["archive_ent"],
    )
    out: dict[str, Any] = {}

    # ---- 档案表位与档案侧开关 ----
    if "archive" in caps:
        out["ARCHIVE_CATEGORY_TABLE"] = str(runtime.get("archive_category_table") or "category")
        out["ARCHIVE_ITEM_TABLE"] = str(runtime.get("archive_item_table") or "book")
        if archive_ent.get("softDelete"):
            out["ARCHIVE_SOFT_DELETE"] = True
        if archive_ent.get("userPublish"):
            out["ARCHIVE_USER_PUBLISH"] = True
        if archive_ent.get("publishReview"):
            out["ARCHIVE_PUBLISH_REVIEW"] = True
        if schema.get("shopMarketplace"):
            out["SHOP_MARKETPLACE"] = True
        if schema.get("stockWarnNotify"):
            out["STOCK_WARN_NOTIFY"] = True
            out["STOCK_WARN_BELOW"] = _clamp(_int_or(schema.get("stockWarnBelow"), 10), 1, 999)
        tag = runtime.get("archive_tag_table")
        item_tag = runtime.get("archive_item_tag_table")
        if tag and item_tag:
            out["ARCHIVE_TAG_TABLE"] = str(tag)
            out["ARCHIVE_ITEM_TAG_TABLE"] = str(item_tag)

    # ---- 下拉主数据 ----
    site = runtime.get("lookup_site_table")
    unit = runtime.get("lookup_unit_table")
    typ = runtime.get("lookup_type_table")
    if site:
        out["LOOKUP_SITE_TABLE"] = str(site)
        out["LOOKUP_SITE_LABEL"] = str(runtime.get("lookup_site_label") or "楼栋")
    if unit:
        out["LOOKUP_UNIT_TABLE"] = str(unit)
        out["LOOKUP_UNIT_LABEL"] = str(runtime.get("lookup_unit_label") or "房间")
        # None 缺省「容量」；显式 "" 表示隐藏（物业/IT）；宿舍写「床位数」
        if "lookup_unit_capacity_label" in runtime:
            cap = runtime.get("lookup_unit_capacity_label")
            out["LOOKUP_UNIT_CAPACITY_LABEL"] = "" if cap is None else str(cap)
    if typ:
        out["LOOKUP_TYPE_TABLE"] = str(typ)
        out["LOOKUP_TYPE_LABEL"] = str(runtime.get("lookup_type_label") or "类型")

    # ---- 购物车 / 订单表位 ----
    if "order_lines" in caps:
        out["ORDER_CART_TABLE"] = str(runtime.get("order_cart_table") or "cart_line")
        out["ORDER_TABLE"] = str(runtime.get("order_table") or "biz_order")
        out["ORDER_LINE_TABLE"] = str(runtime.get("order_line_table") or "order_line")

    # ---- 钱包 / 积分 ----
    loyalty = schema.get("loyalty") or {}
    if "wallet" in caps:
        out["WALLET_ENABLED"] = True
    if "points" in caps:
        out["POINTS_ENABLED"] = True
        pts = loyalty.get("points") if isinstance(loyalty.get("points"), dict) else {}
        epy = _int_or(pts.get("earnPerYuan"), 1)
        if epy > 0:
            out["POINTS_EARN_PER_YUAN"] = epy
        if pts.get("payEnabled"):
            out["POINTS_PAY_ENABLED"] = True

    # ---- 能力开关（caps / 域特判）----
    if "order_review" in caps:
        out["ORDER_REVIEW_ENABLED"] = True
    if "favorites" in caps:
        out["FAVORITES_ENABLED"] = True
    if "dm" in caps:
        shop_cs = bool(schema.get("dmShopCs"))
        if not shop_cs and str(schema.get("dmPeerMode") or "").strip().lower() == "merchant":
            shop_cs = True
        # 与 menu_utils：多店有 dm 即收窄店铺客服，避免文案已是「联系商家」而 Java 仍 false
        if not shop_cs and schema.get("shopMarketplace"):
            shop_cs = True
        out["DM_SHOP_CS"] = bool(shop_cs)
    if "content_report" in caps:
        out["CONTENT_REPORT_ENABLED"] = True
    if "post_mute" in caps:
        out["POST_MUTE_ENABLED"] = True
    if "parcel_shelf" in caps:
        out["PARCEL_SHELF_ENABLED"] = True
    if "archive_log" in caps:
        out["ARCHIVE_LOG_ENABLED"] = True
    if "exam" in caps:
        out["EXAM_ENABLED"] = True
    if "survey" in caps:
        out["SURVEY_ENABLED"] = True
    if "vote" in caps:
        out["VOTE_ENABLED"] = True
    if "doclib" in caps:
        out["DOCLIB_ENABLED"] = True
    if "timebank" in caps:
        out["TIMEBANK_ENABLED"] = True
        out["TIMEBANK_REDEEM_ON_APPROVE"] = True
    if "seat_select" in caps:
        out["SEAT_SELECT_ENABLED"] = True
    if "stock_io" in caps:
        out["STOCK_IO_ENABLED"] = True
    if "e_sign" in caps:
        out["E_SIGN_ENABLED"] = True
    if "balance_ledger" in caps:
        out["BALANCE_LEDGER_ENABLED"] = True
        out["BALANCE_LEDGER_DEBIT_ON_APPROVE"] = True
    if domain == "DOM-GRADE":
        out["GRADE_SCORES_ENABLED"] = True
    if "occupy_span" in caps:
        out["OCCUPY_SPAN_ENABLED"] = True
    if "material_check" in caps:
        out["MATERIAL_CHECK_ENABLED"] = True
    if "claim_proof" in caps:
        out["CLAIM_PROOF_ENABLED"] = True
    if "lost_clue" in caps:
        out["LOST_CLUE_ENABLED"] = True

    # ---- 时段预约表位 + 预约侧开关/阈值（一律 AppPolicy，不进 yml）----
    resv_ent = (schema.get("entities") or {}).get("reservation") or {}
    if not isinstance(resv_ent, dict):
        resv_ent = {}
    if "slot_reserve" in caps:
        out["SLOT_TABLE"] = str(runtime.get("slot_table") or "resource_slot")
        out["RESERVATION_TABLE"] = str(runtime.get("reservation_table") or "reservation")
        if resv_ent.get("requireRemark"):
            out["SLOT_REQUIRE_REMARK"] = True
        if resv_ent.get("requireConfirm"):
            out["SLOT_REQUIRE_CONFIRM"] = True
        if resv_ent.get("allowRating"):
            out["SLOT_ALLOW_RATING"] = True
        for schema_key, const in (
            ("cancelFreeHours", "CANCEL_FREE_HOURS"),
            ("rescheduleMaxTimes", "RESCHEDULE_MAX_TIMES"),
            ("remindAheadMinutes", "REMIND_AHEAD_MINUTES"),
            ("noShowLimit", "NO_SHOW_LIMIT"),
            ("lateGraceMinutes", "LATE_GRACE_MINUTES"),
            ("hospitalCancelCutoffMinutes", "HOSPITAL_CANCEL_CUTOFF_MINUTES"),
            ("hospitalIdLimitPerDay", "HOSPITAL_ID_LIMIT_PER_DAY"),
            ("parkingHourlyYuan", "PARKING_HOURLY_YUAN"),
            ("parkingOvertimeYuan", "PARKING_OVERTIME_YUAN"),
            ("meetingMinDurationMinutes", "MEETING_MIN_DURATION_MINUTES"),
            ("salonRescheduleFeeYuan", "SALON_RESCHEDULE_FEE_YUAN"),
            ("hotelLateCheckoutFeeYuan", "HOTEL_LATE_CHECKOUT_FEE_YUAN"),
            ("carrentMileageOverFeeYuan", "CARRENT_MILEAGE_OVER_FEE_YUAN"),
            ("instrumentOvertimeYuan", "INSTRUMENT_OVERTIME_YUAN"),
        ):
            n = _int_or(schema.get(schema_key), 0)
            if n > 0:
                out[const] = n
        if schema.get("reserveBlacklist"):
            out["RESERVE_BLACKLIST_ENABLED"] = True
        if schema.get("hospitalWaitlist") or resv_ent.get("allowWaitlist"):
            out["HOSPITAL_WAITLIST_ENABLED"] = True
        if schema.get("patientProfile"):
            out["PATIENT_PROFILE_ENABLED"] = True
        if schema.get("parkingPass"):
            out["PARKING_PASS_ENABLED"] = True
        if schema.get("meetingMinutesRequired") or resv_ent.get("meetingMinutesRequired"):
            out["MEETING_MINUTES_REQUIRED"] = True
        if schema.get("hotelNoticeRequired") or resv_ent.get("hotelNoticeRequired"):
            out["HOTEL_NOTICE_REQUIRED"] = True
        if schema.get("instrumentTrainingRequired"):
            out["INSTRUMENT_TRAINING_REQUIRED"] = True

    return out


#: 语义字段的中文注释（渲染进 Java，便于学生/老师阅读）
COMMENTS: dict[str, str] = {
    "ARCHIVE_CATEGORY_TABLE": "档案分类表名",
    "ARCHIVE_ITEM_TABLE": "档案条目表名",
    "ARCHIVE_TAG_TABLE": "档案标签表名；空串表示未启用标签",
    "ARCHIVE_ITEM_TAG_TABLE": "档案条目-标签关联表；空串表示未启用",
    "ORDER_CART_TABLE": "购物车表名；空串表示未启用订单",
    "ORDER_TABLE": "订单主表名",
    "ORDER_LINE_TABLE": "订单明细表名",
    "SLOT_TABLE": "可预约时段表名",
    "RESERVATION_TABLE": "预约记录表名",
    "LOOKUP_SITE_TABLE": "下拉主数据：楼栋 / 站点表",
    "LOOKUP_UNIT_TABLE": "下拉主数据：房间 / 单元表",
    "LOOKUP_TYPE_TABLE": "下拉主数据：类型表",
    "LOOKUP_SITE_LABEL": "楼栋 / 站点列展示名",
    "LOOKUP_UNIT_LABEL": "房间 / 单元列展示名",
    "LOOKUP_UNIT_CAPACITY_LABEL": "单元容量列展示名；空串表示隐藏该列",
    "LOOKUP_TYPE_LABEL": "类型列展示名",
    "STOCK_WARN_BELOW": "库存预警阈值（件）",
    "POINTS_EARN_PER_YUAN": "每消费一元赠送的积分",
    "CANCEL_FREE_HOURS": "预约开始前可免费取消的时限（小时）；0 表示不限制",
    "RESCHEDULE_MAX_TIMES": "预约改约次数上限；0 表示不限制",
    "REMIND_AHEAD_MINUTES": "预约开始前站内信提醒（分钟）；0 表示关闭",
    "NO_SHOW_LIMIT": "爽约次数上限；0 表示不限制",
    "LATE_GRACE_MINUTES": "签到迟到宽限（分钟）",
    "HOSPITAL_CANCEL_CUTOFF_MINUTES": "挂号退号截止（开诊前分钟）；0 表示不额外限制",
    "HOSPITAL_ID_LIMIT_PER_DAY": "同就诊人每日限号；0 表示不限制",
    "PARKING_HOURLY_YUAN": "车位小时费率（元）；0 表示未启用时长计费",
    "PARKING_OVERTIME_YUAN": "车位超时加收默认金额（元）；0 表示未启用",
    "MEETING_MIN_DURATION_MINUTES": "会议室最低预约时长（分钟）；0 表示不限制",
    "SALON_RESCHEDULE_FEE_YUAN": "美业改约手续费默认金额（元）；0 表示未启用",
    "HOTEL_LATE_CHECKOUT_FEE_YUAN": "客房延迟退房加收默认金额（元）；0 表示未启用",
    "CARRENT_MILEAGE_OVER_FEE_YUAN": "租车里程超支加收默认金额（元）；0 表示未启用",
    "INSTRUMENT_OVERTIME_YUAN": "仪器机时超时加收默认金额（元）；0 表示未启用",
    "SLOT_REQUIRE_REMARK": "预约须填写备注",
    "SLOT_REQUIRE_CONFIRM": "预约须管理端确认",
    "SLOT_ALLOW_RATING": "办结后允许用户评价",
    "RESERVE_BLACKLIST_ENABLED": "预约黑名单与申诉",
    "HOSPITAL_WAITLIST_ENABLED": "号源满时可候补",
    "PATIENT_PROFILE_ENABLED": "就诊人多档案",
    "PARKING_PASS_ENABLED": "停车次卡",
    "MEETING_MINUTES_REQUIRED": "会议结束后须上传纪要附件",
    "HOTEL_NOTICE_REQUIRED": "客房预约须勾选入住须知",
    "INSTRUMENT_TRAINING_REQUIRED": "仪器机时预约须勾选培训合格",

    "ARCHIVE_SOFT_DELETE": "档案软删除（标记删除，不物理抹掉）",
    "ARCHIVE_USER_PUBLISH": "允许用户自行发布档案内容",
    "ARCHIVE_PUBLISH_REVIEW": "用户发布需审核后上架",
    "ARCHIVE_LOG_ENABLED": "档案变更日志",
    "SHOP_MARKETPLACE": "店铺入驻 / 多商家市集",
    "STOCK_WARN_NOTIFY": "库存低于阈值时提醒",
    "STOCK_IO_ENABLED": "进销存流水",
    "WALLET_ENABLED": "钱包余额",
    "POINTS_ENABLED": "积分账户",
    "POINTS_PAY_ENABLED": "积分直接抵付",
    "ORDER_REVIEW_ENABLED": "订单评价",
    "FAVORITES_ENABLED": "收藏",
    "MATERIAL_CHECK_ENABLED": "物资核对",
    "OCCUPY_SPAN_ENABLED": "占用时段登记",
    "SEAT_SELECT_ENABLED": "在线选座",
    "PARCEL_SHELF_ENABLED": "包裹上架",
    "CLAIM_PROOF_ENABLED": "领取凭证",
    "LOST_CLUE_ENABLED": "失物线索",
    "POST_MUTE_ENABLED": "帖子禁言",
    "CONTENT_REPORT_ENABLED": "内容举报",
    "DM_SHOP_CS": "私信走店铺客服（买家只能选商家）",
    "E_SIGN_ENABLED": "本地签章",
    "EXAM_ENABLED": "在线考试",
    "DOCLIB_ENABLED": "文档库",
    "SURVEY_ENABLED": "问卷",
    "VOTE_ENABLED": "投票",
    "TIMEBANK_ENABLED": "时间银行",
    "TIMEBANK_REDEEM_ON_APPROVE": "审核通过时兑入时间币",
    "GRADE_SCORES_ENABLED": "成绩分数",
    "BALANCE_LEDGER_ENABLED": "余额流水账",
    "BALANCE_LEDGER_DEBIT_ON_APPROVE": "审核通过时扣减余额",
}

GROUP_TITLES: dict[str, str] = {
    "table": "档案 / 订单 / 预约表位",
    "label": "下拉展示标签",
    "numeric": "数值阈值",
    "flag": "能力开关（按开题启用）",
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
    """渲染 AppPolicy.java（未给出的常量回落到类内默认值）。"""
    given = dict(values or {})
    lines = [
        f"package {POLICY_PACKAGE};",
        "",
        "/**",
        " * 非单据业务规则与功能开关（档案表位、下拉主数据、订单/预约表、能力岛）。",
        " * <p>按本系统开题口径生成；单据相关常量见 {@link TicketPolicy}，两处不要互相搬键。</p>",
        " * <p>需要调整业务口径时改这里的常量即可。</p>",
        " */",
        f"public final class {POLICY_CLASS} {{",
        "",
        f"    private {POLICY_CLASS}() {{}}",
    ]
    for group in ("table", "label", "numeric", "flag"):
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
    """把本项目的非单据策略写成 Java 类；骨架缺目录时跳过（非 Java 交付）。

    路径跟当前学生包根走（remap 后的 ``com.campus.*``），禁止写死 thesis 导致填岛同步空写。
    """
    from app.bake.java_package import java_package_of_file, resolve_student_config_java

    dest_p = Path(dest)
    path = resolve_student_config_java(dest_p, POLICY_CLASS)
    if path is None:
        return None
    pkg = java_package_of_file(dest_p, path)
    text = render(collect(domain, spec))
    if pkg != POLICY_PACKAGE:
        text = text.replace(f"package {POLICY_PACKAGE};", f"package {pkg};", 1)
    path.write_text(text, encoding="utf-8")
    return path


def policy_preview(domain: str, spec: dict[str, Any]) -> str:
    """把生成的策略按旧 yml 键值形式回显（仅门禁/用例核对，不参与交付）。

    只回显本轮 collect 实际写出的键（与旧 yml「未命中不写」一致），避免假开关污染断言。
    """
    values = collect(domain, spec)
    lines = []
    for key, const, jtype, _default, _field, _grp in all_fields():
        if const not in values:
            continue
        lines.append(f"  {key}: {_literal(jtype, values[const]).strip('\"')}")
    return "\n".join(lines) + "\n"
