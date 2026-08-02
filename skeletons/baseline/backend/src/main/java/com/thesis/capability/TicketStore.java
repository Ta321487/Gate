package com.thesis.capability;

import com.thesis.config.DomainResourceJson;
import com.thesis.service.ExamStore;
import com.thesis.service.MessageStore;
import com.thesis.service.TimebankStore;
import com.thesis.service.UserStore;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
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

    /** bake 经 thesis.ticket-* 写入；学生包无配置表 */
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
    /** archive 行外键物理列（bake：book_id / customer_id / activity_id …） */
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

    /** 报修等：无档案占用；deadline 可由开题 SLA（超时未处理）打开 */
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

    /** 幂等建表：未 bake 进 schema 的旧库也能写出进度。 */
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
        } catch (Exception ignored) {
        }
    }

    public static void configureL1(boolean twoLevel, boolean attachRequired, boolean ratingEnabled) {
        twoLevelApprove = twoLevel || threeLevelApprove;
        requireAttach = attachRequired;
        allowRating = ratingEnabled;
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

    /** 自选借期 + 申请数量（设备/图书等开题常见；时间银行核销小时数可无库存） */
    public static void configureLoanOptions(boolean pickPeriod, boolean qtyEnabled) {
        pickLoanPeriod = pickPeriod && useDeadline;
        allowQty = qtyEnabled && MODE == Mode.ARCHIVE && (useQuota || timebankRedeem);
        // qty 列由 bake 按域/能力写入，禁止运行时 ALTER
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
        // period_* 列由 bake 写入
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
        // 档案可能写成「取件码/柜号」或「码 · 柜」；取第一段比对
        String expectCode = expect;
        int slash = expect.indexOf('/');
        if (slash > 0) expectCode = expect.substring(0, slash).trim();
        int dot = expectCode.indexOf('·');
        if (dot > 0) expectCode = expectCode.substring(0, dot).trim();
        if (!expectCode.equalsIgnoreCase(got) && !expect.equalsIgnoreCase(got)) {
            throw new IllegalStateException("取件码不正确");
        }
    }

    /** L1：互斥码 + 分类限额（选课等） */
    public static void configureRules(boolean mutex, int catLimit) {
        checkMutex = mutex;
        categoryLimit = Math.max(0, catLimit);
        // mutex_code 由 bake 写入档案表
    }

    /** bake 灌入的借期/在途上限/逾期费/默认领取地（≤0 或空表示保持默认） */
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
        // checked_in_at / 档案 checkin_code 由 bake 按能力写入
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
        ExamStore.assertTicketGatePassed(username);
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        int stock = item.get("stock") instanceof Number n ? n.intValue() : Integer.parseInt(String.valueOf(item.get("stock")));
        int nQty = resolveQty(qty, stock);
        if (useQuota && stock < nQty) throw new IllegalStateException(ArchiveStore.stockShortage(stock));
        TicketAsserts.assertApplyDeadline(item);
        TicketAsserts.assertNoTimeConflict(username, itemId, item);
        TicketAsserts.assertNoMutexConflict(username, itemId, item);
        TicketAsserts.assertCategoryLimit(username, item);
        TicketAsserts.assertUnderActiveLimit(username);
        String attach = TicketAsserts.normalizeAttach(attachUrl);
        LocalDateTime due = resolveRequestedDue(dueAt);
        LocalDateTime[] period = resolvePeriod(periodStart, periodEnd);
        if (!allowMultiTicket) {
            Integer dup = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM " + TICKET
                            + " WHERE username=? AND " + itemFkColumn()
                            + "=? AND status IN ('pending','pending_mid','pending_final','approved','overdue')",
                    Integer.class, username, itemId);
            if (dup != null && dup > 0) throw new IllegalStateException("该对象已有进行中的单据");
        }

        String rawNote = remark == null ? "" : remark.trim();
        if (requireRemark && rawNote.isBlank()) {
            throw new IllegalStateException("请填写说明后再提交");
        }
        final String note = rawNote.length() > 255 ? rawNote.substring(0, 255) : rawNote;
        KeyHolder kh = new GeneratedKeyHolder();
        final boolean withAttach = hasColumn("attach_url");
        final boolean withQty = hasColumn("qty");
        final boolean withDue = due != null && hasColumn("due_at");
        final boolean withPeriod = period != null && hasColumn("period_start") && hasColumn("period_end");
        final String attachFinal = attach;
        final int qtyFinal = nQty;
        final Timestamp dueTs = withDue ? Timestamp.valueOf(due) : null;
        final Timestamp periodStartTs = withPeriod ? Timestamp.valueOf(period[0]) : null;
        final Timestamp periodEndTs = withPeriod ? Timestamp.valueOf(period[1]) : null;
        final String initialStatus = autoApprove ? "approved" : "pending";
        final boolean withApproveAt = autoApprove && hasColumn("approve_at");
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
                ps.setTimestamp(i, periodEndTs);
            }
            return ps;
        }, kh);
        Number key = kh.getKey();
        long id = key == null ? 0L : key.longValue();
        if (autoApprove) {
            appendProgress(id, "approved", username, "用户提交（即时生效）");
        } else {
            appendProgress(id, "pending", username, "用户提交");
            String subj = subjectOf(get(id));
            notifyAdminsNewTicket(id, username, subj);
            notifyPeerOwnerNewTicket(id, itemId, username, subj);
        }
        return get(id);
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
        if (q instanceof Number n) return Math.max(1, n.intValue());
        try {
            return Math.max(1, Integer.parseInt(String.valueOf(q)));
        } catch (Exception e) {
            return 1;
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
        TicketAsserts.assertUnderActiveLimit(username);
        String attach = TicketAsserts.normalizeAttach(attachUrl);

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
        return get(id);
    }

    /** 兼容旧调用：仅标题/地点/说明 */
    public static Map<String, Object> applyStandalone(String username, String title, String location, String remark) {
        return applyStandalone(username, title, location, remark, null, null, null, null, null);
    }

    private static void patchStandaloneExtras(long id, String priority, String contactPhone) {
        if (id <= 0) return;
        boolean hasP = hasColumn("priority");
        boolean hasC = hasColumn("contact_phone");
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
        String st = String.valueOf(m.get("status"));
        // 仅进行中单据可登记；退库后库存已回补，再登记会乱账
        if (!"approved".equals(st) && !"overdue".equals(st)) {
            throw new IllegalStateException("仅已通过/进行中单据可登记领取");
        }
        if (hasColumn("pickup_at")) {
            String prev = TicketSql.str(m.get("pickupAt"));
            if (!prev.isBlank()) {
                throw new IllegalStateException("该单已登记领取，不可重复操作");
            }
        }
        String loc = place == null ? "" : place.trim();
        if (loc.isBlank()) loc = bizPickupPlace;
        if (loc.isBlank()) {
            throw new IllegalStateException("请填写领取地点");
        }
        if (loc.length() > 128) {
            throw new IllegalStateException("领取地点过长");
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

        if (hasColumn("pickup_at")) {
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

    static void appendProgress(long ticketId, String status, String operator, String remark) {
        if (ticketId <= 0) return;
        ensureProgressTable();
        if (PROGRESS == null || PROGRESS.isBlank()) return;
        try {
            TicketProgressOps.insertProgressRow(
                    ticketId,
                    status,
                    operator,
                    remark,
                    Timestamp.valueOf(LocalDateTime.now()));
        } catch (Exception ignored) {
        }
    }

    /** 默认借期（天）：bake 写入，缺省 LOAN_DAYS */
    public static int loanDays() {
        return bizLoanDays;
    }

    /** 每人在途单据上限：bake 写入，缺省 MAX_ACTIVE */
    public static int maxActive() {
        return bizMaxActive;
    }

    /** 逾期预估单价：bake 写入，缺省 FINE_PER_DAY */
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
        boolean midStage = "pending_mid".equals(st);
        boolean finalStage = "pending_final".equals(st);
        if (!first && !midStage && !finalStage) throw new IllegalStateException("仅待审核单据可审批");
        if (twoLevelApprove && finalStage && pass && !superAdmin) {
            throw new IllegalStateException("终审通过需总管操作");
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
        // 二级：初审通过 → 待终审（不扣库存）
        if (twoLevelApprove && !threeLevelApprove && first) {
            advanceApproveStage(ticketId, "pending_final", note, op, bind, m,
                    "初审已通过", "「" + subjectOf(m) + "」已通过初审，等待终审。",
                    "待终审", "初审通过");
            return get(ticketId);
        }

        // 终审通过或单级通过 → approved（扣库存 / 时间银行扣时长）
        if (timebankRedeem) {
            TimebankStore.debitForTicketApprove(m);
        }
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
            LocalDateTime dueAt = approveAt.plusDays(loanDays());
            Object requested = m.get("dueAt");
            if (requested != null && !String.valueOf(requested).isBlank()) {
                try {
                    dueAt = TicketSql.parseDateTimeFlexible(String.valueOf(requested).trim());
                } catch (Exception ignored) {
                    // 保留默认借期
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
                if (hasColumn("due_at")) {
                    sql.append(", due_at=?");
                    args.add(Timestamp.valueOf(dueAt));
                }
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
                if (hasColumn("due_at")) {
                    sql.append(", due_at=?");
                    args.add(Timestamp.valueOf(dueAt));
                }
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
        } else if (useDeadline && hasColumn("due_at")) {
            // 独立工单 SLA：受理进入处理中时起算处理时限
            LocalDateTime approveAt = LocalDateTime.now();
            LocalDateTime dueAt = approveAt.plusDays(loanDays());
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

    /** C-09：通过后签发通行码（字符串；非硬件门禁）。 */
    private static String issuePassCodeIfNeeded(long ticketId) {
        if (!issuePassCode || !hasColumn("pass_code") || ticketId <= 0) return "";
        try {
            Map<String, Object> cur = get(ticketId);
            if (cur != null) {
                String prev = TicketSql.str(cur.get("passCode"));
                if (!prev.isBlank()) return prev;
            }
            String code = "VIS" + String.format("%08d", Math.floorMod(System.nanoTime(), 100_000_000));
            TicketSql.db().update("UPDATE " + TICKET + " SET pass_code=? WHERE id=?", code, ticketId);
            appendProgress(ticketId, "pass_code", "system", "通行码 " + code);
            return code;
        } catch (Exception ignored) {
            return "";
        }
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
            return 0;
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
            } catch (Exception ignored) {
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
        if (prev != null && !"0".equals(String.valueOf(prev)) && !"".equals(String.valueOf(prev))) {
            throw new IllegalStateException("已评价过，不可重复提交");
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
        boolean anon = anonymous && TicketCopy.ALLOW_ANONYMOUS_RATING;
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
        String tip = overall + " 分";
        if (!dimsJson.isBlank()) tip = tip + "（多维）";
        if (anon) tip = tip + " · 匿名";
        if (!note.isBlank()) tip = tip + " · " + note;
        appendProgress(ticketId, "rated", username, tip);
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
            String title = pass ? "审核已通过" : "审核未通过";
            String body = pass
                    ? ("「" + subject + "」已通过" + (note == null || note.isBlank() ? "" : "：" + note))
                    : ("「" + subject + "」已驳回" + (note == null || note.isBlank() ? "" : "：" + note));
            if (pass && hasColumn("pickup_at") && !bizPickupPlace.isBlank()) {
                body = body + "。请到「" + bizPickupPlace + "」领取，到场后由工作人员登记实发。";
            }
            if (pass && passCode != null && !passCode.isBlank()) {
                body = body + "。通行码：" + passCode + "（非真门禁，到访时出示即可）。";
            }
            MessageStore.send(user, title, body, "ticket", TicketSql.toLong(ticket.get("id")));
        } catch (Exception ignored) {
            // 消息失败不影响主流程
        }
    }

    /** 领取登记后通知申请人地点与实发数量 */
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
     * 申请人撤销待审单据（pending / pending_mid / pending_final）。未扣库存，无需回补。
     */
    public static Map<String, Object> withdraw(long ticketId, String username) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (username == null || username.isBlank()
                || !username.equals(String.valueOf(m.get("username")))) {
            throw new IllegalStateException("只能撤销自己的申请");
        }
        String st = String.valueOf(m.get("status"));
        if (!"pending".equals(st) && !"pending_mid".equals(st) && !"pending_final".equals(st)) {
            throw new IllegalStateException("仅待审核申请可撤销");
        }
        TicketSql.db().update(
                "UPDATE " + TICKET + " SET status='cancelled' WHERE id=?",
                ticketId);
        appendProgress(ticketId, "cancelled", username, "用户撤销申请");
        return get(ticketId);
    }

    public static Map<String, Object> complete(long ticketId) {
        return complete(ticketId, null, true);
    }

    /**
     * @param actorUid 操作者；申请人完结传本人且 asSuperOrOwner=true
     * @param asSuperOrOwner true=总管或单据申请人（不校验处理人）；false=子管须为 assignee
     */
    public static Map<String, Object> complete(long ticketId, String actorUid, boolean asSuperOrOwner) {
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
            }
        }
        String remind = "";
        if (useDeadline) {
            String doneLab = TicketCopy.stateLabel("returned", TicketCopy.verbLabel("return", "已完结"));
            remind = TicketSql.toDouble(m.get("fineYuan")) > 0
                    ? doneLab + "，请按登记费用缴纳 " + m.get("fineYuan") + " 元。"
                    : String.valueOf(m.get("remindMsg") == null ? "" : m.get("remindMsg"));
        }
        if (hasColumn("remind_msg")) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET status='returned', return_at=NOW(), remind_msg=? WHERE id=?",
                    remind, ticketId);
        } else {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET status='returned', return_at=NOW() WHERE id=?",
                    ticketId);
        }
        appendProgress(ticketId, "returned", actorUid, TicketCopy.stateLabel("returned", TicketCopy.verbLabel("return", "已完结")));
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
        return get(ticketId);
    }

    public static Map<String, Object> page(String username, String status, int page, int size) {
        return page(username, status, page, size, null, true, null);
    }

    public static Map<String, Object> page(
            String username, String status, int page, int size, String adminUid, boolean superAdmin) {
        return page(username, status, page, size, adminUid, superAdmin, null);
    }

    /**
     * @param username 业务用户视角：只看自己的单；管理员传 null
     * @param adminUid 子管用户名；总管配合 superAdmin=true 看全部
     * @param superAdmin 总管看全部；子管：待办池 + 自己绑定的进行中 + 全体终态（取消/驳回等）
     * @param ratedOnly true 时仅返回已评分单据（管理端查看评价）
     */
    public static Map<String, Object> page(
            String username,
            String status,
            int page,
            int size,
            String adminUid,
            boolean superAdmin,
            Boolean ratedOnly) {
        if (page < 1) page = 1;
        if (size < 1) size = 10;
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
                where.append(" AND status IN ('pending','pending_mid','pending_final')");
            } else {
                where.append(" AND status=?");
                args.add(status);
            }
        }
        if (Boolean.TRUE.equals(ratedOnly) && hasColumn("rating")) {
            where.append(" AND rating IS NOT NULL AND rating > 0");
        }
        Integer total = TicketSql.db().queryForObject("SELECT COUNT(*) FROM " + TICKET + where, Integer.class, args.toArray());
        int t = total == null ? 0 : total;
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = TicketSql.db().query(
                "SELECT * FROM " + TICKET + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> TicketStatusOps.enrich(TicketRowMaps.mapRow(rs)), args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
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
                || "noshow".equals(status);
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
        // no-op：单据扩展列由 bake 按域/能力写入，禁止运行时补 L1 超集
    }

    /** CRM 等：申请后补写可选列 */
    public static void patchTicketExtras(long ticketId, Map<String, Object> body) {
        if (ticketId <= 0 || body == null || body.isEmpty()) return;
        if (hasColumn("contact_channel") && body.containsKey("contactChannel")) {
            String ch = TicketSql.str(body.get("contactChannel")).trim();
            if (ch.length() > 32) ch = ch.substring(0, 32);
            TicketSql.db().update("UPDATE " + TICKET + " SET contact_channel=? WHERE id=?", ch, ticketId);
        }
        if (hasColumn("next_follow_at") && body.containsKey("nextFollowAt")) {
            Timestamp ts = null;
            Object raw = body.get("nextFollowAt");
            if (raw != null && !String.valueOf(raw).isBlank()) {
                try {
                    ts = Timestamp.valueOf(TicketSql.parseDateTimeFlexible(String.valueOf(raw).trim(), false));
                } catch (Exception ignored) {
                    ts = null;
                }
            }
            TicketSql.db().update("UPDATE " + TICKET + " SET next_follow_at=? WHERE id=?", ts, ticketId);
        }
        // 报销等：提交时写入金额（复用 fine_yuan；借阅罚金/SLA 到期不计此路径）
        if (hasColumn("fine_yuan") && !useDeadline
                && (body.containsKey("fineYuan") || body.containsKey("amountYuan"))) {
            Object raw = body.containsKey("fineYuan") ? body.get("fineYuan") : body.get("amountYuan");
            double amt = TicketSql.toDouble(raw);
            if (amt < 0) amt = 0;
            if (amt > 99999999) amt = 99999999;
            TicketSql.db().update("UPDATE " + TICKET + " SET fine_yuan=? WHERE id=?", amt, ticketId);
        }
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
        return m;
    }

    /** 工作台图表：状态分布 + 近 7 日趋势（按 apply_at）。 */
    public static Map<String, Object> chartStats() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("statusSeries", List.of());
        out.put("trendSeries", List.of());
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
        } catch (Exception ignored) {
            // 表结构差异时不炸工作台
        }
        return out;
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
