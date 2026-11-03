"""LLM 温度分级（主链路确定性 vs 文案活性）。

三档与产品口径对齐（调用点禁止再写魔法数，一律走本模块）：

| 档 | 区间 | 取值 | 场景 |
|---|---|---|---|
| deterministic | 0.0～0.1 | ABSOLUTE / STRUCTURED | 判域、匹配、JSON/Schema、角色原样、门禁诊断 |
| lively | 0.5～0.7 | LIVELY_* | 学生包客服对话、样例开题润色 |
| creative | 0.8～1.0 | CREATIVE | 选题头脑风暴（预留；当前无调用点） |

填岛 labels/seeds 仍是「强约束 JSON + 校验重试」，取 deterministic 上沿的
BOUNDED_COPY，不升到 lively，以免 JSON 漂移拖垮流水线。

比温度更重要的兜底在 ``unit_flow.runner``（校验→带报错重试→PPT/文案 fallback）
与各 Agent 的关键词/静态回落；本模块只管温度数值。
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.llm.unit_flow.models import UnitKind


class TempBand(str, Enum):
    """温度档（产品三档）。"""

    deterministic = "deterministic"
    lively = "lively"
    creative = "creative"


# —— 档内取用值（调用点唯一真源）——
TEMP_ABSOLUTE = 0.05
"""上传分堆、角色原样抄写：几乎不许发散。"""

TEMP_STRUCTURED = 0.1
"""匹配 / QA / 补丁诊断 / 失败分类 / ER·模块·用例标签 JSON。"""

TEMP_BOUNDED_COPY = 0.25
"""填岛 labels/seeds/entities、PPT 整形、Spec/用例散文：JSON 或强校验下的短文案。

略高于 0.1，但仍属 deterministic 哲学（不上 lively），靠 schema 校验+重试兜底。
"""

TEMP_LIVELY_SAMPLE = 0.55
"""工厂侧样例开题润色（读感自然，仍非头脑风暴）。"""

TEMP_LIVELY = 0.6
"""活跃档中位；新「对话/FAQ」类工厂调用默认取此。"""

TEMP_LIVELY_CHAT = 0.7
"""学生包客服/导购对话（``DeepSeekClient`` 应对齐）。"""

TEMP_CREATIVE = 0.85
"""选题头脑风暴 / 多套备选（预留）。"""

# 默认：未声明任务时走结构化档，偏稳不偏活
TEMP_DEFAULT = TEMP_STRUCTURED

# 任务名 → 温度（Agent / stage 字符串）
TASK_TEMPERATURE: dict[str, float] = {
    "upload_cluster": TEMP_ABSOLUTE,
    "match_recommend": TEMP_STRUCTURED,
    "parse_spec": TEMP_BOUNDED_COPY,
    "qa_report": TEMP_STRUCTURED,
    "job_fix": TEMP_STRUCTURED,
    "bake_fail_classify": TEMP_STRUCTURED,
    "bake_fail_hint": TEMP_ABSOLUTE,  # 修复提示：宁可死板
    "sample_proposal": TEMP_LIVELY_SAMPLE,
    "usecase_prose": TEMP_BOUNDED_COPY,
    "student_chat": TEMP_LIVELY_CHAT,
    "brainstorm": TEMP_CREATIVE,
}

# unit_flow UnitKind.value → 温度
UNIT_KIND_TEMPERATURE: dict[str, float] = {
    "island_labels": TEMP_BOUNDED_COPY,
    "island_seeds": TEMP_BOUNDED_COPY,
    "island_entities": TEMP_BOUNDED_COPY,
    "island_roles": TEMP_ABSOLUTE,
    "er_labels": TEMP_STRUCTURED,
    "module_labels": TEMP_STRUCTURED,
    "testcase_labels": TEMP_STRUCTURED,
    "ppt_page": TEMP_BOUNDED_COPY,
}

def temperature_for(task: str) -> float:
    """按任务名取温度；未知任务回落 STRUCTURED。"""
    key = (task or "").strip()
    return float(TASK_TEMPERATURE.get(key, TEMP_DEFAULT))


def temperature_for_unit(kind: "UnitKind | str") -> float:
    """填岛 / 材料 Unit 温度。"""
    key = kind.value if hasattr(kind, "value") else str(kind or "")
    return float(UNIT_KIND_TEMPERATURE.get(key, TEMP_BOUNDED_COPY))


def band_of(temperature: float) -> TempBand:
    """把数值归到产品三档（用于测试与控制台展示）。

    ``TEMP_BOUNDED_COPY``（≈0.25）仍归 deterministic：主链路 JSON 文案，不上 lively。
    """
    t = float(temperature)
    if t < 0.45:
        return TempBand.deterministic
    if t < 0.8:
        return TempBand.lively
    return TempBand.creative
