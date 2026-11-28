"""终稿吸收厂库：CRUD / 上传入库 / 重抽 / 喂助手稿 / 重叠提示。

不建 Project、不跑 proposal_match。口径：docs/thesis-absorb.md。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.proposal import read_proposal
from app.services.thesis_absorb_extract import (
    EXTRACTOR_VERSION,
    apply_figure_cross_check,
    apply_table_module_cross_check,
    build_feed_markdown,
    build_opening_draft,
    build_thesis_excerpt,
    clean_background,
    clean_thesis_title,
    content_sha256,
    excerpt_looks_junk,
    extract_thesis_proposal,
    looks_half_cut,
    fallback_drafts_no_llm,
    finalize_draft_entities,
    finalize_draft_features,
    finalize_feature_lines,
    finalize_sections,
)
from app.services.thesis_absorb_figures import (
    extract_pdf_figure_side,
    extract_tables_pdfplumber,
    figure_libs_ready,
    merge_figure_into_proposal,
)
from app.services.thesis_absorb_schema import extract_draft_schema

logger = logging.getLogger("gf.thesis_absorb")

# 后台抽取任务：离开页面不中断；进程内去重，重启后由 kick_stale_extracts 续跑
_extract_tasks: dict[int, asyncio.Task] = {}
_extract_started_mono: dict[int, float] = {}
# 批量/并发抽取串行：OCR+LLM 同开会打爆 Key/磁盘；换题同形仍可排队
_EXTRACT_SEM: asyncio.Semaphore | None = None
_EXTRACT_CONCURRENCY = 1


def _extract_sem() -> asyncio.Semaphore:
    global _EXTRACT_SEM
    if _EXTRACT_SEM is None:
        _EXTRACT_SEM = asyncio.Semaphore(max(1, int(_EXTRACT_CONCURRENCY)))
    return _EXTRACT_SEM
# 列表/元信息续跑节流，避免与轮询叠成扫库风暴
_kick_stale_mono: float = 0.0
_KICK_STALE_MIN_INTERVAL_S = 15.0
# 同步读文/OCR 上限；整单墙钟超时（含 LLM）→ 落 review，禁止挂死数十分钟
# 须大于 OCR 预算 + 读文/表，否则外层 wait_for 先砍掉扫图
EXTRACT_SYNC_TIMEOUT_S = 300.0
EXTRACT_STALE_S = 600.0

COVERAGE_VALUES = frozenset({"unknown", "covered", "skin_gap", "domain_gap"})
STATUS_VALUES = frozenset(
    {"extracting", "review", "stored", "fed", "covered", "patched"}
)
# 最高挂靠分低于此 → 机器不得留下 covered（同材同果：弱证不假绿）
MIN_COVERED_HINT_SCORE = 2
COVERAGE_HINTS_TOP_N = 6


# 内容域：挂件环境音不得压过借阅/报修/交易/预约等主路径（对齐 catalog）
_COVERAGE_CONTENT_DOMAINS = frozenset(
    {"DOM-FORUM", "DOM-BLOG", "DOM-MEDIA", "DOM-MUSIC", "DOM-DOCLIB"}
)
# 商城旁路「库存管理」易被资产域字面命中抢走
_COVERAGE_STOCK_SIDE = frozenset({"库存管理", "库存", "进销存", "仓库管理", "盘点"})
_COVERAGE_SHOP_ANCHORS = frozenset({"商品", "商城", "购物车", "下单", "电商", "二手"})
_COVERAGE_MAIN_ARCH = frozenset(
    {"ARCH-TRADE", "ARCH-FLOW", "ARCH-RESERVE", "ARCH-STOCK"}
)


def _coverage_hint_text(
    proposal: dict[str, Any],
    *,
    draft_roles: list[str] | None,
    draft_entities: list[str] | None,
    draft_features: list[str] | None,
) -> str:
    parts: list[str] = []
    for key in ("feature_lines", "entity_hints", "role_hints", "roles"):
        for x in list(proposal.get(key) or []):
            if isinstance(x, str) and x.strip():
                parts.append(x.strip())
    for bag in (draft_roles, draft_entities, draft_features):
        for x in list(bag or []):
            if isinstance(x, str) and x.strip():
                parts.append(x.strip())
    return "\n".join(parts)


def _refine_coverage_domain_scores(
    text: str,
    scored: list[tuple[str, int, list[str]]],
) -> list[tuple[str, int, list[str]]]:
    """剥内容环境音、压库存旁路抢商城、主路径原型在时不让内容挂件独占。"""
    from app.bake.catalog import _CONTENT_AMBIENT, score_all_archetypes
    from app.bake.domains import ARCH_PATH_ORDER, DOMAIN_GROUPS

    archs = score_all_archetypes(text)
    arch_set = set(archs)
    primary_arch = next((a for a in ARCH_PATH_ORDER if a in arch_set), None)
    has_main_arch = any(a in arch_set for a in _COVERAGE_MAIN_ARCH)

    trade_domain_ids = next(
        (set(doms) for gid, _lab, doms in DOMAIN_GROUPS if gid == "trade"),
        {"DOM-SHOP", "DOM-FOOD", "DOM-CINEMA"},
    )
    has_non_content = any(
        k not in _COVERAGE_CONTENT_DOMAINS and int(s) > 0 for k, s, _ in scored
    )
    has_trade_domain = any(
        k in trade_domain_ids and int(s) > 0 for k, s, _ in scored
    )
    # 交易/单据/预约/进销存主原型压过内容挂件；纯内容题保留论坛/博客
    drop_content = primary_arch in _COVERAGE_MAIN_ARCH
    strip_ambient = (
        has_non_content or has_main_arch or has_trade_domain or drop_content
    )

    cleaned: list[tuple[str, int, list[str]]] = []
    for key, score, hits in scored:
        hit_list = [str(h) for h in (hits or []) if h]
        if key in _COVERAGE_CONTENT_DOMAINS:
            if drop_content:
                continue
            if strip_ambient:
                hard = [h for h in hit_list if h not in _CONTENT_AMBIENT]
                if not hard:
                    continue
                cleaned.append((key, len(hard), hard))
            else:
                cleaned.append((key, int(score), hit_list))
            continue
        cleaned.append((key, int(score), hit_list))

    # 商品/商城在时：资产域仅命中库存旁路 → 丢掉，避免 DOM-ASSET 字典序压 DOM-SHOP
    shop_hit = any(
        k in trade_domain_ids and int(s) > 0 and any(h in _COVERAGE_SHOP_ANCHORS for h in hits)
        for k, s, hits in cleaned
    )
    if shop_hit:
        narrowed: list[tuple[str, int, list[str]]] = []
        for key, score, hits in cleaned:
            if key == "DOM-ASSET" and hits and set(hits) <= _COVERAGE_STOCK_SIDE:
                continue
            narrowed.append((key, score, hits))
        cleaned = narrowed

    def _sort_key(t: tuple[str, int, list[str]]) -> tuple:
        key, score, hits = t
        non_amb = sum(1 for h in hits if h not in _CONTENT_AMBIENT)
        amb = sum(1 for h in hits if h in _CONTENT_AMBIENT)
        # 同分：非环境音命中多的优先，避免 DOM-FORUM 字典序压挂号/问卷/投票
        return (-int(score), -non_amb, amb, -len(hits), -sum(len(h) for h in hits), key)

    cleaned.sort(key=_sort_key)
    return cleaned


def coverage_domain_hints(
    proposal: dict[str, Any] | None,
    *,
    draft_roles: list[str] | None = None,
    draft_entities: list[str] | None = None,
    draft_features: list[str] | None = None,
    top_n: int = COVERAGE_HINTS_TOP_N,
) -> list[dict[str, Any]]:
    """功能/实体清单 → 现厂挂靠候选（确定性，同材同果）。

    复用目录关键词打分；不写库、不算出包 hits。
    文本用功能行 + 实体线索 + 角色，不用题名/届次。
    """
    from app.bake.capabilities import CAPABILITIES
    from app.bake.catalog import _catalog_scores
    from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS

    prop = proposal if isinstance(proposal, dict) else {}
    text = _coverage_hint_text(
        prop,
        draft_roles=draft_roles,
        draft_entities=draft_entities,
        draft_features=draft_features,
    )
    if not text.strip():
        return []

    scored = _catalog_scores(text, DOMAINS)
    cleaned = _refine_coverage_domain_scores(text, scored)
    positive = [(k, s, h) for k, s, h in cleaned if s > 0]
    if not positive:
        return []
    top_score = int(positive[0][1])
    top_hit_n = len(positive[0][2] or [])
    # 主候选领先：丢掉明显弱尾；同分只留命中数并列的前几
    narrowed: list[tuple[str, int, list]] = []
    for key, score, hits in positive:
        sc = int(score)
        hn = len(hits or [])
        if top_score >= 2 and sc < top_score - 1:
            continue
        if top_score == 1 and (sc < 1 or hn < top_hit_n):
            continue
        narrowed.append((key, sc, list(hits or [])))
        if len(narrowed) >= max(1, int(top_n)):
            break

    out: list[dict[str, Any]] = []
    for i, (key, score, hits) in enumerate(narrowed):
        meta = DOMAINS.get(key) or {}
        cap_labels: list[str] = []
        for cid in list(DOMAIN_CAPABILITIES.get(key) or []):
            lab = (CAPABILITIES.get(cid) or {}).get("label") or cid
            s = str(lab).strip()
            if s and s not in cap_labels:
                cap_labels.append(s)
        out.append(
            {
                "domain_id": key,
                "label": str(meta.get("label") or key),
                "score": int(score),
                "hits": [str(h) for h in hits if h],
                "flows": [str(f) for f in list(meta.get("flows") or [])[:2] if f],
                "caps": cap_labels[:12],
                "primary": i == 0,
            }
        )
    return out


def coverage_hints_brief(hints: list[dict[str, Any]] | None) -> str:
    """给 LLM 的短简报（主候选置顶；弱并列勿当 covered）。"""
    rows = [h for h in (hints or []) if isinstance(h, dict)]
    if not rows:
        return "（无稳定挂靠候选：覆盖请标 unknown，禁止 covered）"
    lines: list[str] = []
    for h in rows:
        hits = "、".join(str(x) for x in (h.get("hits") or []) if x) or "—"
        flows = "；".join(str(x) for x in (h.get("flows") or []) if x) or "—"
        caps = "、".join(str(x) for x in (h.get("caps") or []) if x) or "—"
        tag = "【主候选】" if h.get("primary") else "【次】"
        lines.append(
            f"- {tag}{h.get('domain_id')}（{h.get('label')}）分:{h.get('score')} "
            f"命中:{hits} 流程:{flows} 默认能力:{caps}"
        )
    lines.append(
        "采信规则：优先【主候选】；仅主候选分≥2 且现皮也盖得住才可考虑 covered；"
        "行业皮盖不住 → skin_gap（不是 covered）；"
        "技术栈形态/主线交不了 → domain_gap（不是 covered）；"
        "多条同分弱证 → skin_gap/domain_gap/unknown，禁止 covered。"
    )
    return "\n".join(lines)


def gate_coverage_by_hints(
    coverage: str,
    hints: list[dict[str, Any]] | None,
    *,
    min_score: int = MIN_COVERED_HINT_SCORE,
) -> str:
    """弱证禁假绿：无候选或最高分过弱时 covered → unknown。"""
    cov = str(coverage or "").strip()
    if cov not in COVERAGE_VALUES:
        return "unknown"
    if cov != "covered":
        return cov
    rows = [h for h in (hints or []) if isinstance(h, dict)]
    top = int(rows[0].get("score") or 0) if rows else 0
    if not rows or top < int(min_score):
        return "unknown"
    return "covered"


# 现厂可交主线外的前端/后端点名（stack_scan 未列全时补；禁止静默标已齐）
_ABSORB_SHAPE_EXTRA: tuple[tuple[str, str], ...] = (
    ("React", "React"),
    ("Angular", "Angular"),
    ("Flask", "Flask"),
    ("FastAPI", "FastAPI"),
)


def absorb_stack_coverage_blockers(
    tech_stack_lines: list[str] | None,
) -> list[str]:
    """文中技术栈与现厂可交形态冲突 → 短因列表（同材同果；复用 stack_scan 针）。"""
    from app.bake.stack_scan import UNDELIVERED_STACK_HINTS, UNSUPPORTED_HINTS

    lines = [
        str(x).strip()
        for x in (tech_stack_lines or [])
        if isinstance(x, str) and str(x).strip()
    ]
    if not lines:
        return []
    text = "\n".join(lines)
    text_l = text.lower()
    out: list[str] = []

    def _hit(needle: str) -> bool:
        if not needle:
            return False
        if needle.isascii():
            return needle.lower() in text_l
        return needle in text

    for needle, label in UNSUPPORTED_HINTS:
        if _hit(needle) or _hit(str(label)):
            tag = f"不支持主线·{label}"
            if tag not in out:
                out.append(tag)
    for needle, _tip in UNDELIVERED_STACK_HINTS:
        if _hit(needle):
            tag = f"未落地主线·{needle}"
            if tag not in out:
                out.append(tag)
    for needle, label in _ABSORB_SHAPE_EXTRA:
        if _hit(needle):
            tag = f"形态不符·{label}"
            if tag not in out:
                out.append(tag)
    return out


def gate_coverage_by_stack(
    coverage: str,
    tech_stack_lines: list[str] | None,
) -> str:
    """交付形态交不了 → 禁止假已齐：covered → domain_gap。

    硬案终裁见 resolve_machine_coverage（任意预选遇栈冲突都直判差能力）。
    """
    cov = str(coverage or "").strip()
    if cov not in COVERAGE_VALUES:
        return "unknown"
    if cov != "covered":
        return cov
    if absorb_stack_coverage_blockers(tech_stack_lines):
        return "domain_gap"
    return "covered"


def resolve_machine_coverage(
    proposed: str,
    hints: list[dict[str, Any]] | None,
    tech_stack_lines: list[str] | None,
    *,
    min_score: int = MIN_COVERED_HINT_SCORE,
) -> tuple[str, str]:
    """机审终裁（确定性·同材同果）。

    硬案直接定死；灰区留给人：
    - 技术栈形态/主线交不了 → domain_gap（不论模型预选）
    - 已齐但挂靠弱/空/并列 → unknown
    - 其余保留预选（covered / skin_gap / domain_gap / unknown）
    """
    cov = str(proposed or "unknown").strip()
    if cov not in COVERAGE_VALUES:
        cov = "unknown"

    blockers = absorb_stack_coverage_blockers(tech_stack_lines)
    if blockers:
        return "domain_gap", f"栈冲突·{blockers[0]}"

    cov = gate_coverage_by_hints(cov, hints, min_score=min_score)
    if cov != "covered":
        return cov, ""

    rows = [h for h in (hints or []) if isinstance(h, dict)]
    if not rows:
        return "unknown", "无挂靠候选"
    top = int(rows[0].get("score") or 0)
    if len(rows) >= 2 and int(rows[1].get("score") or 0) == top:
        return "unknown", "挂靠并列弱证"
    return "covered", ""


def _append_coverage_review(
    row: Any,
    *,
    before: str,
    after: str,
    note: str = "",
) -> None:
    """人改覆盖 ≠ 机审原值时记账（回灌样本，不另开旁路表）。"""
    if before == after:
        return
    machine = str(getattr(row, "coverage_machine", None) or "").strip()
    log = getattr(row, "coverage_review_json", None)
    if not isinstance(log, list):
        log = []
    entry = {
        "from": before,
        "to": after,
        "machine": machine,
        "note": (note or "")[:80],
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    row.coverage_review_json = [*log[-19:], entry]


def coverage_stack_brief(tech_stack_lines: list[str] | None) -> str:
    """给 LLM 的技术栈对照短句。"""
    lines = [
        str(x).strip()
        for x in (tech_stack_lines or [])
        if isinstance(x, str) and str(x).strip()
    ]
    named = "、".join(lines[:16]) if lines else "（文中未抽出技术栈点名）"
    blockers = absorb_stack_coverage_blockers(lines)
    if blockers:
        return (
            f"文中点名：{named}。冲突：{'；'.join(blockers[:6])}。"
            "现厂默认可交：Boot + Vue3 + Element + MySQL + jdbc/mybatis/jpa；"
            "形态/主线交不了 → 禁止 covered，标 domain_gap。"
        )
    return (
        f"文中点名：{named}。"
        "现厂默认可交：Boot + Vue3 + Element + MySQL + jdbc/mybatis/jpa；"
        "点名不支持或未落地主线（小程序/SSR/Redis 等）→ 禁止 covered。"
    )


def _absorb_dir() -> Path:
    p = get_settings().data_dir / "thesis_absorb"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _ta_public_id_stamp() -> str:
    return f"gf-ta-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


async def alloc_ta_public_id(
    db: AsyncSession, *, reserved: set[str] | None = None
) -> str:
    """签发终稿吸收对账键 gf-ta-…（撞秒加后缀）。"""
    from app.models import FactoryThesisAbsorb

    taken = {x for x in (reserved or set()) if x}
    base = _ta_public_id_stamp()
    cand = base
    for i in range(0, 50):
        if i:
            cand = f"{base}-{i}"
        if cand in taken:
            continue
        exists = await db.scalar(
            select(FactoryThesisAbsorb.id).where(FactoryThesisAbsorb.public_id == cand)
        )
        if not exists:
            return cand
    return f"{base}-{datetime.now().strftime('%f')}"


async def ensure_row_public_id(db: AsyncSession, row: Any) -> str:
    """旧行补发 public_id；已有则原样返回。"""
    cur = str(getattr(row, "public_id", None) or "").strip()
    if cur:
        return cur
    row.public_id = await alloc_ta_public_id(db)
    await db.commit()
    await db.refresh(row)
    return str(row.public_id)


async def resolve_record_key(db: AsyncSession, key: str | int) -> int | None:
    """路由键：纯数字 → id；gf-ta-… → public_id。"""
    from app.models import FactoryThesisAbsorb

    raw = str(key or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        row = await db.get(FactoryThesisAbsorb, int(raw))
        return int(row.id) if row else None
    if raw.startswith("gf-ta-"):
        row = await db.scalar(
            select(FactoryThesisAbsorb).where(FactoryThesisAbsorb.public_id == raw)
        )
        return int(row.id) if row else None
    return None


def _normalize_proposal(proposal: Any) -> dict[str, Any]:
    """保证前端拿到的 feature_lines / sections 一定是数组，避免 .length 炸。

    顺带剥目录编号 / 丢噪声；保留 module_hints / role_hints（结构线索，勿洗丢）。
    """
    p = dict(proposal or {}) if isinstance(proposal, dict) else {}
    fl = p.get("feature_lines")
    raw_feats = [x for x in fl if isinstance(x, str)] if isinstance(fl, list) else []
    p["feature_lines"] = finalize_feature_lines(raw_feats, limit=20)
    outs = p.get("out_scope_lines")
    p["out_scope_lines"] = (
        [x for x in outs if isinstance(x, str)] if isinstance(outs, list) else []
    )
    secs = p.get("sections")
    raw_secs: list[dict[str, Any]] = []
    if isinstance(secs, list):
        for s in secs:
            if not isinstance(s, dict):
                continue
            lines = s.get("lines")
            raw_secs.append(
                {
                    "heading": s.get("heading") or "",
                    "lines": [x for x in lines if isinstance(x, str)]
                    if isinstance(lines, list)
                    else [],
                }
            )
    p["sections"] = finalize_sections(raw_secs, limit=8, skip_intro=True)
    p["title"] = clean_thesis_title(str(p.get("title") or ""))
    bg = clean_background(str(p.get("background") or ""))
    if bg and excerpt_looks_junk(bg):
        bg = ""
    p["background"] = bg
    ex = str(p.get("excerpt") or "").strip()
    if excerpt_looks_junk(ex) or looks_half_cut(ex):
        rebuilt = build_thesis_excerpt(
            background=bg,
            feature_lines=list(p.get("feature_lines") or []),
        )
        p["excerpt"] = rebuilt or (
            "" if (looks_half_cut(ex) or excerpt_looks_junk(ex)) else re.sub(r"\s+", " ", ex)[:480]
        )
    else:
        p["excerpt"] = re.sub(r"\s+", " ", ex)[:480]
    for key in (
        "module_hints",
        "role_hints",
        "entity_hints",
        "figure_labels",
        "table_labels",
        "structure_ends",
        "tech_stack_lines",
    ):
        raw = p.get(key)
        if isinstance(raw, list):
            p[key] = [x for x in raw if isinstance(x, str) and str(x).strip()]
        elif key in p:
            p[key] = []
    # 结构图题注列表（交叉锚点，可空）
    caps = p.get("structure_captions")
    if isinstance(caps, list):
        p["structure_captions"] = [
            x for x in caps if isinstance(x, str) and str(x).strip()
        ]
    return p


def _proposal_missing_structure_hints(proposal: Any) -> bool:
    """旧库存或「只洗 JSON 假升版」会缺键；缺则必须重读源文件整抽。"""
    if not isinstance(proposal, dict):
        return True
    return "role_hints" not in proposal or "tech_stack_lines" not in proposal


def _try_reextract_from_source(row: Any) -> bool:
    """有源文件则整抽（与 reextract 同路径）；成功返回 True。同步，供线程调用。"""
    path = Path(row.source_path or "")
    if not path.is_file():
        return False
    raw = path.read_bytes()
    text = read_proposal(path)
    data = _extract_bundle(text, raw_bytes=raw, source_path=path)
    _apply_extract_data(row, data)
    return True


def _clean_draft_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for x in raw:
        s = str(x).strip() if x is not None else ""
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _wash_resolved_drafts(
    roles: list[str],
    entities: list[str],
    features: list[str],
) -> dict[str, list[str]]:
    """打开详情再洗三栏：壳实体/RBAC 功能降权，少人工删噪。"""
    return {
        "draft_roles": roles[:8],
        "draft_entities": finalize_draft_entities(entities, limit=24),
        "draft_features": finalize_draft_features(features, limit=32),
    }


def _entities_look_like_feature_stems(
    entities: list[str], features: list[str]
) -> bool:
    """旧草稿把「××管理」掐成实体时，多数能在功能清单找到同词干。"""
    if not entities:
        return False
    stems = {
        f[: -len("管理")]
        for f in features
        if isinstance(f, str) and f.endswith("管理") and len(f) > 2
    }
    if not stems:
        return False
    hit = sum(1 for e in entities if e in stems)
    return hit >= max(2, (len(entities) * 2 + 2) // 3)


def _resolved_drafts(row: Any, proposal: dict[str, Any]) -> dict[str, list[str]]:
    """库里有草稿用库；否则无 LLM 弱抽（仅表题注实体）。禁止正则发明角色/功能。"""
    fb = fallback_drafts_no_llm(proposal)
    roles = _clean_draft_list(getattr(row, "draft_roles", None))
    entities = _clean_draft_list(getattr(row, "draft_entities", None))
    features = _clean_draft_list(getattr(row, "draft_features", None))
    prop_feats = []
    if isinstance(proposal, dict):
        prop_feats = [
            x
            for x in list(proposal.get("feature_lines") or [])
            if isinstance(x, str)
        ]
    if entities and _entities_look_like_feature_stems(entities, features or prop_feats):
        entities = list(fb.get("draft_entities") or [])
    if roles or entities or features:
        return _wash_resolved_drafts(
            roles,
            entities or list(fb.get("draft_entities") or []),
            features,
        )
    return _wash_resolved_drafts(
        list(fb.get("draft_roles") or []),
        list(fb.get("draft_entities") or []),
        list(fb.get("draft_features") or []),
    )


def _row_to_dict(
    row: Any,
    *,
    fig_ready: bool | None = None,
    fig_hint: str | None = None,
) -> dict[str, Any]:
    proposal = _normalize_proposal(row.proposal_json)
    warnings = row.warnings_json if isinstance(row.warnings_json, list) else []
    feat_n = len(proposal.get("feature_lines") or [])
    thin = feat_n < 3
    drafts = _resolved_drafts(row, proposal)
    if fig_ready is None or fig_hint is None:
        fig_ready, fig_hint = figure_libs_ready()
    pid = str(getattr(row, "public_id", None) or "").strip()
    return {
        "id": row.id,
        "public_id": pid,
        "display_no": f"#{row.id}",
        "role": row.role,
        "focus": row.focus,
        "source_files": row.source_files if isinstance(row.source_files, list) else [],
        "source_path": row.source_path,
        "proposal": proposal,
        "status": row.status,
        "coverage": row.coverage,
        "coverage_note": row.coverage_note or "",
        "coverage_machine": str(getattr(row, "coverage_machine", None) or ""),
        "coverage_review": (
            list(row.coverage_review_json)
            if isinstance(getattr(row, "coverage_review_json", None), list)
            else []
        ),
        "coverage_overridden": bool(
            str(getattr(row, "coverage_machine", None) or "").strip()
            and str(getattr(row, "coverage_machine", None) or "").strip()
            != str(row.coverage or "").strip()
        ),
        "extract_round": row.extract_round,
        "content_sha256": row.content_sha256,
        "extractor_version": row.extractor_version,
        "has_figure_text": bool(row.has_figure_text),
        "char_count": row.char_count,
        "feature_line_count": feat_n,
        "warnings": warnings,
        "thin_features": thin,
        "ok_to_feed": not thin,
        "extract_warning": "thin_features" if thin else (
            "cross_check" if warnings else None
        ),
        "draft_roles": drafts["draft_roles"],
        "draft_entities": drafts["draft_entities"],
        "draft_features": drafts["draft_features"],
        "draft_schema_sql": str(getattr(row, "draft_schema_sql", None) or ""),
        "schema_extract_meta": (
            row.schema_extract_meta
            if isinstance(getattr(row, "schema_extract_meta", None), dict)
            else {}
        ),
        "absorb_used_llm": bool(proposal.get("absorb_used_llm")),
        "absorb_llm_skip": str(proposal.get("absorb_llm_skip") or ""),
        "trial_project_id": row.trial_project_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "figure_extract_ready": fig_ready,
        "figure_extract_hint": fig_hint,
    }


def _overlap_noise_labels() -> frozenset[str]:
    """壳文案真源：bake.schema.shell_menus（按菜单 key 展开），禁止本文件手写平行表。"""
    from app.bake.schema.shell_menus import near_dup_shell_feature_labels

    return near_dup_shell_feature_labels()


def _feature_label_set(lines: list[str]) -> set[str]:
    return {str(x).strip() for x in (lines or []) if x and str(x).strip()}


def _distinct_feature_set(labels: set[str]) -> set[str]:
    noise = _overlap_noise_labels()
    return {x for x in labels if x not in noise}


def _overlap_score(a: list[str], b: list[str]) -> tuple[int, list[str]]:
    """剔壳后的交集长度 + 全文交集行（展示可含壳）。

    出条与否见 ``_near_duplicate_features``；本函数只算交。
    """
    na = _feature_label_set(a)
    nb = _feature_label_set(b)
    full_inter = sorted(na & nb)
    distinct_n = len(_distinct_feature_set(na) & _distinct_feature_set(nb))
    return distinct_n, full_inter


def _near_duplicate_features(
    a: list[str],
    b: list[str],
    *,
    min_distinct: int = 3,
    min_coverage: float = 0.8,
) -> tuple[bool, int, list[str]]:
    """两边剔壳后，较短侧几乎被对方盖住才算「几乎整份相近」。"""
    na = _feature_label_set(a)
    nb = _feature_label_set(b)
    da = _distinct_feature_set(na)
    db = _distinct_feature_set(nb)
    full_inter = sorted(na & nb)
    if not da or not db:
        return False, 0, full_inter
    inter_d = da & db
    n = len(inter_d)
    if n < min_distinct:
        return False, n, full_inter
    ratio = n / float(min(len(da), len(db)))
    if ratio < min_coverage:
        return False, n, full_inter
    return True, n, full_inter


async def list_records(
    db: AsyncSession,
    *,
    q: str | None = None,
    coverage: str | None = None,
) -> list[dict[str, Any]]:
    from app.models import FactoryThesisAbsorb

    stmt = select(FactoryThesisAbsorb).order_by(FactoryThesisAbsorb.id.desc())
    rows = list((await db.execute(stmt)).scalars().all())
    reserved = {
        str(getattr(r, "public_id", None) or "").strip()
        for r in rows
        if str(getattr(r, "public_id", None) or "").strip()
    }
    dirty = False
    for r in rows:
        if not str(getattr(r, "public_id", None) or "").strip():
            pid = await alloc_ta_public_id(db, reserved=reserved)
            r.public_id = pid
            reserved.add(pid)
            dirty = True
    if dirty:
        await db.commit()
        for r in rows:
            await db.refresh(r)
    fig_ready, fig_hint = figure_libs_ready()
    items = []
    for r in rows:
        it = _row_to_dict(r, fig_ready=fig_ready, fig_hint=fig_hint)
        if str(r.status or "") == "extracting":
            it["thin_features"] = False
            it["ok_to_feed"] = False
            it["extract_warning"] = None
        items.append(it)
    if coverage:
        items = [i for i in items if i["coverage"] == coverage]
    if q:
        qq = q.strip().lower()
        items = [
            i
            for i in items
            if qq in json.dumps(i.get("source_files") or [], ensure_ascii=False).lower()
            or qq in (i.get("proposal") or {}).get("title", "").lower()
            or qq in (i.get("coverage_note") or "").lower()
            or qq in str(i.get("public_id") or "").lower()
            or qq in str(i.get("display_no") or "").lower()
            or qq == str(i.get("id") or "")
        ]
    return items


def _ver_int(ver: Any) -> int:
    try:
        return int(str(ver or "0").split(".", 1)[0])
    except ValueError:
        return 0


async def get_record(
    db: AsyncSession,
    record_id: int,
    *,
    light: bool = False,
) -> dict[str, Any] | None:
    """打开详情只读库，禁止在 GET 里整抽 / 调 LLM（产品：先出上次结果）。

    light=True：轮询专用——只回库内字段与状态，跳过重叠扫描 / 喂稿 / 开题草稿。
    """
    from app.models import FactoryThesisAbsorb

    row = await db.get(FactoryThesisAbsorb, record_id)
    if not row:
        return None
    await ensure_row_public_id(db, row)
    # 轻量轮询：跳过重叠/喂稿；仅抽取中禁止误标「要点偏少」
    if light or str(row.status or "") == "extracting":
        item = _row_to_dict(row)
        if str(row.status or "") == "extracting":
            item["thin_features"] = False
            item["ok_to_feed"] = False
            item["extract_warning"] = None
        item["overlaps"] = []
        item["feed_markdown"] = ""
        item["opening_draft"] = ""
        item["extractor_outdated"] = False
        item["needs_reextract"] = False
        item["current_extractor_version"] = EXTRACTOR_VERSION
        item["reextract_reasons"] = []
        return item
    empty_drafts = (
        not _clean_draft_list(row.draft_roles)
        and not _clean_draft_list(row.draft_entities)
        and not _clean_draft_list(row.draft_features)
    )
    outdated = _ver_int(row.extractor_version) < _ver_int(EXTRACTOR_VERSION)
    missing_hints = _proposal_missing_structure_hints(row.proposal_json)
    prop0 = row.proposal_json if isinstance(row.proposal_json, dict) else {}
    stem_entity_drafts = _entities_look_like_feature_stems(
        _clean_draft_list(row.draft_entities),
        _clean_draft_list(row.draft_features)
        or [x for x in list(prop0.get("feature_lines") or []) if isinstance(x, str)],
    )
    # 词干重合在现行规则下很常见（购物车/订单既是表也是「××管理」词干），
    # 只在规则落后时当作旧草稿信号；否则会假亮「需重抽」且批量永远消不掉
    need_reextract = bool(outdated or missing_hints or empty_drafts)
    item = _row_to_dict(row)
    prop = item["proposal"]
    item["overlaps"] = await find_overlaps(db, record_id, prop)
    item["feed_markdown"] = build_feed_markdown(
        record_id=row.id,
        public_id=str(getattr(row, "public_id", None) or ""),
        coverage=row.coverage,
        proposal=prop,
        draft_roles=item.get("draft_roles"),
        draft_entities=item.get("draft_entities"),
        draft_features=item.get("draft_features"),
    )
    item["opening_draft"] = build_opening_draft(prop)
    item["extractor_outdated"] = outdated
    item["needs_reextract"] = need_reextract
    item["current_extractor_version"] = EXTRACTOR_VERSION
    reasons: list[str] = []
    if outdated:
        reasons.append(
            f"抽取规则已更新（记录 v{row.extractor_version or '?'} → 现行 v{EXTRACTOR_VERSION}）"
        )
    if empty_drafts:
        reasons.append("补齐建议三栏仍空")
    if missing_hints:
        if isinstance(prop0, dict) and "tech_stack_lines" not in prop0:
            reasons.append("尚未抽取文中技术栈")
        else:
            reasons.append("结构线索不完整")
    if stem_entity_drafts and outdated:
        reasons.append("实体栏仍像功能词干")
    item["reextract_reasons"] = reasons
    # 现厂速查：确定性短表，同材同果；不写库、不算出包 hits
    item["coverage_hints"] = coverage_domain_hints(
        prop,
        draft_roles=item.get("draft_roles"),
        draft_entities=item.get("draft_entities"),
        draft_features=item.get("draft_features"),
    )
    tech_lines = (
        list(prop.get("tech_stack_lines") or []) if isinstance(prop, dict) else []
    )
    item["coverage_stack_blockers"] = absorb_stack_coverage_blockers(tech_lines)
    return item


async def find_overlaps(
    db: AsyncSession,
    record_id: int,
    proposal: dict[str, Any],
    *,
    min_overlap: int = 3,
    min_coverage: float = 0.8,
) -> list[dict[str, Any]]:
    """只提示几乎整份相近；不挡喂入/保存（调用方勿据此 disabled）。"""
    from app.models import FactoryThesisAbsorb

    from sqlalchemy.orm import load_only

    feats = list((proposal or {}).get("feature_lines") or [])
    # 剔壳后至少要有 min_overlap 条业务功能才可能达标
    if len(_distinct_feature_set(_feature_label_set(feats))) < min_overlap:
        return []
    # 只拉重叠比对所需列，禁止 hydrate draft_schema_sql 等大字段（P5）
    stmt = (
        select(FactoryThesisAbsorb)
        .where(FactoryThesisAbsorb.id != record_id)
        .options(
            load_only(
                FactoryThesisAbsorb.id,
                FactoryThesisAbsorb.proposal_json,
                FactoryThesisAbsorb.source_files,
            )
        )
        .limit(200)
    )
    rows = (await db.execute(stmt)).scalars().all()
    out: list[dict[str, Any]] = []
    for r in rows:
        prop_o = r.proposal_json if isinstance(r.proposal_json, dict) else {}
        other = list(prop_o.get("feature_lines") or [])
        ok, n, inter = _near_duplicate_features(
            feats,
            other,
            min_distinct=min_overlap,
            min_coverage=min_coverage,
        )
        if ok:
            out.append(
                {
                    "id": r.id,
                    "overlap_count": n,
                    "overlap_lines": inter[:12],
                    "title": prop_o.get("title") or "",
                    "source_files": r.source_files or [],
                }
            )
    out.sort(key=lambda x: -x["overlap_count"])
    return out[:10]


_FIGURE_CARRY_KEYS = (
    "figure_labels",
    "table_labels",
    "structure_ends",
    "structure_captions",
)


def _carry_prior_figure_fields(
    proposal: dict[str, Any],
    prior: dict[str, Any] | None,
) -> dict[str, Any]:
    """升版快路径：保留上次图侧结果，避免打开详情再跑 OCR。"""
    if not isinstance(prior, dict):
        return proposal
    out = dict(proposal or {})
    for k in _FIGURE_CARRY_KEYS:
        old = prior.get(k)
        if old and not out.get(k):
            out[k] = list(old) if isinstance(old, list) else old
    old_secs = prior.get("sections") if isinstance(prior.get("sections"), list) else []
    fig_sec = next(
        (
            s
            for s in old_secs
            if isinstance(s, dict) and str(s.get("heading") or "") == "图注与结构标签"
        ),
        None,
    )
    if fig_sec:
        secs = list(out.get("sections") or [])
        if not any(
            isinstance(s, dict) and str(s.get("heading") or "") == "图注与结构标签"
            for s in secs
        ):
            secs.append(
                {
                    "heading": "图注与结构标签",
                    "lines": list(fig_sec.get("lines") or [])[:24],
                }
            )
            out["sections"] = secs
    return out


def _extract_bundle(
    text: str,
    *,
    raw_bytes: bytes | None = None,
    source_path: str | Path | None = None,
    with_figures: bool = True,
    prior_proposal: dict[str, Any] | None = None,
    prior_has_figure: bool = False,
) -> dict[str, Any]:
    """纯同步抽取（可进 to_thread）；不碰 ORM。

    with_figures=False：打开详情升版用——只重抽文字，图侧沿用上次，躲开 OCR。
    """
    digest = content_sha256(raw_bytes if raw_bytes is not None else text)
    result = extract_thesis_proposal(text)
    proposal = result["proposal"]
    has_figure = False
    plumber_tables: list[dict[str, Any]] = []
    path = Path(source_path or "")
    if with_figures and path.is_file() and path.suffix.lower() == ".pdf":
        fig = extract_pdf_figure_side(path, text)
        plumber_tables = list(fig.get("plumber_tables") or [])
        if fig.get("section_lines") or fig.get("has_figure_text") or fig.get("warnings"):
            proposal = merge_figure_into_proposal(proposal, fig)
            result["proposal"] = proposal
            # 结构图 OCR 标签 + 表标签 → 与 P1 文字交叉；图题端名 → 与角色交叉
            fig_labs = list(fig.get("structure_labels") or []) + list(
                fig.get("table_labels") or []
            )
            result = apply_figure_cross_check(
                result,
                fig_labs,
                structure_ends=list(fig.get("structure_ends") or []),
            )
            proposal = result["proposal"]
            has_figure = bool(fig.get("has_figure_text"))
            for w in fig.get("warnings") or []:
                warns = list(result.get("warnings") or [])
                if w not in warns:
                    warns.append(w)
                result["warnings"] = warns
    elif not with_figures:
        proposal = _carry_prior_figure_fields(proposal, prior_proposal)
        result["proposal"] = proposal
        has_figure = bool(
            prior_has_figure
            or proposal.get("figure_labels")
            or proposal.get("structure_captions")
        )
        # 有沿用的结构标签则仍做文字交叉（不 OCR）
        fig_labs = list(proposal.get("figure_labels") or []) + list(
            proposal.get("table_labels") or []
        )
        if fig_labs or proposal.get("structure_ends"):
            result = apply_figure_cross_check(
                result,
                fig_labs,
                structure_ends=list(proposal.get("structure_ends") or []),
            )
            proposal = result["proposal"]
        # 跳过 OCR 时仍抽 pdfplumber 字段表，供 schema 落库
        if path.is_file() and path.suffix.lower() == ".pdf" and not plumber_tables:
            plumber_tables = extract_tables_pdfplumber(path)
    # 库表章 → draft schema.sql（正文题注 + plumber 字段表；无表也落空串+告警）
    schema_pack = extract_draft_schema(text, plumber_tables=plumber_tables)
    for w in (schema_pack.get("schema_extract_meta") or {}).get("warnings") or []:
        warns = list(result.get("warnings") or [])
        if w not in warns:
            warns.append(w)
        result["warnings"] = warns
    fl = proposal.get("feature_lines") or []
    # 同步路径只落弱抽；三栏/覆盖由 async LLM 层补齐
    fb = fallback_drafts_no_llm(proposal)
    # §3.0b：物理题注中文名 + 实体栏 ↔ 功能清单（两侧都有才对账）
    schema_meta = dict(schema_pack.get("schema_extract_meta") or {})
    result["warnings"] = apply_table_module_cross_check(
        list(result.get("warnings") or []),
        entities=list(fb.get("draft_entities") or [])
        + [str(x) for x in list(proposal.get("entity_hints") or []) if isinstance(x, str)],
        features=list(fb.get("draft_features") or [])
        + [str(x) for x in fl if isinstance(x, str)],
        table_labels=[
            str(x)
            for x in list(schema_meta.get("table_labels") or [])
            if isinstance(x, str) and str(x).strip()
        ],
    )
    return {
        "proposal_json": proposal,
        "warnings_json": result.get("warnings") or [],
        "content_sha256": digest,
        "extractor_version": result.get("extractor_version") or EXTRACTOR_VERSION,
        "char_count": int(proposal.get("char_count") or len(text)),
        "feature_line_count": len(fl),
        "has_figure_text": has_figure,
        "draft_roles": fb["draft_roles"],
        "draft_entities": fb["draft_entities"],
        "draft_features": fb["draft_features"],
        "draft_schema_sql": str(schema_pack.get("draft_schema_sql") or ""),
        "schema_extract_meta": schema_meta,
        "status": "review" if result.get("thin_features") else "stored",
        "_extract_text": text,
    }


def _apply_extract_data(row: Any, data: dict[str, Any]) -> None:
    row.proposal_json = data["proposal_json"]
    row.warnings_json = data["warnings_json"]
    row.content_sha256 = data["content_sha256"]
    row.extractor_version = data["extractor_version"]
    row.char_count = data["char_count"]
    row.feature_line_count = data["feature_line_count"]
    row.has_figure_text = data["has_figure_text"]
    row.draft_roles = data["draft_roles"]
    row.draft_entities = data["draft_entities"]
    row.draft_features = data["draft_features"]
    row.draft_schema_sql = str(data.get("draft_schema_sql") or "")
    meta = data.get("schema_extract_meta")
    row.schema_extract_meta = meta if isinstance(meta, dict) else {}
    row.status = data["status"]
    if "coverage" in data and data["coverage"] in COVERAGE_VALUES:
        row.coverage = data["coverage"]
    if "coverage_note" in data and data.get("coverage_note") is not None:
        row.coverage_note = str(data.get("coverage_note") or "")[:500]


def _settle_absorb_status_after_drafts(
    row: Any,
    *,
    used_llm: bool,
    coverage: str,
) -> None:
    """按最终功能条数落 status：够厚 → stored；已齐且够厚 → covered；偏少 → review。

    禁止：同步阶段因薄清单写成 review 后，LLM 已抽厚却永不升格；
    禁止：仅靠 status==extracting 才升 stored（后台路径此时已是 review/stored）。
    """
    from app.services.thesis_absorb_extract import THIN_FEATURE_THRESHOLD

    feat_n = int(getattr(row, "feature_line_count", 0) or 0)
    thin = feat_n < int(THIN_FEATURE_THRESHOLD)
    cov = str(coverage or "").strip()
    cur = str(getattr(row, "status", None) or "").strip()
    if used_llm and cov == "covered" and not thin:
        row.status = "covered"
        return
    if thin:
        row.status = "review"
        return
    # 够厚：工作态升/保持 stored；终端标签 covered/patched/fed 不降
    if cur in ("", "extracting", "review", "stored"):
        row.status = "stored"


def _apply_llm_drafts_to_row(
    row: Any,
    out: dict[str, Any],
    *,
    proposal: dict[str, Any] | None = None,
) -> None:
    """把 LLM 三栏结果写回 ORM 行（纯内存，调用方负责 commit）。"""
    prop = proposal if isinstance(proposal, dict) else (
        dict(row.proposal_json) if isinstance(row.proposal_json, dict) else {}
    )
    row.draft_roles = list(out.get("draft_roles") or [])
    row.draft_entities = list(out.get("draft_entities") or [])
    row.draft_features = list(out.get("draft_features") or [])
    cov = str(out.get("coverage") or "unknown")
    if cov in COVERAGE_VALUES:
        row.coverage = cov
        row.coverage_machine = cov
    note = str(out.get("coverage_note") or "").strip()
    if note:
        row.coverage_note = note[:500]
    # 机审重写：清空旧人改分歧，避免旧账绑新抽
    row.coverage_review_json = []
    pj = dict(row.proposal_json) if isinstance(row.proposal_json, dict) else {}
    prev_feats = [
        str(x).strip()
        for x in list(pj.get("feature_lines") or [])
        if isinstance(x, str) and str(x).strip()
    ]
    pj["absorb_used_llm"] = bool(out.get("used_llm"))
    skip = str(out.get("skip_reason") or "").strip()
    if skip:
        pj["absorb_llm_skip"] = skip
    elif "absorb_llm_skip" in pj:
        pj.pop("absorb_llm_skip", None)
    if out.get("used_llm"):
        # 模型跑通：以三栏功能为准（可空），禁止残留正则假清单
        pj["feature_lines"] = list(row.draft_features or [])
        row.feature_line_count = len(pj["feature_lines"])
        row.proposal_json = pj
    else:
        # 模型未跑通：保留同步抽取清单，禁止清空制造假「待核对 / 要点偏少」
        pj["feature_lines"] = prev_feats
        row.feature_line_count = len(prev_feats)
        row.proposal_json = pj
    llm_warns = [w for w in list(out.get("warnings") or []) if isinstance(w, str) and w]
    _feat_cross = (
        "设计有实现无",
        "实现有设计",
        "结构图有、文字清单无",
        "文字清单有、结构图",
        "结构图标签与文字模块清单",
        "测试用例提到设计未列",
        "角色与端不一致",
        "缺实现/结构图交叉",
        "表有模块无",
        "模块有表无",
    )
    old = list(row.warnings_json) if isinstance(row.warnings_json, list) else []
    if out.get("used_llm"):
        base = [
            w
            for w in old
            if isinstance(w, str) and not any(p in w for p in _feat_cross)
        ]
    else:
        base = [w for w in old if isinstance(w, str)]
    for w in llm_warns:
        if w not in base:
            base.append(w)
    if out.get("used_llm") and list(out.get("draft_roles") or []):
        base = [w for w in base if w != "角色与端不一致"]
    if out.get("used_llm"):
        meta = (
            row.schema_extract_meta
            if isinstance(getattr(row, "schema_extract_meta", None), dict)
            else {}
        )
        base = apply_table_module_cross_check(
            base,
            entities=list(row.draft_entities or [])
            + [
                str(x)
                for x in list(prop.get("entity_hints") or [])
                if isinstance(x, str)
            ],
            features=list(row.draft_features or []),
            table_labels=[
                str(x)
                for x in list(meta.get("table_labels") or [])
                if isinstance(x, str) and str(x).strip()
            ],
        )
    row.warnings_json = base
    _settle_absorb_status_after_drafts(
        row,
        used_llm=bool(out.get("used_llm")),
        coverage=cov,
    )


async def _enrich_with_llm_drafts(
    db: AsyncSession,
    row: Any,
    *,
    text: str,
    proposal: dict[str, Any] | None = None,
) -> None:
    """LLM 主抽三栏 + 覆盖预选；失败则保留弱抽并写入明白告警。"""
    from app.llm.agents_thesis_absorb import run_thesis_absorb_drafts_agent
    from app.llm.runtime import load_llm_runtime

    prop = proposal if isinstance(proposal, dict) else (
        dict(row.proposal_json) if isinstance(row.proposal_json, dict) else {}
    )
    rt = await load_llm_runtime(db)
    out = await run_thesis_absorb_drafts_agent(
        db,
        rt,
        text=text,
        proposal=prop,
        record_id=getattr(row, "id", None),
    )
    _apply_llm_drafts_to_row(row, out, proposal=prop)


def _apply_extract_to_row(
    row: Any,
    text: str,
    *,
    raw_bytes: bytes | None = None,
    source_path: str | Path | None = None,
) -> None:
    path = source_path or getattr(row, "source_path", None)
    _apply_extract_data(
        row,
        _extract_bundle(text, raw_bytes=raw_bytes, source_path=path),
    )


async def _reextract_row_async(row: Any, *, with_figures: bool = True) -> bool:
    """整抽进线程，结果回主协程写 ORM，避免堵住事件循环。

    打开详情升版传 with_figures=False；上传/「重新抽取」保持 True。
    """
    path = Path(row.source_path or "")
    if not path.is_file():
        return False
    prior = (
        dict(row.proposal_json)
        if isinstance(row.proposal_json, dict)
        else None
    )
    prior_has = bool(getattr(row, "has_figure_text", False))

    def _job() -> dict[str, Any]:
        raw = path.read_bytes()
        text = read_proposal(path)
        return _extract_bundle(
            text,
            raw_bytes=raw,
            source_path=path,
            with_figures=with_figures,
            prior_proposal=prior,
            prior_has_figure=prior_has,
        )

    data = await asyncio.to_thread(_job)
    _apply_extract_data(row, data)
    return True


def schedule_absorb_extract(record_id: int) -> None:
    """文件已落盘后后台抽取；同 id 已在跑则不重复起。"""
    import time

    rid = int(record_id)
    old = _extract_tasks.get(rid)
    if old is not None and not old.done():
        return
    _extract_started_mono[rid] = time.monotonic()
    task = asyncio.create_task(
        run_absorb_extract(rid),
        name=f"thesis-absorb-extract-{rid}",
    )
    _extract_tasks[rid] = task

    def _done(t: asyncio.Task, *, jid: int = rid) -> None:
        _extract_tasks.pop(jid, None)
        _extract_started_mono.pop(jid, None)
        try:
            exc = t.exception()
        except asyncio.CancelledError:
            return
        if exc is not None:
            logger.exception("终稿吸收后台抽取异常 · #%s", jid, exc_info=exc)

    task.add_done_callback(_done)


def _extract_wall_age_s(row: Any) -> float:
    """库内进入 extracting 后的墙钟秒数（用 updated_at；没有则 created_at）。

    库内多为 naive 本地时：禁止当成 UTC，否则东八区会算出「未来」→ 年龄 0、永不超时。
    """
    ts = getattr(row, "updated_at", None) or getattr(row, "created_at", None)
    if ts is None:
        return 0.0
    if getattr(ts, "tzinfo", None) is None:
        return max(0.0, (datetime.now() - ts).total_seconds())
    return max(0.0, (datetime.now(ts.tzinfo) - ts).total_seconds())


async def _mark_extract_failed(db: AsyncSession, row: Any, reason: str) -> None:
    warns = list(row.warnings_json) if isinstance(row.warnings_json, list) else []
    msg = f"extract_fail:{reason}"[:420]
    if msg not in warns:
        warns.append(msg)
    row.warnings_json = warns
    row.status = "review"
    await db.commit()


async def ensure_extract_alive(db: AsyncSession, record_id: int) -> str:
    """轮询入口：只处理本条。无任务则续跑；墙钟超时则取消并落失败。

    返回：ok | restarted | timed_out | skip
    """
    import time

    from app.models import FactoryThesisAbsorb

    rid = int(record_id)
    row = await db.get(FactoryThesisAbsorb, rid)
    if not row or str(row.status or "") != "extracting":
        return "skip"

    age = _extract_wall_age_s(row)
    old = _extract_tasks.get(rid)
    running = old is not None and not old.done()
    started = _extract_started_mono.get(rid)

    if age >= EXTRACT_STALE_S or (
        running and started is not None and (time.monotonic() - started) >= EXTRACT_STALE_S
    ):
        if running and old is not None:
            old.cancel()
        await _mark_extract_failed(db, row, "抽取超时（读文/扫图或模型过久）")
        _extract_tasks.pop(rid, None)
        _extract_started_mono.pop(rid, None)
        return "timed_out"

    if running:
        return "ok"

    schedule_absorb_extract(rid)
    return "restarted"


async def kick_stale_extracts(db: AsyncSession) -> int:
    """列表/元信息入口：把库内仍标 extracting、进程里没在跑的续上。

    有节流：轮询不得每拍都扫；超时单直接落失败。
    """
    import time

    global _kick_stale_mono
    now = time.monotonic()
    if now - _kick_stale_mono < _KICK_STALE_MIN_INTERVAL_S:
        return 0
    _kick_stale_mono = now

    from app.models import FactoryThesisAbsorb

    rows = list(
        (
            await db.execute(
                select(FactoryThesisAbsorb).where(
                    FactoryThesisAbsorb.status == "extracting"
                )
            )
        )
        .scalars()
        .all()
    )
    n = 0
    for row in rows:
        rid = int(row.id)
        action = await ensure_extract_alive(db, rid)
        if action in ("restarted", "timed_out"):
            n += 1
    return n


async def run_absorb_extract(record_id: int) -> None:
    """独立会话跑抽取 + LLM；失败写入告警并落 review，不丢源文件。

    OCR/LLM 期间不占着 ORM 会话，避免与详情轮询抢库。
    """
    async with _extract_sem():
        await _run_absorb_extract_body(record_id)


async def _run_absorb_extract_body(record_id: int) -> None:
    from app.core.database import SessionLocal
    from app.models import FactoryThesisAbsorb

    path: Path
    prior_prop: dict[str, Any]
    reuse_figures: bool
    async with SessionLocal() as db:
        row = await db.get(FactoryThesisAbsorb, int(record_id))
        if not row:
            return
        path = Path(row.source_path or "")
        if not path.is_file():
            await _mark_extract_failed(db, row, "源文件不在")
            return
        prior_prop = (
            dict(row.proposal_json) if isinstance(row.proposal_json, dict) else {}
        )
        prior_labels = [
            x
            for x in list(prior_prop.get("figure_labels") or [])
            if isinstance(x, str) and str(x).strip()
        ]
        # 重抽且已有图侧标签：跳过 OCR；首抽 / 无标签仍扫图
        reuse_figures = int(row.extract_round or 1) > 1 and (
            bool(prior_labels) or bool(getattr(row, "has_figure_text", False))
        )

    try:

        def _job() -> tuple[str, dict[str, Any]]:
            raw = path.read_bytes()
            text = read_proposal(path)
            return text, _extract_bundle(
                text,
                raw_bytes=raw,
                source_path=path,
                with_figures=not reuse_figures,
                prior_proposal=prior_prop if reuse_figures else None,
                prior_has_figure=reuse_figures,
            )

        try:
            text, data = await asyncio.wait_for(
                asyncio.to_thread(_job),
                timeout=EXTRACT_SYNC_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            # 根因收口：扫图拖死时降级为纯文字，禁止整单挂死
            if reuse_figures:
                raise TimeoutError(
                    f"读文/扫图超过 {int(EXTRACT_SYNC_TIMEOUT_S)} 秒"
                ) from None

            def _job_text_only() -> tuple[str, dict[str, Any]]:
                raw = path.read_bytes()
                text0 = read_proposal(path)
                return text0, _extract_bundle(
                    text0,
                    raw_bytes=raw,
                    source_path=path,
                    with_figures=False,
                    prior_proposal=None,
                    prior_has_figure=False,
                )

            text, data = await asyncio.wait_for(
                asyncio.to_thread(_job_text_only),
                timeout=min(90.0, EXTRACT_SYNC_TIMEOUT_S),
            )
            warns = list(data.get("warnings_json") or [])
            msg = "扫图超时，已按纯文字抽取"
            if msg not in warns:
                warns.append(msg)
            data["warnings_json"] = warns
        prop = (
            data.get("proposal_json")
            if isinstance(data.get("proposal_json"), dict)
            else {}
        )
        # LLM 用短会话；审计行自带独立 Session，勿夹着 absorb 脏行等 2 分钟
        from app.llm.agents_thesis_absorb import run_thesis_absorb_drafts_agent
        from app.llm.runtime import load_llm_runtime

        async with SessionLocal() as db:
            rt = await load_llm_runtime(db)
            llm_out = await run_thesis_absorb_drafts_agent(
                db,
                rt,
                text=text,
                proposal=prop,
                record_id=int(record_id),
            )
        async with SessionLocal() as db:
            row = await db.get(FactoryThesisAbsorb, int(record_id))
            if not row:
                return
            _apply_extract_data(row, data)
            _apply_llm_drafts_to_row(row, llm_out, proposal=prop)
            await db.commit()
    except Exception as exc:  # noqa: BLE001 — 后台任务须落库，不能静默丢
        logger.exception("终稿吸收抽取失败 · #%s", record_id)
        async with SessionLocal() as db:
            row = await db.get(FactoryThesisAbsorb, int(record_id))
            if not row:
                return
            msg = str(exc).strip() or exc.__class__.__name__
            await _mark_extract_failed(db, row, msg[:400])


async def create_from_upload(
    db: AsyncSession,
    *,
    filename: str,
    raw: bytes,
) -> dict[str, Any]:
    """收文件立刻入库（status=extracting），抽取改后台——对齐开题「落盘可离开」。"""
    from app.models import FactoryThesisAbsorb

    safe_name = Path(filename or "thesis.txt").name
    suffix = Path(safe_name).suffix.lower()
    if suffix not in {".txt", ".md", ".pdf", ".doc", ".docx"}:
        raise ValueError("仅支持 PDF / Word / TXT")

    digest = content_sha256(raw)
    dest_dir = _absorb_dir()
    row = FactoryThesisAbsorb(
        public_id=await alloc_ta_public_id(db),
        role="thesis",
        focus="thesis_impl",
        source_files=[safe_name],
        source_path="",
        proposal_json={},
        status="extracting",
        coverage="unknown",
        coverage_note="",
        coverage_machine="",
        coverage_review_json=[],
        extract_round=1,
        content_sha256=digest,
        extractor_version=EXTRACTOR_VERSION,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    final = dest_dir / f"{row.id}_{safe_name}"
    final.write_bytes(raw)
    row.source_path = str(final)
    await db.commit()
    await db.refresh(row)

    schedule_absorb_extract(int(row.id))
    return await get_record(db, row.id)  # type: ignore[return-value]


async def reextract(db: AsyncSession, record_id: int) -> dict[str, Any]:
    """标 extracting 后后台重抽；立即返回，前端轮询。"""
    from app.models import FactoryThesisAbsorb

    row = await db.get(FactoryThesisAbsorb, record_id)
    if not row:
        raise ValueError("未找到记录")
    path = Path(row.source_path or "")
    if not path.is_file():
        raise ValueError("源文件不在，无法重抽")

    prev_sha = row.content_sha256
    prev_ver = row.extractor_version
    row.extract_round = int(row.extract_round or 1) + 1
    row.coverage = "unknown"
    row.coverage_machine = ""
    row.coverage_review_json = []
    row.status = "extracting"
    await db.commit()
    await db.refresh(row)

    schedule_absorb_extract(int(row.id))
    out = await get_record(db, row.id)  # type: ignore[return-value]
    out["same_material_stable"] = False
    out["extractor_bumped"] = bool(prev_ver and prev_ver != EXTRACTOR_VERSION)
    out["extract_queued"] = True
    out["prev_content_sha256"] = prev_sha or ""
    out["figures_reused"] = False
    return out


def _row_needs_rule_reextract(row: Any) -> bool:
    """规则落后 / 结构缺键 / 三栏空 → 批量默认证件。

    实体与「××管理」词干重合 alone 不进队：现行规则下属常态，否则批量抽完条还在、越抽越冤。
    """
    outdated = _ver_int(getattr(row, "extractor_version", None)) < _ver_int(
        EXTRACTOR_VERSION
    )
    if outdated:
        return True
    if _proposal_missing_structure_hints(getattr(row, "proposal_json", None)):
        return True
    empty_drafts = (
        not _clean_draft_list(getattr(row, "draft_roles", None))
        and not _clean_draft_list(getattr(row, "draft_entities", None))
        and not _clean_draft_list(getattr(row, "draft_features", None))
    )
    return bool(empty_drafts)


async def reextract_batch(
    db: AsyncSession,
    *,
    mode: str = "outdated",
    ids: list[int] | None = None,
) -> dict[str, Any]:
    """批量排队重抽：默认只抽规则落后/结构残缺；串行执行防打爆。

    mode=outdated|all；ids 非空时只处理这些 id（仍受 mode 过滤，除非 mode=all）。
    """
    from app.models import FactoryThesisAbsorb

    mode_s = str(mode or "outdated").strip().lower()
    if mode_s not in ("outdated", "all"):
        raise ValueError("mode 须为 outdated 或 all")

    stmt = select(FactoryThesisAbsorb).order_by(FactoryThesisAbsorb.id.asc())
    rows = list((await db.execute(stmt)).scalars().all())
    id_set = {int(x) for x in (ids or []) if str(x).isdigit() or isinstance(x, int)}
    if id_set:
        rows = [r for r in rows if int(r.id) in id_set]

    queued: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for row in rows:
        rid = int(row.id)
        path = Path(row.source_path or "")
        if not path.is_file():
            skipped.append({"id": rid, "reason": "源文件不在"})
            continue
        if mode_s == "outdated" and not _row_needs_rule_reextract(row):
            skipped.append({"id": rid, "reason": "已是现行规则"})
            continue
        old = _extract_tasks.get(rid)
        if old is not None and not old.done():
            skipped.append({"id": rid, "reason": "已在抽取中"})
            continue
        prev_ver = row.extractor_version
        row.extract_round = int(row.extract_round or 1) + 1
        row.coverage = "unknown"
        row.coverage_machine = ""
        row.coverage_review_json = []
        row.status = "extracting"
        queued.append(
            {
                "id": rid,
                "public_id": str(getattr(row, "public_id", None) or ""),
                "from_version": str(prev_ver or ""),
                "to_version": EXTRACTOR_VERSION,
            }
        )
    if queued:
        await db.commit()
        for item in queued:
            schedule_absorb_extract(int(item["id"]))
    return {
        "mode": mode_s,
        "queued": queued,
        "skipped": skipped,
        "queued_count": len(queued),
        "skipped_count": len(skipped),
        "extractor_version": EXTRACTOR_VERSION,
        "message": (
            f"已排队 {len(queued)} 条重抽（现行 v{EXTRACTOR_VERSION}，串行）"
            if queued
            else "没有需要重抽的记录"
        ),
    }


async def update_record(
    db: AsyncSession,
    record_id: int,
    *,
    coverage: str | None = None,
    coverage_note: str | None = None,
    status: str | None = None,
    proposal: dict[str, Any] | None = None,
    draft_roles: list | None = None,
    draft_entities: list | None = None,
    draft_features: list | None = None,
    trial_project_id: str | None = None,
    mark_fed: bool = False,
) -> dict[str, Any]:
    from app.models import FactoryThesisAbsorb

    row = await db.get(FactoryThesisAbsorb, record_id)
    if not row:
        raise ValueError("未找到记录")
    if coverage is not None:
        if coverage not in COVERAGE_VALUES:
            raise ValueError(f"coverage 无效：{coverage}")
        before = str(row.coverage or "unknown")
        row.coverage = coverage
        if coverage != before:
            _append_coverage_review(
                row,
                before=before,
                after=coverage,
                note=(
                    coverage_note
                    if coverage_note is not None
                    else (row.coverage_note or "")
                ),
            )
        if coverage == "covered":
            row.status = "covered"
        elif row.status == "covered" and coverage != "covered":
            row.status = "stored"
    if coverage_note is not None:
        row.coverage_note = coverage_note[:512]
    if status is not None:
        if status not in STATUS_VALUES:
            raise ValueError(f"status 无效：{status}")
        row.status = status
    if proposal is not None:
        # 人工改结构：只允许 proposal 形状字段
        row.proposal_json = proposal
        fl = proposal.get("feature_lines") or []
        row.feature_line_count = len(fl)
        if len(fl) < 3:
            row.status = "review"
        elif row.status == "review":
            row.status = "stored"
        # 改结构后回退覆盖确认
        if row.coverage == "covered":
            _append_coverage_review(
                row, before="covered", after="unknown", note="改结构回退"
            )
            row.coverage = "unknown"
        if row.status in ("covered", "patched", "fed"):
            row.status = "stored"
    if draft_roles is not None:
        row.draft_roles = draft_roles
    if draft_entities is not None:
        row.draft_entities = draft_entities
    if draft_features is not None:
        row.draft_features = draft_features
    if trial_project_id is not None:
        row.trial_project_id = trial_project_id or None
    if mark_fed:
        row.status = "fed"
    await db.commit()
    await db.refresh(row)
    return await get_record(db, row.id)  # type: ignore[return-value]


async def delete_record(db: AsyncSession, record_id: int) -> bool:
    from app.models import FactoryThesisAbsorb

    row = await db.get(FactoryThesisAbsorb, record_id)
    if not row:
        return False
    path = Path(row.source_path or "")
    await db.delete(row)
    await db.commit()
    if path.is_file():
        try:
            path.unlink()
        except OSError:
            pass
    return True
