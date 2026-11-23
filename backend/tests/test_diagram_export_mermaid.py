"""论文图 Mermaid 同源导出：结构 ⊆ model，属性图不含 FK。"""

from __future__ import annotations

from app.bake.schema.diagram_mermaid import (
    activity_diagram_to_mermaid,
    architecture_model_to_mermaid,
    class_model_to_mermaid,
    er_model_to_mermaid,
    expected_er_part_has_no_fk_names,
    module_model_to_mermaid,
    sequence_diagram_to_mermaid,
    usecase_model_to_mermaid,
)


def test_sequence_mermaid_four_slots_and_messages():
    diagram = {
        "figure_title": "下单序列图",
        "participants": [
            {"id": "actor", "label": "买家"},
            {"id": "page", "label": "页面"},
            {"id": "controller", "label": "控制器"},
            {"id": "db", "label": "数据库"},
        ],
        "messages": [
            {"from": "actor", "to": "page", "dir": "request", "text": "提交订单()"},
            {"from": "page", "to": "controller", "dir": "request", "text": "create()"},
            {"from": "controller", "to": "db", "dir": "request", "text": "insert()"},
            {"from": "db", "to": "controller", "dir": "response", "text": "ok"},
            {"from": "controller", "to": "page", "dir": "response", "text": "成功"},
            {"from": "page", "to": "actor", "dir": "response", "text": "展示结果"},
        ],
    }
    text = sequence_diagram_to_mermaid(diagram)
    assert text.startswith("%%")
    assert "sequenceDiagram" in text
    assert "participant actor as 买家" in text
    assert "actor->>page: 提交订单()" in text
    assert "db-->>controller: ok" in text
    assert "幽灵操作" not in text


def test_activity_mermaid_decision_guards():
    diagram = {
        "figure_title": "登录活动图",
        "nodes": [
            {"id": "n1", "kind": "start"},
            {"id": "n2", "kind": "action", "text": "输入账号"},
            {"id": "n3", "kind": "decision", "decision_of": "用户是否存在"},
            {"id": "n4", "kind": "end"},
        ],
        "edges": [
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n3"},
            {"from": "n3", "to": "n2", "guard": "否"},
            {"from": "n3", "to": "n4", "guard": "是"},
        ],
    }
    text = activity_diagram_to_mermaid(diagram)
    assert "flowchart TD" in text
    assert "输入账号" in text
    assert "用户是否存在" in text
    assert "|否|" in text
    assert "|是|" in text


def test_class_mermaid_relations():
    model = {
        "title": "类图",
        "classes": [
            {"id": "users", "name": "User", "attributes": [{"display": "+ id"}], "methods": []},
            {"id": "orders", "name": "Order", "attributes": [], "methods": []},
        ],
        "associations": [
            {"from": "orders", "to": "users", "kind": "association", "label": "归属"},
        ],
    }
    text = class_model_to_mermaid(model)
    assert "classDiagram" in text
    assert "C_users" in text
    assert "C_orders" in text
    assert "归属" in text


def test_er_part_mermaid_excludes_fk():
    model = {
        "er_entity": "orders",
        "tables": [
            {
                "name": "orders",
                "label": "订单",
                "own_columns": [
                    {"name": "id", "label": "编号"},
                    {"name": "amount", "label": "金额"},
                ],
                "columns": [
                    {"name": "id", "label": "编号"},
                    {"name": "user_id", "label": "用户编号", "fk": True},
                    {"name": "amount", "label": "金额"},
                ],
            }
        ],
    }
    text = er_model_to_mermaid(model, mode="part", entity="orders")
    assert "erDiagram" in text
    assert "金额" in text
    expected_er_part_has_no_fk_names(text, model["tables"][0])


def test_usecase_mermaid_skips_hidden():
    model = {
        "actor": {"id": "user", "label": "买家"},
        "level1": [
            {
                "id": "user_uc1",
                "label": "登录注册",
                "includes": [
                    {"id": "user_uc1:login", "label": "登录", "relation": "include"},
                    {
                        "id": "user_uc1:ghost",
                        "label": "幽灵",
                        "relation": "include",
                        "hidden": True,
                    },
                ],
            }
        ],
    }
    text = usecase_model_to_mermaid(model)
    assert "登录" in text
    assert "幽灵" not in text


def test_usecase_mermaid_extend_arrow_points_to_base():
    from app.bake.schema.diagram_mermaid import mermaid_id

    model = {
        "actor": {"id": "user", "label": "买家"},
        "level1": [
            {
                "id": "user_uc_order",
                "label": "查看订单",
                "includes": [
                    {
                        "id": "user_uc_order:list",
                        "label": "浏览订单列表",
                        "relation": "include",
                    },
                    {
                        "id": "user_uc_order:pay",
                        "label": "进行支付",
                        "relation": "extend",
                    },
                ],
            }
        ],
    }
    text = usecase_model_to_mermaid(model)
    umid = mermaid_id("user_uc_order", prefix="U_")
    pay = mermaid_id("user_uc_order:pay", prefix="U_")
    lst = mermaid_id("user_uc_order:list", prefix="U_")
    assert f"{pay} -.->|<<extend>>| {umid}" in text
    assert f"{umid} -.->|<<include>>| {lst}" in text
    assert f"{umid} -.->|<<extend>>| {pay}" not in text


def test_module_mermaid_tree():
    model = {
        "title": "模块",
        "root": {
            "id": "root",
            "label": "系统",
            "depth": 0,
            "children": [
                {
                    "id": "user",
                    "label": "买家",
                    "depth": 1,
                    "children": [
                        {
                            "id": "user_orders",
                            "label": "我的订单",
                            "depth": 2,
                            "children": [],
                        }
                    ],
                }
            ],
        },
    }
    text = module_model_to_mermaid(model)
    assert "flowchart TB" in text
    assert "我的订单" in text
    assert "M_user_orders" in text


def test_architecture_mermaid_roles_and_layers():
    model = {
        "figure_title": "系统逻辑架构图",
        "roles": [{"id": "user", "label": "买家"}],
    }
    text = architecture_model_to_mermaid(model)
    assert "flowchart TB" in text
    assert "买家" in text
    assert "SpringBoot" in text
    assert "MySQL" in text
