"""订单明细快照：刻字/祝语/印字/刻章共用三列，不另开礼品域。"""

from __future__ import annotations

import re

from app.bake.domain_schema import attach_accept
from app.bake.engine_sql import domain_sql
from app.bake.features.line_custom import LINE_CUSTOM_CAP
from app.bake.scene_scan import shop_catalog_kind, shop_product_kind

_GIFT_TITLE = "基于 Spring Boot 与 Vue 的定制礼品商城系统的设计与实现"
_GIFT_BODY = (
    "用户浏览礼品、加入购物车、填写刻字内容、选择字体颜色尺寸、上传定制图片后下单。"
    "订单进入待制作，制作完成后发货。定制品不支持无理由退货。"
)


def _schema(domain: str, title: str, body: str) -> dict:
    spec = attach_accept(
        {"domain": domain, "title": title, "capabilities": []},
        body,
    )
    return spec


def test_gift_opening_enables_snapshot_and_skin() -> None:
    assert shop_product_kind(_GIFT_TITLE, _GIFT_BODY) == "retail"
    assert shop_catalog_kind(_GIFT_TITLE, _GIFT_BODY) == "retail_gift"
    spec = _schema("DOM-SHOP", _GIFT_TITLE, _GIFT_BODY)
    assert LINE_CUSTOM_CAP in (spec.get("capabilities") or [])
    schema = spec["schema"]
    assert schema.get("lineCustom") is True
    assert schema.get("lineCustomPlaceConfirmed") is True
    assert schema.get("noCasualRefund") is True
    labels = schema["labels"]
    assert labels["lineCustomTextLabel"] == "刻字内容"
    assert labels["lineCustomSpecLabel"] == "字体/颜色/尺寸"
    assert labels["lineCustomImageLabel"] == "定制图片"
    assert labels["refundPolicyHint"].startswith("不支持无理由退货")
    states = schema["entities"]["order"]["states"]
    assert states["confirmed"] == "待制作"
    assert states["shipped"] == "已发货"
    assert schema["roles"]["admin"]["label"] == "礼品店主管（总管）"
    assert schema["roles"]["subadmin"]["label"] == "制作员"

    sql = domain_sql("DOM-SHOP", "t", title=_GIFT_TITLE, proposal_text=_GIFT_BODY)
    create = re.search(
        r"CREATE TABLE IF NOT EXISTS\s+order_line\s*\((.*?)\)\s*;",
        sql,
        re.I | re.S,
    )
    assert create is not None
    assert "custom_text" in create.group(1)
    assert "spec_choice" in create.group(1)
    assert "attach_url" in create.group(1)
    assert "CREATE TABLE IF NOT EXISTS line_spec_option" in sql
    assert "'宋体'" in sql
    keys = [m.get("key") for m in (schema.get("menus") or {}).get("admin") or []]
    assert "line_specs" in keys
    assert "刻字马克杯" in sql
    assert "杯壶刻字" in sql
    assert "礼品店主管" in sql
    assert "制作员" in sql
    assert "'张三'" in sql
    assert "'confirmed'" in sql


def test_blessing_only_is_text_and_not_make() -> None:
    spec = _schema("DOM-FOOD", "蛋糕店订购系统", "下单时填写蛋糕祝语。")
    assert LINE_CUSTOM_CAP in (spec.get("capabilities") or [])
    schema = spec["schema"]
    labels = schema["labels"]
    assert labels["lineCustomTextLabel"] == "祝语"
    assert "lineCustomSpecLabel" not in labels
    assert "lineCustomImageLabel" not in labels
    assert schema.get("lineCustomPlaceConfirmed") is False
    assert not schema.get("noCasualRefund")
    states = schema["entities"]["order"]["states"]
    assert states.get("confirmed") != "待制作"


def test_stamp_and_print_share_columns_without_gift_skin() -> None:
    stamp = _schema("DOM-SHOP", "印章服务系统", "选择印章并填写刻章内容后下单。")
    stamp_schema = stamp["schema"]
    assert LINE_CUSTOM_CAP in (stamp.get("capabilities") or [])
    assert stamp_schema["labels"]["lineCustomTextLabel"] == "刻制内容"
    assert stamp_schema.get("lineCustomPlaceConfirmed") is False
    assert stamp_schema["roles"]["admin"]["label"] != "礼品店主管（总管）"

    printed = _schema("DOM-SHOP", "校园文印店管理系统", "上传文件并填写印字内容后下单。")
    printed_schema = printed["schema"]
    assert LINE_CUSTOM_CAP in (printed.get("capabilities") or [])
    assert printed_schema["labels"]["lineCustomTextLabel"] == "定制文字"
    assert printed_schema["labels"]["lineCustomImageLabel"] == "定制图片"
    assert printed_schema.get("lineCustomPlaceConfirmed") is False

    sql = domain_sql(
        "DOM-SHOP",
        "t",
        title="校园文印店管理系统",
        proposal_text="上传文件并填写印字内容后下单。",
    )
    assert "custom_text" in sql
    assert "刻字马克杯" not in sql


def test_supported_return_and_plain_shop_stay_off() -> None:
    spec = _schema(
        "DOM-SHOP",
        "定制礼品商城",
        "支持七天无理由退货。",
    )
    schema = spec["schema"]
    assert LINE_CUSTOM_CAP in (spec.get("capabilities") or [])
    assert not schema.get("noCasualRefund")

    plain = _schema("DOM-SHOP", "日用百货商城", "购物车下单。")
    assert LINE_CUSTOM_CAP not in (plain.get("capabilities") or [])
    assert not (plain["schema"] or {}).get("lineCustom")
    sql = domain_sql("DOM-SHOP", "t", title="日用百货商城", proposal_text="购物车下单。")
    create = re.search(
        r"CREATE TABLE IF NOT EXISTS\s+order_line\s*\((.*?)\)\s*;",
        sql,
        re.I | re.S,
    )
    assert create is not None
    assert "custom_text" not in create.group(1)
    assert "刻字马克杯" not in sql


def test_plain_shop_metadata_word_custom_is_not_product_custom() -> None:
    """研究现状里的「定制化程度有限 / 可定制电商系统」是系统语义，不是商品定制，不得挂 line_custom。"""
    body = (
        "用户浏览商品、加入购物车、下单结算，管理员管理商品与订单。"
        "垂直健身用品电商平台多依托 Shopify、WooCommerce 等建站工具搭建，定制化程度有限。"
        "面向单店经营者的轻量级、可定制电商系统较少。"
    )
    spec = _schema(
        "DOM-SHOP",
        "基于 Spring Boot 与 Vue 的健身用品电商平台的设计与实现",
        body,
    )
    assert "order_lines" in (spec.get("capabilities") or [])
    assert LINE_CUSTOM_CAP not in (spec.get("capabilities") or [])
    assert spec["schema"].get("lineCustom") is not True
