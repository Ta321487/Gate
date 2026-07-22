"""E-R 中文标签：确定性映射 + 英文缺口补丁。"""

from __future__ import annotations

from app.bake.schema.er import (
    apply_er_label_patch,
    collect_english_gaps,
    looks_latin,
    schema_model,
    scrub_relation_labels,
)
from app.bake.sql.fragments import _USER_LEDGER_DDL


def test_user_ledger_fully_chinese():
    model = schema_model(_USER_LEDGER_DDL)
    ledger = next(t for t in model["tables"] if t["name"] == "user_ledger")
    assert ledger["label"] == "账户流水"
    by_name = {c["name"]: c["label"] for c in ledger["columns"]}
    assert by_name["id"] == "编号"
    assert by_name["username"] == "用户名"
    assert by_name["kind"] == "类型"
    assert by_name["delta"] == "变动额"
    assert by_name["balance_after"] == "变动后余额"
    assert by_name["reason"] == "事由"
    assert by_name["ref_type"] == "关联类型"
    assert by_name["ref_id"] == "关联编号"
    assert by_name["operator"] == "操作人"
    assert by_name["created_at"] == "创建时间"
    gaps = collect_english_gaps(model)
    assert gaps["tables"] == []
    assert gaps["columns"] == []


def test_collect_english_gaps_and_patch():
    sql = """
    CREATE TABLE IF NOT EXISTS weird_widget (
      id BIGINT PRIMARY KEY AUTO_INCREMENT,
      frozzle VARCHAR(32) NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    model = schema_model(sql)
    gaps = collect_english_gaps(model)
    assert any(g["name"] == "weird_widget" for g in gaps["tables"])
    assert any(g["name"] == "frozzle" for g in gaps["columns"])
    patched = apply_er_label_patch(
        model,
        {
            "tables": {"weird_widget": "奇异部件"},
            "columns": {"weird_widget": {"frozzle": "异形码"}},
            "relations": {},
        },
    )
    w = next(t for t in patched["tables"] if t["name"] == "weird_widget")
    assert w["label"] == "奇异部件"
    assert {c["name"]: c["label"] for c in w["columns"]}["frozzle"] == "异形码"
    assert collect_english_gaps(patched)["tables"] == []
    assert collect_english_gaps(patched)["columns"] == []


def test_reject_latin_in_patch():
    model = {
        "tables": [{"name": "t1", "label": "t1", "columns": [{"name": "x", "label": "x"}]}],
        "relations": [],
    }
    patched = apply_er_label_patch(
        model,
        {"tables": {"t1": "stillEnglish"}, "columns": {"t1": {"x": "alsoEn"}}, "relations": {}},
    )
    assert looks_latin(patched["tables"][0]["label"])
    assert patched["tables"][0]["label"] == "t1"


def test_expand_user_roles_from_domain_json(tmp_path):
    """同一张 sys_user，总图按 roles JSON 拆成申领人 / 库管员，不再只显示「用户」。"""
    import json
    from app.bake.schema.er import expand_user_role_entities, schema_model

    sql = """
    CREATE TABLE IF NOT EXISTS sys_user (
      id BIGINT PRIMARY KEY,
      username VARCHAR(64)
    );
    CREATE TABLE IF NOT EXISTS requisition (
      id BIGINT PRIMARY KEY,
      username VARCHAR(64),
      assignee_username VARCHAR(64)
    );
    CREATE TABLE IF NOT EXISTS sys_notice (
      id BIGINT PRIMARY KEY,
      publisher_username VARCHAR(64)
    );
    """
    model = schema_model(
        sql,
        extra_rel_zh={
            "requisition": "提交申领",
            "requisition::assignee_username": "通过出库",
            "::assignee_username": "通过出库",
        },
    )
    domain = tmp_path / "domain.schema.json"
    domain.write_text(
        json.dumps(
            {
                "roles": {
                    "user": {"id": "user", "label": "申领人"},
                    "admin": {"id": "admin", "label": "仓管主管（总管）"},
                    "subadmin": {"id": "subadmin", "label": "库管员"},
                    "allowAppointFromUsers": True,
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    expanded = expand_user_role_entities(model, domain)
    labels = {t["name"]: t["label"] for t in expanded["tables"]}
    assert labels.get("sys_user:user") == "申领人"
    assert labels.get("sys_user:subadmin") == "库管员"
    assert labels.get("sys_user:admin") == "仓管主管"
    # 总图连通实体里不应再依赖笼统「用户」框（物理表仍保留给分图）
    assert labels.get("sys_user") == "用户"
    by = {(r["via"], r["left"]): r["label"] for r in expanded["relations"]}
    assert by[("username", "sys_user:user")] == "提交申领"
    assert by[("assignee_username", "sys_user:subadmin")] == "通过出库"
    assert by[("publisher_username", "sys_user:admin")] == "发布"
    # 角色间逻辑联系
    assert by[("staff_post", "sys_user:admin")] == "任命"
    assert by[("role_manage", "sys_user:admin")] == "管理"
    total_names = {
        t["label"]
        for t in expanded["tables"]
        if t["name"] != "sys_user"
        and any(
            r["left"] == t["name"] or r["right"] == t["name"] for r in expanded["relations"]
        )
    }
    assert "用户" not in total_names
    assert "申领人" in total_names
    assert "库管员" in total_names
    assert "仓管主管" in total_names


def test_reject_entity_name_as_relation():
    """联系菱形不得用「用户」「分类」等实体名；无角色字段时按子表判断。"""
    sql = """
    CREATE TABLE IF NOT EXISTS sys_user (
      id BIGINT PRIMARY KEY,
      username VARCHAR(64)
    );
    CREATE TABLE IF NOT EXISTS category (
      id BIGINT PRIMARY KEY,
      name VARCHAR(64)
    );
    CREATE TABLE IF NOT EXISTS biz_item (
      id BIGINT PRIMARY KEY,
      category_id BIGINT
    );
    CREATE TABLE IF NOT EXISTS sys_notice (
      id BIGINT PRIMARY KEY,
      publisher_username VARCHAR(64)
    );
    CREATE TABLE IF NOT EXISTS sys_message (
      id BIGINT PRIMARY KEY,
      username VARCHAR(64)
    );
    CREATE TABLE IF NOT EXISTS user_ledger (
      id BIGINT PRIMARY KEY,
      username VARCHAR(64)
    );
    CREATE TABLE IF NOT EXISTS biz_ticket (
      id BIGINT PRIMARY KEY,
      username VARCHAR(64),
      assignee_username VARCHAR(64)
    );
    CREATE TABLE IF NOT EXISTS biz_ticket_progress (
      id BIGINT PRIMARY KEY,
      ticket_id BIGINT
    );
    """
    model = schema_model(
        sql,
        extra_table_zh={
            "biz_item": "物资",
            "biz_ticket": "申领",
            "sys_notice": "公告",
            "category": "分类",
        },
        extra_rel_zh={
            "biz_ticket": "提交申领",
            "biz_ticket::assignee_username": "通过出库",
            "::assignee_username": "通过出库",
        },
    )
    by_via = {(r["via"], r["right"]): r["label"] for r in model["relations"]}
    assert by_via[("category_id", "biz_item")] == "属于"
    assert by_via[("publisher_username", "sys_notice")] == "发布"
    assert by_via[("username", "sys_message")] == "接收"
    assert by_via[("username", "user_ledger")] == "归属"
    assert by_via[("assignee_username", "biz_ticket")] == "通过出库"
    assert by_via[("username", "biz_ticket")] == "提交申领"
    assert by_via[("ticket_id", "biz_ticket_progress")] == "进度"
    entity_names = {t["label"] for t in model["tables"]}
    assert all(r["label"] not in entity_names for r in model["relations"])

    # 脏数据：公告联系写成「用户」→ 打回「发布」（按子表，不依赖总图是否画出字段）
    dirty = dict(model)
    dirty["relations"] = [dict(r) for r in model["relations"]]
    for r in dirty["relations"]:
        if r["via"] == "publisher_username":
            r["label"] = "用户"
        if r["via"] == "category_id":
            r["label"] = "分类"
    scrub_relation_labels(dirty)
    by_via2 = {(r["via"], r["right"]): r["label"] for r in dirty["relations"]}
    assert by_via2[("publisher_username", "sys_notice")] == "发布"
    assert by_via2[("category_id", "biz_item")] == "属于"

    patched = apply_er_label_patch(
        model,
        {
            "relations": {
                next(r["name"] for r in model["relations"] if r["via"] == "category_id"): "分类",
                next(
                    r["name"] for r in model["relations"] if r["via"] == "publisher_username"
                ): "用户",
            }
        },
    )
    by_via3 = {(r["via"], r["right"]): r["label"] for r in patched["relations"]}
    assert by_via3[("category_id", "biz_item")] == "属于"
    assert by_via3[("publisher_username", "sys_notice")] == "发布"
