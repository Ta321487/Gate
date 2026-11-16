"""工厂词表维护 API。"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.system_router import router
from app.core.database import get_db
from app.services import zh_lexicon as zl


class ZhLexUpsert(BaseModel):
    kind: str = Field(..., description="column|table|stem|table_part")
    key_name: str
    zh: str = Field(..., max_length=zl.ZH_MAX_LEN, description=f"中文，最多 {zl.ZH_MAX_LEN} 字")
    domain: str = ""
    skin: str = ""
    table_name: str = ""
    source: str = "manual"


@router.get("/system/zh-lexicon/meta", summary="词表维护·域皮下拉选项")
async def zh_lexicon_meta(db: AsyncSession = Depends(get_db)):
    """域来自 catalog；皮 = 域 flavor + 词表里已有 skin；表名取自扫缺口命中。"""
    from app.bake.catalog import DOMAINS
    from app.bake.domain_skin import _DOMAIN_FLAVOR

    rows = await zl.load_all_rows(db)
    skins_seen: set[str] = set()
    tables_by_domain: dict[str, set[str]] = {}
    for r in rows:
        if r.get("skin"):
            skins_seen.add(str(r["skin"]))
        if r.get("table_name"):
            tables_by_domain.setdefault(str(r.get("domain") or ""), set()).add(
                str(r["table_name"])
            )
    for hit in zl.scan_sql_columns():
        if hit.skin:
            skins_seen.add(hit.skin)
        if hit.table_name:
            tables_by_domain.setdefault(hit.domain or "", set()).add(hit.table_name)

    skins_by_domain: dict[str, list[str]] = {}
    for dom, flavor in _DOMAIN_FLAVOR.items():
        skins_by_domain.setdefault(dom, [])
        if flavor and flavor not in skins_by_domain[dom]:
            skins_by_domain[dom].append(flavor)
    for r in rows:
        dom = str(r.get("domain") or "")
        sk = str(r.get("skin") or "")
        if dom and sk:
            skins_by_domain.setdefault(dom, [])
            if sk not in skins_by_domain[dom]:
                skins_by_domain[dom].append(sk)

    domains = [
        {"id": k, "name": (DOMAINS.get(k) or {}).get("label") or k}
        for k in DOMAINS
    ]
    return {
        "ok": True,
        "domains": domains,
        "skins": sorted(skins_seen),
        "skins_by_domain": {k: sorted(v) for k, v in skins_by_domain.items()},
        "tables_by_domain": {k: sorted(v) for k, v in tables_by_domain.items()},
    }


@router.get("/system/zh-lexicon", summary="词表列表")
async def list_zh_lexicon(
    kind: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    skin: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="key 或中文模糊"),
    db: AsyncSession = Depends(get_db),
):
    rows = await zl.load_all_rows(db)
    if kind:
        rows = [r for r in rows if r["kind"] == kind]
    if domain is not None:
        rows = [r for r in rows if r["domain"] == domain]
    if skin is not None:
        rows = [r for r in rows if r["skin"] == skin]
    if q:
        qq = q.strip().lower()
        rows = [
            r
            for r in rows
            if qq in (r["key_name"] or "").lower() or qq in (r["zh"] or "")
        ]
    return {"ok": True, "total": len(rows), "items": rows}


@router.post("/system/zh-lexicon/migrate", summary="迁入/补齐种子词表")
async def migrate_zh_lexicon(db: AsyncSession = Depends(get_db)):
    stats = await zl.migrate_seed_if_empty(db)
    return {"ok": True, **stats}


@router.get("/system/zh-lexicon/gaps", summary="相对全量 SQL 扫的词表缺口")
async def zh_lexicon_gaps(db: AsyncSession = Depends(get_db)):
    rows = await zl.load_all_rows(db)
    report = zl.gap_report(rows)
    return {"ok": True, **report}


@router.put("/system/zh-lexicon", summary="新增或更新词条")
async def upsert_zh_lexicon(body: ZhLexUpsert, db: AsyncSession = Depends(get_db)):
    try:
        item = await zl.upsert_entry(
            db,
            kind=body.kind,
            key_name=body.key_name,
            zh=body.zh,
            domain=body.domain,
            skin=body.skin,
            table_name=body.table_name,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    warnings = list(item.pop("warnings", []) or [])
    return {"ok": True, "item": item, "warnings": warnings}


@router.delete("/system/zh-lexicon/{entry_id}", summary="删除词条")
async def delete_zh_lexicon(entry_id: int, db: AsyncSession = Depends(get_db)):
    ok = await zl.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(404, "词条不存在")
    return {"ok": True}


@router.get("/system/zh-lexicon/resolve", summary="解析单键中文（调试）")
async def resolve_zh_lexicon(
    kind: str = Query("column"),
    key_name: str = Query(...),
    domain: str = Query(""),
    skin: str = Query(""),
    table_name: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    rows = await zl.load_all_rows(db)
    zh = zl.resolve_zh(
        kind,
        key_name,
        domain=domain,
        skin=skin,
        table_name=table_name,
        rows=rows,
    )
    return {
        "ok": True,
        "kind": kind,
        "key_name": key_name,
        "domain": domain,
        "skin": skin,
        "table_name": table_name,
        "zh": zh,
    }
