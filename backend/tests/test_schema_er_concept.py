"""毕设口径：概念实体 / M:N 中间表 / 实体属性图无外键。"""

from __future__ import annotations

import re
import unittest

from app.bake.schema.er_model import (
    Table,
    Column,
    is_assoc_link,
    schema_model,
)
from app.bake.schema.er_svg import render_er_svg


_SHOP_SQL = """
CREATE TABLE `sys_user` (
  `id` INT PRIMARY KEY,
  `username` VARCHAR(64) NOT NULL
);
CREATE TABLE `product` (
  `id` INT PRIMARY KEY,
  `name` VARCHAR(128),
  `price` DECIMAL(10,2),
  `category_id` INT,
  FOREIGN KEY (`category_id`) REFERENCES `category`(`id`)
);
CREATE TABLE `category` (
  `id` INT PRIMARY KEY,
  `name` VARCHAR(64)
);
CREATE TABLE `cart` (
  `id` INT PRIMARY KEY,
  `username` VARCHAR(64) NOT NULL UNIQUE,
  `created_at` DATETIME,
  FOREIGN KEY (`username`) REFERENCES `sys_user`(`username`)
);
CREATE TABLE `cart_line` (
  `id` INT PRIMARY KEY,
  `cart_id` INT NOT NULL,
  `product_id` INT NOT NULL,
  `qty` INT,
  FOREIGN KEY (`cart_id`) REFERENCES `cart`(`id`),
  FOREIGN KEY (`product_id`) REFERENCES `product`(`id`)
);
CREATE TABLE `biz_order` (
  `id` INT PRIMARY KEY,
  `username` VARCHAR(64),
  `total_amount` DECIMAL(10,2),
  `status` VARCHAR(32),
  `created_at` DATETIME,
  FOREIGN KEY (`username`) REFERENCES `sys_user`(`username`)
);
CREATE TABLE `order_line` (
  `id` INT PRIMARY KEY,
  `order_id` INT NOT NULL,
  `product_id` INT NOT NULL,
  `qty` INT,
  `price` DECIMAL(10,2),
  FOREIGN KEY (`order_id`) REFERENCES `biz_order`(`id`),
  FOREIGN KEY (`product_id`) REFERENCES `product`(`id`)
);
CREATE TABLE `user_favorite` (
  `id` INT PRIMARY KEY,
  `username` VARCHAR(64) NOT NULL,
  `product_id` INT NOT NULL,
  FOREIGN KEY (`username`) REFERENCES `sys_user`(`username`),
  FOREIGN KEY (`product_id`) REFERENCES `product`(`id`)
);
CREATE TABLE `user_address` (
  `id` INT PRIMARY KEY,
  `username` VARCHAR(64),
  `detail` VARCHAR(255),
  FOREIGN KEY (`username`) REFERENCES `sys_user`(`username`)
);
"""

_RESERVATION_SQL = """
CREATE TABLE `sys_user` (
  `id` INT PRIMARY KEY,
  `username` VARCHAR(64)
);
CREATE TABLE `resource_slot` (
  `id` INT PRIMARY KEY,
  `slot_date` DATE,
  `start_time` VARCHAR(8)
);
CREATE TABLE `reservation` (
  `id` INT PRIMARY KEY,
  `username` VARCHAR(64),
  `slot_id` INT,
  `status` VARCHAR(32),
  `remark` VARCHAR(255),
  `created_at` DATETIME,
  FOREIGN KEY (`username`) REFERENCES `sys_user`(`username`),
  FOREIGN KEY (`slot_id`) REFERENCES `resource_slot`(`id`)
);
"""


class ErConceptTests(unittest.TestCase):
    def test_shop_links_collapse_to_nm(self) -> None:
        m = schema_model(_SHOP_SQL)
        links = set(m.get("link_tables") or [])
        self.assertIn("user_favorite", links)
        self.assertIn("cart_line", links)
        self.assertIn("order_line", links)
        conceptual = set(m.get("conceptual_entities") or [])
        self.assertNotIn("user_favorite", conceptual)
        self.assertNotIn("cart_line", conceptual)
        self.assertNotIn("order_line", conceptual)
        self.assertIn("biz_order", conceptual)
        self.assertIn("product", conceptual)
        self.assertIn("cart", conceptual)

        rels = m.get("relations") or []
        # 中间表不应再作为 right/left 矩形端点
        for r in rels:
            self.assertNotIn(r["left"], links)
            self.assertNotIn(r["right"], links)

        nm = [
            r
            for r in rels
            if str(r.get("card_left")) == "n" and str(r.get("card_right")) == "m"
        ]
        vias = {r.get("via") for r in nm}
        self.assertIn("user_favorite", vias)
        self.assertIn("cart_line", vias)
        self.assertIn("order_line", vias)

        svg = render_er_svg(m, mode="total")
        # 总图矩形不含中间表名
        for name in ("user_favorite", "cart_line", "order_line"):
            self.assertNotIn(f'data-id="entity:{name}"', svg)
        self.assertIn('data-kind="rel"', svg)
        self.assertIn("data-left=", svg)
        self.assertIn("data-right=", svg)

    def test_cart_user_unique_is_one_to_one(self) -> None:
        m = schema_model(_SHOP_SQL)
        cart_rels = [
            r
            for r in (m.get("relations") or [])
            if r.get("right") == "cart" or (r.get("left") == "cart" and r.get("via") == "username")
        ]
        # 用户 → 购物车：UNIQUE username → 1:1
        found = False
        for r in m.get("relations") or []:
            if r.get("right") == "cart" and r.get("via") == "username":
                self.assertEqual(r.get("card_left"), "1")
                self.assertEqual(r.get("card_right"), "1")
                found = True
        self.assertTrue(found, "expected 1:1 user-cart relation")

    def test_order_part_attrs_exclude_fk(self) -> None:
        m = schema_model(_SHOP_SQL)
        by = {t["name"]: t for t in m["tables"]}
        order = by["biz_order"]
        own = order.get("own_columns") or [
            c for c in order["columns"] if not c.get("fk")
        ]
        fk_names = {c["name"] for c in order["columns"] if c.get("fk")}
        self.assertIn("username", fk_names)
        self.assertTrue(all(not c.get("fk") for c in own))

        svg = render_er_svg(m, mode="part", entity="biz_order")
        # 属性椭圆数 = 非 FK 列
        ellipses = len(re.findall(r'data-kind="attr"', svg))
        self.assertEqual(ellipses, len(own))
        self.assertNotIn("polyline", svg)  # 无 FK 波浪线
        for c in order["columns"]:
            if c.get("fk"):
                self.assertNotIn(f'attr:biz_order.{c["name"]}', svg)

    def test_reservation_with_business_cols_not_link(self) -> None:
        m = schema_model(_RESERVATION_SQL)
        self.assertNotIn("reservation", set(m.get("link_tables") or []))
        self.assertIn("reservation", set(m.get("conceptual_entities") or []))
        # 仍是 1:n 到两边，不是 N:M 塌缩
        nm = [
            r
            for r in (m.get("relations") or [])
            if r.get("card_left") == "n" and r.get("card_right") == "m"
        ]
        self.assertEqual(nm, [])
        t = Table(
            name="reservation",
            columns=[
                Column("id", "INT", pk=True),
                Column("username", "VARCHAR(64)", fk=True, fk_table="sys_user"),
                Column("slot_id", "INT", fk=True, fk_table="resource_slot"),
                Column("status", "VARCHAR(32)"),
                Column("remark", "VARCHAR(255)"),
            ],
        )
        others = [
            Table(name="sys_user", columns=[Column("id", "INT", pk=True)]),
            Table(name="resource_slot", columns=[Column("id", "INT", pk=True)]),
            t,
        ]
        self.assertFalse(is_assoc_link(t, others))


if __name__ == "__main__":
    unittest.main()
