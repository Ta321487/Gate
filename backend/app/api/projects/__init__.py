"""项目运营 API 包。

对外仍 ``from app.api import projects; projects.router``，
路径前缀 ``/api/projects`` 不变。子模块按职责挂到同一 router。
"""

from __future__ import annotations

from app.api.projects.common import router

# 注册顺序与旧单文件一致（静态路径优先于 /{project_id}）
from app.api.projects import crud as _crud  # noqa: F401
from app.api.projects import schema as _schema  # noqa: F401
from app.api.projects import runtime as _runtime  # noqa: F401
from app.api.projects import delivery_review as _delivery_review  # noqa: F401

__all__ = ["router"]
