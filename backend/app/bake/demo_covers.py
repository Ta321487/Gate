"""演示封面 / 种子上传物：SQL 写 cover_url，工作区落真实文件，全域统一。

策略：
1. 档案主表若有 cover_url，空封面按 id 轮转到 /uploads/demo/cover-NN.jpg
2. schema.sql 里出现的 /uploads/** 路径，出包时生成对应占位文件（jpg/png/pdf）
禁止再出现「库里有 URL、磁盘无文件」导致详情轮播「加载失败」。
"""

from __future__ import annotations

import logging
import re
import zlib
from pathlib import Path

log = logging.getLogger("gf.demo_covers")

COVER_COUNT = 8
COVER_URL_PREFIX = "/uploads/demo/cover-"

_UPLOAD_REF_RE = re.compile(
    r"/uploads/([A-Za-z0-9_./-]+\.(?:jpe?g|png|gif|webp|pdf))",
    re.IGNORECASE,
)
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# 最小合法 PDF（论坛附件等）
_MIN_PDF = b"""%PDF-1.1
1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj
2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj
3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R >>endobj
4 0 obj<< /Length 44 >>stream
BT /F1 12 Tf 40 100 Td (demo) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
trailer<< /Size 5 /Root 1 0 R >>
startxref
307
%%EOF
"""


def cover_url_for_index(index: int) -> str:
    """1-based cover path：cover-01.jpg … cover-08.jpg。"""
    n = ((int(index) - 1) % COVER_COUNT) + 1
    return f"{COVER_URL_PREFIX}{n:02d}.jpg"


def demo_cover_urls() -> list[str]:
    return [cover_url_for_index(i) for i in range(1, COVER_COUNT + 1)]


def _table_has_cover_url(sql: str, table: str) -> bool:
    if not table or not _IDENT_RE.match(table):
        return False
    m = re.search(
        rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?{re.escape(table)}`?\s*\((.*?)\)\s*;",
        sql or "",
        re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return False
    return bool(re.search(r"\bcover_url\b", m.group(1), re.IGNORECASE))


def ensure_demo_cover_urls_sql(sql: str, *, item_table: str | None) -> str:
    """档案主表空封面补 /uploads/demo/cover-NN.jpg（幂等）。"""
    text = sql or ""
    table = (item_table or "").strip()
    if not _table_has_cover_url(text, table):
        return text
    marker = f"-- gf demo covers for {table}"
    if marker in text:
        return text
    urls = ",\n  ".join(f"'{u}'" for u in demo_cover_urls())
    block = (
        f"\n{marker}\n"
        f"UPDATE `{table}` SET cover_url = ELT(1 + MOD(GREATEST(id, 1) - 1, {COVER_COUNT}),\n"
        f"  {urls}\n"
        f")\n"
        f"WHERE cover_url IS NULL OR TRIM(cover_url) = '';\n"
    )
    return text.rstrip() + "\n" + block


def collect_upload_refs(sql: str) -> list[str]:
    """schema.sql 中引用的 /uploads/ 相对路径（去重保序）。"""
    seen: set[str] = set()
    out: list[str] = []
    for m in _UPLOAD_REF_RE.finditer(sql or ""):
        rel = m.group(1).replace("\\", "/").lstrip("/")
        if ".." in rel or rel in seen:
            continue
        seen.add(rel)
        out.append(rel)
    for u in demo_cover_urls():
        rel = u[len("/uploads/") :]
        if rel not in seen:
            seen.add(rel)
            out.append(rel)
    return out


def _solid_png(rgb: tuple[int, int, int], w: int = 32, h: int = 24) -> bytes:
    r, g, b = rgb
    raw = b"".join(b"\x00" + bytes([r, g, b]) * w for _ in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            len(data).to_bytes(4, "big")
            + tag
            + data
            + zlib.crc32(tag + data).to_bytes(4, "big")
        )

    ihdr = (
        w.to_bytes(4, "big")
        + h.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
    )
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def _write_placeholder(
    dest: Path,
    *,
    domain: str,
    theme: str,
    slot: int,
) -> bool:
    """按扩展名写占位文件；jpg 优先走本地氛围图。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 64:
        return True
    ext = dest.suffix.lower()
    try:
        if ext in {".jpg", ".jpeg", ".webp"}:
            from app.bake.local_atmosphere import (
                render_local_atmosphere,
                write_local_atmosphere_cached,
            )

            ok = write_local_atmosphere_cached(
                dest,
                domain=domain or "DOM-GENERIC",
                theme=theme or "lib-ink",
                kind="portal",
                slot=slot,
            )
            if not ok:
                ok = render_local_atmosphere(
                    dest,
                    domain=domain or "DOM-GENERIC",
                    theme=theme or "lib-ink",
                    kind="portal",
                    slot=slot,
                    width=640,
                    height=480,
                )
            if ok:
                return True
            # 无 Pillow 时退到 PNG 字节写 jpg 名：浏览器仍常能显示；尽量少见
            dest.write_bytes(_solid_png((180, 120, 80 + (slot * 17) % 100)))
            return True
        if ext == ".png" or ext == ".gif":
            tone = 80 + (slot * 23) % 140
            dest.write_bytes(_solid_png((tone, 140, 200 - (slot * 11) % 80)))
            return True
        if ext == ".pdf":
            dest.write_bytes(_MIN_PDF)
            return True
        dest.write_bytes(_solid_png((160, 160, 160)))
        return True
    except OSError as e:
        log.warning("demo upload write failed %s: %s", dest, e)
        return False


def materialize_demo_uploads(
    workspace: Path,
    sql: str,
    *,
    domain: str = "DOM-GENERIC",
    theme: str = "lib-ink",
) -> list[str]:
    """把 SQL 引用的 /uploads/** 与标准 cover-NN 落到 backend/uploads/。"""
    root = Path(workspace) / "backend" / "uploads"
    written: list[str] = []
    for i, rel in enumerate(collect_upload_refs(sql)):
        dest = root / rel
        if _write_placeholder(dest, domain=domain, theme=theme, slot=i):
            written.append(rel)
    log.info("demo uploads materialized %s files under %s", len(written), root)
    return written
