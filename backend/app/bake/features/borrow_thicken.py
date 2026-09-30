"""借用/占用组加厚：浅字段、用途字典、热门榜文案、代取、床位约束、须知勾选等。

硬约束
------
- 不新造厚 DOM；复用 archive/ticket/recommend/MessageStore/material_check。
- 域默认：通识必开（用途字典、热门借阅文案、PARCEL 代取、BED 性别年级、ASSET 预警阈值）。
- 开题扫：ISBN、保养/校准到期、押金、代收协议、行李清点/随借配件/随书光盘、报废二级审等。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

_PURPOSE_OPTS_ASSET = ("教学科研", "办公领用", "实验耗材", "活动保障", "维修更换", "其他")
_PURPOSE_OPTS_EQUIP = ("课程实验", "课题研究", "竞赛实训", "活动保障", "外出外借", "其他")

_DAMAGE_COMP_LIBRARY = (
    {"type": "图书污损", "yuan": 20},
    {"type": "图书丢失（按定价）", "yuan": 0},
    {"type": "条码损坏", "yuan": 5},
)
_DAMAGE_COMP_EQUIP = (
    {"type": "外观轻损", "yuan": 50},
    {"type": "配件丢失", "yuan": 100},
    {"type": "严重损坏（按原值）", "yuan": 0},
)

_ISBN_TERMS = ("ISBN校验", "ISBN 校验", "ISBN查重", "索书号校验", "图书查重")
_MAINTAIN_TERMS = ("保养到期", "维保到期", "设备保养提醒", "保养提醒")
_CALIB_TERMS = ("校准证书", "校检合格", "计量校准", "校准到期", "合格证到期")
_DEPOSIT_TERMS = ("设备押金", "借用押金", "押金登记", "归还退押")
_EXCEPTION_TERMS = ("异常件", "破损理赔", "包裹破损", "异常原因")
_PARCEL_ACK_TERMS = ("代收协议", "驿站协议", "取件须知勾选")
_BED_ACK_TERMS = ("入住须知", "住宿须知勾选", "床位须知")
_DISC_TERMS = ("随书附件", "随书光盘", "光盘借出", "附件光盘")
_ACCESSORY_TERMS = ("随借配件", "配件清单", "设备配件勾选")
_LUGGAGE_TERMS = ("行李清点", "退宿清点", "退宿行李")
_INSURANCE_TERMS = ("保险声明", "借用保险", "设备保险勾选")
_DUAL_REVIEW_TERMS = ("双人复核", "双人签字", "领用复核")
_SHIP_FEE_TERMS = ("寄件运费", "运费登记", "快递运费")
_CREDIT_SOFT_TERMS = ("催还计入信誉", "信誉限制再借", "限制再借")
_CREDIT_POINTS_TERMS = ("逾期扣分", "扣信誉分", "扣信用分", "信誉分扣", "信用分扣")
_CANCEL_HOLD_TERMS = ("预约取消次数", "取消预约限制", "预约取消上限")
_OVERDUE_COMP_TERMS = ("逾期自动转赔付", "超期转赔付", "逾期转赔偿")
_ABANDON_TERMS = ("弃件", "滞留弃件", "逾期弃件")
_PROJECT_TERMS = ("课题号", "课题编号", "科研课题号")
_BED_FEE_TERMS = ("住宿费", "床位费", "预定金", "床位预定金")
_UTILITY_TERMS = ("水电清算", "退宿水电", "水电费备注")
_PEER_CONFIRM_TERMS = ("双方确认", "对向同意", "调宿双方", "互换双方确认")
_FINE_WAIVE_TERMS = ("罚款减免", "逾期减免", "罚金减免", "减免申请")
_RENEW_NO_HOLD_TERMS = ("续借须无预约", "无预约方可续借", "他人预约不可续借")
_MONTH_QUOTA_TERMS = ("领用额度", "按月限额", "每人每月", "月度领用上限")
_COUNT_LOCK_TERMS = ("盘点锁定", "盘点期间禁出入库", "盘点禁出入库")
_BLIND_COUNT_TERMS = ("盲盘", "先数后看账", "盲盘点")
_DIFF_REASON_TERMS = ("盘点差异原因", "差异原因登记", "盘点差额说明")
_ABANDON_DUAL_TERMS = ("弃件双人", "双人确认弃件", "弃件双确认")


def scan_peer_confirm(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _PEER_CONFIRM_TERMS)


def scan_fine_waive(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _FINE_WAIVE_TERMS)


def scan_renew_no_hold(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _RENEW_NO_HOLD_TERMS)


def scan_month_quota(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _MONTH_QUOTA_TERMS)


def scan_count_lock(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _COUNT_LOCK_TERMS)


def scan_blind_count(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _BLIND_COUNT_TERMS)


def scan_diff_reason(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _DIFF_REASON_TERMS)


def scan_abandon_dual(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _ABANDON_DUAL_TERMS)


def scan_isbn_validate(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _ISBN_TERMS)


def scan_maintain_due(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _MAINTAIN_TERMS)


def scan_calib_due(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _CALIB_TERMS)


def scan_equip_deposit(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _DEPOSIT_TERMS)


def scan_parcel_exception(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _EXCEPTION_TERMS)


def scan_parcel_notice_ack(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _PARCEL_ACK_TERMS)


def scan_bed_notice_ack(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _BED_ACK_TERMS)


def scan_book_disc(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _DISC_TERMS)


def scan_equip_accessory(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _ACCESSORY_TERMS)


def scan_bed_luggage(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _LUGGAGE_TERMS)


def scan_equip_insurance(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _INSURANCE_TERMS)


def scan_dual_review(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _DUAL_REVIEW_TERMS)


def scan_ship_fee(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _SHIP_FEE_TERMS)


def scan_credit_score(text: str) -> bool:
    """软信誉：限制再借/次数冻结（不要求分值列）。"""
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _CREDIT_SOFT_TERMS)


def scan_credit_points(text: str) -> bool:
    """分值信誉：信誉分/信用分、逾期扣分、低于 N 停借。"""
    import re

    raw = text or ""
    if any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _CREDIT_POINTS_TERMS):
        return True
    if "信誉分" in raw or "信用分" in raw:
        return True
    if re.search(r"低于\s*\d+\s*.{0,8}停借", raw):
        return True
    return False


def _parse_credit_nums(text: str) -> tuple[int, int, int]:
    """从开题抽初始分/扣分/停借线；缺省 100 / 5 / 60。"""
    import re

    raw = text or ""
    initial, delta, block = 100, 5, 60
    m = re.search(r"(?:信誉分|信用分)\s*[：:为]?\s*(\d{2,3})", raw)
    if m:
        initial = max(1, min(999, int(m.group(1))))
    m = re.search(r"(?:逾期|超期)?(?:每次)?扣\s*(\d{1,3})\s*分", raw)
    if m:
        delta = max(1, min(100, int(m.group(1))))
    m = re.search(r"低于\s*(\d{1,3})\s*.{0,8}停借", raw)
    if m:
        block = max(0, min(999, int(m.group(1))))
    return initial, delta, block


def _enable_credit_points(
    spec: dict[str, Any],
    ticket: dict[str, Any],
    labels: dict[str, Any],
    thicken: dict[str, Any],
    text: str,
) -> None:
    initial, delta, block = _parse_credit_nums(text)
    ticket["creditOnOverdue"] = True
    ticket["creditInitial"] = initial
    ticket["creditOverdueDelta"] = delta
    ticket["creditBlockBelow"] = block
    ticket.setdefault("maxOverdueTimes", 3)
    labels.setdefault(
        "creditRuleHint",
        f"初始信誉分 {initial}；逾期每单扣 {delta} 分；低于 {block} 分暂不可再借。",
    )
    labels.setdefault("creditScoreLabel", "信誉分")
    thicken["creditOnOverdue"] = True
    thicken["creditPoints"] = True
    _add_feature(spec, "超期催还计入信誉分")


def scan_cancel_hold_limit(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _CANCEL_HOLD_TERMS)


def scan_overdue_compensate(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _OVERDUE_COMP_TERMS)


def scan_parcel_abandon(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _ABANDON_TERMS)


def scan_project_no(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _PROJECT_TERMS)


def scan_bed_fee(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _BED_FEE_TERMS)


def scan_utility_note(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _UTILITY_TERMS)


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


def _live_schema(spec: dict[str, Any]) -> dict[str, Any]:
    """原地取 schema，禁止浅拷贝后再写回（否则会冲掉 _force_* 挂上的顶层键）。"""
    schema = spec.get("schema")
    if not isinstance(schema, dict):
        schema = {}
        spec["schema"] = schema
    return schema


def _force_material_check(spec: dict[str, Any], *, title: str, lead: str) -> None:
    """扫词挂材料清单岛（行李/配件/光盘等变体）。"""
    from app.bake.features.ticket_flow_opts import MATERIAL_CHECK_CAP, attach_material_check_menus

    _ensure_cap(spec, MATERIAL_CHECK_CAP)
    schema = _live_schema(spec)
    attach_material_check_menus(schema)
    labels = schema.setdefault("labels", {})
    labels["materialChecklistTitle"] = title
    labels["materialChecklistLead"] = lead
    _add_feature(spec, title)


def apply_borrow_thicken_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """按域默认 + 开题扫词加厚借用组 schema（只增不减）。"""
    domain = str(spec.get("domain") or "")
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
    thicken = schema.setdefault("borrowThicken", {})
    if not isinstance(thicken, dict):
        thicken = {}
        schema["borrowThicken"] = thicken

    # —— LIBRARY ——
    if domain == "DOM-LIBRARY":
        labels["recommendSectionTitle"] = "热门借阅"
        labels["recommendLatestHint"] = "新书上架"
        thicken["hotLoanBoard"] = True
        _add_feature(spec, "热门借阅榜")
        _ensure_archive_field(
            archive, {"key": "holdingLoc", "label": "馆藏地点", "type": "string"}
        )
        _ensure_archive_field(
            archive, {"key": "campusZone", "label": "分馆/校区", "type": "string"}
        )
        _ensure_archive_field(
            archive, {"key": "clcCode", "label": "中图法简码", "type": "string"}
        )
        thicken["clcCode"] = True
        _add_feature(spec, "中图法简码字段")
        schema["damageCompStandards"] = list(
            schema.get("damageCompStandards") or _DAMAGE_COMP_LIBRARY
        )
        labels.setdefault(
            "damageCompHint",
            "污损/丢失按赔偿标准表登记；定价类按图书原价。",
        )
        thicken["damageCompTable"] = True
        _add_feature(spec, "损坏赔偿标准表")
        labels.setdefault(
            "creditRuleHint",
            "超期催还累计计入读者信誉；达到次数上限后可能限制再借，细则见公告。",
        )
        thicken["creditRuleHint"] = True
        # 双端次数方案：用户借还写库产生 ever_overdue；管理按次数限制再借
        ticket.setdefault("maxOverdueTimes", 3)
        _add_feature(spec, "读者信用分规则提示")
        if scan_credit_points(text):
            _enable_credit_points(spec, ticket, labels, thicken, text)
        labels.setdefault(
            "suggestBudgetHint",
            "荐购采纳受本学期预算余额约束，余额不足时可能暂缓或驳回。",
        )
        # 双端：用户提交荐购写库；管理端审核台账（能力+菜单+gate 同挂）
        # 荐购无域默认：须开题扫到荐购词才挂 cap，避免绕开 E-13 扫词门禁
        from app.bake.features.book_suggest import scan_book_suggest

        if scan_book_suggest(text):
            caps = list(spec.get("capabilities") or [])
            if "book_suggest" not in caps:
                caps.append("book_suggest")
            spec["capabilities"] = caps
            schema["capabilities"] = caps
            from app.bake.features.book_suggest import attach_book_suggest_menus
            from app.bake.gate_contracts import merge_book_suggest_gate

            attach_book_suggest_menus(schema)
            spec["gate"] = merge_book_suggest_gate(dict(spec.get("gate") or {}), caps)
            _add_feature(spec, "图书荐购")
        thicken["suggestBudget"] = True
        _add_feature(spec, "图书荐购预算余额提示")
        labels.setdefault(
            "closedStackPrintHint",
            "闭架索书可打印本页清单，持单至书库取书；请先在线提交借阅申请。",
        )
        thicken["closedStackPrint"] = True
        _add_feature(spec, "图书闭架索书单打印提示")
        labels.setdefault(
            "shelfAnnounceHint",
            "新书上架后请关注公告；可将新书加入收藏以便再次借阅。",
        )
        thicken["shelfAnnounce"] = True
        _add_feature(spec, "新书/新物资上架通报提示")
        labels.setdefault(
            "catalogImportHint",
            "征订目录管理端可导入 CSV；读者亦可提交荐购产生需求数据。",
        )
        thicken["catalogImportHint"] = True
        _add_feature(spec, "图书征订目录导入提示")
        ticket["requireNoticeAck"] = True
        labels.setdefault("noticeAckLabel", "我已阅读借阅须知与信用分规则")
        # 漂流/赠阅：并入 stage 选项
        for f in archive.get("fields") or []:
            if isinstance(f, dict) and f.get("key") == "stage" and isinstance(f.get("options"), list):
                for opt in ("漂流", "赠阅"):
                    if opt not in f["options"]:
                        f["options"].append(opt)
                break
        else:
            _ensure_archive_field(
                archive,
                {
                    "key": "stage",
                    "label": "馆藏标记",
                    "type": "select",
                    "options": ["在架", "借出", "漂流", "赠阅", "下架"],
                },
            )
        thicken["driftTag"] = True
        _add_feature(spec, "馆藏地点与分馆")
        labels.setdefault(
            "closedLoanHint",
            "寒暑假或闭馆期间请关注公告；开放后再办理借还。",
        )
        thicken["closedLoanHint"] = True
        # 多册合借：域默认已有 allowQty；统一册数文案
        ticket["allowQty"] = True
        ticket["qtyLabel"] = "册数"
        thicken["multiCopyLoan"] = True
        _add_feature(spec, "多册合借一单")
        if scan_isbn_validate(text):
            thicken["isbnValidate"] = True
            _add_feature(spec, "ISBN校验与查重提示")
        if scan_book_disc(text):
            _force_material_check(
                spec,
                title="随书附件清单",
                lead="有光盘/附件的图书借出时须勾选随附材料并上传凭证。",
            )
            thicken["bookDiscChecklist"] = True
        if scan_credit_score(text):
            ticket.setdefault("maxOverdueTimes", 3)
            labels.setdefault(
                "creditRuleHint",
                "超期催还累计计入信誉；达到次数上限后可能限制再借。",
            )
        if scan_credit_points(text):
            _enable_credit_points(spec, ticket, labels, thicken, text)
        if scan_cancel_hold_limit(text):
            ticket["maxCancelHolds"] = int(ticket.get("maxCancelHolds") or 3)
            thicken["maxCancelHolds"] = True
            _add_feature(spec, "预约取消次数限制")
        if scan_fine_waive(text):
            ticket["allowFineWaive"] = True
            labels.setdefault("fineWaiveLabel", "罚款减免")
            thicken["fineWaive"] = True
            _add_feature(spec, "逾期罚款减免")
        if scan_renew_no_hold(text):
            ticket["renewBlockIfHeld"] = True
            thicken["renewBlockIfHeld"] = True
            _add_feature(spec, "续借须无他人预约")

    # —— EQUIP ——
    if domain == "DOM-EQUIP":
        labels["recommendSectionTitle"] = "热门设备"
        labels["recommendLatestHint"] = "新上架设备"
        thicken["hotLoanBoard"] = True
        _add_feature(spec, "热门借阅榜")
        ticket["requireRemark"] = True
        ticket["remarkLabel"] = "用途说明"
        ticket["remarkOptions"] = list(
            ticket.get("remarkOptions") or _PURPOSE_OPTS_EQUIP
        )
        thicken["purposeDict"] = True
        _add_feature(spec, "常用用途字典")
        _ensure_archive_field(
            archive, {"key": "shelfNo", "label": "存放货架号", "type": "string"}
        )
        _ensure_archive_field(
            archive, {"key": "campusZone", "label": "校区/存放点", "type": "string"}
        )
        _ensure_archive_field(
            archive, {"key": "calibCertUrl", "label": "校检合格证附件", "type": "string"}
        )
        _ensure_archive_field(
            archive, {"key": "repairTicketNo", "label": "关联报修单号", "type": "string"}
        )
        thicken["calibCert"] = True
        thicken["repairLink"] = True
        _add_feature(spec, "设备校检合格证附件槽")
        _add_feature(spec, "设备故障转报修单号")
        schema["damageCompStandards"] = list(
            schema.get("damageCompStandards") or _DAMAGE_COMP_EQUIP
        )
        labels.setdefault(
            "damageCompHint",
            "损坏按赔偿标准表登记；严重损坏按设备原值评估。",
        )
        thicken["damageCompTable"] = True
        _add_feature(spec, "损坏赔偿标准表")
        labels.setdefault(
            "contractTemplateHint",
            "外借须确认借用合同要点；同意后勾选提交，合同扫描件可作附件上传。",
        )
        # 双端：用户勾选 notice_ack 写库；管理端维护合同说明文案
        ticket["requireNoticeAck"] = True
        labels.setdefault("noticeAckLabel", "我已阅读并同意设备借用合同要点")
        thicken["contractAck"] = True
        _add_feature(spec, "设备借用合同模板说明")
        labels.setdefault(
            "equipQrPrintHint",
            "管理端可打印设备标签；借用时请手输资产编号以便核对。",
        )
        ticket["allowAssetCode"] = True
        labels.setdefault("assetCodeLabel", "设备资产编号")
        thicken["equipQr"] = True
        _add_feature(spec, "设备标签二维码打印说明")
        labels.setdefault(
            "maintainWorkOrderHint",
            "保养到期请在档案维护关联报修单号；借用申请可备注保养需求。",
        )
        _ensure_archive_field(
            archive, {"key": "maintainDue", "label": "保养到期日", "type": "date"}
        )
        thicken["maintainDue"] = True
        thicken["maintainWorkOrder"] = True
        _add_feature(spec, "设备保养工单联动说明")
        if scan_maintain_due(text) or scan_calib_due(text):
            pass  # maintainDue 已域默认
        if scan_calib_due(text):
            _ensure_archive_field(
                archive, {"key": "calibDue", "label": "校准证书到期日", "type": "date"}
            )
            ticket["blockIfCalibExpired"] = True
            thicken["calibDueBlock"] = True
            _add_feature(spec, "校准证书到期停借")
        if scan_equip_deposit(text):
            ticket["allowDeposit"] = True
            labels.setdefault("depositLabel", "借用押金（元）")
            thicken["equipDeposit"] = True
            _add_feature(spec, "设备押金登记")
        ticket.setdefault("requireTrainingAck", True)
        thicken["trainingAck"] = True
        _add_feature(spec, "借用须培训合格勾选")
        if scan_equip_insurance(text):
            ticket["requireInsuranceAck"] = True
            labels.setdefault("insuranceAckLabel", "我已阅读设备借用保险声明")
            thicken["insuranceAck"] = True
            _add_feature(spec, "设备借用保险声明勾选")
        _ensure_archive_field(
            archive, {"key": "loanOrg", "label": "外借单位（校外）", "type": "string"}
        )
        if scan_equip_accessory(text):
            _force_material_check(
                spec,
                title="随借配件清单",
                lead="借用时勾选随附配件并上传清点照片，归还时对照核验。",
            )
            thicken["accessoryChecklist"] = True
        if scan_credit_score(text):
            ticket.setdefault("maxOverdueTimes", 3)
            labels.setdefault(
                "creditRuleHint",
                "超期催还累计计入借用信誉；达到次数上限后可能限制再借，细则见公告。",
            )
        if scan_credit_points(text):
            _enable_credit_points(spec, ticket, labels, thicken, text)
        if scan_overdue_compensate(text):
            ticket["overdueAutoCompensate"] = True
            thicken["overdueAutoCompensate"] = True
            _add_feature(spec, "设备归还逾期自动转赔付")

    # —— ASSET ——
    if domain == "DOM-ASSET":
        ticket["requireRemark"] = True
        ticket.setdefault("remarkLabel", "用途说明")
        ticket["remarkOptions"] = list(
            ticket.get("remarkOptions") or _PURPOSE_OPTS_ASSET
        )
        thicken["purposeDict"] = True
        _add_feature(spec, "常用用途字典")
        try:
            below = int(schema.get("stockWarnBelow") or 0)
        except (TypeError, ValueError):
            below = 0
        if below <= 0:
            schema["stockWarnBelow"] = 10
        thicken["stockWarnConfigurable"] = True
        _add_feature(spec, "物资安全库存下限")
        _ensure_archive_field(
            archive, {"key": "shelfNo", "label": "库位/货架号", "type": "string"}
        )
        _ensure_archive_field(
            archive, {"key": "campusZone", "label": "分仓/校区", "type": "string"}
        )
        _ensure_archive_field(
            archive, {"key": "batchNo", "label": "批次号", "type": "string"}
        )
        _ensure_archive_field(
            archive, {"key": "expireOn", "label": "有效期", "type": "date"}
        )
        _ensure_archive_field(
            archive, {"key": "supplierContact", "label": "供应商联系人", "type": "string"}
        )
        _add_feature(spec, "批次号与有效期")
        _add_feature(spec, "库位货架号")
        labels.setdefault(
            "procureToAssetHint",
            "填写申购单号后，管理员可确认申购转入领用。",
        )
        ticket["allowProcureRef"] = True
        labels.setdefault("procureRefLabel", "申购单号")
        labels.setdefault("confirmProcureTransferLabel", "确认申购转入")
        thicken["procureRef"] = True
        _add_feature(spec, "申购转领用衔接")
        labels.setdefault(
            "shelfAnnounceHint",
            "新物资上架后可在公告栏发布通报。",
        )
        labels.setdefault(
            "countDiffReasonHint",
            "盘点结束时可登记差异原因，便于对账。",
        )
        labels.setdefault(
            "countLockHint",
            "盘点锁定期间请暂停出入库操作，解锁后再办理。",
        )
        labels.setdefault(
            "blindCountHint",
            "盲盘时先清点实物再对照账面，避免先看账。",
        )
        if scan_project_no(text):
            ticket["allowProjectNo"] = True
            labels.setdefault("projectNoLabel", "课题号")
            thicken["projectNo"] = True
            _add_feature(spec, "领用用途与课题号")
        if scan_dual_review(text):
            ticket["allowDualReview"] = True
            labels.setdefault("dualReviewerALabel", "复核人甲")
            labels.setdefault("dualReviewerBLabel", "复核人乙")
            thicken["dualReview"] = True
            _add_feature(spec, "领用双人复核签字栏")
        # 报废：已有独立 scrap_request 审批流时不再叠领用单二级审，避免论文写两套审批
        caps_now = set(spec.get("capabilities") or [])
        scrap_opts = schema.get("stockScrapOpts") if isinstance(schema.get("stockScrapOpts"), dict) else {}
        if "stock_scrap" in caps_now and not scrap_opts.get("approveFlow"):
            ticket["twoLevelApprove"] = True
            thicken["scrapTwoLevel"] = True
            _add_feature(spec, "报废审批流（二级审）")
        if scan_month_quota(text):
            try:
                lim = int(ticket.get("categoryLimit") or 0)
            except (TypeError, ValueError):
                lim = 0
            if lim <= 0:
                ticket["categoryLimit"] = 5
            thicken["monthQuota"] = True
            _add_feature(spec, "物资领用额度（分类上限）")
        if scan_count_lock(text) or scan_blind_count(text) or scan_diff_reason(text):
            _ensure_cap(spec, "stock_io")
            _ensure_cap(spec, "stock_count")
            schema["stockCountOpts"] = dict(schema.get("stockCountOpts") or {})
            opts = schema["stockCountOpts"]
            if scan_count_lock(text):
                opts["countLock"] = True
                thicken["countLock"] = True
                _add_feature(spec, "盘点锁定禁出入库")
            if scan_blind_count(text):
                opts["blindCount"] = True
                thicken["blindCount"] = True
                _add_feature(spec, "物资盘点盲盘")
            if scan_diff_reason(text):
                opts["requireDiffReason"] = True
                thicken["requireDiffReason"] = True
                _add_feature(spec, "盘点差异原因必填")

    # —— PROCURE：申购通过后一键入库（同包浅闭环，非跨 ZIP）——
    if domain == "DOM-PROCURE":
        _ensure_cap(spec, "stock_io")
        ticket["procureToStockIn"] = True
        thicken["procureToStockIn"] = True
        labels.setdefault("toStockInLabel", "一键入库")
        labels.setdefault(
            "procureToStockInHint",
            "申购通过后可按明细一键转入库存，增加档案库存并记入库流水。",
        )
        labels.setdefault(
            "procureToAssetHint",
            "申购入库后可凭单号在领用系统衔接领用。",
        )
        from app.bake.features.stock_io import attach_stock_io_menus
        from app.bake.gate_contracts import merge_stock_io_gate

        attach_stock_io_menus(schema)
        # thicken 在 apply_stock_io 之后执行；后置补 cap 时须重挂 gate，否则论文门禁/契约缺 stock_io
        caps_now = list(spec.get("capabilities") or [])
        schema["capabilities"] = caps_now
        spec["gate"] = merge_stock_io_gate(dict(spec.get("gate") or {}), caps_now)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "入出库与库存流水" not in names:
            features.append({"name": "入出库与库存流水", "status": "flow"})
            names.add("入出库与库存流水")
        if "申购转领用一键入库" not in names:
            features.append({"name": "申购转领用一键入库", "status": "flow"})
        spec["features"] = features

    # —— PARCEL ——
    if domain == "DOM-PARCEL":
        ticket["allowProxyPickup"] = True
        labels.setdefault("proxyNameLabel", "代取人姓名")
        labels.setdefault("proxyPhoneLabel", "代取人手机")
        thicken["proxyPickup"] = True
        _add_feature(spec, "代取件登记")
        ticket.setdefault("arrivalNotify", True)
        thicken["arrivalNotify"] = True
        _add_feature(spec, "到件站内信通知")
        _ensure_archive_field(
            archive, {"key": "shelfNo", "label": "货架/格口号", "type": "string"}
        )
        _ensure_archive_field(
            archive,
            {
                "key": "slotStatus",
                "label": "格口占用",
                "type": "select",
                "options": ["空闲", "占用", "预留", "故障"],
            },
        )
        thicken["slotStatus"] = True
        _add_feature(spec, "驿站货架格口占用状态")
        labels.setdefault(
            "offHoursPickupHint",
            "营业时间外到站可能无法取件，请以站点公告为准。",
        )
        thicken["offHoursHint"] = True
        _add_feature(spec, "营业时间外取件提示")
        ticket["allowExceptionClose"] = True
        labels.setdefault("exceptionReasonLabel", "异常原因")
        labels.setdefault("damageClaimLabel", "破损理赔说明")
        thicken["parcelException"] = True
        _add_feature(spec, "包裹异常件原因")
        _add_feature(spec, "包裹破损理赔登记")
        if scan_parcel_notice_ack(text):
            ticket["requireNoticeAck"] = True
            labels.setdefault("noticeAckLabel", "我已阅读并同意代收协议")
            thicken["parcelNoticeAck"] = True
            _add_feature(spec, "驿站代收协议勾选")
        if scan_ship_fee(text):
            ticket["allowShipFee"] = True
            labels.setdefault("shipFeeLabel", "寄件运费（元）")
            thicken["shipFee"] = True
            _add_feature(spec, "驿站寄件运费登记")
        if scan_parcel_abandon(text):
            for f in archive.get("fields") or []:
                if isinstance(f, dict) and f.get("key") == "stage" and isinstance(f.get("options"), list):
                    if "弃件" not in f["options"]:
                        f["options"].append("弃件")
                    break
            else:
                _ensure_archive_field(
                    archive,
                    {
                        "key": "stage",
                        "label": "包裹状态",
                        "type": "select",
                        "options": ["在库", "待取", "已取", "滞留", "弃件"],
                    },
                )
            labels.setdefault(
                "abandonDualHint",
                "滞留弃件办结须两名站点人员确认，避免误弃。",
            )
            thicken["parcelAbandon"] = True
            _add_feature(spec, "包裹逾期弃件标记")
        if scan_abandon_dual(text):
            ticket["requireAbandonDual"] = True
            ticket["allowDualReview"] = True
            labels.setdefault("dualReviewerALabel", "弃件确认人甲")
            labels.setdefault("dualReviewerBLabel", "弃件确认人乙")
            thicken["abandonDual"] = True
            _add_feature(spec, "弃件确认双人")

    # —— BED ——
    if domain == "DOM-BED":
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
            archive, {"key": "allowedGrades", "label": "限年级（逗号分隔）", "type": "string"}
        )
        _ensure_archive_field(
            archive, {"key": "buildingZone", "label": "楼栋分区色块", "type": "string"}
        )
        thicken["bedPlanColor"] = True
        _add_feature(spec, "楼栋床位分区色块字段")
        labels.setdefault(
            "bedPlanHint",
            "列表按楼栋分区色块区分床位状态，便于对照平面示意（非 CAD）。",
        )
        labels.setdefault(
            "bedSwapHint",
            "互换意向：提交调宿并填写对方学号；对方确认后宿管方可审核。",
        )
        labels.setdefault(
            "bedPrintHint",
            "入住登记表可浏览器打印；提交申请须勾选入住须知。",
        )
        # 双端：用户写 peer_username；对方 peer_ack；管理审核
        ticket["requirePeerConfirm"] = True
        labels.setdefault("peerUsernameLabel", "对方学号/用户名")
        labels.setdefault(
            "peerConfirmHint",
            "提交后须对方先确认，宿管方可审核通过。",
        )
        labels.setdefault("peerInboxTitle", "待我确认（调宿）")
        labels.setdefault(
            "peerInboxLead",
            "他人发起的调宿/互换意向，确认后宿管才可审核；也可婉拒。",
        )
        thicken["peerConfirm"] = True
        thicken["bedSwapMatch"] = True
        _add_feature(spec, "床位互换意向双方确认")
        from app.bake.schema.menu_utils import ensure_menu

        menus = schema.setdefault("menus", {})
        user_menu = menus.setdefault("user", [])
        ensure_menu(
            user_menu,
            "peer_tickets",
            {
                "key": "peer_tickets",
                "label": labels.get("peerInboxTitle") or "待我确认（调宿）",
                "path": "/peer-tickets",
            },
            before_key="my_tickets",
        )
        ticket["bedConstraint"] = True
        labels.setdefault(
            "bedConstraintDenyMessage",
            "该床位限对应性别或年级，请改选其他床位或完善个人资料。",
        )
        labels.setdefault(
            "bedConstraintNeedMessage",
            "请先在个人资料填写性别与年级。",
        )
        thicken["bedConstraint"] = True
        _add_feature(spec, "床位性别年级约束")
        labels.setdefault(
            "bedReleaseHint",
            "调宿通过后原床位释放；退宿办结后床位恢复可申请。",
        )
        thicken["bedReleaseHint"] = True
        ticket["requireNoticeAck"] = True
        labels.setdefault("noticeAckLabel", "我已阅读入住须知")
        thicken["bedNoticeAck"] = True
        _add_feature(spec, "床位入住须知勾选")
        if scan_bed_notice_ack(text):
            pass  # 已域默认
        if scan_bed_fee(text):
            ticket["allowDeposit"] = True
            labels.setdefault("depositLabel", "住宿费/预定金（元）")
            thicken["bedFee"] = True
            _add_feature(spec, "床位住宿费与预定金登记")
        if scan_utility_note(text):
            ticket["allowUtilityNote"] = True
            labels.setdefault("utilityNoteLabel", "退宿水电清算备注")
            thicken["utilityNote"] = True
            _add_feature(spec, "退宿水电清算备注")
        if scan_bed_luggage(text):
            _force_material_check(
                spec,
                title="退宿行李清点",
                lead="退宿办结前按清单清点行李与公物，缺件须说明。",
            )
            thicken["luggageChecklist"] = True
        if scan_peer_confirm(text):
            pass  # 调宿双方确认已域默认

    ents["archive"] = archive
    ents["ticket"] = ticket
    schema["entities"] = ents
    schema["labels"] = labels
    schema["borrowThicken"] = thicken
    # material_check 可能已改 capabilities / schema
    caps = list(spec.get("capabilities") or schema.get("capabilities") or [])
    schema["capabilities"] = caps
    spec["capabilities"] = caps
    return spec
