"""预约组加厚（§1.7）：时段占坑壳上的通识钉齐与域皮。

R-00：脚手架（RESERVE_DOMAINS + 注册点）。
R-01：取消时限 / 改约上限 / 提前提醒 / 爽约限制 / 成功信 /
      签到迟到 / 维护禁约 / 候补转正信 / 日历着色 / 管理员备注 / 黑名单申诉。
R-02：HOSPITAL 域皮——报到口令 / 分时段余量 / 就诊人多档案 / 队列号 /
      候补 / 退号 / 初复诊 / 科室介绍 / 停诊通知与日历 / 排队预估 /
      黄牛限号 / 复诊优先说明 / 检验分槽。
R-03：PARKING 域皮——超时加收 / 套餐次卡 / 通行证提示 / 时长计费 /
      取消罚则文案 / 拼单说明 / overlapping 说明（ETC 归 R-07）。
R-04：MEETING 域皮——纪要附件 / 签到导出 / 冲突文案 / 录屏与视频链接 /
      周重复 / 需审批 / 茶水设备勾选 / 黑名单复用 / 门禁密码手发 /
      签到码 / 最低时长 / 召开中状态。
R-05：SALON 域皮——报到口令叠 / 时长占坑 / 队列号 / 改约手续费 /
      迟到宽限文案 / 禁忌备注 / 到店扫码 / 到店次数。
      （储值→wallet 扫词；作品集→gallery 扫词；禁止域默认硬挂）
R-06：HOTEL 域皮——续住延期 / 延迟退房加收 / 身份证脱敏 / 定金尾款 /
      连住说明 / 早餐券 / 入住须知 / 加床 / 钟点房 / 超时转全日说明 /
      同住人数 / 查房清单（浅字段，禁止硬挂 material_check）。
R-07：CARRENT 域皮——违章预留押说明 / 验车单勾选 / 里程超支加收 /
      取还点导航外链 / 保险套餐 / 驾照有效期 / 违章附件 / ETC 通行费。
      （验车浅字段，禁止硬挂 material_check；rental_bond 仍扫词，不域默认）
R-08：INSTRUMENT 域皮——超时计费登记 / 培训合格勾选 / 冲突可视化 /
      实验目的必填 / 耗材领用浅登记 / 导师同意（轻审） / 机时费导出。
      （培训浅字段，禁止硬挂 material_check；≠实验室门禁/硬件）
R-09：能力岛加深——仅当已挂对应 cap：
      staff_roster（医院值班展示 / 美业请假挡班）、
      lesson_pack（余次展示 / 到期站内信）、
      wallet / gallery（美业储值与作品集文案）、
      room_equipment（会议录制设备借用勾选）。
      禁止因「预约常见」域默认硬挂上述 cap。

硬约束
------
- 只挂 RESERVE_DOMAINS；不写 SHOP/FOOD/CINEMA（§1.6）。
- Store 主战场 SlotStore；禁止第二套预约状态机。
- 提醒走同一 DemoScheduleJobs，禁止第二套调度框架。
- 黑名单为轻名单表 + 申诉，≠风控引擎。
- R-02 仅 DOM-HOSPITAL；SALON 报到/队列归 R-05；排班只读归 R-09 staff_roster。
- R-03 仅 DOM-PARKING；≠道闸硬件；租车 ETC 归 R-07。
- R-04 仅 DOM-MEETING；门禁密码手发≠硬件短信；录制设备叠 room_equipment 归 R-09。
- R-05 仅 DOM-SALON；禁止域默认硬挂 wallet/gallery；会员卡余次 lesson_pack 扫词。
- R-06 仅 DOM-HOTEL；查房清单浅字段，禁止硬挂 material_check；≠OTA/门锁/公安网。
- R-07 仅 DOM-CARRENT；验车浅字段，禁止硬挂 material_check；禁止域默认 rental_bond；≠保司/ETC 硬件。
- R-08 仅 DOM-INSTRUMENT；培训浅字段，禁止硬挂 material_check；导师同意=轻审 requireConfirm；≠门禁硬件。
- R-09 仅 cap 已挂时加深；未挂无菜单/无按钮/无 thicken 旗。
"""

from __future__ import annotations

from typing import Any

RESERVE_DOMAINS = frozenset(
    {
        "DOM-HOSPITAL",
        "DOM-PARKING",
        "DOM-MEETING",
        "DOM-SALON",
        "DOM-HOTEL",
        "DOM-CARRENT",
        "DOM-INSTRUMENT",
    }
)

# 通识默认：开始前 N 小时可免费取消；改约上限；提前提醒分钟；爽约再约上限；迟到宽限分钟
_CANCEL_FREE_HOURS_DEFAULT = 2
_RESCHEDULE_MAX_DEFAULT = 2
_REMIND_AHEAD_MINUTES_DEFAULT = 60
_NO_SHOW_LIMIT_DEFAULT = 3
_LATE_GRACE_MINUTES_DEFAULT = 15
# HOSPITAL：开诊前可退号分钟；同就诊人同科室同日限号
_HOSPITAL_CANCEL_CUTOFF_DEFAULT = 30
_HOSPITAL_ID_LIMIT_DEFAULT = 2
# PARKING：小时费 / 超时加收演示默认（元）
_PARKING_HOURLY_DEFAULT = 5
_PARKING_OVERTIME_DEFAULT = 10
# MEETING：最低预约时长（分钟）
_MEETING_MIN_DURATION_DEFAULT = 60
# SALON：项目默认时长 / 改约手续费（元）
_SALON_SERVICE_MINUTES_DEFAULT = 60
_SALON_RESCHEDULE_FEE_DEFAULT = 20
# HOTEL：延迟退房加收默认（元）
_HOTEL_LATE_CHECKOUT_FEE_DEFAULT = 50
# CARRENT：里程超支加收默认（元）
_CARRENT_MILEAGE_OVER_FEE_DEFAULT = 50
# INSTRUMENT：机时超时加收默认（元）
_INSTRUMENT_OVERTIME_DEFAULT = 20


def _live_schema(spec: dict[str, Any]) -> dict[str, Any]:
    schema = spec.get("schema")
    if not isinstance(schema, dict):
        schema = {}
        spec["schema"] = schema
    return schema


def _ensure_archive_field(archive: dict[str, Any], field: dict[str, Any]) -> None:
    fields = archive.get("fields")
    if not isinstance(fields, list):
        fields = []
        archive["fields"] = fields
    key = str(field.get("key") or "")
    if not key:
        return
    for f in fields:
        if isinstance(f, dict) and f.get("key") == key:
            return
    fields.append(field)


def _add_feature(spec: dict[str, Any], name: str) -> None:
    feats = spec.get("features")
    if not isinstance(feats, list):
        feats = []
        spec["features"] = feats
    if name not in feats:
        feats.append(name)


def _attach_reserve_blacklist_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    admin = schema.setdefault("menus", {}).setdefault("admin", [])
    user = schema.setdefault("menus", {}).setdefault("user", [])
    labels = schema.setdefault("labels", {})
    ensure_menu(
        admin,
        "reserve_blacklist",
        {
            "key": "reserve_blacklist",
            "label": labels.get("reserveBlacklistMenuLabel") or "预约黑名单",
            "superOnly": True,
        },
        before_key="content",
    )
    ensure_menu(
        user,
        "reserve_blacklist_appeal",
        {
            "key": "reserve_blacklist_appeal",
            "label": labels.get("reserveBlacklistAppealMenuLabel") or "黑名单申诉",
        },
        before_key="content",
    )


_RESERVE_THICKEN_RESV_COLS: list[tuple[str, str]] = [
    ("reschedule_count", "INT NOT NULL DEFAULT 0"),
    ("remind_sent", "TINYINT NOT NULL DEFAULT 0"),
    ("no_show", "TINYINT NOT NULL DEFAULT 0"),
    ("late_flag", "TINYINT NOT NULL DEFAULT 0"),
    ("checked_in_at", "DATETIME NULL"),
]

_RESERVE_THICKEN_ARCHIVE_COLS: list[tuple[str, str]] = [
    ("maintain_from", "DATE NULL"),
    ("maintain_to", "DATE NULL"),
    ("admin_note", "VARCHAR(255) NOT NULL DEFAULT ''"),
]

_HOSPITAL_ARCHIVE_COLS: list[tuple[str, str]] = [
    ("checkin_code", "VARCHAR(32) NOT NULL DEFAULT ''"),
    ("dept_intro", "VARCHAR(512) NOT NULL DEFAULT ''"),
    ("slot_kind", "VARCHAR(16) NOT NULL DEFAULT 'clinic'"),
    ("queue_estimate_hint", "VARCHAR(255) NOT NULL DEFAULT ''"),
]

_PARKING_RESV_COLS: list[tuple[str, str]] = [
    ("exit_at", "DATETIME NULL"),
    ("overtime_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("duration_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("parking_pass_used", "TINYINT NOT NULL DEFAULT 0"),
]

_PARKING_ARCHIVE_COLS: list[tuple[str, str]] = [
    ("pass_hint", "VARCHAR(255) NOT NULL DEFAULT ''"),
]

_MEETING_RESV_COLS: list[tuple[str, str]] = [
    ("recording_url", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("video_url", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("door_code", "VARCHAR(32) NOT NULL DEFAULT ''"),
    ("service_tea", "TINYINT NOT NULL DEFAULT 0"),
    ("service_device", "TINYINT NOT NULL DEFAULT 0"),
    ("equip_borrow", "TINYINT NOT NULL DEFAULT 0"),
    ("minutes_attach", "VARCHAR(512) NOT NULL DEFAULT ''"),
    ("meeting_stage", "VARCHAR(16) NOT NULL DEFAULT ''"),
    ("checkin_token", "VARCHAR(32) NOT NULL DEFAULT ''"),
]

_MEETING_ARCHIVE_COLS: list[tuple[str, str]] = [
    ("min_duration_minutes", "INT NOT NULL DEFAULT 60"),
]

_SALON_RESV_COLS: list[tuple[str, str]] = [
    ("reschedule_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("checkin_token", "VARCHAR(32) NOT NULL DEFAULT ''"),
]

_SALON_ARCHIVE_COLS: list[tuple[str, str]] = [
    ("checkin_code", "VARCHAR(32) NOT NULL DEFAULT ''"),
    ("service_minutes", "INT NOT NULL DEFAULT 60"),
    ("taboo_note", "VARCHAR(255) NOT NULL DEFAULT ''"),
]

_HOTEL_RESV_COLS: list[tuple[str, str]] = [
    ("stay_from", "DATE NULL"),
    ("stay_to", "DATE NULL"),
    ("id_no", "VARCHAR(32) NOT NULL DEFAULT ''"),
    ("deposit_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("balance_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("breakfast_vouchers", "INT NOT NULL DEFAULT 0"),
    ("notice_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("extra_bed", "TINYINT NOT NULL DEFAULT 0"),
    ("late_checkout_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("checkout_checklist", "VARCHAR(512) NOT NULL DEFAULT ''"),
]

_HOTEL_ARCHIVE_COLS: list[tuple[str, str]] = [
    ("room_kind", "VARCHAR(16) NOT NULL DEFAULT 'full'"),
]

_CARRENT_RESV_COLS: list[tuple[str, str]] = [
    ("violation_hold_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("violation_hold_note", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("inspect_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("mileage_over_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("insurance_pkg", "VARCHAR(32) NOT NULL DEFAULT ''"),
    ("license_expire_on", "DATE NULL"),
    ("violation_attach", "VARCHAR(512) NOT NULL DEFAULT ''"),
    ("etc_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
]

_CARRENT_ARCHIVE_COLS: list[tuple[str, str]] = [
    ("pickup_nav_url", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("return_nav_url", "VARCHAR(255) NOT NULL DEFAULT ''"),
]

_INSTRUMENT_RESV_COLS: list[tuple[str, str]] = [
    ("overtime_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("training_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("consumable_note", "VARCHAR(512) NOT NULL DEFAULT ''"),
]

_PARKING_PASS_DDL = """
CREATE TABLE IF NOT EXISTS parking_pass (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  pack_name VARCHAR(64) NOT NULL DEFAULT '包月次卡',
  remain_count INT NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_parking_pass_user (username)
);
"""

_PATIENT_PROFILE_DDL = """
CREATE TABLE IF NOT EXISTS patient_profile (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  patient_name VARCHAR(32) NOT NULL,
  relation_label VARCHAR(16) NOT NULL DEFAULT '本人',
  id_hint VARCHAR(32) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_patient_profile_user (username)
);
"""

_RESERVE_BLACKLIST_DDL = """
CREATE TABLE IF NOT EXISTS reserve_blacklist (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  reason VARCHAR(255) DEFAULT '',
  status VARCHAR(32) NOT NULL DEFAULT 'blocked',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_reserve_blacklist_user (username)
);
CREATE TABLE IF NOT EXISTS reserve_blacklist_appeal (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  reason VARCHAR(255) NOT NULL DEFAULT '',
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def ensure_reserve_thicken_sql(
    sql: str,
    *,
    domain: str | None,
    reservation_table: str | None = None,
    item_table: str | None = None,
) -> str:
    """七域预约通识列 + 黑名单/申诉表；非本组原样返回。"""
    import re

    from app.bake.sql.fragments import _CREATE_TABLE_RE, _inject_missing_columns

    if (domain or "") not in RESERVE_DOMAINS:
        return sql

    rt = (reservation_table or "reservation").strip()
    it = (item_table or "").strip()
    resv_ok = bool(rt and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", rt))
    item_ok = bool(it and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", it))
    hospital = (domain or "") == "DOM-HOSPITAL"
    parking = (domain or "") == "DOM-PARKING"
    meeting = (domain or "") == "DOM-MEETING"
    salon = (domain or "") == "DOM-SALON"
    hotel = (domain or "") == "DOM-HOTEL"
    carrent = (domain or "") == "DOM-CARRENT"
    instrument = (domain or "") == "DOM-INSTRUMENT"

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        tl = table.lower()
        if resv_ok and tl == rt.lower():
            cols = list(_RESERVE_THICKEN_RESV_COLS)
            if parking:
                cols.extend(_PARKING_RESV_COLS)
            if meeting:
                cols.extend(_MEETING_RESV_COLS)
            if salon:
                cols.extend(_SALON_RESV_COLS)
            if hotel:
                cols.extend(_HOTEL_RESV_COLS)
            if carrent:
                cols.extend(_CARRENT_RESV_COLS)
            if instrument:
                cols.extend(_INSTRUMENT_RESV_COLS)
            body = _inject_missing_columns(body, cols)
        if item_ok and tl == it.lower():
            cols = list(_RESERVE_THICKEN_ARCHIVE_COLS)
            if hospital:
                cols.extend(_HOSPITAL_ARCHIVE_COLS)
            if parking:
                cols.extend(_PARKING_ARCHIVE_COLS)
            if meeting:
                cols.extend(_MEETING_ARCHIVE_COLS)
            if salon:
                cols.extend(_SALON_ARCHIVE_COLS)
            if hotel:
                cols.extend(_HOTEL_ARCHIVE_COLS)
            if carrent:
                cols.extend(_CARRENT_ARCHIVE_COLS)
            body = _inject_missing_columns(body, cols)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if not re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?reserve_blacklist`?\b", out
    ):
        out = out.rstrip() + "\n" + _RESERVE_BLACKLIST_DDL
    if hospital and not re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?patient_profile`?\b", out
    ):
        out = out.rstrip() + "\n" + _PATIENT_PROFILE_DDL
    if parking and not re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?parking_pass`?\b", out
    ):
        out = out.rstrip() + "\n" + _PARKING_PASS_DDL
    return out


def apply_reserve_thicken_to_spec(
    spec: dict[str, Any], proposal_text: str = ""
) -> dict[str, Any]:
    """按域默认加厚预约组 schema（只增不减；非本组原样返回）。"""
    del proposal_text  # 通识/域皮不扫词；R-09 读已合并的 capabilities
    domain = str(spec.get("domain") or "")
    if domain not in RESERVE_DOMAINS:
        return spec
    caps = list(spec.get("capabilities") or [])
    if "slot_reserve" not in caps:
        return spec

    schema = _live_schema(spec)
    labels = schema.setdefault("labels", {})
    ents = schema.setdefault("entities", {})
    resv_ent = ents.get("reservation") if isinstance(ents.get("reservation"), dict) else {}
    if not isinstance(resv_ent, dict):
        resv_ent = {}
        ents["reservation"] = resv_ent
    archive = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
    if not isinstance(archive, dict):
        archive = {}
        ents["archive"] = archive
    thicken = schema.get("reserveThicken") if isinstance(schema.get("reserveThicken"), dict) else {}
    schema["reserveThicken"] = thicken
    resv_ent["reserveThicken"] = True
    thicken["core"] = True

    # —— 取消时限 ——
    if not int(schema.get("cancelFreeHours") or 0):
        schema["cancelFreeHours"] = _CANCEL_FREE_HOURS_DEFAULT
    labels.setdefault("cancelFreeHoursLabel", "免费取消时限（小时）")
    labels.setdefault(
        "cancelFreeHoursHint",
        "开始前至少还有这么多小时时可自行取消；过时请联系管理员。",
    )
    thicken["cancelFreeHours"] = True
    _add_feature(spec, "取消预约时限")

    # —— 改约上限 ——
    if not int(schema.get("rescheduleMaxTimes") or 0):
        schema["rescheduleMaxTimes"] = _RESCHEDULE_MAX_DEFAULT
    labels.setdefault("rescheduleMaxLabel", "改约次数上限")
    labels.setdefault(
        "rescheduleMaxHint",
        "每条预约最多可改约这么多次；超额请重新预约或联系管理员。",
    )
    thicken["rescheduleMax"] = True
    _add_feature(spec, "改约次数上限")

    # —— 提前提醒 ——
    if not int(schema.get("remindAheadMinutes") or 0):
        schema["remindAheadMinutes"] = _REMIND_AHEAD_MINUTES_DEFAULT
    labels.setdefault("remindAheadLabel", "开始前提醒（分钟）")
    labels.setdefault(
        "remindAheadHint",
        "预约开始前将收到站内提醒，请留意消息中心。",
    )
    thicken["remindAhead"] = True
    _add_feature(spec, "预约开始前提醒")

    # —— 爽约限制 ——
    if not int(schema.get("noShowLimit") or 0):
        schema["noShowLimit"] = _NO_SHOW_LIMIT_DEFAULT
    labels.setdefault("noShowLimitLabel", "爽约次数上限")
    labels.setdefault(
        "noShowLimitHint",
        "累计爽约达到上限后将暂时无法再约，可提交申诉。",
    )
    labels.setdefault("noShowDenyMessage", "因多次爽约，暂时无法预约，请先提交申诉。")
    thicken["noShowLimit"] = True
    _add_feature(spec, "爽约次数限制再约")

    # —— 成功站内信 ——
    labels.setdefault("reserveSuccessTitle", "预约成功")
    labels.setdefault(
        "reserveSuccessBody",
        "您的预约已确认，请按时到场；如需取消请留意免费取消时限。",
    )
    labels.setdefault("reservePendingTitle", "预约已提交")
    labels.setdefault(
        "reservePendingBody",
        "已提交预约，请等待确认。",
    )
    thicken["successMessage"] = True
    _add_feature(spec, "预约成功站内信")

    # —— 签到迟到 ——
    if not int(schema.get("lateGraceMinutes") or 0):
        schema["lateGraceMinutes"] = _LATE_GRACE_MINUTES_DEFAULT
    labels.setdefault("lateGraceLabel", "签到宽限（分钟）")
    labels.setdefault(
        "lateGraceHint",
        "超过开始时间这么多分钟再签到，将记为迟到。",
    )
    labels.setdefault("checkInLabel", "签到")
    labels.setdefault("lateFlagLabel", "迟到")
    thicken["lateCheckIn"] = True
    _add_feature(spec, "预约签到迟到标记")

    # —— 维护禁约 ——
    labels.setdefault("maintainFromLabel", "维护开始日")
    labels.setdefault("maintainToLabel", "维护结束日")
    labels.setdefault(
        "maintainBlockHint",
        "该资源在维护期内暂不可约，请换一天或其它资源。",
    )
    _ensure_archive_field(
        archive,
        {"key": "maintainFrom", "label": "维护开始日", "type": "date"},
    )
    _ensure_archive_field(
        archive,
        {"key": "maintainTo", "label": "维护结束日", "type": "date"},
    )
    thicken["maintainBlock"] = True
    _add_feature(spec, "资源维护时段禁约")

    # —— 候补转正信 ——
    labels.setdefault("waitlistPromoteTitle", "候补已转正")
    labels.setdefault(
        "waitlistPromoteBody",
        "您的候补预约已转为正式预约，请按时到场。",
    )
    thicken["waitlistPromote"] = True
    _add_feature(spec, "候补转正站内信")

    # —— 日历着色 ——
    labels.setdefault("slotCalendarLegendOk", "余量充足")
    labels.setdefault("slotCalendarLegendWarn", "余量紧张")
    labels.setdefault("slotCalendarLegendFull", "已约满")
    thicken["calendarTone"] = True
    _add_feature(spec, "容量日历着色")

    # —— 管理员备注（用户不可见） ——
    labels.setdefault("adminNoteLabel", "内部备注")
    labels.setdefault(
        "adminNoteHint",
        "仅管理端可见，不对用户展示。",
    )
    _ensure_archive_field(
        archive,
        {"key": "adminNote", "label": "内部备注", "type": "string", "adminOnly": True},
    )
    thicken["adminNote"] = True
    _add_feature(spec, "资源管理员备注")

    # —— 黑名单 + 申诉 ——
    schema["reserveBlacklist"] = True
    labels.setdefault("reserveBlacklistMenuLabel", "预约黑名单")
    labels.setdefault("reserveBlacklistTitle", "预约黑名单")
    labels.setdefault(
        "reserveBlacklistLead",
        "维护禁止预约的账号；名单内用户提交预约时将被拒绝。",
    )
    labels.setdefault(
        "reserveBlacklistDenyMessage",
        "当前账号暂不可预约，可提交申诉或联系管理员。",
    )
    labels.setdefault("reserveBlacklistAppealMenuLabel", "黑名单申诉")
    labels.setdefault("reserveBlacklistAppealTitle", "黑名单申诉")
    labels.setdefault(
        "reserveBlacklistAppealLead",
        "若被限制预约，可在此说明情况并提交申诉。",
    )
    labels.setdefault("reserveBlacklistAppealReasonLabel", "申诉说明")
    thicken["blacklist"] = True
    thicken["blacklistAppeal"] = True
    _attach_reserve_blacklist_menus(schema)
    _add_feature(spec, "预约黑名单申诉")

    if domain == "DOM-HOSPITAL":
        _apply_hospital_r02(spec, schema, labels, resv_ent, archive, thicken)
    if domain == "DOM-PARKING":
        _apply_parking_r03(spec, schema, labels, archive, thicken)
    if domain == "DOM-MEETING":
        _apply_meeting_r04(spec, schema, labels, resv_ent, archive, thicken)
    if domain == "DOM-SALON":
        _apply_salon_r05(spec, schema, labels, resv_ent, archive, thicken)
    if domain == "DOM-HOTEL":
        _apply_hotel_r06(spec, schema, labels, resv_ent, archive, thicken)
    if domain == "DOM-CARRENT":
        _apply_carrent_r07(spec, schema, labels, resv_ent, archive, thicken)
    if domain == "DOM-INSTRUMENT":
        _apply_instrument_r08(spec, schema, labels, resv_ent, thicken)

    _apply_r09_cap_islands(spec, schema, labels, thicken, set(caps), domain)

    ents["reservation"] = resv_ent
    ents["archive"] = archive
    schema["reserveThicken"] = thicken
    return spec


def _apply_hospital_r02(
    spec: dict[str, Any],
    schema: dict[str, Any],
    labels: dict[str, Any],
    resv_ent: dict[str, Any],
    archive: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """R-02：挂号域皮（仅 HOSPITAL）。"""
    # 报到口令
    labels.setdefault("checkinCodeLabel", "报到口令")
    labels.setdefault(
        "checkinCodeHint",
        "到院后输入科室口令完成报到；与线上签到一致。",
    )
    labels.setdefault("checkinCodeAdminHint", "管理端为科室维护报到口令，用户签到时核对。")
    _ensure_archive_field(
        archive, {"key": "checkinCode", "label": "报到口令", "type": "string"}
    )
    thicken["hospitalCheckinCode"] = True
    _add_feature(spec, "报到签到口令")

    # 分时段余量
    labels.setdefault("slotPeriodMorningLabel", "上午")
    labels.setdefault("slotPeriodAfternoonLabel", "下午")
    labels.setdefault("slotPeriodRemainHint", "本时段余号")
    thicken["hospitalPeriodRemain"] = True
    _add_feature(spec, "号源分时段余量")

    # 就诊人多档案
    schema["patientProfile"] = True
    labels.setdefault("patientProfileMenuLabel", "就诊人")
    labels.setdefault("patientProfileTitle", "我的就诊人")
    labels.setdefault(
        "patientProfileLead",
        "可维护本人与家属就诊人，预约时直接选用。",
    )
    labels.setdefault("patientProfileNameLabel", "就诊人姓名")
    labels.setdefault("patientProfileRelationLabel", "关系")
    labels.setdefault("patientProfileIdHintLabel", "证件后四位")
    thicken["hospitalPatientProfile"] = True
    _attach_patient_profile_menu(schema)
    _add_feature(spec, "就诊人多档案")

    # 队列号钉齐
    labels.setdefault("queueNoLabel", "候诊号")
    labels.setdefault("queueNoHint", "确认预约后生成，到院按号候诊。")
    thicken["hospitalQueueNo"] = True
    _add_feature(spec, "候诊队列序号")

    # 候补
    resv_ent["allowWaitlist"] = True
    schema["hospitalWaitlist"] = True
    labels.setdefault(
        "hospitalWaitlistHint",
        "号源已满时可加入候补，有空位将按顺序转正并通知您。",
    )
    thicken["hospitalWaitlist"] = True
    _add_feature(spec, "号源候补队列")

    # 退号：开诊前 N 分钟
    if not int(schema.get("hospitalCancelCutoffMinutes") or 0):
        schema["hospitalCancelCutoffMinutes"] = _HOSPITAL_CANCEL_CUTOFF_DEFAULT
    labels.setdefault("hospitalCancelCutoffLabel", "退号截止（开诊前分钟）")
    labels.setdefault(
        "hospitalCancelCutoffHint",
        "开诊前不足该分钟数不可自行退号，请联系窗口。",
    )
    thicken["hospitalCancelCutoff"] = True
    _add_feature(spec, "挂号退号规则")

    # 初诊/复诊
    resv_ent["visitTypeLabel"] = resv_ent.get("visitTypeLabel") or "初诊/复诊"
    if not isinstance(resv_ent.get("visitTypeOptions"), list) or not resv_ent.get(
        "visitTypeOptions"
    ):
        resv_ent["visitTypeOptions"] = [
            {"label": "初诊", "value": "初诊"},
            {"label": "复诊", "value": "复诊"},
        ]
    resv_ent["visitTypeDefault"] = resv_ent.get("visitTypeDefault") or "初诊"
    labels.setdefault("visitTypeLabel", "初诊/复诊")
    labels.setdefault("visitTypeHint", "请按实际就诊情况选择。")
    thicken["hospitalVisitType"] = True
    _add_feature(spec, "初诊复诊选项")

    # 科室介绍
    labels.setdefault("deptIntroLabel", "科室介绍")
    labels.setdefault("deptIntroHint", "科室简介，预约页只读展示。")
    _ensure_archive_field(
        archive, {"key": "deptIntro", "label": "科室介绍", "type": "textarea"}
    )
    thicken["hospitalDeptIntro"] = True
    _add_feature(spec, "科室介绍只读")

    # 停诊通知 + 日历（复用 maintain_*，加深文案与发信）
    labels.setdefault(
        "hospitalStopNotifyTitle",
        "科室停诊通知",
    )
    labels.setdefault(
        "hospitalStopNotifyBody",
        "您预约的科室已安排停诊，原预约已取消，请改约其它时段。",
    )
    labels.setdefault("hospitalStopCalendarHint", "维护期内不可约，见科室停诊日历。")
    thicken["hospitalStopNotify"] = True
    thicken["hospitalStopCalendar"] = True
    _add_feature(spec, "停诊通知与日历")

    # 排队预估
    labels.setdefault(
        "queueEstimateHint",
        "当前候诊号约需等待，请留意叫号（演示预估，非现场叫号）。",
    )
    labels.setdefault("queueEstimateLabel", "排队预估")
    _ensure_archive_field(
        archive,
        {"key": "queueEstimateHint", "label": "排队预估文案", "type": "string"},
    )
    thicken["hospitalQueueEstimate"] = True
    _add_feature(spec, "科室排队预估")

    # 黄牛限号
    if not int(schema.get("hospitalIdLimitPerDay") or 0):
        schema["hospitalIdLimitPerDay"] = _HOSPITAL_ID_LIMIT_DEFAULT
    labels.setdefault("hospitalIdLimitLabel", "同就诊人日限号")
    labels.setdefault(
        "hospitalIdLimitHint",
        "同一就诊人同一天在本科室最多可约这么多次，防止占用号源。",
    )
    thicken["hospitalIdLimit"] = True
    _add_feature(spec, "同证件限号")

    # 复诊优先说明
    labels.setdefault(
        "revisitPriorityHint",
        "复诊可优先选择靠前时段（演示说明，不改变号源算法）。",
    )
    thicken["hospitalRevisitPriority"] = True
    _add_feature(spec, "复诊优先说明")

    # 检验分槽
    labels.setdefault("slotKindLabel", "号源类型")
    labels.setdefault("slotKindClinic", "门诊")
    labels.setdefault("slotKindLab", "检验检查")
    labels.setdefault("slotKindHint", "门诊与检验分槽预约，互不影响。")
    _ensure_archive_field(
        archive,
        {
            "key": "slotKind",
            "label": "号源类型",
            "type": "select",
            "options": [
                {"label": "门诊", "value": "clinic"},
                {"label": "检验检查", "value": "lab"},
            ],
        },
    )
    thicken["hospitalSlotKind"] = True
    _add_feature(spec, "检验检查分槽")


def _attach_patient_profile_menu(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    user = schema.setdefault("menus", {}).setdefault("user", [])
    labels = schema.setdefault("labels", {})
    ensure_menu(
        user,
        "patient_profile",
        {
            "key": "patient_profile",
            "label": labels.get("patientProfileMenuLabel") or "就诊人",
        },
        before_key="content",
    )


def _apply_parking_r03(
    spec: dict[str, Any],
    schema: dict[str, Any],
    labels: dict[str, Any],
    archive: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """R-03：车位域皮（仅 PARKING）。"""
    if not int(schema.get("parkingHourlyYuan") or 0):
        schema["parkingHourlyYuan"] = _PARKING_HOURLY_DEFAULT
    if not int(schema.get("parkingOvertimeYuan") or 0):
        schema["parkingOvertimeYuan"] = _PARKING_OVERTIME_DEFAULT

    # 超时占用加收
    labels.setdefault("parkingOvertimeLabel", "超时加收")
    labels.setdefault(
        "parkingOvertimeHint",
        "超过预约结束时间仍占用车位时，管理端可登记加收费用（演示，非地感计费）。",
    )
    thicken["parkingOvertime"] = True
    _add_feature(spec, "车位超时加收")

    # 套餐次卡
    schema["parkingPass"] = True
    labels.setdefault("parkingPassMenuLabel", "停车次卡")
    labels.setdefault("parkingPassTitle", "我的停车次卡")
    labels.setdefault(
        "parkingPassLead",
        "包月次卡剩余次数；预约成功将自动扣减一次（有余次时）。",
    )
    labels.setdefault("parkingPassRemainHint", "次卡余次")
    labels.setdefault("parkingPassPackLabel", "套餐名称")
    labels.setdefault("parkingPassRemainLabel", "剩余次数")
    labels.setdefault("parkingPassGrantLabel", "发放次卡")
    thicken["parkingPass"] = True
    _attach_parking_pass_menu(schema)
    _add_feature(spec, "车位套餐次卡")

    # 通行证提示（管理可改档案）
    labels.setdefault("parkingCarpassHint", "访客车请先办理通行证后再入场（演示提示）。")
    labels.setdefault("passHintLabel", "通行证提示")
    labels.setdefault("passHintAdminHint", "管理端可按车位维护通行证说明，预约页展示。")
    _ensure_archive_field(
        archive, {"key": "passHint", "label": "通行证提示", "type": "string"}
    )
    thicken["parkingCarpassHint"] = True
    _add_feature(spec, "车位通行证提示")

    # 时长计费进离场
    labels.setdefault("parkingDurationFeeLabel", "停车时长费")
    labels.setdefault(
        "parkingDurationFeeHint",
        "登记入场与离场后，按小时费率估算时长费用（演示，非地感计费）。",
    )
    labels.setdefault("parkingEntryLabel", "入场时间")
    labels.setdefault("parkingExitLabel", "离场时间")
    labels.setdefault("parkingHourlyLabel", "小时费率（元）")
    thicken["parkingDurationFee"] = True
    _add_feature(spec, "停车时长计费")

    # 取消罚则说明
    labels.setdefault(
        "parkingCancelPenaltyHint",
        "临近开始取消可能记为违约占用，请尽早取消以便他人预约。",
    )
    thicken["parkingCancelPenalty"] = True
    _add_feature(spec, "车位取消罚则说明")

    # 拼单说明
    labels.setdefault(
        "parkingShareSlotHint",
        "同一时段可与他人共用车位说明：请自行协商，系统按号源余量占坑（演示）。",
    )
    thicken["parkingShareSlot"] = True
    _add_feature(spec, "车位共享拼单说明")

    # overlapping 说明
    labels.setdefault(
        "parkingOverlapHint",
        "同一车牌在重叠时段不可重复预约，请改选其它时段。",
    )
    thicken["parkingOverlap"] = True
    _add_feature(spec, "车位时段重叠检测")


def _attach_parking_pass_menu(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    user = schema.setdefault("menus", {}).setdefault("user", [])
    admin = schema.setdefault("menus", {}).setdefault("admin", [])
    labels = schema.setdefault("labels", {})
    ensure_menu(
        user,
        "parking_pass",
        {
            "key": "parking_pass",
            "label": labels.get("parkingPassMenuLabel") or "停车次卡",
        },
        before_key="content",
    )
    ensure_menu(
        admin,
        "parking_pass_admin",
        {
            "key": "parking_pass_admin",
            "label": labels.get("parkingPassGrantLabel") or "发放次卡",
            "superOnly": True,
        },
        before_key="content",
    )


def _apply_meeting_r04(
    spec: dict[str, Any],
    schema: dict[str, Any],
    labels: dict[str, Any],
    resv_ent: dict[str, Any],
    archive: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """R-04：会议室域皮（仅 MEETING）。"""
    # 需审批
    resv_ent["requireConfirm"] = True
    labels.setdefault(
        "meetingRequireConfirmHint",
        "会议室预约提交后需管理员确认方可生效。",
    )
    thicken["meetingRequireConfirm"] = True
    _add_feature(spec, "会议室预约审批")

    # 纪要附件
    schema["meetingMinutesRequired"] = True
    resv_ent["meetingMinutesRequired"] = True
    labels.setdefault("meetingMinutesLabel", "会议纪要附件")
    labels.setdefault(
        "meetingMinutesHint",
        "会议结束后请上传纪要附件，管理端办结时核验。",
    )
    thicken["meetingMinutes"] = True
    _add_feature(spec, "会议纪要附件")

    # 签到导出
    labels.setdefault("meetingCheckinExportLabel", "导出签到表")
    labels.setdefault(
        "meetingCheckinExportHint",
        "按当前筛选导出签到用名单（CSV）。",
    )
    thicken["meetingCheckinExport"] = True
    _add_feature(spec, "会议签到表导出")

    # 冲突文案
    labels.setdefault(
        "meetingConflictHint",
        "该时段可能与他人预约冲突；已约满时请改选其它时段。已约人可在时段详情中查看。",
    )
    thicken["meetingConflict"] = True
    _add_feature(spec, "会议冲突检测说明")

    # 录屏链接
    labels.setdefault("meetingRecordingLabel", "录屏链接")
    labels.setdefault(
        "meetingRecordingHint",
        "可填写外部录屏地址（演示外链，非会议云录制）。",
    )
    thicken["meetingRecording"] = True
    _add_feature(spec, "会议录屏链接")

    # 视频会议链接
    labels.setdefault("meetingVideoLabel", "视频会议链接")
    labels.setdefault(
        "meetingVideoHint",
        "可填写腾讯会议/钉钉等外链，方便参会人加入。",
    )
    thicken["meetingVideo"] = True
    _add_feature(spec, "视频会议链接")

    # 周重复
    labels.setdefault("meetingWeeklyRepeatLabel", "按周重复生成")
    labels.setdefault(
        "meetingWeeklyRepeatHint",
        "按所选星期几连续生成多周号源（浅演示，非日历引擎）。",
    )
    thicken["meetingWeeklyRepeat"] = True
    _add_feature(spec, "会议室周重复预约")

    # 茶水/设备勾选
    labels.setdefault("meetingServiceTeaLabel", "需要茶水")
    labels.setdefault("meetingServiceDeviceLabel", "需要设备支持")
    labels.setdefault(
        "meetingServiceHint",
        "预约时可勾选茶水与设备服务，管理端可见。",
    )
    thicken["meetingService"] = True
    _add_feature(spec, "会议茶水设备勾选")

    # 黑名单：复用 R-01
    labels.setdefault(
        "meetingBlacklistHint",
        "被限制预约的用户无法提交会议室申请，可走黑名单申诉。",
    )
    thicken["meetingBlacklist"] = True
    _add_feature(spec, "场地预约黑名单")

    # 门禁密码手发
    labels.setdefault("meetingDoorCodeLabel", "门禁密码")
    labels.setdefault(
        "meetingDoorCodeHint",
        "管理员确认后手填门禁密码，用户在我的预约中查看（≠门禁硬件短信）。",
    )
    thicken["meetingDoorCode"] = True
    _add_feature(spec, "会议室门禁密码")

    # 签到码 / 二维码展示
    labels.setdefault("meetingCheckinCodeLabel", "签到码")
    labels.setdefault(
        "meetingCheckinCodeHint",
        "确认预约后生成签到码，到场出示（可叠二维码能力）。",
    )
    thicken["meetingCheckinCode"] = True
    _add_feature(spec, "会议签到码")

    # 最低时长
    if not int(schema.get("meetingMinDurationMinutes") or 0):
        schema["meetingMinDurationMinutes"] = _MEETING_MIN_DURATION_DEFAULT
    labels.setdefault("meetingMinDurationLabel", "最低预约时长（分钟）")
    labels.setdefault(
        "meetingMinDurationHint",
        "短于该时长的号源不可约，请选择更长时段。",
    )
    _ensure_archive_field(
        archive,
        {
            "key": "minDurationMinutes",
            "label": "最低预约时长（分钟）",
            "type": "number",
        },
    )
    thicken["meetingMinDuration"] = True
    _add_feature(spec, "会议室最低预约时长")

    # 召开中状态
    labels.setdefault("meetingStageLabel", "会议状态")
    labels.setdefault("meetingStageInProgress", "召开中")
    labels.setdefault("meetingStageEnded", "已结束")
    labels.setdefault(
        "meetingStageHint",
        "管理端可将已确认预约标为召开中，便于现场管理。",
    )
    thicken["meetingStage"] = True
    _add_feature(spec, "会议召开中状态")


def _apply_salon_r05(
    spec: dict[str, Any],
    schema: dict[str, Any],
    labels: dict[str, Any],
    resv_ent: dict[str, Any],
    archive: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """R-05：美业/服务预约域皮（仅 SALON）。"""
    # 报到口令（叠 HOSPITAL 核验路径）
    labels.setdefault("checkinCodeLabel", "到店口令")
    labels.setdefault(
        "checkinCodeHint",
        "到店后输入服务口令完成报到；与线上签到一致。",
    )
    labels.setdefault(
        "checkinCodeAdminHint",
        "管理端为服务项目维护到店口令，顾客签到时核对。",
    )
    _ensure_archive_field(
        archive, {"key": "checkinCode", "label": "到店口令", "type": "string"}
    )
    thicken["salonCheckinCode"] = True
    _add_feature(spec, "到店报到口令")

    # 时长占坑
    labels.setdefault("salonServiceMinutesLabel", "服务时长（分钟）")
    labels.setdefault(
        "salonServiceMinutesHint",
        "按项目时长自动占坑；短于该时长的号源不可约。",
    )
    _ensure_archive_field(
        archive,
        {
            "key": "serviceMinutes",
            "label": "服务时长（分钟）",
            "type": "number",
        },
    )
    thicken["salonServiceMinutes"] = True
    _add_feature(spec, "服务项目时长占坑")

    # 队列号
    labels.setdefault("queueNoLabel", "到店序号")
    labels.setdefault("queueNoHint", "确认预约后生成，到店按序等候。")
    thicken["salonQueueNo"] = True
    _add_feature(spec, "到店队列序号")

    # 改约手续费
    if not int(schema.get("salonRescheduleFeeYuan") or 0):
        schema["salonRescheduleFeeYuan"] = _SALON_RESCHEDULE_FEE_DEFAULT
    labels.setdefault("salonRescheduleFeeLabel", "改约手续费（元）")
    labels.setdefault(
        "salonRescheduleFeeHint",
        "改约成功后登记手续费金额，可在我的预约中查看。",
    )
    thicken["salonRescheduleFee"] = True
    _add_feature(spec, "美业改约手续费")

    # 迟到宽限：规则数字在 thesis.yml（late-grace-minutes），实例写 late_flag
    labels["lateGraceHint"] = (
        "到店超过预约开始时间这么多分钟再签到，将记为迟到。"
    )
    labels.setdefault(
        "salonLateGraceHint",
        "请尽量按时到店；超过宽限分钟再签到会记迟到。",
    )
    thicken["salonLateGrace"] = True
    _add_feature(spec, "美业到店迟到宽限")

    # 禁忌备注
    labels.setdefault("salonTabooLabel", "项目禁忌")
    labels.setdefault(
        "salonTabooHint",
        "过敏或不宜操作说明，预约页只读展示。",
    )
    _ensure_archive_field(
        archive, {"key": "tabooNote", "label": "项目禁忌", "type": "textarea"}
    )
    thicken["salonTaboo"] = True
    _add_feature(spec, "美业项目禁忌备注")

    # 到店扫码（签到码 + 二维码出示）
    labels.setdefault("salonCheckinScanLabel", "到店签到码")
    labels.setdefault(
        "salonCheckinScanHint",
        "确认预约后生成签到码，到店出示或扫码核对。",
    )
    thicken["salonCheckinScan"] = True
    _add_feature(spec, "美业到店扫码签到")

    # 到店次数
    labels.setdefault("salonVisitCountLabel", "到店次数")
    labels.setdefault(
        "salonVisitCountHint",
        "按已签到预约累计，便于会员到店统计。",
    )
    thicken["salonVisitCount"] = True
    _add_feature(spec, "美业会员到店次数")

    # 储值 / 作品集：禁止域默认硬挂 wallet、gallery（开题写到才挂）。
    # 地图归扫词可顶；勿把 gallery_json 当本组域皮交付。

    if not int(schema.get("salonServiceMinutesDefault") or 0):
        schema["salonServiceMinutesDefault"] = _SALON_SERVICE_MINUTES_DEFAULT


def _apply_hotel_r06(
    spec: dict[str, Any],
    schema: dict[str, Any],
    labels: dict[str, Any],
    resv_ent: dict[str, Any],
    archive: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """R-06：客房预约域皮（仅 HOTEL）。查房浅字段，禁止硬挂 material_check。"""
    # 续住延期（改离店日）
    labels.setdefault("hotelExtendStayLabel", "续住")
    labels.setdefault(
        "hotelExtendStayHint",
        "可将离店日往后延；续住后以新离店日为准。",
    )
    thicken["hotelExtendStay"] = True
    _add_feature(spec, "客房续住延期")

    # 延迟退房加收
    if not int(schema.get("hotelLateCheckoutFeeYuan") or 0):
        schema["hotelLateCheckoutFeeYuan"] = _HOTEL_LATE_CHECKOUT_FEE_DEFAULT
    labels.setdefault("hotelLateCheckoutLabel", "延迟退房加收")
    labels.setdefault(
        "hotelLateCheckoutHint",
        "超过约定离店时间未退房时，前台可登记加收金额。",
    )
    thicken["hotelLateCheckout"] = True
    _add_feature(spec, "客房延迟退房加收")

    # 身份证号 + 脱敏展示
    labels.setdefault("hotelIdNoLabel", "证件号")
    labels.setdefault(
        "hotelIdNoHint",
        "入住人证件号仅用于本系统登记；列表中脱敏展示。",
    )
    labels.setdefault("hotelIdNoMaskedLabel", "证件号（脱敏）")
    thicken["hotelIdNo"] = True
    _add_feature(spec, "入住人证件号脱敏")

    # 定金 / 尾款
    labels.setdefault("hotelDepositLabel", "定金（元）")
    labels.setdefault("hotelBalanceLabel", "尾款（元）")
    labels.setdefault(
        "hotelDepositBalanceHint",
        "定金与尾款分列登记，便于前台对账。",
    )
    thicken["hotelDepositBalance"] = True
    _add_feature(spec, "客房定金尾款分列")

    # 连住说明（文案）
    labels.setdefault(
        "hotelStayMultiNightHint",
        "连住多晚可按门店优惠说明享受折扣，具体以预订页提示为准。",
    )
    thicken["hotelStayMultiNight"] = True
    _add_feature(spec, "酒店连住优惠说明")

    # 早餐券
    labels.setdefault("hotelBreakfastLabel", "早餐券（张）")
    labels.setdefault(
        "hotelBreakfastHint",
        "登记本单可用早餐券张数。",
    )
    thicken["hotelBreakfast"] = True
    _add_feature(spec, "酒店早餐券张数")

    # 入住须知勾选
    schema["hotelNoticeRequired"] = True
    resv_ent["hotelNoticeRequired"] = True
    labels.setdefault("hotelNoticeLabel", "入住须知")
    labels.setdefault(
        "hotelNoticeText",
        "请妥善保管房卡与随身物品，遵守安静时段，退房时请带走个人物品。",
    )
    labels.setdefault("hotelNoticeAckLabel", "我已阅读并同意入住须知")
    thicken["hotelNoticeAck"] = True
    _add_feature(spec, "酒店入住须知勾选")

    # 加床
    labels.setdefault("hotelExtraBedLabel", "加床")
    labels.setdefault(
        "hotelExtraBedHint",
        "需要加床时勾选，费用以前台确认为准。",
    )
    thicken["hotelExtraBed"] = True
    _add_feature(spec, "酒店加床登记")

    # 钟点房类型
    labels.setdefault("hotelRoomKindLabel", "房时类型")
    labels.setdefault("hotelRoomKindFull", "全日房")
    labels.setdefault("hotelRoomKindHourly", "钟点房")
    labels.setdefault(
        "hotelRoomKindHint",
        "钟点房按小时段预订；全日房按晚计。",
    )
    _ensure_archive_field(
        archive,
        {
            "key": "roomKind",
            "label": "房时类型",
            "type": "select",
            "options": [
                {"value": "full", "label": "全日房"},
                {"value": "hourly", "label": "钟点房"},
            ],
        },
    )
    thicken["hotelRoomKind"] = True
    _add_feature(spec, "酒店钟点房时段类型")

    # 钟点超时转全日说明（文案）
    labels.setdefault(
        "hotelHourlyToFullHint",
        "钟点房超过约定时长时，按门店规则可转为全日房计费。",
    )
    thicken["hotelHourlyToFull"] = True
    _add_feature(spec, "钟点房超时转全日说明")

    # 同住人数（叠 guest_count 文案）
    resv_ent["guestCountLabel"] = "同住人数"
    labels.setdefault("hotelRoommateLabel", "同住人数")
    labels.setdefault(
        "hotelRoommateHint",
        "含入住人在内的同住人数。",
    )
    thicken["hotelRoommate"] = True
    _add_feature(spec, "酒店同住人数")

    # 查房清单（浅字段，禁止硬挂 material_check）
    labels.setdefault("hotelCheckoutChecklistLabel", "查房清单")
    labels.setdefault(
        "hotelCheckoutChecklistHint",
        "退房时可勾选或填写查房项，如迷你吧、毛巾、电器等。",
    )
    thicken["hotelCheckoutChecklist"] = True
    _add_feature(spec, "酒店退房查房清单")


def _apply_carrent_r07(
    spec: dict[str, Any],
    schema: dict[str, Any],
    labels: dict[str, Any],
    resv_ent: dict[str, Any],
    archive: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """R-07：租车预约域皮（仅 CARRENT）。验车浅字段；禁止硬挂 material_check / rental_bond。"""
    # 违章预留押说明 + 金额登记
    labels.setdefault("carrentViolationHoldLabel", "违章预留押（元）")
    labels.setdefault(
        "carrentViolationHoldHint",
        "租期内若产生违章，可登记预留押金额与说明，便于对账退还。",
    )
    labels.setdefault("carrentViolationHoldNoteLabel", "违章预留说明")
    thicken["carrentViolationHold"] = True
    _add_feature(spec, "租车违章预留押说明")

    # 验车单勾选（浅字段，禁止硬挂 material_check）
    labels.setdefault("carrentInspectAckLabel", "取还车验车确认")
    labels.setdefault(
        "carrentInspectAckHint",
        "取车或还车时勾选，表示已核对车况。",
    )
    thicken["carrentInspectAck"] = True
    _add_feature(spec, "租车取还车验车单勾选")

    # 里程超支加收
    if not int(schema.get("carrentMileageOverFeeYuan") or 0):
        schema["carrentMileageOverFeeYuan"] = _CARRENT_MILEAGE_OVER_FEE_DEFAULT
    labels.setdefault("carrentMileageOverLabel", "里程超支加收")
    labels.setdefault(
        "carrentMileageOverHint",
        "超出套餐里程时可登记加收金额。",
    )
    thicken["carrentMileageOver"] = True
    _add_feature(spec, "租车里程超支加收")

    # 取还点导航外链
    labels.setdefault("carrentPickupNavLabel", "取车点导航")
    labels.setdefault("carrentReturnNavLabel", "还车点导航")
    labels.setdefault(
        "carrentNavHint",
        "填写地图外链，方便驾车前往取还点。",
    )
    _ensure_archive_field(
        archive,
        {"key": "pickupNavUrl", "label": "取车点导航", "type": "string"},
    )
    _ensure_archive_field(
        archive,
        {"key": "returnNavUrl", "label": "还车点导航", "type": "string"},
    )
    thicken["carrentNav"] = True
    _add_feature(spec, "租车取还点导航外链")

    # 保险套餐勾选
    labels.setdefault("carrentInsuranceLabel", "保险套餐")
    labels.setdefault("carrentInsuranceNone", "不选")
    labels.setdefault("carrentInsuranceBasic", "基础险")
    labels.setdefault("carrentInsuranceFull", "全险")
    labels.setdefault(
        "carrentInsuranceHint",
        "按门店文案价勾选保险套餐，不含保司对接。",
    )
    thicken["carrentInsurance"] = True
    _add_feature(spec, "租车保险套餐勾选")

    # 驾照有效期
    labels.setdefault("carrentLicenseExpireLabel", "驾照有效期")
    labels.setdefault(
        "carrentLicenseExpireHint",
        "请填写驾驶证有效期至，便于门店核对。",
    )
    thicken["carrentLicenseExpire"] = True
    _add_feature(spec, "租车驾驶员驾照有效期")

    # 违章附件
    labels.setdefault("carrentViolationAttachLabel", "违章附件")
    labels.setdefault(
        "carrentViolationAttachHint",
        "可填写违章单据或照片链接，便于后续处理。",
    )
    thicken["carrentViolationAttach"] = True
    _add_feature(spec, "租车违章回传附件")

    # ETC 通行费登记
    labels.setdefault("carrentEtcFeeLabel", "ETC 通行费")
    labels.setdefault(
        "carrentEtcFeeHint",
        "还车后可登记 ETC 通行费金额，系统内记账。",
    )
    thicken["carrentEtcFee"] = True
    _add_feature(spec, "租车 ETC 通行费登记")

    resv_ent["guestNameLabel"] = resv_ent.get("guestNameLabel") or "驾驶人"
    resv_ent["guestCountLabel"] = resv_ent.get("guestCountLabel") or "用车人数"


def _apply_instrument_r08(
    spec: dict[str, Any],
    schema: dict[str, Any],
    labels: dict[str, Any],
    resv_ent: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """R-08：仪器机时域皮（仅 INSTRUMENT）。培训浅字段；禁止硬挂 material_check。"""
    # 机时超时计费登记
    if not int(schema.get("instrumentOvertimeYuan") or 0):
        schema["instrumentOvertimeYuan"] = _INSTRUMENT_OVERTIME_DEFAULT
    labels.setdefault("instrumentOvertimeLabel", "超时机时费")
    labels.setdefault(
        "instrumentOvertimeHint",
        "超出预约结束时间后，管理端可登记超时加收金额。",
    )
    thicken["instrumentOvertime"] = True
    _add_feature(spec, "机时超时自动计费登记")

    # 培训合格才可约（浅勾选，禁止硬挂 material_check）
    schema["instrumentTrainingRequired"] = True
    labels.setdefault("instrumentTrainingAckLabel", "已完成上机培训")
    labels.setdefault(
        "instrumentTrainingAckHint",
        "预约前请确认已完成仪器操作培训；未勾选不可提交。",
    )
    thicken["instrumentTraining"] = True
    _add_feature(spec, "仪器培训合格才可约")

    # 冲突可视化说明（对齐会议冲突提示）
    labels.setdefault(
        "instrumentConflictHint",
        "该时段若已有预约将显示占用；约满时请改选其它机时。",
    )
    thicken["instrumentConflict"] = True
    _add_feature(spec, "机时预约冲突可视化")

    # 实验目的必填（覆盖通识「备注」文案）
    resv_ent["requireRemark"] = True
    resv_ent["remarkLabel"] = "实验目的"
    labels.setdefault("instrumentPurposeLabel", "实验目的")
    labels.setdefault(
        "instrumentPurposeHint",
        "预约时须填写实验目的，便于管理员审核。",
    )
    thicken["instrumentPurpose"] = True
    _add_feature(spec, "仪器预约须填实验目的")

    # 耗材领用浅登记
    labels.setdefault("instrumentConsumableLabel", "耗材领用")
    labels.setdefault(
        "instrumentConsumableHint",
        "可登记本次机时关联的耗材领用说明，便于对账。",
    )
    thicken["instrumentConsumable"] = True
    _add_feature(spec, "仪器耗材领用关联登记")

    # 导师同意（轻审）
    resv_ent["requireConfirm"] = True
    labels.setdefault(
        "instrumentMentorConfirmHint",
        "机时预约提交后须导师或管理员确认后方可使用。",
    )
    thicken["instrumentMentor"] = True
    _add_feature(spec, "仪器预约须导师同意")

    # 机时费结算导出
    labels.setdefault("instrumentFeeExportLabel", "导出机时费")
    labels.setdefault(
        "instrumentFeeExportHint",
        "按当前筛选导出机时与超时加收（CSV）。",
    )
    thicken["instrumentFeeExport"] = True
    _add_feature(spec, "仪器机时费结算导出")


def _apply_r09_cap_islands(
    spec: dict[str, Any],
    schema: dict[str, Any],
    labels: dict[str, Any],
    thicken: dict[str, Any],
    caps: set[str],
    domain: str,
) -> None:
    """R-09：能力岛加深，仅当对应 cap 已挂；禁止域默认硬挂。"""
    if "staff_roster" in caps and domain == "DOM-HOSPITAL":
        labels.setdefault("hospitalRosterLabel", "当日值班")
        labels.setdefault(
            "hospitalRosterHint",
            "日历圆点表示当日有值班；预约时可查看值班医生。",
        )
        thicken["hospitalRoster"] = True
        _add_feature(spec, "医生诊室排班展示")

    if "staff_roster" in caps and domain == "DOM-SALON":
        labels.setdefault("salonLeaveBlockLabel", "技师请假")
        labels.setdefault(
            "salonLeaveBlockHint",
            "班次填「请假」或「休息」时，该日不可约该技师。",
        )
        thicken["salonLeaveBlock"] = True
        _add_feature(spec, "美业技师请假挡班")

    if "lesson_pack" in caps and domain == "DOM-SALON":
        labels.setdefault("salonLessonRemainLabel", "课时余次")
        labels.setdefault(
            "salonLessonRemainHint",
            "预约成功将扣减一节课时；余次不足时无法预约。",
        )
        labels.setdefault("salonLessonExpireTitle", "课时即将到期")
        labels.setdefault(
            "salonLessonExpireBody",
            "您的课时包即将到期，请尽快预约使用。",
        )
        thicken["salonLessonRemain"] = True
        thicken["salonLessonExpire"] = True
        _add_feature(spec, "美业会员卡余次")
        _add_feature(spec, "美业卡项过期提醒")

    if "wallet" in caps and domain == "DOM-SALON":
        labels.setdefault("salonWalletLabel", "储值余额")
        labels.setdefault(
            "salonWalletHint",
            "可在个人中心查看与充值储值余额，到店消费时扣减。",
        )
        thicken["salonWallet"] = True
        _add_feature(spec, "美业储值卡余额")

    if "gallery" in caps and domain == "DOM-SALON":
        labels.setdefault("salonGalleryLabel", "作品集")
        labels.setdefault(
            "salonGalleryHint",
            "技师作品可在资源详情中浏览。",
        )
        thicken["salonGallery"] = True
        _add_feature(spec, "作品集展示")

    if "room_equipment" in caps and domain == "DOM-MEETING":
        labels.setdefault("meetingEquipBorrowLabel", "借用录制设备")
        labels.setdefault(
            "meetingEquipBorrowHint",
            "勾选表示本次会议需借用会议室录制设备。",
        )
        thicken["meetingEquipBorrow"] = True
        _add_feature(spec, "会议录制设备借用勾选")

