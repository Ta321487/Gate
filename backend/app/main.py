from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# 允许在 app/ 下直接 python main.py（把 backend 根加入 path）
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html
from fastapi.responses import HTMLResponse

from app.api import jobs, projects, system
from app.core.database import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    # 启动时把 DB 中 DeepSeek 预算/模型写回内存，避免未打开设置页时任务仍用默认值
    try:
        from app.core.database import SessionLocal
        from app.api.system import _get_ds_row, _hydrate_ds_settings
        from app.core.config import get_settings

        async with SessionLocal() as db:
            cfg = await _get_ds_row(db)
            _hydrate_ds_settings(get_settings(), cfg)
    except Exception:  # noqa: BLE001
        pass
    yield


app = FastAPI(
    title="毕设港",
    version="3.0.0",
    lifespan=lifespan,
    # 默认 redoc@next CDN 已 404，改用自定义 /redoc
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(jobs.router)
app.include_router(system.router)


@app.get("/redoc", include_in_schema=False)
async def redoc_html() -> HTMLResponse:
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.5/bundles/redoc.standalone.js",
        with_google_fonts=False,
    )


@app.get("/api/health")
async def health():
    return {"ok": True, "service": "thesis-harbor"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
