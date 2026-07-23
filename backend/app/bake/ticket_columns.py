"""单据表：借阅壳列按域剔除；archive 外键 book_id → 域语义名。"""

from __future__ import annotations

from typing import Any

from app.bake.sql.ddl_edit import (
    inject_missing_columns,
    map_create_table,
    prune_columns,
    rewrite_col_def,
    rewrite_insert_col_names,
    valid_ident,
)

# 借阅/逾期壳（非借阅域不应出现在 ER）
TICKET_LOAN_SHELL_COLUMNS: list[tuple[str, str]] = [
    ("due_at", "DATETIME NULL"),
    ("fine_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("reminded_at", "DATETIME NULL"),
    ("remind_msg", "VARCHAR(255) DEFAULT ''"),
]

_TICKET_LOAN_NAMES = {n.lower() for n, _ in TICKET_LOAN_SHELL_COLUMNS}

# archive 模式单据 → 档案行外键物理名（图书馆保留 book_id）
# standalone 报修域无档案外键，勿写入 item_id
TICKET_ITEM_FK_BY_DOMAIN: dict[str, str] = {
    "DOM-LIBRARY": "book_id",
    "DOM-EQUIP": "equip_id",
    "DOM-ASSET": "asset_id",
    "DOM-CRM": "customer_id",
    "DOM-EVENT": "event_id",
    "DOM-ACTIVITY": "activity_id",
    "DOM-COURSE": "course_id",
    "DOM-LOST": "lost_item_id",
    "DOM-FORUM": "post_id",
    "DOM-MEDIA": "media_id",
    "DOM-BLOG": "article_id",
    "DOM-MUSIC": "track_id",
    "DOM-GENERIC": "item_id",
}

TICKET_STANDALONE_DOMAINS = frozenset({"DOM-DORM", "DOM-PROPERTY", "DOM-IT"})


def ticket_item_fk_for(domain: str) -> str | None:
    """archive 模式返回外键列名；standalone 返回 None。"""
    d = (domain or "").strip()
    if d in TICKET_STANDALONE_DOMAINS:
        return None
    return TICKET_ITEM_FK_BY_DOMAIN.get(d, "item_id")


def ticket_loan_shell_wanted(domain: str, ticket_flags: dict | None = None) -> bool:
    """仅借阅/设备租借等需要到期与罚金壳。"""
    d = (domain or "").strip()
    if d in ("DOM-LIBRARY", "DOM-EQUIP"):
        return True
    f = ticket_flags or {}
    if f.get("pickLoanPeriod"):
        return True
    if d == "DOM-ACTIVITY":
        return False
    return False


def ticket_column_payload(
    domain: str,
    *,
    ticket_table: str | None = None,
    ticket_flags: dict | None = None,
) -> dict[str, Any]:
    fk = ticket_item_fk_for(domain)
    return {
        "ticketTable": (ticket_table or "").strip(),
        "itemFkColumn": fk or "",
        "loanShell": ticket_loan_shell_wanted(domain, ticket_flags),
        "standalone": fk is None,
    }


def apply_ticket_shell_sql(
    sql: str,
    *,
    domain: str,
    ticket_table: str | None,
    ticket_flags: dict | None = None,
) -> str:
    """剔除非借阅域的 due/fine/remind 壳，并将 book_id 改为域语义外键。"""
    t = (ticket_table or "").strip()
    if not valid_ident(t):
        return sql
    fk = ticket_item_fk_for(domain)
    want_loan = ticket_loan_shell_wanted(domain, ticket_flags)
    loan_allow = _TICKET_LOAN_NAMES if want_loan else set()

    def transform(body: str) -> str:
        body = prune_columns(body, allow=loan_allow, known=_TICKET_LOAN_NAMES)
        if want_loan:
            body = inject_missing_columns(body, list(TICKET_LOAN_SHELL_COLUMNS))
        if fk and fk.lower() != "book_id":
            body = rewrite_col_def(body, "book_id", fk)
        return body

    out = map_create_table(sql, t, transform)
    if fk and fk.lower() != "book_id":
        out = rewrite_insert_col_names(out, t, {"book_id": fk})
    return out
