"""重新生成不得跳过 copy_bake（曾误把已生成工程偷跳到 gate 只重打 ZIP）。"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.models import ProjectStatus
from app.services.jobs import resolve_bake_from_step


class RegenerateMustFullBakeTests(unittest.TestCase):
    def test_generated_with_workspace_still_starts_at_zero(self) -> None:
        p = SimpleNamespace(
            status=ProjectStatus.generated.value,
            workspace_path=r"D:\fake\workspace",
            delivery_review={"status": "closed"},
        )
        with patch("app.services.jobs.Path") as path_cls:
            path_cls.return_value.exists.return_value = True
            self.assertEqual(resolve_bake_from_step(p, 0), 0)

    def test_running_preview_still_starts_at_zero(self) -> None:
        p = SimpleNamespace(
            status=ProjectStatus.running.value,
            workspace_path=r"D:\fake\workspace",
            delivery_review={"status": "closed"},
        )
        self.assertEqual(resolve_bake_from_step(p, 0), 0)

    def test_explicit_resume_keeps_from_step(self) -> None:
        p = SimpleNamespace(
            status=ProjectStatus.failed.value,
            workspace_path=r"D:\fake\workspace",
            delivery_review={"status": "closed"},
        )
        self.assertEqual(resolve_bake_from_step(p, 4), 4)

    def test_active_review_blocks_full_rebake(self) -> None:
        p = SimpleNamespace(
            status=ProjectStatus.generated.value,
            workspace_path=r"D:\fake\workspace",
            delivery_review={"status": "active"},
        )
        with self.assertRaises(ValueError):
            resolve_bake_from_step(p, 0)


if __name__ == "__main__":
    unittest.main()
