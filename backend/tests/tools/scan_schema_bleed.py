"""Scan baked SQL for remaining cross-domain / runtime-superset risks."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.bake.engine import domain_sql  # noqa: E402

L1 = [
    "attach_url",
    "rating",
    "rating_remark",
    "rated_at",
    "priority",
    "contact_phone",
    "fine_status",
    "pickup_at",
    "pickup_place",
    "actual_qty",
    "contact_channel",
    "next_follow_at",
    "checked_in_at",
]

SKIP = {
    "sys_user",
    "sys_message",
    "sys_notice",
    "category",
    "cart_line",
    "user_address",
    "biz_order",
    "order_line",
    "resource_slot",
    "reservation",
    "biz_item",
    "biz_attach",
}


def tables(sql: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for m in re.finditer(
        r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\);", sql, re.S | re.I
    ):
        t = m.group(1).lower()
        cols = {
            mm.group(1).lower()
            for mm in re.finditer(r"(?m)^\s*(\w+)\s+", m.group(2))
        }
        out[t] = cols
    return out


def main() -> None:
    golden = Path(__file__).resolve().parents[1] / "golden" / "sql"
    named = sorted(
        p.stem
        for p in golden.glob("DOM-*.sql")
        if not p.stem.startswith("DOM-GENERIC")
    )

    print("=== ticket L1 columns in BAKE sql (not runtime) ===")
    for d in named:
        sql = domain_sql(d, "t")
        for t, cols in tables(sql).items():
            if t in SKIP or t.endswith("_progress") or t.endswith("_log"):
                continue
            if "username" in cols and "status" in cols and "stock" not in cols:
                hit = [c for c in L1 if c in cols]
                print(f"  {d}.{t}: {hit or ['(lean)']}")

    print()
    print("=== archive semantic columns ===")
    from app.bake.archive_columns import archive_column_spec_for
    from app.bake.domains import DOMAINS

    for d in ["DOM-PARKING", "DOM-SHOP", "DOM-BLOG", "DOM-LIBRARY", "DOM-FOOD", "DOM-HOTEL"]:
        sql = domain_sql(d, "t")
        item = ((DOMAINS.get(d) or {}).get("runtime") or {}).get("archive_item_table") or ""
        (a, _), (i, _) = archive_column_spec_for(d)
        cols = tables(sql).get(item.lower(), set())
        ok = a.lower() in cols and i.lower() in cols
        bad = []
        if i.lower() != "isbn" and "isbn" in cols:
            bad.append("isbn")
        if a.lower() != "author" and "author" in cols:
            bad.append("author")
        print(f"  {d}.{item}: {a}/{i} ok={ok} residue={bad or '-'}")


if __name__ == "__main__":
    main()
