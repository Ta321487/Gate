"""工厂用例描述流程台：flow_kind × face → name/summary/flow。

真源：factory_usecase_flow。种子仅 asset_seeds/usecase_flows.json。
消费面：usecase_descriptions._flow_spec → resolve_flow_spec；禁止渲染器再内置事件流整句。
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
WILDCARD = "*"
FACES = frozenset({"*", "performance", "cinema"})
FACE_LABELS_ZH = {
    "*": "默认",
    "performance": "演艺票务",
    "cinema": "影院票务",
}

# 模板留花括号；出表时由 _ctx_for 填。说明须跨域通用，禁举单域角色/业务名。
PLACEHOLDERS: tuple[dict[str, str], ...] = (
    {"token": "{actor}", "zh": "本用例执行者（按端/岗位）"},
    {"token": "{user}", "zh": "用户端角色名"},
    {"token": "{admin}", "zh": "管理端角色名"},
    {"token": "{label}", "zh": "菜单中文名"},
    {"token": "{entity}", "zh": "主业务对象名"},
    {"token": "{ticket_stem}", "zh": "单据短名（由菜单名收短）"},
    {"token": "{reserve_stem}", "zh": "预约对象短名"},
    {"token": "{app}", "zh": "系统名"},
)

_lock = threading.RLock()
_rows_cache: list[dict[str, Any]] | None = None


def _norm(s: str | None) -> str:
    return (s or "").strip()


def _flow_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            return [line.strip() for line in raw.splitlines() if line.strip()]
    return []


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "flow_kind": _norm(row.flow_kind),
        "face": _norm(row.face) or WILDCARD,
        "name_tpl": _norm(row.name_tpl),
        "summary_tpl": _norm(row.summary_tpl),
        "flow": _flow_list(row.flow_json),
        "sort": int(row.sort or 0),
        "source": str(row.source or "manual"),
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    }


def invalidate_cache() -> None:
    global _rows_cache
    with _lock:
        _rows_cache = None


def _seed_payload() -> list[dict[str, Any]]:
    from app.services.asset_seeds import load_seed_json

    # 开发中改种子 JSON 后须清缓存，避免旧行占坑
    load_seed_json.cache_clear()
    out: list[dict[str, Any]] = []
    for item in load_seed_json("usecase_flows"):
        out.append(
            {
                "flow_kind": _norm(item.get("flow_kind")),
                "face": _norm(item.get("face")) or WILDCARD,
                "name_tpl": _norm(item.get("name_tpl")),
                "summary_tpl": _norm(item.get("summary_tpl")),
                "flow": _flow_list(item.get("flow")),
                "sort": int(item.get("sort") or 0),
                "source": _norm(item.get("source")) or "migrated",
            }
        )
    return out


def bootstrap_from_seed() -> None:
    rows = _seed_payload()
    with _lock:
        global _rows_cache
        _rows_cache = rows


async def load_all_rows(db: AsyncSession) -> list[dict[str, Any]]:
    global _rows_cache
    from app.models import FactoryUsecaseFlow

    result = await db.execute(
        select(FactoryUsecaseFlow).order_by(
            FactoryUsecaseFlow.sort,
            FactoryUsecaseFlow.flow_kind,
            FactoryUsecaseFlow.face,
            FactoryUsecaseFlow.id,
        )
    )
    rows = [row_to_dict(r) for r in result.scalars().all()]
    with _lock:
        _rows_cache = rows
    return list(rows)


async def migrate_seed_if_empty(db: AsyncSession) -> dict[str, int]:
    from app.models import FactoryUsecaseFlow

    key_rows = await db.execute(
        select(FactoryUsecaseFlow.flow_kind, FactoryUsecaseFlow.face)
    )
    have = {(_norm(a), _norm(b) or WILDCARD) for a, b in key_rows.all()}
    inserted = 0
    for item in _seed_payload():
        kind = _norm(item.get("flow_kind"))
        face = _norm(item.get("face")) or WILDCARD
        key = (kind, face)
        if not kind or key in have:
            continue
        db.add(
            FactoryUsecaseFlow(
                flow_kind=kind,
                face=face,
                name_tpl=_norm(item.get("name_tpl")) or "{actor}使用{label}",
                summary_tpl=_norm(item.get("summary_tpl")) or "{actor}打开「{label}」。",
                flow_json=list(item.get("flow") or []),
                sort=int(item.get("sort") or 0),
                source=_norm(item.get("source")) or "migrated",
            )
        )
        inserted += 1
        have.add(key)
    if inserted:
        await db.commit()
    invalidate_cache()
    rows = await load_all_rows(db)
    return {"inserted": inserted, "total": len(rows)}


def _rows_or_seed(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    data = rows
    if data is None:
        with _lock:
            data = list(_rows_cache) if _rows_cache is not None else None
    if not data:
        return _seed_payload()
    return list(data)


def _pick_row(
    kind: str,
    face: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    star = None
    named = None
    for r in rows:
        if _norm(r.get("source")) not in BAKE_SOURCES:
            continue
        if _norm(r.get("flow_kind")) != kind:
            continue
        f = _norm(r.get("face")) or WILDCARD
        if f == face:
            named = r
        elif f == WILDCARD:
            star = r
    return named or star


def resolve_flow_spec(
    kind: str,
    *,
    face: str | None = None,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """返回 name/summary/flow 模板；未知 kind 回落 open；无台则种子。"""
    kind = _norm(kind) or "open"
    face_n = _norm(face) or WILDCARD
    if face_n not in FACES:
        face_n = WILDCARD
    data = _rows_or_seed(rows)
    hit = _pick_row(kind, face_n, data)
    if not hit and kind != "open":
        hit = _pick_row("open", WILDCARD, data)
    if not hit:
        return {
            "name": "{actor}使用{label}",
            "summary": "{actor}打开「{label}」并完成页面主操作。",
            "flow": [
                "{actor}登录成功后进入系统，点击「{label}」",
                "系统转至「{label}」界面",
                "{actor}查看页面主列表或主表单并完成可用操作",
                "系统按页面实现反馈操作结果",
            ],
        }
    return {
        "name": _norm(hit.get("name_tpl")) or "{actor}使用{label}",
        "summary": _norm(hit.get("summary_tpl")) or "{actor}打开「{label}」。",
        "flow": list(_flow_list(hit.get("flow"))),
    }


def seed_kinds() -> set[str]:
    return {
        _norm(r.get("flow_kind"))
        for r in _seed_payload()
        if _norm(r.get("flow_kind")) and (_norm(r.get("face")) or WILDCARD) == WILDCARD
    }


def kinds_required_by_schema(schema: dict[str, Any] | None) -> set[str]:
    """从交付 menus 推导用例描述所需 flow_kind（含登录；与 _case_kind 同口径）。"""
    from app.bake.schema.modules import _SKIP_MENU_KEYS
    from app.bake.schema.usecase_descriptions import _case_kind

    need: set[str] = {"auth_login", "open"}
    menus = (schema or {}).get("menus") if isinstance((schema or {}).get("menus"), dict) else {}
    for side in ("user", "admin", "staff"):
        for raw in menus.get(side) or []:
            if not isinstance(raw, dict):
                continue
            key = _norm(raw.get("key"))
            if not key or key in _SKIP_MENU_KEYS:
                continue
            side_n = "admin" if side == "staff" else side
            need.add(_case_kind(key, side_n))
    return need


def catalog_domain_gaps(
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """扫 catalog 全部 DOM-*：菜单推导出的 kind 须有 face=* 行。"""
    from app.bake import domain_schema as ds
    from app.bake.catalog import DOMAINS

    data = _rows_or_seed(rows)
    have_star = {
        _norm(r.get("flow_kind"))
        for r in data
        if _norm(r.get("source")) in BAKE_SOURCES
        and _norm(r.get("flow_kind"))
        and (_norm(r.get("face")) or WILDCARD) == WILDCARD
    }
    gaps: list[dict[str, Any]] = []
    for dom in sorted(DOMAINS):
        sch = ds.build_domain_schema("用例流程缺口审计", dom)
        for kind in sorted(kinds_required_by_schema(sch)):
            if kind not in have_star:
                gaps.append(
                    {
                        "flow_kind": kind,
                        "face": WILDCARD,
                        "domain_id": dom,
                        "reason": "域菜单缺默认流程",
                    }
                )
    return {"gap_count": len(gaps), "gaps": gaps, "domain_count": len(DOMAINS)}


def gap_report(*, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    data = _rows_or_seed(rows)
    have = {
        (_norm(r.get("flow_kind")), _norm(r.get("face")) or WILDCARD)
        for r in data
        if _norm(r.get("source")) in BAKE_SOURCES and _norm(r.get("flow_kind"))
    }
    gaps = []
    for item in _seed_payload():
        key = (_norm(item.get("flow_kind")), _norm(item.get("face")) or WILDCARD)
        if key[0] and key not in have:
            gaps.append(
                {
                    "flow_kind": key[0],
                    "face": key[1],
                    "reason": "种子缺行",
                }
            )
    for kind in seed_kinds():
        if (kind, WILDCARD) not in have:
            gaps.append(
                {"flow_kind": kind, "face": WILDCARD, "reason": "缺少默认流程"}
            )
    # 去重
    seen: set[tuple[str, str]] = set()
    uniq = []
    for g in gaps:
        k = (g["flow_kind"], g["face"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(g)
    return {"gap_count": len(uniq), "gaps": uniq}


async def upsert_entry(
    db: AsyncSession,
    *,
    flow_kind: str,
    face: str = WILDCARD,
    name_tpl: str,
    summary_tpl: str,
    flow: list[str] | None = None,
    sort: int = 0,
    source: str = "manual",
) -> dict[str, Any]:
    from app.models import FactoryUsecaseFlow

    flow_kind = _norm(flow_kind)
    face = _norm(face) or WILDCARD
    name_tpl = _norm(name_tpl)
    summary_tpl = _norm(summary_tpl)
    source = _norm(source) or "manual"
    steps = _flow_list(flow)
    if not flow_kind:
        raise ValueError("flow_kind 必填")
    if face not in FACES:
        raise ValueError(f"face 须为 {', '.join(sorted(FACES))}")
    if not name_tpl:
        raise ValueError("name_tpl 必填")
    if not summary_tpl:
        raise ValueError("summary_tpl 必填")
    if source not in SOURCES:
        source = "manual"
    result = await db.execute(
        select(FactoryUsecaseFlow).where(
            FactoryUsecaseFlow.flow_kind == flow_kind,
            FactoryUsecaseFlow.face == face,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.name_tpl = name_tpl
        row.summary_tpl = summary_tpl
        row.flow_json = steps
        row.sort = int(sort or 0)
        row.source = source
        row.updated_at = datetime.utcnow()
    else:
        row = FactoryUsecaseFlow(
            flow_kind=flow_kind,
            face=face,
            name_tpl=name_tpl,
            summary_tpl=summary_tpl,
            flow_json=steps,
            sort=int(sort or 0),
            source=source,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    invalidate_cache()
    await load_all_rows(db)
    return row_to_dict(row)


async def delete_entry(db: AsyncSession, entry_id: int) -> bool:
    from app.models import FactoryUsecaseFlow

    row = await db.get(FactoryUsecaseFlow, entry_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    invalidate_cache()
    return True
