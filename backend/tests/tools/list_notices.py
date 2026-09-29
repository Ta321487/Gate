"""列出某域生成 SQL 里含指定词的种子公告（定位文案来源用）。

用法（backend/）：python tests/tools/list_notices.py DOM-EQUIP 领用
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.bake.domain_vocab import seed_notices  # noqa: E402
from app.bake.engine import domain_sql  # noqa: E402


def main() -> int:
    domain = sys.argv[1] if len(sys.argv) > 1 else "DOM-EQUIP"
    needle = sys.argv[2] if len(sys.argv) > 2 else ""
    sql = domain_sql(domain, "thesis_test")
    rows = [
        f"{domain} [{t}] {b}"
        for t, b in seed_notices(sql)
        if not needle or needle in f"{t}{b}"
    ]
    out = ROOT / ".notices_dump.txt"
    out.write_text("\n".join([f"{len(rows)} 条"] + rows), encoding="utf-8")
    print(f"{len(rows)} 条 → {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
