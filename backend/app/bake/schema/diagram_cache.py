"""论文图磁盘缓存：按 (kind, params) 落盘 model+svg，打开读盘；参数变了才重算。

目录：``islands/diagram_cache/<kind>__<param_key>.json``
失效：源文件指纹变化，或调用方 ``invalidate`` / ``force=True``。
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("app.bake.diagram_cache")

_CACHE_DIR = Path("islands") / "diagram_cache"
_CACHE_VER = 3

# 各类图参与指纹的相对路径（缺文件记 0）
_SOURCE_RELS: dict[str, tuple[str, ...]] = {
    "classes": (
        "sql/schema.sql",
        "domain.schema.json",
        "islands/class_layout.json",
    ),
    "er": (
        "sql/schema.sql",
        "domain.schema.json",
        "islands/er_labels.json",
    ),
    "modules": ("domain.schema.json", "spec.json"),
    "architecture": ("domain.schema.json", "spec.json"),
    "sequences": ("domain.schema.json", "spec.json"),
    "activities": ("domain.schema.json", "spec.json"),
    "usecases": ("domain.schema.json", "spec.json"),
}


def param_key(params: dict[str, Any] | None) -> str:
    """稳定短键：排序后 k=v，非法字符压成 _。"""
    if not params:
        return "default"
    parts: list[str] = []
    for k in sorted(params.keys()):
        v = params[k]
        if v is None:
            continue
        if isinstance(v, bool):
            raw = "1" if v else "0"
        elif isinstance(v, (list, tuple)):
            raw = ",".join(str(x) for x in v)
        else:
            raw = str(v)
        parts.append(f"{k}={raw}")
    joined = "__".join(parts) if parts else "default"
    return re.sub(r"[^\w.=,\-]+", "_", joined)[:180]


def source_fingerprint(workspace: Path, kind: str) -> str:
    ws = Path(workspace)
    h = hashlib.sha256()
    h.update(kind.encode("utf-8"))
    for rel in _SOURCE_RELS.get(kind, ("domain.schema.json",)):
        p = ws / rel
        try:
            st = p.stat()
            h.update(rel.encode("utf-8"))
            h.update(str(st.st_mtime_ns).encode("utf-8"))
            h.update(str(st.st_size).encode("utf-8"))
        except OSError:
            h.update(f"{rel}:missing".encode("utf-8"))
    # Java 目录影响类图方法栏：扫一层 mtime 即可（不必 hash 全文）
    if kind == "classes":
        java_root = ws / "backend" / "src" / "main" / "java"
        if java_root.is_dir():
            newest = 0
            count = 0
            for jp in java_root.rglob("*.java"):
                try:
                    newest = max(newest, jp.stat().st_mtime_ns)
                    count += 1
                except OSError:
                    continue
            h.update(f"java:{count}:{newest}".encode("utf-8"))
    return h.hexdigest()[:32]


def cache_file(workspace: Path, kind: str, params: dict[str, Any] | None) -> Path:
    return Path(workspace) / _CACHE_DIR / f"{kind}__{param_key(params)}.json"


def read_cache(
    workspace: Path,
    kind: str,
    params: dict[str, Any] | None,
) -> dict[str, Any] | None:
    path = cache_file(workspace, kind, params)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("version") != _CACHE_VER:
        return None
    if data.get("kind") != kind:
        return None
    fp = source_fingerprint(workspace, kind)
    if data.get("source_fp") != fp:
        return None
    model = data.get("model")
    if not isinstance(model, dict):
        return None
    return data


def write_cache(
    workspace: Path,
    kind: str,
    params: dict[str, Any] | None,
    *,
    model: dict[str, Any],
    timing: dict[str, float] | None = None,
) -> Path:
    ws = Path(workspace)
    path = cache_file(ws, kind, params)
    path.parent.mkdir(parents=True, exist_ok=True)
    # 不把超大内部路径缓存重复塞进 model 的副本字段；调用方已嵌 svg
    payload = {
        "version": _CACHE_VER,
        "kind": kind,
        "params": dict(params or {}),
        "source_fp": source_fingerprint(ws, kind),
        "timing": timing or {},
        "model": model,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return path


def invalidate(
    workspace: Path,
    kind: str | None = None,
) -> int:
    """删缓存文件。kind=None 清空目录。返回删除个数。"""
    root = Path(workspace) / _CACHE_DIR
    if not root.is_dir():
        return 0
    n = 0
    for p in root.glob("*.json"):
        if kind and not p.name.startswith(f"{kind}__"):
            continue
        try:
            p.unlink()
            n += 1
        except OSError:
            continue
    return n


def log_timing(
    kind: str,
    *,
    cache: str,
    timing: dict[str, float],
    params: dict[str, Any] | None = None,
) -> None:
    logger.info(
        "diagram kind=%s cache=%s model_ms=%.0f layout_ms=%.0f svg_ms=%.0f total_ms=%.0f params=%s",
        kind,
        cache,
        float(timing.get("model_ms") or 0),
        float(timing.get("layout_ms") or 0),
        float(timing.get("svg_ms") or 0),
        float(timing.get("total_ms") or 0),
        param_key(params),
    )


def get_or_build(
    workspace: Path,
    kind: str,
    params: dict[str, Any] | None,
    build: Callable[[], tuple[dict[str, Any], dict[str, float]]],
    *,
    force: bool = False,
) -> dict[str, Any]:
    """命中则直接返回 model；未命中则 build→写盘→返回。

    build 返回 (model_with_svg, timing_dict)。
    """
    t0 = time.perf_counter()
    if not force:
        hit = read_cache(workspace, kind, params)
        if hit and isinstance(hit.get("model"), dict):
            model = hit["model"]
            timing = dict(hit.get("timing") or {})
            timing["total_ms"] = (time.perf_counter() - t0) * 1000.0
            timing.setdefault("model_ms", 0.0)
            timing.setdefault("layout_ms", 0.0)
            timing.setdefault("svg_ms", 0.0)
            model = dict(model)
            model["diagram_cache"] = "hit"
            model["timing"] = timing
            log_timing(kind, cache="hit", timing=timing, params=params)
            return model

    model, timing = build()
    if not isinstance(model, dict):
        raise ValueError(f"diagram build returned non-dict for {kind}")
    timing = dict(timing or {})
    timing["total_ms"] = (time.perf_counter() - t0) * 1000.0
    model = dict(model)
    model["diagram_cache"] = "miss"
    model["timing"] = timing
    try:
        # 落盘不含运行期标记，避免污染
        to_store = {k: v for k, v in model.items() if k not in ("diagram_cache",)}
        write_cache(workspace, kind, params, model=to_store, timing=timing)
    except OSError as e:
        logger.warning("diagram cache write failed kind=%s: %s", kind, e)
    log_timing(kind, cache="miss", timing=timing, params=params)
    return model
