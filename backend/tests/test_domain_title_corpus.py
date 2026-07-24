# -*- coding: utf-8 -*-
"""五薄域题名语料：仅调用现有 match_text，命中率 ≥90%。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.bake.catalog import match_text

CORPUS = Path(__file__).resolve().parent / "fixtures" / "domain_title_corpus.json"


def _wrap(title: str) -> str:
    return f"基于 Spring Boot 的{title}的设计与实现"


class DomainTitleCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(CORPUS.read_text(encoding="utf-8"))

    def test_positive_hit_rate(self) -> None:
        positives = self.data["positives"]
        for domain, titles in positives.items():
            with self.subTest(domain=domain):
                self.assertGreaterEqual(len(titles), 30, domain)
                ok = 0
                misses: list[str] = []
                for title in titles:
                    m = match_text(_wrap(title), f"{title}.txt")
                    if m.domain == domain:
                        ok += 1
                    else:
                        misses.append(f"{title}→{m.domain}")
                rate = ok / len(titles)
                self.assertGreaterEqual(
                    rate,
                    0.90,
                    f"{domain} hit={ok}/{len(titles)} misses={misses[:8]}",
                )

    def test_boundary_negatives(self) -> None:
        for row in self.data.get("negatives") or []:
            title = row["title"]
            with self.subTest(title=title):
                m = match_text(_wrap(title), f"{title}.txt")
                for forbid in row.get("forbid") or []:
                    self.assertNotEqual(m.domain, forbid, f"hits={m.hits[:8]}")
                prefer = row.get("prefer")
                if prefer:
                    self.assertEqual(m.domain, prefer, f"hits={m.hits[:8]}")


if __name__ == "__main__":
    unittest.main()
