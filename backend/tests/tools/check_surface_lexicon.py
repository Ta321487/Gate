"""话术层全量普查：对 proposal_packs_data 全部域包断言话术口径。

Run from backend/: python tests/tools/check_surface_lexicon.py

断言（设计稿 §0.1，脚本化全量，不接受抽样）：
1. 产物可见文案对「跨域专属名词表」零命中；
2. 同一 slot（ticket_noun / category_axis）零口径分叉。
退出码非 0 表示有域包不通过。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.bake.domain_vocab import (  # noqa: E402
    cross_domain_findings,
    slot_divergence_findings,
)
from app.bake.schema.templates import SCHEMA_BUILDERS  # noqa: E402

PACKS = ROOT / "app" / "bake" / "proposal_packs_data"

_TEXT_FIELDS = (
    "title",
    "system_name",
    "scene",
    "value",
    "focus",
    "main_path",
    "research_focus",
    "problem",
    "key_consistency",
)


def pack_text(pack: dict) -> str:
    parts: list[str] = []
    for key in _TEXT_FIELDS:
        val = pack.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    for key in ("features", "digressions", "l1_optional"):
        for item in pack.get(key) or []:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
    return "\n".join(parts)


def build_schema(domain: str, title: str, text: str) -> dict:
    builder = SCHEMA_BUILDERS.get(domain)
    if builder is None:
        if domain != "DOM-GENERIC":  # 交叉包兜底：GENERIC 走通用壳，无域皮话术
            raise KeyError(domain)
        from app.bake.schema.shells import generic_schema

        return generic_schema(title, domain)
    try:
        return builder(title, text)
    except TypeError:
        return builder(title)


def main() -> int:
    bad = 0
    total = 0
    for path in sorted(PACKS.glob("*.json")):
        if path.name.startswith("_"):
            continue
        pack = json.loads(path.read_text(encoding="utf-8"))
        domain = str(pack.get("anchor_domain") or "")
        if not domain:
            print(f"SKIP {path.name}: 无 anchor_domain")
            continue
        total += 1
        title = str(pack.get("title") or path.stem)
        schema = build_schema(domain, title, pack_text(pack))
        findings = slot_divergence_findings(schema) + cross_domain_findings(
            schema, domain, title=title
        )
        if findings:
            bad += 1
            print(f"FAIL {path.name} [{domain}]")
            for f in findings[:6]:
                print(f"   - {f['level']} {f['where']}: {f['msg']}")
    print(f"checked {total} packs, failed {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
