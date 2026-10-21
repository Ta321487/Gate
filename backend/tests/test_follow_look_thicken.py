"""跟进组观感加厚（pipeline/dossier/listing）交付护栏。

钉住：
- bake 给 LISTING 归档补 price（挂牌价）与 priceUnit（计价单位）字段；
- 三份骨架 ArchiveStore 都把 price 列映射到 priceYuan、price_unit 列映射到 priceUnit；
- SQL 模板 listing 表含 price / price_unit 列且种子带单位；
- 前端三档主信号、阶段色、独立详情与跟进文案接线；
- 前端按 priceUnit 拼单位，不再靠数值大小猜；
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
        fields = {f.get("key"): f for f in _archive_fields(out)}
        # 键与后端数据键对齐（priceYuan），管理端才读写得到
        self.assertIn("priceYuan", fields)
        # 单位独立成列，取 select 枚举，禁止前端按数值猜
        self.assertIn("priceUnit", fields)
        unit = fields["priceUnit"]
        self.assertEqual(unit.get("type"), "select")
        opts = list(unit.get("options") or [])
        # 选题不唯一：至少覆盖租/售/按面/短租等常见单位，禁止缩成两种
        for need in ("元/月", "元/套", "元/㎡", "元/间", "元/天", "元/辆", "元/个", "万元"):
            self.assertIn(need, opts, f"priceUnit 缺选项 {need}")
        self.assertNotIn("元/月 或 元/套", str(fields["priceYuan"].get("label")))

    def test_price_unit_only_for_listing(self) -> None:
        for domain in ("DOM-CRM", "DOM-RECRUIT", "DOM-EVENT"):
            out = _spec(domain, "跟进系统")
            keys = [f.get("key") for f in _archive_fields(out)]
            self.assertNotIn("priceUnit", keys, f"{domain} 不应有 priceUnit 列")

    def test_price_field_only_for_listing(self) -> None:
        # dossier / pipeline 域不挂 price 列
        for domain in ("DOM-CRM", "DOM-RECRUIT", "DOM-EVENT"):
            out = _spec(domain, "跟进系统")
            keys = [f.get("key") for f in _archive_fields(out)]
            self.assertNotIn("priceYuan", keys, f"{domain} 不应有 price 列")

    def test_archive_store_price_in_all_three_copies(self) -> None:
        for copy, root in COPIES.items():
            text = (root / THE / "capability" / "ArchiveStore.java").read_text(encoding="utf-8")
            with self.subTest(copy=copy):
                self.assertIn('hasItemColumn("price")', text)
                self.assertIn('rs.getDouble("price")', text)
                self.assertIn('m.put("priceYuan", p)', text)
                self.assertIn('patchOptNum(id, patch, "priceYuan", "price")', text)
                self.assertIn('hasItemColumn("price_unit")', text)
                self.assertIn('m.put("priceUnit", safeStr(rs, "price_unit"))', text)
                self.assertIn('patchOptStr(id, patch, "priceUnit", "price_unit", 16)', text)

    def test_sql_template_has_price_column(self) -> None:
        sql = (
            REPO / "backend" / "app" / "bake" / "sql" / "templates" / "DOM-LISTING.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("price DECIMAL(12,2)", sql)
        self.assertIn("price_unit VARCHAR(16)", sql)
        self.assertIn("status, price, price_unit)", sql)
        # 种子带单位：整租/合租按月、二手出售按套
        self.assertIn("'元/月'", sql)
        self.assertIn("'元/套'", sql)

    def test_listing_ensure_injects_price_columns(self) -> None:
        """缺列模板经 ensure 也要补上 price / price_unit（仅 LISTING）。"""
        from app.bake.sql.fragments import ensure_follow_archive_columns

        bare = """
CREATE TABLE IF NOT EXISTS listing (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(128) DEFAULT ''
);
"""
        out = ensure_follow_archive_columns(bare, domain="DOM-LISTING", item_table="listing")
        self.assertIn("price DECIMAL(12,2)", out)
        self.assertIn("price_unit VARCHAR(16)", out)
        crm = ensure_follow_archive_columns(bare, domain="DOM-CRM", item_table="customer")
        self.assertNotIn("price DECIMAL(12,2)", crm)
        self.assertNotIn("price_unit", crm)

    def test_frontend_listing_uses_price_unit(self) -> None:
        setup = (FE / "user" / "ArchiveBrowse.setup.js").read_text(encoding="utf-8")
        self.assertIn("row.priceUnit", setup)
        # 不再出现按数值大小猜单位的旧兜底
        self.assertNotIn("return `¥${p.toFixed(0)}/月`", setup)

    def test_frontend_primary_signal_three_faces(self) -> None:
        setup = (FE / "user" / "ArchiveBrowse.setup.js").read_text(encoding="utf-8")
        for needle in (
            "followSurface.value === 'pipeline'",
            "followSurface.value === 'dossier'",
            "followSurface.value === 'listing'",
            "function followStageToneOf(row)",
            # 阶段→tone 归 statusTone.js，本页只转调
            "import { followStageTone } from '../../utils/statusTone.js'",
            "return followStageTone(row?.stage)",
            # 独立详情：preferArchiveItemPage 吃 follow
            "const follow = String(APP_DELIVERED?.followSurfaceStyle || '').trim()",
        ):
            self.assertIn(needle, setup, f"setup.js 缺 {needle}")

    def test_follow_stage_tone_kept_in_status_tone(self) -> None:
        """阶段色键走共享 tone 口径，且档案行文案不混两种含义。"""
        tone = (
            REPO / "skeletons" / "baseline" / "frontend" / "src" / "utils" / "statusTone.js"
        ).read_text(encoding="utf-8")
        self.assertIn("export function followStageTone(stage)", tone)
        for key in ("'pending'", "'progress'", "'warn'", "'ok'", "'muted'"):
            self.assertIn(f"return {key}", tone, f"statusTone 缺 {key} 档")
        setup = (FE / "user" / "ArchiveBrowse.setup.js").read_text(encoding="utf-8")
        self.assertNotIn("已停/满", setup)

    def test_frontend_stage_attr_bound(self) -> None:
        vue = (FE / "user" / "ArchiveBrowse.vue").read_text(encoding="utf-8")
        self.assertIn(':data-follow-tone="followStageToneOf(row)"', vue)
        self.assertIn("'surface-pipeline': followSurface === 'pipeline'", vue)
        self.assertIn("'surface-dossier': followSurface === 'dossier'", vue)
        self.assertIn("'surface-listing': followSurface === 'listing'", vue)

    def test_css_thicken_three_faces(self) -> None:
        css = (FE / "user" / "ArchiveBrowse.css").read_text(encoding="utf-8")
        for needle in (
            ".surface-pipeline .card[data-follow-tone='pending']",
            ".surface-pipeline .card[data-follow-tone='ok']",
            ".surface-pipeline .card[data-follow-tone]:not([data-follow-tone=''])",
            "var(--follow-tone)",
            ".surface-dossier .card",
            ".surface-listing .main-signal",
        ):
            self.assertIn(needle, css, f"CSS 缺 {needle}")
        # 阶段色挡跟 portal 壳色走，不得留死色表
        for dead in ("#6b8aa8", "#4f76d9", "#d08a32", "#4f9a6a", "#9aa3ad"):
            self.assertNotIn(dead, css, f"CSS 仍留死色 {dead}")

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
