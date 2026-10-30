"""碎另案 i：订单/报修/预约域种子须撑起工作台 KPI（不限商城）。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.sql.domain_scene_seed import apply_domain_scene_seed

_TPL = Path(__file__).resolve().parents[1] / "app" / "bake" / "sql" / "templates"


def _read(domain: str) -> str:
    return (_TPL / f"{domain}.sql").read_text(encoding="utf-8")


class WorkbenchCrossDomainSeedTests(unittest.TestCase):
    def test_food_template_and_canteen_have_order_statuses(self) -> None:
        raw = _read("DOM-FOOD")
        self.assertIn("'pending'", raw)
        self.assertIn("'completed'", raw)
        self.assertIn("created_at", raw.lower())
        canteen = apply_domain_scene_seed(
            "DOM-FOOD",
            raw,
            title="高校食堂点餐系统",
            proposal_text="窗口堂食外卖宿舍配送",
        )
        block = re.search(r"INSERT IGNORE INTO biz_order\b[\s\S]*?;", canteen, re.I)
        self.assertIsNotNone(block)
        chunk = block.group(0)
        for st in ("pending", "confirmed", "shipped", "completed"):
            self.assertIn(f"'{st}'", chunk)

    def test_property_and_it_tickets_multi_status(self) -> None:
        for dom, title, body in (
            ("DOM-PROPERTY", "小区物业报修系统", "水电门禁报修"),
            ("DOM-IT", "校园网故障报修系统", "终端机房报修"),
            ("DOM-PROPERTY", "市政路灯井盖报修", "路灯井盖市政设施"),
            ("DOM-IT", "企业运维报修系统", "内网终端打印机办公区"),
        ):
            with self.subTest(dom=dom, title=title):
                sql = apply_domain_scene_seed(
                    dom, _read(dom), title=title, proposal_text=body
                )
                block = re.search(
                    r"INSERT IGNORE INTO ticket\b[\s\S]*?;", sql, re.I
                )
                self.assertIsNotNone(block)
                chunk = block.group(0)
                for st in ("pending", "approved", "returned"):
                    self.assertIn(f"'{st}'", chunk, f"{title} 缺 {st}")

    def test_reserve_templates_have_pending_confirmed_completed(self) -> None:
        for dom in (
            "DOM-HOSPITAL",
            "DOM-MEETING",
            "DOM-SALON",
            "DOM-PARKING",
            "DOM-HOTEL",
            "DOM-CARRENT",
        ):
            with self.subTest(dom=dom):
                sql = _read(dom)
                block = re.search(
                    r"INSERT IGNORE INTO reservation\b[\s\S]*?;", sql, re.I
                )
                self.assertIsNotNone(block, dom)
                chunk = block.group(0)
                for st in ("pending", "confirmed", "completed"):
                    self.assertIn(f"'{st}'", chunk, f"{dom} 缺 {st}")

    def test_carrent_orders_multi_status_with_dates(self) -> None:
        sql = _read("DOM-CARRENT")
        block = re.search(r"INSERT IGNORE INTO biz_order\b[\s\S]*?;", sql, re.I)
        self.assertIsNotNone(block)
        chunk = block.group(0)
        for st in ("pending", "confirmed", "completed"):
            self.assertIn(f"'{st}'", chunk)
        self.assertIn("DATE_SUB", chunk)
        self.assertIn("created_at", chunk.lower())

    def test_shop_base_template_four_statuses(self) -> None:
        """无场景皮命中时基线模板本身也要能撑工作台。"""
        sql = _read("DOM-SHOP")
        block = re.search(r"INSERT IGNORE INTO biz_order\b[\s\S]*?;", sql, re.I)
        self.assertIsNotNone(block)
        chunk = block.group(0)
        for st in ("pending", "confirmed", "shipped", "completed"):
            self.assertIn(f"'{st}'", chunk)
        self.assertIn("DATE_SUB", chunk)


if __name__ == "__main__":
    unittest.main()
