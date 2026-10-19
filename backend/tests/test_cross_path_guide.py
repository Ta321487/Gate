"""GENERIC / Path B 交叉导引（非 thicken）。"""

from __future__ import annotations


def test_apply_cross_guide_tags_menus_and_portal_lead():
    from app.bake.archetype_shells import build_generic_shell_schema

    schema = build_generic_shell_schema(
        "校园借阅与二手综合平台",
        archetypes=["ARCH-FLOW", "ARCH-TRADE"],
    )
    labels = schema.get("labels") or {}
    lead = str(labels.get("portalHomeLead") or "")
    assert "申请审核" in lead and "购物下单" in lead
    assert "交叉壳" not in lead
    assert "答辩" not in lead
    hint = str(labels.get("industrySkinHint") or "")
    assert hint
    assert "Dom" not in hint and "通用壳" not in hint

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
    assert "业务说明" in text
    assert "申请办理" in text and "时段预约" in text
    assert "DOM-GENERIC" not in text
    assert "答辩" not in text
    assert "浅文案" not in text
