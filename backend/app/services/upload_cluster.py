"""多材料上传：剔除非毕设 + 按课题聚类（规则 + 可选 LLM 结构输出）。"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.bake.catalog import extract_title
from app.core.config import get_settings
from app.services.proposal import (
    business_signal_score,
    extract_module_lines,
    extract_table_features,
    read_proposal,
    strip_non_dev_sections,
)

# 能力/对象词：指纹用（同域不同实现靠差集拆开）
_CAP_TERMS = (
    "借阅", "归还", "逾期", "罚金", "续借", "预约", "挂号", "排队",
    "报修", "派工", "申领", "审核", "领用", "库存", "订单", "购物车",
    "下单", "配送", "外卖", "点餐", "口味", "优惠券", "积分", "会员",
    "收藏", "留言", "评价", "选课", "报名", "签到", "跟进", "客户",
    "失物", "认领", "二手", "支付", "退款", "车位", "车牌", "会议室",
    "客房", "理发", "设备", "物资", "宿舍", "物业", "论坛", "帖子",
    "博客", "媒资", "音乐", "图集", "足迹", "搜索",
)

_TITLE_PREFIX = re.compile(r"^基于[\w\-＋+、/．.\s]{2,36}?的")
_TITLE_SUFFIX = re.compile(
    r"(?:的设计与实现|的设计与开发|系统设计与实现|"
    r"(?:信息)?管理系统|管理系统|系统|平台|网站)$"
)

_ROLE_TASK = re.compile(r"任务书|指导教师意见|进度安排")
_ROLE_LIST = re.compile(r"功能清单|功能列表|用例列表|需求列表|模块划分")
_ROLE_PROP = re.compile(r"开题|选题背景|研究意义|国内外研究现状")


@dataclass
class DocProfile:
    index: int
    name: str
    path: str
    size: int
    signal: int
    role: str  # proposal | taskbook | checklist | unknown
    title: str
    title_key: str
    fingerprint: list[str]
    excerpt: str
    chars: int


@dataclass
class ClusterPlan:
    plan_id: str
    source: str  # llm | rules
    files: list[dict[str, Any]]
    discard: list[dict[str, Any]]
    clusters: list[dict[str, Any]]
    notes: str = ""
    llm_ok: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_title_key(title: str) -> str:
    t = (title or "").strip()
    # 先去尾缀，再去「基于…的」前缀（前缀必须非贪婪，否则会吞掉题名里的「的」）
    for _ in range(3):
        nxt = _TITLE_SUFFIX.sub("", t)
        nxt = _TITLE_PREFIX.sub("", nxt)
        if nxt == t:
            break
        t = nxt
    t = re.sub(r"[\s\-_/\\|·•，,。．.：:；;（）()【】\[\]]+", "", t)
    return t.lower()


def guess_role(name: str, text: str) -> str:
    blob = f"{name}\n{(text or '')[:2500]}"
    has_prop = bool(_ROLE_PROP.search(blob) or "开题" in name or "开题报告" in blob[:200])
    has_list = bool(
        _ROLE_LIST.search(blob)
        or len(extract_table_features(text or "")) >= 3
    )
    # 完整开题里偶尔写「功能清单」字样，仍算开题
    if has_prop and len((text or "").strip()) >= 400:
        return "proposal"
    if has_list and ("功能清单" in blob or len(extract_table_features(text or "")) >= 3):
        return "checklist"
    if _ROLE_TASK.search(name) or (
        _ROLE_TASK.search(blob) and not _ROLE_PROP.search(blob[:800])
    ):
        return "taskbook"
    if has_prop:
        return "proposal"
    if extract_module_lines(text or "")[:2] and business_signal_score(text or "") >= 6:
        return "checklist"
    return "unknown"


def extract_fingerprint(text: str, *, limit: int = 24) -> list[str]:
    body = strip_non_dev_sections(text or "")
    tokens: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        s = re.sub(r"\s+", "", (raw or "").strip())
        if len(s) < 2 or len(s) > 24:
            return
        key = s.lower()
        if key in seen:
            return
        seen.add(key)
        tokens.append(s)

    for m in extract_module_lines(body)[:12]:
        add(m.replace("模块", ""))
    for t in extract_table_features(body)[:16]:
        add(t.split("：")[0] if "：" in t else t)
    for kw in _CAP_TERMS:
        # 否定句里的能力词不进指纹（避免「不实现借阅」污染二手交易）
        if not re.search(
            rf"(?:不(?:实现|包含|做|再)|而非|禁止|无需).{{0,12}}{re.escape(kw)}|{re.escape(kw)}.{{0,6}}(?:不在本期|不做)",
            body,
        ) and kw in body:
            add(kw)
    return tokens[:limit]


def build_profiles(
    files: list[tuple[Path, str, int]],
) -> list[DocProfile]:
    out: list[DocProfile] = []
    for i, (path, name, size) in enumerate(files):
        raw = read_proposal(path)
        body = strip_non_dev_sections(raw)
        title = extract_title(raw, fallback="")
        if not title or title == "未命名毕设项目":
            stem = Path(name).stem
            title = stem if len(stem) >= 4 else ""
        fp = extract_fingerprint(raw)
        signal = business_signal_score(raw)
        excerpt = re.sub(r"\s+", " ", body.strip())[:600]
        out.append(
            DocProfile(
                index=i,
                name=name,
                path=str(path),
                size=int(size or 0),
                signal=signal,
                role=guess_role(name, raw),
                title=title or Path(name).stem,
                title_key=normalize_title_key(title or Path(name).stem),
                fingerprint=fp,
                excerpt=excerpt,
                chars=len(body),
            )
        )
    return out


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _title_similar(a: str, b: str) -> bool:
    """题目锚是否够像（偏严：避免「…管理系统」互相误并）。"""
    if not a or not b:
        return False
    if a == b:
        return True
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    # 短串整段落入长串，且短串足够有辨识度
    if len(short) >= 6 and short in long:
        return True

    def grams(s: str) -> set[str]:
        s = s.lower()
        if len(s) < 2:
            return {s}
        return {s[i : i + 2] for i in range(len(s) - 1)}

    # 提高阈值，减少「图书/管理」等弱重叠误并
    return _jaccard(grams(a), grams(b)) >= 0.72


def _fps_conflict(a: set[str], b: set[str]) -> bool:
    """两边能力指纹都够丰富却几乎不重叠 → 视为不同实现。"""
    return len(a) >= 4 and len(b) >= 4 and _jaccard(a, b) < 0.22


def _is_main_proposal(p: DocProfile) -> bool:
    return p.role == "proposal" and p.signal >= 5 and p.chars >= 400


def rule_cluster(profiles: list[DocProfile]) -> tuple[list[list[int]], list[int], str]:
    """保守规则聚类：宁可多项目。返回 (clusters, discard_indices, notes)。"""
    discard: list[int] = []
    keep: list[DocProfile] = []
    for p in profiles:
        if p.signal < 3 and p.chars < 200:
            discard.append(p.index)
        elif p.signal < 2:
            discard.append(p.index)
        else:
            keep.append(p)

    if not keep:
        return [], discard, "业务信号均偏弱，未形成可匹配项目"

    # 以「开题/有题名」为锚建簇
    anchors: list[DocProfile] = []
    satellites: list[DocProfile] = []
    for p in keep:
        if p.role in ("taskbook", "checklist"):
            satellites.append(p)
        else:
            anchors.append(p)

    # 锚之间：两份主开题须题目够像且指纹不冲突；否则偏拆
    clusters: list[list[DocProfile]] = []
    for a in anchors:
        placed = False
        for cl in clusters:
            head = cl[0]
            fa, fb = set(a.fingerprint), set(head.fingerprint)
            title_ok = _title_similar(a.title_key, head.title_key)
            both_main = _is_main_proposal(a) and _is_main_proposal(head)
            if both_main and not title_ok:
                continue
            if _fps_conflict(fa, fb):
                continue
            jac = _jaccard(fa, fb)
            if both_main:
                # 主开题：题目像 + 指纹不冲突即可并（清单挂靠另走）
                if title_ok:
                    cl.append(a)
                    placed = True
                    break
                continue
            if title_ok or jac >= 0.45:
                cl.append(a)
                placed = True
                break
        if not placed:
            clusters.append([a])

    # 卫星挂靠：题目像或指纹重叠；指纹硬冲突则不挂
    orphan_sats: list[DocProfile] = []
    for s in satellites:
        best_i = -1
        best_score = 0.0
        for i, cl in enumerate(clusters):
            head = cl[0]
            fa, fb = set(s.fingerprint), set(head.fingerprint)
            if _fps_conflict(fa, fb):
                continue
            score = 0.0
            if _title_similar(s.title_key, head.title_key):
                score += 0.6
            jac = _jaccard(fa, fb)
            score += jac
            if jac >= 0.2:
                score += 0.15
            # 题目不像时，要求指纹明显重叠才挂靠（防同域不同实现挂错）
            if not _title_similar(s.title_key, head.title_key) and jac < 0.4:
                continue
            if score > best_score:
                best_score = score
                best_i = i
        if best_i >= 0 and best_score >= 0.35:
            clusters[best_i].append(s)
        else:
            orphan_sats.append(s)

    for s in orphan_sats:
        clusters.append([s])

    out_clusters = [[p.index for p in cl] for cl in clusters]
    notes = (
        f"规则分堆：保留 {len(keep)} 份、剔除 {len(discard)} 份、"
        f"形成 {len(out_clusters)} 个项目（偏保守）"
    )
    return out_clusters, discard, notes


def validate_cluster_payload(
    profiles: list[DocProfile],
    data: dict[str, Any],
) -> tuple[list[list[int]], list[int], str] | None:
    """校验 LLM 结构输出；不合规则返回 None。"""
    if not isinstance(data, dict):
        return None
    n = len(profiles)
    raw_discard = data.get("discard") or []
    raw_clusters = data.get("clusters") or []
    if not isinstance(raw_discard, list) or not isinstance(raw_clusters, list):
        return None

    discard: list[int] = []
    for x in raw_discard:
        try:
            i = int(x)
        except (TypeError, ValueError):
            return None
        if i < 0 or i >= n:
            return None
        discard.append(i)
    discard = sorted(set(discard))

    clusters: list[list[int]] = []
    seen: set[int] = set(discard)
    for c in raw_clusters:
        files = c.get("files") if isinstance(c, dict) else c
        if not isinstance(files, list) or not files:
            return None
        idxs: list[int] = []
        for x in files:
            try:
                i = int(x)
            except (TypeError, ValueError):
                return None
            if i < 0 or i >= n or i in seen:
                return None
            seen.add(i)
            idxs.append(i)
        clusters.append(idxs)

    # 每个非 discard 必须恰好出现一次
    for i in range(n):
        if i not in seen:
            return None

    # 硬否决：两份主开题题目不同却同簇
    by_idx = {p.index: p for p in profiles}
    for cl in clusters:
        mains = [by_idx[i] for i in cl if _is_main_proposal(by_idx[i])]
        for a in range(len(mains)):
            for b in range(a + 1, len(mains)):
                if not _title_similar(mains[a].title_key, mains[b].title_key):
                    return None
        # 指纹硬冲突
        rich = [by_idx[i] for i in cl if len(by_idx[i].fingerprint) >= 4]
        for a in range(len(rich)):
            for b in range(a + 1, len(rich)):
                jac = _jaccard(set(rich[a].fingerprint), set(rich[b].fingerprint))
                if jac < 0.18 and not _title_similar(rich[a].title_key, rich[b].title_key):
                    return None

    notes = str(data.get("notes") or "").strip()[:240]
    return clusters, discard, notes


def reason_for_cluster(profiles: list[DocProfile], idxs: list[int]) -> str:
    ps = [p for p in profiles if p.index in idxs]
    if not ps:
        return ""
    roles = sorted({p.role for p in ps})
    if len(ps) == 1:
        role = ps[0].role
        return {
            "proposal": "独立开题材料",
            "taskbook": "独立任务书",
            "checklist": "独立功能清单",
        }.get(role, "独立材料")
    role_txt = "、".join(
        {"proposal": "开题", "taskbook": "任务书", "checklist": "清单"}.get(r, r)
        for r in roles
    )
    fps: set[str] = set()
    for p in ps:
        fps.update(p.fingerprint[:6])
    tip = "、".join(list(fps)[:5])
    base = f"同课题合并（{role_txt}）"
    return f"{base}；能力含 {tip}" if tip else base


def assemble_plan(
    plan_id: str,
    profiles: list[DocProfile],
    clusters: list[list[int]],
    discard: list[int],
    *,
    source: str,
    notes: str,
    llm_ok: bool,
    llm_reasons: dict[str, str] | None = None,
) -> ClusterPlan:
    by_idx = {p.index: p for p in profiles}
    discard_rows = []
    for i in discard:
        p = by_idx[i]
        discard_rows.append(
            {
                "index": i,
                "name": p.name,
                "reason": f"业务信号弱（score={p.signal}）或非毕设材料",
            }
        )
    cluster_rows = []
    for ci, idxs in enumerate(clusters):
        reason = (llm_reasons or {}).get(str(ci)) or reason_for_cluster(profiles, idxs)
        files = []
        label_title = ""
        for i in idxs:
            p = by_idx[i]
            files.append(
                {
                    "index": i,
                    "name": p.name,
                    "role": p.role,
                    "title": p.title,
                    "signal": p.signal,
                    "fingerprint": p.fingerprint[:12],
                }
            )
            if not label_title and p.role == "proposal":
                label_title = p.title
        if not label_title and files:
            label_title = files[0]["title"]
        cluster_rows.append(
            {
                "id": ci + 1,
                "label": label_title or f"项目 {ci + 1}",
                "reason": reason,
                "files": files,
            }
        )
    file_rows = [
        {
            "index": p.index,
            "name": p.name,
            "role": p.role,
            "title": p.title,
            "signal": p.signal,
            "fingerprint": p.fingerprint[:12],
            "chars": p.chars,
        }
        for p in profiles
    ]
    return ClusterPlan(
        plan_id=plan_id,
        source=source,
        files=file_rows,
        discard=discard_rows,
        clusters=cluster_rows,
        notes=notes,
        llm_ok=llm_ok,
    )


def save_plan_bundle(
    files: list[tuple[Path, str, int]],
    plan: ClusterPlan,
) -> Path:
    """files 已落在 plan 目录内；写 manifest。"""
    settings = get_settings()
    root = settings.uploads_dir / "plans" / plan.plan_id
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "plan_id": plan.plan_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": [
            {"name": name, "rel": Path(path).name, "size": size}
            for path, name, size in files
        ],
        "plan": plan.to_dict(),
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return root


def load_plan_bundle(plan_id: str) -> tuple[Path, dict[str, Any], list[tuple[Path, str, int]]]:
    settings = get_settings()
    root = settings.uploads_dir / "plans" / plan_id
    man = root / "manifest.json"
    if not man.exists():
        raise FileNotFoundError("分堆方案不存在或已过期")
    data = json.loads(man.read_text(encoding="utf-8"))
    files: list[tuple[Path, str, int]] = []
    for row in data.get("files") or []:
        rel = row.get("rel") or row.get("name")
        path = root / rel
        if not path.exists():
            raise FileNotFoundError(f"材料缺失：{rel}")
        files.append((path, str(row.get("name") or rel), int(row.get("size") or path.stat().st_size)))
    return root, data, files


def apply_overrides(
    plan: dict[str, Any],
    *,
    clusters: list[list[int]] | None,
    discard: list[int] | None,
) -> dict[str, Any]:
    """确认时可覆盖分堆（索引基于原 files）。"""
    n = len(plan.get("files") or [])
    if clusters is None and discard is None:
        return plan
    disc = list(discard) if discard is not None else [d["index"] for d in plan.get("discard") or []]
    disc = sorted({i for i in disc if 0 <= i < n})
    if clusters is None:
        # 保留原簇，去掉 discard
        clusters = []
        for c in plan.get("clusters") or []:
            idxs = [f["index"] for f in c.get("files") or [] if f["index"] not in disc]
            if idxs:
                clusters.append(idxs)
    else:
        clusters = [[i for i in cl if 0 <= i < n and i not in disc] for cl in clusters]
        clusters = [cl for cl in clusters if cl]

    seen = set(disc)
    for cl in clusters:
        for i in cl:
            if i in seen:
                raise ValueError("分堆索引重复或与剔除冲突")
            seen.add(i)
    for i in range(n):
        if i not in seen:
            raise ValueError(f"文件索引 {i} 未归入任何项目且未剔除")

    # 重建 plan 行（保留原 file 元数据）
    by_idx = {f["index"]: f for f in plan.get("files") or []}
    plan = dict(plan)
    plan["discard"] = [
        {
            "index": i,
            "name": by_idx.get(i, {}).get("name", f"#{i}"),
            "reason": "确认时剔除",
        }
        for i in disc
    ]
    new_clusters = []
    for ci, idxs in enumerate(clusters):
        files = [by_idx[i] for i in idxs if i in by_idx]
        label = next((f.get("title") for f in files if f.get("role") == "proposal"), None)
        if not label and files:
            label = files[0].get("title") or files[0].get("name")
        new_clusters.append(
            {
                "id": ci + 1,
                "label": label or f"项目 {ci + 1}",
                "reason": "人工确认调整后的分堆",
                "files": files,
            }
        )
    plan["clusters"] = new_clusters
    plan["source"] = "confirmed"
    return plan


async def build_upload_plan(
    files: list[tuple[Path, str, int]],
    *,
    db=None,
    llm_rt=None,
) -> ClusterPlan:
    """读材料 → 规则分堆 → 可选 LLM 结构分堆（失败回落规则）。"""
    plan_id = uuid.uuid4().hex[:12]
    profiles = build_profiles(files)
    rule_clusters, rule_discard, rule_notes = rule_cluster(profiles)
    llm_reasons: dict[str, str] = {}

    clusters, discard, notes, source, llm_ok = (
        rule_clusters,
        rule_discard,
        rule_notes,
        "rules",
        False,
    )

    if llm_rt is not None and getattr(llm_rt, "configured", False) and len(profiles) >= 1:
        try:
            from app.llm.agents import run_upload_cluster_agent

            data = await run_upload_cluster_agent(
                db, llm_rt, plan_id=plan_id, profiles=profiles
            )
            validated = validate_cluster_payload(profiles, data) if data else None
            if validated:
                clusters, discard, llm_notes = validated
                notes = llm_notes or rule_notes
                source = "llm"
                llm_ok = True
                for i, c in enumerate(data.get("clusters") or []):
                    if isinstance(c, dict) and c.get("reason"):
                        llm_reasons[str(i)] = str(c["reason"])[:160]
            else:
                notes = rule_notes + "；LLM 分堆未通过校验，已用规则结果"
        except Exception:  # noqa: BLE001
            notes = rule_notes + "；LLM 分堆失败，已用规则结果"

    return assemble_plan(
        plan_id,
        profiles,
        clusters,
        discard,
        source=source,
        notes=notes,
        llm_ok=llm_ok,
        llm_reasons=llm_reasons,
    )
