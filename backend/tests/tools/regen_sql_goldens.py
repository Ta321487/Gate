"""Regenerate tests/golden/sql from domain_sql. Run from backend/: python tests/tools/regen_sql_goldens.py"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.bake.engine import domain_sql  # noqa: E402
from tests.helpers.normalize import normalize_sql  # noqa: E402

GOLDEN = Path(__file__).resolve().parents[1] / "golden" / "sql"


def main() -> None:
    for path in sorted(GOLDEN.glob("DOM-*.sql")):
        stem = path.stem
        if stem.startswith("DOM-GENERIC__"):
            rest = stem[len("DOM-GENERIC__") :]
            arches = re.findall(r"ARCH-[A-Z]+", rest)
            if len(arches) == 1:
                sql = domain_sql("DOM-GENERIC", "thesis_test", archetype=arches[0])
            else:
                sql = domain_sql("DOM-GENERIC", "thesis_test", archetypes=arches)
        elif stem == "DOM-GENERIC":
            sql = domain_sql("DOM-GENERIC", "thesis_test")
        else:
            sql = domain_sql(stem, "thesis_test")
        path.write_text(normalize_sql(sql), encoding="utf-8")
        print("updated", path.name)


if __name__ == "__main__":
    main()
