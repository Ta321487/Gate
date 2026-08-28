"""Audit pack-only proposal diff."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bake.domains import DOMAINS
from app.bake.proposal_packs import PACKS
from app.services.proposal_diff import build_proposal_diff

failures = []
for pack in PACKS:
    dom = pack.get("anchor_domain") or pack.get("domain")
    if not dom or dom not in DOMAINS or dom == "DOM-GENERIC":
        continue
    lines = list(pack.get("features") or [])
    if not lines:
        continue
    features = list((DOMAINS.get(dom) or {}).get("features") or [])
    diff = build_proposal_diff({"features": features, "proposal": {"feature_lines": lines}})
    if diff["unmatched_proposal"]:
        failures.append((pack["id"], dom, diff["unmatched_proposal"]))

print(f"PACK FAILURES (non-GENERIC): {len(failures)}")
for pid, dom, unmatched in sorted(failures, key=lambda x: -len(x[2])):
    print(f"{pid} ({dom}): {len(unmatched)}")
    for u in unmatched:
        print(f"  - {u}")
