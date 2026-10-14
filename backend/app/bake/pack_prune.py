"""学生包胖骨架裁剪：按本题 capabilities 删除未挂岛源码，并改写残留引用。

P0：ZIP/工作区不得再堆盲盒/考试/选座等本题未开岛的 Store/Controller/Vue。
删类后须同步改写 OrderStore / DomainRuntimeBinder / router 等硬引用，否则 mvn/vite 红。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Island:
    """可选能力岛：未命中 keep 条件则从学生包剔除。"""

    id: str
    keep_caps: frozenset[str]
    # 相对 backend/.../java/<pkg>/ 或整树 glob
    java_files: tuple[str, ...] = ()
    vue_files: tuple[str, ...] = ()
    types: tuple[str, ...] = ()
    router_enrichers: tuple[str, ...] = ()
    keep_domains: frozenset[str] = field(default_factory=frozenset)


# 全壳工作台：订单/预约/工单仪表盘共用，不随 ticket_flow 岛裁掉，也不进 p3lean 毒区。
_WORKBENCH_KEEP_JAVA: frozenset[str] = frozenset(
    {
        "controller/TicketDashboardController.java",
    }
)
_WORKBENCH_KEEP_VUE: frozenset[str] = frozenset(
    {
        "views/admin/TicketDashboard.vue",
        "components/DashboardCharts.vue",
    }
)


def _is_workbench_keep(rel: str, *, kind: str) -> bool:
    rel_n = rel.replace("\\", "/").lstrip("./")
    if kind == "java":
        return rel_n in _WORKBENCH_KEEP_JAVA or rel_n.endswith(
            "/TicketDashboardController.java"
        )
    if rel_n in _WORKBENCH_KEEP_VUE:
        return True
    return rel_n.endswith("/TicketDashboard.vue") or rel_n.endswith(
        "/DashboardCharts.vue"
    )


# 未挂对应 cap 即裁。ticket_flow 整族可裁：Archive/Recommend/Binder 走类型剥离。
_ISLANDS: tuple[Island, ...] = (
    Island(
        "blind_box",
        frozenset({"blind_box"}),
        java_files=("capability/BlindBoxStore.java", "controller/BlindBoxController.java"),
        vue_files=(
            "views/admin/BlindPoolsAdmin.vue",
            "views/user/BlindBoxDraw.vue",
            "views/user/MyBlindDraws.vue",
        ),
        types=("BlindBoxStore",),
        router_enrichers=("withBlindBoxRoutes",),
    ),
    Island(
        "consign",
        frozenset({"consign"}),
        java_files=("capability/ConsignStore.java", "controller/ConsignController.java"),
        vue_files=("views/admin/ConsignsAdmin.vue", "views/user/MyConsigns.vue"),
        types=("ConsignStore",),
        router_enrichers=("withConsignRoutes",),
    ),
    Island(
        "buyback",
        frozenset({"buyback"}),
        java_files=("capability/BuybackStore.java", "controller/BuybackController.java"),
        vue_files=(
            "views/admin/BuybacksAdmin.vue",
            "views/admin/BuybackSlotsAdmin.vue",
            "views/user/BuybackApply.vue",
            "views/user/MyBuybacks.vue",
        ),
        types=("BuybackStore",),
        router_enrichers=("withBuybackRoutes",),
    ),
    Island(
        "group_buy",
        frozenset({"group_buy"}),
        java_files=("capability/GroupBuyStore.java", "controller/GroupBuyController.java"),
        vue_files=(
            "views/admin/GroupCampaignsAdmin.vue",
            "views/user/GroupBuy.vue",
        ),
        types=("GroupBuyStore",),
        router_enrichers=("withGroupBuyRoutes",),
    ),
    Island(
        "digital_goods",
        frozenset({"digital_goods"}),
        java_files=(
            "capability/DigitalGoodsStore.java",
            "controller/DigitalGoodsController.java",
        ),
        vue_files=(
            "views/admin/DigitalCodesAdmin.vue",
            "views/user/MyDigital.vue",
        ),
        types=("DigitalGoodsStore",),
        router_enrichers=("withDigitalRoutes",),
    ),
    Island(
        "weigh_sale",
        frozenset({"weigh_sale"}),
        java_files=("capability/WeighSaleStore.java", "controller/WeighSaleController.java"),
        vue_files=("views/admin/WeighSaleAdmin.vue",),
        types=("WeighSaleStore",),
        router_enrichers=("withWeighRoutes",),
    ),
    Island(
        "purchase_gate",
        frozenset({"purchase_gate"}),
        java_files=(
            "capability/PurchaseGateStore.java",
            "controller/PurchaseGateController.java",
        ),
        vue_files=("views/admin/PurchaseGateAdmin.vue",),
        types=("PurchaseGateStore",),
        router_enrichers=("withPurchaseGateRoutes",),
    ),
    Island(
        "delivery_window",
        frozenset({"delivery_window"}),
        java_files=(
            "capability/DeliveryWindowStore.java",
            "controller/DeliveryWindowController.java",
        ),
        vue_files=("views/admin/DeliverySlotsAdmin.vue",),
        types=("DeliveryWindowStore",),
        router_enrichers=("withDeliveryWindowRoutes",),
    ),
    Island(
        "line_custom",
        frozenset({"line_custom", "line_spec"}),
        java_files=(
            "capability/LineCustomStore.java",
            "controller/LineCustomController.java",
        ),
        vue_files=("views/admin/LineSpecsAdmin.vue",),
        types=("LineCustomStore",),
        router_enrichers=("withLineSpecRoutes",),
    ),
    Island(
        "rental_bond",
        frozenset({"rental_bond"}),
        java_files=("capability/RentalBondStore.java", "controller/RentalBondController.java"),
        vue_files=("views/admin/RentalInspectAdmin.vue",),
        types=("RentalBondStore",),
        router_enrichers=("withRentalBondRoutes",),
    ),
    Island(
        "lesson_pack",
        frozenset({"lesson_pack"}),
        java_files=("capability/LessonStore.java", "controller/LessonController.java"),
        vue_files=(
            "views/admin/LessonPacksAdmin.vue",
            "views/admin/LessonUsesAdmin.vue",
            "views/user/MyLessons.vue",
        ),
        types=("LessonStore",),
        router_enrichers=("withLessonRoutes",),
    ),
    Island(
        "boarding",
        frozenset({"boarding"}),
        java_files=("capability/BoardingStore.java", "controller/BoardingController.java"),
        vue_files=(
            "views/admin/StayLogsAdmin.vue",
            "views/user/MyStay.vue",
        ),
        types=("BoardingStore",),
        router_enrichers=("withBoardingRoutes",),
    ),
    Island(
        "shoot",
        frozenset({"shoot"}),
        java_files=("capability/ShootStore.java", "controller/ShootController.java"),
        vue_files=(
            "views/admin/ShootBundlesAdmin.vue",
            "views/admin/ShootFilesAdmin.vue",
            "views/user/MyShots.vue",
        ),
        types=("ShootStore",),
        router_enrichers=("withShootRoutes",),
    ),
    Island(
        "hotel_pms",
        frozenset({"front_desk", "room_board"}),
        java_files=(
            "capability/FrontDeskStore.java",
            "capability/RoomBoardStore.java",
            "controller/HotelPmsController.java",
        ),
        vue_files=(
            "views/admin/FrontCheckinAdmin.vue",
            "views/admin/FrontCheckoutAdmin.vue",
            "views/admin/RoomBoardAdmin.vue",
        ),
        types=("FrontDeskStore", "RoomBoardStore"),
        router_enrichers=("withHotelPmsRoutes",),
        keep_domains=frozenset({"DOM-HOTEL"}),
    ),
    Island(
        "venue_clean",
        frozenset({"venue_clean"}),
        java_files=("capability/VenueCleanStore.java", "controller/VenueCleanController.java"),
        vue_files=(
            "views/admin/CleanTasksAdmin.vue",
            "views/staff/StaffClean.vue",
        ),
        types=("VenueCleanStore",),
        router_enrichers=(),
    ),
    Island(
        "book_suggest",
        frozenset({"book_suggest"}),
        java_files=(
            "capability/BookSuggestStore.java",
            "controller/BookSuggestController.java",
        ),
        vue_files=(
            "views/admin/BookSuggestAdmin.vue",
            "views/user/BookSuggest.vue",
        ),
        types=("BookSuggestStore",),
        router_enrichers=("withBookSuggestRoutes",),
    ),
    Island(
        "parcel_shelf",
        frozenset({"parcel_shelf"}),
        java_files=(
            "capability/ParcelShelfStore.java",
            "controller/ParcelShelfController.java",
        ),
        vue_files=("views/admin/ParcelShelfAdmin.vue",),
        types=("ParcelShelfStore",),
        router_enrichers=("withParcelExtraRoutes",),
    ),
    Island(
        "parcel_ship",
        frozenset({"parcel_ship"}),
        java_files=(
            "capability/ParcelShipStore.java",
            "controller/ParcelShipController.java",
        ),
        vue_files=(
            "views/admin/ParcelShipAdmin.vue",
            "views/user/ParcelShip.vue",
        ),
        types=("ParcelShipStore",),
        router_enrichers=("withParcelExtraRoutes",),
    ),
    Island(
        "equipment_dict",
        frozenset({"room_equipment", "equipment_dict"}),
        java_files=(
            "capability/EquipmentDictStore.java",
            "controller/EquipmentDictController.java",
        ),
        vue_files=("views/admin/EquipmentDictAdmin.vue",),
        types=("EquipmentDictStore",),
        router_enrichers=("withRoomEquipmentRoutes",),
    ),
    Island(
        "exam",
        frozenset({"exam"}),
        java_files=("service/ExamStore.java", "controller/ExamController.java"),
        vue_files=(
            "views/ExamPapers.vue",
            "views/ExamAttempts.vue",
            "views/ExamTake.vue",
            "views/ExamPractice.vue",
            "views/ExamRank.vue",
            "views/ExamWrongbook.vue",
            "views/ExamCertificate.vue",
            "views/admin/ExamPapersAdmin.vue",
            "views/admin/ExamQuestionsAdmin.vue",
            "views/admin/ExamMarkAdmin.vue",
            "views/CertVerify.vue",
        ),
        types=("ExamStore",),
        router_enrichers=("withExamRoutes",),
    ),
    Island(
        "survey",
        frozenset({"survey"}),
        java_files=("service/SurveyStore.java", "controller/SurveyController.java"),
        vue_files=(
            "views/SurveyForms.vue",
            "views/SurveyFill.vue",
            "views/SurveyThanks.vue",
            "views/SurveyMine.vue",
            "views/admin/SurveyFormsAdmin.vue",
            "views/admin/SurveyStatsAdmin.vue",
        ),
        types=("SurveyStore",),
        router_enrichers=("withSurveyRoutes",),
    ),
    Island(
        "vote",
        frozenset({"vote"}),
        java_files=("service/VoteStore.java", "controller/VoteController.java"),
        vue_files=(
            "views/VoteBallot.vue",
            "views/VoteMine.vue",
            "views/VoteResults.vue",
            "views/VoteCast.vue",
            "views/VoteCampaigns.vue",
            "views/VotePoster.vue",
            "views/admin/VoteCandidatesAdmin.vue",
            "views/admin/VoteResultsAdmin.vue",
        ),
        types=("VoteStore",),
        router_enrichers=("withVoteRoutes",),
    ),
    Island(
        "seat_select",
        frozenset({"seat_select"}),
        java_files=("service/SeatStore.java", "controller/SeatController.java"),
        vue_files=(
            "views/user/SeatSelect.vue",
            "views/admin/SeatShowsAdmin.vue",
            "views/SeatMap.vue",
            "views/SeatShows.vue",
        ),
        types=("SeatStore",),
        router_enrichers=("withSeatSelectRoutes",),
    ),
    Island(
        "doclib",
        frozenset({"doclib"}),
        java_files=("service/DoclibStore.java", "controller/DoclibController.java"),
        vue_files=(
            "views/admin/DocFilesAdmin.vue",
            "views/admin/DocLogsAdmin.vue",
            "views/user/DocBrowse.vue",
            "views/DocBrowse.vue",
            "views/DocMine.vue",
        ),
        types=("DoclibStore",),
        router_enrichers=("withDoclibRoutes",),
    ),
    Island(
        "timebank",
        frozenset({"timebank"}),
        java_files=(
            "service/TimebankStore.java",
            "controller/TimebankController.java",
        ),
        vue_files=(
            "views/TimebankLedger.vue",
            "views/TimebankAccount.vue",
            "views/TimebankCatalog.vue",
            "views/TimebankAppeal.vue",
            "views/TimebankRank.vue",
            "views/admin/TimebankAccountsAdmin.vue",
            "views/admin/TimebankLedgerAdmin.vue",
            "views/admin/TimebankCatalogAdmin.vue",
            "views/admin/TimebankAppealsAdmin.vue",
        ),
        types=("TimebankStore",),
        router_enrichers=("withTimebankRoutes",),
    ),
    Island(
        "e_sign",
        frozenset({"e_sign"}),
        java_files=("service/ESignStore.java", "controller/ESignController.java"),
        vue_files=("views/ESignMine.vue", "views/admin/ESignAdmin.vue"),
        types=("ESignStore",),
        router_enrichers=("withESignRoutes",),
    ),
    Island(
        "stock_io",
        frozenset({"stock_io"}),
        java_files=("service/StockIoStore.java", "controller/StockIoController.java"),
        vue_files=(
            "views/admin/StockLedgerAdmin.vue",
            "views/admin/StockMovesAdmin.vue",
        ),
        types=("StockIoStore",),
        router_enrichers=("withStockIoRoutes",),
    ),
    Island(
        "lost_clue",
        frozenset({"lost_clue"}),
        java_files=(
            "service/LostMessageStore.java",
            "controller/LostMessageController.java",
        ),
        vue_files=("views/admin/LostCluesAdmin.vue",),
        types=("LostMessageStore",),
        router_enrichers=("withBorrowThickenRoutes",),
    ),
    Island(
        "grade_scores",
        frozenset({"grade_scores"}),
        java_files=(
            "service/GradeScoreStore.java",
            "controller/GradeScoreController.java",
        ),
        vue_files=(
            "views/admin/GradeScoresAdmin.vue",
            "views/GradeScoresMine.vue",
        ),
        types=("GradeScoreStore",),
        router_enrichers=("withGradeScoreRoutes",),
    ),
    Island(
        "fund_publicity",
        frozenset({"fund_publicity"}),
        java_files=(
            "service/FundPublicityStore.java",
            "controller/FundPublicityController.java",
            "controller/FundDisburseController.java",
        ),
        vue_files=(
            "views/admin/FundPublicityAdmin.vue",
            "views/admin/FundDisburseAdmin.vue",
            "views/user/FundPublicity.vue",
        ),
        types=("FundPublicityStore",),
        router_enrichers=("withFundIslandRoutes",),
    ),
    Island(
        "occupy_span",
        frozenset({"occupy_span"}),
        java_files=(
            "service/OccupySpanStore.java",
            "controller/OccupySpanController.java",
        ),
        vue_files=(
            "views/admin/OccupyAdmin.vue",
            "views/OccupyMine.vue",
        ),
        types=("OccupySpanStore",),
        router_enrichers=("withBorrowThickenRoutes",),
    ),
    Island(
        "material_check",
        frozenset({"material_check"}),
        java_files=(
            "service/MaterialCheckStore.java",
            "controller/MaterialCheckController.java",
        ),
        vue_files=(
            "views/admin/MaterialChecklistAdmin.vue",
            "components/MaterialChecklistFields.vue",
        ),
        types=("MaterialCheckStore",),
        router_enrichers=("withBorrowThickenRoutes",),
    ),
    Island(
        "balance_ledger",
        frozenset({"balance_ledger"}),
        java_files=(
            "service/BalanceLedgerStore.java",
            "controller/BalanceLedgerController.java",
        ),
        vue_files=(
            "views/admin/BalanceAccountsAdmin.vue",
            "views/admin/BalanceLedgerAdmin.vue",
            "views/BalanceLedgerMine.vue",
            "views/BalanceMine.vue",
        ),
        types=("BalanceLedgerStore",),
        router_enrichers=("withBorrowThickenRoutes",),
    ),
    Island(
        "claim_proof",
        frozenset({"claim_proof"}),
        java_files=(
            "service/ClaimProofStore.java",
            "controller/ClaimProofController.java",
        ),
        vue_files=("components/ClaimProofFields.vue",),
        types=("ClaimProofStore",),
        router_enrichers=(),
    ),
    Island(
        "borrow_credit",
        frozenset({"borrow_credit"}),
        java_files=("capability/BorrowCreditStore.java",),
        vue_files=(),
        types=("BorrowCreditStore",),
        router_enrichers=(),
    ),
    Island(
        "browse_history",
        frozenset({"browse_history"}),
        java_files=(
            "capability/BrowseHistoryStore.java",
            "controller/BrowseHistoryController.java",
        ),
        vue_files=("views/user/BrowseHistory.vue",),
        types=("BrowseHistoryStore",),
        router_enrichers=("withBrowseHistoryRoutes",),
    ),
    Island(
        "archive_log",
        frozenset({"archive_log"}),
        java_files=(
            "capability/ArchiveLogStore.java",
            "controller/ArchiveLogController.java",
            "controller/AdminArchiveLogController.java",
        ),
        vue_files=("views/admin/ArchiveLogsAdmin.vue",),
        types=("ArchiveLogStore",),
        router_enrichers=("withArchiveLogRoutes",),
    ),
    Island(
        "staff_roster",
        frozenset({"staff_roster"}),
        java_files=(
            "capability/StaffRosterStore.java",
            "controller/StaffRosterController.java",
        ),
        vue_files=("views/admin/StaffRosterAdmin.vue",),
        types=("StaffRosterStore",),
        router_enrichers=("withStaffRosterRoutes",),
    ),
    Island(
        "content_report",
        frozenset({"content_report"}),
        java_files=(),
        vue_files=("views/admin/ContentReportsAdmin.vue",),
        types=(),
        router_enrichers=("withContentReportRoutes",),
    ),
    Island(
        "item_comment",
        frozenset({"item_comment"}),
        java_files=(
            "service/ItemCommentStore.java",
            "controller/ItemCommentController.java",
        ),
        vue_files=("views/admin/ItemCommentAdmin.vue",),
        types=("ItemCommentStore",),
        router_enrichers=("withItemCommentRoutes",),
    ),
    Island(
        "slot_reserve",
        frozenset({"slot_reserve"}),
        java_files=(
            "capability/SlotStore.java",
            "controller/SlotController.java",
            "service/ReserveBlacklistStore.java",
            "controller/ReserveBlacklistController.java",
        ),
        vue_files=(
            "views/user/SlotBook.vue",
            "views/user/MyReservations.vue",
            "views/user/ReserveBlacklistAppeal.vue",
            "views/admin/ReservationsAdmin.vue",
            "views/admin/ReserveBlacklistAdmin.vue",
            "views/staff/StaffSlots.vue",
        ),
        types=("SlotStore", "ReserveBlacklistStore"),
        router_enrichers=(),
        keep_domains=frozenset(
            {
                "DOM-HOSPITAL",
                "DOM-PARKING",
                "DOM-MEETING",
                "DOM-SALON",
                "DOM-HOTEL",
                "DOM-CARRENT",
            }
        ),
    ),
    Island(
        "coupon",
        frozenset({"coupon"}),
        java_files=(
            "capability/CouponStore.java",
            "controller/CouponController.java",
        ),
        vue_files=(
            "views/user/MyCoupons.vue",
            "views/admin/CouponsAdmin.vue",
        ),
        types=("CouponStore",),
        router_enrichers=("withCouponRoutes",),
    ),
    Island(
        "listing_deal",
        frozenset({"listing_deal"}),
        java_files=(
            "service/ListingDealStore.java",
            "controller/ListingDealController.java",
        ),
        vue_files=("views/admin/ListingDealAdmin.vue",),
        types=("ListingDealStore",),
        router_enrichers=("withListingDealRoutes",),
    ),
    Island(
        "apply_blacklist",
        frozenset({"apply_blacklist"}),
        java_files=(
            "service/ApplyBlacklistStore.java",
            "controller/ApplyBlacklistController.java",
        ),
        vue_files=("views/admin/ApplyBlacklistAdmin.vue",),
        types=("ApplyBlacklistStore",),
        router_enrichers=(),
    ),
    Island(
        "fund_disburse",
        frozenset({"fund_publicity", "fund_disburse"}),
        java_files=(
            "service/FundDisburseStore.java",
            "controller/FundDisburseController.java",
        ),
        vue_files=("views/admin/FundDisburseAdmin.vue",),
        types=("FundDisburseStore",),
        router_enrichers=("withFundIslandRoutes",),
    ),
    Island(
        "ai_assistant",
        frozenset({"ai_assistant"}),
        java_files=(
            "service/AiAssistantStore.java",
            "service/DeepSeekClient.java",
            "service/AiBizContext.java",
            "controller/AiAssistantController.java",
        ),
        vue_files=(
            "views/AiAssistant.vue",
            "views/admin/AiKnowledgeAdmin.vue",
            "components/AiAssistantFloat.vue",
        ),
        types=("AiAssistantStore", "DeepSeekClient", "AiBizContext"),
        router_enrichers=("withAiAssistantRoutes",),
    ),
    Island(
        "message_template",
        frozenset({"message_template"}),
        java_files=("controller/MessageTemplateController.java",),
        vue_files=("views/admin/MessageTemplatesAdmin.vue",),
        types=(),
        router_enrichers=("withMessageTemplateRoutes",),
    ),
    Island(
        "stock_notify",
        frozenset({"stock_warn_notify", "stock_io"}),
        java_files=(
            "capability/StockNotifyStore.java",
            "controller/StockNotifyController.java",
        ),
        vue_files=(),
        types=("StockNotifyStore",),
        router_enrichers=(),
    ),
    Island(
        "ticket_flow",
        frozenset({"ticket_flow"}),
        java_files=(
            "capability/TicketApplyOps.java",
            "capability/TicketApproveOps.java",
            "capability/TicketAsserts.java",
            "capability/TicketCfgOps.java",
            "capability/TicketCompleteOps.java",
            "capability/TicketCopy.java",
            "capability/TicketDashOps.java",
            "capability/TicketDeriveOps.java",
            "capability/TicketGuardOps.java",
            "capability/TicketLineOps.java",
            "capability/TicketLookupStore.java",
            "capability/TicketNotifyOps.java",
            "capability/TicketPatchOps.java",
            "capability/TicketProgressOps.java",
            "capability/TicketQueryOps.java",
            "capability/TicketQueueOps.java",
            "capability/TicketReviseOps.java",
            "capability/TicketRowMaps.java",
            "capability/TicketSql.java",
            "capability/TicketStatusOps.java",
            "capability/TicketStore.java",
            "config/TicketPolicy.java",
            "controller/TicketController.java",
            # 下列仅登记在岛内便于对照；实际裁剪/lean 由 _WORKBENCH_KEEP_* 豁免
            "controller/TicketDashboardController.java",
            "controller/LookupController.java",
            "controller/LookupAdminController.java",
        ),
        vue_files=(
            "views/user/MyTickets.vue",
            "views/user/PeerTickets.vue",
            "views/user/MutualResults.vue",
            "views/user/WeekCalendar.vue",
            "views/user/MyLoss.vue",
            "views/user/MyPermits.vue",
            "views/admin/TicketsAdmin.vue",
            "views/admin/TicketRecordsAdmin.vue",
            "views/admin/TicketDashboard.vue",
            "views/admin/LookupSitesAdmin.vue",
            "views/admin/LookupTypesAdmin.vue",
            "views/admin/OverdueAdmin.vue",
            "views/admin/LossAdmin.vue",
            "views/admin/PermitsAdmin.vue",
            "views/admin/CareOptionsAdmin.vue",
            "views/admin/PriceSpansAdmin.vue",
            "views/staff/StaffTickets.vue",
            "components/TicketProgressDialog.vue",
            "components/TicketRateDialog.vue",
            "utils/ticketApplyShared.js",
            "utils/ticketFormPrint.js",
            "utils/useTicketApplyForm.js",
            "utils/useTicketSchemaFlags.js",
        ),
        types=("TicketStore", "TicketLookupStore", "TicketPolicy"),
        router_enrichers=(),
    ),
)


def _caps(spec: dict[str, Any]) -> set[str]:
    raw = spec.get("capabilities")
    if not isinstance(raw, list):
        sch = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
        raw = sch.get("capabilities") if isinstance(sch.get("capabilities"), list) else []
    out = {str(x).strip() for x in raw if str(x).strip()}
    # addons
    if spec.get("ai_assistant") or (isinstance(spec.get("addons"), dict) and spec["addons"].get("ai_assistant")):
        out.add("ai_assistant")
    return out


def _domain(spec: dict[str, Any]) -> str:
    return str(spec.get("domain") or "").strip()


def _should_keep(island: Island, caps: set[str], domain: str) -> bool:
    if island.keep_caps & caps:
        return True
    if island.keep_domains and domain in island.keep_domains:
        return True
    # hotel_pms: also keep if DOM-HOTEL even without those caps
    return False


def _java_root(dest: Path) -> Path | None:
    base = dest / "backend" / "src" / "main" / "java"
    if not base.is_dir():
        return None
    # com/<vendor>/<app>/...
    hits = list(base.glob("com/*/*"))
    for h in hits:
        if h.is_dir() and (h / "config").is_dir():
            return h
    # fallback first package leaf with capability
    for p in base.rglob("capability"):
        if p.is_dir():
            return p.parent
    return None


def _fe_src(dest: Path) -> Path | None:
    p = dest / "frontend" / "src"
    return p if p.is_dir() else None


def _delete_rel(root: Path, rel: str, deleted: list[str]) -> None:
    path = root / rel.replace("\\", "/")
    if path.is_file():
        path.unlink()
        deleted.append(str(path.relative_to(root.parent.parent.parent) if False else path))
        deleted[-1] = rel
    elif path.is_dir():
        for child in sorted(path.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink()
        try:
            path.rmdir()
        except OSError:
            pass
        deleted.append(rel)


def _skip_balanced(text: str, open_idx: int, open_ch: str = "(", close_ch: str = ")") -> int:
    """open_idx 指向开括号，返回匹配闭括号之后的下标；失败返回 -1。"""
    if open_idx < 0 or open_idx >= len(text) or text[open_idx] != open_ch:
        return -1
    depth = 0
    j = open_idx
    while j < len(text):
        ch = text[j]
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return -1


def _replace_type_calls(text: str, type_name: str, method: str, replacement: str) -> str:
    """替换 Type.method(...)（支持嵌套括号）为 replacement。"""
    t = re.escape(type_name)
    fqn = rf"(?:[\w.]+\.)?{t}"
    pat = re.compile(rf"{fqn}\.{re.escape(method)}\s*\(")
    while True:
        m = pat.search(text)
        if not m:
            break
        end = _skip_balanced(text, m.end() - 1)
        if end < 0:
            break
        text = text[: m.start()] + replacement + text[end:]
    return text


def _remove_balanced_if_false(text: str) -> str:
    """删掉 if (false …) 整块；else { } 整删；else if 降级为 if。"""
    # if (false) / if (false && …) / if(false||…)
    pattern = re.compile(r"\bif\s*\(\s*false\b")
    while True:
        m = pattern.search(text)
        if not m:
            break
        paren = text.find("(", m.start())
        after_cond = _skip_balanced(text, paren, "(", ")")
        if after_cond < 0:
            break
        rest = text[after_cond:]
        brace = re.match(r"\s*\{", rest)
        if not brace:
            # if (false) stmt;
            semi = rest.find(";")
            if semi < 0:
                break
            text = text[: m.start()] + text[after_cond + semi + 1 :]
            continue
        end_if = _skip_balanced(text, after_cond + brace.end() - 1, "{", "}")
        if end_if < 0:
            break
        j = end_if
        rest2 = text[j:]
        else_if = re.match(r"\s*else\s+(if\b)", rest2)
        if else_if:
            j += else_if.start(1)
        else:
            else_m = re.match(r"\s*else\s*\{", rest2)
            if else_m:
                end_else = _skip_balanced(rest2, else_m.end() - 1, "{", "}")
                if end_else < 0:
                    break
                j += end_else
        text = text[: m.start()] + text[j:]
    return text


def _strip_ticket_policy(text: str) -> str:
    """按左侧声明类型替换 TicketPolicy.CONST，避免 int/boolean/String 互串。"""
    fqn = r"(?:[\w.]+\.)?TicketPolicy"
    text = re.sub(rf"(?m)^\s*import\s+[\w.]+\.TicketPolicy\s*;\s*\n", "", text)

    def _lit(java_type: str) -> str:
        t = java_type.strip()
        if t in {"boolean", "Boolean"}:
            return "false"
        if t in {"String"}:
            return '""'
        if t in {"double", "Double", "float", "Float"}:
            return "0"
        return "0"

    text = re.sub(
        rf"(?m)^(\s*(?:private|protected|public)\s+(?:final\s+)?)(boolean|Boolean|int|Integer|long|Long|double|Double|float|Float|String)\s+(\w+)\s*=\s*{fqn}\.\w+\s*;",
        lambda m: f"{m.group(1)}{m.group(2)} {m.group(3)} = {_lit(m.group(2))};",
        text,
    )
    # 表达式里残留：布尔语境占多数；字符串拼接极少
    text = re.sub(rf"{fqn}\.\w+\b", "false", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _strip_type_usages(text: str, type_name: str) -> str:
    """从残留 Java 中抹掉对已删类型的引用，换成可编译的空操作。"""
    text = re.sub(
        rf"(?m)^\s*import\s+[\w.]+\.{re.escape(type_name)}\s*;\s*\n",
        "",
        text,
    )
    text = re.sub(rf"\{{@link\s+{re.escape(type_name)}\}}", type_name, text)
    fqn = rf"(?:[\w.]+\.)?{re.escape(type_name)}"

    if type_name == "TicketPolicy":
        return _strip_ticket_policy(text)

    if type_name == "TicketStore":
        text = re.sub(rf"{fqn}\.scheduleChangeNotify\b", "false", text)
        text = re.sub(rf"{fqn}\.allowContractExpireRemind\b", "false", text)
        text = re.sub(rf"{fqn}\.notifyArchiveExpireDays\b", "0", text)
        # 占位表名仅出现在 if(false) 死分支；用普通标识避免交源码穿帮
        text = re.sub(rf"{fqn}\.TICKET\b", '"ticket"', text)
        text = re.sub(rf"{fqn}\.PROGRESS\b", '""', text)
        text = re.sub(
            rf"{fqn}\.mode\s*\(\s*\)\s*\.\s*name\s*\(\s*\)\s*\.\s*toLowerCase\s*\(\s*\)",
            '"off"',
            text,
        )
        text = re.sub(rf"{fqn}\.mode\s*\(\s*\)\s*==\s*{fqn}\.Mode\.\w+", "false", text)
        text = re.sub(rf"{fqn}\.mode\s*\(\s*\)\s*!=\s*{fqn}\.Mode\.\w+", "true", text)
        text = re.sub(rf"{fqn}\.Mode\.\w+", "null", text)
        text = re.sub(rf"{fqn}\.get\s*\([^)]*\)\s*==\s*null", "true", text)
        text = re.sub(rf"{fqn}\.get\s*\([^)]*\)\s*!=\s*null", "false", text)
        text = _replace_type_calls(text, type_name, "itemFkColumn", '"item_id"')
        text = _replace_type_calls(
            text, type_name, "listApprovedUsernamesForItem", "java.util.List.of()"
        )
        text = _replace_type_calls(text, type_name, "autoPassStalePending", "0")
        text = _replace_type_calls(text, type_name, "autoRejectStalePeerPending", "0")
        text = _replace_type_calls(text, type_name, "runMainPathSelfCheck", "true")
        text = _replace_type_calls(text, type_name, "isArchiveMode", "false")
        text = re.sub(rf"{fqn}\.is[A-Z]\w*\s*\(\s*\)", "false", text)
        text = re.sub(rf"{fqn}\.ratingDimsRequiredOnApply\s*\(\s*\)", "false", text)
        text = re.sub(rf"{fqn}\.hasColumn\s*\([^)]*\)", "false", text)

    if type_name == "TicketLookupStore":
        text = _replace_type_calls(text, type_name, "meta", "java.util.Map.of()")
        for meth in (
            "listSites",
            "listSitesAdmin",
            "listUnits",
            "listUnitsAdmin",
            "listTypes",
            "listTypesAdmin",
        ):
            text = _replace_type_calls(text, type_name, meth, "java.util.List.of()")

    # 无参 / 简单布尔（含 TicketStore.enabled 字段与 enabled() 方法）
    text = re.sub(rf"{fqn}\.(?:enabled|snackReady|ready)\s*\(\s*\)", "false", text)
    text = re.sub(rf"{fqn}\.(?:enabled|snackReady|ready|useDeadline|noShowAfterEnd|approveEndsFlow|allowRating|repairThicken)\b(?!\s*\()", "false", text)
    text = re.sub(rf"{fqn}\.(?:userRole|MODE)\b(?!\s*\()", "null", text)
    text = _replace_type_calls(text, type_name, "isBox", "false")
    text = _replace_type_calls(text, type_name, "pityText", '""')
    for meth in (
        "drawAll",
        "listOpenShows",
        "listPublishedPapers",
        "listOnSale",
        "listActiveTemplates",
    ):
        text = _replace_type_calls(text, type_name, meth, "java.util.List.of()")
    text = _replace_type_calls(text, type_name, "onDutyUsernames", "java.util.Set.of()")
    for meth in (
        "remindAheadMinutes",
        "expireSweep",
        "expirePastShows",
        "releaseExpiredHolds",
        "remindDueSweep",
        "scheduleOpenCloseSweep",
        "remindCloseSweep",
        "expireSoonNotify",
    ):
        text = _replace_type_calls(text, type_name, meth, "0")
    for meth in (
        "getSnack",
        "progressForOrder",
        "pageMyAttempts",
        "getAccount",
        "matchForCheckout",
        "matchCoupon",
    ):
        text = _replace_type_calls(text, type_name, meth, "null")

    # WeighSaleStore.priceLine(...) 赋值 → item
    assign_pl = re.compile(
        rf"Map<\s*String\s*,\s*Object\s*>\s+(\w+)\s*=\s*{fqn}\.priceLine\s*\("
    )
    while True:
        m = assign_pl.search(text)
        if not m:
            break
        end = _skip_balanced(text, m.end() - 1)
        if end < 0:
            break
        k = end
        while k < len(text) and text[k] in " \t":
            k += 1
        if k < len(text) and text[k] == ";":
            k += 1
        text = text[: m.start()] + f"Map<String, Object> {m.group(1)} = item;" + text[k:]
    text = _replace_type_calls(text, type_name, "priceLine", "null")

    # 三元：false ? … : fallback → fallback
    text = re.sub(r"\bfalse\s*\?\s*[^;]*?:\s*", "", text)

    # return Type.foo(...);
    ret_pat = re.compile(rf"return\s+{fqn}\.\w+\s*\(")
    while True:
        m = ret_pat.search(text)
        if not m:
            break
        end = _skip_balanced(text, m.end() - 1)
        if end < 0:
            break
        k = end
        while k < len(text) and text[k] in " \t":
            k += 1
        if k < len(text) and text[k] == ";":
            k += 1
        text = text[: m.start()] + "return null;" + text[k:]

    # 整行 void 调用 Type.foo(...);
    call_pat = re.compile(rf"(?m)^\s*{fqn}\.\w+\s*\(")
    while True:
        m = call_pat.search(text)
        if not m:
            break
        end = _skip_balanced(text, m.end() - 1)
        if end < 0:
            break
        k = end
        while k < len(text) and text[k] in " \t":
            k += 1
        if k < len(text) and text[k] == ";":
            k += 1
        if k < len(text) and text[k] == "\n":
            k += 1
        text = text[: m.start()] + text[k:]

    # 残留 Type.foo(...) → null（断言类变空串再清分号行）
    for meth in (
        "assertCanBuy",
        "assertPurchasable",
        "assertOnSale",
        "assertListed",
        "assertJoin",
        "assertOrderRefundOpen",
        "configure",
        "bind",
        "unbind",
        "deliverOnPay",
        "quote",
    ):
        text = _replace_type_calls(text, type_name, meth, "null")

    gen_pat = re.compile(rf"{fqn}\.\w+\s*\(")
    for _ in range(40):
        m = gen_pat.search(text)
        if not m:
            break
        end = _skip_balanced(text, m.end() - 1)
        if end < 0:
            break
        text = text[: m.start()] + "null" + text[end:]

    # 清掉变成「null;」的空语句
    text = re.sub(r"(?m)^\s*null\s*;\s*\n", "", text)
    # int n = Type.foo() → int n = null 会炸编译；数值原语改 0，布尔改 false
    text = re.sub(
        r"\b(int|long|short|byte|float|double)\s+(\w+)\s*=\s*null\b",
        r"\1 \2 = 0",
        text,
    )
    text = re.sub(r"\bboolean\s+(\w+)\s*=\s*null\b", r"boolean \1 = false", text)
    # if (false) Type.foo(); → if (false) null; → 整句删
    text = re.sub(r"\bif\s*\(\s*false\s*\)\s*null\s*;", "", text)
    text = re.sub(r"\bif\s*\(\s*false\s*\)\s*[^;{\n]+;", "", text)

    text = _remove_balanced_if_false(text)
    text = re.sub(
        r"\bif\s*\(\s*!\s*false\s*\)\s*\{([^{}]*)\}",
        r"\1",
        text,
    )
    text = re.sub(r"\bif\s*\(\s*!\s*false\s*\)\s*", "", text)
    # if (!enabled) / if (!snackReady) 展开后：return X; return null; 或 throw 后死代码
    text = re.sub(
        r"return\s+([a-zA-Z_][\w]*)\s*;\s*return\s+null\s*;",
        r"return \1;",
        text,
    )
    # snackReady：if (!false) { throw ... } 后整段卖品逻辑不可达 — 保留 throw，砍掉后面到方法级需人工；
    # 这里把「throw ...;」紧随的「return;」清掉
    text = re.sub(r"(throw\s+[^;]+;)\s*return\s*;", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _passthrough_enricher(name: str) -> str:
    return (
        f"function {name}(baseRoutes) {{\n"
        f"  return baseRoutes\n"
        f"}}\n"
    )


def _strip_router_enrichers(router_text: str, enrichers: set[str]) -> str:
    if not enrichers:
        return router_text
    text = router_text
    # remove from enrichers array entries
    for name in enrichers:
        text = re.sub(rf"(?m)^\s*{re.escape(name)}\s*,\s*\n", "", text)
        text = re.sub(rf",\s*{re.escape(name)}\b", "", text)
        # replace function body with passthrough (keep name for any residual refs)
        text = re.sub(
            rf"function\s+{re.escape(name)}\s*\(\s*baseRoutes\s*\)\s*\{{.*?\n\}}",
            _passthrough_enricher(name).rstrip(),
            text,
            flags=re.S,
        )
    return text


def _remove_java_void_method(src: str, name: str) -> str:
    """按方法签名删掉 public static void name(...){...}（含紧邻 javadoc）。"""
    sig = re.search(rf"(?m)^([ \t]*)public static void {re.escape(name)}\s*\(", src)
    if not sig:
        return src
    start = sig.start()
    pre = src[:start]
    i = len(pre)
    while i > 0 and pre[i - 1] in " \t":
        i -= 1
    while i > 0 and pre[i - 1] in "\r\n":
        i -= 1
        while i > 0 and pre[i - 1] in " \t":
            i -= 1
    if i >= 2 and pre[i - 2 : i] == "*/":
        open_at = pre.rfind("/**", 0, i)
        if open_at != -1 and pre[i:].strip() == "":
            start = open_at
            if start > 0 and pre[start - 1] == "\n":
                start -= 1
    brace = src.find("{", sig.end() - 1)
    if brace < 0:
        return src
    end = _skip_balanced(src, brace, "{", "}")
    if end < 0:
        return src
    while end < len(src) and src[end] in "\r\n":
        end += 1
    return src[:start] + src[end:]


def _scrub_order_cinema_snacks(text: str) -> str:
    """无选座岛时，OrderStore 不得残留影院卖品 API（交源码观感）。"""
    if "attachCinemaSnacks" not in text and "restoreSnackStockForOrder" not in text:
        return text
    text = _remove_java_void_method(text, "attachCinemaSnacks")
    text = _remove_java_void_method(text, "restoreSnackStockForOrder")
    text = re.sub(r"(?m)^[ \t]*restoreSnackStockForOrder\s*\([^;]*\)\s*;\s*\n", "", text)
    text = re.sub(r"(?m)^[ \t]*attachCinemaSnacks\s*\([^;]*\)\s*;\s*\n", "", text)
    text = re.sub(
        r"(?m)^[ \t]*if\s*\(\s*LoyaltyStore\.isCouponEnabled\s*\(\s*\)\s*\)\s*\{\s*\}\s*\n",
        "",
        text,
    )
    text = text.replace(
        "选座等「先下单再履约」失败时关单：退余额、释放券，不回补库存（库存由调用方按是否已扣处理）。",
        "下单失败关单：退余额；不回补库存（库存由调用方按是否已扣处理）。",
    )
    return text


def _fe_import_rels(text: str) -> set[str]:
    """收集相对前端 src 的 import 路径（views/components/utils/layouts）。"""
    out: set[str] = set()
    for pat in (
        r"import\(['\"]((?:\.\./|\./|@/)+[^'\"]+)['\"]\)",
        r"from\s+['\"]((?:\.\./|\./|@/)+[^'\"]+)['\"]",
    ):
        for m in re.findall(pat, text):
            rel = str(m).replace("\\", "/")
            if rel.startswith("@/"):
                rel = rel[2:]
            else:
                # ../../components/Foo.vue → components/Foo.vue
                while rel.startswith("../"):
                    rel = rel[3:]
                if rel.startswith("./"):
                    rel = rel[2:]
            rel = rel.lstrip("/")
            if rel.startswith(("views/", "components/", "utils/", "layouts/")):
                out.add(rel)
                # import '@/utils/foo' 无后缀时补全扩展，避免可达性分析漏网
                if not rel.endswith((".vue", ".js", ".ts", ".tsx", ".jsx", ".css", ".scss")):
                    if rel.startswith("utils/"):
                        out.add(rel + ".js")
                    else:
                        out.add(rel + ".vue")
                        out.add(rel + ".js")
    return out


def _scrub_killed_imports_in_text(text: str, killed: set[str]) -> str:
    """删掉指向已裁文件的 import / 组件注册行。"""
    if not killed:
        return text
    names = {Path(k).name for k in killed}
    stems = {Path(k).stem for k in killed}
    for name in names:
        text = re.sub(
            rf"(?m)^\s*import\s+.+\s+from\s+['\"][^'\"]*{re.escape(name)}['\"]\s*;?\s*\n",
            "",
            text,
        )
        text = re.sub(
            rf"(?m)^\s*const\s+\w+\s*=\s*\(\)\s*=>\s*import\(['\"][^'\"]*{re.escape(name)}['\"]\)\s*;?\s*\n",
            "",
            text,
        )
    for stem in stems:
        # <AiAssistantFloat .../> 或 <AiAssistantFloat></AiAssistantFloat>
        text = re.sub(
            rf"(?m)^\s*<{re.escape(stem)}\b[^>]*/>\s*\n?",
            "",
            text,
        )
        text = re.sub(
            rf"(?s)<{re.escape(stem)}\b[^>]*>.*?</{re.escape(stem)}\s*>",
            "",
            text,
        )
        # components: { AiAssistantFloat }
        text = re.sub(rf"\b{re.escape(stem)}\s*,\s*", "", text)
        text = re.sub(rf",\s*\b{re.escape(stem)}\b", "", text)
    return text


def _sweep_unreachable_frontend(fe: Path) -> list[str]:
    """删掉 router 与存活页面都引用不到的 views/components（交源码观感）。"""
    router = fe / "router" / "index.js"
    if not router.is_file():
        return []
    seeds: set[str] = set(_fe_import_rels(router.read_text(encoding="utf-8")))
    # 壳层与公共页：即便动态拼接也保留
    seeds.update(
        {
            "views/Login.vue",
            "views/Register.vue",
            "views/Home.vue",
            "views/Profile.vue",
            "views/Notices.vue",
            "views/NoticeDetail.vue",
            "views/Agreement.vue",
            "views/Privacy.vue",
            "views/ForgotPassword.vue",
            "views/ActivateAccount.vue",
            "views/ForceChangePassword.vue",
            "layouts/PortalLayout.vue",
            "layouts/AdminLayout.vue",
            "layouts/WorkLayout.vue",
            "views/user/PortalHome.vue",
            "views/user/ArchiveBrowse.vue",
            "views/admin/ArchiveAdmin.vue",
            "views/admin/CategoriesAdmin.vue",
            "views/admin/UsersAdmin.vue",
            "views/admin/NoticesAdmin.vue",
            "views/admin/TicketDashboard.vue",
            "components/DashboardCharts.vue",
        }
    )
    for seed_name in ("App.vue", "main.js"):
        sp = fe / seed_name if seed_name == "App.vue" else fe.parent / seed_name
        # main.js 常在 frontend/src/main.js
        if seed_name == "main.js":
            sp = fe / "main.js"
        if sp.is_file():
            seeds |= _fe_import_rels(sp.read_text(encoding="utf-8"))

    reachable: set[str] = set()
    queue = list(seeds)
    while queue:
        rel = queue.pop().replace("\\", "/")
        if rel in reachable:
            continue
        path = fe / rel
        if not path.is_file():
            # try resolve relative component next to a view — skip
            continue
        reachable.add(rel)
        try:
            deps = _fe_import_rels(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        for d in deps:
            if d not in reachable:
                queue.append(d)

    deleted: list[str] = []
    for folder in ("views", "components"):
        root = fe / folder
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*.vue")):
            rel = p.relative_to(fe).as_posix()
            if rel in reachable or _is_workbench_keep(rel, kind="vue"):
                continue
            p.unlink()
            deleted.append(rel)
    return deleted


def _scrub_frontend_killed_refs(fe: Path, killed: set[str]) -> None:
    """布局/残留页里抹掉已删组件的 import 与标签。"""
    if not killed:
        return
    for path in list(fe.rglob("*.vue")) + list(fe.rglob("*.js")):
        if not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8")
        new = _scrub_killed_imports_in_text(raw, killed)
        if new != raw:
            path.write_text(new, encoding="utf-8")


def _scrub_router_vue_imports(router_text: str, vue_rels: set[str]) -> str:
    """删掉指向已裁 Vue 的路由对象字面量，避免 Vite 解析缺失文件。"""
    if not vue_rels:
        return router_text
    text = router_text
    for rel in sorted(vue_rels, key=len, reverse=True):
        rel_n = rel.replace("\\", "/")
        if _is_workbench_keep(rel_n, kind="vue"):
            continue
        # { path: '...', component: () => import('../views/...') }
        text = re.sub(
            rf"\{{[^{{}}]*import\(\s*['\"]\.\./{re.escape(rel_n)}['\"]\s*\)[^{{}}]*\}}\s*,?",
            "",
            text,
        )
        # 残留的单行 import 引用（防御）
        text = re.sub(
            rf"[^\n]*import\(\s*['\"]\.\./{re.escape(rel_n)}['\"]\s*\)[^\n]*\n?",
            "",
            text,
        )
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\[\s*,", "[", text)
    text = re.sub(r",\s*\]", "]", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _invite_wanted(spec: dict[str, Any]) -> bool:
    """开题挂了邀请码菜单或 requireInvite>0 才保留码池源码。"""
    schema = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
    pol = schema.get("authPolicy") if isinstance(schema.get("authPolicy"), dict) else {}
    try:
        if int(pol.get("requireInvite") or 0) > 0:
            return True
    except (TypeError, ValueError):
        pass
    admin = (schema.get("menus") or {}).get("admin") or []
    return any(isinstance(m, dict) and m.get("key") == "invite_codes" for m in admin)


_INVITE_JAVA_RELS = ("service/InviteCodeStore.java",)
_INVITE_VUE_RELS = ("views/admin/InviteCodesAdmin.vue",)


def _remove_java_annotated_methods(text: str, mapping_substrings: tuple[str, ...]) -> str:
    """删掉带指定 Mapping 注解的整段方法（含注解行）。

    先跳过注解块再按方法体花括号配对，避免 ``/path/{code}`` 路径变量被当成方法体。
    """
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if any(s in line for s in mapping_substrings) and "@" in line:
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("@"):
                j += 1
            while j < len(lines) and "{" not in lines[j]:
                j += 1
            if j >= len(lines):
                break
            brace = 0
            while j < len(lines):
                for ch in lines[j]:
                    if ch == "{":
                        brace += 1
                    elif ch == "}":
                        brace -= 1
                j += 1
                if brace <= 0:
                    break
            i = j
            continue
        out.append(line)
        i += 1
    return "".join(out)


def _scrub_invite_java(text: str) -> str:
    text = re.sub(r"(?m)^\s*import\s+[\w.]+\.InviteCodeStore\s*;\s*\n", "", text)
    text = re.sub(
        r"(?s)\s*if\s*\(\s*AppPolicy\.AUTH_REQUIRE_INVITE\s*>\s*0\s*\)\s*\{"
        r"\s*InviteCodeStore\.consumeOrThrow\([^;]*\);\s*\}",
        "",
        text,
    )
    text = _remove_java_annotated_methods(
        text,
        ("/api/admin/invite-codes",),
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _prune_invite_codes(
    dest: Path,
    *,
    java_root: Path | None,
    fe: Path | None,
    deleted: list[str],
) -> None:
    """开题未挂邀请码：删码池 Store/管理页，并抹掉 Controller/路由引用。"""
    if java_root:
        for rel in _INVITE_JAVA_RELS:
            p = java_root / rel
            if p.is_file():
                p.unlink()
                deleted.append(f"java:{rel}")
        for java in java_root.rglob("*.java"):
            raw = java.read_text(encoding="utf-8")
            if "InviteCodeStore" not in raw and "invite-codes" not in raw:
                continue
            new = _scrub_invite_java(raw)
            if new != raw:
                java.write_text(new, encoding="utf-8")
                deleted.append(f"scrub:{java.name}.invite")
    if fe:
        vue_killed: set[str] = set()
        for rel in _INVITE_VUE_RELS:
            rel_n = rel.replace("\\", "/")
            p = fe / rel_n
            if p.is_file():
                p.unlink()
                deleted.append(f"vue:{rel_n}")
            vue_killed.add(rel_n)
        router = fe / "router" / "index.js"
        if router.is_file():
            rt = router.read_text(encoding="utf-8")
            nt = _scrub_router_vue_imports(rt, vue_killed)
            nt2 = re.sub(
                r"\{[^{}]*path:\s*['\"]invite-codes['\"][^{}]*\}\s*,?",
                "",
                nt,
            )
            nt2 = re.sub(r",\s*,", ",", nt2)
            if nt2 != rt:
                router.write_text(nt2, encoding="utf-8")
                deleted.append("scrub:router.invite-codes")
        routes_util = fe / "utils" / "menuRoutes.js"
        if routes_util.is_file():
            raw = routes_util.read_text(encoding="utf-8")
            new = re.sub(
                r"(?m)^\s*invite_codes\s*:\s*['\"][^'\"]+['\"]\s*,?\s*\n",
                "",
                raw,
            )
            if new != raw:
                routes_util.write_text(new, encoding="utf-8")
                deleted.append("scrub:menuRoutes.invite_codes")


def prune_student_pack(dest: Path, spec: dict[str, Any] | None = None) -> dict[str, Any]:
    """按 spec 裁剪工作区；返回统计。可对已有工作区幂等重跑。"""
    dest = Path(dest)
    if spec is None:
        sp = dest / "spec.json"
        if sp.is_file():
            import json

            spec = json.loads(sp.read_text(encoding="utf-8"))
        else:
            spec = {}
    assert isinstance(spec, dict)
    caps = _caps(spec)
    domain = _domain(spec)
    java_root = _java_root(dest)
    fe = _fe_src(dest)
    deleted: list[str] = []
    stripped_types: list[str] = []
    enrichers_to_kill: set[str] = set()
    vue_killed: set[str] = set()

    for island in _ISLANDS:
        if _should_keep(island, caps, domain):
            continue
        # special: parcel enricher shared — only kill routes file refs if BOTH parcel caps off
        if island.id == "parcel_shelf" and ("parcel_ship" in caps):
            # still delete shelf store but keep enricher for ship
            pass
        if island.id == "parcel_ship" and ("parcel_shelf" in caps):
            pass
        if island.id in ("parcel_shelf", "parcel_ship"):
            if "parcel_shelf" not in caps and "parcel_ship" not in caps:
                enrichers_to_kill.update(island.router_enrichers)
        elif island.id in ("occupy_span", "material_check", "balance_ledger", "lost_clue"):
            # shared withBorrowThickenRoutes — only kill if all related caps off
            related = {"occupy_span", "material_check", "balance_ledger", "lost_clue", "borrow_credit"}
            if not (related & caps):
                enrichers_to_kill.update(island.router_enrichers)
        else:
            enrichers_to_kill.update(island.router_enrichers)

        if java_root:
            for rel in island.java_files:
                if rel.endswith(".vue"):
                    continue
                if _is_workbench_keep(rel, kind="java"):
                    continue
                p = java_root / rel
                if p.is_file():
                    p.unlink()
                    deleted.append(f"java:{rel}")
        if fe:
            for rel in island.vue_files:
                rel_n = rel.replace("\\", "/")
                if _is_workbench_keep(rel_n, kind="vue"):
                    continue
                vue_killed.add(rel_n)
                p = fe / rel
                if p.is_file():
                    p.unlink()
                    deleted.append(f"vue:{rel}")
        stripped_types.extend(island.types)

    # strip usages from remaining java
    if java_root and stripped_types:
        for java in java_root.rglob("*.java"):
            raw = java.read_text(encoding="utf-8")
            new = raw
            for tname in stripped_types:
                if tname in new:
                    new = _strip_type_usages(new, tname)
            if new != raw:
                java.write_text(new, encoding="utf-8")

    # 无 seat_select：OrderStore 里影院卖品方法/调用整段删掉（交源码不能留空壳）
    if java_root and "SeatStore" in set(stripped_types):
        for order in java_root.rglob("OrderStore.java"):
            raw = order.read_text(encoding="utf-8")
            new = _scrub_order_cinema_snacks(raw)
            if new != raw:
                order.write_text(new, encoding="utf-8")
                deleted.append("scrub:OrderStore.cinemaSnacks")

    # router：enricher 置空透传 + 抹掉已删 Vue 的 import 路由项
    if fe:
        router = fe / "router" / "index.js"
        if router.is_file() and (enrichers_to_kill or vue_killed):
            rt = router.read_text(encoding="utf-8")
            nt = _strip_router_enrichers(rt, enrichers_to_kill)
            nt = _scrub_router_vue_imports(nt, vue_killed)
            if nt != rt:
                router.write_text(nt, encoding="utf-8")

        # 布局等残留引用
        _scrub_frontend_killed_refs(fe, vue_killed)

        # 路由不可达的 views/components 再扫一遍（补名单漏网）
        for rel in _sweep_unreachable_frontend(fe):
            deleted.append(f"vue-orphan:{rel}")
            vue_killed.add(rel)
        if vue_killed:
            _scrub_frontend_killed_refs(fe, vue_killed)
            if router.is_file():
                rt = router.read_text(encoding="utf-8")
                nt = _scrub_router_vue_imports(rt, vue_killed)
                if nt != rt:
                    router.write_text(nt, encoding="utf-8")

    # 邀请码：开题未挂则连源码一起裁（禁止只关菜单留空壳页）
    if not _invite_wanted(spec):
        _prune_invite_codes(dest, java_root=java_root, fe=fe, deleted=deleted)

    return {
        "domain": domain,
        "capabilities": sorted(caps),
        "deleted": deleted,
        "stripped_types": sorted(set(stripped_types)),
        "router_enrichers_cleared": sorted(enrichers_to_kill),
        "deleted_count": len(deleted),
    }


def scan_forbidden_island_files(
    dest: Path, spec: dict[str, Any] | None = None
) -> list[str]:
    """扫描学生包：未挂岛却仍存在的 Java/Vue 路径（门禁用）。"""
    dest = Path(dest)
    if spec is None:
        sp = dest / "spec.json"
        if sp.is_file():
            import json

            spec = json.loads(sp.read_text(encoding="utf-8"))
        else:
            spec = {}
    assert isinstance(spec, dict)
    caps = _caps(spec)
    domain = _domain(spec)
    java_root = _java_root(dest)
    fe = _fe_src(dest)
    hits: list[str] = []

    for island in _ISLANDS:
        if _should_keep(island, caps, domain):
            continue
        if java_root:
            for rel in island.java_files:
                if rel.endswith(".vue"):
                    continue
                if _is_workbench_keep(rel, kind="java"):
                    continue
                if (java_root / rel).is_file():
                    hits.append(f"java:{rel}")
            for tname in island.types:
                for p in java_root.rglob(f"{tname}.java"):
                    rel_hit = p.relative_to(java_root).as_posix()
                    if _is_workbench_keep(rel_hit, kind="java"):
                        continue
                    hits.append(f"java:{rel_hit}")
        if fe:
            for rel in island.vue_files:
                rel_n = rel.replace("\\", "/")
                if _is_workbench_keep(rel_n, kind="vue"):
                    continue
                if (fe / rel_n).is_file():
                    hits.append(f"vue:{rel_n}")
    if not _invite_wanted(spec):
        if java_root:
            for rel in _INVITE_JAVA_RELS:
                if (java_root / rel).is_file():
                    hits.append(f"java:{rel}")
        if fe:
            for rel in _INVITE_VUE_RELS:
                rel_n = rel.replace("\\", "/")
                if (fe / rel_n).is_file():
                    hits.append(f"vue:{rel_n}")
    return sorted(set(hits))


def evaluate_pack_lean_gate(
    workspace: Path, spec: dict[str, Any] | None = None
) -> dict[str, Any]:
    """p3lean：本题未挂岛不得残留源码文件。"""
    hits = scan_forbidden_island_files(workspace, spec)
    ok = not hits
    sample = hits[:12]
    desc = (
        "未见未挂岛残留文件"
        if ok
        else f"未挂岛仍残留 {len(hits)} 个文件：{', '.join(sample)}"
        + ("…" if len(hits) > len(sample) else "")
    )
    return {
        "ok": ok,
        "label": "学生包瘦身 · 未挂岛无残留",
        "desc": desc,
        "detail": {"forbidden": hits[:40], "count": len(hits)},
    }
