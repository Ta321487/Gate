"""开题功能行 ↔ 工厂 checklist 对照（规则层，不调 LLM）。

与 bake/gates/evaluate._checklist_feature_ok 共用同一套能力关键词口径，
避免生成前 diff 与包后门禁各说各话。
"""

from __future__ import annotations

import re
from typing import Any, Literal

MatchConfidence = Literal["exact", "substring", "hint", "token", "none"]

# 短词白名单：子串匹配时允许 <4 字
_SHORT_TERMS = frozenset(
    {
        "登录",
        "注册",
        "公告",
        "分类",
        "审核",
        "驳回",
        "归还",
        "借阅",
        "报修",
        "预约",
        "下单",
        "跟进",
        "档案",
        "销假",
        "请假",
        "投递",
        "检索",
        "浏览",
        "公告",
    }
)

# 单独命中不足以认定对照（同名不同义时宁可漏报、不误绿）
_GENERIC_TOKENS = frozenset(
    {
        "管理",
        "查询",
        "统计",
        "信息",
        "系统",
        "功能",
        "模块",
        "业务",
        "数据",
        "维护",
        "发布",
        "查阅",
        "展示",
        "用户",
        "记录",
        "申请",
        "提交",
        "审核",
        "浏览",
        "检索",
        "查看",
        "台账",
        "通知",
        "资料",
        "详情",
        "列表",
        "操作",
    }
)

_PUNCT_RE = re.compile(r"[，,。．.;；:：、/\\|（）()【】\[\]《》「」『』\-—·\s]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]{2,8}")


def normalize_text(text: str) -> str:
    s = re.sub(r"\s+", "", (text or "").strip().lower())
    return s[:120]


def split_clauses(text: str) -> list[str]:
    """长功能行按标点拆句，便于一句对照多项 checklist。"""
    raw = (text or "").strip()
    if not raw:
        return []
    parts = [p.strip() for p in _PUNCT_RE.split(raw) if p.strip()]
    return parts or [raw]


def extract_tokens(text: str) -> set[str]:
    norm = normalize_text(text)
    tokens = set(_CJK_RE.findall(norm))
    for short in _SHORT_TERMS:
        if short in norm:
            tokens.add(short)
    return {t for t in tokens if t}


def feature_hints(feature_name: str) -> set[str]:
    """从 checklist 项名派生可命中开题多样措辞的提示词（跨域通用）。"""
    name = (feature_name or "").strip()
    if not name:
        return set()
    hints: set[str] = {name}
    norm = normalize_text(name)

    if "登录" in name or "注册" in name:
        hints.update({"登录", "注册", "鉴权", "签到"})
    if "个人资料" in name or "头像" in name:
        hints.update({"个人资料", "资料维护", "资料", "头像", "读者证", "班级信息"})
    if "工作台" in name or "概览" in name or "驾驶舱" in name:
        hints.update({"工作台", "概览", "驾驶舱", "业务概览", "统计图表", "统计"})
    if "公告" in name:
        hints.update({"公告", "通知", "公示"})
    if any(k in name for k in ("用户管理", "读者管理", "学生管理", "会员管理", "患者管理")):
        hints.update(
            {
                "用户管理",
                "用户信息",
                "人员档案",
                "读者管理",
                "学生管理",
                "会员管理",
                "人员管理",
            }
        )
    if "分类" in name:
        hints.update({"分类", "类别"})
    if "记录" in name:
        hints.update({"记录", "台账", "历史", "查询"})
    if any(k in name for k in ("档案", "检索", "详情", "书目", "器材", "物资", "商品", "岗位", "客户", "会员", "图书", "设备", "菜品", "号源", "车位", "场地", "建档")):
        hints.update({"档案", "检索", "浏览", "录入", "维护", "详情", "书目", "建档"})
    if any(
        k in name
        for k in (
            "跟进",
            "借阅",
            "报修",
            "申领",
            "请假",
            "投递",
            "预约",
            "下单",
            "购物车",
            "订单",
            "销假",
            "归还",
            "审核",
        )
    ):
        hints.update(
            {
                "提交",
                "审核",
                "审批",
                "驳回",
                "办结",
                "完结",
                "入档",
                "销假",
                "归还",
                "占用",
                "出库",
                "派工",
            }
        )
    if "推荐" in name or "猜你喜欢" in name:
        hints.update({"推荐", "猜你喜欢", "书目展示"})
    if "逾期" in name or "罚款" in name or "提醒" in name:
        hints.update({"逾期", "罚款", "提醒", "应还"})
    if "购物车" in name or "下单" in name or ("订单" in name and "记录" not in name):
        hints.update({"购物车", "下单", "订单", "结算"})
    if "预约" in name:
        hints.update({"预约", "号源", "场次", "名额"})

    # 项名本身拆词
    hints.update(extract_tokens(name))
    return {normalize_text(h) for h in hints if h and normalize_text(h)}


def _distinctive_hints(hints: set[str], feature_name: str) -> set[str]:
    out = {h for h in hints if h not in _GENERIC_TOKENS and len(h) >= 2}
    for short in _SHORT_TERMS:
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
        if hit_hints[0] in _SHORT_TERMS:
            return (75, "hint", f"能力词：{hit_hints[0]}")

    feat_tokens = extract_tokens(feature_name)
    line_tokens = extract_tokens(line)
    shared = feat_tokens & line_tokens
    shared_distinct = {t for t in shared if t not in _GENERIC_TOKENS}
    if shared_distinct:
        if len(shared_distinct) >= 2:
            return (70, "token", f"关键词：{'、'.join(sorted(shared_distinct)[:3])}")
        tok = next(iter(shared_distinct))
        if len(tok) >= 4 or tok in _SHORT_TERMS:
            return (60, "token", f"关键词：{tok}")

    # 复合项：项名中多个实词在线里分散出现（如「客户分类与档案维护」↔ 客户档案+分类管理）
    parts = [p for p in re.split(r"[与及/→\-—]", normalize_text(feature_name)) if len(p) >= 2]
    if len(parts) >= 2 and all(any(p in t or t in p for t in line_tokens | {n_line}) for p in parts):
        return (55, "token", "项名分段共现")

    for feat in hints:
        if len(feat) >= 4 and (feat in n_line or n_line in feat):
            if feat not in _GENERIC_TOKENS:
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
    # 保留与最佳同档或接近的命中（一句可覆盖多项 baseline/module）
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
        # 低置信：同名不同实现风险，生成前提示人工扫一眼
        return ("review", links)
    return ("unmatched", links)
