"""开题功能行 ↔ 工厂 checklist 对照（规则层，不调 LLM）。

文本层对照见 `bake.gates.feature_keywords`；包后实装判定见 `bake.gates.evaluate._checklist_feature_ok`。
两层职责不同，共享同一套能力触发词表，避免 diff 与门禁各说各话。
"""

from __future__ import annotations

import re
from typing import Any, Literal

from app.bake.gates.feature_keywords import (
    GENERIC_TOKENS,
    SHORT_TERMS,
    extract_tokens,
    feature_hints,
    normalize_text,
)

MatchConfidence = Literal["exact", "substring", "hint", "token", "none"]

_PUNCT_RE = re.compile(r"[，,。．.;；:：、/\\|（）()【】\[\]《》「」『』\-—·\s]+")


def split_clauses(text: str) -> list[str]:
    """长功能行按标点拆句，便于一句对照多项 checklist。"""
    raw = (text or "").strip()
    if not raw:
        return []
    parts = [p.strip() for p in _PUNCT_RE.split(raw) if p.strip()]
    return parts or [raw]


def _distinctive_hints(hints: set[str], feature_name: str) -> set[str]:
    out = {h for h in hints if h not in GENERIC_TOKENS and len(h) >= 2}
    for short in SHORT_TERMS:
        if short in normalize_text(feature_name) and short in hints:
            out.add(short)
    return out


def score_line_feature(line: str, feature_name: str) -> tuple[int, MatchConfidence, str]:
    """返回 (分数, 置信度, 原因)。分数<=0 表示未命中。"""
    n_line = normalize_text(line)
    n_feat = normalize_text(feature_name)
    if not n_line or not n_feat:
        return (0, "none", "")

    if n_line == n_feat:
        return (100, "exact", "文案一致")
    if n_feat in n_line or n_line in n_feat:
        return (90, "substring", "包含 checklist 项名")

    hints = feature_hints(feature_name)
    distinctive = _distinctive_hints(hints, feature_name)
    hit_hints = [h for h in sorted(distinctive, key=len, reverse=True) if h in n_line]
    if hit_hints:
        if len(hit_hints) >= 2 or any(len(h) >= 4 for h in hit_hints):
            return (80, "hint", f"能力词：{'、'.join(hit_hints[:3])}")
        if hit_hints[0] in SHORT_TERMS:
            return (75, "hint", f"能力词：{hit_hints[0]}")

    feat_tokens = extract_tokens(feature_name)
    line_tokens = extract_tokens(line)
    shared = feat_tokens & line_tokens
    shared_distinct = {t for t in shared if t not in GENERIC_TOKENS}
    if shared_distinct:
        if len(shared_distinct) >= 2:
            return (70, "token", f"关键词：{'、'.join(sorted(shared_distinct)[:3])}")
        tok = next(iter(shared_distinct))
        if len(tok) >= 4 or tok in SHORT_TERMS:
            return (60, "token", f"关键词：{tok}")

    parts = [p for p in re.split(r"[与及/→\-—]", normalize_text(feature_name)) if len(p) >= 2]
    if len(parts) >= 2 and all(any(p in t or t in p for t in line_tokens | {n_line}) for p in parts):
        return (55, "token", "项名分段共现")

    for feat in hints:
        if len(feat) >= 4 and (feat in n_line or n_line in feat):
            if feat not in GENERIC_TOKENS:
                return (50, "substring", f"能力短语：{feat}")

    return (0, "none", "")


def match_line_to_features(
    line: str,
    features: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """一行开题功能 → 最佳 checklist 命中（可多项）。"""
    scored: list[tuple[int, MatchConfidence, str, str, dict[str, Any]]] = []
    for feat in features:
        if not isinstance(feat, dict):
            continue
        name = str(feat.get("name") or "").strip()
        if not name or feat.get("status") == "out_of_mvp":
            continue
        for clause in split_clauses(line):
            score, conf, reason = score_line_feature(clause, name)
            if score > 0:
                scored.append((score, conf, reason, name, feat))
    if not scored:
        return []

    scored.sort(key=lambda x: (-x[0], x[3]))
    best = scored[0][0]
    floor = max(best - 15, 55)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for score, conf, reason, name, feat in scored:
        if score < floor:
            break
        if name in seen:
            continue
        seen.add(name)
        out.append(
            {
                "feature": name,
                "status": feat.get("status"),
                "confidence": conf,
                "score": score,
                "reason": reason,
            }
        )
    return out


def classify_line_match(
    line: str,
    features: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """返回 (matched|review|unmatched, links)。"""
    links = match_line_to_features(line, features)
    if not links:
        return ("unmatched", [])

    best = links[0]
    if best["confidence"] in ("exact", "substring") or best["score"] >= 75:
        return ("matched", links)
    if best["score"] >= 55:
        return ("review", links)
    return ("unmatched", links)
