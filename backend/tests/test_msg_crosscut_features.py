"""§0 X-MSG 通识横切：列注入 / labels / 骨架契约（XM-00～XM-02）。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_sql import domain_sql
from app.bake.features.msg_crosscut import (
    MSG_CROSSCUT_COLUMNS,
    NOTICE_CROSSCUT_COLUMNS,
    apply_msg_crosscut_to_spec,
)
from app.bake.features.proposal_caps import HUB_BYPASS_MODULES

REPO = Path(__file__).resolve().parents[2]

_MSG_LABEL_KEYS = (
    "messageKindAll",
    "messageKindSystem",
    "messageKindBiz",
    "messageDeleteLabel",
    "messageDeletedHint",
)

_XM02_LABEL_KEYS = (
    "noticeExpireLabel",
    "noticeForceAckLabel",
    "noticeForceAckHint",
    "noticeForceAckConfirm",
    "noticeRichHtmlHint",
    "noticeContentFmtLabel",
    "bannersMenu",
    "bannerSlotLabel",
    "bannerEmptyHint",
)


def _spec(domain: str = "DOM-LIBRARY", title: str = "图书借阅管理系统") -> dict:
    return attach_accept(
        {
            "domain": domain,
            "title": title,
            "capabilities": list(DOMAIN_CAPABILITIES[domain]),
            "features": [],
            "archetype": "ARCH-FLOW",
        },
        "",
    )


class MsgCrosscutFeatureTests(unittest.TestCase):
    def test_hub_bypass_lists_msg_crosscut(self) -> None:
        self.assertIn("msg_crosscut", HUB_BYPASS_MODULES)

    def test_sys_message_deleted_at_injected_on_bake(self) -> None:
        sql = domain_sql("DOM-LIBRARY", "thesis_msg_x", title="图书借阅管理系统")
        m = re.search(
            r"CREATE TABLE IF NOT EXISTS\s+`?sys_message`?\s*\((.*?)\)\s*;",
            sql,
            flags=re.I | re.S,
        )
        self.assertIsNotNone(m, "sys_message CREATE missing")
        body = m.group(1).lower()
        for col, _decl in MSG_CROSSCUT_COLUMNS:
            self.assertIn(col.lower(), body, f"missing column {col}")

    def test_sys_notice_xm02_columns_and_tables(self) -> None:
        sql = domain_sql("DOM-LIBRARY", "thesis_msg_x2", title="图书借阅管理系统")
        m = re.search(
            r"CREATE TABLE IF NOT EXISTS\s+`?sys_notice`?\s*\((.*?)\)\s*;",
            sql,
            flags=re.I | re.S,
        )
        self.assertIsNotNone(m, "sys_notice CREATE missing")
        body = m.group(1).lower()
        for col, _decl in NOTICE_CROSSCUT_COLUMNS:
            self.assertIn(col.lower(), body, f"missing notice column {col}")
        self.assertIn("CREATE TABLE IF NOT EXISTS sys_notice_ack", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS sys_banner", sql)

    def test_apply_spec_seeds_labels(self) -> None:
        out = apply_msg_crosscut_to_spec(_spec(), "")
        labels = (out.get("schema") or {}).get("labels") or {}
        for key in _MSG_LABEL_KEYS + _XM02_LABEL_KEYS:
            self.assertTrue(str(labels.get(key) or "").strip(), f"label {key}")
        admin = ((out.get("schema") or {}).get("menus") or {}).get("admin") or []
        self.assertTrue(any(m.get("key") == "banners" for m in admin), "banners menu")

    def test_attach_accept_includes_msg_labels(self) -> None:
        labels = ((_spec().get("schema") or {}).get("labels") or {})
        for key in _MSG_LABEL_KEYS + _XM02_LABEL_KEYS:
            self.assertTrue(str(labels.get(key) or "").strip(), f"attach label {key}")

    def test_baseline_fe_reads_msg_labels(self) -> None:
        fe = (
            REPO
            / "skeletons/baseline/frontend/src/views/user/Messages.vue"
        ).read_text(encoding="utf-8")
        for key in _MSG_LABEL_KEYS:
            self.assertIn(key, fe, f"Messages.vue must read {key}")

    def test_three_message_stores_have_soft_delete_and_kind(self) -> None:
        paths = [
            REPO
            / "skeletons/baseline/backend/src/main/java/com/thesis/service/MessageStore.java",
            REPO
            / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/service/MessageStore.java",
            REPO
            / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/service/MessageStore.java",
        ]
        for p in paths:
            text = p.read_text(encoding="utf-8")
            self.assertIn("softDelete", text, str(p))
            self.assertIn("normalizeKind", text, str(p))
            self.assertTrue(
                "deleted_at" in text or "hasDeletedAt" in text,
                f"missing deleted_at plumbing: {p}",
            )
            self.assertIn("page(String username, int page, int size, String kind)", text, str(p))

    def test_message_controller_kind_and_delete(self) -> None:
        text = (
            REPO
            / "skeletons/baseline/backend/src/main/java/com/thesis/controller/MessageController.java"
        ).read_text(encoding="utf-8")
        self.assertIn('RequestParam(defaultValue = "all") String kind', text)
        self.assertIn("@DeleteMapping", text)
        self.assertIn("softDelete", text)

    def test_three_notice_stores_have_xm02(self) -> None:
        paths = [
            REPO
            / "skeletons/baseline/backend/src/main/java/com/thesis/service/NoticeStore.java",
            REPO
            / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/service/NoticeStore.java",
            REPO
            / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/service/NoticeStore.java",
        ]
        for p in paths:
            text = p.read_text(encoding="utf-8")
            self.assertIn("listForcePending", text, str(p))
            self.assertIn("ackForce", text, str(p))
            self.assertIn("expire_at", text, str(p))
            self.assertIn("force_ack", text, str(p))
            self.assertIn("content_fmt", text, str(p))
            self.assertIn("isPortalVisible", text, str(p))

    def test_three_banner_stores(self) -> None:
        paths = [
            REPO
            / "skeletons/baseline/backend/src/main/java/com/thesis/service/BannerStore.java",
            REPO
            / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/service/BannerStore.java",
            REPO
            / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/service/BannerStore.java",
        ]
        for p in paths:
            text = p.read_text(encoding="utf-8")
            self.assertIn("sys_banner", text, str(p))
            self.assertIn("listEnabled", text, str(p))

    def test_notice_controller_force_and_banner_controller(self) -> None:
        nc = (
            REPO
            / "skeletons/baseline/backend/src/main/java/com/thesis/controller/NoticeController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("force-pending", nc)
        self.assertIn("ackForce", nc)
        self.assertIn("isPortalVisible", nc)
        bc = (
            REPO
            / "skeletons/baseline/backend/src/main/java/com/thesis/controller/BannerController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/banners", bc)
        self.assertIn("BannerStore", bc)

    def test_fe_xm02_surfaces(self) -> None:
        notices = (
            REPO / "skeletons/baseline/frontend/src/views/admin/NoticesAdmin.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("forceAck", notices)
        self.assertIn("expireAt", notices)
        self.assertIn("contentFmt", notices)
        detail = (
            REPO / "skeletons/baseline/frontend/src/views/NoticeDetail.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("isHtml", detail)
        self.assertIn("v-html", detail)
        gate = (
            REPO / "skeletons/baseline/frontend/src/components/ForceNoticeGate.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("force-pending", gate)
        self.assertIn("show-close=\"false\"", gate)
        banners = (
            REPO / "skeletons/baseline/frontend/src/views/admin/BannersAdmin.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/banners", banners)
        self.assertIn("/uploads/", banners)
        self.assertIn("aria-label=\"图片地址怎么填\"", banners)
        carousel = (
            REPO / "skeletons/baseline/frontend/src/components/PortalCarousel.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/banners", carousel)


if __name__ == "__main__":
    unittest.main()
