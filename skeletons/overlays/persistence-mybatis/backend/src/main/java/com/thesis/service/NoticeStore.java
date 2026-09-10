package com.thesis.service;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.NoticeMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 基线公告（MySQL sys_notice）— MyBatis。
 */
public class NoticeStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static Boolean hasAuditStatus;
    private static Boolean hasSubmitterUsername;

    private static NoticeMapper mapper() {
        return MybatisSupport.mapper(NoticeMapper.class);
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    private static Object col(Map<String, Object> raw, String camel, String snake) {
        if (raw == null) return null;
        if (raw.containsKey(camel)) return raw.get(camel);
        if (raw.containsKey(snake)) return raw.get(snake);
        String lower = snake.toLowerCase(Locale.ROOT);
        for (Map.Entry<String, Object> e : raw.entrySet()) {
            if (e.getKey() != null && e.getKey().equalsIgnoreCase(lower)) return e.getValue();
        }
        return null;
    }

    private static Map<String, Object> shape(Map<String, Object> raw) {
        if (raw == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", raw.get("id"));
        m.put("title", col(raw, "title", "title"));
        m.put("content", col(raw, "content", "content"));
        m.put("publisherUsername", col(raw, "publisherUsername", "publisher_username"));
        m.put("publisherName", col(raw, "publisherName", "publisher_name"));
        m.put("createdAt", fmt(col(raw, "createdAt", "created_at")));
        m.put("updatedAt", fmt(col(raw, "updatedAt", "updated_at")));
        if (hasAuditStatus()) {
            Object as = col(raw, "auditStatus", "audit_status");
            m.put("auditStatus", as == null ? "" : String.valueOf(as));
        }
        if (hasSubmitterUsername()) {
            Object su = col(raw, "submitterUsername", "submitter_username");
            m.put("submitterUsername", su == null ? "" : String.valueOf(su));
        }
        return m;
    }

    public static boolean hasAuditStatus() {
        if (hasAuditStatus == null) hasAuditStatus = mapper().countColumn("audit_status") > 0;
        return hasAuditStatus;
    }

    public static boolean hasSubmitterUsername() {
        if (hasSubmitterUsername == null) hasSubmitterUsername = mapper().countColumn("submitter_username") > 0;
        return hasSubmitterUsername;
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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("title", title == null ? "" : title);
        row.put("content", content == null ? "" : content);
        row.put("publisherUsername", publisherUsername == null ? "" : publisherUsername);
        row.put("publisherName", name);
        boolean withAudit = hasAuditStatus();
        String audit = auditStatus == null || auditStatus.isBlank() ? "approved" : auditStatus.trim();
        String submitter = submitterUsername == null ? "" : submitterUsername.trim();
        if (withAudit && hasSubmitterUsername()) {
            row.put("auditStatus", audit);
            row.put("submitterUsername", submitter);
            mapper().insertWithAuditSubmitter(row);
        } else if (withAudit) {
            row.put("auditStatus", audit);
            mapper().insertWithAudit(row);
        } else {
            mapper().insert(row);
        }
        Object key = row.get("id");
        return get(key == null ? 0L : ((Number) key).longValue());
    }

    public static void seedDomain(String title, String content, String publisherUsername, String publisherName) {
        if (mapper().countByTitle(title) > 0) return;
        add(title, content, publisherUsername, publisherName);
    }

    public static Map<String, Object> get(long id) {
        return shape(mapper().selectById(id));
    }

    public static Map<String, Object> update(long id, String title, String content) {
        Map<String, Object> m = get(id);
        if (m == null) return null;
        String t = title != null ? title : String.valueOf(m.get("title"));
        String c = content != null ? content : String.valueOf(m.get("content"));
        mapper().update(id, t, c);
        return get(id);
    }

    public static Map<String, Object> approve(long id) {
        if (!hasAuditStatus()) throw new IllegalStateException("当前公告无需审核");
        Map<String, Object> m = get(id);
        if (m == null) return null;
        mapper().approve(id);
        return get(id);
    }

    public static boolean delete(long id) {
        return mapper().deleteById(id) > 0;
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
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw;
        if (submitterOnly != null && !submitterOnly.isBlank() && hasSubmitterUsername()) {
            raw = mapper().selectBySubmitterOrderByIdDesc(submitterOnly.trim());
        } else if (approvedOnly && hasAuditStatus()) {
            raw = mapper().selectApprovedOrderByIdDesc();
        } else {
            raw = mapper().selectAllOrderByIdDesc();
        }
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : raw) {
            list.add(shape(r));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", pi.getTotal());
        out.put("page", page);
        out.put("size", size);
        return out;
    }
}
