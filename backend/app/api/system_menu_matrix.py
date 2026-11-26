"""工厂岗位×菜单矩阵维护 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.system_router import router
from app.core.database import get_db
from app.services import menu_matrix as mm


class MenuMatrixUpsert(BaseModel):
    domain_id: str = Field("*", description="DOM-* 或 *")
    role: str
    menu_id: str
    label_zh: str = ""
    cap_id: str = ""
    always_on: bool = False
    sort: int = 0
    enabled: bool = True
    source: str = "manual"


@router.get("/system/menu-matrix/meta", summary="菜单矩阵·选项")
async def menu_matrix_meta(db: AsyncSession = Depends(get_db)):
    from app.bake.catalog import DOMAINS

    rows = await mm.load_all_rows(db)
    menu_ids = sorted({r["menu_id"] for r in rows if r.get("menu_id")})
    caps = sorted({r["cap_id"] for r in rows if r.get("cap_id")})
    try:
        from app.services import cap_cards as cc

        for card in cc._seed_payload():
            cid = (card.get("cap_id") or "").strip()
            if cid and cid not in caps:
                caps.append(cid)
            for mid in [
                x.strip()
                for x in str(card.get("menu_ids") or "").split(",")
                if x.strip()
            ]:
                if mid not in menu_ids:
                    menu_ids.append(mid)
        caps = sorted(set(caps))
        menu_ids = sorted(set(menu_ids))
    except Exception:  # noqa: BLE001
        pass
    domains = [
        {"id": "*", "name": "跨域壳默认"},
        *[
            {"id": k, "name": (DOMAINS.get(k) or {}).get("label") or k}
            for k in DOMAINS
        ],
    ]
    roles = sorted(mm.ROLES)
    return {
        "ok": True,
        "domains": domains,
        "roles": roles,
        "role_options": [
            {"value": r, "label": mm.ROLE_LABELS_ZH.get(r, r)} for r in roles
        ],
        "menu_ids": menu_ids,
        "caps": caps,
    }


@router.get("/system/menu-matrix", summary="菜单矩阵列表")
async def list_menu_matrix(
    domain_id: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    rows = await mm.load_all_rows(db)
    if domain_id is not None:
        rows = [r for r in rows if r["domain_id"] == domain_id]
    if role:
        rows = [r for r in rows if r["role"] == role]
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in (r["menu_id"] or "").lower()
            or qq in (r["label_zh"] or "").lower()
            or qq in (r["cap_id"] or "").lower()
        ]
    return {"ok": True, "total": len(rows), "items": rows}


@router.post("/system/menu-matrix/migrate", summary="迁入/补齐菜单矩阵种子")
async def migrate_menu_matrix(db: AsyncSession = Depends(get_db)):
    stats = await mm.migrate_seed_if_empty(db)
    return {"ok": True, **stats}


@router.get("/system/menu-matrix/gaps", summary="缺少的菜单矩阵行")
async def menu_matrix_gaps(
    scan_domains: bool = Query(False, description="扫 catalog 全部域具名常驻菜单"),
    db: AsyncSession = Depends(get_db),
):
    rows = await mm.load_all_rows(db)
    if scan_domains:
        return {"ok": True, **mm.catalog_domain_gaps(rows=rows)}
    return {"ok": True, **mm.gap_report(rows=rows)}


@router.put("/system/menu-matrix", summary="新增或更新矩阵行")
async def upsert_menu_matrix(body: MenuMatrixUpsert, db: AsyncSession = Depends(get_db)):
    try:
        row = await mm.upsert_entry(
            db,
            domain_id=body.domain_id,
            role=body.role,
            menu_id=body.menu_id,
            label_zh=body.label_zh,
            cap_id=body.cap_id,
            always_on=body.always_on,
            sort=body.sort,
            enabled=body.enabled,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "item": row}


@router.delete("/system/menu-matrix/{entry_id}", summary="删除矩阵行")
async def delete_menu_matrix(entry_id: int, db: AsyncSession = Depends(get_db)):
    ok = await mm.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="未找到")
    return {"ok": True}
