"""匹配确认灌氛围缓存。"""

from __future__ import annotations

from pathlib import Path

from app.bake import atmosphere_prefetch as ap
from app.bake import unsplash_fetch as uf


def test_auth_cache_path_stable(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "app.bake.atmosphere_prefetch.get_settings",
        lambda: type("S", (), {"cache_dir": tmp_path})(),
    )
    a = ap.auth_cache_path("DOM-LIBRARY", "gen-ink", cache_dir=tmp_path)
    b = ap.auth_cache_path("DOM-LIBRARY", "gen-ink", cache_dir=tmp_path)
    assert a == b
    assert "auth-heroes" in str(a)
    assert a.name.endswith(".jpg")


def test_prefetch_records_real_when_cache_written(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "app.bake.atmosphere_prefetch.get_settings",
        lambda: type("S", (), {"cache_dir": tmp_path, "unsplash_access_key": ""})(),
    )
    monkeypatch.setattr(uf, "http_proxy", lambda: "")

    def _fake_hero(ws: Path, domain: str, theme: str) -> bool:
        dest = ws / "frontend" / "public" / "auth-hero.jpg"
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob = b"\xff\xd8\xff" + b"z" * 3000
        dest.write_bytes(blob)
        cache = ap.auth_cache_path(domain, theme, cache_dir=tmp_path)
        uf.cache_write(cache, dest)
        return True

    monkeypatch.setattr(
        "app.bake.auth_hero.fetch_auth_hero",
        _fake_hero,
    )
    monkeypatch.setattr(
        "app.bake.portal_banners.domain_wants_portal_banners",
        lambda _d: False,
    )

    out = ap.prefetch_match_atmosphere("DOM-LIBRARY", "gen-ink")
    assert out["auth_ok"] is True
    assert out["auth_real"] is True
    assert out["auth_was_cached"] is False
    assert out["portal_slides"] == 0
    assert "at" in out


def test_apply_atmosphere_to_spec():
    spec = ap.apply_atmosphere_to_spec({"x": 1}, {"auth_real": True})
    assert spec["x"] == 1
    assert spec["atmosphere"]["auth_real"] is True
