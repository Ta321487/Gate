"""列表分页：默认 page-size 必须落在 page-sizes 选项内。

曾漏：ArchiveBrowse 默认 ref(9)，补上 sizes 下拉后界面露出「9」，
而选项只有 [10, 20, 50]。扫基线 Vue，禁止再出现。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

_FRONT = (
    Path(__file__).resolve().parents[2] / "skeletons" / "baseline" / "frontend" / "src"
)

_PAGE_SIZES = re.compile(
    r""":page-sizes\s*=\s*["']\[([^\]]+)\]["']""",
)
_SIZE_REF = re.compile(r"""const\s+size\s*=\s*ref\(\s*(\d+)\s*\)""")


def _parse_sizes(raw: str) -> set[int]:
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


class PaginationPageSizeTests(unittest.TestCase):
    def test_default_size_in_page_sizes(self) -> None:
        bad: list[str] = []
        for path in sorted(_FRONT.rglob("*.vue")):
            text = path.read_text(encoding="utf-8")
            sizes_m = _PAGE_SIZES.search(text)
            size_m = _SIZE_REF.search(text)
            if not sizes_m or not size_m:
                continue
            allowed = _parse_sizes(sizes_m.group(1))
            if not allowed:
                continue
            default = int(size_m.group(1))
            if default not in allowed:
                rel = path.relative_to(_FRONT).as_posix()
                bad.append(f"{rel}: size=ref({default}) 不在 page-sizes={sorted(allowed)}")
        self.assertEqual(bad, [], "默认每页条数必须是 sizes 选项之一:\n" + "\n".join(bad))


if __name__ == "__main__":
    unittest.main()
