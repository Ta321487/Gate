"""窄 Agent：匹配推荐 / Spec 润色 / 填岛 / E-R 中文补全 / 模块图命名 / 测试用例文案 / 修复 / 质检。

实现拆至 agents_*.py；本模块再导出对外符号。
"""

from __future__ import annotations

from app.llm.agents_common import (  # noqa: F401
    _LABEL_KEYS,
    _SEED_KEYS,
    _proposal_text,
)
from app.llm.agents_fix import run_fix_agent  # noqa: F401
from app.llm.agents_island import (  # noqa: F401
    _sanitize_island_patch,
    _sanitize_island_roles,
    run_island_agent,
)
from app.llm.agents_labels import (  # noqa: F401
    run_er_label_agent,
    run_module_label_agent,
    run_testcase_label_agent,
)
from app.llm.agents_match import (  # noqa: F401
    run_match_agent,
    run_spec_agent,
    run_upload_cluster_agent,
)
from app.llm.agents_qa import run_qa_agent  # noqa: F401
from app.llm.agents_sample import run_sample_proposal_agent  # noqa: F401

__all__ = [
    "_LABEL_KEYS",
    "_SEED_KEYS",
    "_proposal_text",
    "_sanitize_island_patch",
    "_sanitize_island_roles",
    "run_upload_cluster_agent",
    "run_match_agent",
    "run_spec_agent",
    "run_island_agent",
    "run_er_label_agent",
    "run_module_label_agent",
    "run_testcase_label_agent",
    "run_fix_agent",
    "run_qa_agent",
    "run_sample_proposal_agent",
]
