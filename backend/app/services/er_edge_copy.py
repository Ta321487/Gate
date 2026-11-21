"""工厂表关系叙事句：table_a–table_b → 一句中文。

真源：factory_er_edge_copy。种子仅 asset_seeds/er_edge_copy.json。
消费面：schema.erEdgeCopy；服务论文库设旁注，不替代结构对账。
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SOURCES = frozenset({"migrated", "scan", "manual"})
BAKE_SOURCES = frozenset({"migrated", "scan", "manual"})

_lock = threading.RLock()
_rows_cache: list[dict[str, Any]] | None = None


def _norm(s: str | None) -> str:
    return (s or "").strip()


def _pair_key(a: str, b: str) -> str:
    return f"{_norm(a)}|{_norm(b)}"


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "table_a": _norm(row.table_a),
        "table_b": _norm(row.table_b),
        "sentence_zh": _norm(row.sentence_zh),
        "sort": int(row.sort or 0),
        "source": str(row.source or "manual"),
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    }


def invalidate_cache() -> None:
    global _rows_cache
    with _lock:
        _rows_cache = None


def _seed_payload() -> list[dict[str, Any]]:
    from app.services.asset_seeds import load_seed_json

    return list(load_seed_json("er_edge_copy"))


def bootstrap_from_seed() -> None:
    rows = _seed_payload()
    with _lock:
        global _rows_cache
        _rows_cache = rows


async def load_all_rows(db: AsyncSession) -> list[dict[str, Any]]:
    global _rows_cache
    from app.models import FactoryErEdgeCopy

    result = await db.execute(
        select(FactoryErEdgeCopy).order_by(FactoryErEdgeCopy.sort, FactoryErEdgeCopy.id)
    )
    rows = [row_to_dict(r) for r in result.scalars().all()]
    with _lock:
        _rows_cache = rows
    return list(rows)


async def migrate_seed_if_empty(db: AsyncSession) -> dict[str, int]:
    from app.models import FactoryErEdgeCopy

    key_rows = await db.execute(
        select(FactoryErEdgeCopy.table_a, FactoryErEdgeCopy.table_b)
    )
    have = {_pair_key(a, b) for a, b in key_rows.all()}
    inserted = 0
    for item in _seed_payload():
        a = _norm(item.get("table_a"))
        b = _norm(item.get("table_b"))
        key = _pair_key(a, b)
        if not a or not b or key in have:
            continue
        db.add(
            FactoryErEdgeCopy(
                table_a=a,
                table_b=b,
                sentence_zh=_norm(item.get("sentence_zh")) or f"{a} 关联 {b}",
                sort=int(item.get("sort") or 0),
                source=_norm(item.get("source")) or "migrated",
            )
        )
        inserted += 1
        have.add(key)
    if inserted:
        await db.commit()
    invalidate_cache()
    rows = await load_all_rows(db)
    return {"inserted": inserted, "total": len(rows)}


def _rows_or_seed(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    data = rows
    if data is None:
        with _lock:
            data = list(_rows_cache) if _rows_cache is not None else None
    if not data:
        return _seed_payload()
    return list(data)


def apply_er_edge_copy_to_schema(
    schema: dict[str, Any],
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    bag: dict[str, str] = {}
    ordered: list[dict[str, str]] = []
    for r in sorted(_rows_or_seed(rows), key=lambda x: int(x.get("sort") or 0)):
        if _norm(r.get("source")) not in BAKE_SOURCES:
            continue
        a = _norm(r.get("table_a"))
        b = _norm(r.get("table_b"))
        s = _norm(r.get("sentence_zh"))
        if not a or not b or not s:
            continue
        bag[_pair_key(a, b)] = s
        ordered.append({"table_a": a, "table_b": b, "sentence_zh": s})
    schema["erEdgeCopy"] = bag
    schema["erEdgeCopyList"] = ordered
    return schema


def apply_er_edge_copy_to_spec(
    spec: dict[str, Any],
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """收束：写入 schema.erEdgeCopy / erEdgeCopyList，供论文库设旁注。"""
    sch = dict(spec.get("schema") or {})
    sch = apply_er_edge_copy_to_schema(sch, rows=rows)
    out = dict(spec)
    out["schema"] = sch
    return out


SENTENCE_MAX = 256


def gap_report(*, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    data = _rows_or_seed(rows)
    have = {
        _pair_key(r.get("table_a"), r.get("table_b"))
        for r in data
        if _norm(r.get("source")) in BAKE_SOURCES
    }
    gaps = []
    for item in _seed_payload():
        key = _pair_key(item.get("table_a"), item.get("table_b"))
        if key != "|" and key not in have:
            gaps.append(
                {
                    "table_a": _norm(item.get("table_a")),
                    "table_b": _norm(item.get("table_b")),
                    "reason": "种子缺行",
                }
            )
    return {"gap_count": len(gaps), "gaps": gaps}


async def upsert_entry(
    db: AsyncSession,
    *,
    table_a: str,
    table_b: str,
    sentence_zh: str,
    sort: int = 0,
    source: str = "manual",
) -> dict[str, Any]:
    from app.models import FactoryErEdgeCopy

    table_a = _norm(table_a)
    table_b = _norm(table_b)
    sentence_zh = _norm(sentence_zh)
    source = _norm(source) or "manual"
    if not table_a or not table_b or not sentence_zh:
        raise ValueError("table_a、table_b、sentence_zh 必填")
    if len(sentence_zh) > SENTENCE_MAX:
        raise ValueError(f"sentence_zh 最长 {SENTENCE_MAX} 字")
    if source not in SOURCES:
        source = "manual"
    result = await db.execute(
        select(FactoryErEdgeCopy).where(
            FactoryErEdgeCopy.table_a == table_a,
            FactoryErEdgeCopy.table_b == table_b,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.sentence_zh = sentence_zh
        row.sort = int(sort or 0)
        row.source = source
        row.updated_at = datetime.utcnow()
    else:
        row = FactoryErEdgeCopy(
            table_a=table_a,
            table_b=table_b,
            sentence_zh=sentence_zh,
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
    from app.models import FactoryErEdgeCopy

    row = await db.get(FactoryErEdgeCopy, entry_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    invalidate_cache()
    return True
