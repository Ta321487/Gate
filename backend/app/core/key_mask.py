"""密钥展示脱敏（运营台）。"""

from __future__ import annotations


def mask_key(key: str, *, env_name: str = "API_KEY", hint_prefix: str = "") -> str:
    if not key:
        return f"未配置（环境变量 {env_name}）"
    if len(key) < 8:
        return f"{hint_prefix}••••" if hint_prefix else "••••"
    return f"{hint_prefix}••••••••••••{key[-4:]}（来自环境变量）"
