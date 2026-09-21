"""验证脚本：模拟健身用品商城 + 宠物用品商城 bake，检查4个功能点。"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_sql import domain_sql
from app.bake.features.multi_category import (
    MULTI_CATEGORY_CAP,
    parse_category_axes,
    scan_multi_category,
)
from app.bake.features.detail_attrs import (
    DETAIL_ATTRS_CAP,
    parse_detail_labels,
)
from app.bake.features.order_extras import (
    FLASH_PRICE_CAP,
    scan_flash_price,
)
from tests.helpers.normalize import normalize_sql

SHOP_CAPS = list(DOMAIN_CAPABILITIES["DOM-SHOP"])

FITNESS_TEXT = """
健身用品商城。
浏览搜索（按运动类型：力量/有氧/瑜伽；按目标部位：胸肌/背部/腿部；按品牌：迪卡侬/李宁/Keep）。
查看商品详情（品牌、材质、重量、尺寸、承重/阻力、适用人群、价格、简介、图片）。
工作台展示近6个月销量趋势图。
活动模块限时购与活动价节日优惠，结算时按活动价计算金额。
购物车、下单、支付、订单管理、库存管理、客服沟通。
"""

PET_TEXT = """
宠物用品商城。
浏览搜索（按宠物类别：猫咪/狗狗/其他；按功能用途：粮食/玩具/洗护；按适用阶段：幼年期/成年期/老年期）。
查看商品详情（品牌、材质、重量、尺寸、适用宠物、口味、容量、价格、简介、图片）。
管理员工作台展示近6个月销量趋势与热销商品。
促销模块限时购活动价，下单结算优先取活动价。
购物车、订单管理、库存管理、客户留言反馈。
"""


def run_case(title: str, text: str, db_prefix: str) -> dict:
    print(f"\n===== {title} =====")
    result: dict = {}

    # 1. 扫描
    print(f"\n[扫描] multi_category: {scan_multi_category(text, title)}")
    print(f"[扫描] detail_attrs labels: {parse_detail_labels(text)}")
    print(f"[扫描] category_axes: {parse_category_axes(text, title)}")
    print(f"[扫描] flash_price: {scan_flash_price(text)}")

    # 2. attach_accept
    spec = attach_accept(
        {
            "domain": "DOM-SHOP",
            "title": title,
            "capabilities": list(SHOP_CAPS),
            "archetype": "ARCH-TRADE",
        },
        text,
    )
    caps = spec.get("capabilities") or []
    print(f"\n[能力] caps 命中: {[c for c in caps if c in (MULTI_CATEGORY_CAP, DETAIL_ATTRS_CAP, FLASH_PRICE_CAP)]}")
    result["multi_category_cap"] = MULTI_CATEGORY_CAP in caps
    result["detail_attrs_cap"] = DETAIL_ATTRS_CAP in caps
    result["flash_price_cap"] = FLASH_PRICE_CAP in caps

    # 3. schema / fields
    archive = ((spec.get("schema") or {}).get("entities") or {}).get("archive") or {}
    fields = archive.get("fields") or []
    keys = {f.get("key") for f in fields if isinstance(f, dict)}
    labels = {f.get("label") for f in fields if isinstance(f, dict)}
    print(f"\n[schema] multiCategory: {bool(archive.get('multiCategory'))}")
    print(f"[schema] categoryIds in keys: {'categoryIds' in keys}")
    print(f"[schema] 详情属性字段 labels: {sorted([l for l in labels if l in {'品牌','材质','重量','尺寸'}])}")
    result["multiCategory_flag"] = bool(archive.get("multiCategory"))
    result["categoryIds_key"] = "categoryIds" in keys
    result["detail_attrs_labels_ok"] = {"品牌", "材质", "重量", "尺寸"}.issubset(labels)
    # 活动价字段
    flash_fields = {"promoPrice", "promoStart", "promoEnd"}
    print(f"[schema] flashPriceEnabled: {bool(archive.get('flashPriceEnabled'))}")
    print(f"[schema] 活动价字段 keys: {sorted(keys & flash_fields)}")
    result["flashPrice_flag"] = bool(archive.get("flashPriceEnabled"))
    result["flash_fields_ok"] = flash_fields.issubset(keys)

    # 4. SQL
    sql = domain_sql(
        "DOM-SHOP",
        db_prefix,
        capabilities=caps,
        proposal_text=text,
        title=title,
    )
    n = normalize_sql(sql)
    print(f"\n[SQL] product_category 表: {'product_category' in n}")
    print(f"[SQL] dimension 列: {'dimension' in n}")
    print(f"[SQL] detail_json 列: {'detail_json' in n}")
    print(f"[SQL] promo_price/promo_start/promo_end: {('promo_price' in n) and ('promo_start' in n) and ('promo_end' in n)}")
    result["sql_product_category"] = "product_category" in n
    result["sql_dimension"] = "dimension" in n
    result["sql_detail_json"] = "detail_json" in n
    result["sql_promo_cols"] = ("promo_price" in n) and ("promo_start" in n) and ("promo_end" in n)

    # 解析出的维度种子（验证两个维度以上）
    axes = parse_category_axes(text, title)
    print(f"\n[分类轴] 解析出的轴数: {len(axes)}，轴名: {[a[0] for a in axes]}")
    result["axes_count_ge2"] = len(axes) >= 2

    # 5. 骨架：月销量图 + 活动价结算
    baseline = ROOT / "skeletons" / "baseline"
    dashboard = (baseline / "frontend/src/components/DashboardCharts.vue").read_text(encoding="utf-8")
    order_store = (baseline / "backend/src/main/java/com/thesis/capability/OrderStore.java").read_text(encoding="utf-8")
    archive_store = (baseline / "backend/src/main/java/com/thesis/capability/ArchiveStore.java").read_text(encoding="utf-8")
    browse = (baseline / "frontend/src/views/user/ArchiveBrowse.vue").read_text(encoding="utf-8")
    cats_admin = (baseline / "frontend/src/views/admin/CategoriesAdmin.vue").read_text(encoding="utf-8")
    archive_admin = (baseline / "frontend/src/views/admin/ArchiveAdmin.vue").read_text(encoding="utf-8")
    binder = (baseline / "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java").read_text(encoding="utf-8")

    month_in_dashboard = "近 6 个月销量" in dashboard and "monthSeries" in dashboard
    detail_json_in_store = "detail_json" in archive_store or "detailJson" in archive_store or "detailAttrKeys" in archive_store or "detailAttrsEnabled" in archive_store
    multi_cat_in_store = "configureMultiCategory" in archive_store and "bindItemCategories" in archive_store
    promo_price_in_order = "effectiveUnitPrice" in order_store or "ArchiveStore.effectiveUnitPrice" in order_store or "promoPrice" in order_store
    multi_cat_in_cats_admin = "dimension" in cats_admin and "multiCategory" in cats_admin
    multi_cat_in_archive_admin = "categoryIds" in archive_admin and "multiCategory" in archive_admin
    detail_in_browse = "cardDetailFields" in browse
    binder_multi = "multi-category-enabled" in binder
    binder_detail = "detail-attrs-enabled" in binder
    binder_flash = "flash-price-enabled" in binder

    print(f"\n[骨架] 月销量图(工作台): {month_in_dashboard}")
    print(f"[骨架] ArchiveStore detail_json: {detail_json_in_store}")
    print(f"[骨架] ArchiveStore multiCategory: {multi_cat_in_store}")
    print(f"[骨架] OrderStore 活动价结算: {promo_price_in_order}")
    print(f"[骨架] CategoriesAdmin 多维度: {multi_cat_in_cats_admin}")
    print(f"[骨架] ArchiveAdmin 多分类: {multi_cat_in_archive_admin}")
    print(f"[骨架] Browse 详情属性: {detail_in_browse}")
    print(f"[骨架] DomainRuntimeBinder multi/detail/flash: {binder_multi}/{binder_detail}/{binder_flash}")

    result["skeleton_month_chart"] = month_in_dashboard
    result["skeleton_detail_json_store"] = detail_json_in_store
    result["skeleton_multi_cat_store"] = multi_cat_in_store
    result["skeleton_promo_price_order"] = promo_price_in_order
    result["skeleton_cats_admin_multi"] = multi_cat_in_cats_admin
    result["skeleton_archive_admin_multi"] = multi_cat_in_archive_admin
    result["skeleton_browse_detail"] = detail_in_browse
    result["skeleton_binder_multi"] = binder_multi
    result["skeleton_binder_detail"] = binder_detail
    result["skeleton_binder_flash"] = binder_flash

    return result


def check(name: str, cond: bool) -> tuple[str, bool]:
    mark = "✅ PASS" if cond else "❌ FAIL"
    return (f"  {mark}  {name}", cond)


def print_summary(title: str, r: dict) -> None:
    lines: list[str] = []
    passed = 0
    total = 0

    def add(n: str, c: bool) -> None:
        nonlocal passed, total
        total += 1
        ln, ok = check(n, c)
        lines.append(ln)
        if ok:
            passed += 1

    # 多维分类
    add("多维分类-能力岛挂入", r["multi_category_cap"])
    add("多维分类-schema标志multiCategory", r["multiCategory_flag"])
    add("多维分类-字段categoryIds", r["categoryIds_key"])
    add("多维分类-分类轴>=2个", r["axes_count_ge2"])
    add("多维分类-SQL含product_category表", r["sql_product_category"])
    add("多维分类-SQL含dimension列", r["sql_dimension"])
    add("多维分类-骨架ArchiveStore支持", r["skeleton_multi_cat_store"])
    add("多维分类-骨架分类管理支持dimension", r["skeleton_cats_admin_multi"])
    add("多维分类-骨架档案管理支持categoryIds", r["skeleton_archive_admin_multi"])
    add("多维分类-binder开关", r["skeleton_binder_multi"])

    # 详情属性
    add("详情属性-能力岛挂入", r["detail_attrs_cap"])
    add("详情属性-品牌/材质/重量/尺寸都有label", r["detail_attrs_labels_ok"])
    add("详情属性-SQL含detail_json列", r["sql_detail_json"])
    add("详情属性-骨架Store支持detail_json", r["skeleton_detail_json_store"])
    add("详情属性-骨架Browse支持展示", r["skeleton_browse_detail"])
    add("详情属性-binder开关", r["skeleton_binder_detail"])

    # 月销量图
    add("月销量图-骨架DashboardChart含近6月销量", r["skeleton_month_chart"])

    # 活动价
    add("活动价-能力岛挂入", r["flash_price_cap"])
    add("活动价-schema标志flashPriceEnabled", r["flashPrice_flag"])
    add("活动价-字段promoPrice/promoStart/promoEnd", r["flash_fields_ok"])
    add("活动价-SQL含promo_price/start/end三列", r["sql_promo_cols"])
    add("活动价-骨架OrderStore取活动价结算", r["skeleton_promo_price_order"])
    add("活动价-binder开关", r["skeleton_binder_flash"])

    print(f"\n=== {title} 验证汇总 ({passed}/{total}) ===")
    for ln in lines:
        print(ln)
    return passed, total


if __name__ == "__main__":
    fit = run_case("健身用品商城", FITNESS_TEXT, "thesis_fitness_shop")
    pet = run_case("宠物用品商城", PET_TEXT, "thesis_pet_shop")

    print("\n" + "=" * 60)
    fp, ft = print_summary("健身用品商城", fit)
    print()
    pp, pt = print_summary("宠物用品商城", pet)
    print("\n" + "=" * 60)
    print(f"合计通过 {fp + pp} / {ft + pt}")
    if fp == ft and pp == pt:
        print("全部通过 ✅")
    else:
        print("存在未通过项 ❌")
        sys.exit(1)
