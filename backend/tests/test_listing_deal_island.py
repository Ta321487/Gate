"""房源成交台账：域默认旁路岛（表 + 三套同源 Store + 管理端点）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.engine_sql import domain_sql

ROOT = Path(__file__).resolve().parents[2]
STORES = {
    "baseline": ROOT / "skeletons" / "baseline",
    "mybatis": ROOT / "skeletons" / "overlays" / "persistence-mybatis",
    "jpa": ROOT / "skeletons" / "overlays" / "persistence-jpa",
}


class ListingDealIslandTests(unittest.TestCase):
    def test_listing_domain_carries_deal_table(self) -> None:
        sql = domain_sql("DOM-LISTING", "t_listing", title="房源信息管理")
        self.assertIn("listing_deal", sql)

    def test_other_domains_not_leaked(self) -> None:
        for dom in ("DOM-FUND", "DOM-CRM", "DOM-RECRUIT", "DOM-GRADE"):
            with self.subTest(domain=dom):
                sql = domain_sql(dom, "t_x", title="通用")
                self.assertNotIn("listing_deal", sql)

    def test_three_stacks_share_store_apis(self) -> None:
        apis = (
            "public static List<Map<String, Object>> listAdmin(",
            "public static Map<String, Object> save(",
            "public static String total()",
            "public static void remove(long id)",
        )
        for label, root in STORES.items():
            text = (
                root / "backend/src/main/java/com/thesis/service/ListingDealStore.java"
            ).read_text(encoding="utf-8")
            for api in apis:
                self.assertIn(api, text, msg=f"{label}:{api}")
            self.assertIn("仅已办结的带看跟进可登记成交", text, msg=label)

    def test_listing_detail_attrs_area_rent(self) -> None:
        """房源开题点名详情属性 → detail_attrs 落真列 area_sqm / rent_yuan（number 型）。"""
        from app.bake.domain_schema import attach_accept

        body = "房源详情显示面积、租金、朝向。"
        spec = attach_accept(
            {
                "domain": "DOM-LISTING",
                "title": "高校房源信息管理系统",
                "capabilities": ["archive", "ticket_flow", "content", "org_users"],
                "archetype": "ARCH-FLOW",
                "features": [],
            },
            body,
        )
        self.assertIn("detail_attrs", spec.get("capabilities") or [])
        arch = ((spec.get("schema") or {}).get("entities") or {}).get("archive") or {}
        by_key = {
            str(f.get("key")): f for f in (arch.get("fields") or []) if isinstance(f, dict)
        }
        self.assertEqual(by_key["areaSqm"]["type"], "number")
        self.assertEqual(by_key["rentYuan"]["type"], "number")
        sql = domain_sql(
            "DOM-LISTING",
            "t_l",
            title="高校房源信息管理系统",
            capabilities=spec.get("capabilities") or [],
            proposal_text=body,
        )
        self.assertIn("area_sqm", sql)
        self.assertIn("rent_yuan", sql)

    def test_controller_exposes_endpoints(self) -> None:
        text = (
            ROOT
            / "skeletons/baseline/backend/src/main/java/com/thesis/controller/ListingDealController.java"
        ).read_text(encoding="utf-8")
        for path in (
            '@RequestMapping("/api/listing-deal")',
            '@GetMapping("/admin")',
            '@GetMapping("/admin/total")',
            '@PostMapping("/admin")',
            '@DeleteMapping("/admin/{id}")',
        ):
            self.assertIn(path, text)
        self.assertIn("AdminAuth.requireAdmin(session)", text)
