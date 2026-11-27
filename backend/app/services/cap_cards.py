"""工厂能力说明卡：cap → README 段 / 菜单入口 / 关则禁宣称。

真源：factory_cap_card。种子仅 asset_seeds/cap_cards.json。
消费面：bake README 占位（addons.security/ai_assistant bits）；诚实闸查关开宣称。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_desk_cache import AssetRowsCache, norm_text

SOURCES = frozenset({"migrated", "scan", "manual"})
BAKE_SOURCES = frozenset({"migrated", "scan", "manual"})

_cache = AssetRowsCache()


def _norm(s: str | None) -> str:
    return norm_text(s)


def _needles_val(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [_norm(str(x)) for x in raw if _norm(str(x))]
    if isinstance(raw, str) and raw.strip():
        try:
            obj = json.loads(raw)
            if isinstance(obj, list):
                return [_norm(str(x)) for x in obj if _norm(str(x))]
        except json.JSONDecodeError:
            return [p.strip() for p in raw.split(",") if p.strip()]
    return []


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "cap_id": _norm(row.cap_id),
        "title_zh": _norm(row.title_zh),
        "body_zh": str(row.body_zh or ""),
        "auth_line_on": str(row.auth_line_on or ""),
        "auth_line_off": str(row.auth_line_off or ""),
        "backend_suffix": _norm(row.backend_suffix),
        "menu_ids": _norm(row.menu_ids),
        "claim_needles": _needles_val(row.claim_needles),
        "readme_slot": _norm(row.readme_slot),
        "sort": int(row.sort or 0),
        "source": str(row.source or "manual"),
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    }


def invalidate_cache() -> None:
    _cache.invalidate()


def _seed_payload() -> list[dict[str, Any]]:
    from app.services.asset_seeds import load_seed_json

    return list(load_seed_json("cap_cards"))


def bootstrap_from_seed() -> None:
    _cache.set(_seed_payload())


async def load_all_rows(db: AsyncSession) -> list[dict[str, Any]]:
    from app.models import FactoryCapCard

    result = await db.execute(
        select(FactoryCapCard).order_by(FactoryCapCard.sort, FactoryCapCard.id)
    )
    rows = [row_to_dict(r) for r in result.scalars().all()]
    _cache.set(rows)
    return list(rows)


async def migrate_seed_if_empty(db: AsyncSession) -> dict[str, int]:
    from app.models import FactoryCapCard

    key_rows = await db.execute(select(FactoryCapCard.cap_id))
    have = {_norm(a) for (a,) in key_rows.all()}
    inserted = 0
    for item in _seed_payload():
        cid = _norm(item.get("cap_id"))
        if not cid or cid in have:
            continue
        db.add(
            FactoryCapCard(
                cap_id=cid,
                title_zh=_norm(item.get("title_zh")) or cid,
                body_zh=str(item.get("body_zh") or ""),
                auth_line_on=str(item.get("auth_line_on") or ""),
                auth_line_off=str(item.get("auth_line_off") or ""),
                backend_suffix=_norm(item.get("backend_suffix")),
                menu_ids=_norm(item.get("menu_ids")),
                claim_needles=_needles_val(item.get("claim_needles")),
                readme_slot=_norm(item.get("readme_slot")),
                sort=int(item.get("sort") or 0),
                source=_norm(item.get("source")) or "migrated",
            )
        )
        inserted += 1
        have.add(cid)
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


def get_card(
    cap_id: str,
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    cap_id = _norm(cap_id)
    for r in _rows_or_seed(rows):
        if _norm(r.get("source")) not in BAKE_SOURCES:
            continue
        if _norm(r.get("cap_id")) == cap_id:
            return r
    return None


def readme_faq_body(cap_id: str, *, enabled: bool, rows: list[dict[str, Any]] | None = None) -> str:
    if not enabled:
        return ""
    card = get_card(cap_id, rows=rows)
    if not card:
        return ""
    return str(card.get("body_zh") or "")


def security_auth_bits(
    enabled: bool,
    persistence_backend: str,
    *,
    rows: list[dict[str, Any]] | None = None,
) -> tuple[str, str, str]:
    """对齐原 security_readme_bits：(backend_cell, auth_line, faq)。"""
    card = get_card("spring_security", rows=rows)
    if enabled:
        suffix = (card or {}).get("backend_suffix") or " + Spring Security"
        backend = persistence_backend.rstrip("。") + str(suffix)
        auth = str((card or {}).get("auth_line_on") or "")
        faq = str((card or {}).get("body_zh") or "")
        return backend, auth, faq
    auth = str((card or {}).get("auth_line_off") or "")
    return persistence_backend, auth, ""


def menu_ids_for(cap_id: str, *, rows: list[dict[str, Any]] | None = None) -> list[str]:
    card = get_card(cap_id, rows=rows)
    if not card:
        return []
    raw = _norm(card.get("menu_ids"))
    return [p for p in raw.split(",") if p]


def readme_honesty_errors(
    readme: str,
    *,
    enabled: dict[str, bool],
    rows: list[dict[str, Any]] | None = None,
) -> list[str]:
    """开则 README 须含宣称针；关则不得残留宣称针。"""
    text = readme or ""
    errors: list[str] = []
    for r in _rows_or_seed(rows):
        if _norm(r.get("source")) not in BAKE_SOURCES:
            continue
        cid = _norm(r.get("cap_id"))
        if not cid or cid not in enabled:
            continue
        needles = _needles_val(r.get("claim_needles"))
        on = bool(enabled.get(cid))
        if on:
            if needles and not any(n in text for n in needles):
                errors.append(f"已开 {cid} 但 README 缺少说明要点（如 {needles[0]}）")
        else:
            for n in needles:
                if n and n in text:
                    errors.append(f"未开 {cid} 但 README 仍宣称「{n}」")
    return errors


def expected_cap_ids_from_seed() -> tuple[str, ...]:
    return tuple(
        sorted({_norm(r.get("cap_id")) for r in _seed_payload() if _norm(r.get("cap_id"))})
    )


def gap_report(*, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    data = _rows_or_seed(rows)
    have = {
        _norm(r.get("cap_id"))
        for r in data
        if _norm(r.get("source")) in BAKE_SOURCES and _norm(r.get("cap_id"))
    }
    gaps = []
    for cid in expected_cap_ids_from_seed():
        if cid not in have:
            gaps.append({"cap_id": cid, "reason": "缺少能力说明卡"})
            continue
        card = next((r for r in data if _norm(r.get("cap_id")) == cid), None)
        if card and not str(card.get("body_zh") or "").strip():
            gaps.append({"cap_id": cid, "reason": "说明正文为空"})
    return {"gap_count": len(gaps), "gaps": gaps}


async def upsert_entry(
    db: AsyncSession,
    *,
    cap_id: str,
    title_zh: str = "",
    body_zh: str = "",
    auth_line_on: str = "",
    auth_line_off: str = "",
    backend_suffix: str = "",
    menu_ids: str = "",
    claim_needles: list[str] | None = None,
    readme_slot: str = "",
    sort: int = 0,
    source: str = "manual",
) -> dict[str, Any]:
    from app.models import FactoryCapCard

    cap_id = _norm(cap_id)
    source = _norm(source) or "manual"
    if not cap_id:
        raise ValueError("cap_id 必填")
    if source not in SOURCES:
        source = "manual"
    needles = _needles_val(claim_needles)
    result = await db.execute(select(FactoryCapCard).where(FactoryCapCard.cap_id == cap_id))
    row = result.scalar_one_or_none()
    if row:
        row.title_zh = _norm(title_zh) or row.title_zh or cap_id
        row.body_zh = body_zh if body_zh is not None else row.body_zh
        row.auth_line_on = auth_line_on if auth_line_on is not None else row.auth_line_on
        row.auth_line_off = auth_line_off if auth_line_off is not None else row.auth_line_off
        row.backend_suffix = _norm(backend_suffix) if backend_suffix is not None else row.backend_suffix
        row.menu_ids = _norm(menu_ids) if menu_ids is not None else row.menu_ids
        row.claim_needles = needles if claim_needles is not None else row.claim_needles
        row.readme_slot = _norm(readme_slot) or row.readme_slot
        row.sort = int(sort or 0)
        row.source = source
        row.updated_at = datetime.utcnow()
    else:
        row = FactoryCapCard(
            cap_id=cap_id,
            title_zh=_norm(title_zh) or cap_id,
            body_zh=body_zh or "",
            auth_line_on=auth_line_on or "",
            auth_line_off=auth_line_off or "",
            backend_suffix=_norm(backend_suffix),
            menu_ids=_norm(menu_ids),
            claim_needles=needles,
            readme_slot=_norm(readme_slot),
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
    from app.models import FactoryCapCard

    row = await db.get(FactoryCapCard, entry_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    invalidate_cache()
    return True
