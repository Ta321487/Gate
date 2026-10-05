"""出包构建：mvn compile 失败必须 ok=False，禁止假通过。"""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.llm.agents_fix import run_fix_agent
from app.llm.runtime import LlmRuntime, ProviderEndpoint


def _rt(*, auto_fix: bool = False, configured: bool = False) -> LlmRuntime:
    ds = ProviderEndpoint(
        name="deepseek",
        api_key="k" if configured else "",
        base_url="https://example.invalid",
        model="m",
    )
    gem = ProviderEndpoint(name="gemini", api_key="", base_url="", model="")
    return LlmRuntime(
        deepseek=ds,
        gemini=gem,
        deepseek_enabled=configured,
        gemini_enabled=False,
        preferred="deepseek",
        match_recommend=False,
        parse_spec=False,
        island_fill=False,
        er_labels=False,
        module_labels=False,
        testcase_labels=False,
        defense_ppt=False,
        auto_fix=auto_fix,
        qa_report=False,
        fix_rounds_max=0,
        fill_unit_concurrency=1,
        project_token_budget=0,
        monthly_token_budget=0,
    )


def _ws(tmp: Path) -> Path:
    (tmp / "backend").mkdir()
    (tmp / "frontend").mkdir()
    return tmp


class AgentsFixCompileGateTests(unittest.TestCase):
    def test_compile_fail_without_auto_fix_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _ws(Path(td))
            db = AsyncMock()
            with patch("app.llm.agents_fix._mvn_compile", return_value=(False, "cannot find symbol")):
                ok, meta = asyncio.run(
                    run_fix_agent(db, _rt(auto_fix=False), project_id="p1", workspace=ws, spec={})
                )
            self.assertFalse(ok)
            self.assertIn("编译失败", meta)

    def test_compile_ok_without_auto_fix_passes(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _ws(Path(td))
            db = AsyncMock()
            with patch("app.llm.agents_fix._mvn_compile", return_value=(True, "compile ok")):
                ok, meta = asyncio.run(
                    run_fix_agent(db, _rt(auto_fix=False), project_id="p1", workspace=ws, spec={})
                )
            self.assertTrue(ok)
            self.assertIn("已预编译", meta)

    def test_auto_fix_exhausted_still_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _ws(Path(td))
            db = AsyncMock()
            with (
                patch("app.llm.agents_fix._mvn_compile", return_value=(False, "COMPILATION ERROR")),
                patch("app.llm.agents_fix.record_call", new_callable=AsyncMock) as rec,
            ):
                ok, meta = asyncio.run(
                    run_fix_agent(
                        db,
                        _rt(auto_fix=True, configured=True),
                        project_id="p1",
                        workspace=ws,
                        spec={},
                    )
                )
            self.assertFalse(ok)
            self.assertIn("编译失败", meta)
            rec.assert_awaited()
            self.assertFalse(rec.await_args.kwargs.get("ok", True))

    def test_skip_mvn_still_passes(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _ws(Path(td))
            db = AsyncMock()
            with patch(
                "app.llm.agents_fix._mvn_compile",
                return_value=(True, "skip · 未检测到 mvn"),
            ):
                ok, meta = asyncio.run(
                    run_fix_agent(db, _rt(auto_fix=False), project_id="p1", workspace=ws, spec={})
                )
            self.assertTrue(ok)
            self.assertIn("skip", meta)


if __name__ == "__main__":
    unittest.main()
