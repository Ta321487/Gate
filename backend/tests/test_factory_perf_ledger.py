"""工厂控制台性能账本 P1–P7 契约（docs/factory-perf-ledger.md）。"""

from __future__ import annotations

import inspect
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BE = ROOT / "backend" / "app"
FE = ROOT / "frontend" / "src"


class FactoryPerfLedgerContract(unittest.TestCase):
    def test_ledger_doc_marks_all_fixed(self) -> None:
        doc = (ROOT / "docs" / "factory-perf-ledger.md").read_text(encoding="utf-8")
        self.assertIn("工厂控制台性能账本", doc)
        for pid in ("P1", "P2", "P3", "P4", "P5", "P6", "P7"):
            self.assertIn(pid, doc)
        self.assertGreaterEqual(doc.count("**已修**"), 7)

    def test_p1_poll_endpoint_and_frontend(self) -> None:
        crud = (BE / "api" / "projects" / "crud.py").read_text(encoding="utf-8")
        self.assertIn("/{project_id}/poll", crud)
        self.assertIn("get_project_poll", crud)
        self.assertIn("ProjectPollOut", crud)
        self.assertIn("build_review_payload", (BE / "api" / "projects" / "common.py").read_text(encoding="utf-8"))
        # poll 路径不得调用 build_review_payload
        poll_src = crud.split("async def get_project_poll", 1)[1].split(
            "async def get_project", 1
        )[0]
        self.assertNotIn("build_review_payload", poll_src)
        self.assertNotIn("refresh_project_projection", poll_src)
        self.assertNotIn("workspace_delivery_hash", poll_src)

        api = (FE / "api.js").read_text(encoding="utf-8")
        self.assertIn("/projects/${id}/poll", api)
        detail = (FE / "views" / "projectDetail" / "useProjectDetail.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("getProjectPoll", detail)
        self.assertIn("...(p.value || {})", detail)

    def test_p2_runtime_action_uses_to_thread(self) -> None:
        src = (BE / "api" / "projects" / "runtime.py").read_text(encoding="utf-8")
        body = src.split("async def runtime_action", 1)[1].split(
            '@router.get("/{project_id}/fill-plan"', 1
        )[0]
        self.assertIn("await asyncio.to_thread(_blocking_runtime)", body)
        # sleep / start_* 只允许出现在 _blocking_runtime 闭包内
        outer, _, rest = body.partition("def _blocking_runtime")
        self.assertNotIn("time.sleep(", outer)
        self.assertNotIn("rt.start_backend(", outer)
        self.assertIn("time.sleep(", rest)
        self.assertIn("rt.start_backend(", rest)

    def test_p3_list_jobs_no_per_row_get(self) -> None:
        src = (BE / "api" / "jobs.py").read_text(encoding="utf-8")
        body = src.split("async def list_jobs", 1)[1].split(
            "async def get_job_gate_report", 1
        )[0]
        self.assertIn("Project.id.in_", body)
        self.assertNotIn("await db.get(Project", body)

    def test_p4_list_and_stats_defer_gates(self) -> None:
        crud = (BE / "api" / "projects" / "crud.py").read_text(encoding="utf-8")
        self.assertIn("defer(Project.gates)", crud)
        projects = (BE / "services" / "projects.py").read_text(encoding="utf-8")
        self.assertIn("defer(Project.gates)", projects)
        delivery = (BE / "services" / "project_delivery.py").read_text(encoding="utf-8")
        self.assertIn("unloaded", delivery)
        self.assertIn("zip_ready", delivery)

    def test_p5_find_overlaps_load_only(self) -> None:
        src = (BE / "services" / "thesis_absorb.py").read_text(encoding="utf-8")
        body = src.split("async def find_overlaps", 1)[1].split(
            "_FIGURE_CARRY_KEYS", 1
        )[0]
        self.assertIn("load_only", body)
        self.assertIn("FactoryThesisAbsorb.proposal_json", body)
        self.assertIn(".limit(200)", body)
        # 注释可提 draft_schema_sql；load_only 列清单不得包含它
        load_block = body.split("load_only(", 1)[1].split(")", 1)[0]
        self.assertNotIn("draft_schema_sql", load_block)

    def test_p6_reconcile_defaults_and_zip_stale_budget(self) -> None:
        cfg = (BE / "core" / "config.py").read_text(encoding="utf-8")
        self.assertIn("default=8.0", cfg)
        self.assertIn('alias="GF_RUNTIME_RECONCILE_SEC"', cfg)
        self.assertIn("default=1", cfg)
        self.assertIn('alias="GF_RECONCILE_SCAN_PER_PASS"', cfg)
        proj = (BE / "services" / "project_projection.py").read_text(encoding="utf-8")
        self.assertIn("compute=bool(scanned) or budget <= 0", proj)

    def test_p7_diagram_fit_debounce_shared(self) -> None:
        util = (FE / "utils" / "diagramFitDebounce.js").read_text(encoding="utf-8")
        self.assertIn("watchFrameHeightFit", util)
        self.assertIn("debounce", util)
        viewers = (
            "ModuleDiagramViewer.vue",
            "SequenceDiagramViewer.vue",
            "ActivityDiagramViewer.vue",
            "UseCaseDiagramViewer.vue",
            "ErDiagramViewer.vue",
            "ArchitectureDiagramViewer.vue",
        )
        for name in viewers:
            src = (FE / "components" / name).read_text(encoding="utf-8")
            self.assertIn("diagramFitDebounce", src, name)
            self.assertIn("watchFrameHeightFit", src, name)
        klass = (FE / "components" / "ClassDiagramViewer.vue").read_text(encoding="utf-8")
        self.assertIn("fitToFrameDebounced", klass)
        frame = (FE / "components" / "useDiagramFrameResize.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("applyPreferredDebounced", frame)


class FactoryPerfLedgerRuntimeSmoke(unittest.TestCase):
    def test_project_poll_out_schema_exists(self) -> None:
        from app.schemas import ProjectPollOut

        fields = set(ProjectPollOut.model_fields)
        self.assertIn("status", fields)
        self.assertIn("zip_ready", fields)
        self.assertNotIn("spec", fields)
        self.assertNotIn("gates", fields)
        self.assertNotIn("checklist", fields)

    def test_runtime_action_source_has_to_thread(self) -> None:
        from app.api.projects import runtime as runtime_mod

        src = inspect.getsource(runtime_mod.runtime_action)
        self.assertIn("to_thread", src)
        self.assertIn("_blocking_runtime", src)


if __name__ == "__main__":
    unittest.main()
