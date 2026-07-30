# -*- coding: utf-8 -*-
"""档案 stage 列 DEFAULT 必须落在该域 schema 选项内（防「奖学金显示在岗」）。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.schema.followup_presets import FOLLOWUP_PRESETS

_ROOT = Path(__file__).resolve().parents[1]
_TPL = _ROOT / "app" / "bake" / "sql" / "templates"
_STAGE_DEF = re.compile(r"stage VARCHAR\(32\) DEFAULT '([^']+)'")


class ArchiveStageDefaultTests(unittest.TestCase):
    def test_sql_stage_default_in_schema_options(self) -> None:
        mismatches: list[str] = []
        for p in sorted(_TPL.glob("DOM-*.sql")):
            m = _STAGE_DEF.search(p.read_text(encoding="utf-8"))
            if not m:
                continue
            default = m.group(1)
            preset = FOLLOWUP_PRESETS.get(p.stem) or {}
            stage = next(
                (f for f in (preset.get("archive_fields") or []) if f.get("key") == "stage"),
                None,
            )
            opts = list((stage or {}).get("options") or [])
            if opts and default not in opts:
                mismatches.append(f"{p.stem}: DEFAULT={default!r} not in {opts}")
        self.assertEqual(mismatches, [], "\n".join(mismatches))

    def test_fund_not_on_duty(self) -> None:
        sql = (_TPL / "DOM-FUND.sql").read_text(encoding="utf-8")
        self.assertNotIn("DEFAULT '在岗'", sql)
        self.assertIn("DEFAULT '开放申请'", sql)


if __name__ == "__main__":
    unittest.main()
