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

    def test_farm_attrs_not_jammed_into_meta_line(self) -> None:
        """产地/采摘走属性行；metaLine 禁再拼「产地/采摘」，避免一行灰字堆满。"""
        text = DETAIL.read_text(encoding="utf-8")
        meta_at = text.find("const metaLine = computed")
        attrs_at = text.find("const detailAttrLines = computed")
        self.assertGreater(meta_at, 0)
        self.assertGreater(attrs_at, meta_at)
        meta_chunk = text[meta_at:attrs_at]
        self.assertNotIn("bits.push(`产地", meta_chunk)
        self.assertNotIn("bits.push(`采摘", meta_chunk)
        skip_at = text.find("const skip = new Set([", attrs_at)
        self.assertGreater(skip_at, 0)
        skip_chunk = text[skip_at : skip_at + 220]
        self.assertNotIn("'region'", skip_chunk)
        self.assertNotIn("'harvestOn'", skip_chunk)


if __name__ == "__main__":
    unittest.main()
