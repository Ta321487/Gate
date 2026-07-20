"""种子日期工具（离线自检用）。

正式交付不要在 bake 时把日期写死成「今天」——答辩往往在数月后。
运行时由基线 SeedCalendarAligner 在启动时平移 start_at/end_at/apply_deadline_at
（不写进学生 application.yml）。
"""

from __future__ import annotations

import re
from datetime import date, timedelta

_SEED_DT = re.compile(
    r"(?<![\d])(\d{4}-\d{2}-\d{2})(?:([ T])(\d{2}:\d{2}:\d{2}))?"
)


def shift_seed_datetimes(sql: str, *, today: date | None = None) -> str:
    """将文本中种子日期整体平移，使最早一天落到 today。仅供单测/手工预览。"""
    if not sql:
        return sql
    anchor = today or date.today()
    found: list[date] = []
    for m in _SEED_DT.finditer(sql):
        try:
            found.append(date.fromisoformat(m.group(1)))
        except ValueError:
            continue
    if not found:
        return sql
    delta: timedelta = anchor - min(found)
    if delta.days == 0:
        return sql

    def _repl(m: re.Match[str]) -> str:
        try:
            d = date.fromisoformat(m.group(1)) + delta
        except ValueError:
            return m.group(0)
        sep = m.group(2)
        tim = m.group(3)
        if sep and tim:
            return f"{d.isoformat()}{sep}{tim}"
        return d.isoformat()

    return _SEED_DT.sub(_repl, sql)
