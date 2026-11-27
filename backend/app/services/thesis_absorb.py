"""终稿吸收厂库：CRUD / 上传入库 / 重抽 / 喂助手稿 / 重叠提示。

不建 Project、不跑 proposal_match。口径：docs/thesis-absorb.md。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
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


def coverage_domain_hints(
    proposal: dict[str, Any] | None,
    *,
    draft_roles: list[str] | None = None,
    top_n: int = COVERAGE_HINTS_TOP_N,
) -> list[dict[str, Any]]:
    """功能清单 → 现厂挂靠候选（确定性，同材同果）。

    复用目录关键词打分；不写库、不算出包 hits。文本用 feature_lines + 角色，不用题名/届次。
    """
    from app.bake.capabilities import CAPABILITIES
    from app.bake.catalog import _catalog_scores
    from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS

    prop = proposal if isinstance(proposal, dict) else {}
    parts: list[str] = []
    for key in ("feature_lines", "role_hints", "roles"):
        for x in list(prop.get(key) or []):
            if isinstance(x, str) and x.strip():
                parts.append(x.strip())
    for x in list(draft_roles or []):
        if isinstance(x, str) and x.strip():
            parts.append(x.strip())
    text = "\n".join(parts)
    if not text.strip():
        return []

    scored = _catalog_scores(text, DOMAINS)
    scored.sort(
        key=lambda t: (-t[1], -len(t[2]), -sum(len(h) for h in t[2]), t[0]),
    )
    positive = [(k, s, h) for k, s, h in scored if s > 0]
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
        "采信规则：优先【主候选】；仅主候选分≥2 才可考虑 covered；"
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
    # 抽取进行中：草稿必空，完整诊断无意义且拖轮询；禁止误标「要点偏少」
    if light or str(row.status or "") == "extracting":
        item = _row_to_dict(row)
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
    need_reextract = bool(
        outdated or missing_hints or stem_entity_drafts or empty_drafts
    )
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
    if stem_entity_drafts:
        reasons.append("实体栏仍像功能词干")
    item["reextract_reasons"] = reasons
    # 现厂速查：确定性短表，同材同果；不写库、不算出包 hits
    item["coverage_hints"] = coverage_domain_hints(
        prop,
        draft_roles=item.get("draft_roles"),
    )
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
    note = str(out.get("coverage_note") or "").strip()
    if note:
        row.coverage_note = note[:500]
    # 功能主清单：LLM 跑过就整表替换（含空），禁止残留正则假清单
    pj = dict(row.proposal_json) if isinstance(row.proposal_json, dict) else {}
    pj["absorb_used_llm"] = bool(out.get("used_llm"))
    skip = str(out.get("skip_reason") or "").strip()
    if skip:
        pj["absorb_llm_skip"] = skip
    elif "absorb_llm_skip" in pj:
        pj.pop("absorb_llm_skip", None)
    if out.get("used_llm"):
        pj["feature_lines"] = list(row.draft_features or [])
        row.feature_line_count = len(pj["feature_lines"])
        row.proposal_json = pj
    else:
        pj["feature_lines"] = []
        row.feature_line_count = 0
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
    if out.get("used_llm") and cov == "covered":
        row.status = "covered"
    elif row.status in ("extracting",):
        row.status = "stored"


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
        row.coverage = coverage
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
