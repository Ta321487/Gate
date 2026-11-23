"""系统配置 / LLM 用量 / 运行环境 / 样例开题工具。

路由实现见 system_*.py；本模块聚合 router 并再导出 main 所需符号。
"""

from __future__ import annotations

from app.api.system_router import router  # noqa: F401

# 注册路由（导入副作用）
from app.api import system_deepseek as _system_deepseek  # noqa: F401
from app.api import system_gemini as _system_gemini  # noqa: F401
from app.api import system_info as _system_info  # noqa: F401
from app.api import system_tools as _system_tools  # noqa: F401
from app.api import system_unsplash as _system_unsplash  # noqa: F401
from app.api import system_usage as _system_usage  # noqa: F401
from app.api import system_zh_lexicon as _system_zh_lexicon  # noqa: F401
from app.api import system_status_copy as _system_status_copy  # noqa: F401
from app.api import system_dict_values as _system_dict_values  # noqa: F401
from app.api import system_demo_scripts as _system_demo_scripts  # noqa: F401
from app.api import system_addon_suggest as _system_addon_suggest  # noqa: F401
from app.api import system_cap_cards as _system_cap_cards  # noqa: F401
from app.api import system_error_copy as _system_error_copy  # noqa: F401
from app.api import system_widget_hints as _system_widget_hints  # noqa: F401
from app.api import system_menu_matrix as _system_menu_matrix  # noqa: F401
from app.api import system_rule_params as _system_rule_params  # noqa: F401
from app.api import system_er_edge_copy as _system_er_edge_copy  # noqa: F401
from app.api import system_demo_accounts as _system_demo_accounts  # noqa: F401
from app.api import system_thesis_absorb as _system_thesis_absorb  # noqa: F401

# main.py 启动时水合 DeepSeek
from app.api.system_deepseek import _get_ds_row, _hydrate_ds_settings  # noqa: F401

__all__ = ["router", "_get_ds_row", "_hydrate_ds_settings"]
