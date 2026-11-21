"""工厂演示剧本台：持久化、只追加迁入、bake 注入 schema.demoScript。

真源：factory_demo_script。种子仅 asset_seeds/demo_scripts.json。
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SOURCES = frozenset({"migrated", "scan", "manual"})
BAKE_SOURCES = frozenset({"migrated", "scan", "manual"})
DEFAULT_SCRIPT = "default"
TITLE_MAX = 128

_lock = threading.RLock()
_rows_cache: list[dict[str, Any]] | None = None


def _norm(s: str | None) -> str:
    return (s or "").strip()


def _need_rows_val(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            obj = json.loads(raw)
            return dict(obj) if isinstance(obj, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "domain_id": _norm(row.domain_id),
        "skin_id": _norm(row.skin_id),
        "script_id": _norm(row.script_id) or DEFAULT_SCRIPT,
        "step_no": int(row.step_no or 1),
        "role": _norm(row.role) or "user",
        "title_zh": _norm(row.title_zh),
        "need_rows": _need_rows_val(row.need_rows),
        "seed_fragment_id": _norm(row.seed_fragment_id),
        "source": str(row.source or "manual"),
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    }


def invalidate_cache() -> None:
    global _rows_cache
    with _lock:
        _rows_cache = None


def _seed_payload() -> list[dict[str, Any]]:
    from app.services.asset_seeds import load_seed_json

    return list(load_seed_json("demo_scripts"))


def bootstrap_from_seed() -> None:
    rows = _seed_payload()
    with _lock:
        global _rows_cache
        _rows_cache = rows


async def load_all_rows(db: AsyncSession) -> list[dict[str, Any]]:
    """读库并刷新进程缓存。"""
    global _rows_cache
    from app.models import FactoryDemoScript

    result = await db.execute(
        select(FactoryDemoScript).order_by(
            FactoryDemoScript.domain_id,
            FactoryDemoScript.script_id,
            FactoryDemoScript.step_no,
            FactoryDemoScript.id,
        )
    )
    rows = [row_to_dict(r) for r in result.scalars().all()]
    with _lock:
        _rows_cache = rows
    return list(rows)


async def migrate_seed_if_empty(db: AsyncSession) -> dict[str, int]:
    """只追加：种子缺主键才 INSERT；已有行一律不改。"""
    from app.models import FactoryDemoScript

    key_rows = await db.execute(
        select(
            FactoryDemoScript.domain_id,
            FactoryDemoScript.skin_id,
            FactoryDemoScript.script_id,
            FactoryDemoScript.step_no,
        )
    )
    have = {
        (_norm(a), _norm(b), _norm(c) or DEFAULT_SCRIPT, int(d or 0))
        for a, b, c, d in key_rows.all()
    }
    inserted = 0
    for item in _seed_payload():
        tup = (
            _norm(item.get("domain_id")),
            _norm(item.get("skin_id")),
            _norm(item.get("script_id")) or DEFAULT_SCRIPT,
            int(item.get("step_no") or 0),
        )
        if not tup[0] or tup[3] < 1 or tup in have:
            continue
        db.add(
            FactoryDemoScript(
                domain_id=tup[0],
                skin_id=tup[1],
                script_id=tup[2],
                step_no=tup[3],
                role=_norm(item.get("role")) or "user",
                title_zh=_norm(item.get("title_zh"))[:TITLE_MAX],
                need_rows=_need_rows_val(item.get("need_rows")),
                seed_fragment_id=_norm(item.get("seed_fragment_id")),
                source=_norm(item.get("source")) or "migrated",
            )
        )
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


def list_script_steps(
    domain_id: str,
    *,
    script_id: str = DEFAULT_SCRIPT,
    skin_id: str = "",
    rows: list[dict[str, Any]] | None = None,
    strict: bool = False,
) -> list[dict[str, Any]]:
    """``strict=True`` 时按传入 ``rows`` 原样扫（含空列表），不回落种子。"""
    data = list(rows or []) if strict else _rows_or_seed(rows)
    domain_id = _norm(domain_id)
    script_id = _norm(script_id) or DEFAULT_SCRIPT
    skin_id = _norm(skin_id)
    hits: list[dict[str, Any]] = []
    for r in data:
        if _norm(r.get("source")) not in BAKE_SOURCES:
            continue
        if _norm(r.get("domain_id")) != domain_id:
            continue
        if (_norm(r.get("script_id")) or DEFAULT_SCRIPT) != script_id:
            continue
        sk = _norm(r.get("skin_id"))
        if sk and sk != skin_id:
            continue
        if not sk or sk == skin_id:
            hits.append(r)
    # 有皮专属步时优先皮；否则用空皮
    skinned = [h for h in hits if _norm(h.get("skin_id")) == skin_id and skin_id]
    use = skinned if skinned else [h for h in hits if not _norm(h.get("skin_id"))]
    use.sort(key=lambda x: int(x.get("step_no") or 0))
    return [
        {
            "step": int(h.get("step_no") or 0),
            "role": _norm(h.get("role")) or "user",
            "title": _norm(h.get("title_zh")),
            "needRows": _need_rows_val(h.get("need_rows")),
            "seedFragmentId": _norm(h.get("seed_fragment_id")),
        }
        for h in use
    ]


def apply_demo_script_to_schema(
    schema: dict[str, Any] | None,
    domain_id: str,
    *,
    skin_id: str = "",
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return schema or {}
    steps = list_script_steps(domain_id, skin_id=skin_id, rows=rows)
    out = schema
    out["demoScript"] = {
        "id": DEFAULT_SCRIPT,
        "steps": steps,
    }
    return out


def apply_demo_script_to_spec(
    spec: dict[str, Any],
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    out = dict(spec)
    sch = out.get("schema") if isinstance(out.get("schema"), dict) else {}
    domain = _norm(out.get("domain")) or _norm(sch.get("domain")) or ""
    if not domain:
        return out
    skin = _norm(out.get("skin")) or ""
    out["schema"] = apply_demo_script_to_schema(dict(sch), domain, skin_id=skin, rows=rows)
    return out


def gap_report(
    domain_id: str,
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """域缺少 default 剧本任一步 → 缺口。

    显式传入 ``rows``（含 ``[]``）时按传入集扫，不回落种子。
    """
    if rows is not None:
        steps = list_script_steps(domain_id, rows=rows, strict=True)
    else:
        steps = list_script_steps(domain_id)
    if steps:
        return {"gap_count": 0, "gaps": [], "domain_id": domain_id}
    return {
        "gap_count": 1,
        "gaps": [
            {
                "domain_id": domain_id,
                "script_id": DEFAULT_SCRIPT,
                "reason": "缺少 default 演示剧本",
            }
        ],
        "domain_id": domain_id,
    }


async def upsert_entry(
    db: AsyncSession,
    *,
    domain_id: str,
    skin_id: str = "",
    script_id: str = DEFAULT_SCRIPT,
    step_no: int,
    role: str = "user",
    title_zh: str,
    need_rows: dict[str, Any] | None = None,
    seed_fragment_id: str = "",
    source: str = "manual",
) -> dict[str, Any]:
    from app.models import FactoryDemoScript

    domain_id = _norm(domain_id)
    skin_id = _norm(skin_id)
    script_id = _norm(script_id) or DEFAULT_SCRIPT
    title_zh = _norm(title_zh)[:TITLE_MAX]
    role = _norm(role) or "user"
    source = _norm(source) or "manual"
    if not domain_id or step_no < 1 or not title_zh:
        raise ValueError("domain_id、step_no、title_zh 必填")
    if source not in SOURCES:
        source = "manual"
    result = await db.execute(
        select(FactoryDemoScript).where(
            FactoryDemoScript.domain_id == domain_id,
            FactoryDemoScript.skin_id == skin_id,
            FactoryDemoScript.script_id == script_id,
            FactoryDemoScript.step_no == step_no,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.role = role
        row.title_zh = title_zh
        row.need_rows = need_rows or {}
        row.seed_fragment_id = _norm(seed_fragment_id)
        row.source = source
        row.updated_at = datetime.utcnow()
    else:
        row = FactoryDemoScript(
            domain_id=domain_id,
            skin_id=skin_id,
            script_id=script_id,
            step_no=step_no,
            role=role,
            title_zh=title_zh,
            need_rows=need_rows or {},
            seed_fragment_id=_norm(seed_fragment_id),
            source=source,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    invalidate_cache()
    await load_all_rows(db)
    return row_to_dict(row)


async def delete_entry(db: AsyncSession, entry_id: int) -> bool:
    from app.models import FactoryDemoScript

    row = await db.get(FactoryDemoScript, entry_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    invalidate_cache()
    return True
