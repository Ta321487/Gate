"""开题扫词 → 已有积木：recommend / time_conflict / deadline（借阅逾期）。

硬约束
------
- **只增不减**：域默认已挂的能力，扫不到也不剥掉。
- **开题写了才往没有的域上挂**；否定/对比不计（keyword_mentioned）。
- **借阅逾期 ≠ 申报截止**：本模块的 ``deadline`` 是到期催还/罚金壳；
  申报/报名窗口见 ``ticket_flow_opts.scan_apply_deadline``，勿在此重复扫「报名截止」类词。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

RECOMMEND_CAP = "recommend"
TIME_CONFLICT_CAP = "time_conflict"
DEADLINE_CAP = "deadline"

_RECOMMEND_TERMS = (
    "猜你喜欢",
    "个性化推荐",
    "相关推荐",
    "热度推荐",
    "推荐列表",
    "推荐模块",
    "推荐功能",
    "轻量推荐",
    "首页推荐",
)

_TIME_CONFLICT_TERMS = (
    "时间冲突检测",
    "时段冲突检测",
    "时间冲突",
    "时段冲突",
    "课表冲突",
    "日程冲突",
    "占用时段冲突",
    "避免时间冲突",
    "冲突检测",
)

# 须具体到催还/罚金；裸「逾期」会误伤「逾期不可申报」
_LOAN_DEADLINE_TERMS = (
    "逾期催还",
    "到期催还",
    "超期催还",
    "催还提醒",
    "逾期提醒",
    "到期催办",
    "逾期催办",
    "逾期罚款",
    "超期罚款",
    "借阅逾期",
    "逾期费用",
    "归还逾期",
    "超期归还",
)


def scan_recommend(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _RECOMMEND_TERMS)


def scan_time_conflict(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _TIME_CONFLICT_TERMS)


def scan_loan_deadline(text: str) -> bool:
    """借阅/占用到期催办；不含申报截止。"""
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _LOAN_DEADLINE_TERMS)


def merge_recommend_capabilities(caps: list[str], proposal_text: str = "") -> list[str]:
    out = list(caps or [])
    if "archive" not in out:
        return [c for c in out if c != RECOMMEND_CAP]
    if RECOMMEND_CAP in out:
        return out
    if scan_recommend(proposal_text or ""):
        out.append(RECOMMEND_CAP)
    return out


def merge_time_conflict_capabilities(caps: list[str], proposal_text: str = "") -> list[str]:
    out = list(caps or [])
    if "archive" not in out or "ticket_flow" not in out:
        return [c for c in out if c != TIME_CONFLICT_CAP]
    if TIME_CONFLICT_CAP in out:
        return out
    if scan_time_conflict(proposal_text or ""):
        out.append(TIME_CONFLICT_CAP)
    return out


def merge_loan_deadline_capabilities(caps: list[str], proposal_text: str = "") -> list[str]:
    out = list(caps or [])
    if "ticket_flow" not in out:
        return [c for c in out if c != DEADLINE_CAP]
    if DEADLINE_CAP in out:
        return out
    if scan_loan_deadline(proposal_text or ""):
        out.append(DEADLINE_CAP)
    return out


def enrich_loan_deadline_flags(
    flags: dict[str, Any] | None,
    proposal_text: str = "",
    *,
    capabilities: list[str] | None = None,
) -> dict[str, Any]:
    """已有 deadline 能力时打开借阅壳列（只增不减）。扫词只走 merge，不在此重复。"""
    del proposal_text  # 接口与其它 enrich 对齐；命中判断在 merge_loan_deadline_capabilities
    out = dict(flags or {})
    if DEADLINE_CAP in list(capabilities or []):
        out["pickLoanPeriod"] = True
    return out


def _ensure_schedule_fields(archive: dict[str, Any]) -> None:
    fields = archive.get("fields")
    if not isinstance(fields, list):
        fields = []
        archive["fields"] = fields
    keys = {f.get("key") for f in fields if isinstance(f, dict)}
    if "startAt" not in keys:
        fields.append({"key": "startAt", "label": "开始时间", "type": "datetime"})
    if "endAt" not in keys:
        fields.append({"key": "endAt", "label": "结束时间", "type": "datetime"})


def attach_core_caps_schema(schema: dict[str, Any], caps: list[str]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    caps = list(caps or [])
    labels = schema.setdefault("labels", {})
    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    ents = schema.setdefault("entities", {})

    if RECOMMEND_CAP in caps:
        labels.setdefault("recommendSectionTitle", "猜你喜欢")
        labels.setdefault("recommendLatestHint", "最新发布")

    if TIME_CONFLICT_CAP in caps:
        archive = ents.setdefault("archive", {})
        if isinstance(archive, dict):
            _ensure_schedule_fields(archive)

    if DEADLINE_CAP in caps:
        ticket = ents.get("ticket")
        if isinstance(ticket, dict):
            ticket["pickLoanPeriod"] = True
        ensure_menu(
            admin,
            "deadline",
            {"key": "deadline", "label": labels.get("deadlineMenuLabel") or "逾期催还"},
            before_key="content",
        )
        labels.setdefault("deadlineMenuLabel", "逾期催还")


def apply_core_caps_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """能力已在 merge_proposal_capabilities 合并；此处只补 schema 侧效应与 features 文案。"""
    text = proposal_text or ""
    caps = list(spec.get("capabilities") or [])
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    attach_core_caps_schema(schema, caps)

    features = list(spec.get("features") or [])
    names = {f.get("name") for f in features if isinstance(f, dict)}

    def _add(name: str) -> None:
        if name not in names:
            features.append({"name": name, "status": "module"})
            names.add(name)

    # 仅在「本次扫词命中」时写 features，避免域默认能力重复刷文案
    if RECOMMEND_CAP in caps and scan_recommend(text):
        _add("猜你喜欢")
    if TIME_CONFLICT_CAP in caps and scan_time_conflict(text):
        _add("时间冲突检测")
    if DEADLINE_CAP in caps and scan_loan_deadline(text):
        _add("逾期催还")

    spec = {**spec, "capabilities": caps, "schema": schema, "features": features}
    return spec
