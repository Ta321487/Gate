"""窄 Agent：匹配推荐 / Spec 润色 / 拆解填岛 / 修复 / 质检。

填岛与 ER/模块/用例标签统一走 app.llm.unit_flow.run_fill_pipeline。
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
)
from app.llm.agents_match import (  # noqa: F401
    run_match_agent,
    run_spec_agent,
    run_upload_cluster_agent,
)
from app.llm.agents_qa import run_qa_agent  # noqa: F401
from app.llm.agents_sample import run_sample_proposal_agent  # noqa: F401
from app.llm.unit_flow import run_fill_pipeline  # noqa: F401

__all__ = [
    "_LABEL_KEYS",
    "_SEED_KEYS",
    "_proposal_text",
    "_sanitize_island_patch",
    "_sanitize_island_roles",
    "run_upload_cluster_agent",
    "run_match_agent",
    "run_spec_agent",
    "run_fill_pipeline",
    "run_fix_agent",
    "run_qa_agent",
    "run_sample_proposal_agent",
]
