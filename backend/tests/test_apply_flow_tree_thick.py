"""OA 申请流角色树加厚：共享 _apply_flow_tree 横切模块。"""

from __future__ import annotations

import unittest

from app.bake.proposal_packs import PACKS
from app.bake.proposal_pressure import expected_capability_ids
from app.bake.proposal_role_modules import resolve_role_modules
from app.bake.domain_schema import attach_accept, required_capabilities
from app.bake.catalog import match_text
from app.bake.sample_proposal import build_sample_proposal


class ApplyFlowTreeThickTests(unittest.TestCase):
    def test_seal_tree_has_cross_cut_modules(self) -> None:
        pack = next(p for p in PACKS if p["id"] == "seal")
        tree = resolve_role_modules(pack)
        blob = "\n".join(
            f"{m[0]}:{m[1]}"
            for r in tree
            for m in (r.get("modules") or [])
            if isinstance(m, (tuple, list)) and len(m) >= 2
        )
        for needle in (
            "材料附件模块",
            "驳回重提模块",
            "办理催办模块",
            "消息通知模块",
            "多级审批模块",
            "操作审计模块",
            "留言反馈模块",
        ):
            self.assertIn(needle, blob)

    def test_seal_pressure_caps(self) -> None:
        sp = build_sample_proposal(pack_id="seal", seed=1, pressure=True)
        got = match_text(sp.text, sp.filename)
        self.assertEqual(got.domain, "DOM-SEAL")
        base = required_capabilities(got.domain, got.archetype, archetypes=got.archetypes)
        spec = attach_accept(
            {
                "domain": got.domain,
                "title": sp.title,
                "archetype": got.archetype,
                "archetypes": list(got.archetypes or []),
                "capabilities": base,
                "features": [],
            },
            sp.text,
        )
        caps = list(spec.get("capabilities") or [])
        for cap in expected_capability_ids("DOM-SEAL"):
            self.assertIn(cap, caps, f"missing {cap}; caps={caps}")
        ticket = ((spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("requireAttach"), "上传附件应打开 requireAttach")


if __name__ == "__main__":
    unittest.main()
