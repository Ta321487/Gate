"""工厂用例描述流程维护 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["用例流程"])
from app.core.database import get_db
from app.services import usecase_flows as uf


class UsecaseFlowUpsert(BaseModel):
    flow_kind: str
    face: str = Field("*", description="* | performance | cinema")
    name_tpl: str = Field(..., max_length=128)
    summary_tpl: str = Field(..., max_length=256)
    flow: list[str] = Field(default_factory=list)
    sort: int = 0
    source: str = "manual"


@router.get("/system/usecase-flows/meta", summary="用例流程·选项")
async def usecase_flows_meta(db: AsyncSession = Depends(get_db)):
    await uf.load_all_rows(db)
    kinds = sorted(uf.seed_kinds())
    faces = sorted(uf.FACES)
    return {
        "ok": True,
        "kinds": kinds,
        "kind_options": [{"value": k, "label": k} for k in kinds],
        "faces": faces,
        "face_options": [
            {"value": f, "label": uf.FACE_LABELS_ZH.get(f, f)} for f in faces
        ],
        "placeholders": [dict(x) for x in uf.PLACEHOLDERS],
    }


@router.get("/system/usecase-flows", summary="用例流程列表")
async def list_usecase_flows(
    flow_kind: Optional[str] = Query(None),
    face: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    rows = await uf.load_all_rows(db)
    if flow_kind:
        rows = [r for r in rows if r["flow_kind"] == flow_kind]
    if face is not None:
        rows = [r for r in rows if r["face"] == face]
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in (r["name_tpl"] or "").lower()
            or qq in (r["summary_tpl"] or "").lower()
            or qq in (r["flow_kind"] or "").lower()
            or any(qq in step.lower() for step in (r.get("flow") or []))
        ]
    return {"ok": True, "total": len(rows), "items": rows}


@router.post("/system/usecase-flows/migrate", summary="迁入/补齐用例流程种子")
async def migrate_usecase_flows(db: AsyncSession = Depends(get_db)):
    stats = await uf.migrate_seed_if_empty(db)
    return {"ok": True, **stats}


@router.get("/system/usecase-flows/gaps", summary="缺少的用例流程")
async def usecase_flows_gaps(
    scan_domains: bool = Query(False, description="扫 catalog 全部域菜单"),
    db: AsyncSession = Depends(get_db),
):
    rows = await uf.load_all_rows(db)
    seed_gaps = uf.gap_report(rows=rows)
    if not scan_domains:
        return {"ok": True, **seed_gaps}
    dom_gaps = uf.catalog_domain_gaps(rows=rows)
    merged = list(seed_gaps.get("gaps") or []) + list(dom_gaps.get("gaps") or [])
    return {
        "ok": True,
        "gap_count": len(merged),
        "gaps": merged,
        "seed_gap_count": seed_gaps.get("gap_count") or 0,
        "domain_gap_count": dom_gaps.get("gap_count") or 0,
        "domain_count": dom_gaps.get("domain_count") or 0,
    }


@router.put("/system/usecase-flows", summary="新增或更新用例流程")
async def upsert_usecase_flow(body: UsecaseFlowUpsert, db: AsyncSession = Depends(get_db)):
    try:
        row = await uf.upsert_entry(
            db,
            flow_kind=body.flow_kind,
            face=body.face,
            name_tpl=body.name_tpl,
            summary_tpl=body.summary_tpl,
            flow=body.flow,
            sort=body.sort,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "item": row}


@router.delete("/system/usecase-flows/{entry_id}", summary="删除用例流程")
async def delete_usecase_flow(entry_id: int, db: AsyncSession = Depends(get_db)):
    ok = await uf.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="未找到")
    return {"ok": True}
