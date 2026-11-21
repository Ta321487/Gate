"""工厂能力说明卡：种子、README 注入、开关诚实。"""

from __future__ import annotations

import unittest

from app.bake import addons
from app.services import cap_cards as cc


class CapCardsUnit(unittest.TestCase):
    def setUp(self) -> None:
        cc.invalidate_cache()
        cc.bootstrap_from_seed()

    def test_seed_covers_security_and_ai(self) -> None:
        ids = set(cc.expected_cap_ids_from_seed())
        self.assertEqual(ids, {"ai_assistant", "spring_security"})
        ai = cc.get_card("ai_assistant")
        self.assertIsNotNone(ai)
        assert ai is not None
        self.assertIn("DeepSeek", ai["body_zh"])
        self.assertIn("ai_assistant", ai["menu_ids"])

    def test_ai_readme_bits_from_card(self) -> None:
        on = addons.ai_assistant_readme_bits(True)
        off = addons.ai_assistant_readme_bits(False)
        self.assertIn("DeepSeek", on)
        self.assertIn("Spring AI", on)
        self.assertEqual(off, "")

    def test_security_readme_bits_from_card(self) -> None:
        be, auth, faq = addons.security_readme_bits(True, "JdbcTemplate")
        self.assertIn("Spring Security", be)
        self.assertIn("过滤器链", auth)
        self.assertIn("SecurityFilterChain", faq)
        be2, auth2, faq2 = addons.security_readme_bits(False, "JdbcTemplate")
        self.assertEqual(be2, "JdbcTemplate")
        self.assertIn("未启用", auth2)
        self.assertEqual(faq2, "")

    def test_honesty_off_rejects_claim(self) -> None:
        errs = cc.readme_honesty_errors(
            "本包已集成 DeepSeek 与 Spring AI",
            enabled={"ai_assistant": False, "spring_security": False},
        )
        self.assertTrue(any("ai_assistant" in e for e in errs))

    def test_honesty_on_requires_needle(self) -> None:
        errs = cc.readme_honesty_errors(
            "普通 README 无助手说明",
            enabled={"ai_assistant": True},
        )
        self.assertTrue(errs)
        ok = cc.readme_honesty_errors(
            addons.ai_assistant_readme_bits(True),
            enabled={"ai_assistant": True},
        )
        self.assertEqual(ok, [])

    def test_gap_when_body_missing(self) -> None:
        rows = [
            {
                "cap_id": "spring_security",
                "body_zh": "有正文",
                "source": "migrated",
            }
        ]
        report = cc.gap_report(rows=rows)
        aids = {g["cap_id"] for g in report["gaps"]}
        self.assertIn("ai_assistant", aids)

    def test_no_hardcoded_put(self) -> None:
        from pathlib import Path

        src = Path(cc.__file__).read_text(encoding="utf-8")
        self.assertIn("load_seed_json", src)
        addons_src = Path(addons.__file__).read_text(encoding="utf-8")
        self.assertIn("cap_cards", addons_src)
        self.assertNotIn("DEEPSEEK_API_KEY 环境变量自配", addons_src)


if __name__ == "__main__":
    unittest.main()
