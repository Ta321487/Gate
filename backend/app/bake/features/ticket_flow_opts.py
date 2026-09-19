"""开题扫词 → 单据流程选项（两级/三级审 / 必传附件 / 材料清单 / 申报截止）。

硬约束
------
- **只增不减**：域默认已开的开关（宿舍报修两级审等）扫不到也不关掉。
- **词必须对应该功能**：裸「审核」「截止」不够；否定/本期不 不计（keyword_mentioned）。
- **截止 ≠ 借阅逾期**：本模块的「截止」是档案 ``applyDeadlineAt``（申报/报名窗口）；
  借阅 ``deadline`` / 罚金壳见 ``core_cap_scan.scan_loan_deadline``，勿在此重复扫词。
- **三级（C-16）**：固定 pending→pending_mid→pending_final→approved；非任意流程图。
- **material_check**：清单项 + requireAttach；缺件拒绝，不新开附件引擎。
"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned, pattern_mentioned

MULTI_APPROVE_CAP = "multi_approve"
WAITLIST_CAP = "waitlist"

# 候补可挂名额报名/选课类域；活动/选课另见行业默认
_WAITLIST_DOMAINS = frozenset({
    "DOM-ACTIVITY",
    "DOM-COURSE",
    "DOM-TOUR",
    "DOM-LOST",
})

_WAITLIST_TERMS = (
    "候补",
    "等位",
    "等待队列",
    "满员候补",
    "候补队列",
    "候补名单",
    "满员",
    "额满",
    "名额已满",
    "报名已满",
    "选课已满",
    "人数已满",
)

# 活动/选课行默认候补（开题常只写名额报名、漏写候补）
_WAITLIST_DEFAULT_DOMAINS = frozenset({"DOM-ACTIVITY", "DOM-COURSE"})

# —— 扫词（正向提及才算）——

_THREE_LEVEL_TERMS = (
    "三级审批",
    "三级审核",
    "三级会签",
    "三层审批",
    "三级审签",
    "初审复审终审",
    "初审、复审、终审",
    "初审复审与终审",
    "科长复审",
    "部门复审",
    "三级签批",
)

_TWO_LEVEL_TERMS = (
    "两级审批",
    "两级审核",
    "二级审批",
    "二级审核",
    "初审与终审",
    "初审终审",
    "待终审",
    "辅导员初审",
    "学院初审",
    "层层审批",
    "初审通过后",
    "终审通过",
)

_ATTACH_TERMS = (
    "上传附件",
    "上传材料",
    "附件上传",
    "必须上传",
    "上传证明",
    "上传照片",
    "现场照片",
    "佐证材料",
    "材料附件",
    "附件必传",
    "带附件提交",
    "提交附件",
)

_APPLY_DEADLINE_TERMS = (
    "报名截止",
    "申报截止",
    "申请截止",
    "选课截止",
    "截止报名",
    "截止申报",
    "截止申请",
    "报名截止日期",
    "申报截止日期",
    "申请截止日期",
)


def scan_three_level(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _THREE_LEVEL_TERMS)


def scan_two_level(text: str) -> bool:
    raw = text or ""
    if scan_three_level(raw):
        return True
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _TWO_LEVEL_TERMS)


def scan_require_attach(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _ATTACH_TERMS)


def scan_apply_deadline(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _APPLY_DEADLINE_TERMS)


def scan_waitlist(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _WAITLIST_TERMS)


def merge_waitlist_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    """候补：活动/选课行业默认；旅拍等仍须开题写到或扫到满员。只增不减。"""
    out = list(caps or [])
    if WAITLIST_CAP in out:
        return out
    if "ticket_flow" not in out or "quota" not in out:
        return out
    if (domain or "") not in _WAITLIST_DOMAINS:
        return out
    want = (domain or "") in _WAITLIST_DEFAULT_DOMAINS or scan_waitlist(
        proposal_text or ""
    )
    if not want:
        return out
    out.append(WAITLIST_CAP)
    return out


def _apply_deadline_label(text: str) -> str:
    raw = text or ""
    if keyword_mentioned(raw, "选课截止", ignore_contrast=True) or "选课" in raw:
        return "选课截止"
    if keyword_mentioned(raw, "报名截止", ignore_contrast=True) or keyword_mentioned(
        raw, "截止报名", ignore_contrast=True
    ):
        return "报名截止"
    if keyword_mentioned(raw, "申报截止", ignore_contrast=True) or keyword_mentioned(
        raw, "截止申报", ignore_contrast=True
    ):
        return "申报截止"
    return "申请截止"


def enrich_ticket_flags_from_proposal(
    flags: dict[str, Any] | None,
    proposal_text: str = "",
) -> dict[str, Any]:
    """合并开题扫到的单据开关；已有 True 保留。"""
    out = dict(flags or {})
    if scan_three_level(proposal_text):
        out["threeLevelApprove"] = True
        out["twoLevelApprove"] = True
    elif scan_two_level(proposal_text):
        out["twoLevelApprove"] = True
    if scan_require_attach(proposal_text):
        out["requireAttach"] = True
    return out


def _ensure_pending_final(ticket: dict[str, Any]) -> None:
    states = ticket.get("states")
    if not isinstance(states, dict):
        return
    if "pending_final" in states:
        return
    ordered: dict[str, str] = {}
    for k, v in states.items():
        ordered[k] = v
        if k == "pending":
            ordered["pending_final"] = "待终审"
    if "pending_final" not in ordered:
        ordered["pending_final"] = "待终审"
    ticket["states"] = ordered


def _ensure_three_level_states(ticket: dict[str, Any]) -> None:
    """pending → pending_mid → pending_final。"""
    states = ticket.get("states")
    if not isinstance(states, dict):
        return
    ordered: dict[str, str] = {}
    for k, v in states.items():
        ordered[k] = v
        if k == "pending":
            if "pending_mid" not in states:
                ordered["pending_mid"] = "待复审"
            if "pending_final" not in states:
                ordered["pending_final"] = "待终审"
    if "pending_mid" not in ordered:
        ordered["pending_mid"] = "待复审"
    if "pending_final" not in ordered:
        ordered["pending_final"] = "待终审"
    ticket["states"] = ordered
    ticket["threeLevelApprove"] = True
    ticket["twoLevelApprove"] = True


def _ensure_apply_deadline_field(
    archive: dict[str, Any], label: str, proposal_text: str = ""
) -> None:
    from app.bake.features.temporal_field import calendar_field_type

    fields = archive.get("fields")
    if not isinstance(fields, list):
        fields = []
        archive["fields"] = fields
    want = calendar_field_type(proposal_text)
    for f in fields:
        if isinstance(f, dict) and f.get("key") == "applyDeadlineAt":
            f["label"] = label
            f["type"] = want
            if want == "datetime":
                f.setdefault("timeStepMinutes", 30)
            else:
                f.pop("timeStepMinutes", None)
            return
    # 插在 stock / category 附近，避免甩在末尾难找
    insert_at = len(fields)
    for i, f in enumerate(fields):
        if isinstance(f, dict) and f.get("key") in ("stock", "status"):
            insert_at = i
            break
    row: dict[str, Any] = {"key": "applyDeadlineAt", "label": label, "type": want}
    if want == "datetime":
        row["timeStepMinutes"] = 30
    fields.insert(insert_at, row)


def apply_ticket_flow_opts_to_schema(
    schema: dict[str, Any],
    proposal_text: str = "",
    *,
    capabilities: list[str] | None = None,
) -> None:
    """就地改 schema.entities.ticket / archive；只开不开。"""
    if not isinstance(schema, dict):
        return
    text = proposal_text or ""
    caps = list(capabilities or schema.get("capabilities") or [])
    entities = schema.setdefault("entities", {})
    ticket = entities.get("ticket")
    if isinstance(ticket, dict):
        if scan_three_level(text):
            _ensure_three_level_states(ticket)
        elif scan_two_level(text):
            ticket["twoLevelApprove"] = True
            _ensure_pending_final(ticket)
        if scan_require_attach(text):
            ticket["requireAttach"] = True
        if WAITLIST_CAP in caps:
            ticket["allowWaitlist"] = True
            states = ticket.get("states")
            if isinstance(states, dict) and "waitlisted" not in states:
                ordered: dict[str, str] = {}
                for k, v in states.items():
                    ordered[k] = v
                    if k == "pending":
                        ordered["waitlisted"] = "候补中"
                if "waitlisted" not in ordered:
                    ordered["waitlisted"] = "候补中"
                ticket["states"] = ordered
            labels = schema.setdefault("labels", {})
            if isinstance(labels, dict):
                labels.setdefault("waitlistVerb", "候补报名")
                labels.setdefault("waitlistOkMessage", "名额已满，已加入候补队列")
            verbs = schema.setdefault("verbs", {})
            if isinstance(verbs, dict):
                wlab = "候补报名"
                if isinstance(labels, dict) and labels.get("waitlistVerb"):
                    wlab = str(labels.get("waitlistVerb"))
                verbs.setdefault("waitlist", wlab)

    archive = entities.get("archive")
    if isinstance(archive, dict) and scan_apply_deadline(text):
        _ensure_apply_deadline_field(archive, _apply_deadline_label(text), text)

    from app.bake.features.temporal_field import apply_soft_calendar_types

    apply_soft_calendar_types(schema, text)


def merge_multi_approve_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
) -> list[str]:
    out = list(caps or [])
    if scan_three_level(proposal_text) and MULTI_APPROVE_CAP not in out:
        out.append(MULTI_APPROVE_CAP)
    return out


def apply_ticket_flow_opts_to_spec(
    spec: dict[str, Any],
    proposal_text: str = "",
) -> dict[str, Any]:
    """挂 features 文案；schema 开关由 apply_ticket_flow_opts_to_schema 完成。"""
    text = proposal_text or ""
    caps = merge_multi_approve_capabilities(list(spec.get("capabilities") or []), text)
    caps = merge_waitlist_capabilities(
        caps, text, domain=str(spec.get("domain") or "")
    )
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    apply_ticket_flow_opts_to_schema(schema, text, capabilities=caps)
    spec = {**spec, "capabilities": caps, "schema": schema}

    features = list(spec.get("features") or [])
    names = {
        str(f.get("name") or "")
        for f in features
        if isinstance(f, dict)
    }

    def _add_feat(name: str, status: str = "module") -> None:
        if name not in names:
            features.append({"name": name, "status": status})
            names.add(name)

    ticket = ((schema.get("entities") or {}).get("ticket") or {})
    if isinstance(ticket, dict) and ticket.get("threeLevelApprove") and scan_three_level(text):
        _add_feat("三级会签审批", "flow")
    elif isinstance(ticket, dict) and ticket.get("twoLevelApprove") and scan_two_level(text):
        _add_feat("两级审批", "flow")
    if isinstance(ticket, dict) and ticket.get("requireAttach") and scan_require_attach(text):
        _add_feat("附件上传", "module")
    archive = ((schema.get("entities") or {}).get("archive") or {})
    if isinstance(archive, dict) and scan_apply_deadline(text):
        fields = archive.get("fields") or []
        if any(isinstance(f, dict) and f.get("key") == "applyDeadlineAt" for f in fields):
            _add_feat(_apply_deadline_label(text), "module")
    if WAITLIST_CAP in caps:
        _add_feat("候补", "flow")

    spec["features"] = features
    return spec


# —— 材料清单（借用族）：挂在本文件，复用 requireAttach ——

MATERIAL_CHECK_CAP = "material_check"

MATERIAL_DOMAINS: frozenset[str] = frozenset({
    "DOM-CLUB",
    "DOM-PROJ",
    "DOM-ETHIC",
    "DOM-PARTY",
    "DOM-CERT",
    "DOM-CONTRACT",
    "DOM-LABSAFE",
})

MULTI_APPROVE_DEFAULT_DOMAINS: frozenset[str] = frozenset({
    "DOM-EXPENSE",
    "DOM-CONTRACT",
    "DOM-ETHIC",
    "DOM-PROJ",
})

_MATERIAL_SIGNALS = re.compile(
    r"材料清单|附件清单|必传材料|材料核验|缺件|提交材料|证明材料清单|"
    r"年审材料|申报材料|培训证明材料"
)


def scan_material_check(text: str) -> bool:
    return pattern_mentioned(text or "", _MATERIAL_SIGNALS, ignore_contrast=True)


def material_check_wanted(
    *,
    domain: str | None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
) -> bool:
    caps = list(capabilities or [])
    if MATERIAL_CHECK_CAP in caps:
        return True
    if (domain or "") in MATERIAL_DOMAINS:
        return True
    return scan_material_check(proposal_text)


def merge_material_check_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
    force: bool = False,
) -> list[str]:
    out = list(caps or [])
    want = force or material_check_wanted(
        domain=domain,
        capabilities=out,
        proposal_text=proposal_text,
    )
    if want and MATERIAL_CHECK_CAP not in out:
        out.append(MATERIAL_CHECK_CAP)
    return out


def attach_material_check_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    ensure_menu(
        admin,
        "material_checklist",
        {"key": "material_checklist", "label": "材料清单", "superOnly": True},
        before_key="content",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("materialChecklistTitle", "材料清单")
    labels.setdefault(
        "materialChecklistLead",
        "维护必传材料项；申请人须按清单上传，缺件不可提交。",
    )
    ticket = schema.setdefault("entities", {}).setdefault("ticket", {})
    if isinstance(ticket, dict):
        ticket["requireAttach"] = True
        ticket["requireMaterialChecklist"] = True
    ents = schema.setdefault("entities", {})
    if "material_check" not in ents:
        ents["material_check"] = {
            "key": "material_check",
            "label": "材料",
            "labelPlural": "材料清单",
        }


def apply_material_check_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain")
    caps = merge_material_check_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if MATERIAL_CHECK_CAP in caps:
        attach_material_check_menus(schema)
        from app.bake.gate_contracts import merge_material_check_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_material_check_gate(gate, caps)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "材料清单与缺件核验" not in names:
            features.append({"name": "材料清单与缺件核验", "status": "flow"})
        spec["features"] = features

        ents = list(spec.get("entities") or [])
        if "MaterialCheck" not in ents:
            if "Notice" in ents:
                ents.insert(ents.index("Notice"), "MaterialCheck")
            else:
                ents.append("MaterialCheck")
            spec["entities"] = ents

    spec["schema"] = schema
    return spec