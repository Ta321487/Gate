# -*- coding: utf-8 -*-
"""非单据策略：AppPolicy 骨架↔渲染器一致；binder 无 sunk yml 占位。"""

from __future__ import annotations

from pathlib import Path

from app.bake.engine_bake import _patch_thesis_yml
from app.bake.runtime_policy import KEEP_YML_KEYS, SINK_YML_KEYS, collect, render


def test_skeleton_app_policy_matches_renderer():
    """三棵树骨架的 AppPolicy 必须与渲染器默认版逐字一致（防止手改漂移）。"""
    from app.bake.runtime_policy import POLICY_REL, render as render_app

    repo = Path(__file__).resolve().parents[2]
    expected = render_app({})
    for tag, tree in (
        ("baseline", "skeletons/baseline"),
        ("mybatis", "skeletons/overlays/persistence-mybatis"),
        ("jpa", "skeletons/overlays/persistence-jpa"),
    ):
        text = (repo / tree / POLICY_REL).read_text(encoding="utf-8")
        assert text == expected, f"{tag} 骨架 AppPolicy 与渲染器不一致"


def test_binder_reads_app_policy_not_yml():
    """binder 不再持有已下沉的 thesis.* 占位，改读 AppPolicy 常量。"""
    repo = Path(__file__).resolve().parents[2]
    rel = "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java"
    for tag, tree in (
        ("baseline", "skeletons/baseline"),
        ("mybatis", "skeletons/overlays/persistence-mybatis"),
        ("jpa", "skeletons/overlays/persistence-jpa"),
    ):
        text = (repo / tree / rel).read_text(encoding="utf-8")
        for key in SINK_YML_KEYS:
            assert f"thesis.{key}" not in text, f"{tag} still has thesis.{key}"
        assert "AppPolicy." in text, tag
        # 与 TicketPolicy 分工：单据键不得出现在 AppPolicy 引用侧误吞
        assert "TicketPolicy." in text, tag


def test_thesis_yml_no_longer_emits_sunk_keys():
    """下沉键不得再出现在 application.yml thesis 段。"""
    from app.bake.catalog import DOMAINS
    from app.bake.domains import DOMAIN_CAPABILITIES

    text = "thesis:\n  title: demo\n"
    for dom in (
        "DOM-LIBRARY",
        "DOM-SHOP",
        "DOM-EXAM",
        "DOM-CINEMA",
        "DOM-GRADE",
        "DOM-HOSPITAL",
        "DOM-PARKING",
        "DOM-MEETING",
        "DOM-SALON",
        "DOM-HOTEL",
    ):
        out = _patch_thesis_yml(
            text,
            dom,
            {
                "title": "demo",
                "capabilities": list(DOMAIN_CAPABILITIES.get(dom) or []),
                "runtime": dict((DOMAINS.get(dom) or {}).get("runtime") or {}),
                "schema": {},
            },
        )
        for key in SINK_YML_KEYS:
            assert f"{key}:" not in out, f"{dom} yml still has {key}"
        assert "title:" in out
        assert "register-role:" in out
        assert "password-hash:" in out
        assert "allow-appoint-from-users:" in out


def test_library_archive_tables_land_in_app_policy():
    spec = {
        "capabilities": ["archive", "ticket_flow", "quota"],
        "runtime": {
            "archive_category_table": "category",
            "archive_item_table": "book",
        },
        "schema": {"entities": {"archive": {}}},
    }
    policy = collect("DOM-LIBRARY", spec)
    assert policy["ARCHIVE_CATEGORY_TABLE"] == "category"
    assert policy["ARCHIVE_ITEM_TABLE"] == "book"
    java = render(policy)
    assert 'ARCHIVE_CATEGORY_TABLE = "category"' in java
    assert "class AppPolicy" in java


def test_marketplace_dm_forces_dm_shop_cs_even_without_flag():
    """多店 + dm：即使 schema 漏落 dmShopCs，AppPolicy 也须收窄店铺客服。"""
    policy = collect(
        "DOM-SHOP",
        {
            "capabilities": ["archive", "order_lines", "dm"],
            "runtime": {
                "archive_category_table": "category",
                "archive_item_table": "product",
            },
            "schema": {"shopMarketplace": True, "entities": {"archive": {}}},
        },
    )
    assert policy.get("DM_SHOP_CS") is True
    assert policy.get("SHOP_MARKETPLACE") is True
