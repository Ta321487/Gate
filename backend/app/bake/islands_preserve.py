"""重 bake 时保留人工 / Overrides islands 白名单（见 docs/pack-overrides.md §4.4）。

bake_project 整树删除前 stash，copytree 后再 restore。
禁止收录 diagram_cache（应随新 schema 作废）。
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger("app.bake.islands_preserve")

# 文件：相对工作区根
ISLANDS_PRESERVE_FILES: tuple[str, ...] = (
    "islands/overrides.json",
    "islands/module_labels.json",
    "islands/class_layout.json",
    "islands/er_labels.json",
    "islands/testcase_labels.json",
)

# 目录：整树保留（相对工作区根）
ISLANDS_PRESERVE_DIRS: tuple[str, ...] = ("islands/er_view",)

# 明确排除（文档钉死；勿误加入 FILES/DIRS）
ISLANDS_PRESERVE_FORBIDDEN_PREFIXES: tuple[str, ...] = ("islands/diagram_cache",)


def _assert_not_forbidden(rel: str) -> None:
    norm = rel.replace("\\", "/").lstrip("./")
    for bad in ISLANDS_PRESERVE_FORBIDDEN_PREFIXES:
        if norm == bad or norm.startswith(bad + "/"):
            raise ValueError(f"islands preserve 禁止收录: {rel}")


def stash_islands_whitelist(workspace: Path) -> Path | None:
    """把白名单路径拷到临时目录；无任何命中则返回 None。"""
    ws = Path(workspace)
    if not ws.is_dir():
        return None

    for rel in ISLANDS_PRESERVE_FILES:
        _assert_not_forbidden(rel)
    for rel in ISLANDS_PRESERVE_DIRS:
        _assert_not_forbidden(rel)

    hits: list[tuple[str, Path]] = []
    for rel in ISLANDS_PRESERVE_FILES:
        src = ws / rel
        if src.is_file():
            hits.append((rel, src))
    for rel in ISLANDS_PRESERVE_DIRS:
        src = ws / rel
        if src.is_dir():
            hits.append((rel, src))

    if not hits:
        return None

    stash_root = Path(tempfile.mkdtemp(prefix="gf_islands_stash_"))
    for rel, src in hits:
        dest = stash_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dest)
    logger.info(
        "islands stash %s → %s (%s paths)",
        ws,
        stash_root,
        len(hits),
    )
    return stash_root


def restore_islands_whitelist(
    workspace: Path, stash_root: Path | None
) -> list[str]:
    """从 stash 写回工作区；返回已恢复的相对路径列表。"""
    if stash_root is None:
        return []
    stash = Path(stash_root)
    if not stash.is_dir():
        return []

    ws = Path(workspace)
    restored: list[str] = []

    for rel in ISLANDS_PRESERVE_FILES:
        src = stash / rel
        if not src.is_file():
            continue
        dest = ws / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        restored.append(rel)

    for rel in ISLANDS_PRESERVE_DIRS:
        src = stash / rel
        if not src.is_dir():
            continue
        dest = ws / rel
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest)
        restored.append(rel)

    if restored:
        logger.info("islands restore → %s (%s)", ws, restored)
    return restored


def clear_islands_stash(stash_root: Path | None) -> None:
    if stash_root is None:
        return
    shutil.rmtree(Path(stash_root), ignore_errors=True)
