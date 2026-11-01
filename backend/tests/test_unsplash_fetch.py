"""Unsplash 共用拉图：缓存读写 / 提示真源 / 下载重试。"""

from __future__ import annotations

from pathlib import Path

from app.bake import unsplash_fetch as uf


def test_operator_hints_single_source():
    assert len(uf.OPERATOR_HINTS) >= 3
    text = uf.operator_hint_text()
    assert "本机缓存" in text
    assert "UNSPLASH_HTTP_PROXY" in text
    st = uf.status_payload()
    assert st["hints"] == list(uf.OPERATOR_HINTS)
    assert "vault_auth_heroes" in st


def test_cache_read_write_roundtrip(tmp_path: Path):
    src = tmp_path / "src.jpg"
    src.write_bytes(b"\xff\xd8\xff" + b"x" * 3000)
    cache = uf.cache_file("auth-heroes", "dom-theme-abcd.jpg", cache_dir=tmp_path / "cache")
    uf.cache_write(cache, src)
    dest = tmp_path / "out.jpg"
    assert uf.cache_read(cache, dest)
    assert dest.read_bytes() == src.read_bytes()


def test_cache_read_rejects_tiny(tmp_path: Path):
    cache = tmp_path / "tiny.jpg"
    cache.write_bytes(b"nope")
    dest = tmp_path / "out.jpg"
    assert not uf.cache_read(cache, dest)


def test_download_retries_then_ok(monkeypatch, tmp_path: Path):
    calls = {"n": 0}
    good = b"\xff\xd8\xff" + b"y" * 3000

    class _Resp:
        headers = {"Content-Type": "image/jpeg"}

        def read(self):
            return good

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _Opener:
        def open(self, req, timeout=8.0):
            calls["n"] += 1
            if calls["n"] < 2:
                raise TimeoutError("slow")
            return _Resp()

    monkeypatch.setattr(uf, "_opener", lambda: _Opener())
    dest = tmp_path / "d.jpg"
    assert uf.download_image("https://images.unsplash.com/photo-x", dest, retries=3)
    assert calls["n"] == 2
    assert dest.stat().st_size > 2000


def test_direct_photo_url_shape():
    u = uf.direct_photo_url("1507842217343-583bb7270b66", width=1800, height=720)
    assert u.startswith("https://images.unsplash.com/photo-1507842217343-583bb7270b66")
    assert "w=1800" in u and "h=720" in u


def test_auth_hero_and_portal_reuse_fetch_module():
    from app.bake import auth_hero as ah
    from app.bake import portal_banners as pb

    assert ah._download is uf.download_image or ah._download == uf.download_image
    assert pb._download is uf.download_image or pb._download == uf.download_image
    assert pb._search_photo_urls is uf.search_photo_urls or pb._search_photo_urls == uf.search_photo_urls
