"""孤儿工程盘清理：受理式全量 + 对账小额额度，互斥，不绑死 HTTP 生命周期。

状态在进程内；单 worker 工厂足够。与 runtime_reconcile 共用额度旋钮。
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

from app.core.config import get_settings
from app.services import projects as project_svc

_log = logging.getLogger("gf.orphan_disk")

# 同步互斥：全量任务与对账额度共用，避免两路同时 rmtree
_run_lock = threading.Lock()
_task: asyncio.Task[None] | None = None
_state: dict[str, Any] = {
    "status": "idle",  # idle | running | done | error
    "mode": None,  # full | budget
    "accepted": False,
    "already_running": False,
    "started_at": None,
    "finished_at": None,
    "message": "",
    "removed": 0,
    "errors": [],
    "last_result": None,
}


def snapshot() -> dict[str, Any]:
    """只读副本，给 API / 前端轮询。"""
    return dict(_state)


def _set(**kwargs: Any) -> None:
    _state.update(kwargs)


def _apply_result(result: dict[str, Any], *, mode: str, ok: bool, err: str | None = None) -> None:
    removed = int(result.get("removed") or 0)
    errors = list(result.get("errors") or [])
    if err:
        errors = [*errors, err]
    if ok and not errors:
        msg = f"已清理 {removed} 项孤儿磁盘产物"
    elif ok:
        msg = f"已清理 {removed} 项孤儿磁盘产物（{len(errors)} 项失败）"
    else:
        msg = err or "清理失败"
    _set(
        status="done" if ok else "error",
        mode=mode,
        finished_at=time.time(),
        message=msg,
        removed=removed,
        errors=errors,
        last_result=result,
        accepted=False,
        already_running=False,
    )


def _run_purge(alive_ids: set[str], *, max_dirs: int | None) -> dict[str, Any]:
    """在工作线程内执行；调用方须已持有 _run_lock。"""
    return project_svc.purge_orphan_project_disk(alive_ids, max_dirs=max_dirs)


async def enqueue_full(alive_ids: set[str] | frozenset[str]) -> dict[str, Any]:
    """受理全量清理：立刻返回；已在跑则返回 already_running。"""
    global _task
    alive = {str(x) for x in alive_ids if x}

    if not _run_lock.acquire(blocking=False):
        _set(already_running=True, accepted=False)
        snap = snapshot()
        snap["message"] = snap.get("message") or "清理进行中"
        return snap

    _set(
        status="running",
        mode="full",
        accepted=True,
        already_running=False,
        started_at=time.time(),
        finished_at=None,
        message="磁盘清理已开始",
        removed=0,
        errors=[],
        last_result=None,
    )

    async def _job() -> None:
        try:
            result = await asyncio.to_thread(_run_purge, alive, max_dirs=None)
            _apply_result(result, mode="full", ok=True)
            _log.info(
                "orphan disk full purge done removed=%s errors=%s",
                result.get("removed"),
                len(result.get("errors") or []),
            )
        except Exception as e:  # noqa: BLE001
            _log.exception("orphan disk full purge failed")
            _apply_result(
                {
                    "removed": 0,
                    "errors": [],
                    "removed_workspaces": [],
                    "removed_logs": [],
                    "removed_zips": [],
                },
                mode="full",
                ok=False,
                err=str(e),
            )
        finally:
            if _run_lock.locked():
                _run_lock.release()

    _task = asyncio.create_task(_job(), name="gf-orphan-disk-full")
    return snapshot()


def try_budgeted_purge(alive_ids: set[str] | frozenset[str]) -> dict[str, Any] | None:
    """对账线程：有额度且空闲时同步清一小批；忙则跳过。

    在 to_thread / 同步上下文调用；不启 asyncio 任务。
    """
    settings = get_settings()
    per = int(getattr(settings, "gf_orphan_purge_per_pass", 1) or 0)
    if per <= 0:
        return None
    if not _run_lock.acquire(blocking=False):
        return None

    alive = {str(x) for x in alive_ids if x}
    _set(
        status="running",
        mode="budget",
        accepted=True,
        already_running=False,
        started_at=time.time(),
        finished_at=None,
        message=f"后台额度清理（每轮 ≤{per}）",
        removed=0,
        errors=[],
        last_result=None,
    )
    try:
        result = _run_purge(alive, max_dirs=per)
        if int(result.get("removed") or 0) == 0 and not result.get("errors"):
            _set(
                status="idle",
                mode="budget",
                finished_at=time.time(),
                message="",
                removed=0,
                errors=[],
                last_result=result,
                accepted=False,
                already_running=False,
            )
        else:
            _apply_result(result, mode="budget", ok=True)
            _log.info(
                "orphan disk budget purge removed=%s budget=%s",
                result.get("removed"),
                per,
            )
        return result
    except Exception as e:  # noqa: BLE001
        _log.exception("orphan disk budget purge failed")
        _apply_result(
            {"removed": 0, "errors": [], "removed_workspaces": [], "removed_logs": [], "removed_zips": []},
            mode="budget",
            ok=False,
            err=str(e),
        )
        return snapshot()
    finally:
        if _run_lock.locked():
            _run_lock.release()
