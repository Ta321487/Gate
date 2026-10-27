"""起包前布局闸 D1：台账覆盖 + 漏页/漏组件对账红灯（只验闸，不改学生页）。"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from app.bake import layout_inventory as li
from app.bake.layout_inventory import (
    BASELINE_KNOWN_ISSUES,
    LayoutRow,
    assert_layout_inventory_ok,
    generate_layout_inventory,
    inventory_coverage,
    issue_key,
    reconcile_layout_inventory,
)


def _issue_key(issue: li.LayoutIssue) -> tuple[str, str]:
    return issue_key(issue)


class LayoutInventoryD1Tests(unittest.TestCase):
    def test_coverage_views_layouts_components(self) -> None:
        rows = generate_layout_inventory()
        cov = inventory_coverage(rows)
        self.assertEqual(cov["views_in_ledger"], cov["views_on_disk"])
        self.assertEqual(cov["layouts_in_ledger"], cov["layouts_on_disk"])
        self.assertEqual(cov["components_in_ledger"], cov["components_on_disk"])
        self.assertGreaterEqual(cov["views_on_disk"], 1)
        self.assertGreaterEqual(cov["layouts_on_disk"], 1)
        self.assertGreaterEqual(cov["components_on_disk"], 1)

    def test_shared_baseline_rows_present(self) -> None:
        """共享基线优先入账（壳 / AuthShell / 列表主路径）。"""
        rows = generate_layout_inventory()
        by_vue = {r.vue for r in rows}
        for rel in (
            "layouts/PortalLayout.vue",
            "layouts/AdminLayout.vue",
            "layouts/WorkLayout.vue",
            "components/AuthShell.vue",
            "views/user/ArchiveBrowse.vue",
            "views/user/MyTickets.vue",
        ):
            self.assertIn(rel, by_vue, rel)
        self.assertEqual(sum(1 for r in rows if r.kind == "shell"), 3)
        auth = next(r for r in rows if r.vue == "components/AuthShell.vue")
        self.assertEqual(auth.kind, "component")
        self.assertTrue(auth.hosts, "AuthShell 须有 hosts（登录等页）")

    def test_component_hosts_from_import_graph(self) -> None:
        rows = generate_layout_inventory()
        bell = next(r for r in rows if r.vue == "components/MessageBell.vue")
        self.assertTrue(
            any("PortalLayout" in h for h in bell.hosts),
            bell.hosts,
        )

    def test_surfaces_axis_tagged_and_not_cross_polluted(self) -> None:
        """多脸按轴标记；ArchiveBrowse 不得因 setup 读 portalHome 而挂门户皮。"""
        rows = generate_layout_inventory()
        ab = next(
            r
            for r in rows
            if r.vue == "views/user/ArchiveBrowse.vue"
            and r.row_id == "page:user:/archive"
        )
        self.assertTrue(ab.surfaces, "ArchiveBrowse 模板有 data-*-surface")
        for s in ab.surfaces:
            self.assertIn(":", s, s)
            self.assertFalse(s.startswith("portalHome:"), s)
        home = next(
            r
            for r in rows
            if r.vue == "views/user/PortalHome.vue" and r.row_id == "page:user:/home"
        )
        self.assertTrue(
            any(s.startswith("portalHome:") for s in home.surfaces),
            home.surfaces,
        )

    def test_no_baseline_orphan_components(self) -> None:
        """基线组件不得长期空 hosts；孤儿探测能力见 test_empty_hosts_reds。"""
        issues = reconcile_layout_inventory()
        orphans = [i for i in issues if i.code == "empty_hosts"]
        self.assertEqual(orphans, [], orphans)

    def test_inline_drawer_and_card_voice_in_ledger(self) -> None:
        """抽屉入 dialog 行；ArchiveBrowse 卡面叙事入 surfaces（册 D）。"""
        rows = generate_layout_inventory()
        drawer_ids = {
            r.row_id
            for r in rows
            if r.kind == "dialog" and "detailVisible" in r.row_id
        }
        self.assertTrue(
            any("ArchiveBrowse" in i for i in drawer_ids),
            drawer_ids,
        )
        self.assertTrue(
            any("MyArchive" in i for i in drawer_ids),
            drawer_ids,
        )
        ab = next(
            r
            for r in rows
            if r.vue == "views/user/ArchiveBrowse.vue"
            and r.row_id == "page:user:/archive"
        )
        for voice in ("cardVoice:catalog", "cardVoice:story", "cardVoice:board"):
            self.assertIn(voice, ab.surfaces, ab.surfaces)

    def test_menu_admin_hub_paths_in_router(self) -> None:
        """复用用户端 Vue 的管理端 path 仍须进路由集合。"""
        paths = li.collect_router_paths(li.frontend_src())
        self.assertIn("/admin/messages", paths)
        self.assertIn("/admin/dm", paths)

    def test_baseline_reconcile_only_known_debt(self) -> None:
        """漏文件 / A↔B / hosts 不一致须绿；已知孤儿只记账。"""
        rows = generate_layout_inventory()
        issues = reconcile_layout_inventory(rows)
        unexpected = [i for i in issues if _issue_key(i) not in BASELINE_KNOWN_ISSUES]
        self.assertEqual(
            unexpected,
            [],
            "非预期对账红灯:\n" + "\n".join(str(i) for i in unexpected),
        )
        known_hit = {_issue_key(i) for i in issues}
        missing_known = BASELINE_KNOWN_ISSUES - known_hit
        self.assertFalse(
            missing_known,
            f"已知债未再报（若已挂回请清空 BASELINE_KNOWN_ISSUES）: {missing_known}",
        )

    def test_missing_component_reds(self) -> None:
        """磁盘有、台账无 → missing_component 红。"""
        rows = generate_layout_inventory()
        fake = "components/__GateProbeOrphan__.vue"
        real_list = li.list_vue_rel

        def _list(s: Path, *parts: str) -> list[str]:
            out = real_list(s, *parts)
            if parts == ("components",):
                return out + [fake]
            return out

        with mock.patch.object(li, "list_vue_rel", side_effect=_list):
            issues = reconcile_layout_inventory(rows)
        self.assertTrue(
            any(i.code == "missing_component" and fake in i.detail for i in issues),
            issues,
        )

    def test_empty_hosts_reds(self) -> None:
        """hosts 为空 → empty_hosts 红（验闸能力）。"""
        real = generate_layout_inventory()
        probe = LayoutRow(
            row_id="component:components/NoHostProbe.vue",
            kind="component",
            side="shared",
            path="",
            vue="components/NoHostProbe.vue",
            hosts=[],
        )
        mixed = [r for r in real if r.vue != probe.vue] + [probe]
        real_list = li.list_vue_rel

        def _list(s: Path, *parts: str) -> list[str]:
            out = real_list(s, *parts)
            if parts == ("components",):
                return out + [probe.vue]
            return out

        with mock.patch.object(li, "list_vue_rel", side_effect=_list):
            with mock.patch.object(li, "build_import_graph", return_value={}):
                issues = reconcile_layout_inventory(mixed)
        self.assertTrue(
            any(i.code == "empty_hosts" and "NoHostProbe" in i.detail for i in issues),
            issues,
        )

    def test_assert_ok_when_no_known_debt(self) -> None:
        if BASELINE_KNOWN_ISSUES:
            self.skipTest("基线仍有已知债，不要求 assert_layout_inventory_ok 零红")
        assert_layout_inventory_ok()


if __name__ == "__main__":
    unittest.main()
