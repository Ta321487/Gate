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

    def test_event_keyword_budget(self) -> None:
        kws = DOMAINS["DOM-EVENT"].get("keywords") or []
        self.assertLessEqual(len(kws), 20, kws)

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
        ]
        for title, want in cases:
            with self.subTest(title=title):
                got = match_text(f"基于 Spring Boot 的{title}的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:8]}")

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
            / "鲜花销售管理系统开题报告.txt"
        )
        text = path.read_text(encoding="utf-8")
        focus = proposal_focus_for_match(text)
        self.assertIn("商品", focus)
        self.assertIn("购物车", focus)
        got = match_text(text, path.name)
        self.assertEqual(got.domain, "DOM-SHOP", f"arch={got.archetype} hits={got.hits[:10]}")



if __name__ == "__main__":
    unittest.main()
