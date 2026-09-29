"""打印若干域的槽位解析结果（golden 口径），供人工核对。

用法（backend/）：python tests/tools/dump_lex.py [输出文件]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

GOLDEN = Path(__file__).resolve().parents[1] / "golden" / "schema"
DOMAINS = (
    "DOM-CHECKIN",
    "DOM-VISITOR",
    "DOM-CRM",
    "DOM-ATTEND",
    "DOM-PARCEL",
    "DOM-EVENT",
    "DOM-EQUIP",
    "DOM-FUND",
    "DOM-RECRUIT",
    "DOM-INTERN",
)


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("lex_dump.txt")
    lines: list[str] = []
    for name in DOMAINS:
        data = json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))
        lex = data.get("lex") or {}
        labels = data.get("labels") or {}
        tickets = next(
            (m.get("label") for m in (data.get("menus") or {}).get("user") or []
             if isinstance(m, dict) and m.get("key") == "my_tickets"),
            None,
        )
        lines.append(
            f"{name}\tnoun={lex.get('ticket_noun')}\taxis={lex.get('category_axis')}"
            f"\tmenu={tickets}\tempty={labels.get('myTicketsEmpty')}"
        )
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
