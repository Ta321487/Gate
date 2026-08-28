"""生成前开题措辞核对确认与 start_job 状态。"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.delivery_review import ack_pre_generate, has_proposal_material, require_pre_generate_ack


class GenerateConfirmDiffTests(unittest.TestCase):
    def test_has_proposal_material_filename_only(self):
        p = SimpleNamespace(source_path=None, source_filename="开题.docx")
        self.assertTrue(has_proposal_material(p))

    def test_confirm_diff_flow_in_memory(self):
        p = SimpleNamespace(
            source_path="/data/proposal",
            source_filename="开题.docx",
            delivery_review={},
        )
        self.assertIsNotNone(require_pre_generate_ack(p))
        ack_pre_generate(p)
        self.assertIsNone(require_pre_generate_ack(p))
        self.assertTrue(p.delivery_review.get("pre_generate_ack_at"))

    def test_generate_handler_ack_then_start(self):
        """模拟 generate 端点：confirm_diff 与 start_job 同请求内完成 ack。"""
        from app.api.projects import generate

        async def _run():
            p = SimpleNamespace(
                id="gf-test",
                match_confirmed=True,
                source_path="/x",
                source_filename="a.txt",
                delivery_review={},
            )
            db = AsyncMock()
            db.get = AsyncMock(return_value=p)
            fake_job = SimpleNamespace(id=99)
            with patch("app.api.projects.start_job", new_callable=AsyncMock) as mock_start:
                mock_start.return_value = fake_job
                out = await generate("gf-test", confirm_diff=True, db=db)
            mock_start.assert_awaited_once()
            self.assertIsNone(require_pre_generate_ack(p))
            return out

        import asyncio

        res = asyncio.run(_run())
        self.assertIn("Job #99", res.message)


if __name__ == "__main__":
    unittest.main()
