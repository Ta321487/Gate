package com.thesis.service;

import com.thesis.config.GeneratedKeyHolder;
import com.thesis.config.JpaSupport;
import com.thesis.config.JpaDb;
import com.thesis.config.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 基线公告（MySQL sys_notice）— JpaDb。
 */
public class NoticeStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static Boolean hasAuditStatus;
    private static Boolean hasSubmitterUsername;

    private static JpaDb db() {
        return JpaSupport.db();
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
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

    public static Map<String, Object> add(String title, String content, String publisherUsername, String publisherName) {
        return add(title, content, publisherUsername, publisherName, null, null);
    }

    public static Map<String, Object> add(
            String title,
            String content,
            String publisherUsername,
            String publisherName,
            String auditStatus,
            String submitterUsername) {
        String name = publisherName == null || publisherName.isBlank()
                ? (publisherUsername == null ? "系统" : publisherUsername)
                : publisherName;
        KeyHolder kh = new GeneratedKeyHolder();
        boolean withAudit = hasAuditStatus();
        String audit = auditStatus == null || auditStatus.isBlank() ? "approved" : auditStatus.trim();
        String submitter = submitterUsername == null ? "" : submitterUsername.trim();
        db().update(con -> {
            PreparedStatement ps;
            if (withAudit && hasSubmitterUsername()) {
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
        Map<String, Object> m = get(id);
        if (m == null) return null;
        String t = title != null ? title : String.valueOf(m.get("title"));
        String c = content != null ? content : String.valueOf(m.get("content"));
        db().update(
                "UPDATE sys_notice SET title=?, content=?, updated_at=NOW() WHERE id=?",
                t, c, id);
        return get(id);
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

    public static Map<String, Object> page(int page, int size) {
        return page(page, size, false);
    }

    public static Map<String, Object> page(int page, int size, boolean approvedOnly) {
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String where = "";
        if (approvedOnly && hasAuditStatus()) {
            where = " WHERE (audit_status='approved' OR audit_status IS NULL OR audit_status='')";
        }
        Integer total = db().queryForObject("SELECT COUNT(*) FROM sys_notice" + where, Integer.class);
        int t = total == null ? 0 : total;
        int offset = (page - 1) * size;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM sys_notice" + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> row(rs), size, offset);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }
}
