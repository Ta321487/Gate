"""泳道 B：§3 深皮 S-* 正命中挂靠域；样例路径存在。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.catalog import match_text
from app.bake.deep_skin_s import S_SKIN_CASES
from app.bake.domain_schema import build_domain_schema
from app.bake.domains import DOMAINS

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples" / "深皮开题"


class DeepSkinSMatchTests(unittest.TestCase):
    def test_all_s_ids_hit_anchor_domain(self) -> None:
        self.assertEqual(len(S_SKIN_CASES), 60)
        for sid, phrase, want, title in S_SKIN_CASES:
            with self.subTest(id=sid, title=title):
                text = f"基于 Spring Boot 的{title}的设计与实现。主要功能：{phrase}。"
                got = match_text(text)
                self.assertEqual(got.domain, want, f"hits={got.hits[:8]}")

    def test_sample_files_exist(self) -> None:
        self.assertTrue(SAMPLES.is_dir(), SAMPLES)
        for sid, _phrase, domain, title in S_SKIN_CASES:
            with self.subTest(id=sid):
                path = SAMPLES / f"{sid}-{domain}-{title}.txt"
                self.assertTrue(path.is_file(), path)
                body = path.read_text(encoding="utf-8")
                self.assertIn(title, body)
                self.assertIn(sid, body)

    def test_s21_complaint_verbs(self) -> None:
        schema = build_domain_schema(
            "社区物业投诉建议工单管理系统",
            "DOM-PROPERTY",
            proposal_text="业主投诉建议工单受理完结",
        )
        labels = schema.get("labels") or {}
        self.assertEqual(labels.get("authEyebrow"), "投诉建议")
        self.assertIn("提交投诉", labels.get("authPoints") or [])
        menus = (schema.get("menus") or {}).get("admin") or []
        site = next((m.get("label") for m in menus if m.get("key") == "lookup_site"), None)
        self.assertEqual(site, "楼栋单元")

    def test_s02_s03_equip_skin(self) -> None:
        """S-02/S-03：EQUIP 深皮不得仍显示实验室设备壳。"""
        from app.bake.scene_scan import equip_product_kind

        s02 = build_domain_schema(
            "校园共享雨伞与充电宝租借管理系统",
            "DOM-EQUIP",
            proposal_text="校园雨伞充电宝门禁卡租借归还",
        )
        self.assertEqual(equip_product_kind("校园共享雨伞与充电宝租借管理系统", ""), "light")
        self.assertEqual((s02.get("labels") or {}).get("authEyebrow"), "校园轻资产")
        self.assertNotEqual((s02.get("labels") or {}).get("authEyebrow"), "实验室设备")

        s03 = build_domain_schema(
            "校园演出服装道具租借管理系统",
            "DOM-EQUIP",
            proposal_text="演出服装道具器材租借归还审核",
        )
        self.assertEqual(equip_product_kind("校园演出服装道具租借管理系统", ""), "costume")
        self.assertEqual((s03.get("labels") or {}).get("authEyebrow"), "演出道具")

    def test_s16_2_spot_checks(self) -> None:
        """§16.2 深皮抽检句。"""
        cases = [
            ("档案馆卷宗借阅与归还审核", "DOM-LIBRARY"),
            ("业主投诉建议与物业工单办结", "DOM-PROPERTY"),
            ("高校心理咨询预约时段管理", "DOM-SALON"),
            ("政务服务中心窗口取号预约", "DOM-HOSPITAL"),
        ]
        for phrase, want in cases:
            with self.subTest(phrase=phrase):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:8]}")

    def test_s75_s81_skin_eyebrows(self) -> None:
        """S-75～S-81：文案皮与种子不穿帮。"""
        from app.bake.engine_sql import domain_sql
        from app.bake.scene_scan import (
            activity_product_kind,
            event_product_kind,
            procure_product_kind,
            recruit_product_kind,
            scene_lost_parts,
        )

        cases = [
            ("防返贫数字化辅助系统", "DOM-EVENT", "帮扶户建档走访上报", "防返贫监测", "边缘易致贫"),
            ("安顺学院献血管理系统", "DOM-ACTIVITY", "献血场次报名审核", "献血管理", "无偿献血"),
            ("校园防暴恐培训管理系统", "DOM-ACTIVITY", "防暴恐安全培训报名", "防暴恐培训", "防暴恐"),
            ("歌剧院票务报名管理系统", "DOM-ACTIVITY", "歌剧院演出领票", "歌剧票务", "茶花女"),
            ("外文学术期刊遴选服务平台", "DOM-PROCURE", "期刊品目遴选荐购", "期刊遴选", "Nature"),
            ("航班行李挂失认领管理系统", "DOM-LOST", "航班行李挂失认领", "行李挂失", "拉杆箱"),
            ("威客任务接单管理系统", "DOM-RECRUIT", "威客任务发布投递初筛", "威客任务", "Logo"),
        ]
        for title, domain, body, brow, seed_needle in cases:
            with self.subTest(title=title, needle=seed_needle):
                schema = build_domain_schema(title, domain, proposal_text=body)
                self.assertEqual((schema.get("labels") or {}).get("authEyebrow"), brow)
                sql = domain_sql(domain, "t_skin", title=title, proposal_text=body)
                self.assertIn(seed_needle, sql)
                # 学生可见面禁止「演示」字样（H22）
                self.assertNotIn("演示", sql)
                if domain == "DOM-EVENT":
                    self.assertEqual(event_product_kind(title, body), "household")
                elif domain == "DOM-ACTIVITY":
                    self.assertIn(activity_product_kind(title, body), {"blood", "cert", "ticket"})
                elif domain == "DOM-PROCURE":
                    self.assertEqual(procure_product_kind(title, body), "journal")
                elif domain == "DOM-LOST":
                    self.assertEqual(scene_lost_parts(title, body), "baggage")
                elif domain == "DOM-RECRUIT":
                    self.assertEqual(recruit_product_kind(title, body), "witkey")

    def test_event_keyword_budget_still_holds(self) -> None:
        kws = DOMAINS["DOM-EVENT"].get("keywords") or []
        self.assertLessEqual(len(kws), 20, kws)


if __name__ == "__main__":
    unittest.main()
