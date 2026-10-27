"""档案独立详情：商城货架脸护栏。

钉住：
- 买区 aid-buybox 钉右栏底（与左图齐高，禁顶对齐留下半截空）；
- 下单态不露「单价(元)」表单腔价签标签。
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DETAIL = (
    REPO
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "views"
    / "user"
    / "ArchiveItemDetail.vue"
)


class ArchiveItemDetailShopTests(unittest.TestCase):
    def test_buybox_pinned_and_shop_price(self) -> None:
        text = DETAIL.read_text(encoding="utf-8")
        self.assertIn('class="aid-buybox"', text)
        self.assertIn("detailAttrLines", text)
        self.assertIn("shouldShowDetailAttr", text)
        self.assertIn("showPriceLabel", text)
        self.assertIn("if (orderOn.value) return false", text)
        self.assertIn(".aid-buybox", text)
        self.assertIn("margin-top: auto", text)
        self.assertIn(".aid-info", text)
        # 数量与主操作须在 buybox 内，禁散落在 info 顶段
        buy_at = text.find('class="aid-buybox"')
        self.assertGreater(buy_at, 0)
        chunk = text[buy_at : buy_at + 1200]
        self.assertIn('class="aid-qty"', chunk)
        self.assertIn('class="aid-acts"', chunk)
        head = text[:buy_at]
        self.assertNotIn('class="aid-qty"', head)


if __name__ == "__main__":
    unittest.main()
