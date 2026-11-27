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

from app.api import defense_ppt, jobs, projects, system
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
    # 工厂资产台：表已 create_all；种子只追加缺键，永不改已有行（含 manual/scan/migrated）
    try:
        from app.core.database import SessionLocal
        from app.services.addon_suggest import migrate_seed_if_empty as migrate_addon
        from app.services.cap_cards import migrate_seed_if_empty as migrate_caps
        from app.services.demo_scripts import migrate_seed_if_empty as migrate_demo
        from app.services.dict_values import migrate_seed_if_empty as migrate_dicts
        from app.services.error_copy import migrate_seed_if_empty as migrate_errors
        from app.services.status_copy import migrate_seed_if_empty as migrate_status
        from app.services.widget_hints import migrate_seed_if_empty as migrate_widgets
        from app.services.menu_matrix import migrate_seed_if_empty as migrate_menus
        from app.services.rule_params import migrate_seed_if_empty as migrate_rules
        from app.services.er_edge_copy import migrate_seed_if_empty as migrate_edges
        from app.services.demo_accounts import migrate_seed_if_empty as migrate_accts
        from app.services.diagram_titles import migrate_seed_if_empty as migrate_titles
        from app.services.diagram_verbs import migrate_seed_if_empty as migrate_verbs
        from app.services.usecase_flows import migrate_seed_if_empty as migrate_ucf
        from app.services.zh_lexicon import migrate_seed_if_empty as migrate_zh

        async with SessionLocal() as db:
            await migrate_zh(db)
            await migrate_status(db)
            await migrate_dicts(db)
            await migrate_demo(db)
            await migrate_addon(db)
            await migrate_caps(db)
            await migrate_widgets(db)
            await migrate_errors(db)
            await migrate_menus(db)
            await migrate_rules(db)
            await migrate_edges(db)
            await migrate_accts(db)
            await migrate_titles(db)
            await migrate_verbs(db)
            await migrate_ucf(db)
    except Exception:  # noqa: BLE001
        from app.services.addon_suggest import bootstrap_from_seed as boot_addon
        from app.services.cap_cards import bootstrap_from_seed as boot_caps
        from app.services.demo_scripts import bootstrap_from_seed as boot_demo
        from app.services.dict_values import bootstrap_from_seed as boot_dv
        from app.services.error_copy import bootstrap_from_seed as boot_ec
        from app.services.status_copy import bootstrap_from_seed as boot_sc
        from app.services.widget_hints import bootstrap_from_seed as boot_wh
        from app.services.menu_matrix import bootstrap_from_seed as boot_mm
        from app.services.rule_params import bootstrap_from_seed as boot_rp
        from app.services.er_edge_copy import bootstrap_from_seed as boot_eec
        from app.services.demo_accounts import bootstrap_from_seed as boot_da
        from app.services.diagram_titles import bootstrap_from_seed as boot_dt
        from app.services.diagram_verbs import bootstrap_from_seed as boot_dvb
        from app.services.usecase_flows import bootstrap_from_seed as boot_ucf
        from app.services.zh_lexicon import bootstrap_from_seed as boot_zh

        boot_zh()
        boot_sc()
        boot_dv()
        boot_demo()
        boot_addon()
        boot_caps()
        boot_wh()
        boot_ec()
        boot_mm()
        boot_rp()
        boot_eec()
        boot_da()
        boot_dt()
        boot_dvb()
        boot_ucf()
    # 重启后无内存 Task 的 running 任务会永远卡在进度条（如 pack=91%）
    try:
        from app.services.jobs import fail_orphaned_jobs

        n = await fail_orphaned_jobs()
        if n:
            import logging

            logging.getLogger("gf.job").warning("marked %s orphaned job(s) failed", n)
    except Exception:  # noqa: BLE001
        pass
    from app.services.runtime_reconcile import start_runtime_reconcile, stop_runtime_reconcile

    start_runtime_reconcile()
    try:
        yield
    finally:
        await stop_runtime_reconcile()


# Swagger 分组顺序；tags 真挂在各 APIRouter 上（禁止 OpenAPI 事后改写）
_OPENAPI_TAGS = [
    {"name": "健康", "description": "服务存活探测"},
    {"name": "项目", "description": "列表/上传/匹配/生成/下载"},
    {"name": "论文材料", "description": "库表、论文图、学生端 API"},
    {"name": "质检交付", "description": "门禁、复审、清洗、重打包"},
    {"name": "预览运行", "description": "启停预览与日志"},
    {"name": "手调", "description": "论文材料手调覆盖"},
    {"name": "答辩PPT", "description": "答辩演示文稿"},
    {"name": "任务", "description": "异步生成任务队列"},
    {"name": "终稿吸收", "description": "终稿入库与抽取"},
    {"name": "词表", "description": "中文词表维护"},
    {"name": "状态话术", "description": "状态文案"},
    {"name": "字典台", "description": "字典值"},
    {"name": "实体动作词", "description": "图中实体动作词"},
    {"name": "论文图题", "description": "论文图标题"},
    {"name": "用例流程", "description": "用例流程"},
    {"name": "演示剧本", "description": "演示剧本"},
    {"name": "测试账号", "description": "演示账号"},
    {"name": "开关建议", "description": "能力开关建议"},
    {"name": "能力说明", "description": "能力卡片文案"},
    {"name": "错误码中文", "description": "错误码中文"},
    {"name": "控件语义", "description": "表单控件提示"},
    {"name": "菜单矩阵", "description": "菜单矩阵"},
    {"name": "规则参数", "description": "规则参数"},
    {"name": "表关系叙事", "description": "E-R 边文案"},
    {"name": "DeepSeek", "description": "大模型配置、余额与用量"},
    {"name": "Gemini", "description": "Gemini 配置"},
    {"name": "LLM", "description": "用量与调用审计"},
    {"name": "Unsplash", "description": "配图配置"},
    {"name": "工具", "description": "测试开题等工具"},
    {"name": "系统", "description": "本机环境、端口池与领域目录"},
]

app = FastAPI(
    title="毕设港",
    description=(
        "毕设港运营后端（FastAPI）。"
        "日常请用工作台页面；本页供查参与 Postman / 脚本调试。"
        "勿与学生端 ZIP 内的 Spring 接口混淆。"
    ),
    version="3.0.0",
    lifespan=lifespan,
    # 默认 redoc@next CDN 已 404，改用自定义 /redoc
    redoc_url=None,
    openapi_tags=_OPENAPI_TAGS,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(defense_ppt.router, prefix="/api/projects")
app.include_router(jobs.router)
app.include_router(system.router)


@app.get("/redoc", include_in_schema=False)
async def redoc_html() -> HTMLResponse:
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} · API 文档",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.5/bundles/redoc.standalone.js",
        with_google_fonts=False,
    )


@app.get("/api/health", tags=["健康"], summary="健康检查")
async def health():
    return {"ok": True, "service": "thesis-harbor"}


if __name__ == "__main__":
    import uvicorn

    from app.core.config import get_settings

    s = get_settings()
    uvicorn.run(
        "app.main:app",
        host=s.host,
        port=s.port,
        reload=False,
    )
