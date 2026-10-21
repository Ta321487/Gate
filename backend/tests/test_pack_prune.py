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
    scan_factory_notes_leaks,
    scan_forbidden_island_files,
    prune_shell_chrome_in_workspace,
    scrub_factory_notes_from_source,
    scrub_factory_notes_in_workspace,
    scan_shell_chrome_leaks,
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

    def test_fe_import_rels_follows_sfc_src_siblings(self) -> None:
        """ArchiveBrowse.vue 拆出 setup.js/css 后，prune 须跟 src= 才能扫到组件 import。"""
        got = _fe_import_rels(
            '<script setup src="./ArchiveBrowse.setup.js"></script>\n'
            '<style scoped src="./ArchiveBrowse.css"></style>\n',
            from_rel="views/user/ArchiveBrowse.vue",
        )
        self.assertIn("views/user/ArchiveBrowse.setup.js", got)
        self.assertIn("views/user/ArchiveBrowse.css", got)
        nested = _fe_import_rels(
            "import EmptyHint from '../../components/EmptyHint.vue'\n",
            from_rel="views/user/ArchiveBrowse.setup.js",
        )
        self.assertIn("components/EmptyHint.vue", nested)

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

        # 预约+未挂寄养：if (enabled) 岛路径 else 主路径 —— else 体必须留下
        boarding = """
        Map<String, Object> slot;
        if (BoardingStore.enabled()) {
            BoardingStore.assertStay(early);
            if (slotId > 0) {
                Map<String, Object> picked = getSlot(slotId);
                if (picked != null) stayItemId = 1L;
            }
            slotId = BoardingStore.holdFrom(early, stayItemId);
            rangeHeld = true;
            slot = getSlot(slotId);
        } else {
            slot = getSlot(slotId);
        }
        if (slot == null) throw new IllegalArgumentException("时段不存在");
        if (isPastSlot(slot)) {
            if (rangeHeld) BoardingStore.releaseRange(stayItemId, stayFromHeld, stayToHeld);
            throw new IllegalStateException("该时段已过，不可预约");
        }
        } catch (RuntimeException e) {
            if (rangeHeld) BoardingStore.releaseRange(stayItemId, stayFromHeld, stayToHeld);
            else db().update(
                    "UPDATE slot SET booked=GREATEST(booked-1,0) WHERE id=?", slotId);
            throw e;
        }
"""
        out7 = _strip_type_usages(boarding, "BoardingStore")
        self.assertNotIn("BoardingStore", out7)
        self.assertIn("slot = getSlot(slotId)", out7)
        self.assertIn('throw new IllegalArgumentException("时段不存在")', out7)
        self.assertNotRegex(out7, r"\bif\s*\([^)]*\)\s*null\s*;")
        self.assertNotIn("if (false)", out7)
        # 悬空 else 禁止；回滚名额须在 !(rangeHeld) 下保留
        self.assertNotRegex(out7, r"(?m)^\s*else\b")
        self.assertIn("UPDATE slot SET booked=GREATEST(booked-1,0)", out7)
        self.assertIn("if (!(rangeHeld))", out7)

        # releaseStay 布尔谓词：if (!releaseStay) 回滚名额 —— 抹成 false 后须留下回滚
        release_stay = """
        if (!BoardingStore.releaseStay(RESV, SLOT, resvId)) {
            db().update("UPDATE slot SET booked=GREATEST(booked-1,0) WHERE id=?", slotId);
        }
"""
        out8 = _strip_type_usages(release_stay, "BoardingStore")
        self.assertNotIn("BoardingStore", out8)
        self.assertNotIn("if (!null)", out8)
        self.assertNotIn("if (null)", out8)
        self.assertIn("UPDATE slot SET booked=GREATEST(booked-1,0)", out8)

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

    def test_parking_pass_pruned_when_schema_off(self) -> None:
        """未开 parkingPass：次卡 Store/页/路由一并裁掉；PARKING 域打开则保留。"""
        if not BASELINE_JAVA.is_dir() or not BASELINE_FE.is_dir():
            self.skipTest("baseline skeleton missing")
        store = BASELINE_JAVA / "service/ParkingPassStore.java"
        ctrl = BASELINE_JAVA / "controller/ParkingPassController.java"
        binder = BASELINE_JAVA / "config/DomainRuntimeBinder.java"
        slot = BASELINE_JAVA / "capability/SlotStore.java"
        vue_u = BASELINE_FE / "views/user/ParkingPasses.vue"
        vue_a = BASELINE_FE / "views/admin/ParkingPassAdmin.vue"
        router_src = BASELINE_FE / "router/index.js"
        if not all(p.is_file() for p in (store, ctrl, binder, slot, vue_u, vue_a, router_src)):
            self.skipTest("parking-pass baseline missing")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            java_dst = dest / "backend/src/main/java/com/demo/shop"
            fe_dst = dest / "frontend/src"
            java_dst.mkdir(parents=True)
            for rel, src in (
                ("service/ParkingPassStore.java", store),
                ("controller/ParkingPassController.java", ctrl),
                ("config/DomainRuntimeBinder.java", binder),
                ("capability/SlotStore.java", slot),
            ):
                out = java_dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out)
            for rel, src in (
                ("views/user/ParkingPasses.vue", vue_u),
                ("views/admin/ParkingPassAdmin.vue", vue_a),
            ):
                out = fe_dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out)
            router = fe_dst / "router/index.js"
            router.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(router_src, router)
            menu_routes = BASELINE_FE / "utils/menuRoutes.js"
            if menu_routes.is_file():
                mr_out = fe_dst / "utils/menuRoutes.js"
                mr_out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(menu_routes, mr_out)
            # 挂 slot_reserve 留住 SlotStore，专门验次卡引用被抹掉（而非整岛删掉预约）
            spec = {
                "domain": "DOM-SHOP",
                "capabilities": ["archive", "order_lines", "quota", "wallet", "slot_reserve"],
                "schema": {"parkingPass": False, "menus": {"admin": [], "user": []}},
            }
            self.assertTrue(
                any("ParkingPass" in h for h in scan_forbidden_island_files(dest, spec))
            )
            prune_student_pack(dest, spec)
            self.assertFalse((java_dst / "service/ParkingPassStore.java").is_file())
            self.assertFalse((java_dst / "controller/ParkingPassController.java").is_file())
            self.assertFalse((fe_dst / "views/user/ParkingPasses.vue").is_file())
            self.assertFalse((fe_dst / "views/admin/ParkingPassAdmin.vue").is_file())
            binder_txt = (java_dst / "config/DomainRuntimeBinder.java").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("ParkingPassStore", binder_txt)
            slot_txt = (java_dst / "capability/SlotStore.java").read_text(encoding="utf-8")
            self.assertNotIn("ParkingPassStore", slot_txt)
            rt = router.read_text(encoding="utf-8")
            self.assertNotIn("ParkingPasses.vue", rt)
            self.assertNotIn("ParkingPassAdmin.vue", rt)
            if (fe_dst / "utils/menuRoutes.js").is_file():
                mr = (fe_dst / "utils/menuRoutes.js").read_text(encoding="utf-8")
                self.assertNotIn("parking_pass", mr)
            self.assertEqual(scan_forbidden_island_files(dest, spec), [])

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            java_dst = dest / "backend/src/main/java/com/demo/park"
            fe_dst = dest / "frontend/src"
            java_dst.mkdir(parents=True)
            for rel, src in (
                ("service/ParkingPassStore.java", store),
                ("controller/ParkingPassController.java", ctrl),
            ):
                out = java_dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out)
            vue_out = fe_dst / "views/user/ParkingPasses.vue"
            vue_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(vue_u, vue_out)
            keep_spec = {
                "domain": "DOM-PARKING",
                "capabilities": ["archive", "slot_reserve"],
                "schema": {"parkingPass": True},
            }
            prune_student_pack(dest, keep_spec)
            self.assertTrue((java_dst / "service/ParkingPassStore.java").is_file())
            self.assertTrue(vue_out.is_file())

    def test_patient_profile_pruned_when_schema_off(self) -> None:
        """未开 patientProfile：就诊人 Store/页裁掉；开则保留。"""
        if not BASELINE_JAVA.is_dir() or not BASELINE_FE.is_dir():
            self.skipTest("baseline skeleton missing")
        store = BASELINE_JAVA / "service/PatientProfileStore.java"
        ctrl = BASELINE_JAVA / "controller/PatientProfileController.java"
        vue = BASELINE_FE / "views/user/PatientProfiles.vue"
        if not all(p.is_file() for p in (store, ctrl, vue)):
            self.skipTest("patient-profile baseline missing")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            java_dst = dest / "backend/src/main/java/com/demo/shop"
            fe_dst = dest / "frontend/src"
            for rel, src in (
                ("service/PatientProfileStore.java", store),
                ("controller/PatientProfileController.java", ctrl),
            ):
                out = java_dst / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out)
            vue_out = fe_dst / "views/user/PatientProfiles.vue"
            vue_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(vue, vue_out)
            spec = {
                "domain": "DOM-SHOP",
                "capabilities": ["archive", "order_lines"],
                "schema": {"patientProfile": False},
            }
            prune_student_pack(dest, spec)
            self.assertFalse((java_dst / "service/PatientProfileStore.java").is_file())
            self.assertFalse(vue_out.is_file())
            self.assertEqual(
                [h for h in scan_forbidden_island_files(dest, spec) if "PatientProfile" in h],
                [],
            )
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            java_dst = dest / "backend/src/main/java/com/demo/hosp"
            fe_dst = dest / "frontend/src"
            out = java_dst / "service/PatientProfileStore.java"
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(store, out)
            vue_out = fe_dst / "views/user/PatientProfiles.vue"
            vue_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(vue, vue_out)
            keep = {
                "domain": "DOM-HOSPITAL",
                "capabilities": ["archive", "slot_reserve"],
                "schema": {"patientProfile": True},
            }
            prune_student_pack(dest, keep)
            self.assertTrue(out.is_file())
            self.assertTrue(vue_out.is_file())

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

    def test_scrub_factory_notes_keeps_code_drops_factory_comments(self) -> None:
        src = (
            "// 开题挂了才出\n"
            "export const X = 1; // 正常说明\n"
            "const u = 'http://example.com/path'; // keep url\n"
            "/* §3 工厂注记 */\n"
            "const y = 2;\n"
            "<!-- bake 注入 -->\n"
            "<div/>\n"
        )
        out = scrub_factory_notes_from_source(src)
        self.assertNotIn("开题", out)
        self.assertNotIn("§3", out)
        self.assertNotIn("bake", out)
        self.assertIn("export const X = 1;", out)
        self.assertIn("// 正常说明", out)
        self.assertIn("http://example.com/path", out)
        self.assertIn("const y = 2;", out)

    def test_prune_shell_chrome_drops_side_rail_for_storefront(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            fe = dest / "frontend" / "src"
            (fe / "components").mkdir(parents=True)
            (fe / "layouts").mkdir(parents=True)
            (fe / "components" / "PortalSideRail.vue").write_text(
                "<template><aside/></template>\n", encoding="utf-8"
            )
            (fe / "layouts" / "PortalLayout.vue").write_text(
                "import PortalSideRail from '../components/PortalSideRail.vue'\n",
                encoding="utf-8",
            )
            spec = {"domain": "DOM-HOSPITAL", "shell_nav_style": "storefront"}
            self.assertTrue(scan_shell_chrome_leaks(dest, spec))
            deleted = prune_shell_chrome_in_workspace(dest, spec)
            self.assertIn("vue:components/PortalSideRail.vue", deleted)
            self.assertFalse((fe / "components" / "PortalSideRail.vue").is_file())
            self.assertEqual(scan_shell_chrome_leaks(dest, spec), [])

    def test_scrub_factory_notes_in_workspace_clears_listed_leaks(self) -> None:
        """门禁曾列的 js/css/vue 注记路径，工作区一键抹后须空。"""
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            fe = dest / "frontend" / "src"
            for rel in (
                "main.js",
                "router/index.js",
                "styles/accountFace.css",
                "styles/layout.css",
                "utils/notify.js",
                "utils/portalShellNav.js",
                "views/Profile.vue",
            ):
                path = fe / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    f"/* 开题 · §3 · 软皮 · 工厂腔 */\nexport const _{rel.replace('/', '_').replace('.', '_')} = 1\n",
                    encoding="utf-8",
                )
            self.assertGreaterEqual(len(scan_factory_notes_leaks(dest)), 7)
            touched = scrub_factory_notes_in_workspace(dest)
            self.assertGreaterEqual(len(touched), 7)
            self.assertEqual(scan_factory_notes_leaks(dest), [])

    def test_prune_drops_side_rail_when_not_marketplace(self) -> None:
        if not BASELINE_FE.is_dir():
            self.skipTest("baseline skeleton missing")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            fe_dst = dest / "frontend/src"
            (fe_dst / "components").mkdir(parents=True)
            (fe_dst / "layouts").mkdir(parents=True)
            (fe_dst / "router").mkdir(parents=True)
            rail_src = BASELINE_FE / "components/PortalSideRail.vue"
            layout_src = BASELINE_FE / "layouts/PortalLayout.vue"
            if not rail_src.is_file() or not layout_src.is_file():
                self.skipTest("PortalSideRail/PortalLayout missing")
            shutil.copy2(rail_src, fe_dst / "components/PortalSideRail.vue")
            shutil.copy2(layout_src, fe_dst / "layouts/PortalLayout.vue")
            (fe_dst / "router/index.js").write_text(
                "export default [{ path: '/', component: () => "
                "import('../layouts/PortalLayout.vue') }]\n",
                encoding="utf-8",
            )
            util = fe_dst / "utils/portalShellNav.js"
            util.parent.mkdir(parents=True, exist_ok=True)
            util.write_text(
                "/** 开题 schemaMenus；§3 摆法 */\n"
                "export function classifyPortalMenus() { return {}; }\n",
                encoding="utf-8",
            )
            spec = {
                "domain": "DOM-LIBRARY",
                "shell_nav_style": "storefront",
                "capabilities": ["archive", "ticket_flow", "content"],
            }
            stats = prune_student_pack(dest, spec)
            self.assertFalse((fe_dst / "components/PortalSideRail.vue").is_file())
            layout = (fe_dst / "layouts/PortalLayout.vue").read_text(encoding="utf-8")
            self.assertNotIn("PortalSideRail", layout)
            util_txt = util.read_text(encoding="utf-8")
            self.assertNotIn("开题", util_txt)
            self.assertNotIn("§3", util_txt)
            self.assertIn("classifyPortalMenus", util_txt)
            self.assertGreaterEqual(stats.get("notes_scrubbed_count", 0), 1)

    def test_zip_final_confirm_fails_on_factory_notes_or_rail(self) -> None:
        """p3lean：注记未抹或误带 SideRail → ZIP 不得过。"""
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            fe = dest / "frontend/src"
            (fe / "utils").mkdir(parents=True)
            (fe / "components").mkdir(parents=True)
            (fe / "router").mkdir(parents=True)
            (fe / "router/index.js").write_text("export default []\n", encoding="utf-8")
            dirty = fe / "utils/portalShellNav.js"
            dirty.write_text(
                "/** 开题 schemaMenus §3 */\nexport const X = 1\n",
                encoding="utf-8",
            )
            (fe / "components/PortalSideRail.vue").write_text(
                "<template><aside/></template>\n",
                encoding="utf-8",
            )
            spec = {
                "domain": "DOM-LIBRARY",
                "shell_nav_style": "storefront",
                "capabilities": ["archive", "content"],
            }
            # 未跑 prune：lean 应红
            lean = evaluate_pack_lean_gate(dest, spec)
            self.assertFalse(lean["ok"])
            detail = lean.get("detail") or {}
            self.assertTrue(detail.get("factory_notes") or detail.get("chrome"))
            self.assertTrue(scan_factory_notes_leaks(dest))

            # prune 后应绿
            prune_student_pack(dest, spec)
            lean2 = evaluate_pack_lean_gate(dest, spec)
            self.assertTrue(lean2["ok"], lean2.get("desc"))
            self.assertFalse((fe / "components/PortalSideRail.vue").is_file())
            self.assertEqual(scan_factory_notes_leaks(dest), [])

    def test_prune_keeps_side_rail_for_marketplace(self) -> None:
        if not BASELINE_FE.is_dir():
            self.skipTest("baseline skeleton missing")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ws"
            fe_dst = dest / "frontend/src"
            (fe_dst / "components").mkdir(parents=True)
            (fe_dst / "layouts").mkdir(parents=True)
            (fe_dst / "router").mkdir(parents=True)
            rail_src = BASELINE_FE / "components/PortalSideRail.vue"
            layout_src = BASELINE_FE / "layouts/PortalLayout.vue"
            if not rail_src.is_file() or not layout_src.is_file():
                self.skipTest("PortalSideRail/PortalLayout missing")
            shutil.copy2(rail_src, fe_dst / "components/PortalSideRail.vue")
            shutil.copy2(layout_src, fe_dst / "layouts/PortalLayout.vue")
            (fe_dst / "router/index.js").write_text(
                "export default [{ path: '/', component: () => "
                "import('../layouts/PortalLayout.vue') }]\n",
                encoding="utf-8",
            )
            prune_student_pack(
                dest,
                {
                    "domain": "DOM-SHOP",
                    "shell_nav_style": "marketplace",
                    "capabilities": ["archive", "order_lines"],
                },
            )
            self.assertTrue((fe_dst / "components/PortalSideRail.vue").is_file())
            self.assertIn(
                "PortalSideRail",
                (fe_dst / "layouts/PortalLayout.vue").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
