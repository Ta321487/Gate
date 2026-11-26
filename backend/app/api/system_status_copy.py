"""工厂状态机话术维护 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.system_router import router
from app.core.database import get_db
from app.services import status_copy as sc


class StatusCopyUpsert(BaseModel):
    domain_id: str = Field("*", description="DOM-* 或 *")
    machine_id: str = Field(..., description="order|ticket|reservation|…")
    status_code: str
    label_zh: str = Field(..., max_length=sc.ZH_MAX_LEN)
    action_zh: str = Field("", max_length=sc.ZH_MAX_LEN)
    empty_zh: str = Field("", max_length=sc.EMPTY_MAX_LEN)
    for_roles: str = Field(sc.ROLES_DEFAULT)
    source: str = "manual"


@router.get("/system/status-copy/meta", summary="状态话术·域/机选项")
async def status_copy_meta(db: AsyncSession = Depends(get_db)):
    from app.bake.catalog import DOMAINS

    rows = await sc.load_all_rows(db)
    machines = sorted({r["machine_id"] for r in rows if r.get("machine_id")})
    for m in sc.MACHINE_ENTITY_KEY:
        if m not in machines:
            machines.append(m)
    machines = sorted(set(machines))
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
        "machines": machines,
        "machine_options": [
            {
                "value": m,
                "label": f"{sc.MACHINE_LABELS_ZH.get(m, m)}（{m}）",
            }
            for m in machines
        ],
        "machine_entity_key": dict(sc.MACHINE_ENTITY_KEY),
        "roles": ["admin", "staff", "user"],
    }


@router.get("/system/status-copy", summary="状态话术列表")
async def list_status_copy(
    domain_id: Optional[str] = Query(None),
    machine_id: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="status 或中文模糊"),
    db: AsyncSession = Depends(get_db),
):
    rows = await sc.load_all_rows(db)
    if domain_id is not None:
        rows = [r for r in rows if r["domain_id"] == domain_id]
    if machine_id:
        rows = [r for r in rows if r["machine_id"] == machine_id]
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in (r["status_code"] or "").lower()
            or qq in (r["label_zh"] or "")
            or qq in (r["action_zh"] or "")
        ]
    return {"ok": True, "total": len(rows), "items": rows}


@router.post("/system/status-copy/migrate", summary="迁入/补齐状态话术种子")
async def migrate_status_copy(db: AsyncSession = Depends(get_db)):
    stats = await sc.migrate_seed_if_empty(db)
    return {"ok": True, **stats}


@router.get("/system/status-copy/gaps", summary="相对域 schema 的状态缺口")
async def status_copy_gaps(
    domain_id: Optional[str] = Query(None, description="如 DOM-SHOP；与 scan_domains 二选一"),
    scan_domains: bool = Query(False, description="扫 catalog 全部域具名话术"),
    db: AsyncSession = Depends(get_db),
):
    from app.bake.domain_schema import build_domain_schema

    rows = await sc.load_all_rows(db)
    if scan_domains:
        return {"ok": True, **sc.catalog_domain_gaps(rows=rows)}
    if not domain_id:
        raise HTTPException(400, "请指定 domain_id，或打开 scan_domains 扫 68 域")
    # 用裸 builder（未注入台）看实体上有哪些 status；再对台查缺
    schema = build_domain_schema(f"状态话术缺口探针-{domain_id}", domain_id)
    report = sc.gap_report(domain_id, schema, rows=rows)
    return {"ok": True, **report}


@router.put("/system/status-copy", summary="新增或更新状态话术")
async def upsert_status_copy(body: StatusCopyUpsert, db: AsyncSession = Depends(get_db)):
    try:
        item = await sc.upsert_entry(
            db,
            domain_id=body.domain_id,
            machine_id=body.machine_id,
            status_code=body.status_code,
            label_zh=body.label_zh,
            action_zh=body.action_zh,
            empty_zh=body.empty_zh,
            for_roles=body.for_roles,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True, "item": item}


@router.delete("/system/status-copy/{entry_id}", summary="删除状态话术")
async def delete_status_copy(entry_id: int, db: AsyncSession = Depends(get_db)):
    ok = await sc.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(404, "词条不存在")
    return {"ok": True}


@router.get("/system/status-copy/resolve", summary="解析单状态（调试）")
async def resolve_status_copy(
    domain_id: str = Query("*"),
    machine_id: str = Query(...),
    status_code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    rows = await sc.load_all_rows(db)
    hit = sc.resolve_status(domain_id, machine_id, status_code, rows=rows)
    return {"ok": True, "hit": hit}
