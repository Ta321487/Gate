"""从已有 GENERIC SQL 模板拼装多主路径 schema，避免复制整份 DDL。"""

from __future__ import annotations

import re
from pathlib import Path

_SQL_DIR = Path(__file__).resolve().parent

_TABLE_RE = re.compile(
    r"CREATE TABLE IF NOT EXISTS (\w+)\s*\((?:.|\n)*?\);",
    re.IGNORECASE,
)
_INSERT_SLOT_RE = re.compile(
    r"INSERT IGNORE INTO resource_slot\b(?:.|\n)*?;",
    re.IGNORECASE,
)
_INSERT_NOTICE_RE = re.compile(
    r"INSERT INTO sys_notice\b(?:.|\n)*?;",
    re.IGNORECASE,
)


def _load(name: str) -> str:
    return (_SQL_DIR / name).read_text(encoding="utf-8")


def _tables(sql: str) -> dict[str, str]:
    return {m.group(1): m.group(0) for m in _TABLE_RE.finditer(sql)}


def compose_generic_sql(
    *,
    need_flow: bool,
    need_trade: bool,
    need_reserve: bool,
    db_name: str,
    table_min: int,
    table_max: int,
) -> str:
    """按能力开关从 FLOW/TRADE/RESERVE/CRUD 模板抽表拼装。"""
    crud = _load("DOM-GENERIC.sql")
    flow = _load("DOM-GENERIC-FLOW.sql")
    trade = _load("DOM-GENERIC-TRADE.sql")
    reserve = _load("DOM-GENERIC-RESERVE.sql")

    pool: dict[str, str] = {}
    pool.update(_tables(crud))
    pool.update(_tables(flow))
    pool.update(_tables(trade))
    pool.update(_tables(reserve))

    order = [
        "sys_user",
        "category",
        "biz_item",
        "biz_attach",
        "biz_ticket",
        "biz_ticket_log",
        "cart_line",
        "user_address",
        "biz_order",
        "order_line",
        "resource_slot",
        "reservation",
        "sys_message",
        "sys_notice",
    ]
    want = {"sys_user", "category", "biz_item", "sys_message", "sys_notice"}
    if not (need_flow or need_trade or need_reserve):
        want.add("biz_attach")
    if need_flow:
        want.update({"biz_ticket", "biz_ticket_log"})
    if need_trade:
        want.update({"cart_line", "user_address", "biz_order", "order_line"})
    if need_reserve:
        want.update({"resource_slot", "reservation"})
    if need_flow or need_trade or need_reserve:
        want.discard("biz_attach")

    parts = [
        f"-- bake domain=DOM-GENERIC · composed · tables in [{table_min},{table_max}]",
        f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4;",
        f"USE `{db_name}`;",
        "",
    ]
    for name in order:
        if name in want and name in pool:
            parts.append(pool[name])
            parts.append("")

    seed_src = flow if need_flow else (trade if need_trade else (reserve if need_reserve else crud))
    m = re.search(r"INSERT INTO sys_user\b", seed_src)
    if m:
        seed_tail = seed_src[m.start() :]
        seed_tail = _INSERT_NOTICE_RE.sub("", seed_tail).rstrip() + "\n"
        parts.append(seed_tail)
        parts.append("")

    if need_reserve:
        slot_ins = _INSERT_SLOT_RE.search(reserve)
        if slot_ins:
            parts.append(slot_ins.group(0))
            parts.append("")

    notice = "系统已就绪，可开始业务演示。"
    if need_flow and need_trade and need_reserve:
        notice = "支持申请审核、购物车订单与时段预约（演示）。"
    elif need_flow and need_trade:
        notice = "支持申请审核与购物车订单（演示无真支付）。"
    elif need_flow and need_reserve:
        notice = "支持申请审核与时段预约。"
    elif need_trade and need_reserve:
        notice = "支持购物车订单与时段预约（演示无真支付）。"
    elif need_flow:
        notice = "请提交申请并等待审核；结果将写入站内消息。"
    elif need_trade:
        notice = "演示环境支持购物车与多明细订单，无真支付。"
    elif need_reserve:
        notice = "选择资源与时段占坑预约；约满后不可再约。"

    parts.append(
        "INSERT INTO sys_notice (title, content, publisher_username, publisher_name)\n"
        f"SELECT '使用须知', '{notice}', 'admin', '系统管理员'\n"
        "FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='使用须知');\n"
    )
    return "\n".join(parts)


def compose_named_domain_sql(domain: str) -> str:
    """具名域 SQL 唯一入口（原 bake/sql/DOM-*.sql）。

    模板登记于 ``DOMAIN_SQL_TEMPLATES``；bake 不再读散落的域 SQL 文件。
    GENERIC 多路径仍走 ``compose_generic_sql`` / DOM-GENERIC*.sql。
    """
    from app.bake.sql.domain_templates import DOMAIN_SQL_TEMPLATES

    text = DOMAIN_SQL_TEMPLATES.get(domain)
    if text is None:
        raise FileNotFoundError(
            f"缺少领域 SQL 模板: {domain}（未登记于 DOMAIN_SQL_TEMPLATES）"
        )
    return text
