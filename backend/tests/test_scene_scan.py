"""开题场景单一真源：壳与资料页必须同判定。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import build_domain_schema
from app.bake.scene_scan import scene_for
from app.bake.schema.templates import SCHEMA_BUILDERS


class SceneScanContractTests(unittest.TestCase):
    def test_crm_sales_beats_campus_background(self) -> None:
        scene = scene_for(
            "DOM-CRM",
            "中小企业客户跟进管理系统",
            "学院创业孵化；销售人员维护客户并提交跟进。",
        )
        self.assertEqual(scene, "enterprise")
        schema = build_domain_schema(
            "中小企业客户跟进管理系统",
            "DOM-CRM",
            proposal_text="学院创业孵化；销售人员维护客户并提交跟进。",
        )
        ident = next(f for f in schema["profileFields"] if f["key"] == "identityType")
        self.assertEqual(ident["options"], ["销售", "运营", "其他"])
        self.assertNotIn("studentNo", {f["key"] for f in schema["profileFields"]})

    def test_shell_and_profile_same_scene_asset_attend_event(self) -> None:
        cases = [
            (
                "DOM-ASSET",
                "物资领用系统",
                "企业仓储部门耗材申领出库。",
                "enterprise",
                "物资领用",
            ),
            (
                "DOM-ASSET",
                "高校固定资产申领",
                "学院行政部门物资申领。",
                "campus",
                "高校物资",
            ),
            (
                "DOM-ATTEND",
                "学生请假销假管理系统",
                "",
                "campus",
                "学生请假",
            ),
            (
                "DOM-ATTEND",
                "企业员工考勤请假管理系统",
                "",
                "enterprise",
                "人事公告",
            ),
            (
                "DOM-EVENT",
                "社区健康监测",
                "社区网格员维护居民档案。",
                "community",
                "社区公卫",
            ),
            (
                "DOM-EVENT",
                "校园晨午检",
                "因病缺课上报。",
                "campus",
                "校园晨午检",
            ),
        ]
        for domain, title, body, want_scene, eyebrow_or_notice in cases:
            with self.subTest(domain=domain, title=title):
                self.assertEqual(scene_for(domain, title, body), want_scene)
                schema = build_domain_schema(title, domain, proposal_text=body)
                labels = schema.get("labels") or {}
                blob = " ".join(
                    [
                        labels.get("authEyebrow") or "",
                        labels.get("noticePageTitle") or "",
                        (schema.get("roles") or {}).get("admin", {}).get("label") or "",
                    ]
                )
                self.assertIn(eyebrow_or_notice, blob)

    def test_parcel_community_no_campus_profile(self) -> None:
        title, body = "快递代收系统", "小区菜鸟驿站取件核销。"
        self.assertEqual(scene_for("DOM-PARCEL", title, body), "community")
        schema = build_domain_schema(title, "DOM-PARCEL", proposal_text=body)
        self.assertEqual(schema["labels"]["authEyebrow"], "快递代收")
        self.assertNotIn("campusNo", {f["key"] for f in schema["profileFields"]})

    def test_builders_accept_proposal_kw(self) -> None:
        """SCENE_COPY 域 builder 必须吃 proposal_text，避免只扫题名。"""
        from app.bake.schema.shells import _SCENE_COPY_DOMAINS

        for dom in sorted(_SCENE_COPY_DOMAINS):
            with self.subTest(dom=dom):
                fn = SCHEMA_BUILDERS[dom]
                schema = fn("测试课题", proposal_text="占位开题正文")
                self.assertTrue(schema.get("labels") or schema.get("roles"))


if __name__ == "__main__":
    unittest.main()
