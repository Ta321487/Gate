"""开题与 checklist diff。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.bake.domains import DOMAINS
from app.bake.proposal_packs import PACKS
from app.services.proposal import summarize_proposal
from app.services.proposal_diff import build_proposal_diff


class ProposalDiffTests(unittest.TestCase):
    def test_unmatched_proposal_lines(self):
        spec = {
            "features": [{"name": "登录", "status": "baseline"}],
            "proposal": {"feature_lines": ["登录", "宿舍报修受理"]},
        }
        diff = build_proposal_diff(spec)
        self.assertFalse(diff["ok"])
        self.assertIn("宿舍报修受理", diff["unmatched_proposal"])

    def test_all_matched(self):
        spec = {
            "features": [
                {"name": "登录", "status": "baseline"},
                {"name": "报修申请", "status": "mvp"},
            ],
            "proposal": {"feature_lines": ["登录", "报修申请"]},
        }
        diff = build_proposal_diff(spec)
        self.assertTrue(diff["ok"])
        self.assertEqual(diff["unmatched_proposal"], [])

    def test_crm_pack_lines_cover_checklist(self):
        pack = next(p for p in PACKS if p.get("id") == "crm")
        features = list((DOMAINS.get("DOM-CRM") or {}).get("features") or [])
        spec = {
            "features": features,
            "proposal": {"feature_lines": list(pack.get("features") or [])},
        }
        diff = build_proposal_diff(spec)
        self.assertEqual(diff["unmatched_proposal"], [], diff)
        self.assertGreaterEqual(len(diff["matched"]), 6)

    def test_crm_real_opening_corpus(self):
        corpus_path = Path(__file__).resolve().parent / "fixtures" / "domain_opening_corpus.json"
        corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
        sample = next(s for s in corpus["samples"] if s["domain"] == "DOM-CRM")
        features = list((DOMAINS.get("DOM-CRM") or {}).get("features") or [])
        summary = summarize_proposal(sample["text"], ["DOM-CRM"])
        diff = build_proposal_diff({"features": features}, sample["text"])
        self.assertGreater(len(summary["feature_lines"]), 0)
        self.assertLessEqual(len(diff["unmatched_proposal"]), 1, diff)

    def test_library_opening_corpus_mostly_matched(self):
        corpus_path = Path(__file__).resolve().parent / "fixtures" / "domain_opening_corpus.json"
        corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
        sample = next(s for s in corpus["samples"] if s["domain"] == "DOM-LIBRARY")
        features = list((DOMAINS.get("DOM-LIBRARY") or {}).get("features") or [])
        diff = build_proposal_diff({"features": features}, sample["text"])
        self.assertLessEqual(len(diff["unmatched_proposal"]), 2, diff)

    def test_match_links_explain_hit(self):
        spec = {
            "features": [
                {"name": "登录", "status": "baseline"},
                {"name": "个人资料与头像", "status": "baseline"},
            ],
            "proposal": {"feature_lines": ["用户注册、登录与个人资料维护"]},
        }
        diff = build_proposal_diff(spec)
        self.assertIn("用户注册、登录与个人资料维护", diff["matched"])
        links = diff["match_links"][0]["hits"]
        hit_names = {h["feature"] for h in links}
        self.assertIn("登录", hit_names)
        self.assertIn("个人资料与头像", hit_names)


if __name__ == "__main__":
    unittest.main()
