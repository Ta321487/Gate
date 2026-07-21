"""质感 / 配色种子挑选与规范化。"""

from app.bake.themes import (
    CHROME_STYLES,
    normalize_chrome,
    pick_chrome,
    pick_theme,
)


def test_chrome_styles_include_dense_ruled():
    ids = {t["id"] for t in CHROME_STYLES}
    assert {"soft", "sharp", "pill", "outline", "dense", "ruled"} <= ids


def test_normalize_chrome():
    assert normalize_chrome("dense") == "dense"
    assert normalize_chrome("nope") == "soft"
    assert normalize_chrome(None) == "soft"


def test_pick_chrome_stable_and_varied():
    a = pick_chrome("医院挂号|DOM-HOSPITAL|chrome")
    b = pick_chrome("医院挂号|DOM-HOSPITAL|chrome")
    assert a == b
    seen = {pick_chrome(f"t{i}|DOM-X|chrome") for i in range(48)}
    assert len(seen) >= 4


def test_pick_theme_stable_and_varied():
    a = pick_theme("DOM-LIBRARY", "图书系统|DOM-LIBRARY|theme")
    b = pick_theme("DOM-LIBRARY", "图书系统|DOM-LIBRARY|theme")
    assert a == b
    seen = {pick_theme("DOM-LIBRARY", f"t{i}|DOM-LIBRARY|theme") for i in range(48)}
    assert len(seen) >= 3


def test_build_spec_chrome_override():
    from app.bake.catalog import build_spec

    spec = build_spec(
        title="测试系统",
        archetype="ARCH-CRUD",
        domain="DOM-LIBRARY",
        theme="lib-ink",
        llm_enabled=False,
        match_mode="recommended",
        confidence=0.9,
        chrome="ruled",
    )
    assert spec["chrome"] == "ruled"
    assert "细线" in spec["chrome_label"]
