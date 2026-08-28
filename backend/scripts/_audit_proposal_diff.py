"""Audit proposal diff coverage across packs and corpus."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bake.domains import DOMAINS
from app.bake.proposal_packs import PACKS
from app.services.proposal_diff import build_proposal_diff

failures: list[dict] = []
for pack in PACKS:
    dom = pack.get("anchor_domain") or pack.get("domain")
    if not dom or dom not in DOMAINS:
        continue
    features = list((DOMAINS.get(dom) or {}).get("features") or [])
    lines = list(pack.get("features") or [])
    if not lines:
        continue
    diff = build_proposal_diff({"features": features, "proposal": {"feature_lines": lines}})
    if diff["unmatched_proposal"] or not diff["ready"]:
        failures.append(
            {
                "kind": "pack",
                "id": pack.get("id"),
                "domain": dom,
                "matched": len(diff["matched"]),
                "review": len(diff["review_proposal"]),
                "unmatched": diff["unmatched_proposal"],
                "ready": diff["ready"],
            }
        )

corpus_path = Path(__file__).resolve().parents[1] / "tests/fixtures/domain_opening_corpus.json"
if corpus_path.exists():
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    for sample in corpus.get("samples", []):
        dom = sample.get("domain")
        if not dom or dom not in DOMAINS:
            continue
        features = list((DOMAINS.get(dom) or {}).get("features") or [])
        diff = build_proposal_diff({"features": features}, sample["text"])
        if diff["unmatched_proposal"] or not diff["ready"]:
            failures.append(
                {
                    "kind": "corpus",
                    "id": sample.get("title", dom)[:48],
                    "domain": dom,
                    "matched": len(diff["matched"]),
                    "review": len(diff["review_proposal"]),
                    "unmatched": diff["unmatched_proposal"],
                    "ready": diff["ready"],
                }
            )

print(f"FAILURES: {len(failures)}")
for f in sorted(failures, key=lambda x: (-len(x["unmatched"]), x["domain"], x["id"])):
    print(f"[{f['kind']}] {f['id']} ({f['domain']}) matched={f['matched']} unmatched={len(f['unmatched'])} ready={f['ready']}")
    for u in f["unmatched"]:
        print(f"  - {u}")
