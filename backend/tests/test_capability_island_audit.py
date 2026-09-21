"""能力岛总账 / 挂载对账门禁。

对账：CAPABILITIES ↔ docs/capabilities.md ↔ features/*_CAP ↔ proposal_caps 挂载。
腐化：孤儿 cap、两岛挂载词完全相同。
例外：无 merge_* 的 features 模块 ⊆ HUB_BYPASS_MODULES。
"""

from __future__ import annotations

import ast
import re
import unittest
from collections import defaultdict
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.features.proposal_caps import HUB_BYPASS_MODULES

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FEATURES_DIR = _REPO_ROOT / "backend" / "app" / "bake" / "features"
_CAPS_DOC = _REPO_ROOT / "docs" / "capabilities.md"
_PROPOSAL_CAPS = _FEATURES_DIR / "proposal_caps.py"
_DOMAIN_SCHEMA = _REPO_ROOT / "backend" / "app" / "bake" / "domain_schema.py"
_ENGINE_SQL = _REPO_ROOT / "backend" / "app" / "bake" / "engine_sql.py"

_HUB_INFRA = frozenset({"proposal_caps", "__init__"})
_CAP_ASSIGN_RE = re.compile(
    r'^([A-Z][A-Z0-9_]*)_CAP\s*=\s*["\']([^"\']+)["\']',
    re.M,
)
_CAPS_TUPLE_RE = re.compile(
    r'^[A-Z][A-Z0-9_]*_CAPS\s*=\s*\((.*?)\)',
    re.M | re.S,
)
_MERGE_DEF_RE = re.compile(r"^def (merge_\w+_capabilities)\b", re.M)
_MERGE_CALL_RE = re.compile(r"\b(merge_\w+_capabilities)\s*\(")
_APPLY_DEF_RE = re.compile(r"^def (apply_\w+)\b", re.M)
_DOC_CAP_RE = re.compile(r"`([a-z][a-z0-9_]*)`")
_TERMS_ASSIGN_RE = re.compile(
    r"^(_[A-Z0-9_]*(?:TERMS|HINTS))\s*=\s*\((.*?)\)",
    re.M | re.S,
)


def _feature_modules() -> list[Path]:
    return sorted(
        p
        for p in _FEATURES_DIR.glob("*.py")
        if p.stem not in _HUB_INFRA
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _attach_accept_source() -> str:
    text = _read(_DOMAIN_SCHEMA)
    start = text.find("def attach_accept(")
    if start < 0:
        return ""
    rest = text[start + 1 :]
    m = re.search(r"\ndef [a-z_]", rest)
    return text[start : start + 1 + (m.start() if m else len(rest))]


def _feature_cap_ids(text: str) -> set[str]:
    ids = {m.group(2) for m in _CAP_ASSIGN_RE.finditer(text)}
    for m in _CAPS_TUPLE_RE.finditer(text):
        ids.update(re.findall(r'["\']([^"\']+)["\']', m.group(1)))
    return ids


def _module_term_sets(stem: str, text: str) -> dict[str, tuple[str, ...]]:
    """Collect mount-term tuples named *_TERMS / *_HINTS (skip CLOCK-style non-island)."""
    out: dict[str, tuple[str, ...]] = {}
    for m in _TERMS_ASSIGN_RE.finditer(text):
        name = m.group(1)
        # 非能力扫词：控件精度等
        if name in {"CLOCK_EMPHASIS_HINTS"} or name.startswith("CLOCK_"):
            continue
        terms = tuple(re.findall(r'["\']([^"\']+)["\']', m.group(2)))
        if terms:
            out[f"{stem}.{name}"] = terms
    return out


class CapabilityIslandAuditTests(unittest.TestCase):
    def test_capabilities_documented(self) -> None:
        doc = _read(_CAPS_DOC)
        found = set(_DOC_CAP_RE.findall(doc))
        missing = sorted(set(CAPABILITIES) - found)
        self.assertEqual(
            missing,
            [],
            f"CAPABILITIES 未写入 docs/capabilities.md: {missing}",
        )

    def test_three_mount_contract_documented(self) -> None:
        doc = _read(_CAPS_DOC)
        for needle in (
            "开岛三处挂载契约",
            "proposal_caps",
            "merge_*",
            "attach_accept",
            "apply_*",
            "engine_sql",
            "HUB_BYPASS_MODULES",
        ):
            self.assertIn(needle, doc, f"capabilities.md 缺少契约措辞: {needle}")

    def test_feature_cap_consts_in_registry(self) -> None:
        unknown: list[str] = []
        for path in _feature_modules():
            for cap_id in _feature_cap_ids(_read(path)):
                if cap_id not in CAPABILITIES:
                    unknown.append(f"{path.stem}:{cap_id}")
        self.assertEqual(
            unknown,
            [],
            f"features *_CAP 不在 CAPABILITIES: {unknown}",
        )

    def test_hub_bypass_whitelist(self) -> None:
        no_merge: list[str] = []
        for path in _feature_modules():
            text = _read(path)
            if _MERGE_DEF_RE.search(text):
                continue
            no_merge.append(path.stem)
        extras = sorted(set(no_merge) - set(HUB_BYPASS_MODULES))
        self.assertEqual(
            extras,
            [],
            f"无 merge_* 却未登记 HUB_BYPASS_MODULES: {extras}",
        )
        stale = sorted(set(HUB_BYPASS_MODULES) - set(no_merge))
        self.assertEqual(
            stale,
            [],
            f"HUB_BYPASS_MODULES 含已有 merge_* 的模块: {stale}",
        )
        # 白名单不得偷偷导出进总账的 *_CAP
        leaked: list[str] = []
        for stem in HUB_BYPASS_MODULES:
            path = _FEATURES_DIR / f"{stem}.py"
            if not path.is_file():
                leaked.append(f"missing:{stem}")
                continue
            for cap_id in _feature_cap_ids(_read(path)):
                leaked.append(f"{stem}:{cap_id}")
        self.assertEqual(
            leaked,
            [],
            f"HUB_BYPASS 模块不得导出 *_CAP: {leaked}",
        )

    def test_merge_modules_mounted_in_proposal_caps(self) -> None:
        hub = _read(_PROPOSAL_CAPS)
        called = set(_MERGE_CALL_RE.findall(hub))
        unmounted: list[str] = []
        for path in _feature_modules():
            if path.stem in HUB_BYPASS_MODULES:
                continue
            defined = set(_MERGE_DEF_RE.findall(_read(path)))
            if not defined:
                continue
            if not (defined & called):
                unmounted.append(f"{path.stem}:{sorted(defined)}")
        self.assertEqual(
            unmounted,
            [],
            f"有 merge_* 但 proposal_caps 未调用任一: {unmounted}",
        )

    def test_merge_modules_have_apply_in_attach_accept(self) -> None:
        attach_body = _attach_accept_source()
        self.assertIn("def attach_accept(", attach_body)
        missing: list[str] = []
        for path in _feature_modules():
            if path.stem in HUB_BYPASS_MODULES:
                continue
            text = _read(path)
            if not _MERGE_DEF_RE.search(text):
                continue
            applies = set(_APPLY_DEF_RE.findall(text))
            if not applies:
                missing.append(f"{path.stem}:no_apply_def")
                continue
            if not any(name in attach_body for name in applies):
                missing.append(f"{path.stem}:{sorted(applies)}")
        self.assertEqual(
            missing,
            [],
            f"有 merge_* 但 apply_* 未进 attach_accept: {missing}",
        )

    def test_engine_sql_shares_proposal_caps_hub(self) -> None:
        engine = _read(_ENGINE_SQL)
        self.assertIn(
            "merge_proposal_capabilities",
            engine,
            "engine_sql 必须调用 merge_proposal_capabilities（三处挂载之 SQL 侧）",
        )

    def test_no_orphan_capabilities(self) -> None:
        domain_caps: set[str] = set()
        for caps in DOMAIN_CAPABILITIES.values():
            domain_caps.update(caps or [])

        merge_ref: set[str] = set()
        for path in _feature_modules():
            text = _read(path)
            if not _MERGE_DEF_RE.search(text):
                continue
            for cap_id in CAPABILITIES:
                if f'"{cap_id}"' in text or f"'{cap_id}'" in text:
                    merge_ref.add(cap_id)

        orphans = sorted(set(CAPABILITIES) - domain_caps - merge_ref)
        self.assertEqual(
            orphans,
            [],
            f"孤儿 cap（总账有、域默认与 merge_* 都没有）: {orphans}",
        )

    def test_no_identical_mount_terms(self) -> None:
        by_terms: dict[tuple[str, ...], list[str]] = defaultdict(list)
        for path in _feature_modules():
            for label, terms in _module_term_sets(path.stem, _read(path)).items():
                by_terms[terms].append(label)
        dups = {
            terms: labels
            for terms, labels in by_terms.items()
            if len(labels) > 1
        }
        self.assertEqual(
            dups,
            {},
            f"两个岛挂载词完全相同: {dups}",
        )

    def test_hub_bypass_constant_is_frozenset_of_str(self) -> None:
        self.assertIsInstance(HUB_BYPASS_MODULES, frozenset)
        self.assertTrue(HUB_BYPASS_MODULES)
        for name in HUB_BYPASS_MODULES:
            self.assertIsInstance(name, str)
            self.assertTrue((_FEATURES_DIR / f"{name}.py").is_file(), name)
        # 源码可被 ast 解析（防语法腐化）
        ast.parse(_read(_PROPOSAL_CAPS))


if __name__ == "__main__":
    unittest.main()
