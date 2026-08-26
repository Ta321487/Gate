"""档案演示种子硬闸：单据流域须能 apply（gate 自检与冒烟主链）。"""

from __future__ import annotations

import re


def assert_archive_demo_seed(
    sql: str,
    *,
    item_table: str | None,
    flow_api: dict | None,
    ticket_mode: str | None = None,
) -> None:
    """archive 模式且有 flow_api.apply 时，schema.sql 必须含档案主表演示 INSERT。"""
    if not isinstance(flow_api, dict) or "apply" not in flow_api:
        return
    if str(ticket_mode or "archive").strip().lower() == "standalone":
        return
    table = (item_table or "").strip()
    if not table:
        raise ValueError("单据流域缺少 archive_item_table，无法保证主路径 apply 演示种子")
    if not re.search(
        rf"INSERT\s+IGNORE\s+INTO\s+`?{re.escape(table)}`?\b",
        sql or "",
        re.IGNORECASE,
    ):
        raise ValueError(
            f"schema.sql 缺少 {table} 的 INSERT IGNORE 演示种子，"
            "gate 自检与冒烟 apply 将因「对象不存在」失败"
        )
