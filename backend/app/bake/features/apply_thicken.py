"""报名/申请组加厚：须知勾选、驳回理由、站内信、失物下架/到期、浅档案字段与规则。

硬约束
------
- 不新造厚 DOM；复用 ticket_flow / quota / ArchiveStore / MessageStore / DemoScheduleJobs / allowBatchHire。
- 须知勾选 ≠ 合同平台；悬赏备注 ≠ 真打赏；行程日明细 ≠ 地图轨迹；紧急联系人 ≠ 外呼。
- 学分上限 / 退选上限 / 取消时限 / 认领冷却 = 浅规则，≠ 完整教务引擎 / 公平抽签平台。
- 域默认：四域通识必开；域皮字段与规则按 ACTIVITY / LOST / COURSE / TOUR 分流。
"""

from __future__ import annotations

from typing import Any

APPLY_DOMAINS = frozenset({"DOM-ACTIVITY", "DOM-LOST", "DOM-COURSE", "DOM-TOUR"})

_NOTICE_ACK_BY_DOMAIN: dict[str, str] = {
    "DOM-ACTIVITY": "我已阅读报名须知并确认可按时参加",
    "DOM-LOST": "我已阅读认领须知并确认物品特征属实",
    "DOM-COURSE": "我已阅读选课须知并确认课表无冲突",
    "DOM-TOUR": "我已阅读出团须知并确认行程与联系方式",
}


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


def _force_material_check(
    spec: dict[str, Any],
    schema: dict[str, Any],
    *,
    title: str,
    lead: str,
) -> None:
    """域默认挂材料清单：管理端维护项，用户申请须按清单上传写库。"""
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
    attach_material_check_menus(schema)
    labels = schema.setdefault("labels", {})
    labels["materialChecklistTitle"] = title
    labels["materialChecklistLead"] = lead
    gate = spec.get("gate") if isinstance(spec.get("gate"), dict) else {}
    spec["gate"] = merge_material_check_gate(gate, caps)


def apply_apply_thicken_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """按域默认加厚报名/申请组 schema（只增不减）。"""
    _ = proposal_text
    domain = str(spec.get("domain") or "")
    if domain not in APPLY_DOMAINS:
        return spec

    schema = _live_schema(spec)
    ents = schema.setdefault("entities", {})
    ticket = ents.get("ticket") if isinstance(ents.get("ticket"), dict) else {}
    if not isinstance(ticket, dict):
        ticket = {}
        ents["ticket"] = ticket
    archive = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
    if not isinstance(archive, dict):
        archive = {}
        ents["archive"] = archive
    labels = schema.setdefault("labels", {})
    thicken = schema.setdefault("applyThicken", {})
    if not isinstance(thicken, dict):
        thicken = {}
        schema["applyThicken"] = thicken

    ticket["applyThicken"] = True
    thicken["core"] = True

    # —— 四域通识 ——
    ticket["requireNoticeAck"] = True
    labels.setdefault(
        "noticeAckLabel",
        _NOTICE_ACK_BY_DOMAIN.get(domain, "我已阅读须知并确认可提交"),
    )
    thicken["noticeAck"] = True
    _add_feature(spec, "报名须知已阅读勾选")

    labels.setdefault("rejectReasonRequired", "请填写驳回原因，申请人可见")
    thicken["rejectReasonRequired"] = True
    _add_feature(spec, "报名审核驳回理由必填")

    ticket["notifyOnApplySuccess"] = True
    labels.setdefault("applySuccessInboxTitle", "报名已提交")
    labels.setdefault(
        "applySuccessInboxBody",
        "「{subject}」已提交，请留意审核结果站内信。",
    )
    thicken["applySuccessInbox"] = True
    _add_feature(spec, "报名成功站内信")

    schema.setdefault("stockTightBelow", 3)
    labels.setdefault("stockTightHint", "余量紧张，请尽快提交")
    thicken["stockTight"] = True
    _add_feature(spec, "名额紧张提示")

    # 复用招聘皮批量审 API；文案换成报名口径（材料序列图跟 labels）
    ticket["allowBatchHire"] = True
    labels.setdefault("batchHireLabel", "批量通过")
    labels.setdefault("batchRejectLabel", "批量驳回")
    thicken["batchApprove"] = True
    _add_feature(spec, "报名审核批量通过驳回")

    labels.setdefault(
        "waitlistPromoteHint",
        "名额空出后，候补将按提交顺序自动转为待审并站内通知。",
    )
    thicken["waitlistPromote"] = True
    _add_feature(spec, "候补自动递补占额")
    _add_feature(spec, "活动候补转正站内信")

    # —— ACTIVITY ——
    if domain == "DOM-ACTIVITY":
        _ensure_archive_field(
            archive,
            {"key": "checkinPlace", "label": "签到地点", "type": "string"},
        )
        _ensure_archive_field(
            archive,
            {"key": "sessionGroup", "label": "场次/分组", "type": "string"},
        )
        _ensure_archive_field(
            archive,
            {"key": "applyInviteCode", "label": "报名口令", "type": "string"},
        )
        _ensure_archive_field(
            archive,
            {"key": "sponsorNote", "label": "赞助商展示", "type": "string"},
        )
        _ensure_archive_field(
            archive,
            {"key": "groupPriceNote", "label": "团体票价说明", "type": "textarea"},
        )
        _ensure_archive_field(
            archive,
            {"key": "feeYuan", "label": "报名费（元）", "type": "number"},
        )
        _ensure_archive_field(
            archive,
            {
                "key": "allowedGender",
                "label": "限性别",
                "type": "select",
                "options": ["不限", "男", "女"],
            },
        )
        _ensure_archive_field(
            archive,
            {"key": "allowedGrades", "label": "限年级（逗号分隔）", "type": "string"},
        )
        ticket.setdefault("cancelBeforeHours", 24)
        labels.setdefault(
            "cancelBeforeHint",
            "活动开始前规定时限内可取消报名；临近开始后不可自行取消。",
        )
        ticket["requireInsuranceAck"] = True
        labels.setdefault("insuranceAckLabel", "我已阅读并同意安全责任书要点")
        ticket["requireApplyInvite"] = True
        labels.setdefault("applyInviteLabel", "报名口令")
        labels.setdefault("applyInviteHint", "请填写本场活动报名口令后再提交。")
        ticket["allowDeposit"] = True
        labels.setdefault("depositLabel", "报名费（演示登记，非商户支付）")
        ticket["bedConstraint"] = True
        labels.setdefault(
            "bedConstraintNeedMessage",
            "请先在个人资料填写性别与年级后再报名。",
        )
        labels.setdefault(
            "bedConstraintDenyMessage",
            "当前资料不符合本场活动的年级或身份限制，请改选其他场次。",
        )
        labels.setdefault(
            "sessionGroupHint",
            "同一活动可按场次/分组分别报名，请核对所选场次。",
        )
        ticket["requirePriceNoteAck"] = True
        ticket["requireSponsorAck"] = True
        labels.setdefault("priceNoteAckLabel", "我已阅读团体票价说明")
        labels.setdefault("sponsorAckLabel", "我已知晓本场赞助说明")
        thicken["checkinPlace"] = True
        thicken["cancelBeforeHours"] = True
        thicken["safetyAck"] = True
        thicken["sessionGroup"] = True
        thicken["applyInvite"] = True
        thicken["feeDemo"] = True
        thicken["gradeLimit"] = True
        thicken["sponsorNote"] = True
        thicken["groupPriceNote"] = True
        thicken["priceNoteAck"] = True
        thicken["sponsorAck"] = True
        ticket["allowLateMinutes"] = True
        labels.setdefault("lateMinutesLabel", "迟到分钟数")
        labels.setdefault(
            "lateMinutesHint",
            "签到时可登记相对集合时间的迟到分钟数（演示登记）。",
        )
        thicken["lateMinutes"] = True
        _add_feature(spec, "活动签到地点字段")
        _add_feature(spec, "活动取消开始前时限")
        _add_feature(spec, "安全责任书勾选")
        _add_feature(spec, "活动分场次分组报名")
        _add_feature(spec, "报名邀请码口令报名")
        _add_feature(spec, "报名费演示登记")
        _add_feature(spec, "年级身份资格限制")
        _add_feature(spec, "活动赞助商展示位")
        _add_feature(spec, "团体票价说明")
        _add_feature(spec, "活动签到迟到分钟数登记")

    # —— LOST ——
    if domain == "DOM-LOST":
        _ensure_archive_field(
            archive,
            {
                "key": "stage",
                "label": "启事状态",
                "type": "select",
                "options": ["招领中", "已认领", "已下架"],
            },
        )
        _ensure_archive_field(
            archive,
            {"key": "expireOn", "label": "启事到期日", "type": "date"},
        )
        _ensure_archive_field(
            archive,
            {"key": "bountyNote", "label": "悬赏说明（非支付）", "type": "string"},
        )
        _ensure_archive_field(
            archive,
            {
                "key": "lostCategory",
                "label": "失物分类",
                "type": "select",
                "options": ["卡证", "数码", "衣物", "证件", "其他"],
            },
        )
        _ensure_archive_field(
            archive,
            {"key": "viewCount", "label": "浏览次数", "type": "number"},
        )
        _ensure_archive_field(
            archive,
            {"key": "feeYuan", "label": "认领押金（元）", "type": "number"},
        )
        ticket["preferredSlot"] = True
        ticket["allowMeetingPlace"] = True
        ticket["requireMeetingAck"] = True
        ticket["allowDeposit"] = True
        ticket.setdefault("claimCooldownHours", 2)
        labels.setdefault("preferredSlotLabel", "约定面交时间")
        labels.setdefault("meetingPlaceLabel", "约定面交地点")
        labels.setdefault(
            "meetingAckLabel",
            "我已与对方约定面交时间与地点",
        )
        labels.setdefault(
            "ownerMeetingAckLabel",
            "启事方确认面交安排",
        )
        labels.setdefault(
            "claimAutoOffHint",
            "认领审核通过后启事自动下架，余量清零。",
        )
        labels.setdefault(
            "expireOffHint",
            "超过启事到期日后自动下架，不再接受新认领。",
        )
        labels.setdefault(
            "claimCooldownHint",
            "启事发布后需经过冷却期才可提交认领，避免秒认。",
        )
        labels.setdefault("depositLabel", "认领押金（演示登记，非商户支付）")
        _force_material_check(
            spec,
            schema,
            title="认领证件材料",
            lead="维护认领须出示的证件类型；申请人按清单上传，缺件不可提交。",
        )
        thicken["claimAutoOff"] = True
        thicken["expireOff"] = True
        thicken["bountyNote"] = True
        thicken["meetingPlace"] = True
        thicken["claimCooldown"] = True
        thicken["lostCategory"] = True
        thicken["viewCount"] = True
        thicken["meetingAck"] = True
        thicken["claimDeposit"] = True
        thicken["claimMaterial"] = True
        _add_feature(spec, "认领成功自动下架启事")
        _add_feature(spec, "失物启事过期自动关闭")
        _add_feature(spec, "失物悬赏备注字段")
        _add_feature(spec, "失物面交地点时间约定")
        _add_feature(spec, "认领冷却期")
        _add_feature(spec, "失物分类字典")
        _add_feature(spec, "失物启事浏览计数")
        _add_feature(spec, "认领面交双方确认勾选")
        _add_feature(spec, "失物认领押金演示")
        _add_feature(spec, "失物认领证件材料清单")

    # —— COURSE ——
    if domain == "DOM-COURSE":
        _ensure_archive_field(
            archive,
            {"key": "textbook", "label": "教材信息", "type": "string"},
        )
        _ensure_archive_field(
            archive,
            {
                "key": "courseKind",
                "label": "课程属性",
                "type": "select",
                "options": ["必修", "选修", "通识"],
            },
        )
        _ensure_archive_field(
            archive,
            {"key": "prereqCode", "label": "先修课提示码", "type": "string"},
        )
        _ensure_archive_field(
            archive,
            {"key": "college", "label": "开课学院", "type": "string"},
        )
        _ensure_archive_field(
            archive,
            {"key": "planUrl", "label": "培养方案外链", "type": "url"},
        )
        _ensure_archive_field(
            archive,
            {
                "key": "allowedGender",
                "label": "限性别",
                "type": "select",
                "options": ["不限", "男", "女"],
            },
        )
        _ensure_archive_field(
            archive,
            {"key": "allowedGrades", "label": "限年级（逗号分隔）", "type": "string"},
        )
        ticket.setdefault("semesterCreditCap", 30)
        ticket.setdefault("creditWarnRemaining", 4)
        ticket.setdefault("maxDropTimes", 3)
        ticket["bedConstraint"] = True
        labels.setdefault(
            "creditCapHint",
            "已选学分合计不可超过本学期上限；接近上限时会提示。",
        )
        labels.setdefault(
            "creditWarnHint",
            "所选学分已接近学期上限，请留意剩余额度。",
        )
        labels.setdefault(
            "maxDropHint",
            "本学期退选次数有上限，请谨慎操作。",
        )
        labels.setdefault(
            "prereqHint",
            "请确认已具备先修基础；系统按提示码做弱提示，不强制拦截。",
        )
        labels.setdefault(
            "courseKindHint",
            "列表按必修/选修/通识区分，便于对照培养方案结构（非完整方案引擎）。",
        )
        labels.setdefault(
            "bedConstraintNeedMessage",
            "请先在个人资料填写性别与年级后再选课。",
        )
        labels.setdefault(
            "bedConstraintDenyMessage",
            "当前资料不符合本课的年级或身份限制，请改选其他课程。",
        )
        labels.setdefault("collegeFilterHint", "可按开课学院筛选课程。")
        labels.setdefault("planUrlHint", "培养方案说明见外链，请先打开查阅。")
        ticket["requirePlanAck"] = True
        labels.setdefault("planAckLabel", "我已查阅培养方案外链")
        ticket["requirePrereqAck"] = True
        labels.setdefault(
            "prereqAckLabel",
            "我确认已具备先修基础（有提示码时须勾选）",
        )
        labels.setdefault(
            "prereqHardHint",
            "本课开启先修确认：档案有先修提示码时须勾选后才能提交。",
        )
        thicken["textbook"] = True
        thicken["creditCap"] = True
        thicken["maxDrop"] = True
        thicken["prereqHint"] = True
        thicken["courseKind"] = True
        thicken["college"] = True
        thicken["planUrl"] = True
        thicken["gradeLimit"] = True
        thicken["planAck"] = True
        thicken["prereqHard"] = True
        _add_feature(spec, "选课教材信息字段")
        _add_feature(spec, "选课学分上限")
        _add_feature(spec, "选课学分预警")
        _add_feature(spec, "退选次数上限")
        _add_feature(spec, "先修课提示")
        _add_feature(spec, "培养方案学分结构提示")
        _add_feature(spec, "选课开课学院筛选")
        _add_feature(spec, "选课培养方案外链")
        _add_feature(spec, "年级身份资格限制")
        _add_feature(spec, "选课先修课硬确认")

    # —— TOUR ——
    if domain == "DOM-TOUR":
        _ensure_archive_field(
            archive,
            {"key": "dayItinerary", "label": "行程日明细（D1/D2）", "type": "textarea"},
        )
        _ensure_archive_field(
            archive,
            {"key": "leaderContact", "label": "领队联系方式", "type": "string"},
        )
        _ensure_archive_field(
            archive,
            {"key": "meetingPoint", "label": "出团集合点", "type": "string"},
        )
        _ensure_archive_field(
            archive,
            {"key": "minGroupSize", "label": "成团最低人数", "type": "number"},
        )
        _ensure_archive_field(
            archive,
            {"key": "singleRoomNote", "label": "单房差说明", "type": "textarea"},
        )
        _ensure_archive_field(
            archive,
            {"key": "groupPriceNote", "label": "团体票价说明", "type": "textarea"},
        )
        _ensure_archive_field(
            archive,
            {"key": "feeYuan", "label": "报名费（元）", "type": "number"},
        )
        _ensure_archive_field(
            archive,
            {"key": "minAge", "label": "最低年龄", "type": "number"},
        )
        _ensure_archive_field(
            archive,
            {"key": "maxAge", "label": "最高年龄", "type": "number"},
        )
        ticket["allowEmergencyContact"] = True
        ticket["requireInsuranceAck"] = True
        ticket["allowWaitlist"] = True
        ticket["allowDeposit"] = True
        ticket["ageConstraint"] = True
        labels.setdefault("emergencyContactLabel", "紧急联系人")
        labels.setdefault("emergencyPhoneLabel", "紧急联系电话")
        labels.setdefault("insuranceAckLabel", "我已阅读出行保险声明（非保单系统）")
        labels.setdefault(
            "minGroupHint",
            "未达成团最低人数时线路可能调整，以计调通知为准（不强制关团）。",
        )
        labels.setdefault("depositLabel", "线路费用（演示登记，非商户支付）")
        labels.setdefault(
            "waitlistPromoteHint",
            "名额空出后，候补将按提交顺序自动转为待审并站内通知。",
        )
        labels.setdefault(
            "ageConstraintNeedMessage",
            "请先在个人资料填写年龄后再报名本线路。",
        )
        labels.setdefault(
            "ageConstraintDenyMessage",
            "当前年龄不符合本线路限制，请改选其他线路。",
        )
        labels.setdefault(
            "insuranceExportHint",
            "出团名单导出含保险声明勾选列，便于核对。",
        )
        ticket["requirePriceNoteAck"] = True
        labels.setdefault("priceNoteAckLabel", "我已阅读团体票价与单房差说明")
        _force_material_check(
            spec,
            schema,
            title="出团前资料清单",
            lead="维护护照复印件等出团资料项；团员按清单上传，缺件不可提交。",
        )
        thicken["dayItinerary"] = True
        thicken["leaderContact"] = True
        thicken["meetingPoint"] = True
        thicken["emergencyContact"] = True
        thicken["insuranceAck"] = True
        thicken["minGroupSize"] = True
        thicken["singleRoomNote"] = True
        thicken["groupPriceNote"] = True
        thicken["feeDemo"] = True
        thicken["tourWaitlist"] = True
        thicken["tourRosterExport"] = True
        thicken["priceNoteAck"] = True
        thicken["ageLimit"] = True
        thicken["tourMaterial"] = True
        thicken["insuranceExport"] = True
        _add_feature(spec, "线路行程日明细")
        _add_feature(spec, "出团领队联系方式字段")
        _add_feature(spec, "出团集合点字段")
        _add_feature(spec, "线路报名紧急联系人")
        _add_feature(spec, "保险声明勾选")
        _add_feature(spec, "线路成团最低人数提示")
        _add_feature(spec, "线路单房差说明")
        _add_feature(spec, "团体票价说明")
        _add_feature(spec, "报名费演示登记")
        _add_feature(spec, "线路余位紧张候补开关")
        _add_feature(spec, "出团名单打印导出")
        _add_feature(spec, "线路报名年龄限制")
        _add_feature(spec, "出团前资料清单")
        _add_feature(spec, "团员保险名单导出列")

    return spec
