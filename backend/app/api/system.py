"""系统配置 / LLM 用量 / 运行环境 / 样例开题工具。

路由实现见 system_*.py；本模块聚合 router 并再导出 main 所需符号。
"""

from __future__ import annotations

from app.api.system_router import router  # noqa: F401

# 已自带 tags 的配置/用量（副作用注册到 system_router）
from app.api import system_deepseek as _system_deepseek  # noqa: F401
from app.api import system_gemini as _system_gemini  # noqa: F401
from app.api import system_info as _system_info  # noqa: F401
from app.api import system_tools as _system_tools  # noqa: F401
from app.api import system_unsplash as _system_unsplash  # noqa: F401
from app.api import system_usage as _system_usage  # noqa: F401

# 资产台：子模块自带 OpenAPI tags，挂到同一 /api 前缀
from app.api import system_zh_lexicon as _system_zh_lexicon
from app.api import system_status_copy as _system_status_copy
from app.api import system_dict_values as _system_dict_values
from app.api import system_demo_scripts as _system_demo_scripts
from app.api import system_addon_suggest as _system_addon_suggest
from app.api import system_cap_cards as _system_cap_cards
from app.api import system_error_copy as _system_error_copy
from app.api import system_widget_hints as _system_widget_hints
from app.api import system_menu_matrix as _system_menu_matrix
from app.api import system_rule_params as _system_rule_params
from app.api import system_er_edge_copy as _system_er_edge_copy
from app.api import system_demo_accounts as _system_demo_accounts
from app.api import system_diagram_titles as _system_diagram_titles
from app.api import system_diagram_verbs as _system_diagram_verbs
from app.api import system_usecase_flows as _system_usecase_flows
from app.api import system_thesis_absorb as _system_thesis_absorb

for _mod in (
    _system_zh_lexicon,
    _system_status_copy,
    _system_dict_values,
    _system_demo_scripts,
    _system_addon_suggest,
    _system_cap_cards,
    _system_error_copy,
    _system_widget_hints,
    _system_menu_matrix,
    _system_rule_params,
    _system_er_edge_copy,
    _system_demo_accounts,
    _system_diagram_titles,
    _system_diagram_verbs,
    _system_usecase_flows,
    _system_thesis_absorb,
):
    router.include_router(_mod.router)

# main.py 启动时水合 DeepSeek
from app.api.system_deepseek import _get_ds_row, _hydrate_ds_settings  # noqa: F401

__all__ = ["router", "_get_ds_row", "_hydrate_ds_settings"]
