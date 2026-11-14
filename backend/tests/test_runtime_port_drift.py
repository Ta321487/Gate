"""预览端口登记漂移：停启收尸 + 探活认实占端口。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.services import runtime as rt
from app.services.project_projection import sync_project_runtime


def test_port_from_side_log_reads_last_start(tmp_path: Path, monkeypatch) -> None:
    log_dir = tmp_path / "logs" / "gf-x"
    log_dir.mkdir(parents=True)
    (log_dir / "backend.log").write_text(
        "--- start port=9100 db=demo ---\nTomcat started\n"
        "--- start port=9101 db=demo ---\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        rt,
        "get_settings",
        lambda: SimpleNamespace(logs_dir=tmp_path / "logs", workspace_dir=tmp_path / "ws"),
    )
    assert rt.port_from_side_log("gf-x", "backend") == 9101


def test_stop_backend_kills_registered_and_log_port(tmp_path: Path, monkeypatch) -> None:
    log_dir = tmp_path / "logs" / "gf-x"
    log_dir.mkdir(parents=True)
    (log_dir / "backend.log").write_text(
        "--- start port=9100 db=demo ---\nUP\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        rt,
        "get_settings",
        lambda: SimpleNamespace(logs_dir=tmp_path / "logs", workspace_dir=tmp_path / "ws"),
    )
    killed: list[int] = []

    def _fake_kill(port: int, pids=None) -> None:  # noqa: ANN001
        killed.append(int(port))

    with (
        patch.object(rt, "_kill_port", side_effect=_fake_kill),
        patch.object(rt, "kill_pool_orphans_for_workspace", return_value=[]),
    ):
        rt.stop_backend("gf-x", 9101, workspace=None)
    assert set(killed) == {9100, 9101}
    assert (log_dir / "backend.log").read_text(encoding="utf-8").startswith("--- stopped ---")


def test_backend_status_healthy_on_log_port_when_registered_dead(
    tmp_path: Path, monkeypatch
) -> None:
    log_dir = tmp_path / "logs" / "gf-x"
    log_dir.mkdir(parents=True)
    (log_dir / "backend.log").write_text(
        "--- start port=9100 db=demo ---\nTomcat started\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        rt,
        "get_settings",
        lambda: SimpleNamespace(logs_dir=tmp_path / "logs", workspace_dir=tmp_path / "ws"),
    )

    def _healthy(port: int) -> bool:
        return int(port) == 9100

    with (
        patch.object(rt, "backend_port_healthy", side_effect=_healthy),
        patch.object(rt, "_tcp_open", side_effect=lambda p, timeout=0.15: int(p) == 9100),
        patch.object(rt, "backend_running", return_value=True),
        patch.object(rt, "workspace_pool_listening_port", return_value=None),
    ):
        # 登记 9101 空，实占在日志 9100 → 须 healthy，不能假 starting
        assert rt.backend_status("gf-x", 9101) == "healthy"


def test_sync_heals_registered_backend_port(tmp_path: Path, monkeypatch) -> None:
    log_dir = tmp_path / "logs" / "gf-x"
    ws = tmp_path / "ws" / "gf-x"
    log_dir.mkdir(parents=True)
    ws.mkdir(parents=True)
    (log_dir / "backend.log").write_text(
        "--- start port=9100 ---\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.services.project_projection.get_settings",
        lambda: SimpleNamespace(logs_dir=tmp_path / "logs", workspace_dir=tmp_path / "ws"),
    )
    monkeypatch.setattr(
        rt,
        "get_settings",
        lambda: SimpleNamespace(logs_dir=tmp_path / "logs", workspace_dir=tmp_path / "ws"),
    )
    project = SimpleNamespace(
        id="gf-x",
        backend_port=9101,
        frontend_port=9200,
        backend_running=True,
        frontend_running=False,
        status="running",
    )

    with (
        patch.object(rt, "discover_backend_port", return_value=9100),
        patch.object(rt, "discover_frontend_port", return_value=9200),
        patch.object(rt, "backend_port_healthy", side_effect=lambda p: int(p) == 9100),
        patch.object(rt, "frontend_port_healthy", return_value=False),
        patch.object(rt, "backend_status", return_value="healthy"),
        patch.object(rt, "frontend_status", return_value="stopped"),
    ):
        be_st, fe_st, dirty = sync_project_runtime(project, probe_http=True)
    assert dirty is True
    assert project.backend_port == 9100
    assert be_st == "healthy"
    assert fe_st == "stopped"


def test_start_frontend_proxy_uses_effective_backend(
    tmp_path: Path, monkeypatch
) -> None:
    ws = tmp_path / "proj"
    fe = ws / "frontend"
    fe.mkdir(parents=True)
    (fe / "package.json").write_text('{"name":"x"}', encoding="utf-8")
    log_dir = tmp_path / "logs" / "gf-x"
    log_dir.mkdir(parents=True)
    monkeypatch.setattr(
        rt,
        "get_settings",
        lambda: SimpleNamespace(
            logs_dir=tmp_path / "logs",
            workspace_dir=tmp_path / "ws",
            bind_host="127.0.0.1",
        ),
    )
    captured: dict[str, str] = {}

    def _fake_popen(*_a, **kw):  # noqa: ANN001
        env = kw.get("env") or {}
        captured["proxy"] = env.get("VITE_API_PROXY", "")
        return SimpleNamespace(pid=1, poll=lambda: None, wait=lambda timeout=None: None)

    with (
        patch.object(rt, "stop_frontend"),
        patch.object(rt, "discover_backend_port", return_value=9100),
        patch.object(rt, "_resolve_cmd", return_value="npm"),
        patch.object(rt, "prepare_frontend_deps"),
        patch.object(rt, "_clear_vite_cache"),
        patch.object(rt.subprocess, "Popen", side_effect=_fake_popen),
        patch.object(rt, "frontend_deps_ok", return_value=True),
    ):
        # Windows 分支写 cmd；非 win 走 sh。统一 mock Popen 覆盖 win 路径需 platform
        monkeypatch.setattr(rt.sys, "platform", "win32")
        rt.start_frontend("gf-x", ws, 9200, 9101)
    assert captured.get("proxy") == "http://127.0.0.1:9100"
    log = (log_dir / "frontend.log").read_text(encoding="utf-8")
    assert "proxy=9100" in log
    assert "registered=9101" in log or "drift" in log.lower()
