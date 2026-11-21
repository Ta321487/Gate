"""工厂演示剧本维护 API。"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.system_router import router
from app.core.database import get_db
from app.services import demo_scripts as ds


class DemoScriptUpsert(BaseModel):
    domain_id: str
    skin_id: str = ""
    script_id: str = "default"
    step_no: int = Field(..., ge=1)
    role: str = "user"
    title_zh: str = Field(..., max_length=ds.TITLE_MAX)
    need_rows: dict[str, Any] = Field(default_factory=dict)
    seed_fragment_id: str = ""
    source: str = "manual"


@router.get("/system/demo-scripts/meta", summary="演示剧本·域选项")
async def demo_scripts_meta(db: AsyncSession = Depends(get_db)):
    from app.bake.catalog import DOMAINS

    rows = await ds.load_all_rows(db)
    scripts = sorted({r["script_id"] for r in rows if r.get("script_id")})
    skins = sorted({r.get("skin_id") for r in rows if r.get("skin_id")})
    domains = [
        {"id": k, "name": (DOMAINS.get(k) or {}).get("label") or k} for k in DOMAINS
    ]
    return {
        "ok": True,
        "domains": domains,
        "scripts": scripts or ["default"],
        "skins": skins,
        "roles": ["admin", "staff", "user"],
    }


@router.get("/system/demo-scripts", summary="演示剧本列表")
async def list_demo_scripts(
    domain_id: Optional[str] = Query(None),
    script_id: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    rows = await ds.load_all_rows(db)
    if domain_id is not None:
        rows = [r for r in rows if r["domain_id"] == domain_id]
    if script_id:
        rows = [r for r in rows if r["script_id"] == script_id]
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in (r["title_zh"] or "").lower()
            or qq in (r["domain_id"] or "").lower()
            or qq in (r["role"] or "").lower()
        ]
    return {"ok": True, "total": len(rows), "items": rows}


@router.post("/system/demo-scripts/migrate", summary="迁入/补齐演示剧本种子")
async def migrate_demo_scripts(db: AsyncSession = Depends(get_db)):
    stats = await ds.migrate_seed_if_empty(db)
    return {"ok": True, **stats}


@router.get("/system/demo-scripts/gaps", summary="域缺少 default 剧本")
async def demo_scripts_gaps(
    domain_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    rows = await ds.load_all_rows(db)
    report = ds.gap_report(domain_id, rows=rows)
    return {"ok": True, **report}


@router.put("/system/demo-scripts", summary="新增或更新剧本步")
async def upsert_demo_script(body: DemoScriptUpsert, db: AsyncSession = Depends(get_db)):
    try:
        item = await ds.upsert_entry(
            db,
            domain_id=body.domain_id,
            skin_id=body.skin_id,
            script_id=body.script_id,
            step_no=body.step_no,
            role=body.role,
            title_zh=body.title_zh,
            need_rows=body.need_rows,
            seed_fragment_id=body.seed_fragment_id,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True, "item": item}


@router.delete("/system/demo-scripts/{entry_id}", summary="删除剧本步")
async def delete_demo_script(entry_id: int, db: AsyncSession = Depends(get_db)):
    ok = await ds.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(404, "记录不存在")
    return {"ok": True}
