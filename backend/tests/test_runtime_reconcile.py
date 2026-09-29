"""后台运行态投影：列表只读，对账写库与 GET 解耦。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.runtime_reconcile import (
    reconcile_projects_projection,
    start_runtime_reconcile,
    stop_runtime_reconcile,
)


def test_reconcile_projects_projection_commits_when_dirty():
    async def _run() -> None:
        p = SimpleNamespace(id="p1", backend_port=9100, frontend_port=0)
        db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [p]
        db.execute = AsyncMock(return_value=result)
        db.commit = AsyncMock()
        lock = asyncio.Lock()

        with (
            patch(
                "app.services.runtime_reconcile.project_svc.release_read_transaction",
                new_callable=AsyncMock,
            ) as release,
            patch(
                "app.services.runtime_reconcile.rt.listening_tcp_ports",
                return_value={9100},
            ),
            patch(
                "app.services.runtime_reconcile.project_svc.reconcile_list_items",
                return_value=True,
            ) as reconcile,
            patch("app.services.runtime_reconcile.project_svc.reconcile_lock", lock),
        ):
            dirty = await reconcile_projects_projection(db)

        assert dirty is True
        release.assert_awaited_once()
        reconcile.assert_called_once()
        db.commit.assert_awaited_once()

    asyncio.run(_run())


def test_reconcile_projects_projection_skips_commit_when_clean():
    async def _run() -> None:
        p = SimpleNamespace(id="p1", backend_port=0, frontend_port=0)
        db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [p]
        db.execute = AsyncMock(return_value=result)
        db.commit = AsyncMock()
        lock = asyncio.Lock()

        with (
            patch(
                "app.services.runtime_reconcile.project_svc.release_read_transaction",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.runtime_reconcile.project_svc.reconcile_list_items",
                return_value=False,
            ),
            patch("app.services.runtime_reconcile.project_svc.reconcile_lock", lock),
        ):
            dirty = await reconcile_projects_projection(db)

        assert dirty is False
        db.commit.assert_not_awaited()

    asyncio.run(_run())


def test_start_runtime_reconcile_disabled_when_interval_zero():
    async def _run() -> None:
        await stop_runtime_reconcile()
        with patch(
            "app.services.runtime_reconcile.get_settings",
            return_value=SimpleNamespace(gf_runtime_reconcile_sec=0),
        ):
            start_runtime_reconcile()
        await stop_runtime_reconcile()

    asyncio.run(_run())
