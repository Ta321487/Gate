"""失败分析聚合与草稿丢弃（不调真实 LLM）。"""

from __future__ import annotations

import time
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services import bake_fail_analysis as bfa
from app.services.bake_fail_classify import FIX_LOCUS


class FailAnalysisUnitTests(unittest.IsolatedAsyncioTestCase):
    async def test_build_fail_analysis_buckets(self):
        now = datetime.now()
        jobs = [
            SimpleNamespace(
                id=1,
                project_id="p1",
                kind="bake",
                status="failed",
                step="gate_e2e",
                steps=[{"key": "gate_e2e", "status": "fail"}],
                error="质量检查未通过 · 暂不可下载交付包 · 交付质量摘要 · 1 项 error",
                error_code="GATE_QA",
                finished_at=now,
                started_at=now,
                created_at=now,
            ),
            SimpleNamespace(
                id=2,
                project_id="p2",
                kind="bake",
                status="failed",
                step="copy_bake",
                steps=[{"key": "copy_bake", "status": "fail"}],
                error="错皮/怪交互硬闸失败 [DOM-SHOP] title=t: x",
                error_code=None,
                finished_at=now,
                started_at=now,
                created_at=now,
            ),
        ]
        projects = {
            "p1": SimpleNamespace(
                id="p1",
                title="题甲",
                domain="DOM-EVENT",
                persistence="jdbc",
                gates={"p3q": {"ok": False}, "overall": False},
            ),
            "p2": SimpleNamespace(
                id="p2",
                title="题乙",
                domain="DOM-SHOP",
                persistence="mybatis",
                gates={},
            ),
        }

        class _Result:
            def __init__(self, rows):
                self._rows = rows

            def scalars(self):
                return self

            def all(self):
                return self._rows

        class _Db:
            async def execute(self, _stmt):
                # 第一次 Job，第二次 Project
                if not hasattr(self, "_n"):
                    self._n = 0
                self._n += 1
                if self._n == 1:
                    return _Result(jobs)
                return _Result(list(projects.values()))

        with patch.object(bfa, "_annotate_samples_resolve", AsyncMock()):
            out = await bfa.build_fail_analysis(_Db(), sample_page=1, sample_page_size=10)
        self.assertEqual(out["totals"]["failed"], 2)
        self.assertEqual(out["samples_total"], 2)
        self.assertEqual(len(out["samples"]), 2)
        codes = {x["code"]: x["count"] for x in out["by_code"]}
        self.assertEqual(codes.get("GATE_QA"), 1)
        self.assertEqual(codes.get("BAKE_SKIN"), 1)
        self.assertTrue(out["priorities"])
        self.assertEqual(out["priorities"][0]["fix_locus"], FIX_LOCUS[out["priorities"][0]["code"]])
        # A 档不得用自由文案冒充
        for p in out["priorities"]:
            self.assertEqual(p["fix_locus"], FIX_LOCUS[p["code"]])

        with patch.object(bfa, "_annotate_samples_resolve", AsyncMock()):
            page2 = await bfa.build_fail_analysis(_Db(), sample_page=2, sample_page_size=1)
        self.assertEqual(page2["samples_total"], 2)
        self.assertEqual(len(page2["samples"]), 1)

    def test_discard_draft(self):
        bfa._draft_store_set(
            99,
            {
                "draft": "假修法",
                "status": "unverified",
                "fix_locus": FIX_LOCUS["BAKE_SKIN"],
            },
        )
        self.assertTrue(bfa.discard_fix_draft(99))
        self.assertIsNone(bfa.get_fix_draft(99))
        self.assertFalse(bfa.discard_fix_draft(99))

    def test_draft_ttl_and_max(self):
        bfa._FIX_DRAFTS.clear()
        bfa._draft_store_set(1, {"draft": "a", "job_id": 1})
        self.assertIsNotNone(bfa.get_fix_draft(1))
        bfa._FIX_DRAFTS[1]["at"] = time.time() - bfa._DRAFT_TTL_SEC - 10
        self.assertIsNone(bfa.get_fix_draft(1))

        bfa._FIX_DRAFTS.clear()
        for i in range(bfa._DRAFT_MAX + 5):
            bfa._draft_store_set(i, {"draft": f"d{i}", "job_id": i})
        self.assertLessEqual(len(bfa._FIX_DRAFTS), bfa._DRAFT_MAX)

    async def test_classify_assist_rejects_bad_code(self):
        class _Rt:
            def endpoint_chain(self):
                return [object()]

        async def _chat(*_a, **_k):
            return SimpleNamespace(ok=True, data={"code": "NOT_A_REAL_CODE", "reason": "x"}, error=None)

        with (
            patch.object(bfa, "load_llm_runtime", AsyncMock(return_value=_Rt())),
            patch.object(bfa, "chat", _chat),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                await bfa.classify_assist(AsyncMock(), error="错皮/怪交互硬闸失败 x")
            self.assertIn("有效类型", str(ctx.exception))

    async def test_fix_draft_reuses_cache(self):
        bfa._draft_store_set(
            42,
            {
                "draft": "稳定建议",
                "status": "unverified",
                "fix_locus": FIX_LOCUS["BAKE_SKIN"],
                "job_id": 42,
                "code": "BAKE_SKIN",
            },
        )

        class _Rt:
            def endpoint_chain(self):
                return [object()]

        chat_mock = AsyncMock(
            return_value=SimpleNamespace(ok=True, data={"draft": "新建议", "paths": []}, error=None)
        )
        hint = {
            "maybe_resolved": False,
            "resolve_stale": False,
            "resolve_note": "",
        }
        with (
            patch.object(bfa, "load_llm_runtime", AsyncMock(return_value=_Rt())),
            patch.object(bfa, "chat", chat_mock),
            patch.object(bfa, "job_fix_resolve_hint", AsyncMock(return_value=hint)),
        ):
            cached = await bfa.create_fix_draft(
                AsyncMock(), job_id=42, error="错皮", code="BAKE_SKIN"
            )
            self.assertTrue(cached.get("cached"))
            self.assertEqual(cached["draft"], "稳定建议")
            chat_mock.assert_not_awaited()

            forced = await bfa.create_fix_draft(
                AsyncMock(), job_id=42, error="错皮", code="BAKE_SKIN", force=True
            )
            self.assertFalse(forced.get("cached"))
            self.assertEqual(forced["draft"], "新建议")
            chat_mock.assert_awaited()

    async def test_job_fix_resolve_hint_after_success(self):
        failed = SimpleNamespace(
            id=10,
            project_id="p1",
            kind="bake",
            status="failed",
            error_code="BAKE_PACK_LEAN",
        )

        class _Db:
            async def get(self, _model, _id):
                return failed

            async def execute(self, stmt):
                sql = str(stmt)
                if "success" in sql or "JobStatus.success" in sql:
                    return SimpleNamespace(scalar_one_or_none=lambda: 20)
                # later same-code fail query
                return SimpleNamespace(scalar_one_or_none=lambda: None)

        # Real execute uses compiled SQL; mock by patching select path via side effects on id checks.
        calls = {"n": 0}

        class _Db2:
            async def get(self, _model, _id):
                return failed

            async def execute(self, _stmt):
                calls["n"] += 1
                if calls["n"] == 1:
                    return SimpleNamespace(scalar_one_or_none=lambda: 20)
                return SimpleNamespace(scalar_one_or_none=lambda: None)

        out = await bfa.job_fix_resolve_hint(_Db2(), job_id=10, code="BAKE_PACK_LEAN")
        self.assertTrue(out["maybe_resolved"])
        self.assertIn("可能已失效", out["resolve_note"])


if __name__ == "__main__":
    unittest.main()
