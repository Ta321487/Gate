"""DeepSeek 窄 Agent：Spec / 填岛 / 修复诊断 / QA。禁止生成业务源码。"""

from app.llm.runtime import LlmRuntime, load_llm_runtime
from app.llm.temperature import (
    TEMP_DEFAULT,
    temperature_for,
    temperature_for_unit,
)

__all__ = [
    "LlmRuntime",
    "load_llm_runtime",
    "TEMP_DEFAULT",
    "temperature_for",
    "temperature_for_unit",
]
