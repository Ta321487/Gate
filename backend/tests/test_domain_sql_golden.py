"""Characterization: domain_sql output must match golden snapshots."""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.engine import domain_sql
from tests._normalize import normalize_sql

GOLDEN_DIR = Path(__file__).resolve().parent / "golden" / "sql"

# domain -> (archetype, archetypes)
_GENERIC_CASES: list[tuple[str, str | None, list[str] | None]] = [
    ("DOM-GENERIC", None, None),
    ("DOM-GENERIC", "ARCH-FLOW", None),
    ("DOM-GENERIC", "ARCH-TRADE", None),
    ("DOM-GENERIC", "ARCH-RESERVE", None),
    ("DOM-GENERIC", None, ["ARCH-FLOW", "ARCH-TRADE"]),
]


def _golden_name(domain: str, archetype: str | None, archetypes: list[str] | None) -> str:
    if archetypes:
        return f"{domain}__{'_'.join(archetypes)}.sql"
    if archetype:
        return f"{domain}__{archetype}.sql"
    return f"{domain}.sql"


class DomainSqlGoldenTests(unittest.TestCase):
    def test_non_generic_domains(self) -> None:
        domains = sorted(
            p.stem
            for p in GOLDEN_DIR.glob("DOM-*.sql")
            if not p.stem.startswith("DOM-GENERIC")
        )
        self.assertGreaterEqual(len(domains), 20)
        for domain in domains:
            with self.subTest(domain=domain):
                got = normalize_sql(domain_sql(domain, "thesis_test"))
                path = GOLDEN_DIR / f"{domain}.sql"
                want = path.read_text(encoding="utf-8")
                self.assertEqual(got, want, f"domain_sql mismatch: {domain}")

    def test_generic_shells(self) -> None:
        for domain, arch, arches in _GENERIC_CASES:
            name = _golden_name(domain, arch, arches)
            with self.subTest(case=name):
                got = normalize_sql(
                    domain_sql(domain, "thesis_test", archetype=arch, archetypes=arches)
                )
                want = (GOLDEN_DIR / name).read_text(encoding="utf-8")
                self.assertEqual(got, want, f"domain_sql mismatch: {name}")


if __name__ == "__main__":
    unittest.main()
