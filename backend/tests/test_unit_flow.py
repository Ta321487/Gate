"""unit_flow：Plan 生成 + 确定性 merge（不调 LLM）。"""

from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from app.bake.domain_schema import build_domain_schema, ensure_spec_schema
from app.bake.engine import bake_project
from app.llm.unit_flow.merge import apply_unit_results_to_workspace
from app.llm.unit_flow.models import UnitKind, UnitStatus
from app.llm.unit_flow.planner import build_delivery_plan


def _mini_workspace() -> tuple[Path, dict]:
    title = "基于 Spring Boot 与 Vue 的高校图书借阅管理系统的设计与实现"
    domain = "DOM-LIBRARY"
    body = "管理员、读者；借阅申请与归还；公告发布。"
    schema = build_domain_schema(title, domain, proposal_text=body)
    spec = ensure_spec_schema(
        {
            "title": title,
            "domain": domain,
            "archetype": "ARCH-FLOW",
            "schema": schema,
            "proposal": {
                "title": title,
                "background": "图书馆借还高峰排队时间长。",
                "feature_lines": ["图书检索", "借阅申请", "归还登记", "公告"],
            },
        }
    )
    ws = bake_project("unit-flow-test", spec, "unit_flow_test")
    return ws, spec


class UnitFlowPlannerTest(unittest.TestCase):
    def test_build_delivery_plan_has_frozen_and_units(self):
        ws, spec = _mini_workspace()
        try:
            plan = build_delivery_plan(ws, spec, "")
            self.assertEqual(plan.frozen.domain, "DOM-LIBRARY")
            self.assertGreater(len(plan.units), 0)
            kinds = {u.kind for u in plan.units}
            self.assertIn(UnitKind.island_labels, kinds)
            ids = [u.id for u in plan.units]
            self.assertTrue(any(i.startswith("island.labels.") for i in ids))
            roundtrip = plan.to_dict()
            self.assertIn("units", roundtrip)
            self.assertIn("frozen", roundtrip)
        finally:
            import shutil

            shutil.rmtree(ws, ignore_errors=True)

    def test_plan_persists_json_shape(self):
        ws, spec = _mini_workspace()
        try:
            plan = build_delivery_plan(ws, spec, "岗位：馆员、读者")
            data = plan.to_dict()
            self.assertEqual(data["version"], 1)
            self.assertTrue(all("id" in u and "kind" in u for u in data["units"]))
        finally:
            import shutil

            shutil.rmtree(ws, ignore_errors=True)


class UnitFlowMergeTest(unittest.TestCase):
    def test_deterministic_merge_without_llm_results(self):
        ws, spec = _mini_workspace()
        try:
            result = apply_unit_results_to_workspace(ws, spec, [], llm_enabled=False)
            self.assertTrue(result.ok)
            self.assertIn("deterministic", result.detail or result.mode)
            self.assertTrue((ws / "islands").exists())
        finally:
            import shutil

            shutil.rmtree(ws, ignore_errors=True)

    def test_merge_island_patch_fragment(self):
        from app.llm.unit_flow.models import UnitResult

        ws, spec = _mini_workspace()
        try:
            results = [
                UnitResult(
                    "island.labels.0",
                    UnitStatus.done,
                    patch={"labels": {"authEyebrow": "图书借阅", "authLead": "线上借还"}},
                    attempts=1,
                )
            ]
            ok = apply_unit_results_to_workspace(ws, spec, results, llm_enabled=True)
            self.assertTrue(ok.ok)
            schema = spec.get("schema") or {}
            labels = schema.get("labels") or {}
            self.assertEqual(labels.get("authEyebrow"), "图书借阅")
        finally:
            import shutil

            shutil.rmtree(ws, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
