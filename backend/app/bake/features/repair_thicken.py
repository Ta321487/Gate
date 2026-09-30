"""报修/工单组加厚：催办链、结单校验、SLA 分列、浅台账与文案。

硬约束
------
- 不新造厚 DOM；复用 ticket/deadline/content/allowRating/MessageStore。
- 催办=站内时限提醒，≠短信外呼；派单过滤≠智能派单；知识页≠ RAG。
- 域默认：通识必开（用户催办/冷却/撤催、结单摘要与原因、紧急排序、时间轴等）。
- 开题扫：备件台账、报价确认、知识沉淀、远程协助、合并工单等。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

REPAIR_DOMAINS = frozenset({"DOM-DORM", "DOM-PROPERTY", "DOM-IT"})

_PARTS_TERMS = ("备件出库", "耗材出库", "备件登记", "耗材台账", "备件不足")
_QUOTE_TERMS = ("维修报价", "报价确认", "材料费", "维修费用确认")
_FAQ_TERMS = ("常见问题", "知识库", "自助排查", "常见故障")
_KNOWLEDGE_TERMS = ("知识沉淀", "写入常见问题", "知识条目", "关联知识")
_REMOTE_TERMS = ("远程协助", "会议号", "远程会议")
_MERGE_TERMS = ("工单合并", "重复工单合并", "主从工单")
_SERIAL_TERMS = ("备件序列号", "序列号登记")
_ROSTER_TERMS = ("值班表", "排班冲突", "值班冲突")
_ASSET_TERMS = ("资产编号", "扫码录入", "终端编号")
_SKILL_TERMS = ("技能标签", "维修技能", "按技能派单")


def scan_parts_ledger(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _PARTS_TERMS)


def scan_quote_confirm(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _QUOTE_TERMS)


def scan_faq_page(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _FAQ_TERMS)


def scan_knowledge_deposit(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _KNOWLEDGE_TERMS)


def scan_remote_assist(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _REMOTE_TERMS)


def scan_ticket_merge(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _MERGE_TERMS)


def scan_serial_no(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _SERIAL_TERMS)


def scan_roster_hint(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _ROSTER_TERMS)


def scan_asset_code(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _ASSET_TERMS)


def scan_skill_tag(text: str) -> bool:
    return any(keyword_mentioned(text or "", kw, ignore_contrast=True) for kw in _SKILL_TERMS)


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


def _ensure_user_menu(schema: dict[str, Any], key: str, label: str) -> None:
    menus = schema.setdefault("menus", {})
    if not isinstance(menus, dict):
        return
    user = menus.get("user")
    if not isinstance(user, list):
        user = []
        menus["user"] = user
    for item in user:
        if isinstance(item, dict) and item.get("key") == key:
            item.setdefault("label", label)
            return
    insert_at = 1 if user else 0
    user.insert(insert_at, {"key": key, "label": label})


def _ensure_states(ticket: dict[str, Any]) -> None:
    states = ticket.get("states")
    if not isinstance(states, dict):
        states = {}
        ticket["states"] = states
    states.setdefault("paused", "已挂起")
    states.setdefault("draft", "草稿")
    states.setdefault("cancelled", "已撤销")


def apply_repair_thicken_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """按域默认 + 开题扫词加厚报修组 schema（只增不减）。"""
    domain = str(spec.get("domain") or "")
    if domain not in REPAIR_DOMAINS:
        return spec
    text = proposal_text or ""
    schema = _live_schema(spec)
    ents = schema.setdefault("entities", {})
    ticket = ents.get("ticket") if isinstance(ents.get("ticket"), dict) else {}
    if not isinstance(ticket, dict):
        ticket = {}
        ents["ticket"] = ticket
    labels = schema.setdefault("labels", {})
    thicken = schema.setdefault("repairThicken", {})
    if not isinstance(thicken, dict):
        thicken = {}
        schema["repairThicken"] = thicken

    ticket["repairThicken"] = True
    ticket.setdefault("allowUserUrge", True)
    ticket.setdefault("urgeCooldownMinutes", 60)
    ticket.setdefault("lockUrgeAfterRate", True)
    ticket.setdefault("allowCancelUrge", True)
    ticket.setdefault("requireFaultReason", True)
    ticket.setdefault("requireCloseSummary", True)
    ticket.setdefault("requireCloseAttach", True)
    ticket.setdefault("requireLowRatingRemark", True)
    ticket.setdefault("slaSplit", True)
    ticket.setdefault("escalateOnOverdue", True)
    ticket.setdefault("notifySupervisorOnOverdue", True)
    ticket.setdefault("allowHoldResume", True)
    ticket.setdefault("allowCancelDispatched", True)
    ticket.setdefault("allowTicketDraft", True)
    ticket.setdefault("allowFollowRate", True)
    ticket.setdefault("preferredSlot", True)
    ticket.setdefault("progressSubscribe", True)
    ticket.setdefault("nightUrgent", True)
    ticket.setdefault("addressReuse", True)
    ticket.setdefault("allowRating", True)
    ticket.setdefault("allowRatingTags", True)
    ticket.setdefault("printTicket", True)
    ticket.setdefault("todayBoard", True)
    ticket.setdefault("exportAttachUrls", True)
    ticket.setdefault("visitFollowup", True)
    ticket.setdefault("allowHelper", True)
    ticket.setdefault("allowAudioRemark", True)
    ticket.setdefault("allowRouteNote", True)
    ticket.setdefault("categoryColorHint", True)
    _ensure_states(ticket)
    ticket.setdefault(
        "faultReasons",
        ["线路故障", "漏水渗水", "门锁损坏", "照明故障", "网络中断", "设备损坏", "其他"],
    )
    ticket.setdefault(
        "ratingTags",
        ["态度好", "准时上门", "一次修好", "说明清楚"],
    )
    if not ticket.get("ratingDims"):
        ticket["ratingDims"] = [
            {"key": "attitude", "label": "服务态度"},
            {"key": "speed", "label": "处理效率"},
            {"key": "quality", "label": "维修质量"},
        ]
    labels.setdefault("ratingDimsTitle", "分项评价")
    labels.setdefault("ratingDimsLead", "按态度、效率、质量打分后取均值。")
    labels.setdefault("urgeLabel", "催办")
    labels.setdefault("cancelUrgeLabel", "撤销催办")
    labels.setdefault("holdLabel", "挂起")
    labels.setdefault("resumeLabel", "恢复")
    labels.setdefault("printTicketLabel", "打印工单")
    labels.setdefault("faultReasonLabel", "故障原因")
    labels.setdefault("closeSummaryLabel", "处理过程摘要")
    labels.setdefault("preferredSlotLabel", "期望上门时段")
    labels.setdefault("slaResponseLabel", "响应时限")
    labels.setdefault("slaDoneLabel", "完结时限")
    labels.setdefault(
        "ticketNoHint",
        "工单编号按提交顺序自动生成，可在列表中按编号查询。",
    )
    labels.setdefault(
        "progressTimelineHint",
        "提交、受理、转派、催办与完结会记入进度，可随时查看时间轴。",
    )
    labels.setdefault(
        "slaPageHint",
        "一般报修按处理时限跟进；紧急单优先排序。超时将升为紧急并站内通知主管。",
    )
    labels.setdefault(
        "lowRatingReasonHint",
        "评分低于 3 分时请写明原因，便于改进。",
    )
    labels.setdefault(
        "dupRepairHint",
        "同一地点、同一类型且尚未办结的报修将提示可能重复。",
    )
    labels.setdefault(
        "addressReuseHint",
        "可沿用上次填写的地点，或从地址簿里点选。",
    )
    labels.setdefault(
        "todayBoardHint",
        "记录页可筛「今日处理中」，查看本人当天工单。",
    )
    labels.setdefault(
        "workloadHint",
        "工作台按处理人汇总接单与完结数。",
    )
    labels.setdefault(
        "heatHint",
        "工作台按地点汇总未结工单，便于安排巡检。",
    )
    labels.setdefault(
        "rateInviteHint",
        "办结后可对本次服务评分；如需补充感受可再追评一次。",
    )
    labels.setdefault("helperLabel", "协助人")
    labels.setdefault("routeNoteLabel", "当日路线备注")
    thicken["core"] = True
    _add_feature(spec, "用户端催办（未超时也可记一笔）")
    _add_feature(spec, "用户催办后冷却")
    _add_feature(spec, "用户端撤销催办")
    _add_feature(spec, "评价后锁定单据不可再催")
    _add_feature(spec, "报修单满意度（单据星级）")
    _add_feature(spec, "服务态度/效率分项评价")
    _add_feature(spec, "报修满意度差评必填原因")
    _add_feature(spec, "报修评价标签")
    _add_feature(spec, "用户端满意度追评")
    _add_feature(spec, "常用故障原因字典 + 结单必选")
    _add_feature(spec, "结单必填处理过程摘要")
    _add_feature(spec, "维修前后图片对比区")
    _add_feature(spec, "紧急程度影响列表排序")
    _add_feature(spec, "报修进度时间轴")
    _add_feature(spec, "预约上门时段")
    _add_feature(spec, "SLA：响应时限与完结时限分列")
    _add_feature(spec, "维修超时自动升紧急")
    _add_feature(spec, "维修超时升级主管站内信")
    _add_feature(spec, "用户撤单（未派单前可撤）")
    _add_feature(spec, "用户端取消已派单（须理由）")
    _add_feature(spec, "维修员拒单原因登记")
    _add_feature(spec, "工单挂起/恢复")
    _add_feature(spec, "用户端草稿报修")
    _add_feature(spec, "夜间/节假日报修加急标记")
    _add_feature(spec, "工单编号规则说明")
    _add_feature(spec, "报修服务水平协议说明页")
    _add_feature(spec, "维修员工作量统计")
    _add_feature(spec, "维修员端今日工单看板")
    _add_feature(spec, "维修员拒单次数统计")
    _add_feature(spec, "转派记录留痕")
    _add_feature(spec, "报修单打印工单页")
    _add_feature(spec, "报修单导出含图片链接列")
    _add_feature(spec, "用户端进度订阅开关")
    _add_feature(spec, "报修语音备注")
    _add_feature(spec, "用户端历史报修复用上次地址")
    _add_feature(spec, "用户端历史地址簿")
    _add_feature(spec, "结单回访任务")
    _add_feature(spec, "故障现象词云式高频标签")
    _add_feature(spec, "报修分类图标/色标")
    _add_feature(spec, "多人协作工单")
    _add_feature(spec, "维修员当日路线备注")
    _add_feature(spec, "报修评价邀请延迟说明")

    ticket.setdefault("dupRoomCheck", domain in ("DOM-DORM", "DOM-PROPERTY"))
    if ticket.get("dupRoomCheck"):
        thicken["dupRoomCheck"] = True
        _add_feature(spec, "重复报修提示")

    ticket.setdefault("allowPublicArea", domain in ("DOM-DORM", "DOM-PROPERTY"))
    if ticket.get("allowPublicArea"):
        labels.setdefault("publicAreaLabel", "公共区域" if domain == "DOM-PROPERTY" else "公共卫生间/公区")
        thicken["publicArea"] = True
        _add_feature(spec, "物业公共区域报修" if domain == "DOM-PROPERTY" else "宿舍公共卫生间报修")

    if domain == "DOM-DORM":
        thicken["buildingHeat"] = True
        _add_feature(spec, "同楼栋未结工单热力简表")
        labels.setdefault("dispatchFilterHint", "派单时可按楼栋筛选处理人。")
        _add_feature(spec, "派单按区域/楼栋过滤维修员")

    if domain == "DOM-PROPERTY":
        labels.setdefault("dispatchFilterHint", "派单时可按小区/楼栋筛选处理人。")
        _add_feature(spec, "派单按区域/楼栋过滤维修员")

    if domain == "DOM-IT":
        ticket.setdefault("allowAssetCode", True)
        labels.setdefault("assetCodeLabel", "资产编号")
        thicken["assetCode"] = True
        _add_feature(spec, "资产编号扫码录入（手输码）")

    if domain in ("DOM-IT", "DOM-PROPERTY"):
        labels.setdefault(
            "faqPageHint",
            "公告栏提供常见故障说明与自助排查步骤，便于先自行核对。",
        )
        thicken["faq"] = True
        _add_feature(spec, "知识库式常见问题只读页")
        _add_feature(spec, "用户端常见故障自助排查页")
        _ensure_user_menu(schema, "content", "公告与常见问题")

    if domain in ("DOM-PROPERTY", "DOM-IT") or scan_parts_ledger(text):
        ticket["allowPartsNote"] = True
        labels.setdefault("partsNoteLabel", "备件/耗材出库")
        labels.setdefault("partsWarnHint", "结单时若未登记耗材将提示核对。")
        thicken["parts"] = True
        _add_feature(spec, "备件/耗材出库记一笔")
        _add_feature(spec, "备件不足时结单警告")

    if scan_serial_no(text) or domain in ("DOM-PROPERTY", "DOM-IT"):
        ticket["allowSerialNo"] = True
        labels.setdefault("serialNoLabel", "备件序列号")
        thicken["serial"] = True
        _add_feature(spec, "备件序列号登记")

    if scan_quote_confirm(text):
        ticket["allowQuote"] = True
        labels.setdefault("quoteLabel", "维修报价（元）")
        labels.setdefault("materialFeeLabel", "材料费（元）")
        thicken["quote"] = True
        _add_feature(spec, "维修报价用户确认")
        _add_feature(spec, "报修材料费用户确认支付")

    if scan_faq_page(text) and domain == "DOM-DORM":
        labels.setdefault("faqPageHint", "公告栏可查阅报修须知与常见情况说明。")
        _ensure_user_menu(schema, "content", "公告与常见问题")
        thicken["faq"] = True
        _add_feature(spec, "知识库式常见问题只读页")

    if scan_knowledge_deposit(text) and domain in ("DOM-IT", "DOM-PROPERTY"):
        ticket["allowKnowledgeDeposit"] = True
        labels.setdefault("knowledgeDepositLabel", "写入常见问题")
        thicken["knowledge"] = True
        _add_feature(spec, "结单知识沉淀勾选")
        _add_feature(spec, "同类知识条目关联推荐")

    if scan_remote_assist(text) or domain == "DOM-IT":
        ticket["allowRemoteUrl"] = True
        labels.setdefault("remoteUrlLabel", "远程协助备注")
        thicken["remote"] = True
        _add_feature(spec, "IT 远程协助备注")

    if scan_ticket_merge(text):
        ticket["allowTicketMerge"] = True
        labels.setdefault("parentTicketLabel", "合并到主单编号")
        thicken["merge"] = True
        _add_feature(spec, "重复工单合并")

    if scan_roster_hint(text):
        labels.setdefault("rosterConflictHint", "派单时请对照当日值班，避免与休息时段冲突。")
        thicken["rosterHint"] = True
        _add_feature(spec, "值班表冲突与报修派单提示")

    if scan_asset_code(text):
        ticket["allowAssetCode"] = True
        labels.setdefault("assetCodeLabel", "资产编号")
        thicken["assetCode"] = True
        _add_feature(spec, "资产编号扫码录入（手输码）")

    # 报修三域默认开技能标签过滤（浅名单筛，≠智能派单）；开题扫词可再钉文案
    ticket["allowSkillTag"] = True
    labels.setdefault("skillTagLabel", "技能标签")
    labels.setdefault(
        "skillFilterHint",
        "派单可按技能标签筛选处理人，不自动智能派单。",
    )
    thicken["skill"] = True
    _add_feature(spec, "维修员技能标签过滤派单")
    if scan_skill_tag(text):
        thicken["skillScanned"] = True

    spec["schema"] = schema
    return spec
