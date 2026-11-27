"""项目运营 API 包。

对外仍 ``from app.api import projects; projects.router``，
路径前缀 ``/api/projects`` 不变。子模块按职责挂到同一 router，并自带 OpenAPI tags。
"""

from __future__ import annotations

from app.api.projects.common import router

# 注册顺序与旧单文件一致（静态路径优先于 /{project_id}）
from app.api.projects import crud as _crud
from app.api.projects import schema as _schema
from app.api.projects import runtime as _runtime
from app.api.projects import delivery_review as _delivery_review
from app.api.projects import overrides as _overrides

router.include_router(_crud.router)
router.include_router(_schema.router)
router.include_router(_runtime.router)
router.include_router(_delivery_review.router)
router.include_router(_overrides.router)

__all__ = ["router"]
