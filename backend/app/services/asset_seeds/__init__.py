"""工厂资产台首迁种子（版本化 JSON）。

纪律：业务字面量只活在本目录 JSON + 工厂库表；services 逻辑不得再 put() 写死域/态/枚举。
迁入只追加缺主键；已有行永不被种子 UPDATE。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=8)
def load_seed_json(name: str) -> tuple[dict[str, Any], ...]:
    """读取 ``asset_seeds/<name>.json``；返回不可变元组。

    缺 ``source`` 时默认 ``migrated``，保证种子可进 bake / 解析（与迁入库行口径一致）。
    """
    path = _DIR / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"asset seed missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"asset seed must be a list: {path}")
    out: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        if not str(row.get("source") or "").strip():
            row["source"] = "migrated"
        out.append(row)
    return tuple(out)
