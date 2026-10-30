"""项目磁盘生命周期：工作区 / ZIP / 日志 / 孤儿清理。"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from app.core.config import get_settings
from app.models import Project
from app.services import runtime as rt

logger = logging.getLogger(__name__)

# 常见占锁进程名（Windows 预览 JVM / 前端 / IDE）；CIM 匹配时去 .exe 再比
_LOCK_SUSPECT_BASENAMES = frozenset(
    {
        "java",
        "javaw",
        "node",
        "vite",
        "mvn",
        "idea64",
        "code",
        "cursor",
        "clion64",
        "devenv",
        "eclipse",
        "studio64",
        "gradle",
    }
)

#: bake 进行中标记：孤儿清理不得删带此文件的工作区（对账额度清盘会误伤正在出包的目录）
BAKE_IN_PROGRESS_REL = Path(".factory") / "bake_in_progress"
#: 刚写完的工作区宽限期（秒）：bake 结束后预览/compile 仍可能占用目录。
#: 默认 0=只认 bake 进行中标记，不按 mtime 兜底；确需缓冲由调用方显式传 fresh_grace_sec。
ORPHAN_FRESH_GRACE_SEC = 0


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


def orphan_workspace_protected(
    child: Path, *, fresh_grace_sec: float | None = None
) -> bool:
    """孤儿清理是否应跳过该工作区（bake 中 / 宽限期内的新鲜目录）。"""
    if (child / BAKE_IN_PROGRESS_REL).is_file():
        return True
    grace = ORPHAN_FRESH_GRACE_SEC if fresh_grace_sec is None else fresh_grace_sec
    if grace <= 0:
        return False
    try:
        age = time.time() - child.stat().st_mtime
    except OSError:
        return False
    # Windows 上新建目录偶发 st_mtime 略超前 → age 为负，仍视为「新鲜」
    return age < grace


def _is_sharing_violation_text(text: str) -> bool:
    t = text or ""
    return (
        "WinError 32" in t
        or "另一个程序正在使用此文件" in t
        or "being used by another process" in t.lower()
    )


def _is_sharing_violation(err: BaseException | None) -> bool:
    if err is None:
        return False
    if isinstance(err, OSError):
        # WinError 32 = sharing violation；Errno 13 偶发只读/拒删
        if getattr(err, "winerror", None) == 32:
            return True
        if err.errno in {13, 11}:  # EACCES / EAGAIN
            return True
    return _is_sharing_violation_text(str(err))


def path_from_os_error(err: BaseException | None) -> Path | None:
    """从 OSError/PermissionError 抽出被锁路径（filename 或文案里的盘符路径）。"""
    if err is None:
        return None
    fn = getattr(err, "filename", None)
    if isinstance(fn, (str, bytes)) and fn:
        try:
            return Path(fn if isinstance(fn, str) else fn.decode("utf-8", "replace"))
        except OSError:
            pass
    text = str(err)
    # Windows: ...: 'D:\...\file.java' 或 "...file.java"
    m = re.search(r"""['"]([A-Za-z]:\\[^'"]+)['"]""", text)
    if m:
        return Path(m.group(1))
    m = re.search(r"""['"](/[^'"]+)['"]""", text)
    if m:
        return Path(m.group(1))
    return None


def _workspace_needle(path: Path) -> str:
    """匹配用：优先工作区根（…/workspace/gf-xxx），否则整路径。"""
    try:
        target = str(path.resolve())
    except OSError:
        target = str(path)
    parts = Path(target).parts
    try:
        wi = next(i for i, p in enumerate(parts) if p.lower() == "workspace")
        if wi + 1 < len(parts):
            return str(Path(*parts[: wi + 2]))
    except StopIteration:
        pass
    return target


def _suspect_lock_holders(path: Path, *, limit: int = 6) -> list[str]:
    """尽量列出可能占着该路径的本机进程（Windows：CIM；其它平台空）。

    不依赖 handle.exe / 管理员；查不到不编造。
    匹配命令行含工作区根，或含被锁文件名（IDE 单开文件时常只有文件名）。
    """
    if sys.platform != "win32":
        return []
    needle = _workspace_needle(path)
    leaf = path.name if path.name else ""
    needle_ps = needle.replace("'", "''")
    leaf_ps = leaf.replace("'", "''")
    names_ps = ",".join(f"'{n}'" for n in sorted(_LOCK_SUSPECT_BASENAMES))
    script = (
        f"$n = '{needle_ps}'.ToLower();\n"
        f"$leaf = '{leaf_ps}'.ToLower();\n"
        f"$names = @({names_ps});\n"
        "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |\n"
        "  Where-Object {\n"
        "    $base = ([string]$_.Name) -replace '\\.exe$','';\n"
        "    if ($names -notcontains $base.ToLower()) { return $false }\n"
        "    $cl = ([string]$_.CommandLine).ToLower()\n"
        "    if (-not $cl) { return $false }\n"
        "    if ($n -and $cl.Contains($n)) { return $true }\n"
        "    if ($leaf -and $leaf.Length -ge 6 -and $cl.Contains($leaf)) { return $true }\n"
        "    return $false\n"
        "  } |\n"
        f"  Select-Object -First {int(limit)} |\n"
        "  ForEach-Object {\n"
        "    $bn = ([string]$_.Name) -replace '\\.exe$','';\n"
        "    Write-Output ($bn + ' pid=' + $_.ProcessId)\n"
        "  }\n"
    )
    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    out: list[str] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if line:
            out.append(line)
    return out[:limit]


def format_file_busy_error(
    path: Path,
    err: BaseException | None,
    *,
    action: str = "删除",
) -> str:
    """给人看的占用失败说明：步骤语义 + 文件 + 嫌疑进程 + 怎么重试。"""
    leaf = path.name or str(path)
    try:
        shown = str(path.resolve())
    except OSError:
        shown = str(path)
    # 截短超长路径，中间用 …
    if len(shown) > 120:
        shown = shown[:48] + "…" + shown[-48:]
    holders = _suspect_lock_holders(path)
    parts = [
        f"工作区文件被占用，无法{action}",
        f"文件 {leaf}",
        f"路径 {shown}",
    ]
    if holders:
        parts.append("可能占用进程：" + "；".join(holders))
    else:
        parts.append(
            "未查到命令行含本工作区的 java/node/IDE（仍可能是编辑器打开该文件、杀毒扫描或已退出残留句柄）"
        )
    parts.append(
        "请先停本机预览（后端 Java / 前端 Vite），关闭 IDE 里该文件标签后，点「从失败步骤重试」"
    )
    if err is not None:
        parts.append(f"系统原文：{err}")
    return " · ".join(parts)


def humanize_job_exception(exc: BaseException | str) -> str:
    """任务失败文案：占用类 OSError 补进程线索；已格式化的 RuntimeError 原样保留。"""
    if isinstance(exc, str):
        text = exc.strip() or "未知错误"
        if _is_sharing_violation_text(text) and "工作区文件被占用" not in text:
            path = path_from_os_error(OSError(text)) or Path(".")
            return format_file_busy_error(path, OSError(text), action="读写")
        return text

    text = str(exc).strip() or "未知错误"
    if "工作区文件被占用" in text:
        return text
    if _is_sharing_violation(exc) or _is_sharing_violation_text(text):
        path = path_from_os_error(exc) or Path(".")
        action = "删除" if ("无法删除" in text or "unlink" in text.lower()) else "读写"
        return format_file_busy_error(path, exc, action=action)
    return text


def release_workspace_locks(workspace: Path) -> list[str]:
    """出包裁剪前尽量松锁：卸前端联接；记录仍占着工作区的嫌疑进程（不擅自杀 IDE）。"""
    ws = Path(workspace)
    notes: list[str] = []
    try:
        rt.detach_frontend_deps(ws)
        notes.append("detach_frontend_deps")
    except Exception as e:  # noqa: BLE001
        logger.warning("detach_frontend_deps failed ws=%s: %s", ws, e)
        notes.append(f"detach_frontend_deps_fail:{e}")
    holders = _suspect_lock_holders(ws)
    if holders:
        notes.append("suspects=" + ",".join(holders))
        logger.warning(
            "workspace still has suspect lock holders before prune ws=%s %s",
            ws,
            holders,
        )
    return notes


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
        if _is_sharing_violation(last_err):
            raise RuntimeError(format_file_busy_error(path, last_err, action="删除"))
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
    fresh_grace_sec: float | None = None,
) -> dict:
    """清理库中已不存在的工程目录、日志目录与对应 ZIP；不动 cache / uploads。

    max_dirs：本轮最多处理几个孤儿工程目录（按名排序）。每个工程顺带清同名日志与
    对应 ZIP。None 表示一次清光（含仅残留日志/ZIP 的孤儿）。
    fresh_grace_sec：刚写完工作区的宽限秒数；None 用 ORPHAN_FRESH_GRACE_SEC（默认 0）。
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
            if orphan_workspace_protected(child, fresh_grace_sec=fresh_grace_sec):
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

