"""质感 / 配色 / 门户壳 / 字体：种子挑选与规范化。"""

from app.bake.themes import (
    CHROME_STYLES,
    LAYOUT_SHELLS,
    TYPE_PAIRINGS,
    is_dark_theme,
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


def test_is_dark_theme_covers_cinema_and_night():
    assert is_dark_theme("media-cinema")
    assert is_dark_theme("media-night")
    assert is_dark_theme("music-vinyl")
    assert is_dark_theme("lib-night")
    assert is_dark_theme("theme-night")
    assert is_dark_theme("dating-night")
    assert not is_dark_theme("media-amber")
    assert not is_dark_theme("lib-ink")
    assert not is_dark_theme(None)
    assert not is_dark_theme("")


def test_all_catalog_themes_declare_scheme_mix_and_colors():
    """每个目录主题（含浅色）必须自带 scheme/mix/bg/ink，避免层叠残缺。"""
    from pathlib import Path
    import re

    from app.bake.domains import DOMAINS

    root = Path(__file__).resolve().parents[2] / "skeletons/baseline/frontend/src/styles"
    css = (root / "themes.css").read_text(encoding="utf-8")
    for p in sorted((root / "themes").glob("*.css")):
        css += "\n" + p.read_text(encoding="utf-8")

    rule_pat = re.compile(
        r"((?:\[[^\]]+\]\s*,\s*)*\[[^\]]+\])\s*\{([^}]+)\}",
        re.DOTALL,
    )
    missing = []
    for domain, meta in sorted(DOMAINS.items()):
        for t in meta.get("themes") or []:
            tid = t["id"]
            needle = f'[data-theme="{tid}"]'
            ok = False
            for sel, body in rule_pat.findall(css):
                if needle not in sel:
                    continue
                if (
                    "--portal-bg:" in body
                    and "--portal-ink:" in body
                    and "--portal-mix:" in body
                    and "--portal-scheme:" in body
                ):
                    ok = True
                    break
            if not ok:
                missing.append(f"{domain}:{tid}")
    assert not missing, "themes missing full tokens: " + ", ".join(missing)


def test_root_must_not_override_imported_theme_colors():
    """:root 若写 bg/ink，会盖掉 @import 的行业皮，再叠 night 的 mix=#000 → 留言黑块。"""
    from pathlib import Path
    import re

    path = (
        Path(__file__).resolve().parents[2]
        / "skeletons/baseline/frontend/src/styles/themes.css"
    )
    css = path.read_text(encoding="utf-8")
    # 只检查顶层 :root { ... }，不含 [data-theme=…] 合并选择器
    roots = re.findall(r"(?m)^:root\s*\{([^}]+)\}", css)
    assert roots, "expected a standalone :root block"
    for body in roots:
        assert "--portal-bg:" not in body
        assert "--portal-ink:" not in body
        assert "--portal-surface:" not in body


def test_dark_theme_accent_usable_as_primary_button():
    """深色皮 accent 过浅时，主按钮/editorial 要点会洗成惨白块。"""
    from pathlib import Path
    import re

    from app.bake.domains import DOMAINS

    root = Path(__file__).resolve().parents[2] / "skeletons/baseline/frontend/src/styles"
    css = (root / "themes.css").read_text(encoding="utf-8")
    for p in sorted((root / "themes").glob("*.css")):
        css += "\n" + p.read_text(encoding="utf-8")

    def lum(h: str) -> float:
        h = h.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255

    rule_pat = re.compile(
        r"((?:\[[^\]]+\]\s*,\s*)*\[[^\]]+\])\s*\{([^}]+)\}",
        re.DOTALL,
    )
    too_light = []
    for domain, meta in sorted(DOMAINS.items()):
        for t in meta.get("themes") or []:
            tid = t["id"]
            if not is_dark_theme(tid):
                continue
            needle = f'[data-theme="{tid}"]'
            for sel, body in rule_pat.findall(css):
                if needle not in sel or "--portal-bg:" not in body:
                    continue
                m = re.search(r"--portal-accent:\s*(#[0-9a-fA-F]+)", body)
                if m and lum(m.group(1)) > 0.55:
                    too_light.append(f"{domain}:{tid}={m.group(1)}")
                break
    assert not too_light, "dark accents too light for primary buttons: " + ", ".join(too_light)


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
