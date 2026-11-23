"""论文图 Draw.io 同源导出：结构 ⊆ model，属性图不含 FK。"""

from __future__ import annotations

import pytest

from app.bake.schema.diagram_drawio import (
    architecture_model_to_drawio,
    class_model_to_drawio,
    er_model_to_drawio,
    er_parts_bundle_to_drawio,
    expected_architecture_vertex_ids,
    expected_class_vertex_ids,
    expected_er_vertex_ids,
    expected_usecase_vertex_ids,
    module_model_to_drawio,
    usecase_model_to_drawio,
)
from app.bake.schema.diagram_export import (
    DRAWIO_M1_KINDS,
    EXPORT_KINDS,
    assert_drawio_ids_subset,
    er_own_column_names,
    parse_drawio_vertex_ids,
    stable_cell_id,
)


def test_export_kind_contract():
    assert "er" in EXPORT_KINDS
    assert set(DRAWIO_M1_KINDS) <= set(EXPORT_KINDS)


def test_er_total_drawio_homology_skips_assoc_link():
    model = {
        "title": "测试E-R",
        "tables": [
            {"name": "users", "label": "用户"},
            {"name": "orders", "label": "订单"},
            {"name": "order_item", "label": "订单项", "assoc_link": True},
        ],
        "relations": [
            {
                "name": "place",
                "left": "users",
                "right": "orders",
                "label": "下单",
                "card_left": "1",
                "card_right": "N",
            }
        ],
    }
    xml = er_model_to_drawio(model, mode="total")
    assert "mxfile" in xml
    assert "diagrams.net" in xml or 'host="app.diagrams.net"' in xml
    assert_drawio_ids_subset(
        xml, expected_vertex_ids=expected_er_vertex_ids(model, mode="total")
    )
    verts = parse_drawio_vertex_ids(xml)
    assert stable_cell_id("er", "order_item") not in verts
    assert stable_cell_id("er", "users") in verts
    assert "下单" in xml


def test_er_part_drawio_excludes_fk_column_names():
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
    assert er_own_column_names(model["tables"][0]) == ["id", "amount"]
    xml = er_model_to_drawio(model, mode="part", entity="orders")
    assert_drawio_ids_subset(
        xml,
        expected_vertex_ids=expected_er_vertex_ids(
            model, mode="part", entity="orders"
        ),
    )
    assert "user_id" not in xml
    assert "用户编号" not in xml
    assert "金额" in xml
    # 陈氏：实体单框 + 属性椭圆，禁止「表名&#xa;属性」糊成一格
    assert "ellipse;" in xml
    assert xml.count("ellipse;") >= 2
    assert "订单&#xa;" not in xml
    assert stable_cell_id("era", "orders.id") in parse_drawio_vertex_ids(xml)
    assert stable_cell_id("era", "orders.amount") in parse_drawio_vertex_ids(xml)


def test_er_parts_bundle_drawio_multipage():
    users = {
        "er_entity": "users",
        "tables": [
            {
                "name": "users",
                "label": "用户",
                "own_columns": [
                    {"name": "id", "label": "编号"},
                    {"name": "username", "label": "用户名"},
                ],
                "columns": [
                    {"name": "id", "label": "编号"},
                    {"name": "username", "label": "用户名"},
                ],
            }
        ],
    }
    orders = {
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
    xml = er_parts_bundle_to_drawio([users, orders])
    assert xml.count("<diagram ") == 2
    assert "用户-实体属性" in xml
    assert "订单-实体属性" in xml
    assert "金额" in xml
    assert "user_id" not in xml
    assert xml.count("</mxfile>") == 1


def test_class_drawio_homology():
    model = {
        "title": "类图",
        "classes": [
            {
                "id": "users",
                "name": "User",
                "attributes": [{"name": "id", "display": "+ id: Long"}],
                "methods": [{"name": "save", "display": "+ save()"}],
            },
            {
                "id": "orders",
                "name": "Order",
                "attributes": [],
                "methods": [],
            },
        ],
        "associations": [
            {
                "from": "orders",
                "to": "users",
                "kind": "association",
                "label": "归属",
            }
        ],
    }
    xml = class_model_to_drawio(model)
    assert_drawio_ids_subset(
        xml, expected_vertex_ids=expected_class_vertex_ids(model)
    )
    assert "User" in xml
    assert stable_cell_id("cls", "orders") in parse_drawio_vertex_ids(xml)


def test_module_drawio_homology():
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
                        {"id": "user_orders", "label": "我的订单", "depth": 2, "children": []}
                    ],
                }
            ],
        },
    }
    xml = module_model_to_drawio(model)
    verts = parse_drawio_vertex_ids(xml)
    assert stable_cell_id("mod", "root") in verts
    assert stable_cell_id("mod", "user_orders") in verts
    assert "我的订单" in xml


def test_usecase_drawio_skips_hidden_includes():
    model = {
        "title": "用例",
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
    xml = usecase_model_to_drawio(model)
    assert_drawio_ids_subset(
        xml, expected_vertex_ids=expected_usecase_vertex_ids(model)
    )
    verts = parse_drawio_vertex_ids(xml)
    assert stable_cell_id("ucu", "user_uc1:ghost") not in verts
    assert "幽灵" not in xml
    assert "登录" in xml


def test_usecase_drawio_extend_arrow_points_to_base():
    """UML：<<extend>> 须从扩展用例指向基用例，禁止一级→支付这种反画。"""
    model = {
        "title": "用例",
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
    xml = usecase_model_to_drawio(model)
    l1 = stable_cell_id("ucu", "user_uc_order")
    pay = stable_cell_id("ucu", "user_uc_order:pay")
    lst = stable_cell_id("ucu", "user_uc_order:list")
    assert "<<extend>>" in xml or "&lt;&lt;extend&gt;&gt;" in xml
    assert "<<include>>" in xml or "&lt;&lt;include&gt;&gt;" in xml
    # extend：支付 → 查看订单
    assert f'source="{pay}"' in xml and f'target="{l1}"' in xml
    assert f'source="{l1}" target="{pay}"' not in xml
    # include：查看订单 → 列表
    assert f'source="{l1}"' in xml and f'target="{lst}"' in xml


def test_architecture_drawio_homology():
    model = {
        "figure_title": "系统逻辑架构图",
        "roles": [
            {"id": "user", "label": "买家"},
            {"id": "admin", "label": "管理员"},
        ],
    }
    xml = architecture_model_to_drawio(model)
    assert_drawio_ids_subset(
        xml, expected_vertex_ids=expected_architecture_vertex_ids(model)
    )
    assert "买家" in xml
    assert "SpringBoot" in xml
    assert "MySQL" in xml
