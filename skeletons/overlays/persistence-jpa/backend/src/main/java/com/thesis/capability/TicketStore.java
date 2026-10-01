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
     static int bizLoanDays = LOAN_DAYS;
     static int bizMaxActive = MAX_ACTIVE;
     static double bizFinePerDay = FINE_PER_DAY;
     static String bizPickupPlace = "";

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
        TicketDeriveOps.bind(ticketTable, quota, deadline, multiTicket, timeConflict);
    }

    /** 报修等：无档案占用；超时未处理 SLA 可打开 deadline */
    public static void bindStandalone(String ticketTable) {
        bindStandalone(ticketTable, false);
    }

    public static void bindStandalone(String ticketTable, boolean deadline) {
        TicketDeriveOps.bindStandalone(ticketTable, deadline);
    }

    /** 约定：进度表 = {单据表}_progress；可显式覆盖。 */
    public static void configureProgress(String progressTable) {
        TicketCfgOps.configureProgress(progressTable);
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
        TicketCfgOps.configureL1(twoLevel, attachRequired, ratingEnabled);
    }

    public static void configureRequireClaimProof(boolean enabled) {
        TicketCfgOps.configureRequireClaimProof(enabled);
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
        TicketDeriveOps.appendProgress(ticketId, "verifying", operator == null ? "" : operator, "已提交认领凭证，等待核验");
    }

    /** 凭证驳回后回到待交凭证 */
    public static void markPendingForProof(long ticketId, String operator) {
        if (ticketId <= 0) return;
        TicketSql.db().update(
                "UPDATE " + TICKET + " SET status='pending' WHERE id=? AND status='verifying'",
                ticketId);
        TicketDeriveOps.appendProgress(ticketId, "pending", operator == null ? "" : operator, "凭证未通过，请重新提交");
    }

    public static void configureApplicantCompleteOnly(boolean enabled) {
        TicketCfgOps.configureApplicantCompleteOnly(enabled);
    }

    public static boolean isApplicantCompleteOnly() {
        return applicantCompleteOnly;
    }

    /** C-16：三级会签；开启后二级路径扩展为 pending→pending_mid→pending_final */
    public static void configureThreeLevel(boolean enabled) {
        TicketCfgOps.configureThreeLevel(enabled);
    }

    public static boolean isThreeLevelApprove() {
        return threeLevelApprove;
    }

    /** 自选借期 + 申请数量（设备/图书常见；时间银行核销小时数可无库存） */
    public static void configureLoanOptions(boolean pickPeriod, boolean qtyEnabled) {
        TicketCfgOps.configureLoanOptions(pickPeriod, qtyEnabled);
    }

    /** C-14：审核通过扣减时长；须在 configureLoanOptions 前或后再调一次 refresh */
    public static void configureTimebankRedeem(boolean enabled) {
        TicketCfgOps.configureTimebankRedeem(enabled);
    }

    /** 必填说明 + 起止日期（申领用途 / 跟进 / 请假等） */
    public static void configureApplyExtras(boolean remarkRequired, boolean dateRange) {
        TicketCfgOps.configureApplyExtras(remarkRequired, dateRange);
    }

    /** 审核即收口：通过/驳回都算办结，不再把 approved 算作处理中 */
    public static void configureApproveEndsFlow(boolean enabled) {
        TicketCfgOps.configureApproveEndsFlow(enabled);
    }

    /** 提交即生效：申请直接落 approved，跳过管理端待审 */
    public static void configureAutoApprove(boolean enabled) {
        TicketCfgOps.configureAutoApprove(enabled);
    }

    public static boolean isAutoApprove() {
        return autoApprove;
    }

    /** 驿站等：申请说明/取件码须与档案取件码一致 */
    static boolean requireClaimCode = false;

    public static void configureRequireClaimCode(boolean enabled) {
        TicketCfgOps.configureRequireClaimCode(enabled);
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
        TicketCfgOps.configureMatchProfileRoom(enabled, buildingKey, roomKey, buildingField, roomField, looseBuilding, needMessage, denyMessage);
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
    /** 认领面交双方确认（申请人 meetingAck + 审核 ownerMeetingAck） */
    static boolean requireMeetingAck = false;
    /** 报名口令：须与档案 applyInviteCode 一致 */
    static boolean requireApplyInvite = false;
    /** 有团体票价/单房差文案时须勾选已读 */
    static boolean requirePriceNoteAck = false;
    /** 有赞助说明时须勾选已知晓 */
    static boolean requireSponsorAck = false;
    /** 有培养方案外链时须勾选已查阅 */
    static boolean requirePlanAck = false;
    /** 有先修提示码时须勾选确认（硬确认，非弱提示） */
    static boolean requirePrereqAck = false;
    /** 线路年龄上下限对照资料 ageYears */
    static boolean ageConstraint = false;
    static String ageConstraintNeedMessage = "请先在个人资料填写年龄。";
    static String ageConstraintDenyMessage = "当前年龄不符合本线路限制，请改选其他线路。";
    /** 签到可登记迟到分钟数 */
    static boolean allowLateMinutes = false;
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
    /** 报名组加厚：提交成功站内信 / 面交约定 / 紧急联系人 */
    static boolean applyThicken = false;
    static boolean notifyOnApplySuccess = false;
    static boolean allowMeetingPlace = false;
    static boolean allowEmergencyContact = false;
    static int cancelBeforeHours = 0;
    static int claimCooldownHours = 0;
    static int maxDropTimes = 0;
    static int semesterCreditCap = 0;
    static int creditWarnRemaining = 0;

    public static void configureProxyPickup(boolean enabled) {
        TicketCfgOps.configureProxyPickup(enabled);
    }

    public static void configureBedConstraint(boolean enabled, String needMessage, String denyMessage) {
        TicketCfgOps.configureBedConstraint(enabled, needMessage, denyMessage);
    }

    public static void configureArrivalNotify(boolean enabled) {
        TicketCfgOps.configureArrivalNotify(enabled);
    }

    public static void configureNoticeAck(boolean enabled) {
        TicketCfgOps.configureNoticeAck(enabled);
    }

    public static void configureApplyThicken(
            boolean applyThickenIn,
            boolean notifyOnApplySuccessIn,
            boolean allowMeetingPlaceIn,
            boolean allowEmergencyContactIn,
            int cancelBeforeHoursIn,
            int claimCooldownHoursIn,
            int maxDropTimesIn,
            int semesterCreditCapIn,
            int creditWarnRemainingIn) {
        TicketCfgOps.configureApplyThicken(applyThickenIn, notifyOnApplySuccessIn, allowMeetingPlaceIn, allowEmergencyContactIn, cancelBeforeHoursIn, claimCooldownHoursIn, maxDropTimesIn, semesterCreditCapIn, creditWarnRemainingIn);
    }

    public static void configureDeposit(boolean enabled) {
        TicketCfgOps.configureDeposit(enabled);
    }

    public static void configureExceptionClose(boolean enabled) {
        TicketCfgOps.configureExceptionClose(enabled);
    }

    public static void configureTrainingAck(boolean enabled) {
        TicketCfgOps.configureTrainingAck(enabled);
    }

    public static void configureInsuranceAck(boolean enabled) {
        TicketCfgOps.configureInsuranceAck(enabled);
    }

    public static void configureMeetingAck(boolean enabled) {
        TicketCfgOps.configureMeetingAck(enabled);
    }

    public static void configureApplyInvite(boolean enabled) {
        TicketCfgOps.configureApplyInvite(enabled);
    }

    public static void configurePriceNoteAck(boolean enabled) {
        TicketCfgOps.configurePriceNoteAck(enabled);
    }

    public static void configureSponsorAck(boolean enabled) {
        TicketCfgOps.configureSponsorAck(enabled);
    }

    public static void configurePlanAck(boolean enabled) {
        TicketCfgOps.configurePlanAck(enabled);
    }

    public static void configurePrereqAck(boolean enabled) {
        TicketCfgOps.configurePrereqAck(enabled);
    }

    public static void configureAgeConstraint(boolean enabled, String needMessage, String denyMessage) {
        TicketCfgOps.configureAgeConstraint(enabled, needMessage, denyMessage);
    }

    public static void configureLateMinutes(boolean enabled) {
        TicketCfgOps.configureLateMinutes(enabled);
    }

    public static void configureCalibBlock(boolean enabled) {
        TicketCfgOps.configureCalibBlock(enabled);
    }

    public static void configureProjectNo(boolean enabled) {
        TicketCfgOps.configureProjectNo(enabled);
    }

    public static void configureProcureRef(boolean enabled) {
        TicketCfgOps.configureProcureRef(enabled);
    }

    public static void configureProcureToStockIn(boolean enabled) {
        TicketCfgOps.configureProcureToStockIn(enabled);
    }

    public static boolean procureToStockInEnabled() {
        return procureToStockIn;
    }

    public static void configureDualReview(boolean enabled) {
        TicketCfgOps.configureDualReview(enabled);
    }

    public static void configureShipFee(boolean enabled) {
        TicketCfgOps.configureShipFee(enabled);
    }

    public static void configureUtilityNote(boolean enabled) {
        TicketCfgOps.configureUtilityNote(enabled);
    }

    public static void configureMaxCancelHolds(int max) {
        TicketCfgOps.configureMaxCancelHolds(max);
    }

    public static void configureOverdueAutoCompensate(boolean enabled) {
        TicketCfgOps.configureOverdueAutoCompensate(enabled);
    }

    public static void configureFineWaive(boolean enabled) {
        TicketCfgOps.configureFineWaive(enabled);
    }

    public static void configureRenewBlockIfHeld(boolean enabled) {
        TicketCfgOps.configureRenewBlockIfHeld(enabled);
    }

    public static void configurePeerConfirm(boolean enabled) {
        TicketCfgOps.configurePeerConfirm(enabled);
    }

    public static void configureAbandonDual(boolean enabled) {
        TicketCfgOps.configureAbandonDual(enabled);
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
        TicketCfgOps.configureFollowThicken(followRemindDaysIn, minRemarkWordsIn, maxReviseTimesIn, requireCloseAttachIn, requireReturnDateIn, requireFeedbackSetIn, requireAppraisalIn, allowDealAmountIn, allowNextActionIn, allowInterviewResultIn, allowWrittenScoreIn, allowBgCheckNoteIn, allowDefenseResultIn, maskBankAccountIn, allowDisburseBatchIn, allowLeaveProxyIn, allowCompanyEvalIn, allowExcellentMarkIn, allowRecordUrlIn, allowConfidentialIn, allowAssignDeptIn, allowBatchHireIn, weekReportRemindIn, homeVisitTemplateIn, attachByLeaveTypeIn, allowMakeupApplyIn, weekReportDeadlineDayIn);
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
        TicketCfgOps.configureFollowOps(staleFollowDaysIn, phoneDupCheckIn);
    }

    /** 事件组闸：等级影响处理时限 + 上报群发值班。 */
    public static void configureEventOps(
            boolean levelSlaIn, int highDaysIn, int midDaysIn, int lowDaysIn, boolean dutyNotifyIn) {
        TicketCfgOps.configureEventOps(levelSlaIn, highDaysIn, midDaysIn, lowDaysIn, dutyNotifyIn);
    }

    /** 等级 → 处理时限天数；levelSla 关时原样返回 fallback。 */
    static int levelSlaDays(Map<String, Object> m, int fallback) {
        return TicketDeriveOps.levelSlaDays(m, fallback);
    }

    /** 等级文本：单据行 level 优先，其次关联档案（event_case.level）。 */
    static String levelTextOf(Map<String, Object> m) {
        return TicketDeriveOps.levelTextOf(m);
    }

    /** 高,中,低 时限天数（未开时为空串），供前端展示。 */
    static String levelSlaCsv() {
        return levelSla ? (levelSlaHighDays + "," + levelSlaMidDays + "," + levelSlaLowDays) : "";
    }

    /** 事件上报群发当日值班；返回实际通知人数。 */
    static int notifyDutyOnNewReport(long ticketId, String applicant, String subject) {
        return TicketNotifyOps.notifyDutyOnNewReport(ticketId, applicant, subject);
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
        TicketCfgOps.configureRepairThicken(repairThickenIn, allowUserUrgeIn, urgeCooldownMinutesIn, lockUrgeAfterRateIn, allowCancelUrgeIn, requireFaultReasonIn, requireCloseSummaryIn, requireLowRatingRemarkIn, slaSplitIn, escalateOnOverdueIn, notifySupervisorOnOverdueIn, allowHoldResumeIn, allowCancelDispatchedIn, allowTicketDraftIn, allowFollowRateIn, preferredSlotIn, progressSubscribeIn, nightUrgentIn, allowPartsNoteIn, allowQuoteIn, allowPublicAreaIn, dupRoomCheckIn, allowAssetCodeIn, allowRemoteUrlIn, allowSerialNoIn, allowHelperIn, allowRatingTagsIn, todayBoardIn, printTicketIn);
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
        return TicketReviseOps.saveDraft(ticketId, username);
    }

    /**
     * 管理端退回修改：revise_count 记库；maxReviseTimes&gt;0 时超上限拒绝。
     */
    public static Map<String, Object> returnForRevise(long ticketId, String op, String note) {
        return TicketReviseOps.returnForRevise(ticketId, op, note);
    }

    /** 用户重新提交被退回的单据；修改次数未超上限才放行。 */
    public static Map<String, Object> resubmit(long ticketId, String username, String remark) {
        return TicketReviseOps.resubmit(ticketId, username, remark);
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
        TicketGuardOps.assertClaimCodeIfRequired(itemId, code);
    }

    /** matchProfileRoom：资料键↔档案列（查寝默认楼栋/房间；实习绑岗可配单位/岗位） */
    public static void assertMatchProfileRoomIfRequired(String username, long itemId) {
        TicketGuardOps.assertMatchProfileRoomIfRequired(username, itemId);
    }

    /** bedConstraint：档案限性别/年级 vs 个人资料 */
    public static void assertBedConstraintIfRequired(String username, long itemId) {
        TicketGuardOps.assertBedConstraintIfRequired(username, itemId);
    }

    /** 须知勾选 / 培训勾选 / 保险勾选：申请体校验 */
    public static void assertAckFlagsIfRequired(Map<String, Object> body) {
        TicketGuardOps.assertAckFlagsIfRequired(body);
    }

    /** 档案有票价/单房差说明时，申请须勾选已读。 */
    public static void assertPriceNoteAckIfRequired(Map<String, Object> item, Map<String, Object> body) {
        TicketGuardOps.assertPriceNoteAckIfRequired(item, body);
    }

    /** 档案有赞助说明时，申请须勾选已知晓。 */
    public static void assertSponsorAckIfRequired(Map<String, Object> item, Map<String, Object> body) {
        TicketGuardOps.assertSponsorAckIfRequired(item, body);
    }

    /** 档案有培养方案外链时，申请须勾选已查阅。 */
    public static void assertPlanAckIfRequired(Map<String, Object> item, Map<String, Object> body) {
        TicketGuardOps.assertPlanAckIfRequired(item, body);
    }

    public static void assertPrereqAckIfRequired(Map<String, Object> item, Map<String, Object> body) {
        TicketGuardOps.assertPrereqAckIfRequired(item, body);
    }

    public static void assertAgeConstraintIfRequired(String username, long itemId) {
        TicketGuardOps.assertAgeConstraintIfRequired(username, itemId);
    }

    /** 报名口令：与档案 applyInviteCode 比对（档案为空则不拦）。 */
    public static void assertApplyInviteIfRequired(long itemId, String code) {
        TicketGuardOps.assertApplyInviteIfRequired(itemId, code);
    }

    /** 审核通过时：启事方确认面交安排。 */
    public static void assertOwnerMeetingAckIfRequired(boolean pass, Map<String, Object> body) {
        TicketGuardOps.assertOwnerMeetingAckIfRequired(pass, body);
    }

    /** 失物认领冷却：启事发布后 N 小时才可提交。 */
    static void assertClaimCooldownIfRequired(Map<String, Object> item) {
        TicketGuardOps.assertClaimCooldownIfRequired(item);
    }

    /** 选课学分上限：已选（含本单）合计不可超过学期上限。 */
    static void assertSemesterCreditCapIfRequired(String username, Map<String, Object> item) {
        TicketGuardOps.assertSemesterCreditCapIfRequired(username, item);
    }

    static String creditWarnIfNearCap(String username, Map<String, Object> item) {
        return TicketGuardOps.creditWarnIfNearCap(username, item);
    }

    private static double itemCredit(Map<String, Object> item) {
        return TicketDeriveOps.itemCredit(item);
    }

     static double sumApprovedCredits(String username) {
        String user = username == null ? "" : username.trim();
        if (user.isBlank() || MODE != Mode.ARCHIVE) return 0;
        try {
            List<Map<String, Object>> rows = TicketSql.db().query(
                    "SELECT " + itemFkColumn() + " AS item_id FROM " + TICKET
                            + " WHERE username=? AND status IN ('approved','pending','pending_mid','pending_final','waitlisted')",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("itemId", rs.getLong("item_id"));
                        return m;
                    },
                    user);
            double sum = 0;
            if (rows != null) {
                for (Map<String, Object> r : rows) {
                    long iid = TicketSql.toLong(r.get("itemId"));
                    if (iid <= 0) continue;
                    Map<String, Object> it = ArchiveStore.getItemRaw(iid);
                    sum += TicketDeriveOps.itemCredit(it);
                }
            }
            return sum;
        } catch (Exception e) {
            return 0;
        }
    }

     static String trimCredit(double v) {
        if (Math.abs(v - Math.rint(v)) < 1e-6) return String.valueOf((int) Math.rint(v));
        return String.format(java.util.Locale.ROOT, "%.1f", v);
    }

    /** 活动取消：开始前不足 N 小时则禁止申请人自行取消。 */
    static void assertCancelBeforeIfRequired(Map<String, Object> ticket, String actorUid) {
        TicketGuardOps.assertCancelBeforeIfRequired(ticket, actorUid);
    }

    /** 退选次数上限：申请人完结（退选）时累计 returned 次数。 */
    static void assertMaxDropIfRequired(String username) {
        if (maxDropTimes <= 0) return;
        String user = username == null ? "" : username.trim();
        if (user.isBlank()) return;
        try {
            Integer n = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM " + TICKET + " WHERE username=? AND status='returned'",
                    Integer.class, user);
            if (n != null && n >= maxDropTimes) {
                throw new IllegalStateException("退选次数已达上限（" + maxDropTimes + " 次），暂不可再退选");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception ignored) {
        }
    }

    /** 校准证书过期停借 */
    public static void assertCalibDueIfRequired(long itemId) {
        TicketGuardOps.assertCalibDueIfRequired(itemId);
    }

    private static boolean truthy(Object v) {
        return TicketNotifyOps.truthy(v);
    }

    /** 与前端 profileRoomMatch 同规则，勿分叉 */
    public static boolean profileRoomMatches(String building, String room, String author, String title) {
        return profileRoomMatches(building, room, author, title, false);
    }

    public static boolean profileRoomMatches(
            String building, String room, String author, String title, boolean looseBuilding) {
        return TicketDeriveOps.profileRoomMatches(building, room, author, title, looseBuilding);
    }

    static String normRoomToken(String s) {
        if (s == null) return "";
        return s.trim().replace(" ", "").toLowerCase();
    }

    /** L1：互斥码 + 分类限额（选课等） */
    public static void configureRules(boolean mutex, int catLimit) {
        TicketCfgOps.configureRules(mutex, catLimit);
    }

    /** 借期/在途上限/逾期费/默认领取地（≤0 或空表示保持默认） */
    public static void configureBizParams(int loanDays, int maxActive, double finePerDay, String pickupPlace) {
        TicketCfgOps.configureBizParams(loanDays, maxActive, finePerDay, pickupPlace);
    }

    public static String ticketTable() {
        return TICKET;
    }

    /** 档案外键物理列名；API 仍暴露 bookId/itemId */
    public static String itemFkColumn() {
        return ITEM_FK == null || ITEM_FK.isBlank() ? "book_id" : ITEM_FK;
    }

     static void loadTicketColumnsFromResource() {
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
        TicketCfgOps.configureCheckin(enabled);
    }

    public static void configurePeerAccept(boolean enabled) {
        TicketCfgOps.configurePeerAccept(enabled);
    }

    public static boolean isPeerAccept() {
        return peerAccept;
    }

    public static void configureIssuePassCode(boolean enabled) {
        TicketCfgOps.configureIssuePassCode(enabled);
    }

    public static boolean isIssuePassCode() {
        return issuePassCode;
    }

    public static void configureRenew(boolean enabled, int maxTimes, int days) {
        TicketCfgOps.configureRenew(enabled, maxTimes, days);
    }

    public static void configureDueSoon(int days) {
        TicketCfgOps.configureDueSoon(days);
    }

    public static void configureMaxOverdueTimes(int times) {
        TicketCfgOps.configureMaxOverdueTimes(times);
    }

    public static int dueSoonDays() {
        return dueSoonDays;
    }

    public static int maxOverdueTimes() {
        return maxOverdueTimes;
    }

    public static void configureWaitlist(boolean enabled) {
        TicketCfgOps.configureWaitlist(enabled);
    }

    public static void configureBookHold(boolean enabled, int hours) {
        TicketCfgOps.configureBookHold(enabled, hours);
    }

    public static void configureBookLost(boolean enabled) {
        TicketCfgOps.configureBookLost(enabled);
    }

    public static void configureRequireReturnAttach(boolean enabled) {
        TicketCfgOps.configureRequireReturnAttach(enabled);
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
        TicketCfgOps.configureNoShow(afterEnd, penaltyYuan);
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
        return TicketApplyOps.apply(username, itemId, remark, attachUrl, qty, dueAt, periodStart, periodEnd);
    }

    private static LocalDateTime[] resolvePeriod(String periodStart, String periodEnd) {
        return TicketDeriveOps.resolvePeriod(periodStart, periodEnd);
    }

    private static int resolveQty(Integer qty, int stock) {
        return TicketDeriveOps.resolveQty(qty, stock);
    }

    private static LocalDateTime resolveRequestedDue(String dueAt) {
        return TicketDeriveOps.resolveRequestedDue(dueAt);
    }

    private static int rowQty(Map<String, Object> m) {
        return TicketDeriveOps.rowQty(m);
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
        return TicketApplyOps.applyStandalone(username, title, location, remark, typeId, roomId, attachUrl, priority, contactPhone);
    }

    /** 兼容旧调用：仅标题/地点/说明 */
    public static Map<String, Object> applyStandalone(String username, String title, String location, String remark) {
        return applyStandalone(username, title, location, remark, null, null, null, null, null);
    }

        
    
    /** C-05：档案主人确认/拒绝志愿；通过时复用 approve 扣库存。 */
    public static Map<String, Object> peerRespond(long ticketId, String username, boolean pass, String remark) {
        return TicketDeriveOps.peerRespond(ticketId, username, pass, remark);
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
        return TicketDeriveOps.isPeerOwnerOf(ticketId, username);
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

        int applied = TicketDeriveOps.rowQty(m);
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
        TicketDeriveOps.appendProgress(ticketId, "pickup", operator, tip);
        TicketNotifyOps.notifyPickup(m, loc, qtyToWrite);
        return TicketDeriveOps.get(ticketId);
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
        TicketDeriveOps.appendProgress(ticketId, "fine_paid", operator, TicketCopy.FINE_PAID_LABEL);
        return TicketDeriveOps.get(ticketId);
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
        TicketDeriveOps.appendProgress(ticketId, "fine_waived", operator, note.isBlank() ? "罚款已减免" : ("罚款减免：" + note));
        return TicketDeriveOps.get(ticketId);
    }

    static void appendProgress(long ticketId, String status, String operator, String remark) {
        TicketDeriveOps.appendProgress(ticketId, status, operator, remark);
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
        return TicketApproveOps.approve(ticketId, pass, remark, null, true, null);
    }

    public static Map<String, Object> approve(long ticketId, boolean pass, String remark, String operator) {
        return TicketApproveOps.approve(ticketId, pass, remark, operator, true, null);
    }

    public static Map<String, Object> approve(
            long ticketId, boolean pass, String remark, String operator, boolean superAdmin) {
        return TicketApproveOps.approve(ticketId, pass, remark, operator, superAdmin, null);
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
        return TicketApproveOps.approve(ticketId, pass, remark, operator, superAdmin, assigneeUsername);
    }

    
    /** C-09：通过后签发通行码（字符串；不对接闸机硬件）。失败须抛错，禁止静默无码。 */
    static String issuePassCodeIfNeeded(long ticketId) {
        return TicketApproveOps.issuePassCodeIfNeeded(ticketId);
    }

    /**
     * 通过并扣库存后若余量为 0，驳回同档案其它 pending/pending_mid/pending_final。
     * @return 实际驳回条数
     */
    static int rejectSiblingsWhenStockGone(long itemId, long approvedTicketId) {
        return TicketApproveOps.rejectSiblingsWhenStockGone(itemId, approvedTicketId);
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
        TicketDeriveOps.appendProgress(ticketId, followPass ? "follow_rated" : "rated", username, tip);
        return TicketDeriveOps.get(ticketId);
    }

    /** 活动口令签到：本人 + approved + 码匹配 */
    public static Map<String, Object> checkin(long ticketId, String username, String code) {
        return checkin(ticketId, username, code, null);
    }

    public static Map<String, Object> checkin(long ticketId, String username, String code, Integer lateMinutes) {
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
        if (allowLateMinutes && lateMinutes != null && hasColumn("late_minutes")) {
            int late = Math.max(0, lateMinutes);
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET late_minutes=? WHERE id=?",
                    late,
                    ticketId);
        }
        String tip = TicketCopy.CHECKIN_LABEL;
        if (allowLateMinutes && lateMinutes != null && lateMinutes > 0) {
            tip = tip + " · 迟到" + lateMinutes + "分钟";
        }
        TicketDeriveOps.appendProgress(ticketId, "checkin", username, tip);
        return TicketDeriveOps.get(ticketId);
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
            ArchiveStore.adjustStock(itemId, TicketDeriveOps.rowQty(m));
        }
        TicketSql.db().update(
                "UPDATE " + TICKET + " SET status='cancelled'"
                        + (hasColumn("hold_expire_at") ? ", hold_expire_at=NULL" : "")
                        + " WHERE id=?",
                ticketId);
        String progNote = "held".equals(st) ? "用户取消预约"
                : ("hold_ready".equals(st) ? "用户放弃取书"
                : ("waitlisted".equals(st) ? "用户取消候补" : "用户撤销申请"));
        TicketDeriveOps.appendProgress(ticketId, "cancelled", username, progNote);
        if ("hold_ready".equals(st) && itemId > 0) {
            tryPromoteBookHold(itemId);
        }
        return TicketDeriveOps.get(ticketId);
    }

    /**
     * 名额回补后：按申请时间 FIFO 将最早候补单升为待审（不直接扣库存，审过才占名额）。
     */
    static void tryPromoteWaitlist(long itemId) {
        TicketQueueOps.tryPromoteWaitlist(itemId);
    }

    /**
     * 还书入库后：FIFO 将最早预约单升为待取书并预扣库存；发到书站内信。
     */
    static void tryPromoteBookHold(long itemId) {
        TicketQueueOps.tryPromoteBookHold(itemId);
    }

    /** 超时未确认的待取书：取消、回补库存；顺延在调用方统一触发。 */
    static void expireBookHolds() {
        TicketQueueOps.expireBookHolds();
    }

    /**
     * 申请人确认借阅（hold_ready → approved）；库存已在到书晋升时预扣。
     */
    public static Map<String, Object> claimHold(long ticketId, String username) {
        return TicketDeriveOps.claimHold(ticketId, username);
    }

    /** hold_ready 通过：写 approved / due_at，不二次扣库存。 */
     static Map<String, Object> finalizeHoldReadyApprove(
            long ticketId,
            Map<String, Object> m,
            String note,
            String op,
            String dispatchTo,
            boolean bind) {
        return TicketQueueOps.finalizeHoldReadyApprove(ticketId, m, note, op, dispatchTo, bind);
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
        return TicketCompleteOps.complete(ticketId, actorUid, asSuperOrOwner, returnAttachUrl);
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
        TicketDeriveOps.appendProgress(ticketId, "lost", username, TicketCopy.stateLabel("lost", "丢失申报"));
        return TicketDeriveOps.get(ticketId);
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
        TicketDeriveOps.appendProgress(
                ticketId,
                "compensated",
                operator == null ? "" : operator,
                TicketCopy.stateLabel("compensated", "赔偿完成"));
        return TicketDeriveOps.get(ticketId);
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
        TicketDeriveOps.appendProgress(ticketId, "urged", username, "用户催办（第 " + count + " 次）");
        try {
            String title = TicketNotifyOps.subjectOf(m);
            String body = "【催办】用户对「" + title + "」发起催办，请尽快处理。";
            String asg = TicketSql.str(m.get("assigneeUsername"));
            if (!asg.isBlank()) {
                MessageStore.send(asg, "报修催办", body, "ticket", ticketId);
            } else {
                MessageStore.notifyAdmins("报修催办", body, "ticket", ticketId);
            }
        } catch (Exception ignored) {
        }
        return TicketDeriveOps.get(ticketId);
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
        TicketDeriveOps.appendProgress(ticketId, "urge_cancelled", username, "用户撤销催办");
        return TicketDeriveOps.get(ticketId);
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
        TicketDeriveOps.appendProgress(ticketId, "paused", operator == null ? "" : operator, "挂起：" + note);
        return TicketDeriveOps.get(ticketId);
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
        TicketDeriveOps.appendProgress(ticketId, "approved", operator == null ? "" : operator, "恢复处理");
        return TicketDeriveOps.get(ticketId);
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
        TicketDeriveOps.appendProgress(ticketId, "reassigned", operator == null ? "" : operator, note);
        try {
            MessageStore.send(to, "工单转派", "「" + TicketNotifyOps.subjectOf(m) + "」已转派给你，请尽快处理。", "ticket", ticketId);
        } catch (Exception ignored) {
        }
        return TicketDeriveOps.get(ticketId);
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
        TicketDeriveOps.appendProgress(ticketId, "cancelled", username, "用户取消已派单：" + note);
        return TicketDeriveOps.get(ticketId);
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
        TicketDeriveOps.appendProgress(ticketId, "pending", operator == null ? "" : operator, "拒单回池：" + note);
        return TicketDeriveOps.get(ticketId);
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
        TicketDeriveOps.appendProgress(ticketId, "quote_confirmed", username,
                payMaterial ? "用户确认报价并登记材料费" : "用户确认报价");
        return TicketDeriveOps.get(ticketId);
    }

    public static Map<String, Object> markOverdue(long ticketId) {
        return TicketDeriveOps.markOverdue(ticketId);
    }

    public static Map<String, Object> remind(long ticketId) {
        return TicketNotifyOps.remind(ticketId);
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
        TicketDeriveOps.appendProgress(
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
        return TicketDeriveOps.get(ticketId);
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
        return TicketQueryOps.page(username, status, page, size, adminUid, superAdmin, ratedOnly, todayAssigned);
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
            TicketDeriveOps.appendProgress(ticketId, "rejected", "system", reason);
            return;
        }
        TicketDeriveOps.appendProgress(ticketId, st, "system", "举报已记录：" + reason);
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
        return TicketDeriveOps.isHistoryStatus(status);
    }

    public static boolean isTodoPoolStatus(String status) {
        return "pending".equals(status) || "pending_mid".equals(status)
                || "pending_final".equals(status) || "todo".equals(status);
    }

    public static Map<String, Object> get(long id) {
        return TicketDeriveOps.get(id);
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
        TicketPatchOps.patchTicketExtras(ticketId, Map<String, body);
    }

        /** 调宿等：对方确认后宿管才可审过 */
    /** ASSET：确认领用单已关联申购单号（浅衔接，不跨库）。 */
    public static Map<String, Object> confirmProcureTransfer(long ticketId, String operator) {
        return TicketDeriveOps.confirmProcureTransfer(ticketId, operator);
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
            int q = TicketDeriveOps.rowQty(m);
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
        TicketDeriveOps.appendProgress(ticketId, st, op, "申购明细已一键入库（" + result.get("count") + " 行）");
        Map<String, Object> out = new LinkedHashMap<>(TicketDeriveOps.get(ticketId));
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
            TicketDeriveOps.appendProgress(ticketId, "peer_confirm", uid, note.isBlank() ? "对方已确认" : note);
            try {
                String owner = TicketSql.str(m.get("username"));
                if (!owner.isBlank()) {
                    MessageStore.send(
                            owner,
                            "对方已确认",
                            "「" + TicketNotifyOps.subjectOf(m) + "」对方已确认，请等待宿管审核。",
                            "ticket",
                            ticketId);
                }
            } catch (Exception ignored) {
            }
        } else {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET status='rejected', remark=?, peer_ack=0 WHERE id=?",
                    note, ticketId);
            TicketDeriveOps.appendProgress(ticketId, "peer_reject", uid, note);
            try {
                String owner = TicketSql.str(m.get("username"));
                if (!owner.isBlank()) {
                    MessageStore.send(
                            owner,
                            "对方已婉拒",
                            "「" + TicketNotifyOps.subjectOf(m) + "」对方婉拒：" + note,
                            "ticket",
                            ticketId);
                }
            } catch (Exception ignored) {
            }
        }
        return TicketDeriveOps.get(ticketId);
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
        return TicketDashOps.dashboard(readerRole);
    }

    /** 工作台图表：状态分布 + 近 7 日趋势（按 apply_at）+ 跟进渠道饼图。 */
    public static Map<String, Object> chartStats() {
        return TicketDashOps.chartStats();
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
        return TicketDeriveOps.runMainPathSelfCheck();
    }
}
