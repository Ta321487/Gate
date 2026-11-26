"""工厂级实体动作词：论文图内业务动词的唯一词源。

真源：``factory_diagram_verb``；种子 ``asset_seeds/diagram_verbs.json``
（由 golden + 项目 ``domain.schema.json`` 的 ``entities.*.verbs`` 生成）。

优先级（与 status_copy / diagram_titles 同构）：
1. 项目 ``domain.schema.json`` 的 ``entities.<entity>.verbs``（随材料走）
2. 工厂表具名域行 ``domain_id=<DOM-*>``
3. 工厂表跨域默认行 ``domain_id='*'``
4. 都没有 → 返回空串：**调用方降级为技术骨架并报缺口**，不得自带业务词

句式骨架只在 ``asset_seeds/diagram_flow.json``（kind → 实体/动作/状态），
本模块只负责"查词 + 拼句"，不写任何业务名词。
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SOURCES = frozenset({"migrated", "scan", "manual", "draft"})
BAKE_SOURCES = frozenset({"migrated", "scan", "manual"})
WILDCARD = "*"

_lock = threading.RLock()
_rows_cache: list[dict[str, Any]] | None = None


def _norm(s: Any) -> str:
    return str(s or "").strip()


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "domain_id": _norm(row.domain_id) or WILDCARD,
        "skin_id": _norm(row.skin_id),
        "entity_key": _norm(row.entity_key),
        "verb_key": _norm(row.verb_key),
        "action_zh": _norm(row.action_zh),
        "source": str(row.source or "manual"),
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    }


def invalidate_cache() -> None:
    global _rows_cache
    with _lock:
        _rows_cache = None


def _seed_payload() -> list[dict[str, Any]]:
    from app.services.asset_seeds import load_seed_json

    return list(load_seed_json("diagram_verbs"))


def verb_keys() -> list[dict[str, str]]:
    from app.services.asset_seeds import load_seed_json

    return [dict(x) for x in load_seed_json("diagram_verb_meta")]


def verb_key_names() -> set[str]:
    return {_norm(x.get("verb_key")) for x in verb_keys() if _norm(x.get("verb_key"))}


def expect_map() -> dict[str, list[str]]:
    from app.services.asset_seeds import load_seed_json

    out: dict[str, list[str]] = {}
    for item in load_seed_json("diagram_verb_expect"):
        ek = _norm(item.get("entity_key"))
        req = [str(v) for v in (item.get("required_verbs") or []) if _norm(v)]
        if ek and req:
            out[ek] = req
    return out


def _seed_flow() -> list[dict[str, Any]]:
    from app.services.asset_seeds import load_seed_json

    return [dict(x) for x in load_seed_json("diagram_flow")]


def flow_for_kind(kind: str) -> dict[str, Any] | None:
    """kind → 句式形状（实体 / 动作 / 前后状态）；查不到则 None。"""
    kind = _norm(kind).lower()
    for item in _seed_flow():
        if _norm(item.get("kind")).lower() == kind:
            return dict(item)
    return None


def domain_entities(
    domain: str,
    *,
    schema: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
) -> list[str]:
    domain = _norm(domain) or WILDCARD
    ents = (schema or {}).get("entities")
    if isinstance(ents, dict) and ents:
        return sorted(_norm(k) for k in ents if _norm(k))
    from app.services.asset_seeds import load_seed_json

    for item in load_seed_json("diagram_verb_entities"):
        if _norm(item.get("domain_id")) == domain:
            keys = [_norm(k) for k in (item.get("entity_keys") or []) if _norm(k)]
            if keys:
                return sorted(keys)
    have = {
        _norm(r.get("entity_key"))
        for r in _rows_or_seed(rows)
        if _norm(r.get("domain_id")) == domain
    }
    return sorted(k for k in have if k)


def bootstrap_from_seed() -> None:
    with _lock:
        global _rows_cache
        _rows_cache = _seed_payload()


async def load_all_rows(db: AsyncSession) -> list[dict[str, Any]]:
    global _rows_cache
    from app.models import FactoryDiagramVerb

    result = await db.execute(
        select(FactoryDiagramVerb).order_by(
            FactoryDiagramVerb.domain_id,
            FactoryDiagramVerb.entity_key,
            FactoryDiagramVerb.verb_key,
            FactoryDiagramVerb.id,
        )
    )
    rows = [row_to_dict(r) for r in result.scalars().all()]
    with _lock:
        _rows_cache = rows
    return list(rows)


async def migrate_seed_if_empty(db: AsyncSession) -> dict[str, int]:
    """只追加缺主键；已有行永不被种子覆盖。"""
    from app.models import FactoryDiagramVerb

    key_rows = await db.execute(
        select(
            FactoryDiagramVerb.domain_id,
            FactoryDiagramVerb.skin_id,
            FactoryDiagramVerb.entity_key,
            FactoryDiagramVerb.verb_key,
        )
    )
    have = {(_norm(a) or WILDCARD, _norm(b), _norm(c), _norm(d)) for a, b, c, d in key_rows.all()}
    inserted = 0
    for item in _seed_payload():
        domain = _norm(item.get("domain_id")) or WILDCARD
        skin = _norm(item.get("skin_id"))
        entity = _norm(item.get("entity_key"))
        verb = _norm(item.get("verb_key"))
        zh = _norm(item.get("action_zh"))
        if not (entity and verb and zh):
            continue
        key = (domain, skin, entity, verb)
        if key in have:
            continue
        db.add(
            FactoryDiagramVerb(
                domain_id=domain,
                skin_id=skin,
                entity_key=entity,
                verb_key=verb,
                action_zh=zh,
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
    """与 diagram_titles 同构：显式空 / 缓存空 → 回退种子，避免未迁入时丢跨域默认词。"""
    data = rows
    if data is None:
        with _lock:
            data = list(_rows_cache) if _rows_cache is not None else None
    if not data:
        return _seed_payload()
    return list(data)


def _factory_verb(
    entity_key: str,
    verb_key: str,
    *,
    domain: str,
    skin: str,
    rows: list[dict[str, Any]],
) -> str:
    named = ""
    star = ""
    for r in rows:
        if _norm(r.get("source")) not in BAKE_SOURCES:
            continue
        if _norm(r.get("entity_key")) != entity_key:
            continue
        if _norm(r.get("verb_key")) != verb_key:
            continue
        rdom = _norm(r.get("domain_id")) or WILDCARD
        rskin = _norm(r.get("skin_id"))
        if rskin and skin and rskin != skin:
            continue
        zh = _norm(r.get("action_zh"))
        if not zh:
            continue
        if rdom == domain:
            named = zh
        elif rdom == WILDCARD:
            star = zh
    return named or star


def _schema_verb(schema: dict[str, Any] | None, entity_key: str, verb_key: str) -> str:
    ents = (schema or {}).get("entities")
    if not isinstance(ents, dict):
        return ""
    ent = ents.get(entity_key)
    if not isinstance(ent, dict):
        return ""
    verbs = ent.get("verbs")
    if not isinstance(verbs, dict):
        return ""
    return _norm(verbs.get(verb_key))


def resolve_verb(
    entity_key: str,
    verb_key: str,
    *,
    domain: str = WILDCARD,
    skin: str = "",
    schema: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
) -> str:
    entity_key = _norm(entity_key)
    verb_key = _norm(verb_key)
    if not (entity_key and verb_key):
        return ""
    hit = _schema_verb(schema, entity_key, verb_key)
    if hit:
        return hit
    return _factory_verb(
        entity_key,
        verb_key,
        domain=_norm(domain) or WILDCARD,
        skin=_norm(skin),
        rows=_rows_or_seed(rows),
    )


def verbs_for_entity(
    entity_key: str,
    *,
    domain: str = WILDCARD,
    skin: str = "",
    schema: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    entity_key = _norm(entity_key)
    out: dict[str, str] = {}
    data = _rows_or_seed(rows)
    for vk in sorted(verb_key_names()):
        zh = resolve_verb(entity_key, vk, domain=domain, skin=skin, schema=schema, rows=data)
        if zh:
            out[vk] = zh
    return out


def entity_label(schema: dict[str, Any] | None, entity_key: str, *, fallback: str = "") -> str:
    ents = (schema or {}).get("entities")
    if isinstance(ents, dict):
        ent = ents.get(entity_key)
        if isinstance(ent, dict):
            lab = _norm(ent.get("label")) or _norm(ent.get("labelPlural"))
            if lab:
                return lab
    return _norm(fallback)


def entity_state(schema: dict[str, Any] | None, entity_key: str, state_key: str) -> str:
    ents = (schema or {}).get("entities")
    if not isinstance(ents, dict):
        return ""
    ent = ents.get(entity_key)
    if not isinstance(ent, dict):
        return ""
    states = ent.get("states")
    if not isinstance(states, dict):
        return ""
    return _norm(states.get(state_key))


def safe_label(label: str) -> str:
    """容器类名词（购物车/收藏夹/文件夹）不拼「提交购物车」，改说「记录」。

    「订单」「清单」这类业务对象照常保留：它们是材料名词，不是容器。
    """
    s = _norm(label)
    if not s:
        return "记录"
    if s.endswith(("车", "篮", "夹", "箱")) and len(s) >= 2:
        return "记录"
    if s.endswith(("购物车", "购物篮", "收藏夹", "文件夹", "回收站")):
        return "记录"
    return s


def entity_for_menu(
    schema: dict[str, Any] | None,
    *,
    menu_key: str = "",
    menu_label: str = "",
) -> str:
    """按菜单键/菜单名在材料实体里定位业务实体（open 类菜单用）。"""
    ents = (schema or {}).get("entities")
    if not isinstance(ents, dict) or not ents:
        return ""
    keys = [_norm(k) for k in ents if _norm(k)]
    tokens = [t for t in _norm(menu_key).lower().split("_") if t]
    for tok in tokens:
        for k in keys:
            if k.lower() == tok or tok.startswith(k.lower()) or k.lower().startswith(tok):
                return k
    lab = _norm(menu_label)
    if lab:
        for k, v in ents.items():
            if not isinstance(v, dict):
                continue
            el = _norm(v.get("label")) or _norm(v.get("labelPlural"))
            if el and (el in lab or lab in el):
                return _norm(k)
    return ""


def material_phases(
    kind: str,
    schema: dict[str, Any] | None,
    *,
    domain: str = WILDCARD,
    skin: str = "",
    menu_key: str = "",
    menu_label: str = "",
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, str] | None:
    """按材料词拼出五相位。

    - 无句式形状 / 无实体名可落 → None（调用方回退中性兜底）
    - 有实体但缺动作词 → 仍返回中性骨架（缺口由 flow_gap 报出），绝不借别域业务句
    """
    flow = flow_for_kind(kind)
    if not flow:
        return None
    entity = _norm(flow.get("entity_key"))
    verb_key = _norm(flow.get("verb_key"))
    if not entity:
        entity = entity_for_menu(
            schema, menu_key=_norm(menu_key), menu_label=_norm(menu_label)
        )
    if not entity and not _norm(menu_label) and not _norm(menu_key):
        return None
    label = entity_label(schema, entity, fallback=menu_label or menu_key)
    if not label:
        return None
    if not verb_key:
        # 展示/办理类菜单（open）：只用材料菜单名 + 中性技术动词，不编业务步骤
        return {
            "select": f"进入{label}",
            "confirm": f"选择{label}",
            "submit": f"提交{label}操作",
            "save": f"保存{label}结果",
            "ok": f"{label}操作完成",
        }
    verb = resolve_verb(
        entity, verb_key, domain=domain, skin=skin, schema=schema, rows=rows
    )
    from_state = entity_state(schema, entity, _norm(flow.get("from_state")))
    to_state = entity_state(schema, entity, _norm(flow.get("to_state")))
    select = f"选择{from_state}{label}" if from_state else f"查看{label}"
    save = f"更新{label}为{to_state}" if to_state else f"更新{label}状态"
    if verb:
        return {
            "select": select,
            "confirm": verb,
            "submit": f"发起{verb}",
            "save": save,
            "ok": f"{verb}成功",
        }
    # 材料缺动作词：只出中性骨架，绝不借用别域业务句（缺口由 flow_gap 报出）
    return {
        "select": f"查看{label}",
        "confirm": f"查看{label}详情",
        "submit": "提交变更",
        "save": f"更新{label}状态",
        "ok": f"{label}操作成功",
    }


def flow_gap(
    kind: str,
    schema: dict[str, Any] | None,
    *,
    domain: str = WILDCARD,
    skin: str = "",
    menu_key: str = "",
    menu_label: str = "",
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, str] | None:
    """该 kind 缺哪个词（None = 不缺 / 未登记形状）。"""
    flow = flow_for_kind(kind)
    if not flow:
        return None
    entity = _norm(flow.get("entity_key"))
    verb_key = _norm(flow.get("verb_key"))
    if not verb_key:
        return None
    if not entity:
        entity = entity_for_menu(
            schema, menu_key=_norm(menu_key), menu_label=_norm(menu_label)
        )
    label = entity_label(schema, entity, fallback=menu_label or menu_key)
    verb = resolve_verb(entity, verb_key, domain=domain, skin=skin, schema=schema, rows=rows)
    if not label:
        return {
            "kind": _norm(kind),
            "entity_key": entity,
            "reason": f"材料缺实体名 entities.{entity}.label",
        }
    if not verb:
        return {
            "kind": _norm(kind),
            "entity_key": entity,
            "verb_key": verb_key,
            "reason": f"材料缺动作词 entities.{entity}.verbs.{verb_key}",
        }
    return None


def domain_gaps(
    domain: str,
    *,
    schema: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    domain = _norm(domain) or WILDCARD
    data = _rows_or_seed(rows)
    present = set(domain_entities(domain, schema=schema, rows=data))
    gaps: list[dict[str, str]] = []
    for entity_key, required in expect_map().items():
        if present and entity_key not in present:
            continue
        for verb_key in required:
            if not resolve_verb(entity_key, verb_key, domain=domain, schema=schema, rows=data):
                gaps.append(
                    {
                        "entity_key": entity_key,
                        "verb_key": verb_key,
                        "reason": "材料与工厂均缺词，图内会降级为骨架句",
                    }
                )
    return {"domain_id": domain, "gap_count": len(gaps), "gaps": gaps}


def gap_report(
    *,
    rows: list[dict[str, Any]] | None = None,
    domains: list[str] | None = None,
    schemas: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    data = _rows_or_seed(rows)
    if domains is None:
        domains = sorted({_norm(r.get("domain_id")) for r in data if _norm(r.get("domain_id"))})
    out: list[dict[str, Any]] = []
    for dom in domains:
        sch = (schemas or {}).get(dom)
        rep = domain_gaps(dom, schema=sch, rows=data)
        if rep["gap_count"]:
            out.append(rep)
    return {"domains": len(domains), "gap_domains": len(out), "reports": out}


def catalog_domain_gaps(*, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """扫 catalog 全部 DOM-*：按域 schema 实体对 expect_map 查缺词。"""
    from app.bake import domain_schema as ds
    from app.bake.catalog import DOMAINS
    from app.services import demo_accounts as da
    from app.services import dict_values as dv
    from app.services import status_copy as sc

    # 避免 bake 注入盖住材料态；只读实体键
    saved = (
        sc.apply_status_copy_to_schema,
        dv.apply_dict_values_to_schema,
        da.apply_demo_accounts_to_schema,
    )
    sc.apply_status_copy_to_schema = lambda s, d, **k: s  # type: ignore[assignment]
    dv.apply_dict_values_to_schema = lambda s, d, **k: s  # type: ignore[assignment]
    da.apply_demo_accounts_to_schema = lambda s, d, **k: s  # type: ignore[assignment]
    try:
        schemas = {
            dom: ds.build_domain_schema("动作词缺口审计", dom) for dom in DOMAINS
        }
    finally:
        sc.apply_status_copy_to_schema = saved[0]  # type: ignore[assignment]
        dv.apply_dict_values_to_schema = saved[1]  # type: ignore[assignment]
        da.apply_demo_accounts_to_schema = saved[2]  # type: ignore[assignment]
    rep = gap_report(rows=rows, domains=sorted(DOMAINS), schemas=schemas)
    return {
        "gap_count": sum(int(r.get("gap_count") or 0) for r in rep.get("reports") or []),
        "gap_domains": rep.get("gap_domains") or 0,
        "domain_count": len(DOMAINS),
        "reports": rep.get("reports") or [],
    }


async def upsert_entry(
    db: AsyncSession,
    *,
    domain_id: str = WILDCARD,
    entity_key: str,
    verb_key: str,
    action_zh: str,
    skin_id: str = "",
    source: str = "manual",
) -> dict[str, Any]:
    from app.models import FactoryDiagramVerb

    domain_id = _norm(domain_id) or WILDCARD
    skin_id = _norm(skin_id)
    entity_key = _norm(entity_key)
    verb_key = _norm(verb_key)
    action_zh = _norm(action_zh)
    source = _norm(source) or "manual"
    if not entity_key:
        raise ValueError("entity_key 必填")
    if not verb_key:
        raise ValueError("verb_key 必填")
    if not action_zh:
        raise ValueError("action_zh 必填")
    if len(action_zh) > 32:
        raise ValueError("action_zh 最多 32 字")
    if source not in SOURCES:
        source = "manual"
    result = await db.execute(
        select(FactoryDiagramVerb).where(
            FactoryDiagramVerb.domain_id == domain_id,
            FactoryDiagramVerb.skin_id == skin_id,
            FactoryDiagramVerb.entity_key == entity_key,
            FactoryDiagramVerb.verb_key == verb_key,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.action_zh = action_zh
        row.source = source
        row.updated_at = datetime.utcnow()
    else:
        row = FactoryDiagramVerb(
            domain_id=domain_id,
            skin_id=skin_id,
            entity_key=entity_key,
            verb_key=verb_key,
            action_zh=action_zh,
            source=source,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    invalidate_cache()
    await load_all_rows(db)
    return row_to_dict(row)


async def delete_entry(db: AsyncSession, entry_id: int) -> bool:
    from app.models import FactoryDiagramVerb

    row = await db.get(FactoryDiagramVerb, entry_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    invalidate_cache()
    return True
