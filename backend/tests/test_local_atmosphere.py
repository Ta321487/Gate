"""本地氛围图：主题色解析 + 无网生成。"""

from __future__ import annotations

from pathlib import Path

from app.bake.local_atmosphere import (
    _all_theme_palettes,
    family_for_domain,
    palette_for_theme,
    render_local_atmosphere,
    write_local_atmosphere_cached,
)


def test_theme_palettes_load_from_css():
    pals = _all_theme_palettes()
    assert len(pals) >= 20
    assert "crm-ocean" in pals
    assert "lib-ink" in pals
    crm = pals["crm-ocean"]
    assert crm.brand == (0x1D, 0x5A, 0x7A)
    assert crm.accent == (0x2D, 0x7A, 0x9E)


def test_family_differs_across_domains():
    assert family_for_domain("DOM-CRM") == "office"
    assert family_for_domain("DOM-LIBRARY") == "campus"
    assert family_for_domain("DOM-SHOP") == "trade"
    assert family_for_domain("DOM-IT") == "tech"


def test_render_matches_theme_and_varies_by_slot(tmp_path: Path):
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    c = tmp_path / "c.jpg"
    assert render_local_atmosphere(
        a, domain="DOM-CRM", theme="crm-ocean", kind="auth", slot=0
    )
    assert render_local_atmosphere(
        b, domain="DOM-CRM", theme="crm-sand", kind="auth", slot=0
    )
    assert render_local_atmosphere(
        c, domain="DOM-CRM", theme="crm-ocean", kind="auth", slot=1
    )
    assert a.stat().st_size > 2000
    assert a.read_bytes() != b.read_bytes()  # 不同 theme → 不同配色
    assert a.read_bytes() != c.read_bytes()  # 同 theme 不同 slot → 构图差


def test_auth_hero_falls_back_to_local(monkeypatch, tmp_path: Path):
    from app.bake import auth_hero as ah

    monkeypatch.setattr(ah, "_fetch_via_api", lambda *a, **k: False)
    monkeypatch.setattr(ah, "_fetch_fallback_photo", lambda *a, **k: False)

    class _S:
        unsplash_access_key = ""
        cache_dir = tmp_path / "cache"

    monkeypatch.setattr(ah, "get_settings", lambda: _S())
    ws = tmp_path / "ws"
    assert ah.fetch_auth_hero(ws, "DOM-CRM", "crm-ocean")
    hero = ws / "frontend" / "public" / "auth-hero.jpg"
    assert hero.is_file() and hero.stat().st_size > 2000


def test_portal_fills_local_when_download_fails(monkeypatch, tmp_path: Path):
    from app.bake import portal_banners as pb

    monkeypatch.setattr(pb, "_search_photo_urls", lambda *a, **k: [])
    monkeypatch.setattr(pb, "_download", lambda *a, **k: False)
    monkeypatch.setattr(pb, "_download_portal_photo", lambda *a, **k: False)
    monkeypatch.setattr(pb, "domain_wants_portal_banners", lambda d: True)

    class _S:
        unsplash_access_key = ""
        cache_dir = tmp_path / "cache"

    monkeypatch.setattr(pb, "get_settings", lambda: _S())
    ws = tmp_path / "ws"
    slides = pb.fetch_portal_banners(
        ws,
        "DOM-LIBRARY",
        "lib-ink",
        schema={"shell": {"title": "测试图书", "eyebrow": "图书"}},
        count=3,
    )
    assert len(slides) >= 3
    for s in slides:
        path = ws / "frontend" / "public" / s["src"].lstrip("/")
        assert path.is_file() and path.stat().st_size > 2000


def test_write_cached_reuses_file(tmp_path: Path):
    dest1 = tmp_path / "out" / "1.jpg"
    dest2 = tmp_path / "out" / "2.jpg"
    cache = tmp_path / "cache"
    assert write_local_atmosphere_cached(
        dest1,
        domain="DOM-FOOD",
        theme="food-chili",
        kind="portal",
        slot=1,
        cache_dir=cache,
    )
    first = dest1.read_bytes()
    assert write_local_atmosphere_cached(
        dest2,
        domain="DOM-FOOD",
        theme="food-chili",
        kind="portal",
        slot=1,
        cache_dir=cache,
    )
    assert dest2.read_bytes() == first


def test_palette_for_unknown_theme_defaults():
    pal = palette_for_theme("no-such-theme-xyz")
    assert pal.brand[0] >= 0
