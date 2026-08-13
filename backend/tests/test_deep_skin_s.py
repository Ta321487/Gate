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
        self.assertEqual(len(S_SKIN_CASES), 53)
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

    def test_event_keyword_budget_still_holds(self) -> None:
        kws = DOMAINS["DOM-EVENT"].get("keywords") or []
        self.assertLessEqual(len(kws), 20, kws)


if __name__ == "__main__":
    unittest.main()
