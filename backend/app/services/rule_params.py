"""工厂业务规则参数台：domain × rule_id → 数值默认。

真源：factory_rule_param。种子仅 asset_seeds/rule_params.json。
消费面：apply_rule_params_to_schema 写入 schema.ruleParams 与已知 schema_key。
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SOURCES = frozenset({"migrated", "scan", "manual"})
BAKE_SOURCES = frozenset({"migrated", "scan", "manual"})
WILDCARD = "*"

_lock = threading.RLock()
_rows_cache: list[dict[str, Any]] | None = None


def _norm(s: str | None) -> str:
    return (s or "").strip()


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "domain_id": _norm(row.domain_id) or WILDCARD,
        "rule_id": _norm(row.rule_id),
        "label_zh": _norm(row.label_zh),
        "value_num": float(row.value_num or 0),
        "unit_zh": _norm(row.unit_zh),
        "schema_key": _norm(row.schema_key),
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

    return list(load_seed_json("rule_params"))


def bootstrap_from_seed() -> None:
    rows = _seed_payload()
    with _lock:
        global _rows_cache
        _rows_cache = rows


async def load_all_rows(db: AsyncSession) -> list[dict[str, Any]]:
    global _rows_cache
    from app.models import FactoryRuleParam

    result = await db.execute(
        select(FactoryRuleParam).order_by(
            FactoryRuleParam.domain_id,
            FactoryRuleParam.sort,
            FactoryRuleParam.id,
        )
    )
    rows = [row_to_dict(r) for r in result.scalars().all()]
    with _lock:
        _rows_cache = rows
    return list(rows)


async def migrate_seed_if_empty(db: AsyncSession) -> dict[str, int]:
    from app.models import FactoryRuleParam

    key_rows = await db.execute(
        select(FactoryRuleParam.domain_id, FactoryRuleParam.rule_id)
    )
    have = {(_norm(a) or WILDCARD, _norm(b)) for a, b in key_rows.all()}
    inserted = 0
    for item in _seed_payload():
        domain_id = _norm(item.get("domain_id")) or WILDCARD
        rule_id = _norm(item.get("rule_id"))
        key = (domain_id, rule_id)
        if not rule_id or key in have:
            continue
        db.add(
            FactoryRuleParam(
                domain_id=domain_id,
                rule_id=rule_id,
                label_zh=_norm(item.get("label_zh")) or rule_id,
                value_num=float(item.get("value_num") or 0),
                unit_zh=_norm(item.get("unit_zh")),
                schema_key=_norm(item.get("schema_key")),
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


def _pick_rows(domain: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """具名域优先生效；同 rule_id 以具名盖 *。"""
    by_rule: dict[str, dict[str, Any]] = {}
    for r in rows:
        if _norm(r.get("source")) not in BAKE_SOURCES:
            continue
        rid = _norm(r.get("rule_id"))
        if not rid:
            continue
        dom = _norm(r.get("domain_id")) or WILDCARD
        if dom not in (WILDCARD, domain):
            continue
        prev = by_rule.get(rid)
        if prev is None or dom == domain:
            by_rule[rid] = r
    return list(by_rule.values())


def apply_rule_params_to_schema(
    schema: dict[str, Any],
    domain: str,
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    picked = _pick_rows(domain, _rows_or_seed(rows))
    bag: dict[str, Any] = {}
    for r in sorted(picked, key=lambda x: int(x.get("sort") or 0)):
        rid = _norm(r.get("rule_id"))
        val = float(r.get("value_num") or 0)
        bag[rid] = {
            "value": val,
            "unit_zh": _norm(r.get("unit_zh")),
            "label_zh": _norm(r.get("label_zh")),
            "schema_key": _norm(r.get("schema_key")),
        }
        sk = _norm(r.get("schema_key"))
        if sk and not schema.get(sk):
            # 已有扫词/加厚写入则不覆盖；仅补缺省
            schema[sk] = int(val) if val == int(val) else val
    schema["ruleParams"] = bag
    return schema


def apply_rule_params_to_spec(
    spec: dict[str, Any],
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """收束：写入 schema.ruleParams；已知 schema_key 仅补缺不覆盖。"""
    sch = dict(spec.get("schema") or {})
    domain = _norm(spec.get("domain") or sch.get("domain") or "")
    sch = apply_rule_params_to_schema(sch, domain, rows=rows)
    out = dict(spec)
    out["schema"] = sch
    return out


# 台内可登记的常见落点键（meta 选项；未知键仍可手填）
KNOWN_SCHEMA_KEYS = (
    "orderTimeoutMinutes",
    "reservationAdvanceHours",
    "pointsEarnRate",
)


def gap_report(*, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    data = _rows_or_seed(rows)
    have = {
        (_norm(r.get("domain_id")) or WILDCARD, _norm(r.get("rule_id")))
        for r in data
        if _norm(r.get("source")) in BAKE_SOURCES and _norm(r.get("rule_id"))
    }
    gaps = []
    for item in _seed_payload():
        key = (_norm(item.get("domain_id")) or WILDCARD, _norm(item.get("rule_id")))
        if key[1] and key not in have:
            gaps.append({"domain_id": key[0], "rule_id": key[1], "reason": "种子缺行"})
    return {"gap_count": len(gaps), "gaps": gaps}


async def upsert_entry(
    db: AsyncSession,
    *,
    domain_id: str = WILDCARD,
    rule_id: str,
    label_zh: str = "",
    value_num: float = 0,
    unit_zh: str = "",
    schema_key: str = "",
    sort: int = 0,
    source: str = "manual",
) -> dict[str, Any]:
    from app.models import FactoryRuleParam

    domain_id = _norm(domain_id) or WILDCARD
    rule_id = _norm(rule_id)
    source = _norm(source) or "manual"
    if not rule_id:
        raise ValueError("rule_id 必填")
    if source not in SOURCES:
        source = "manual"
    result = await db.execute(
        select(FactoryRuleParam).where(
            FactoryRuleParam.domain_id == domain_id,
            FactoryRuleParam.rule_id == rule_id,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.label_zh = _norm(label_zh) or row.label_zh or rule_id
        row.value_num = float(value_num)
        row.unit_zh = _norm(unit_zh)
        row.schema_key = _norm(schema_key)
        row.sort = int(sort or 0)
        row.source = source
        row.updated_at = datetime.utcnow()
    else:
        row = FactoryRuleParam(
            domain_id=domain_id,
            rule_id=rule_id,
            label_zh=_norm(label_zh) or rule_id,
            value_num=float(value_num),
            unit_zh=_norm(unit_zh),
            schema_key=_norm(schema_key),
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
    from app.models import FactoryRuleParam

    row = await db.get(FactoryRuleParam, entry_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    invalidate_cache()
    return True
