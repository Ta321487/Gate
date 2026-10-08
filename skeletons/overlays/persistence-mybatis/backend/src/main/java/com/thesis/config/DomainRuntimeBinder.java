package com.thesis.config;

import com.thesis.capability.ArchiveLogStore;
import com.thesis.capability.AuditLogStore;
import com.thesis.capability.StaffRosterStore;
import com.thesis.capability.BookSuggestStore;
import com.thesis.capability.BorrowCreditStore;
import com.thesis.capability.ParcelShelfStore;
import com.thesis.capability.ParcelShipStore;
import com.thesis.capability.EquipmentDictStore;
import com.thesis.capability.ArchiveStore;
import com.thesis.capability.BrowseHistoryStore;
import com.thesis.capability.CouponStore;
import com.thesis.capability.ConsignStore;
import com.thesis.capability.WeighSaleStore;
import com.thesis.capability.ShootStore;
import com.thesis.capability.BoardingStore;
import com.thesis.capability.RoomBoardStore;
import com.thesis.capability.FrontDeskStore;
import com.thesis.capability.VenueCleanStore;
import com.thesis.capability.BuybackStore;
import com.thesis.capability.DigitalGoodsStore;
import com.thesis.capability.RentalBondStore;
import com.thesis.capability.LessonStore;
import com.thesis.capability.DeliveryWindowStore;
import com.thesis.capability.BlindBoxStore;
import com.thesis.capability.GroupBuyStore;
import com.thesis.capability.PurchaseGateStore;
import com.thesis.capability.FavoriteStore;
import com.thesis.capability.LineCustomStore;
import com.thesis.capability.LoyaltyStore;
import com.thesis.capability.OrderReviewStore;
import com.thesis.capability.OrderStore;
import com.thesis.capability.SlotStore;
import com.thesis.capability.TicketLookupStore;
import com.thesis.capability.TicketStore;
import com.thesis.common.PasswordHashes;
import com.thesis.service.MessageStore;
import com.thesis.service.DmStore;
import com.thesis.service.ExamStore;
import com.thesis.service.SurveyStore;
import com.thesis.service.UserStore;
import com.thesis.service.VoteStore;
import com.thesis.service.BalanceLedgerStore;
import com.thesis.service.GradeScoreStore;
import com.thesis.service.FundPublicityStore;
import com.thesis.service.DoclibStore;
import com.thesis.service.ESignStore;
import com.thesis.service.MaterialCheckStore;
import com.thesis.service.ClaimProofStore;
import com.thesis.service.LostMessageStore;
import com.thesis.service.OccupySpanStore;
import com.thesis.service.SeatStore;
import com.thesis.service.StockIoStore;
import com.thesis.service.TimebankStore;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * 按 thesis.* 配置绑定能力运行时（薄领域无专用 Store）。
 * 用 ApplicationRunner：保证 MybatisSupport 已注入后再 ensureStaffColumns。
 */
@Component
@Order(0)
public class DomainRuntimeBinder implements ApplicationRunner {

    private final String ticketMode = TicketPolicy.MODE;

    private final String ticketTable = TicketPolicy.TABLE;

    private final boolean enableTicket = TicketPolicy.ENABLED;

    private final String archiveCategoryTable = AppPolicy.ARCHIVE_CATEGORY_TABLE;

    private final String archiveItemTable = AppPolicy.ARCHIVE_ITEM_TABLE;

    @Value("${thesis.register-role:user}")
    private String registerRole;

    @Value("${thesis.password-hash:none}")
    private String passwordHash;

    private final String lookupSiteTable = AppPolicy.LOOKUP_SITE_TABLE;

    private final String lookupUnitTable = AppPolicy.LOOKUP_UNIT_TABLE;

    private final String lookupTypeTable = AppPolicy.LOOKUP_TYPE_TABLE;

    private final String lookupSiteLabel = AppPolicy.LOOKUP_SITE_LABEL;

    private final String lookupUnitLabel = AppPolicy.LOOKUP_UNIT_LABEL;

    private final String lookupTypeLabel = AppPolicy.LOOKUP_TYPE_LABEL;

    /** 空串 = 管理端不展示单元容量列 */
    private final String lookupUnitCapacityLabel = AppPolicy.LOOKUP_UNIT_CAPACITY_LABEL;

    @Value("${thesis.use-quota:true}")
    private boolean useQuota;

    private final boolean useDeadline = TicketPolicy.USE_DEADLINE;

    private final boolean allowMultiTicket = TicketPolicy.ALLOW_MULTI;

    private final boolean checkTimeConflict = TicketPolicy.CHECK_TIME_CONFLICT;

    private final String orderCartTable = AppPolicy.ORDER_CART_TABLE;

    private final String orderTable = AppPolicy.ORDER_TABLE;

    private final String orderLineTable = AppPolicy.ORDER_LINE_TABLE;

    private final String slotTable = AppPolicy.SLOT_TABLE;

    private final String reservationTable = AppPolicy.RESERVATION_TABLE;

    private final boolean ticketTwoLevel = TicketPolicy.TWO_LEVEL;

    private final boolean ticketThreeLevel = TicketPolicy.THREE_LEVEL;

    private final boolean ticketRequireAttach = TicketPolicy.REQUIRE_ATTACH;

    private final boolean ticketAllowRating = TicketPolicy.ALLOW_RATING;

    private final boolean ticketCheckMutex = TicketPolicy.CHECK_MUTEX;

    private final int ticketCategoryLimit = TicketPolicy.CATEGORY_LIMIT;

    private final int ticketLoanDays = TicketPolicy.LOAN_DAYS;

    private final int ticketMaxActive = TicketPolicy.MAX_ACTIVE;

    private final double ticketFinePerDay = TicketPolicy.FINE_PER_DAY;

    private final String ticketPickupPlace = TicketPolicy.PICKUP_PLACE;

    private final boolean archiveSoftDelete = AppPolicy.ARCHIVE_SOFT_DELETE;

    private final boolean archiveUserPublish = AppPolicy.ARCHIVE_USER_PUBLISH;

    private final boolean archivePublishReview = AppPolicy.ARCHIVE_PUBLISH_REVIEW;

    private final String archiveTagTable = AppPolicy.ARCHIVE_TAG_TABLE;

    private final String archiveItemTagTable = AppPolicy.ARCHIVE_ITEM_TAG_TABLE;

    @Value("${thesis.multi-category-enabled:false}")
    private boolean multiCategoryEnabled;

    @Value("${thesis.archive-item-category-table:}")
    private String archiveItemCategoryTable;

    private final boolean ticketWeekCalendar = TicketPolicy.WEEK_CALENDAR;

    private final boolean ticketAllowCheckin = TicketPolicy.ALLOW_CHECKIN;

    private final boolean ticketPeerAccept = TicketPolicy.PEER_ACCEPT;

    private final boolean ticketIssuePassCode = TicketPolicy.ISSUE_PASS_CODE;

    private final boolean ticketAllowRenew = TicketPolicy.ALLOW_RENEW;

    private final boolean ticketAllowWaitlist = TicketPolicy.ALLOW_WAITLIST;

    private final boolean ticketAllowBookHold = TicketPolicy.ALLOW_BOOK_HOLD;

    private final boolean ticketAllowBookLost = TicketPolicy.ALLOW_BOOK_LOST;

    private final boolean ticketRequireReturnAttach = TicketPolicy.REQUIRE_RETURN_ATTACH;

    private final int ticketHoldHours = TicketPolicy.HOLD_HOURS;

    private final int ticketMaxRenew = TicketPolicy.MAX_RENEW;

    private final int ticketRenewDays = TicketPolicy.RENEW_DAYS;

    private final int ticketDueSoonDays = TicketPolicy.DUE_SOON_DAYS;

    private final int ticketMaxOverdueTimes = TicketPolicy.MAX_OVERDUE_TIMES;

    private final boolean ticketCreditOnOverdue = TicketPolicy.CREDIT_ON_OVERDUE;

    private final int ticketCreditInitial = TicketPolicy.CREDIT_INITIAL;

    private final int ticketCreditOverdueDelta = TicketPolicy.CREDIT_OVERDUE_DELTA;

    private final int ticketCreditBlockBelow = TicketPolicy.CREDIT_BLOCK_BELOW;

    private final boolean ticketNoShowAfterEnd = TicketPolicy.NO_SHOW_AFTER_END;

    private final double ticketNoShowPenaltyYuan = TicketPolicy.NO_SHOW_PENALTY_YUAN;

    private final boolean ticketPickLoanPeriod = TicketPolicy.PICK_LOAN_PERIOD;

    private final boolean ticketAllowQty = TicketPolicy.ALLOW_QTY;

    private final boolean ticketRequireRemark = TicketPolicy.REQUIRE_REMARK;

    private final boolean ticketPickDateRange = TicketPolicy.PICK_DATE_RANGE;

    private final boolean ticketApproveEndsFlow = TicketPolicy.APPROVE_ENDS_FLOW;

    private final boolean ticketAutoApprove = TicketPolicy.AUTO_APPROVE;

    private final boolean ticketRequireClaimCode = TicketPolicy.REQUIRE_CLAIM_CODE;

    private final boolean ticketMatchProfileRoom = TicketPolicy.MATCH_PROFILE_ROOM;

    private final String ticketMatchProfileBuildingKey = TicketPolicy.MATCH_PROFILE_BUILDING_KEY;

    private final String ticketMatchProfileRoomKey = TicketPolicy.MATCH_PROFILE_ROOM_KEY;

    private final String ticketMatchProfileBuildingField = TicketPolicy.MATCH_PROFILE_BUILDING_FIELD;

    private final String ticketMatchProfileRoomField = TicketPolicy.MATCH_PROFILE_ROOM_FIELD;

    private final boolean ticketMatchProfileLooseBuilding = TicketPolicy.MATCH_PROFILE_LOOSE_BUILDING;

    private final String ticketMatchProfileNeedMessage = TicketPolicy.MATCH_PROFILE_NEED_MESSAGE;

    private final String ticketMatchProfileDenyMessage = TicketPolicy.MATCH_PROFILE_DENY_MESSAGE;

    private final boolean ticketApplicantCompleteOnly = TicketPolicy.APPLICANT_COMPLETE_ONLY;

    private final boolean ticketAllowProxyPickup = TicketPolicy.ALLOW_PROXY_PICKUP;

    private final boolean ticketBedConstraint = TicketPolicy.BED_CONSTRAINT;

    private final String ticketBedConstraintNeedMessage = TicketPolicy.BED_CONSTRAINT_NEED_MESSAGE;

    private final String ticketBedConstraintDenyMessage = TicketPolicy.BED_CONSTRAINT_DENY_MESSAGE;

    private final boolean ticketArrivalNotify = TicketPolicy.ARRIVAL_NOTIFY;

    private final boolean ticketRequireNoticeAck = TicketPolicy.REQUIRE_NOTICE_ACK;

    private final boolean ticketAllowDeposit = TicketPolicy.ALLOW_DEPOSIT;

    private final boolean ticketAllowExceptionClose = TicketPolicy.ALLOW_EXCEPTION_CLOSE;

    private final boolean ticketRequireTrainingAck = TicketPolicy.REQUIRE_TRAINING_ACK;

    private final boolean ticketRequireInsuranceAck = TicketPolicy.REQUIRE_INSURANCE_ACK;
    private final boolean ticketRequireMeetingAck = TicketPolicy.REQUIRE_MEETING_ACK;
    private final boolean ticketRequireApplyInvite = TicketPolicy.REQUIRE_APPLY_INVITE;
    private final boolean ticketRequirePriceNoteAck = TicketPolicy.REQUIRE_PRICE_NOTE_ACK;
    private final boolean ticketRequireSponsorAck = TicketPolicy.REQUIRE_SPONSOR_ACK;
    private final boolean ticketRequirePlanAck = TicketPolicy.REQUIRE_PLAN_ACK;
    private final boolean ticketRequirePrereqAck = TicketPolicy.REQUIRE_PREREQ_ACK;
    private final boolean ticketAgeConstraint = TicketPolicy.AGE_CONSTRAINT;
    private final String ticketAgeConstraintNeedMessage = TicketPolicy.AGE_CONSTRAINT_NEED_MESSAGE;
    private final String ticketAgeConstraintDenyMessage = TicketPolicy.AGE_CONSTRAINT_DENY_MESSAGE;
    private final boolean ticketAllowLateMinutes = TicketPolicy.ALLOW_LATE_MINUTES;
    private final boolean ticketAllowWishOrder = TicketPolicy.ALLOW_WISH_ORDER;
    private final boolean ticketAllowVolunteerRole = TicketPolicy.ALLOW_VOLUNTEER_ROLE;
    private final boolean ticketAllowAdminCheckin = TicketPolicy.ALLOW_ADMIN_CHECKIN;
    private final boolean ticketRequireTourNoticeAck = TicketPolicy.REQUIRE_TOUR_NOTICE_ACK;
    private final boolean ticketAllowCompanions = TicketPolicy.ALLOW_COMPANIONS;
    private final boolean ticketAllowLottery = TicketPolicy.ALLOW_LOTTERY;
    private final boolean ticketAllowSeatZone = TicketPolicy.ALLOW_SEAT_ZONE;
    private final boolean ticketAllowTicketTransfer = TicketPolicy.ALLOW_TICKET_TRANSFER;
    private final boolean ticketAllowTicketWallet = TicketPolicy.ALLOW_TICKET_WALLET;
    private final boolean ticketAllowApplyBlacklist = TicketPolicy.ALLOW_APPLY_BLACKLIST;
    private final boolean ticketScheduleChangeNotify = TicketPolicy.SCHEDULE_CHANGE_NOTIFY;
    private final boolean ticketAllowPostGallery = TicketPolicy.ALLOW_POST_GALLERY;
    private final boolean ticketRequireCreditWritebackAck = TicketPolicy.REQUIRE_CREDIT_WRITEBACK_ACK;

    private final boolean ticketBlockIfCalibExpired = TicketPolicy.BLOCK_IF_CALIB_EXPIRED;

    private final boolean ticketAllowProjectNo = TicketPolicy.ALLOW_PROJECT_NO;

    private final boolean ticketAllowProcureRef = TicketPolicy.ALLOW_PROCURE_REF;

    private final boolean ticketProcureToStockIn = TicketPolicy.PROCURE_TO_STOCK_IN;

    private final boolean ticketAllowDualReview = TicketPolicy.ALLOW_DUAL_REVIEW;

    private final boolean ticketAllowShipFee = TicketPolicy.ALLOW_SHIP_FEE;

    private final boolean ticketAllowUtilityNote = TicketPolicy.ALLOW_UTILITY_NOTE;

    private final int ticketMaxCancelHolds = TicketPolicy.MAX_CANCEL_HOLDS;

    private final boolean ticketOverdueAutoCompensate = TicketPolicy.OVERDUE_AUTO_COMPENSATE;

    private final boolean ticketAllowFineWaive = TicketPolicy.ALLOW_FINE_WAIVE;

    private final boolean ticketRenewBlockIfHeld = TicketPolicy.RENEW_BLOCK_IF_HELD;

    private final boolean ticketRequirePeerConfirm = TicketPolicy.REQUIRE_PEER_CONFIRM;

    private final boolean ticketRequireAbandonDual = TicketPolicy.REQUIRE_ABANDON_DUAL;

    private final int ticketFollowRemindDays = TicketPolicy.FOLLOW_REMIND_DAYS;

    private final int ticketMinRemarkWords = TicketPolicy.MIN_REMARK_WORDS;

    private final int ticketMaxReviseTimes = TicketPolicy.MAX_REVISE_TIMES;

    private final int ticketStaleFollowDays = TicketPolicy.STALE_FOLLOW_DAYS;

    private final boolean ticketLevelAffectsDeadline = TicketPolicy.LEVEL_AFFECTS_DEADLINE;

    private final int ticketLevelSlaHighDays = TicketPolicy.LEVEL_SLA_HIGH_DAYS;

    private final int ticketLevelSlaMidDays = TicketPolicy.LEVEL_SLA_MID_DAYS;

    private final int ticketLevelSlaLowDays = TicketPolicy.LEVEL_SLA_LOW_DAYS;

    private final boolean ticketNotifyDutyOnReport = TicketPolicy.NOTIFY_DUTY_ON_REPORT;

    private final boolean ticketAllowObjectionWindow = TicketPolicy.ALLOW_OBJECTION_WINDOW;

    private final int ticketObjectionDays = TicketPolicy.OBJECTION_DAYS;

    private final boolean ticketPhoneDupCheck = TicketPolicy.PHONE_DUP_CHECK;

    private final boolean ticketRequireCloseAttach = TicketPolicy.REQUIRE_CLOSE_ATTACH;

    private final boolean ticketRequireReturnDate = TicketPolicy.REQUIRE_RETURN_DATE;

    private final boolean ticketRequireFeedbackSet = TicketPolicy.REQUIRE_FEEDBACK_SET;

    private final boolean ticketRequireAppraisal = TicketPolicy.REQUIRE_APPRAISAL;

    private final boolean ticketAllowDealAmount = TicketPolicy.ALLOW_DEAL_AMOUNT;

    private final boolean ticketAllowNextAction = TicketPolicy.ALLOW_NEXT_ACTION;

    private final boolean ticketAllowInterviewResult = TicketPolicy.ALLOW_INTERVIEW_RESULT;

    private final boolean ticketAllowWrittenScore = TicketPolicy.ALLOW_WRITTEN_SCORE;

    private final boolean ticketAllowBgCheckNote = TicketPolicy.ALLOW_BG_CHECK_NOTE;

    private final boolean ticketAllowDefenseResult = TicketPolicy.ALLOW_DEFENSE_RESULT;

    private final boolean ticketMaskBankAccount = TicketPolicy.MASK_BANK_ACCOUNT;

    private final boolean ticketAllowDisburseBatch = TicketPolicy.ALLOW_DISBURSE_BATCH;

    private final boolean ticketAllowLeaveProxy = TicketPolicy.ALLOW_LEAVE_PROXY;

    private final boolean ticketAllowCompanyEval = TicketPolicy.ALLOW_COMPANY_EVAL;

    private final boolean ticketAllowExcellentMark = TicketPolicy.ALLOW_EXCELLENT_MARK;

    private final boolean ticketAllowRecordUrl = TicketPolicy.ALLOW_RECORD_URL;

    private final boolean ticketAllowConfidential = TicketPolicy.ALLOW_CONFIDENTIAL;

    private final boolean ticketAllowAssignDept = TicketPolicy.ALLOW_ASSIGN_DEPT;

    private final boolean ticketAllowBatchHire = TicketPolicy.ALLOW_BATCH_HIRE;

    private final boolean ticketWeekReportRemind = TicketPolicy.WEEK_REPORT_REMIND;

    private final boolean ticketHomeVisitTemplate = TicketPolicy.HOME_VISIT_TEMPLATE;

    private final boolean ticketAttachByLeaveType = TicketPolicy.ATTACH_BY_LEAVE_TYPE;

    private final boolean ticketAllowMakeupApply = TicketPolicy.ALLOW_MAKEUP_APPLY;

    private final int ticketWeekReportDeadlineDay = TicketPolicy.WEEK_REPORT_DEADLINE_DAY;

    private final boolean ticketRepairThicken = TicketPolicy.REPAIR_THICKEN;

    private final boolean ticketApplyThicken = TicketPolicy.APPLY_THICKEN;

    private final boolean ticketApproveThicken = TicketPolicy.APPROVE_THICKEN;

    private final boolean ticketAllowApproveCc = TicketPolicy.ALLOW_APPROVE_CC;

    private final int ticketMinApproveRemarkWords = TicketPolicy.MIN_APPROVE_REMARK_WORDS;

    private final boolean ticketAllowApproveTransfer = TicketPolicy.ALLOW_APPROVE_TRANSFER;

    private final boolean ticketAllowApproveDelegate = TicketPolicy.ALLOW_APPROVE_DELEGATE;

    private final boolean ticketAllowApproveRemarkAttach = TicketPolicy.ALLOW_APPROVE_REMARK_ATTACH;

    private final boolean ticketAllowApproveCcComment = TicketPolicy.ALLOW_APPROVE_CC_COMMENT;

    private final boolean ticketAllowApproveAutoPass = TicketPolicy.ALLOW_APPROVE_AUTO_PASS;

    private final int ticketApproveAutoPassHours = TicketPolicy.APPROVE_AUTO_PASS_HOURS;

    private final boolean ticketAllowCertPickup = TicketPolicy.ALLOW_CERT_PICKUP;

    private final boolean ticketAllowCertUrgent = TicketPolicy.ALLOW_CERT_URGENT;

    private final boolean ticketAllowSealCopies = TicketPolicy.ALLOW_SEAL_COPIES;

    private final boolean ticketAllowFleetMileage = TicketPolicy.ALLOW_FLEET_MILEAGE;

    private final boolean ticketAllowExpenseInvoice = TicketPolicy.ALLOW_EXPENSE_INVOICE;

    private final boolean ticketAllowVisitorCount = TicketPolicy.ALLOW_VISITOR_COUNT;

    private final boolean ticketAllowAwardCertNo = TicketPolicy.ALLOW_AWARD_CERT_NO;

    private final boolean ticketAllowVendorQuotes = TicketPolicy.ALLOW_VENDOR_QUOTES;

    private final boolean ticketForceOnePerArchive = TicketPolicy.FORCE_ONE_PER_ARCHIVE;

    private final int ticketMinVendorQuotes = TicketPolicy.MIN_VENDOR_QUOTES;

    private final int ticketNotifyArchiveExpireDays = TicketPolicy.NOTIFY_ARCHIVE_EXPIRE_DAYS;

    private final String ticketOnePerArchiveDenyMessage = TicketPolicy.ONE_PER_ARCHIVE_DENY_MESSAGE;

    private final boolean ticketAllowEvalOpenWindow = TicketPolicy.ALLOW_EVAL_OPEN_WINDOW;

    private final boolean ticketAllowCompHours = TicketPolicy.ALLOW_COMP_HOURS;

    private final boolean ticketAllowFleetCrew = TicketPolicy.ALLOW_FLEET_CREW;

    private final boolean ticketAllowEthicBatch = TicketPolicy.ALLOW_ETHIC_BATCH;

    private final String ticketEvalOpenWindowDenyMessage = TicketPolicy.EVAL_OPEN_WINDOW_DENY_MESSAGE;

    private final boolean ticketAllowPassExpire = TicketPolicy.ALLOW_PASS_EXPIRE;

    private final boolean ticketAllowReturnFuel = TicketPolicy.ALLOW_RETURN_FUEL;

    private final boolean ticketAllowLaborPlace = TicketPolicy.ALLOW_LABOR_PLACE;

    private final boolean ticketAllowPromoPlace = TicketPolicy.ALLOW_PROMO_PLACE;

    private final boolean ticketAllowEthicMeeting = TicketPolicy.ALLOW_ETHIC_MEETING;

    private final boolean ticketAllowEffectiveOn = TicketPolicy.ALLOW_EFFECTIVE_ON;

    private final boolean ticketAllowCertIssueNo = TicketPolicy.ALLOW_CERT_ISSUE_NO;

    private final boolean ticketAllowPromoFeedback = TicketPolicy.ALLOW_PROMO_FEEDBACK;

    private final boolean ticketAllowDocRev = TicketPolicy.ALLOW_DOC_REV;

    private final boolean ticketAllowFitoutQuiet = TicketPolicy.ALLOW_FITOUT_QUIET;

    private final boolean ticketAllowSealClosePhoto = TicketPolicy.ALLOW_SEAL_CLOSE_PHOTO;

    private final boolean ticketAllowIssueCopies = TicketPolicy.ALLOW_ISSUE_COPIES;

    private final boolean ticketAllowSignParties = TicketPolicy.ALLOW_SIGN_PARTIES;

    private final boolean ticketAllowTrainHours = TicketPolicy.ALLOW_TRAIN_HOURS;

    private final boolean ticketAllowInspectExpire = TicketPolicy.ALLOW_INSPECT_EXPIRE;

    private final boolean ticketAllowMemberChange = TicketPolicy.ALLOW_MEMBER_CHANGE;

    private final boolean ticketAllowProcureBudget = TicketPolicy.ALLOW_PROCURE_BUDGET;

    private final boolean ticketAllowCheckinException = TicketPolicy.ALLOW_CHECKIN_EXCEPTION;

    private final boolean ticketAllowVisitPurpose = TicketPolicy.ALLOW_VISIT_PURPOSE;

    private final boolean ticketAllowFleetViolation = TicketPolicy.ALLOW_FLEET_VIOLATION;

    private final boolean ticketAllowFitoutRectify = TicketPolicy.ALLOW_FITOUT_RECTIFY;

    private final boolean ticketAllowProjNodeRemind = TicketPolicy.ALLOW_PROJ_NODE_REMIND;

    private final boolean ticketAllowClubCopyLast = TicketPolicy.ALLOW_CLUB_COPY_LAST;

    private final boolean ticketAllowProcureReturn = TicketPolicy.ALLOW_PROCURE_RETURN;

    private final boolean ticketAllowMoralObjection = TicketPolicy.ALLOW_MORAL_OBJECTION;

    private final boolean ticketAllowProjFundUse = TicketPolicy.ALLOW_PROJ_FUND_USE;

    private final boolean ticketAllowEvalDimWeight = TicketPolicy.ALLOW_EVAL_DIM_WEIGHT;

    private final boolean ticketAllowVisitSlotRemain = TicketPolicy.ALLOW_VISIT_SLOT_REMAIN;

    private final boolean ticketAllowPlagiarismUrl = TicketPolicy.ALLOW_PLAGIARISM_URL;

    private final boolean ticketAllowAbsentStreak = TicketPolicy.ALLOW_ABSENT_STREAK;

    private final boolean ticketAllowPartyStage = TicketPolicy.ALLOW_PARTY_STAGE;

    private final boolean ticketAllowEvalObserve = TicketPolicy.ALLOW_EVAL_OBSERVE;

    private final boolean ticketAllowScheduleImpact = TicketPolicy.ALLOW_SCHEDULE_IMPACT;

    private final boolean ticketAllowContractAmount = TicketPolicy.ALLOW_CONTRACT_AMOUNT;

    private final boolean ticketAllowExpenseLines = TicketPolicy.ALLOW_EXPENSE_LINES;

    private final boolean ticketAllowTripLegs = TicketPolicy.ALLOW_TRIP_LEGS;

    private final boolean ticketAllowHideEvalResult = TicketPolicy.ALLOW_HIDE_EVAL_RESULT;

    private final boolean ticketAllowSignRemarkVisible = TicketPolicy.ALLOW_SIGN_REMARK_VISIBLE;

    private final boolean ticketAllowProjChangeLog = TicketPolicy.ALLOW_PROJ_CHANGE_LOG;

    private final boolean ticketAllowCertVerify = TicketPolicy.ALLOW_CERT_VERIFY;

    private final boolean ticketAllowVisitWalkIn = TicketPolicy.ALLOW_VISIT_WALK_IN;

    private final boolean ticketAllowCheckinProxy = TicketPolicy.ALLOW_CHECKIN_PROXY;

    private final boolean ticketAllowClubRoster = TicketPolicy.ALLOW_CLUB_ROSTER;

    private final boolean ticketAllowCarpassParkingMutex = TicketPolicy.ALLOW_CARPASS_PARKING_MUTEX;

    private final boolean ticketAllowEvalUrge = TicketPolicy.ALLOW_EVAL_URGE;

    private final boolean ticketAllowContractRenew = TicketPolicy.ALLOW_CONTRACT_RENEW;

    private final boolean ticketAllowContractExpireRemind = TicketPolicy.ALLOW_CONTRACT_EXPIRE_REMIND;

    private final boolean ticketAllowCertPickupRedeem = TicketPolicy.ALLOW_CERT_PICKUP_REDEEM;

    private final boolean ticketAllowExamPassMin = TicketPolicy.ALLOW_EXAM_PASS_MIN;

    private final boolean ticketAllowCheckinSpot = TicketPolicy.ALLOW_CHECKIN_SPOT;

    private final boolean ticketAllowEvalBeforeGrade = TicketPolicy.ALLOW_EVAL_BEFORE_GRADE;

    private final boolean ticketAllowApproveDurationStats = TicketPolicy.ALLOW_APPROVE_DURATION_STATS;

    private final boolean ticketAllowAttachKeepOld = TicketPolicy.ALLOW_ATTACH_KEEP_OLD;

    private final boolean ticketAllowCertPickupQr = TicketPolicy.ALLOW_CERT_PICKUP_QR;

    private final boolean ticketAllowCertVerifyPage = TicketPolicy.ALLOW_CERT_VERIFY_PAGE;

    private final boolean ticketAllowVisitorPassPrint = TicketPolicy.ALLOW_VISITOR_PASS_PRINT;

    private final boolean ticketAllowCheckinDailyReport = TicketPolicy.ALLOW_CHECKIN_DAILY_REPORT;

    private final boolean ticketAllowEvalCollegeExport = TicketPolicy.ALLOW_EVAL_COLLEGE_EXPORT;

    private final boolean ticketAllowSealLedgerExport = TicketPolicy.ALLOW_SEAL_LEDGER_EXPORT;

    private final boolean ticketAllowMoralMaterialCheck = TicketPolicy.ALLOW_MORAL_MATERIAL_CHECK;

    private final boolean ticketAllowPartyMaterialTemplate = TicketPolicy.ALLOW_PARTY_MATERIAL_TEMPLATE;

    private final boolean ticketAllowPartyThoughtAttach = TicketPolicy.ALLOW_PARTY_THOUGHT_ATTACH;

    private final boolean ticketAllowCertFormPrint = TicketPolicy.ALLOW_CERT_FORM_PRINT;

    private final boolean ticketAllowSealFormPrint = TicketPolicy.ALLOW_SEAL_FORM_PRINT;

    private final boolean ticketAllowProjMidFormPrint = TicketPolicy.ALLOW_PROJ_MID_FORM_PRINT;

    private final boolean ticketAllowEthicOpinionPrint = TicketPolicy.ALLOW_ETHIC_OPINION_PRINT;

    private final boolean ticketAllowExpenseAttachCount = TicketPolicy.ALLOW_EXPENSE_ATTACH_COUNT;

    private final boolean ticketAllowFleetDriverCert = TicketPolicy.ALLOW_FLEET_DRIVER_CERT;

    private final int ticketPassExpireDays = TicketPolicy.PASS_EXPIRE_DAYS;



    private final String ticketApplyBlacklistDenyMessage = TicketPolicy.APPLY_BLACKLIST_DENY_MESSAGE;

    private final boolean ticketNotifyOnApplySuccess = TicketPolicy.NOTIFY_ON_APPLY_SUCCESS;

    private final boolean ticketAllowMeetingPlace = TicketPolicy.ALLOW_MEETING_PLACE;

    private final boolean ticketAllowEmergencyContact = TicketPolicy.ALLOW_EMERGENCY_CONTACT;

    private final int ticketCancelBeforeHours = TicketPolicy.CANCEL_BEFORE_HOURS;

    private final int ticketClaimCooldownHours = TicketPolicy.CLAIM_COOLDOWN_HOURS;

    private final int ticketMaxDropTimes = TicketPolicy.MAX_DROP_TIMES;

    private final int ticketSemesterCreditCap = TicketPolicy.SEMESTER_CREDIT_CAP;

    private final int ticketCreditWarnRemaining = TicketPolicy.CREDIT_WARN_REMAINING;

    private final boolean ticketAllowUserUrge = TicketPolicy.ALLOW_USER_URGE;

    private final int ticketUrgeCooldownMinutes = TicketPolicy.URGE_COOLDOWN_MINUTES;

    private final boolean ticketLockUrgeAfterRate = TicketPolicy.LOCK_URGE_AFTER_RATE;

    private final boolean ticketAllowCancelUrge = TicketPolicy.ALLOW_CANCEL_URGE;

    private final boolean ticketRequireFaultReason = TicketPolicy.REQUIRE_FAULT_REASON;

    private final boolean ticketRequireCloseSummary = TicketPolicy.REQUIRE_CLOSE_SUMMARY;

    private final boolean ticketRequireLowRatingRemark = TicketPolicy.REQUIRE_LOW_RATING_REMARK;

    private final boolean ticketSlaSplit = TicketPolicy.SLA_SPLIT;

    private final boolean ticketEscalateOnOverdue = TicketPolicy.ESCALATE_ON_OVERDUE;

    private final boolean ticketNotifySupervisorOnOverdue = TicketPolicy.NOTIFY_SUPERVISOR_ON_OVERDUE;

    private final boolean ticketAllowHoldResume = TicketPolicy.ALLOW_HOLD_RESUME;

    private final boolean ticketAllowCancelDispatched = TicketPolicy.ALLOW_CANCEL_DISPATCHED;

    private final boolean ticketAllowTicketDraft = TicketPolicy.ALLOW_TICKET_DRAFT;

    private final boolean ticketAllowFollowRate = TicketPolicy.ALLOW_FOLLOW_RATE;

    private final boolean ticketPreferredSlot = TicketPolicy.PREFERRED_SLOT;

    private final boolean ticketProgressSubscribe = TicketPolicy.PROGRESS_SUBSCRIBE;

    private final boolean ticketNightUrgent = TicketPolicy.NIGHT_URGENT;

    private final boolean ticketAllowPartsNote = TicketPolicy.ALLOW_PARTS_NOTE;

    private final boolean ticketAllowQuote = TicketPolicy.ALLOW_QUOTE;

    private final boolean ticketAllowPublicArea = TicketPolicy.ALLOW_PUBLIC_AREA;

    private final boolean ticketDupRoomCheck = TicketPolicy.DUP_ROOM_CHECK;

    private final boolean ticketAllowAssetCode = TicketPolicy.ALLOW_ASSET_CODE;

    private final boolean ticketAllowRemoteUrl = TicketPolicy.ALLOW_REMOTE_URL;

    private final boolean ticketAllowSerialNo = TicketPolicy.ALLOW_SERIAL_NO;

    private final boolean ticketAllowHelper = TicketPolicy.ALLOW_HELPER;

    private final boolean ticketAllowRatingTags = TicketPolicy.ALLOW_RATING_TAGS;

    private final boolean ticketTodayBoard = TicketPolicy.TODAY_BOARD;

    private final boolean ticketPrintTicket = TicketPolicy.PRINT_TICKET;

    private final boolean slotRequireRemark = AppPolicy.SLOT_REQUIRE_REMARK;

    private final boolean slotRequireConfirm = AppPolicy.SLOT_REQUIRE_CONFIRM;

    private final boolean slotAllowRating = AppPolicy.SLOT_ALLOW_RATING;

    private final int cancelFreeHours = AppPolicy.CANCEL_FREE_HOURS;

    private final int rescheduleMaxTimes = AppPolicy.RESCHEDULE_MAX_TIMES;

    private final int remindAheadMinutes = AppPolicy.REMIND_AHEAD_MINUTES;

    private final int noShowLimit = AppPolicy.NO_SHOW_LIMIT;

    private final int lateGraceMinutes = AppPolicy.LATE_GRACE_MINUTES;

    private final boolean reserveBlacklistEnabled = AppPolicy.RESERVE_BLACKLIST_ENABLED;

    private final int hospitalCancelCutoffMinutes = AppPolicy.HOSPITAL_CANCEL_CUTOFF_MINUTES;

    private final int hospitalIdLimitPerDay = AppPolicy.HOSPITAL_ID_LIMIT_PER_DAY;

    private final boolean hospitalWaitlistEnabled = AppPolicy.HOSPITAL_WAITLIST_ENABLED;

    private final boolean patientProfileEnabled = AppPolicy.PATIENT_PROFILE_ENABLED;

    private final int parkingHourlyYuan = AppPolicy.PARKING_HOURLY_YUAN;

    private final int parkingOvertimeYuan = AppPolicy.PARKING_OVERTIME_YUAN;

    private final boolean parkingPassEnabled = AppPolicy.PARKING_PASS_ENABLED;

    private final int meetingMinDurationMinutes = AppPolicy.MEETING_MIN_DURATION_MINUTES;

    private final boolean meetingMinutesRequired = AppPolicy.MEETING_MINUTES_REQUIRED;

    private final int salonRescheduleFeeYuan = AppPolicy.SALON_RESCHEDULE_FEE_YUAN;

    private final int hotelLateCheckoutFeeYuan = AppPolicy.HOTEL_LATE_CHECKOUT_FEE_YUAN;

    private final boolean hotelNoticeRequired = AppPolicy.HOTEL_NOTICE_REQUIRED;

    private final int carrentMileageOverFeeYuan = AppPolicy.CARRENT_MILEAGE_OVER_FEE_YUAN;

    private final int instrumentOvertimeYuan = AppPolicy.INSTRUMENT_OVERTIME_YUAN;

    private final boolean instrumentTrainingRequired = AppPolicy.INSTRUMENT_TRAINING_REQUIRED;

    private final boolean walletEnabled = AppPolicy.WALLET_ENABLED;

    private final boolean pointsEnabled = AppPolicy.POINTS_ENABLED;

    @Value("${thesis.spend-discount-enabled:false}")
    private boolean spendDiscountEnabled;

    @Value("${thesis.member-tier-enabled:false}")
    private boolean memberTierEnabled;

    @Value("${thesis.coupon-enabled:false}")
    private boolean couponEnabled;

    private final boolean orderReviewEnabled = AppPolicy.ORDER_REVIEW_ENABLED;

    @Value("${thesis.line-custom-enabled:false}")
    private boolean lineCustomEnabled;

    @Value("${thesis.line-custom-place-confirmed:false}")
    private boolean lineCustomPlaceConfirmed;

    @Value("${thesis.delivery-window-enabled:false}")
    private boolean deliveryWindowEnabled;

    @Value("${thesis.purchase-gate-enabled:false}")
    private boolean purchaseGateEnabled;

    @Value("${thesis.group-buy-enabled:false}")
    private boolean groupBuyEnabled;

    @Value("${thesis.blind-box-enabled:false}")
    private boolean blindBoxEnabled;

    @Value("${thesis.consign-enabled:false}")
    private boolean consignEnabled;

    @Value("${thesis.weigh-sale-enabled:false}")
    private boolean weighSaleEnabled;

    @Value("${thesis.shoot-enabled:false}")
    private boolean shootEnabled;

    @Value("${thesis.boarding-enabled:false}")
    private boolean boardingEnabled;

    @Value("${thesis.room-board-enabled:false}")
    private boolean roomBoardEnabled;

    @Value("${thesis.front-desk-enabled:false}")
    private boolean frontDeskEnabled;

    @Value("${thesis.housekeeping-enabled:false}")
    private boolean housekeepingEnabled;

    @Value("${thesis.venue-clean-enabled:false}")
    private boolean venueCleanEnabled;

    @Value("${thesis.buyback-enabled:false}")
    private boolean buybackEnabled;

    @Value("${thesis.lesson-pack-enabled:false}")
    private boolean lessonPackEnabled;

    @Value("${thesis.rental-bond-enabled:false}")
    private boolean rentalBondEnabled;

    @Value("${thesis.digital-goods-enabled:false}")
    private boolean digitalGoodsEnabled;

    @Value("${thesis.no-casual-refund:false}")
    private boolean noCasualRefund;

    @Value("${thesis.after-sale-days:0}")
    private int afterSaleDays;

    @Value("${thesis.ticket-refund-cutoff-minutes:0}")
    private int ticketRefundCutoffMinutes;

    @Value("${thesis.seat-hold-timeout-minutes:0}")
    private int seatHoldTimeoutMinutes;

    @Value("${thesis.packaging-fee-yuan:0}")
    private double packagingFeeYuan;

    @Value("${thesis.delivery-fee-base-yuan:0}")
    private double deliveryFeeBaseYuan;

    @Value("${thesis.delivery-fee-free-yuan:0}")
    private double deliveryFeeFreeYuan;

    @Value("${thesis.eta-minutes:0}")
    private int etaMinutes;

    private final boolean favoritesEnabled = AppPolicy.FAVORITES_ENABLED;

    @Value("${thesis.post-like-enabled:false}")
    private boolean postLikeEnabled;

    private final boolean contentReportEnabled = AppPolicy.CONTENT_REPORT_ENABLED;

    private final boolean postMuteEnabled = AppPolicy.POST_MUTE_ENABLED;

    @Value("${thesis.book-suggest-enabled:false}")
    private boolean bookSuggestEnabled;

    private final boolean parcelShelfEnabled = AppPolicy.PARCEL_SHELF_ENABLED;

    @Value("${thesis.parcel-ship-enabled:false}")
    private boolean parcelShipEnabled;

    @Value("${thesis.audit-log-enabled:false}")
    private boolean auditLogEnabled;

    @Value("${thesis.message-template-enabled:false}")
    private boolean messageTemplateEnabled;

    @Value("${thesis.staff-roster-enabled:false}")
    private boolean staffRosterEnabled;

    @Value("${thesis.room-equipment-enabled:false}")
    private boolean roomEquipmentEnabled;

    @Value("${thesis.audit-log-login-only:false}")
    private boolean auditLogLoginOnly;

    @Value("${thesis.browse-history-enabled:false}")
    private boolean browseHistoryEnabled;

    private final boolean archiveLogEnabled = AppPolicy.ARCHIVE_LOG_ENABLED;

    private final boolean examEnabled = AppPolicy.EXAM_ENABLED;

    @Value("${thesis.exam-practice-enabled:false}")
    private boolean examPracticeEnabled;

    @Value("${thesis.exam-explain-enabled:false}")
    private boolean examExplainEnabled;

    @Value("${thesis.exam-timer-enabled:false}")
    private boolean examTimerEnabled;

    @Value("${thesis.exam-attempt-limit-enabled:false}")
    private boolean examAttemptLimitEnabled;

    @Value("${thesis.exam-rank-enabled:false}")
    private boolean examRankEnabled;

    @Value("${thesis.exam-wrongbook-enabled:false}")
    private boolean examWrongbookEnabled;

    @Value("${thesis.exam-require-before-ticket:false}")
    private boolean examRequireBeforeTicket;

    private final boolean surveyEnabled = AppPolicy.SURVEY_ENABLED;

    private final boolean voteEnabled = AppPolicy.VOTE_ENABLED;

    private final boolean doclibEnabled = AppPolicy.DOCLIB_ENABLED;

    private final boolean timebankEnabled = AppPolicy.TIMEBANK_ENABLED;

    private final boolean timebankRedeemOnApprove = AppPolicy.TIMEBANK_REDEEM_ON_APPROVE;

    /** C-15 影院选座 */
    private final boolean seatSelectEnabled = AppPolicy.SEAT_SELECT_ENABLED;

    /** C-17 浅进销存 */
    private final boolean stockIoEnabled = AppPolicy.STOCK_IO_ENABLED;

    /** E-08 报废 */
    @Value("${thesis.stock-scrap-enabled:false}")
    private boolean stockScrapEnabled;

    /** E-08 盘点 */
    @Value("${thesis.stock-count-enabled:false}")
    private boolean stockCountEnabled;

    @Value("${thesis.stock-count-lock:false}")
    private boolean stockCountLock;

    @Value("${thesis.stock-blind-count:false}")
    private boolean stockBlindCount;

    @Value("${thesis.stock-require-diff-reason:false}")
    private boolean stockRequireDiffReason;

    @Value("${thesis.stock-scrap-approve-flow:false}")
    private boolean stockScrapApproveFlow;

    /** C-18 本地签章 */
    private final boolean eSignEnabled = AppPolicy.E_SIGN_ENABLED;

    private final boolean balanceLedgerEnabled = AppPolicy.BALANCE_LEDGER_ENABLED;

    private final boolean balanceLedgerDebitOnApprove = AppPolicy.BALANCE_LEDGER_DEBIT_ON_APPROVE;

    private final boolean gradeScoresEnabled = AppPolicy.GRADE_SCORES_ENABLED;

    private final boolean occupySpanEnabled = AppPolicy.OCCUPY_SPAN_ENABLED;

    private final boolean materialCheckEnabled = AppPolicy.MATERIAL_CHECK_ENABLED;

    private final boolean claimProofEnabled = AppPolicy.CLAIM_PROOF_ENABLED;

    private final boolean lostClueEnabled = AppPolicy.LOST_CLUE_ENABLED;

    @Value("${thesis.gallery-enabled:false}")
    private boolean galleryEnabled;

    private final boolean stockWarnNotify = AppPolicy.STOCK_WARN_NOTIFY;

    private final int stockWarnBelow = AppPolicy.STOCK_WARN_BELOW;

    @Value("${thesis.detail-attrs-enabled:false}")
    private boolean detailAttrsEnabled;

    @Value("${thesis.detail-attr-keys:}")
    private String detailAttrKeys;

    @Value("${thesis.flash-price-enabled:false}")
    private boolean flashPriceEnabled;

    @Value("${thesis.product-spec-enabled:false}")
    private boolean productSpecEnabled;

    private final boolean shopMarketplace = AppPolicy.SHOP_MARKETPLACE;

    /** 店铺客服选人 */
    private final boolean dmShopCs = AppPolicy.DM_SHOP_CS;

    private final int pointsEarnPerYuan = AppPolicy.POINTS_EARN_PER_YUAN;

    private final boolean pointsPayEnabled = AppPolicy.POINTS_PAY_ENABLED;

    @Value("${thesis.points-offset-enabled:false}")
    private boolean pointsOffsetEnabled;

    @Value("${thesis.points-checkin-enabled:false}")
    private boolean pointsCheckInEnabled;

    @Value("${thesis.points-checkin-amount:10}")
    private int pointsCheckInAmount;

    @Value("${thesis.points-expire-enabled:false}")
    private boolean pointsExpireEnabled;

    @Value("${thesis.points-expire-period:year}")
    private String pointsExpirePeriod;

    @Value("${thesis.points-expire-scope:all}")
    private String pointsExpireScope;

    @Value("${thesis.member-tier-basis:spend}")
    private String memberTierBasis;

    @Value("${thesis.spend-discount-threshold-yuan:100}")
    private double spendDiscountThresholdYuan;

    @Value("${thesis.spend-discount-off-yuan:10}")
    private double spendDiscountOffYuan;

    @Override
    public void run(ApplicationArguments args) {
        ArchiveStore.bind(archiveCategoryTable, archiveItemTable);
        ArchiveStore.configureSoftDelete(archiveSoftDelete);
        ArchiveStore.configureUserPublish(archiveUserPublish);
        ArchiveStore.configurePublishReview(archivePublishReview);
        ArchiveStore.configureGallery(galleryEnabled);
        ArchiveStore.configureStockWarn(stockWarnNotify, stockWarnBelow);
        ArchiveStore.configureDetailAttrs(detailAttrsEnabled, detailAttrKeys);
        ArchiveStore.configureRoomEquipment(roomEquipmentEnabled);
        ArchiveStore.configureFlashPrice(flashPriceEnabled);
        ArchiveStore.configureProductSpec(productSpecEnabled);
        ArchiveStore.configureShopMarketplace(shopMarketplace);
        DmStore.configureShopCustomerService(dmShopCs);
        if (archiveTagTable != null && !archiveTagTable.isBlank()) {
            ArchiveStore.bindTags(archiveTagTable, archiveItemTagTable);
        }
        ArchiveStore.configureMultiCategory(multiCategoryEnabled);
        if (archiveItemCategoryTable != null && !archiveItemCategoryTable.isBlank()) {
            ArchiveStore.bindItemCategories(archiveItemCategoryTable);
        }
        if (ticketAllowCheckin) {
            // checkin_code 已随档案表 schema 建好；此处不再 ALTER
        }
        if (enableTicket && ticketTable != null && !ticketTable.isBlank()) {
            if ("standalone".equalsIgnoreCase(ticketMode)) {
                TicketStore.bindStandalone(ticketTable, useDeadline);
            } else {
                TicketStore.bind(ticketTable, useQuota, useDeadline, allowMultiTicket, checkTimeConflict);
            }
            TicketStore.setUserRole(registerRole);
            TicketStore.configureThreeLevel(ticketThreeLevel);
            TicketStore.configureL1(ticketTwoLevel || ticketThreeLevel, ticketRequireAttach, ticketAllowRating);
            TicketStore.configureRules(ticketCheckMutex, ticketCategoryLimit);
            TicketStore.configureBizParams(ticketLoanDays, ticketMaxActive, ticketFinePerDay, ticketPickupPlace);
            TicketStore.configureCheckin(ticketAllowCheckin);
            TicketStore.configurePeerAccept(ticketPeerAccept);
            TicketStore.configureIssuePassCode(ticketIssuePassCode);
            TicketStore.configureRenew(ticketAllowRenew, ticketMaxRenew, ticketRenewDays);
            TicketStore.configureDueSoon(ticketDueSoonDays);
            TicketStore.configureMaxOverdueTimes(ticketMaxOverdueTimes);
            BorrowCreditStore.configure(
                    ticketCreditOnOverdue,
                    ticketCreditInitial,
                    ticketCreditOverdueDelta,
                    ticketCreditBlockBelow);
            TicketStore.configureWaitlist(ticketAllowWaitlist);
            TicketStore.configureBookHold(ticketAllowBookHold, ticketHoldHours);
            TicketStore.configureBookLost(ticketAllowBookLost);
            TicketStore.configureRequireReturnAttach(ticketRequireReturnAttach);
            TicketStore.configureNoShow(ticketNoShowAfterEnd, ticketNoShowPenaltyYuan);
            TicketStore.configureTimebankRedeem(timebankEnabled && timebankRedeemOnApprove);
            TicketStore.configureLoanOptions(ticketPickLoanPeriod, ticketAllowQty);
            TicketStore.configureApplyExtras(ticketRequireRemark, ticketPickDateRange);
            TicketStore.configureApproveEndsFlow(ticketApproveEndsFlow);
            TicketStore.configureAutoApprove(ticketAutoApprove);
            TicketStore.configureRequireClaimCode(ticketRequireClaimCode);
            TicketStore.configureMatchProfileRoom(
                    ticketMatchProfileRoom,
                    ticketMatchProfileBuildingKey,
                    ticketMatchProfileRoomKey,
                    ticketMatchProfileBuildingField,
                    ticketMatchProfileRoomField,
                    ticketMatchProfileLooseBuilding,
                    ticketMatchProfileNeedMessage,
                    ticketMatchProfileDenyMessage);
            TicketStore.configureApplicantCompleteOnly(ticketApplicantCompleteOnly);
            TicketStore.configureProxyPickup(ticketAllowProxyPickup);
            TicketStore.configureBedConstraint(
                    ticketBedConstraint,
                    ticketBedConstraintNeedMessage,
                    ticketBedConstraintDenyMessage);
            TicketStore.configureArrivalNotify(ticketArrivalNotify);
            TicketStore.configureNoticeAck(ticketRequireNoticeAck);
            
            TicketStore.configureApproveThicken(
                    ticketApproveThicken,
                    ticketAllowApproveCc,
                    ticketMinApproveRemarkWords,
                    ticketAllowApproveTransfer,
                    ticketAllowApproveDelegate,
                    ticketAllowApproveRemarkAttach,
                    ticketAllowApproveCcComment,
                    ticketAllowApproveAutoPass,
                    ticketApproveAutoPassHours);
            TicketStore.configureApproveSkin(
                    ticketAllowCertPickup,
                    ticketAllowCertUrgent,
                    ticketAllowSealCopies,
                    ticketAllowFleetMileage,
                    ticketAllowExpenseInvoice,
                    ticketAllowVisitorCount);
            TicketStore.configureApplyThicken(
                    ticketApplyThicken,
                    ticketNotifyOnApplySuccess,
                    ticketAllowMeetingPlace,
                    ticketAllowEmergencyContact,
                    ticketCancelBeforeHours,
                    ticketClaimCooldownHours,
                    ticketMaxDropTimes,
                    ticketSemesterCreditCap,
                    ticketCreditWarnRemaining);
            TicketStore.configureDeposit(ticketAllowDeposit);
            TicketStore.configureExceptionClose(ticketAllowExceptionClose);
            TicketStore.configureTrainingAck(ticketRequireTrainingAck);
            TicketStore.configureInsuranceAck(ticketRequireInsuranceAck);
            TicketStore.configureMeetingAck(ticketRequireMeetingAck);
            TicketStore.configureApplyInvite(ticketRequireApplyInvite);
            TicketStore.configurePriceNoteAck(ticketRequirePriceNoteAck);
            TicketStore.configureSponsorAck(ticketRequireSponsorAck);
            TicketStore.configurePlanAck(ticketRequirePlanAck);
            TicketStore.configurePrereqAck(ticketRequirePrereqAck);
            TicketStore.configureAgeConstraint(
                    ticketAgeConstraint,
                    ticketAgeConstraintNeedMessage,
                    ticketAgeConstraintDenyMessage);
            TicketStore.configureLateMinutes(ticketAllowLateMinutes);
            TicketStore.configureWishOrder(ticketAllowWishOrder);
            TicketStore.configureVolunteerRole(ticketAllowVolunteerRole);
            TicketStore.configureAdminCheckin(ticketAllowAdminCheckin);
            TicketStore.configureTourNoticeAck(ticketRequireTourNoticeAck);
            TicketStore.configureCompanions(ticketAllowCompanions);
            TicketStore.configureLottery(ticketAllowLottery);
            TicketStore.configureSeatZone(ticketAllowSeatZone);
            TicketStore.configureTicketTransfer(ticketAllowTicketTransfer);
            TicketStore.configureTicketWallet(ticketAllowTicketWallet);
            TicketStore.configureApplyBlacklist(ticketAllowApplyBlacklist);
            TicketStore.configureScheduleChangeNotify(ticketScheduleChangeNotify);
            TicketStore.configurePostGallery(ticketAllowPostGallery);
            TicketStore.configureCreditWritebackAck(ticketRequireCreditWritebackAck);
            TicketStore.configureApproveBatch4(
                    ticketAllowAwardCertNo,
                    ticketAllowVendorQuotes,
                    ticketForceOnePerArchive,
                    ticketMinVendorQuotes,
                    ticketNotifyArchiveExpireDays,
                    ticketOnePerArchiveDenyMessage);

            TicketStore.configureApproveBatch5(
                    ticketAllowEvalOpenWindow,
                    ticketAllowCompHours,
                    ticketAllowFleetCrew,
                    ticketAllowEthicBatch,
                    ticketEvalOpenWindowDenyMessage);

            TicketStore.configureApproveBatch6(
                    ticketAllowPassExpire,
                    ticketAllowReturnFuel,
                    ticketAllowLaborPlace,
                    ticketAllowPromoPlace,
                    ticketAllowEthicMeeting,
                    ticketAllowEffectiveOn,
                    ticketPassExpireDays);
            TicketStore.configureApproveBatch7(
                    ticketAllowCertIssueNo,
                    ticketAllowPromoFeedback,
                    ticketAllowDocRev,
                    ticketAllowFitoutQuiet);
            TicketStore.configureApproveBatch8(
                    ticketAllowSealClosePhoto,
                    ticketAllowIssueCopies,
                    ticketAllowSignParties,
                    ticketAllowTrainHours,
                    ticketAllowInspectExpire,
                    ticketAllowMemberChange);
            TicketStore.configureApproveBatch9(
                    ticketAllowProcureBudget,
                    ticketAllowCheckinException,
                    ticketAllowVisitPurpose,
                    ticketAllowFleetViolation,
                    ticketAllowFitoutRectify,
                    ticketAllowProjNodeRemind);
            TicketStore.configureApproveBatch10(
                    ticketAllowClubCopyLast,
                    ticketAllowProcureReturn,
                    ticketAllowMoralObjection,
                    ticketAllowProjFundUse,
                    ticketAllowEvalDimWeight,
                    ticketAllowVisitSlotRemain);
            TicketStore.configureApproveBatch11(
                    ticketAllowPlagiarismUrl,
                    ticketAllowAbsentStreak,
                    ticketAllowPartyStage,
                    ticketAllowEvalObserve,
                    ticketAllowScheduleImpact,
                    ticketAllowContractAmount);
            TicketStore.configureApproveBatch12(
                    ticketAllowExpenseLines,
                    ticketAllowTripLegs,
                    ticketAllowHideEvalResult,
                    ticketAllowSignRemarkVisible,
                    ticketAllowProjChangeLog,
                    ticketAllowCertVerify);
            TicketStore.configureApproveBatch13(
                    ticketAllowVisitWalkIn,
                    ticketAllowCheckinProxy,
                    ticketAllowClubRoster,
                    ticketAllowCarpassParkingMutex,
                    ticketAllowEvalUrge,
                    ticketAllowContractRenew);
            TicketStore.configureApproveBatch14(
                    ticketAllowContractExpireRemind,
                    ticketAllowCertPickupRedeem,
                    ticketAllowExamPassMin,
                    ticketAllowCheckinSpot,
                    ticketAllowEvalBeforeGrade,
                    ticketAllowApproveDurationStats);
            TicketStore.configureApproveBatch15(
                    ticketAllowAttachKeepOld,
                    ticketAllowCertPickupQr,
                    ticketAllowCertVerifyPage,
                    ticketAllowVisitorPassPrint,
                    ticketAllowCheckinDailyReport,
                    ticketAllowEvalCollegeExport);
            TicketStore.configureApproveBatch16(
                    ticketAllowSealLedgerExport,
                    ticketAllowMoralMaterialCheck,
                    ticketAllowPartyMaterialTemplate,
                    ticketAllowPartyThoughtAttach);
            TicketStore.configureApproveBatch17(
                    ticketAllowCertFormPrint,
                    ticketAllowSealFormPrint,
                    ticketAllowProjMidFormPrint,
                    ticketAllowEthicOpinionPrint,
                    ticketAllowExpenseAttachCount,
                    ticketAllowFleetDriverCert);
            String blDeny = (ticketApplyBlacklistDenyMessage == null || ticketApplyBlacklistDenyMessage.isBlank())
                    ? "当前账号暂不可报名，请联系管理员。"
                    : ticketApplyBlacklistDenyMessage;
            com.thesis.service.ApplyBlacklistStore.configure(ticketAllowApplyBlacklist, blDeny);
            TicketStore.configureCalibBlock(ticketBlockIfCalibExpired);
            TicketStore.configureProjectNo(ticketAllowProjectNo);
            TicketStore.configureProcureRef(ticketAllowProcureRef);
            TicketStore.configureProcureToStockIn(ticketProcureToStockIn);
            TicketStore.configureDualReview(ticketAllowDualReview);
            TicketStore.configureShipFee(ticketAllowShipFee);
            TicketStore.configureUtilityNote(ticketAllowUtilityNote);
            TicketStore.configureMaxCancelHolds(ticketMaxCancelHolds);
            TicketStore.configureOverdueAutoCompensate(ticketOverdueAutoCompensate);
            TicketStore.configureFineWaive(ticketAllowFineWaive);
            TicketStore.configureRenewBlockIfHeld(ticketRenewBlockIfHeld);
            TicketStore.configurePeerConfirm(ticketRequirePeerConfirm);
            TicketStore.configureAbandonDual(ticketRequireAbandonDual);
            TicketStore.configureFollowThicken(
                    ticketFollowRemindDays,
                    ticketMinRemarkWords,
                    ticketMaxReviseTimes,
                    ticketRequireCloseAttach,
                    ticketRequireReturnDate,
                    ticketRequireFeedbackSet,
                    ticketRequireAppraisal,
                    ticketAllowDealAmount,
                    ticketAllowNextAction,
                    ticketAllowInterviewResult,
                    ticketAllowWrittenScore,
                    ticketAllowBgCheckNote,
                    ticketAllowDefenseResult,
                    ticketMaskBankAccount,
                    ticketAllowDisburseBatch,
                    ticketAllowLeaveProxy,
                    ticketAllowCompanyEval,
                    ticketAllowExcellentMark,
                    ticketAllowRecordUrl,
                    ticketAllowConfidential,
                    ticketAllowAssignDept,
                    ticketAllowBatchHire,
                    ticketWeekReportRemind,
                    ticketHomeVisitTemplate,
                    ticketAttachByLeaveType,
                    ticketAllowMakeupApply,
                    ticketWeekReportDeadlineDay);
            TicketStore.configureFollowOps(ticketStaleFollowDays, ticketPhoneDupCheck);
            TicketStore.configureEventOps(
                    ticketLevelAffectsDeadline,
                    Math.max(1, ticketLevelSlaHighDays),
                    Math.max(1, ticketLevelSlaMidDays),
                    Math.max(1, ticketLevelSlaLowDays),
                    ticketNotifyDutyOnReport);
            FundPublicityStore.configureObjection(ticketAllowObjectionWindow, ticketObjectionDays);
            GradeScoreStore.configureObjectionDays(ticketObjectionDays);
            TicketStore.configureRepairThicken(
                    ticketRepairThicken,
                    ticketAllowUserUrge,
                    ticketUrgeCooldownMinutes,
                    ticketLockUrgeAfterRate,
                    ticketAllowCancelUrge,
                    ticketRequireFaultReason,
                    ticketRequireCloseSummary,
                    ticketRequireLowRatingRemark,
                    ticketSlaSplit,
                    ticketEscalateOnOverdue,
                    ticketNotifySupervisorOnOverdue,
                    ticketAllowHoldResume,
                    ticketAllowCancelDispatched,
                    ticketAllowTicketDraft,
                    ticketAllowFollowRate,
                    ticketPreferredSlot,
                    ticketProgressSubscribe,
                    ticketNightUrgent,
                    ticketAllowPartsNote,
                    ticketAllowQuote,
                    ticketAllowPublicArea,
                    ticketDupRoomCheck,
                    ticketAllowAssetCode,
                    ticketAllowRemoteUrl,
                    ticketAllowSerialNo,
                    ticketAllowHelper,
                    ticketAllowRatingTags,
                    ticketTodayBoard,
                    ticketPrintTicket);

        }
        LoyaltyStore.configure(
                walletEnabled,
                pointsEnabled,
                spendDiscountEnabled,
                memberTierEnabled,
                couponEnabled,
                pointsEarnPerYuan,
                spendDiscountThresholdYuan,
                spendDiscountOffYuan);
        LoyaltyStore.configurePointsModes(
                pointsPayEnabled,
                pointsOffsetEnabled,
                pointsCheckInEnabled,
                pointsCheckInAmount,
                pointsExpireEnabled,
                pointsExpirePeriod,
                pointsExpireScope,
                memberTierBasis);
        CouponStore.configure(couponEnabled);
        if (orderCartTable != null && !orderCartTable.isBlank()) {
            OrderStore.bind(orderCartTable, orderTable, orderLineTable, useQuota);
        } else {
            OrderStore.unbind();
        }
        OrderReviewStore.configure(orderReviewEnabled);
        OrderStore.configureLineCustom(lineCustomEnabled, lineCustomPlaceConfirmed, noCasualRefund);
        OrderStore.configureAfterSaleDays(afterSaleDays);
        OrderStore.configureFoodFees(packagingFeeYuan, deliveryFeeBaseYuan, deliveryFeeFreeYuan, etaMinutes);
        LineCustomStore.configure(lineCustomEnabled);
        DeliveryWindowStore.configure(deliveryWindowEnabled);
        PurchaseGateStore.configure(purchaseGateEnabled);
        GroupBuyStore.configure(groupBuyEnabled);
        BlindBoxStore.configure(blindBoxEnabled);
        ConsignStore.configure(consignEnabled);
        WeighSaleStore.configure(weighSaleEnabled);
        ShootStore.configure(shootEnabled);
        BoardingStore.configure(boardingEnabled);
        RoomBoardStore.configure(roomBoardEnabled);
        FrontDeskStore.configure(frontDeskEnabled);
        VenueCleanStore.configure(venueCleanEnabled);
        BuybackStore.configure(buybackEnabled);
        LessonStore.configure(lessonPackEnabled);
        RentalBondStore.configure(rentalBondEnabled);
        DigitalGoodsStore.configure(digitalGoodsEnabled);
        FavoriteStore.configure(favoritesEnabled);
        FavoriteStore.configureLike(postLikeEnabled);
        FavoriteStore.configureReport(contentReportEnabled);
        UserStore.configurePostMute(postMuteEnabled);
        BrowseHistoryStore.configure(browseHistoryEnabled, 20);
        ArchiveLogStore.configure(archiveLogEnabled);
        AuditLogStore.configure(auditLogEnabled, auditLogLoginOnly);
        MessageStore.configureTemplate(messageTemplateEnabled);
        StaffRosterStore.configure(staffRosterEnabled);
        BookSuggestStore.configure(bookSuggestEnabled);
        ParcelShelfStore.configure(parcelShelfEnabled);
        ParcelShipStore.configure(parcelShipEnabled);
        EquipmentDictStore.configure(roomEquipmentEnabled);
        ExamStore.configure(
                examEnabled,
                examPracticeEnabled,
                examExplainEnabled,
                examTimerEnabled,
                examAttemptLimitEnabled,
                examRankEnabled,
                examWrongbookEnabled,
                examRequireBeforeTicket);
        SurveyStore.configure(surveyEnabled);
        VoteStore.configure(voteEnabled);
        DoclibStore.configure(doclibEnabled);
        TimebankStore.configure(timebankEnabled, timebankRedeemOnApprove);
        SeatStore.configure(seatSelectEnabled);
        SeatStore.configureHoldTimeoutMinutes(seatHoldTimeoutMinutes);
        SeatStore.configureTicketRefundCutoffMinutes(ticketRefundCutoffMinutes);
        StockIoStore.configure(
                stockIoEnabled,
                stockScrapEnabled,
                stockCountEnabled,
                stockCountLock,
                stockBlindCount,
                stockRequireDiffReason,
                stockScrapApproveFlow);
        ESignStore.configure(eSignEnabled);
        BalanceLedgerStore.configure(balanceLedgerEnabled, balanceLedgerDebitOnApprove);
        GradeScoreStore.configure(gradeScoresEnabled);
        OccupySpanStore.configure(occupySpanEnabled);
        MaterialCheckStore.configure(materialCheckEnabled);
        ClaimProofStore.configure(claimProofEnabled);
        LostMessageStore.configure(lostClueEnabled);
        if (slotTable != null && !slotTable.isBlank()) {
            SlotStore.bind(slotTable, reservationTable);
            SlotStore.configureRemark(slotRequireRemark);
            SlotStore.configureConfirm(slotRequireConfirm);
            SlotStore.configureRating(slotAllowRating);
            SlotStore.configureThicken(
                    cancelFreeHours,
                    rescheduleMaxTimes,
                    remindAheadMinutes,
                    noShowLimit,
                    lateGraceMinutes,
                    reserveBlacklistEnabled);
            com.thesis.service.ReserveBlacklistStore.configure(reserveBlacklistEnabled, null);
            SlotStore.configureHospital(
                    hospitalCancelCutoffMinutes, hospitalIdLimitPerDay, hospitalWaitlistEnabled);
            SlotStore.configureParking(parkingHourlyYuan, parkingOvertimeYuan, parkingPassEnabled);
            SlotStore.configureMeeting(meetingMinDurationMinutes, meetingMinutesRequired);
            SlotStore.configureSalon(salonRescheduleFeeYuan);
            SlotStore.configureHotel(hotelLateCheckoutFeeYuan, hotelNoticeRequired);
            SlotStore.configureCarrent(carrentMileageOverFeeYuan);
            SlotStore.configureInstrument(instrumentOvertimeYuan, instrumentTrainingRequired);
            com.thesis.service.PatientProfileStore.configure(patientProfileEnabled);
            com.thesis.service.ParkingPassStore.configure(parkingPassEnabled);
        } else {
            SlotStore.unbind();
            com.thesis.service.ReserveBlacklistStore.configure(false, null);
            com.thesis.service.PatientProfileStore.configure(false);
            com.thesis.service.ParkingPassStore.configure(false);
        }
        PasswordHashes.bind(passwordHash);
        TicketLookupStore.bind(
                lookupSiteTable,
                lookupUnitTable,
                lookupTypeTable,
                lookupSiteLabel,
                lookupUnitLabel,
                lookupTypeLabel,
                lookupUnitCapacityLabel);
        UserStore.ensureStaffColumns();
    }
}
