"""§0 X-UX：使用说明页扫词才挂。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_sql import domain_sql
from app.bake.features.proposal_caps import HUB_BYPASS_MODULES
from app.bake.features.ux_crosscut import apply_ux_crosscut_to_spec, resolve_ux_crosscut_flags

REPO = Path(__file__).resolve().parents[2]


def _spec(body: str = "") -> dict:
    return attach_accept(
        {
            "domain": "DOM-LIBRARY",
            "title": "图书借阅管理系统",
            "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
            "features": [],
            "archetype": "ARCH-FLOW",
        },
        body,
    )


class UxCrosscutFeatureTests(unittest.TestCase):
    def test_hub_lists_ux(self) -> None:
        self.assertIn("ux_crosscut", HUB_BYPASS_MODULES)

    def test_empty_opening_skips_help(self) -> None:
        flags = resolve_ux_crosscut_flags("实现图书借阅与归还。", "图书借阅管理系统")
        self.assertFalse(flags["help"])
        self.assertFalse(flags["files"])
        self.assertFalse(flags["region"])
        self.assertFalse(flags["confirm"])
        self.assertFalse(flags["commission"])
        out = apply_ux_crosscut_to_spec(_spec(), "")
        keys = {
            m.get("key")
            for m in ((out.get("schema") or {}).get("menus") or {}).get("user") or []
            if isinstance(m, dict)
        }
        self.assertNotIn("help", keys)

    def test_files_region_confirm_commission(self) -> None:
        body = "需要文件管理、省市区三级联动、敏感操作二次确认，并做一级佣金。"
        flags = resolve_ux_crosscut_flags(body, "")
        self.assertTrue(flags["files"])
        self.assertTrue(flags["region"])
        self.assertTrue(flags["confirm"])
        self.assertTrue(flags["commission"])
        self.assertFalse(flags["help"])
        out = apply_ux_crosscut_to_spec(_spec(body=body), body)
        admin = ((out.get("schema") or {}).get("menus") or {}).get("admin") or []
        keys = {m.get("key") for m in admin if isinstance(m, dict)}
        self.assertIn("files", keys)
        self.assertIn("commissions", keys)
        labels = (out.get("schema") or {}).get("labels") or {}
        blob = " ".join(str(v) for v in labels.values())
        for bad in ("bake", "开题", "工厂"):
            self.assertNotIn(bad, blob)
        sql = domain_sql(
            "DOM-LIBRARY",
            "thesis_ux2",
            title="图书借阅管理系统",
            proposal_text=body,
        )
        self.assertIn("sys_commission", sql.lower())
        self.assertNotIn("sys_help_doc", sql.lower())

    def test_literature_fenxiao_does_not_mount_commission(self) -> None:
        """方木探针：研究现状「综合分销系统 / 多维分销网络」≠ 佣金台账。"""
        body = (
            "1.2 本课题所涉及问题在国内外设计或研究的现状\n"
            "1.2.1 国内现状\n"
            "在国内，针对各类垂直电商及综合分销系统的技术研讨与平台实践日益丰富。"
            "郑彩莲强调了多维分销网络对扩大体育消费的赋能价值[2]。\n"
            "管理员端具备用户与商家账号管理、违规商品强制下架与订单监督。"
        )
        self.assertFalse(resolve_ux_crosscut_flags(body, "方木健身用品电商平台")["commission"])
        out = apply_ux_crosscut_to_spec(_spec(body=body), body)
        admin = ((out.get("schema") or {}).get("menus") or {}).get("admin") or []
        keys = {m.get("key") for m in admin if isinstance(m, dict)}
        self.assertNotIn("commissions", keys)

    def test_fenxiao_commission_phrase_still_mounts(self) -> None:
        body = "注册填邀请人，支付成功记分销佣金并入佣金台账。"
        self.assertTrue(resolve_ux_crosscut_flags(body, "")["commission"])

    def test_help_phrase_opens_menu_and_sql(self) -> None:
        body = "提供系统帮助与操作手册。"
        self.assertTrue(resolve_ux_crosscut_flags(body, "")["help"])
        out = apply_ux_crosscut_to_spec(_spec(body=body), body)
        user = ((out.get("schema") or {}).get("menus") or {}).get("user") or []
        admin = ((out.get("schema") or {}).get("menus") or {}).get("admin") or []
        self.assertIn("help", {m.get("key") for m in user if isinstance(m, dict)})
        self.assertIn("help_admin", {m.get("key") for m in admin if isinstance(m, dict)})
        labels = (out.get("schema") or {}).get("labels") or {}
        blob = " ".join(str(v) for v in labels.values())
        for bad in ("bake", "开题", "工厂"):
            self.assertNotIn(bad, blob)
        sql = domain_sql(
            "DOM-LIBRARY",
            "thesis_help",
            title="图书借阅管理系统",
            proposal_text=body,
        )
        self.assertIn("sys_help_doc", sql.lower())

    def test_sql_without_phrase_has_no_help_table(self) -> None:
        sql = domain_sql("DOM-LIBRARY", "thesis_help0", title="图书借阅管理系统")
        self.assertNotIn("sys_help_doc", sql.lower())

    def test_skeleton_files(self) -> None:
        base = REPO / "skeletons/baseline"
        self.assertTrue((base / "backend/src/main/java/com/thesis/service/HelpStore.java").is_file())
        self.assertTrue((base / "frontend/src/views/Help.vue").is_file())
        self.assertTrue((base / "frontend/src/views/admin/FilesAdmin.vue").is_file())
        self.assertTrue((base / "frontend/src/utils/regionOptions.js").is_file())
        self.assertTrue((base / "backend/src/main/java/com/thesis/service/CommissionStore.java").is_file())
        handler = (base / "backend/src/main/java/com/thesis/common/GlobalExceptionHandler.java").read_text(
            encoding="utf-8"
        )
        self.assertIn("文件不能超过 10MB", handler)


if __name__ == "__main__":
    unittest.main()
