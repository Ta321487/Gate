"""孤儿磁盘清理：受理式全量 + 额度互斥。"""

from __future__ import annotations

import asyncio
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile

from app.services import orphan_disk_purge as odp


class TestOrphanDiskPurgeService(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        odp._set(
            status="idle",
            mode=None,
            accepted=False,
            already_running=False,
            started_at=None,
            finished_at=None,
            message="",
            removed=0,
            errors=[],
            last_result=None,
        )
        if odp._run_lock.locked():
            odp._run_lock.release()
        odp._task = None

    async def test_enqueue_full_returns_immediately_and_finishes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ws = base / "workspace"
            logs = base / "logs"
            ws.mkdir()
            logs.mkdir()
            (ws / "gf-dead").mkdir()

            with (
                patch("app.services.project_disk.get_settings") as gs,
                patch("app.services.project_disk.rt.detach_frontend_deps"),
                patch("app.services.project_disk.ORPHAN_FRESH_GRACE_SEC", 0),
            ):
                gs.return_value = SimpleNamespace(workspace_dir=ws, logs_dir=logs)
                snap = await odp.enqueue_full(set())
                self.assertTrue(snap["accepted"])
                self.assertEqual(snap["status"], "running")
                for _ in range(50):
                    st = odp.snapshot()
                    if st["status"] in ("done", "error"):
                        break
                    await asyncio.sleep(0.05)
                st = odp.snapshot()
                self.assertEqual(st["status"], "done")
                self.assertGreaterEqual(st["removed"], 1)
                self.assertFalse((ws / "gf-dead").exists())

    async def test_second_enqueue_while_running_is_rejected(self) -> None:
        hold = threading.Event()
        release = threading.Event()

        def slow_purge(*_a, **_k):
            hold.set()
            release.wait(timeout=2)
            return {
                "removed": 0,
                "errors": [],
                "removed_workspaces": [],
                "removed_logs": [],
                "removed_zips": [],
            }

        with patch.object(odp, "_run_purge", side_effect=slow_purge):
            first = await odp.enqueue_full({"alive"})
            self.assertTrue(first["accepted"])
            for _ in range(50):
                if hold.is_set():
                    break
                await asyncio.sleep(0.02)
            self.assertTrue(hold.is_set())
            second = await odp.enqueue_full({"alive"})
            self.assertTrue(second["already_running"])
            self.assertFalse(second["accepted"])
            release.set()
            for _ in range(50):
                if odp.snapshot()["status"] != "running":
                    break
                await asyncio.sleep(0.05)

    def test_budgeted_respects_lock(self) -> None:
        self.assertTrue(odp._run_lock.acquire(blocking=False))
        try:
            with patch("app.services.orphan_disk_purge.get_settings") as gs:
                gs.return_value = SimpleNamespace(gf_orphan_purge_per_pass=1)
                self.assertIsNone(odp.try_budgeted_purge(set()))
        finally:
            odp._run_lock.release()

    def test_purge_skips_bake_in_progress_workspace(self) -> None:
        from app.services.project_disk import BAKE_IN_PROGRESS_REL, purge_orphan_project_disk

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ws = base / "workspace"
            logs = base / "logs"
            ws.mkdir()
            logs.mkdir()
            baking = ws / "gf-baking"
            baking.mkdir()
            lock = baking / BAKE_IN_PROGRESS_REL
            lock.parent.mkdir(parents=True)
            lock.write_text("baking\n", encoding="utf-8")
            dead = ws / "gf-dead"
            dead.mkdir()
            with (
                patch("app.services.project_disk.get_settings") as gs,
                patch("app.services.project_disk.rt.detach_frontend_deps"),
                patch("app.services.project_disk.ORPHAN_FRESH_GRACE_SEC", 0),
            ):
                gs.return_value = SimpleNamespace(workspace_dir=ws, logs_dir=logs)
                result = purge_orphan_project_disk(set())
            self.assertTrue(baking.exists(), "bake 中工作区不得被清")
            self.assertFalse(dead.exists(), "无标记孤儿应被清")
            self.assertIn("gf-dead", result.get("removed_workspaces") or [])
            self.assertNotIn("gf-baking", result.get("removed_workspaces") or [])


if __name__ == "__main__":
    unittest.main()
