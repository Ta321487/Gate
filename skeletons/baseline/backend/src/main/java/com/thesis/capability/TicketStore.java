package com.thesis.capability;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.config.JdbcSupport;
import com.thesis.service.MessageStore;
import com.thesis.service.UserStore;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.io.InputStream;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
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

    public enum Mode {
        ARCHIVE,
        STANDALONE
    }

    private static String TICKET = "borrow";
    private static String PROGRESS = "";
    private static Mode MODE = Mode.ARCHIVE;
    private static boolean enabled = false;
    private static boolean useQuota = true;
    private static boolean useDeadline = true;
    /** 允许同一档案多次开单（论坛跟帖等） */
    private static boolean allowMultiTicket = false;
    /** 申请时检测与本人已占用时段是否相交 */
    private static boolean checkTimeConflict = false;
    /** L1：初审 → 终审 */
    private static boolean twoLevelApprove = false;
    /** L1：申请须上传附件 */
    private static boolean requireAttach = false;
    /** L1：完结后可评分 */
    private static boolean allowRating = false;
    /** L1：同 mutex_code 的档案不可同时选 */
    private static boolean checkMutex = false;
    /** L1：同一分类下进行中单据上限；≤0 表示不限 */
    private static int categoryLimit = 0;
    /** L1：签到口令 */
    private static boolean allowCheckin = false;
    /** 活动结束未签到 → 爽约（复用 overdue 状态） */
    private static boolean noShowAfterEnd = false;
    /** 爽约固定费用；0 只改状态 */
    private static double noShowPenaltyYuan = 0;
    /** 申请时可自选到期日（写入 due_at；审批时沿用） */
    private static boolean pickLoanPeriod = false;
    /** 申请时可填数量（扣/还库存按 qty） */
    private static boolean allowQty = false;
    /** 申请须填写说明（用途/跟进/认领事由等） */
    private static boolean requireRemark = false;
    /** 申请须选起止日期（请假等 → period_start/period_end） */
    private static boolean pickDateRange = false;
    private static String userRole = "reader";

    /** bake 注入的 schema 文案（domain-ticket-copy.json），禁止按域 if/else 写死中文 */
    private static final ObjectMapper COPY_JSON = new ObjectMapper();
    private static Map<String, String> STATE_LABELS = Map.of();
    private static Map<String, String> VERB_LABELS = Map.of();
    private static String CHECKIN_LABEL = "签到";
    private static String FINE_PAID_LABEL = "费用已结清";
    private static String ARCHIVE_LABEL = "";
    private static String APPLY_DEADLINE_LABEL = "报名截止";

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

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
        loadCopyFromResource();
        ensureProgressTable();
        ensureL1Columns();
    }

    /** 报修等：无档案占用、无到期催办 */
    public static void bindStandalone(String ticketTable) {
        if (ticketTable != null && !ticketTable.isBlank()) TICKET = ticketTable.trim();
        MODE = Mode.STANDALONE;
        useQuota = false;
        useDeadline = false;
        enabled = true;
        bindProgressDefault();
        loadCopyFromResource();
        ensureProgressTable();
        ensureL1Columns();
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

    private static void bindProgressDefault() {
        PROGRESS = TICKET == null || TICKET.isBlank() ? "" : TICKET + "_progress";
    }

    /** 读取 bake 写入的 domain-ticket-copy.json（states/verbs 文案）。 */
    private static void loadCopyFromResource() {
        try {
            ClassPathResource res = new ClassPathResource("domain-ticket-copy.json");
            if (!res.exists()) return;
            try (InputStream in = res.getInputStream()) {
                Map<String, Object> root = COPY_JSON.readValue(in, new TypeReference<>() {});
                Object st = root.get("states");
                if (st instanceof Map<?, ?> map) {
                    Map<String, String> out = new LinkedHashMap<>();
                    for (Map.Entry<?, ?> e : map.entrySet()) {
                        if (e.getKey() == null || e.getValue() == null) continue;
                        String lab = String.valueOf(e.getValue()).trim();
                        if (!lab.isBlank()) out.put(String.valueOf(e.getKey()), lab);
                    }
                    if (!out.isEmpty()) STATE_LABELS = out;
                }
                Object vb = root.get("verbs");
                if (vb instanceof Map<?, ?> map) {
                    Map<String, String> out = new LinkedHashMap<>();
                    for (Map.Entry<?, ?> e : map.entrySet()) {
                        if (e.getKey() == null || e.getValue() == null) continue;
                        String lab = String.valueOf(e.getValue()).trim();
                        if (!lab.isBlank()) out.put(String.valueOf(e.getKey()), lab);
                    }
                    if (!out.isEmpty()) VERB_LABELS = out;
                }
                String cin = str(root.get("checkinLabel")).trim();
                if (!cin.isBlank()) CHECKIN_LABEL = cin;
                String fp = str(root.get("finePaidLabel")).trim();
                if (!fp.isBlank()) FINE_PAID_LABEL = fp;
                String arch = str(root.get("archiveLabel")).trim();
                if (!arch.isBlank()) ARCHIVE_LABEL = arch;
                String dl = str(root.get("applyDeadlineLabel")).trim();
                if (!dl.isBlank()) APPLY_DEADLINE_LABEL = dl;
                String sl = str(root.get("stockLabel")).trim();
                if (!sl.isBlank()) ArchiveStore.configureStockLabel(sl);
            }
        } catch (Exception ignored) {
        }
    }

    private static String stateLabel(String key, String fallback) {
        if (key == null || key.isBlank()) return fallback;
        String lab = STATE_LABELS.get(key);
        return lab == null || lab.isBlank() ? fallback : lab;
    }

    private static String verbLabel(String key, String fallback) {
        if (key == null || key.isBlank()) return fallback;
        String lab = VERB_LABELS.get(key);
        return lab == null || lab.isBlank() ? fallback : lab;
    }

    private static String archiveNoun() {
        return ARCHIVE_LABEL.isBlank() ? "项目" : ARCHIVE_LABEL;
    }

    /** 幂等建表：未 bake 进 schema 的旧库也能写出进度。 */
    private static void ensureProgressTable() {
        if (PROGRESS == null || PROGRESS.isBlank()) return;
        try {
            db().execute(
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
        if (allowQty) {
            ensureColumn("qty", "INT NOT NULL DEFAULT 1");
        }
    }

    /** 必填说明 + 起止日期（申领用途 / 跟进 / 请假等） */
    public static void configureApplyExtras(boolean remarkRequired, boolean dateRange) {
        requireRemark = remarkRequired;
        pickDateRange = dateRange && MODE == Mode.ARCHIVE;
        if (pickDateRange) {
            ensureColumn("period_start", "DATETIME NULL");
            ensureColumn("period_end", "DATETIME NULL");
        }
    }

    /** L1：互斥码 + 分类限额（选课等） */
    public static void configureRules(boolean mutex, int catLimit) {
        checkMutex = mutex;
        categoryLimit = Math.max(0, catLimit);
        if (checkMutex) {
            ArchiveStore.ensureMutexColumn();
        }
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
        if (enabled) {
            ensureColumn("checked_in_at", "DATETIME NULL");
            ArchiveStore.ensureCheckinCodeColumn();
        }
    }

    public static void configureNoShow(boolean afterEnd, double penaltyYuan) {
        noShowAfterEnd = afterEnd && allowCheckin;
        noShowPenaltyYuan = Math.max(0, penaltyYuan);
        if (noShowAfterEnd) {
            ensureColumn("checked_in_at", "DATETIME NULL");
            ensureColumn("fine_status", "VARCHAR(16) DEFAULT 'none'");
        }
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

    /** 当前单据表名（推荐等跨能力读行为用） */
    public static String ticketTable() {
        return TICKET;
    }

    public static boolean isArchiveMode() {
        return MODE == Mode.ARCHIVE;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static String now() {
        return LocalDateTime.now().format(FMT);
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return (s.isBlank() || "null".equals(s)) ? null : s;
    }

    private static long toLong(Object o) {
        if (o == null) return 0L;
        if (o instanceof Number n) return n.longValue();
        return Long.parseLong(String.valueOf(o));
    }

    private static double toDouble(Object o) {
        if (o == null) return 0.0;
        if (o instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(o));
        } catch (Exception e) {
            return 0.0;
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
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
        assertApplyDeadline(item);
        assertNoTimeConflict(username, itemId, item);
        assertNoMutexConflict(username, itemId, item);
        assertCategoryLimit(username, item);
        assertUnderActiveLimit(username);
        String attach = normalizeAttach(attachUrl);
        LocalDateTime due = resolveRequestedDue(dueAt);
        LocalDateTime[] period = resolvePeriod(periodStart, periodEnd);
        if (!allowMultiTicket) {
            Integer dup = db().queryForObject(
                    "SELECT COUNT(*) FROM " + TICKET
                            + " WHERE username=? AND book_id=? AND status IN ('pending','pending_final','approved','overdue')",
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
        db().update(con -> {
            StringBuilder cols = new StringBuilder("book_id,username,status,apply_at,fine_yuan,remind_msg,remark");
            StringBuilder vals = new StringBuilder("?,?, 'pending', NOW(), 0, '', ?");
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
        appendProgress(id, "pending", username, "用户提交");
        notifyAdminsNewTicket(id, username, subjectOf(get(id)));
        return get(id);
    }

    private static LocalDateTime[] resolvePeriod(String periodStart, String periodEnd) {
        if (!pickDateRange) return null;
        if (periodStart == null || periodStart.isBlank() || periodEnd == null || periodEnd.isBlank()) {
            throw new IllegalStateException("请选择起止日期");
        }
        LocalDateTime start = parseDateTimeFlexible(periodStart.trim(), false);
        LocalDateTime end = parseDateTimeFlexible(periodEnd.trim(), true);
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
        LocalDateTime due = parseDateTimeFlexible(dueAt.trim(), true);
        LocalDateTime now = LocalDateTime.now();
        if (!due.isAfter(now)) {
            throw new IllegalStateException("到期日期须晚于当前时间");
        }
        if (due.isAfter(now.plusDays(90))) {
            throw new IllegalStateException("到期日期不能超过 90 天");
        }
        return due;
    }

    /** @param endOfDay true 时仅日期补 23:59:59，否则补 00:00:00 */
    private static LocalDateTime parseDateTimeFlexible(String raw, boolean endOfDay) {
        String s = raw.length() >= 19 ? raw.substring(0, 19) : raw;
        try {
            if (s.length() == 10) {
                return LocalDateTime.parse(s + (endOfDay ? " 23:59:59" : " 00:00:00"), FMT);
            }
            return LocalDateTime.parse(s, FMT);
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("日期格式无效");
        }
    }

    private static LocalDateTime parseDateTimeFlexible(String raw) {
        return parseDateTimeFlexible(raw, true);
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
        return applyStandalone(username, title, location, remark, typeId, roomId, null);
    }

    public static Map<String, Object> applyStandalone(
            String username,
            String title,
            String location,
            String remark,
            Long typeId,
            Long roomId,
            String attachUrl) {
        if (MODE != Mode.STANDALONE) {
            throw new IllegalStateException("当前为档案关联模式，请使用 apply");
        }
        String t = title == null ? "" : title.trim();
        if (t.isBlank()) throw new IllegalArgumentException("请填写标题");
        assertUnderActiveLimit(username);
        String attach = normalizeAttach(attachUrl);

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
            db().update(con -> {
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
            db().update(con -> {
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
        if (hasColumn("priority") || hasColumn("contact_phone")) {
            // 可选：从 remark 前缀解析不强制；预留列已 ensure
        }
        appendProgress(id, "pending", username, "用户提交");
        notifyAdminsNewTicket(id, username, t);
        return get(id);
    }

    /** 兼容旧调用：仅标题/地点/说明 */
    public static Map<String, Object> applyStandalone(String username, String title, String location, String remark) {
        return applyStandalone(username, title, location, remark, null, null, null);
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
        ensureProgressTable();
        if (PROGRESS == null || PROGRESS.isBlank()) return List.of();
        List<Map<String, Object>> rows = queryProgress(ticketId);
        if (rows.isEmpty()) {
            backfillProgressFromTicket(ticketId);
            rows = queryProgress(ticketId);
        }
        return rows;
    }

    private static List<Map<String, Object>> queryProgress(long ticketId) {
        try {
            return db().query(
                    "SELECT * FROM `" + PROGRESS + "` WHERE ticket_id=? ORDER BY id",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("id", rs.getLong("id"));
                        row.put("ticketId", rs.getLong("ticket_id"));
                        row.put("status", rs.getString("status"));
                        row.put("operator", rs.getString("operator"));
                        row.put("remark", rs.getString("remark"));
                        row.put("createdAt", fmt(rs.getTimestamp("created_at")));
                        return row;
                    },
                    ticketId);
        } catch (Exception e) {
            return List.of();
        }
    }

    /** 旧数据无流水时，按单据时间戳回填一次（各域同一套列，无分支）。 */
    private static void backfillProgressFromTicket(long ticketId) {
        if (ticketId <= 0 || PROGRESS == null || PROGRESS.isBlank()) return;
        try {
            String cols = "username, status, apply_at, approve_at, return_at, assignee_username";
            boolean withRating = hasColumn("rating");
            if (withRating) cols += ", rating, rating_remark, rated_at";
            List<Map<String, Object>> tickets = db().query(
                    "SELECT " + cols + " FROM " + TICKET + " WHERE id=?",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("username", rs.getString("username"));
                        row.put("status", rs.getString("status"));
                        row.put("applyAt", rs.getTimestamp("apply_at"));
                        row.put("approveAt", safeTs(rs, "approve_at"));
                        row.put("returnAt", safeTs(rs, "return_at"));
                        row.put("assignee", safeStr(rs, "assignee_username"));
                        if (withRating) {
                            Integer rating = null;
                            int r = rs.getInt("rating");
                            if (!rs.wasNull()) rating = r;
                            row.put("rating", rating);
                            row.put("ratingRemark", safeStr(rs, "rating_remark"));
                            row.put("ratedAt", safeTs(rs, "rated_at"));
                        }
                        return row;
                    },
                    ticketId);
            if (tickets.isEmpty()) return;
            Map<String, Object> t = tickets.get(0);
            String user = String.valueOf(t.getOrDefault("username", ""));
            String st = String.valueOf(t.getOrDefault("status", ""));
            String assignee = String.valueOf(t.getOrDefault("assignee", ""));
            Timestamp applyAt = (Timestamp) t.get("applyAt");
            Timestamp approveAt = (Timestamp) t.get("approveAt");
            Timestamp returnAt = (Timestamp) t.get("returnAt");
            if (applyAt != null) {
                insertProgressRow(ticketId, "pending", user, "用户提交", applyAt);
            }
            if (approveAt != null) {
                if ("rejected".equals(st)) {
                    insertProgressRow(ticketId, "rejected", blankTo(assignee, "admin"),
                            stateLabel("rejected", "已驳回"), approveAt);
                } else if (!"pending".equals(st) && !"pending_final".equals(st)) {
                    insertProgressRow(ticketId, "approved", blankTo(assignee, "admin"),
                            stateLabel("approved", "审核通过"), approveAt);
                } else if ("pending_final".equals(st)) {
                    insertProgressRow(ticketId, "pending_final", blankTo(assignee, "admin"),
                            stateLabel("pending_final", "初审通过"), approveAt);
                }
            }
            if (returnAt != null) {
                boolean noShow = "overdue".equals(st) && noShowAfterEnd;
                String fin = noShow ? "overdue" : "returned";
                String tip = noShow
                        ? stateLabel("overdue", "爽约")
                        : stateLabel("returned", verbLabel("return", "已完结"));
                insertProgressRow(ticketId, fin, blankTo(assignee, "system"), tip, returnAt);
            } else if ("overdue".equals(st) && noShowAfterEnd) {
                insertProgressRow(ticketId, "overdue", "system",
                        stateLabel("overdue", "爽约"), Timestamp.valueOf(LocalDateTime.now()));
            } else if ("noshow".equals(st)) {
                insertProgressRow(ticketId, "overdue", "system",
                        stateLabel("overdue", "爽约"), Timestamp.valueOf(LocalDateTime.now()));
            }
            Object ratingObj = t.get("rating");
            if (ratingObj instanceof Number rn && rn.intValue() > 0) {
                String tip = rn.intValue() + " 分";
                String note = str(t.get("ratingRemark"));
                if (!note.isBlank()) tip = tip + " · " + note;
                Timestamp ratedAt = (Timestamp) t.get("ratedAt");
                if (ratedAt == null) ratedAt = Timestamp.valueOf(LocalDateTime.now());
                insertProgressRow(ticketId, "rated", user, tip, ratedAt);
            }
        } catch (Exception ignored) {
        }
    }

    private static String blankTo(String s, String fallback) {
        return s == null || s.isBlank() ? fallback : s;
    }

    private static void insertProgressRow(
            long ticketId, String status, String operator, String remark, Timestamp at) {
        if (at == null) at = Timestamp.valueOf(LocalDateTime.now());
        db().update(
                "INSERT INTO `" + PROGRESS + "` (ticket_id,status,operator,remark,created_at) VALUES (?,?,?,?,?)",
                ticketId,
                status == null ? "" : status,
                operator == null ? "" : operator,
                remark == null ? "" : remark,
                at);
    }

    /** 认领/领用：登记领取 */
    public static Map<String, Object> markPickup(long ticketId, String place, Integer actualQty, String operator) {
        Map<String, Object> m = load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String st = String.valueOf(m.get("status"));
        if (!"approved".equals(st) && !"returned".equals(st)) {
            throw new IllegalStateException("仅已通过/完结单据可登记领取");
        }
        String loc = place == null ? "" : place.trim();
        if (loc.isBlank()) loc = configValue("pickup_place");
        if (hasColumn("pickup_at")) {
            if (hasColumn("actual_qty") && actualQty != null && actualQty > 0) {
                db().update(
                        "UPDATE " + TICKET + " SET pickup_at=NOW(), pickup_place=?, actual_qty=? WHERE id=?",
                        loc, actualQty, ticketId);
            } else if (hasColumn("pickup_place")) {
                db().update(
                        "UPDATE " + TICKET + " SET pickup_at=NOW(), pickup_place=? WHERE id=?",
                        loc, ticketId);
            } else {
                db().update("UPDATE " + TICKET + " SET pickup_at=NOW() WHERE id=?", ticketId);
            }
        }
        appendProgress(ticketId, "pickup", operator, "领取登记：" + loc);
        return get(ticketId);
    }

    public static Map<String, Object> markFinePaid(long ticketId, String operator) {
        if (!hasColumn("fine_status")) throw new IllegalStateException("当前不支持逾期费用登记");
        Map<String, Object> m = load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        db().update("UPDATE " + TICKET + " SET fine_status='paid' WHERE id=?", ticketId);
        appendProgress(ticketId, "fine_paid", operator, FINE_PAID_LABEL);
        return get(ticketId);
    }

    private static void appendProgress(long ticketId, String status, String operator, String remark) {
        if (ticketId <= 0) return;
        ensureProgressTable();
        if (PROGRESS == null || PROGRESS.isBlank()) return;
        try {
            insertProgressRow(
                    ticketId,
                    status,
                    operator,
                    remark,
                    Timestamp.valueOf(LocalDateTime.now()));
        } catch (Exception ignored) {
        }
    }

    private static String configValue(String key) {
        try {
            List<String> rows = db().query(
                    "SELECT cfg_value FROM sys_config WHERE cfg_key=? LIMIT 1",
                    (rs, i) -> rs.getString(1), key);
            return rows.isEmpty() || rows.get(0) == null ? "" : rows.get(0);
        } catch (Exception e) {
            return "";
        }
    }

    private static String normalizeAttach(String attachUrl) {
        String attach = attachUrl == null ? "" : attachUrl.trim();
        if (requireAttach && attach.isBlank()) {
            throw new IllegalStateException("请上传附件后再提交");
        }
        if (attach.length() > 255) attach = attach.substring(0, 255);
        return attach;
    }

    private static void assertUnderActiveLimit(String username) {
        // 多开单（跟帖）：只限制待审数量，已展示的回复不占额度
        String statuses = allowMultiTicket
                ? "('pending','pending_final')"
                : "('pending','pending_final','approved','overdue')";
        Integer active = db().queryForObject(
                "SELECT COUNT(*) FROM " + TICKET + " WHERE username=? AND status IN " + statuses,
                Integer.class, username);
        if (active != null && active >= MAX_ACTIVE) {
            throw new IllegalStateException(
                    allowMultiTicket
                            ? "待审核回复不得超过 " + MAX_ACTIVE + " 条，请稍后再发"
                            : "同时进行中的单据不得超过 " + MAX_ACTIVE + " 条");
        }
    }

    private static void assertApplyDeadline(Map<String, Object> item) {
        if (!ArchiveStore.hasApplyDeadline()) return;
        Object raw = item.get("applyDeadlineAt");
        if (raw == null || String.valueOf(raw).isBlank()) return;
        try {
            LocalDateTime deadline = LocalDateTime.parse(String.valueOf(raw).substring(0, 19), FMT);
            if (LocalDateTime.now().isAfter(deadline)) {
                throw new IllegalStateException("已过" + APPLY_DEADLINE_LABEL + "时间");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception ignored) {
            // 解析失败则不拦截
        }
    }

    /** 同互斥码的其它进行中单据不可并存 */
    private static void assertNoMutexConflict(String username, long itemId, Map<String, Object> item) {
        if (!checkMutex || !ArchiveStore.hasMutexCode()) return;
        String code = str(item.get("mutexCode")).trim();
        if (code.isBlank()) return;
        String itemTable = ArchiveStore.itemTable();
        List<String> titles = db().query(
                "SELECT i.title FROM " + TICKET + " t "
                        + "JOIN " + itemTable + " i ON t.book_id=i.id "
                        + "WHERE t.username=? AND t.book_id<>? "
                        + "AND t.status IN ('pending','pending_final','approved','overdue') "
                        + "AND i.mutex_code=? AND i.mutex_code<>''",
                (rs, i) -> rs.getString(1),
                username, itemId, code);
        if (!titles.isEmpty()) {
            throw new IllegalStateException(
                    "互斥冲突：与「" + titles.get(0) + "」同属互斥组「" + code + "」，不可同时选择");
        }
    }

    /** 同一分类下进行中单据不得超过 categoryLimit */
    private static void assertCategoryLimit(String username, Map<String, Object> item) {
        if (categoryLimit <= 0) return;
        long categoryId = 0L;
        Object cid = item.get("categoryId");
        if (cid instanceof Number n) categoryId = n.longValue();
        else {
            try {
                categoryId = Long.parseLong(str(cid));
            } catch (Exception ignored) {
                return;
            }
        }
        if (categoryId <= 0) return;
        String itemTable = ArchiveStore.itemTable();
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM " + TICKET + " t "
                        + "JOIN " + itemTable + " i ON t.book_id=i.id "
                        + "WHERE t.username=? AND t.status IN ('pending','pending_final','approved','overdue') "
                        + "AND i.category_id=?",
                Integer.class, username, categoryId);
        if (n != null && n >= categoryLimit) {
            String catName = str(item.get("categoryName"));
            String hint = catName.isBlank() ? "该分类" : ("分类「" + catName + "」");
            throw new IllegalStateException(
                    hint + "最多可选 " + categoryLimit + " 门，请先退选后再申请");
        }
    }

    /** 区间相交：newStart < oldEnd && oldStart < newEnd */
    private static void assertNoTimeConflict(String username, long itemId, Map<String, Object> item) {
        if (!checkTimeConflict || !ArchiveStore.hasScheduleColumns()) return;
        Object ns = item.get("startAt");
        Object ne = item.get("endAt");
        if (ns == null || ne == null || String.valueOf(ns).isBlank() || String.valueOf(ne).isBlank()) return;
        LocalDateTime newStart;
        LocalDateTime newEnd;
        try {
            newStart = LocalDateTime.parse(String.valueOf(ns).substring(0, 19), FMT);
            newEnd = LocalDateTime.parse(String.valueOf(ne).substring(0, 19), FMT);
        } catch (Exception e) {
            return;
        }
        if (!newEnd.isAfter(newStart)) {
            throw new IllegalStateException("时段配置无效：结束时间须晚于开始时间");
        }
        String itemTable = ArchiveStore.itemTable();
        List<Map<String, Object>> occupied = db().query(
                "SELECT i.title AS title, i.start_at AS start_at, i.end_at AS end_at FROM " + TICKET + " t "
                        + "JOIN " + itemTable + " i ON t.book_id=i.id "
                        + "WHERE t.username=? AND t.book_id<>? AND t.status IN ('pending','pending_final','approved','overdue') "
                        + "AND i.start_at IS NOT NULL AND i.end_at IS NOT NULL",
                (rs, i) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("title", rs.getString("title"));
                    row.put("start", rs.getTimestamp("start_at").toLocalDateTime());
                    row.put("end", rs.getTimestamp("end_at").toLocalDateTime());
                    return row;
                },
                username, itemId);
        for (Map<String, Object> row : occupied) {
            LocalDateTime oldStart = (LocalDateTime) row.get("start");
            LocalDateTime oldEnd = (LocalDateTime) row.get("end");
            if (newStart.isBefore(oldEnd) && oldStart.isBefore(newEnd)) {
                throw new IllegalStateException(
                        "时间冲突：与「" + row.get("title") + "」（"
                                + oldStart.format(FMT) + " ~ " + oldEnd.format(FMT) + "）重叠");
            }
        }
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
        Map<String, Object> m = load(ticketId);
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
            if (bind) {
                db().update(
                        "UPDATE " + TICKET + " SET status='rejected', approve_at=NOW(), remark=?, assignee_username=? WHERE id=?",
                        note, op, ticketId);
            } else {
                db().update(
                        "UPDATE " + TICKET + " SET status='rejected', approve_at=NOW(), remark=? WHERE id=?",
                        note, ticketId);
            }
            notifyTicketResult(m, false, note);
            appendProgress(ticketId, "rejected", op,
                    note == null || note.isBlank() ? stateLabel("rejected", verbLabel("reject", "已驳回")) : note);
            return get(ticketId);
        }

        // 二级：初审通过 → 待终审（不扣库存）
        if (twoLevelApprove && first) {
            if (bind) {
                db().update(
                        "UPDATE " + TICKET + " SET status='pending_final', remark=?, assignee_username=? WHERE id=?",
                        note, op, ticketId);
            } else {
                db().update(
                        "UPDATE " + TICKET + " SET status='pending_final', remark=? WHERE id=?",
                        note, ticketId);
            }
            try {
                String user = str(m.get("username"));
                if (!user.isBlank()) {
                    MessageStore.send(user, "初审已通过", "「" + subjectOf(m) + "」已通过初审，等待终审。",
                            "ticket", toLong(m.get("id")));
                }
                MessageStore.notifyAdmins(
                        "待终审",
                        "「" + subjectOf(m) + "」已通过初审，等待终审。",
                        "ticket",
                        toLong(m.get("id")),
                        op);
            } catch (Exception ignored) {
            }
            appendProgress(ticketId, "pending_final", op, note.isBlank()
                    ? stateLabel("pending_final", "初审通过") : note);
            return get(ticketId);
        }

        // 终审通过或单级通过 → approved（扣库存）
        if (MODE == Mode.ARCHIVE && useQuota) {
            long itemId = toLong(m.get("bookId"));
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            if (item == null) throw new IllegalStateException("对象不存在");
            int stock = item.get("stock") instanceof Number n ? n.intValue() : 0;
            int nQty = rowQty(m);
            if (stock < nQty) throw new IllegalStateException(ArchiveStore.stockShortageNeed(nQty));
            ArchiveStore.adjustStock(itemId, -nQty);
        }
        if (MODE == Mode.ARCHIVE && useDeadline) {
            LocalDateTime approveAt = LocalDateTime.now();
            LocalDateTime dueAt = approveAt.plusDays(LOAN_DAYS);
            Object requested = m.get("dueAt");
            if (requested != null && !String.valueOf(requested).isBlank()) {
                try {
                    dueAt = parseDateTimeFlexible(String.valueOf(requested).trim());
                } catch (Exception ignored) {
                    // 保留默认借期
                }
            }
            if (bind) {
                db().update(
                        "UPDATE " + TICKET + " SET status='approved', approve_at=?, due_at=?, fine_yuan=0, remind_msg='', remark=?, assignee_username=? WHERE id=?",
                        Timestamp.valueOf(approveAt), Timestamp.valueOf(dueAt),
                        note, op, ticketId);
            } else {
                db().update(
                        "UPDATE " + TICKET + " SET status='approved', approve_at=?, due_at=?, fine_yuan=0, remind_msg='', remark=? WHERE id=?",
                        Timestamp.valueOf(approveAt), Timestamp.valueOf(dueAt),
                        note, ticketId);
            }
        } else if (bind) {
            db().update(
                    "UPDATE " + TICKET + " SET status='approved', approve_at=NOW(), remark=?, assignee_username=? WHERE id=?",
                    note, op, ticketId);
        } else {
            db().update(
                    "UPDATE " + TICKET + " SET status='approved', approve_at=NOW(), remark=? WHERE id=?",
                    note, ticketId);
        }
        notifyTicketResult(m, true, note);
        appendProgress(ticketId, "approved", op, note.isBlank()
                ? stateLabel("approved", verbLabel("approve", "审核通过")) : note);
        return get(ticketId);
    }

    private static String subjectOf(Map<String, Object> ticket) {
        String subject = str(ticket.get("title"));
        if (subject.isBlank()) subject = str(ticket.get("bookTitle"));
        if (subject.isBlank()) subject = "单据#" + ticket.get("id");
        return subject;
    }

    /** 完结后评分 1～5 */
    public static Map<String, Object> rate(long ticketId, String username, int rating, String ratingRemark) {
        if (!allowRating) throw new IllegalStateException("当前未开启评分");
        if (rating < 1 || rating > 5) throw new IllegalArgumentException("评分须为 1～5 分");
        if (!hasColumn("rating")) throw new IllegalStateException("当前不支持评分");
        Map<String, Object> m = load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!str(m.get("username")).equals(username)) {
            throw new IllegalStateException("只能评价自己的单据");
        }
        if (!"returned".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅「" + stateLabel("returned", "已完结") + "」单据可评分");
        }
        Object prev = m.get("rating");
        if (prev != null && !"0".equals(String.valueOf(prev)) && !"".equals(String.valueOf(prev))) {
            throw new IllegalStateException("已评价过，不可重复提交");
        }
        String note = ratingRemark == null ? "" : ratingRemark.trim();
        if (note.length() > 255) note = note.substring(0, 255);
        db().update(
                "UPDATE " + TICKET + " SET rating=?, rating_remark=?, rated_at=NOW() WHERE id=?",
                rating, note, ticketId);
        String tip = rating + " 分";
        if (!note.isBlank()) tip = tip + " · " + note;
        appendProgress(ticketId, "rated", username, tip);
        return get(ticketId);
    }

    /** 活动口令签到：本人 + approved + 码匹配 */
    public static Map<String, Object> checkin(long ticketId, String username, String code) {
        if (!allowCheckin) throw new IllegalStateException("当前未开启签到");
        if (!hasColumn("checked_in_at")) throw new IllegalStateException("当前不支持签到");
        Map<String, Object> m = load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!str(m.get("username")).equals(username)) {
            throw new IllegalStateException("只能为自己的单据签到");
        }
        if (!"approved".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅已通过的单据可签到");
        }
        Object prev = m.get("checkedInAt");
        if (prev != null && !String.valueOf(prev).isBlank()) {
            throw new IllegalStateException("已签到，不可重复");
        }
        long itemId = toLong(m.get("bookId"));
        if (itemId <= 0) itemId = toLong(m.get("itemId"));
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalStateException(archiveNoun() + "不存在");
        String expect = str(item.get("checkinCode")).trim();
        if (expect.isBlank()) throw new IllegalStateException(archiveNoun() + "尚未设置签到码");
        String got = code == null ? "" : code.trim();
        if (!expect.equalsIgnoreCase(got)) {
            throw new IllegalStateException("签到码不正确");
        }
        db().update("UPDATE " + TICKET + " SET checked_in_at=NOW() WHERE id=?", ticketId);
        appendProgress(ticketId, "checkin", username, CHECKIN_LABEL);
        return get(ticketId);
    }

    /** 审核结果写入申请人站内消息（无表或失败则静默跳过） */
    private static void notifyTicketResult(Map<String, Object> ticket, boolean pass, String note) {
        try {
            String user = str(ticket.get("username"));
            if (user.isBlank()) return;
            String subject = subjectOf(ticket);
            String title = pass ? "审核已通过" : "审核未通过";
            String body = pass
                    ? ("「" + subject + "」已通过" + (note == null || note.isBlank() ? "" : "：" + note))
                    : ("「" + subject + "」已驳回" + (note == null || note.isBlank() ? "" : "：" + note));
            MessageStore.send(user, title, body, "ticket", toLong(ticket.get("id")));
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
        Map<String, Object> m = load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!asSuperOrOwner && hasColumn("assignee_username")) {
            String asg = str(m.get("assigneeUsername"));
            if (!asg.isBlank() && (actorUid == null || !asg.equals(actorUid))) {
                throw new IllegalStateException("该单已绑定处理人，仅处理人或总管可完结");
            }
        }
        if (useDeadline) refreshOverdue(m);
        String st = String.valueOf(m.get("status"));
        if (!List.of("approved", "overdue").contains(st)) {
            throw new IllegalStateException("仅进行中/逾期可完结");
        }
        if (MODE == Mode.ARCHIVE && useQuota) {
            long itemId = toLong(m.get("bookId"));
            if (ArchiveStore.getItemRaw(itemId) != null) {
                ArchiveStore.adjustStock(itemId, rowQty(m));
            }
        }
        String remind = "";
        if (useDeadline) {
            String doneLab = stateLabel("returned", verbLabel("return", "已完结"));
            remind = toDouble(m.get("fineYuan")) > 0
                    ? doneLab + "，请按登记费用缴纳 " + m.get("fineYuan") + " 元。"
                    : String.valueOf(m.get("remindMsg") == null ? "" : m.get("remindMsg"));
        }
        if (hasColumn("remind_msg")) {
            db().update(
                    "UPDATE " + TICKET + " SET status='returned', return_at=NOW(), remind_msg=? WHERE id=?",
                    remind, ticketId);
        } else {
            db().update(
                    "UPDATE " + TICKET + " SET status='returned', return_at=NOW() WHERE id=?",
                    ticketId);
        }
        appendProgress(ticketId, "returned", actorUid, stateLabel("returned", verbLabel("return", "已完结")));
        return get(ticketId);
    }

    public static Map<String, Object> markOverdue(long ticketId) {
        if (!useDeadline) throw new IllegalStateException("当前不支持到期催办");
        Map<String, Object> m = load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!"approved".equals(m.get("status")) && !"overdue".equals(m.get("status"))) {
            throw new IllegalStateException("仅进行中/逾期可标记");
        }
        m.put("status", "overdue");
        applyFineAndRemind(m, false);
        persistFine(m);
        return get(ticketId);
    }

    public static Map<String, Object> remind(long ticketId) {
        if (!useDeadline) throw new IllegalStateException("当前不支持到期催办");
        Map<String, Object> m = load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        refreshOverdue(m);
        String st = String.valueOf(m.get("status"));
        if (!List.of("approved", "overdue").contains(st)) {
            throw new IllegalStateException("仅进行中/逾期可催办");
        }
        applyFineAndRemind(m, true);
        persistFine(m);
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
            List<Map<String, Object>> open = db().query(
                    "SELECT * FROM " + TICKET + " WHERE status IN ('approved','overdue')",
                    (rs, i) -> mapRow(rs));
            for (Map<String, Object> b : open) refreshOverdue(b);
        }

        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        if (username != null && !username.isBlank()) {
            where.append(" AND username=?");
            args.add(username);
        } else if (!superAdmin && adminUid != null && !adminUid.isBlank() && hasColumn("assignee_username")) {
            // 子管可见范围：
            // - 待办池 pending/pending_final：全员可见（抢单）
            // - 进行中 approved/overdue 等：仅自己绑定
            // - 终态 returned/rejected/noshow：全员可读（含用户「取消报名」）
            boolean historyStatus = isHistoryStatus(status);
            boolean todoPool = status == null || status.isBlank()
                    || "pending".equals(status)
                    || "pending_final".equals(status)
                    || "todo".equals(status);
            if (historyStatus) {
                // 筛终态：不加处理人条件
            } else if (todoPool) {
                if (status == null || status.isBlank()) {
                    where.append(
                            " AND (status IN ('pending','pending_final','returned','rejected','noshow')"
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
                where.append(" AND status IN ('pending','pending_final')");
            } else {
                where.append(" AND status=?");
                args.add(status);
            }
        }
        if (Boolean.TRUE.equals(ratedOnly) && hasColumn("rating")) {
            where.append(" AND rating IS NOT NULL AND rating > 0");
        }
        Integer total = db().queryForObject("SELECT COUNT(*) FROM " + TICKET + where, Integer.class, args.toArray());
        int t = total == null ? 0 : total;
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + TICKET + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> enrich(mapRow(rs)), args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
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
        Map<String, Object> m = load(id);
        if (m == null) return null;
        touchTicketStatus(m);
        return enrich(load(id));
    }

    private static Map<String, Object> load(long id) {
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + TICKET + " WHERE id=?", (rs, i) -> mapRow(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    private static Map<String, Object> mapRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("status", rs.getString("status"));
        m.put("applyAt", fmt(rs.getTimestamp("apply_at")));
        m.put("approveAt", fmt(safeTs(rs, "approve_at")));
        m.put("returnAt", fmt(safeTs(rs, "return_at")));
        m.put("remark", safeStr(rs, "remark"));
        m.put("assigneeUsername", safeStr(rs, "assignee_username"));
        m.put("attachUrl", safeStr(rs, "attach_url"));
        Integer rating = null;
        try {
            int r = rs.getInt("rating");
            if (!rs.wasNull()) rating = r;
        } catch (Exception ignored) {
        }
        m.put("rating", rating);
        m.put("ratingRemark", safeStr(rs, "rating_remark"));
        m.put("ratedAt", fmt(safeTs(rs, "rated_at")));
        m.put("checkedInAt", fmt(safeTs(rs, "checked_in_at")));

        if (MODE == Mode.STANDALONE) {
            m.put("title", safeStr(rs, "title"));
            m.put("location", safeStr(rs, "location"));
            m.put("typeId", safeLong(rs, "type_id"));
            m.put("roomId", safeLong(rs, "room_id"));
            m.put("priority", safeStr(rs, "priority"));
            m.put("contactPhone", safeStr(rs, "contact_phone"));
            long typeId = safeLong(rs, "type_id");
            m.put("typeName", typeId > 0 ? TicketLookupStore.typeName(typeId) : "");
            m.put("itemTitle", safeStr(rs, "title"));
            m.put("bookTitle", safeStr(rs, "title"));
            m.put("bookId", 0L);
            m.put("itemId", 0L);
            m.put("dueAt", null);
            m.put("fineYuan", 0.0);
            m.put("remindedAt", null);
            m.put("remindMsg", "");
        } else {
            long bookId = rs.getLong("book_id");
            m.put("bookId", bookId);
            m.put("itemId", bookId);
            m.put("dueAt", fmt(safeTs(rs, "due_at")));
            m.put("fineYuan", safeDouble(rs, "fine_yuan"));
            m.put("fineStatus", safeStr(rs, "fine_status"));
            m.put("remindedAt", fmt(safeTs(rs, "reminded_at")));
            m.put("remindMsg", safeStr(rs, "remind_msg"));
            m.put("pickupAt", fmt(safeTs(rs, "pickup_at")));
            m.put("pickupPlace", safeStr(rs, "pickup_place"));
            m.put("contactChannel", safeStr(rs, "contact_channel"));
            m.put("nextFollowAt", fmt(safeTs(rs, "next_follow_at")));
            try {
                int aq = rs.getInt("actual_qty");
                if (!rs.wasNull()) m.put("actualQty", aq);
            } catch (Exception ignored) {
            }
            int qty = 1;
            try {
                int q = rs.getInt("qty");
                if (!rs.wasNull() && q > 0) qty = q;
            } catch (Exception ignored) {
            }
            m.put("qty", qty);
            Map<String, Object> item = ArchiveStore.getItemRaw(bookId);
            m.put("bookTitle", item == null ? "" : item.get("title"));
            m.put("itemTitle", item == null ? "" : item.get("title"));
            m.put("title", item == null ? "" : str(item.get("title")));
            m.put("location", "");
            String periodStart = fmt(safeTs(rs, "period_start"));
            String periodEnd = fmt(safeTs(rs, "period_end"));
            if (periodStart != null || periodEnd != null) {
                m.put("periodStart", periodStart);
                m.put("periodEnd", periodEnd);
                m.put("startAt", periodStart);
                m.put("endAt", periodEnd);
            } else if (item != null) {
                m.put("startAt", item.get("startAt"));
                m.put("endAt", item.get("endAt"));
                m.put("applyDeadlineAt", item.get("applyDeadlineAt"));
            }
        }
        return m;
    }

    private static Timestamp safeTs(java.sql.ResultSet rs, String col) {
        try {
            return rs.getTimestamp(col);
        } catch (Exception e) {
            return null;
        }
    }

    private static String safeStr(java.sql.ResultSet rs, String col) {
        try {
            String v = rs.getString(col);
            return v == null ? "" : v;
        } catch (Exception e) {
            return "";
        }
    }

    private static double safeDouble(java.sql.ResultSet rs, String col) {
        try {
            return rs.getDouble(col);
        } catch (Exception e) {
            return 0.0;
        }
    }

    private static long safeLong(java.sql.ResultSet rs, String col) {
        try {
            long v = rs.getLong(col);
            return rs.wasNull() ? 0L : v;
        } catch (Exception e) {
            return 0L;
        }
    }

    private static boolean hasColumn(String col) {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=? AND COLUMN_NAME=?",
                    Integer.class, TICKET, col);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static void ensureL1Columns() {
        ensureColumn("attach_url", "VARCHAR(255) NOT NULL DEFAULT ''");
        ensureColumn("rating", "INT NULL");
        ensureColumn("rating_remark", "VARCHAR(255) NOT NULL DEFAULT ''");
        ensureColumn("rated_at", "DATETIME NULL");
        ensureColumn("priority", "VARCHAR(16) DEFAULT '普通'");
        ensureColumn("contact_phone", "VARCHAR(20) DEFAULT ''");
        ensureColumn("fine_status", "VARCHAR(16) DEFAULT 'none'");
        ensureColumn("pickup_at", "DATETIME NULL");
        ensureColumn("pickup_place", "VARCHAR(128) DEFAULT ''");
        ensureColumn("actual_qty", "INT NULL");
        ensureColumn("contact_channel", "VARCHAR(32) DEFAULT ''");
        ensureColumn("next_follow_at", "DATETIME NULL");
        if (allowCheckin) {
            ensureColumn("checked_in_at", "DATETIME NULL");
        }
    }

    /** CRM 等：申请后补写可选列 */
    public static void patchTicketExtras(long ticketId, Map<String, Object> body) {
        if (ticketId <= 0 || body == null || body.isEmpty()) return;
        if (hasColumn("contact_channel") && body.containsKey("contactChannel")) {
            String ch = str(body.get("contactChannel")).trim();
            if (ch.length() > 32) ch = ch.substring(0, 32);
            db().update("UPDATE " + TICKET + " SET contact_channel=? WHERE id=?", ch, ticketId);
        }
        if (hasColumn("next_follow_at") && body.containsKey("nextFollowAt")) {
            Timestamp ts = null;
            Object raw = body.get("nextFollowAt");
            if (raw != null && !String.valueOf(raw).isBlank()) {
                try {
                    ts = Timestamp.valueOf(parseDateTimeFlexible(String.valueOf(raw).trim(), false));
                } catch (Exception ignored) {
                    ts = null;
                }
            }
            db().update("UPDATE " + TICKET + " SET next_follow_at=? WHERE id=?", ts, ticketId);
        }
    }

    private static void ensureColumn(String col, String ddlType) {
        if (hasColumn(col)) return;
        try {
            db().execute("ALTER TABLE " + TICKET + " ADD COLUMN " + col + " " + ddlType);
        } catch (Exception ignored) {
        }
    }

    private static Map<String, Object> enrich(Map<String, Object> b) {
        Map<String, Object> m = new LinkedHashMap<>(b);
        touchTicketStatus(m);
        if (useDeadline) {
            m.put("loanDays", LOAN_DAYS);
            m.put("finePerDay", FINE_PER_DAY);
        }
        if (noShowAfterEnd && noShowPenaltyYuan > 0) {
            m.put("noShowPenaltyYuan", noShowPenaltyYuan);
        }
        m.put("mode", MODE.name().toLowerCase());
        Object u = m.get("username");
        if (u != null && !String.valueOf(u).isBlank()) {
            m.put("displayName", UserStore.displayName(String.valueOf(u)));
        }
        return m;
    }

    /** 列表/详情时推进逾期或爽约状态 */
    private static void touchTicketStatus(Map<String, Object> m) {
        if (m == null) return;
        if (useDeadline) refreshOverdue(m);
        if (noShowAfterEnd) refreshNoShow(m);
    }

    private static void refreshOverdue(Map<String, Object> m) {
        if (!useDeadline) return;
        String st = String.valueOf(m.get("status"));
        if (!"approved".equals(st) && !"overdue".equals(st)) return;
        Object due = m.get("dueAt");
        if (due == null || String.valueOf(due).isBlank()) return;
        LocalDateTime dueAt = LocalDateTime.parse(String.valueOf(due), FMT);
        if (LocalDateTime.now().isAfter(dueAt)) {
            m.put("status", "overdue");
            applyFineAndRemind(m, false);
            persistFine(m);
        }
    }

    /**
     * 活动结束仍未签到 → overdue（文案多为「爽约」）+ 可选固定费用。
     * 与借还逾期互斥场景：活动域通常 useDeadline=false。
     */
    private static void refreshNoShow(Map<String, Object> m) {
        if (!noShowAfterEnd || !allowCheckin) return;
        String st = String.valueOf(m.get("status"));
        if (!"approved".equals(st)) return;
        Object checked = m.get("checkedInAt");
        if (checked != null && !String.valueOf(checked).isBlank()) return;
        long itemId = toLong(m.get("bookId"));
        if (itemId <= 0) itemId = toLong(m.get("itemId"));
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) return;
        String endStr = str(item.get("endAt"));
        if (endStr.isBlank()) return;
        LocalDateTime endAt;
        try {
            endAt = LocalDateTime.parse(endStr.length() == 10 ? endStr + " 23:59:59" : endStr, FMT);
        } catch (Exception e) {
            return;
        }
        if (!LocalDateTime.now().isAfter(endAt)) return;
        m.put("status", "overdue");
        double penalty = noShowPenaltyYuan;
        m.put("fineYuan", penalty);
        String overdueLab = stateLabel("overdue", "爽约");
        String msg = penalty > 0
                ? archiveNoun() + "已结束且未签到，记为" + overdueLab + "；费用 " + penalty + " 元。"
                : archiveNoun() + "已结束且未签到，记为" + overdueLab + "。";
        m.put("remindMsg", msg);
        persistFine(m);
        try {
            appendProgress(toLong(m.get("id")), "overdue", "system", msg);
        } catch (Exception ignored) {
        }
    }

    private static void applyFineAndRemind(Map<String, Object> m, boolean forceRemind) {
        double fine = calcFineYuan(m);
        m.put("fineYuan", fine);
        String msg;
        if (fine > 0) {
            msg = "已逾期，请尽快处理。当前预估费用 " + fine + " 元（" + FINE_PER_DAY + " 元/天）。";
        } else {
            msg = "请于到期日前处理，逾期将按 " + FINE_PER_DAY + " 元/天计费。";
        }
        if (forceRemind) {
            m.put("remindedAt", now());
            m.put("remindMsg", "【催办】" + msg);
        } else {
            m.put("remindMsg", msg);
        }
    }

    private static void persistFine(Map<String, Object> m) {
        Object reminded = m.get("remindedAt");
        Timestamp remindedTs = null;
        if (reminded != null && !String.valueOf(reminded).isBlank()) {
            remindedTs = Timestamp.valueOf(LocalDateTime.parse(String.valueOf(reminded), FMT));
        }
        db().update(
                "UPDATE " + TICKET + " SET status=?, fine_yuan=?, remind_msg=?, reminded_at=? WHERE id=?",
                m.get("status"), toDouble(m.get("fineYuan")),
                String.valueOf(m.get("remindMsg") == null ? "" : m.get("remindMsg")),
                remindedTs, m.get("id"));
    }

    private static double calcFineYuan(Map<String, Object> m) {
        Object due = m.get("dueAt");
        if (due == null || String.valueOf(due).isBlank()) return 0.0;
        LocalDateTime dueAt = LocalDateTime.parse(String.valueOf(due), FMT);
        LocalDateTime end = m.get("returnAt") != null && !String.valueOf(m.get("returnAt")).isBlank()
                ? LocalDateTime.parse(String.valueOf(m.get("returnAt")), FMT)
                : LocalDateTime.now();
        long days = ChronoUnit.DAYS.between(dueAt.toLocalDate(), end.toLocalDate());
        if (days <= 0) return 0.0;
        return Math.round(days * FINE_PER_DAY * 10.0) / 10.0;
    }

    public static Map<String, Object> dashboard(String readerRole) {
        if (!enabled) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("pendingTickets", 0);
            empty.put("activeTickets", 0);
            empty.put("completedTickets", 0);
            empty.put("userTotal", UserStore.countByRole(
                    readerRole == null || readerRole.isBlank() ? userRole : readerRole));
            empty.put("bookTotal", ArchiveStore.countItems());
            empty.put("stockTotal", ArchiveStore.sumStock());
            empty.put("categoryTotal", ArchiveStore.countCategories());
            return empty;
        }
        String role = readerRole == null || readerRole.isBlank() ? userRole : readerRole;
        if (useDeadline) {
            db().query("SELECT * FROM " + TICKET + " WHERE status IN ('approved','overdue')",
                    (rs, i) -> {
                        Map<String, Object> b = mapRow(rs);
                        refreshOverdue(b);
                        return b;
                    });
        }
        Long pending = db().queryForObject(
                "SELECT COUNT(*) FROM " + TICKET + " WHERE status IN ('pending','pending_final')", Long.class);
        Long approved = db().queryForObject("SELECT COUNT(*) FROM " + TICKET + " WHERE status='approved'", Long.class);
        Long overdue = useDeadline
                ? db().queryForObject("SELECT COUNT(*) FROM " + TICKET + " WHERE status='overdue'", Long.class)
                : 0L;
        Long returned = db().queryForObject("SELECT COUNT(*) FROM " + TICKET + " WHERE status='returned'", Long.class);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("pendingTickets", pending == null ? 0 : pending);
        m.put("activeTickets", approved == null ? 0 : approved);
        m.put("completedTickets", returned == null ? 0 : returned);
        m.put("userTotal", UserStore.countByRole(role));
        m.put("pendingBorrow", pending == null ? 0 : pending);
        m.put("onLoan", approved == null ? 0 : approved);
        m.put("overdueBorrow", overdue == null ? 0 : overdue);
        m.put("returnedBorrow", returned == null ? 0 : returned);
        m.put("readerTotal", UserStore.countByRole(role));
        if (MODE == Mode.ARCHIVE) {
            m.put("bookTotal", ArchiveStore.countItems());
            m.put("stockTotal", ArchiveStore.sumStock());
            m.put("categoryTotal", ArchiveStore.countCategories());
            if (useDeadline) {
                Double fineOpen = db().queryForObject(
                        "SELECT COALESCE(SUM(fine_yuan),0) FROM " + TICKET + " WHERE status='overdue'", Double.class);
                m.put("openFineYuan", Math.round((fineOpen == null ? 0 : fineOpen) * 10.0) / 10.0);
                m.put("loanDays", LOAN_DAYS);
                m.put("finePerDay", FINE_PER_DAY);
            }
        } else {
            m.put("bookTotal", 0);
            m.put("stockTotal", 0);
            m.put("categoryTotal", 0);
            m.put("openFineYuan", 0);
        }
        m.put("mode", MODE.name().toLowerCase());
        if (allowRating && hasColumn("rating")) {
            Double avg = db().queryForObject(
                    "SELECT AVG(rating) FROM " + TICKET + " WHERE rating IS NOT NULL AND rating > 0",
                    Double.class);
            Long ratedCnt = db().queryForObject(
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
            List<Map<String, Object>> status = db().query(
                    "SELECT status AS name, COUNT(*) AS value FROM " + TICKET + " GROUP BY status",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("name", rs.getString("name"));
                        row.put("value", rs.getLong("value"));
                        return row;
                    });
            out.put("statusSeries", status);
            List<Map<String, Object>> trend = db().query(
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
                    typeId = toLong(types.get(0).get("id"));
                    roomId = toLong(units.get(0).get("id"));
                }
                Map<String, Object> br = applyStandalone(user, "门禁自检报修", "测试地点", "gate", typeId, roomId);
                long bid = toLong(br.get("id"));
                approve(bid, true, "gate");
                complete(bid);
                Map<String, Object> done = get(bid);
                return done != null && "returned".equals(done.get("status"));
            }
            Map<String, Object> page = ArchiveStore.pageItems(null, null, 1, 1);
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> list = (List<Map<String, Object>>) page.get("list");
            if (list == null || list.isEmpty()) return false;
            long itemId = toLong(list.get(0).get("id"));
            String user = "gate_" + System.currentTimeMillis();
            Map<String, Object> br = apply(user, itemId);
            long bid = toLong(br.get("id"));
            approve(bid, true, "gate");
            complete(bid);
            Map<String, Object> done = get(bid);
            return done != null && "returned".equals(done.get("status"));
        } catch (Exception e) {
            return false;
        }
    }
}
