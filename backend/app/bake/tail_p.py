"""长尾预设 P-18、P-23～P-29 验收表。"""

from __future__ import annotations

from app.bake.tail_meta import TAIL_META

TAIL_CASES: list[tuple[str, str, str, str]] = [
    (m["pid"], m["phrase"], m["domain"], m["title"]) for m in TAIL_META
]
