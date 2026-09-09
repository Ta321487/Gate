"""能力已开则用户菜单须挂齐；gallery 扫「简介、图片」。"""

from __future__ import annotations

from app.bake.features.ux_scan import scan_gallery
from app.bake.schema.menu_utils import sync_user_menus_from_caps


def test_sync_user_menus_from_caps_shop():
    schema = {
        "capabilities": ["archive", "order_lines", "dm", "favorites", "order_review", "guestbook"],
        "menus": {
            "user": [
                {"key": "archive", "label": "浏览"},
                {"key": "cart", "label": "购物车"},
                {"key": "my_orders", "label": "订单"},
                {"key": "profile", "label": "个人中心"},
            ],
            "admin": [{"key": "orders", "label": "订单管理"}],
        },
        "labels": {"dmPageTitle": "客服", "orderReviewPageTitle": "我的评价"},
    }
    sync_user_menus_from_caps(schema)
    keys = [m["key"] for m in schema["menus"]["user"]]
    assert "favorites" in keys
    assert "dm" in keys
    assert "order_reviews" in keys
    assert "guestbook" in keys
    assert "order_reviews" in [m["key"] for m in schema["menus"]["admin"]]


def test_gallery_scan_opening_product_images():
    text = "查看农产品详情（产地、采摘时间、商品规格、价格、简介、图片）"
    assert scan_gallery(text)


def test_clean_typeface_css_is_sans():
    from pathlib import Path

    css = (
        Path(__file__).resolve().parents[2]
        / "skeletons"
        / "baseline"
        / "frontend"
        / "src"
        / "styles"
        / "type.css"
    ).read_text(encoding="utf-8")
    # clean 块在 serif 块之前；取 clean 段
    chunk = css.split('html[data-typeface="serif"]', 1)[0]
    assert "Noto Serif SC" not in chunk
    assert "Plus Jakarta Sans" in chunk
    assert "--el-font-family" in css
