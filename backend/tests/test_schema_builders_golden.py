"""Characterization: SCHEMA_BUILDERS output must match golden snapshots."""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.schema.templates import SCHEMA_BUILDERS
from tests.helpers.normalize import normalize_json

GOLDEN_DIR = Path(__file__).resolve().parent / "golden" / "schema"


class SchemaBuildersGoldenTests(unittest.TestCase):
    def test_all_builders(self) -> None:
        self.assertGreaterEqual(len(SCHEMA_BUILDERS), 20)
        for domain, builder in sorted(SCHEMA_BUILDERS.items()):
            with self.subTest(domain=domain):
                got = normalize_json(builder("测试课题"))
                path = GOLDEN_DIR / f"{domain}.json"
                want = path.read_text(encoding="utf-8")
                self.assertEqual(got, want, f"schema mismatch: {domain}")


if __name__ == "__main__":
    unittest.main()
