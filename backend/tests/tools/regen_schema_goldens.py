"""Regenerate tests/golden/schema from SCHEMA_BUILDERS. Run from backend/: python tests/tools/regen_schema_goldens.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.bake.schema.templates import SCHEMA_BUILDERS  # noqa: E402
from tests.helpers.normalize import normalize_json  # noqa: E402

GOLDEN = Path(__file__).resolve().parents[1] / "golden" / "schema"


def main() -> None:
    for domain, builder in sorted(SCHEMA_BUILDERS.items()):
        path = GOLDEN / f"{domain}.json"
        path.write_text(normalize_json(builder("测试课题")), encoding="utf-8")
        print("updated", path.name)


if __name__ == "__main__":
    main()
