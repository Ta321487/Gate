# -*- coding: utf-8 -*-
"""Gate-facing match probes: dense openings must keep named domains."""
from __future__ import annotations

import unittest

from app.bake.catalog import match_text


class MatchFaceAccuracyTests(unittest.TestCase):
    def _dom(self, title: str, body: str) -> str:
        return match_text(body, title).domain

    def test_shop_marketplace_dense(self) -> None:
        self.assertEqual(
            self._dom(
                "农产品多商家销售网站",
                "用户商家管理员。购物车支付订单售后。商家入驻审核库存预警活动审核。留言客服评价。",
            ),
            "DOM-SHOP",
        )

    def test_food_dense(self) -> None:
        self.assertEqual(
            self._dom(
                "食堂点餐外卖系统",
                "菜品购物车下单商家接单配送库存评价支付订单审核。",
            ),
            "DOM-FOOD",
        )

    def test_carpool_yuyue_keeps_carpool(self) -> None:
        """拼车正文写「预约」勿抬场地预约壳改通用。"""
        r = match_text("拼车发布预约成行取消。", "拼车出行")
        self.assertEqual(r.domain, "DOM-CARPOOL", f"arch={r.archetypes} hits={r.hits[:8]}")

    def test_meeting_audit_keeps_meeting(self) -> None:
        self.assertEqual(
            self._dom("会议室预约", "会议室预约审批签到取消使用率统计催办。"),
            "DOM-MEETING",
        )

    def test_hotel_pay_keeps_hotel(self) -> None:
        self.assertEqual(
            self._dom("酒店客房预订", "房型预订审核取消定金支付签到。"),
            "DOM-HOTEL",
        )

    def test_forum_audit_keeps_forum(self) -> None:
        self.assertEqual(
            self._dom("校园论坛", "发帖回帖审帖举报私信。"),
            "DOM-FORUM",
        )

    def test_property_keeps_property(self) -> None:
        self.assertEqual(
            self._dom("物业报修", "报修派单跟进催办完结评价。"),
            "DOM-PROPERTY",
        )

    def test_library_only_keeps_library(self) -> None:
        self.assertEqual(
            self._dom("图书借阅", "借还续借超期罚款。"),
            "DOM-LIBRARY",
        )

    def test_library_plus_seat_may_generic(self) -> None:
        """借阅+座位是真交叉，允许通用壳。"""
        r = match_text("借还续借。阅览室座位预约签到。", "图书借阅与座位预约")
        self.assertIn(r.domain, {"DOM-GENERIC", "DOM-LIBRARY", "DOM-MEETING"})
        if r.domain == "DOM-GENERIC":
            self.assertTrue(len(r.archetypes or []) >= 2)

    def test_doclib_keeps_doclib(self) -> None:
        self.assertEqual(
            self._dom("资料文库", "资料上传分类下载台账。"),
            "DOM-DOCLIB",
        )

    def test_tour_keeps_tour(self) -> None:
        self.assertEqual(
            self._dom("旅游线路报名", "线路报名审核缴费出团取消。"),
            "DOM-TOUR",
        )

    def test_parcel_keeps_parcel(self) -> None:
        self.assertEqual(
            self._dom("快递驿站", "到件取件码核销滞留催领。"),
            "DOM-PARCEL",
        )


if __name__ == "__main__":
    unittest.main()
