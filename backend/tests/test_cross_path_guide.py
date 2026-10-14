"""GENERIC / Path B 交叉导引（非 thicken）。"""

from __future__ import annotations


def test_apply_cross_guide_tags_menus_and_portal_lead():
    from app.bake.archetype_shells import build_generic_shell_schema

    schema = build_generic_shell_schema(
        "校园借阅与二手综合平台",
        archetypes=["ARCH-FLOW", "ARCH-TRADE"],
    )
    labels = schema.get("labels") or {}
    assert "交叉壳" in str(labels.get("portalHomeLead") or "")
    assert labels.get("industrySkinHint")

    user = {m["key"]: m for m in (schema.get("menus") or {}).get("user") or []}
    assert user.get("my_tickets", {}).get("navSection") == "申请办理"
    assert user.get("cart", {}).get("navSection") == "购物下单"


def test_single_path_generic_no_cross_guide():
    from app.bake.archetype_shells import build_generic_shell_schema

    schema = build_generic_shell_schema(
        "物资台账",
        archetypes=["ARCH-CRUD"],
    )
    labels = schema.get("labels") or {}
    assert "交叉壳" not in str(labels.get("portalHomeLead") or "")
    user = (schema.get("menus") or {}).get("user") or []
    assert all(not m.get("navSection") for m in user if isinstance(m, dict))


def test_readme_bits_only_for_generic_multi():
    from app.bake.cross_path_guide import readme_bits_from_spec

    empty = readme_bits_from_spec({"domain": "DOM-LIBRARY", "archetypes": ["ARCH-FLOW", "ARCH-TRADE"]})
    assert empty == ""
    text = readme_bits_from_spec(
        {
            "domain": "DOM-GENERIC",
            "archetype": "ARCH-FLOW",
            "archetypes": ["ARCH-FLOW", "ARCH-RESERVE"],
        }
    )
    assert "交叉主路径答辩导引" in text
    assert "DOM-GENERIC" in text
    assert "浅文案" in text or "浅文案替换" in text
