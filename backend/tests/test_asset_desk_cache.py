"""资产台共享缓存 / 列表筛。"""

from __future__ import annotations

import unittest


class AssetDeskCacheTests(unittest.TestCase):
    def test_cache_roundtrip(self) -> None:
        from app.services.asset_desk_cache import AssetRowsCache

        c = AssetRowsCache()
        self.assertIsNone(c.get())
        c.set([{"id": 1}])
        self.assertEqual(c.get(), [{"id": 1}])
        c.invalidate()
        self.assertIsNone(c.get())

    def test_filter_and_domains(self) -> None:
        from app.services.asset_desk_cache import (
            domain_options_star_first,
            filter_rows,
        )

        rows = [
            {"domain_id": "DOM-A", "code": "x", "label_zh": "甲"},
            {"domain_id": "DOM-B", "code": "y", "label_zh": "乙"},
        ]
        got = filter_rows(
            rows, equals={"domain_id": "DOM-A"}, q="甲", q_fields=("label_zh", "code")
        )
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["code"], "x")
        opts = domain_options_star_first({"DOM-A": {"label": "甲域"}})
        self.assertEqual(opts[0]["id"], "*")
        self.assertEqual(opts[1]["id"], "DOM-A")


class ThesisOcrBudgetContract(unittest.TestCase):
    def test_ocr_budget_and_text_fallback(self) -> None:
        from pathlib import Path

        from app.services import thesis_absorb as ta
        from app.services import thesis_absorb_figures as fig

        self.assertGreaterEqual(fig.OCR_SCAN_BUDGET_S, 180)
        self.assertLessEqual(fig.OCR_SCAN_BUDGET_S, 240)
        self.assertGreaterEqual(ta.EXTRACT_SYNC_TIMEOUT_S, fig.OCR_SCAN_BUDGET_S)
        fig_src = Path(fig.__file__).read_text(encoding="utf-8")
        self.assertIn("OCR_SCAN_BUDGET_S", fig_src)
        self.assertIn("timed_out", fig_src)
        svc = Path(ta.__file__).read_text(encoding="utf-8")
        self.assertIn("_job_text_only", svc)
        self.assertIn("扫图超时，已按纯文字抽取", svc)


if __name__ == "__main__":
    unittest.main()
