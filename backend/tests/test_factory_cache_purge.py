"""工厂共享缓存清理：不动工程正文，有预览时拒绝。"""

from __future__ import annotations

from pathlib import Path

from app.services import factory_cache_purge as purge
from app.services import runtime as rt


def test_purge_removes_cache_and_runtime_tmp(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    ws = tmp_path / "workspace"
    (cache / "baseline-frontend" / "node_modules").mkdir(parents=True)
    (cache / "baseline-frontend" / "node_modules" / "x").write_text("1", encoding="utf-8")
    (cache / "auth-heroes").mkdir()
    (cache / "auth-heroes" / "a.jpg").write_bytes(b"img")
    proj = ws / "p1"
    (proj / ".runtime-tmp").mkdir(parents=True)
    (proj / ".runtime-tmp" / "t").write_text("tmp", encoding="utf-8")
    (proj / "frontend" / "src").mkdir(parents=True)
    (proj / "frontend" / "src" / "App.vue").write_text("ok", encoding="utf-8")

    class _S:
        cache_dir = cache
        workspace_dir = ws

    monkeypatch.setattr(purge, "get_settings", lambda: _S())
    monkeypatch.setattr(purge, "preview_running_count", lambda: 0)

    status = purge.cache_status()
    assert status["can_purge"] is True
    assert status["total_bytes"] > 0

    result = purge.purge_factory_cache()
    assert result["ok"] is True
    assert not (cache / "baseline-frontend").exists()
    assert not (proj / ".runtime-tmp").exists()
    assert (proj / "frontend" / "src" / "App.vue").read_text(encoding="utf-8") == "ok"
    assert cache.is_dir()


def test_purge_blocked_when_preview_running(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    (cache / "baseline-frontend").mkdir(parents=True)
    (cache / "baseline-frontend" / "x").write_text("1", encoding="utf-8")

    class _S:
        cache_dir = cache
        workspace_dir = tmp_path / "ws"

    monkeypatch.setattr(purge, "get_settings", lambda: _S())
    monkeypatch.setattr(purge, "preview_running_count", lambda: 2)

    result = purge.purge_factory_cache()
    assert result["ok"] is False
    assert (cache / "baseline-frontend" / "x").exists()
    assert "预览" in result["message"]


def test_preview_running_count_uses_store(monkeypatch):
    class _Proc:
        def poll(self):
            return None

    class _H:
        process = _Proc()

    monkeypatch.setattr(rt.STORE, "backends", {"a": _H()}, raising=False)
    monkeypatch.setattr(rt.STORE, "frontends", {}, raising=False)
    assert purge.preview_running_count() == 1
