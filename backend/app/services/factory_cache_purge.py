"""工厂共享缓存清理：data/cache 与各工作区 .runtime-tmp。

不动：开题上传、项目工程正文、骨架、本机 ~/.m2。
有预览进程在跑时默认拒绝（node_modules 联接中，删了会炸预览）。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services import runtime as rt

# 已知子目录（按名清理；也扫 cache 根下其它一级目录）
_NAMED_BUCKETS = (
    "baseline-frontend",
    "auth-heroes",
    "portal-banners",
    "local-atmosphere",
)


def _dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    try:
        if path.is_file():
            return path.stat().st_size
        for p in path.rglob("*"):
            try:
                if p.is_file():
                    total += p.stat().st_size
            except OSError:
                continue
    except OSError:
        return 0
    return total


def _fmt_mb(n: int) -> str:
    if n <= 0:
        return "0 MB"
    return f"{n / (1024 * 1024):.1f} MB"


def _rmtree(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return True, "不存在"
    try:
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
        else:
            shutil.rmtree(path, ignore_errors=False)
        return True, "已删"
    except OSError as e:
        # Windows 联接/占用时再试 ignore
        try:
            shutil.rmtree(path, ignore_errors=True)
            if not path.exists():
                return True, "已删（忽略部分错误）"
        except OSError:
            pass
        return False, str(e)[:120]


def preview_running_count() -> int:
    n = 0
    for h in list(rt.STORE.backends.values()) + list(rt.STORE.frontends.values()):
        if h and getattr(h, "process", None) is not None:
            proc = h.process
            if proc.poll() is None:
                n += 1
    return n


def cache_status() -> dict[str, Any]:
    """供运行环境页展示：各缓存桶占用与可否清理。"""
    s = get_settings()
    cache = s.cache_dir.resolve()
    buckets: list[dict[str, Any]] = []
    total = 0
    names_seen: set[str] = set()
    for name in _NAMED_BUCKETS:
        p = cache / name
        names_seen.add(name)
        sz = _dir_size_bytes(p)
        total += sz
        buckets.append(
            {
                "key": name,
                "path": str(p),
                "bytes": sz,
                "size_label": _fmt_mb(sz),
                "exists": p.exists(),
            }
        )
    if cache.is_dir():
        for child in sorted(cache.iterdir()):
            if child.name in names_seen or child.name.startswith("."):
                continue
            sz = _dir_size_bytes(child)
            total += sz
            buckets.append(
                {
                    "key": child.name,
                    "path": str(child.resolve()),
                    "bytes": sz,
                    "size_label": _fmt_mb(sz),
                    "exists": True,
                }
            )

    runtime_tmp_bytes = 0
    runtime_tmp_dirs = 0
    ws = s.workspace_dir
    if ws.is_dir():
        for child in ws.iterdir():
            if not child.is_dir():
                continue
            tmp = child / ".runtime-tmp"
            if tmp.exists():
                runtime_tmp_dirs += 1
                runtime_tmp_bytes += _dir_size_bytes(tmp)

    running = preview_running_count()
    return {
        "cache_dir": str(cache),
        "buckets": buckets,
        "total_bytes": total,
        "total_label": _fmt_mb(total),
        "runtime_tmp_dirs": runtime_tmp_dirs,
        "runtime_tmp_bytes": runtime_tmp_bytes,
        "runtime_tmp_label": _fmt_mb(runtime_tmp_bytes),
        "preview_running": running,
        "can_purge": running == 0,
        "block_reason": (
            f"有 {running} 路预览在跑，请先到项目详情全部停止后再清缓存"
            if running
            else None
        ),
    }


def purge_factory_cache(*, include_runtime_tmp: bool = True) -> dict[str, Any]:
    """删除 data/cache 下内容；可选清各工作区 .runtime-tmp。"""
    running = preview_running_count()
    if running > 0:
        return {
            "ok": False,
            "removed": [],
            "failed": [],
            "freed_bytes": 0,
            "freed_label": "0 MB",
            "message": f"有 {running} 路预览在跑，已拒绝清理（避免弄坏联接中的前端依赖）",
        }

    s = get_settings()
    cache = s.cache_dir.resolve()
    removed: list[str] = []
    failed: list[str] = []
    freed = 0

    targets: list[Path] = []
    if cache.is_dir():
        for child in list(cache.iterdir()):
            if child.name.startswith("."):
                continue
            targets.append(child)

    if include_runtime_tmp and s.workspace_dir.is_dir():
        for child in s.workspace_dir.iterdir():
            if child.is_dir():
                tmp = child / ".runtime-tmp"
                if tmp.exists():
                    targets.append(tmp)

    for path in targets:
        before = _dir_size_bytes(path)
        ok, detail = _rmtree(path)
        label = str(path)
        if ok:
            removed.append(label)
            freed += before
        else:
            failed.append(f"{label}: {detail}")

    # 保证 cache 根目录仍在
    cache.mkdir(parents=True, exist_ok=True)

    parts = []
    if removed:
        parts.append(f"已清理 {len(removed)} 项 · 约释放 {_fmt_mb(freed)}")
    else:
        parts.append("没有可删的缓存")
    if failed:
        parts.append(f"失败 {len(failed)} 项")

    return {
        "ok": not failed,
        "removed": removed,
        "failed": failed,
        "freed_bytes": freed,
        "freed_label": _fmt_mb(freed),
        "message": "；".join(parts),
    }
