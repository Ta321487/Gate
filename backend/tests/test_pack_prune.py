"""学生包胖骨架裁剪：未挂岛不得残留 Store；挂上的不得误删。"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from app.bake.pack_prune import (
    _fe_import_rels,
    _strip_type_usages,
    evaluate_pack_lean_gate,
    prune_student_pack,
    scan_forbidden_island_files,
)


REPO = Path(__file__).resolve().parents[2]
BASELINE_JAVA = (
    REPO
    / "skeletons/baseline/backend/src/main/java/com/thesis"
)
BASELINE_FE = REPO / "skeletons/baseline/frontend/src"


class PackPruneTests(unittest.TestCase):
    def test_shop_prunes_blind_box_and_exam(self) -> None:
        if not BASELINE_JAVA.is_dir():
            self.skipTest("baseline skeleton missing")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            java_dst = dest / "backend/src/main/java/com/demo/shop"
            fe_dst = dest / "frontend/src"
            java_dst.mkdir(parents=True)
            # 拷贝若干关键路径
            for rel in (
                "capability/BlindBoxStore.java",
                "capability/OrderStore.java",
                "capability/ArchiveStore.java",
                "capability/TicketStore.java",
                "capability/RecommendStore.java",
                "config/TicketPolicy.java",
                "service/ExamStore.java",
                "service/SeatStore.java",
                "config/DomainRuntimeBinder.java",
                "controller/BlindBoxController.java",
                "controller/ExamController.java",
                "controller/OrderController.java",
                "controller/TicketController.java",
                "controller/GateController.java",
            ):
                src = BASELINE_JAVA / rel
                if not src.is_file():
                    continue
                out = java_dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out)
            if (BASELINE_FE / "router/index.js").is_file():
                (fe_dst / "router").mkdir(parents=True, exist_ok=True)
                shutil.copy2(BASELINE_FE / "router/index.js", fe_dst / "router/index.js")
            for vue in (
                "views/admin/BlindPoolsAdmin.vue",
                "views/ExamPapers.vue",
                "views/admin/ExamPapersAdmin.vue",
                "views/user/SlotBook.vue",
                "views/user/MyCoupons.vue",
            ):
                src = BASELINE_FE / vue
                if src.is_file():
                    out = fe_dst / vue
                    out.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, out)
            for rel in (
                "capability/CouponStore.java",
                "capability/SlotStore.java",
                "controller/CouponController.java",
            ):
                src = BASELINE_JAVA / rel
                if src.is_file():
                    out = java_dst / rel
                    out.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, out)

            spec = {
                "domain": "DOM-SHOP",
                "capabilities": [
                    "archive",
                    "order_lines",
                    "quota",
                    "wallet",
                    "dm",
                    "favorites",
                    "order_review",
                    "guestbook",
                ],
            }
            stats = prune_student_pack(dest, spec)
            self.assertGreater(stats["deleted_count"], 0)
            self.assertFalse((java_dst / "capability/BlindBoxStore.java").exists())
            self.assertFalse((java_dst / "service/ExamStore.java").exists())
            self.assertFalse((java_dst / "service/SeatStore.java").exists())
            self.assertFalse((java_dst / "capability/CouponStore.java").exists())
            self.assertFalse((java_dst / "capability/SlotStore.java").exists())
            self.assertFalse((java_dst / "capability/TicketStore.java").exists())
            self.assertFalse((java_dst / "config/TicketPolicy.java").exists())
            self.assertFalse((java_dst / "controller/TicketController.java").exists())
            self.assertFalse((fe_dst / "views/user/SlotBook.vue").exists())
            self.assertFalse((fe_dst / "views/user/MyCoupons.vue").exists())
            self.assertTrue((java_dst / "capability/OrderStore.java").exists())
            self.assertTrue((java_dst / "capability/ArchiveStore.java").exists())
            order = (java_dst / "capability/OrderStore.java").read_text(encoding="utf-8")
            self.assertNotIn("BlindBoxStore", order)
            self.assertNotIn("ExamStore", order)
            archive = (java_dst / "capability/ArchiveStore.java").read_text(encoding="utf-8")
            self.assertNotIn("TicketStore", archive)
            binder = (java_dst / "config/DomainRuntimeBinder.java").read_text(encoding="utf-8")
            self.assertNotIn("import com.thesis.capability.BlindBoxStore", binder)
            self.assertNotIn("BlindBoxStore.configure", binder)
            self.assertNotIn("TicketStore", binder)
            self.assertNotIn("TicketPolicy", binder)
            gate = (java_dst / "controller/GateController.java").read_text(encoding="utf-8")
            self.assertNotIn("TicketStore", gate)
            router = (fe_dst / "router/index.js").read_text(encoding="utf-8")
            self.assertNotIn("SlotBook.vue", router)
            self.assertNotIn("MyCoupons.vue", router)
            self.assertNotIn("MyTickets.vue", router)

    def test_fe_import_rels_normalizes_parent_paths(self) -> None:
        got = _fe_import_rels(
            "import ArchiveFieldControl from '../../components/ArchiveFieldControl.vue'\n"
            "import { x } from '@/utils/authEntry'\n"
        )
        self.assertIn("components/ArchiveFieldControl.vue", got)
        self.assertIn("utils/authEntry.js", got)

    def test_strip_coupon_and_roster_ternary(self) -> None:
        loyalty = """
    public static Map<String, Object> matchCoupon(String username, String code, double amountYuan) {
        Map<String, Object> out = new LinkedHashMap<>();
        if (!couponEnabled || code == null || code.isBlank()) return out;
        if (!CouponStore.enabled()) {
            out.put("message", "券码无效");
            return out;
        }
        return CouponStore.matchForCheckout(username, code, amountYuan);
    }
    public static void onOrderCompleted(long orderId) {
        if (!pointsEnabled) return;
        LoyaltyStore.addPoints("u", 1, "x");
    }
"""
        out = _strip_type_usages(loyalty, "CouponStore")
        self.assertNotIn("CouponStore", out)
        self.assertIn('out.put("message", "券码无效");', out)
        self.assertIn("return out;", out)
        self.assertIn("if (!pointsEnabled) return;", out)
        self.assertNotIn("matchForCheckout", out)

        roster = """
        java.util.Set<String> onDuty = StaffRosterStore.enabled()
                ? StaffRosterStore.onDutyUsernames(java.time.LocalDate.now().toString())
                : java.util.Set.of();
"""
        out2 = _strip_type_usages(roster, "StaffRosterStore")
        self.assertNotIn("StaffRosterStore", out2)
        self.assertIn("java.util.Set.of()", out2)
        self.assertNotIn("false", out2.split("onDuty")[1][:40])

        weigh = (
            "Map<String, Object> priced = WeighSaleStore.priceLine("
            "item, qty, extraForItem(lineExtras, itemId));\n"
        )
        out3 = _strip_type_usages(weigh, "WeighSaleStore")
        self.assertEqual(out3.strip(), "Map<String, Object> priced = item;")

        seat = """
        String st = "x";
        if (SeatStore.enabled()) {
            SeatStore.assertOrderRefundOpen(orderId);
        } else if (!"shipped".equals(st)) {
            throw new IllegalStateException("仅已发货及之后状态可申请售后");
        }
"""
        out4 = _strip_type_usages(seat, "SeatStore")
        self.assertNotIn("SeatStore", out4)
        self.assertIn('if (!"shipped".equals(st))', out4)
        self.assertNotIn("else if", out4)

        oneline = "        if (BlindBoxStore.enabled()) BlindBoxStore.ensureSchema();\n"
        out5 = _strip_type_usages(oneline, "BlindBoxStore")
        self.assertNotIn("BlindBoxStore", out5)
        self.assertNotIn("if (false)", out5)
        self.assertNotIn("null;", out5)

        sched = """
            int n = TicketStore.autoPassStalePending();
            if (n > 0) log.info("auto-passed {}", n);
            int m = TicketStore.autoRejectStalePeerPending();
            if (m > 0) log.info("auto-rejected {}", m);
"""
        out6 = _strip_type_usages(sched, "TicketStore")
        self.assertNotIn("TicketStore", out6)
        self.assertIn("int n = 0", out6)
        self.assertIn("int m = 0", out6)
        self.assertNotIn("= null", out6)

    def test_exam_domain_keeps_exam_store(self) -> None:
        if not BASELINE_JAVA.is_dir():
            self.skipTest("baseline skeleton missing")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            java_dst = dest / "backend/src/main/java/com/demo/exam"
            java_dst.mkdir(parents=True)
            for rel in ("service/ExamStore.java", "capability/OrderStore.java"):
                src = BASELINE_JAVA / rel
                if not src.is_file():
                    continue
                out = java_dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out)
            prune_student_pack(
                dest,
                {"domain": "DOM-EXAM", "capabilities": ["archive", "exam", "content"]},
            )
            self.assertTrue((java_dst / "service/ExamStore.java").exists())

    def test_ticket_flow_keeps_ticket_store(self) -> None:
        if not BASELINE_JAVA.is_dir():
            self.skipTest("baseline skeleton missing")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            java_dst = dest / "backend/src/main/java/com/demo/borrow"
            java_dst.mkdir(parents=True)
            for rel in (
                "capability/TicketStore.java",
                "capability/ArchiveStore.java",
                "config/TicketPolicy.java",
                "controller/TicketController.java",
                "service/ExamStore.java",
            ):
                src = BASELINE_JAVA / rel
                if not src.is_file():
                    continue
                out = java_dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out)
            prune_student_pack(
                dest,
                {
                    "domain": "DOM-LIBRARY",
                    "capabilities": ["archive", "ticket_flow", "content", "org_users"],
                },
            )
            self.assertTrue((java_dst / "capability/TicketStore.java").exists())
            self.assertTrue((java_dst / "config/TicketPolicy.java").exists())
            self.assertTrue((java_dst / "controller/TicketController.java").exists())
            self.assertFalse((java_dst / "service/ExamStore.java").exists())

    def test_p3lean_blocks_forbidden_leftovers(self) -> None:
        if not BASELINE_JAVA.is_dir():
            self.skipTest("baseline skeleton missing")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            java_dst = dest / "backend/src/main/java/com/demo/shop"
            java_dst.mkdir(parents=True)
            for rel in (
                "capability/OrderStore.java",
                "capability/BlindBoxStore.java",
                "service/ExamStore.java",
            ):
                src = BASELINE_JAVA / rel
                if not src.is_file():
                    continue
                out = java_dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out)
            spec = {
                "domain": "DOM-SHOP",
                "capabilities": ["archive", "order_lines", "quota", "wallet"],
            }
            hits = scan_forbidden_island_files(dest, spec)
            self.assertTrue(any("BlindBox" in h for h in hits))
            self.assertTrue(any("Exam" in h for h in hits))
            lean = evaluate_pack_lean_gate(dest, spec)
            self.assertFalse(lean["ok"])
            prune_student_pack(dest, spec)
            self.assertEqual(scan_forbidden_island_files(dest, spec), [])
            self.assertTrue(evaluate_pack_lean_gate(dest, spec)["ok"])

    def test_invite_codes_pruned_when_opening_unwanted(self) -> None:
        """开题未挂邀请码：码池 Store/管理页/路由/注册核销一并裁掉。"""
        if not BASELINE_JAVA.is_dir() or not BASELINE_FE.is_dir():
            self.skipTest("baseline skeleton missing")
        store = BASELINE_JAVA / "service/InviteCodeStore.java"
        auth = BASELINE_JAVA / "controller/AuthController.java"
        sess = BASELINE_JAVA / "controller/AuthSessionController.java"
        vue = BASELINE_FE / "views/admin/InviteCodesAdmin.vue"
        router_src = BASELINE_FE / "router/index.js"
        if not all(p.is_file() for p in (store, auth, sess, vue, router_src)):
            self.skipTest("invite baseline missing")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            java_dst = dest / "backend/src/main/java/com/demo/shop"
            fe_dst = dest / "frontend/src"
            java_dst.mkdir(parents=True)
            for rel, src in (
                ("service/InviteCodeStore.java", store),
                ("controller/AuthController.java", auth),
                ("controller/AuthSessionController.java", sess),
                ("capability/OrderStore.java", BASELINE_JAVA / "capability/OrderStore.java"),
            ):
                out = java_dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out)
            vue_out = fe_dst / "views/admin/InviteCodesAdmin.vue"
            vue_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(vue, vue_out)
            router = fe_dst / "router/index.js"
            router.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(router_src, router)
            menu_routes = BASELINE_FE / "utils/menuRoutes.js"
            if menu_routes.is_file():
                mr_out = fe_dst / "utils/menuRoutes.js"
                mr_out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(menu_routes, mr_out)
            spec = {
                "domain": "DOM-SHOP",
                "capabilities": ["archive", "order_lines", "quota", "wallet"],
                "schema": {
                    "authPolicy": {"requireInvite": 0},
                    "menus": {"admin": [{"key": "products", "title": "商品"}]},
                },
            }
            self.assertTrue(
                any("InviteCode" in h for h in scan_forbidden_island_files(dest, spec))
            )
            prune_student_pack(dest, spec)
            self.assertFalse((java_dst / "service/InviteCodeStore.java").is_file())
            self.assertFalse(vue_out.is_file())
            auth_txt = (java_dst / "controller/AuthController.java").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("InviteCodeStore", auth_txt)
            self.assertNotIn("consumeOrThrow", auth_txt)
            sess_txt = (java_dst / "controller/AuthSessionController.java").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("InviteCodeStore", sess_txt)
            self.assertNotIn("invite-codes", sess_txt)
            rt = router.read_text(encoding="utf-8")
            self.assertNotIn("InviteCodesAdmin.vue", rt)
            self.assertNotIn("invite-codes", rt)
            if (fe_dst / "utils/menuRoutes.js").is_file():
                self.assertNotIn(
                    "invite_codes",
                    (fe_dst / "utils/menuRoutes.js").read_text(encoding="utf-8"),
                )
            self.assertEqual(scan_forbidden_island_files(dest, spec), [])

        # 开题明确要邀请码时保留（独立工作区，避免上轮已 scrub 路由导致 orphan 误删）
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            java_dst = dest / "backend/src/main/java/com/demo/shop"
            fe_dst = dest / "frontend/src"
            java_dst.mkdir(parents=True)
            for rel, src in (
                ("service/InviteCodeStore.java", store),
                ("controller/AuthController.java", auth),
                ("capability/OrderStore.java", BASELINE_JAVA / "capability/OrderStore.java"),
            ):
                out = java_dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out)
            vue_out = fe_dst / "views/admin/InviteCodesAdmin.vue"
            vue_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(vue, vue_out)
            router = fe_dst / "router/index.js"
            router.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(router_src, router)
            keep_spec = {
                "domain": "DOM-SHOP",
                "capabilities": ["archive", "order_lines", "quota", "wallet"],
                "schema": {
                    "authPolicy": {"requireInvite": 1},
                    "menus": {
                        "admin": [
                            {"key": "invite_codes", "title": "邀请码"},
                            {"key": "products", "title": "商品"},
                        ]
                    },
                },
            }
            prune_student_pack(dest, keep_spec)
            self.assertTrue((java_dst / "service/InviteCodeStore.java").is_file())
            self.assertTrue(vue_out.is_file())
            self.assertIn("InviteCodesAdmin.vue", router.read_text(encoding="utf-8"))

    def test_shop_keeps_ticket_dashboard_workbench(self) -> None:
        """未挂 ticket_flow 仍保留仪表盘；p3lean 不得当残留毒区。"""
        if not BASELINE_JAVA.is_dir() or not BASELINE_FE.is_dir():
            self.skipTest("baseline skeleton missing")
        dash_java = BASELINE_JAVA / "controller/TicketDashboardController.java"
        dash_vue = BASELINE_FE / "views/admin/TicketDashboard.vue"
        ticket_store = BASELINE_JAVA / "capability/TicketStore.java"
        if not dash_java.is_file() or not dash_vue.is_file():
            self.skipTest("TicketDashboard baseline missing")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            java_dst = dest / "backend/src/main/java/com/demo/shop"
            fe_dst = dest / "frontend/src"
            java_dst.mkdir(parents=True)
            fe_dst.mkdir(parents=True)
            for rel, src in (
                ("controller/TicketDashboardController.java", dash_java),
                ("capability/TicketStore.java", ticket_store),
                ("capability/OrderStore.java", BASELINE_JAVA / "capability/OrderStore.java"),
            ):
                if not src.is_file():
                    continue
                out = java_dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out)
            vue_out = fe_dst / "views/admin/TicketDashboard.vue"
            vue_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dash_vue, vue_out)
            charts = BASELINE_FE / "components/DashboardCharts.vue"
            if charts.is_file():
                charts_out = fe_dst / "components/DashboardCharts.vue"
                charts_out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(charts, charts_out)
            spec = {
                "domain": "DOM-SHOP",
                "capabilities": ["archive", "order_lines", "quota", "wallet"],
            }
            # 登记在 ticket 岛内时，lean 也不得误杀工作台
            hits_before = scan_forbidden_island_files(dest, spec)
            self.assertFalse(
                any("TicketDashboard" in h for h in hits_before),
                hits_before,
            )
            self.assertTrue(any("TicketStore" in h for h in hits_before), hits_before)
            # 路由默认进工作台；裁岛不得把 dashboard 路由项 scrub 掉
            router = fe_dst / "router/index.js"
            router.parent.mkdir(parents=True, exist_ok=True)
            router.write_text(
                "export default [{ path: '/admin', children: [\n"
                "  { path: '', redirect: '/admin/dashboard' },\n"
                "  { path: 'dashboard', component: () => "
                "import('../views/admin/TicketDashboard.vue') },\n"
                "  { path: 'tickets', component: () => "
                "import('../views/admin/TicketsAdmin.vue') },\n"
                "] }]\n",
                encoding="utf-8",
            )
            tickets_vue = fe_dst / "views/admin/TicketsAdmin.vue"
            tickets_vue.write_text("<template></template>\n", encoding="utf-8")
            prune_student_pack(dest, spec)
            self.assertTrue(
                (java_dst / "controller/TicketDashboardController.java").is_file()
            )
            self.assertTrue((fe_dst / "views/admin/TicketDashboard.vue").is_file())
            self.assertTrue((fe_dst / "components/DashboardCharts.vue").is_file())
            self.assertFalse((java_dst / "capability/TicketStore.java").is_file())
            rt = router.read_text(encoding="utf-8")
            self.assertIn("TicketDashboard.vue", rt)
            self.assertIn("path: 'dashboard'", rt)
            self.assertNotIn("TicketsAdmin.vue", rt)
            self.assertEqual(scan_forbidden_island_files(dest, spec), [])
            self.assertTrue(evaluate_pack_lean_gate(dest, spec)["ok"])


if __name__ == "__main__":
    unittest.main()
