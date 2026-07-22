"""质感 / 配色 / 门户壳 / 字体：种子挑选与规范化。"""

from app.bake.themes import (
    CHROME_STYLES,
    LAYOUT_SHELLS,
    TYPE_PAIRINGS,
    normalize_chrome,
    normalize_layout,
    normalize_typeface,
    pick_chrome,
    pick_layout,
    pick_theme,
    pick_typeface,
    resolve_or_pick,
    resolve_style_override,
)


def test_chrome_styles_include_dense_ruled():
    ids = {t["id"] for t in CHROME_STYLES}
    assert {"soft", "sharp", "pill", "outline", "dense", "ruled"} <= ids


def test_layout_shells():
    ids = {t["id"] for t in LAYOUT_SHELLS}
    assert {"topbar", "rail", "masthead", "island"} <= ids
    assert normalize_layout("rail") == "rail"
    assert normalize_layout("nope") == "topbar"


def test_type_pairings():
    ids = {t["id"] for t in TYPE_PAIRINGS}
    assert {"clean", "serif", "tech", "soft"} <= ids
    assert normalize_typeface("tech") == "tech"
    assert normalize_typeface("nope") == "clean"


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


def test_pick_layout_stable_and_varied():
    a = pick_layout("鲜花销售|DOM-SHOP|layout")
    b = pick_layout("鲜花销售|DOM-SHOP|layout")
    assert a == b
    seen = {pick_layout(f"t{i}|DOM-X|layout") for i in range(48)}
    assert len(seen) >= 3


def test_pick_typeface_stable_and_varied():
    a = pick_typeface("图书馆|DOM-LIBRARY|type")
    b = pick_typeface("图书馆|DOM-LIBRARY|type")
    assert a == b
    seen = {pick_typeface(f"t{i}|DOM-X|type") for i in range(48)}
    assert len(seen) >= 3


def test_pick_theme_stable_and_varied():
    a = pick_theme("DOM-LIBRARY", "图书系统|DOM-LIBRARY|theme")
    b = pick_theme("DOM-LIBRARY", "图书系统|DOM-LIBRARY|theme")
    assert a == b
    seen = {pick_theme("DOM-LIBRARY", f"t{i}|DOM-LIBRARY|theme") for i in range(48)}
    assert len(seen) >= 3


def test_resolve_style_override_shared():
    assert (
        resolve_style_override(
            reset=True,
            body_value="rail",
            prev_value="island",
            catalog=LAYOUT_SHELLS,
            default="topbar",
            unknown_message="未知门户布局",
        )
        is None
    )
    assert (
        resolve_style_override(
            reset=False,
            body_value="serif",
            prev_value="clean",
            catalog=TYPE_PAIRINGS,
            default="clean",
            unknown_message="未知字体配对",
        )
        == "serif"
    )


def test_build_spec_visual_overrides():
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
        layout="rail",
        typeface="serif",
    )
    assert spec["chrome"] == "ruled"
    assert spec["layout"] == "rail"
    assert spec["typeface"] == "serif"
    assert "书香" in spec["typeface_label"]
    assert resolve_or_pick(TYPE_PAIRINGS, None, "x|type", "clean") in {
        t["id"] for t in TYPE_PAIRINGS
    }
