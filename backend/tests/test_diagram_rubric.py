"""论文图老师 rubric 确定性闸。"""

from __future__ import annotations

import pytest

from app.bake.schema.diagram_rubric import (
    attach_rubric_gate,
    audit_er_rubric,
    audit_sequence_rubric,
    audit_usecase_desc_rubric,
    export_blocked_reason,
    raise_if_export_blocked,
)


def test_er_part_fk_in_own_columns_blocks_export():
    model = {
        "er_mode": "part",
        "er_entity": "orders",
        "tables": [
            {
                "name": "orders",
                "own_columns": [
                    {"name": "id"},
                    {"name": "user_id", "fk": True},
                ],
                "columns": [
                    {"name": "id"},
                    {"name": "user_id", "fk": True},
                ],
            }
        ],
        "conceptual_entities": ["orders"],
    }
    findings = audit_er_rubric(model, mode="part", entity="orders")
    assert any(f["level"] == "error" and "外键" in f["msg"] for f in findings)
    gated = attach_rubric_gate(dict(model), kind="er", mode="part", entity="orders")
    assert gated["rubric_gate"]["ok"] is False
    assert export_blocked_reason(gated)
    with pytest.raises(ValueError, match="规则"):
        raise_if_export_blocked(gated)


def test_er_part_clean_own_columns_ok():
    model = {
        "er_mode": "part",
        "er_entity": "orders",
        "tables": [
            {
                "name": "orders",
                "own_columns": [{"name": "id"}, {"name": "amount"}],
                "columns": [
                    {"name": "id"},
                    {"name": "user_id", "fk": True},
                    {"name": "amount"},
                ],
            }
        ],
        "conceptual_entities": ["orders"],
    }
    gated = attach_rubric_gate(dict(model), kind="er", mode="part", entity="orders")
    assert gated["rubric_gate"]["ok"] is True
    assert export_blocked_reason(gated) is None


def test_er_total_assoc_link_not_in_conceptual():
    model = {
        "er_mode": "total",
        "tables": [
            {"name": "users"},
            {"name": "order_item", "assoc_link": True},
        ],
        "conceptual_entities": ["users", "order_item"],
    }
    findings = audit_er_rubric(model, mode="total")
    assert any("中间表" in f["msg"] for f in findings)


def test_sequence_missing_slot_blocks():
    model = {
        "diagrams": [
            {
                "index": 0,
                "participants": [
                    {"id": "actor", "label": "买家"},
                    {"id": "page", "label": "页面"},
                    {"id": "controller", "label": "控制器"},
                ],
                "messages": [
                    {"from": "actor", "to": "page", "text": "点"},
                ],
            }
        ]
    }
    gated = attach_rubric_gate(dict(model), kind="sequences")
    assert gated["rubric_gate"]["ok"] is False
    assert any("db" in f["msg"] for f in gated["rubric_gate"]["findings"])


def test_sequence_message_unknown_endpoint():
    model = {
        "diagrams": [
            {
                "index": 0,
                "participants": [
                    {"id": "actor", "label": "买家"},
                    {"id": "page", "label": "页面"},
                    {"id": "controller", "label": "控制器"},
                    {"id": "db", "label": "数据库"},
                ],
                "messages": [
                    {"from": "actor", "to": "ghost", "text": "幽灵"},
                ],
            }
        ]
    }
    findings = audit_sequence_rubric(model)
    assert any("ghost" in f["msg"] for f in findings)


def test_sequence_actor_menu_side_mismatch():
    """无 staff_posts 时：商家当执行者但 subadmin 菜单空 → 规则红。"""
    model = {
        "delivery_menus": {
            "user": [{"key": "order_reviews", "label": "评价"}],
            "admin": [{"key": "order_reviews", "label": "评价管理"}],
            "subadmin": [],
        },
        "roles": {"subadmin": {"label": "商家"}},
        "diagrams": [
            {
                "index": 2,
                "figure_title": "商家管理评价序列图",
                "menu_key": "order_reviews",
                "side": "admin",
                "actor_label": "商家",
                "participants": [
                    {"id": "actor", "label": "商家"},
                    {"id": "page", "label": "页面"},
                    {"id": "controller", "label": "控制器"},
                    {"id": "db", "label": "数据库"},
                ],
                "messages": [
                    {"from": "actor", "to": "page", "text": "打开"},
                ],
            }
        ],
    }
    findings = audit_sequence_rubric(model)
    assert any(
        f.get("level") == "error" and "商家" in f["msg"] and "subadmin" in f["msg"]
        for f in findings
    )


def test_sequence_review_orderish_messages_rule_red():
    """评价图消息订单文案占优 → 规则红（即使尾句带评价成功）。"""
    model = {
        "diagrams": [
            {
                "index": 1,
                "figure_title": "买家发表评价序列图",
                "menu_key": "order_reviews",
                "kind": "order_reviews_user",
                "side": "user",
                "actor_label": "买家",
                "participants": [
                    {"id": "actor", "label": "买家"},
                    {"id": "page", "label": "页面"},
                    {"id": "controller", "label": "控制器"},
                    {"id": "db", "label": "数据库"},
                ],
                "messages": [
                    {"from": "page", "to": "controller", "text": "分页查询订单"},
                    {"from": "page", "to": "page", "text": "选择订单"},
                    {"from": "page", "to": "controller", "text": "提交订单"},
                    {"from": "controller", "to": "db", "text": "保存订单信息"},
                    {"from": "controller", "to": "page", "text": "我的评价成功"},
                ],
            }
        ],
    }
    findings = audit_sequence_rubric(model)
    assert any("订单操作文案" in f["msg"] for f in findings if f.get("level") == "error")


def test_sequence_merchant_staff_post_not_false_red():
    """有商家岗 pack 覆盖 order_reviews 时，subadmin 空菜单不得误杀。"""
    model = {
        "delivery_menus": {
            "user": [{"key": "order_reviews", "label": "评价"}],
            "admin": [{"key": "order_reviews", "label": "评价管理"}, {"key": "orders", "label": "订单"}],
            "subadmin": [],
        },
        "roles": {
            "subadmin": {"label": "商家"},
            "staff_posts": [
                {"id": "shop_merchant", "label": "商家", "packs": ["merchant_ops"]}
            ],
        },
        "diagrams": [
            {
                "index": 2,
                "figure_title": "商家管理评价序列图",
                "menu_key": "order_reviews",
                "side": "admin",
                "actor_label": "商家",
                "participants": [
                    {"id": "actor", "label": "商家"},
                    {"id": "page", "label": "页面"},
                    {"id": "controller", "label": "控制器"},
                    {"id": "db", "label": "数据库"},
                ],
                "messages": [
                    {"from": "actor", "to": "page", "text": "打开评价"},
                ],
            }
        ],
    }
    findings = audit_sequence_rubric(model)
    assert not any(f.get("level") == "error" for f in findings)


def test_usecase_desc_missing_table_suffix():
    model = {
        "count": 1,
        "requested_count": 1,
        "candidate_count": 1,
        "cases": [
            {
                "name": "登录",
                "menu_key": "login",
                "flow": ["打开", "提交"],
            }
        ],
        "markdown": "## 系统\n\n| 项目 | 内容 |\n",
    }
    findings = audit_usecase_desc_rubric(model)
    assert any("用例描述表" in f["msg"] for f in findings)


def test_usecase_desc_ok_with_suffix_and_flow():
    model = {
        "count": 1,
        "requested_count": 1,
        "candidate_count": 1,
        "cases": [
            {
                "name": "登录",
                "menu_key": "login",
                "flow": ["打开登录页", "提交"],
            }
        ],
        "markdown": "（1）登录功能……见表 3.1 所示。\n\n表 3.1 “登录”的用例描述表\n",
    }
    gated = attach_rubric_gate(dict(model), kind="usecase_desc")
    assert gated["rubric_gate"]["ok"] is True


def test_usecase_desc_menu_mismatch_lists_all_with_fix():
    """交付菜单不一致一次列全，并带操作路径。"""
    model = {
        "count": 2,
        "requested_count": 2,
        "candidate_count": 2,
        "delivery_menus": {
            "user": [{"key": "cart", "label": "购物车"}],
            "admin": [{"key": "orders", "label": "订单"}],
            "subadmin": [],
        },
        "roles": {"subadmin": {"label": "商家"}},
        "cases": [
            {
                "name": "买家登录",
                "actor": "买家",
                "menu_key": "auth",
                "side": "user",
                "source": "auth",
                "kind": "auth_login",
                "flow": ["打开登录", "提交"],
            },
            {
                "name": "商家处理订单",
                "actor": "商家",
                "menu_key": "orders",
                "side": "admin",
                "source": "menu",
                "flow": ["进入订单", "处理"],
            },
            {
                "name": "买家退款",
                "actor": "买家",
                "menu_key": "refund",
                "side": "user",
                "source": "menu",
                "flow": ["申请退款"],
            },
        ],
        "markdown": (
            "（1）登录……见表\n表 1 “买家登录”的用例描述表\n"
            "（2）订单……见表\n表 2 “商家处理订单”的用例描述表\n"
            "（3）退款……见表\n表 3 “买家退款”的用例描述表\n"
        ),
    }
    findings = audit_usecase_desc_rubric(model)
    msgs = [f["msg"] for f in findings]
    # auth 不算「不在菜单」
    assert not any("auth" in m and "未包含" in m for m in msgs)
    assert not any("auth" in m and "没有的操作" in m for m in msgs)
    # 商家 vs subadmin 空菜单
    assert any("商家" in m and "orders" in m for m in msgs)
    # refund 不在 user 菜单
    assert any("refund" in m for m in msgs)
    # 一次收齐 + 可跳转
    bad = [f for f in findings if f.get("level") == "error"]
    assert len(bad) >= 2
    assert all(f.get("goto") == "usecase_desc" for f in bad)
    assert all("用例描述表" in (f.get("fix") or "") for f in bad)


def test_label_gate_also_blocks_export():
    model = {"label_gate": {"ok": False, "note": "模块图叶子文案检查红 2 处"}}
    assert "文案" in (export_blocked_reason(model) or "")
