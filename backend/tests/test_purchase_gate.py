"""购买审核：药店开，普通商城和医院挂号不开。"""

from __future__ import annotations

import re

from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import domain_sql
from app.bake.features.purchase_gate import PURCHASE_GATE_CAP


def _spec(domain: str, title: str, body: str) -> dict:
    return attach_accept(
        {"domain": domain, "title": title, "capabilities": []},
        body,
    )


def test_pharmacy_review_enables_gate() -> None:
    title = "基于 Spring Boot 的药店管理系统"
    body = "用户上传处方图片，药师审核后购买。处方药每人每月限购。"
    spec = _spec("DOM-SHOP", title, body)
    assert PURCHASE_GATE_CAP in (spec.get("capabilities") or [])
    schema = spec["schema"]
    assert schema.get("purchaseGate") is True
    assert schema["roles"]["subadmin"]["label"] == "药师"
    keys = [f.get("key") for f in schema["entities"]["archive"]["fields"]]
    assert "needPermit" in keys
    assert "monthLimit" in keys
    menus = [m.get("key") for m in (schema.get("menus") or {}).get("admin") or []]
    assert "purchase_permits" in menus
    sql = domain_sql("DOM-SHOP", "t", title=title, proposal_text=body)
    assert "CREATE TABLE IF NOT EXISTS purchase_permit" in sql
    assert "need_permit" in sql
    assert "month_limit=2" in sql
    assert "'pending'" in sql


def test_plain_shop_and_hospital_stay_off() -> None:
    plain = _spec("DOM-SHOP", "日用百货商城", "购物车下单。")
    assert PURCHASE_GATE_CAP not in (plain.get("capabilities") or [])
    sql = domain_sql("DOM-SHOP", "t", title="日用百货商城", proposal_text="购物车下单。")
    create = re.search(
        r"CREATE TABLE IF NOT EXISTS\s+product\s*\((.*?)\)\s*;",
        sql,
        re.I | re.S,
    )
    assert create is not None
    assert "need_permit" not in create.group(1)
    assert "CREATE TABLE IF NOT EXISTS purchase_permit" not in sql

    hospital = domain_sql(
        "DOM-HOSPITAL",
        "t",
        title="医院门诊挂号系统",
        proposal_text="患者选科室挂号就诊，并支持处方开药。",
    )
    assert "CREATE TABLE IF NOT EXISTS purchase_permit" not in hospital
    assert "need_permit" not in hospital
