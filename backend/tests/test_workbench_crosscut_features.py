"""§0 X-DASH 通识横切：工作台角标/快捷入口 + XD-02 PV/单据/定时任务台。"""

from __future__ import annotations

from tests._vue_src import vue_src

import re
import unittest
from pathlib import Path

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_sql import domain_sql
from app.bake.features.proposal_caps import HUB_BYPASS_MODULES
from app.bake.features.workbench_crosscut import apply_workbench_crosscut_to_spec

REPO = Path(__file__).resolve().parents[2]

_DASH_LABEL_KEYS = (
    "dashShortcutsTitle",
    "dashTodoTitle",
    "dashScopedHint",
    "dashPvTitle",
    "dashPvTotalLabel",
    "myDocsTitle",
    "myDocsEmptyHint",
    "scheduleJobsMenu",
    "scheduleJobsHint",
)


def _spec(domain: str = "DOM-LIBRARY", title: str = "图书借阅管理系统") -> dict:
    return attach_accept(
        {
            "domain": domain,
            "title": title,
            "capabilities": list(DOMAIN_CAPABILITIES[domain]),
            "features": [],
            "archetype": "ARCH-FLOW",
        },
        "",
    )


class WorkbenchCrosscutFeatureTests(unittest.TestCase):
    def test_hub_bypass_lists_workbench_crosscut(self) -> None:
        self.assertIn("workbench_crosscut", HUB_BYPASS_MODULES)

    def test_apply_spec_seeds_labels_and_shortcuts(self) -> None:
        out = apply_workbench_crosscut_to_spec(_spec(), "")
        labels = (out.get("schema") or {}).get("labels") or {}
        for key in _DASH_LABEL_KEYS:
            self.assertTrue(str(labels.get(key) or "").strip(), f"label {key}")
        wb = (out.get("schema") or {}).get("workbench") or {}
        self.assertIn("shortcuts", wb)
        self.assertIsInstance(wb["shortcuts"], list)
        self.assertIn("myDocs", wb)
        admin = ((out.get("schema") or {}).get("menus") or {}).get("admin") or []
        self.assertTrue(any(m.get("key") == "schedule_jobs" for m in admin), "schedule_jobs menu")

    def test_attach_accept_includes_dash_labels(self) -> None:
        labels = ((_spec().get("schema") or {}).get("labels") or {})
        for key in _DASH_LABEL_KEYS:
            self.assertTrue(str(labels.get(key) or "").strip(), f"attach label {key}")

    def test_sys_site_stat_injected_on_bake(self) -> None:
        sql = domain_sql("DOM-LIBRARY", "thesis_dash_x", title="图书借阅管理系统")
        self.assertIn("CREATE TABLE IF NOT EXISTS sys_site_stat", sql)

    def test_dashboard_controller_counts(self) -> None:
        text = (
            REPO
            / "skeletons/baseline/backend/src/main/java/com/thesis/controller/TicketDashboardController.java"
        ).read_text(encoding="utf-8")
        self.assertIn('/counts', text)
        self.assertIn("todoScopedByRole", text)
        self.assertIn("TicketStore.dashboard(userRole, uid, superAdmin)", text)
        self.assertIn("SiteStatStore.snapshot", text)
        # 无单据域 prune TicketStore 后仍须发出买家/用户数
        self.assertIn("UserStore.countByRole", text)
        self.assertIn('putIfAbsent("userTotal"', text)

    def test_three_ticket_dash_ops_scope(self) -> None:
        paths = [
            REPO
            / "skeletons/baseline/backend/src/main/java/com/thesis/capability/TicketDashOps.java",
            REPO
            / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/TicketDashOps.java",
            REPO
            / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/TicketDashOps.java",
        ]
        for p in paths:
            text = p.read_text(encoding="utf-8")
            self.assertIn("dashboard(String readerRole, String scopeUid, boolean superAdmin)", text, str(p))
            self.assertIn("todoScopedByRole", text, str(p))
            self.assertIn("assignee_username", text, str(p))

    def test_three_site_stat_stores(self) -> None:
        paths = [
            REPO
            / "skeletons/baseline/backend/src/main/java/com/thesis/service/SiteStatStore.java",
            REPO
            / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/service/SiteStatStore.java",
            REPO
            / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/service/SiteStatStore.java",
        ]
        for p in paths:
            text = p.read_text(encoding="utf-8")
            self.assertIn("bumpPv", text, str(p))
            self.assertIn("snapshot", text, str(p))
            self.assertIn("sys_site_stat", text, str(p))

    def test_schedule_and_site_stat_controllers(self) -> None:
        sc = (
            REPO
            / "skeletons/baseline/backend/src/main/java/com/thesis/controller/ScheduleJobsController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/admin/schedule-jobs", sc)
        self.assertIn("armed", sc)
        # 只列本包已启用：禁农产包串出台「影院/课时」灰项
        self.assertIn("addIfArmed", sc)
        self.assertIn("SeatStore.enabled()", sc)
        self.assertIn("UserStore.postMuteEnabled()", sc)
        self.assertIn("ArchiveStore.hasStartAt()", sc)
        st = (
            REPO
            / "skeletons/baseline/backend/src/main/java/com/thesis/controller/SiteStatController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/site-stat", st)
        self.assertIn("bumpPv", st)

    def test_fe_badges_and_shortcuts(self) -> None:
        layout = (
            REPO / "skeletons/baseline/frontend/src/layouts/AdminLayout.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/admin/dashboard/counts", layout)
        self.assertIn("pendingOrders", layout)
        self.assertIn("menuBadge", layout)
        dash = (
            REPO / "skeletons/baseline/frontend/src/views/admin/TicketDashboard.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("shortcuts", dash)
        self.assertIn("workbench?.shortcuts", dash)
        self.assertIn("withNav('/admin/tickets')", dash)
        self.assertIn("todoScopedByRole", dash)
        self.assertIn("pvToday", dash)

    def test_fe_xd02_surfaces(self) -> None:
        profile = vue_src((
            REPO / "skeletons/baseline/frontend/src/views/Profile.vue"
        ))
        self.assertIn("myDocLinks", profile)
        self.assertIn("myDocsTitle", profile)
        # 管理/商家岗不得展示买家「我的单据」浅链
        self.assertIn("audience.value !== 'user'", profile)
        portal = (
            REPO / "skeletons/baseline/frontend/src/layouts/PortalLayout.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/site-stat/pv", portal)
        jobs = (
            REPO / "skeletons/baseline/frontend/src/views/admin/ScheduleJobsAdmin.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/admin/schedule-jobs", jobs)
        routes = (
            REPO / "skeletons/baseline/frontend/src/utils/menuRoutes.js"
        ).read_text(encoding="utf-8")
        self.assertIn("schedule_jobs", routes)
        router = (
            REPO / "skeletons/baseline/frontend/src/router/index.js"
        ).read_text(encoding="utf-8")
        self.assertGreaterEqual(len(re.findall(r"schedule-jobs", router)), 5)


if __name__ == "__main__":
    unittest.main()
