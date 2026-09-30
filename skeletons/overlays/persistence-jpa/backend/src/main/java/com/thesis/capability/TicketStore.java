package com.thesis.capability;

import com.thesis.config.DomainResourceJson;
import com.thesis.service.BalanceLedgerStore;
import com.thesis.service.ClaimProofStore;
import com.thesis.service.ExamStore;
import com.thesis.service.MessageStore;
import com.thesis.service.OccupySpanStore;
import com.thesis.service.TimebankStore;
import com.thesis.service.UserStore;
import com.thesis.config.GeneratedKeyHolder;
import com.thesis.config.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.*;

/**
 * 能力 ticket_flow（±quota ±deadline）：单据申请/审核/完结。
 * <ul>
 *   <li>archive 模式：关联档案表占用库存（默认 borrow + book）</li>
 *   <li>standalone 模式：自由填写标题/地点（报修等，无库存）</li>
 * </ul>
 */
public final class TicketStore {

    public static final int LOAN_DAYS = 14;
    public static final double FINE_PER_DAY = 0.5;
    public static final int MAX_ACTIVE = 5;

    /** 借期等业务参数：见 config/TicketPolicy（bake 按开题生成，可直接修改） */
    private static int bizLoanDays = LOAN_DAYS;
    private static int bizMaxActive = MAX_ACTIVE;
    private static double bizFinePerDay = FINE_PER_DAY;
    private static String bizPickupPlace = "";

    public enum Mode {
        ARCHIVE,
        STANDALONE
    }

    static String TICKET = "borrow";
    static String PROGRESS = "";
    /** 档案行外键物理列（如 book_id / customer_id / activity_id） */
    static String ITEM_FK = "book_id";
    static Mode MODE = Mode.ARCHIVE;
    static boolean enabled = false;
    static boolean useQuota = true;
    static boolean useDeadline = true;
    /** 允许同一档案多次开单（论坛跟帖等） */
    static boolean allowMultiTicket = false;
    /** 申请时检测与本人已占用时段是否相交 */
    static boolean checkTimeConflict = false;
    /** L1：初审 → 终审（二级） */
    static boolean twoLevelApprove = false;
    /** C-16：初审 → 复审 → 终审（三级；隐含 twoLevel） */
    static boolean threeLevelApprove = false;
    /** L1：申请须上传附件 */
    static boolean requireAttach = false;
    /** 失物认领：须提交凭证并核验后才可审批 */
    static boolean requireClaimProof = false;
    /** L1：完结后可评分 */
    static boolean allowRating = false;
    /** 报修等：完结须由申请人确认，管理端不可代点完成 */
    static boolean applicantCompleteOnly = false;
    /** L1：同 mutex_code 的档案不可同时选 */
    static boolean checkMutex = false;
    /** L1：同一分类下进行中单据上限；≤0 表示不限 */
    static int categoryLimit = 0;
    /** L1：签到口令 */
    static boolean allowCheckin = false;
    /** C-05：档案主人可确认/拒绝志愿（互选） */
    static boolean peerAccept = false;
    /** C-09：审核通过签发通行码（非真门禁） */
    static boolean issuePassCode = false;
    /** C-14：核销审批通过时扣减时长账户 */
    static boolean timebankRedeem = false;
    /** 活动结束未签到 → 爽约（复用 overdue 状态） */
    static boolean noShowAfterEnd = false;
    /** 爽约固定费用；0 只改状态 */
    static double noShowPenaltyYuan = 0;
    /** 申请时可自选到期日（写入 due_at；审批时沿用） */
    static boolean pickLoanPeriod = false;
    /** 允许续借（延长 due_at） */
    static boolean allowRenew = false;
    /** 单次借出最多续借次数 */
    static int maxRenew = 1;
    /** 每次续借延长天数；≤0 则跟 loanDays */
    static int renewDays = 0;
    /** 应还日前 N 天站内提前催还；≤0 关闭 */
    static int dueSoonDays = 0;
    /** 历史超期达 N 次限制再借；≤0 关闭 */
    static int maxOverdueTimes = 0;
    /** 名额满可候补（waitlisted） */
    static boolean allowWaitlist = false;
    /** 无库存可预约到书（held → hold_ready） */
    static boolean allowBookHold = false;
    /** 丢失申报 → 赔偿完成（LIBRARY） */
    static boolean allowBookLost = false;
    /** 归还完结须上传附件（EQUIP 验图） */
    static boolean requireReturnAttach = false;
    /** 到书后限时确认借阅小时数 */
    static int holdHours = 48;
    /** 申请时可填数量（扣/还库存按 qty） */
    static boolean allowQty = false;
    /** 申请须填写说明（用途/跟进/认领事由等） */
    static boolean requireRemark = false;
    /** 申请须选起止日期（请假等 → period_start/period_end） */
    static boolean pickDateRange = false;
    /**
     * 审核通过/驳回即为收口（报名、选课、认领、收藏等）。
     * 工作台「已完成」统计 approved+rejected(+returned)；「处理中」不再含 approved。
     */
    static boolean approveEndsFlow = false;
    /** 提交即生效（跟进/考勤登记等），不进待审队列、不通知管理员 */
    static boolean autoApprove = false;
    static String userRole = "reader";

    private TicketStore() {}

    public static void bind(String ticketTable) {
        bind(ticketTable, true, true);
    }

    /** archive 模式；媒资收藏等可关 quota/deadline */
    public static void bind(String ticketTable, boolean quota, boolean deadline) {
        bind(ticketTable, quota, deadline, false, false);
    }

    public static void bind(String ticketTable, boolean quota, boolean deadline, boolean multiTicket) {
        bind(ticketTable, quota, deadline, multiTicket, false);
    }

    public static void bind(
            String ticketTable, boolean quota, boolean deadline, boolean multiTicket, boolean timeConflict) {
        if (ticketTable != null && !ticketTable.isBlank()) TICKET = ticketTable.trim();
        MODE = Mode.ARCHIVE;
        useQuota = quota;
        useDeadline = deadline;
        allowMultiTicket = multiTicket;
        checkTimeConflict = timeConflict;
        enabled = true;
        bindProgressDefault();
        TicketCopy.loadCopyFromResource();
        ensureProgressTable();
        ensureL1Columns();
        loadTicketColumnsFromResource();
    }

    /** 报修等：无档案占用；超时未处理 SLA 可打开 deadline */
    public static void bindStandalone(String ticketTable) {
        bindStandalone(ticketTable, false);
    }

    public static void bindStandalone(String ticketTable, boolean deadline) {
        if (ticketTable != null && !ticketTable.isBlank()) TICKET = ticketTable.trim();
        MODE = Mode.STANDALONE;
        useQuota = false;
        useDeadline = deadline;
        enabled = true;
        bindProgressDefault();
        TicketCopy.loadCopyFromResource();
        ensureProgressTable();
        ensureL1Columns();
        loadTicketColumnsFromResource();
    }

    /** 约定：进度表 = {单据表}_progress；可显式覆盖。 */
    public static void configureProgress(String progressTable) {
        if (progressTable != null && !progressTable.isBlank()) {
            PROGRESS = progressTable.trim();
        } else {
            bindProgressDefault();
        }
        ensureProgressTable();
    }

    static void bindProgressDefault() {
        PROGRESS = TICKET == null || TICKET.isBlank() ? "" : TICKET + "_progress";
    }

    /** 幂等建表：缺进度表时也能写出流转记录。 */
    static void ensureProgressTable() {
        if (PROGRESS == null || PROGRESS.isBlank()) return;
        try {
            TicketSql.db().execute(
                    "CREATE TABLE IF NOT EXISTS `" + PROGRESS + "` ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "ticket_id BIGINT NOT NULL,"
                            + "status VARCHAR(32) NOT NULL,"
                            + "operator VARCHAR(64),"
                            + "remark VARCHAR(255) DEFAULT '',"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "KEY idx_progress_ticket (ticket_id, id))");
        } catch (Exception e) {
            throw new IllegalStateException("无法创建审核进度表", e);
        }
    }

    public static void configureL1(boolean twoLevel, boolean attachRequired, boolean ratingEnabled) {
        twoLevelApprove = twoLevel || threeLevelApprove;
        requireAttach = attachRequired;
        allowRating = ratingEnabled;
    }

    public static void configureRequireClaimProof(boolean enabled) {
        requireClaimProof = enabled;
    }

    public static boolean isRequireClaimProof() {
        return requireClaimProof;
    }

    /** 用户已交凭证 → 待核验 */
    public static void markVerifying(long ticketId, String operator) {
        if (ticketId <= 0) return;
        TicketSql.db().update(
                "UPDATE " + TICKET + " SET status='verifying' WHERE id=? AND status IN ('pending','verifying')",
                ticketId);
        appendProgress(ticketId, "verifying", operator == null ? "" : operator, "已提交认领凭证，等待核验");
    }

    /** 凭证驳回后回到待交凭证 */
    public static void markPendingForProof(long ticketId, String operator) {
        if (ticketId <= 0) return;
        TicketSql.db().update(
                "UPDATE " + TICKET + " SET status='pending' WHERE id=? AND status='verifying'",
                ticketId);
        appendProgress(ticketId, "pending", operator == null ? "" : operator, "凭证未通过，请重新提交");
    }

    public static void configureApplicantCompleteOnly(boolean enabled) {
        applicantCompleteOnly = enabled;
    }

    public static boolean isApplicantCompleteOnly() {
        return applicantCompleteOnly;
    }

    /** C-16：三级会签；开启后二级路径扩展为 pending→pending_mid→pending_final */
    public static void configureThreeLevel(boolean enabled) {
        threeLevelApprove = enabled;
        if (enabled) {
            twoLevelApprove = true;
        }
    }

    public static boolean isThreeLevelApprove() {
        return threeLevelApprove;
    }

    /** 自选借期 + 申请数量（设备/图书常见；时间银行核销小时数可无库存） */
    public static void configureLoanOptions(boolean pickPeriod, boolean qtyEnabled) {
        pickLoanPeriod = pickPeriod && useDeadline;
        allowQty = qtyEnabled && MODE == Mode.ARCHIVE && (useQuota || timebankRedeem);
        // qty 列随本系统 schema 建表，禁止运行时 ALTER
    }

    /** C-14：审核通过扣减时长；须在 configureLoanOptions 前或后再调一次 refresh */
    public static void configureTimebankRedeem(boolean enabled) {
        timebankRedeem = enabled;
        if (enabled && MODE == Mode.ARCHIVE) {
            allowQty = true;
        }
    }

    /** 必填说明 + 起止日期（申领用途 / 跟进 / 请假等） */
    public static void configureApplyExtras(boolean remarkRequired, boolean dateRange) {
        requireRemark = remarkRequired;
        pickDateRange = dateRange && MODE == Mode.ARCHIVE;
        // period_* 列随本系统 schema 建表
    }

    /** 审核即收口：通过/驳回都算办结，不再把 approved 算作处理中 */
    public static void configureApproveEndsFlow(boolean enabled) {
        approveEndsFlow = enabled;
    }

    /** 提交即生效：申请直接落 approved，跳过管理端待审 */
    public static void configureAutoApprove(boolean enabled) {
        autoApprove = enabled;
    }

    public static boolean isAutoApprove() {
        return autoApprove;
    }

    /** 驿站等：申请说明/取件码须与档案取件码一致 */
    static boolean requireClaimCode = false;

    public static void configureRequireClaimCode(boolean enabled) {
        requireClaimCode = enabled;
    }

    public static boolean isRequireClaimCode() {
        return requireClaimCode;
    }

    /** 查寝/绑岗等：资料键须匹配档案列（默认 dormBuilding↔author、dormRoom↔title） */
    static boolean matchProfileRoom = false;
    static String matchProfileBuildingKey = "dormBuilding";
    static String matchProfileRoomKey = "dormRoom";
    static String matchProfileBuildingField = "author";
    static String matchProfileRoomField = "title";
    static boolean matchProfileLooseBuilding = false;
    static String matchProfileNeedMessage = "请先在个人资料填写楼栋与房间";
    static String matchProfileDenyMessage = "只能对本寝室的查寝场次登记归寝";

    public static void configureMatchProfileRoom(boolean enabled) {
        configureMatchProfileRoom(enabled, null, null, null, null, false, null, null);
    }

    public static void configureMatchProfileRoom(
            boolean enabled,
            String buildingKey,
            String roomKey,
            String buildingField,
            String roomField,
            boolean looseBuilding,
            String needMessage,
            String denyMessage) {
        matchProfileRoom = enabled;
        matchProfileBuildingKey = (buildingKey == null || buildingKey.isBlank()) ? "dormBuilding" : buildingKey.trim();
        matchProfileRoomKey = (roomKey == null || roomKey.isBlank()) ? "dormRoom" : roomKey.trim();
        matchProfileBuildingField = (buildingField == null || buildingField.isBlank()) ? "author" : buildingField.trim();
        matchProfileRoomField = (roomField == null || roomField.isBlank()) ? "title" : roomField.trim();
        matchProfileLooseBuilding = looseBuilding;
        if (needMessage != null && !needMessage.isBlank()) {
            matchProfileNeedMessage = needMessage.trim();
        } else {
            matchProfileNeedMessage = "请先在个人资料填写楼栋与房间";
        }
        if (denyMessage != null && !denyMessage.isBlank()) {
            matchProfileDenyMessage = denyMessage.trim();
        } else {
            matchProfileDenyMessage = "只能对本寝室的查寝场次登记归寝";
        }
    }

    public static boolean isMatchProfileRoom() {
        return matchProfileRoom;
    }

    /** 驿站代取 */
    static boolean allowProxyPickup = false;
    /** 床位性别/年级约束 */
    static boolean bedConstraint = false;
    static String bedConstraintNeedMessage = "请先在个人资料填写性别与年级。";
    static String bedConstraintDenyMessage = "该床位限对应性别或年级，请改选其他床位或完善个人资料。";
    /** 到件/通过后站内信通知申请人 */
    static boolean arrivalNotify = false;
    /** 申请须勾选须知 */
    static boolean requireNoticeAck = false;
    /** 设备押金可选登记 */
    static boolean allowDeposit = false;
    /** 异常件/破损理赔字段 */
    static boolean allowExceptionClose = false;
    /** 申请须勾选培训合格 */
    static boolean requireTrainingAck = false;
    /** 申请须勾选保险声明 */
    static boolean requireInsuranceAck = false;
    /** 校准证书过期禁止借用 */
    static boolean blockIfCalibExpired = false;
    /** 课题号 / 双人复核 / 运费 / 水电备注 */
    static boolean allowProjectNo = false;
    /** 领用单关联申购单号 */
    static boolean allowProcureRef = false;
    /** 申购通过后可一键入库 */
    static boolean procureToStockIn = false;
    static boolean allowDualReview = false;
    static boolean allowShipFee = false;
    static boolean allowUtilityNote = false;
    /** 预约取消次数上限；≤0 不限 */
    static int maxCancelHolds = 0;
    /** 超期自动提示转赔付（站内文案，不强制改终态） */
    static boolean overdueAutoCompensate = false;
    /** 逾期罚款可减免登记 */
    static boolean allowFineWaive = false;
    /** 续借时若该册仍有他人预约则拒绝 */
    static boolean renewBlockIfHeld = false;
    /** 调宿等：须对方确认后才可审过 */
    static boolean requirePeerConfirm = false;
    /** 弃件须双人确认字段齐全 */
    static boolean requireAbandonDual = false;

    /** 跟进组加厚 */
    static int followRemindDays = 0;
    static int minRemarkWords = 0;
    static int maxReviseTimes = 0;
    /** 未跟进 N 天列表筛（0=关） */
    static int staleFollowDays = 0;
    /** 同联系电话拦重号（开题扫 CRM 查重提示） */
    static boolean phoneDupCheck = false;
    static boolean requireCloseAttach = false;
    static boolean requireReturnDate = false;
    static boolean requireFeedbackSet = false;
    static boolean requireAppraisal = false;
    static boolean allowDealAmount = false;
    static boolean allowNextAction = false;
    static boolean allowInterviewResult = false;
    static boolean allowWrittenScore = false;
    static boolean allowBgCheckNote = false;
    static boolean allowDefenseResult = false;
    static boolean maskBankAccount = false;
    static boolean allowDisburseBatch = false;
    static boolean allowLeaveProxy = false;
    static boolean allowCompanyEval = false;
    static boolean allowExcellentMark = false;
    static boolean allowRecordUrl = false;
    static boolean allowConfidential = false;
    static boolean allowAssignDept = false;
    static boolean allowBatchHire = false;
    static boolean weekReportRemind = false;
    static boolean homeVisitTemplate = false;
    static boolean attachByLeaveType = false;
    static boolean allowMakeupApply = false;
    static int weekReportDeadlineDay = 0;

    /** 报修组加厚 */
    static boolean repairThicken = false;
    static boolean allowUserUrge = false;
    static int urgeCooldownMinutes = 0;
    static boolean lockUrgeAfterRate = false;
    static boolean allowCancelUrge = false;
    static boolean requireFaultReason = false;
    static boolean requireCloseSummary = false;
    static boolean requireLowRatingRemark = false;
    static boolean slaSplit = false;
    static boolean escalateOnOverdue = false;
    static boolean notifySupervisorOnOverdue = false;
    static boolean allowHoldResume = false;
    static boolean allowCancelDispatched = false;
    static boolean allowTicketDraft = false;
    static boolean allowFollowRate = false;
    static boolean preferredSlot = false;
    static boolean progressSubscribe = false;
    static boolean nightUrgent = false;
    static boolean allowPartsNote = false;
    static boolean allowQuote = false;
    static boolean allowPublicArea = false;
    static boolean dupRoomCheck = false;
    static boolean allowAssetCode = false;
    static boolean allowRemoteUrl = false;
    static boolean allowSerialNo = false;
    static boolean allowHelper = false;
    static boolean allowRatingTags = false;
    static boolean todayBoard = false;
    static boolean printTicket = false;

    public static void configureProxyPickup(boolean enabled) {
        allowProxyPickup = enabled;
    }

    public static void configureBedConstraint(boolean enabled, String needMessage, String denyMessage) {
        bedConstraint = enabled;
        if (needMessage != null && !needMessage.isBlank()) {
            bedConstraintNeedMessage = needMessage.trim();
        }
        if (denyMessage != null && !denyMessage.isBlank()) {
            bedConstraintDenyMessage = denyMessage.trim();
        }
    }

    public static void configureArrivalNotify(boolean enabled) {
        arrivalNotify = enabled;
    }

    public static void configureNoticeAck(boolean enabled) {
        requireNoticeAck = enabled;
    }

    public static void configureDeposit(boolean enabled) {
        allowDeposit = enabled;
    }

    public static void configureExceptionClose(boolean enabled) {
        allowExceptionClose = enabled;
    }

    public static void configureTrainingAck(boolean enabled) {
        requireTrainingAck = enabled;
    }

    public static void configureInsuranceAck(boolean enabled) {
        requireInsuranceAck = enabled;
    }

    public static void configureCalibBlock(boolean enabled) {
        blockIfCalibExpired = enabled;
    }

    public static void configureProjectNo(boolean enabled) {
        allowProjectNo = enabled;
    }

    public static void configureProcureRef(boolean enabled) {
        allowProcureRef = enabled;
    }

    public static void configureProcureToStockIn(boolean enabled) {
        procureToStockIn = enabled;
    }

    public static boolean procureToStockInEnabled() {
        return procureToStockIn;
    }

    public static void configureDualReview(boolean enabled) {
        allowDualReview = enabled;
    }

    public static void configureShipFee(boolean enabled) {
        allowShipFee = enabled;
    }

    public static void configureUtilityNote(boolean enabled) {
        allowUtilityNote = enabled;
    }

    public static void configureMaxCancelHolds(int max) {
        maxCancelHolds = Math.max(0, Math.min(20, max));
    }

    public static void configureOverdueAutoCompensate(boolean enabled) {
        overdueAutoCompensate = enabled;
    }

    public static void configureFineWaive(boolean enabled) {
        allowFineWaive = enabled;
    }

    public static void configureRenewBlockIfHeld(boolean enabled) {
        renewBlockIfHeld = enabled;
    }

    public static void configurePeerConfirm(boolean enabled) {
        requirePeerConfirm = enabled;
    }

    public static void configureAbandonDual(boolean enabled) {
        requireAbandonDual = enabled;
    }

    public static void configureFollowThicken(
            int followRemindDaysIn,
            int minRemarkWordsIn,
            int maxReviseTimesIn,
            boolean requireCloseAttachIn,
            boolean requireReturnDateIn,
            boolean requireFeedbackSetIn,
            boolean requireAppraisalIn,
            boolean allowDealAmountIn,
            boolean allowNextActionIn,
            boolean allowInterviewResultIn,
            boolean allowWrittenScoreIn,
            boolean allowBgCheckNoteIn,
            boolean allowDefenseResultIn,
            boolean maskBankAccountIn,
            boolean allowDisburseBatchIn,
            boolean allowLeaveProxyIn,
            boolean allowCompanyEvalIn,
            boolean allowExcellentMarkIn,
            boolean allowRecordUrlIn,
            boolean allowConfidentialIn,
            boolean allowAssignDeptIn,
            boolean allowBatchHireIn,
            boolean weekReportRemindIn,
            boolean homeVisitTemplateIn,
            boolean attachByLeaveTypeIn,
            boolean allowMakeupApplyIn,
            int weekReportDeadlineDayIn) {
        followRemindDays = Math.max(0, Math.min(14, followRemindDaysIn));
        minRemarkWords = Math.max(0, Math.min(5000, minRemarkWordsIn));
        maxReviseTimes = Math.max(0, Math.min(20, maxReviseTimesIn));
        requireCloseAttach = requireCloseAttachIn;
        requireReturnDate = requireReturnDateIn;
        requireFeedbackSet = requireFeedbackSetIn;
        requireAppraisal = requireAppraisalIn;
        allowDealAmount = allowDealAmountIn;
        allowNextAction = allowNextActionIn;
        allowInterviewResult = allowInterviewResultIn;
        allowWrittenScore = allowWrittenScoreIn;
        allowBgCheckNote = allowBgCheckNoteIn;
        allowDefenseResult = allowDefenseResultIn;
        maskBankAccount = maskBankAccountIn;
        allowDisburseBatch = allowDisburseBatchIn;
        allowLeaveProxy = allowLeaveProxyIn;
        allowCompanyEval = allowCompanyEvalIn;
        allowExcellentMark = allowExcellentMarkIn;
        allowRecordUrl = allowRecordUrlIn;
        allowConfidential = allowConfidentialIn;
        allowAssignDept = allowAssignDeptIn;
        allowBatchHire = allowBatchHireIn;
        weekReportRemind = weekReportRemindIn;
        homeVisitTemplate = homeVisitTemplateIn;
        attachByLeaveType = attachByLeaveTypeIn;
        allowMakeupApply = allowMakeupApplyIn;
        weekReportDeadlineDay = Math.max(0, Math.min(28, weekReportDeadlineDayIn));
    }

    /** 开题扫：事件等级 → 处理时限天数（高/中/低） */
    static boolean levelSla = false;
    static int levelSlaHighDays = 1;
    static int levelSlaMidDays = 3;
    static int levelSlaLowDays = 7;
    /** 开题扫：事件上报后一键通知当日值班（站内信浅群发） */
    static boolean dutyNotify = false;

    /** 跟进组列表闸：未跟进 N 天筛 + 同联系电话拦重号。 */
    public static void configureFollowOps(int staleFollowDaysIn, boolean phoneDupCheckIn) {
        staleFollowDays = Math.max(0, Math.min(90, staleFollowDaysIn));
        phoneDupCheck = phoneDupCheckIn;
    }

    /** 事件组闸：等级影响处理时限 + 上报群发值班。 */
    public static void configureEventOps(
            boolean levelSlaIn, int highDaysIn, int midDaysIn, int lowDaysIn, boolean dutyNotifyIn) {
        levelSla = levelSlaIn;
        levelSlaHighDays = Math.max(1, Math.min(60, highDaysIn));
        levelSlaMidDays = Math.max(1, Math.min(60, midDaysIn));
        levelSlaLowDays = Math.max(1, Math.min(60, lowDaysIn));
        dutyNotify = dutyNotifyIn;
    }

    /** 等级 → 处理时限天数；levelSla 关时原样返回 fallback。 */
    static int levelSlaDays(Map<String, Object> m, int fallback) {
        if (!levelSla) return fallback;
        String lv = levelTextOf(m);
        if (lv.isBlank()) return fallback;
        if (lv.contains("高") || lv.contains("严重") || lv.contains("重大")
                || lv.contains("紧急") || lv.contains("一级") || lv.contains("红")) {
            return levelSlaHighDays;
        }
        if (lv.contains("中") || lv.contains("较重") || lv.contains("二级")
                || lv.contains("橙") || lv.contains("黄")) {
            return levelSlaMidDays;
        }
        if (lv.contains("低") || lv.contains("轻微") || lv.contains("一般")
                || lv.contains("三级") || lv.contains("蓝")) {
            return levelSlaLowDays;
        }
        return fallback;
    }

    /** 等级文本：单据行 level 优先，其次关联档案（event_case.level）。 */
    static String levelTextOf(Map<String, Object> m) {
        if (m == null) return "";
        String own = TicketSql.str(m.get("level"));
        if (!own.isBlank()) return own;
        long itemId = TicketSql.toLong(m.get("bookId"));
        if (itemId <= 0) return "";
        try {
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            return item == null ? "" : TicketSql.str(item.get("level"));
        } catch (Exception ignored) {
            return "";
        }
    }

    /** 高,中,低 时限天数（未开时为空串），供前端展示。 */
    static String levelSlaCsv() {
        return levelSla ? (levelSlaHighDays + "," + levelSlaMidDays + "," + levelSlaLowDays) : "";
    }

    /** 事件上报群发当日值班；返回实际通知人数。 */
    static int notifyDutyOnNewReport(long ticketId, String applicant, String subject) {
        if (!dutyNotify || ticketId <= 0) return 0;
        try {
            Set<String> onDuty = StaffRosterStore.onDutyUsernames(LocalDate.now().toString());
            if (onDuty.isEmpty()) return 0;
            String sub = subject == null || subject.isBlank() ? ("单据#" + ticketId) : subject;
            String who = UserStore.displayName(applicant);
            int sent = 0;
            for (String un : onDuty) {
                if (un == null || un.isBlank() || un.equals(applicant)) continue;
                MessageStore.send(un, "新事件上报", who + " 上报了「" + sub + "」，请当日值班关注。", "ticket", ticketId);
                sent++;
            }
            return sent;
        } catch (Exception ignored) {
            return 0;
        }
    }

    public static void configureRepairThicken(
            boolean repairThickenIn,
            boolean allowUserUrgeIn,
            int urgeCooldownMinutesIn,
            boolean lockUrgeAfterRateIn,
            boolean allowCancelUrgeIn,
            boolean requireFaultReasonIn,
            boolean requireCloseSummaryIn,
            boolean requireLowRatingRemarkIn,
            boolean slaSplitIn,
            boolean escalateOnOverdueIn,
            boolean notifySupervisorOnOverdueIn,
            boolean allowHoldResumeIn,
            boolean allowCancelDispatchedIn,
            boolean allowTicketDraftIn,
            boolean allowFollowRateIn,
            boolean preferredSlotIn,
            boolean progressSubscribeIn,
            boolean nightUrgentIn,
            boolean allowPartsNoteIn,
            boolean allowQuoteIn,
            boolean allowPublicAreaIn,
            boolean dupRoomCheckIn,
            boolean allowAssetCodeIn,
            boolean allowRemoteUrlIn,
            boolean allowSerialNoIn,
            boolean allowHelperIn,
            boolean allowRatingTagsIn,
            boolean todayBoardIn,
            boolean printTicketIn) {
        repairThicken = repairThickenIn;
        allowUserUrge = allowUserUrgeIn;
        urgeCooldownMinutes = Math.max(0, Math.min(1440, urgeCooldownMinutesIn));
        lockUrgeAfterRate = lockUrgeAfterRateIn;
        allowCancelUrge = allowCancelUrgeIn;
        requireFaultReason = requireFaultReasonIn;
        requireCloseSummary = requireCloseSummaryIn;
        requireLowRatingRemark = requireLowRatingRemarkIn;
        slaSplit = slaSplitIn;
        escalateOnOverdue = escalateOnOverdueIn;
        notifySupervisorOnOverdue = notifySupervisorOnOverdueIn;
        allowHoldResume = allowHoldResumeIn;
        allowCancelDispatched = allowCancelDispatchedIn;
        allowTicketDraft = allowTicketDraftIn;
        allowFollowRate = allowFollowRateIn;
        preferredSlot = preferredSlotIn;
        progressSubscribe = progressSubscribeIn;
        nightUrgent = nightUrgentIn;
        allowPartsNote = allowPartsNoteIn;
        allowQuote = allowQuoteIn;
        allowPublicArea = allowPublicAreaIn;
        dupRoomCheck = dupRoomCheckIn;
        allowAssetCode = allowAssetCodeIn;
        allowRemoteUrl = allowRemoteUrlIn;
        allowSerialNo = allowSerialNoIn;
        allowHelper = allowHelperIn;
        allowRatingTags = allowRatingTagsIn;
        todayBoard = todayBoardIn;
        printTicket = printTicketIn;
    }

    public static boolean isAllowFineWaive() {
        return allowFineWaive;
    }

    public static boolean isAllowTicketDraft() {
        return allowTicketDraft;
    }

    public static boolean isAllowUserUrge() {
        return allowUserUrge;
    }

    public static boolean isAllowHoldResume() {
        return allowHoldResume;
    }

    public static boolean isAllowCancelDispatched() {
        return allowCancelDispatched;
    }

    public static boolean isAllowCancelUrge() {
        return allowCancelUrge;
    }

    public static boolean isAllowQuote() {
        return allowQuote;
    }

    /** 草稿：把刚提交的 pending 改为 draft（仅本人）。 */
    public static Map<String, Object> saveDraft(long ticketId, String username) {
        if (!allowTicketDraft) throw new IllegalStateException("当前未开启草稿报修");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!TicketSql.str(m.get("username")).equals(username)) {
            throw new IllegalStateException("只能保存自己的草稿");
        }
        String st = String.valueOf(m.get("status"));
        if (!"pending".equals(st) && !"draft".equals(st)) {
            throw new IllegalStateException("仅新建单据可存为草稿");
        }
        TicketSql.db().update("UPDATE " + TICKET + " SET status='draft' WHERE id=?", ticketId);
        appendProgress(ticketId, "draft", username, "保存草稿");
        return get(ticketId);
    }

    /**
     * 管理端退回修改：revise_count 记库；maxReviseTimes&gt;0 时超上限拒绝。
     */
    public static Map<String, Object> returnForRevise(long ticketId, String op, String note) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String st = String.valueOf(m.get("status"));
        if (!"pending".equals(st) && !"pending_mid".equals(st) && !"pending_final".equals(st)) {
            throw new IllegalStateException("仅待审单据可退回修改");
        }
        int used = reviseCountOf(m);
        if (maxReviseTimes > 0 && used >= maxReviseTimes) {
            throw new IllegalStateException(
                    "退回修改次数已达上限（" + maxReviseTimes + " 次），请直接驳回或联系管理员。");
        }
        int next = used + 1;
        String reason = note == null || note.isBlank() ? ("退回修改第 " + next + " 次") : note.trim();
        if (hasColumn("revise_count")) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET status='returned', revise_count=? WHERE id=?",
                    next, ticketId);
        } else {
            TicketSql.db().update("UPDATE " + TICKET + " SET status='returned' WHERE id=?", ticketId);
        }
        appendProgress(ticketId, "returned", op == null ? "" : op, reason);
        return get(ticketId);
    }

    /** 用户重新提交被退回的单据；修改次数未超上限才放行。 */
    public static Map<String, Object> resubmit(long ticketId, String username, String remark) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!String.valueOf(m.get("username")).equals(username)) {
            throw new IllegalStateException("只能重新提交自己的单据");
        }
        if (!"returned".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅被退回的单据可重新提交");
        }
        if (maxReviseTimes > 0 && reviseCountOf(m) >= maxReviseTimes) {
            throw new IllegalStateException("修改次数已达上限（" + maxReviseTimes + " 次），请联系管理员。");
        }
        TicketSql.db().update("UPDATE " + TICKET + " SET status='pending' WHERE id=?", ticketId);
        appendProgress(ticketId, "pending", username,
                remark == null || remark.isBlank() ? "重新提交" : remark.trim());
        return get(ticketId);
    }

    private static int reviseCountOf(Map<String, Object> m) {
        return m.get("reviseCount") instanceof Number n ? n.intValue() : 0;
    }

    /** 同联系电话是否已有未办结单；返回单据号（0=未开或未命中）。 */
    static long dupPhoneOpenId(String phone) {
        if (!phoneDupCheck || !hasColumn("contact_phone")) return 0L;
        String p = phone == null ? "" : phone.trim();
        if (p.isBlank()) return 0L;
        try {
            Long hit = TicketSql.db().queryForObject(
                    "SELECT id FROM " + TICKET
                            + " WHERE contact_phone=? AND status IN"
                            + " ('pending','pending_final','pending_mid','approved','overdue','paused')"
                            + " ORDER BY id DESC LIMIT 1",
                    Long.class, p);
            return hit == null ? 0L : hit;
        } catch (Exception ignored) {
            return 0L;
        }
    }

    /** 同房间未结同类提示（浅：返回文案，不阻断提交）。 */
    public static String checkDupRepairHint(long ticketId) {
        if (!dupRoomCheck || MODE != Mode.STANDALONE) return null;
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) return null;
        long roomId = TicketSql.toLong(m.get("roomId"));
        long typeId = TicketSql.toLong(m.get("typeId"));
        if (roomId <= 0) return null;
        try {
            Integer n = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM " + TICKET
                            + " WHERE id<>? AND room_id=?"
                            + (typeId > 0 ? " AND type_id=?" : "")
                            + " AND status IN ('pending','pending_final','pending_mid','approved','overdue','paused')",
                    Integer.class,
                    typeId > 0
                            ? new Object[]{ticketId, roomId, typeId}
                            : new Object[]{ticketId, roomId});
            if (n != null && n > 0) {
                return "同地点尚有 " + n + " 单未办结报修，请确认是否重复提交。";
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    public static boolean isAllowBatchHire() {
        return allowBatchHire;
    }

    /**
     * 批量录用/淘汰：逐单走既有 approve；录用时顺便写面试结果=通过，淘汰写未通过。
     * 单笔失败计入 failed，不中断其余。
     */
    public static Map<String, Object> batchHire(
            java.util.List<Long> ids, boolean pass, String remark, String op, boolean asSuper) {
        if (!allowBatchHire) throw new IllegalStateException("未开通批量录用");
        if (ids == null || ids.isEmpty()) throw new IllegalStateException("请先勾选单据");
        if (ids.size() > 50) throw new IllegalStateException("单次最多处理 50 条");
        int ok = 0;
        java.util.List<String> errors = new java.util.ArrayList<>();
        String note = remark == null ? "" : remark.trim();
        for (Long id : ids) {
            if (id == null || id <= 0) continue;
            try {
                approve(id, pass, note, op, asSuper, "");
                if (allowInterviewResult && hasColumn("interview_result")) {
                    String result = pass ? "通过" : "未通过";
                    TicketSql.db().update(
                            "UPDATE " + TICKET + " SET interview_result=? WHERE id=?", result, id);
                }
                ok++;
            } catch (Exception e) {
                String msg = e.getMessage() == null ? "失败" : e.getMessage();
                errors.add("#" + id + "：" + msg);
            }
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("okCount", ok);
        out.put("failCount", errors.size());
        out.put("errors", errors);
        if (ok == 0 && !errors.isEmpty()) {
            throw new IllegalStateException(errors.get(0));
        }
        return out;
    }

    public static boolean isRequirePeerConfirm() {
        return requirePeerConfirm;
    }

    /** 评教等：提交即评分且配置了维度时，申请必须带 dims */
    public static boolean ratingDimsRequiredOnApply() {
        return autoApprove && allowRating
                && TicketCopy.RATING_DIMS != null && !TicketCopy.RATING_DIMS.isEmpty();
    }

    /** 提交后置步骤失败时硬删刚插入的单据（避免半截单） */
    public static void deleteFreshTicket(long ticketId) {
        if (ticketId <= 0) return;
        try {
            if (hasColumn("id")) {
                TicketSql.db().update("DELETE FROM " + TICKET + " WHERE id=?", ticketId);
            }
        } catch (Exception ignored) {
            // 回滚失败不掩盖主错误
        }
    }

    /** requireClaimCode 时校验取件码与档案 isbn（取件码/柜号）一致 */
    public static void assertClaimCodeIfRequired(long itemId, String code) {
        if (!requireClaimCode) return;
        String got = code == null ? "" : code.trim();
        if (got.isBlank()) {
            throw new IllegalStateException("请填写取件码");
        }
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        String expect = TicketSql.str(item.get("isbn")).trim();
        if (expect.isBlank()) {
            throw new IllegalStateException("该包裹尚未登记取件码");
        }
        // 档案可能写成「取件码 3182 / 柜 / 手机」；取第一段比对，也允许纯数字码
        String expectCode = expect;
        int slash = expect.indexOf('/');
        if (slash > 0) expectCode = expect.substring(0, slash).trim();
        int dot = expectCode.indexOf('·');
        if (dot > 0) expectCode = expectCode.substring(0, dot).trim();
        String gotNorm = got.replace("取件码", "").replace(" ", "").trim();
        String expectNorm = expectCode.replace("取件码", "").replace(" ", "").trim();
        if (expectCode.equalsIgnoreCase(got)
                || expect.equalsIgnoreCase(got)
                || expectNorm.equalsIgnoreCase(gotNorm)
                || (!gotNorm.isEmpty() && expectNorm.contains(gotNorm))
                || (!gotNorm.isEmpty() && expect.replace(" ", "").toLowerCase().contains(gotNorm.toLowerCase()))) {
            return;
        }
        throw new IllegalStateException("取件码不正确");
    }

    /** matchProfileRoom：资料键↔档案列（查寝默认楼栋/房间；实习绑岗可配单位/岗位） */
    public static void assertMatchProfileRoomIfRequired(String username, long itemId) {
        if (!matchProfileRoom) return;
        com.thesis.service.UserStore.Profile p = com.thesis.service.UserStore.get(username);
        if (p == null) {
            throw new IllegalStateException("请先登录");
        }
        String building = p.extras == null ? "" : TicketSql.str(p.extras.get(matchProfileBuildingKey)).trim();
        String room = p.extras == null ? "" : TicketSql.str(p.extras.get(matchProfileRoomKey)).trim();
        if (building.isBlank() || room.isBlank()) {
            throw new IllegalStateException(matchProfileNeedMessage);
        }
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        String author = TicketSql.str(item.get(matchProfileBuildingField)).trim();
        String title = TicketSql.str(item.get(matchProfileRoomField)).trim();
        if (!profileRoomMatches(building, room, author, title, matchProfileLooseBuilding)) {
            throw new IllegalStateException(matchProfileDenyMessage);
        }
    }

    /** bedConstraint：档案限性别/年级 vs 个人资料 */
    public static void assertBedConstraintIfRequired(String username, long itemId) {
        if (!bedConstraint) return;
        com.thesis.service.UserStore.Profile p = com.thesis.service.UserStore.get(username);
        if (p == null) {
            throw new IllegalStateException("请先登录");
        }
        String gender = p.extras == null ? "" : TicketSql.str(p.extras.get("gender")).trim();
        String grade = p.extras == null ? "" : TicketSql.str(p.extras.get("grade")).trim();
        if (gender.isBlank() && grade.isBlank()) {
            throw new IllegalStateException(bedConstraintNeedMessage);
        }
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        String allowedGender = TicketSql.str(item.get("allowedGender")).trim();
        String allowedGrades = TicketSql.str(item.get("allowedGrades")).trim();
        if (!allowedGender.isBlank()
                && !"不限".equals(allowedGender)
                && !gender.isBlank()
                && !allowedGender.equals(gender)) {
            throw new IllegalStateException(bedConstraintDenyMessage);
        }
        if (!allowedGrades.isBlank() && !grade.isBlank()) {
            boolean ok = false;
            for (String part : allowedGrades.split("[,，、\\s]+")) {
                if (part != null && !part.isBlank() && part.trim().equals(grade)) {
                    ok = true;
                    break;
                }
            }
            if (!ok) {
                throw new IllegalStateException(bedConstraintDenyMessage);
            }
        }
    }

    /** 须知勾选 / 培训勾选 / 保险勾选：申请体校验 */
    public static void assertAckFlagsIfRequired(Map<String, Object> body) {
        if (body == null) body = Map.of();
        if (requireNoticeAck && !truthy(body.get("noticeAck"))) {
            throw new IllegalStateException("请先阅读并勾选须知");
        }
        if (requireTrainingAck && !truthy(body.get("trainingAck"))) {
            throw new IllegalStateException("请确认已完成相关培训");
        }
        if (requireInsuranceAck && !truthy(body.get("insuranceAck"))) {
            throw new IllegalStateException("请先阅读并勾选保险声明");
        }
    }

    /** 校准证书过期停借 */
    public static void assertCalibDueIfRequired(long itemId) {
        if (!blockIfCalibExpired) return;
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        String due = TicketSql.str(item.get("calibDue")).trim();
        if (due.isBlank()) return;
        try {
            java.time.LocalDate d = java.time.LocalDate.parse(due.substring(0, Math.min(10, due.length())));
            if (d.isBefore(java.time.LocalDate.now())) {
                throw new IllegalStateException("该设备校准证书已过期，暂不可借用");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception ignored) {
            // 日期格式异常时不拦截，避免误伤
        }
    }

    private static boolean truthy(Object v) {
        if (v == null) return false;
        if (v instanceof Boolean b) return b;
        String s = String.valueOf(v).trim();
        return "1".equals(s) || "true".equalsIgnoreCase(s) || "yes".equalsIgnoreCase(s);
    }

    /** 与前端 profileRoomMatch 同规则，勿分叉 */
    public static boolean profileRoomMatches(String building, String room, String author, String title) {
        return profileRoomMatches(building, room, author, title, false);
    }

    public static boolean profileRoomMatches(
            String building, String room, String author, String title, boolean looseBuilding) {
        String b = normRoomToken(building);
        String r = normRoomToken(room);
        String a = normRoomToken(author);
        String t = normRoomToken(title);
        if (b.isEmpty() || r.isEmpty()) return false;
        boolean buildingOk = looseBuilding
                ? (b.equals(a) || a.contains(b) || b.contains(a))
                : b.equals(a);
        if (!buildingOk) return false;
        return t.equals(r) || t.contains(r) || r.contains(t);
    }

    static String normRoomToken(String s) {
        if (s == null) return "";
        return s.trim().replace(" ", "").toLowerCase();
    }

    /** L1：互斥码 + 分类限额（选课等） */
    public static void configureRules(boolean mutex, int catLimit) {
        checkMutex = mutex;
        categoryLimit = Math.max(0, catLimit);
        // mutex_code 随档案表 schema 建表
    }

    /** 借期/在途上限/逾期费/默认领取地（≤0 或空表示保持默认） */
    public static void configureBizParams(int loanDays, int maxActive, double finePerDay, String pickupPlace) {
        if (loanDays > 0) bizLoanDays = Math.min(365, loanDays);
        if (maxActive > 0) bizMaxActive = Math.min(200, maxActive);
        if (finePerDay >= 0) bizFinePerDay = Math.min(100.0, finePerDay);
        if (pickupPlace != null && !pickupPlace.isBlank()) bizPickupPlace = pickupPlace.trim();
    }

    public static String ticketTable() {
        return TICKET;
    }

    /** 档案外键物理列名；API 仍暴露 bookId/itemId */
    public static String itemFkColumn() {
        return ITEM_FK == null || ITEM_FK.isBlank() ? "book_id" : ITEM_FK;
    }

    private static void loadTicketColumnsFromResource() {
        Map<String, Object> root = DomainResourceJson.loadObjectMap("domain-ticket-columns.json");
        ITEM_FK = DomainResourceJson.str(root, "itemFkColumn", "book_id");
    }

    public static boolean enabled() {
        return enabled;
    }

    public static boolean isTwoLevelApprove() {
        return twoLevelApprove;
    }

    public static boolean isRequireAttach() {
        return requireAttach;
    }

    public static boolean isAllowRating() {
        return allowRating;
    }

    public static boolean isCheckMutex() {
        return checkMutex;
    }

    public static int categoryLimit() {
        return categoryLimit;
    }

    public static void configureCheckin(boolean enabled) {
        allowCheckin = enabled;
        // checked_in_at / 档案 checkin_code 随能力写入 schema
    }

    public static void configurePeerAccept(boolean enabled) {
        peerAccept = enabled;
    }

    public static boolean isPeerAccept() {
        return peerAccept;
    }

    public static void configureIssuePassCode(boolean enabled) {
        issuePassCode = enabled;
    }

    public static boolean isIssuePassCode() {
        return issuePassCode;
    }

    public static void configureRenew(boolean enabled, int maxTimes, int days) {
        allowRenew = enabled;
        maxRenew = Math.max(1, Math.min(5, maxTimes <= 0 ? 1 : maxTimes));
        renewDays = Math.max(0, days);
        if (allowRenew) {
            ensureColumn("renew_count", "INT NOT NULL DEFAULT 0");
        }
    }

    public static void configureDueSoon(int days) {
        dueSoonDays = Math.max(0, Math.min(14, days));
        if (dueSoonDays > 0) {
            ensureColumn("due_soon_notified_at", "DATETIME NULL");
        }
    }

    public static void configureMaxOverdueTimes(int times) {
        maxOverdueTimes = Math.max(0, Math.min(20, times));
        if (maxOverdueTimes > 0) {
            ensureColumn("ever_overdue", "TINYINT NOT NULL DEFAULT 0");
        }
    }

    public static int dueSoonDays() {
        return dueSoonDays;
    }

    public static int maxOverdueTimes() {
        return maxOverdueTimes;
    }

    public static void configureWaitlist(boolean enabled) {
        allowWaitlist = enabled;
    }

    public static void configureBookHold(boolean enabled, int hours) {
        allowBookHold = enabled;
        holdHours = Math.max(1, Math.min(168, hours <= 0 ? 48 : hours));
        if (allowBookHold) {
            ensureColumn("hold_expire_at", "DATETIME NULL");
        }
    }

    public static void configureBookLost(boolean enabled) {
        allowBookLost = enabled;
    }

    public static void configureRequireReturnAttach(boolean enabled) {
        requireReturnAttach = enabled;
        if (requireReturnAttach) {
            ensureColumn("attach_url", "VARCHAR(255) DEFAULT ''");
        }
    }

    public static boolean isAllowBookLost() {
        return allowBookLost;
    }

    public static boolean isRequireReturnAttach() {
        return requireReturnAttach;
    }

    public static boolean isAllowRenew() {
        return allowRenew;
    }

    public static boolean isAllowBookHold() {
        return allowBookHold;
    }

    public static int holdHours() {
        return holdHours;
    }

    public static int maxRenew() {
        return maxRenew;
    }

    public static void configureNoShow(boolean afterEnd, double penaltyYuan) {
        noShowAfterEnd = afterEnd && allowCheckin;
        noShowPenaltyYuan = Math.max(0, penaltyYuan);
    }

    public static boolean isAllowCheckin() {
        return allowCheckin;
    }

    public static boolean isNoShowAfterEnd() {
        return noShowAfterEnd;
    }

    public static boolean isPickLoanPeriod() {
        return pickLoanPeriod;
    }

    public static boolean isAllowQty() {
        return allowQty;
    }

    public static boolean isRequireRemark() {
        return requireRemark;
    }

    public static boolean isPickDateRange() {
        return pickDateRange;
    }

    public static void setUserRole(String role) {
        if (role != null && !role.isBlank()) userRole = role.trim();
    }

    public static Mode mode() {
        return MODE;
    }

    public static boolean isArchiveMode() {
        return MODE == Mode.ARCHIVE;
    }

    /** archive 模式：按档案 id 申请 */
    public static Map<String, Object> apply(String username, long itemId) {
        return apply(username, itemId, "", null, null, null, null, null);
    }

    public static Map<String, Object> apply(String username, long itemId, String remark) {
        return apply(username, itemId, remark, null, null, null, null, null);
    }

    public static Map<String, Object> apply(String username, long itemId, String remark, String attachUrl) {
        return apply(username, itemId, remark, attachUrl, null, null, null, null);
    }

    public static Map<String, Object> apply(
            String username, long itemId, String remark, String attachUrl, Integer qty, String dueAt) {
        return apply(username, itemId, remark, attachUrl, qty, dueAt, null, null);
    }

    /**
     * @param qty 申请数量；未开 allowQty 时固定为 1
     * @param dueAt 自选到期日；未开 pickLoanPeriod 时忽略
     * @param periodStart 起止日期（请假等）；未开 pickDateRange 时忽略
     * @param periodEnd 结束日期
     */
    public static Map<String, Object> apply(
            String username,
            long itemId,
            String remark,
            String attachUrl,
            Integer qty,
            String dueAt,
            String periodStart,
            String periodEnd) {
        if (MODE != Mode.ARCHIVE) {
            throw new IllegalStateException("当前为独立工单模式，请使用 applyStandalone");
        }
        com.thesis.service.UserStore.assertNotPostMuted(username);
        ExamStore.assertTicketGatePassed(username);
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        int stock = item.get("stock") instanceof Number n ? n.intValue() : Integer.parseInt(String.valueOf(item.get("stock")));
        int nQty = resolveQty(qty, stock);
        boolean asWaitlist = false;
        boolean asBookHold = false;
        if (useQuota && stock < nQty) {
            if (allowBookHold) {
                if (!hasColumn("hold_expire_at")) {
                    throw new IllegalStateException("系统未配置到书过期字段，无法预约到书");
                }
                asBookHold = true;
            } else if (allowWaitlist) {
                asWaitlist = true;
            } else {
                throw new IllegalStateException(ArchiveStore.stockShortage(stock));
            }
        }
        TicketAsserts.assertItemOpen(item);
        TicketAsserts.assertApplyDeadline(item);
        if (!asWaitlist && !asBookHold) {
            TicketAsserts.assertNoTimeConflict(username, itemId, item);
            TicketAsserts.assertNoMutexConflict(username, itemId, item);
            TicketAsserts.assertCategoryLimit(username, item);
            TicketAsserts.assertUnderActiveLimit(username);
        }
        String attach = TicketAsserts.normalizeAttach(attachUrl);
        if (requireAttach && !hasColumn("attach_url")) {
            throw new IllegalStateException("系统未配置附件字段，无法提交带附件的申请");
        }
        if (!attach.isBlank() && !hasColumn("attach_url")) {
            throw new IllegalStateException("系统未配置附件字段，无法保存附件");
        }
        LocalDateTime due = resolveRequestedDue(dueAt);
        LocalDateTime[] period = resolvePeriod(periodStart, periodEnd);
        if (allowQty && !hasColumn("qty")) {
            throw new IllegalStateException("系统未配置数量字段，无法提交带数量的申请");
        }
        if (due != null && !hasColumn("due_at")) {
            throw new IllegalStateException("系统未配置应还日字段，无法保存到期日期");
        }
        if (period != null && (!hasColumn("period_start") || !hasColumn("period_end"))) {
            throw new IllegalStateException("系统未配置请假区间字段，无法保存起止日期");
        }
        if (OccupySpanStore.enabled() && period != null) {
            OccupySpanStore.assertNoOverlap(username, itemId, period[0], period[1]);
        }
        assertNotOverdueFrozen(username);
        if (!allowMultiTicket) {
            Integer dup = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM " + TICKET
                            + " WHERE username=? AND " + itemFkColumn()
                            + "=? AND status IN ('pending','pending_mid','pending_final','approved','overdue','waitlisted','held','hold_ready')",
                    Integer.class, username, itemId);
            if (dup != null && dup > 0) throw new IllegalStateException("该对象已有进行中的单据");
        }

        String rawNote = remark == null ? "" : remark.trim();
        if (requireRemark && rawNote.isBlank()) {
            throw new IllegalStateException("请填写说明后再提交");
        }
        if (minRemarkWords > 0) {
            int words = rawNote.replaceAll("\\s+", "").length();
            if (words < minRemarkWords) {
                throw new IllegalStateException("正文不少于 " + minRemarkWords + " 字后再提交");
            }
        }
        final String note = rawNote.length() > 255 ? rawNote.substring(0, 255) : rawNote;
        KeyHolder kh = new GeneratedKeyHolder();
        final boolean withAttach = hasColumn("attach_url");
        final boolean withQty = hasColumn("qty");
        final boolean withDue = due != null;
        final boolean withPeriod = period != null;
        final String attachFinal = attach;
        final int qtyFinal = nQty;
        final Timestamp dueTs = withDue ? Timestamp.valueOf(due) : null;
        final Timestamp periodStartTs = withPeriod ? Timestamp.valueOf(period[0]) : null;
        final Timestamp periodEndTs = withPeriod ? Timestamp.valueOf(period[1]) : null;
        final boolean withLeaveDays = withPeriod && hasColumn("leave_days");
        final int leaveDaysFinal = withLeaveDays
                ? (int) (java.time.temporal.ChronoUnit.DAYS.between(
                                period[0].toLocalDate(), period[1].toLocalDate())
                        + 1)
                : 0;
        final String initialStatus = asBookHold
                ? "held"
                : (asWaitlist ? "waitlisted" : (autoApprove ? "approved" : "pending"));
        final boolean withApproveAt = !asWaitlist && !asBookHold && autoApprove && hasColumn("approve_at");
        TicketSql.db().update(con -> {
            StringBuilder cols = new StringBuilder(
                    itemFkColumn() + ",username,status,apply_at,remark");
            StringBuilder vals = new StringBuilder("?,?,?,NOW(),?");
            if (hasColumn("fine_yuan")) {
                cols.append(",fine_yuan");
                vals.append(",0");
            }
            if (hasColumn("remind_msg")) {
                cols.append(",remind_msg");
                vals.append(",''");
            }
            if (withApproveAt) {
                cols.append(",approve_at");
                vals.append(",NOW()");
            }
            if (withAttach) {
                cols.append(",attach_url");
                vals.append(",?");
            }
            if (withQty) {
                cols.append(",qty");
                vals.append(",?");
            }
            if (withDue) {
                cols.append(",due_at");
                vals.append(",?");
            }
            if (withPeriod) {
                cols.append(",period_start,period_end");
                vals.append(",?,?");
                if (withLeaveDays) {
                    cols.append(",leave_days");
                    vals.append(",?");
                }
            }
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + TICKET + " (" + cols + ") VALUES (" + vals + ")",
                    Statement.RETURN_GENERATED_KEYS);
            int i = 1;
            ps.setLong(i++, itemId);
            ps.setString(i++, username);
            ps.setString(i++, initialStatus);
            ps.setString(i++, note);
            if (withAttach) ps.setString(i++, attachFinal);
            if (withQty) ps.setInt(i++, qtyFinal);
            if (withDue) ps.setTimestamp(i++, dueTs);
            if (withPeriod) {
                ps.setTimestamp(i++, periodStartTs);
                ps.setTimestamp(i++, periodEndTs);
                if (withLeaveDays) ps.setInt(i, leaveDaysFinal);
            }
            return ps;
        }, kh);
        Number key = kh.getKey();
        long id = key == null ? 0L : key.longValue();
        if (asBookHold) {
            appendProgress(id, "held", username, "暂无库存，加入预约");
            try {
                MessageStore.send(
                        username,
                        "预约排队",
                        "「" + subjectOf(get(id)) + "」暂无库存，已加入预约队列，到书后将站内信通知。",
                        "ticket",
                        id);
            } catch (Exception ignored) {
                // 站内信失败不影响预约单
            }
        } else if (asWaitlist) {
            appendProgress(id, "waitlisted", username, "名额已满，加入候补");
            try {
                MessageStore.send(
                        username,
                        "候补排队",
                        "「" + subjectOf(get(id)) + "」名额已满，已进入候补队列，有名额时将按顺序转为待审。",
                        "ticket",
                        id);
            } catch (Exception ignored) {
                // 站内信失败不影响候补单
            }
        } else if (autoApprove) {
            appendProgress(id, "approved", username, "用户提交（即时生效）");
        } else {
            appendProgress(id, "pending", username, "用户提交");
            String subj = subjectOf(get(id));
            notifyAdminsNewTicket(id, username, subj);
            notifyPeerOwnerNewTicket(id, itemId, username, subj);
        }
        if (period != null && OccupySpanStore.enabled()) {
            OccupySpanStore.record(username, itemId, id, subjectOf(get(id)), period[0], period[1]);
        }
        Map<String, Object> applied = get(id);
        if (applied != null) {
            int dutyNotified = notifyDutyOnNewReport(id, username, subjectOf(applied));
            if (dutyNotified > 0) applied.put("dutyNotified", dutyNotified);
        }
        return applied;
    }

    private static LocalDateTime[] resolvePeriod(String periodStart, String periodEnd) {
        if (!pickDateRange) return null;
        if (periodStart == null || periodStart.isBlank() || periodEnd == null || periodEnd.isBlank()) {
            throw new IllegalStateException("请选择起止日期");
        }
        LocalDateTime start = TicketSql.parseDateTimeFlexible(periodStart.trim(), false);
        LocalDateTime end = TicketSql.parseDateTimeFlexible(periodEnd.trim(), true);
        if (!end.isAfter(start)) {
            throw new IllegalStateException("结束日期须晚于开始日期");
        }
        if (ChronoUnit.DAYS.between(start.toLocalDate(), end.toLocalDate()) > 90) {
            throw new IllegalStateException("起止跨度不能超过 90 天");
        }
        return new LocalDateTime[]{start, end};
    }

    private static int resolveQty(Integer qty, int stock) {
        if (!allowQty) return 1;
        int n = qty == null ? 1 : qty;
        if (n < 1) throw new IllegalStateException("数量至少为 1");
        if (n > 99) throw new IllegalStateException("单次数量不能超过 99");
        if (stock > 0 && n > stock) throw new IllegalStateException(ArchiveStore.stockShortage(stock));
        return n;
    }

    private static LocalDateTime resolveRequestedDue(String dueAt) {
        if (!pickLoanPeriod) return null;
        if (dueAt == null || dueAt.isBlank()) {
            throw new IllegalStateException("请选择到期日期");
        }
        LocalDateTime due = TicketSql.parseDateTimeFlexible(dueAt.trim(), true);
        LocalDateTime now = LocalDateTime.now();
        if (!due.isAfter(now)) {
            throw new IllegalStateException("到期日期须晚于当前时间");
        }
        if (due.isAfter(now.plusDays(90))) {
            throw new IllegalStateException("到期日期不能超过 90 天");
        }
        return due;
    }

    private static int rowQty(Map<String, Object> m) {
        Object q = m.get("qty");
        if (q == null) return 1;
        String s = String.valueOf(q).trim();
        if (s.isBlank() || "null".equalsIgnoreCase(s)) return 1;
        if (q instanceof Number n) return Math.max(1, n.intValue());
        try {
            return Math.max(1, Integer.parseInt(s));
        } catch (Exception e) {
            throw new IllegalStateException("单据数量无效", e);
        }
    }

    /** standalone 模式：报修等；优先用楼栋/房间/类型 FK，地点由房间拼出 */
    public static Map<String, Object> applyStandalone(
            String username,
            String title,
            String location,
            String remark,
            Long typeId,
            Long roomId) {
        return applyStandalone(username, title, location, remark, typeId, roomId, null, null, null);
    }

    public static Map<String, Object> applyStandalone(
            String username,
            String title,
            String location,
            String remark,
            Long typeId,
            Long roomId,
            String attachUrl) {
        return applyStandalone(username, title, location, remark, typeId, roomId, attachUrl, null, null);
    }

    public static Map<String, Object> applyStandalone(
            String username,
            String title,
            String location,
            String remark,
            Long typeId,
            Long roomId,
            String attachUrl,
            String priority,
            String contactPhone) {
        if (MODE != Mode.STANDALONE) {
            throw new IllegalStateException("当前为档案关联模式，请使用 apply");
        }
        String t = title == null ? "" : title.trim();
        if (t.isBlank()) throw new IllegalArgumentException("请填写标题");
        long dupPhoneId = dupPhoneOpenId(contactPhone);
        if (dupPhoneId > 0) {
            throw new IllegalStateException(
                    "该联系电话已有未办结单据#" + dupPhoneId + "，请确认是否重复提交。");
        }
        TicketAsserts.assertUnderActiveLimit(username);
        String attach = TicketAsserts.normalizeAttach(attachUrl);
        if (requireAttach && !hasColumn("attach_url")) {
            throw new IllegalStateException("系统未配置附件字段，无法提交带附件的申请");
        }
        if (!attach.isBlank() && !hasColumn("attach_url")) {
            throw new IllegalStateException("系统未配置附件字段，无法保存附件");
        }

        long tid = typeId == null ? 0L : typeId;
        long rid = roomId == null ? 0L : roomId;
        if (TicketLookupStore.enabled()) {
            if (tid <= 0 || !TicketLookupStore.typeExists(tid)) {
                throw new IllegalArgumentException("请选择" + TicketLookupStore.meta().get("typeLabel"));
            }
            if (rid <= 0 || !TicketLookupStore.unitExists(rid)) {
                throw new IllegalArgumentException("请选择" + TicketLookupStore.meta().get("unitLabel"));
            }
        }

        String loc = location == null ? "" : location.trim();
        if (rid > 0) {
            String fromUnit = TicketLookupStore.formatLocation(rid);
            if (!fromUnit.isBlank()) loc = fromUnit;
        }

        final String locFinal = loc;
        final String remarkFinal = remark == null ? "" : remark.trim();
        final long tidFinal = tid;
        final long ridFinal = rid;
        final String attachFinal = attach;

        KeyHolder kh = new GeneratedKeyHolder();
        if (hasColumn("attach_url")) {
            TicketSql.db().update(con -> {
                PreparedStatement ps = con.prepareStatement(
                        "INSERT INTO " + TICKET
                                + " (username,title,location,type_id,room_id,status,apply_at,remark,attach_url) "
                                + "VALUES (?,?,?,?,?, 'pending', NOW(), ?, ?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, username);
                ps.setString(2, t);
                ps.setString(3, locFinal);
                if (tidFinal > 0) ps.setLong(4, tidFinal); else ps.setObject(4, null);
                if (ridFinal > 0) ps.setLong(5, ridFinal); else ps.setObject(5, null);
                ps.setString(6, remarkFinal);
                ps.setString(7, attachFinal);
                return ps;
            }, kh);
        } else {
            TicketSql.db().update(con -> {
                PreparedStatement ps = con.prepareStatement(
                        "INSERT INTO " + TICKET
                                + " (username,title,location,type_id,room_id,status,apply_at,remark) "
                                + "VALUES (?,?,?,?,?, 'pending', NOW(), ?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, username);
                ps.setString(2, t);
                ps.setString(3, locFinal);
                if (tidFinal > 0) ps.setLong(4, tidFinal); else ps.setObject(4, null);
                if (ridFinal > 0) ps.setLong(5, ridFinal); else ps.setObject(5, null);
                ps.setString(6, remarkFinal);
                return ps;
            }, kh);
        }
        Number key = kh.getKey();
        long id = key == null ? 0L : key.longValue();
        patchStandaloneExtras(id, priority, contactPhone);
        appendProgress(id, "pending", username, "用户提交");
        notifyAdminsNewTicket(id, username, t);
        Map<String, Object> createdStd = get(id);
        if (createdStd != null) {
            int dutyNotified = notifyDutyOnNewReport(id, username, t);
            if (dutyNotified > 0) createdStd.put("dutyNotified", dutyNotified);
        }
        return createdStd;
    }

    /** 兼容旧调用：仅标题/地点/说明 */
    public static Map<String, Object> applyStandalone(String username, String title, String location, String remark) {
        return applyStandalone(username, title, location, remark, null, null, null, null, null);
    }

    private static void patchStandaloneExtras(long id, String priority, String contactPhone) {
        if (id <= 0) return;
        boolean hasP = hasColumn("priority");
        boolean hasC = hasColumn("contact_phone");
        boolean wantP = priority != null && !priority.isBlank();
        boolean wantC = contactPhone != null && !contactPhone.isBlank();
        if (wantP && !hasP) {
            throw new IllegalStateException("系统未配置优先级字段，无法保存");
        }
        if (wantC && !hasC) {
            throw new IllegalStateException("系统未配置联系电话字段，无法保存");
        }
        if (!hasP && !hasC) return;
        String p = priority == null || priority.isBlank() ? "普通" : priority.trim();
        if (p.length() > 16) p = p.substring(0, 16);
        String phone = contactPhone == null ? "" : contactPhone.trim();
        if (phone.length() > 20) phone = phone.substring(0, 20);
        if (hasP && hasC) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET priority=?, contact_phone=? WHERE id=?", p, phone, id);
        } else if (hasP) {
            TicketSql.db().update("UPDATE " + TICKET + " SET priority=? WHERE id=?", p, id);
        } else {
            TicketSql.db().update("UPDATE " + TICKET + " SET contact_phone=? WHERE id=?", phone, id);
        }
    }

    private static void notifyAdminsNewTicket(long ticketId, String applicant, String subject) {
        if (ticketId <= 0) return;
        try {
            String sub = subject == null || subject.isBlank() ? ("单据#" + ticketId) : subject;
            String who = UserStore.displayName(applicant);
            MessageStore.notifyAdmins(
                    peerAccept ? "待调剂" : "待受理",
                    who + " 提交了「" + sub + "」，请尽快处理。",
                    "ticket",
                    ticketId);
        } catch (Exception ignored) {
        }
    }

    private static void notifyPeerOwnerNewTicket(long ticketId, long itemId, String applicant, String subject) {
        if (!peerAccept || ticketId <= 0 || itemId <= 0) return;
        try {
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            if (item == null) return;
            String owner = TicketSql.str(item.get("ownerUsername"));
            if (owner.isBlank() || owner.equals(applicant)) return;
            String sub = subject == null || subject.isBlank() ? ("单据#" + ticketId) : subject;
            String who = UserStore.displayName(applicant);
            MessageStore.send(
                    owner,
                    "待确认志愿",
                    who + " 向「" + sub + "」提交了志愿，请确认或婉拒。",
                    "ticket",
                    ticketId);
        } catch (Exception ignored) {
        }
    }

    /** C-05：档案主人确认/拒绝志愿；通过时复用 approve 扣库存。 */
    public static Map<String, Object> peerRespond(long ticketId, String username, boolean pass, String remark) {
        if (!peerAccept) throw new IllegalStateException("当前未开启互选确认");
        if (MODE != Mode.ARCHIVE) throw new IllegalStateException("当前不支持互选确认");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!"pending".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅待确认志愿可操作");
        }
        long itemId = TicketSql.toLong(m.get("bookId"));
        if (itemId <= 0) itemId = TicketSql.toLong(m.get("itemId"));
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalStateException(TicketCopy.archiveNoun() + "不存在");
        String owner = TicketSql.str(item.get("ownerUsername"));
        if (owner.isBlank()) throw new IllegalStateException("档案未绑定确认人");
        if (!owner.equals(username == null ? "" : username.trim())) {
            throw new IllegalStateException("仅档案确认人可操作");
        }
        String note = remark == null ? "" : remark.trim();
        if (!pass && note.isBlank()) {
            throw new IllegalStateException("请填写婉拒原因");
        }
        Map<String, Object> out = approve(ticketId, pass, note, username, true);
        appendProgress(
                ticketId,
                pass ? "peer_accept" : "peer_reject",
                username,
                pass ? "对方确认" : (note.isBlank() ? "对方婉拒" : note));
        return out;
    }

    /** 待我确认：档案 owner_username=我 且待审的志愿单。 */
    public static Map<String, Object> pagePeerInbox(String ownerUsername, String status, int page, int size) {
        if (!peerAccept || MODE != Mode.ARCHIVE) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("list", List.of());
            empty.put("total", 0);
            empty.put("page", Math.max(1, page));
            empty.put("size", Math.max(1, size));
            return empty;
        }
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String owner = ownerUsername == null ? "" : ownerUsername.trim();
        if (owner.isBlank()) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("list", List.of());
            empty.put("total", 0);
            empty.put("page", page);
            empty.put("size", size);
            return empty;
        }
        String itemTable = ArchiveStore.itemTable();
        String fk = itemFkColumn();
        StringBuilder where = new StringBuilder(
                " WHERE i.owner_username=? AND t." + fk + "=i.id");
        List<Object> args = new ArrayList<>();
        args.add(owner);
        if (status != null && !status.isBlank()) {
            where.append(" AND t.status=?");
            args.add(status);
        } else {
            where.append(" AND t.status='pending'");
        }
        String from = " FROM " + TICKET + " t JOIN " + itemTable + " i ON t." + fk + "=i.id";
        Integer total = TicketSql.db().queryForObject(
                "SELECT COUNT(*)" + from + where, Integer.class, args.toArray());
        int t = total == null ? 0 : total;
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = TicketSql.db().query(
                "SELECT t.*" + from + where + " ORDER BY t.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> TicketStatusOps.enrich(TicketRowMaps.mapRow(rs)),
                args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    /** 当前用户是否为某单据关联档案的确认人 */
    public static boolean isPeerOwnerOf(long ticketId, String username) {
        if (!peerAccept || MODE != Mode.ARCHIVE || username == null || username.isBlank()) return false;
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) return false;
        long itemId = TicketSql.toLong(m.get("bookId"));
        if (itemId <= 0) itemId = TicketSql.toLong(m.get("itemId"));
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) return false;
        return username.trim().equals(TicketSql.str(item.get("ownerUsername")));
    }

    public static List<Map<String, Object>> listProgress(long ticketId) {
        return TicketProgressOps.listProgress(ticketId);
    }

    public static Map<String, Object> markPickup(long ticketId, String place, Integer actualQty, String operator) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!hasColumn("pickup_at")) {
            throw new IllegalStateException("系统未配置领取时间字段，无法登记领取");
        }
        if (allowQty && !hasColumn("actual_qty")) {
            throw new IllegalStateException("系统未配置实发数量字段，无法登记领取");
        }
        String st = String.valueOf(m.get("status"));
        // 仅进行中单据可登记；退库后库存已回补，再登记会乱账
        if (!"approved".equals(st) && !"overdue".equals(st)) {
            throw new IllegalStateException("仅已通过/进行中单据可登记领取");
        }
        String prev = TicketSql.str(m.get("pickupAt"));
        if (!prev.isBlank()) {
            throw new IllegalStateException("该单已登记领取，不可重复操作");
        }
        String loc = place == null ? "" : place.trim();
        if (loc.isBlank()) loc = bizPickupPlace;
        if (loc.isBlank()) {
            throw new IllegalStateException("请填写领取地点");
        }
        if (loc.length() > 128) {
            throw new IllegalStateException("领取地点过长");
        }
        if (!hasColumn("pickup_place")) {
            throw new IllegalStateException("系统未配置领取地点字段，无法登记领取");
        }

        int applied = rowQty(m);
        Integer qtyToWrite = null;
        if (allowQty && hasColumn("actual_qty")) {
            if (actualQty == null || actualQty <= 0) {
                throw new IllegalStateException("请填写实发数量（正整数）");
            }
            if (actualQty > applied) {
                throw new IllegalStateException("实发数量不能超过申领数量 " + applied);
            }
            qtyToWrite = actualQty;
            // 少发：把未发出部分回补库存，避免完结时按申领量超额回库
            if (MODE == Mode.ARCHIVE && useQuota && actualQty < applied) {
                long itemId = TicketSql.toLong(m.get("bookId"));
                if (itemId > 0 && ArchiveStore.getItemRaw(itemId) != null) {
                    ArchiveStore.adjustStock(itemId, applied - actualQty);
                    tryPromoteWaitlist(itemId);
                    tryPromoteBookHold(itemId);
                }
            }
        } else if (actualQty != null && hasColumn("actual_qty")) {
            if (actualQty <= 0) {
                throw new IllegalStateException("实发数量须为正整数");
            }
            if (actualQty > applied) {
                throw new IllegalStateException("实发数量不能超过申领数量 " + applied);
            }
            qtyToWrite = actualQty;
        }

        if (hasColumn("actual_qty") && qtyToWrite != null) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET pickup_at=NOW(), pickup_place=?, actual_qty=? WHERE id=?",
                    loc, qtyToWrite, ticketId);
        } else if (hasColumn("pickup_place")) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET pickup_at=NOW(), pickup_place=? WHERE id=?",
                    loc, ticketId);
        } else {
            TicketSql.db().update("UPDATE " + TICKET + " SET pickup_at=NOW() WHERE id=?", ticketId);
        }
        String tip = "领取登记：" + loc;
        if (qtyToWrite != null) tip = tip + "，实发 " + qtyToWrite;
        appendProgress(ticketId, "pickup", operator, tip);
        notifyPickup(m, loc, qtyToWrite);
        return get(ticketId);
    }

    public static Map<String, Object> markFinePaid(long ticketId, String operator) {
        if (!hasColumn("fine_status")) throw new IllegalStateException("当前不支持逾期费用登记");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String st = String.valueOf(m.get("status"));
        if (!List.of("approved", "overdue", "returned").contains(st)) {
            throw new IllegalStateException("当前状态不可登记费用结清");
        }
        if (TicketSql.toDouble(m.get("fineYuan")) <= 0) {
            throw new IllegalStateException("无待结清费用");
        }
        if ("paid".equals(String.valueOf(m.getOrDefault("fineStatus", "")))) {
            throw new IllegalStateException("费用已结清");
        }
        TicketSql.db().update("UPDATE " + TICKET + " SET fine_status='paid' WHERE id=?", ticketId);
        appendProgress(ticketId, "fine_paid", operator, TicketCopy.FINE_PAID_LABEL);
        return get(ticketId);
    }

    /** 逾期罚款减免（开题挂 allowFineWaive） */
    public static Map<String, Object> markFineWaived(long ticketId, String operator, String reason) {
        if (!allowFineWaive) throw new IllegalStateException("当前未开启罚款减免");
        if (!hasColumn("fine_status")) throw new IllegalStateException("当前不支持逾期费用登记");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String st = String.valueOf(m.get("status"));
        if (!List.of("approved", "overdue", "returned").contains(st)) {
            throw new IllegalStateException("当前状态不可登记罚款减免");
        }
        if ("paid".equals(String.valueOf(m.getOrDefault("fineStatus", "")))
                || "waived".equals(String.valueOf(m.getOrDefault("fineStatus", "")))) {
            throw new IllegalStateException("费用已结清或已减免");
        }
        String note = reason == null ? "" : reason.trim();
        if (note.length() > 200) note = note.substring(0, 200);
        if (hasColumn("fine_yuan")) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET fine_status='waived', fine_yuan=0 WHERE id=?", ticketId);
        } else {
            TicketSql.db().update("UPDATE " + TICKET + " SET fine_status='waived' WHERE id=?", ticketId);
        }
        appendProgress(ticketId, "fine_waived", operator, note.isBlank() ? "罚款已减免" : ("罚款减免：" + note));
        return get(ticketId);
    }

    static void appendProgress(long ticketId, String status, String operator, String remark) {
        if (ticketId <= 0) return;
        if (PROGRESS == null || PROGRESS.isBlank()) return;
        ensureProgressTable();
        try {
            TicketProgressOps.insertProgressRow(
                    ticketId,
                    status,
                    operator,
                    remark,
                    Timestamp.valueOf(LocalDateTime.now()));
        } catch (Exception e) {
            throw new IllegalStateException("审核进度写入失败", e);
        }
    }

    /** 默认借期（天）：thesis 配置，缺省 LOAN_DAYS */
    public static int loanDays() {
        return bizLoanDays;
    }

    /** 每人在途单据上限：thesis 配置，缺省 MAX_ACTIVE */
    public static int maxActive() {
        return bizMaxActive;
    }

    /** 逾期预估单价：thesis 配置，缺省 FINE_PER_DAY */
    public static double finePerDay() {
        return bizFinePerDay;
    }

    /** 兼容：无处理人（门禁自检等） */
    public static Map<String, Object> approve(long ticketId, boolean pass, String remark) {
        return approve(ticketId, pass, remark, null, true, null);
    }

    public static Map<String, Object> approve(long ticketId, boolean pass, String remark, String operator) {
        return approve(ticketId, pass, remark, operator, true, null);
    }

    public static Map<String, Object> approve(
            long ticketId, boolean pass, String remark, String operator, boolean superAdmin) {
        return approve(ticketId, pass, remark, operator, superAdmin, null);
    }

    /**
     * @param assigneeUsername 终审通过时派给的处理人；空则绑定操作者本人
     */
    public static Map<String, Object> approve(
            long ticketId,
            boolean pass,
            String remark,
            String operator,
            boolean superAdmin,
            String assigneeUsername) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String st = String.valueOf(m.get("status"));
        boolean first = "pending".equals(st);
        boolean verifying = "verifying".equals(st);
        boolean midStage = "pending_mid".equals(st);
        boolean finalStage = "pending_final".equals(st);
        boolean holdReady = "hold_ready".equals(st);
        if (requireClaimProof && first && pass) {
            throw new IllegalStateException("请先提交并核验认领凭证");
        }
        if (requireClaimProof && verifying && pass) {
            ClaimProofStore.assertPassed(ticketId);
            first = true; // 核验通过后按初审路径办结
        }
        if (!first && !midStage && !finalStage && !holdReady && !verifying) {
            throw new IllegalStateException("仅待审核或待取书单据可审批");
        }
        if (verifying && !requireClaimProof) {
            throw new IllegalStateException("仅待审核或待取书单据可审批");
        }
        if (twoLevelApprove && finalStage && pass && !superAdmin) {
            throw new IllegalStateException("终审通过需总管操作");
        }
        if (pass && requirePeerConfirm && hasColumn("peer_ack")) {
            Object rawAck = m.get("peerAck");
            boolean acked = Boolean.TRUE.equals(rawAck)
                    || "1".equals(String.valueOf(rawAck))
                    || "true".equalsIgnoreCase(String.valueOf(rawAck));
            if (!acked) {
                throw new IllegalStateException("对方尚未确认，暂不可审核通过");
            }
        }
        String op = operator == null ? "" : operator.trim();
        String dispatchTo = assigneeUsername == null ? "" : assigneeUsername.trim();
        boolean bind = !op.isBlank() && hasColumn("assignee_username");
        String note = remark == null ? "" : remark.trim();
        if (!pass && note.isBlank()) {
            throw new IllegalStateException("请填写驳回原因");
        }
        if (pass && note.isBlank()) {
            Object prev = m.get("remark");
            note = prev == null ? "" : String.valueOf(prev);
        }

        // 到书待取：通过=确认借出（库存已在晋升时预扣）；驳回=回补并顺延
        if (holdReady) {
            long itemId = TicketSql.toLong(m.get("bookId"));
            int nQty = rowQty(m);
            if (!pass) {
                if (MODE == Mode.ARCHIVE && useQuota && itemId > 0
                        && ArchiveStore.getItemRaw(itemId) != null) {
                    ArchiveStore.adjustStock(itemId, nQty);
                }
                TicketSql.db().update(
                        "UPDATE " + TICKET + " SET status='rejected', remark=?"
                                + (hasColumn("hold_expire_at") ? ", hold_expire_at=NULL" : "")
                                + " WHERE id=?",
                        note, ticketId);
                appendProgress(ticketId, "rejected", op,
                        note.isBlank() ? "驳回待取书预约" : note);
                notifyTicketResult(m, false, note);
                if (itemId > 0) tryPromoteBookHold(itemId);
                return get(ticketId);
            }
            return finalizeHoldReadyApprove(ticketId, m, note, op, dispatchTo, bind);
        }

        if (!pass) {
            if (bind) {
                TicketSql.db().update(
                        "UPDATE " + TICKET + " SET status='rejected', approve_at=NOW(), remark=?, assignee_username=? WHERE id=?",
                        note, op, ticketId);
            } else {
                TicketSql.db().update(
                        "UPDATE " + TICKET + " SET status='rejected', approve_at=NOW(), remark=? WHERE id=?",
                        note, ticketId);
            }
            notifyTicketResult(m, false, note);
            appendProgress(ticketId, "rejected", op,
                    note == null || note.isBlank() ? TicketCopy.stateLabel("rejected", TicketCopy.verbLabel("reject", "已驳回")) : note);
            return get(ticketId);
        }

        // 三级：初审通过 → 待复审
        if (threeLevelApprove && first) {
            advanceApproveStage(ticketId, "pending_mid", note, op, bind, m,
                    "初审已通过", "「" + subjectOf(m) + "」已通过初审，等待复审。",
                    "待复审", "初审通过");
            return get(ticketId);
        }
        // 三级：复审通过 → 待终审
        if (threeLevelApprove && midStage) {
            advanceApproveStage(ticketId, "pending_final", note, op, bind, m,
                    "复审已通过", "「" + subjectOf(m) + "」已通过复审，等待终审。",
                    "待终审", "复审通过");
            return get(ticketId);
        }
        // 二级：首关 → 待终审（不扣库存）；文案跟 verbs（报修「受理」等），勿写死「初审」
        if (twoLevelApprove && !threeLevelApprove && first) {
            String approveV = TicketCopy.verbLabel("approve", "通过");
            String waitLab = TicketCopy.stateLabel("pending_final", "待终审");
            advanceApproveStage(ticketId, "pending_final", note, op, bind, m,
                    approveV + "成功",
                    "「" + subjectOf(m) + "」" + approveV + "成功，等待终审。",
                    waitLab,
                    approveV);
            return get(ticketId);
        }

        // 终审通过或单级通过 → approved（扣库存 / 时间银行扣时长）
        if (useDeadline && !hasColumn("due_at")) {
            throw new IllegalStateException("系统未配置应还日字段，无法审批通过");
        }
        if (timebankRedeem) {
            TimebankStore.debitForTicketApprove(m);
        }
        BalanceLedgerStore.debitForTicketApprove(m);
        long approvedItemId = 0L;
        if (MODE == Mode.ARCHIVE && useQuota) {
            long itemId = TicketSql.toLong(m.get("bookId"));
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            if (item == null) throw new IllegalStateException("对象不存在");
            int stock = item.get("stock") instanceof Number n ? n.intValue() : 0;
            int nQty = rowQty(m);
            if (stock < nQty) throw new IllegalStateException(ArchiveStore.stockShortageNeed(nQty));
            ArchiveStore.adjustStock(itemId, -nQty);
            approvedItemId = itemId;
        }
        if (MODE == Mode.ARCHIVE && useDeadline) {
            LocalDateTime approveAt = LocalDateTime.now();
            LocalDateTime dueAt = approveAt.plusDays(levelSlaDays(m, loanDays()));
            Object requested = m.get("dueAt");
            if (requested != null && !String.valueOf(requested).isBlank()) {
                try {
                    dueAt = TicketSql.parseDateTimeFlexible(String.valueOf(requested).trim());
                } catch (RuntimeException e) {
                    throw e;
                } catch (Exception e) {
                    throw new IllegalStateException("应还日期无效", e);
                }
            }
            String handler = !dispatchTo.isBlank() ? dispatchTo : op;
            boolean bindHandler = !handler.isBlank() && hasColumn("assignee_username");
            if (bindHandler) {
                StringBuilder sql = new StringBuilder(
                        "UPDATE " + TICKET + " SET status='approved', approve_at=?, remark=?, assignee_username=?");
                List<Object> args = new ArrayList<>();
                args.add(Timestamp.valueOf(approveAt));
                args.add(note);
                args.add(handler);
                sql.append(", due_at=?");
                args.add(Timestamp.valueOf(dueAt));
                if (hasColumn("fine_yuan")) {
                    sql.append(", fine_yuan=0");
                }
                if (hasColumn("remind_msg")) {
                    sql.append(", remind_msg=''");
                }
                sql.append(" WHERE id=?");
                args.add(ticketId);
                TicketSql.db().update(sql.toString(), args.toArray());
            } else {
                StringBuilder sql = new StringBuilder(
                        "UPDATE " + TICKET + " SET status='approved', approve_at=?, remark=?");
                List<Object> args = new ArrayList<>();
                args.add(Timestamp.valueOf(approveAt));
                args.add(note);
                sql.append(", due_at=?");
                args.add(Timestamp.valueOf(dueAt));
                if (hasColumn("fine_yuan")) {
                    sql.append(", fine_yuan=0");
                }
                if (hasColumn("remind_msg")) {
                    sql.append(", remind_msg=''");
                }
                sql.append(" WHERE id=?");
                args.add(ticketId);
                TicketSql.db().update(sql.toString(), args.toArray());
            }
        } else if (useDeadline) {
            // 独立工单 SLA：受理进入处理中时起算处理时限（等级影响时限时按等级取天数）
            LocalDateTime approveAt = LocalDateTime.now();
            LocalDateTime dueAt = approveAt.plusDays(levelSlaDays(m, loanDays()));
            String handler = !dispatchTo.isBlank() ? dispatchTo : op;
            boolean bindHandler = !handler.isBlank() && hasColumn("assignee_username");
            if (bindHandler) {
                TicketSql.db().update(
                        "UPDATE " + TICKET
                                + " SET status='approved', approve_at=?, remark=?, assignee_username=?, due_at=?"
                                + (hasColumn("fine_yuan") ? ", fine_yuan=0" : "")
                                + (hasColumn("remind_msg") ? ", remind_msg=''" : "")
                                + " WHERE id=?",
                        Timestamp.valueOf(approveAt),
                        note,
                        handler,
                        Timestamp.valueOf(dueAt),
                        ticketId);
            } else {
                TicketSql.db().update(
                        "UPDATE " + TICKET
                                + " SET status='approved', approve_at=?, remark=?, due_at=?"
                                + (hasColumn("fine_yuan") ? ", fine_yuan=0" : "")
                                + (hasColumn("remind_msg") ? ", remind_msg=''" : "")
                                + " WHERE id=?",
                        Timestamp.valueOf(approveAt),
                        note,
                        Timestamp.valueOf(dueAt),
                        ticketId);
            }
            if (slaSplit && hasColumn("response_due_at")) {
                LocalDateTime respDue = approveAt.plusDays(levelSlaDays(m, 1));
                TicketSql.db().update(
                        "UPDATE " + TICKET + " SET response_due_at=? WHERE id=?",
                        Timestamp.valueOf(respDue),
                        ticketId);
            }
        } else if (bind) {
            String handler = !dispatchTo.isBlank() ? dispatchTo : op;
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET status='approved', approve_at=NOW(), remark=?, assignee_username=? WHERE id=?",
                    note, handler, ticketId);
        } else {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET status='approved', approve_at=NOW(), remark=? WHERE id=?",
                    note, ticketId);
        }
        String passCode = issuePassCodeIfNeeded(ticketId);
        notifyTicketResult(m, true, note, passCode);
        notifyArrivalIfNeeded(m);
        appendProgress(ticketId, "approved", op, note.isBlank()
                ? TicketCopy.stateLabel("approved", TicketCopy.verbLabel("approve", "审核通过")) : note);
        // 库存扣尽：同对象其它待审自动驳回（失物一件一主；图书最后一本等同）
        int autoRejected = 0;
        if (approvedItemId > 0) {
            autoRejected = rejectSiblingsWhenStockGone(approvedItemId, ticketId);
        }
        Map<String, Object> out = get(ticketId);
        if (out != null) {
            out.put("autoRejectedCount", autoRejected);
        }
        return out;
    }

    /** 中间审批推进（不扣库存）。 */
    private static void advanceApproveStage(
            long ticketId,
            String nextStatus,
            String note,
            String op,
            boolean bind,
            Map<String, Object> m,
            String userTitle,
            String userBody,
            String adminTitle,
            String progressDefault) {
        if (bind) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET status=?, remark=?, assignee_username=? WHERE id=?",
                    nextStatus, note, op, ticketId);
        } else {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET status=?, remark=? WHERE id=?",
                    nextStatus, note, ticketId);
        }
        try {
            String user = TicketSql.str(m.get("username"));
            if (!user.isBlank()) {
                MessageStore.send(user, userTitle, userBody, "ticket", TicketSql.toLong(m.get("id")));
            }
            MessageStore.notifyAdmins(
                    adminTitle, userBody, "ticket", TicketSql.toLong(m.get("id")), op);
        } catch (Exception ignored) {
        }
        appendProgress(ticketId, nextStatus, op, note.isBlank()
                ? TicketCopy.stateLabel(nextStatus, progressDefault) : note);
    }

    /** C-09：通过后签发通行码（字符串；不对接闸机硬件）。失败须抛错，禁止静默无码。 */
    private static String issuePassCodeIfNeeded(long ticketId) {
        if (!issuePassCode || ticketId <= 0) return "";
        if (!hasColumn("pass_code")) {
            throw new IllegalStateException("系统未配置通行码字段，无法签发");
        }
        Map<String, Object> cur = get(ticketId);
        if (cur != null) {
            String prev = TicketSql.str(cur.get("passCode"));
            if (!prev.isBlank()) return prev;
        }
        String code = "VIS" + String.format("%08d", Math.floorMod(System.nanoTime(), 100_000_000));
        try {
            int n = TicketSql.db().update("UPDATE " + TICKET + " SET pass_code=? WHERE id=?", code, ticketId);
            if (n <= 0) {
                throw new IllegalStateException("通行码签发失败，请重试");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("通行码签发失败，请重试", e);
        }
        appendProgress(ticketId, "pass_code", "system", "通行码 " + code);
        return code;
    }

    /**
     * 通过并扣库存后若余量为 0，驳回同档案其它 pending/pending_mid/pending_final。
     * @return 实际驳回条数
     */
    private static int rejectSiblingsWhenStockGone(long itemId, long approvedTicketId) {
        if (MODE != Mode.ARCHIVE || !useQuota || itemId <= 0) return 0;
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) return 0;
        int remain = item.get("stock") instanceof Number n ? n.intValue() : 0;
        if (remain > 0) return 0;
        String reason = TicketCopy.siblingRejectTip();
        List<Long> ids;
        try {
            ids = TicketSql.db().query(
                    "SELECT id FROM " + TICKET
                            + " WHERE " + itemFkColumn() + "=? AND id<>? AND status IN ('pending','pending_mid','pending_final')",
                    (rs, i) -> rs.getLong(1),
                    itemId,
                    approvedTicketId);
        } catch (Exception e) {
            throw new IllegalStateException("库存耗尽后查询同档待审失败", e);
        }
        if (ids == null || ids.isEmpty()) return 0;
        int rejected = 0;
        for (Long sid : ids) {
            if (sid == null || sid <= 0) continue;
            try {
                int n = TicketSql.db().update(
                        "UPDATE " + TICKET
                                + " SET status='rejected', approve_at=NOW(), remark=? WHERE id=? AND status IN ('pending','pending_mid','pending_final')",
                        reason,
                        sid);
                if (n <= 0) continue;
                rejected++;
                Map<String, Object> sibling = TicketRowMaps.load(sid);
                if (sibling != null) {
                    notifyTicketResult(sibling, false, reason);
                }
                appendProgress(sid, "rejected", "system", reason);
            } catch (Exception e) {
                throw new IllegalStateException("库存耗尽后驳回同档待审失败", e);
            }
        }
        return rejected;
    }

    private static String subjectOf(Map<String, Object> ticket) {
        String subject = TicketSql.str(ticket.get("title"));
        if (subject.isBlank()) subject = TicketSql.str(ticket.get("bookTitle"));
        if (subject.isBlank()) subject = "单据#" + ticket.get("id");
        return subject;
    }

    /** 完结后评分 1～5；可选多维 dims（C-06）与匿名。 */
    public static Map<String, Object> rate(long ticketId, String username, int rating, String ratingRemark) {
        return rate(ticketId, username, rating, ratingRemark, null, false);
    }

    public static Map<String, Object> rate(
            long ticketId,
            String username,
            int rating,
            String ratingRemark,
            Map<String, Integer> dims,
            boolean anonymous) {
        if (!allowRating) throw new IllegalStateException("当前未开启评分");
        if (!hasColumn("rating")) throw new IllegalStateException("当前不支持评分");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!TicketSql.str(m.get("username")).equals(username)) {
            throw new IllegalStateException("只能评价自己的单据");
        }
        String st = String.valueOf(m.get("status"));
        boolean rateable = "returned".equals(st)
                || (approveEndsFlow && "approved".equals(st));
        if (!rateable) {
            throw new IllegalStateException(
                    approveEndsFlow
                            ? "仅已办结单据可评分"
                            : "仅「" + TicketCopy.stateLabel("returned", "已完结") + "」单据可评分");
        }
        Object prev = m.get("rating");
        boolean alreadyRated = prev != null && !"0".equals(String.valueOf(prev)) && !"".equals(String.valueOf(prev));
        boolean followPass = false;
        if (alreadyRated) {
            if (!allowFollowRate) {
                throw new IllegalStateException("已评价过，不可重复提交");
            }
            Object fr = m.get("followRated");
            boolean followed = fr != null && (
                    Boolean.TRUE.equals(fr)
                            || "1".equals(String.valueOf(fr))
                            || "true".equalsIgnoreCase(String.valueOf(fr)));
            if (followed) {
                throw new IllegalStateException("已追评过，不可重复提交");
            }
            followPass = true;
        }

        List<Map<String, String>> dimDefs = TicketCopy.RATING_DIMS;
        String dimsJson = "";
        int overall = rating;
        if (dimDefs != null && !dimDefs.isEmpty()) {
            if (dims == null || dims.isEmpty()) {
                throw new IllegalArgumentException("请完成各维度评分");
            }
            StringBuilder json = new StringBuilder("{");
            int sum = 0;
            int n = 0;
            for (Map<String, String> def : dimDefs) {
                String key = def.get("key");
                Integer v = dims.get(key);
                if (v == null) throw new IllegalArgumentException("请完成「" + def.get("label") + "」评分");
                if (v < 1 || v > 5) throw new IllegalArgumentException("「" + def.get("label") + "」须为 1～5 分");
                if (n > 0) json.append(",");
                json.append("\"").append(key.replace("\"", "")).append("\":").append(v);
                sum += v;
                n++;
            }
            json.append("}");
            dimsJson = json.toString();
            overall = Math.max(1, Math.min(5, (int) Math.round(sum / (double) n)));
        } else if (rating < 1 || rating > 5) {
            throw new IllegalArgumentException("评分须为 1～5 分");
        }

        String note = ratingRemark == null ? "" : ratingRemark.trim();
        if (note.length() > 255) note = note.substring(0, 255);
        if (requireLowRatingRemark && overall <= 2 && note.isBlank()) {
            throw new IllegalArgumentException("评分较低时请填写原因");
        }
        boolean anon = anonymous && TicketCopy.ALLOW_ANONYMOUS_RATING;
        if (dimDefs != null && !dimDefs.isEmpty() && !hasColumn("rating_dims_json")) {
            throw new IllegalStateException("系统未配置多维评分字段，无法提交评分");
        }
        if (hasColumn("rating_dims_json")) {
            TicketSql.db().update(
                    "UPDATE " + TICKET
                            + " SET rating=?, rating_remark=?, rated_at=NOW(), rating_dims_json=?, rating_anonymous=? WHERE id=?",
                    overall, note, dimsJson, anon ? 1 : 0, ticketId);
        } else {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET rating=?, rating_remark=?, rated_at=NOW() WHERE id=?",
                    overall, note, ticketId);
        }
        if (followPass && hasColumn("follow_rated")) {
            TicketSql.db().update("UPDATE " + TICKET + " SET follow_rated=1 WHERE id=?", ticketId);
        }
        String tip = (followPass ? "追评 " : "") + overall + " 分";
        if (!dimsJson.isBlank()) tip = tip + "（多维）";
        if (anon) tip = tip + " · 匿名";
        if (!note.isBlank()) tip = tip + " · " + note;
        appendProgress(ticketId, followPass ? "follow_rated" : "rated", username, tip);
        return get(ticketId);
    }

    /** 活动口令签到：本人 + approved + 码匹配 */
    public static Map<String, Object> checkin(long ticketId, String username, String code) {
        if (!allowCheckin) throw new IllegalStateException("当前未开启签到");
        if (!hasColumn("checked_in_at")) throw new IllegalStateException("当前不支持签到");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!TicketSql.str(m.get("username")).equals(username)) {
            throw new IllegalStateException("只能为自己的单据签到");
        }
        // 先推进爽约，避免活动已结束后仍可签到
        TicketStatusOps.touchTicketStatus(m);
        if (!"approved".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅已通过且未爽约的单据可签到");
        }
        Object prev = m.get("checkedInAt");
        if (prev != null && !String.valueOf(prev).isBlank()) {
            throw new IllegalStateException("已签到，不可重复");
        }
        long itemId = TicketSql.toLong(m.get("bookId"));
        if (itemId <= 0) itemId = TicketSql.toLong(m.get("itemId"));
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalStateException(TicketCopy.archiveNoun() + "不存在");
        String expect = TicketSql.str(item.get("checkinCode")).trim();
        if (expect.isBlank()) throw new IllegalStateException(TicketCopy.archiveNoun() + "尚未设置签到码");
        String got = code == null ? "" : code.trim();
        if (!expect.equalsIgnoreCase(got)) {
            throw new IllegalStateException("签到码不正确");
        }
        TicketSql.db().update(
                "UPDATE " + TICKET + " SET checked_in_at=NOW(), status='returned' WHERE id=?",
                ticketId);
        appendProgress(ticketId, "checkin", username, TicketCopy.CHECKIN_LABEL);
        return get(ticketId);
    }

    /** 审核结果写入申请人站内消息（无表或失败则静默跳过） */
    private static void notifyTicketResult(Map<String, Object> ticket, boolean pass, String note) {
        notifyTicketResult(ticket, pass, note, "");
    }

    private static void notifyTicketResult(Map<String, Object> ticket, boolean pass, String note, String passCode) {
        try {
            String user = TicketSql.str(ticket.get("username"));
            if (user.isBlank()) return;
            String subject = subjectOf(ticket);
            String noteText = note == null ? "" : note.trim();
            String noteSuffix = noteText.isBlank() ? "" : ("：" + noteText);
            String title = pass ? "审核已通过" : "审核未通过";
            String body = pass
                    ? ("「" + subject + "」已通过" + noteSuffix)
                    : ("「" + subject + "」已驳回" + noteSuffix);
            if (pass && hasColumn("pickup_at") && !bizPickupPlace.isBlank()) {
                body = body + "。请到「" + bizPickupPlace + "」领取，到场后由工作人员登记实发。";
            }
            String code = passCode == null ? "" : passCode.trim();
            if (pass && !code.isBlank()) {
                body = body + "。通行码：" + code + "（到访时出示即可）。";
            }
            java.util.Map<String, String> vars = new java.util.LinkedHashMap<>();
            vars.put("subject", subject);
            vars.put("note", noteText);
            vars.put("note_suffix", noteSuffix);
            vars.put("passCode", code);
            String tpl = pass ? "ticket_approved" : "ticket_rejected";
            MessageStore.sendWithTemplate(
                    user, tpl, vars, title, body, "ticket", TicketSql.toLong(ticket.get("id")));
        } catch (Exception ignored) {
            // 消息失败不影响主流程
        }
    }

    /** 领取登记后通知申请人地点与实发数量 */
    /** 驿站等到件：审核通过后站内信提醒申请人可取件 */
    private static void notifyArrivalIfNeeded(Map<String, Object> ticket) {
        if (!arrivalNotify || ticket == null) return;
        String user = TicketSql.str(ticket.get("username")).trim();
        if (user.isBlank()) return;
        String subj = subjectOf(ticket);
        String body = "「" + subj + "」已到站/可办理，请尽快取件或按指引办理。";
        try {
            MessageStore.send(user, "到件通知", body, "ticket", TicketSql.toLong(ticket.get("id")));
        } catch (Exception ignored) {
            // 站内信失败不影响审核
        }
    }

    private static void notifyPickup(Map<String, Object> ticket, String place, Integer actualQty) {
        try {
            String user = TicketSql.str(ticket.get("username"));
            if (user.isBlank()) return;
            String subject = subjectOf(ticket);
            String body = "「" + subject + "」已登记领取，地点：" + (place == null || place.isBlank() ? "—" : place);
            if (actualQty != null && actualQty > 0) {
                body = body + "，实发数量：" + actualQty;
            }
            MessageStore.send(user, "领取已登记", body, "ticket", TicketSql.toLong(ticket.get("id")));
        } catch (Exception ignored) {
            // 消息失败不影响主流程
        }
    }

    /**
     * 申请人撤销待审单据（pending / pending_mid / pending_final / waitlisted / held / hold_ready）。
     * held 未扣库存；hold_ready 须回补预扣库存。
     */
    public static Map<String, Object> withdraw(long ticketId, String username) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (username == null || username.isBlank()
                || !username.equals(String.valueOf(m.get("username")))) {
            throw new IllegalStateException("只能撤销自己的申请");
        }
        String st = String.valueOf(m.get("status"));
        if (!"pending".equals(st) && !"pending_mid".equals(st)
                && !"pending_final".equals(st) && !"waitlisted".equals(st)
                && !"held".equals(st) && !"hold_ready".equals(st)
                && !"verifying".equals(st)) {
            throw new IllegalStateException("仅待审核、候补或预约申请可撤销");
        }
        if (maxCancelHolds > 0 && ("held".equals(st) || "hold_ready".equals(st) || "waitlisted".equals(st))) {
            Integer n = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM " + TICKET + " WHERE username=? AND status='cancelled'",
                    Integer.class, username);
            if (n != null && n >= maxCancelHolds) {
                throw new IllegalStateException("预约/候补取消次数已达上限，暂不可再取消");
            }
        }
        long itemId = TicketSql.toLong(m.get("bookId"));
        if ("hold_ready".equals(st) && MODE == Mode.ARCHIVE && useQuota && itemId > 0
                && ArchiveStore.getItemRaw(itemId) != null) {
            ArchiveStore.adjustStock(itemId, rowQty(m));
        }
        TicketSql.db().update(
                "UPDATE " + TICKET + " SET status='cancelled'"
                        + (hasColumn("hold_expire_at") ? ", hold_expire_at=NULL" : "")
                        + " WHERE id=?",
                ticketId);
        String progNote = "held".equals(st) ? "用户取消预约"
                : ("hold_ready".equals(st) ? "用户放弃取书"
                : ("waitlisted".equals(st) ? "用户取消候补" : "用户撤销申请"));
        appendProgress(ticketId, "cancelled", username, progNote);
        if ("hold_ready".equals(st) && itemId > 0) {
            tryPromoteBookHold(itemId);
        }
        return get(ticketId);
    }

    /**
     * 名额回补后：按申请时间 FIFO 将最早候补单升为待审（不直接扣库存，审过才占名额）。
     */
    static void tryPromoteWaitlist(long itemId) {
        if (!allowWaitlist || MODE != Mode.ARCHIVE || !useQuota || itemId <= 0) {
            return;
        }
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) return;
        int stock = item.get("stock") instanceof Number n ? n.intValue() : 0;
        if (stock <= 0) return;
        Long wid = null;
        try {
            wid = TicketSql.db().queryForObject(
                    "SELECT id FROM " + TICKET
                            + " WHERE " + itemFkColumn() + "=? AND status='waitlisted'"
                            + " ORDER BY apply_at ASC, id ASC LIMIT 1",
                    Long.class, itemId);
        } catch (Exception ignored) {
            return;
        }
        if (wid == null || wid <= 0) return;
        Map<String, Object> w = TicketRowMaps.load(wid);
        if (w == null) return;
        int need = rowQty(w);
        if (stock < need) return;
        int n = TicketSql.db().update(
                "UPDATE " + TICKET + " SET status='pending' WHERE id=? AND status='waitlisted'",
                wid);
        if (n <= 0) return;
        appendProgress(wid, "pending", "system", "候补晋升：名额空出，转为待审");
        try {
            String user = TicketSql.str(w.get("username"));
            if (!user.isBlank()) {
                MessageStore.send(
                        user,
                        "候补已晋升",
                        "「" + subjectOf(w) + "」已有名额，候补已转为待审，请等待审核。",
                        "ticket",
                        wid);
            }
            notifyAdminsNewTicket(wid, user, subjectOf(get(wid)));
        } catch (Exception ignored) {
            // 通知失败不影响晋升
        }
    }

    /**
     * 还书入库后：FIFO 将最早预约单升为待取书并预扣库存；发到书站内信。
     */
    static void tryPromoteBookHold(long itemId) {
        if (!allowBookHold || MODE != Mode.ARCHIVE || !useQuota || itemId <= 0) {
            return;
        }
        if (!hasColumn("hold_expire_at")) {
            // 能力开了却缺过期列：禁止晋升成永不超时的 hold_ready
            return;
        }
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) return;
        int stock = item.get("stock") instanceof Number n ? n.intValue() : 0;
        if (stock <= 0) return;
        Long hid = null;
        try {
            hid = TicketSql.db().queryForObject(
                    "SELECT id FROM " + TICKET
                            + " WHERE " + itemFkColumn() + "=? AND status='held'"
                            + " ORDER BY apply_at ASC, id ASC LIMIT 1",
                    Long.class, itemId);
        } catch (Exception ignored) {
            return;
        }
        if (hid == null || hid <= 0) return;
        Map<String, Object> h = TicketRowMaps.load(hid);
        if (h == null) return;
        int need = rowQty(h);
        if (stock < need) return;
        ArchiveStore.adjustStock(itemId, -need);
        LocalDateTime expireAt = LocalDateTime.now().plusHours(holdHours);
        int n = TicketSql.db().update(
                "UPDATE " + TICKET + " SET status='hold_ready', hold_expire_at=? WHERE id=? AND status='held'",
                Timestamp.valueOf(expireAt), hid);
        if (n <= 0) {
            ArchiveStore.adjustStock(itemId, need);
            return;
        }
        appendProgress(hid, "hold_ready", "system",
                "到书通知：请于 " + TicketSql.fmt(Timestamp.valueOf(expireAt)) + " 前确认借阅");
        try {
            String user = TicketSql.str(h.get("username"));
            if (!user.isBlank()) {
                MessageStore.send(
                        user,
                        "到书通知",
                        "「" + subjectOf(h) + "」已到馆，请在 "
                                + TicketSql.fmt(Timestamp.valueOf(expireAt))
                                + " 前确认借阅；逾期将取消并顺延下一位。",
                        "ticket",
                        hid);
            }
        } catch (Exception ignored) {
            // 通知失败不影响晋升
        }
    }

    /** 超时未确认的待取书：取消、回补库存；顺延在调用方统一触发。 */
    static void expireBookHolds() {
        if (!allowBookHold || !hasColumn("hold_expire_at")) return;
        List<Long> ids;
        try {
            ids = TicketSql.db().query(
                    "SELECT id FROM " + TICKET
                            + " WHERE status='hold_ready' AND hold_expire_at IS NOT NULL"
                            + " AND hold_expire_at < NOW()",
                    (rs, i) -> rs.getLong("id"));
        } catch (Exception e) {
            return;
        }
        java.util.LinkedHashSet<Long> promoteItems = new java.util.LinkedHashSet<>();
        for (Long id : ids) {
            if (id == null || id <= 0) continue;
            Map<String, Object> m = TicketRowMaps.load(id);
            if (m == null || !"hold_ready".equals(String.valueOf(m.get("status")))) continue;
            long itemId = TicketSql.toLong(m.get("bookId"));
            int n = TicketSql.db().update(
                    "UPDATE " + TICKET + " SET status='cancelled', hold_expire_at=NULL"
                            + " WHERE id=? AND status='hold_ready'",
                    id);
            if (n <= 0) continue;
            if (MODE == Mode.ARCHIVE && useQuota && itemId > 0
                    && ArchiveStore.getItemRaw(itemId) != null) {
                ArchiveStore.adjustStock(itemId, rowQty(m));
            }
            appendProgress(id, "cancelled", "system", "预约取书超时自动取消");
            try {
                String user = TicketSql.str(m.get("username"));
                if (!user.isBlank()) {
                    MessageStore.send(
                            user,
                            "预约已超时",
                            "「" + subjectOf(m) + "」取书时限已过，预约已取消。",
                            "ticket",
                            id);
                }
            } catch (Exception ignored) {
            }
            if (itemId > 0) promoteItems.add(itemId);
        }
        for (Long itemId : promoteItems) {
            tryPromoteBookHold(itemId);
        }
    }

    /**
     * 申请人确认借阅（hold_ready → approved）；库存已在到书晋升时预扣。
     */
    public static Map<String, Object> claimHold(long ticketId, String username) {
        if (!allowBookHold) throw new IllegalStateException("当前未开启图书预约");
        expireBookHolds();
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (username == null || username.isBlank()
                || !username.equals(String.valueOf(m.get("username")))) {
            throw new IllegalStateException("只能确认本人的预约");
        }
        if (!"hold_ready".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅待取书状态可确认借阅");
        }
        return finalizeHoldReadyApprove(ticketId, m, "用户确认借阅", username, "", false);
    }

    /** hold_ready 通过：写 approved / due_at，不二次扣库存。 */
    private static Map<String, Object> finalizeHoldReadyApprove(
            long ticketId,
            Map<String, Object> m,
            String note,
            String op,
            String dispatchTo,
            boolean bind) {
        if (useDeadline && !hasColumn("due_at")) {
            throw new IllegalStateException("系统未配置应还日字段，无法审批通过");
        }
        LocalDateTime approveAt = LocalDateTime.now();
        LocalDateTime dueAt = approveAt.plusDays(loanDays());
        Object requested = m.get("dueAt");
        if (requested != null && !String.valueOf(requested).isBlank()) {
            try {
                dueAt = TicketSql.parseDateTimeFlexible(String.valueOf(requested).trim());
            } catch (RuntimeException e) {
                throw e;
            } catch (Exception e) {
                throw new IllegalStateException("应还日期无效", e);
            }
        }
        String handler = !dispatchTo.isBlank() ? dispatchTo : op;
        boolean bindHandler = bind && !handler.isBlank() && hasColumn("assignee_username");
        StringBuilder sql = new StringBuilder(
                "UPDATE " + TICKET + " SET status='approved', approve_at=?, remark=?");
        List<Object> args = new ArrayList<>();
        args.add(Timestamp.valueOf(approveAt));
        args.add(note == null ? "" : note);
        if (bindHandler) {
            sql.append(", assignee_username=?");
            args.add(handler);
        }
        if (useDeadline) {
            sql.append(", due_at=?");
            args.add(Timestamp.valueOf(dueAt));
        }
        if (hasColumn("fine_yuan")) {
            sql.append(", fine_yuan=0");
        }
        if (hasColumn("remind_msg")) {
            sql.append(", remind_msg=''");
        }
        if (hasColumn("hold_expire_at")) {
            sql.append(", hold_expire_at=NULL");
        }
        sql.append(" WHERE id=? AND status='hold_ready'");
        args.add(ticketId);
        int n = TicketSql.db().update(sql.toString(), args.toArray());
        if (n <= 0) throw new IllegalStateException("确认借阅失败，状态已变更");
        String passCode = issuePassCodeIfNeeded(ticketId);
        notifyTicketResult(m, true, note == null ? "" : note, passCode);
        appendProgress(ticketId, "approved", op,
                note == null || note.isBlank() ? "确认借阅" : note);
        long approvedItemId = TicketSql.toLong(m.get("bookId"));
        int autoRejected = 0;
        if (approvedItemId > 0) {
            autoRejected = rejectSiblingsWhenStockGone(approvedItemId, ticketId);
        }
        Map<String, Object> out = get(ticketId);
        if (out != null && autoRejected > 0) {
            out.put("autoRejectedSiblings", autoRejected);
        }
        return out;
    }

    public static Map<String, Object> complete(long ticketId) {
        return complete(ticketId, null, true);
    }

    /**
     * @param actorUid 操作者；申请人完结传本人且 asSuperOrOwner=true
     * @param asSuperOrOwner true=总管或单据申请人（不校验处理人）；false=子管须为 assignee
     */
    public static Map<String, Object> complete(long ticketId, String actorUid, boolean asSuperOrOwner) {
        return complete(ticketId, actorUid, asSuperOrOwner, null);
    }

    /**
     * @param returnAttachUrl 归还附件；requireReturnAttach 时必填
     */
    public static Map<String, Object> complete(
            long ticketId, String actorUid, boolean asSuperOrOwner, String returnAttachUrl) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!asSuperOrOwner && hasColumn("assignee_username")) {
            String asg = TicketSql.str(m.get("assigneeUsername"));
            if (!asg.isBlank() && (actorUid == null || !asg.equals(actorUid))) {
                throw new IllegalStateException("该单已绑定处理人，仅处理人或总管可完结");
            }
        }
        if (useDeadline) TicketStatusOps.refreshOverdue(m);
        String st = String.valueOf(m.get("status"));
        if (!List.of("approved", "overdue").contains(st)) {
            throw new IllegalStateException("仅进行中/逾期可完结");
        }
        // 驿站/失物等：审批即核销出库（approveEndsFlow + pickup 列），禁止再「取消取件」回补库存
        if (approveEndsFlow && hasColumn("pickup_at")
                && ("approved".equals(st) || "overdue".equals(st))) {
            throw new IllegalStateException("已核销办结，不可取消取件");
        }
        String retAttach = returnAttachUrl == null ? "" : returnAttachUrl.trim();
        if (requireReturnAttach) {
            if (retAttach.isBlank()) {
                throw new IllegalStateException("归还请上传设备照片后再完结");
            }
            if (!hasColumn("attach_url")) {
                throw new IllegalStateException("系统未配置附件字段，无法保存归还照片");
            }
            if (retAttach.length() > 255) retAttach = retAttach.substring(0, 255);
        }
        if (requireCloseAttach) {
            String closeUrl = TicketSql.str(m.get("closeAttachUrl")).trim();
            if (closeUrl.isBlank() && !retAttach.isBlank()) closeUrl = retAttach;
            if (closeUrl.isBlank()) {
                throw new IllegalStateException("请上传结案报告附件后再办结");
            }
        }
        if (requireFaultReason) {
            String fr = TicketSql.str(m.get("faultReason")).trim();
            if (fr.isBlank()) {
                throw new IllegalStateException("请选择故障原因后再办结");
            }
        }
        if (requireCloseSummary) {
            String cs = TicketSql.str(m.get("closeSummary")).trim();
            if (cs.isBlank()) {
                throw new IllegalStateException("请填写处理过程摘要后再办结");
            }
        }
        if (allowPartsNote && hasColumn("parts_note")) {
            String pn = TicketSql.str(m.get("partsNote")).trim();
            if (pn.isBlank()) {
                // 浅警告：记入进度但不阻断（答辩可讲「提醒核对耗材」）
                appendProgress(ticketId, st, actorUid == null ? "" : actorUid, "结单提示：未登记备件/耗材出库");
            }
        }
        if (requireReturnDate) {
            String rd = TicketSql.str(m.get("returnDate")).trim();
            if (rd.isBlank()) {
                throw new IllegalStateException("请填写返岗日期后再销假");
            }
        }
        if (requireFeedbackSet) {
            if (TicketSql.str(m.get("feedbackInterest")).isBlank()
                    || TicketSql.str(m.get("feedbackConcern")).isBlank()
                    || TicketSql.str(m.get("feedbackNext")).isBlank()) {
                throw new IllegalStateException("请填写带看反馈后再办结");
            }
        }
        if (requireAppraisal) {
            if (TicketSql.str(m.get("appraisalComment")).isBlank()
                    || TicketSql.str(m.get("appraisalGrade")).isBlank()) {
                throw new IllegalStateException("请填写实习鉴定评语与等级后再办结");
            }
        }
        if (MODE == Mode.ARCHIVE && useQuota) {
            long itemId = TicketSql.toLong(m.get("bookId"));
            if (ArchiveStore.getItemRaw(itemId) != null) {
                // 已登记实发则按实发回补；少发差额已在领取时回库
                int restore = rowQty(m);
                Object aq = m.get("actualQty");
                if (aq instanceof Number n && n.intValue() > 0) {
                    restore = n.intValue();
                }
                ArchiveStore.adjustStock(itemId, restore);
                tryPromoteWaitlist(itemId);
                tryPromoteBookHold(itemId);
            }
        }
        String remind = "";
        if (useDeadline) {
            String doneLab = TicketCopy.stateLabel("returned", TicketCopy.verbLabel("return", "已完结"));
            remind = TicketSql.toDouble(m.get("fineYuan")) > 0
                    ? doneLab + "，请按登记费用缴纳 " + m.get("fineYuan") + " 元。"
                    : String.valueOf(m.get("remindMsg") == null ? "" : m.get("remindMsg"));
        }
        StringBuilder sql = new StringBuilder("UPDATE " + TICKET + " SET status='returned', return_at=NOW()");
        java.util.ArrayList<Object> args = new java.util.ArrayList<>();
        if (hasColumn("remind_msg")) {
            sql.append(", remind_msg=?");
            args.add(remind);
        }
        if (requireReturnAttach && hasColumn("attach_url") && !retAttach.isBlank()) {
            sql.append(", attach_url=?");
            args.add(retAttach);
        }
        sql.append(" WHERE id=?");
        args.add(ticketId);
        TicketSql.db().update(sql.toString(), args.toArray());
        try {
            BalanceLedgerStore.creditForTicketReturn(m);
        } catch (Exception ignored) {
        }
        appendProgress(ticketId, "returned", actorUid, TicketCopy.stateLabel("returned", TicketCopy.verbLabel("return", "已完结")));
        return get(ticketId);
    }

    /** 借出中/逾期 → 丢失申报；库存不回补 */
    public static Map<String, Object> reportLost(long ticketId, String username) {
        if (!allowBookLost) throw new IllegalStateException("当前未开启丢失申报");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String owner = TicketSql.str(m.get("username"));
        if (username == null || username.isBlank() || !username.equals(owner)) {
            throw new IllegalStateException("只能申报本人的单据");
        }
        if (useDeadline) TicketStatusOps.refreshOverdue(m);
        String st = String.valueOf(m.get("status"));
        if (!List.of("approved", "overdue").contains(st)) {
            throw new IllegalStateException("仅借出中或逾期可申报丢失");
        }
        TicketSql.db().update("UPDATE " + TICKET + " SET status='lost' WHERE id=?", ticketId);
        appendProgress(ticketId, "lost", username, TicketCopy.stateLabel("lost", "丢失申报"));
        return get(ticketId);
    }

    /** 丢失申报 → 赔偿完成（馆员）；库存仍不回补 */
    public static Map<String, Object> markCompensated(long ticketId, String operator) {
        if (!allowBookLost) throw new IllegalStateException("当前未开启丢失赔偿");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!"lost".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅丢失申报状态可登记赔偿完成");
        }
        TicketSql.db().update("UPDATE " + TICKET + " SET status='compensated' WHERE id=?", ticketId);
        appendProgress(
                ticketId,
                "compensated",
                operator == null ? "" : operator,
                TicketCopy.stateLabel("compensated", "赔偿完成"));
        return get(ticketId);
    }

    /**
     * 用户催办：处理中/逾期可催；未超时也可记一笔。冷却防刷；评后可锁催。
     * 站内信通知处理人/管理员，≠短信外呼。
     */
    public static Map<String, Object> userUrge(long ticketId, String username) {
        if (!allowUserUrge) throw new IllegalStateException("当前未开启用户催办");
        if (!hasColumn("urge_at") && !hasColumn("urge_count")) {
            throw new IllegalStateException("系统未配置催办字段");
        }
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!TicketSql.str(m.get("username")).equals(username)) {
            throw new IllegalStateException("只能催办自己的单据");
        }
        String st = String.valueOf(m.get("status"));
        if (!List.of("approved", "overdue", "paused").contains(st)) {
            throw new IllegalStateException("仅处理中/逾期/挂起单据可催办");
        }
        if (lockUrgeAfterRate) {
            Object rating = m.get("rating");
            if (rating != null && !"0".equals(String.valueOf(rating)) && !"".equals(String.valueOf(rating))) {
                throw new IllegalStateException("已评价单据不可再催办");
            }
        }
        if (urgeCooldownMinutes > 0 && hasColumn("urge_at")) {
            Object last = m.get("urgeAt");
            if (last != null && !String.valueOf(last).isBlank()) {
                try {
                    LocalDateTime at = LocalDateTime.parse(String.valueOf(last), TicketSql.FMT);
                    if (at.plusMinutes(urgeCooldownMinutes).isAfter(LocalDateTime.now())) {
                        throw new IllegalStateException("催办过于频繁，请稍后再试");
                    }
                } catch (IllegalStateException e) {
                    throw e;
                } catch (Exception ignored) {
                }
            }
        }
        int count = 0;
        Object uc = m.get("urgeCount");
        if (uc instanceof Number n) count = n.intValue();
        count++;
        StringBuilder sql = new StringBuilder("UPDATE " + TICKET + " SET ");
        List<Object> args = new ArrayList<>();
        boolean first = true;
        if (hasColumn("urge_at")) {
            sql.append("urge_at=NOW()");
            first = false;
        }
        if (hasColumn("urge_count")) {
            if (!first) sql.append(", ");
            sql.append("urge_count=?");
            args.add(count);
            first = false;
        }
        if (hasColumn("urge_cancelled")) {
            if (!first) sql.append(", ");
            sql.append("urge_cancelled=0");
        }
        sql.append(" WHERE id=?");
        args.add(ticketId);
        TicketSql.db().update(sql.toString(), args.toArray());
        appendProgress(ticketId, "urged", username, "用户催办（第 " + count + " 次）");
        try {
            String title = subjectOf(m);
            String body = "【催办】用户对「" + title + "」发起催办，请尽快处理。";
            String asg = TicketSql.str(m.get("assigneeUsername"));
            if (!asg.isBlank()) {
                MessageStore.send(asg, "报修催办", body, "ticket", ticketId);
            } else {
                MessageStore.notifyAdmins("报修催办", body, "ticket", ticketId);
            }
        } catch (Exception ignored) {
        }
        return get(ticketId);
    }

    /** 用户撤销催办（浅：标记撤催并记流水）。 */
    public static Map<String, Object> cancelUrge(long ticketId, String username) {
        if (!allowCancelUrge) throw new IllegalStateException("当前未开启撤销催办");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!TicketSql.str(m.get("username")).equals(username)) {
            throw new IllegalStateException("只能操作自己的单据");
        }
        Object uc = m.get("urgeCount");
        int count = uc instanceof Number n ? n.intValue() : 0;
        if (count <= 0) throw new IllegalStateException("当前没有催办记录");
        if (hasColumn("urge_cancelled")) {
            TicketSql.db().update("UPDATE " + TICKET + " SET urge_cancelled=1 WHERE id=?", ticketId);
        }
        appendProgress(ticketId, "urge_cancelled", username, "用户撤销催办");
        return get(ticketId);
    }

    /** 挂起工单（处理中 → paused）。 */
    public static Map<String, Object> holdTicket(long ticketId, String operator, String reason) {
        if (!allowHoldResume) throw new IllegalStateException("当前未开启挂起");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String st = String.valueOf(m.get("status"));
        if (!"approved".equals(st) && !"overdue".equals(st)) {
            throw new IllegalStateException("仅处理中/逾期可挂起");
        }
        String note = reason == null ? "" : reason.trim();
        if (note.isBlank()) throw new IllegalArgumentException("请填写挂起原因");
        if (note.length() > 255) note = note.substring(0, 255);
        if (hasColumn("hold_reason")) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET status='paused', hold_reason=? WHERE id=?", note, ticketId);
        } else {
            TicketSql.db().update("UPDATE " + TICKET + " SET status='paused' WHERE id=?", ticketId);
        }
        appendProgress(ticketId, "paused", operator == null ? "" : operator, "挂起：" + note);
        return get(ticketId);
    }

    /** 恢复挂起（paused → approved）。 */
    public static Map<String, Object> resumeTicket(long ticketId, String operator) {
        if (!allowHoldResume) throw new IllegalStateException("当前未开启挂起恢复");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!"paused".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅挂起单据可恢复");
        }
        TicketSql.db().update("UPDATE " + TICKET + " SET status='approved' WHERE id=?", ticketId);
        appendProgress(ticketId, "approved", operator == null ? "" : operator, "恢复处理");
        return get(ticketId);
    }

    /** 转派：改处理人并写进度流水。 */
    public static Map<String, Object> reassign(
            long ticketId, String newAssignee, String operator, String remark) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!hasColumn("assignee_username")) {
            throw new IllegalStateException("系统未配置处理人字段");
        }
        String st = String.valueOf(m.get("status"));
        if (!List.of("approved", "overdue", "paused", "pending", "pending_final", "pending_mid")
                .contains(st)) {
            throw new IllegalStateException("当前状态不可转派");
        }
        String to = newAssignee == null ? "" : newAssignee.trim();
        if (to.isBlank()) throw new IllegalArgumentException("请选择转派对象");
        String from = TicketSql.str(m.get("assigneeUsername"));
        TicketSql.db().update("UPDATE " + TICKET + " SET assignee_username=? WHERE id=?", to, ticketId);
        String note = remark == null || remark.isBlank()
                ? ("转派：" + (from.isBlank() ? "未派" : from) + " → " + to)
                : remark.trim();
        appendProgress(ticketId, "reassigned", operator == null ? "" : operator, note);
        try {
            MessageStore.send(to, "工单转派", "「" + subjectOf(m) + "」已转派给你，请尽快处理。", "ticket", ticketId);
        } catch (Exception ignored) {
        }
        return get(ticketId);
    }

    /** 已派单后用户取消（须理由）。 */
    public static Map<String, Object> cancelDispatched(long ticketId, String username, String reason) {
        if (!allowCancelDispatched) throw new IllegalStateException("当前未开启取消已派单");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!TicketSql.str(m.get("username")).equals(username)) {
            throw new IllegalStateException("只能取消自己的单据");
        }
        String st = String.valueOf(m.get("status"));
        if (!"approved".equals(st) && !"overdue".equals(st) && !"paused".equals(st)) {
            throw new IllegalStateException("仅处理中单据可取消，未派单请用撤销");
        }
        String note = reason == null ? "" : reason.trim();
        if (note.isBlank()) throw new IllegalArgumentException("请填写取消原因");
        if (note.length() > 255) note = note.substring(0, 255);
        TicketSql.db().update(
                "UPDATE " + TICKET + " SET status='cancelled', remark=? WHERE id=?", note, ticketId);
        appendProgress(ticketId, "cancelled", username, "用户取消已派单：" + note);
        return get(ticketId);
    }

    /** 维修员拒单：回池待受理 + 原因。 */
    public static Map<String, Object> rejectAssignment(long ticketId, String operator, String reason) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String st = String.valueOf(m.get("status"));
        if (!"approved".equals(st) && !"overdue".equals(st) && !"paused".equals(st)) {
            throw new IllegalStateException("仅处理中单据可拒单");
        }
        String note = reason == null ? "" : reason.trim();
        if (note.isBlank()) throw new IllegalArgumentException("请填写拒单原因");
        if (note.length() > 255) note = note.substring(0, 255);
        StringBuilder sql = new StringBuilder("UPDATE " + TICKET + " SET status='pending'");
        if (hasColumn("assignee_username")) sql.append(", assignee_username=''");
        if (hasColumn("due_at")) sql.append(", due_at=NULL");
        if (hasColumn("response_due_at")) sql.append(", response_due_at=NULL");
        sql.append(", remark=? WHERE id=?");
        TicketSql.db().update(sql.toString(), note, ticketId);
        appendProgress(ticketId, "pending", operator == null ? "" : operator, "拒单回池：" + note);
        return get(ticketId);
    }

    /** 报价确认（用户）。 */
    public static Map<String, Object> confirmQuote(long ticketId, String username, boolean payMaterial) {
        if (!allowQuote) throw new IllegalStateException("当前未开启维修报价");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!TicketSql.str(m.get("username")).equals(username)) {
            throw new IllegalStateException("只能确认自己的单据报价");
        }
        if (!hasColumn("quote_confirmed")) throw new IllegalStateException("系统未配置报价字段");
        StringBuilder sql = new StringBuilder("UPDATE " + TICKET + " SET quote_confirmed=1");
        if (payMaterial && hasColumn("material_paid")) sql.append(", material_paid=1");
        sql.append(" WHERE id=?");
        TicketSql.db().update(sql.toString(), ticketId);
        appendProgress(ticketId, "quote_confirmed", username,
                payMaterial ? "用户确认报价并登记材料费" : "用户确认报价");
        return get(ticketId);
    }

    public static Map<String, Object> markOverdue(long ticketId) {
        if (!useDeadline) throw new IllegalStateException("当前不支持到期催办");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!"approved".equals(m.get("status")) && !"overdue".equals(m.get("status"))) {
            throw new IllegalStateException("仅进行中/逾期可标记");
        }
        m.put("status", "overdue");
        TicketStatusOps.applyFineAndRemind(m, false);
        TicketStatusOps.persistFine(m);
        TicketStatusOps.markEverOverdue(m);
        return get(ticketId);
    }

    public static Map<String, Object> remind(long ticketId) {
        if (!useDeadline) throw new IllegalStateException("当前不支持到期催办");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        TicketStatusOps.refreshOverdue(m);
        String st = String.valueOf(m.get("status"));
        if (!List.of("approved", "overdue").contains(st)) {
            throw new IllegalStateException("仅进行中/逾期可催办");
        }
        TicketStatusOps.applyFineAndRemind(m, true);
        TicketStatusOps.persistFine(m);
        try {
            String owner = TicketSql.str(m.get("username"));
            if (!owner.isBlank()) {
                String title = TicketSql.str(m.get("title"));
                if (title.isBlank()) title = TicketSql.str(m.get("bookTitle"));
                if (title.isBlank()) title = "单据#" + ticketId;
                String dueLab = "应还日";
                Object due = m.get("dueAt");
                String dueTxt = due == null ? "" : String.valueOf(due);
                String body = "【催办】「" + title + "」请尽快处理"
                        + (dueTxt.isBlank() ? "。" : "，" + dueLab + "：" + dueTxt + "。");
                Object fine = m.get("fineYuan");
                if (fine instanceof Number n && n.doubleValue() > 0) {
                    body += "预估费用 " + n.doubleValue() + " 元。";
                }
                MessageStore.send(owner, "催办提醒", body, "ticket", ticketId);
            }
        } catch (Exception ignored) {
        }
        return get(ticketId);
    }

    /** 超期达上限则拒绝新申请（开题挂 maxOverdueTimes 时）。 */
    static void assertNotOverdueFrozen(String username) {
        BorrowCreditStore.assertCanBorrow(username);
        if (maxOverdueTimes <= 0 || username == null || username.isBlank()) return;
        if (!hasColumn("ever_overdue")) return;
        Integer n = TicketSql.db().queryForObject(
                "SELECT COUNT(*) FROM " + TICKET + " WHERE username=? AND ever_overdue=1",
                Integer.class,
                username.trim());
        int used = n == null ? 0 : n;
        if (used >= maxOverdueTimes) {
            throw new IllegalStateException(
                    "超期已达 " + maxOverdueTimes + " 次，暂不可再借，请先处理逾期单据");
        }
    }

    /**
     * 续借：延长应还日。须启用 loan_renew；仅借出中/逾期可续，受 maxRenew 限制。
     */
    public static Map<String, Object> renew(long ticketId, String username) {
        if (!allowRenew) throw new IllegalStateException("当前未开启续借");
        if (!useDeadline || !hasColumn("due_at")) {
            throw new IllegalStateException("当前单据无应还日，无法续借");
        }
        if (!hasColumn("renew_count")) {
            throw new IllegalStateException("系统未配置续借次数字段，无法续借");
        }
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String owner = TicketSql.str(m.get("username"));
        if (username == null || username.isBlank() || !username.equals(owner)) {
            throw new IllegalStateException("只能续借本人的单据");
        }
        TicketStatusOps.refreshOverdue(m);
        String st = String.valueOf(m.get("status"));
        if (!List.of("approved", "overdue").contains(st)) {
            throw new IllegalStateException("仅借出中或逾期可续借");
        }
        int used = 0;
        Object rc = m.get("renewCount");
        if (rc instanceof Number) used = ((Number) rc).intValue();
        else if (rc != null && !String.valueOf(rc).isBlank()) {
            try {
                used = Integer.parseInt(String.valueOf(rc).trim());
            } catch (NumberFormatException e) {
                throw new IllegalStateException("续借次数数据异常，无法续借", e);
            }
        }
        if (used >= maxRenew) {
            throw new IllegalStateException("已达续借次数上限（" + maxRenew + " 次）");
        }
        long itemId = TicketSql.toLong(m.get("bookId"));
        if (itemId <= 0) itemId = TicketSql.toLong(m.get("itemId"));
        if (renewBlockIfHeld && itemId > 0) {
            Integer holds = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM " + TICKET
                            + " WHERE " + itemFkColumn() + "=? AND status IN ('held','hold_ready')"
                            + " AND username<>?",
                    Integer.class, itemId, username);
            if (holds != null && holds > 0) {
                throw new IllegalStateException("该书另有读者预约，暂不可续借");
            }
        }
        LocalDateTime due = null;
        Object dueObj = m.get("dueAt");
        if (dueObj instanceof LocalDateTime) {
            due = (LocalDateTime) dueObj;
        } else if (dueObj != null && !String.valueOf(dueObj).isBlank()) {
            due = TicketSql.parseDateTimeFlexible(String.valueOf(dueObj).trim());
        }
        if (due == null) {
            due = LocalDateTime.now();
        }
        // 已过期则从当前时间起算，避免续到过去
        LocalDateTime base = due.isBefore(LocalDateTime.now()) ? LocalDateTime.now() : due;
        int days = renewDays > 0 ? renewDays : loanDays();
        LocalDateTime newDue = base.plusDays(days);
        int nextCount = used + 1;
        StringBuilder sql = new StringBuilder(
                "UPDATE " + TICKET + " SET due_at=?, status='approved', renew_count=?");
        List<Object> args = new ArrayList<>();
        args.add(Timestamp.valueOf(newDue));
        args.add(nextCount);
        if (hasColumn("fine_yuan")) {
            sql.append(", fine_yuan=0");
        }
        if (hasColumn("remind_msg")) {
            sql.append(", remind_msg=''");
        }
        sql.append(" WHERE id=?");
        args.add(ticketId);
        TicketSql.db().update(sql.toString(), args.toArray());
        appendProgress(
                ticketId, "approved", username, "续借第" + nextCount + "次，应还日延至 " + TicketSql.fmt(newDue));
        try {
            String title = TicketSql.str(m.get("title"));
            if (title.isBlank()) title = TicketSql.str(m.get("bookTitle"));
            if (title.isBlank()) title = "单据#" + ticketId;
            MessageStore.send(
                    owner,
                    "续借成功",
                    "「" + title + "」已续借，新应还日：" + TicketSql.fmt(newDue) + "（第 " + nextCount + "/" + maxRenew + " 次）",
                    "ticket",
                    ticketId);
        } catch (Exception ignored) {
        }
        return get(ticketId);
    }

    public static Map<String, Object> page(String username, String status, int page, int size) {
        return page(username, status, page, size, null, true, null, null);
    }

    public static Map<String, Object> page(
            String username, String status, int page, int size, String adminUid, boolean superAdmin) {
        return page(username, status, page, size, adminUid, superAdmin, null, null);
    }

    public static Map<String, Object> page(
            String username,
            String status,
            int page,
            int size,
            String adminUid,
            boolean superAdmin,
            Boolean ratedOnly) {
        return page(username, status, page, size, adminUid, superAdmin, ratedOnly, null);
    }

    /**
     * @param username 业务用户视角：只看自己的单；管理员传 null
     * @param adminUid 子管用户名；总管配合 superAdmin=true 看全部
     * @param superAdmin 总管看全部；子管：待办池 + 自己绑定的进行中 + 全体终态（取消/驳回等）
     * @param ratedOnly true 时仅返回已评分单据（管理端查看评价）
     * @param todayAssigned true 且 todayBoard 开：仅本人当日受理/处理中的单
     */
    public static Map<String, Object> page(
            String username,
            String status,
            int page,
            int size,
            String adminUid,
            boolean superAdmin,
            Boolean ratedOnly,
            Boolean todayAssigned) {
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        expireBookHolds();
        if (username != null && !username.isBlank()) {
            maybeNotifyWeekReports(username);
        }
        if (useDeadline) {
            List<Map<String, Object>> open = TicketSql.db().query(
                    "SELECT * FROM " + TICKET + " WHERE status IN ('approved','overdue')",
                    (rs, i) -> TicketRowMaps.mapRow(rs));
            for (Map<String, Object> b : open) TicketStatusOps.refreshOverdue(b);
        }

        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        if (username != null && !username.isBlank()) {
            where.append(" AND username=?");
            args.add(username);
        } else if (!superAdmin && adminUid != null && !adminUid.isBlank() && hasColumn("assignee_username")) {
            // 子管可见范围：
            // - 待办池 pending/pending_mid/pending_final：全员可见（抢单）
            // - 进行中 approved/overdue 等：仅自己绑定
            // - 终态 returned/rejected/noshow：全员可读（含用户「取消报名」）
            boolean historyStatus = isHistoryStatus(status);
            boolean todoPool = status == null || status.isBlank()
                    || "pending".equals(status)
                    || "pending_mid".equals(status)
                    || "pending_final".equals(status)
                    || "todo".equals(status);
            if (historyStatus) {
                // 筛终态：不加处理人条件
            } else if (todoPool) {
                if (status == null || status.isBlank()) {
                    where.append(
                            " AND (status IN ('pending','pending_mid','pending_final','returned','rejected','noshow')"
                                    + " OR assignee_username=?)");
                    args.add(adminUid);
                }
            } else {
                where.append(" AND assignee_username=?");
                args.add(adminUid);
            }
        }
        if (status != null && !status.isBlank()) {
            if ("todo".equals(status)) {
                where.append(" AND status IN ('pending','pending_mid','pending_final','hold_ready','verifying')");
            } else if ("stale".equals(status) && staleFollowDays > 0 && hasColumn("next_follow_at")) {
                // 未跟进 N 天：无下次跟进或已过期 N 天以上的未结单
                where.append(" AND status IN ('pending','pending_mid','pending_final','approved','overdue','paused')")
                        .append(" AND (next_follow_at IS NULL OR next_follow_at <= ?)");
                args.add(Timestamp.valueOf(LocalDateTime.now().minusDays(staleFollowDays)));
            } else {
                where.append(" AND status=?");
                args.add(status);
            }
        }
        if (Boolean.TRUE.equals(ratedOnly) && hasColumn("rating")) {
            where.append(" AND rating IS NOT NULL AND rating > 0");
        }
        if (Boolean.TRUE.equals(todayAssigned) && todayBoard && hasColumn("assignee_username")) {
            String who = adminUid != null && !adminUid.isBlank() ? adminUid : username;
            if (who != null && !who.isBlank()) {
                where.append(" AND assignee_username=? AND status IN ('approved','overdue','paused')");
                args.add(who);
                if (hasColumn("approve_at")) {
                    where.append(" AND approve_at IS NOT NULL AND DATE(approve_at)=CURDATE()");
                }
            }
        }
        Integer total = TicketSql.db().queryForObject("SELECT COUNT(*) FROM " + TICKET + where, Integer.class, args.toArray());
        int t = total == null ? 0 : total;
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = TicketSql.db().query(
                "SELECT * FROM " + TICKET + where + " ORDER BY "
                        + (hasColumn("priority")
                        ? "CASE WHEN priority IN ('紧急','高') THEN 0 ELSE 1 END, id DESC"
                        : "id DESC")
                        + " LIMIT ? OFFSET ?",
                (rs, i) -> TicketStatusOps.enrich(TicketRowMaps.mapRow(rs)), args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        out.put("staleFollowDays", staleFollowDays);
        out.put("levelSlaDays", levelSlaCsv());
        out.put("dutyNotify", dutyNotify);
        return out;
    }

    /**
     * 内容举报下架：将回帖/单据标为 rejected，从前台楼层消失。
     * 待审走驳回；已通过直接改状态（不走审批状态机）。
     */
    public static void hideForReport(long ticketId, String note) {
        if (!enabled || ticketId <= 0) return;
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String st = String.valueOf(m.get("status"));
        String reason = note == null || note.isBlank() ? "举报下架" : note.trim();
        if ("pending".equals(st) || "pending_mid".equals(st) || "pending_final".equals(st)) {
            approve(ticketId, false, reason);
            return;
        }
        if ("approved".equals(st)) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET status='rejected', approve_at=NOW(), remark=? WHERE id=?",
                    reason, ticketId);
            appendProgress(ticketId, "rejected", "system", reason);
            return;
        }
        appendProgress(ticketId, st, "system", "举报已记录：" + reason);
    }

    /**
     * 公开楼层：某档案下已通过的单据（论坛回复等），访客可读。
     * 仅返回 approved；不含待审/驳回。
     */
    public static Map<String, Object> listPublicByItem(long itemId, int page, int size) {
        if (!enabled || MODE != Mode.ARCHIVE) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("list", List.of());
            empty.put("total", 0);
            empty.put("page", Math.max(1, page));
            empty.put("size", Math.max(1, size));
            return empty;
        }
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        if (size > 50) size = 50;
        Integer total = TicketSql.db().queryForObject(
                "SELECT COUNT(*) FROM " + TICKET + " WHERE " + itemFkColumn() + "=? AND status='approved'",
                Integer.class, itemId);
        int t = total == null ? 0 : total;
        List<Map<String, Object>> list = TicketSql.db().query(
                "SELECT * FROM " + TICKET
                        + " WHERE " + itemFkColumn() + "=? AND status='approved' ORDER BY id ASC LIMIT ? OFFSET ?",
                (rs, i) -> TicketStatusOps.enrich(TicketRowMaps.mapRow(rs)),
                itemId, size, (page - 1) * size);
        // 公开楼层不暴露内部字段
        if (list != null) {
            for (Map<String, Object> row : list) {
                row.remove("assigneeUsername");
                row.remove("fineYuan");
                row.remove("remindMsg");
                row.remove("attachUrl");
            }
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list == null ? List.of() : list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    /** 终态：全体子管可读（不按处理人隔离） */
    public static boolean isHistoryStatus(String status) {
        return "returned".equals(status)
                || "rejected".equals(status)
                || "cancelled".equals(status)
                || "noshow".equals(status)
                || "lost".equals(status)
                || "compensated".equals(status);
    }

    public static boolean isTodoPoolStatus(String status) {
        return "pending".equals(status) || "pending_mid".equals(status)
                || "pending_final".equals(status) || "todo".equals(status);
    }

    public static Map<String, Object> get(long id) {
        Map<String, Object> m = TicketRowMaps.load(id);
        if (m == null) return null;
        TicketStatusOps.touchTicketStatus(m);
        return TicketStatusOps.enrich(TicketRowMaps.load(id));
    }

    static boolean hasColumn(String col) {
        try {
            Integer n = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=? AND COLUMN_NAME=?",
                    Integer.class, TICKET, col);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    static void ensureL1Columns() {
        // no-op：单据扩展列随本系统 schema 建表，禁止运行时补审级超集
    }

    /** CRM 等：申请后补写可选列 */
    public static void patchTicketExtras(long ticketId, Map<String, Object> body) {
        if (ticketId <= 0 || body == null || body.isEmpty()) return;
        if (body.containsKey("contactChannel")) {
            if (!hasColumn("contact_channel")) {
                throw new IllegalStateException("系统未配置联系渠道字段");
            }
            String ch = TicketSql.str(body.get("contactChannel")).trim();
            if (ch.length() > 32) ch = ch.substring(0, 32);
            TicketSql.db().update("UPDATE " + TICKET + " SET contact_channel=? WHERE id=?", ch, ticketId);
        }
        if (body.containsKey("weekNo")) {
            if (!hasColumn("week_no")) {
                throw new IllegalStateException("系统未配置周次字段");
            }
            String rawWeek = TicketSql.str(body.get("weekNo")).trim();
            int weekNo;
            try {
                weekNo = Integer.parseInt(rawWeek);
            } catch (NumberFormatException e) {
                throw new IllegalStateException("周次须为数字");
            }
            if (weekNo < 1 || weekNo > 60) throw new IllegalStateException("周次须在 1 到 60 之间");
            TicketSql.db().update("UPDATE " + TICKET + " SET week_no=? WHERE id=?", weekNo, ticketId);
        }
        if (body.containsKey("interviewPlace")) {
            if (!hasColumn("interview_place")) {
                throw new IllegalStateException("系统未配置面试地点字段");
            }
            String place = TicketSql.str(body.get("interviewPlace")).trim();
            if (place.length() > 128) place = place.substring(0, 128);
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET interview_place=? WHERE id=?", place, ticketId);
        }
        if (body.containsKey("nextFollowAt")) {
            if (!hasColumn("next_follow_at")) {
                throw new IllegalStateException("系统未配置下次跟进字段");
            }
            Timestamp ts = null;
            Object raw = body.get("nextFollowAt");
            if (raw != null && !String.valueOf(raw).isBlank()) {
                try {
                    ts = Timestamp.valueOf(TicketSql.parseDateTimeFlexible(String.valueOf(raw).trim(), false));
                } catch (RuntimeException e) {
                    throw e instanceof IllegalStateException
                            ? e
                            : new IllegalStateException("下次跟进时间无效", e);
                } catch (Exception e) {
                    throw new IllegalStateException("下次跟进时间无效", e);
                }
            }
            TicketSql.db().update("UPDATE " + TICKET + " SET next_follow_at=? WHERE id=?", ts, ticketId);
        }
        // 报销等：提交时写入金额（复用 fine_yuan；借阅罚金/SLA 到期不计此路径）
        if (!useDeadline && (body.containsKey("fineYuan") || body.containsKey("amountYuan"))) {
            if (!hasColumn("fine_yuan")) {
                throw new IllegalStateException("系统未配置金额字段");
            }
            Object raw = body.containsKey("fineYuan") ? body.get("fineYuan") : body.get("amountYuan");
            double amt = TicketSql.toDouble(raw);
            if (amt < 0) amt = 0;
            if (amt > 99999999) amt = 99999999;
            TicketSql.db().update("UPDATE " + TICKET + " SET fine_yuan=? WHERE id=?", amt, ticketId);
        }
        if (allowProxyPickup || body.containsKey("proxyName") || body.containsKey("proxyPhone")) {
            if (body.containsKey("proxyName") || body.containsKey("proxyPhone")) {
                if (!hasColumn("proxy_name") || !hasColumn("proxy_phone")) {
                    throw new IllegalStateException("系统未配置代取人字段");
                }
                String pn = TicketSql.str(body.get("proxyName")).trim();
                String pp = TicketSql.str(body.get("proxyPhone")).trim();
                if (pn.length() > 64) pn = pn.substring(0, 64);
                if (pp.length() > 20) pp = pp.substring(0, 20);
                TicketSql.db().update(
                        "UPDATE " + TICKET + " SET proxy_name=?, proxy_phone=? WHERE id=?", pn, pp, ticketId);
            }
        }
        if (body.containsKey("noticeAck") && hasColumn("notice_ack")) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET notice_ack=? WHERE id=?",
                    truthy(body.get("noticeAck")) ? 1 : 0,
                    ticketId);
        }
        if ((allowDeposit || body.containsKey("depositYuan")) && body.containsKey("depositYuan")) {
            if (!hasColumn("deposit_yuan")) {
                throw new IllegalStateException("系统未配置押金字段");
            }
            double dep = TicketSql.toDouble(body.get("depositYuan"));
            if (dep < 0) dep = 0;
            if (dep > 999999) dep = 999999;
            TicketSql.db().update("UPDATE " + TICKET + " SET deposit_yuan=? WHERE id=?", dep, ticketId);
        }
        if (allowExceptionClose || body.containsKey("exceptionReason") || body.containsKey("damageClaimNote")) {
            if (body.containsKey("exceptionReason") && hasColumn("exception_reason")) {
                String er = TicketSql.str(body.get("exceptionReason")).trim();
                if (er.length() > 128) er = er.substring(0, 128);
                TicketSql.db().update(
                        "UPDATE " + TICKET + " SET exception_reason=? WHERE id=?", er, ticketId);
            }
            if (body.containsKey("damageClaimNote") && hasColumn("damage_claim_note")) {
                String dn = TicketSql.str(body.get("damageClaimNote")).trim();
                if (dn.length() > 255) dn = dn.substring(0, 255);
                TicketSql.db().update(
                        "UPDATE " + TICKET + " SET damage_claim_note=? WHERE id=?", dn, ticketId);
            }
        }
        if (body.containsKey("insuranceAck") && hasColumn("insurance_ack")) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET insurance_ack=? WHERE id=?",
                    truthy(body.get("insuranceAck")) ? 1 : 0,
                    ticketId);
        }
        if ((allowProjectNo || body.containsKey("projectNo")) && body.containsKey("projectNo") && hasColumn("project_no")) {
            String pn = TicketSql.str(body.get("projectNo")).trim();
            if (pn.length() > 64) pn = pn.substring(0, 64);
            TicketSql.db().update("UPDATE " + TICKET + " SET project_no=? WHERE id=?", pn, ticketId);
        }
        if ((allowProcureRef || body.containsKey("procureRefNo")) && body.containsKey("procureRefNo")
                && hasColumn("procure_ref_no")) {
            String pr = TicketSql.str(body.get("procureRefNo")).trim();
            if (pr.length() > 64) pr = pr.substring(0, 64);
            TicketSql.db().update("UPDATE " + TICKET + " SET procure_ref_no=? WHERE id=?", pr, ticketId);
        }
        if (allowDualReview || body.containsKey("dualReviewerA") || body.containsKey("dualReviewerB")) {
            if (body.containsKey("dualReviewerA") && hasColumn("dual_reviewer_a")) {
                String a = TicketSql.str(body.get("dualReviewerA")).trim();
                if (a.length() > 64) a = a.substring(0, 64);
                TicketSql.db().update("UPDATE " + TICKET + " SET dual_reviewer_a=? WHERE id=?", a, ticketId);
            }
            if (body.containsKey("dualReviewerB") && hasColumn("dual_reviewer_b")) {
                String b = TicketSql.str(body.get("dualReviewerB")).trim();
                if (b.length() > 64) b = b.substring(0, 64);
                TicketSql.db().update("UPDATE " + TICKET + " SET dual_reviewer_b=? WHERE id=?", b, ticketId);
            }
        }
        if ((allowShipFee || body.containsKey("shipFeeYuan")) && body.containsKey("shipFeeYuan") && hasColumn("ship_fee_yuan")) {
            double fee = TicketSql.toDouble(body.get("shipFeeYuan"));
            if (fee < 0) fee = 0;
            if (fee > 999999) fee = 999999;
            TicketSql.db().update("UPDATE " + TICKET + " SET ship_fee_yuan=? WHERE id=?", fee, ticketId);
        }
        if ((allowUtilityNote || body.containsKey("utilityNote")) && body.containsKey("utilityNote") && hasColumn("utility_note")) {
            String un = TicketSql.str(body.get("utilityNote")).trim();
            if (un.length() > 255) un = un.substring(0, 255);
            TicketSql.db().update("UPDATE " + TICKET + " SET utility_note=? WHERE id=?", un, ticketId);
        }
        if (requirePeerConfirm || body.containsKey("peerUsername")) {
            if (body.containsKey("peerUsername") && hasColumn("peer_username")) {
                String pu = TicketSql.str(body.get("peerUsername")).trim();
                if (pu.length() > 64) pu = pu.substring(0, 64);
                if (requirePeerConfirm && pu.isBlank()) {
                    throw new IllegalStateException("请填写对方学号或用户名");
                }
                TicketSql.db().update(
                        "UPDATE " + TICKET + " SET peer_username=?, peer_ack=0 WHERE id=?", pu, ticketId);
            }
        }
        if (requireAbandonDual && allowDualReview) {
            String a = TicketSql.str(body.get("dualReviewerA")).trim();
            String b = TicketSql.str(body.get("dualReviewerB")).trim();
            if (a.isBlank() || b.isBlank()) {
                throw new IllegalStateException("弃件须两名确认人签字");
            }
            if (a.equalsIgnoreCase(b)) {
                throw new IllegalStateException("弃件确认人不能为同一人");
            }
        }
        patchFollowExtraStr(ticketId, body, "interviewResult", "interview_result", 16, allowInterviewResult);
        if ((allowWrittenScore || body.containsKey("writtenScore")) && body.containsKey("writtenScore")
                && hasColumn("written_score")) {
            double sc = TicketSql.toDouble(body.get("writtenScore"));
            if (sc < 0) sc = 0;
            if (sc > 999) sc = 999;
            TicketSql.db().update("UPDATE " + TICKET + " SET written_score=? WHERE id=?", sc, ticketId);
        }
        patchFollowExtraStr(ticketId, body, "bgCheckNote", "bg_check_note", 255, allowBgCheckNote);
        if ((allowDealAmount || body.containsKey("dealAmountYuan")) && body.containsKey("dealAmountYuan")
                && hasColumn("deal_amount_yuan")) {
            double amt = TicketSql.toDouble(body.get("dealAmountYuan"));
            if (amt < 0) amt = 0;
            if (amt > 99999999) amt = 99999999;
            TicketSql.db().update("UPDATE " + TICKET + " SET deal_amount_yuan=? WHERE id=?", amt, ticketId);
        }
        patchFollowExtraStr(ticketId, body, "nextAction", "next_action", 255, allowNextAction);
        if (body.containsKey("nextActionDone") && hasColumn("next_action_done")) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET next_action_done=? WHERE id=?",
                    truthy(body.get("nextActionDone")) ? 1 : 0,
                    ticketId);
        }
        if (allowLeaveProxy && body.containsKey("proxyName") && hasColumn("proxy_name")) {
            String pn = TicketSql.str(body.get("proxyName")).trim();
            if (pn.length() > 64) pn = pn.substring(0, 64);
            TicketSql.db().update("UPDATE " + TICKET + " SET proxy_name=? WHERE id=?", pn, ticketId);
        }
        patchFollowExtraStr(ticketId, body, "returnDate", "return_date", 32, requireReturnDate);
        patchFollowExtraStr(ticketId, body, "defenseResult", "defense_result", 32, allowDefenseResult);
        patchFollowExtraStr(ticketId, body, "bankAccount", "bank_account", 64, maskBankAccount);
        patchFollowExtraStr(ticketId, body, "closeAttachUrl", "close_attach_url", 255, requireCloseAttach);
        patchFollowExtraStr(ticketId, body, "assignDept", "assign_dept", 64, allowAssignDept);
        if (body.containsKey("confidential") && hasColumn("confidential")) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET confidential=? WHERE id=?",
                    truthy(body.get("confidential")) ? 1 : 0,
                    ticketId);
        }
        patchFollowExtraStr(ticketId, body, "appraisalComment", "appraisal_comment", 512, requireAppraisal);
        patchFollowExtraStr(ticketId, body, "appraisalGrade", "appraisal_grade", 16, requireAppraisal);
        patchFollowExtraStr(ticketId, body, "companyEval", "company_eval", 512, allowCompanyEval);
        if (body.containsKey("excellentMark") && hasColumn("excellent_mark")) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET excellent_mark=? WHERE id=?",
                    truthy(body.get("excellentMark")) ? 1 : 0,
                    ticketId);
        }
        patchFollowExtraStr(ticketId, body, "feedbackInterest", "feedback_interest", 128, requireFeedbackSet);
        patchFollowExtraStr(ticketId, body, "feedbackConcern", "feedback_concern", 255, requireFeedbackSet);
        patchFollowExtraStr(ticketId, body, "feedbackNext", "feedback_next", 255, requireFeedbackSet);
        patchFollowExtraStr(ticketId, body, "recordUrl", "record_url", 255, allowRecordUrl);
        patchFollowExtraStr(ticketId, body, "disburseBatch", "disburse_batch", 64, allowDisburseBatch);
        patchFollowExtraStr(ticketId, body, "faultReason", "fault_reason", 64, requireFaultReason || repairThicken);
        patchFollowExtraStr(ticketId, body, "closeSummary", "close_summary", 512, requireCloseSummary || repairThicken);
        patchFollowExtraStr(ticketId, body, "preferredSlot", "preferred_slot", 64, preferredSlot);
        patchFollowExtraStr(ticketId, body, "holdReason", "hold_reason", 255, allowHoldResume);
        patchFollowExtraStr(ticketId, body, "assetCode", "asset_code", 64, allowAssetCode);
        patchFollowExtraStr(ticketId, body, "remoteUrl", "remote_url", 255, allowRemoteUrl);
        patchFollowExtraStr(ticketId, body, "skillTag", "skill_tag", 64, repairThicken);
        patchFollowExtraStr(ticketId, body, "routeNote", "route_note", 255, repairThicken);
        patchFollowExtraStr(ticketId, body, "partsNote", "parts_note", 255, allowPartsNote);
        patchFollowExtraStr(ticketId, body, "serialNo", "serial_no", 64, allowSerialNo);
        patchFollowExtraStr(ticketId, body, "helperUsername", "helper_username", 64, allowHelper);
        patchFollowExtraStr(ticketId, body, "audioUrl", "audio_url", 255, repairThicken);
        patchFollowExtraStr(ticketId, body, "ratingTags", "rating_tags", 255, allowRatingTags);
        patchFollowExtraStr(ticketId, body, "addressType", "address_type", 16, allowPublicArea);
        patchFollowExtraStr(ticketId, body, "rankScope", "rank_scope", 16, true);
        if (body.containsKey("nightUrgent") && hasColumn("night_urgent")) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET night_urgent=? WHERE id=?",
                    truthy(body.get("nightUrgent")) ? 1 : 0,
                    ticketId);
        }
        if (body.containsKey("subscribeProgress") && hasColumn("subscribe_progress")) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET subscribe_progress=? WHERE id=?",
                    truthy(body.get("subscribeProgress")) ? 1 : 0,
                    ticketId);
        }
        if (body.containsKey("knowledgeDeposit") && hasColumn("knowledge_deposit")) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET knowledge_deposit=? WHERE id=?",
                    truthy(body.get("knowledgeDeposit")) ? 1 : 0,
                    ticketId);
        }
        if ((allowQuote || body.containsKey("quoteYuan")) && body.containsKey("quoteYuan") && hasColumn("quote_yuan")) {
            double q = TicketSql.toDouble(body.get("quoteYuan"));
            if (q < 0) q = 0;
            if (q > 999999) q = 999999;
            TicketSql.db().update("UPDATE " + TICKET + " SET quote_yuan=? WHERE id=?", q, ticketId);
        }
        if ((allowQuote || body.containsKey("materialFeeYuan")) && body.containsKey("materialFeeYuan")
                && hasColumn("material_fee_yuan")) {
            double fee = TicketSql.toDouble(body.get("materialFeeYuan"));
            if (fee < 0) fee = 0;
            if (fee > 999999) fee = 999999;
            TicketSql.db().update("UPDATE " + TICKET + " SET material_fee_yuan=? WHERE id=?", fee, ticketId);
        }
        if (body.containsKey("parentTicketId") && hasColumn("parent_ticket_id")) {
            long pid = TicketSql.toLong(body.get("parentTicketId"));
            if (pid > 0) {
                TicketSql.db().update("UPDATE " + TICKET + " SET parent_ticket_id=? WHERE id=?", pid, ticketId);
            }
        }
        if (body.containsKey("visitDueAt") && hasColumn("visit_due_at") && repairThicken) {
            String raw = TicketSql.str(body.get("visitDueAt")).trim();
            if (raw.isBlank()) {
                TicketSql.db().update("UPDATE " + TICKET + " SET visit_due_at=NULL WHERE id=?", ticketId);
            } else {
                try {
                    LocalDateTime due = LocalDateTime.parse(raw.replace(' ', 'T'));
                    TicketSql.db().update(
                            "UPDATE " + TICKET + " SET visit_due_at=? WHERE id=?",
                            Timestamp.valueOf(due),
                            ticketId);
                } catch (Exception ignored) {
                    // 格式不对则跳过，避免假成功写坏列
                }
            }
        }
    }

    private static void patchFollowExtraStr(
            long ticketId, Map<String, Object> body, String bodyKey, String col, int maxLen, boolean flagOn) {
        if (!(flagOn || body.containsKey(bodyKey)) || !body.containsKey(bodyKey) || !hasColumn(col)) return;
        String v = TicketSql.str(body.get(bodyKey)).trim();
        if (v.length() > maxLen) v = v.substring(0, maxLen);
        TicketSql.db().update("UPDATE " + TICKET + " SET " + col + "=? WHERE id=?", v, ticketId);
    }

    /** 调宿等：对方确认后宿管才可审过 */
    /** ASSET：确认领用单已关联申购单号（浅衔接，不跨库）。 */
    public static Map<String, Object> confirmProcureTransfer(long ticketId, String operator) {
        if (!allowProcureRef) throw new IllegalStateException("未开通申购单号衔接");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!hasColumn("procure_ref_no")) throw new IllegalStateException("系统未配置申购单号字段");
        String ref = TicketSql.str(m.get("procureRefNo")).trim();
        if (ref.isBlank()) throw new IllegalStateException("请先填写申购单号");
        String op = operator == null ? "" : operator.trim();
        appendProgress(ticketId, String.valueOf(m.get("status")), op, "已确认申购单号「" + ref + "」转入领用");
        return get(ticketId);
    }

    private static void tryEnsureProcureLine(long ticketId, Map<String, Object> m) {
        try {
            Integer n = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='procure_line'",
                    Integer.class);
            if (n == null || n <= 0) return;
            Integer cnt = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM procure_line WHERE ticket_id=?", Integer.class, ticketId);
            if (cnt != null && cnt > 0) return;
            String title = TicketSql.str(m.get("itemTitle"));
            if (title.isBlank()) title = TicketSql.str(m.get("bookTitle"));
            if (title.isBlank()) title = TicketSql.str(m.get("title"));
            if (title.isBlank()) title = "申购物资#" + ticketId;
            if (title.length() > 200) title = title.substring(0, 200);
            int q = rowQty(m);
            if (q <= 0) q = 1;
            TicketSql.db().update(
                    "INSERT INTO procure_line (ticket_id, item_title, qty, unit_price) VALUES (?,?,?,0)",
                    ticketId, title, q);
        } catch (Exception ignored) {
            // 无表或列差异时由 StockIoStore 兜底
        }
    }

    /** PROCURE：审过单据按明细一键入库。 */
    public static Map<String, Object> transferApprovedToStockIn(long ticketId, String operator) {
        if (!procureToStockIn) throw new IllegalStateException("未开通申购一键入库");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String st = String.valueOf(m.get("status"));
        if (!"approved".equals(st) && !"returned".equals(st) && !"completed".equals(st)) {
            throw new IllegalStateException("仅已通过的申购单可一键入库");
        }
        String op = operator == null ? "" : operator.trim();
        // 无明细时用单据标题兜底写入一行，便于演示
        tryEnsureProcureLine(ticketId, m);
        Map<String, Object> result = com.thesis.service.StockIoStore.receiveFromProcureTicket(ticketId, op);
        appendProgress(ticketId, st, op, "申购明细已一键入库（" + result.get("count") + " 行）");
        Map<String, Object> out = new LinkedHashMap<>(get(ticketId));
        out.put("stockIn", result);
        return out;
    }

    public static Map<String, Object> peerConfirm(long ticketId, String username, boolean pass, String remark) {
        if (!requirePeerConfirm) throw new IllegalStateException("当前未开启双方确认");
        if (!hasColumn("peer_username") || !hasColumn("peer_ack")) {
            throw new IllegalStateException("系统未配置双方确认字段");
        }
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!"pending".equals(String.valueOf(m.get("status")))
                && !"pending_mid".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅待审单据可确认");
        }
        String expect = TicketSql.str(m.get("peerUsername")).trim();
        String uid = username == null ? "" : username.trim();
        if (expect.isBlank() || !expect.equalsIgnoreCase(uid)) {
            throw new IllegalStateException("仅指定对方可确认");
        }
        String note = remark == null ? "" : remark.trim();
        if (!pass && note.isBlank()) {
            throw new IllegalStateException("请填写婉拒原因");
        }
        if (pass) {
            TicketSql.db().update("UPDATE " + TICKET + " SET peer_ack=1 WHERE id=?", ticketId);
            appendProgress(ticketId, "peer_confirm", uid, note.isBlank() ? "对方已确认" : note);
            try {
                String owner = TicketSql.str(m.get("username"));
                if (!owner.isBlank()) {
                    MessageStore.send(
                            owner,
                            "对方已确认",
                            "「" + subjectOf(m) + "」对方已确认，请等待宿管审核。",
                            "ticket",
                            ticketId);
                }
            } catch (Exception ignored) {
            }
        } else {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET status='rejected', remark=?, peer_ack=0 WHERE id=?",
                    note, ticketId);
            appendProgress(ticketId, "peer_reject", uid, note);
            try {
                String owner = TicketSql.str(m.get("username"));
                if (!owner.isBlank()) {
                    MessageStore.send(
                            owner,
                            "对方已婉拒",
                            "「" + subjectOf(m) + "」对方婉拒：" + note,
                            "ticket",
                            ticketId);
                }
            } catch (Exception ignored) {
            }
        }
        return get(ticketId);
    }

    /** 待我确认：peer_username=我 且待审 */
    public static Map<String, Object> pagePeerConfirmInbox(String username, int page, int size) {
        Map<String, Object> empty = new LinkedHashMap<>();
        empty.put("list", List.of());
        empty.put("total", 0);
        empty.put("page", Math.max(1, page));
        empty.put("size", Math.max(1, size));
        if (!requirePeerConfirm || !hasColumn("peer_username") || username == null || username.isBlank()) {
            return empty;
        }
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        Integer total = TicketSql.db().queryForObject(
                "SELECT COUNT(*) FROM " + TICKET
                        + " WHERE peer_username=? AND peer_ack=0 AND status IN ('pending','pending_mid')",
                Integer.class, username.trim());
        int t = total == null ? 0 : total;
        List<Map<String, Object>> list = TicketSql.db().query(
                "SELECT * FROM " + TICKET
                        + " WHERE peer_username=? AND peer_ack=0 AND status IN ('pending','pending_mid')"
                        + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> TicketStatusOps.enrich(TicketRowMaps.mapRow(rs)),
                username.trim(), size, (page - 1) * size);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list == null ? List.of() : list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    static void ensureColumn(String col, String ddlType) {
        if (hasColumn(col)) return;
        try {
            TicketSql.db().execute("ALTER TABLE " + TICKET + " ADD COLUMN " + col + " " + ddlType);
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> dashboard(String readerRole) {
        if (!enabled) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("pendingTickets", 0);
            empty.put("activeTickets", 0);
            empty.put("completedTickets", 0);
            empty.put("rejectedTickets", 0);
            empty.put("approveEndsFlow", approveEndsFlow);
            empty.put("userTotal", UserStore.countByRole(
                    readerRole == null || readerRole.isBlank() ? userRole : readerRole));
            empty.put("bookTotal", ArchiveStore.countItems());
            empty.put("stockTotal", ArchiveStore.sumStock());
            empty.put("categoryTotal", ArchiveStore.countCategories());
            return empty;
        }
        String role = readerRole == null || readerRole.isBlank() ? userRole : readerRole;
        if (useDeadline) {
            TicketSql.db().query("SELECT * FROM " + TICKET + " WHERE status IN ('approved','overdue')",
                    (rs, i) -> {
                        Map<String, Object> b = TicketRowMaps.mapRow(rs);
                        TicketStatusOps.refreshOverdue(b);
                        return b;
                    });
        }
        Long pending = TicketSql.db().queryForObject(
                "SELECT COUNT(*) FROM " + TICKET + " WHERE status IN ('pending','pending_mid','pending_final')", Long.class);
        Long approved = TicketSql.db().queryForObject("SELECT COUNT(*) FROM " + TICKET + " WHERE status='approved'", Long.class);
        Long overdue = useDeadline || noShowAfterEnd
                ? TicketSql.db().queryForObject("SELECT COUNT(*) FROM " + TICKET + " WHERE status='overdue'", Long.class)
                : 0L;
        Long returned = TicketSql.db().queryForObject("SELECT COUNT(*) FROM " + TICKET + " WHERE status='returned'", Long.class);
        Long rejected = TicketSql.db().queryForObject(
                "SELECT COUNT(*) FROM " + TICKET + " WHERE status='rejected'", Long.class);
        Long completed;
        Long active;
        if (approveEndsFlow) {
            long a = approved == null ? 0 : approved;
            long r = returned == null ? 0 : returned;
            long j = rejected == null ? 0 : rejected;
            long o = overdue == null ? 0 : overdue;
            // 通过 / 驳回 / 取消 / 爽约 均视为已处理；处理中不再含 approved
            completed = a + r + j + o;
            active = 0L;
        } else {
            completed = returned == null ? 0L : returned;
            active = approved == null ? 0L : approved;
        }
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("pendingTickets", pending == null ? 0 : pending);
        m.put("activeTickets", active);
        m.put("completedTickets", completed);
        m.put("rejectedTickets", rejected == null ? 0 : rejected);
        m.put("approveEndsFlow", approveEndsFlow);
        m.put("userTotal", UserStore.countByRole(role));
        m.put("pendingBorrow", pending == null ? 0 : pending);
        m.put("onLoan", approveEndsFlow ? 0 : (approved == null ? 0 : approved));
        m.put("overdueBorrow", overdue == null ? 0 : overdue);
        m.put("returnedBorrow", returned == null ? 0 : returned);
        if (approveEndsFlow) {
            m.put("approvedTickets", approved == null ? 0 : approved);
        }
        m.put("readerTotal", UserStore.countByRole(role));
        if (MODE == Mode.ARCHIVE) {
            m.put("bookTotal", ArchiveStore.countItems());
            m.put("stockTotal", ArchiveStore.sumStock());
            m.put("categoryTotal", ArchiveStore.countCategories());
            if (useDeadline && hasColumn("fine_yuan")) {
                Double fineOpen = TicketSql.db().queryForObject(
                        "SELECT COALESCE(SUM(fine_yuan),0) FROM " + TICKET + " WHERE status='overdue'", Double.class);
                m.put("openFineYuan", Math.round((fineOpen == null ? 0 : fineOpen) * 10.0) / 10.0);
            } else {
                m.put("openFineYuan", 0);
            }
        } else {
            m.put("bookTotal", 0);
            m.put("stockTotal", 0);
            m.put("categoryTotal", 0);
            m.put("openFineYuan", 0);
        }
        m.put("mode", MODE.name().toLowerCase());
        m.put("maxActive", maxActive());
        if (useDeadline) {
            m.put("loanDays", loanDays());
            m.put("finePerDay", finePerDay());
        }
        if (allowRating && hasColumn("rating")) {
            Double avg = TicketSql.db().queryForObject(
                    "SELECT AVG(rating) FROM " + TICKET + " WHERE rating IS NOT NULL AND rating > 0",
                    Double.class);
            Long ratedCnt = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM " + TICKET + " WHERE rating IS NOT NULL AND rating > 0",
                    Long.class);
            m.put("avgRating", avg == null ? 0 : Math.round(avg * 10.0) / 10.0);
            m.put("ratedCount", ratedCnt == null ? 0 : ratedCnt);
        }
        if (repairThicken && hasColumn("assignee_username")) {
            try {
                Long rejectCnt = TicketSql.db().queryForObject(
                        "SELECT COUNT(*) FROM " + TICKET + " WHERE remark LIKE '拒单%' OR remark LIKE '%拒单回池%'",
                        Long.class);
                m.put("rejectAssignmentCount", rejectCnt == null ? 0 : rejectCnt);
            } catch (Exception ignored) {
                m.put("rejectAssignmentCount", 0);
            }
        }
        return m;
    }

    /** 工作台图表：状态分布 + 近 7 日趋势（按 apply_at）+ 跟进渠道饼图。 */
    public static Map<String, Object> chartStats() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("statusSeries", List.of());
        out.put("trendSeries", List.of());
        out.put("channelSeries", List.of());
        if (!enabled) return out;
        try {
            List<Map<String, Object>> status = TicketSql.db().query(
                    "SELECT status AS name, COUNT(*) AS value FROM " + TICKET + " GROUP BY status",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("name", rs.getString("name"));
                        row.put("value", rs.getLong("value"));
                        return row;
                    });
            out.put("statusSeries", status);
            List<Map<String, Object>> trend = TicketSql.db().query(
                    "SELECT DATE_FORMAT(apply_at,'%Y-%m-%d') AS day, COUNT(*) AS value FROM " + TICKET
                            + " WHERE apply_at >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)"
                            + " GROUP BY DATE_FORMAT(apply_at,'%Y-%m-%d') ORDER BY day",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("day", rs.getString("day"));
                        row.put("value", rs.getLong("value"));
                        return row;
                    });
            out.put("trendSeries", trend);
            if (hasColumn("contact_channel")) {
                List<Map<String, Object>> channel = TicketSql.db().query(
                        "SELECT COALESCE(NULLIF(TRIM(contact_channel),''),'未填') AS name, COUNT(*) AS value FROM "
                                + TICKET
                                + " GROUP BY COALESCE(NULLIF(TRIM(contact_channel),''),'未填') ORDER BY value DESC LIMIT 12",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("name", rs.getString("name"));
                            row.put("value", rs.getLong("value"));
                            return row;
                        });
                out.put("channelSeries", channel);
            }
            // 热借/热办排行：按档案条目聚合（图书借阅量等）
            if (MODE == Mode.ARCHIVE && hasColumn(itemFkColumn())) {
                String itemTable = ArchiveStore.itemTable();
                List<Map<String, Object>> hot = TicketSql.db().query(
                        "SELECT COALESCE(i.title, CONCAT('编号', t." + itemFkColumn() + ")) AS name, COUNT(*) AS value "
                                + "FROM " + TICKET + " t LEFT JOIN " + itemTable + " i ON t." + itemFkColumn() + "=i.id "
                                + "WHERE t.status IN ('approved','overdue','returned','lost','compensated') "
                                + "GROUP BY t." + itemFkColumn() + ", i.title ORDER BY value DESC LIMIT 8",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("name", rs.getString("name"));
                            row.put("value", rs.getLong("value"));
                            return row;
                        });
                out.put("hotItemSeries", hot);
            }
            if (repairThicken && hasColumn("assignee_username")) {
                List<Map<String, Object>> workers = TicketSql.db().query(
                        "SELECT COALESCE(NULLIF(TRIM(assignee_username),''),'未派') AS name,"
                                + " SUM(CASE WHEN status IN ('approved','overdue','paused') THEN 1 ELSE 0 END) AS active,"
                                + " SUM(CASE WHEN status='returned' THEN 1 ELSE 0 END) AS done"
                                + " FROM " + TICKET
                                + " GROUP BY COALESCE(NULLIF(TRIM(assignee_username),''),'未派')"
                                + " ORDER BY done DESC, active DESC LIMIT 12",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("name", rs.getString("name"));
                            row.put("active", rs.getLong("active"));
                            row.put("done", rs.getLong("done"));
                            row.put("value", rs.getLong("done"));
                            return row;
                        });
                out.put("workerSeries", workers);
            }
            if (repairThicken && MODE == Mode.STANDALONE && hasColumn("location")) {
                List<Map<String, Object>> heat = TicketSql.db().query(
                        "SELECT COALESCE(NULLIF(TRIM(location),''),'未填地点') AS name, COUNT(*) AS value FROM "
                                + TICKET
                                + " WHERE status IN ('pending','pending_final','pending_mid','approved','overdue','paused')"
                                + " GROUP BY COALESCE(NULLIF(TRIM(location),''),'未填地点') ORDER BY value DESC LIMIT 12",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("name", rs.getString("name"));
                            row.put("value", rs.getLong("value"));
                            return row;
                        });
                out.put("locationHeatSeries", heat);
            }
            if (repairThicken && hasColumn("fault_reason")) {
                List<Map<String, Object>> faults = TicketSql.db().query(
                        "SELECT COALESCE(NULLIF(TRIM(fault_reason),''),'未填') AS name, COUNT(*) AS value FROM "
                                + TICKET
                                + " WHERE fault_reason IS NOT NULL AND TRIM(fault_reason)<>''"
                                + " GROUP BY COALESCE(NULLIF(TRIM(fault_reason),''),'未填') ORDER BY value DESC LIMIT 12",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("name", rs.getString("name"));
                            row.put("value", rs.getLong("value"));
                            return row;
                        });
                out.put("faultReasonSeries", faults);
            }
        } catch (Exception ignored) {
            // 表结构差异时不炸工作台
        }
        return out;
    }

    /**
     * 实习周报：截止日（weekReportDeadlineDay，周一=1…周日=7）到仍无本周 week_no 时站内催交。
     * 每用户每周最多一封（sys_message ref=week_report + 年周号）。
     */
    public static void maybeNotifyWeekReports(String forUsername) {
        if (!enabled || !weekReportRemind || weekReportDeadlineDay <= 0) return;
        if (!hasColumn("week_no")) return;
        java.time.LocalDate today = java.time.LocalDate.now();
        int dow = today.getDayOfWeek().getValue();
        if (dow < weekReportDeadlineDay) return;
        java.time.temporal.WeekFields wf = java.time.temporal.WeekFields.ISO;
        int weekNo = today.get(wf.weekOfWeekBasedYear());
        long refId = today.get(wf.weekBasedYear()) * 100L + weekNo;
        java.util.List<String> users = new java.util.ArrayList<>();
        try {
            if (forUsername != null && !forUsername.isBlank()) {
                users.add(forUsername.trim());
            } else {
                users = TicketSql.db().query(
                        "SELECT DISTINCT username FROM " + TICKET
                                + " WHERE username IS NOT NULL AND TRIM(username)<>'' LIMIT 200",
                        (rs, i) -> rs.getString(1));
            }
        } catch (Exception e) {
            return;
        }
        if (users == null || users.isEmpty()) return;
        for (String u : users) {
            if (u == null || u.isBlank()) continue;
            try {
                if (com.thesis.service.MessageStore.existsRef(u, "week_report", refId)) continue;
                Integer cnt = TicketSql.db().queryForObject(
                        "SELECT COUNT(*) FROM " + TICKET + " WHERE username=? AND week_no=?",
                        Integer.class,
                        u,
                        weekNo);
                if (cnt != null && cnt > 0) continue;
                com.thesis.service.MessageStore.send(
                        u,
                        "周报催交",
                        "本周（第 " + weekNo + " 周）周报尚未提交，请尽快填写提交。",
                        "week_report",
                        refId);
            } catch (Exception ignored) {
            }
        }
    }

    public static boolean runMainPathSelfCheck() {
        try {
            if (MODE == Mode.STANDALONE) {
                String user = "gate_" + System.currentTimeMillis();
                Long typeId = null;
                Long roomId = null;
                if (TicketLookupStore.enabled()) {
                    List<Map<String, Object>> types = TicketLookupStore.listTypes();
                    List<Map<String, Object>> units = TicketLookupStore.listUnits(null);
                    if (types.isEmpty() || units.isEmpty()) return false;
                    typeId = TicketSql.toLong(types.get(0).get("id"));
                    roomId = TicketSql.toLong(units.get(0).get("id"));
                }
                Map<String, Object> br = applyStandalone(user, "门禁自检报修", "测试地点", "gate", typeId, roomId);
                long bid = TicketSql.toLong(br.get("id"));
                approve(bid, true, "gate");
                complete(bid);
                Map<String, Object> done = get(bid);
                return done != null && "returned".equals(done.get("status"));
            }
            Map<String, Object> page = ArchiveStore.pageItems(null, null, 1, 1);
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> list = (List<Map<String, Object>>) page.get("list");
            if (list == null || list.isEmpty()) return false;
            long itemId = TicketSql.toLong(list.get(0).get("id"));
            String user = "gate_" + System.currentTimeMillis();
            Map<String, Object> br = apply(user, itemId);
            long bid = TicketSql.toLong(br.get("id"));
            approve(bid, true, "gate");
            complete(bid);
            Map<String, Object> done = get(bid);
            return done != null && "returned".equals(done.get("status"));
        } catch (Exception e) {
            return false;
        }
    }
}
