"""工厂字典/枚举值维护 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.system_router import router
from app.core.database import get_db
from app.services import dict_values as dv


class DictValueUpsert(BaseModel):
    domain_id: str = Field("*", description="DOM-* 或 *")
    skin_id: str = ""
    dict_key: str = Field(..., description="如 refund_type / ticket_priority")
    value_code: str
    label_zh: str = Field(..., max_length=dv.ZH_MAX_LEN)
    sort: int = 0
    enabled: bool = True
    source: str = "manual"


@router.get("/system/dict-values/meta", summary="字典台·域/键选项")
async def dict_values_meta(db: AsyncSession = Depends(get_db)):
    from app.bake.catalog import DOMAINS

    rows = await dv.load_all_rows(db)
    keys = sorted({r["dict_key"] for r in rows if r.get("dict_key")})
    for pack in dv.EXPECTED_DICT_CODES.values():
        for k in pack:
            if k not in keys:
                keys.append(k)
    keys = sorted(set(keys))
    domains = [
        {"id": "*", "name": "跨域壳默认"},
        *[
            {"id": k, "name": (DOMAINS.get(k) or {}).get("label") or k}
            for k in DOMAINS
        ],
    ]
    skins = sorted({r.get("skin_id") for r in rows if r.get("skin_id")})
    return {
        "ok": True,
        "domains": domains,
        "dict_keys": keys,
        "skins": skins,
        "repair_domains": sorted(dv.REPAIR_DOMAINS),
    }


@router.get("/system/dict-values", summary="字典值列表")
async def list_dict_values(
    domain_id: Optional[str] = Query(None),
    dict_key: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="code 或中文模糊"),
    db: AsyncSession = Depends(get_db),
):
    rows = await dv.load_all_rows(db)
    if domain_id is not None:
        rows = [r for r in rows if r["domain_id"] == domain_id]
    if dict_key:
        rows = [r for r in rows if r["dict_key"] == dict_key]
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in (r["value_code"] or "").lower()
            or qq in (r["label_zh"] or "")
            or qq in (r["dict_key"] or "").lower()
        ]
    return {"ok": True, "total": len(rows), "items": rows}


@router.post("/system/dict-values/migrate", summary="迁入/补齐字典种子")
async def migrate_dict_values(db: AsyncSession = Depends(get_db)):
    stats = await dv.migrate_seed_if_empty(db)
    return {"ok": True, **stats}


@router.get("/system/dict-values/gaps", summary="相对期望码的字典缺口")
async def dict_values_gaps(
    domain_id: str = Query(..., description="如 DOM-SHOP / DOM-DORM"),
    skin_id: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    rows = await dv.load_all_rows(db)
    report = dv.gap_report(domain_id, skin_id=skin_id, rows=rows)
    return {"ok": True, **report}


@router.put("/system/dict-values", summary="新增或更新字典值")
async def upsert_dict_value(body: DictValueUpsert, db: AsyncSession = Depends(get_db)):
    try:
        item = await dv.upsert_entry(
            db,
            domain_id=body.domain_id,
            skin_id=body.skin_id,
            dict_key=body.dict_key,
            value_code=body.value_code,
            label_zh=body.label_zh,
            sort=body.sort,
            enabled=body.enabled,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True, "item": item}


@router.delete("/system/dict-values/{entry_id}", summary="删除字典值")
async def delete_dict_value(entry_id: int, db: AsyncSession = Depends(get_db)):
    ok = await dv.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(404, "词条不存在")
    return {"ok": True}


@router.get("/system/dict-values/resolve", summary="解析单值（调试）")
async def resolve_dict_value(
    domain_id: str = Query("*"),
    dict_key: str = Query(...),
    value_code: str = Query(...),
    skin_id: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    rows = await dv.load_all_rows(db)
    label = dv.resolve_label(
        domain_id, dict_key, value_code, skin_id=skin_id, rows=rows
    )
    opts = dv.list_dict_options(domain_id, dict_key, skin_id=skin_id, rows=rows)
    return {"ok": True, "label": label, "options": opts}
