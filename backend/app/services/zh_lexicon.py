"""工厂级中文词表：持久化、迁入、解析、扫缺口、写 COMMENT。

真源：factory_zh_lexicon。首迁种子仅 er_zh 静态字典（进程内缓存回退同此）。
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

KINDS = frozenset({"column", "table", "stem", "table_part"})
SOURCES = frozenset({"migrated", "scan", "manual", "draft"})
# bake COMMENT / 出包只认已确认来源；draft 仅控制台草稿
BAKE_SOURCES = frozenset({"migrated", "scan", "manual"})
# 与 factory_zh_lexicon.zh / COMMENT 写出一致；严于 MySQL 列 COMMENT 常见 255 上限
ZH_MAX_LEN = 64

# 有把握的后缀：必须先解析出词根再拼接；禁止退回裸默认词（如「时间」）
_SUGGEST_SUFFIX_RULES: tuple[tuple[str, str], ...] = (
    ("_username", "{stem}账号"),
    ("_name", "{stem}"),
    ("_at", "{stem}时间"),
    ("_url", "{stem}链接"),
    ("_yuan", "{stem}"),
    ("_msg", "{stem}说明"),
    ("_code", "{stem}码"),
    ("_type", "{stem}类型"),
    ("_note", "{stem}备注"),
    ("_method", "{stem}方式"),
    ("_status", "{stem}状态"),
    ("_no", "{stem}单号"),
    ("_id", "{stem}编号"),
)

_COMMENT_RE = re.compile(
    r"""COMMENT\s+(?:N)?['"]([^'"]*)['"]""",
    re.IGNORECASE,
)
_COL_LINE_RE = re.compile(
    r"^(\s*)(`?)(\w+)\2(\s+)([^,\n]+?)(,?\s*)$",
    re.IGNORECASE,
)
_CREATE_RE = re.compile(
    r"(CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\()((?:.|\n)*?)(\);)",
    re.IGNORECASE,
)
_HAN_RE = re.compile(r"[\u4e00-\u9fff]")

_lock = threading.RLock()
# kind -> list of row dicts (全量缓存)
_rows_cache: list[dict[str, Any]] | None = None
# 全局 kind+key -> zh（供 er_zh 热更新）
_global_maps: dict[str, dict[str, str]] = {
    "column": {},
    "table": {},
    "stem": {},
    "table_part": {},
}


def _norm(s: str | None) -> str:
    return (s or "").strip()


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "kind": str(row.kind),
        "key_name": str(row.key_name),
        "zh": str(row.zh),
        "domain": _norm(row.domain),
        "skin": _norm(row.skin),
        "table_name": _norm(row.table_name),
        "source": str(row.source or "manual"),
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    }


def invalidate_cache() -> None:
    global _rows_cache
    with _lock:
        _rows_cache = None


def _seed_payload() -> list[dict[str, str]]:
    """首迁种子：仅 er_zh 静态字典（运行真源仍是 factory_zh_lexicon）。"""
    from app.bake.schema import er_zh as ez

    by_key: dict[tuple[str, str, str, str, str], dict[str, str]] = {}

    def put(kind: str, key: str, zh: str) -> None:
        key, zh = _norm(key), _norm(zh)
        if not key or not zh:
            return
        by_key[(kind, key, "", "", "")] = {
            "kind": kind,
            "key_name": key,
            "zh": zh,
            "domain": "",
            "skin": "",
            "table_name": "",
            "source": "migrated",
        }

    for key, zh in ez._COMMON_COL_ZH.items():
        put("column", key, zh)
    for key, zh in ez._INFRA_TABLE_ZH.items():
        put("table", key, zh)
    for key, zh in ez._STEM_ZH.items():
        put("stem", key, zh)
    for key, zh in ez._TABLE_PART_ZH.items():
        put("table_part", key, zh)
    # 域×皮异名：进库表由侧栏维护 / migrate 追加，禁止在种子里写死 DOM 皮文案
    return list(by_key.values())


def lexicon_skin_for_bake(
    *,
    domain: str = "",
    title: str = "",
    proposal_text: str = "",
    schema: dict[str, Any] | None = None,
) -> str:
    """bake/出图用的皮 id：优先 schema.cinemaFace，否则开题扫（仅工厂侧参数）。"""
    if isinstance(schema, dict):
        face = _norm(str(schema.get("cinemaFace") or ""))
        if not face:
            labels = schema.get("labels") if isinstance(schema.get("labels"), dict) else {}
            face = _norm(str(labels.get("cinemaFace") or ""))
        if face:
            return face
    if _norm(domain) == "DOM-CINEMA":
        try:
            from app.bake.scene_scan import cinema_product_kind

            return _norm(cinema_product_kind(title or "", proposal_text or ""))
        except Exception:  # noqa: BLE001
            return "cinema"
    return ""


def column_zh_map(*, domain: str = "", skin: str = "") -> dict[str, str]:
    """列键 → 中文：对全局列键走 resolve_zh(domain, skin)（窄皮覆盖宽全局）。"""
    domain, skin = _norm(domain), _norm(skin)
    if _rows_cache is None:
        bootstrap_from_seed()
    keys: set[str] = set()
    with _lock:
        keys.update(_global_maps.get("column") or {})
        for r in _rows_cache or []:
            if r.get("kind") == "column" and _norm(r.get("key_name")):
                keys.add(_norm(r.get("key_name")))
    out: dict[str, str] = {}
    for key in keys:
        zh = resolve_zh(
            "column", key, domain=domain, skin=skin, for_bake=True
        )
        if zh:
            out[key] = zh
    return out


def column_zh_overrides_from_labels(labels: dict[str, Any] | None) -> dict[str, str]:
    """从 bake schema.labels 拼列中文覆盖（同源 seat* 名词，非词表种子写死）。

    规则固定、汉字来自 labels；侧栏域×皮行仍可另写覆盖同列。
    """
    if not isinstance(labels, dict):
        return {}
    out: dict[str, str] = {}
    hall = _norm(str(labels.get("seatHallNoun") or ""))
    if hall:
        out["hall_note"] = f"{hall}名称"
    org = _norm(str(labels.get("seatOrgNoun") or ""))
    if org:
        out["owner_username"] = f"{org}账号"
    return out


def _apply_global_maps(rows: Iterable[dict[str, Any]]) -> None:
    maps = {"column": {}, "table": {}, "stem": {}, "table_part": {}}
    for r in rows:
        kind = r.get("kind") or ""
        if kind not in maps:
            continue
        if _norm(r.get("source")) == "draft":
            continue
        if _norm(r.get("domain")) or _norm(r.get("skin")) or _norm(r.get("table_name")):
            continue
        key = _norm(r.get("key_name"))
        zh = _norm(r.get("zh"))
        if key and zh:
            maps[kind][key] = zh
    # 种子兜底：库空或缺项时仍可读（仅 er_zh）
    from app.bake.schema import er_zh as ez

    for k, v in ez._COMMON_COL_ZH.items():
        maps["column"].setdefault(k, v)
    for k, v in ez._INFRA_TABLE_ZH.items():
        maps["table"].setdefault(k, v)
    for k, v in ez._STEM_ZH.items():
        maps["stem"].setdefault(k, v)
    for k, v in ez._TABLE_PART_ZH.items():
        maps["table_part"].setdefault(k, v)
    with _lock:
        _global_maps.clear()
        _global_maps.update(maps)
        # 热更新 er_zh 导出名，供既有调用方
        ez._COMMON_COL_ZH.clear()
        ez._COMMON_COL_ZH.update(maps["column"])
        ez._INFRA_TABLE_ZH.clear()
        ez._INFRA_TABLE_ZH.update(maps["table"])
        ez._STEM_ZH.clear()
        ez._STEM_ZH.update(maps["stem"])
        ez._TABLE_PART_ZH.clear()
        ez._TABLE_PART_ZH.update(maps["table_part"])


def bootstrap_from_seed() -> None:
    """无 DB 时（单测）用种子灌缓存。"""
    rows = _seed_payload()
    with _lock:
        global _rows_cache
        _rows_cache = rows
    _apply_global_maps(rows)


async def load_all_rows(db: AsyncSession) -> list[dict[str, Any]]:
    """读库并刷新进程缓存。有 Session 时禁止返回种子冒充库数据。"""
    global _rows_cache
    from app.models import FactoryZhLexicon

    result = await db.execute(select(FactoryZhLexicon).order_by(FactoryZhLexicon.id))
    rows = [row_to_dict(r) for r in result.scalars().all()]
    with _lock:
        _rows_cache = rows
    _apply_global_maps(rows)
    return list(rows)


async def migrate_seed_if_empty(db: AsyncSession) -> dict[str, int]:
    """只追加：种子里库中没有的主键才 INSERT；已有行一律不改。"""
    from app.models import FactoryZhLexicon

    key_rows = await db.execute(
        select(
            FactoryZhLexicon.kind,
            FactoryZhLexicon.key_name,
            FactoryZhLexicon.domain,
            FactoryZhLexicon.skin,
            FactoryZhLexicon.table_name,
        )
    )
    have = {
        (_norm(k), _norm(n), _norm(d), _norm(s), _norm(t))
        for k, n, d, s, t in key_rows.all()
    }
    inserted = 0
    seed = _seed_payload()
    for item in seed:
        tup = (
            item["kind"],
            item["key_name"],
            item["domain"],
            item["skin"],
            item["table_name"],
        )
        if tup in have:
            continue
        db.add(
            FactoryZhLexicon(
                kind=item["kind"],
                key_name=item["key_name"],
                zh=item["zh"],
                domain=item["domain"],
                skin=item["skin"],
                table_name=item["table_name"],
                source=item["source"],
            )
        )
        inserted += 1
        have.add(tup)
    if inserted:
        await db.commit()
    invalidate_cache()
    rows = await load_all_rows(db)
    return {"inserted": inserted, "total": len(rows)}


def resolve_zh(
    kind: str,
    key: str,
    *,
    domain: str = "",
    skin: str = "",
    table_name: str = "",
    rows: list[dict[str, Any]] | None = None,
    for_bake: bool = False,
) -> str | None:
    """从窄到宽解析中文。for_bake=True 时跳过 draft。"""
    kind = _norm(kind)
    key = _norm(key)
    if not kind or not key or kind not in KINDS:
        return None
    domain, skin, table_name = _norm(domain), _norm(skin), _norm(table_name)
    data = rows
    if data is None:
        with _lock:
            data = list(_rows_cache) if _rows_cache is not None else None
    if data is None:
        bootstrap_from_seed()
        with _lock:
            data = list(_rows_cache or [])

    def pick(d: str, s: str, t: str) -> str | None:
        for r in data or []:
            if (
                r.get("kind") == kind
                and _norm(r.get("key_name")) == key
                and _norm(r.get("domain")) == d
                and _norm(r.get("skin")) == s
                and _norm(r.get("table_name")) == t
            ):
                if for_bake and _norm(r.get("source")) not in BAKE_SOURCES:
                    continue
                zh = _norm(r.get("zh"))
                if zh:
                    return zh
        return None

    seen: set[tuple[str, str, str]] = set()
    for cand in (
        (domain, skin, table_name),
        (domain, skin, ""),
        (domain, "", ""),
        ("", "", ""),
    ):
        if cand in seen:
            continue
        seen.add(cand)
        hit = pick(*cand)
        if hit:
            return hit
    if for_bake:
        # 全局热表来自非 draft 行 + 种子；draft 不会进 _global_maps（有 domain 空也需过滤）
        for r in data or []:
            if (
                r.get("kind") == kind
                and _norm(r.get("key_name")) == key
                and not _norm(r.get("domain"))
                and not _norm(r.get("skin"))
                and not _norm(r.get("table_name"))
                and _norm(r.get("source")) in BAKE_SOURCES
            ):
                zh = _norm(r.get("zh"))
                if zh:
                    return zh
        # 种子兜底仍可读
        with _lock:
            return _global_maps.get(kind, {}).get(key)
    with _lock:
        return _global_maps.get(kind, {}).get(key)


def suggested_column_zh(
    name: str,
    *,
    domain: str = "",
    skin: str = "",
    table_name: str = "",
) -> str | None:
    """有把握的建议中文：词表命中才返回（不做弱后缀）；bake 路径跳过 draft。"""
    return resolve_zh(
        "column",
        name,
        domain=domain,
        skin=skin,
        table_name=table_name,
        for_bake=True,
    )


def _fragment_zh(seg: str, rows: list[dict[str, Any]] | None) -> str | None:
    """词根段：先 stem，再全局 column（与 er_labels 词根回退一致）。"""
    seg = _norm(seg)
    if not seg:
        return None
    hit = resolve_zh("stem", seg, rows=rows)
    if hit:
        return hit
    return resolve_zh("column", seg, rows=rows)


def _compose_stem_parts(name: str, rows: list[dict[str, Any]] | None) -> str | None:
    name = _norm(name)
    if not name:
        return None
    if "_" not in name:
        return _fragment_zh(name, rows)
    parts = name.split("_")
    labs = [_fragment_zh(p, rows) for p in parts]
    if all(labs):
        return "".join(labs)  # type: ignore[arg-type]
    return None


def _suggest_from_stems(
    key_name: str, rows: list[dict[str, Any]] | None
) -> dict[str, str] | None:
    key_name = _norm(key_name)
    if not key_name:
        return None
    for suffix, fmt in _SUGGEST_SUFFIX_RULES:
        if not key_name.endswith(suffix) or len(key_name) <= len(suffix):
            continue
        stem_key = key_name[: -len(suffix)]
        stem = _compose_stem_parts(stem_key, rows) or _fragment_zh(stem_key, rows)
        if not stem:
            return None
        zh = fmt.format(stem=stem).strip()
        if not zh or len(zh) > ZH_MAX_LEN:
            return None
        return {"zh": zh, "reason": "词根组合"}
    composed = _compose_stem_parts(key_name, rows)
    if composed and composed != key_name and len(composed) <= ZH_MAX_LEN:
        return {"zh": composed, "reason": "词根组合"}
    return None


def _suggest_from_same_table(
    hit: ScanHit, rows: list[dict[str, Any]] | None
) -> dict[str, str] | None:
    domain = _norm(hit.domain)
    table = _norm(hit.table_name)
    key = _norm(hit.key_name)
    if not table or "_" not in key:
        return None
    key_parts = key.split("_")
    prefix = "_".join(key_parts[:-1])
    last = key_parts[-1]
    last_zh = _fragment_zh(last, rows)
    if not prefix or not last_zh:
        return None
    candidates: list[str] = []
    for r in rows or []:
        if _norm(r.get("kind")) != "column":
            continue
        if _norm(r.get("domain")) != domain:
            continue
        if _norm(r.get("table_name")) != table:
            continue
        other = _norm(r.get("key_name"))
        other_zh = _norm(r.get("zh"))
        if not other or other == key or not other_zh:
            continue
        if _norm(r.get("source")) == "draft":
            continue
        op = other.split("_")
        if len(op) < 2 or "_".join(op[:-1]) != prefix:
            continue
        sib_last_zh = _fragment_zh(op[-1], rows)
        if not sib_last_zh or not other_zh.endswith(sib_last_zh):
            continue
        new_zh = other_zh[: -len(sib_last_zh)] + last_zh
        if new_zh and len(new_zh) <= ZH_MAX_LEN:
            candidates.append(new_zh)
    uniq = set(candidates)
    if len(uniq) == 1:
        return {"zh": uniq.pop(), "reason": "同表类推"}
    return None


def suggest_gap_zh(
    hit: ScanHit | dict[str, Any],
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, str] | None:
    """对待补列产出确定性建议；无把握返回 None。永不调用 LLM。"""
    if isinstance(hit, dict):
        scan = ScanHit(
            domain=_norm(hit.get("domain")),
            skin=_norm(hit.get("skin")),
            table_name=_norm(hit.get("table_name")),
            key_name=_norm(hit.get("key_name")),
            kind=_norm(hit.get("kind")) or "column",
        )
    else:
        scan = hit
    data = rows
    if data is None:
        with _lock:
            data = list(_rows_cache) if _rows_cache is not None else None
    if data is None:
        bootstrap_from_seed()
        with _lock:
            data = list(_rows_cache or [])

    # 保险丝：更宽作用域已有正式词（含 draft 以外）
    existing = resolve_zh(
        scan.kind or "column",
        scan.key_name,
        domain=scan.domain,
        skin=scan.skin,
        table_name=scan.table_name,
        rows=data,
        for_bake=True,
    )
    if existing:
        return {"zh": existing, "reason": "词表已有"}

    stem_hit = _suggest_from_stems(scan.key_name, data)
    if stem_hit:
        return stem_hit
    return _suggest_from_same_table(scan, data)


def sql_templates_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "bake" / "sql" / "templates"


@dataclass
class ScanHit:
    domain: str
    skin: str
    table_name: str
    key_name: str
    kind: str = "column"


def scan_sql_columns() -> list[ScanHit]:
    """扫 DOM-*.sql 模板中的列；domain=文件名 DOM-*，skin 暂空。"""
    hits: list[ScanHit] = []
    root = sql_templates_dir()
    if not root.is_dir():
        return hits
    for path in sorted(root.glob("DOM-*.sql")):
        domain = path.stem  # DOM-SHOP
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in _CREATE_RE.finditer(text):
            tname = m.group(2)
            body = m.group(3)
            for raw in body.splitlines():
                line = raw.strip().rstrip(",")
                if not line or line.startswith("--"):
                    continue
                upper = line.upper()
                if upper.startswith(
                    ("PRIMARY KEY", "FOREIGN KEY", "KEY ", "INDEX ", "CONSTRAINT", "UNIQUE")
                ):
                    continue
                cm = re.match(r"^`?(\w+)`?\s+\w+", line)
                if not cm:
                    continue
                hits.append(
                    ScanHit(
                        domain=domain,
                        skin="",
                        table_name=tname,
                        key_name=cm.group(1),
                        kind="column",
                    )
                )
    # fragments 壳列：全局
    try:
        from app.bake.sql import fragments as fr

        for attr in dir(fr):
            if not attr.endswith("_COLUMNS") and attr not in {
                "ORDER_ADDRESS_COLUMNS",
                "ORDER_FOOD_COLUMNS",
                "ORDER_SHOP_FULFILL_COLUMNS",
                "ORDER_REFUND_COLUMNS",
                "ORDER_LIFECYCLE_COLUMNS",
                "ORDER_REFUND_CORE_COLUMNS",
                "ORDER_REFUND_EXTRA_COLUMNS",
                "ORDER_SHIP_COLUMNS",
            }:
                continue
            cols = getattr(fr, attr, None)
            if not isinstance(cols, list):
                continue
            for item in cols:
                if not isinstance(item, (tuple, list)) or not item:
                    continue
                hits.append(
                    ScanHit(
                        domain="",
                        skin="",
                        table_name="",
                        key_name=str(item[0]),
                        kind="column",
                    )
                )
    except Exception:  # noqa: BLE001
        pass
    return hits


def gap_report(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """相对词表的列缺口（扫到的列无任何作用域命中）；附带确定性建议。"""
    data = rows
    if data is None:
        with _lock:
            data = list(_rows_cache) if _rows_cache is not None else None
    if data is None:
        bootstrap_from_seed()
        with _lock:
            data = list(_rows_cache or [])
    gaps: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for hit in scan_sql_columns():
        tup = (hit.domain, hit.skin, hit.table_name, hit.key_name)
        if tup in seen:
            continue
        seen.add(tup)
        if resolve_zh(
            hit.kind,
            hit.key_name,
            domain=hit.domain,
            skin=hit.skin,
            table_name=hit.table_name,
            rows=data,
        ):
            continue
        # 全局也没有
        if resolve_zh("column", hit.key_name, rows=data):
            continue
        item: dict[str, Any] = {
            "kind": hit.kind,
            "key_name": hit.key_name,
            "domain": hit.domain,
            "skin": hit.skin,
            "table_name": hit.table_name,
            "suggested_zh": None,
            "suggest_reason": None,
        }
        suggestion = suggest_gap_zh(hit, data)
        if suggestion:
            item["suggested_zh"] = suggestion["zh"]
            item["suggest_reason"] = suggestion["reason"]
        gaps.append(item)
    return {"gap_count": len(gaps), "gaps": gaps}


def same_table_zh_collisions(
    rows: Iterable[dict[str, Any]] | None,
    *,
    kind: str,
    key_name: str,
    zh: str,
    domain: str = "",
    table_name: str = "",
) -> list[str]:
    """同域同表已有其它列用了同一中文 → 返回对方英文键（可保存，供弱警告）。"""
    kind, key_name, zh = _norm(kind), _norm(key_name), _norm(zh)
    domain, table_name = _norm(domain), _norm(table_name)
    if kind != "column" or not zh or not table_name or not key_name:
        return []
    hits: list[str] = []
    seen: set[str] = set()
    for r in rows or ():
        if _norm(r.get("kind")) != "column":
            continue
        if _norm(r.get("table_name")) != table_name:
            continue
        if _norm(r.get("domain")) != domain:
            continue
        if _norm(r.get("zh")) != zh:
            continue
        other = _norm(r.get("key_name"))
        if not other or other == key_name or other in seen:
            continue
        seen.add(other)
        hits.append(other)
    return sorted(hits)


async def upsert_entry(
    db: AsyncSession,
    *,
    kind: str,
    key_name: str,
    zh: str,
    domain: str = "",
    skin: str = "",
    table_name: str = "",
    source: str = "manual",
) -> dict[str, Any]:
    from app.models import FactoryZhLexicon

    kind, key_name, zh = _norm(kind), _norm(key_name), _norm(zh)
    domain, skin, table_name = _norm(domain), _norm(skin), _norm(table_name)
    source = _norm(source) or "manual"
    if kind not in KINDS:
        raise ValueError(f"kind 无效: {kind}")
    if not key_name or not zh:
        raise ValueError("key_name / zh 不能为空")
    if len(zh) > ZH_MAX_LEN:
        raise ValueError(f"中文最多 {ZH_MAX_LEN} 字")
    if _HAN_RE.search(key_name):
        raise ValueError("英文键禁止含汉字")
    if source not in SOURCES:
        source = "manual"
    existing = await load_all_rows(db)
    # draft 不得覆盖已有正式词条
    if source == "draft":
        for r in existing:
            if (
                r.get("kind") == kind
                and _norm(r.get("key_name")) == key_name
                and _norm(r.get("domain")) == domain
                and _norm(r.get("skin")) == skin
                and _norm(r.get("table_name")) == table_name
                and _norm(r.get("source")) in BAKE_SOURCES
            ):
                out = dict(r)
                out["warnings"] = ["已有正式词条，跳过草稿"]
                out["skipped"] = True
                return out
    warnings: list[str] = []
    twins = same_table_zh_collisions(
        existing,
        kind=kind,
        key_name=key_name,
        zh=zh,
        domain=domain,
        table_name=table_name,
    )
    if twins:
        shown = "、".join(twins[:5])
        more = f" 等{len(twins)}列" if len(twins) > 5 else ""
        warnings.append(f"同表已有列也叫「{zh}」（{shown}{more}），答辩看 COMMENT 时可能分不清")
    result = await db.execute(
        select(FactoryZhLexicon).where(
            FactoryZhLexicon.kind == kind,
            FactoryZhLexicon.key_name == key_name,
            FactoryZhLexicon.domain == domain,
            FactoryZhLexicon.skin == skin,
            FactoryZhLexicon.table_name == table_name,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.zh = zh
        row.source = source
        row.updated_at = datetime.utcnow()
    else:
        row = FactoryZhLexicon(
            kind=kind,
            key_name=key_name,
            zh=zh,
            domain=domain,
            skin=skin,
            table_name=table_name,
            source=source,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    invalidate_cache()
    await load_all_rows(db)
    out = row_to_dict(row)
    out["warnings"] = warnings
    return out


async def apply_suggest_drafts(
    db: AsyncSession,
    *,
    gaps: list[dict[str, Any]] | None = None,
) -> dict[str, int]:
    """把有 suggested_zh 的待补写成 source=draft；不覆盖正式词条。"""
    report_gaps = gaps
    if report_gaps is None:
        rows = await load_all_rows(db)
        report_gaps = gap_report(rows).get("gaps") or []
    written = 0
    skipped = 0
    no_suggest = 0
    for g in report_gaps:
        zh = _norm(g.get("suggested_zh"))
        if not zh:
            # 现场再算一次（调用方可能只传身份）
            sug = suggest_gap_zh(g)
            zh = _norm((sug or {}).get("zh"))
        if not zh:
            no_suggest += 1
            continue
        item = await upsert_entry(
            db,
            kind=_norm(g.get("kind")) or "column",
            key_name=_norm(g.get("key_name")),
            zh=zh,
            domain=_norm(g.get("domain")),
            skin=_norm(g.get("skin")),
            table_name=_norm(g.get("table_name")),
            source="draft",
        )
        if item.get("skipped"):
            skipped += 1
        else:
            written += 1
    return {
        "written": written,
        "skipped": skipped,
        "no_suggest": no_suggest,
        "total": len(report_gaps),
    }


async def delete_entry(db: AsyncSession, entry_id: int) -> bool:
    from app.models import FactoryZhLexicon

    row = await db.get(FactoryZhLexicon, entry_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    invalidate_cache()
    await load_all_rows(db)
    return True


def _escape_comment(zh: str) -> str:
    return (zh or "").replace("'", "").replace('"', "")[:ZH_MAX_LEN]


def append_comment_to_ddl(ddl: str, zh: str | None) -> str:
    """给列 DDL 片段补 COMMENT（已有则不改）。"""
    s = (ddl or "").rstrip()
    if not zh or _COMMENT_RE.search(s):
        return s
    return f"{s} COMMENT '{_escape_comment(zh)}'"


def annotate_sql_comments(
    sql: str,
    *,
    domain: str = "",
    skin: str = "",
    col_overrides: dict[str, str] | None = None,
) -> str:
    """幂等：CREATE 体里无 COMMENT 的列按词表补上。

    ``col_overrides``：本包 bake 皮词（来自 schema.labels，非词表种子写死）。
    优先于 resolve；学生包只见最终汉字。
    """
    overrides = {
        _norm(k): _norm(v)
        for k, v in (col_overrides or {}).items()
        if _norm(k) and _norm(v)
    }

    def repl(m: re.Match[str]) -> str:
        head, tname, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        lines_out: list[str] = []
        for raw in body.splitlines(keepends=True):
            core = raw.rstrip("\n")
            ending = "\n" if raw.endswith("\n") else ""
            stripped = core.strip()
            if not stripped or stripped.startswith("--"):
                lines_out.append(raw)
                continue
            upper = stripped.upper()
            if upper.startswith(
                ("PRIMARY KEY", "FOREIGN KEY", "KEY ", "INDEX ", "CONSTRAINT", "UNIQUE")
            ):
                lines_out.append(raw)
                continue
            cm = _COL_LINE_RE.match(core)
            if not cm:
                lines_out.append(raw)
                continue
            indent, tick, cname, sp, rest, comma = cm.groups()
            if _COMMENT_RE.search(rest):
                lines_out.append(raw)
                continue
            zh = overrides.get(_norm(cname)) or suggested_column_zh(
                cname, domain=domain, skin=skin, table_name=tname
            ) or suggested_column_zh(cname)
            if not zh:
                lines_out.append(raw)
                continue
            new_rest = append_comment_to_ddl(rest.rstrip(), zh)
            lines_out.append(f"{indent}{tick}{cname}{tick}{sp}{new_rest}{comma}{ending}")
        return head + "".join(lines_out) + tail

    return _CREATE_RE.sub(repl, sql or "")


def write_column_comment_in_sql(
    sql: str,
    *,
    table: str,
    column: str,
    zh: str,
) -> str:
    """改指定表列的 COMMENT（无则追加）；列名英文不动。"""
    table, column, zh = _norm(table), _norm(column), _norm(zh)
    if not table or not column or not zh:
        return sql or ""
    zh_esc = _escape_comment(zh)

    def repl(m: re.Match[str]) -> str:
        head, tname, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if tname != table:
            return m.group(0)
        lines_out: list[str] = []
        for raw in body.splitlines(keepends=True):
            core = raw.rstrip("\n")
            ending = "\n" if raw.endswith("\n") else ""
            cm = _COL_LINE_RE.match(core)
            if not cm or cm.group(3) != column:
                lines_out.append(raw)
                continue
            indent, tick, cname, sp, rest, comma = cm.groups()
            rest_stripped = _COMMENT_RE.sub("", rest).rstrip()
            new_rest = f"{rest_stripped} COMMENT '{zh_esc}'"
            lines_out.append(f"{indent}{tick}{cname}{tick}{sp}{new_rest}{comma}{ending}")
        return head + "".join(lines_out) + tail

    return _CREATE_RE.sub(repl, sql or "")


def extract_comment_from_line(line: str) -> str | None:
    m = _COMMENT_RE.search(line or "")
    return m.group(1).strip() if m else None


def assert_no_han_identifiers(sql: str) -> list[str]:
    """列名/表名含汉字则报错条目。"""
    bad: list[str] = []
    for m in _CREATE_RE.finditer(sql or ""):
        tname = m.group(2)
        if _HAN_RE.search(tname):
            bad.append(f"table:{tname}")
        for raw in m.group(3).splitlines():
            line = raw.strip().rstrip(",")
            if not line or line.startswith("--"):
                continue
            cm = re.match(r"^`?(\w+)`?\s+", line)
            if cm and _HAN_RE.search(cm.group(1)):
                bad.append(f"{tname}.{cm.group(1)}")
    return bad


# 禁止 import 时 bootstrap：会把种子灌进缓存，迁入/列表偏离库表。
# 起服 lifespan 只追加迁入；单测 setUp / 未起服 bake 走 bootstrap 或 _seed_payload。
