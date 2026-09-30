"""跟进组加厚：CRM/EVENT/ATTEND/FUND/RECRUIT/GRADE/INTERN/LISTING 浅字段、文案、扫词开关。

硬约束
------
- 不新造厚 DOM；复用 archive/ticket/balance_ledger/favorites/allowRating/deadline/material_check。
- 域默认：通识必开（下次跟进提醒、搁置阶段、渠道饼图文案、假种额度、带看评价等）。
- 开题扫：家访模板、补考报名、周报优秀、房源对比、公海替代池、异议窗口等。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

FOLLOW_DOMAINS = frozenset(
    {
        "DOM-CRM",
        "DOM-EVENT",
        "DOM-ATTEND",
        "DOM-FUND",
        "DOM-RECRUIT",
        "DOM-GRADE",
        "DOM-INTERN",
        "DOM-LISTING",
    }
)

_HOME_VISIT_TERMS = ("家访", "谈话记录", "家访记录", "谈话模板")
_HOME_PHOTO_TERMS = ("家访照片", "家访附件", "谈话照片")
_PHONE_DUP_TERMS = ("客户查重", "同手机号", "线索查重", "手机号查重")
_ASSIGN_OWNER_TERMS = ("分配负责人", "改派负责人", "客户改派")
_STALE_POOL_TERMS = ("未跟进列表", "长期未跟进", "搁置池", "未跟进 N 天", "未跟进N天")
_CONTRACT_PLAN_TERMS = ("回款计划", "合同回款", "分期回款")
_DEAL_AMOUNT_TERMS = ("成交金额", "客户成交额", "成交登记金额")
_NEXT_ACTION_TERMS = ("下次行动", "行动待办", "跟进待办勾选")
_TAG_COLOR_TERMS = ("标签颜色", "客户标签色")
_SOURCE_PIE_TERMS = ("线索来源", "来源统计")
_FUNNEL_TERMS = ("阶段漏斗", "客户漏斗", "线索漏斗")
_CHANNEL_PIE_TERMS = ("跟进方式统计", "渠道饼图", "联系渠道统计")

_EVENT_CLOSE_ATTACH_TERMS = ("结案报告", "结案附件", "办结报告必传")
_EVENT_LEVEL_SLA_TERMS = ("事件等级时限", "等级影响时限", "按等级处理时限")
_EVENT_CONF_TERMS = ("事件保密", "上报保密", "保密标记")
_EVENT_DEPT_TERMS = ("分拨科室", "转派科室", "事件分拨")
_EVENT_DUTY_TERMS = ("值班排班", "事件值班", "值班表")
_EVENT_NOTIFY_DUTY_TERMS = ("通知值班", "一键通知值班", "值班群发")
_EVENT_LOC_TERMS = ("手填位置", "位置描述", "事发地点描述")
_EVENT_CHECK_EXPORT_TERMS = ("未打卡名单", "晨午检导出", "未打卡导出")

_LEAVE_BALANCE_TERMS = ("年假余额", "调休余额", "假期余额", "假种额度")
_LEAVE_ATTACH_TERMS = ("病假条", "请假附件", "假条必传")
_LEAVE_RETURN_TERMS = ("销假确认", "返岗日期", "销假返岗")
_LEAVE_PROXY_TERMS = ("请假代理人", "代请假", "代理人登记")
_LEAVE_MONTH_EXPORT_TERMS = ("考勤月汇总", "月汇总导出", "请假月报")
_LEAVE_IMPORT_TERMS = ("假期余额导入", "年假导入", "余额导入")
_LEAVE_APPROVE_SLA_TERMS = ("请假审批时限", "审批超时提醒", "请假超时提醒")
_LEAVE_QR_TERMS = ("销假二维码", "销假确认码")
_LEAVE_SPLIT_TERMS = ("跨天拆段", "请假拆段")

_FUND_DEFENSE_TERMS = ("资助答辩", "评议结果", "资助评议")
_FUND_OBJECTION_TERMS = ("公示异议", "异议登记", "奖学金异议")
_FUND_BANK_MASK_TERMS = ("银行卡脱敏", "卡号脱敏", "银行账号脱敏")
_FUND_BATCH_TERMS = ("发放批次", "批次号", "发放批次号")
_FUND_FORM_TERMS = ("资助形式", "减免发放", "助学金形式")
_FUND_QUOTA_SHOW_TERMS = ("名额余量", "名额实时", "剩余名额展示")

_INTERVIEW_RESULT_TERMS = ("面试结果", "通过未过", "录用淘汰")
_BATCH_HIRE_TERMS = ("批量录用", "批量淘汰", "录用批量")
_JOB_EXPIRE_TERMS = ("岗位有效期", "岗位下架", "招聘下架")
_INTERVIEW_DIMS_TERMS = ("面试评价表", "面试维度", "面试打分")
_WRITTEN_SCORE_TERMS = ("笔试成绩", "机试成绩", "笔试登记")
_DEPT_FILTER_TERMS = ("用人部门", "招聘部门筛选")
_RESUME_FIELDS_TERMS = ("简历解析字段", "简历手填", "结构化简历")
_ONBOARD_MAT_TERMS = ("入职材料", "入职清单", "入职材料清单")
_HIRE_MSG_TERMS = ("录用通知", "录用站内信", "录用消息模板")
_BG_CHECK_TERMS = ("背调备注", "背景调查备注", "背调登记")
_MEETING_HINT_TERMS = ("面试间预约", "会议室面试", "面试会议室")
_JOB_FAV_TERMS = ("岗位收藏", "职位收藏", "投递收藏")

_GRADE_PRINT_TERMS = ("成绩单打印", "成绩单预览", "打印成绩单")
_GRADE_RANK_SWITCH_TERMS = ("班级排名", "专业排名", "排名切换")
_MAKEUP_TERMS = ("补考报名", "不及格补考", "补考入口")
_IMPORT_ERR_TERMS = ("导入行级错误", "成绩导入错误", "行级错误回显")
_GPA_PAGE_TERMS = ("绩点换算", "绩点说明")
_OBJECTION_WINDOW_TERMS = ("成绩异议时限", "异议申请时限")
_WEIGHTED_AVG_TERMS = ("加权平均", "加权平均说明")
_DIST_CHART_TERMS = ("成绩分布图", "正态分布", "及格率图")
_STU_MASK_TERMS = ("学号脱敏", "成绩导出脱敏")
_RANK_PRIVACY_TERMS = ("排名隐私", "成绩排名隐私")
_MAKEUP_OVERLAY_TERMS = ("补考覆盖", "补考后覆盖")

_WEEK_DEADLINE_TERMS = ("周报截止", "周报未交", "周报提醒")
_APPRAISAL_TERMS = ("实习鉴定", "鉴定表", "评语等级")
_EXCELLENT_TERMS = ("周报优秀", "优秀标记", "优秀周报")
_MAX_REVISE_TERMS = ("退回修改次数", "周报退回上限", "修改次数限制")
_COMPANY_EVAL_TERMS = ("单位评价", "实习单位评价", "企业对实习生")
_ANON_EVAL_TERMS = ("评价匿名", "单位评价匿名")
_WORD_MIN_TERMS = ("周报字数", "字数下限", "周报最少字")
_ATTEND_LINK_TERMS = ("考勤与周报", "周报联动考勤")

_LISTING_RATING_TERMS = ("带看评价", "看房评价", "带看星级")
_LISTING_FAV_TERMS = ("房源收藏", "房源对比", "收藏对比")
_LISTING_FUNNEL_TERMS = ("成交漏斗", "挂牌带看成交")
_PRICE_HIST_TERMS = ("价格变更留痕", "房价流水", "调价留痕")
_LISTING_CONFLICT_TERMS = ("带看冲突", "带看时段冲突")
_VR_URL_TERMS = ("VR外链", "全景外链", "房源VR")
_FEEDBACK_SET_TERMS = ("带看反馈", "反馈必填", "看房反馈")
_INTENT_COUNT_TERMS = ("意向客户", "意向计数")
_RECORD_URL_TERMS = ("带看录音", "录音外链")


def scan_home_visit(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _HOME_VISIT_TERMS)


def scan_home_photo(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _HOME_PHOTO_TERMS)


def scan_phone_dup(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _PHONE_DUP_TERMS)


def scan_assign_owner(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _ASSIGN_OWNER_TERMS)


def scan_stale_pool(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _STALE_POOL_TERMS)


def scan_contract_plan(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _CONTRACT_PLAN_TERMS)


def scan_event_close_attach(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _EVENT_CLOSE_ATTACH_TERMS)


def scan_event_level_sla(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _EVENT_LEVEL_SLA_TERMS)


def scan_leave_attach(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _LEAVE_ATTACH_TERMS)


def scan_leave_return(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _LEAVE_RETURN_TERMS)


def scan_leave_proxy(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _LEAVE_PROXY_TERMS)


def scan_leave_approve_sla(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _LEAVE_APPROVE_SLA_TERMS)


def scan_fund_defense(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _FUND_DEFENSE_TERMS)


def scan_fund_objection(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _FUND_OBJECTION_TERMS)


def scan_interview_result(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _INTERVIEW_RESULT_TERMS)


def scan_batch_hire(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _BATCH_HIRE_TERMS)


def scan_job_expire(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _JOB_EXPIRE_TERMS)


def scan_interview_dims(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _INTERVIEW_DIMS_TERMS)


def scan_onboard_mat(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _ONBOARD_MAT_TERMS)


def scan_job_fav(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _JOB_FAV_TERMS) or any(
        keyword_mentioned(raw, kw, ignore_contrast=True) for kw in ("收藏岗位", "收藏职位")
    )


def scan_makeup(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _MAKEUP_TERMS)


def scan_week_deadline(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _WEEK_DEADLINE_TERMS)


def scan_appraisal(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _APPRAISAL_TERMS)


def scan_excellent(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _EXCELLENT_TERMS)


def scan_max_revise(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _MAX_REVISE_TERMS)


def scan_word_min(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _WORD_MIN_TERMS)


def scan_listing_rating(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _LISTING_RATING_TERMS)


def scan_listing_fav(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _LISTING_FAV_TERMS)


def scan_price_hist(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _PRICE_HIST_TERMS)


def _live_schema(spec: dict[str, Any]) -> dict[str, Any]:
    """原地取 schema，禁止浅拷贝后再写回（否则会冲掉 _force_* 挂上的顶层键）。"""
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
    schema = spec.get("schema")
    if isinstance(schema, dict):
        schema["capabilities"] = list(caps)


def _force_favorites(spec: dict[str, Any], *, lead: str, feature_name: str) -> None:
    from app.bake.features.favorites import FAVORITES_CAP, attach_favorites_menus
    from app.bake.gate_contracts import merge_favorites_gate

    _ensure_cap(spec, FAVORITES_CAP)
    schema = _live_schema(spec)
    attach_favorites_menus(schema, page_lead=lead)
    spec["schema"] = schema
    spec["gate"] = merge_favorites_gate(dict(spec.get("gate") or {}), list(spec.get("capabilities") or []))
    _add_feature(spec, feature_name, "module")


def _force_material_check(spec: dict[str, Any], *, title: str, lead: str) -> None:
    from app.bake.features.ticket_flow_opts import MATERIAL_CHECK_CAP, attach_material_check_menus

    _ensure_cap(spec, MATERIAL_CHECK_CAP)
    schema = _live_schema(spec)
    attach_material_check_menus(schema)
    labels = schema.setdefault("labels", {})
    labels["materialChecklistTitle"] = title
    labels["materialChecklistLead"] = lead
    spec["schema"] = schema
    _add_feature(spec, title)


def _force_balance_ledger(spec: dict[str, Any], domain: str) -> None:
    from app.bake.features.timebank import BALANCE_LEDGER_CAP, attach_balance_ledger_menus
    from app.bake.gate_contracts import merge_balance_ledger_gate

    _ensure_cap(spec, BALANCE_LEDGER_CAP)
    schema = _live_schema(spec)
    attach_balance_ledger_menus(schema, domain)
    if domain == "DOM-ATTEND":
        labels = schema.setdefault("labels", {})
        labels["balanceUnit"] = "天"
        labels["balanceSubjectTitle"] = "假期额度"
        labels.setdefault(
            "balanceMineLead",
            "查看本人年假/调休等可用天数；请假批准时按请假天数扣减，销假后按规则回补。",
        )
        bl = schema.setdefault("balanceLedger", {})
        if isinstance(bl, dict):
            bl["debitOnApprove"] = True
            bl["creditOnReturn"] = True
            bl["useLeaveDays"] = True
    spec["schema"] = schema
    spec["gate"] = merge_balance_ledger_gate(
        dict(spec.get("gate") or {}), list(spec.get("capabilities") or [])
    )
    _add_feature(spec, "假期额度扣减与回补")


def _force_deadline(spec: dict[str, Any], *, menu_label: str) -> None:
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


def _force_message_template(spec: dict[str, Any]) -> None:
    from app.bake.features.message_template import MESSAGE_TEMPLATE_CAP, attach_message_template_menus
    from app.bake.gate_contracts import merge_message_template_gate

    _ensure_cap(spec, MESSAGE_TEMPLATE_CAP)
    schema = _live_schema(spec)
    attach_message_template_menus(schema)
    spec["schema"] = schema
    spec["gate"] = merge_message_template_gate(
        dict(spec.get("gate") or {}), list(spec.get("capabilities") or [])
    )
    _add_feature(spec, "站内消息模板")


def _force_code_qr(spec: dict[str, Any]) -> None:
    from app.bake.features.code_qr import CODE_QR_CAP, CODE_QR_HINT_DEFAULT
    from app.bake.gate_contracts import merge_code_qr_gate

    _ensure_cap(spec, CODE_QR_CAP)
    schema = _live_schema(spec)
    labels = schema.setdefault("labels", {})
    labels.setdefault("codeQrShowVerb", "出示二维码")
    labels.setdefault("codeQrPrintVerb", "打印")
    labels.setdefault("codeQrHint", CODE_QR_HINT_DEFAULT)
    spec["schema"] = schema
    spec["gate"] = merge_code_qr_gate(
        dict(spec.get("gate") or {}), list(spec.get("capabilities") or [])
    )
    _add_feature(spec, "销假确认二维码")


def _force_staff_roster(spec: dict[str, Any]) -> None:
    from app.bake.features.staff_roster import STAFF_ROSTER_CAP, attach_staff_roster_menus
    from app.bake.gate_contracts import merge_staff_roster_gate

    _ensure_cap(spec, STAFF_ROSTER_CAP)
    schema = _live_schema(spec)
    attach_staff_roster_menus(schema)
    spec["schema"] = schema
    try:
        spec["gate"] = merge_staff_roster_gate(
            dict(spec.get("gate") or {}), list(spec.get("capabilities") or [])
        )
    except Exception:
        pass
    _add_feature(spec, "值班排班")


def _force_rating_dims(spec: dict[str, Any]) -> None:
    _ensure_cap(spec, "rating_dims")
    schema = _live_schema(spec)
    ticket = schema.setdefault("entities", {}).setdefault("ticket", {})
    if isinstance(ticket, dict):
        ticket["allowRating"] = True
        ticket["ratingDims"] = list(
            ticket.get("ratingDims")
            or [
                {"key": "skill", "label": "专业能力"},
                {"key": "comm", "label": "沟通表达"},
                {"key": "fit", "label": "岗位匹配"},
            ]
        )
    labels = schema.setdefault("labels", {})
    labels.setdefault("ratingDimsTitle", "面试评价")
    labels.setdefault("ratingDimsLead", "按维度打分后取均值作为综合分。")
    spec["schema"] = schema
    _add_feature(spec, "面试评价表（维度打分）")


def apply_follow_thicken_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """按域默认 + 开题扫词加厚跟进组 schema（只增不减）。"""
    domain = str(spec.get("domain") or "")
    if domain not in FOLLOW_DOMAINS:
        return spec
    text = proposal_text or ""
    schema = _live_schema(spec)
    ents = schema.setdefault("entities", {})
    archive = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
    if not isinstance(archive, dict):
        archive = {}
        ents["archive"] = archive
    ticket = ents.get("ticket") if isinstance(ents.get("ticket"), dict) else {}
    if not isinstance(ticket, dict):
        ticket = {}
        ents["ticket"] = ticket
    labels = schema.setdefault("labels", {})
    thicken = schema.setdefault("followThicken", {})
    if not isinstance(thicken, dict):
        thicken = {}
        schema["followThicken"] = thicken

    # —— CRM ——
    if domain == "DOM-CRM":
        ticket.setdefault("followRemindDays", 1)
        thicken["followRemind"] = True
        _add_feature(spec, "下次跟进日到期站内信提醒")
        labels.setdefault(
            "followTimelineHint",
            "同一客户下的跟进记录按时间倒序排列；请登记联系渠道与下次跟进日。",
        )
        thicken["followTimeline"] = True
        _add_feature(spec, "跟进记录时间轴")
        # 双端：用户/业务员写 contact_channel+next_follow；管理端档案标签
        labels.setdefault("tagColorHint", "客户标签可选用颜色备注区分优先级。")
        thicken["tagColor"] = True
        _add_feature(spec, "客户标签颜色")
        _ensure_archive_field(
            archive,
            {
                "key": "tags",
                "label": "客户标签",
                "type": "string",
                "placeholder": "多个标签用逗号分隔",
            },
        )
        thicken["customerTags"] = True
        _add_feature(spec, "客户标签多选筛选")
        labels.setdefault(
            "channelPieHint",
            "工作台可按联系渠道（电话/微信/到访等）汇总跟进次数。",
        )
        thicken["channelPie"] = True
        _add_feature(spec, "跟进方式统计饼图")
        labels.setdefault(
            "stageFunnelHint",
            "工作台按销售阶段统计客户数，形成浅漏斗（线索→意向→谈判→成交）。",
        )
        thicken["stageFunnel"] = True
        _add_feature(spec, "客户阶段漏斗简图")
        # 搁置已在 stage 选项
        thicken["shelveStage"] = True
        _add_feature(spec, "长期未跟进标搁置")
        # 查重 / 成交金额：域默认
        ticket["phoneDupCheck"] = True
        labels.setdefault(
            "phoneDupHint",
            "录入客户时若手机号与已有客户相同，将提示可能重复，请确认后再保存。",
        )
        thicken["phoneDupCheck"] = True
        _add_feature(spec, "客户/线索查重提示")
        ticket["allowDealAmount"] = True
        labels.setdefault("dealAmountLabel", "成交金额（元）")
        thicken["dealAmount"] = True
        _add_feature(spec, "客户成交金额登记")
        if scan_home_visit(text):
            ticket["homeVisitTemplate"] = True
            labels.setdefault("homeVisitFamilyLabel", "家庭情况")
            labels.setdefault("homeVisitTalkLabel", "谈话要点")
            labels.setdefault("homeVisitPlanLabel", "后续计划")
            thicken["homeVisit"] = True
            _add_feature(spec, "家访/谈话记录模板字段套")
        if scan_home_photo(text):
            ticket["requireAttach"] = True
            labels.setdefault("homePhotoAttachHint", "家访请上传现场照片附件。")
            thicken["homePhoto"] = True
            _add_feature(spec, "家访照片附件槽")
        if scan_assign_owner(text):
            _ensure_archive_field(
                archive, {"key": "ownerUsername", "label": "负责人账号", "type": "string"}
            )
            labels.setdefault("assignOwnerHint", "可将客户改派给其他业务员，不支持公海抢客。")
            thicken["assignOwner"] = True
            _add_feature(spec, "分配负责人")
        if scan_stale_pool(text):
            ticket.setdefault("staleFollowDays", 14)
            labels.setdefault(
                "stalePoolHint",
                "可按「超过 N 天未跟进」筛选客户列表，便于回访；≠公海抢客。",
            )
            thicken["stalePool"] = True
            _add_feature(spec, "未跟进 N 天列表")
        if scan_contract_plan(text):
            _ensure_archive_field(
                archive, {"key": "paymentPlan", "label": "回款计划备注", "type": "string"}
            )
            thicken["paymentPlan"] = True
            _add_feature(spec, "客户合同回款计划")
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _NEXT_ACTION_TERMS):
            ticket["allowNextAction"] = True
            labels.setdefault("nextActionLabel", "下次行动待办")
            labels.setdefault("nextActionDoneLabel", "行动已完成")
            thicken["nextAction"] = True
            _add_feature(spec, "客户跟进下次行动待办勾选")
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _TAG_COLOR_TERMS):
            pass  # 标签色标已域默认
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _SOURCE_PIE_TERMS):
            _ensure_archive_field(
                archive,
                {
                    "key": "leadSource",
                    "label": "线索来源",
                    "type": "select",
                    "options": ["转介绍", "线上广告", "线下活动", "自然到访", "其他"],
                },
            )
            labels.setdefault("sourcePieHint", "工作台可按线索来源汇总客户数。")
            thicken["sourcePie"] = True
            _add_feature(spec, "线索来源统计饼图")

    # —— EVENT ——
    if domain == "DOM-EVENT":
        _ensure_archive_field(
            archive, {"key": "locationDesc", "label": "位置描述", "type": "string"}
        )
        thicken["locationDesc"] = True
        _add_feature(spec, "事件上报手填位置描述")
        labels.setdefault(
            "checkExportHint",
            "师生晨午检打卡写入记录；管理端可导出未打卡名单 CSV。",
        )
        thicken["checkExport"] = True
        _add_feature(spec, "晨午检未打卡名单导出")
        # 结案报告附件：域默认
        ticket["requireCloseAttach"] = True
        labels.setdefault("closeAttachLabel", "结案报告附件")
        labels.setdefault("closeAttachHint", "办结前须上传结案报告附件。")
        thicken["closeAttach"] = True
        _add_feature(spec, "事件结案报告附件必传")
        if scan_event_level_sla(text):
            _force_deadline(spec, menu_label="处理时限")
            ticket["levelAffectsDeadline"] = True
            # 等级 → 处理时限天数（高/中/低），受理时按事件等级落 due_at / response_due_at
            ticket["levelSlaHighDays"] = int(ticket.get("levelSlaHighDays") or 1)
            ticket["levelSlaMidDays"] = int(ticket.get("levelSlaMidDays") or 3)
            ticket["levelSlaLowDays"] = int(ticket.get("levelSlaLowDays") or 7)
            labels.setdefault(
                "levelSlaHint",
                "高等级事件默认更短处理时限；可在处理时限菜单调整。",
            )
            thicken["levelSla"] = True
            _add_feature(spec, "事件等级影响处理时限")
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _EVENT_CONF_TERMS):
            ticket["allowConfidential"] = True
            labels.setdefault("confidentialLabel", "保密事件")
            thicken["confidential"] = True
            _add_feature(spec, "事件上报保密标记")
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _EVENT_DEPT_TERMS):
            ticket["allowAssignDept"] = True
            labels.setdefault("assignDeptLabel", "分拨科室")
            thicken["assignDept"] = True
            _add_feature(spec, "事件上报分拨科室")
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _EVENT_DUTY_TERMS):
            _force_staff_roster(spec)
            thicken["dutyRoster"] = True
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _EVENT_NOTIFY_DUTY_TERMS):
            ticket["notifyDutyOnReport"] = True
            labels.setdefault(
                "notifyDutyHint",
                "新上报可通过站内信通知当日值班人员（浅群发，非短信）。",
            )
            thicken["notifyDuty"] = True
            _add_feature(spec, "事件上报一键通知值班表")

    # —— ATTEND ——
    if domain == "DOM-ATTEND":
        _force_balance_ledger(spec, domain)
        thicken["leaveBalance"] = True
        labels.setdefault(
            "leaveBalanceHint",
            "年假/调休等从额度账户扣减；销假办结后按请假天数回补。",
        )
        labels.setdefault(
            "leaveOverlapHint",
            "本人已有请假时段与新申请相交时将提示冲突，请调整起止日期。",
        )
        thicken["overlapHint"] = True
        _add_feature(spec, "请假 overlapping 跨岗冲突提示")
        labels.setdefault(
            "leaveSplitHint",
            "跨天请假在列表中按起止日展示占用天数，便于核对。",
        )
        thicken["leaveSplit"] = True
        _add_feature(spec, "请假跨天拆段展示")
        labels.setdefault(
            "monthExportHint",
            "员工提交请假写库；管理端可按月导出汇总，员工可导出本人办理记录。",
        )
        thicken["monthExport"] = True
        _add_feature(spec, "考勤月汇总表导出")
        labels.setdefault(
            "leaveBalanceImportHint",
            "管理端维护假期额度；员工请假时从额度扣减并产生单据。",
        )
        thicken["leaveImport"] = True
        _add_feature(spec, "请假假期余额导入")
        # 按假种附件 + 返岗日期：域默认
        ticket["attachByLeaveType"] = True
        labels.setdefault(
            "sickAttachHint",
            "病假等假种可要求上传假条附件；提交时请按假种说明上传。",
        )
        thicken["attachByLeaveType"] = True
        _add_feature(spec, "请假附件按假种必传")
        ticket["requireReturnDate"] = True
        labels.setdefault("returnDateLabel", "返岗日期")
        thicken["returnDate"] = True
        _add_feature(spec, "销假确认（返岗日期）")
        if scan_leave_proxy(text):
            ticket["allowLeaveProxy"] = True
            labels.setdefault("leaveProxyLabel", "代理人")
            thicken["leaveProxy"] = True
            _add_feature(spec, "请假代理人登记")
        if scan_leave_approve_sla(text):
            _force_deadline(spec, menu_label="审批时限")
            thicken["approveSla"] = True
            _add_feature(spec, "请假审批时限超时提醒")
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _LEAVE_QR_TERMS):
            _force_code_qr(spec)
            ticket["issuePassCode"] = True
            thicken["returnQr"] = True
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _LEAVE_IMPORT_TERMS):
            pass  # 假期余额导入说明已域默认

    # —— FUND ——
    if domain == "DOM-FUND":
        labels.setdefault(
            "quotaRemainHint",
            "列表展示剩余名额；学生提交资助申请写库，管理端审批占用名额。",
        )
        thicken["quotaRemain"] = True
        _add_feature(spec, "资助名额余量实时展示")
        _ensure_archive_field(
            archive,
            {
                "key": "fundForm",
                "label": "资助形式",
                "type": "select",
                "options": ["发放", "学费减免", "勤工助学", "其他"],
            },
        )
        thicken["fundForm"] = True
        _add_feature(spec, "资助形式枚举")
        # 答辩结果 / 银行卡脱敏 / 发放批次：域默认
        ticket["allowDefenseResult"] = True
        labels.setdefault("defenseResultLabel", "答辩/评议结果")
        labels.setdefault(
            "defenseResultOptions",
            ["通过", "候补", "未通过", "待定"],
        )
        thicken["defenseResult"] = True
        _add_feature(spec, "资助答辩/评议结果登记")
        ticket["maskBankAccount"] = True
        labels.setdefault("bankAccountLabel", "银行卡号")
        labels.setdefault("bankMaskHint", "列表与详情仅显示后四位，中间以*脱敏。")
        thicken["bankMask"] = True
        _add_feature(spec, "资助银行卡号脱敏展示")
        ticket["allowDisburseBatch"] = True
        labels.setdefault("disburseBatchLabel", "发放批次号")
        thicken["disburseBatch"] = True
        _add_feature(spec, "资助发放批次号")
        if scan_fund_objection(text):
            ticket["allowObjectionWindow"] = True
            # 公示结束日 + N 天为异议登记窗口（超期入口关闭）
            ticket["objectionDays"] = int(ticket.get("objectionDays") or 5)
            labels.setdefault("objectionWindowLabel", "异议登记截止日")
            labels.setdefault("objectionNoteLabel", "异议说明")
            labels.setdefault(
                "objectionWindowHint",
                "公示结束日 + N 天内可登记异议，逾期关闭入口。",
            )
            thicken["objectionWindow"] = True
            _add_feature(spec, "奖学金公示异议登记窗口")

    # —— RECRUIT ——
    if domain == "DOM-RECRUIT":
        labels.setdefault(
            "progressTimelineHint",
            "投递进度按提交→初筛→面试→结果时间线展示。",
        )
        thicken["progressTimeline"] = True
        _add_feature(spec, "投递进度时间轴")
        # 面试结果 / 批量录用 / 岗位有效期：域默认
        ticket["allowInterviewResult"] = True
        labels.setdefault("interviewResultLabel", "面试结果")
        labels.setdefault(
            "interviewResultOptions",
            ["待定", "通过", "未通过"],
        )
        thicken["interviewResult"] = True
        _add_feature(spec, "面试结果登记")
        ticket["allowBatchHire"] = True
        labels.setdefault("batchHireLabel", "批量录用")
        labels.setdefault("batchRejectLabel", "批量淘汰")
        thicken["batchHire"] = True
        _add_feature(spec, "录用/淘汰批量操作")
        _ensure_archive_field(
            archive, {"key": "expireOn", "label": "岗位有效期", "type": "date"}
        )
        labels.setdefault(
            "jobExpireHint",
            "超过有效期的岗位自动标为下架，不再接受新投递。",
        )
        thicken["jobExpire"] = True
        _add_feature(spec, "招聘岗位有效期自动下架")
        # 双端：用户/招聘专员写面试地点；管理端审核投递
        labels.setdefault("interviewPlaceLabel", "面试地点/会议室")
        labels.setdefault(
            "interviewPlaceLead",
            "可填写楼栋会议室号；需要另约会议室时请注明时段。",
        )
        labels.setdefault(
            "interviewRoomHint",
            "面试地点写入本单；会议室紧张时可叠会议室预约系统另约。",
        )
        thicken["meetingHint"] = True
        _add_feature(spec, "招聘面试间预约叠会议室")
        if scan_interview_dims(text):
            _force_rating_dims(spec)
            thicken["interviewDims"] = True
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _WRITTEN_SCORE_TERMS):
            ticket["allowWrittenScore"] = True
            labels.setdefault("writtenScoreLabel", "笔试/机试成绩")
            thicken["writtenScore"] = True
            _add_feature(spec, "招聘笔试/机试成绩登记")
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _DEPT_FILTER_TERMS):
            _ensure_archive_field(
                archive, {"key": "hireDept", "label": "用人部门", "type": "string"}
            )
            thicken["hireDept"] = True
            _add_feature(spec, "招聘用人部门筛选")
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _RESUME_FIELDS_TERMS):
            ticket["resumeFieldSet"] = True
            labels.setdefault("resumeEduLabel", "学历")
            labels.setdefault("resumeExpLabel", "工作年限")
            labels.setdefault("resumeSkillLabel", "技能摘要")
            thicken["resumeFields"] = True
            _add_feature(spec, "招聘简历解析字段手填套")
        if scan_onboard_mat(text):
            _force_material_check(
                spec,
                title="入职材料清单",
                lead="录用后须勾选并上传入职材料，材料齐备方可办结。",
            )
            thicken["onboardMat"] = True
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _HIRE_MSG_TERMS):
            _force_message_template(spec)
            thicken["hireMsg"] = True
            _add_feature(spec, "招聘录用通知站内信模板")
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _BG_CHECK_TERMS):
            ticket["allowBgCheckNote"] = True
            labels.setdefault("bgCheckNoteLabel", "背调备注")
            thicken["bgCheck"] = True
            _add_feature(spec, "招聘背调备注字段")
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _MEETING_HINT_TERMS):
            pass  # 面试地点/会议室提示已域默认
        if scan_job_fav(text):
            _force_favorites(
                spec,
                lead="收藏感兴趣的岗位，便于再次投递与对比。",
                feature_name="岗位收藏",
            )
            thicken["jobFav"] = True
            labels.setdefault(
                "favShareHint",
                "可「导出清单」或「复制清单」发给同学；无需独立分享页。",
            )
            _add_feature(spec, "招聘岗位收藏夹分享")

    # —— GRADE ——
    if domain == "DOM-GRADE":
        labels.setdefault(
            "gradePrintHint",
            "成绩查询页可浏览器打印；如有异议请提交成绩更正申请。",
        )
        thicken["gradePrint"] = True
        _add_feature(spec, "成绩单打印预览页")
        labels.setdefault(
            "rankSwitchHint",
            "成绩列表可按班级/专业切换名次维度；提交更正申请时一并登记范围。",
        )
        thicken["rankSwitch"] = True
        _add_feature(spec, "成绩排名班级/专业切换")
        labels.setdefault(
            "distChartHint",
            "工作台展示成绩分布与及格率；分数由管理端登记，学生可申请更正。",
        )
        thicken["distChart"] = True
        _add_feature(spec, "成绩正态分布简易图")
        labels.setdefault(
            "gpaPageHint",
            "绩点换算规则见说明；提交申请前请勾选已知悉。",
        )
        thicken["gpaPage"] = True
        _add_feature(spec, "绩点换算说明页")
        labels.setdefault(
            "weightedAvgHint",
            "加权平均按学分权重计算；详见成绩须知。",
        )
        thicken["weightedAvg"] = True
        _add_feature(spec, "成绩加权平均说明")
        labels.setdefault(
            "makeupOverlayHint",
            "补考通过后按规则覆盖原成绩；请通过补考报名入口提交。",
        )
        thicken["makeupOverlay"] = True
        _add_feature(spec, "成绩补考后覆盖规则说明")
        labels.setdefault(
            "importRowErrorHint",
            "管理端导入成绩若有行错误会回显；学生可对异常成绩提交更正申请。",
        )
        thicken["importRowError"] = True
        _add_feature(spec, "成绩导入行级错误回显")
        labels.setdefault(
            "stuNoMaskExportHint",
            "导出成绩时可勾选学号脱敏；学生本人可导出自己的办理记录。",
        )
        thicken["stuNoMask"] = True
        _add_feature(spec, "成绩导出含学号脱敏选项")
        ticket["requireNoticeAck"] = True
        labels.setdefault("noticeAckLabel", "我已阅读绩点与成绩覆盖规则")
        ticket["allowMakeupApply"] = True
        labels.setdefault("makeupApplyLabel", "补考报名")
        labels.setdefault(
            "makeupApplyHint",
            "不及格成绩可提交补考报名，审核通过后参加补考。",
        )
        thicken["makeupApply"] = True
        _add_feature(spec, "补考报名入口")
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _OBJECTION_WINDOW_TERMS):
            ticket["objectionDays"] = int(ticket.get("objectionDays") or 7)
            labels.setdefault(
                "objectionWindowHint",
                "成绩发布后 N 日内可提交更正/异议申请，逾期关闭入口。",
            )
            thicken["objectionWindow"] = True
            _add_feature(spec, "成绩异议申请时限")
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _RANK_PRIVACY_TERMS):
            schema["rankPrivacy"] = True
            labels.setdefault(
                "rankPrivacyHint",
                "开启后学生端仅看本人名次，不展示完整排行榜。",
            )
            thicken["rankPrivacy"] = True
            _add_feature(spec, "成绩排名隐私开关")

    # —— INTERN ——
    if domain == "DOM-INTERN":
        labels.setdefault(
            "attendLinkHint",
            "请保证周报周次与考勤记录一致；缺勤周请在周报中说明。",
        )
        thicken["attendLink"] = True
        _add_feature(spec, "实习考勤与周报联动提示")
        # 周报催交 / 鉴定表 / 退回上限 / 单位评价 / 字数下限：域默认
        ticket.setdefault("weekReportDeadlineDay", 7)
        ticket["weekReportRemind"] = True
        labels.setdefault(
            "weekReportRemindHint",
            "每周截止日前未提交周报将收到站内信提醒。",
        )
        thicken["weekRemind"] = True
        _add_feature(spec, "周报截止未交提醒")
        ticket["requireAppraisal"] = True
        labels.setdefault("appraisalCommentLabel", "鉴定评语")
        labels.setdefault("appraisalGradeLabel", "鉴定等级")
        labels.setdefault(
            "appraisalGradeOptions",
            ["优秀", "良好", "合格", "不合格"],
        )
        thicken["appraisal"] = True
        _add_feature(spec, "实习鉴定表字段套")
        ticket.setdefault("maxReviseTimes", 2)
        labels.setdefault(
            "maxReviseHint",
            "导师退回修改超过上限后不可再提交，须联系导师说明。",
        )
        thicken["maxRevise"] = True
        _add_feature(spec, "周报退回修改次数限制")
        ticket["allowCompanyEval"] = True
        labels.setdefault("companyEvalLabel", "单位评价")
        thicken["companyEval"] = True
        _add_feature(spec, "实习单位对实习生评价")
        ticket.setdefault("minRemarkWords", 100)
        labels.setdefault(
            "minRemarkWordsHint",
            "周报正文不少于设定字数方可提交。",
        )
        thicken["minWords"] = True
        _add_feature(spec, "实习周报字数下限")
        if scan_excellent(text):
            ticket["allowExcellentMark"] = True
            labels.setdefault("excellentMarkLabel", "优秀周报")
            labels.setdefault(
                "excellentExportHint",
                "管理端可筛选优秀周报并导出 CSV。",
            )
            thicken["excellent"] = True
            _add_feature(spec, "实习周报优秀标记与汇总导出")
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _ANON_EVAL_TERMS):
            schema["companyEvalAnonymous"] = True
            labels.setdefault("companyEvalAnonHint", "单位评价可匿名展示给学生。")
            thicken["companyEvalAnon"] = True
            _add_feature(spec, "实习单位评价匿名开关")

    # —— LISTING ——
    if domain == "DOM-LISTING":
        ticket.setdefault("followRemindDays", 1)
        thicken["followRemind"] = True
        _add_feature(spec, "房源意向跟进下次提醒")
        labels.setdefault(
            "listingFunnelHint",
            "工作台统计挂牌→带看→成交数量，形成浅漏斗。",
        )
        thicken["listingFunnel"] = True
        _add_feature(spec, "成交漏斗简图")
        labels.setdefault(
            "intentCountHint",
            "用户收藏房源产生意向；详情展示意向次数，管理端可跟进。",
        )
        thicken["intentCount"] = True
        _add_feature(spec, "房源意向客户计数")
        labels.setdefault("tagColorHint", "房源标签以色点区分；管理端维护标签，带看单可关联。")
        thicken["tagColor"] = True
        _add_feature(spec, "客户/房源标签色标")
        _force_favorites(
            spec,
            lead="收藏房源产生意向数据，支持对比与再次带看。",
            feature_name="房源收藏与意向",
        )
        # 带看评价 / 调价留痕 / VR / 反馈套：域默认
        ticket["allowRating"] = True
        labels.setdefault("ratingLabel", "带看评价")
        thicken["listingRating"] = True
        _add_feature(spec, "带看评价（星级）")
        _ensure_archive_field(
            archive, {"key": "priceHistory", "label": "价格变更备注", "type": "string"}
        )
        labels.setdefault(
            "priceHistHint",
            "调价时请在价格变更备注中留下原价与原因，便于留痕。",
        )
        thicken["priceHist"] = True
        _add_feature(spec, "房源价格变更留痕")
        _ensure_archive_field(
            archive, {"key": "vrUrl", "label": "VR/全景外链", "type": "string"}
        )
        thicken["vrUrl"] = True
        _add_feature(spec, "房源VR外链字段")
        ticket["requireFeedbackSet"] = True
        labels.setdefault("feedbackInterestLabel", "客户意向")
        labels.setdefault("feedbackConcernLabel", "顾虑点")
        labels.setdefault("feedbackNextLabel", "下一步建议")
        thicken["feedbackSet"] = True
        _add_feature(spec, "带看反馈必填项套")
        if scan_listing_fav(text):
            _force_favorites(
                spec,
                lead="收藏房源，支持两套字段并排对比。",
                feature_name="房源收藏与对比",
            )
            labels.setdefault(
                "listingCompareHint",
                "可导出或复制收藏清单，对照面积/价格等字段再决定；无需独立对比页。",
            )
            thicken["listingFav"] = True
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _LISTING_CONFLICT_TERMS):
            _ensure_cap(spec, "time_conflict")
            ticket["checkTimeConflict"] = True
            labels.setdefault(
                "listingConflictHint",
                "同一经纪人带看时段相交时将提示冲突。",
            )
            thicken["listingConflict"] = True
            _add_feature(spec, "带看预约时段冲突提示")
        if any(keyword_mentioned(text, kw, ignore_contrast=True) for kw in _RECORD_URL_TERMS):
            ticket["allowRecordUrl"] = True
            labels.setdefault("recordUrlLabel", "带看录音外链")
            thicken["recordUrl"] = True
            _add_feature(spec, "带看录音外链字段")
        # 标签筛选（与 CRM 同思路）
        _ensure_archive_field(
            archive,
            {
                "key": "tags",
                "label": "房源标签",
                "type": "string",
                "placeholder": "多个标签用逗号分隔",
            },
        )
        thicken["listingTags"] = True
        _add_feature(spec, "房源标签多选筛选")

    schema["followThicken"] = thicken
    ents["archive"] = archive
    ents["ticket"] = ticket
    schema["entities"] = ents
    schema["labels"] = labels
    spec["schema"] = schema
    return spec
