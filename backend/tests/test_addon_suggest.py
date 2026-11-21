"""工厂开关建议台：种子、扫词、匹配建议、缺口。"""

from __future__ import annotations

import unittest

from app.services import addon_suggest as ads


class AddonSuggestUnit(unittest.TestCase):
    def setUp(self) -> None:
        ads.invalidate_cache()
        ads.bootstrap_from_seed()

    def test_seed_has_core_addons(self) -> None:
        ids = set(ads.expected_addon_ids_from_seed())
        self.assertIn("ai_assistant", ids)
        self.assertIn("spring_security", ids)
        rows = ads._seed_payload()
        self.assertGreaterEqual(len(rows), 10)
        keys = [(r["addon_id"], r["hint"].casefold()) for r in rows]
        self.assertEqual(len(keys), len(set(keys)))

    def test_suggest_ai_assistant_with_evidence(self) -> None:
        hits = ads.suggest_addons("校园报修系统", "集成智能客服与大模型问答助手")
        by_id = {h["addon_id"]: h for h in hits}
        self.assertIn("ai_assistant", by_id)
        self.assertTrue(by_id["ai_assistant"]["recommended"])
        self.assertTrue(by_id["ai_assistant"]["evidences"])

    def test_suggest_chatgpt_case_insensitive(self) -> None:
        hits = ads.suggest_addons("演示", "接入 chatgpt 做问答")
        by_id = {h["addon_id"]: h for h in hits}
        self.assertIn("ai_assistant", by_id)
        self.assertIn("ChatGPT", by_id["ai_assistant"]["hints"])

    def test_suggest_security_named(self) -> None:
        hits = ads.suggest_addons("商城", "采用 Spring Security 做登录鉴权")
        by_id = {h["addon_id"]: h for h in hits}
        self.assertIn("spring_security", by_id)
        self.assertTrue(by_id["spring_security"]["recommended"])

    def test_no_hit_returns_empty(self) -> None:
        hits = ads.suggest_addons("图书借阅", "读者在线续借与预约")
        self.assertEqual(hits, [])

    def test_stack_scan_exposes_addon_suggestions(self) -> None:
        from app.bake.stack_scan import scan_stack

        out = scan_stack("演示", "需要接入 DeepSeek 智能助手")
        self.assertIn("addon_suggestions", out)
        aids = {s["addon_id"] for s in out["addon_suggestions"]}
        self.assertIn("ai_assistant", aids)
        self.assertTrue(out.get("recommended_ai_assistant") or out.get("ai_assistant"))

    def test_gap_when_rows_empty_strict(self) -> None:
        report = ads.gap_report(rows=[])
        # 空集不回落种子时：expected 相对空 have 全缺口
        # gap_report 经 _rows_or_seed([]) 会回落种子 → 0；用伪造缺 addon 行测
        seed = ads._seed_payload()
        trimmed = [r for r in seed if r.get("addon_id") != "echarts"]
        report = ads.gap_report(rows=trimmed)
        aids = {g["addon_id"] for g in report["gaps"]}
        self.assertIn("echarts", aids)
        self.assertNotIn("ai_assistant", aids)

    def test_no_hardcoded_put_in_service(self) -> None:
        from pathlib import Path

        src = Path(ads.__file__).read_text(encoding="utf-8")
        self.assertNotIn('put("DOM-', src)
        self.assertIn("load_seed_json", src)


if __name__ == "__main__":
    unittest.main()
