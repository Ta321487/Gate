"""bake 失败码分类：与 docs/bake-fail-analysis.md 同源。

A 档修法只读 FIX_LOCUS；大模型不得改写本模块常量。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

# 机器真源：改码须同步 docs/bake-fail-analysis.md + tests/test_bake_fail_classify.py
CODES: tuple[str, ...] = (
    "OPS_RESTART",
    "OPS_CANCELLED",
    "OPS_PROJECT_MISSING",
    "OPS_REVIEW_LOCK",
    "RESUME_NO_WORKSPACE",
    "BAKE_SCHEMA_NF",
    "BAKE_TABLE_BUDGET",
    "BAKE_ARCHIVE_COLUMNS",
    "BAKE_ARCHIVE_SEED",
    "BAKE_IDENTITY",
    "BAKE_MENU_ROUTES",
    "BAKE_HARD_ASSERT_UI",
    "BAKE_SKIN",
    "BAKE_TRADE_SURFACE",
    "BAKE_USECASE",
    "BAKE_PERSISTENCE",
    "BAKE_ADDON_SECURITY",
    "BAKE_PACK_LEAN",
    "FILL_MERGE",
    "BUILD_SKELETON",
    "BUILD_COMPILE",
    "GATE_ACCEPT",
    "GATE_SCHEMA",
    "GATE_E2E_PATH",
    "GATE_ADMIN_BOUNDARY",
    "GATE_STUDENT_COPY",
    "GATE_SEMANTIC",
    "GATE_CHECKLIST",
    "GATE_QA",
    "GATE_GENERIC_UNREALIZED",
    "GATE_OVERALL",
    "MATCH_PATH",
    "STUDENT_DB",
    "UNKNOWN",
)

LABELS: dict[str, str] = {
    "OPS_RESTART": "服务重启中断",
    "OPS_CANCELLED": "已取消",
    "OPS_PROJECT_MISSING": "项目不存在",
    "OPS_REVIEW_LOCK": "交付复审锁",
    "RESUME_NO_WORKSPACE": "续跑无工作区",
    "BAKE_SCHEMA_NF": "库表 3NF",
    "BAKE_TABLE_BUDGET": "表数量预算",
    "BAKE_ARCHIVE_COLUMNS": "档案语义列",
    "BAKE_ARCHIVE_SEED": "档案演示种子",
    "BAKE_IDENTITY": "身份/壳对齐",
    "BAKE_MENU_ROUTES": "菜单/路由对齐",
    "BAKE_HARD_ASSERT_UI": "硬拦与收集 UI",
    "BAKE_SKIN": "错皮/怪交互硬闸",
    "BAKE_TRADE_SURFACE": "交易表面契约",
    "BAKE_USECASE": "用例图构建",
    "BAKE_PERSISTENCE": "持久化叠层残留",
    "BAKE_ADDON_SECURITY": "Security 叠层",
    "BAKE_PACK_LEAN": "学生包瘦身",
    "FILL_MERGE": "填岛合并",
    "BUILD_SKELETON": "骨架不完整",
    "BUILD_COMPILE": "编译失败",
    "GATE_ACCEPT": "可接题边界",
    "GATE_SCHEMA": "Domain Schema / 契约",
    "GATE_E2E_PATH": "主流程 E2E",
    "GATE_ADMIN_BOUNDARY": "总管/子管边界",
    "GATE_STUDENT_COPY": "学生可见文案",
    "GATE_SEMANTIC": "交付语义/场景",
    "GATE_CHECKLIST": "清单实装",
    "GATE_QA": "交付质量摘要",
    "GATE_GENERIC_UNREALIZED": "领域尚未做实",
    "GATE_OVERALL": "质量检查未通过",
    "MATCH_PATH": "身份/主路径入口",
    "STUDENT_DB": "学生库（当前非拦包）",
    "UNKNOWN": "待补码表",
}

# A 档权威落点：空白优于假话；UNKNOWN 固定待补
FIX_LOCUS: dict[str, str] = {
    "OPS_RESTART": "backend/app/services/jobs.py · 孤儿任务收口",
    "OPS_CANCELLED": "backend/app/services/jobs.py · cancel_job",
    "OPS_PROJECT_MISSING": "backend/app/services/jobs.py · run_job",
    "OPS_REVIEW_LOCK": "backend/app/services/delivery_review.py · forbid_full_rebake",
    "RESUME_NO_WORKSPACE": "backend/app/services/jobs.py · 续跑工作区",
    "BAKE_SCHEMA_NF": "backend/app/bake/gates/schema_nf.py",
    "BAKE_TABLE_BUDGET": "backend/app/bake/engine_sql.py · 表预算",
    "BAKE_ARCHIVE_COLUMNS": "backend/app/bake/archive_columns.py",
    "BAKE_ARCHIVE_SEED": "backend/app/bake/archive_seed_guard.py",
    "BAKE_IDENTITY": "backend/app/bake/identity_align.py",
    "BAKE_MENU_ROUTES": "backend/app/bake/menu_routes.py",
    "BAKE_HARD_ASSERT_UI": "backend/app/bake/schema/hard_assert_ui.py",
    "BAKE_SKIN": "backend/app/bake/skin_invariants.py",
    "BAKE_TRADE_SURFACE": "backend/app/bake/features/trade_thicken.py",
    "BAKE_USECASE": "backend/app/bake/schema/usecases.py",
    "BAKE_PERSISTENCE": "backend/app/bake/persistence.py",
    "BAKE_ADDON_SECURITY": "backend/app/bake/addons.py",
    "BAKE_PACK_LEAN": "backend/app/bake/pack_prune.py",
    "FILL_MERGE": "backend/app/llm/unit_flow/merge.py",
    "BUILD_SKELETON": "backend/app/llm/agents_fix.py · 骨架探测",
    "BUILD_COMPILE": "backend/app/llm/agents_fix.py · mvn compile",
    "GATE_ACCEPT": "backend/app/bake/gates/evaluate.py · accept",
    "GATE_SCHEMA": "backend/app/bake/gates/evaluate.py · p3c/p3b",
    "GATE_E2E_PATH": "backend/app/bake/gates/evaluate.py · p2/p1/p0",
    "GATE_ADMIN_BOUNDARY": "backend/app/bake/gates/evaluate.py · p3d",
    "GATE_STUDENT_COPY": "backend/app/bake/gates · p3copy / FACTORY_UI",
    "GATE_SEMANTIC": "backend/app/bake/gates/semantic.py · p3s",
    "GATE_CHECKLIST": "backend/app/bake/gates/evaluate.py · p3a",
    "GATE_QA": "backend/app/services/delivery_review.py · p3q / domain_vocab",
    "GATE_GENERIC_UNREALIZED": "backend/app/bake/gates/evaluate.py · 域未做实",
    "GATE_OVERALL": "backend/app/services/jobs.py · _gate_fail_summary",
    "MATCH_PATH": "backend/app/bake/match_path_axes.py",
    "STUDENT_DB": "backend/app/services/student_db.py · 当前不写 job.failed",
    "UNKNOWN": "待补码表",
}

# 与 jobs._gate_fail_summary 同序
_GATE_KEY_ORDER: tuple[str, ...] = (
    "accept",
    "p3c",
    "p3d",
    "p3t",
    "p3q",
    "p3copy",
    "p3s",
    "p3lean",
    "p3layout",
    "p3n",
    "p3ac",
    "p3a",
    "p3b",
    "p2",
    "p1",
    "p0b",
    "p0a",
)

_GATE_KEY_TO_CODE: dict[str, str] = {
    "accept": "GATE_ACCEPT",
    "p3c": "GATE_SCHEMA",
    "p3b": "GATE_SCHEMA",
    "p3d": "GATE_ADMIN_BOUNDARY",
    "p3t": "BAKE_TABLE_BUDGET",
    "p3q": "GATE_QA",
    "p3copy": "GATE_STUDENT_COPY",
    "p3s": "GATE_SEMANTIC",
    "p3lean": "BAKE_PACK_LEAN",
    "p3layout": "BAKE_LAYOUT",
    "p3n": "BAKE_SCHEMA_NF",
    "p3ac": "BAKE_ARCHIVE_COLUMNS",
    "p3a": "GATE_CHECKLIST",
    "p2": "GATE_E2E_PATH",
    "p1": "GATE_E2E_PATH",
    "p0b": "GATE_E2E_PATH",
    "p0a": "GATE_E2E_PATH",
}

# (substring, code) — 先匹配先得；运维句优先单独处理
_STEM_RULES: tuple[tuple[str, str], ...] = (
    ("库表须满足 3NF", "BAKE_SCHEMA_NF"),
    ("表数量=", "BAKE_TABLE_BUDGET"),
    ("低于下限", "BAKE_TABLE_BUDGET"),
    ("超过硬顶", "BAKE_TABLE_BUDGET"),
    ("档案语义列未对齐", "BAKE_ARCHIVE_COLUMNS"),
    ("INSERT IGNORE 演示种子", "BAKE_ARCHIVE_SEED"),
    ("缺少 archive_item_table", "BAKE_ARCHIVE_SEED"),
    ("身份/壳未对齐", "BAKE_IDENTITY"),
    ("菜单/路由未对齐", "BAKE_MENU_ROUTES"),
    ("硬拦与收集 UI 未对齐", "BAKE_HARD_ASSERT_UI"),
    ("错皮/怪交互硬闸失败", "BAKE_SKIN"),
    ("refundReasonOptions", "BAKE_TRADE_SURFACE"),
    ("usecase:", "BAKE_USECASE"),
    ("persistence=mybatis", "BAKE_PERSISTENCE"),
    ("persistence=jpa", "BAKE_PERSISTENCE"),
    ("JdbcSupport", "BAKE_PERSISTENCE"),
    ("spring-boot-starter-security", "BAKE_ADDON_SECURITY"),
    ("Security 叠层缺少", "BAKE_ADDON_SECURITY"),
    ("pack_prune", "BAKE_PACK_LEAN"),
    ("未挂岛", "BAKE_PACK_LEAN"),
    ("工厂注记", "BAKE_PACK_LEAN"),
    ("壳件不符", "BAKE_PACK_LEAN"),
    ("p3lean", "BAKE_PACK_LEAN"),
    ("布局检查", "BAKE_LAYOUT"),
    ("布局一眼病", "BAKE_LAYOUT"),
    ("台账对账", "BAKE_LAYOUT"),
    ("结构契约", "BAKE_LAYOUT"),
    ("p3layout", "BAKE_LAYOUT"),
    ("island merge", "FILL_MERGE"),
    ("填岛合并失败", "FILL_MERGE"),
    ("骨架不完整", "BUILD_SKELETON"),
    ("编译失败", "BUILD_COMPILE"),
    ("mvn compile timeout", "BUILD_COMPILE"),
    ("该领域尚未做实", "GATE_GENERIC_UNREALIZED"),
    ("可接题边界", "GATE_ACCEPT"),
    ("说明书口吻", "GATE_STUDENT_COPY"),
    ("交付质量摘要", "GATE_QA"),
    ("项 error", "GATE_QA"),
    ("未知身份场景", "MATCH_PATH"),
    ("未知主路径入口", "MATCH_PATH"),
    ("当前领域无主路径入口", "MATCH_PATH"),
    ("无法连接学生 MySQL", "STUDENT_DB"),
    ("执行 schema.sql 失败", "STUDENT_DB"),
    ("工作区不存在，无法续跑", "RESUME_NO_WORKSPACE"),
)


@dataclass(frozen=True)
class ClassifyResult:
    code: str
    confidence: str  # high | low
    looks_like_code: str | None = None
    label: str = ""
    fix_locus: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "confidence": self.confidence,
            "looks_like_code": self.looks_like_code,
            "label": self.label or LABELS.get(self.code, self.code),
            "fix_locus": self.fix_locus or FIX_LOCUS.get(self.code, FIX_LOCUS["UNKNOWN"]),
        }


def fix_locus_for(code: str | None) -> str:
    c = (code or "UNKNOWN").strip()
    if c not in FIX_LOCUS:
        return FIX_LOCUS["UNKNOWN"]
    return FIX_LOCUS[c]


def label_for(code: str | None) -> str:
    c = (code or "UNKNOWN").strip()
    return LABELS.get(c, c or "UNKNOWN")


def _norm_error(text: str | None) -> str:
    return " ".join(str(text or "").strip().split())


def _failing_step(step: str | None, steps: list[Any] | None) -> str:
    if steps and isinstance(steps, list):
        for s in steps:
            if not isinstance(s, dict):
                continue
            if str(s.get("status") or "") == "fail":
                return str(s.get("key") or "")
    raw = str(step or "").strip()
    if raw.startswith("resume:"):
        return raw.split(":", 1)[-1]
    return raw


def code_from_gates(gates: dict[str, Any] | None) -> str | None:
    g = gates or {}
    acc = g.get("accept")
    if isinstance(acc, dict) and acc.get("ok") is False:
        return "GATE_ACCEPT"
    for k in _GATE_KEY_ORDER:
        if k == "accept":
            continue
        item = g.get(k)
        if isinstance(item, dict) and item.get("ok") is False:
            return _GATE_KEY_TO_CODE.get(k)
    if g.get("overall") is False:
        return "GATE_OVERALL"
    return None


def _code_from_stems(err: str) -> str | None:
    if "质量检查未通过" in err:
        if "该领域尚未做实" in err:
            return "GATE_GENERIC_UNREALIZED"
        if "可接题" in err or "accept" in err.lower():
            return "GATE_ACCEPT"
        if "说明书口吻" in err or "工厂腔" in err:
            return "GATE_STUDENT_COPY"
        if "交付质量摘要" in err or "项 error" in err:
            return "GATE_QA"
        if "演示" in err and ("字样" in err or "场景" in err):
            return "GATE_SEMANTIC"
        if "总管" in err or "子管" in err:
            return "GATE_ADMIN_BOUNDARY"
        if "清单实装" in err:
            return "GATE_CHECKLIST"
        if "Domain Schema" in err or "未知 capability" in err:
            return "GATE_SCHEMA"
        if "主流程" in err or "缺文件" in err or "缺路由" in err:
            return "GATE_E2E_PATH"
        if "3NF" in err:
            return "BAKE_SCHEMA_NF"
        if "表数量" in err or "表数" in err:
            return "BAKE_TABLE_BUDGET"
        if "档案语义" in err:
            return "BAKE_ARCHIVE_COLUMNS"
        if "未挂岛" in err or "瘦身" in err or "工厂注记" in err:
            return "BAKE_PACK_LEAN"
        return "GATE_OVERALL"
    for stem, code in _STEM_RULES:
        if stem in err:
            return code
    return None


def _fingerprint(err: str) -> str:
    """去数字/路径噪声后的稳定指纹，用于 UNKNOWN 并族。"""
    s = err.lower()
    s = re.sub(r"\d+", "0", s)
    s = re.sub(r"[a-f0-9]{8,}", "h", s)
    s = re.sub(r"\s+", " ", s).strip()
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:12]


def looks_like_from_error(err: str) -> str | None:
    """UNKNOWN 时根据 stem 弱提示（仍只返回已有码）。"""
    hit = _code_from_stems(err)
    if hit and hit != "UNKNOWN":
        return hit
    # 弱启发：步骤关键词
    if "gate" in err.lower() or "门禁" in err:
        return "GATE_OVERALL"
    if "compile" in err.lower() or "mvn" in err.lower():
        return "BUILD_COMPILE"
    return None


def classify_bake_error(
    error: str | None,
    *,
    step: str | None = None,
    steps: list[Any] | None = None,
    gates: dict[str, Any] | None = None,
) -> ClassifyResult:
    err = _norm_error(error)
    fail_step = _failing_step(step, steps)

    if not err:
        return ClassifyResult(
            code="UNKNOWN",
            confidence="low",
            label=LABELS["UNKNOWN"],
            fix_locus=FIX_LOCUS["UNKNOWN"],
        )

    # 1) 运维固定句
    if "服务重启，任务中断" in err:
        return _ok("OPS_RESTART")
    if err == "已取消" or err.startswith("已取消"):
        return _ok("OPS_CANCELLED")
    if "项目不存在" in err:
        return _ok("OPS_PROJECT_MISSING")
    if "交付复审进行中" in err:
        return _ok("OPS_REVIEW_LOCK")

    # 2) gates 结构化（写入门禁失败时优先）
    if gates:
        gcode = code_from_gates(gates if isinstance(gates, dict) else None)
        if gcode:
            return _ok(gcode)

    # 3–4) stem / 质量检查文案
    stem_code = _code_from_stems(err)
    if stem_code:
        conf = "high"
        if stem_code == "GATE_OVERALL":
            conf = "low"
        return _ok(stem_code, confidence=conf)

    # 步骤弱提示
    if fail_step == "build_verify":
        return _ok("BUILD_COMPILE", confidence="low")
    if fail_step == "island_fill":
        return _ok("FILL_MERGE", confidence="low")
    if fail_step == "gate_e2e":
        return _ok("GATE_OVERALL", confidence="low")

    like = looks_like_from_error(err)
    return ClassifyResult(
        code="UNKNOWN",
        confidence="low",
        looks_like_code=like,
        label=LABELS["UNKNOWN"],
        fix_locus=FIX_LOCUS["UNKNOWN"],
    )


def _ok(code: str, *, confidence: str = "high") -> ClassifyResult:
    return ClassifyResult(
        code=code,
        confidence=confidence,
        label=LABELS.get(code, code),
        fix_locus=FIX_LOCUS.get(code, FIX_LOCUS["UNKNOWN"]),
    )


def catalog_payload() -> list[dict[str, str]]:
    return [
        {
            "code": c,
            "label": LABELS[c],
            "fix_locus": FIX_LOCUS[c],
        }
        for c in CODES
    ]


def error_fingerprint(error: str | None) -> str:
    return _fingerprint(_norm_error(error))
