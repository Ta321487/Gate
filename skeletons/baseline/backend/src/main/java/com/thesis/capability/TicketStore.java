package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import com.thesis.service.MessageStore;
import com.thesis.service.UserStore;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

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
    private static Mode MODE = Mode.ARCHIVE;
    private static boolean useQuota = true;
    private static boolean useDeadline = true;
    /** 允许同一档案多次开单（论坛跟帖等） */
    private static boolean allowMultiTicket = false;
    /** 申请时检测与本人已占用时段是否相交 */
    private static boolean checkTimeConflict = false;
    private static String userRole = "reader";

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
    }

    /** 报修等：无档案占用、无到期催办 */
    public static void bindStandalone(String ticketTable) {
        if (ticketTable != null && !ticketTable.isBlank()) TICKET = ticketTable.trim();
        MODE = Mode.STANDALONE;
        useQuota = false;
        useDeadline = false;
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
        return apply(username, itemId, "");
    }

    public static Map<String, Object> apply(String username, long itemId, String remark) {
        if (MODE != Mode.ARCHIVE) {
            throw new IllegalStateException("当前为独立工单模式，请使用 applyStandalone");
        }
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        int stock = item.get("stock") instanceof Number n ? n.intValue() : Integer.parseInt(String.valueOf(item.get("stock")));
        if (useQuota && stock <= 0) throw new IllegalStateException("库存不足");
        assertApplyDeadline(item);
        assertNoTimeConflict(username, itemId, item);
        assertUnderActiveLimit(username);
        if (!allowMultiTicket) {
            Integer dup = db().queryForObject(
                    "SELECT COUNT(*) FROM " + TICKET + " WHERE username=? AND book_id=? AND status IN ('pending','approved','overdue')",
                    Integer.class, username, itemId);
            if (dup != null && dup > 0) throw new IllegalStateException("该对象已有进行中的单据");
        }

        String note = remark == null ? "" : remark.trim();
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + TICKET + " (book_id,username,status,apply_at,fine_yuan,remind_msg,remark) "
                            + "VALUES (?,?, 'pending', NOW(), 0, '', ?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, itemId);
            ps.setString(2, username);
            ps.setString(3, note);
            return ps;
        }, kh);
        Number key = kh.getKey();
        return get(key == null ? 0L : key.longValue());
    }

    /** standalone 模式：报修等；优先用楼栋/房间/类型 FK，地点由房间拼出 */
    public static Map<String, Object> applyStandalone(
            String username,
            String title,
            String location,
            String remark,
            Long typeId,
            Long roomId) {
        if (MODE != Mode.STANDALONE) {
            throw new IllegalStateException("当前为档案关联模式，请使用 apply");
        }
        String t = title == null ? "" : title.trim();
        if (t.isBlank()) throw new IllegalArgumentException("请填写标题");
        assertUnderActiveLimit(username);

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

        KeyHolder kh = new GeneratedKeyHolder();
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
        Number key = kh.getKey();
        return get(key == null ? 0L : key.longValue());
    }

    /** 兼容旧调用：仅标题/地点/说明 */
    public static Map<String, Object> applyStandalone(String username, String title, String location, String remark) {
        return applyStandalone(username, title, location, remark, null, null);
    }

    private static void assertUnderActiveLimit(String username) {
        // 多开单（跟帖）：只限制待审数量，已展示的回复不占额度
        String statuses = allowMultiTicket
                ? "('pending')"
                : "('pending','approved','overdue')";
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
                throw new IllegalStateException("已过报名/选课截止时间");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception ignored) {
            // 解析失败则不拦截
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
                        + "WHERE t.username=? AND t.book_id<>? AND t.status IN ('pending','approved','overdue') "
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
        return approve(ticketId, pass, remark, null);
    }

    /**
     * 审批。通过/驳回时若有 assignee_username 列，将单绑定到 operator（受理人=处理人）。
     */
    public static Map<String, Object> approve(long ticketId, boolean pass, String remark, String operator) {
        Map<String, Object> m = load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!"pending".equals(m.get("status"))) throw new IllegalStateException("仅待审核可审批");
        String op = operator == null ? "" : operator.trim();
        boolean bind = !op.isBlank() && hasColumn("assignee_username");
        String note = remark == null ? "" : remark.trim();
        if (!pass && note.isBlank()) {
            throw new IllegalStateException("请填写驳回原因");
        }
        // 受理未填备注时保留申请人原说明，避免被空串覆盖
        if (pass && note.isBlank()) {
            Object prev = m.get("remark");
            note = prev == null ? "" : String.valueOf(prev);
        }
        if (pass) {
            if (MODE == Mode.ARCHIVE && useQuota) {
                long itemId = toLong(m.get("bookId"));
                Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
                if (item == null) throw new IllegalStateException("对象不存在");
                int stock = item.get("stock") instanceof Number n ? n.intValue() : 0;
                if (stock <= 0) throw new IllegalStateException("库存不足，无法通过");
                ArchiveStore.adjustStock(itemId, -1);
            }
            if (MODE == Mode.ARCHIVE && useDeadline) {
                LocalDateTime approveAt = LocalDateTime.now();
                LocalDateTime dueAt = approveAt.plusDays(LOAN_DAYS);
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
        } else if (bind) {
            db().update(
                    "UPDATE " + TICKET + " SET status='rejected', approve_at=NOW(), remark=?, assignee_username=? WHERE id=?",
                    note, op, ticketId);
        } else {
            db().update(
                    "UPDATE " + TICKET + " SET status='rejected', approve_at=NOW(), remark=? WHERE id=?",
                    note, ticketId);
        }
        notifyTicketResult(m, pass, note);
        return get(ticketId);
    }

    /** 审核结果写入申请人站内消息（无表或失败则静默跳过） */
    private static void notifyTicketResult(Map<String, Object> ticket, boolean pass, String note) {
        try {
            String user = str(ticket.get("username"));
            if (user.isBlank()) return;
            String subject = str(ticket.get("title"));
            if (subject.isBlank()) subject = str(ticket.get("bookTitle"));
            if (subject.isBlank()) subject = "单据#" + ticket.get("id");
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
                ArchiveStore.adjustStock(itemId, 1);
            }
        }
        String remind = "";
        if (useDeadline) {
            remind = toDouble(m.get("fineYuan")) > 0
                    ? "已完结，请按登记费用缴纳 " + m.get("fineYuan") + " 元。"
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
        return get(ticketId);
    }

    public static Map<String, Object> markOverdue(long ticketId) {
        if (!useDeadline) throw new IllegalStateException("当前领域未启用到期催办");
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
        if (!useDeadline) throw new IllegalStateException("当前领域未启用到期催办");
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
        return page(username, status, page, size, null, true);
    }

    /**
     * @param username 业务用户视角：只看自己的单；管理员传 null
     * @param adminUid 子管用户名；总管传 null 或配合 superAdmin=true
     * @param superAdmin 总管看全部；子管：待办池全可见，已受理及之后只看自己绑定的
     */
    public static Map<String, Object> page(
            String username, String status, int page, int size, String adminUid, boolean superAdmin) {
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
            // 子管：待办公开池；其它状态仅自己绑定的单
            if (status != null && !status.isBlank()) {
                if (!"pending".equals(status)) {
                    where.append(" AND assignee_username=?");
                    args.add(adminUid);
                }
            } else {
                where.append(" AND (status='pending' OR assignee_username=?)");
                args.add(adminUid);
            }
        }
        if (status != null && !status.isBlank()) {
            where.append(" AND status=?");
            args.add(status);
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

    public static Map<String, Object> get(long id) {
        Map<String, Object> m = load(id);
        if (m == null) return null;
        if (useDeadline) refreshOverdue(m);
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

        if (MODE == Mode.STANDALONE) {
            m.put("title", safeStr(rs, "title"));
            m.put("location", safeStr(rs, "location"));
            m.put("typeId", safeLong(rs, "type_id"));
            m.put("roomId", safeLong(rs, "room_id"));
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
            m.put("remindedAt", fmt(safeTs(rs, "reminded_at")));
            m.put("remindMsg", safeStr(rs, "remind_msg"));
            Map<String, Object> item = ArchiveStore.getItemRaw(bookId);
            m.put("bookTitle", item == null ? "" : item.get("title"));
            m.put("itemTitle", item == null ? "" : item.get("title"));
            m.put("title", item == null ? "" : str(item.get("title")));
            m.put("location", "");
            if (item != null) {
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
            return MODE == Mode.ARCHIVE;
        }
    }

    private static Map<String, Object> enrich(Map<String, Object> b) {
        Map<String, Object> m = new LinkedHashMap<>(b);
        if (useDeadline) {
            m.put("loanDays", LOAN_DAYS);
            m.put("finePerDay", FINE_PER_DAY);
        }
        m.put("mode", MODE.name().toLowerCase());
        return m;
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
        String role = readerRole == null || readerRole.isBlank() ? userRole : readerRole;
        if (useDeadline) {
            db().query("SELECT * FROM " + TICKET + " WHERE status IN ('approved','overdue')",
                    (rs, i) -> {
                        Map<String, Object> b = mapRow(rs);
                        refreshOverdue(b);
                        return b;
                    });
        }
        Long pending = db().queryForObject("SELECT COUNT(*) FROM " + TICKET + " WHERE status='pending'", Long.class);
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
        return m;
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
