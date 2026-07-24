"""单据表：借阅壳列按域剔除；archive 外键 book_id → 域语义名。"""

from __future__ import annotations

from typing import Any

from app.bake.domain_entities import (
    DOMAIN_ENTITIES,
    TICKET_STANDALONE_DOMAINS,
    ticket_item_fk_for,
)
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

# 兼容旧导入：派生自 domain_entities（勿再手扩）
TICKET_ITEM_FK_BY_DOMAIN: dict[str, str] = {
    d: e.item_fk
    for d, e in DOMAIN_ENTITIES.items()
    if e.item_fk and not e.standalone
}


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
