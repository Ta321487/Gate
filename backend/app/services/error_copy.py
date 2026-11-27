"""工厂错误码中文台：ErrorCode → 学生可见默认句。

真源：factory_error_copy。种子仅 asset_seeds/error_copy.json。
消费面：bake 写入 error-messages.json + schema.errorCopy；Java ErrorMessages 回落默认句。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_desk_cache import AssetRowsCache, norm_text

SOURCES = frozenset({"migrated", "scan", "manual"})
BAKE_SOURCES = frozenset({"migrated", "scan", "manual"})

# 与 skeletons/.../ErrorCode.java 对齐；缺口扫描以此为准
EXPECTED_ERROR_CODES: tuple[tuple[str, int], ...] = (
    ("OK", 0),
    ("BAD_REQUEST", 40000),
    ("UNAUTHORIZED", 40100),
    ("CAPTCHA_INVALID", 40101),
    ("ACCOUNT_DISABLED", 40102),
    ("ACCOUNT_LOCKED", 40103),
    ("FORBIDDEN", 40300),
    ("NOT_FOUND", 40400),
    ("INTERNAL", 50000),
)

_cache = AssetRowsCache()


def _norm(s: str | None) -> str:
    return norm_text(s)


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "error_code": _norm(row.error_code),
        "code_num": int(row.code_num or 0),
        "message_zh": _norm(row.message_zh),
        "sort": int(row.sort or 0),
        "source": str(row.source or "manual"),
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    }


def invalidate_cache() -> None:
    _cache.invalidate()


def _seed_payload() -> list[dict[str, Any]]:
    from app.services.asset_seeds import load_seed_json

    return list(load_seed_json("error_copy"))


def bootstrap_from_seed() -> None:
    _cache.set(_seed_payload())


async def load_all_rows(db: AsyncSession) -> list[dict[str, Any]]:
    from app.models import FactoryErrorCopy

    result = await db.execute(
        select(FactoryErrorCopy).order_by(FactoryErrorCopy.sort, FactoryErrorCopy.id)
    )
    rows = [row_to_dict(r) for r in result.scalars().all()]
    _cache.set(rows)
    return list(rows)


async def migrate_seed_if_empty(db: AsyncSession) -> dict[str, int]:
    from app.models import FactoryErrorCopy

    key_rows = await db.execute(select(FactoryErrorCopy.error_code))
    have = {_norm(a) for (a,) in key_rows.all()}
    inserted = 0
    for item in _seed_payload():
        code = _norm(item.get("error_code"))
        if not code or code in have:
            continue
        db.add(
            FactoryErrorCopy(
                error_code=code,
                code_num=int(item.get("code_num") or 0),
                message_zh=_norm(item.get("message_zh")) or code,
                sort=int(item.get("sort") or 0),
                source=_norm(item.get("source")) or "migrated",
            )
        )
        inserted += 1
        have.add(code)
    if inserted:
        await db.commit()
    invalidate_cache()
    rows = await load_all_rows(db)
    return {"inserted": inserted, "total": len(rows)}


def _rows_or_seed(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    data = rows if rows is not None else _cache.get()
    if not data:
        return _seed_payload()
    return list(data)


def build_message_map(*, rows: list[dict[str, Any]] | None = None) -> dict[str, str]:
    out: dict[str, str] = {}
    for r in sorted(_rows_or_seed(rows), key=lambda x: int(x.get("sort") or 0)):
        if _norm(r.get("source")) not in BAKE_SOURCES:
            continue
        code = _norm(r.get("error_code"))
        msg = _norm(r.get("message_zh"))
        if code and msg:
            out[code] = msg
    return out


def resolve_message(
    error_code: str,
    *,
    fallback: str = "",
    rows: list[dict[str, Any]] | None = None,
) -> str:
    fb = _norm(fallback)
    if fb:
        return fb
    return build_message_map(rows=rows).get(_norm(error_code), "请求失败")


def apply_error_copy_to_schema(
    schema: dict[str, Any] | None,
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return schema or {}
    tree: dict[str, dict[str, Any]] = {}
    for r in _rows_or_seed(rows):
        if _norm(r.get("source")) not in BAKE_SOURCES:
            continue
        code = _norm(r.get("error_code"))
        msg = _norm(r.get("message_zh"))
        if not code or not msg:
            continue
        tree[code] = {"code": int(r.get("code_num") or 0), "message": msg}
    schema["errorCopy"] = tree
    return schema


def write_error_messages_json(
    dest: Path,
    *,
    rows: list[dict[str, Any]] | None = None,
) -> Path | None:
    """写入学生包 backend/.../resources/error-messages.json。"""
    be = dest / "backend" / "src" / "main" / "resources"
    if not be.is_dir():
        be.mkdir(parents=True, exist_ok=True)
    path = be / "error-messages.json"
    path.write_text(
        json.dumps(build_message_map(rows=rows), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def gap_report(*, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    data = _rows_or_seed(rows)
    have = {
        _norm(r.get("error_code")): _norm(r.get("message_zh"))
        for r in data
        if _norm(r.get("source")) in BAKE_SOURCES
    }
    gaps = []
    for code, num in EXPECTED_ERROR_CODES:
        if code not in have:
            gaps.append(
                {
                    "error_code": code,
                    "code_num": num,
                    "reason": "缺少默认中文",
                }
            )
        elif not have[code]:
            gaps.append(
                {
                    "error_code": code,
                    "code_num": num,
                    "reason": "中文为空",
                }
            )
    return {"gap_count": len(gaps), "gaps": gaps}


async def upsert_entry(
    db: AsyncSession,
    *,
    error_code: str,
    message_zh: str,
    code_num: int = 0,
    sort: int = 0,
    source: str = "manual",
) -> dict[str, Any]:
    from app.models import FactoryErrorCopy

    error_code = _norm(error_code)
    message_zh = _norm(message_zh)
    source = _norm(source) or "manual"
    if not error_code or not message_zh:
        raise ValueError("error_code、message_zh 必填")
    if source not in SOURCES:
        source = "manual"
    if not code_num:
        code_num = next((n for c, n in EXPECTED_ERROR_CODES if c == error_code), 0)
    result = await db.execute(
        select(FactoryErrorCopy).where(FactoryErrorCopy.error_code == error_code)
    )
    row = result.scalar_one_or_none()
    if row:
        row.message_zh = message_zh
        row.code_num = int(code_num or row.code_num or 0)
        row.sort = int(sort or 0)
        row.source = source
        row.updated_at = datetime.utcnow()
    else:
        row = FactoryErrorCopy(
            error_code=error_code,
            code_num=int(code_num or 0),
            message_zh=message_zh,
            sort=int(sort or 0),
            source=source,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    invalidate_cache()
    await load_all_rows(db)
    return row_to_dict(row)


async def delete_entry(db: AsyncSession, entry_id: int) -> bool:
    from app.models import FactoryErrorCopy

    row = await db.get(FactoryErrorCopy, entry_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    invalidate_cache()
    return True
