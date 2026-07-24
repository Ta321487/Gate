"""共享 APIRouter（避免 system 子模块循环导入）。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api")
