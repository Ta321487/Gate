"""开题样例 / 瘦词表：不新增匹配旁路，只校验词表预算与硬分流。"""

from __future__ import annotations

import unittest

from app.bake.catalog import match_text
from app.bake.domains import DOMAINS


class SlimMatchDataTests(unittest.TestCase):
    def test_all_domains_have_match_hint(self) -> None:
        for key, meta in DOMAINS.items():
            with self.subTest(domain=key):
                self.assertTrue(
                    str(meta.get("match_hint") or "").strip(),
                    f"{key} missing match_hint（给 Match Agent 目录用，非新路由）",
                )

    def test_all_domains_keyword_budget(self) -> None:
        """全域词表硬分流预算 ≤20；近义长尾靠 match_hint / match_recommend。"""
        for key, meta in DOMAINS.items():
            with self.subTest(domain=key):
                kws = meta.get("keywords") or []
                self.assertLessEqual(len(kws), 20, f"{key} keywords={kws}")

    def test_keyword_hard_split_titles(self) -> None:
        cases = [
            ("社区公共卫生事件应急管理系统", "DOM-EVENT"),
            ("医院感染防控管理系统", "DOM-EVENT"),
            ("基层慢性病随访健康管理系统", "DOM-EVENT"),
            ("应急物资仓储与调度管理系统", "DOM-ASSET"),
            ("校园传染病防控晨午检管理系统", "DOM-EVENT"),
            ("疾控流调协查风险管理系统", "DOM-EVENT"),
            ("小型餐厅点餐系统", "DOM-FOOD"),
            ("医院门诊挂号预约系统", "DOM-HOSPITAL"),
            ("宠物医院挂号预约管理系统", "DOM-HOSPITAL"),
            ("HPV疫苗预约系统", "DOM-HOSPITAL"),
            ("校医院慢病复诊号源预约改约系统", "DOM-HOSPITAL"),
            ("宠物医院病患随访隔离观察管理系统", "DOM-EVENT"),
            ("图书馆预约占座系统", "DOM-MEETING"),
            ("图书馆研讨隔间预约系统", "DOM-MEETING"),
            ("实验室工位预约系统", "DOM-MEETING"),
            ("创新实验室工位短租预约系统", "DOM-MEETING"),
            ("实验室安全准入管理系统", "DOM-LABSAFE"),
            ("高校学生资助奖学金申请系统", "DOM-FUND"),
            ("健身房私教预约管理系统", "DOM-SALON"),
            ("心理辅导室一对一面询排班预约系统", "DOM-SALON"),
            ("宠物领养管理系统", "DOM-LOST"),
            ("校园闲置球鞋转卖系统", "DOM-SHOP"),
            ("校园歌手大赛报名海选系统", "DOM-ACTIVITY"),
            ("新生军训分连报名系统", "DOM-ACTIVITY"),
            ("医护实训耗材库存预警与申领系统", "DOM-ASSET"),
        ]
        for title, want in cases:
            with self.subTest(title=title):
                got = match_text(f"基于 Spring Boot 的{title}的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:8]}")

    def test_hospital_pet_variant_overlay_in_sample(self) -> None:
        """宠物医院题名的样例开题正文不得仍写「门诊挂号」。"""
        from app.bake.domain_schema import build_domain_schema
        from app.bake.proposal_packs import PACKS
        from app.bake.sample_proposal import render_template

        pack = next(p for p in PACKS if p["id"] == "hospital")
        title = next(t for t in pack["title_variants"] if "宠物" in t)
        text = render_template(pack, digressions=[], l1_extras=[], title=title)
        self.assertIn("宠物医院", text)
        self.assertIn("宠主", text)
        self.assertNotIn("门诊挂号若依赖", text)
        self.assertNotIn("互联网医院", text)
        schema = build_domain_schema(title, "DOM-HOSPITAL", proposal_text=text)
        self.assertEqual(schema["labels"]["authEyebrow"], "宠物挂号")
        self.assertEqual(schema["roles"]["user"]["label"], "宠主")
        self.assertIn("petName", {f["key"] for f in schema["profileFields"]})

    def test_batch_mgmt_overreach_needs_erp_companion(self) -> None:
        from app.bake.capabilities import scan_out_of_scope

        # 食安裸写批次管理：不过重
        food = "主要功能\n5.4 高风险食品批次管理\n对食品批次建档与排查。"
        self.assertNotIn("ERP/多仓进销存", scan_out_of_scope(food))
        # 裸词 + ERP 同伴：过重
        erp = "主要功能\n实现进销存与批次管理，支持多组织库存。"
        self.assertIn("ERP/多仓进销存", scan_out_of_scope(erp))

    def test_sample_opening_reports_keyword_match(self) -> None:
        """data/samples/开题报告 全文关键词匹配（口径见 00-选题目录）。"""
        from pathlib import Path

        root = Path(__file__).resolve().parents[2] / "data" / "samples" / "开题报告"
        expect = {
            "01": "DOM-EVENT",
            "02": "DOM-EVENT",
            "03": "DOM-EVENT",
            "04": "DOM-ASSET",
            "05": "DOM-EVENT",
            "06": "DOM-EVENT",
            "07": "DOM-EVENT",
            "08": "DOM-EVENT",
            "09": "DOM-EVENT",
            "10": "DOM-EVENT",
            "11": "DOM-EVENT",
            "12": "DOM-EVENT",
        }
        files = sorted(p for p in root.glob("[0-9][0-9]-*.txt") if not p.name.startswith("00-"))
        self.assertEqual(len(files), 12, files)
        for path in files:
            with self.subTest(file=path.name):
                want = expect[path.name[:2]]
                got = match_text(path.read_text(encoding="utf-8"), path.name)
                self.assertEqual(got.domain, want, f"arch={got.archetype} hits={got.hits[:10]}")

    def test_flower_shop_opening_not_hijacked_by_xitong_shixian(self) -> None:
        """「研究内容→系统实现」不得吞掉功能需求；鲜花开题应落商城皮。"""
        from pathlib import Path

        from app.bake.catalog import proposal_focus_for_match

        path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "samples"
            / "快速试传"
            / "鲜花销售管理系统开题报告.txt"
        )
        text = path.read_text(encoding="utf-8")
        focus = proposal_focus_for_match(text)
        self.assertIn("商品", focus)
        self.assertIn("购物车", focus)
        got = match_text(text, path.name)
        self.assertEqual(got.domain, "DOM-SHOP", f"arch={got.archetype} hits={got.hits[:10]}")

    def test_single_sample_packs_keyword_hit_anchor(self) -> None:
        """生成测试开题（无 LLM）须硬分流到锚域；交叉包除外。"""
        from app.bake.proposal_packs import PACKS
        from app.bake.sample_proposal import build_sample_proposal

        for pack in PACKS:
            if (pack.get("kind") or "single") == "cross":
                continue
            with self.subTest(pack_id=pack["id"]):
                sp = build_sample_proposal(pack_id=pack["id"], seed=1)
                got = match_text(sp.text, sp.filename)
                self.assertEqual(
                    got.domain,
                    pack["anchor_domain"],
                    f"title={sp.title} hits={got.hits[:8]}",
                )

    def test_all_named_domains_have_sample_pack(self) -> None:
        """具名域均可被「生成测试开题」抽到（交叉包除外）。"""
        from app.bake.proposal_packs import PACKS

        have = {
            p["anchor_domain"]
            for p in PACKS
            if (p.get("kind") or "single") != "cross"
        }
        missing = sorted(
            d for d in DOMAINS if d != "DOM-GENERIC" and d not in have
        )
        self.assertEqual(missing, [], f"缺选题包: {missing}")

    def test_it_spaced_title_hits_dom_it(self) -> None:
        """开题常见「IT 报修」（带空格）须命中 DOM-IT，不落 GENERIC。"""
        got = match_text("基于 Spring Boot 与 Vue 的校园 IT 报修服务台系统的设计与实现")
        self.assertEqual(got.domain, "DOM-IT", f"hits={got.hits[:8]}")

    def test_contrast_分流_does_not_lift_neighbor(self) -> None:
        """对比/否定句不得抬邻域关键词（用开题常见「区分/不做成」，非工厂「分流」套话）。"""
        from app.bake.proposal_lexicon import keyword_mentioned

        self.assertFalse(
            keyword_mentioned(
                "本期做演出票务报名，与影院选座购票区分。",
                "影院选座",
                ignore_contrast=True,
            )
        )
        self.assertFalse(
            keyword_mentioned(
                "不做成社团活动报名，聚焦公选课选课。",
                "社团活动",
                ignore_contrast=True,
            )
        )
        self.assertFalse(
            keyword_mentioned(
                "不同于证书报考名额报名，本系统为公选课选课。",
                "证书报考",
                ignore_contrast=True,
            )
        )

    def test_deep_skin_samples_keep_industry_not_generic(self) -> None:
        """深皮样例须保住行业皮，禁止因旁路噪声改通用壳穿帮。"""
        from pathlib import Path

        root = Path(__file__).resolve().parents[2] / "data" / "samples" / "深皮开题"
        cases = [
            ("S-25-DOM-PROPERTY-市政路灯井盖报修管理系统.txt", "DOM-PROPERTY"),
            ("S-33-DOM-ACTIVITY-景区演出票务报名管理系统.txt", "DOM-ACTIVITY"),
            ("S-34-DOM-ACTIVITY-献血与开放日报名管理系统.txt", "DOM-ACTIVITY"),
            ("S-35-DOM-LOST-流浪动物领养申请管理系统.txt", "DOM-LOST"),
            ("S-36-DOM-LOST-捐赠物资认领管理系统.txt", "DOM-LOST"),
            ("S-37-DOM-COURSE-公选课在线选课管理系统.txt", "DOM-COURSE"),
            ("S-51-DOM-HOTEL-乡村民宿客房预订管理系统.txt", "DOM-HOTEL"),
        ]
        for name, want in cases:
            with self.subTest(file=name):
                path = root / name
                got = match_text(path.read_text(encoding="utf-8"), path.name)
                self.assertEqual(
                    got.domain,
                    want,
                    f"arch={got.archetypes} hits={got.hits[:10]}",
                )

    def test_tour_pack_exists_and_matches(self) -> None:
        from app.bake.sample_proposal import build_sample_proposal, list_packs

        self.assertTrue(any(p["id"] == "tour" for p in list_packs()))
        sp = build_sample_proposal(pack_id="tour", seed=7)
        self.assertEqual(sp.anchor_domain, "DOM-TOUR")
        got = match_text(sp.text)
        self.assertEqual(got.domain, "DOM-TOUR", f"hits={got.hits[:8]}")


if __name__ == "__main__":
    unittest.main()
