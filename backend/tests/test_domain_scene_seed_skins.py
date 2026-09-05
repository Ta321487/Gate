"""各域 scene seed 货皮串味锁：apply 后须含本皮标志物、不含他皮标志物。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.scene_scan import (
    food_product_kind,
    hospital_product_kind,
    hotel_product_kind,
    meeting_product_kind,
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


class ShopSceneSeedSkinTests(unittest.TestCase):
    """DOM-SHOP：farm/print/flowers/errand/points/campus/retail 互不串味。"""

    # kind → (title, body, must_have, must_not)
    CASES: dict[str, tuple[str, str, tuple[str, ...], tuple[str, ...]]] = {
        "farm": (
            "农产品电商系统",
            "助农生鲜果蔬粮油",
            ("红富士苹果", "水果", "有机生菜"),
            (
                "日用收纳盒",
                "'热销'",
                "康乃馨",
                "黑白打印",
                "食堂代买套餐",
                "校徽帆布袋",
                "高等数学",
            ),
        ),
        "print": (
            "文印打印店订单管理系统",
            "打印装订下单",
            ("黑白打印", "毕业论文胶装", "文印店长"),
            (
                "红富士苹果",
                "康乃馨",
                "食堂代买套餐",
                "日用收纳盒",
                "'热销'",
                "校徽帆布袋",
            ),
        ),
        "flowers": (
            "鲜花销售管理系统",
            "鲜切花盆花绿植下单",
            ("康乃馨花束", "鲜切花", "绿萝盆栽"),
            (
                "红富士苹果",
                "食堂代买套餐",
                "黑白打印",
                "日用收纳盒",
                "'热销'",
                "跑腿调度",
            ),
        ),
        "errand": (
            "校园跑腿代买订单管理系统",
            "代买餐饮代取快递",
            ("食堂代买套餐", "跑腿调度", "代取快递"),
            (
                "红富士苹果",
                "康乃馨花束",
                "日用收纳盒",
                "'热销'",
                "高等数学上下册",
                "驿站取件核销",
            ),
        ),
        "points": (
            "校园积分商城兑换系统",
            "积分兑换文创",
            ("校徽帆布袋", "积分商城主管", "文创兑换"),
            (
                "红富士苹果",
                "康乃馨",
                "食堂代买套餐",
                "日用收纳盒",
                "'热销'",
            ),
        ),
        "campus": (
            "校园二手闲置交易系统",
            "校内二手教材数码",
            ("高等数学上下册", "教材教辅", "九成新"),
            (
                "红富士苹果",
                "康乃馨",
                "食堂代买套餐",
                "日用收纳盒",
                "'热销'",
            ),
        ),
        "retail": (
            "数码配件商城系统",
            "社区二手数码配件零售",
            ("日用收纳盒", "热销爆款套装"),
            (
                "红富士苹果",
                "康乃馨",
                "食堂代买套餐",
                "黑白打印",
                "校徽帆布袋",
                "高等数学上下册",
            ),
        ),
    }

    def test_shop_kinds_no_cross_skin(self) -> None:
        for kind, (title, body, must, must_not) in self.CASES.items():
            with self.subTest(kind=kind):
                self.assertEqual(shop_product_kind(title, body), kind)
                sql = _apply("DOM-SHOP", "DOM-SHOP.sql", title, body)
                for w in must:
                    self.assertIn(w, sql, f"{kind} missing {w!r}")
                for w in must_not:
                    self.assertNotIn(w, sql, f"{kind} leaked {w!r}")


class FoodSceneSeedSkinTests(unittest.TestCase):
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
        self.assertNotIn("示例小区 5 号楼", canteen)

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
        self.assertIn("总店", restaurant)
        self.assertIn("门店主管", restaurant)
        self.assertNotIn("窗口A", restaurant)
        self.assertNotIn("食堂主管", restaurant)


class HospitalSceneSeedSkinTests(unittest.TestCase):
    CASES: dict[str, tuple[str, str, tuple[str, ...], tuple[str, ...]]] = {
        "clinic": (
            "医院门诊挂号预约系统",
            "门诊挂号预约医生",
            ("张医生", "钱患者", "口腔专科"),
            ("社保卡补换窗口", "内科三病区探视", "HPV九价接种", "宠主甲", "剪发"),
        ),
        "window": (
            "政务大厅窗口取号预约系统",
            "社保户籍车管窗口",
            ("社保卡补换窗口", "大厅主管", "取号须知"),
            ("钱患者", "HPV九价接种", "宠主甲", "基础剪发", "快充桩"),
        ),
        "visit": (
            "医院病区探视预约系统",
            "探视陪护养老探访",
            ("内科三病区探视", "探视须知"),
            ("社保卡补换窗口", "HPV九价接种", "宠主甲", "基础剪发", "快充桩"),
        ),
        "vaccine": (
            "社区疫苗接种预约系统",
            "疫苗接种预约",
            ("HPV九价接种", "接种点主管"),
            ("社保卡补换窗口", "内科三病区探视", "宠主甲", "基础剪发"),
        ),
        "pet": (
            "宠物医院挂号预约系统",
            "宠物门诊挂号",
            ("宠主甲", "豆豆", "宠物医院主管"),
            ("社保卡补换窗口", "内科三病区探视", "HPV九价接种", "基础剪发"),
        ),
    }

    def test_hospital_kinds_no_cross_skin(self) -> None:
        for kind, (title, body, must, must_not) in self.CASES.items():
            with self.subTest(kind=kind):
                self.assertEqual(hospital_product_kind(title, body), kind)
                sql = _apply("DOM-HOSPITAL", "DOM-HOSPITAL.sql", title, body)
                for w in must:
                    self.assertIn(w, sql, f"{kind} missing {w!r}")
                for w in must_not:
                    self.assertNotIn(w, sql, f"{kind} leaked {w!r}")


class SalonSceneSeedSkinTests(unittest.TestCase):
    CASES: dict[str, tuple[str, str, tuple[str, ...], tuple[str, ...]]] = {
        "salon": (
            "美发店预约管理系统",
            "美发烫染造型预约",
            ("基础剪发", "精致烫染咨询"),
            ("力量私教体验", "王咨询师", "上门保洁", "科目二", "快充桩"),
        ),
        "fitness": (
            "健身房私教预约系统",
            "健身私教团课预约",
            ("力量私教体验", "瑜伽团课", "健身预约"),
            ("基础剪发", "精致烫染咨询", "王咨询师", "上门保洁", "科目二"),
        ),
        "counsel": (
            "心理咨询预约系统",
            "个体咨询团体辅导",
            ("王咨询师", "学业压力个体咨询", "咨询预约"),
            ("基础剪发", "力量私教体验", "上门保洁", "科目二", "快充桩"),
        ),
        "home": (
            "家政上门预约系统",
            "上门保洁维修",
            ("上门保洁", "家政站主管"),
            ("基础剪发", "力量私教体验", "王咨询师", "科目二", "快充桩"),
        ),
        "drive": (
            "驾校练车预约系统",
            "科目二科目三练车",
            ("科目二场地练车", "驾校主管", "张教练"),
            ("基础剪发", "力量私教体验", "王咨询师", "上门保洁", "快充桩"),
        ),
        "tutor": (
            "家教辅导预约系统",
            "学科辅导一对一",
            ("高中数学一对一", "辅导站主管", "陈老师"),
            ("基础剪发", "力量私教体验", "王咨询师", "上门保洁", "科目二", "快充桩"),
        ),
    }

    def test_salon_kinds_no_cross_skin(self) -> None:
        for kind, (title, body, must, must_not) in self.CASES.items():
            with self.subTest(kind=kind):
                self.assertEqual(salon_product_kind(title, body), kind)
                sql = _apply("DOM-SALON", "DOM-SALON.sql", title, body)
                for w in must:
                    self.assertIn(w, sql, f"{kind} missing {w!r}")
                for w in must_not:
                    self.assertNotIn(w, sql, f"{kind} leaked {w!r}")


class ParkingHotelSceneSeedSkinTests(unittest.TestCase):
    def test_parking_charge_space_campus(self) -> None:
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
        self.assertIn("充电预约", charge)
        self.assertNotIn("基础剪发", charge)
        self.assertNotIn("张医生", charge)
        self.assertNotIn("星河科技", charge)

        space = _apply(
            "DOM-PARKING",
            "DOM-PARKING.sql",
            "商业停车场车位预约系统",
            "月租临停车位",
        )
        self.assertEqual(
            parking_product_kind("商业停车场车位预约系统", "月租临停车位"),
            "space",
        )
        self.assertNotIn("快充桩", space)
        self.assertNotIn("基础剪发", space)
        self.assertNotIn("张医生", space)

        campus_title = "校园车位预约管理系统"
        campus_body = "教职工与学生预约校内车位"
        self.assertEqual(scene_for("DOM-PARKING", campus_title, campus_body), "campus")
        campus = _apply("DOM-PARKING", "DOM-PARKING.sql", campus_title, campus_body)
        self.assertIn("图书馆东侧", campus)
        self.assertNotIn("快充桩", campus)
        self.assertNotIn("星河科技", campus)

    def test_hotel_homestay_vs_hotel(self) -> None:
        homestay = _apply(
            "DOM-HOTEL",
            "DOM-HOTEL.sql",
            "乡村民宿预订系统",
            "山景房亲子房民宿",
        )
        self.assertEqual(
            hotel_product_kind("乡村民宿预订系统", "山景房亲子房民宿"),
            "homestay",
        )
        self.assertIn("山景双床客栈房", homestay)
        self.assertIn("民宿预订", homestay)
        self.assertNotIn("基础剪发", homestay)
        self.assertNotIn("张医生", homestay)
        self.assertNotIn("快充桩", homestay)

        hotel = _apply(
            "DOM-HOTEL",
            "DOM-HOTEL.sql",
            "商务宾馆客房预订系统",
            "宾馆客房预订",
        )
        self.assertEqual(
            hotel_product_kind("商务宾馆客房预订系统", "宾馆客房预订"),
            "hotel",
        )
        self.assertNotIn("山景双床客栈房", hotel)
        self.assertNotIn("民宿老板", hotel)
        self.assertNotIn("基础剪发", hotel)


class MeetingSceneSeedSkinTests(unittest.TestCase):
    """展馆 / 场馆 / 会议室：预约对象不得与医院/美发/充电串味。"""

    def test_exhibit_gym_room_no_cross_skin(self) -> None:
        exhibit = _apply(
            "DOM-MEETING",
            "DOM-MEETING.sql",
            "党史馆参观预约系统",
            "展厅参观预约",
        )
        self.assertEqual(
            meeting_product_kind("党史馆参观预约系统", "展厅参观预约"),
            "exhibit",
        )
        self.assertIn("党史馆一楼展厅", exhibit)
        self.assertIn("参观预约须知", exhibit)
        self.assertNotIn("羽毛球馆", exhibit)
        self.assertNotIn("基础剪发", exhibit)
        self.assertNotIn("张医生", exhibit)
        self.assertNotIn("快充桩", exhibit)

        gym = _apply(
            "DOM-MEETING",
            "DOM-MEETING.sql",
            "体育馆场地预约系统",
            "羽毛球游泳馆预约",
        )
        self.assertEqual(
            meeting_product_kind("体育馆场地预约系统", "羽毛球游泳馆预约"),
            "gym",
        )
        self.assertIn("羽毛球馆 3 号场", gym)
        self.assertIn("场地预约须知", gym)
        self.assertNotIn("党史馆一楼展厅", gym)
        self.assertNotIn("基础剪发", gym)
        self.assertNotIn("张医生", gym)
        self.assertNotIn("快充桩", gym)

        room = _apply(
            "DOM-MEETING",
            "DOM-MEETING.sql",
            "会议室分时预约管理系统",
            "会议室预约",
        )
        self.assertEqual(
            meeting_product_kind("会议室分时预约管理系统", "会议室预约"),
            "meeting",
        )
        self.assertNotIn("党史馆一楼展厅", room)
        self.assertNotIn("羽毛球馆 3 号场", room)
        self.assertNotIn("基础剪发", room)
        self.assertNotIn("张医生", room)


if __name__ == "__main__":
    unittest.main()
