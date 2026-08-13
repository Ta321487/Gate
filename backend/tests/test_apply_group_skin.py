"""报名/申请组深皮：ACTIVITY 产品皮 + LOST 捐赠认领 + TOUR stage 落库。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import build_domain_schema
from app.bake.engine_sql import domain_sql
from app.bake.scene_scan import activity_product_kind, scene_lost_parts
from app.bake.schema.templates import SCHEMA_BUILDERS


class ApplyGroupSkinTests(unittest.TestCase):
    def test_activity_product_kinds(self) -> None:
        cases = [
            ("证书报考与培训班报名管理系统", "cert", "证书报考", "报考/培训项目"),
            ("景区演出票务报名管理系统", "ticket", "票务报名", "场次/演出名称"),
            ("献血与开放日报名管理系统", "blood", "献血开放日", "场次名称"),
            ("研学夏令营赛事报名管理系统", "camp", "研学赛事", "项目名称"),
            ("讲座志愿社团活动报名管理系统", "default", "活动报名", "活动名称"),
        ]
        for title, kind, brow, field_lab in cases:
            with self.subTest(title=title):
                self.assertEqual(activity_product_kind(title, ""), kind)
                schema = SCHEMA_BUILDERS["DOM-ACTIVITY"](title, proposal_text="")
                self.assertEqual(schema["labels"]["authEyebrow"], brow)
                fields = schema["entities"]["archive"]["fields"]
                title_f = next(f for f in fields if f.get("key") == "title")
                self.assertEqual(title_f.get("label"), field_lab)

    def test_lost_donate_scene(self) -> None:
        self.assertEqual(
            scene_lost_parts("捐赠物资认领管理系统", "捐赠物资名录认领申请审核"),
            "donate",
        )
        schema = build_domain_schema(
            "捐赠物资认领管理系统",
            "DOM-LOST",
            proposal_text="捐赠物资名录；认领申请与审核。",
        )
        self.assertEqual(schema["labels"]["authEyebrow"], "捐赠认领")
        self.assertEqual(schema["entities"]["archive"]["label"], "捐赠物资")
        keys = {f["key"] for f in schema.get("profileFields") or []}
        self.assertIn("claimPurpose", keys)
        self.assertNotIn("usualPlace", keys)
        self.assertNotEqual(schema["labels"]["authEyebrow"], "社区招领")

    def test_activity_cert_sql_seed(self) -> None:
        sql = domain_sql(
            "DOM-ACTIVITY",
            "t_act",
            title="证书报考与培训班报名管理系统",
            proposal_text="证书报考名额报名审核。",
        )
        self.assertIn("大学英语四级报名", sql)
        self.assertNotIn("演示", sql)
        self.assertIn("便于校验时段冲突", sql)
        self.assertIn("INSERT IGNORE INTO signup", sql)

    def test_ticket_seeds_four_domains(self) -> None:
        cases = [
            ("DOM-ACTIVITY", "社团志愿活动报名管理系统", "INSERT IGNORE INTO signup"),
            ("DOM-LOST", "校园失物招领管理系统", "INSERT IGNORE INTO claim"),
            ("DOM-COURSE", "公选课在线选课管理系统", "INSERT IGNORE INTO enrollment"),
            ("DOM-TOUR", "旅行社线路报名管理系统", "INSERT IGNORE INTO tour_signup"),
        ]
        for domain, title, needle in cases:
            with self.subTest(domain=domain):
                sql = domain_sql(domain, "t_x", title=title, proposal_text=title)
                self.assertIn(needle, sql)
                self.assertIn("'pending'", sql)

    def test_no_dead_overdue_on_lost_course_tour(self) -> None:
        cases = [
            ("DOM-LOST", "校园失物招领管理系统"),
            ("DOM-COURSE", "公选课在线选课管理系统"),
            ("DOM-TOUR", "旅行社线路报名管理系统"),
        ]
        for domain, title in cases:
            with self.subTest(domain=domain):
                schema = build_domain_schema(title, domain, proposal_text=title)
                states = (schema.get("entities") or {}).get("ticket", {}).get("states") or {}
                self.assertNotIn("overdue", states)
        # ACTIVITY 有口令签到爽约，保留 overdue
        act = build_domain_schema(
            "讲座志愿社团活动报名管理系统",
            "DOM-ACTIVITY",
            proposal_text="活动报名",
        )
        self.assertEqual(
            ((act.get("entities") or {}).get("ticket") or {}).get("states", {}).get("overdue"),
            "爽约",
        )

    def test_tour_stage_column(self) -> None:
        sql = domain_sql(
            "DOM-TOUR",
            "t_tour",
            title="旅行社线路报名管理系统",
            proposal_text="线路报名审核出团",
        )
        # CREATE tour_line 含 stage；种子含开放报名
        self.assertRegex(sql, r"CREATE TABLE IF NOT EXISTS tour_line[\s\S]*?stage VARCHAR")
        self.assertIn("'开放报名'", sql)
        self.assertIn("apply_deadline_at", sql)
        schema = build_domain_schema(
            "旅行社线路报名管理系统",
            "DOM-TOUR",
            proposal_text="线路档案；游客报名。",
        )
        stage_f = next(
            f
            for f in schema["entities"]["archive"]["fields"]
            if f.get("key") == "stage"
        )
        self.assertEqual(stage_f.get("label"), "线路状态")
        verbs = schema["entities"]["ticket"]["verbs"]
        self.assertEqual(verbs.get("approve"), "确认报名")
        self.assertEqual(verbs.get("return"), "取消报名")
        self.assertEqual(
            schema["entities"]["ticket"]["states"].get("returned"),
            "已取消",
        )
        self.assertNotEqual(verbs.get("approve"), "确认出团")


if __name__ == "__main__":
    unittest.main()
