"""开题扫词 → 单据流程选项（两级审 / 必传附件 / 申报截止）。

硬约束
------
- **只增不减**：域默认已开的开关（宿舍报修两级审等）扫不到也不关掉。
- **词必须对应该功能**：裸「审核」「截止」不够；否定/本期不 不计（keyword_mentioned）。
- **截止 ≠ 借阅逾期**：本模块的「截止」是档案 ``applyDeadlineAt``（申报/报名窗口）；
  借阅 ``deadline`` / 罚金壳见 ``core_cap_scan.scan_loan_deadline``，勿在此重复扫词。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

# —— 扫词（正向提及才算）——

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


def scan_two_level(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _TWO_LEVEL_TERMS)


def scan_require_attach(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _ATTACH_TERMS)


def scan_apply_deadline(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _APPLY_DEADLINE_TERMS)


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
    if scan_two_level(proposal_text):
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


def _ensure_apply_deadline_field(archive: dict[str, Any], label: str) -> None:
    fields = archive.get("fields")
    if not isinstance(fields, list):
        fields = []
        archive["fields"] = fields
    for f in fields:
        if isinstance(f, dict) and f.get("key") == "applyDeadlineAt":
            return
    # 插在 stock / category 附近，避免甩在末尾难找
    insert_at = len(fields)
    for i, f in enumerate(fields):
        if isinstance(f, dict) and f.get("key") in ("stock", "status"):
            insert_at = i
            break
    fields.insert(
        insert_at,
        {"key": "applyDeadlineAt", "label": label, "type": "datetime"},
    )


def apply_ticket_flow_opts_to_schema(
    schema: dict[str, Any],
    proposal_text: str = "",
) -> None:
    """就地改 schema.entities.ticket / archive；只开不开。"""
    if not isinstance(schema, dict):
        return
    text = proposal_text or ""
    entities = schema.setdefault("entities", {})
    ticket = entities.get("ticket")
    if isinstance(ticket, dict):
        if scan_two_level(text):
            ticket["twoLevelApprove"] = True
            _ensure_pending_final(ticket)
        if scan_require_attach(text):
            ticket["requireAttach"] = True

    archive = entities.get("archive")
    if isinstance(archive, dict) and scan_apply_deadline(text):
        _ensure_apply_deadline_field(archive, _apply_deadline_label(text))


def apply_ticket_flow_opts_to_spec(
    spec: dict[str, Any],
    proposal_text: str = "",
) -> dict[str, Any]:
    """挂 features 文案；schema 开关由 apply_ticket_flow_opts_to_schema 完成。"""
    text = proposal_text or ""
    schema = dict(spec.get("schema") or {})
    apply_ticket_flow_opts_to_schema(schema, text)
    spec = {**spec, "schema": schema}

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
    if isinstance(ticket, dict) and ticket.get("twoLevelApprove") and scan_two_level(text):
        _add_feat("两级审批", "flow")
    if isinstance(ticket, dict) and ticket.get("requireAttach") and scan_require_attach(text):
        _add_feat("附件上传", "module")
    archive = ((schema.get("entities") or {}).get("archive") or {})
    if isinstance(archive, dict) and scan_apply_deadline(text):
        fields = archive.get("fields") or []
        if any(isinstance(f, dict) and f.get("key") == "applyDeadlineAt" for f in fields):
            _add_feat(_apply_deadline_label(text), "module")

    spec["features"] = features
    return spec
