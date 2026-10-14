"""能力已开则表面须挂齐；硬拦 cap 则收集旗标必真；gallery 扫「简介、图片」。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.bake.domain_schema import sync_cap_surfaces
from app.bake.features.dm import sync_dm_surface_from_caps
from app.bake.features.lostfound import sync_lostfound_surface_from_caps
from app.bake.features.ticket_flow_opts import sync_material_check_surface_from_caps
from app.bake.features.ux_scan import scan_gallery
from app.bake.schema.hard_assert_ui import (
    HARD_ASSERT_UI_FROM_CAPS,
    assert_hard_assert_ui_aligned,
    check_hard_assert_ui_aligned,
    sync_hard_assert_ui_from_caps,
)
from app.bake.schema.menu_utils import sync_user_menus_from_caps


def test_sync_user_menus_from_caps_generic():
    schema = {
        "capabilities": ["archive", "order_lines", "favorites", "order_review", "guestbook"],
        "menus": {
            "user": [
                {"key": "archive", "label": "浏览"},
                {"key": "cart", "label": "购物车"},
                {"key": "my_orders", "label": "订单"},
                {"key": "profile", "label": "个人中心"},
            ],
            "admin": [{"key": "orders", "label": "订单管理"}],
        },
        "labels": {"orderReviewPageTitle": "我的评价"},
    }
    sync_user_menus_from_caps(schema)
    keys = [m["key"] for m in schema["menus"]["user"]]
    assert "favorites" in keys
    assert "order_reviews" in keys
    assert "guestbook" in keys
    assert "dm" not in keys  # dm 不归通用菜单收束
    admin_keys = [m["key"] for m in schema["menus"]["admin"]]
    assert "order_reviews" in admin_keys


def test_sync_dm_surface_from_caps_shop():
    schema = {
        "capabilities": ["dm"],
        "shopMarketplace": True,
        "menus": {
            "user": [
                {"key": "archive", "label": "浏览"},
                {"key": "cart", "label": "购物车"},
                {"key": "profile", "label": "个人中心"},
            ],
            "admin": [{"key": "orders", "label": "订单管理"}],
        },
        "labels": {},
    }
    sync_dm_surface_from_caps(schema)
    assert schema.get("dmShopCs") is True
    keys = [m["key"] for m in schema["menus"]["user"]]
    assert "dm" in keys
    admin_keys = [m["key"] for m in schema["menus"]["admin"]]
    assert "dm" in admin_keys
    dm_admin = next(m for m in schema["menus"]["admin"] if m["key"] == "dm")
    assert dm_admin.get("superOnly") is False
    assert dm_admin.get("label") == "客服"
    assert schema["labels"].get("dmNewTitle") == "联系商家客服"


def test_sync_dm_surface_preserves_existing_labels():
    schema = {
        "capabilities": ["dm"],
        "menus": {"user": [], "admin": []},
        "labels": {"dmNewTitle": "联系红娘"},
    }
    sync_dm_surface_from_caps(schema)
    assert schema["labels"]["dmNewTitle"] == "联系红娘"
    assert schema["labels"].get("dmPageLead")  # 缺省仍补


def test_sync_hard_assert_ui_from_caps_flags_only():
    """合同收束只钉旗标路径，不碰材料/失物菜单实体。"""
    schema = {
        "capabilities": ["material_check", "claim_proof", "ticket"],
        "entities": {"ticket": {}},
        "menus": {"admin": [{"key": "content", "label": "内容"}], "user": []},
        "labels": {},
    }
    sync_hard_assert_ui_from_caps(schema)
    ticket = schema["entities"]["ticket"]
    assert ticket.get("requireMaterialChecklist") is True
    assert ticket.get("requireAttach") is True
    assert ticket.get("requireClaimProof") is True
    admin_keys = [m["key"] for m in schema["menus"]["admin"]]
    assert "material_checklist" not in admin_keys
    assert "material_check" not in schema["entities"]
    assert "lost_claim_proof" not in schema["entities"]


def test_sync_hard_assert_ui_accepts_non_ticket_path(monkeypatch):
    """合同路径不绑死 ticket，可落 reservation 等实体。"""
    from app.bake.schema import hard_assert_ui as mod

    monkeypatch.setitem(
        mod.HARD_ASSERT_UI_FROM_CAPS,
        "_probe_cap",
        ("entities.reservation.requireRemark",),
    )
    schema = {
        "capabilities": ["_probe_cap"],
        "entities": {"reservation": {}},
    }
    sync_hard_assert_ui_from_caps(schema)
    assert schema["entities"]["reservation"].get("requireRemark") is True
    assert check_hard_assert_ui_aligned(schema) == []


def test_check_hard_assert_ui_aligned_flags_missing():
    schema = {
        "capabilities": ["material_check"],
        "entities": {"ticket": {}},
    }
    issues = check_hard_assert_ui_aligned(schema)
    assert issues
    assert "material_check" in issues[0]
    assert "requireMaterialChecklist" in issues[0]


def test_assert_hard_assert_ui_aligned_raises():
    schema = {
        "capabilities": ["claim_proof"],
        "entities": {"ticket": {"requireClaimProof": False}},
    }
    with pytest.raises(ValueError, match="硬拦与收集 UI 未对齐"):
        assert_hard_assert_ui_aligned(schema, domain="DOM-LOST")


def test_assert_hard_assert_ui_aligned_ok_after_sync():
    schema = {
        "capabilities": ["material_check", "claim_proof"],
        "entities": {"ticket": {}},
    }
    sync_hard_assert_ui_from_caps(schema)
    assert check_hard_assert_ui_aligned(schema) == []
    assert_hard_assert_ui_aligned(schema)


def test_hard_assert_contract_covers_runtime_policy_caps():
    """runtime_policy 里按 cap 打开的硬拦开关，必须登记在合同表。"""
    text = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "bake"
        / "runtime_policy.py"
    ).read_text(encoding="utf-8")
    expected = {
        "material_check": "MATERIAL_CHECK_ENABLED",
        "claim_proof": "CLAIM_PROOF_ENABLED",
    }
    for cap, const in expected.items():
        assert f'"{cap}" in caps' in text or f"'{cap}' in caps" in text
        assert const in text
        assert cap in HARD_ASSERT_UI_FROM_CAPS, (
            f"{cap} 在 runtime_policy 开硬拦却未进 HARD_ASSERT_UI_FROM_CAPS"
        )


def test_feature_surfaces_own_attach():
    schema = {
        "capabilities": ["material_check", "claim_proof"],
        "entities": {"ticket": {}},
        "menus": {"admin": [{"key": "content", "label": "内容"}], "user": []},
        "labels": {},
    }
    sync_material_check_surface_from_caps(schema)
    sync_lostfound_surface_from_caps(schema)
    assert "material_checklist" in [m["key"] for m in schema["menus"]["admin"]]
    assert "material_check" in schema["entities"]
    assert "lost_claim_proof" in schema["entities"]


def test_sync_cap_surfaces_orchestrates():
    schema = {
        "capabilities": [
            "favorites",
            "dm",
            "material_check",
            "claim_proof",
            "order_review",
        ],
        "shopMarketplace": True,
        "entities": {"ticket": {}},
        "menus": {
            "user": [
                {"key": "cart", "label": "购物车"},
                {"key": "my_orders", "label": "订单"},
            ],
            "admin": [{"key": "orders", "label": "订单"}, {"key": "content", "label": "内容"}],
        },
        "labels": {},
    }
    sync_cap_surfaces(schema)
    user_keys = [m["key"] for m in schema["menus"]["user"]]
    admin_keys = [m["key"] for m in schema["menus"]["admin"]]
    assert "favorites" in user_keys
    assert "dm" in user_keys
    assert "order_reviews" in user_keys
    assert "material_checklist" in admin_keys
    assert schema["entities"]["ticket"].get("requireMaterialChecklist") is True
    assert schema["entities"]["ticket"].get("requireClaimProof") is True
    assert schema.get("dmShopCs") is True


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
