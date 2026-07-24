"""常见本科/专科 Web 毕设选题包（覆盖优先，不完全等于 DOMAINS 原文）。

正文在 proposal_packs_data/*.json；顺序见 _order.json。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DIR = Path(__file__).resolve().parent / "proposal_packs_data"
_ORDER = json.loads((_DIR / "_order.json").read_text(encoding="utf-8"))

PACKS: list[dict[str, Any]] = [
    json.loads((_DIR / f"{pid}.json").read_text(encoding="utf-8")) for pid in _ORDER
]
