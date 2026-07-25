package com.thesis.capability;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.DomainResourceJson;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.SchemaMapper;
import com.thesis.mapper.TicketMapper;
import com.thesis.service.MessageStore;
import com.thesis.service.UserStore;

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
    /** L1：初审 → 终审 */
    static boolean twoLevelApprove = false;
    /** L1：申请须上传附件 */
    static boolean requireAttach = false;
    /** L1：完结后可评分 */
    static boolean allowRating = false;
    /** L1：同 mutex_code 的档案不可同时选 */
    static boolean checkMutex = false;
    /** L1：同一分类下进行中单据上限；≤0 表示不限 */
    static int categoryLimit = 0;
    /** L1：签到口令 */
    static boolean allowCheckin = false;
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

    private static TicketMapper mapper() {
        return MybatisSupport.mapper(TicketMapper.class);
    }

    private static SchemaMapper schema() {
        return MybatisSupport.mapper(SchemaMapper.class);
    }

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

    /** 报修等：无档案占用、无到期催办 */
    public static void bindStandalone(String ticketTable) {
        if (ticketTable != null && !ticketTable.isBlank()) TICKET = ticketTable.trim();
        MODE = Mode.STANDALONE;
        useQuota = false;
        useDeadline = false;
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
            schema().executeDdl(
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
        twoLevelApprove = twoLevel;
        requireAttach = attachRequired;
        allowRating = ratingEnabled;
    }

    /** 自选借期 + 申请数量（设备/图书等开题常见） */
    public static void configureLoanOptions(boolean pickPeriod, boolean qtyEnabled) {
        pickLoanPeriod = pickPeriod && useDeadline;
        allowQty = qtyEnabled && useQuota && MODE == Mode.ARCHIVE;
        // qty 列由 bake 按域/能力写入，禁止运行时 ALTER
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
            int dup = mapper().countActiveDup(TICKET, itemFkColumn(), username, itemId);
            if (dup > 0) throw new IllegalStateException("该对象已有进行中的单据");
        }

        String rawNote = remark == null ? "" : remark.trim();
        if (requireRemark && rawNote.isBlank()) {
            throw new IllegalStateException("请填写说明后再提交");
        }
        final String note = rawNote.length() > 255 ? rawNote.substring(0, 255) : rawNote;
        final boolean withAttach = hasColumn("attach_url");
        final boolean withQty = hasColumn("qty");
        final boolean withDue = due != null && hasColumn("due_at");
        final boolean withPeriod = period != null && hasColumn("period_start") && hasColumn("period_end");
        final String initialStatus = autoApprove ? "approved" : "pending";
        final boolean withApproveAt = autoApprove && hasColumn("approve_at");
        Map<String, Object> ins = new LinkedHashMap<>();
        ins.put("ticketTable", TICKET);
        ins.put("itemFk", itemFkColumn());
        ins.put("itemId", itemId);
        ins.put("username", username);
        ins.put("status", initialStatus);
        ins.put("remark", note);
        ins.put("withFineYuan", hasColumn("fine_yuan"));
        ins.put("withRemindMsg", hasColumn("remind_msg"));
        ins.put("withApproveAt", withApproveAt);
        ins.put("withAttach", withAttach);
        ins.put("withQty", withQty);
        ins.put("withDue", withDue);
        ins.put("withPeriod", withPeriod);
        if (withAttach) ins.put("attachUrl", attach);
        if (withQty) ins.put("qty", nQty);
        if (withDue) ins.put("dueAt", Timestamp.valueOf(due));
        if (withPeriod) {
            ins.put("periodStart", Timestamp.valueOf(period[0]));
            ins.put("periodEnd", Timestamp.valueOf(period[1]));
        }
        mapper().insertArchive(ins);
        long id = TicketSql.toLong(ins.get("id"));
        if (autoApprove) {
            appendProgress(id, "approved", username, "用户提交（即时生效）");
        } else {
            appendProgress(id, "pending", username, "用户提交");
            notifyAdminsNewTicket(id, username, subjectOf(get(id)));
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

        String p = priority == null || priority.isBlank() ? "普通" : priority.trim();
        if (p.length() > 16) p = p.substring(0, 16);
        String phone = contactPhone == null ? "" : contactPhone.trim();
        if (phone.length() > 20) phone = phone.substring(0, 20);

        Map<String, Object> ins = new LinkedHashMap<>();
        ins.put("ticketTable", TICKET);
        ins.put("username", username);
        ins.put("title", t);
        ins.put("location", locFinal);
        ins.put("typeId", tidFinal > 0 ? tidFinal : null);
        ins.put("roomId", ridFinal > 0 ? ridFinal : null);
        ins.put("remark", remarkFinal);
        boolean withAttach = hasColumn("attach_url");
        ins.put("withAttach", withAttach);
        if (withAttach) ins.put("attachUrl", attachFinal);
        boolean withPriority = hasColumn("priority");
        boolean withContact = hasColumn("contact_phone");
        ins.put("withPriority", withPriority);
        ins.put("withContactPhone", withContact);
        if (withPriority) ins.put("priority", p);
        if (withContact) ins.put("contactPhone", phone);
        mapper().insertStandalone(ins);
        long id = TicketSql.toLong(ins.get("id"));
        appendProgress(id, "pending", username, "用户提交");
        notifyAdminsNewTicket(id, username, t);
        return get(id);
    }

    /** 兼容旧调用：仅标题/地点/说明 */
    public static Map<String, Object> applyStandalone(String username, String title, String location, String remark) {
        return applyStandalone(username, title, location, remark, null, null, null, null, null);
    }

    private static void notifyAdminsNewTicket(long ticketId, String applicant, String subject) {
        if (ticketId <= 0) return;
        try {
            String sub = subject == null || subject.isBlank() ? ("单据#" + ticketId) : subject;
            String who = UserStore.displayName(applicant);
            MessageStore.notifyAdmins(
                    "待受理",
                    who + " 提交了「" + sub + "」，请尽快处理。",
                    "ticket",
                    ticketId);
        } catch (Exception ignored) {
        }
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
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("ticketTable", TICKET);
            row.put("id", ticketId);
            row.put("withPlace", hasColumn("pickup_place"));
            row.put("pickupPlace", loc);
            row.put("withActualQty", hasColumn("actual_qty") && qtyToWrite != null);
            if (qtyToWrite != null) row.put("actualQty", qtyToWrite);
            mapper().updatePickup(row);
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
        mapper().updateFinePaid(TICKET, ticketId);
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
        return approve(ticketId, pass, remark, null, true);
    }

    public static Map<String, Object> approve(long ticketId, boolean pass, String remark, String operator) {
        return approve(ticketId, pass, remark, operator, true);
    }

    /**
     * 审批。二级审批时：pending→pending_final（初审，不占库存）→approved（终审占库存）。
     * 终审通过需总管（superAdmin=true）。
     */
    public static Map<String, Object> approve(
            long ticketId, boolean pass, String remark, String operator, boolean superAdmin) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String st = String.valueOf(m.get("status"));
        boolean first = "pending".equals(st);
        boolean finalStage = "pending_final".equals(st);
        if (!first && !finalStage) throw new IllegalStateException("仅待审核单据可审批");
        if (twoLevelApprove && finalStage && pass && !superAdmin) {
            throw new IllegalStateException("终审通过需总管操作");
        }
        String op = operator == null ? "" : operator.trim();
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
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("ticketTable", TICKET);
            row.put("id", ticketId);
            row.put("remark", note);
            row.put("bindAssignee", bind);
            if (bind) row.put("assigneeUsername", op);
            mapper().updateReject(row);
            notifyTicketResult(m, false, note);
            appendProgress(ticketId, "rejected", op,
                    note == null || note.isBlank() ? TicketCopy.stateLabel("rejected", TicketCopy.verbLabel("reject", "已驳回")) : note);
            return get(ticketId);
        }

        // 二级：初审通过 → 待终审（不扣库存）
        if (twoLevelApprove && first) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("ticketTable", TICKET);
            row.put("id", ticketId);
            row.put("remark", note);
            row.put("bindAssignee", bind);
            if (bind) row.put("assigneeUsername", op);
            mapper().updatePendingFinal(row);
            try {
                String user = TicketSql.str(m.get("username"));
                if (!user.isBlank()) {
                    MessageStore.send(user, "初审已通过", "「" + subjectOf(m) + "」已通过初审，等待终审。",
                            "ticket", TicketSql.toLong(m.get("id")));
                }
                MessageStore.notifyAdmins(
                        "待终审",
                        "「" + subjectOf(m) + "」已通过初审，等待终审。",
                        "ticket",
                        TicketSql.toLong(m.get("id")),
                        op);
            } catch (Exception ignored) {
            }
            appendProgress(ticketId, "pending_final", op, note.isBlank()
                    ? TicketCopy.stateLabel("pending_final", "初审通过") : note);
            return get(ticketId);
        }

        // 终审通过或单级通过 → approved（扣库存）
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
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("ticketTable", TICKET);
            row.put("id", ticketId);
            row.put("remark", note);
            row.put("bindAssignee", bind);
            if (bind) row.put("assigneeUsername", op);
            row.put("approveAt", Timestamp.valueOf(approveAt));
            row.put("withDue", hasColumn("due_at"));
            if (hasColumn("due_at")) row.put("dueAt", Timestamp.valueOf(dueAt));
            row.put("withFineYuan", hasColumn("fine_yuan"));
            row.put("withRemindMsg", hasColumn("remind_msg"));
            mapper().updateApproved(row);
        } else {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("ticketTable", TICKET);
            row.put("id", ticketId);
            row.put("remark", note);
            row.put("bindAssignee", bind);
            if (bind) row.put("assigneeUsername", op);
            row.put("withDue", false);
            row.put("withFineYuan", false);
            row.put("withRemindMsg", false);
            mapper().updateApproved(row);
        }
        notifyTicketResult(m, true, note);
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

    /**
     * 通过并扣库存后若余量为 0，驳回同档案其它 pending/pending_final。
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
            ids = mapper().selectSiblingPendingIds(TICKET, itemFkColumn(), itemId, approvedTicketId);
        } catch (Exception e) {
            return 0;
        }
        if (ids == null || ids.isEmpty()) return 0;
        int rejected = 0;
        for (Long sid : ids) {
            if (sid == null || sid <= 0) continue;
            try {
                int n = mapper().updateRejectSibling(TICKET, sid, reason);
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

    /** 完结后评分 1～5 */
    public static Map<String, Object> rate(long ticketId, String username, int rating, String ratingRemark) {
        if (!allowRating) throw new IllegalStateException("当前未开启评分");
        if (rating < 1 || rating > 5) throw new IllegalArgumentException("评分须为 1～5 分");
        if (!hasColumn("rating")) throw new IllegalStateException("当前不支持评分");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!TicketSql.str(m.get("username")).equals(username)) {
            throw new IllegalStateException("只能评价自己的单据");
        }
        if (!"returned".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅「" + TicketCopy.stateLabel("returned", "已完结") + "」单据可评分");
        }
        Object prev = m.get("rating");
        if (prev != null && !"0".equals(String.valueOf(prev)) && !"".equals(String.valueOf(prev))) {
            throw new IllegalStateException("已评价过，不可重复提交");
        }
        String note = ratingRemark == null ? "" : ratingRemark.trim();
        if (note.length() > 255) note = note.substring(0, 255);
        mapper().updateRating(TICKET, ticketId, rating, note);
        String tip = rating + " 分";
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
        mapper().updateCheckin(TICKET, ticketId);
        appendProgress(ticketId, "checkin", username, TicketCopy.CHECKIN_LABEL);
        return get(ticketId);
    }

    /** 审核结果写入申请人站内消息（无表或失败则静默跳过） */
    private static void notifyTicketResult(Map<String, Object> ticket, boolean pass, String note) {
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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("ticketTable", TICKET);
        row.put("id", ticketId);
        row.put("withRemindMsg", hasColumn("remind_msg"));
        row.put("remindMsg", remind);
        mapper().updateComplete(row);
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
            List<Map<String, Object>> open = mapper().selectOpenApprovedOverdue(TICKET);
            if (open != null) {
                for (Map<String, Object> raw : open) {
                    Map<String, Object> b = TicketRowMaps.shape(raw);
                    TicketStatusOps.refreshOverdue(b);
                }
            }
        }

        Map<String, Object> q = new LinkedHashMap<>();
        q.put("ticketTable", TICKET);
        if (username != null && !username.isBlank()) {
            q.put("username", username);
        } else if (!superAdmin && adminUid != null && !adminUid.isBlank() && hasColumn("assignee_username")) {
            // 子管可见范围：待办池全员 / 进行中仅自己 / 终态全员
            boolean historyStatus = isHistoryStatus(status);
            boolean todoPool = status == null || status.isBlank()
                    || "pending".equals(status)
                    || "pending_final".equals(status)
                    || "todo".equals(status);
            q.put("adminUid", adminUid);
            q.put("superAdmin", false);
            q.put("hasAssignee", true);
            q.put("historyStatus", historyStatus);
            q.put("todoPool", todoPool);
            q.put("todoPoolBlank", todoPool && (status == null || status.isBlank()));
        }
        if (status != null && !status.isBlank()) {
            if ("todo".equals(status)) {
                q.put("statusTodo", true);
            } else {
                q.put("statusExact", status);
            }
        }
        if (Boolean.TRUE.equals(ratedOnly) && hasColumn("rating")) {
            q.put("ratedOnly", true);
        }
        PageHelper.startPage(page, size);
        List<Map<String, Object>> rawList = mapper().selectTickets(q);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(rawList == null ? List.of() : rawList);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> raw : pi.getList()) {
            list.add(TicketStatusOps.enrich(TicketRowMaps.shape(raw)));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", pi.getTotal());
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
        PageHelper.startPage(page, size);
        List<Map<String, Object>> rawList = mapper().selectPublicByItem(TICKET, itemFkColumn(), itemId);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(rawList == null ? List.of() : rawList);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> raw : pi.getList()) {
            list.add(TicketStatusOps.enrich(TicketRowMaps.shape(raw)));
        }
        int t = (int) pi.getTotal();
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
                || "noshow".equals(status);
    }

    public static boolean isTodoPoolStatus(String status) {
        return "pending".equals(status) || "pending_final".equals(status) || "todo".equals(status);
    }

    public static Map<String, Object> get(long id) {
        Map<String, Object> m = TicketRowMaps.load(id);
        if (m == null) return null;
        TicketStatusOps.touchTicketStatus(m);
        return TicketStatusOps.enrich(TicketRowMaps.load(id));
    }

    static boolean hasColumn(String col) {
        try {
            Integer n = schema().countColumn(TICKET, col);
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
            mapper().updateContactChannel(TICKET, ticketId, ch);
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
            mapper().updateNextFollowAt(TICKET, ticketId, ts);
        }
    }

    static void ensureColumn(String col, String ddlType) {
        if (hasColumn(col)) return;
        try {
            schema().executeDdl("ALTER TABLE `" + TICKET + "` ADD COLUMN `" + col + "` " + ddlType);
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
            List<Map<String, Object>> open = mapper().selectOpenApprovedOverdue(TICKET);
            if (open != null) {
                for (Map<String, Object> raw : open) {
                    Map<String, Object> b = TicketRowMaps.shape(raw);
                    TicketStatusOps.refreshOverdue(b);
                }
            }
        }
        Long pending = mapper().countPending(TICKET);
        Long approved = mapper().countByStatus(TICKET, "approved");
        Long overdue = useDeadline || noShowAfterEnd
                ? mapper().countByStatus(TICKET, "overdue")
                : 0L;
        Long returned = mapper().countByStatus(TICKET, "returned");
        Long rejected = mapper().countByStatus(TICKET, "rejected");
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
                Double fineOpen = mapper().sumOpenFine(TICKET);
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
            Double avg = mapper().avgRating(TICKET);
            Long ratedCnt = mapper().countRated(TICKET);
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
            List<Map<String, Object>> status = mapper().selectStatusSeries(TICKET);
            out.put("statusSeries", status == null ? List.of() : status);
            List<Map<String, Object>> trend = mapper().selectTrendSeries(TICKET);
            out.put("trendSeries", trend == null ? List.of() : trend);
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
