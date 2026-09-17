"""五组压力开题：match → caps → **真实 bake_project 出包**。

组：报修 / 预约 / 报名 / 借用 / 内容（每组 1 个代表 pack）。
此前 schema/SQL 冒烟不等于出包；本文件补真实 bake。
"""

from __future__ import annotations

import re
import shutil
import unittest

from app.bake.catalog import build_spec, match_text
from app.bake.engine import bake_project
from app.bake.proposal_pressure import expected_capability_ids
from app.bake.sample_proposal import build_sample_proposal
from app.core.config import get_settings

_TRAILING_COMMA = re.compile(r",\s*\n\s*\)")

_PRESSURE_BAKE_CASES: list[tuple[str, str]] = [
    ("报修", "dorm"),
    ("预约", "meeting"),
    ("报名", "activity"),
    ("借用", "library"),
    ("内容", "forum"),
    ("内容", "media"),
]


class PressureGroupRealBakeTests(unittest.TestCase):
    def test_pressure_groups_real_bake_workspace(self) -> None:
        settings = get_settings()
        for group, pack_id in _PRESSURE_BAKE_CASES:
            with self.subTest(group=group, pack=pack_id):
                sp = build_sample_proposal(pack_id=pack_id, seed=1, pressure=True)
                domain = sp.anchor_domain
                got = match_text(sp.text, sp.filename)
                self.assertEqual(got.domain, domain, f"match={got.domain}")

                pid = f"gf-pressure-{pack_id}"
                dest = settings.workspace_dir / pid
                if dest.exists():
                    shutil.rmtree(dest)

                archetype = got.archetype or "ARCH-FLOW"
                arches = list(got.archetypes or [archetype])
                spec = build_spec(
                    title=sp.title,
                    archetype=archetype,
                    domain=domain,
                    theme="gen-ink",
                    llm_enabled=False,
                    match_mode="recommended",
                    confidence=0.9,
                    archetypes=arches,
                    proposal={"excerpt": sp.text},
                )
                self.assertEqual(
                    spec.get("accept"),
                    "full",
                    f"accept={spec.get('accept')} reason={spec.get('accept_reason')}",
                )
                caps = list(spec.get("capabilities") or [])
                for cap in expected_capability_ids(domain):
                    self.assertIn(cap, caps, f"missing {cap} in {caps}")

                ws = bake_project(pid, spec, f"pressure_{pack_id}")
                self.assertTrue(ws.is_dir(), str(ws))
                self.assertTrue((ws / "README.md").is_file(), "缺 README")
                self.assertTrue((ws / "backend" / "pom.xml").is_file(), "缺 backend")
                self.assertTrue(
                    (ws / "frontend" / "package.json").is_file(),
                    "缺 frontend",
                )
                sqls = list(ws.rglob("schema.sql"))
                self.assertTrue(sqls, "缺 schema.sql")
                sql_text = sqls[0].read_text(encoding="utf-8")
                self.assertFalse(
                    _TRAILING_COMMA.search(sql_text),
                    "schema.sql 末列拖尾逗号",
                )


if __name__ == "__main__":
    unittest.main()
