"""api_style：跨题传参风格抽签；bake 写死进源码。"""

from __future__ import annotations

from pathlib import Path

from app.bake.api_inventory import load_api_inventory, parse_controller_source
from app.bake.api_style import (
    apply_api_style_to_workspace,
    normalize_api_style,
    pick_api_style,
)


def test_pick_api_style_stable_and_varied():
    a = pick_api_style("校园商城|DOM-SHOP")
    b = pick_api_style("校园商城|DOM-SHOP")
    assert a == b
    assert set(a) == {"item_ref", "cart_mutate"}
    seen_item = {pick_api_style(f"t{i}|DOM-X")["item_ref"] for i in range(48)}
    seen_cart = {pick_api_style(f"t{i}|DOM-X")["cart_mutate"] for i in range(48)}
    assert seen_item == {"path", "body"}
    assert seen_cart == {"path", "body"}


def test_normalize_api_style_accepts_camel():
    s = normalize_api_style({"itemRef": "body", "cartMutate": "path"})
    assert s == {"item_ref": "body", "cart_mutate": "path"}


def test_build_spec_includes_api_style():
    from app.bake.catalog import build_spec

    spec = build_spec(
        title="图书借阅系统",
        archetype="ARCH-FLOW",
        domain="DOM-LIBRARY",
        theme="lib-ink",
        llm_enabled=False,
        match_mode="recommended",
        confidence=0.9,
    )
    assert "api_style" in spec
    assert spec["api_style"]["item_ref"] in ("path", "body")


def test_apply_writes_single_style(tmp_path):
    root = Path(__file__).resolve().parents[2]
    src = root / "skeletons" / "baseline"
    # 最小骨架：只拷可变文件
    be = tmp_path / "backend" / "src" / "main" / "java" / "com" / "thesis"
    (be / "controller").mkdir(parents=True)
    (be / "capability").mkdir(parents=True)
    fe = tmp_path / "frontend" / "src" / "utils"
    fe.mkdir(parents=True)
    for name in ("FavoriteController.java", "BrowseHistoryController.java", "OrderController.java"):
        (be / "controller" / name).write_text(
            (src / "backend/src/main/java/com/thesis/controller" / name).read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
    (fe / "apiCalls.js").write_text("// placeholder", encoding="utf-8")

    apply_api_style_to_workspace(
        tmp_path, {"item_ref": "body", "cart_mutate": "path"}
    )
    fav = (be / "controller" / "FavoriteController.java").read_text(encoding="utf-8")
    assert '@PostMapping("/toggle")' in fav
    assert "/{itemId}/toggle" not in fav
    assert "ApiStyle" not in fav
    assert not (be / "capability" / "ApiStyle.java").exists()

    calls = (fe / "apiCalls.js").read_text(encoding="utf-8")
    assert "/api/favorites/toggle" in calls
    assert "getApiStyle" not in calls
    assert "`/api/cart/${id}`" in calls or "/api/cart/${id}" in calls

    order = (be / "controller" / "OrderController.java").read_text(encoding="utf-8")
    assert 'DeleteMapping("/api/cart/{itemId}")' in order
    assert "/api/cart/remove" not in order
    assert "@@CART_MUTATE" not in order


def test_inventory_filters_inactive_variants(tmp_path):
    be = tmp_path / "backend" / "src" / "main" / "java" / "com" / "thesis" / "controller"
    be.mkdir(parents=True)
    (be / "FavoriteController.java").write_text(
        """
package com.thesis.controller;
@RestController
@RequestMapping("/api/favorites")
public class FavoriteController {
  @PostMapping("/{itemId}/toggle")
  public Object togglePath() { return null; }
  @PostMapping("/toggle")
  public Object toggleBody() { return null; }
}
""",
        encoding="utf-8",
    )
    inv = load_api_inventory(
        tmp_path,
        {"api_style": {"item_ref": "body", "cart_mutate": "body"}},
    )
    paths = {(e["method"], e["path"]) for e in inv["endpoints"]}
    assert ("POST", "/api/favorites/toggle") in paths
    assert ("POST", "/api/favorites/{itemId}/toggle") not in paths


def test_baseline_favorite_is_single_path():
    root = Path(__file__).resolve().parents[2]
    src = (
        root
        / "skeletons/baseline/backend/src/main/java/com/thesis/controller/FavoriteController.java"
    ).read_text(encoding="utf-8")
    parsed = parse_controller_source(src, rel_file="FavoriteController.java")
    paths = {e["path"] for e in parsed["endpoints"]}
    assert "/api/favorites/{itemId}/toggle" in paths
    assert "/api/favorites/toggle" not in paths
