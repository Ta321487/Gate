"""确定性 bake：复制骨架 + 领域叠加 + SQL / Spec。

实现见 engine_sql / engine_bake / engine_resources / engine_islands。
"""

from __future__ import annotations

from app.bake.engine_bake import bake_project  # noqa: F401
from app.bake.engine_islands import (  # noqa: F401
    emit_schema_to_workspace,
    llm_fill_islands,
    sync_workspace_thesis_yml,
)
from app.bake.engine_sql import (  # noqa: F401
    TABLE_COUNT_MAX,
    TABLE_COUNT_MIN,
    assert_table_budget,
    count_create_tables,
    domain_sql,
)

__all__ = [
    "TABLE_COUNT_MIN",
    "TABLE_COUNT_MAX",
    "count_create_tables",
    "assert_table_budget",
    "domain_sql",
    "bake_project",
    "emit_schema_to_workspace",
    "sync_workspace_thesis_yml",
    "llm_fill_islands",
]
