"""工厂字典/枚举值台：持久化、迁入、解析、扫缺口、bake 注入。

真源：factory_dict_values。下拉/筛选只消费本台 bake 出的 schema.dicts。
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SOURCES = frozenset({"migrated", "scan", "manual"})
BAKE_SOURCES = frozenset({"migrated", "scan", "manual"})
WILDCARD_DOMAIN = "*"
ZH_MAX_LEN = 64
KEY_MAX_LEN = 64

# 报修 / 交易组（缺口扫描用；码表正文在 asset_seeds/dict_values.json → 库）
REPAIR_DOMAINS = frozenset({"DOM-DORM", "DOM-PROPERTY", "DOM-IT"})
TRADE_DOMAINS = frozenset({"DOM-SHOP", "DOM-FOOD", "DOM-CINEMA"})

_lock = threading.RLock()
_rows_cache: list[dict[str, Any]] | None = None


def _norm(s: str | None) -> str:
    return (s or "").strip()


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "domain_id": _norm(row.domain_id) or WILDCARD_DOMAIN,
        "skin_id": _norm(row.skin_id),
        "dict_key": _norm(row.dict_key),
        "value_code": _norm(row.value_code),
        "label_zh": _norm(row.label_zh),
        "sort": int(row.sort or 0),
        "enabled": bool(row.enabled),
        "source": str(row.source or "manual"),
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    }


def invalidate_cache() -> None:
    global _rows_cache
    with _lock:
        _rows_cache = None


def _seed_payload() -> list[dict[str, Any]]:
    """首迁种子仅来自 asset_seeds/dict_values.json；运行真源是库表。"""
    from app.services.asset_seeds import load_seed_json

    return list(load_seed_json("dict_values"))


def expected_dict_codes_from_seed() -> dict[str, dict[str, tuple[str, ...]]]:
    """由种子推导缺口期望（逻辑层不写死业务码）。"""
    out: dict[str, dict[str, list[str]]] = {}
    for r in _seed_payload():
        if not bool(r.get("enabled", True)):
            continue
        dom = _norm(r.get("domain_id")) or WILDCARD_DOMAIN
        key = _norm(r.get("dict_key"))
        code = _norm(r.get("value_code"))
        if not key or not code:
            continue
        # 缺口扫描按域聚合；带 skin 的分类仍记在域下便于扫
        out.setdefault(dom, {}).setdefault(key, [])
        if code not in out[dom][key]:
            out[dom][key].append(code)
    return {d: {k: tuple(v) for k, v in keys.items()} for d, keys in out.items()}


# 兼容旧名
EXPECTED_DICT_CODES: dict[str, dict[str, tuple[str, ...]]] = {}  # 懒填


def _expected() -> dict[str, dict[str, tuple[str, ...]]]:
    global EXPECTED_DICT_CODES
    if not EXPECTED_DICT_CODES:
        EXPECTED_DICT_CODES = expected_dict_codes_from_seed()
    return EXPECTED_DICT_CODES


def bootstrap_from_seed() -> None:
    rows = _seed_payload()
    with _lock:
        global _rows_cache
        _rows_cache = rows


async def load_all_rows(db: AsyncSession) -> list[dict[str, Any]]:
    """读库并刷新进程缓存。有 Session 时禁止返回种子冒充库数据。"""
    global _rows_cache
    from app.models import FactoryDictValue

    result = await db.execute(
        select(FactoryDictValue).order_by(
            FactoryDictValue.dict_key,
            FactoryDictValue.sort,
            FactoryDictValue.id,
        )
    )
    rows = [row_to_dict(r) for r in result.scalars().all()]
    with _lock:
        _rows_cache = rows
    return list(rows)


async def migrate_seed_if_empty(db: AsyncSession) -> dict[str, int]:
    """只追加：种子里库中没有的主键才 INSERT；已有行一律不改。"""
    from app.models import FactoryDictValue

    # 补缺键必须来自 DB，不能 load_all_rows（可能被 bootstrap 种子缓存骗过）
    key_rows = await db.execute(
        select(
            FactoryDictValue.domain_id,
            FactoryDictValue.skin_id,
            FactoryDictValue.dict_key,
            FactoryDictValue.value_code,
        )
    )
    have = {
        (_norm(a) or WILDCARD_DOMAIN, _norm(b), _norm(c), _norm(d))
        for a, b, c, d in key_rows.all()
    }
    inserted = 0
    seed = _seed_payload()
    for item in seed:
        tup = (
            _norm(item.get("domain_id")) or WILDCARD_DOMAIN,
            _norm(item.get("skin_id")),
            _norm(item.get("dict_key")),
            _norm(item.get("value_code")),
        )
        if not tup[2] or not tup[3] or tup in have:
            continue
        payload = {
            "domain_id": tup[0],
            "skin_id": tup[1],
            "dict_key": tup[2],
            "value_code": tup[3],
            "label_zh": _norm(item.get("label_zh")) or tup[3],
            "sort": int(item.get("sort") or 0),
            "enabled": bool(item.get("enabled", True)),
            "source": "migrated",
        }
        db.add(FactoryDictValue(**payload))
        inserted += 1
        have.add(tup)
    if inserted:
        await db.commit()
    invalidate_cache()
    rows = await load_all_rows(db)
    return {"inserted": inserted, "total": len(rows)}


def _rows_or_seed(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """空库未迁入时仍用种子，保证 bake 注入不空白。"""
    data = rows
    if data is None:
        with _lock:
            data = list(_rows_cache) if _rows_cache is not None else None
    if not data:
        return _seed_payload()
    return list(data)


def _row_matches(
    r: dict[str, Any],
    *,
    domain_id: str,
    skin_id: str,
    dict_key: str,
    value_code: str | None = None,
) -> bool:
    if _norm(r.get("dict_key")) != dict_key:
        return False
    if value_code is not None and _norm(r.get("value_code")) != value_code:
        return False
    if _norm(r.get("source")) not in BAKE_SOURCES:
        return False
    if not bool(r.get("enabled", True)):
        return False
    d = _norm(r.get("domain_id")) or WILDCARD_DOMAIN
    s = _norm(r.get("skin_id"))
    if d not in (domain_id, WILDCARD_DOMAIN):
        return False
    if s and s != skin_id:
        return False
    return True


def resolve_label(
    domain_id: str,
    dict_key: str,
    value_code: str,
    *,
    skin_id: str = "",
    rows: list[dict[str, Any]] | None = None,
) -> str | None:
    data = _rows_or_seed(rows)
    domain_id = _norm(domain_id) or WILDCARD_DOMAIN
    skin_id = _norm(skin_id)
    dict_key = _norm(dict_key)
    value_code = _norm(value_code)
    # 窄到宽：具名域+皮 → 具名域 → *
    ranked: list[tuple[int, dict[str, Any]]] = []
    for r in data:
        if not _row_matches(
            r,
            domain_id=domain_id,
            skin_id=skin_id,
            dict_key=dict_key,
            value_code=value_code,
        ):
            continue
        d = _norm(r.get("domain_id")) or WILDCARD_DOMAIN
        s = _norm(r.get("skin_id"))
        score = 0
        if d == domain_id:
            score += 2
        if s and s == skin_id:
            score += 1
        ranked.append((score, r))
    if not ranked:
        return None
    ranked.sort(key=lambda x: (-x[0], int(x[1].get("sort") or 0)))
    return _norm(ranked[0][1].get("label_zh")) or None


def list_dict_options(
    domain_id: str,
    dict_key: str,
    *,
    skin_id: str = "",
    rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """某 dict_key 的选项表（已按 sort）；具名域覆盖 *。"""
    data = _rows_or_seed(rows)
    domain_id = _norm(domain_id) or WILDCARD_DOMAIN
    skin_id = _norm(skin_id)
    dict_key = _norm(dict_key)
    by_code: dict[str, tuple[int, dict[str, Any]]] = {}
    for r in data:
        if not _row_matches(
            r, domain_id=domain_id, skin_id=skin_id, dict_key=dict_key
        ):
            continue
        code = _norm(r.get("value_code"))
        if not code:
            continue
        d = _norm(r.get("domain_id")) or WILDCARD_DOMAIN
        s = _norm(r.get("skin_id"))
        score = 0
        if d == domain_id:
            score += 2
        if s and s == skin_id:
            score += 1
        prev = by_code.get(code)
        if prev is None or score > prev[0]:
            by_code[code] = (score, r)
    items: list[dict[str, Any]] = []
    for code, (_sc, r) in by_code.items():
        items.append(
            {
                "value": code,
                "label": _norm(r.get("label_zh")) or code,
                "sort": int(r.get("sort") or 0),
            }
        )
    items.sort(key=lambda x: (x["sort"], x["value"]))
    return items


def expected_dicts_for_domain(domain_id: str) -> dict[str, tuple[str, ...]]:
    domain_id = _norm(domain_id) or WILDCARD_DOMAIN
    out: dict[str, tuple[str, ...]] = {}
    exp = _expected()
    if domain_id in exp:
        out.update(exp[domain_id])
    if domain_id in REPAIR_DOMAINS or domain_id == WILDCARD_DOMAIN:
        out.update(exp.get("*", {}))
    return out


def build_dicts_tree(
    domain_id: str,
    *,
    skin_id: str = "",
    rows: list[dict[str, Any]] | None = None,
    dict_keys: Iterable[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    data = _rows_or_seed(rows)
    domain_id = _norm(domain_id) or WILDCARD_DOMAIN
    skin_id = _norm(skin_id)
    keys: set[str] = set(dict_keys or ())
    if not keys:
        for r in data:
            d = _norm(r.get("domain_id")) or WILDCARD_DOMAIN
            if d not in (domain_id, WILDCARD_DOMAIN):
                continue
            if _norm(r.get("source")) not in BAKE_SOURCES:
                continue
            if not bool(r.get("enabled", True)):
                continue
            k = _norm(r.get("dict_key"))
            if k:
                keys.add(k)
        keys.update(expected_dicts_for_domain(domain_id).keys())
    tree: dict[str, list[dict[str, Any]]] = {}
    for key in sorted(keys):
        opts = list_dict_options(domain_id, key, skin_id=skin_id, rows=data)
        if opts:
            tree[key] = opts
    return tree


def apply_dict_values_to_schema(
    schema: dict[str, Any] | None,
    domain_id: str,
    *,
    skin_id: str = "",
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return schema or {}
    out = schema
    tree = build_dicts_tree(domain_id, skin_id=skin_id, rows=rows)
    out["dicts"] = tree
    # 兼容旧 labels 键：售后类型名
    labels = dict(out.get("labels") or {})
    refund = {o["value"]: o["label"] for o in tree.get("refund_type") or []}
    if "refund_only" in refund:
        labels.setdefault("refundTypeRefundOnly", refund["refund_only"])
    if "return_refund" in refund:
        labels.setdefault("refundTypeReturnRefund", refund["return_refund"])
    if labels:
        out["labels"] = labels
    return out


def apply_dict_values_to_spec(
    spec: dict[str, Any],
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    out = dict(spec)
    sch = out.get("schema") if isinstance(out.get("schema"), dict) else {}
    domain = _norm(out.get("domain")) or _norm(sch.get("domain")) or ""
    if not domain:
        return out
    skin = _norm(out.get("skin")) or _norm(sch.get("skin")) or ""
    out["schema"] = apply_dict_values_to_schema(
        dict(sch), domain, skin_id=skin, rows=rows
    )
    return out


def gap_report(
    domain_id: str,
    *,
    skin_id: str = "",
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """期望 dict_key/value_code 在台里解析不到 → 缺口。"""
    data = _rows_or_seed(rows)
    domain_id = _norm(domain_id) or WILDCARD_DOMAIN
    skin_id = _norm(skin_id)
    expected = expected_dicts_for_domain(domain_id)
    gaps: list[dict[str, str]] = []
    for dict_key, codes in expected.items():
        for code in codes:
            if resolve_label(
                domain_id, dict_key, code, skin_id=skin_id, rows=data
            ):
                continue
            gaps.append(
                {
                    "domain_id": domain_id,
                    "skin_id": skin_id,
                    "dict_key": dict_key,
                    "value_code": code,
                }
            )
    return {"gap_count": len(gaps), "gaps": gaps, "domain_id": domain_id}


async def upsert_entry(
    db: AsyncSession,
    *,
    domain_id: str,
    dict_key: str,
    value_code: str,
    label_zh: str,
    skin_id: str = "",
    sort: int = 0,
    enabled: bool = True,
    source: str = "manual",
) -> dict[str, Any]:
    from app.models import FactoryDictValue

    domain_id = _norm(domain_id) or WILDCARD_DOMAIN
    skin_id = _norm(skin_id)
    dict_key = _norm(dict_key)
    value_code = _norm(value_code)
    label_zh = _norm(label_zh)
    source = _norm(source) or "manual"
    if not dict_key or not value_code or not label_zh:
        raise ValueError("dict_key / value_code / label_zh 不能为空")
    if len(dict_key) > KEY_MAX_LEN or len(value_code) > KEY_MAX_LEN:
        raise ValueError(f"dict_key / value_code 最多 {KEY_MAX_LEN} 字")
    if len(label_zh) > ZH_MAX_LEN:
        raise ValueError(f"label_zh 最多 {ZH_MAX_LEN} 字")
    if source not in SOURCES:
        source = "manual"
    result = await db.execute(
        select(FactoryDictValue).where(
            FactoryDictValue.domain_id == domain_id,
            FactoryDictValue.skin_id == skin_id,
            FactoryDictValue.dict_key == dict_key,
            FactoryDictValue.value_code == value_code,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.label_zh = label_zh
        row.sort = int(sort or 0)
        row.enabled = bool(enabled)
        row.source = source
        row.updated_at = datetime.utcnow()
    else:
        row = FactoryDictValue(
            domain_id=domain_id,
            skin_id=skin_id,
            dict_key=dict_key,
            value_code=value_code,
            label_zh=label_zh,
            sort=int(sort or 0),
            enabled=bool(enabled),
            source=source,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    invalidate_cache()
    await load_all_rows(db)
    return row_to_dict(row)


async def delete_entry(db: AsyncSession, entry_id: int) -> bool:
    from app.models import FactoryDictValue

    row = await db.get(FactoryDictValue, entry_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    invalidate_cache()
    return True


# 禁止模块 import 时 bootstrap_from_seed()：会把种子灌进 _rows_cache，
# 导致 migrate 误判「已有」、列表短暂偏离库表。单测在 setUp 里自行 bootstrap。
