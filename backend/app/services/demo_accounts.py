"""工厂测试账号卡：domain × role → 账号三步。

真源：factory_demo_account。种子仅 asset_seeds/demo_accounts.json。
消费面：schema.demoAccounts；与 #3 剧本角色列对齐。
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
        "username": _norm(row.username),
        "password": _norm(row.password),
        "nickname_zh": _norm(row.nickname_zh),
        "login_hint_zh": _norm(row.login_hint_zh),
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

    return list(load_seed_json("demo_accounts"))


def bootstrap_from_seed() -> None:
    rows = _seed_payload()
    with _lock:
        global _rows_cache
        _rows_cache = rows


async def load_all_rows(db: AsyncSession) -> list[dict[str, Any]]:
    global _rows_cache
    from app.models import FactoryDemoAccount

    result = await db.execute(
        select(FactoryDemoAccount).order_by(
            FactoryDemoAccount.domain_id,
            FactoryDemoAccount.sort,
            FactoryDemoAccount.id,
        )
    )
    rows = [row_to_dict(r) for r in result.scalars().all()]
    with _lock:
        _rows_cache = rows
    return list(rows)


async def migrate_seed_if_empty(db: AsyncSession) -> dict[str, int]:
    from app.models import FactoryDemoAccount

    key_rows = await db.execute(
        select(FactoryDemoAccount.domain_id, FactoryDemoAccount.role)
    )
    have = {(_norm(a) or WILDCARD, _norm(b)) for a, b in key_rows.all()}
    inserted = 0
    for item in _seed_payload():
        domain_id = _norm(item.get("domain_id")) or WILDCARD
        role = _norm(item.get("role"))
        key = (domain_id, role)
        if not role or key in have:
            continue
        db.add(
            FactoryDemoAccount(
                domain_id=domain_id,
                role=role,
                username=_norm(item.get("username")) or role,
                password=_norm(item.get("password")) or f"{role}123",
                nickname_zh=_norm(item.get("nickname_zh")) or role,
                login_hint_zh=_norm(item.get("login_hint_zh")),
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


def _pick_for_domain(domain: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_role: dict[str, dict[str, Any]] = {}
    for r in rows:
        if _norm(r.get("source")) not in BAKE_SOURCES:
            continue
        role = _norm(r.get("role"))
        if role not in ROLES:
            continue
        dom = _norm(r.get("domain_id")) or WILDCARD
        if dom not in (WILDCARD, domain):
            continue
        prev = by_role.get(role)
        if prev is None or dom == domain:
            by_role[role] = r
    return [by_role[k] for k in ("admin", "staff", "user") if k in by_role]


def apply_demo_accounts_to_schema(
    schema: dict[str, Any],
    domain: str,
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    picked = _pick_for_domain(domain, _rows_or_seed(rows))
    schema["demoAccounts"] = [
        {
            "role": _norm(r.get("role")),
            "username": _norm(r.get("username")),
            "password": _norm(r.get("password")),
            "nickname_zh": _norm(r.get("nickname_zh")),
            "login_hint_zh": _norm(r.get("login_hint_zh")),
        }
        for r in picked
    ]
    return schema


def apply_demo_accounts_to_spec(
    spec: dict[str, Any],
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """收束：写入 schema.demoAccounts（具名域盖 *）。"""
    sch = dict(spec.get("schema") or {})
    domain = _norm(spec.get("domain") or sch.get("domain") or "")
    sch = apply_demo_accounts_to_schema(sch, domain, rows=rows)
    out = dict(spec)
    out["schema"] = sch
    return out


ROLE_LABELS_ZH = {
    "admin": "管理端",
    "staff": "受理端",
    "user": "用户端",
}


def gap_report(*, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    data = _rows_or_seed(rows)
    have = {
        (_norm(r.get("domain_id")) or WILDCARD, _norm(r.get("role")))
        for r in data
        if _norm(r.get("source")) in BAKE_SOURCES and _norm(r.get("role"))
    }
    gaps = []
    for item in _seed_payload():
        key = (_norm(item.get("domain_id")) or WILDCARD, _norm(item.get("role")))
        if key[1] and key not in have:
            gaps.append({"domain_id": key[0], "role": key[1], "reason": "种子缺行"})
    # * 下三端必须齐
    for role in ("admin", "staff", "user"):
        if (WILDCARD, role) not in have and not any(
            _norm(r.get("role")) == role for r in data if _norm(r.get("source")) in BAKE_SOURCES
        ):
            gaps.append({"domain_id": WILDCARD, "role": role, "reason": "缺少跨域默认账号"})
    return {"gap_count": len(gaps), "gaps": gaps}


async def upsert_entry(
    db: AsyncSession,
    *,
    domain_id: str = WILDCARD,
    role: str,
    username: str,
    password: str,
    nickname_zh: str = "",
    login_hint_zh: str = "",
    sort: int = 0,
    source: str = "manual",
) -> dict[str, Any]:
    from app.models import FactoryDemoAccount

    domain_id = _norm(domain_id) or WILDCARD
    role = _norm(role)
    username = _norm(username)
    password = _norm(password)
    source = _norm(source) or "manual"
    if role not in ROLES:
        raise ValueError("role 须为 admin / staff / user")
    if not username or not password:
        raise ValueError("username、password 必填")
    if source not in SOURCES:
        source = "manual"
    result = await db.execute(
        select(FactoryDemoAccount).where(
            FactoryDemoAccount.domain_id == domain_id,
            FactoryDemoAccount.role == role,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.username = username
        row.password = password
        row.nickname_zh = _norm(nickname_zh) or row.nickname_zh or role
        row.login_hint_zh = _norm(login_hint_zh)
        row.sort = int(sort or 0)
        row.source = source
        row.updated_at = datetime.utcnow()
    else:
        row = FactoryDemoAccount(
            domain_id=domain_id,
            role=role,
            username=username,
            password=password,
            nickname_zh=_norm(nickname_zh) or role,
            login_hint_zh=_norm(login_hint_zh),
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
    from app.models import FactoryDemoAccount

    row = await db.get(FactoryDemoAccount, entry_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    invalidate_cache()
    return True
