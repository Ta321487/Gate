"""运行态与 checklist 投影原语（供 runtime_reconcile / 列表后台）。"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bake.gates import evaluate_domain_gates
from app.core.config import get_settings
from app.models import Project, ProjectStatus
from app.services import runtime as rt
from app.services.project_delivery import (
    gates_allow_delivery,
    reset_delivery_mark,
    touch_json_fields,
)

logger = logging.getLogger(__name__)

async def reclaim_idle_ports(db: AsyncSession, *, keep_id: str | None = None) -> int:
    """未在跑的项目释放端口占用，让库存可大于并发预览数。"""
    listening = rt.listening_tcp_ports()
    result = await db.execute(select(Project))
    n = 0
    for proj in result.scalars().all():
        if keep_id and proj.id == keep_id:
            continue
        if not proj.backend_port and not proj.frontend_port:
            continue
        be_on = rt.side_active(proj.id, proj.backend_port, "backend", listening)
        fe_on = rt.side_active(proj.id, proj.frontend_port, "frontend", listening)
        if be_on or fe_on:
            continue
        proj.backend_port = 0
        proj.frontend_port = 0
        n += 1
        if proj.status == ProjectStatus.running.value:
            proj.status = ProjectStatus.generated.value
    return n

async def ensure_project_ports(db: AsyncSession, project: Project) -> tuple[int, int]:
    """启动预览前租用一对端口；已占用则复用。"""
    await reclaim_idle_ports(db, keep_id=project.id)
    if project.backend_port and project.frontend_port:
        return project.backend_port, project.frontend_port

    q = await db.execute(select(Project.backend_port, Project.frontend_port))
    used_be = {r[0] for r in q.all() if r[0]}
    used_fe = {r[1] for r in q.all() if r[1]}
    s = get_settings()
    listening = rt.listening_tcp_ports()
    used_be |= {p for p in listening if s.backend_port_start <= p <= s.backend_port_end}
    used_fe |= {p for p in listening if s.frontend_port_start <= p <= s.frontend_port_end}
    be, fe = await rt.allocate_ports(used_be, used_fe)
    project.backend_port = be
    project.frontend_port = fe
    await db.flush()
    return be, fe

def sync_project_runtime(
    project: Project,
    *,
    listening: set[int] | None = None,
    probe_http: bool = True,
    statuses: tuple[str, str] | None = None,
) -> tuple[str, str, bool]:
    """按真实可服务态纠正 running 标记与项目 status；两侧皆停时还端口。

    返回 (backend_status, frontend_status, dirty)。
    listening：调用方已探测过的 LISTENING 端口；传入后两侧皆停时不再逐项 netstat。
    probe_http：False 时只看进程表/LISTENING（列表页用，避免逐项 HTTP 拖死事件循环）。
    statuses：调用方在线程里已探好的 (backend_status, frontend_status)；传入即跳过探测
    （批量启停用，整批阻塞探测都不落在事件循环里）。
    """
    if statuses is not None:
        be_st, fe_st = statuses
        be = be_st in ("starting", "healthy")
        fe = fe_st in ("starting", "healthy")
    elif probe_http:
        be_st = rt.backend_status(project.id, project.backend_port)
        fe_st = rt.frontend_status(project.id, project.frontend_port)
        be = be_st in ("starting", "healthy")
        fe = fe_st in ("starting", "healthy")
    else:
        be = rt.side_active(
            project.id, project.backend_port, "backend", listening=listening
        )
        fe = rt.side_active(
            project.id, project.frontend_port, "frontend", listening=listening
        )
        be_st = "healthy" if be else "stopped"
        fe_st = "healthy" if fe else "stopped"
    dirty = False
    if project.backend_running != be or project.frontend_running != fe:
        project.backend_running = be
        project.frontend_running = fe
        dirty = True
    if be or fe:
        if project.status not in (
            ProjectStatus.running.value,
            ProjectStatus.generating.value,
        ):
            project.status = ProjectStatus.running.value
            dirty = True
    elif project.status == ProjectStatus.running.value:
        project.status = ProjectStatus.generated.value
        dirty = True
    if not be and not fe and (project.backend_port or project.frontend_port):
        ports = listening if listening is not None else rt.listening_tcp_ports()
        be_listen = bool(project.backend_port and project.backend_port in ports)
        fe_listen = bool(project.frontend_port and project.frontend_port in ports)
        if not be_listen and not fe_listen:
            project.backend_port = 0
            project.frontend_port = 0
            dirty = True
    return be_st, fe_st, dirty

def _clear_stale_zip_ready(project: Project) -> bool:
    """无工作区时仍按 ZIP 在盘 + 库内 gates 收敛 zip_ready（只降不升）。"""
    generating = project.status == ProjectStatus.generating.value
    if generating:
        changed = False
        if project.zip_ready:
            project.zip_ready = False
            changed = True
        if reset_delivery_mark(project):
            changed = True
        return changed
    zip_exists = bool(project.zip_path and Path(str(project.zip_path)).exists())
    downloadable = zip_exists and gates_allow_delivery(project.gates)
    if project.zip_ready and not downloadable:
        project.zip_ready = False
        reset_delivery_mark(project)
        return True
    return False

def sync_checklist_from_workspace(project: Project) -> bool:
    """工作区存在则重算 checklist / gates；缺失时仍收敛陈旧 zip_ready。

    若交付复审存有 last_qa，重挂到 gates（与验圈同口径），避免刷新后 p3q/挡包消失。
    复审进行中且尚未验圈通过时，只降不升 zip_ready（保留进入复审/跑 QA 的锁包意图）。
    """
    if not project.workspace_path:
        return _clear_stale_zip_ready(project)
    ws = Path(project.workspace_path)
    if not ws.exists():
        return _clear_stale_zip_ready(project)
    generating = project.status == ProjectStatus.generating.value
    # 生成中勿与 Job 抢写同一行 gates/checklist（列表轮询会触发）；仅关掉误亮的 zip
    if generating:
        return _clear_stale_zip_ready(project)
    from app.services.delivery_review import (
        apply_qa_to_gates,
        get_review_state,
        is_zip_stale_cached,
        review_allows_zip_promote,
    )

    gates = evaluate_domain_gates(ws, project.spec or {})
    st = get_review_state(project)
    last_qa = st.get("last_qa")
    if isinstance(last_qa, dict) and last_qa:
        apply_qa_to_gates(gates, last_qa)
    new_checklist = gates.get("checklist") or []
    new_gates = {k: v for k, v in gates.items() if k != "checklist"}
    downloadable = gates_allow_delivery(new_gates)
    zip_exists = bool(project.zip_path and Path(str(project.zip_path)).exists())

    # 过期判定与列表投影共用 TTL 缓存：一次对账只遍历一次工作区（合卷时已置 False）
    if downloadable and zip_exists and is_zip_stale_cached(project, ws):
        downloadable = False
    can_promote = review_allows_zip_promote(project)
    # 门禁回退时关掉 zip_ready，并清掉人工已审待发/已发出
    zip_changed = False
    if downloadable and zip_exists and not project.zip_ready and can_promote:
        project.zip_ready = True
        zip_changed = True
    elif (not downloadable or not zip_exists) and project.zip_ready:
        project.zip_ready = False
        zip_changed = True
        reset_delivery_mark(project)
    if project.checklist == new_checklist and project.gates == new_gates and not zip_changed:
        return False
    project.checklist = new_checklist
    project.gates = new_gates
    touch_json_fields(project, "checklist", "gates")
    return True

# 运行态/checklist 投影由 runtime_reconcile 后台写库；列表与 /stats 只读。
# 短 TTL：生成任务自己会写 gates；挡住后台连扫。详情页仍当场重扫。
# reconcile_lock：后台对账与（若有）其它写投影路径互斥，避免双写打架。
_CHECKLIST_LIST_TTL_SEC = 20.0

_checklist_list_at: dict[str, float] = {}

# 上次重算时记下的「投影输入签名」（工作区 size+mtime + spec + 复审态 + zip 路径）。
# 签名一致说明 evaluate_domain_gates 的输入没变，可跳过重算：实测（2026-09-29 本机，
# 每项目 370~750 文件）签名走查 ≈18~20ms/项目，gates 重算要 110~180ms/项目；
# 整轮对账 615ms → 稳态 ≈200ms（本机瓶颈是目录枚举/Defender，不是签名算法）。
_checklist_sig: dict[str, str] = {}

_SIG_PRUNE_DIRS = frozenset(
    {
        "node_modules",
        "target",
        ".git",
        ".mvn",
        "dist",
        ".idea",
        ".vscode",
        "__pycache__",
        ".pytest_cache",
        ".venv",
        "venv",
        "logs",
        "coverage",
        ".mypy_cache",
    }
)

reconcile_lock = asyncio.Lock()

def reset_checklist_list_cache() -> None:
    _checklist_list_at.clear()
    _checklist_sig.clear()

def workspace_signature(workspace: Path) -> str:
    """工作区廉价签名：只取目录枚举自带的 size + mtime_ns，不读文件内容。

    gates 只从 backend/src、frontend/src 与根级 spec/schema 读值，剪掉
    node_modules/target/.git 等产物目录后的全树走查已覆盖其全部输入。
    用 os.scandir + DirEntry.stat（Windows 上由目录枚举缓存，免逐文件额外 syscall），
    比逐个 Path.stat() 约快 20%（本机瓶颈在目录枚举本身）。
    """
    h = hashlib.sha256()

    def walk(current: Path) -> None:
        try:
            with os.scandir(current) as it:
                entries = sorted(it, key=lambda e: e.name)
        except OSError:
            return
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    if entry.name not in _SIG_PRUNE_DIRS:
                        walk(Path(entry.path))
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
                st = entry.stat(follow_symlinks=False)
            except OSError:
                continue
            rel = Path(entry.path).relative_to(workspace).as_posix()
            h.update(f"{rel}|{st.st_size}|{st.st_mtime_ns}\n".encode())

    walk(workspace)
    return h.hexdigest()[:24]

def _projection_input_signature(project: Project, workspace: Path) -> str:
    """投影输入签名 = 工作区签名 + 非文件输入（spec / 复审态 / zip 路径与存在性）。

    复审态（last_qa / last_verify）与 zip 路径都会改变投影结果，必须进签名，
    否则「只改了复审态、工作区没动」时会被误跳过。
    """
    from app.services.delivery_review import get_review_state

    h = hashlib.sha256()
    h.update(("ws:" + workspace_signature(workspace)).encode())
    h.update(("status:" + str(getattr(project, "status", ""))).encode())
    zip_path = str(getattr(project, "zip_path", "") or "")
    h.update(("zip:" + zip_path).encode())
    h.update(("zipexists:" + str(bool(zip_path and Path(zip_path).exists()))).encode())
    pairs = (
        ("spec", getattr(project, "spec", None)),
        ("review", get_review_state(project)),
    )
    for tag, value in pairs:
        try:
            blob = json.dumps(value, sort_keys=True, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            blob = repr(value)
        h.update(f"{tag}:{blob}".encode())
    return h.hexdigest()[:24]

async def release_read_transaction(db: AsyncSession) -> None:
    """结束当前只读事务，避免随后的磁盘扫描占着 SQLite 读锁。"""
    await db.commit()

def _sync_checklist_for_list(
    project: Project, *, allow_scan: bool
) -> tuple[bool, bool]:
    """后台单项目投影收敛，返回 (changed, scanned)。

    generating：只走廉价收敛（只降 zip_ready），不吃重算额度。
    其余项目：TTL 内直接返回；TTL 过后若投影输入签名未变也跳过重算（scanned=False）。
    scanned 只在「真有工作区、因而真跑了 gates 重算」时为 True —— 没工作区的项目
    只走 O(1) 的 _clear_stale_zip_ready，不该占别人的额度。
    allow_scan=False 时把需要的重算推迟到下一轮，且不刷新 TTL —— 下一轮仍按
    「最久未扫」优先排到它，不会被额度饿死。
    """
    generating = project.status == ProjectStatus.generating.value
    if generating:
        changed = sync_checklist_from_workspace(project)
        _checklist_list_at.pop(project.id, None)
        return changed, False
    seen = _checklist_list_at.get(project.id)
    if seen is not None and (time.monotonic() - seen) < _CHECKLIST_LIST_TTL_SEC:
        return False, False
    signature: str | None = None
    ws = Path(project.workspace_path) if getattr(project, "workspace_path", "") else None
    if ws is not None and ws.is_dir():
        signature = _projection_input_signature(project, ws)
        if _checklist_sig.get(project.id) == signature:
            _checklist_list_at[project.id] = time.monotonic()
            return False, False
    if not allow_scan:
        return False, False
    changed = sync_checklist_from_workspace(project)
    _checklist_list_at[project.id] = time.monotonic()
    if signature is None:
        return changed, False
    _checklist_sig[project.id] = signature
    return changed, True

def sync_checklist_for_list(project: Project) -> bool:
    """后台投影：TTL 内不重扫；投影输入签名未变也不重扫。生成中仍走廉价收敛。"""
    return _sync_checklist_for_list(project, allow_scan=True)[0]

def _reconcile_scan_budget(max_scans: int | None) -> int:
    """本轮重算额度；<=0 表示不限（缺省读 GF_RECONCILE_SCAN_PER_PASS）。"""
    if max_scans is not None:
        return int(max_scans)
    return int(getattr(get_settings(), "gf_reconcile_scan_per_pass", 2) or 0)

def reconcile_list_items(
    items: list[Project],
    *,
    listening: set[int] | None = None,
    max_scans: int | None = None,
) -> bool:
    """批量收敛 checklist/运行态（后台投影；供 to_thread，勿在持读事务时调用）。

    max_scans：本轮最多重算几个 checklist 投影（<=0 不限）。重算按「最久未扫」
    优先轮转，额度小时不会总停在同一批项目上；没排到的项目留到下一轮（TTL 不刷新）。
    """
    from app.services.delivery_review import is_zip_stale_cached

    budget = _reconcile_scan_budget(max_scans)
    dirty = False
    scans = 0
    for p in sorted(items, key=lambda q: _checklist_list_at.get(q.id, 0.0)):
        allow_scan = budget <= 0 or scans < budget
        changed, scanned = _sync_checklist_for_list(p, allow_scan=allow_scan)
        if scanned:
            scans += 1
        if changed:
            dirty = True
        _, _, changed = sync_project_runtime(
            p, listening=listening, probe_http=False
        )
        if changed:
            dirty = True
        # 「合卷后工程是否变更」要在后台线程里重算好，列表/统计只读缓存；
        # 生成中的项目跳过 checklist 扫描，这里也要补一次，否则列表没有投影值。
        if getattr(p, "workspace_path", ""):
            is_zip_stale_cached(p)
    return dirty

