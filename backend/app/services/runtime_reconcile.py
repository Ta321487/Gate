"""运行态 / checklist 投影：进程内后台对账，不挂在列表 GET 上。

列表与 /stats 只读库；启停与详情仍可当场 sync 写回。
不上 Redis：单进程 asyncio 循环即可。
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Project
from app.services import projects as project_svc
from app.services import runtime as rt

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_log = logging.getLogger("gf.runtime")
_task: asyncio.Task[None] | None = None


async def reconcile_projects_projection(db: AsyncSession) -> bool:
    """全表廉价对账并在 dirty 时 commit。持 reconcile_lock。"""
    async with project_svc.reconcile_lock:
        result = await db.execute(select(Project))
        items = list(result.scalars().all())
        # 放开读事务，再扫盘 / netstat（与旧列表路径同口径）
        await project_svc.release_read_transaction(db)
        listening: set[int] | None = None
        if any(p.backend_port or p.frontend_port for p in items):
            listening = await asyncio.to_thread(rt.listening_tcp_ports)
        dirty = await asyncio.to_thread(
            project_svc.reconcile_list_items, items, listening=listening
        )
        if dirty:
            await db.commit()
        return dirty


async def _budgeted_orphan_disk_purge(db: AsyncSession) -> None:
    """每轮对账后小额清孤儿盘；与全量受理互斥，忙则跳过。"""
    from app.services import orphan_disk_purge as orphan_purge

    per = int(getattr(get_settings(), "gf_orphan_purge_per_pass", 1) or 0)
    if per <= 0:
        return
    result = await db.execute(select(Project.id))
    alive = set(result.scalars().all())
    await project_svc.release_read_transaction(db)
    await asyncio.to_thread(orphan_purge.try_budgeted_purge, alive)


async def _reconcile_loop(interval_sec: float) -> None:
    # 启动先跑一轮，清掉重启后残留的 running / 端口投影
    while True:
        try:
            async with SessionLocal() as db:
                dirty = await reconcile_projects_projection(db)
                if dirty:
                    _log.info("runtime reconcile committed")
                await _budgeted_orphan_disk_purge(db)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            _log.exception("runtime reconcile failed")
        await asyncio.sleep(interval_sec)


def start_runtime_reconcile() -> None:
    """lifespan 启动；GF_RUNTIME_RECONCILE_SEC<=0 则关闭。"""
    global _task
    if _task is not None and not _task.done():
        return
    interval = float(getattr(get_settings(), "gf_runtime_reconcile_sec", 5.0) or 0.0)
    if interval <= 0:
        _log.info("runtime reconcile disabled (GF_RUNTIME_RECONCILE_SEC<=0)")
        return
    _task = asyncio.create_task(
        _reconcile_loop(interval), name="gf-runtime-reconcile"
    )
    _log.info("runtime reconcile started interval=%.1fs", interval)


async def stop_runtime_reconcile() -> None:
    global _task
    task = _task
    _task = None
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
