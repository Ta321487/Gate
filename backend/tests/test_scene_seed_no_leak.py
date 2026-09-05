"""货皮 scene seed 串味锁：apply 后须含本皮标志、不含他皮/错误行业词。

覆盖 SHOP / FOOD / 预约族 / 内容 overlays；与 test_domain_scene_seed_skins 互补，
本文件按审计清单正反例写死，便于回归「农产仍有日用收纳盒」类问题。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.scene_scan import (
    blog_product_kind,
    food_product_kind,
    hospital_product_kind,
    hotel_product_kind,
    media_product_kind,
    parking_product_kind,
    salon_product_kind,
    scene_for,
    shop_product_kind,
)
from app.bake.sql.domain_scene_seed import apply_domain_scene_seed

_SQL = Path(__file__).resolve().parents[1] / "app" / "bake" / "sql" / "templates"


def _apply(domain: str, template: str, title: str, body: str = "") -> str:
    raw = (_SQL / template).read_text(encoding="utf-8")
    return apply_domain_scene_seed(domain, raw, title=title, proposal_text=body)


def _category_blob(sql: str) -> str:
    m = re.search(
        r"INSERT IGNORE INTO category \(id, name\) VALUES\s*(.+?);",
        sql,
        re.S,
    )
    return m.group(1) if m else ""


class ShopSceneSeedNoLeakTests(unittest.TestCase):
    """DOM-SHOP：farm/print/flowers/errand/points/campus/retail。"""

    # kind → (title, body, must_have, must_not)
    CASES: list[tuple[str, str, str, tuple[str, ...], tuple[str, ...]]] = [
        (
            "farm",
            "农产品电商系统",
            "助农生鲜果蔬粮油",
            ("水果", "红富士"),
            (
                "日用收纳盒",
                "胶装",
                "康乃馨",
                "跑腿套餐",
                "高等数学",
                "热销",
            ),
        ),
        (
            "print",
            "文印打印店订单管理系统",
            "打印装订下单",
            ("打印", "胶装"),
            ("苹果", "康乃馨", "机械键盘"),
        ),
        (
            "flowers",
            "鲜花销售管理系统",
            "鲜切花盆花绿植下单",
            ("康乃馨", "花"),
            ("胶装", "苹果", "跑腿"),
        ),
        (
            "errand",
            "校园跑腿代买订单管理系统",
            "代买餐饮代取快递",
            ("代买", "跑腿"),
            ("胶装", "苹果", "康乃馨", "驿站取件核销"),
        ),
        (
            "points",
            "校园积分商城兑换系统",
            "积分兑换文创",
            ("积分兑换",),
            ("日用收纳盒",),
        ),
        (
            "campus",
            "校园二手闲置交易系统",
            "校内二手教材数码",
            ("教材", "成色"),
            (),
        ),
        (
            "retail",
            "数码配件商城系统",
            "社区二手数码配件零售",
            ("日用", "配件"),
            (),
        ),
    ]

    def test_shop_kinds_parametrized(self) -> None:
        for kind, title, body, must, must_not in self.CASES:
            with self.subTest(kind=kind):
                self.assertEqual(shop_product_kind(title, body), kind)
                sql = _apply("DOM-SHOP", "DOM-SHOP.sql", title, body)
                for w in must:
                    self.assertIn(w, sql, f"{kind} missing {w!r}")
                for w in must_not:
                    self.assertNotIn(w, sql, f"{kind} leaked {w!r}")

    def test_print_cats_not_farm(self) -> None:
        sql = _apply(
            "DOM-SHOP",
            "DOM-SHOP.sql",
            "文印打印店订单管理系统",
            "打印装订下单",
        )
        self.assertNotIn("水果", _category_blob(sql))

    def test_campus_cats_not_farm_only(self) -> None:
        sql = _apply(
            "DOM-SHOP",
            "DOM-SHOP.sql",
            "校园二手闲置交易系统",
            "校内二手教材数码",
        )
        blob = _category_blob(sql)
        self.assertIn("教材", blob)
        self.assertFalse(
            all(x in blob for x in ("水果", "蔬菜", "粮油"))
            and "教材" not in blob
        )

    def test_retail_cats_not_farm_trio(self) -> None:
        sql = _apply(
            "DOM-SHOP",
            "DOM-SHOP.sql",
            "数码配件商城系统",
            "社区二手数码配件零售",
        )
        blob = _category_blob(sql)
        self.assertFalse(all(x in blob for x in ("水果", "蔬菜", "粮油")))


class FoodSceneSeedNoLeakTests(unittest.TestCase):
    def test_canteen_vs_restaurant(self) -> None:
        canteen = _apply(
            "DOM-FOOD",
            "DOM-FOOD.sql",
            "高校食堂在线点餐系统",
            "餐品目录与下单取餐",
        )
        self.assertEqual(
            food_product_kind("高校食堂在线点餐系统", "餐品目录与下单取餐"),
            "canteen",
        )
        self.assertIn("窗口A", canteen)
        self.assertIn("食堂主管", canteen)
        self.assertNotIn("门店主管", canteen)

        restaurant = _apply(
            "DOM-FOOD",
            "DOM-FOOD.sql",
            "小型餐厅点餐系统",
            "外卖配送点餐",
        )
        self.assertEqual(
            food_product_kind("小型餐厅点餐系统", "外卖配送点餐"),
            "restaurant",
        )
        self.assertIn("门店主管", restaurant)
        self.assertNotIn("窗口A", restaurant)
        self.assertNotIn("食堂主管", restaurant)


class ReserveSceneSeedNoLeakTests(unittest.TestCase):
    HOSPITAL: list[tuple[str, str, str, tuple[str, ...], tuple[str, ...]]] = [
        (
            "pet",
            "宠物医院挂号预约系统",
            "宠物门诊挂号",
            ("宠主甲", "宠物"),
            ("基础剪发", "HPV九价"),
        ),
        (
            "vaccine",
            "社区疫苗接种预约系统",
            "疫苗接种预约",
            ("HPV", "接种"),
            ("基础剪发", "宠主甲"),
        ),
        (
            "window",
            "政务大厅窗口取号预约系统",
            "社保户籍车管窗口",
            ("社保卡补换窗口",),
            ("基础剪发", "钱患者"),
        ),
        (
            "visit",
            "医院病区探视预约系统",
            "探视陪护养老探访",
            ("探视",),
            ("基础剪发", "HPV九价", "宠主甲"),
        ),
    ]

    SALON: list[tuple[str, str, str, tuple[str, ...], tuple[str, ...]]] = [
        (
            "fitness",
            "健身房私教预约系统",
            "健身私教团课预约",
            ("私教", "瑜伽"),
            ("基础剪发",),
        ),
        (
            "home",
            "家政上门预约系统",
            "上门保洁维修",
            ("上门保洁",),
            ("基础剪发",),
        ),
        (
            "counsel",
            "心理咨询预约系统",
            "个体咨询团体辅导",
            ("咨询",),
            ("基础剪发",),
        ),
    ]

    def test_hospital(self) -> None:
        for kind, title, body, must, must_not in self.HOSPITAL:
            with self.subTest(kind=kind):
                self.assertEqual(hospital_product_kind(title, body), kind)
                sql = _apply("DOM-HOSPITAL", "DOM-HOSPITAL.sql", title, body)
                for w in must:
                    self.assertIn(w, sql)
                for w in must_not:
                    self.assertNotIn(w, sql)

    def test_salon(self) -> None:
        for kind, title, body, must, must_not in self.SALON:
            with self.subTest(kind=kind):
                self.assertEqual(salon_product_kind(title, body), kind)
                sql = _apply("DOM-SALON", "DOM-SALON.sql", title, body)
                for w in must:
                    self.assertIn(w, sql)
                for w in must_not:
                    self.assertNotIn(w, sql)

    def test_parking_charge_and_campus(self) -> None:
        charge = _apply(
            "DOM-PARKING",
            "DOM-PARKING.sql",
            "新能源充电桩预约系统",
            "快充慢充预约",
        )
        self.assertEqual(
            parking_product_kind("新能源充电桩预约系统", "快充慢充预约"),
            "charge",
        )
        self.assertIn("快充桩", charge)
        self.assertNotIn("基础剪发", charge)
        self.assertNotIn("张医生", charge)

        title, body = "校园车位预约管理系统", "教职工与学生预约校内车位"
        self.assertEqual(scene_for("DOM-PARKING", title, body), "campus")
        campus = _apply("DOM-PARKING", "DOM-PARKING.sql", title, body)
        self.assertIn("图书馆东侧", campus)
        self.assertNotIn("快充桩", campus)
        self.assertNotIn("基础剪发", campus)

    def test_hotel_homestay(self) -> None:
        title, body = "乡村民宿预订系统", "山景房亲子房民宿"
        self.assertEqual(hotel_product_kind(title, body), "homestay")
        sql = _apply("DOM-HOTEL", "DOM-HOTEL.sql", title, body)
        self.assertIn("山景", sql)
        self.assertIn("民宿", sql)
        self.assertNotIn("基础剪发", sql)
        self.assertNotIn("张医生", sql)


class ContentSceneSeedNoLeakTests(unittest.TestCase):
    def test_blog_press(self) -> None:
        title, body = "校园记者站稿件管理系统", "广播稿图文报道"
        self.assertEqual(blog_product_kind(title, body), "press")
        sql = _apply("DOM-BLOG", "DOM-BLOG.sql", title, body)
        self.assertIn("广播稿", sql)
        self.assertIn("记者站", sql)
        self.assertNotIn("教学安排说明", sql)

    def test_media_coursevod(self) -> None:
        title, body = "课程点播视频学习系统", "点播课专业课"
        self.assertEqual(media_product_kind(title, body), "coursevod")
        sql = _apply("DOM-MEDIA", "DOM-MEDIA.sql", title, body)
        self.assertIn("点播", sql)
        self.assertIn("数据结构", sql)
        self.assertNotIn("实验室安全培训", sql)


if __name__ == "__main__":
    unittest.main()
