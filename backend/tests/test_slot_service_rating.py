"""预约服务评价：补齐 Binder / API / 我的预约；美业/医院/酒店/租车默认开。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.domain_schema import attach_accept, build_domain_schema
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from tests.helpers.normalize import normalize_sql

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class SlotServiceRatingTests(unittest.TestCase):
    def test_salon_hotel_carrent_hospital_allow_rating(self) -> None:
        for dom, title, body in (
            ("DOM-SALON", "美发预约系统", "技师排班时段预约"),
            ("DOM-HOTEL", "酒店客房预订", "选房入住离店"),
            ("DOM-CARRENT", "汽车租赁系统", "选车取还车"),
            ("DOM-HOSPITAL", "门诊预约挂号", "分时挂号就诊"),
        ):
            schema = build_domain_schema(title, dom, proposal_text=body)
            resv = (schema.get("entities") or {}).get("reservation") or {}
            self.assertTrue(resv.get("allowRating"), dom)

    def test_meeting_default_no_rating(self) -> None:
        schema = build_domain_schema("会议室预约", "DOM-MEETING", proposal_text="会议室时段预约")
        resv = (schema.get("entities") or {}).get("reservation") or {}
        self.assertFalse(bool(resv.get("allowRating")))

    def test_yml_and_sql_when_allow_rating(self) -> None:
        out = attach_accept(
            {
                "domain": "DOM-SALON",
                "title": "美发预约",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SALON"]),
                "schema": {},
            },
            "美发美容技师预约到店服务",
        )
        resv = ((out.get("schema") or {}).get("entities") or {}).get("reservation") or {}
        self.assertTrue(resv.get("allowRating"))
        yml = _patch_thesis_yml("thesis:\n  domain: DOM-SALON\n", "DOM-SALON", out)
        self.assertIn("slot-allow-rating: true", yml)
        sql = domain_sql(
            "DOM-SALON",
            "thesis_salon",
            title="美发预约",
            proposal_text="美发美容技师预约",
            capabilities=list(out.get("capabilities") or []),
            reservation_flags=resv,
        )
        n = normalize_sql(sql)
        self.assertIn("rating", n)
        self.assertIn("rating_remark", n)
        self.assertIn("rated_at", n)

    def test_runtime_wired(self) -> None:
        ctrl = (
            BASELINE / "backend/src/main/java/com/thesis/controller/SlotController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("/reservations/{id}/rate", ctrl)
        self.assertIn("SlotStore.rate", ctrl)

        binder = (
            BASELINE / "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java"
        ).read_text(encoding="utf-8")
        self.assertIn("slot-allow-rating", binder)
        self.assertIn("configureRating", binder)

        store = (
            BASELINE / "backend/src/main/java/com/thesis/capability/SlotStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("configureRating", store)
        self.assertIn("public static Map<String, Object> rate(", store)

        mine = (BASELINE / "frontend/src/views/user/MyReservations.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("canRate", mine)
        self.assertIn("/api/slots/reservations/${rateId.value}/rate", mine)
        self.assertIn("allowRating", mine)

        admin = (BASELINE / "frontend/src/views/admin/ReservationsAdmin.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("allowRating", admin)
        self.assertIn("ratingRemark", admin)

    def test_ticket_repair_still_allow_rating(self) -> None:
        """报修行办结评价此前已齐：回归别弄丢。"""
        for dom, title in (
            ("DOM-DORM", "宿舍报修"),
            ("DOM-PROPERTY", "物业报修"),
            ("DOM-IT", "校园网故障报修"),
        ):
            schema = build_domain_schema(title, dom, proposal_text=f"{title}派单催办完结")
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            self.assertTrue(ticket.get("allowRating"), dom)


if __name__ == "__main__":
    unittest.main()
