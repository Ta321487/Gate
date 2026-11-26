"""工厂测试账号卡维护 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.system_router import router
from app.core.database import get_db
from app.services import demo_accounts as da


class DemoAccountUpsert(BaseModel):
    domain_id: str = Field("*", description="DOM-* 或 *")
    role: str
    username: str
    password: str
    nickname_zh: str = ""
    login_hint_zh: str = Field("", max_length=256)
    sort: int = 0
    source: str = "manual"


@router.get("/system/demo-accounts/meta", summary="测试账号·选项")
async def demo_accounts_meta(db: AsyncSession = Depends(get_db)):
    from app.bake.catalog import DOMAINS

    await da.load_all_rows(db)
    roles = sorted(da.ROLES)
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
        "roles": roles,
        "role_options": [
            {"value": r, "label": da.ROLE_LABELS_ZH.get(r, r)} for r in roles
        ],
    }


@router.get("/system/demo-accounts", summary="测试账号列表")
async def list_demo_accounts(
    domain_id: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    rows = await da.load_all_rows(db)
    if domain_id is not None:
        rows = [r for r in rows if r["domain_id"] == domain_id]
    if role:
        rows = [r for r in rows if r["role"] == role]
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in (r["username"] or "").lower()
            or qq in (r["nickname_zh"] or "").lower()
            or qq in (r["login_hint_zh"] or "").lower()
        ]
    return {"ok": True, "total": len(rows), "items": rows}


@router.post("/system/demo-accounts/migrate", summary="迁入/补齐测试账号种子")
async def migrate_demo_accounts(db: AsyncSession = Depends(get_db)):
    stats = await da.migrate_seed_if_empty(db)
    return {"ok": True, **stats}


@router.get("/system/demo-accounts/gaps", summary="缺少的测试账号")
async def demo_accounts_gaps(
    scan_domains: bool = Query(False, description="扫 catalog 全部域具名账号"),
    db: AsyncSession = Depends(get_db),
):
    rows = await da.load_all_rows(db)
    seed_gaps = da.gap_report(rows=rows)
    if not scan_domains:
        return {"ok": True, **seed_gaps}
    dom_gaps = da.catalog_domain_gaps(rows=rows)
    merged = list(seed_gaps.get("gaps") or []) + list(dom_gaps.get("gaps") or [])
    return {
        "ok": True,
        "gap_count": len(merged),
        "gaps": merged,
        "seed_gap_count": seed_gaps.get("gap_count") or 0,
        "domain_gap_count": dom_gaps.get("gap_count") or 0,
        "domain_count": dom_gaps.get("domain_count") or 0,
    }


@router.put("/system/demo-accounts", summary="新增或更新测试账号")
async def upsert_demo_account(body: DemoAccountUpsert, db: AsyncSession = Depends(get_db)):
    try:
        row = await da.upsert_entry(
            db,
            domain_id=body.domain_id,
            role=body.role,
            username=body.username,
            password=body.password,
            nickname_zh=body.nickname_zh,
            login_hint_zh=body.login_hint_zh,
            sort=body.sort,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "item": row}


@router.delete("/system/demo-accounts/{entry_id}", summary="删除测试账号")
async def delete_demo_account(entry_id: int, db: AsyncSession = Depends(get_db)):
    ok = await da.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="未找到")
    return {"ok": True}
