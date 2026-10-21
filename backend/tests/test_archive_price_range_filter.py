"""商城单价：区间筛，禁止关键词 LIKE 糊弄。"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"
OVERLAYS = (
    ROOT / "skeletons" / "overlays" / "persistence-mybatis",
    ROOT / "skeletons" / "overlays" / "persistence-jpa",
)


class ArchivePriceRangeFilterTests(unittest.TestCase):
    def test_three_stores_skip_money_in_keyword_and_have_range(self) -> None:
        for root in (BASELINE, *OVERLAYS):
            store = (
                root
                / "backend/src/main/java/com/thesis/capability/ArchiveStore.java"
            ).read_text(encoding="utf-8")
            with self.subTest(store=str(root.relative_to(ROOT))):
                self.assertIn("authorColumnIsMoney", store)
                self.assertIn("appendPriceRangeFilter", store)
                self.assertIn("priceMin", store)
                self.assertIn("price_yuan", store)
                # 金额列不得无条件塞进 keyword LIKE 列清单
                self.assertIn("if (!authorColumnIsMoney())", store)
                self.assertIn('cols.add(authorColumn())', store)

    def test_controller_and_browse_ui(self) -> None:
        ctrl = (
            BASELINE
            / "backend/src/main/java/com/thesis/controller/ArchiveController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("BigDecimal priceMin", ctrl)
        self.assertIn("BigDecimal priceMax", ctrl)
        self.assertIn("priceMin,", ctrl)

        fe = (BASELINE / "frontend/src/views/user/ArchiveBrowse.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("priceRangeFilterOn", fe)
        self.assertIn("priceMinFilter", fe)
        self.assertIn("priceMaxFilter", fe)
        self.assertIn("authorFieldIsMoney", fe)
        self.assertIn("最低价", fe)
        self.assertIn("最高价", fe)
        # 占位不再默认拼单价进关键词
        self.assertIn("if (!authorFieldIsMoney.value)", fe)
        # 价筛独立组：关步进器，避免与搜索钮重叠/双边框
        self.assertIn('class="price-range"', fe)
        self.assertIn(':controls="false"', fe)
        self.assertIn("search > :deep(.el-input)", fe)


if __name__ == "__main__":
    unittest.main()
