"""工厂业务规则参数维护 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.system_router import router
from app.core.database import get_db
from app.services import rule_params as rp


class RuleParamUpsert(BaseModel):
    domain_id: str = Field("*", description="DOM-* 或 *")
    rule_id: str
    label_zh: str = ""
    value_num: float = 0
    unit_zh: str = ""
    schema_key: str = ""
    sort: int = 0
    source: str = "manual"


@router.get("/system/rule-params/meta", summary="规则参数·选项")
async def rule_params_meta(db: AsyncSession = Depends(get_db)):
    from app.bake.catalog import DOMAINS

    rows = await rp.load_all_rows(db)
    rule_ids = sorted({r["rule_id"] for r in rows if r.get("rule_id")})
    for item in rp._seed_payload():
        rid = (item.get("rule_id") or "").strip()
        if rid and rid not in rule_ids:
            rule_ids.append(rid)
    rule_ids = sorted(set(rule_ids))
    schema_keys = sorted(
        set(rp.KNOWN_SCHEMA_KEYS)
        | {r.get("schema_key") for r in rows if r.get("schema_key")}
        | {
            (item.get("schema_key") or "").strip()
            for item in rp._seed_payload()
            if (item.get("schema_key") or "").strip()
        }
    )
    units = sorted(
        {
            r.get("unit_zh")
            for r in rows
            if r.get("unit_zh")
        }
        | {
            (item.get("unit_zh") or "").strip()
            for item in rp._seed_payload()
            if (item.get("unit_zh") or "").strip()
        }
    )
    domains = [
        {"id": "*", "name": "跨域壳默认"},
        *[
            {"id": k, "name": (DOMAINS.get(k) or {}).get("label") or k}
            for k in DOMAINS
        ],
    ]
    return {
        "ok": True,
        "domains": domains,
        "rule_ids": rule_ids,
        "schema_keys": schema_keys,
        "units": units,
        "schema_key_options": [{"value": k, "label": k} for k in schema_keys],
        "unit_options": [{"value": u, "label": u} for u in units],
    }


@router.get("/system/rule-params", summary="规则参数列表")
async def list_rule_params(
    domain_id: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    rows = await rp.load_all_rows(db)
    if domain_id is not None:
        rows = [r for r in rows if r["domain_id"] == domain_id]
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in (r["rule_id"] or "").lower()
            or qq in (r["label_zh"] or "").lower()
            or qq in (r["schema_key"] or "").lower()
        ]
    return {"ok": True, "total": len(rows), "items": rows}


@router.post("/system/rule-params/migrate", summary="迁入/补齐规则参数种子")
async def migrate_rule_params(db: AsyncSession = Depends(get_db)):
    stats = await rp.migrate_seed_if_empty(db)
    return {"ok": True, **stats}


@router.get("/system/rule-params/gaps", summary="缺少的规则参数")
async def rule_params_gaps(db: AsyncSession = Depends(get_db)):
    rows = await rp.load_all_rows(db)
    return {"ok": True, **rp.gap_report(rows=rows)}


@router.put("/system/rule-params", summary="新增或更新规则参数")
async def upsert_rule_param(body: RuleParamUpsert, db: AsyncSession = Depends(get_db)):
    try:
        row = await rp.upsert_entry(
            db,
            domain_id=body.domain_id,
            rule_id=body.rule_id,
            label_zh=body.label_zh,
            value_num=body.value_num,
            unit_zh=body.unit_zh,
            schema_key=body.schema_key,
            sort=body.sort,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "item": row}


@router.delete("/system/rule-params/{entry_id}", summary="删除规则参数")
async def delete_rule_param(entry_id: int, db: AsyncSession = Depends(get_db)):
    ok = await rp.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="未找到")
    return {"ok": True}
