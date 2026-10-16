package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 基线公告（MySQL sys_notice）。过期下架 / 强制弹窗 / 简易富文本格式。
 */
public class NoticeStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static Boolean hasAuditStatus;
    private static Boolean hasSubmitterUsername;
    private static Boolean hasPinned;
    private static Boolean hasExpireAt;
    private static Boolean hasForceAck;
    private static Boolean hasContentFmt;
    private static Boolean hasAckTable;

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    private static Timestamp parseTs(String s) {
        if (s == null || s.isBlank()) return null;
        String t = s.trim().replace('T', ' ');
        if (t.length() == 16) t = t + ":00";
        try {
            return Timestamp.valueOf(LocalDateTime.parse(t, FMT));
        } catch (Exception e) {
            return null;
        }
    }

    private static Map<String, Object> row(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("title", rs.getString("title"));
        m.put("content", rs.getString("content"));
        m.put("publisherUsername", rs.getString("publisher_username"));
        m.put("publisherName", rs.getString("publisher_name"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        m.put("updatedAt", fmt(rs.getTimestamp("updated_at")));
        if (hasPinned()) {
            try {
                m.put("pinned", rs.getInt("pinned") > 0);
            } catch (Exception ignored) {
                m.put("pinned", false);
            }
        } else {
            m.put("pinned", false);
        }
        if (hasExpireAt()) {
            try {
                m.put("expireAt", fmt(rs.getTimestamp("expire_at")));
            } catch (Exception ignored) {
                m.put("expireAt", null);
            }
        } else {
            m.put("expireAt", null);
        }
        if (hasForceAck()) {
            try {
                m.put("forceAck", rs.getInt("force_ack") > 0);
            } catch (Exception ignored) {
                m.put("forceAck", false);
            }
        } else {
            m.put("forceAck", false);
        }
        if (hasContentFmt()) {
            try {
                String cf = rs.getString("content_fmt");
                m.put("contentFmt", cf == null || cf.isBlank() ? "text" : cf.trim());
            } catch (Exception ignored) {
                m.put("contentFmt", "text");
            }
        } else {
            m.put("contentFmt", "text");
        }
        if (hasAuditStatus()) {
            try {
                String as = rs.getString("audit_status");
                m.put("auditStatus", as == null ? "" : as);
            } catch (Exception ignored) {
                m.put("auditStatus", "");
            }
        }
        if (hasSubmitterUsername()) {
            try {
                String su = rs.getString("submitter_username");
                m.put("submitterUsername", su == null ? "" : su);
            } catch (Exception ignored) {
                m.put("submitterUsername", "");
            }
        }
        return m;
    }

    public static boolean hasAuditStatus() {
        if (hasAuditStatus == null) hasAuditStatus = hasNoticeColumn("audit_status");
        return hasAuditStatus;
    }

    public static boolean hasSubmitterUsername() {
        if (hasSubmitterUsername == null) hasSubmitterUsername = hasNoticeColumn("submitter_username");
        return hasSubmitterUsername;
    }

    public static boolean hasPinned() {
        ensurePinnedColumn();
        return hasPinned != null && hasPinned;
    }

    public static boolean hasExpireAt() {
        ensureXm02Columns();
        return hasExpireAt != null && hasExpireAt;
    }

    public static boolean hasForceAck() {
        ensureXm02Columns();
        return hasForceAck != null && hasForceAck;
    }

    public static boolean hasContentFmt() {
        ensureXm02Columns();
        return hasContentFmt != null && hasContentFmt;
    }

    private static synchronized void ensurePinnedColumn() {
        if (hasPinned != null) return;
        if (hasNoticeColumn("pinned")) {
            hasPinned = true;
            return;
        }
        try {
            db().execute("ALTER TABLE sys_notice ADD COLUMN pinned TINYINT NOT NULL DEFAULT 0");
            hasPinned = true;
        } catch (Exception e) {
            hasPinned = hasNoticeColumn("pinned");
        }
    }

    private static synchronized void ensureXm02Columns() {
        if (hasExpireAt != null && hasForceAck != null && hasContentFmt != null) return;
        if (hasExpireAt == null) {
            if (!hasNoticeColumn("expire_at")) {
                try {
                    db().execute("ALTER TABLE sys_notice ADD COLUMN expire_at DATETIME NULL");
                } catch (Exception ignored) {
                }
            }
            hasExpireAt = hasNoticeColumn("expire_at");
        }
        if (hasForceAck == null) {
            if (!hasNoticeColumn("force_ack")) {
                try {
                    db().execute("ALTER TABLE sys_notice ADD COLUMN force_ack TINYINT NOT NULL DEFAULT 0");
                } catch (Exception ignored) {
                }
            }
            hasForceAck = hasNoticeColumn("force_ack");
        }
        if (hasContentFmt == null) {
            if (!hasNoticeColumn("content_fmt")) {
                try {
                    db().execute("ALTER TABLE sys_notice ADD COLUMN content_fmt VARCHAR(16) NOT NULL DEFAULT 'text'");
                } catch (Exception ignored) {
                }
            }
            hasContentFmt = hasNoticeColumn("content_fmt");
        }
        ensureAckTable();
    }

    private static synchronized void ensureAckTable() {
        if (hasAckTable != null) return;
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS sys_notice_ack ("
                            + "notice_id BIGINT NOT NULL,"
                            + "username VARCHAR(64) NOT NULL,"
                            + "acked_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "PRIMARY KEY (notice_id, username),"
                            + "KEY idx_notice_ack_user (username)"
                            + ")");
            hasAckTable = true;
        } catch (Exception e) {
            hasAckTable = false;
        }
    }

    private static boolean hasNoticeColumn(String col) {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE()"
                            + " AND TABLE_NAME='sys_notice' AND COLUMN_NAME=?",
                    Integer.class, col);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    /** 门户可见：未过期（无 expire_at 列则不过滤）。 */
    public static boolean isPortalVisible(Map<String, Object> m) {
        if (m == null) return false;
        if (!hasExpireAt()) return true;
        String exp = m.get("expireAt") == null ? null : String.valueOf(m.get("expireAt"));
        if (exp == null || exp.isBlank() || "null".equals(exp)) return true;
        Timestamp ts = parseTs(exp);
        if (ts == null) return true;
        return ts.after(new Timestamp(System.currentTimeMillis()));
    }

    public static Map<String, Object> add(String title, String content, String publisherUsername, String publisherName) {
        return add(title, content, publisherUsername, publisherName, null, null, null, null, null);
    }

    public static Map<String, Object> add(
            String title,
            String content,
            String publisherUsername,
            String publisherName,
            String auditStatus,
            String submitterUsername) {
        return add(title, content, publisherUsername, publisherName, auditStatus, submitterUsername, null, null, null);
    }

    public static Map<String, Object> add(
            String title,
            String content,
            String publisherUsername,
            String publisherName,
            String auditStatus,
            String submitterUsername,
            String expireAt,
            Boolean forceAck,
            String contentFmt) {
        String name = publisherName == null || publisherName.isBlank()
                ? (publisherUsername == null ? "系统" : publisherUsername)
                : publisherName;
        KeyHolder kh = new GeneratedKeyHolder();
        boolean withAudit = hasAuditStatus();
        String audit = auditStatus == null || auditStatus.isBlank() ? "approved" : auditStatus.trim();
        String submitter = submitterUsername == null ? "" : submitterUsername.trim();
        String fmtVal = normalizeContentFmt(contentFmt);
        Timestamp exp = parseTs(expireAt);
        int force = Boolean.TRUE.equals(forceAck) ? 1 : 0;
        ensureXm02Columns();
        db().update(con -> {
            PreparedStatement ps;
            if (withAudit && hasSubmitterUsername() && hasExpireAt() && hasForceAck() && hasContentFmt()) {
                ps = con.prepareStatement(
                        "INSERT INTO sys_notice (title,content,publisher_username,publisher_name,audit_status,submitter_username,"
                                + "expire_at,force_ack,content_fmt) VALUES (?,?,?,?,?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, title == null ? "" : title);
                ps.setString(2, content == null ? "" : content);
                ps.setString(3, publisherUsername == null ? "" : publisherUsername);
                ps.setString(4, name);
                ps.setString(5, audit);
                ps.setString(6, submitter);
                ps.setTimestamp(7, exp);
                ps.setInt(8, force);
                ps.setString(9, fmtVal);
            } else if (withAudit && hasSubmitterUsername()) {
                ps = con.prepareStatement(
                        "INSERT INTO sys_notice (title,content,publisher_username,publisher_name,audit_status,submitter_username) "
                                + "VALUES (?,?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, title == null ? "" : title);
                ps.setString(2, content == null ? "" : content);
                ps.setString(3, publisherUsername == null ? "" : publisherUsername);
                ps.setString(4, name);
                ps.setString(5, audit);
                ps.setString(6, submitter);
            } else if (withAudit) {
                ps = con.prepareStatement(
                        "INSERT INTO sys_notice (title,content,publisher_username,publisher_name,audit_status) "
                                + "VALUES (?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, title == null ? "" : title);
                ps.setString(2, content == null ? "" : content);
                ps.setString(3, publisherUsername == null ? "" : publisherUsername);
                ps.setString(4, name);
                ps.setString(5, audit);
            } else if (hasExpireAt() && hasForceAck() && hasContentFmt()) {
                ps = con.prepareStatement(
                        "INSERT INTO sys_notice (title,content,publisher_username,publisher_name,expire_at,force_ack,content_fmt) "
                                + "VALUES (?,?,?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, title == null ? "" : title);
                ps.setString(2, content == null ? "" : content);
                ps.setString(3, publisherUsername == null ? "" : publisherUsername);
                ps.setString(4, name);
                ps.setTimestamp(5, exp);
                ps.setInt(6, force);
                ps.setString(7, fmtVal);
            } else {
                ps = con.prepareStatement(
                        "INSERT INTO sys_notice (title,content,publisher_username,publisher_name) VALUES (?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, title == null ? "" : title);
                ps.setString(2, content == null ? "" : content);
                ps.setString(3, publisherUsername == null ? "" : publisherUsername);
                ps.setString(4, name);
            }
            return ps;
        }, kh);
        Number key = kh.getKey();
        return get(key == null ? 0L : key.longValue());
    }

    private static String normalizeContentFmt(String contentFmt) {
        if (contentFmt == null || contentFmt.isBlank()) return "text";
        String s = contentFmt.trim().toLowerCase(Locale.ROOT);
        return "html".equals(s) ? "html" : "text";
    }

    /** 领域启动时追加种子；表内已有同标题则跳过。 */
    public static void seedDomain(String title, String content, String publisherUsername, String publisherName) {
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM sys_notice WHERE title=?", Integer.class, title);
        if (n != null && n > 0) return;
        add(title, content, publisherUsername, publisherName);
    }

    public static Map<String, Object> get(long id) {
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM sys_notice WHERE id=?", (rs, i) -> row(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Map<String, Object> update(long id, String title, String content) {
        return update(id, title, content, null, null, null, null);
    }

    public static Map<String, Object> update(long id, String title, String content, Boolean pinned) {
        return update(id, title, content, pinned, null, null, null);
    }

    /**
     * @param pinned null=不改置顶；true/false=写入 pinned（须有 pinned 列）
     * @param expireAt 非 null 时写入（空串清过期）
     * @param forceAck null=不改
     * @param contentFmt null=不改
     */
    public static Map<String, Object> update(
            long id,
            String title,
            String content,
            Boolean pinned,
            String expireAt,
            Boolean forceAck,
            String contentFmt) {
        Map<String, Object> m = get(id);
        if (m == null) return null;
        String t = title != null ? title : String.valueOf(m.get("title"));
        String c = content != null ? content : String.valueOf(m.get("content"));
        if (pinned != null && !hasPinned()) {
            throw new IllegalStateException("当前公告不支持置顶");
        }
        if (Boolean.TRUE.equals(pinned)) {
            assertCanPinForDisplay(m);
        }
        ensureXm02Columns();
        List<String> sets = new ArrayList<>();
        List<Object> args = new ArrayList<>();
        sets.add("title=?");
        args.add(t);
        sets.add("content=?");
        args.add(c);
        if (pinned != null) {
            sets.add("pinned=?");
            args.add(pinned ? 1 : 0);
        }
        if (expireAt != null && hasExpireAt()) {
            sets.add("expire_at=?");
            args.add(expireAt.isBlank() ? null : parseTs(expireAt));
        }
        if (forceAck != null && hasForceAck()) {
            sets.add("force_ack=?");
            args.add(forceAck ? 1 : 0);
        }
        if (contentFmt != null && hasContentFmt()) {
            sets.add("content_fmt=?");
            args.add(normalizeContentFmt(contentFmt));
        }
        sets.add("updated_at=NOW()");
        args.add(id);
        db().update("UPDATE sys_notice SET " + String.join(", ", sets) + " WHERE id=?", args.toArray());
        return get(id);
    }

    public static Map<String, Object> setPinned(long id, boolean pinned) {
        if (!hasPinned()) throw new IllegalStateException("当前公告不支持置顶");
        Map<String, Object> m = get(id);
        if (m == null) return null;
        if (pinned) {
            assertCanPinForDisplay(m);
        }
        db().update("UPDATE sys_notice SET pinned=?, updated_at=NOW() WHERE id=?", pinned ? 1 : 0, id);
        return get(id);
    }

    private static void assertCanPinForDisplay(Map<String, Object> m) {
        if (!hasAuditStatus()) return;
        String as = String.valueOf(m.getOrDefault("auditStatus", "")).trim();
        if (as.isEmpty() || "approved".equals(as)) return;
        throw new IllegalStateException("待审核通过后才能置顶");
    }

    public static Map<String, Object> approve(long id) {
        if (!hasAuditStatus()) throw new IllegalStateException("当前公告无需审核");
        Map<String, Object> m = get(id);
        if (m == null) return null;
        db().update(
                "UPDATE sys_notice SET audit_status='approved', updated_at=NOW() WHERE id=?",
                id);
        return get(id);
    }

    public static boolean delete(long id) {
        return db().update("DELETE FROM sys_notice WHERE id=?", id) > 0;
    }

    /** 登录用户待强制确认的公告（最多 5 条）。 */
    public static List<Map<String, Object>> listForcePending(String username) {
        if (username == null || username.isBlank() || !hasForceAck()) return List.of();
        ensureAckTable();
        StringBuilder sql = new StringBuilder(
                "SELECT n.* FROM sys_notice n WHERE n.force_ack=1");
        if (hasAuditStatus()) {
            sql.append(" AND (n.audit_status='approved' OR n.audit_status IS NULL OR n.audit_status='')");
        }
        if (hasExpireAt()) {
            sql.append(" AND (n.expire_at IS NULL OR n.expire_at > NOW())");
        }
        if (hasAckTable != null && hasAckTable) {
            sql.append(" AND NOT EXISTS (SELECT 1 FROM sys_notice_ack a WHERE a.notice_id=n.id AND a.username=?)");
        }
        sql.append(hasPinned() ? " ORDER BY n.pinned DESC, n.id DESC LIMIT 5" : " ORDER BY n.id DESC LIMIT 5");
        if (hasAckTable != null && hasAckTable) {
            return db().query(sql.toString(), (rs, i) -> row(rs), username.trim());
        }
        return db().query(sql.toString(), (rs, i) -> row(rs));
    }

    public static void ackForce(long noticeId, String username) {
        if (username == null || username.isBlank()) return;
        ensureAckTable();
        if (hasAckTable == null || !hasAckTable) return;
        db().update(
                "INSERT IGNORE INTO sys_notice_ack (notice_id, username, acked_at) VALUES (?,?,NOW())",
                noticeId, username.trim());
    }

    public static Map<String, Object> page(int page, int size) {
        return page(page, size, false, null);
    }

    public static Map<String, Object> page(int page, int size, boolean approvedOnly) {
        return page(page, size, approvedOnly, null);
    }

    public static Map<String, Object> page(int page, int size, boolean approvedOnly, String submitterOnly) {
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        StringBuilder where = new StringBuilder();
        List<Object> args = new ArrayList<>();
        if (approvedOnly && hasAuditStatus()) {
            where.append(" WHERE (audit_status='approved' OR audit_status IS NULL OR audit_status='')");
        }
        if (approvedOnly && hasExpireAt()) {
            if (where.length() == 0) where.append(" WHERE ");
            else where.append(" AND ");
            where.append("(expire_at IS NULL OR expire_at > NOW())");
        }
        if (submitterOnly != null && !submitterOnly.isBlank() && hasSubmitterUsername()) {
            if (where.length() == 0) where.append(" WHERE ");
            else where.append(" AND ");
            where.append("submitter_username=?");
            args.add(submitterOnly.trim());
        }
        Integer total = args.isEmpty()
                ? db().queryForObject("SELECT COUNT(*) FROM sys_notice" + where, Integer.class)
                : db().queryForObject("SELECT COUNT(*) FROM sys_notice" + where, Integer.class, args.toArray());
        int t = total == null ? 0 : total;
        int offset = (page - 1) * size;
        args.add(size);
        args.add(offset);
        String order = hasPinned()
                ? " ORDER BY pinned DESC, id DESC LIMIT ? OFFSET ?"
                : " ORDER BY id DESC LIMIT ? OFFSET ?";
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM sys_notice" + where + order,
                (rs, i) -> row(rs), args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }
}
