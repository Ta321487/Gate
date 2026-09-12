"""DeepSeek / Gemini 模型目录：官方 ID、旧名别名、设置页选项。

换官方模型名时优先改本文件；API GET /deepseek 会下发 model_options，前端跟目录走。
"""

from __future__ import annotations

from typing import Any

# 官方日常默认（V4.1 Flash）；旧 v4-flash / chat 等经别名落到此
DEEPSEEK_DEFAULT_MODEL = "deepseek-flash"

# 设置页可选（value=请求 API 的 model 字段）
DEEPSEEK_MODEL_OPTIONS: tuple[dict[str, str], ...] = (
    {
        "id": "deepseek-flash",
        "label": "deepseek-flash · V4.1 Flash（日常 / 官方现行）",
    },
    # Pro 档：官方称 V4 Pro 将路由到 Flash，直至 V4.1 Pro；保留旧名作兼容入口
    {
        "id": "deepseek-v4-pro",
        "label": "deepseek-v4-pro · 旧 Pro 名（官方正路由到 Flash）",
    },
)

# 读库 / 环境 / 调用链上的历史名 → 现行官方 ID
DEEPSEEK_MODEL_ALIASES: dict[str, str] = {
    "deepseek-chat": DEEPSEEK_DEFAULT_MODEL,
    "deepseek-reasoner": DEEPSEEK_DEFAULT_MODEL,
    "deepseek-v4-flash": DEEPSEEK_DEFAULT_MODEL,
    "deepseek-v4-flash-vision-exp": DEEPSEEK_DEFAULT_MODEL,
    "deepseek-v4.1-flash": DEEPSEEK_DEFAULT_MODEL,
    "deepseek-v4.1-flash-expires-on-0910": DEEPSEEK_DEFAULT_MODEL,
}


def resolve_deepseek_model(model: str | None) -> str:
    m = (model or "").strip() or DEEPSEEK_DEFAULT_MODEL
    return DEEPSEEK_MODEL_ALIASES.get(m, m)


def deepseek_model_options_payload() -> list[dict[str, Any]]:
    return [{"id": o["id"], "label": o["label"]} for o in DEEPSEEK_MODEL_OPTIONS]
