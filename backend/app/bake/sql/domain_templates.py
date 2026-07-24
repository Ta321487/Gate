"""Per-domain SQL templates（正文在 templates/DOM-*.sql）。"""

from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).resolve().parent / "templates"

DOMAIN_SQL_TEMPLATES: dict[str, str] = {
    p.stem: p.read_text(encoding="utf-8")
    for p in sorted(_DIR.glob("DOM-*.sql"))
}
