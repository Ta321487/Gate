"""出包主题瘦身：学生包只留本题 data-theme，不带全厂行业肤目录。

骨架 themes.css / themes/*.css 是工厂配色库；bake 末按 spec.theme 裁剪。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.services.project_disk import remove_tree_reliable

_THEME_BLOCK_RE = re.compile(
    r"((?:\[data-theme=[\"'][^\"']+[\"']\]\s*,?\s*)+)\s*\{([^{}]*)\}",
    re.MULTILINE,
)
_THEME_ID_RE = re.compile(r'\[data-theme=["\']([^"\']+)["\']\]')
_IMPORT_RE = re.compile(
    r'@import\s+["\']\./themes/([a-z0-9_-]+)\.css["\']\s*;',
    re.IGNORECASE,
)


def resolve_pack_theme_id(spec: dict[str, Any] | None) -> str:
    """本题生效主题 id（已解别名）。"""
    from app.bake.themes import THEME_ALIASES, default_theme

    spec = spec or {}
    raw = str(spec.get("theme") or "").strip()
    domain = str(spec.get("domain") or "").strip() or "DOM-GENERIC"
    if not raw:
        raw = default_theme(domain)
    return THEME_ALIASES.get(raw, raw)


def _allowed_theme_ids(theme_id: str) -> set[str]:
    """本题可出现在 CSS 里的 data-theme id（含指向它的旧别名）。"""
    from app.bake.themes import THEME_ALIASES

    allowed = {theme_id}
    for old, new in THEME_ALIASES.items():
        if new == theme_id:
            allowed.add(old)
    return allowed


def _extract_blocks_for_theme(css: str, theme_id: str) -> str:
    chunks: list[str] = []
    for m in _THEME_BLOCK_RE.finditer(css):
        ids = set(_THEME_ID_RE.findall(m.group(1)))
        if theme_id in ids:
            chunks.append(m.group(0).strip())
    return "\n\n".join(chunks)


def _find_theme_owner(
    styles: Path, theme_id: str
) -> tuple[str, Path] | None:
    """返回 ('file', themes/xxx.css) 或 ('inline', themes.css)。"""
    needle = f'[data-theme="{theme_id}"]'
    themes_dir = styles / "themes"
    if themes_dir.is_dir():
        for path in sorted(themes_dir.glob("*.css")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if needle in text:
                return ("file", path)
    themes_css = styles / "themes.css"
    if themes_css.is_file():
        try:
            text = themes_css.read_text(encoding="utf-8")
        except OSError:
            text = ""
        if needle in text:
            return ("inline", themes_css)
    return None


def _write_lean_themes_css(
    themes_css: Path,
    *,
    import_stem: str | None,
    body_blocks: str,
) -> None:
    lines = [
        "/* 本包配色：data-theme → --portal-* */",
        "",
    ]
    if import_stem:
        lines.append(f'@import "./themes/{import_stem}.css";')
        lines.append("")
    lines.extend(
        [
            ":root {",
            "  --portal-scheme: light;",
            "  --portal-mix: #ffffff;",
            "  color-scheme: light;",
            "}",
            "",
        ]
    )
    if body_blocks:
        lines.append(body_blocks)
        lines.append("")
    themes_css.parent.mkdir(parents=True, exist_ok=True)
    themes_css.write_text("\n".join(lines), encoding="utf-8")


def scrub_pack_themes(
    workspace: Path, spec: dict[str, Any] | None = None
) -> list[str]:
    """按 spec.theme 裁 themes.css / themes/*；返回变更记录。"""
    workspace = Path(workspace)
    fe = workspace / "frontend" / "src"
    if not fe.is_dir():
        return []
    styles = fe / "styles"
    themes_css = styles / "themes.css"
    themes_dir = styles / "themes"
    if not themes_css.is_file() and not (themes_dir.is_dir() and any(themes_dir.glob("*.css"))):
        return []

    theme_id = resolve_pack_theme_id(spec)
    owner = _find_theme_owner(styles, theme_id)
    notes: list[str] = []
    if owner is None:
        notes.append(f"theme_missing:{theme_id}")
        return notes

    kind, path = owner
    if kind == "file":
        raw = path.read_text(encoding="utf-8")
        block = _extract_blocks_for_theme(raw, theme_id)
        if not block:
            notes.append(f"theme_block_missing:{theme_id}")
            return notes
        stem = path.stem
        lean_file = (
            f"/* {theme_id} */\n\n{block}\n"
            if not block.startswith("/*")
            else f"{block}\n"
        )
        path.write_text(lean_file, encoding="utf-8")
        notes.append(f"theme_keep:themes/{stem}.css:{theme_id}")
        _write_lean_themes_css(themes_css, import_stem=stem, body_blocks="")
        notes.append("theme_rewrite:themes.css")
        if themes_dir.is_dir():
            for other in list(themes_dir.glob("*.css")):
                if other.resolve() == path.resolve():
                    continue
                remove_tree_reliable(other)
                notes.append(f"theme_drop:themes/{other.name}")
    else:
        raw = path.read_text(encoding="utf-8")
        block = _extract_blocks_for_theme(raw, theme_id)
        if not block:
            notes.append(f"theme_block_missing:{theme_id}")
            return notes
        _write_lean_themes_css(themes_css, import_stem=None, body_blocks=block)
        notes.append(f"theme_keep:themes.css:{theme_id}")
        if themes_dir.is_dir():
            for other in list(themes_dir.glob("*.css")):
                remove_tree_reliable(other)
                notes.append(f"theme_drop:themes/{other.name}")

    return notes


def scan_foreign_theme_leaks(
    workspace: Path, spec: dict[str, Any] | None = None
) -> list[str]:
    """学生包仍带异域行业肤 / 多余 themes 文件 → 路径标记（p3lean）。"""
    workspace = Path(workspace)
    fe = workspace / "frontend" / "src"
    styles = fe / "styles"
    themes_css = styles / "themes.css"
    themes_dir = styles / "themes"
    if not themes_css.is_file() and not (
        themes_dir.is_dir() and any(themes_dir.glob("*.css"))
    ):
        return []

    theme_id = resolve_pack_theme_id(spec)
    allowed = _allowed_theme_ids(theme_id)
    hits: list[str] = []

    owner = _find_theme_owner(styles, theme_id)
    if owner is None:
        hits.append(f"theme_missing:{theme_id}")
        return sorted(set(hits))

    kind, keep_path = owner
    keep_stem = keep_path.stem if kind == "file" else None

    if themes_dir.is_dir():
        for path in sorted(themes_dir.glob("*.css")):
            if kind == "file" and path.resolve() == keep_path.resolve():
                text = path.read_text(encoding="utf-8")
                ids = set(_THEME_ID_RE.findall(text))
                foreign = sorted(ids - allowed)
                if foreign:
                    hits.append(
                        f"theme_extra_id:themes/{path.name}:{','.join(foreign[:6])}"
                    )
                continue
            hits.append(f"theme_file:themes/{path.name}")

    if themes_css.is_file():
        text = themes_css.read_text(encoding="utf-8")
        imports = _IMPORT_RE.findall(text)
        for stem in imports:
            if keep_stem and stem == keep_stem:
                continue
            hits.append(f"theme_import:{stem}")
        if kind == "file" and keep_stem and keep_stem not in imports:
            # 瘦身后应 import 唯一 stem；未剪则多半还挂着一长串，上面已报
            if not imports:
                hits.append(f"theme_import_missing:{keep_stem}")
        ids = set(_THEME_ID_RE.findall(text))
        foreign = sorted(ids - allowed)
        # 文件型主题时 themes.css 不应再内联异域块；允许空
        if foreign:
            hits.append(f"theme_extra_id:themes.css:{','.join(foreign[:6])}")
        if theme_id not in ids and kind == "inline":
            hits.append(f"theme_missing_id:themes.css:{theme_id}")
        if kind == "file":
            # 色块在 themes/stem.css；入口只需 import
            keep_file = themes_dir / f"{keep_stem}.css"
            if keep_file.is_file():
                file_ids = set(
                    _THEME_ID_RE.findall(keep_file.read_text(encoding="utf-8"))
                )
                if theme_id not in file_ids:
                    hits.append(f"theme_missing_id:themes/{keep_stem}.css:{theme_id}")

    return sorted(set(hits))
