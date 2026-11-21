"""工厂开关建议台：开题扫词 → 匹配页建议卡证据。

真源：factory_addon_suggest。种子仅 asset_seeds/addon_suggest.json。
消费面：stack_scan / 匹配确认；不自动改开题、不默认瞎开。
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


def _uk(addon_id: str, hint: str) -> tuple[str, str]:
    """与 MySQL uk_addon_suggest_hint（通常大小写不敏感）对齐的逻辑主键。"""
    return (_norm(addon_id), _norm(hint).casefold())


def _hint_in_text(hint: str, text: str) -> bool:
    """扫词命中：原文包含；ASCII 提示词再按忽略大小写兜一层。"""
    h = _norm(hint)
    if not h:
        return False
    if h in text:
        return True
    if h.isascii():
        return h.casefold() in text.casefold()
    return False


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "addon_id": _norm(row.addon_id),
        "addon_label": _norm(row.addon_label),
        "hint": _norm(row.hint),
        "evidence_zh": _norm(row.evidence_zh),
        "summary_zh": _norm(row.summary_zh),
        "recommend": bool(row.recommend),
        "deliverable": bool(row.deliverable),
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

    return list(load_seed_json("addon_suggest"))


def bootstrap_from_seed() -> None:
    rows = _seed_payload()
    with _lock:
        global _rows_cache
        _rows_cache = rows


async def load_all_rows(db: AsyncSession) -> list[dict[str, Any]]:
    global _rows_cache
    from app.models import FactoryAddonSuggest

    result = await db.execute(
        select(FactoryAddonSuggest).order_by(
            FactoryAddonSuggest.addon_id,
            FactoryAddonSuggest.sort,
            FactoryAddonSuggest.id,
        )
    )
    rows = [row_to_dict(r) for r in result.scalars().all()]
    with _lock:
        _rows_cache = rows
    return list(rows)


async def migrate_seed_if_empty(db: AsyncSession) -> dict[str, int]:
    """只追加：种子缺主键才 INSERT（hint 按 casefold，避免撞 MySQL uk）。"""
    from app.models import FactoryAddonSuggest

    key_rows = await db.execute(
        select(FactoryAddonSuggest.addon_id, FactoryAddonSuggest.hint)
    )
    have = {_uk(a, b) for a, b in key_rows.all()}
    inserted = 0
    for item in _seed_payload():
        addon_id = _norm(item.get("addon_id"))
        hint = _norm(item.get("hint"))
        key = _uk(addon_id, hint)
        if not addon_id or not hint or key in have:
            continue
        db.add(
            FactoryAddonSuggest(
                addon_id=addon_id,
                addon_label=_norm(item.get("addon_label")) or addon_id,
                hint=hint,
                evidence_zh=_norm(item.get("evidence_zh")) or f"开题点名「{hint}」",
                summary_zh=_norm(item.get("summary_zh")),
                recommend=bool(item.get("recommend", True)),
                deliverable=bool(item.get("deliverable", True)),
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


def suggest_addons(
    title: str,
    proposal_text: str = "",
    *,
    rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """扫题名+正文 → 开关建议列表（含证据）。不改开题。"""
    from app.bake.scene_scan import copy_scan_text
    from app.services.proposal import strip_non_dev_sections

    body = strip_non_dev_sections(proposal_text or "")
    text = copy_scan_text(title, body)
    data = [
        r
        for r in _rows_or_seed(rows)
        if _norm(r.get("source")) in BAKE_SOURCES and _norm(r.get("hint"))
    ]
    by_addon: dict[str, dict[str, Any]] = {}
    for r in sorted(data, key=lambda x: (x.get("addon_id") or "", int(x.get("sort") or 0))):
        hint = _norm(r.get("hint"))
        if not _hint_in_text(hint, text):
            continue
        aid = _norm(r.get("addon_id"))
        if not aid:
            continue
        slot = by_addon.get(aid)
        if not slot:
            slot = {
                "addon_id": aid,
                "addon_label": _norm(r.get("addon_label")) or aid,
                "recommended": bool(r.get("recommend")),
                "deliverable": bool(r.get("deliverable", True)),
                "summary_zh": _norm(r.get("summary_zh")),
                "evidences": [],
                "hints": [],
            }
            by_addon[aid] = slot
        ev = _norm(r.get("evidence_zh")) or f"开题点名「{hint}」"
        if ev not in slot["evidences"]:
            slot["evidences"].append(ev)
        if hint not in slot["hints"]:
            slot["hints"].append(hint)
        if bool(r.get("recommend")):
            slot["recommended"] = True
        if not slot["summary_zh"]:
            slot["summary_zh"] = _norm(r.get("summary_zh"))
    return list(by_addon.values())


def expected_addon_ids_from_seed() -> tuple[str, ...]:
    ids = sorted({_norm(r.get("addon_id")) for r in _seed_payload() if _norm(r.get("addon_id"))})
    return tuple(ids)


def gap_report(
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """期望有扫词的 addon 在台中无任何 hint → 缺口。"""
    data = _rows_or_seed(rows)
    have = {
        _norm(r.get("addon_id"))
        for r in data
        if _norm(r.get("source")) in BAKE_SOURCES and _norm(r.get("hint"))
    }
    gaps = []
    for aid in expected_addon_ids_from_seed():
        if aid not in have:
            gaps.append({"addon_id": aid, "reason": "缺少扫词规则"})
    return {"gap_count": len(gaps), "gaps": gaps}


async def upsert_entry(
    db: AsyncSession,
    *,
    addon_id: str,
    hint: str,
    addon_label: str = "",
    evidence_zh: str = "",
    summary_zh: str = "",
    recommend: bool = True,
    deliverable: bool = True,
    sort: int = 0,
    source: str = "manual",
) -> dict[str, Any]:
    from app.models import FactoryAddonSuggest

    addon_id = _norm(addon_id)
    hint = _norm(hint)
    source = _norm(source) or "manual"
    if not addon_id or not hint:
        raise ValueError("addon_id、hint 必填")
    if source not in SOURCES:
        source = "manual"
    result = await db.execute(
        select(FactoryAddonSuggest).where(FactoryAddonSuggest.addon_id == addon_id)
    )
    row = next(
        (
            r
            for r in result.scalars().all()
            if _norm(r.hint).casefold() == hint.casefold()
        ),
        None,
    )
    if row:
        row.addon_label = _norm(addon_label) or row.addon_label or addon_id
        row.evidence_zh = _norm(evidence_zh) or row.evidence_zh
        row.summary_zh = _norm(summary_zh) or row.summary_zh
        row.recommend = bool(recommend)
        row.deliverable = bool(deliverable)
        row.sort = int(sort or 0)
        row.source = source
        row.updated_at = datetime.utcnow()
    else:
        row = FactoryAddonSuggest(
            addon_id=addon_id,
            addon_label=_norm(addon_label) or addon_id,
            hint=hint,
            evidence_zh=_norm(evidence_zh) or f"开题点名「{hint}」",
            summary_zh=_norm(summary_zh),
            recommend=bool(recommend),
            deliverable=bool(deliverable),
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
    from app.models import FactoryAddonSuggest

    row = await db.get(FactoryAddonSuggest, entry_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    invalidate_cache()
    return True
