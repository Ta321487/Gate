"""跟进组观感加厚（pipeline/dossier/listing）交付护栏。

钉住：
- bake 给 LISTING 归档补 price 字段（挂牌价）；
- 三份骨架 ArchiveStore 都把 price 列映射到 priceYuan；
- SQL 模板 listing 表含 price 列；
- 前端三档主信号、阶段色、独立详情与跟进文案接线；
- CSS 三档加厚类存在。
"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES

REPO = Path(__file__).resolve().parents[2]
THE = "backend/src/main/java/com/thesis"
COPIES = {
    "baseline": REPO / "skeletons" / "baseline",
    "mybatis": REPO / "skeletons" / "overlays" / "persistence-mybatis",
    "jpa": REPO / "skeletons" / "overlays" / "persistence-jpa",
}
FE = REPO / "skeletons" / "baseline" / "frontend" / "src" / "views"


def _spec(domain: str, title: str, body: str = "") -> dict:
    return attach_accept(
        {
            "domain": domain,
            "title": title,
            "capabilities": list(DOMAIN_CAPABILITIES[domain]),
            "features": [],
            "archetype": "ARCH-FLOW",
        },
        body,
    )


def _archive_fields(spec: dict) -> list[dict]:
    archive = ((spec.get("schema") or {}).get("entities") or {}).get("archive") or {}
    return list(archive.get("fields") or [])


class FollowLookThickenTests(unittest.TestCase):
    def test_listing_bake_emits_price_field(self) -> None:
        out = _spec("DOM-LISTING", "房源带看系统")
        keys = [f.get("key") for f in _archive_fields(out)]
        self.assertIn("price", keys)

    def test_price_field_only_for_listing(self) -> None:
        # dossier / pipeline 域不挂 price 列
        for domain in ("DOM-CRM", "DOM-RECRUIT", "DOM-EVENT"):
            out = _spec(domain, "跟进系统")
            keys = [f.get("key") for f in _archive_fields(out)]
            self.assertNotIn("price", keys, f"{domain} 不应有 price 列")

    def test_archive_store_price_in_all_three_copies(self) -> None:
        for copy, root in COPIES.items():
            text = (root / THE / "capability" / "ArchiveStore.java").read_text(encoding="utf-8")
            with self.subTest(copy=copy):
                self.assertIn('hasItemColumn("price")', text)
                self.assertIn('rs.getDouble("price")', text)
                self.assertIn('m.put("priceYuan", p)', text)

    def test_sql_template_has_price_column(self) -> None:
        sql = (
            REPO / "backend" / "app" / "bake" / "sql" / "templates" / "DOM-LISTING.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("price DECIMAL(12,2)", sql)
        self.assertIn("status, price)", sql)

    def test_frontend_primary_signal_three_faces(self) -> None:
        setup = (FE / "user" / "ArchiveBrowse.setup.js").read_text(encoding="utf-8")
        for needle in (
            "followSurface.value === 'pipeline'",
            "followSurface.value === 'dossier'",
            "followSurface.value === 'listing'",
            "function followStageKey(row)",
            # 独立详情：preferArchiveItemPage 吃 follow
            "const follow = String(APP_DELIVERED?.followSurfaceStyle || '').trim()",
        ):
            self.assertIn(needle, setup, f"setup.js 缺 {needle}")

    def test_frontend_stage_attr_bound(self) -> None:
        vue = (FE / "user" / "ArchiveBrowse.vue").read_text(encoding="utf-8")
        self.assertIn(':data-follow-stage="followStageKey(row)"', vue)
        self.assertIn("'surface-pipeline': followSurface === 'pipeline'", vue)
        self.assertIn("'surface-dossier': followSurface === 'dossier'", vue)
        self.assertIn("'surface-listing': followSurface === 'listing'", vue)

    def test_css_thicken_three_faces(self) -> None:
        css = (FE / "user" / "ArchiveBrowse.css").read_text(encoding="utf-8")
        for needle in (
            ".surface-pipeline .card[data-follow-stage='lead']",
            ".surface-pipeline .card[data-follow-stage='won']",
            ".surface-dossier .card",
            ".surface-listing .main-signal",
        ):
            self.assertIn(needle, css, f"CSS 缺 {needle}")

    def test_item_detail_follow_copy(self) -> None:
        detail = (FE / "user" / "ArchiveItemDetail.vue").read_text(encoding="utf-8")
        for needle in (
            "followSurfaceOn",
            "'预约带看'",
            "'记录跟进'",
            "'跟进说明'",
        ):
            self.assertIn(needle, detail, f"ArchiveItemDetail 缺 {needle}")


if __name__ == "__main__":
    unittest.main()
