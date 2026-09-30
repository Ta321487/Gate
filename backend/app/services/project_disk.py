"""项目磁盘生命周期：工作区 / ZIP / 日志 / 孤儿清理。"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from app.core.config import get_settings
from app.models import Project
from app.services import runtime as rt

logger = logging.getLogger(__name__)

#: bake 进行中标记：孤儿清理不得删带此文件的工作区（对账额度清盘会误伤正在出包的目录）
BAKE_IN_PROGRESS_REL = Path(".factory") / "bake_in_progress"
#: 刚写完的工作区宽限期（秒）：bake 结束后预览/compile 仍可能占用目录
ORPHAN_FRESH_GRACE_SEC = 30 * 60


def resolve_workspace_dir(project: Project) -> Path:
    """优先 workspace_path；否则 data/workspace/{id}。"""
    if project.workspace_path:
        return Path(project.workspace_path)
    return get_settings().workspace_dir / project.id


def mark_bake_in_progress(workspace: Path) -> Path:
    """写入 bake 进行中标记，供孤儿清理跳过。"""
    lock = workspace / BAKE_IN_PROGRESS_REL
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("baking\n", encoding="utf-8")
    return lock


def clear_bake_in_progress(workspace: Path) -> None:
    lock = workspace / BAKE_IN_PROGRESS_REL
    try:
        lock.unlink(missing_ok=True)
    except OSError:
        pass


def orphan_workspace_protected(child: Path) -> bool:
    """孤儿清理是否应跳过该工作区（bake 中 / 刚出炉）。"""
    if (child / BAKE_IN_PROGRESS_REL).is_file():
        return True
    if ORPHAN_FRESH_GRACE_SEC <= 0:
        return False
    try:
        age = time.time() - child.stat().st_mtime
    except OSError:
        return False
    # Windows 上新建目录偶发 st_mtime 略超前 → age 为负，仍视为「新鲜」
    return age < ORPHAN_FRESH_GRACE_SEC


def remove_tree_reliable(
    path: Path, *, retries: int = 8, delay: float = 0.25
) -> None:
    """带重试删除目录；仍残留则抛 RuntimeError（避免假成功）。"""
    if not path.exists():
        return
    last_err: Exception | None = None
    for i in range(retries):
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
        except OSError as e:
            last_err = e
            time.sleep(delay * (1 + i * 0.4))
            continue
        if not path.exists():
            return
        time.sleep(delay)
    if path.exists():
        raise RuntimeError(f"无法删除 {path}: {last_err or '目录仍存在'}")

def remove_project_zips(project_id: str, zip_path: str | None) -> None:
    """清理工作区下该项目 ZIP（旧名 + {id}-*.zip + 记录路径）。"""
    settings = get_settings()
    legacy = settings.workspace_dir / f"{project_id}-thesis-app.zip"
    if legacy.exists():
        try:
            legacy.unlink()
        except OSError as e:
            logger.warning("删除旧 ZIP 失败 %s: %s", legacy, e)
    for zp in settings.workspace_dir.glob(f"{project_id}-*.zip"):
        try:
            zp.unlink()
        except OSError as e:
            logger.warning("删除 ZIP 失败 %s: %s", zp, e)
    if zip_path:
        try:
            Path(zip_path).unlink(missing_ok=True)
        except OSError as e:
            logger.warning("删除 zip_path 失败 %s: %s", zip_path, e)

def remove_project_logs(project_id: str) -> None:
    """删项目日志目录；删不干净则抛错（与工程目录同口径）。"""
    logs = get_settings().logs_dir / project_id
    if logs.exists():
        remove_tree_reliable(logs)

def purge_orphan_project_disk(
    alive_ids: set[str] | frozenset[str],
    *,
    max_dirs: int | None = None,
) -> dict:
    """清理库中已不存在的工程目录、日志目录与对应 ZIP；不动 cache / uploads。

    max_dirs：本轮最多处理几个孤儿工程目录（按名排序）。每个工程顺带清同名日志与
    对应 ZIP。None 表示一次清光（含仅残留日志/ZIP 的孤儿）。
    """
    alive = {str(x) for x in alive_ids if x}
    settings = get_settings()
    removed_workspaces: list[str] = []
    removed_logs: list[str] = []
    removed_zips: list[str] = []
    errors: list[str] = []
    budget = None if max_dirs is None else max(0, int(max_dirs))

    def _remove_zip_for(pid: str) -> None:
        ws_root = settings.workspace_dir
        if not ws_root.is_dir():
            return
        for zp in sorted(ws_root.glob(f"{pid}-*.zip")):
            if not zp.is_file():
                continue
            try:
                zp.unlink()
                removed_zips.append(zp.name)
            except OSError as e:
                msg = f"{zp}: {e}"
                errors.append(msg)
                logger.warning("清理孤儿 ZIP 失败 %s", msg)

    def _remove_logs_for(pid: str) -> None:
        logs = settings.logs_dir / pid
        if not logs.is_dir():
            return
        try:
            remove_tree_reliable(logs)
            removed_logs.append(pid)
        except Exception as e:  # noqa: BLE001
            msg = f"{logs}: {e}"
            errors.append(msg)
            logger.warning("清理孤儿日志失败 %s", msg)

    ws_root = settings.workspace_dir
    all_orphan_ws: list[Path] = []
    if ws_root.is_dir():
        for child in sorted(ws_root.iterdir(), key=lambda p: p.name):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if child.name in alive:
                continue
            if orphan_workspace_protected(child):
                continue
            all_orphan_ws.append(child)

    truncated = budget is not None and len(all_orphan_ws) > budget
    orphan_ws = all_orphan_ws[:budget] if budget is not None else all_orphan_ws

    for child in orphan_ws:
        try:
            rt.detach_frontend_deps(child)
            remove_tree_reliable(child)
            removed_workspaces.append(child.name)
        except Exception as e:  # noqa: BLE001
            msg = f"{child}: {e}"
            errors.append(msg)
            logger.warning("清理孤儿目录失败 %s", msg)
            continue
        _remove_logs_for(child.name)
        _remove_zip_for(child.name)

    # 全量模式：清掉仅残留的日志目录与 ZIP（额度模式留给后续轮次）
    if budget is None:
        logs_root = settings.logs_dir
        if logs_root.is_dir():
            for child in sorted(logs_root.iterdir(), key=lambda p: p.name):
                if not child.is_dir() or child.name.startswith("."):
                    continue
                if child.name in alive or child.name in removed_logs:
                    continue
                try:
                    remove_tree_reliable(child)
                    removed_logs.append(child.name)
                except Exception as e:  # noqa: BLE001
                    msg = f"{child}: {e}"
                    errors.append(msg)
                    logger.warning("清理孤儿日志失败 %s", msg)

        if ws_root.is_dir():
            for zp in sorted(ws_root.glob("*.zip")):
                if not zp.is_file():
                    continue
                if any(zp.name.startswith(f"{pid}-") for pid in alive):
                    continue
                if zp.name in removed_zips:
                    continue
                try:
                    zp.unlink()
                    removed_zips.append(zp.name)
                except OSError as e:
                    msg = f"{zp}: {e}"
                    errors.append(msg)
                    logger.warning("清理孤儿 ZIP 失败 %s", msg)

    return {
        "removed_workspaces": removed_workspaces,
        "removed_logs": removed_logs,
        "removed_zips": removed_zips,
        "errors": errors,
        "removed": len(removed_workspaces) + len(removed_logs) + len(removed_zips),
        "truncated": truncated,
    }

def remove_project_source_if_owned(
    source_path: str | None, *, shared: bool
) -> None:
    """仅当路径在 uploads 下且无其它项目共用时清理开题材料。"""
    if shared or not source_path:
        return
    path = Path(source_path)
    try:
        uploads = get_settings().uploads_dir.resolve()
        resolved = path.resolve()
    except OSError:
        return
    if uploads != resolved and uploads not in resolved.parents:
        return
    try:
        if resolved.is_file():
            parent = resolved.parent
            # 上传包目录整删；散落单文件只删文件
            if parent != uploads and (
                parent.name.endswith("_bundle") or resolved.name == "manifest.json"
            ):
                shutil.rmtree(parent, ignore_errors=True)
            else:
                resolved.unlink(missing_ok=True)
        elif resolved.is_dir():
            shutil.rmtree(resolved, ignore_errors=True)
    except OSError as e:
        logger.warning("清理开题材料失败 %s: %s", source_path, e)

def purge_project_disk(project: Project) -> None:
    """删除工程目录与 ZIP；工程目录删不干净则抛错（项目行勿先删）。"""
    ws = resolve_workspace_dir(project)
    if ws.exists():
        rt.detach_frontend_deps(ws)
        remove_tree_reliable(ws)
    # 兼容：workspace_path 与默认目录不一致时两边都清
    default_ws = get_settings().workspace_dir / project.id
    if default_ws != ws and default_ws.exists():
        rt.detach_frontend_deps(default_ws)
        remove_tree_reliable(default_ws)
    remove_project_zips(project.id, project.zip_path)
    remove_project_logs(project.id)

