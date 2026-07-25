#!/usr/bin/env python3
"""历史脚本：曾把 baseline Store 的 JdbcTemplate 机械改写成 MbBridge。

大/小 Store 均已手工 Mapper 化，禁止再跑本脚本覆盖 overlay。
保留文件仅作考古说明。
"""

from __future__ import annotations

import sys


def main() -> None:
    print(
        "build_mybatis_overlay.py 已停用：persistence-mybatis overlay 已全部 Mapper 化，"
        "勿再生成 MbBridge 过渡层。",
        file=sys.stderr,
    )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
