"""工厂实体动作词维护 API（论文图内业务动词唯一词源）。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["实体动作词"])
from app.core.database import get_db
from app.services import diagram_verbs as dv


class DiagramVerbUpsert(BaseModel):
    entity_key: str = Field(..., description="实体键，如 order / ticket / review")
    verb_key: str = Field(..., description="动作键，如 ship / complete")
    action_zh: str = Field(..., max_length=32, description="中文动作，最多 32 字")
    domain_id: str = Field("*", description="DOM-* 或 *（跨域默认）")
    skin_id: str = ""
    source: str = "manual"


@router.get("/system/diagram-verbs/meta", summary="实体动作词·选项与句式")
async def diagram_verbs_meta(db: AsyncSession = Depends(get_db)):
    from app.bake.catalog import DOMAINS
    from app.services.asset_seeds import load_seed_json

    await dv.load_all_rows(db)
    domains = [
        {"id": "*", "name": "跨域壳默认"},
        *[{"id": k, "name": (DOMAINS.get(k) or {}).get("label") or k} for k in DOMAINS],
    ]
    return {
        "ok": True,
        "domains": domains,
        "verb_keys": dv.verb_keys(),
        "expect": dv.expect_map(),
        "flow": [dict(x) for x in load_seed_json("diagram_flow")],
    }


@router.get("/system/diagram-verbs", summary="实体动作词列表")
async def list_diagram_verbs(
    domain_id: Optional[str] = Query(None),
    entity_key: Optional[str] = Query(None),
    verb_key: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    rows = await dv.load_all_rows(db)
    if domain_id is not None:
        rows = [r for r in rows if r["domain_id"] == (domain_id or dv.WILDCARD)]
    if entity_key:
        rows = [r for r in rows if r["entity_key"] == entity_key]
    if verb_key:
        rows = [r for r in rows if r["verb_key"] == verb_key]
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in (r["action_zh"] or "").lower()
            or qq in (r["entity_key"] or "").lower()
            or qq in (r["verb_key"] or "").lower()
        ]
    return {"ok": True, "total": len(rows), "items": rows}


@router.post("/system/diagram-verbs/migrate", summary="迁入/补齐动作词种子")
async def migrate_diagram_verbs(db: AsyncSession = Depends(get_db)):
    stats = await dv.migrate_seed_if_empty(db)
    return {"ok": True, **stats}


@router.get("/system/diagram-verbs/gaps", summary="缺少的动作词")
async def diagram_verbs_gaps(
    domain_id: Optional[str] = Query(None, description="查单域；不传则按已有种子域扫"),
    scan_domains: bool = Query(False, description="扫 catalog 全部域 schema"),
    db: AsyncSession = Depends(get_db),
):
    rows = await dv.load_all_rows(db)
    if domain_id:
        return {"ok": True, **dv.domain_gaps(domain_id, rows=rows)}
    if scan_domains:
        return {"ok": True, **dv.catalog_domain_gaps(rows=rows)}
    return {"ok": True, **dv.gap_report(rows=rows)}


@router.get("/system/diagram-verbs/resolve", summary="解析单动作（调试）")
async def resolve_diagram_verb(
    entity_key: str = Query(...),
    verb_key: str = Query(...),
    domain_id: str = Query(dv.WILDCARD),
    skin_id: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    rows = await dv.load_all_rows(db)
    return {
        "ok": True,
        "entity_key": entity_key,
        "verb_key": verb_key,
        "domain_id": domain_id,
        "action_zh": dv.resolve_verb(
            entity_key, verb_key, domain=domain_id, skin=skin_id, rows=rows
        ),
    }


@router.put("/system/diagram-verbs", summary="新增或更新动作词")
async def upsert_diagram_verb(body: DiagramVerbUpsert, db: AsyncSession = Depends(get_db)):
    try:
        row = await dv.upsert_entry(
            db,
            domain_id=body.domain_id,
            skin_id=body.skin_id,
            entity_key=body.entity_key,
            verb_key=body.verb_key,
            action_zh=body.action_zh,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "item": row}


@router.delete("/system/diagram-verbs/{entry_id}", summary="删除动作词")
async def delete_diagram_verb(entry_id: int, db: AsyncSession = Depends(get_db)):
    ok = await dv.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="未找到")
    return {"ok": True}
