"""交易组 trade_thicken：T-00～T-11（含影院卖品与 SHOP 包装费）。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.trade_thicken import (
    TRADE_DOMAINS,
    ensure_catalog_thicken_sql,
    ensure_cinema_thicken_sql,
    ensure_food_thicken_sql,
    ensure_trade_archive_columns,
)


def _spec(domain: str, title: str, body: str = "") -> dict:
    return attach_accept(
        {
            "domain": domain,
            "title": title,
            "capabilities": list(DOMAIN_CAPABILITIES[domain]),
            "features": [],
            "archetype": "ARCH-TRADE",
        },
        body,
    )


class TradeThickenFeatureTests(unittest.TestCase):
    def test_trade_domains_constant(self) -> None:
        self.assertEqual(TRADE_DOMAINS, frozenset({"DOM-SHOP", "DOM-FOOD", "DOM-CINEMA"}))

    def test_hotel_carrent_untouched(self) -> None:
        for domain, title in (
            ("DOM-HOTEL", "酒店客房预订系统"),
            ("DOM-CARRENT", "汽车租赁管理系统"),
        ):
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            self.assertFalse(schema.get("tradeThicken"))
            order = (schema.get("entities") or {}).get("order") or {}
            self.assertFalse(order.get("tradeThicken"))

    def test_shop_t01_nails(self) -> None:
        out = _spec("DOM-SHOP", "校园二手商城系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("tradeThicken") or {}
        labels = schema.get("labels") or {}
        order = (schema.get("entities") or {}).get("order") or {}
        self.assertTrue(order.get("tradeThicken"))
        self.assertTrue(thicken.get("core"))
        self.assertTrue(thicken.get("orderRemark"))
        self.assertTrue(thicken.get("defaultAddress"))
        self.assertTrue(thicken.get("orderTimeoutNail"))
        self.assertFalse(thicken.get("tasteChips"))
        self.assertFalse(thicken.get("cinemaPickup"))
        self.assertIn("orderRemarkLabel", labels)
        self.assertIn("orderRemarkHint", labels)
        self.assertIn("defaultAddressLabel", labels)
        self.assertIn("defaultAddressHint", labels)
        self.assertIn("orderTimeoutHint", labels)
        self.assertGreaterEqual(int(schema.get("orderTimeoutMinutes") or 0), 1)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-SHOP", out)
        self.assertIn("order-timeout-minutes:", yml)
        self.assertRegex(yml, r"order-timeout-minutes:\s*[1-9]\d*")

    def test_food_t01_taste_chips(self) -> None:
        out = _spec("DOM-FOOD", "校园点餐配送系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("tradeThicken") or {}
        labels = schema.get("labels") or {}
        order = (schema.get("entities") or {}).get("order") or {}
        self.assertTrue(thicken.get("tasteChips"))
        self.assertTrue(thicken.get("orderRemark"))
        chips = order.get("tasteNoteChips") or []
        self.assertGreaterEqual(len(chips), 2)
        self.assertIn("tasteNoteLabel", labels)
        self.assertIn("tasteNotePlaceholder", labels)
        self.assertIn("tasteNoteHint", labels)
        self.assertEqual(labels.get("pickupCodeLabel"), "取餐码")

    def test_cinema_t01_pickup(self) -> None:
        out = _spec("DOM-CINEMA", "影院在线选座购票系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("tradeThicken") or {}
        labels = schema.get("labels") or {}
        self.assertTrue(thicken.get("cinemaPickup"))
        self.assertTrue(thicken.get("orderTimeoutNail"))
        self.assertFalse(thicken.get("orderRemark"))
        self.assertFalse(thicken.get("tasteChips"))
        self.assertEqual(labels.get("pickupCodeLabel"), "取票码")
        self.assertIn("pickupCodeHint", labels)
        self.assertGreaterEqual(int(schema.get("orderTimeoutMinutes") or 0), 1)

    def test_approve_domain_untouched(self) -> None:
        out = _spec("DOM-CERT", "校园证明开具管理系统", "")
        schema = out.get("schema") or {}
        self.assertFalse(schema.get("tradeThicken"))

    def test_shop_t02_cart_ux(self) -> None:
        out = _spec("DOM-SHOP", "校园二手商城系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("tradeThicken") or {}
        labels = schema.get("labels") or {}
        archive = ((schema.get("entities") or {}).get("archive") or {})
        keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}
        self.assertTrue(thicken.get("cartSelectAll"))
        self.assertTrue(thicken.get("cartClearInvalid"))
        self.assertTrue(thicken.get("cartAutoUncheck"))
        self.assertTrue(thicken.get("cartChangeSpec"))
        self.assertTrue(thicken.get("cartFreeShip"))
        self.assertEqual(float(schema.get("freeShipYuan") or 0), 49.0)
        self.assertIn("freeShipYuan", keys)
        for key in (
            "cartSelectAllLabel",
            "cartClearInvalidLabel",
            "cartInvalidHint",
            "cartChangeSpecLabel",
            "cartNoSpecHint",
            "cartFreeShipHint",
            "cartFreeShipOkHint",
        ):
            self.assertIn(key, labels)
        self.assertFalse(thicken.get("tasteChips"))

    def test_food_t02_cart_select_only(self) -> None:
        out = _spec("DOM-FOOD", "校园点餐配送系统", "")
        thicken = (out.get("schema") or {}).get("tradeThicken") or {}
        labels = (out.get("schema") or {}).get("labels") or {}
        self.assertTrue(thicken.get("cartSelectAll"))
        self.assertTrue(thicken.get("cartClearInvalid"))
        self.assertTrue(thicken.get("cartAutoUncheck"))
        self.assertFalse(thicken.get("cartChangeSpec"))
        self.assertFalse(thicken.get("cartFreeShip"))
        self.assertIn("cartSelectAllLabel", labels)
        self.assertNotIn("cartChangeSpecLabel", labels)

    def test_cinema_t02_skips_cart_ux(self) -> None:
        out = _spec("DOM-CINEMA", "影院在线选座购票系统", "")
        thicken = (out.get("schema") or {}).get("tradeThicken") or {}
        self.assertTrue(thicken.get("cinemaPickup"))
        self.assertFalse(thicken.get("cartSelectAll"))
        self.assertFalse(thicken.get("cartChangeSpec"))
        self.assertFalse(thicken.get("cartFreeShip"))

    def test_shop_archive_sql_injects_free_ship(self) -> None:
        sql = """
CREATE TABLE IF NOT EXISTS goods (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(128) DEFAULT ''
);
"""
        out = ensure_trade_archive_columns(sql, domain="DOM-SHOP", item_table="goods")
        self.assertIn("free_ship_yuan", out)
        skip = ensure_trade_archive_columns(sql, domain="DOM-FOOD", item_table="goods")
        self.assertNotIn("free_ship_yuan", skip)
        baked = domain_sql(
            "DOM-SHOP",
            "db_test",
            capabilities=list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
            title="校园二手商城系统",
        )
        self.assertIn("free_ship_yuan", baked)

    def test_shop_t03_order_rules(self) -> None:
        out = _spec("DOM-SHOP", "校园二手商城系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("tradeThicken") or {}
        labels = schema.get("labels") or {}
        self.assertTrue(thicken.get("stockLock"))
        self.assertTrue(thicken.get("confirmReceiveTimeout"))
        self.assertTrue(thicken.get("changeAddress"))
        self.assertTrue(thicken.get("salesDaily"))
        self.assertTrue(thicken.get("inviteReview"))
        self.assertTrue(thicken.get("orderReceiptPrint"))
        self.assertGreaterEqual(int(schema.get("confirmReceiveTimeoutMinutes") or 0), 1)
        for key in (
            "stockLockHint",
            "confirmReceiveTimeoutHint",
            "changeAddressLabel",
            "changeAddressHint",
            "salesDailyLabel",
            "salesDailyHint",
            "inviteReviewTitle",
            "inviteReviewBody",
            "orderReceiptPrintLabel",
        ):
            self.assertIn(key, labels)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-SHOP", out)
        self.assertIn("confirm-receive-timeout-minutes:", yml)
        self.assertRegex(yml, r"confirm-receive-timeout-minutes:\s*[1-9]\d*")

    def test_food_t03_skips_shop_only(self) -> None:
        out = _spec("DOM-FOOD", "校园点餐配送系统", "")
        thicken = (out.get("schema") or {}).get("tradeThicken") or {}
        self.assertTrue(thicken.get("stockLock"))
        self.assertTrue(thicken.get("salesDaily"))
        self.assertTrue(thicken.get("inviteReview"))
        self.assertTrue(thicken.get("orderReceiptPrint"))
        self.assertFalse(thicken.get("confirmReceiveTimeout"))
        self.assertFalse(thicken.get("changeAddress"))

    def test_cinema_t03_print_only_rules(self) -> None:
        out = _spec("DOM-CINEMA", "影院在线选座购票系统", "")
        thicken = (out.get("schema") or {}).get("tradeThicken") or {}
        self.assertTrue(thicken.get("orderReceiptPrint"))
        self.assertFalse(thicken.get("stockLock"))
        self.assertFalse(thicken.get("confirmReceiveTimeout"))
        self.assertFalse(thicken.get("changeAddress"))
        self.assertFalse(thicken.get("salesDaily"))
        self.assertFalse(thicken.get("inviteReview"))

    def test_t03_stores_and_schedule(self) -> None:
        from pathlib import Path

        repo = Path(__file__).resolve().parents[2]
        stores = [
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/capability/OrderStore.java",
            repo / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/OrderStore.java",
            repo / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/OrderStore.java",
        ]
        for path in stores:
            text = path.read_text(encoding="utf-8")
            self.assertIn("completeTimedOutUnreceived", text, path.name)
            self.assertIn("updateShippingAddress", text, path.name)
            self.assertIn("salesDailySeries", text, path.name)
            self.assertIn("OrderReviewStore.enabled()", text, path.name)
        jobs = [
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/config/DemoScheduleJobs.java",
            repo / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/config/DemoScheduleJobs.java",
        ]
        for path in jobs:
            text = path.read_text(encoding="utf-8")
            self.assertIn("confirm-receive-timeout-minutes", text, path.name)
            self.assertIn("completeTimedOutUnreceived", text, path.name)
        ctrl = (
            repo
            / "skeletons/baseline/backend/src/main/java/com/thesis/controller/OrderController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/orders/{id}/address", ctrl)
        xml = (
            repo
            / "skeletons/overlays/persistence-mybatis/backend/src/main/resources/mapper/OrderMapper.xml"
        ).read_text(encoding="utf-8")
        self.assertIn("selectTimedOutUnreceivedIds", xml)
        self.assertIn("selectSalesDailySeries", xml)
        self.assertIn("updateOrderAddress", xml)

    def test_shop_t04_after_sale(self) -> None:
        out = _spec("DOM-SHOP", "校园二手商城系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("tradeThicken") or {}
        labels = schema.get("labels") or {}
        order = (schema.get("entities") or {}).get("order") or {}
        self.assertTrue(thicken.get("refundReasonCategories"))
        self.assertTrue(thicken.get("refundReasonRequired"))
        self.assertTrue(thicken.get("refundType"))
        self.assertTrue(thicken.get("refundTracking"))
        self.assertTrue(thicken.get("afterSaleDays"))
        self.assertTrue(thicken.get("refundTrace"))
        self.assertGreaterEqual(int(schema.get("afterSaleDays") or 0), 1)
        opts = order.get("refundReasonOptions") or []
        self.assertGreaterEqual(len(opts), 3)
        for key in (
            "refundReasonLabel",
            "refundReasonHint",
            "refundReasonRequiredHint",
            "refundReasonChartLabel",
            "refundTypeLabel",
            "refundTypeRefundOnly",
            "refundTypeReturnRefund",
            "refundTrackingLabel",
            "afterSaleDaysHint",
            "refundTraceLabel",
        ):
            self.assertIn(key, labels)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-SHOP", out)
        self.assertRegex(yml, r"after-sale-days:\s*[1-9]\d*")
        baked = domain_sql(
            "DOM-SHOP",
            "db_test",
            capabilities=list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
            title="校园二手商城系统",
        )
        for col in ("refund_type", "refund_tracking_no", "refund_requested_at", "completed_at"):
            self.assertIn(col, baked)

    def test_food_t04_reason_only(self) -> None:
        out = _spec("DOM-FOOD", "校园点餐配送系统", "")
        thicken = (out.get("schema") or {}).get("tradeThicken") or {}
        self.assertTrue(thicken.get("refundReasonCategories"))
        self.assertTrue(thicken.get("refundReasonRequired"))
        self.assertFalse(thicken.get("refundType"))
        self.assertFalse(thicken.get("refundTracking"))
        self.assertFalse(thicken.get("afterSaleDays"))
        self.assertFalse(thicken.get("refundTrace"))

    def test_cinema_t04_skips_after_sale(self) -> None:
        out = _spec("DOM-CINEMA", "影院在线选座购票系统", "")
        thicken = (out.get("schema") or {}).get("tradeThicken") or {}
        self.assertFalse(thicken.get("refundReasonCategories"))
        self.assertFalse(thicken.get("refundType"))
        self.assertFalse(thicken.get("afterSaleDays"))

    def test_t04_stores_and_api(self) -> None:
        from pathlib import Path

        repo = Path(__file__).resolve().parents[2]
        stores = [
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/capability/OrderStore.java",
            repo / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/OrderStore.java",
            repo / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/OrderStore.java",
        ]
        for path in stores:
            text = path.read_text(encoding="utf-8")
            self.assertIn("configureAfterSaleDays", text, path.name)
            self.assertIn("refundReasonSeries", text, path.name)
            self.assertIn("updateRefundTracking", text, path.name)
            self.assertIn("refundTrace", text, path.name)
            self.assertIn("String reason, String refundType", text, path.name)
        ctrl = (
            repo
            / "skeletons/baseline/backend/src/main/java/com/thesis/controller/OrderController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/orders/{id}/refund-tracking", ctrl)
        self.assertIn("/api/orders/{id}/refund-trace", ctrl)
        xml = (
            repo
            / "skeletons/overlays/persistence-mybatis/backend/src/main/resources/mapper/OrderMapper.xml"
        ).read_text(encoding="utf-8")
        self.assertIn("selectRefundReasonSeries", xml)
        fe = (
            repo / "skeletons/baseline/frontend/src/views/user/MyOrders.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("submitRefund", fe)
        self.assertIn("refund-tracking", fe)
        self.assertIn("refund-trace", fe)
        charts = (
            repo / "skeletons/baseline/frontend/src/components/DashboardCharts.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("refundReasonSeries", charts)
        self.assertIn("refundReasonCategories", charts)

    def test_shop_t05_exchange_and_ship(self) -> None:
        out = _spec("DOM-SHOP", "校园二手商城系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("tradeThicken") or {}
        labels = schema.get("labels") or {}
        self.assertTrue(thicken.get("refundExchange"))
        self.assertTrue(thicken.get("shipNodes"))
        self.assertTrue(thicken.get("partialShip"))
        self.assertTrue(thicken.get("orderShare"))
        self.assertTrue(thicken.get("receiveCode"))
        self.assertTrue(thicken.get("warranty"))
        for key in (
            "refundTypeExchange",
            "refundTypeExchangeOnly",
            "logisticsTraceLabel",
            "shipNodeLabel",
            "partialShipLabel",
            "orderShareLabel",
            "receiveCodeLabel",
            "receiveCodeVerifyLabel",
            "warrantyLabel",
        ):
            self.assertIn(key, labels)
        self.assertEqual(labels.get("logisticsTraceLabel"), "物流进度")
        baked = domain_sql(
            "DOM-SHOP",
            "db_test",
            capabilities=list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
            title="校园二手商城系统",
        )
        self.assertIn("order_ship_node", baked)
        for col in ("share_token", "warranty_until", "partial_ship", "receive_verified_at"):
            self.assertIn(col, baked)

    def test_food_t05_share_and_receive(self) -> None:
        out = _spec("DOM-FOOD", "校园点餐配送系统", "")
        thicken = (out.get("schema") or {}).get("tradeThicken") or {}
        self.assertTrue(thicken.get("orderShare"))
        self.assertTrue(thicken.get("receiveCode"))
        self.assertFalse(thicken.get("refundExchange"))
        self.assertFalse(thicken.get("shipNodes"))
        self.assertFalse(thicken.get("warranty"))
        baked = domain_sql(
            "DOM-FOOD",
            "db_test",
            capabilities=list(DOMAIN_CAPABILITIES["DOM-FOOD"]),
            title="校园点餐配送系统",
        )
        self.assertIn("share_token", baked)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS order_ship_node", baked)

    def test_cinema_t05_skips(self) -> None:
        out = _spec("DOM-CINEMA", "影院在线选座购票系统", "")
        thicken = (out.get("schema") or {}).get("tradeThicken") or {}
        self.assertFalse(thicken.get("refundExchange"))
        self.assertFalse(thicken.get("shipNodes"))
        self.assertFalse(thicken.get("orderShare"))
        self.assertFalse(thicken.get("receiveCode"))
        self.assertFalse(thicken.get("warranty"))

    def test_t05_stores_and_api(self) -> None:
        from pathlib import Path

        repo = Path(__file__).resolve().parents[2]
        stores = [
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/capability/OrderStore.java",
            repo / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/OrderStore.java",
            repo / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/OrderStore.java",
        ]
        for path in stores:
            text = path.read_text(encoding="utf-8")
            self.assertIn("ensureShareToken", text, path.name)
            self.assertIn("getOrderByShareToken", text, path.name)
            self.assertIn("addShipNode", text, path.name)
            self.assertIn("verifyReceiveCode", text, path.name)
            self.assertIn("updateWarranty", text, path.name)
            self.assertIn("exchange_only", text, path.name)
        ctrl = (
            repo
            / "skeletons/baseline/backend/src/main/java/com/thesis/controller/OrderController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/order-share/{token}", ctrl)
        self.assertIn("/api/orders/{id}/ship-nodes", ctrl)
        self.assertIn("/api/orders/{id}/verify-receive", ctrl)
        self.assertIn("/api/orders/{id}/warranty", ctrl)
        xml = (
            repo
            / "skeletons/overlays/persistence-mybatis/backend/src/main/resources/mapper/OrderMapper.xml"
        ).read_text(encoding="utf-8")
        self.assertIn("selectOrderByShareToken", xml)
        self.assertIn("insertShipNode", xml)
        fe_user = (repo / "skeletons/baseline/frontend/src/views/user/MyOrders.vue").read_text(
            encoding="utf-8"
        )
        fe_admin = (repo / "skeletons/baseline/frontend/src/views/admin/OrdersAdmin.vue").read_text(
            encoding="utf-8"
        )
        fe_login = (repo / "skeletons/baseline/frontend/src/views/Login.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("refundTypeExchange", fe_user)
        self.assertIn("copyShareToken", fe_user)
        self.assertIn("submitWarranty", fe_user)
        self.assertIn("submitShipNode", fe_admin)
        self.assertIn("verify-receive", fe_admin)
        self.assertIn("partialShip", fe_admin)
        self.assertIn("order-share", fe_login)

    def test_cinema_t06a(self) -> None:
        out = _spec("DOM-CINEMA", "影院在线选座购票系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("tradeThicken") or {}
        labels = schema.get("labels") or {}
        self.assertTrue(thicken.get("ticketRefundCutoff"))
        self.assertTrue(thicken.get("seatHoldTimeout"))
        self.assertTrue(thicken.get("adjacentSeatHint"))
        self.assertTrue(thicken.get("showSoldOut"))
        self.assertTrue(thicken.get("cinemaNotice"))
        self.assertEqual(int(schema.get("ticketRefundCutoffMinutes") or 0), 30)
        self.assertEqual(int(schema.get("seatHoldTimeoutMinutes") or 0), 10)
        for key in (
            "ticketRefundCutoffHint",
            "cinemaRefundLabel",
            "seatHoldTimeoutHint",
            "adjacentSeatHintTitle",
            "adjacentSeatHintEmpty",
            "showSoldOutLabel",
            "showSoldOutHint",
            "cinemaNoticeLabel",
            "cinemaNoticeBody",
            "cinemaNoticeRequiredHint",
        ):
            self.assertIn(key, labels)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-CINEMA", out)
        self.assertIn("ticket-refund-cutoff-minutes:", yml)
        self.assertIn("seat-hold-timeout-minutes:", yml)
        shop = _spec("DOM-SHOP", "校园二手商城系统", "")
        shop_t = (shop.get("schema") or {}).get("tradeThicken") or {}
        self.assertFalse(shop_t.get("ticketRefundCutoff"))
        self.assertFalse(shop_t.get("cinemaNotice"))
        sql = (
            "CREATE TABLE IF NOT EXISTS cinema_seat (\n"
            "  id BIGINT PRIMARY KEY AUTO_INCREMENT,\n"
            "  show_id BIGINT NOT NULL,\n"
            "  seat_code VARCHAR(16) NOT NULL,\n"
            "  status VARCHAR(16) NOT NULL DEFAULT 'free'\n"
            ");\n"
            "CREATE TABLE IF NOT EXISTS biz_order (\n"
            "  id BIGINT PRIMARY KEY AUTO_INCREMENT,\n"
            "  username VARCHAR(64) NOT NULL\n"
            ");\n"
        )
        out_sql = ensure_cinema_thicken_sql(sql, domain="DOM-CINEMA", order_table="biz_order")
        self.assertIn("hold_until", out_sql)
        self.assertIn("notice_agreed", out_sql)
        skip = ensure_cinema_thicken_sql(sql, domain="DOM-SHOP", order_table="biz_order")
        self.assertNotIn("hold_until", skip)
        baked = domain_sql(
            "DOM-CINEMA",
            "db_test",
            capabilities=list(DOMAIN_CAPABILITIES["DOM-CINEMA"]),
            title="影院在线选座购票系统",
        )
        self.assertIn("hold_until", baked)
        self.assertIn("notice_agreed", baked)

    def test_t06a_stores_and_api(self) -> None:
        from pathlib import Path

        repo = Path(__file__).resolve().parents[2]
        seats = [
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/service/SeatStore.java",
            repo / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/service/SeatStore.java",
            repo / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/service/SeatStore.java",
        ]
        for path in seats:
            text = path.read_text(encoding="utf-8")
            self.assertIn("holdSeats", text, path.name)
            self.assertIn("releaseExpiredHolds", text, path.name)
            self.assertIn("syncShowSaleStatus", text, path.name)
            self.assertIn("assertOrderRefundOpen", text, path.name)
            self.assertIn("noticeAgreed", text, path.name)
        stores = [
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/capability/OrderStore.java",
            repo / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/OrderStore.java",
            repo / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/OrderStore.java",
        ]
        for path in stores:
            text = path.read_text(encoding="utf-8")
            self.assertIn("markNoticeAgreed", text, path.name)
        ctrl = (
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/controller/SeatController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("/hold", ctrl)
        self.assertIn("noticeAgreed", ctrl)
        jobs = (
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/config/DemoScheduleJobs.java"
        ).read_text(encoding="utf-8")
        self.assertIn("releaseExpiredHolds", jobs)
        fe_map = (repo / "skeletons/baseline/frontend/src/views/SeatMap.vue").read_text(
            encoding="utf-8"
        )
        fe_shows = (repo / "skeletons/baseline/frontend/src/views/SeatShows.vue").read_text(
            encoding="utf-8"
        )
        fe_orders = (repo / "skeletons/baseline/frontend/src/views/user/MyOrders.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("cinemaNoticeLabel", fe_map)
        self.assertIn("/api/seats/hold", fe_map)
        self.assertIn("adjacentSeatHintTitle", fe_map)
        self.assertIn("seatHoldTimeoutHint", fe_map)
        self.assertIn("showSoldOutLabel", fe_shows)
        self.assertIn("cinemaRefundLabel", fe_orders)
        self.assertIn("ticketRefundCutoffHint", fe_orders)

    def test_cinema_t06b(self) -> None:
        out = _spec("DOM-CINEMA", "影院在线选座购票系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("tradeThicken") or {}
        labels = schema.get("labels") or {}
        for key in ("seatAttrs", "effectHall", "refundFee", "showWeekView", "cinemaCombo"):
            self.assertTrue(thicken.get(key), key)
        for key in (
            "seatAttrCoupleLabel",
            "seatAttrAccessibleLabel",
            "seatAttrLegendLabel",
            "seatAttrEditLabel",
            "effectHallLabel",
            "effectHallImax",
            "refundFeeLabel",
            "refundFeeHint",
            "showWeekViewLabel",
            "showWeekViewEmpty",
            "cinemaComboLabel",
            "cinemaComboBody",
        ):
            self.assertIn(key, labels)
        shop = _spec("DOM-SHOP", "校园二手商城系统", "")
        shop_t = (shop.get("schema") or {}).get("tradeThicken") or {}
        self.assertFalse(shop_t.get("seatAttrs"))
        self.assertFalse(shop_t.get("refundFee"))
        sql = (
            "CREATE TABLE IF NOT EXISTS cinema_seat (\n"
            "  id BIGINT PRIMARY KEY AUTO_INCREMENT,\n"
            "  show_id BIGINT NOT NULL,\n"
            "  seat_code VARCHAR(16) NOT NULL,\n"
            "  status VARCHAR(16) NOT NULL DEFAULT 'free'\n"
            ");\n"
            "CREATE TABLE IF NOT EXISTS biz_order (\n"
            "  id BIGINT PRIMARY KEY AUTO_INCREMENT,\n"
            "  username VARCHAR(64) NOT NULL\n"
            ");\n"
        )
        out_sql = ensure_cinema_thicken_sql(sql, domain="DOM-CINEMA", order_table="biz_order")
        self.assertIn("seat_attr", out_sql)
        self.assertIn("refund_fee_yuan", out_sql)
        baked = domain_sql(
            "DOM-CINEMA",
            "db_test",
            capabilities=list(DOMAIN_CAPABILITIES["DOM-CINEMA"]),
            title="影院在线选座购票系统",
        )
        self.assertIn("seat_attr", baked)
        self.assertIn("refund_fee_yuan", baked)

    def test_t06b_stores_and_api(self) -> None:
        from pathlib import Path

        repo = Path(__file__).resolve().parents[2]
        seats = [
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/service/SeatStore.java",
            repo / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/service/SeatStore.java",
            repo / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/service/SeatStore.java",
        ]
        for path in seats:
            text = path.read_text(encoding="utf-8")
            self.assertIn("updateSeatAttrs", text, path.name)
            self.assertIn("seatAttr", text, path.name)
            self.assertIn("categoryName", text, path.name)
        stores = [
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/capability/OrderStore.java",
            repo / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/OrderStore.java",
            repo / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/OrderStore.java",
        ]
        for path in stores:
            text = path.read_text(encoding="utf-8")
            self.assertIn("updateRefundFee", text, path.name)
            self.assertIn("refundFeeYuan", text, path.name)
        seat_ctrl = (
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/controller/SeatController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("/attrs", seat_ctrl)
        order_ctrl = (
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/controller/OrderController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("refund-fee", order_ctrl)
        fe_map = (repo / "skeletons/baseline/frontend/src/views/SeatMap.vue").read_text(
            encoding="utf-8"
        )
        fe_shows = (repo / "skeletons/baseline/frontend/src/views/SeatShows.vue").read_text(
            encoding="utf-8"
        )
        fe_admin = (repo / "skeletons/baseline/frontend/src/views/admin/ArchiveAdmin.vue").read_text(
            encoding="utf-8"
        )
        fe_orders = (repo / "skeletons/baseline/frontend/src/views/admin/OrdersAdmin.vue").read_text(
            encoding="utf-8"
        )
        fe_my = (repo / "skeletons/baseline/frontend/src/views/user/MyOrders.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("seatAttrCoupleLabel", fe_map)
        self.assertIn("cinemaComboBody", fe_map)
        self.assertIn("effectHallLabel", fe_map)
        self.assertIn("showWeekViewLabel", fe_shows)
        self.assertIn("cinemaComboBody", fe_shows)
        self.assertIn("effectHallLabel", fe_shows)
        self.assertIn("seatAttrEditLabel", fe_admin)
        self.assertIn("/api/seats/shows/", fe_admin)
        self.assertIn("refundFeeLabel", fe_orders)
        self.assertIn("refund-fee", fe_orders)
        self.assertIn("refundFeeLabel", fe_my)
        self.assertIn("refund-fee", fe_my)

    def test_t07_food_thicken_schema_and_sql(self) -> None:
        out = _spec("DOM-FOOD", "校园点餐配送系统", "骑手配送到宿舍楼")
        schema = out.get("schema") or {}
        thicken = schema.get("tradeThicken") or {}
        labels = schema.get("labels") or {}
        for key in (
            "tableNo",
            "pickupNo",
            "utensilPack",
            "packagingFee",
            "stallOpenHours",
            "deliveryFeeLadder",
            "etaText",
            "requiredCategory",
            "tableMerge",
            "stallScoreSort",
            "riderPool",
        ):
            self.assertTrue(thicken.get(key), key)
        for key in (
            "tableNoLabel",
            "tableNoHint",
            "pickupNoLabel",
            "pickupNoHint",
            "utensilOptLabel",
            "packOptLabel",
            "packagingFeeLabel",
            "packagingFeeHint",
            "stallOpenHoursLabel",
            "stallOpenHoursHint",
            "stallClosedHint",
            "deliveryFeeLabel",
            "deliveryFeeLadderBody",
            "etaLabel",
            "etaHint",
            "requiredCategoryLabel",
            "requiredCategoryHint",
            "requiredCategoryMissingHint",
            "mergeCodeLabel",
            "mergeCodeHint",
            "stallScoreLabel",
            "stallScoreHint",
            "riderClaimLabel",
            "riderClaimTimeoutHint",
        ):
            self.assertIn(key, labels)
        self.assertGreater(float(schema.get("packagingFeeYuan") or 0), 0)
        self.assertGreater(float(schema.get("deliveryFeeBaseYuan") or 0), 0)
        self.assertGreater(int(schema.get("etaMinutes") or 0), 0)
        self.assertGreaterEqual(int(schema.get("riderClaimTimeoutMinutes") or 0), 1)
        archive = (schema.get("entities") or {}).get("archive") or {}
        fields = {str(f.get("key")) for f in (archive.get("fields") or []) if isinstance(f, dict)}
        self.assertIn("openHours", fields)
        self.assertIn("stallScore", fields)
        order = (schema.get("entities") or {}).get("order") or {}
        self.assertGreaterEqual(len(order.get("utensilOpts") or []), 1)
        self.assertGreaterEqual(len(order.get("packOpts") or []), 1)

        sql = (
            "CREATE TABLE IF NOT EXISTS biz_order (\n"
            "  id BIGINT PRIMARY KEY AUTO_INCREMENT,\n"
            "  username VARCHAR(64) NOT NULL\n"
            ");\n"
            "CREATE TABLE IF NOT EXISTS dish (\n"
            "  id BIGINT PRIMARY KEY AUTO_INCREMENT,\n"
            "  title VARCHAR(128) NOT NULL\n"
            ");\n"
            "CREATE TABLE IF NOT EXISTS category (\n"
            "  id BIGINT PRIMARY KEY AUTO_INCREMENT,\n"
            "  name VARCHAR(64) NOT NULL\n"
            ");\n"
        )
        out_sql = ensure_food_thicken_sql(
            sql, domain="DOM-FOOD", order_table="biz_order", item_table="dish"
        )
        for col in (
            "table_no",
            "utensil_opt",
            "pack_opt",
            "packaging_fee_yuan",
            "delivery_fee_yuan",
            "eta_text",
            "merge_code",
            "stall_score",
            "open_hours",
            "required_pick",
        ):
            self.assertIn(col, out_sql)
        baked = domain_sql(
            "DOM-FOOD",
            "db_test",
            capabilities=list(DOMAIN_CAPABILITIES["DOM-FOOD"]),
            title="校园点餐配送系统",
        )
        self.assertIn("table_no", baked)
        self.assertIn("stall_score", baked)
        self.assertIn("required_pick", baked)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-FOOD", out)
        self.assertIn("packaging-fee-yuan:", yml)
        self.assertIn("rider-claim-timeout-minutes:", yml)

        no_rider = _spec("DOM-FOOD", "食堂堂食点餐系统", "仅支持堂食到店自取")
        self.assertFalse((no_rider.get("schema") or {}).get("tradeThicken", {}).get("riderPool"))

    def test_t07_stores_and_api(self) -> None:
        from pathlib import Path

        repo = Path(__file__).resolve().parents[2]
        stores = [
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/capability/OrderStore.java",
            repo / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/OrderStore.java",
            repo / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/OrderStore.java",
        ]
        for path in stores:
            text = path.read_text(encoding="utf-8")
            self.assertIn("configureFoodFees", text, path.name)
            self.assertIn("claimRider", text, path.name)
            self.assertIn("releaseTimedOutRiderClaims", text, path.name)
            self.assertIn("assertStallOpenForCart", text, path.name)
            self.assertIn("assertRequiredCategoryInCart", text, path.name)
            self.assertIn("PLACE_EXTRAS", text, path.name)
        archives = [
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/capability/ArchiveStore.java",
            repo / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/ArchiveStore.java",
            repo / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/ArchiveStore.java",
        ]
        for path in archives:
            text = path.read_text(encoding="utf-8")
            self.assertIn("requiredPick", text, path.name)
            self.assertIn("stallScore", text, path.name)
            self.assertIn("openHours", text, path.name)
        order_ctrl = (
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/controller/OrderController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("claimRider", order_ctrl)
        self.assertIn("tableNo", order_ctrl)
        cat_ctrl = (
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/controller/CategoryController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("requiredPick", cat_ctrl)
        demo = (
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/config/DemoScheduleJobs.java"
        ).read_text(encoding="utf-8")
        self.assertIn("releaseTimedOutRiderClaims", demo)
        fe_cart = (repo / "skeletons/baseline/frontend/src/views/user/Cart.vue").read_text(
            encoding="utf-8"
        )
        fe_my = (repo / "skeletons/baseline/frontend/src/views/user/MyOrders.vue").read_text(
            encoding="utf-8"
        )
        fe_orders = (repo / "skeletons/baseline/frontend/src/views/admin/OrdersAdmin.vue").read_text(
            encoding="utf-8"
        )
        fe_cat = (repo / "skeletons/baseline/frontend/src/views/admin/CategoriesAdmin.vue").read_text(
            encoding="utf-8"
        )
        fe_staff = (repo / "skeletons/baseline/frontend/src/views/staff/StaffOrders.vue").read_text(
            encoding="utf-8"
        )
        fe_print = (repo / "skeletons/baseline/frontend/src/utils/orderReceiptPrint.js").read_text(
            encoding="utf-8"
        )
        for needle in (
            "tableNoLabel",
            "utensilOptLabel",
            "packOptLabel",
            "packagingFeeLabel",
            "mergeCodeLabel",
            "stallClosedHint",
            "deliveryFeeLadderBody",
            "requiredCategoryMissingHint",
        ):
            self.assertIn(needle, fe_cart, needle)
        self.assertIn("pickupNoLabel", fe_my)
        self.assertIn("etaLabel", fe_my)
        self.assertIn("riderClaimLabel", fe_orders)
        self.assertIn("/claim", fe_orders)
        self.assertIn("requiredCategoryLabel", fe_cat)
        self.assertIn("requiredPick", fe_cat)
        self.assertIn("riderClaimTimeoutHint", fe_staff)
        self.assertIn("tableNo", fe_print)
        self.assertIn("mergeCode", fe_print)

    def test_t08_invoice_and_rule_copy(self) -> None:
        from pathlib import Path

        caps = list(DOMAIN_CAPABILITIES["DOM-SHOP"]) + [
            "spend_discount",
            "coupon",
            "member_tier",
        ]
        out = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "校园二手商城系统",
                "capabilities": caps,
                "features": [],
                "archetype": "ARCH-TRADE",
            },
            "满减优惠券会员日折扣",
        )
        schema = out.get("schema") or {}
        thicken = schema.get("tradeThicken") or {}
        labels = schema.get("labels") or {}
        for key in (
            "invoiceTitle",
            "invoiceStatus",
            "invoicePdf",
            "giftPromo",
            "refundOrigin",
            "spendDiscountHelp",
            "couponMutex",
            "memberDay",
        ):
            self.assertTrue(thicken.get(key), key)
        for key in (
            "invoiceTitleLabel",
            "invoiceTitleHint",
            "invoiceStatusLabel",
            "invoiceStatusPending",
            "invoiceStatusIssued",
            "invoiceRequestLabel",
            "invoiceIssueLabel",
            "invoiceDownloadLabel",
            "invoiceDownloadHint",
            "giftPromoLabel",
            "giftPromoBody",
            "spendDiscountHelpLabel",
            "spendDiscountHelpBody",
            "couponMutexLabel",
            "couponMutexBody",
            "refundOriginLabel",
            "refundOriginHint",
            "memberDayLabel",
            "memberDayHint",
        ):
            self.assertIn(key, labels)
        food = _spec("DOM-FOOD", "校园点餐配送系统", "")
        self.assertTrue((food.get("schema") or {}).get("tradeThicken", {}).get("refundOrigin"))
        self.assertFalse((food.get("schema") or {}).get("tradeThicken", {}).get("invoiceTitle"))

        baked = domain_sql(
            "DOM-SHOP",
            "db_test",
            capabilities=caps,
            title="校园二手商城系统",
        )
        self.assertIn("invoice_title", baked)
        self.assertIn("invoice_status", baked)

        repo = Path(__file__).resolve().parents[2]
        stores = [
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/capability/OrderStore.java",
            repo / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/OrderStore.java",
            repo / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/OrderStore.java",
        ]
        for path in stores:
            text = path.read_text(encoding="utf-8")
            self.assertIn("updateInvoice", text, path.name)
            self.assertIn("invoiceTitle", text, path.name)
        ctrl = (
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/controller/OrderController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("/invoice", ctrl)
        fe_cart = (repo / "skeletons/baseline/frontend/src/views/user/Cart.vue").read_text(
            encoding="utf-8"
        )
        fe_my = (repo / "skeletons/baseline/frontend/src/views/user/MyOrders.vue").read_text(
            encoding="utf-8"
        )
        fe_orders = (repo / "skeletons/baseline/frontend/src/views/admin/OrdersAdmin.vue").read_text(
            encoding="utf-8"
        )
        fe_inv = (repo / "skeletons/baseline/frontend/src/utils/orderInvoicePrint.js").read_text(
            encoding="utf-8"
        )
        for needle in (
            "invoiceTitleLabel",
            "spendDiscountHelpBody",
            "giftPromoBody",
            "couponMutexBody",
            "memberDayHint",
        ):
            self.assertIn(needle, fe_cart, needle)
        self.assertIn("refundOriginHint", fe_my)
        self.assertIn("invoiceRequestLabel", fe_my)
        self.assertIn("invoiceIssueLabel", fe_orders)
        self.assertIn("/invoice", fe_my)
        self.assertIn("/invoice", fe_orders)
        self.assertIn("printOrderInvoice", fe_inv)

    def test_t09_catalog_side(self) -> None:
        from pathlib import Path

        out = _spec("DOM-SHOP", "校园二手商城系统", "")
        schema = out.get("schema") or {}
        thicken = schema.get("tradeThicken") or {}
        labels = schema.get("labels") or {}
        caps = schema.get("capabilities") or []
        for key in (
            "shelfSchedule",
            "goodRate",
            "stockNotify",
            "presaleNote",
            "specStock",
            "itemQa",
            "browseHistory",
            "reviewImage",
            "reviewFollow",
        ):
            self.assertTrue(thicken.get(key), key)
        self.assertIn("browse_history", caps)
        for key in (
            "shelfOnLabel",
            "shelfOffLabel",
            "goodRateLabel",
            "stockNotifyLabel",
            "presaleNoteLabel",
            "specStockLabel",
            "itemQaLabel",
            "reviewImageLabel",
            "reviewFollowLabel",
        ):
            self.assertIn(key, labels)
        archive = (schema.get("entities") or {}).get("archive") or {}
        field_keys = {f.get("key") for f in (archive.get("fields") or []) if isinstance(f, dict)}
        self.assertIn("shelfOn", field_keys)
        self.assertIn("shelfOff", field_keys)
        self.assertIn("presaleNote", field_keys)

        food = _spec("DOM-FOOD", "校园点餐配送系统", "")
        ft = (food.get("schema") or {}).get("tradeThicken") or {}
        self.assertTrue(ft.get("shelfSchedule"))
        self.assertTrue(ft.get("goodRate"))
        self.assertFalse(ft.get("stockNotify"))
        self.assertFalse(ft.get("presaleNote"))

        baked = domain_sql(
            "DOM-SHOP",
            "db_test",
            capabilities=list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
            title="校园二手商城系统",
        )
        for needle in (
            "shelf_on",
            "shelf_off",
            "presale_note",
            "stock_notify",
            "follow_body",
            "image_url",
        ):
            self.assertIn(needle, baked, needle)
        inj = ensure_catalog_thicken_sql(
            "CREATE TABLE IF NOT EXISTS shop_item (id BIGINT PRIMARY KEY);\n"
            "CREATE TABLE IF NOT EXISTS order_review (id BIGINT PRIMARY KEY);\n"
            "CREATE TABLE IF NOT EXISTS sys_guestbook (id BIGINT PRIMARY KEY);\n",
            domain="DOM-SHOP",
            item_table="shop_item",
        )
        self.assertIn("shelf_on", inj)
        self.assertIn("stock_notify", inj)
        self.assertIn("follow_body", inj)
        self.assertIn("item_id", inj)

        repo = Path(__file__).resolve().parents[2]
        for rel in (
            "skeletons/baseline/backend/src/main/java/com/thesis/capability/StockNotifyStore.java",
            "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/StockNotifyStore.java",
            "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/StockNotifyStore.java",
        ):
            text = (repo / rel).read_text(encoding="utf-8")
            self.assertIn("notifyRestock", text, rel)
            self.assertIn("subscribe", text, rel)
        for rel in (
            "skeletons/baseline/backend/src/main/java/com/thesis/capability/ArchiveStore.java",
            "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/ArchiveStore.java",
            "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/ArchiveStore.java",
        ):
            text = (repo / rel).read_text(encoding="utf-8")
            self.assertIn("applyShelfSchedule", text, rel)
            self.assertIn("listSiblingSpecStock", text, rel)
        for rel in (
            "skeletons/baseline/backend/src/main/java/com/thesis/capability/OrderReviewStore.java",
            "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/OrderReviewStore.java",
            "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/OrderReviewStore.java",
        ):
            text = (repo / rel).read_text(encoding="utf-8")
            self.assertIn("follow", text, rel)
            self.assertIn("goodRate", text, rel)
            self.assertIn("imageUrl", text, rel)
        ctrl = (
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/controller/StockNotifyController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/stock-notify", ctrl)
        fe_browse = (
            repo / "skeletons/baseline/frontend/src/views/user/ArchiveBrowse.vue"
        ).read_text(encoding="utf-8")
        fe_my = (
            repo / "skeletons/baseline/frontend/src/views/user/MyOrders.vue"
        ).read_text(encoding="utf-8")
        fe_rev = (
            repo / "skeletons/baseline/frontend/src/views/user/MyOrderReviews.vue"
        ).read_text(encoding="utf-8")
        for needle in (
            "stockNotifyLabel",
            "goodRateLabel",
            "itemQaLabel",
            "specStockLabel",
            "presaleNote",
            "/api/stock-notify",
        ):
            self.assertIn(needle, fe_browse, needle)
        self.assertIn("reviewImage", fe_my)
        self.assertIn("imageUrl", fe_my)
        self.assertIn("reviewFollow", fe_rev)
        self.assertIn("/follow", fe_rev)

    def test_t10_capability_islands(self) -> None:
        from pathlib import Path

        caps = list(DOMAIN_CAPABILITIES["DOM-SHOP"]) + [
            "coupon",
            "group_buy",
            "flash_price",
            "blind_box",
            "points",
            "member_tier",
        ]
        out = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "校园二手商城系统",
                "capabilities": caps,
                "features": [],
                "archetype": "ARCH-TRADE",
            },
            "优惠券拼团限时购盲盒积分会员",
        )
        schema = out.get("schema") or {}
        thicken = schema.get("tradeThicken") or {}
        labels = schema.get("labels") or {}
        for key in (
            "couponRedeemCode",
            "couponClaimCenter",
            "couponExpireNotify",
            "groupBuyProgress",
            "groupBuyFailRefund",
            "flashCountdown",
            "blindDraws",
            "pointsLedger",
            "pointsFreight",
        ):
            self.assertTrue(thicken.get(key), key)
        for key in (
            "couponRedeemCodeLabel",
            "couponClaimCenterTitle",
            "couponExpireNotifyBody",
            "groupBuyProgressLabel",
            "groupBuyFailRefundHint",
            "flashCountdownLabel",
            "blindDrawsPageTitle",
            "pointsLedgerPageTitle",
            "pointsFreightHint",
        ):
            self.assertIn(key, labels)
        menus = ((schema.get("menus") or {}).get("user") or [])
        menu_keys = {m.get("key") for m in menus if isinstance(m, dict)}
        self.assertIn("blind_draws", menu_keys)
        self.assertIn("points_ledger", menu_keys)

        cinema = attach_accept(
            {
                "domain": "DOM-CINEMA",
                "title": "影院选座购票系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-CINEMA"]) + ["points", "member_tier"],
                "features": [],
                "archetype": "ARCH-TRADE",
            },
            "积分会员",
        )
        ct = (cinema.get("schema") or {}).get("tradeThicken") or {}
        cl = (cinema.get("schema") or {}).get("labels") or {}
        self.assertTrue(ct.get("cinemaPointsTicket"))
        self.assertTrue(ct.get("cinemaMemberPrice"))
        self.assertIn("cinemaPointsTicketHint", cl)
        self.assertIn("cinemaMemberPriceHint", cl)

        repo = Path(__file__).resolve().parents[2]
        for rel in (
            "skeletons/baseline/backend/src/main/java/com/thesis/capability/CouponStore.java",
            "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/CouponStore.java",
            "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/CouponStore.java",
        ):
            text = (repo / rel).read_text(encoding="utf-8")
            self.assertIn("MessageStore.send", text, rel)
        for rel in (
            "skeletons/baseline/backend/src/main/java/com/thesis/capability/GroupBuyStore.java",
            "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/GroupBuyStore.java",
            "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/GroupBuyStore.java",
        ):
            self.assertIn(
                "progressForOrder",
                (repo / rel).read_text(encoding="utf-8"),
                rel,
            )
        for rel in (
            "skeletons/baseline/backend/src/main/java/com/thesis/capability/BlindBoxStore.java",
            "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/BlindBoxStore.java",
            "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/BlindBoxStore.java",
        ):
            self.assertIn("listMyDraws", (repo / rel).read_text(encoding="utf-8"), rel)
        ctrl = (
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/controller/BlindBoxController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("/draws", ctrl)
        fe_files = {
            "my": (repo / "skeletons/baseline/frontend/src/views/user/MyOrders.vue").read_text(
                encoding="utf-8"
            ),
            "coupons": (repo / "skeletons/baseline/frontend/src/views/user/MyCoupons.vue").read_text(
                encoding="utf-8"
            ),
            "browse": (repo / "skeletons/baseline/frontend/src/views/user/ArchiveBrowse.vue").read_text(
                encoding="utf-8"
            ),
            "draws": (repo / "skeletons/baseline/frontend/src/views/user/MyBlindDraws.vue").read_text(
                encoding="utf-8"
            ),
            "ledger": (repo / "skeletons/baseline/frontend/src/views/user/PointsLedger.vue").read_text(
                encoding="utf-8"
            ),
            "seat": (repo / "skeletons/baseline/frontend/src/views/SeatMap.vue").read_text(encoding="utf-8"),
            "cart": (repo / "skeletons/baseline/frontend/src/views/user/Cart.vue").read_text(
                encoding="utf-8"
            ),
            "router": (repo / "skeletons/baseline/frontend/src/router/index.js").read_text(
                encoding="utf-8"
            ),
        }
        self.assertIn("couponRedeemCodeLabel", fe_files["my"])
        self.assertIn("groupBuyProgress", fe_files["my"])
        self.assertIn("groupBuyFailRefundHint", fe_files["my"])
        self.assertIn("couponClaimCenterTitle", fe_files["coupons"])
        self.assertIn("flashCountdownLabel", fe_files["browse"])
        self.assertIn("blindDrawsPageTitle", fe_files["draws"])
        self.assertIn("/api/blind-boxes/draws", fe_files["draws"])
        self.assertIn("pointsLedgerPageTitle", fe_files["ledger"])
        self.assertIn("pointsFreightHint", fe_files["ledger"])
        self.assertIn("pointsFreightHint", fe_files["cart"])
        self.assertIn("cinemaMemberPriceHint", fe_files["seat"])
        self.assertIn("cinemaPointsTicketHint", fe_files["seat"])
        self.assertIn("blind-draws", fe_files["router"])
        self.assertIn("points-ledger", fe_files["router"])

    def test_t11_cinema_snack_and_shop_packaging(self) -> None:
        from pathlib import Path

        cinema = _spec("DOM-CINEMA", "影院在线选座购票系统", "")
        ct = (cinema.get("schema") or {}).get("tradeThicken") or {}
        cl = (cinema.get("schema") or {}).get("labels") or {}
        self.assertTrue(ct.get("cinemaSnack"))
        self.assertTrue(ct.get("cinemaSnackStock"))
        for key in (
            "cinemaSnackLabel",
            "cinemaSnackHint",
            "cinemaSnackEmpty",
            "cinemaSnackStockHint",
            "cinemaSnackSoldOutLabel",
            "cinemaSnackSaveLabel",
        ):
            self.assertIn(key, cl)
        shop = _spec("DOM-SHOP", "校园二手商城系统", "")
        st = (shop.get("schema") or {}).get("tradeThicken") or {}
        sl = (shop.get("schema") or {}).get("labels") or {}
        self.assertTrue(st.get("packagingFee"))
        self.assertIn("packagingFeeLabel", sl)
        self.assertGreater(float((shop.get("schema") or {}).get("packagingFeeYuan") or 0), 0)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-SHOP", shop)
        self.assertIn("packaging-fee-yuan:", yml)
        sql = (
            "CREATE TABLE IF NOT EXISTS order_line (\n"
            "  id BIGINT PRIMARY KEY AUTO_INCREMENT,\n"
            "  order_id BIGINT NOT NULL,\n"
            "  item_id BIGINT NOT NULL,\n"
            "  title VARCHAR(200) NOT NULL,\n"
            "  price_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,\n"
            "  qty INT NOT NULL DEFAULT 1\n"
            ");\n"
        )
        out_sql = ensure_cinema_thicken_sql(sql, domain="DOM-CINEMA", order_table="biz_order")
        self.assertIn("cinema_snack", out_sql)
        self.assertIn("line_kind", out_sql)
        self.assertIn("爆米花", out_sql)
        baked = domain_sql(
            "DOM-CINEMA",
            "db_test",
            capabilities=list(DOMAIN_CAPABILITIES["DOM-CINEMA"]),
            title="影院在线选座购票系统",
        )
        self.assertIn("cinema_snack", baked)
        self.assertIn("line_kind", baked)
        shop_sql = domain_sql(
            "DOM-SHOP",
            "db_test",
            capabilities=list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
            title="校园二手商城系统",
        )
        self.assertIn("packaging_fee_yuan", shop_sql)

        repo = Path(__file__).resolve().parents[2]
        for rel in (
            "skeletons/baseline/backend/src/main/java/com/thesis/service/SeatStore.java",
            "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/service/SeatStore.java",
            "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/service/SeatStore.java",
        ):
            text = (repo / rel).read_text(encoding="utf-8")
            self.assertIn("snackReady", text, rel)
            self.assertIn("listOpenSnacks", text, rel)
            self.assertIn("adjustSnackStock", text, rel)
            self.assertIn("attachCinemaSnacks", text, rel)
        for rel in (
            "skeletons/baseline/backend/src/main/java/com/thesis/capability/OrderStore.java",
            "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/OrderStore.java",
            "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/OrderStore.java",
        ):
            text = (repo / rel).read_text(encoding="utf-8")
            self.assertIn("attachCinemaSnacks", text, rel)
            self.assertIn("restoreSnackStockForOrder", text, rel)
            self.assertIn("lineKind", text, rel)
        ctrl = (
            repo / "skeletons/baseline/backend/src/main/java/com/thesis/controller/SeatController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("/snacks", ctrl)
        self.assertIn("parseSnacks", ctrl)
        fe_seat = (repo / "skeletons/baseline/frontend/src/views/SeatMap.vue").read_text(encoding="utf-8")
        fe_admin = (repo / "skeletons/baseline/frontend/src/views/admin/ArchiveAdmin.vue").read_text(
            encoding="utf-8"
        )
        fe_cart = (repo / "skeletons/baseline/frontend/src/views/user/Cart.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("cinemaSnackLabel", fe_seat)
        self.assertIn("/api/seats/snacks", fe_seat)
        self.assertIn("snacks:", fe_seat)
        self.assertIn("cinemaSnackOn", fe_admin)
        self.assertIn("/api/seats/snacks/all", fe_admin)
        self.assertIn("!isFood && packagingFeeOn", fe_cart)


if __name__ == "__main__":
    unittest.main()
