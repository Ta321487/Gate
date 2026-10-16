"""§0 X-LIST XL-01：组合筛选 / 导出列 / 顶栏搜索，扫词才挂。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.features.list_crosscut import apply_list_crosscut_to_spec, resolve_list_crosscut_flags
from app.bake.features.proposal_caps import HUB_BYPASS_MODULES

REPO = Path(__file__).resolve().parents[2]


def _spec(body: str = "") -> dict:
    return attach_accept(
        {
            "domain": "DOM-LIBRARY",
            "title": "图书借阅管理系统",
            "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
            "features": [],
            "archetype": "ARCH-FLOW",
        },
        body,
    )


class ListCrosscutFeatureTests(unittest.TestCase):
    def test_hub_bypass_lists_list_crosscut(self) -> None:
        self.assertIn("list_crosscut", HUB_BYPASS_MODULES)

    def test_empty_opening_skips_flags(self) -> None:
        flags = resolve_list_crosscut_flags("实现图书借阅与归还。", "图书借阅管理系统")
        self.assertFalse(flags["advancedFilter"])
        self.assertFalse(flags["exportColumns"])
        self.assertFalse(flags["globalSearch"])
        self.assertFalse(flags["recycle"])
        self.assertFalse(flags["batchDelete"])
        self.assertFalse(flags["batchReview"])

    def test_scan_terms_open_flags(self) -> None:
        flags = resolve_list_crosscut_flags(
            "管理端支持高级筛选与导出字段勾选，门户提供全局搜索。另有回收站、批量删除和批量通过。",
            "",
        )
        self.assertTrue(flags["advancedFilter"])
        self.assertTrue(flags["exportColumns"])
        self.assertTrue(flags["globalSearch"])
        self.assertTrue(flags["recycle"])
        self.assertTrue(flags["batchDelete"])
        self.assertTrue(flags["batchReview"])

    def test_apply_spec_empty_has_no_labels(self) -> None:
        out = apply_list_crosscut_to_spec(_spec(), "")
        labels = (out.get("schema") or {}).get("labels") or {}
        self.assertNotIn("listFilterStatus", labels)
        self.assertNotIn("topSearchPlaceholder", labels)
        flags = (out.get("schema") or {}).get("listCrosscut") or {}
        self.assertFalse(flags.get("advancedFilter"))

    def test_apply_spec_with_terms_sets_labels(self) -> None:
        body = "需要组合筛选、导出列勾选和顶栏搜索。"
        out = apply_list_crosscut_to_spec(_spec(body=body), body)
        labels = (out.get("schema") or {}).get("labels") or {}
        self.assertTrue(str(labels.get("listFilterStatus") or "").strip())
        self.assertTrue(str(labels.get("exportColumnsTitle") or "").strip())
        self.assertTrue(str(labels.get("topSearchPlaceholder") or "").strip())
        blob = " ".join(str(v) for v in labels.values()).lower()
        for bad in ("bake", "dom-", "开题", "工厂"):
            self.assertNotIn(bad, blob, bad)

    def test_recycle_turns_on_soft_delete_and_batch_review(self) -> None:
        body = "客户档案支持软删除，删除后可恢复。"
        out = apply_list_crosscut_to_spec(_spec(body=body), body)
        archive = (((out.get("schema") or {}).get("entities") or {}).get("archive") or {})
        self.assertTrue(archive.get("softDelete"))
        labels = (out.get("schema") or {}).get("labels") or {}
        self.assertTrue(str(labels.get("recycleBinLabel") or "").strip())
        self.assertFalse((out.get("schema") or {}).get("listCrosscut", {}).get("batchReview"))
        ctrl = (
            REPO / "skeletons/baseline/backend/src/main/java/com/thesis/controller/ArchiveController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("String listStatus", ctrl)
        self.assertIn("String createdFrom", ctrl)
        self.assertIn("batch-delete", ctrl)
        self.assertIn("deletedOnly", ctrl)
        for rel in (
            "skeletons/baseline/backend/src/main/java/com/thesis/capability/ArchiveStore.java",
            "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/ArchiveStore.java",
            "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/ArchiveStore.java",
        ):
            text = (REPO / rel).read_text(encoding="utf-8")
            self.assertIn("String listStatus", text, rel)
            self.assertIn("created_at >= ?", text, rel)
            self.assertIn("deleted_at IS NOT NULL", text, rel)


if __name__ == "__main__":
    unittest.main()
