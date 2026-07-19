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
from app.llm.client import monthly_tokens_used, project_usage_rows
from app.models import LlmCall, Project, ProjectStatus, SettingRow
from app.schemas import (
    ApiOk,
    DeepSeekBalance,
    DeepSeekBalanceInfo,
    DeepSeekSettings,
    DeepSeekUpdate,
    SystemInfo,
)
from app.services import runtime as rt
from app.services.projects import mask_key, reclaim_idle_ports

router = APIRouter(prefix="/api", tags=["system"])


DEFAULT_DS = {
    "thinking": True,
    "parse_spec": True,
    "island_fill": True,
    "auto_fix": True,
    "qa_report": False,
}


async def _get_ds_row(db: AsyncSession) -> dict:
    row = await db.get(SettingRow, "deepseek")
    if not row:
        row = SettingRow(key="deepseek", value=dict(DEFAULT_DS))
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return dict(row.value or {})


def _hydrate_ds_settings(s, cfg: dict) -> None:
    """把 DB 中的 DeepSeek 配置写回内存 settings，供生成任务读取。"""
    if cfg.get("base_url"):
        s.deepseek_base_url = str(cfg["base_url"])
    if cfg.get("model"):
        s.deepseek_model = str(cfg["model"])
    if "project_token_budget" in cfg:
        s.project_token_budget = int(cfg["project_token_budget"])
    if "monthly_token_budget" in cfg:
        s.monthly_token_budget = int(cfg["monthly_token_budget"])
    if "fix_rounds_max" in cfg:
        s.fix_rounds_max = int(cfg["fix_rounds_max"])


@router.get("/deepseek", response_model=DeepSeekSettings)
async def get_deepseek(db: AsyncSession = Depends(get_db)):
    s = get_settings()
    cfg = await _get_ds_row(db)
    _hydrate_ds_settings(s, cfg)
    tokens = await monthly_tokens_used(db)
    # 预算/开关优先读 DB cfg，避免「已保存」重启后回退到默认值
    return DeepSeekSettings(
        base_url=str(cfg.get("base_url") or s.deepseek_base_url),
        model=str(cfg.get("model") or s.deepseek_model),
        thinking=bool(cfg.get("thinking", True)),
        key_configured=bool(s.deepseek_api_key),
        key_masked=mask_key(s.deepseek_api_key),
        parse_spec=bool(cfg.get("parse_spec", True)),
        island_fill=bool(cfg.get("island_fill", True)),
        auto_fix=bool(cfg.get("auto_fix", True)),
        qa_report=bool(cfg.get("qa_report", False)),
        project_token_budget=int(cfg.get("project_token_budget", s.project_token_budget)),
        monthly_token_budget=int(cfg.get("monthly_token_budget", s.monthly_token_budget)),
        fix_rounds_max=int(cfg.get("fix_rounds_max", s.fix_rounds_max)),
        monthly_tokens_used=int(tokens),
        project_usages=[],
    )


@router.put("/deepseek", response_model=DeepSeekSettings)
async def put_deepseek(body: DeepSeekUpdate, db: AsyncSession = Depends(get_db)):
    s = get_settings()
    row = await db.get(SettingRow, "deepseek")
    if not row:
        row = SettingRow(key="deepseek", value=dict(DEFAULT_DS))
        db.add(row)
    cfg = dict(row.value or DEFAULT_DS)
    data = body.model_dump(exclude_none=True)
    # base_url / model 存 settings 行，Key 永不入库
    for k in ("thinking", "parse_spec", "island_fill", "auto_fix", "qa_report"):
        if k in data:
            cfg[k] = data[k]
    if "base_url" in data:
        cfg["base_url"] = data["base_url"]
        s.deepseek_base_url = data["base_url"]
    if "model" in data:
        cfg["model"] = data["model"]
        s.deepseek_model = data["model"]
    if "project_token_budget" in data:
        s.project_token_budget = data["project_token_budget"]
        cfg["project_token_budget"] = data["project_token_budget"]
    if "monthly_token_budget" in data:
        s.monthly_token_budget = data["monthly_token_budget"]
        cfg["monthly_token_budget"] = data["monthly_token_budget"]
    if "fix_rounds_max" in data:
        s.fix_rounds_max = data["fix_rounds_max"]
        cfg["fix_rounds_max"] = data["fix_rounds_max"]
    row.value = cfg
    await db.commit()
    return await get_deepseek(db)


@router.post("/deepseek/test", response_model=ApiOk)
async def test_deepseek():
    s = get_settings()
    if not s.deepseek_api_key:
        return ApiOk(ok=False, message="未配置 DEEPSEEK_API_KEY")
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{s.deepseek_base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {s.deepseek_api_key}"},
            )
        ms = int((time.perf_counter() - t0) * 1000)
        if r.status_code >= 400:
            return ApiOk(ok=False, message=f"HTTP {r.status_code} · {ms} ms")
        return ApiOk(ok=True, message=f"延迟 {ms} ms · 模型可用", data={"latency_ms": ms})
    except Exception as e:  # noqa: BLE001
        return ApiOk(ok=False, message=str(e))


@router.get("/deepseek/balance", response_model=DeepSeekBalance)
async def deepseek_balance(db: AsyncSession = Depends(get_db)):
    """查询 DeepSeek 官方账户余额：GET /user/balance。"""
    s = get_settings()
    cfg = await _get_ds_row(db)
    _hydrate_ds_settings(s, cfg)
    if not s.deepseek_api_key:
        return DeepSeekBalance(ok=False, message="未配置 DEEPSEEK_API_KEY")
    base = (cfg.get("base_url") or s.deepseek_base_url or "https://api.deepseek.com").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{base}/user/balance",
                headers={
                    "Authorization": f"Bearer {s.deepseek_api_key}",
                    "Accept": "application/json",
                },
            )
        if r.status_code >= 400:
            return DeepSeekBalance(
                ok=False,
                message=f"查询失败 HTTP {r.status_code}：{(r.text or '')[:200]}",
            )
        data = r.json() if r.content else {}
        infos = [
            DeepSeekBalanceInfo(
                currency=str(x.get("currency") or "CNY"),
                total_balance=str(x.get("total_balance") or "0"),
                granted_balance=str(x.get("granted_balance") or "0"),
                topped_up_balance=str(x.get("topped_up_balance") or "0"),
            )
            for x in (data.get("balance_infos") or [])
            if isinstance(x, dict)
        ]
        avail = data.get("is_available")
        return DeepSeekBalance(
            ok=True,
            message="ok",
            is_available=bool(avail) if avail is not None else None,
            balance_infos=infos,
        )
    except Exception as e:  # noqa: BLE001
        return DeepSeekBalance(ok=False, message=str(e))


def _parse_dt(value: str | None, *, end: bool = False) -> datetime | None:
    """解析查询时间：支持 YYYY-MM-DD / ISO；end=True 时日期落在当日末。"""
    if not value:
        return None
    raw = value.strip()
    try:
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            dt = datetime.strptime(raw, "%Y-%m-%d")
            if end:
                return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            return dt
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"时间格式无效: {value}") from e


@router.get("/deepseek/usage")
async def list_usage(
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str | None = None,
    sort_order: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """按项目用量：时间范围 + 项目 ID 模糊查询 + 排序 + 分页。"""
    items, total = await project_usage_rows(
        db,
        q=q,
        date_from=_parse_dt(date_from),
        date_to=_parse_dt(date_to, end=True),
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return {
        "items": items,
        "total": total,
        "page": max(1, int(page)),
        "page_size": max(1, min(100, int(page_size))),
    }


@router.get("/deepseek/calls")
async def list_calls(
    project_id: str | None = None,
    stage: str | None = None,
    ok: bool | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """最近调用：项目 / 阶段 / 结果 / 时间 / 关键字 + 分页。"""
    stmt = select(LlmCall)
    count_stmt = select(func.count()).select_from(LlmCall)
    pid = (project_id or "").strip()
    if pid:
        stmt = stmt.where(LlmCall.project_id == pid)
        count_stmt = count_stmt.where(LlmCall.project_id == pid)
    st = (stage or "").strip()
    if st:
        stmt = stmt.where(LlmCall.stage == st)
        count_stmt = count_stmt.where(LlmCall.stage == st)
    if ok is not None:
        stmt = stmt.where(LlmCall.ok == ok)
        count_stmt = count_stmt.where(LlmCall.ok == ok)
    df = _parse_dt(date_from)
    if df is not None:
        stmt = stmt.where(LlmCall.created_at >= df)
        count_stmt = count_stmt.where(LlmCall.created_at >= df)
    dt = _parse_dt(date_to, end=True)
    if dt is not None:
        stmt = stmt.where(LlmCall.created_at <= dt)
        count_stmt = count_stmt.where(LlmCall.created_at <= dt)
    needle = (q or "").strip()
    if needle:
        like = f"%{needle}%"
        cond = or_(
            LlmCall.project_id.ilike(like),
            LlmCall.detail.ilike(like),
            LlmCall.stage.ilike(like),
        )
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    total = int((await db.scalar(count_stmt)) or 0)
    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))
    offset = (page - 1) * page_size
    result = await db.execute(stmt.order_by(LlmCall.id.desc()).offset(offset).limit(page_size))
    rows = result.scalars().all()
    return {
        "items": [
            {
                "id": r.id,
                "project_id": r.project_id,
                "stage": r.stage,
                "tokens": r.tokens,
                "ok": r.ok,
                "detail": (r.detail or "")[:240],
                "created_at": r.created_at,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


_TOOL_VER_CACHE: dict[str, tuple[float, str]] = {}
_TOOL_VER_TTL = 60.0


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


def _probe_used_ports(rows: list) -> tuple[list[int], list[int]]:
    """一次 netstat + 进程表，不打 HTTP。"""
    listening = rt.listening_tcp_ports()
    used_be, used_fe = [], []
    for pid, be, fe in rows:
        if rt.side_active(pid, be, "backend", listening):
            used_be.append(be)
        if rt.side_active(pid, fe, "frontend", listening):
            used_fe.append(fe)
    return used_be, used_fe


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


@router.get("/system", response_model=SystemInfo)
async def system_info(db: AsyncSession = Depends(get_db)):
    s = get_settings()
    result = await db.execute(select(Project.id, Project.backend_port, Project.frontend_port))
    rows = list(result.all())
    # 同步探测放到线程，避免堵死事件循环拖慢其它接口
    (used_be, used_fe), (jdk, maven, node), mysql = await asyncio.gather(
        asyncio.to_thread(_probe_used_ports, rows),
        asyncio.to_thread(_probe_tool_versions),
        asyncio.to_thread(_probe_student_mysql),
    )
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
        used_backend=sorted(set(used_be)),
        used_frontend=sorted(set(used_fe)),
        workspace=str(s.workspace_dir.resolve()),
        uploads=str(s.uploads_dir.resolve()),
        skeletons=str(s.skeletons_dir.resolve()),
    )


@router.post("/system/free-ports", response_model=ApiOk)
async def free_ports(db: AsyncSession = Depends(get_db)):
    """清理未托管但仍占端口的进程，并同步 running 标志。"""
    result = await db.execute(select(Project))
    projects = list(result.scalars().all())

    def _run() -> tuple[int, dict[str, tuple[bool, bool]]]:
        listening = rt.listening_tcp_ports()
        cleaned = 0
        flags: dict[str, tuple[bool, bool]] = {}
        for p in projects:
            if rt.free_idle_ports(p.id, p.backend_port, p.frontend_port, listening):
                cleaned += 1
                flags[p.id] = (False, False)
            else:
                flags[p.id] = (
                    rt.side_active(p.id, p.backend_port, "backend", listening),
                    rt.side_active(p.id, p.frontend_port, "frontend", listening),
                )
            # free 可能改了端口占用，刷新 listening 成本高；批量结束前用旧集合同步即可
        return cleaned, flags

    cleaned, flags = await asyncio.to_thread(_run)
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
    if cleaned:
        return ApiOk(message=f"已清理 {cleaned} 个项目的空闲端口占用")
    return ApiOk(message="没有可释放的空闲占用")


@router.get("/catalog")
async def catalog():
    from app.bake.catalog import ARCHETYPES, DOMAINS, themes_for_domain

    return {
        "archetypes": [
            {"id": k, "label": f"{k} · {v['label']}"} for k, v in ARCHETYPES.items()
        ],
        "domains": [
            {"id": k, "label": f"{k} · {v['label']}"} for k, v in DOMAINS.items() if k != "DOM-GENERIC"
        ]
        + [{"id": "DOM-GENERIC", "label": "DOM-GENERIC · 通用"}],
        "themes_by_domain": {k: themes_for_domain(k) for k in DOMAINS},
    }
