"""工厂岗位×菜单矩阵：role × menu_id → bake 补齐 menus。

真源：factory_menu_matrix。种子仅 asset_seeds/menu_matrix.json。
消费面：apply_menu_matrix_to_schema；扫「能力开了菜单无入口」。
不替代 X-ORG 岗位菜单勾选（那是学生包内运行时能力）。
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SOURCES = frozenset({"migrated", "scan", "manual"})
BAKE_SOURCES = frozenset({"migrated", "scan", "manual"})
ROLES = frozenset({"admin", "staff", "user"})
WILDCARD = "*"

_lock = threading.RLock()
_rows_cache: list[dict[str, Any]] | None = None


def _norm(s: str | None) -> str:
    return (s or "").strip()


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "domain_id": _norm(row.domain_id) or WILDCARD,
        "role": _norm(row.role),
        "menu_id": _norm(row.menu_id),
        "label_zh": _norm(row.label_zh),
        "cap_id": _norm(row.cap_id),
        "always_on": bool(row.always_on),
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
    from app.services.asset_seeds import load_seed_json

    return list(load_seed_json("menu_matrix"))


def bootstrap_from_seed() -> None:
    rows = _seed_payload()
    with _lock:
        global _rows_cache
        _rows_cache = rows


async def load_all_rows(db: AsyncSession) -> list[dict[str, Any]]:
    global _rows_cache
    from app.models import FactoryMenuMatrix

    result = await db.execute(
        select(FactoryMenuMatrix).order_by(
            FactoryMenuMatrix.domain_id,
            FactoryMenuMatrix.role,
            FactoryMenuMatrix.sort,
            FactoryMenuMatrix.id,
        )
    )
    rows = [row_to_dict(r) for r in result.scalars().all()]
    with _lock:
        _rows_cache = rows
    return list(rows)


async def migrate_seed_if_empty(db: AsyncSession) -> dict[str, int]:
    from app.models import FactoryMenuMatrix

    key_rows = await db.execute(
        select(
            FactoryMenuMatrix.domain_id,
            FactoryMenuMatrix.role,
            FactoryMenuMatrix.menu_id,
        )
    )
    have = {
        (_norm(a) or WILDCARD, _norm(b), _norm(c)) for a, b, c in key_rows.all()
    }
    inserted = 0
    for item in _seed_payload():
        domain_id = _norm(item.get("domain_id")) or WILDCARD
        role = _norm(item.get("role"))
        menu_id = _norm(item.get("menu_id"))
        key = (domain_id, role, menu_id)
        if not role or not menu_id or key in have:
            continue
        db.add(
            FactoryMenuMatrix(
                domain_id=domain_id,
                role=role,
                menu_id=menu_id,
                label_zh=_norm(item.get("label_zh")) or menu_id,
                cap_id=_norm(item.get("cap_id")),
                always_on=bool(item.get("always_on", False)),
                sort=int(item.get("sort") or 0),
                enabled=bool(item.get("enabled", True)),
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


def _domain_rows(domain: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    named = [r for r in rows if _norm(r.get("domain_id")) == domain]
    if named:
        return named
    return [r for r in rows if _norm(r.get("domain_id")) in ("", WILDCARD)]


def _menu_keys(items: list[Any]) -> set[str]:
    out: set[str] = set()
    for m in items:
        if isinstance(m, dict):
            k = _norm(m.get("key") or m.get("id") or m.get("menu_id"))
            if k:
                out.add(k)
    return out


def apply_menu_matrix_to_schema(
    schema: dict[str, Any],
    domain: str,
    *,
    addons: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """按矩阵补齐 schema.menus[role] 缺项；不删已有项、不另起 RBAC。"""
    data = [
        r
        for r in _domain_rows(domain, _rows_or_seed(rows))
        if _norm(r.get("source")) in BAKE_SOURCES
        and bool(r.get("enabled", True))
        and _norm(r.get("role")) in ROLES
        and _norm(r.get("menu_id"))
    ]
    cap_on: set[str] = set()
    caps = addons if isinstance(addons, dict) else {}
    for k, v in caps.items():
        if k == "addons" and isinstance(v, dict):
            for nk, nv in v.items():
                if nv:
                    cap_on.add(_norm(nk))
        elif v:
            cap_on.add(_norm(k))
    for c in schema.get("capabilities") or []:
        if isinstance(c, str) and c.strip():
            cap_on.add(c.strip())

    def _cap_on(cap: str) -> bool:
        return _norm(cap) in cap_on

    menus = schema.setdefault("menus", {})
    if not isinstance(menus, dict):
        return schema
    for r in sorted(data, key=lambda x: int(x.get("sort") or 0)):
        cap = _norm(r.get("cap_id"))
        always = bool(r.get("always_on"))
        if not always:
            if not cap or not _cap_on(cap):
                continue
        role = _norm(r.get("role"))
        items = menus.get(role)
        if not isinstance(items, list):
            items = []
            menus[role] = items
        mid = _norm(r.get("menu_id"))
        if mid in _menu_keys(items):
            continue
        items.append(
            {
                "key": mid,
                "label": _norm(r.get("label_zh")) or mid,
            }
        )
    schema["menuMatrix"] = [
        {
            "role": _norm(r.get("role")),
            "menu_id": _norm(r.get("menu_id")),
            "label_zh": _norm(r.get("label_zh")),
            "cap_id": _norm(r.get("cap_id")),
            "always_on": bool(r.get("always_on")),
        }
        for r in data
    ]
    return schema


def apply_menu_matrix_to_spec(
    spec: dict[str, Any],
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """收束阶段：按矩阵补齐 menus；addon/capabilities 决定能力菜单是否挂上。"""
    sch = dict(spec.get("schema") or {})
    domain = _norm(spec.get("domain") or sch.get("domain") or "")
    addons = spec.get("addons") if isinstance(spec.get("addons"), dict) else {}
    sch = apply_menu_matrix_to_schema(sch, domain, addons=addons, rows=rows)
    out = dict(spec)
    out["schema"] = sch
    return out


ROLE_LABELS_ZH = {
    "admin": "管理端",
    "staff": "受理端",
    "user": "用户端",
}


def gap_report(*, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """种子主键缺行；以及能力卡 menu_ids 未覆盖到矩阵。"""
    data = _rows_or_seed(rows)
    have = {
        (
            _norm(r.get("domain_id")) or WILDCARD,
            _norm(r.get("role")),
            _norm(r.get("menu_id")),
        )
        for r in data
        if _norm(r.get("source")) in BAKE_SOURCES and _norm(r.get("menu_id"))
    }
    gaps: list[dict[str, Any]] = []
    for item in _seed_payload():
        key = (
            _norm(item.get("domain_id")) or WILDCARD,
            _norm(item.get("role")),
            _norm(item.get("menu_id")),
        )
        if key[1] and key[2] and key not in have:
            gaps.append(
                {
                    "domain_id": key[0],
                    "role": key[1],
                    "menu_id": key[2],
                    "reason": "种子缺行",
                }
            )
    try:
        from app.services import cap_cards as cc

        for card in cc._seed_payload():
            cid = _norm(card.get("cap_id"))
            for mid in [_norm(x) for x in _norm(card.get("menu_ids")).split(",") if _norm(x)]:
                covered = any(
                    _norm(r.get("menu_id")) == mid and _norm(r.get("cap_id")) == cid
                    for r in data
                    if _norm(r.get("source")) in BAKE_SOURCES
                )
                if not covered:
                    gaps.append(
                        {
                            "domain_id": WILDCARD,
                            "role": "",
                            "menu_id": mid,
                            "reason": f"能力 {cid} 菜单未进矩阵",
                        }
                    )
    except Exception:  # noqa: BLE001
        pass
    return {"gap_count": len(gaps), "gaps": gaps}


async def upsert_entry(
    db: AsyncSession,
    *,
    domain_id: str = WILDCARD,
    role: str,
    menu_id: str,
    label_zh: str = "",
    cap_id: str = "",
    always_on: bool = False,
    sort: int = 0,
    enabled: bool = True,
    source: str = "manual",
) -> dict[str, Any]:
    from app.models import FactoryMenuMatrix

    domain_id = _norm(domain_id) or WILDCARD
    role = _norm(role)
    menu_id = _norm(menu_id)
    source = _norm(source) or "manual"
    if role not in ROLES:
        raise ValueError("role 须为 admin / staff / user")
    if not menu_id:
        raise ValueError("menu_id 必填")
    if source not in SOURCES:
        source = "manual"
    result = await db.execute(
        select(FactoryMenuMatrix).where(
            FactoryMenuMatrix.domain_id == domain_id,
            FactoryMenuMatrix.role == role,
            FactoryMenuMatrix.menu_id == menu_id,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.label_zh = _norm(label_zh) or row.label_zh or menu_id
        row.cap_id = _norm(cap_id)
        row.always_on = bool(always_on)
        row.sort = int(sort or 0)
        row.enabled = bool(enabled)
        row.source = source
        row.updated_at = datetime.utcnow()
    else:
        row = FactoryMenuMatrix(
            domain_id=domain_id,
            role=role,
            menu_id=menu_id,
            label_zh=_norm(label_zh) or menu_id,
            cap_id=_norm(cap_id),
            always_on=bool(always_on),
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
    from app.models import FactoryMenuMatrix

    row = await db.get(FactoryMenuMatrix, entry_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    invalidate_cache()
    return True
