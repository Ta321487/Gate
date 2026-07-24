"""system_info.py — 由 system 聚合。"""

from __future__ import annotations

import asyncio
import subprocess
import time
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.llm.client import (
    monthly_tokens_breakdown,
    project_lifetime_token_rows,
    project_usage_chart,
    project_usage_rows,
    support_usage,
)
from app.llm.runtime import DEFAULT_DS, get_llm_flags, set_llm_flags
from app.models import LlmCall, Project, ProjectStatus, SettingRow
from app.schemas import (
    ApiOk,
    DeepSeekBalance,
    DeepSeekBalanceInfo,
    DeepSeekSettings,
    DeepSeekUpdate,
    GeminiSettings,
    GeminiUpdate,
    SampleProposalRequest,
    SampleProposalResult,
    SystemInfo,
    UnsplashSettings,
)
from app.services import runtime as rt
from app.services.projects import mask_key, reclaim_idle_ports

from app.api.system_router import router  # noqa: E402

def _cmd_version(name: str, *args: str) -> str:
    """用与 runtime 相同的可执行解析（Windows 上 mvn → mvn.cmd）。"""
    key = name + " ".join(args)
    now = time.monotonic()
    hit = _TOOL_VER_CACHE.get(key)
    if hit and now - hit[0] < _TOOL_VER_TTL:
        return hit[1]
    exe = rt._resolve_cmd(name)
    if not exe:
        val = "未检测到"
    else:
        try:
            out = subprocess.check_output(
                [exe, *args], stderr=subprocess.STDOUT, text=True, timeout=5
            )
            val = out.strip().splitlines()[0][:40]
        except Exception:  # noqa: BLE001
            val = "未检测到"
    _TOOL_VER_CACHE[key] = (now, val)
    return val


def _java_ver() -> str:
    key = "java"
    now = time.monotonic()
    hit = _TOOL_VER_CACHE.get(key)
    if hit and now - hit[0] < _TOOL_VER_TTL:
        return hit[1]
    try:
        out = subprocess.check_output(
            ["java", "-version"], stderr=subprocess.STDOUT, text=True, timeout=5
        )
        val = out.strip().splitlines()[0].replace('"', "")[:48]
    except Exception:  # noqa: BLE001
        val = "未检测到"
    _TOOL_VER_CACHE[key] = (now, val)
    return val


def _probe_used_ports(
    rows: list,
) -> tuple[list[int], list[int], list[int], list[int]]:
    """一次 netstat + 进程表。返回 managed_*/idle_*（used = 二者并集）。"""
    listening = rt.listening_tcp_ports()
    managed_be, managed_fe = [], []
    idle_be, idle_fe = [], []
    for pid, be, fe in rows:
        if rt.side_active(pid, be, "backend", listening):
            (managed_be if rt.backend_running(pid) else idle_be).append(be)
        if rt.side_active(pid, fe, "frontend", listening):
            (managed_fe if rt.frontend_running(pid) else idle_fe).append(fe)
    return managed_be, managed_fe, idle_be, idle_fe


def _probe_tool_versions() -> tuple[str, str, str]:
    return _java_ver(), _cmd_version("mvn", "-v"), _cmd_version("node", "-v")


def _factory_db_label() -> str:
    url = get_settings().database_url or ""
    if "sqlite" in url:
        # sqlite+aiosqlite:///D:/.../factory.db
        path = url.split("///")[-1] if "///" in url else url
        return f"SQLite · {path}"
    if "mysql" in url:
        # 隐藏密码
        try:
            after = url.split("://", 1)[1]
            cred, rest = after.split("@", 1)
            user = cred.split(":")[0]
            return f"MySQL · {user}@{rest.split('?')[0]}"
        except Exception:  # noqa: BLE001
            return "MySQL · (已配置)"
    return url[:64] or "未配置"


def _probe_student_mysql() -> str:
    """学生毕设库（GF_STUDENT_MYSQL_*），与工厂元数据库分开。"""
    s = get_settings()
    target = f"{s.gf_student_mysql_user}@{s.gf_student_mysql_host}:{s.gf_student_mysql_port}"
    try:
        import pymysql

        conn = pymysql.connect(
            host=s.gf_student_mysql_host,
            port=s.gf_student_mysql_port,
            user=s.gf_student_mysql_user,
            password=s.gf_student_mysql_password,
            connect_timeout=2,
        )
        conn.close()
        return f"{target} · 可达"
    except Exception as e:  # noqa: BLE001
        msg = str(e).split("\n")[0][:48]
        return f"{target} · 失败（{msg}）"


@router.get("/system", response_model=SystemInfo, tags=["系统"], summary="运行环境信息")
async def system_info(db: AsyncSession = Depends(get_db)):
    s = get_settings()
    result = await db.execute(select(Project.id, Project.backend_port, Project.frontend_port))
    rows = list(result.all())
    # 同步探测放到线程，避免堵死事件循环拖慢其它接口
    (managed_be, managed_fe, idle_be, idle_fe), (jdk, maven, node), mysql = await asyncio.gather(
        asyncio.to_thread(_probe_used_ports, rows),
        asyncio.to_thread(_probe_tool_versions),
        asyncio.to_thread(_probe_student_mysql),
    )
    managed_be, managed_fe = sorted(set(managed_be)), sorted(set(managed_fe))
    idle_be, idle_fe = sorted(set(idle_be)), sorted(set(idle_fe))
    return SystemInfo(
        jdk=jdk,
        maven=maven,
        node=node,
        mysql=mysql,
        factory_db=_factory_db_label(),
        public_host=s.public_host,
        bind_host=s.bind_host,
        backend_ports=f"{s.backend_port_start}–{s.backend_port_end}",
        frontend_ports=f"{s.frontend_port_start}–{s.frontend_port_end}",
        used_backend=sorted(set(managed_be) | set(idle_be)),
        used_frontend=sorted(set(managed_fe) | set(idle_fe)),
        managed_backend=managed_be,
        managed_frontend=managed_fe,
        idle_backend=idle_be,
        idle_frontend=idle_fe,
        workspace=str(s.workspace_dir.resolve()),
        uploads=str(s.uploads_dir.resolve()),
        skeletons=str(s.skeletons_dir.resolve()),
    )


@router.post("/system/free-ports", response_model=ApiOk, tags=["系统"], summary="释放僵尸端口")
async def free_ports(db: AsyncSession = Depends(get_db)):
    """清理未托管但仍占端口的僵尸进程；正在预览的项目不会被停止。"""
    result = await db.execute(select(Project))
    projects = list(result.scalars().all())

    def _run() -> tuple[int, int, dict[str, tuple[bool, bool]]]:
        listening = rt.listening_tcp_ports()
        cleaned = 0
        still_active = 0
        flags: dict[str, tuple[bool, bool]] = {}
        for p in projects:
            if rt.free_idle_ports(p.id, p.backend_port, p.frontend_port, listening):
                cleaned += 1
                flags[p.id] = (False, False)
            else:
                be = rt.side_active(p.id, p.backend_port, "backend", listening)
                fe = rt.side_active(p.id, p.frontend_port, "frontend", listening)
                flags[p.id] = (be, fe)
                if be or fe:
                    still_active += 1
            # free 可能改了端口占用，刷新 listening 成本高；批量结束前用旧集合同步即可
        return cleaned, still_active, flags

    cleaned, still_active, flags = await asyncio.to_thread(_run)
    await reclaim_idle_ports(db)
    for p in projects:
        be, fe = flags.get(p.id, (False, False))
        p.backend_running = be
        p.frontend_running = fe
        if not be and not fe:
            p.backend_port = 0
            p.frontend_port = 0
        if not be and not fe and p.status == ProjectStatus.running.value:
            p.status = ProjectStatus.generated.value
    await db.commit()
    data = {"cleaned": cleaned, "still_active": still_active}
    if cleaned and still_active:
        return ApiOk(
            message=(
                f"已清理 {cleaned} 个僵尸占用；另有 {still_active} 个预览仍在运行，"
                "请到项目详情停止"
            ),
            data=data,
        )
    if cleaned:
        return ApiOk(message=f"已清理 {cleaned} 个项目的僵尸端口占用", data=data)
    if still_active:
        return ApiOk(
            message=(
                f"当前 {still_active} 个占用均为正在运行的预览，"
                "请到对应项目详情停止；本按钮不会停运行中的预览"
            ),
            data=data,
        )
    return ApiOk(message="没有可释放的空闲占用", data=data)


@router.get("/catalog", tags=["系统"], summary="骨架与领域目录")
async def catalog():
    from app.bake.catalog import (
        ARCHETYPES,
        CHROME_STYLES,
        DOMAIN_GROUPS,
        DOMAINS,
        LAYOUT_SHELLS,
        TYPE_PAIRINGS,
        themes_for_domain,
    )
    from app.bake.api_style import CART_MUTATE_STYLES, ITEM_REF_STYLES

    domain_group_of = {
        dom_id: group_id
        for group_id, _label, members in DOMAIN_GROUPS
        for dom_id in members
    }

    def _domain_row(dom_id: str) -> dict:
        meta = DOMAINS[dom_id]
        name = meta["label"]
        return {
            "id": dom_id,
            "name": name,
            "label": f"{dom_id} · {name}",
            "group": domain_group_of.get(dom_id),
        }

    return {
        "archetypes": [
            {"id": k, "label": f"{k} · {v['label']}"} for k, v in ARCHETYPES.items()
        ],
        "domains": [
            _domain_row(k) for k in DOMAINS if k != "DOM-GENERIC"
        ]
        + [_domain_row("DOM-GENERIC")],
        "domain_groups": [
            {"id": gid, "label": glabel, "domains": list(members)}
            for gid, glabel, members in DOMAIN_GROUPS
        ],
        "themes_by_domain": {k: themes_for_domain(k) for k in DOMAINS},
        "chrome_styles": list(CHROME_STYLES),
        "layout_shells": list(LAYOUT_SHELLS),
        "type_pairings": list(TYPE_PAIRINGS),
        "api_style_axes": {
            "item_ref": list(ITEM_REF_STYLES),
            "cart_mutate": list(CART_MUTATE_STYLES),
        },
    }

