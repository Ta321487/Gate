"""工厂论文图题模板：diagram_kind × domain → 标题模板。

真源：factory_diagram_title。种子仅 asset_seeds/diagram_titles.json。
消费面：resolve_figure_title / schema.diagramTitleTemplates；几何仍归 parked m。
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SOURCES = frozenset({"migrated", "scan", "manual"})
BAKE_SOURCES = frozenset({"migrated", "scan", "manual"})
DIAGRAM_KINDS = frozenset(
    {"class", "sequence", "activity", "er", "architecture", "modules"}
)
KIND_LABELS_ZH = {
    "class": "类图",
    "sequence": "序列图",
    "activity": "活动图",
    "er": "E-R图",
    "architecture": "逻辑架构图",
    "modules": "功能模块图",
}
WILDCARD = "*"

_lock = threading.RLock()
_rows_cache: list[dict[str, Any]] | None = None


def _norm(s: str | None) -> str:
    return (s or "").strip()


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "diagram_kind": _norm(row.diagram_kind),
        "domain_id": _norm(row.domain_id) or WILDCARD,
        "title_tpl": _norm(row.title_tpl),
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

    return list(load_seed_json("diagram_titles"))


def bootstrap_from_seed() -> None:
    rows = _seed_payload()
    with _lock:
        global _rows_cache
        _rows_cache = rows


async def load_all_rows(db: AsyncSession) -> list[dict[str, Any]]:
    global _rows_cache
    from app.models import FactoryDiagramTitle

    result = await db.execute(
        select(FactoryDiagramTitle).order_by(
            FactoryDiagramTitle.diagram_kind,
            FactoryDiagramTitle.sort,
            FactoryDiagramTitle.id,
        )
    )
    rows = [row_to_dict(r) for r in result.scalars().all()]
    with _lock:
        _rows_cache = rows
    return list(rows)


async def migrate_seed_if_empty(db: AsyncSession) -> dict[str, int]:
    from app.models import FactoryDiagramTitle

    key_rows = await db.execute(
        select(FactoryDiagramTitle.diagram_kind, FactoryDiagramTitle.domain_id)
    )
    have = {(_norm(a), _norm(b) or WILDCARD) for a, b in key_rows.all()}
    inserted = 0
    for item in _seed_payload():
        kind = _norm(item.get("diagram_kind"))
        domain_id = _norm(item.get("domain_id")) or WILDCARD
        key = (kind, domain_id)
        if not kind or key in have:
            continue
        db.add(
            FactoryDiagramTitle(
                diagram_kind=kind,
                domain_id=domain_id,
                title_tpl=_norm(item.get("title_tpl")) or f"{{name}}{kind}",
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


def _pick_tpl(
    kind: str,
    domain: str,
    rows: list[dict[str, Any]],
) -> str | None:
    star = None
    named = None
    for r in rows:
        if _norm(r.get("source")) not in BAKE_SOURCES:
            continue
        if _norm(r.get("diagram_kind")) != kind:
            continue
        dom = _norm(r.get("domain_id")) or WILDCARD
        tpl = _norm(r.get("title_tpl"))
        if not tpl:
            continue
        if dom == domain:
            named = tpl
        elif dom == WILDCARD:
            star = tpl
    return named or star


def resolve_figure_title(
    kind: str,
    *,
    domain: str = WILDCARD,
    name: str = "",
    rows: list[dict[str, Any]] | None = None,
) -> str:
    kind = _norm(kind)
    name = _norm(name) or "系统"
    tpl = _pick_tpl(kind, domain, _rows_or_seed(rows))
    if not tpl:
        fallback = {
            "class": "{name}类图",
            "sequence": "{name}序列图",
            "activity": "{name}活动图",
            "er": "{name}E-R图",
            "architecture": "{name}逻辑架构图",
            "modules": "{name}功能模块图",
        }
        tpl = fallback.get(kind, "{name}图")
    from app.bake.schema.zh_copy import squeeze_cjk_alnum_spaces

    return squeeze_cjk_alnum_spaces(
        tpl.replace("{name}", name).replace("{domain}", domain)
    )


def figure_title_from_schema(
    schema: dict[str, Any] | None,
    kind: str,
    *,
    name: str = "",
    domain: str = WILDCARD,
) -> str:
    """出图消费：优先 schema.diagramTitleTemplates（bake 已解析），否则现场 resolve。"""
    kind = _norm(kind)
    name = _norm(name) or "系统"
    bag = (schema or {}).get("diagramTitleTemplates")
    if isinstance(bag, dict):
        hit = _norm(bag.get(kind))
        if hit:
            return hit
    dom = _norm(domain) or _norm((schema or {}).get("domain")) or WILDCARD
    return resolve_figure_title(kind, domain=dom, name=name)


def apply_diagram_titles_to_schema(
    schema: dict[str, Any],
    domain: str,
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    name = _norm(
        (schema.get("labels") or {}).get("systemName")
        if isinstance(schema.get("labels"), dict)
        else ""
    ) or _norm(schema.get("title")) or "系统"
    bag: dict[str, str] = {}
    for kind in sorted(DIAGRAM_KINDS):
        bag[kind] = resolve_figure_title(kind, domain=domain, name=name, rows=rows)
    schema["diagramTitleTemplates"] = bag
    return schema


def apply_diagram_titles_to_spec(
    spec: dict[str, Any],
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    sch = dict(spec.get("schema") or {})
    domain = _norm(spec.get("domain") or sch.get("domain") or "")
    sch = apply_diagram_titles_to_schema(sch, domain, rows=rows)
    out = dict(spec)
    out["schema"] = sch
    return out


def gap_report(*, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    data = _rows_or_seed(rows)
    have = {
        (_norm(r.get("diagram_kind")), _norm(r.get("domain_id")) or WILDCARD)
        for r in data
        if _norm(r.get("source")) in BAKE_SOURCES and _norm(r.get("diagram_kind"))
    }
    gaps = []
    for item in _seed_payload():
        key = (_norm(item.get("diagram_kind")), _norm(item.get("domain_id")) or WILDCARD)
        if key[0] and key not in have:
            gaps.append(
                {
                    "diagram_kind": key[0],
                    "domain_id": key[1],
                    "reason": "种子缺行",
                }
            )
    for kind in DIAGRAM_KINDS:
        if not any(k == kind for k, _ in have):
            gaps.append({"diagram_kind": kind, "domain_id": WILDCARD, "reason": "缺少图种模板"})
    return {"gap_count": len(gaps), "gaps": gaps}


async def upsert_entry(
    db: AsyncSession,
    *,
    diagram_kind: str,
    domain_id: str = WILDCARD,
    title_tpl: str,
    sort: int = 0,
    source: str = "manual",
) -> dict[str, Any]:
    from app.models import FactoryDiagramTitle

    diagram_kind = _norm(diagram_kind)
    domain_id = _norm(domain_id) or WILDCARD
    title_tpl = _norm(title_tpl)
    source = _norm(source) or "manual"
    if diagram_kind not in DIAGRAM_KINDS:
        raise ValueError(f"diagram_kind 须为 {', '.join(sorted(DIAGRAM_KINDS))}")
    if not title_tpl:
        raise ValueError("title_tpl 必填")
    if source not in SOURCES:
        source = "manual"
    result = await db.execute(
        select(FactoryDiagramTitle).where(
            FactoryDiagramTitle.diagram_kind == diagram_kind,
            FactoryDiagramTitle.domain_id == domain_id,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.title_tpl = title_tpl
        row.sort = int(sort or 0)
        row.source = source
        row.updated_at = datetime.utcnow()
    else:
        row = FactoryDiagramTitle(
            diagram_kind=diagram_kind,
            domain_id=domain_id,
            title_tpl=title_tpl,
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
    from app.models import FactoryDiagramTitle

    row = await db.get(FactoryDiagramTitle, entry_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    invalidate_cache()
    return True
