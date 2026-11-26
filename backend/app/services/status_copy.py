"""工厂状态机话术台：持久化、迁入、解析、扫缺口、bake 注入。

真源：factory_status_copy。与 ticket_copy_text / Surface Lexicon 分工：
本台只管 status_code ↔ 列表徽章 / 主按钮 / 空态句。
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
# machine_id → schema.entities 键
MACHINE_ENTITY_KEY: dict[str, str] = {
    "order": "order",
    "ticket": "ticket",
    "reservation": "reservation",
}
MACHINE_LABELS_ZH: dict[str, str] = {
    "order": "订单",
    "ticket": "单据",
    "reservation": "预约",
}
ZH_MAX_LEN = 64
EMPTY_MAX_LEN = 128
ROLES_DEFAULT = "admin,staff,user"

_lock = threading.RLock()
_rows_cache: list[dict[str, Any]] | None = None


def _norm(s: str | None) -> str:
    return (s or "").strip()


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "domain_id": _norm(row.domain_id) or WILDCARD_DOMAIN,
        "machine_id": _norm(row.machine_id),
        "status_code": _norm(row.status_code),
        "label_zh": _norm(row.label_zh),
        "action_zh": _norm(row.action_zh),
        "empty_zh": _norm(row.empty_zh),
        "for_roles": _norm(row.for_roles) or ROLES_DEFAULT,
        "source": str(row.source or "manual"),
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    }


def invalidate_cache() -> None:
    global _rows_cache
    with _lock:
        _rows_cache = None


def _seed_payload() -> list[dict[str, Any]]:
    """首迁种子仅来自 asset_seeds/status_copy.json；运行真源是库表。"""
    from app.services.asset_seeds import load_seed_json

    return list(load_seed_json("status_copy"))


def bootstrap_from_seed() -> None:
    rows = _seed_payload()
    with _lock:
        global _rows_cache
        _rows_cache = rows


async def load_all_rows(db: AsyncSession) -> list[dict[str, Any]]:
    """读库并刷新进程缓存。有 Session 时禁止返回种子冒充库数据。"""
    global _rows_cache
    from app.models import FactoryStatusCopy

    result = await db.execute(select(FactoryStatusCopy).order_by(FactoryStatusCopy.id))
    rows = [row_to_dict(r) for r in result.scalars().all()]
    with _lock:
        _rows_cache = rows
    return list(rows)


async def migrate_seed_if_empty(db: AsyncSession) -> dict[str, int]:
    """只追加：种子里库中没有的主键才 INSERT；已有行一律不改。"""
    from app.models import FactoryStatusCopy

    key_rows = await db.execute(
        select(
            FactoryStatusCopy.domain_id,
            FactoryStatusCopy.machine_id,
            FactoryStatusCopy.status_code,
        )
    )
    have = {
        (_norm(a) or WILDCARD_DOMAIN, _norm(b), _norm(c)) for a, b, c in key_rows.all()
    }
    inserted = 0
    seed = _seed_payload()
    for item in seed:
        tup = (
            _norm(item.get("domain_id")) or WILDCARD_DOMAIN,
            _norm(item.get("machine_id")),
            _norm(item.get("status_code")),
        )
        if not tup[1] or not tup[2] or tup in have:
            continue
        payload = {
            "domain_id": tup[0],
            "machine_id": tup[1],
            "status_code": tup[2],
            "label_zh": _norm(item.get("label_zh")),
            "action_zh": _norm(item.get("action_zh")),
            "empty_zh": _norm(item.get("empty_zh")),
            "for_roles": _norm(item.get("for_roles")) or ROLES_DEFAULT,
            "source": "migrated",
        }
        if not payload["label_zh"]:
            continue
        db.add(FactoryStatusCopy(**payload))
        inserted += 1
        have.add(tup)
    if inserted:
        await db.commit()
    invalidate_cache()
    rows = await load_all_rows(db)
    return {"inserted": inserted, "total": len(rows)}


def _pick_row(
    rows: Iterable[dict[str, Any]],
    *,
    domain_id: str,
    machine_id: str,
    status_code: str,
) -> dict[str, Any] | None:
    domain_id = _norm(domain_id) or WILDCARD_DOMAIN
    machine_id = _norm(machine_id)
    status_code = _norm(status_code)
    by_dom: dict[str, dict[str, Any]] = {}
    for r in rows:
        if _norm(r.get("machine_id")) != machine_id:
            continue
        if _norm(r.get("status_code")) != status_code:
            continue
        if _norm(r.get("source")) not in BAKE_SOURCES:
            continue
        d = _norm(r.get("domain_id")) or WILDCARD_DOMAIN
        by_dom[d] = r
    if domain_id in by_dom:
        return by_dom[domain_id]
    if WILDCARD_DOMAIN in by_dom:
        return by_dom[WILDCARD_DOMAIN]
    return None


def _rows_or_seed(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """空库未迁入时仍用种子，保证 bake 注入不空白。"""
    data = rows
    if data is None:
        with _lock:
            data = list(_rows_cache) if _rows_cache is not None else None
    if not data:
        return _seed_payload()
    return list(data)


def resolve_status(
    domain_id: str,
    machine_id: str,
    status_code: str,
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    data = _rows_or_seed(rows)
    hit = _pick_row(
        data or [],
        domain_id=domain_id,
        machine_id=machine_id,
        status_code=status_code,
    )
    if not hit:
        return None
    return {
        "label": hit["label_zh"],
        "action": hit.get("action_zh") or "",
        "empty": hit.get("empty_zh") or "",
        "forRoles": [
            p for p in (_norm(hit.get("for_roles")) or ROLES_DEFAULT).split(",") if p
        ],
        "domain_id": hit["domain_id"],
        "machine_id": hit["machine_id"],
        "status_code": hit["status_code"],
    }


def build_status_copy_tree(
    domain_id: str,
    *,
    rows: list[dict[str, Any]] | None = None,
    machines: Iterable[str] | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    """schema.statusCopy：machine → status → {label,action,empty,forRoles}。"""
    data = _rows_or_seed(rows)
    domain_id = _norm(domain_id) or WILDCARD_DOMAIN
    want = set(machines or MACHINE_ENTITY_KEY.keys())
    tree: dict[str, dict[str, dict[str, Any]]] = {}
    # 收集该域+通配下各 machine 的全部 status
    codes_by_machine: dict[str, set[str]] = {}
    for r in data or []:
        mid = _norm(r.get("machine_id"))
        if mid not in want:
            continue
        d = _norm(r.get("domain_id")) or WILDCARD_DOMAIN
        if d not in (domain_id, WILDCARD_DOMAIN):
            continue
        codes_by_machine.setdefault(mid, set()).add(_norm(r.get("status_code")))
    for mid, codes in codes_by_machine.items():
        bucket: dict[str, dict[str, Any]] = {}
        for code in sorted(codes):
            resolved = resolve_status(domain_id, mid, code, rows=data)
            if not resolved:
                continue
            bucket[code] = {
                "label": resolved["label"],
                "action": resolved["action"],
                "empty": resolved["empty"],
                "forRoles": resolved["forRoles"],
            }
        if bucket:
            tree[mid] = bucket
    return tree


def apply_status_copy_to_schema(
    schema: dict[str, Any] | None,
    domain_id: str,
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """写入 schema.statusCopy，并用 label 覆盖 entities.*.states（有台账才盖）。"""
    if not isinstance(schema, dict):
        return schema or {}
    out = schema
    tree = build_status_copy_tree(domain_id, rows=rows)
    out["statusCopy"] = tree
    ents = out.get("entities")
    if not isinstance(ents, dict):
        return out
    for machine, entity_key in MACHINE_ENTITY_KEY.items():
        pack = tree.get(machine)
        if not pack:
            continue
        ent = ents.get(entity_key)
        if not isinstance(ent, dict):
            continue
        states = dict(ent.get("states") or {})
        for code, meta in pack.items():
            lab = _norm(meta.get("label"))
            if lab:
                states[code] = lab
        ent["states"] = states
        ents[entity_key] = ent
    out["entities"] = ents
    return out


def apply_status_copy_to_spec(
    spec: dict[str, Any],
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """装配管线末段：按 spec.domain / schema.domain 注入。"""
    out = dict(spec)
    sch = out.get("schema") if isinstance(out.get("schema"), dict) else {}
    domain = _norm(out.get("domain")) or _norm(sch.get("domain")) or ""
    if not domain:
        return out
    out["schema"] = apply_status_copy_to_schema(dict(sch), domain, rows=rows)
    return out


def gap_report(
    domain_id: str,
    schema: dict[str, Any] | None,
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """包内 entities.*.states 出现的 status 在台里没有（含 * 兜底）→ 缺口。"""
    data = _rows_or_seed(rows)
    gaps: list[dict[str, str]] = []
    ents = (schema or {}).get("entities") if isinstance(schema, dict) else {}
    if not isinstance(ents, dict):
        return {"gap_count": 0, "gaps": [], "domain_id": domain_id}
    entity_to_machine = {v: k for k, v in MACHINE_ENTITY_KEY.items()}
    for ek, ent in ents.items():
        if not isinstance(ent, dict):
            continue
        mid = entity_to_machine.get(ek)
        if not mid:
            continue
        states = ent.get("states")
        if not isinstance(states, dict):
            continue
        for code in states:
            code_n = _norm(str(code))
            if not code_n:
                continue
            if resolve_status(domain_id, mid, code_n, rows=data):
                continue
            gaps.append(
                {
                    "domain_id": domain_id,
                    "machine_id": mid,
                    "status_code": code_n,
                    "entity_key": ek,
                    "schema_label": _norm(str(states.get(code) or "")),
                }
            )
    return {"gap_count": len(gaps), "gaps": gaps, "domain_id": domain_id}


def _schema_machine_states(schema: dict[str, Any] | None) -> list[tuple[str, str, str, str]]:
    """返回 (machine_id, status_code, entity_key, schema_label)。"""
    out: list[tuple[str, str, str, str]] = []
    ents = (schema or {}).get("entities") if isinstance(schema, dict) else {}
    if not isinstance(ents, dict):
        return out
    entity_to_machine = {v: k for k, v in MACHINE_ENTITY_KEY.items()}
    for ek, ent in ents.items():
        if not isinstance(ent, dict):
            continue
        mid = entity_to_machine.get(ek)
        if not mid:
            continue
        states = ent.get("states")
        if not isinstance(states, dict):
            continue
        for code, lab in states.items():
            code_n = _norm(str(code))
            if not code_n:
                continue
            out.append((mid, code_n, ek, _norm(str(lab or ""))))
    return out


def catalog_domain_gaps(*, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """扫 catalog：凡 schema 暴露的 order/ticket/reservation 状态，须有具名域行（仅 * 不够加厚）。

    无这三类状态机的域（内容向等）不记缺口。
    """
    from app.bake import domain_schema as ds
    from app.bake.catalog import DOMAINS
    from app.services import dict_values as dv

    data = _rows_or_seed(rows)
    named = {
        (
            _norm(r.get("domain_id")),
            _norm(r.get("machine_id")),
            _norm(r.get("status_code")),
        )
        for r in data
        if _norm(r.get("domain_id")) not in ("", WILDCARD_DOMAIN)
        and _norm(r.get("source")) in BAKE_SOURCES
        and _norm(r.get("machine_id"))
        and _norm(r.get("status_code"))
        and _norm(r.get("label_zh"))
    }
    gaps: list[dict[str, str]] = []
    # 裸 builder：domain_schema 晚导入本函数名，须改模块属性才能跳过注入
    import app.services.status_copy as sc_mod

    saved_sc = sc_mod.apply_status_copy_to_schema
    saved_dv = dv.apply_dict_values_to_schema
    sc_mod.apply_status_copy_to_schema = lambda s, d, **k: s  # type: ignore[assignment]
    dv.apply_dict_values_to_schema = lambda s, d, **k: s  # type: ignore[assignment]
    try:
        for dom in sorted(DOMAINS):
            sch = ds.build_domain_schema("状态话术加厚探针", dom)
            for mid, code, ek, lab in _schema_machine_states(sch):
                if (dom, mid, code) in named:
                    continue
                gaps.append(
                    {
                        "domain_id": dom,
                        "machine_id": mid,
                        "status_code": code,
                        "entity_key": ek,
                        "schema_label": lab,
                        "reason": "域缺具名话术（仅有 * 不够加厚）",
                    }
                )
    finally:
        sc_mod.apply_status_copy_to_schema = saved_sc  # type: ignore[assignment]
        dv.apply_dict_values_to_schema = saved_dv  # type: ignore[assignment]
    return {
        "gap_count": len(gaps),
        "gaps": gaps,
        "domain_count": len(DOMAINS),
    }


async def upsert_entry(
    db: AsyncSession,
    *,
    domain_id: str,
    machine_id: str,
    status_code: str,
    label_zh: str,
    action_zh: str = "",
    empty_zh: str = "",
    for_roles: str = ROLES_DEFAULT,
    source: str = "manual",
) -> dict[str, Any]:
    from app.models import FactoryStatusCopy

    domain_id = _norm(domain_id) or WILDCARD_DOMAIN
    machine_id = _norm(machine_id)
    status_code = _norm(status_code)
    label_zh = _norm(label_zh)
    action_zh = _norm(action_zh)
    empty_zh = _norm(empty_zh)
    for_roles = _norm(for_roles) or ROLES_DEFAULT
    source = _norm(source) or "manual"
    if not machine_id or not status_code or not label_zh:
        raise ValueError("machine_id / status_code / label_zh 不能为空")
    if len(label_zh) > ZH_MAX_LEN:
        raise ValueError(f"label_zh 最多 {ZH_MAX_LEN} 字")
    if len(action_zh) > ZH_MAX_LEN:
        raise ValueError(f"action_zh 最多 {ZH_MAX_LEN} 字")
    if len(empty_zh) > EMPTY_MAX_LEN:
        raise ValueError(f"empty_zh 最多 {EMPTY_MAX_LEN} 字")
    if source not in SOURCES:
        source = "manual"
    if machine_id not in MACHINE_ENTITY_KEY:
        # 允许扩展机，但不拦；首刀测只钉 order/ticket
        pass
    result = await db.execute(
        select(FactoryStatusCopy).where(
            FactoryStatusCopy.domain_id == domain_id,
            FactoryStatusCopy.machine_id == machine_id,
            FactoryStatusCopy.status_code == status_code,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.label_zh = label_zh
        row.action_zh = action_zh
        row.empty_zh = empty_zh
        row.for_roles = for_roles
        row.source = source
        row.updated_at = datetime.utcnow()
    else:
        row = FactoryStatusCopy(
            domain_id=domain_id,
            machine_id=machine_id,
            status_code=status_code,
            label_zh=label_zh,
            action_zh=action_zh,
            empty_zh=empty_zh,
            for_roles=for_roles,
            source=source,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    invalidate_cache()
    await load_all_rows(db)
    return row_to_dict(row)


async def delete_entry(db: AsyncSession, entry_id: int) -> bool:
    from app.models import FactoryStatusCopy

    row = await db.get(FactoryStatusCopy, entry_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    invalidate_cache()
    return True
