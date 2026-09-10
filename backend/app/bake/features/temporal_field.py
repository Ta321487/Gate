"""档案日历字段精度：默认只有日期；开题特别强调时分才上 datetime。

- **默认 date**：产品属性日（采摘等）、报名/申报/选课截止、拾获日。
- **升 datetime**：开题正向提及钟点/时分（见 ``CLOCK_EMPHASIS_HINTS``）。
- **写死 datetime**（不走本扫词）：开场/上课/查寝/出发、时段冲突起止、限时购窗口等域内生调度。

勿塞进 ``scene_scan``（场景轴 ≠ 控件精度）。
"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned, pattern_mentioned

# 软日历：默认可只有日；命中钟点强调再升 datetime
SOFT_CALENDAR_KEYS = frozenset({"applyDeadlineAt", "foundAt", "harvestOn"})

# 域内生调度：必须带时分，禁止被扫成 date
SCHEDULE_DATETIME_KEYS = frozenset(
    {"startAt", "endAt", "promoStart", "promoEnd"}
)

CLOCK_EMPHASIS_HINTS = (
    "时分",
    "几点",
    "准时",
    "整点",
    "开抢",
    "发车时刻",
    "精确到分",
    "精确到时",
    "截止到点",
    "截止至点",
)

# 「截止到 18 点」「晚上8点前」「12:00 截止」等
_CLOCK_PATTERN = re.compile(
    r"(?:"
    r"截止[到至].{0,6}\d{1,2}\s*[点时]"
    r"|\d{1,2}\s*[点时]\s*(?:前|整|截止)?"
    r"|\d{1,2}\s*:\s*\d{2}"
    r"|HH\s*:\s*mm"
    r")",
    re.I,
)


def scan_clock_emphasis(text: str) -> bool:
    """开题是否特别强调钟点（时:分）。默认 False → 只要日期。"""
    raw = (text or "").strip()
    if not raw:
        return False
    for kw in CLOCK_EMPHASIS_HINTS:
        if keyword_mentioned(raw, kw, ignore_contrast=True):
            return True
    return pattern_mentioned(raw, _CLOCK_PATTERN, ignore_contrast=True)


def calendar_field_type(
    proposal_text: str = "",
    *,
    clock_inherent: bool = False,
) -> str:
    """返回 ``date`` 或 ``datetime``。"""
    if clock_inherent:
        return "datetime"
    if scan_clock_emphasis(proposal_text or ""):
        return "datetime"
    return "date"


def calendar_field(
    key: str,
    label: str,
    proposal_text: str = "",
    *,
    clock_inherent: bool = False,
    time_step_minutes: int | None = None,
) -> dict[str, Any]:
    """构造档案日历字段；软字段默认 date。"""
    t = calendar_field_type(proposal_text, clock_inherent=clock_inherent)
    out: dict[str, Any] = {"key": key, "label": label, "type": t}
    if t == "datetime" and time_step_minutes is not None:
        out["timeStepMinutes"] = time_step_minutes
    return out


def apply_soft_calendar_types(
    schema: dict[str, Any],
    proposal_text: str = "",
) -> None:
    """就地：软日历字段按开题钟点强调升/降精度；调度字段强制 datetime。"""
    if not isinstance(schema, dict):
        return
    ents = schema.get("entities")
    if not isinstance(ents, dict):
        return
    archive = ents.get("archive")
    if not isinstance(archive, dict):
        return
    fields = archive.get("fields")
    if not isinstance(fields, list):
        return
    want = calendar_field_type(proposal_text)
    for f in fields:
        if not isinstance(f, dict):
            continue
        key = str(f.get("key") or "")
        if key in SCHEDULE_DATETIME_KEYS:
            f["type"] = "datetime"
            continue
        if key not in SOFT_CALENDAR_KEYS:
            continue
        f["type"] = want
        if want == "datetime":
            f.setdefault("timeStepMinutes", 30)
        else:
            f.pop("timeStepMinutes", None)
