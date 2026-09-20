"""骨架前端：router/index.js 必须能被 Node 语法检查通过。"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROUTER = ROOT / "skeletons/baseline/frontend/src/router/index.js"


def test_baseline_router_index_js_syntax() -> None:
    assert ROUTER.is_file()
    text = ROUTER.read_text(encoding="utf-8")
    # 禁止再回到深嵌套 withX(withY(...)) 收口（括号极易漏）
    assert "enrichers.reduce" in text, "能力补路由须用 enrichers.reduce，勿深嵌套括号"
    assert "return withDigitalRoutes(withHotelPmsRoutes(" not in text
    proc = subprocess.run(
        ["node", "--check", str(ROUTER)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
