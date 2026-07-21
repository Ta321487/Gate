package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 门户留言板（sys_guestbook）：用户发表；管理端删除/简短回复。
 * 非公告、非站内信、非论坛跟帖。
 */
public class GuestbookStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int BODY_MAX = 500;
    private static Boolean tableReady;

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static boolean ready() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='sys_guestbook'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        String t = s.trim();
        return t.length() <= max ? t : t.substring(0, max);
    }

    private static Map<String, Object> row(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("nickname", rs.getString("nickname"));
        m.put("body", rs.getString("body"));
        m.put("reply", rs.getString("reply"));
        m.put("replyUsername", rs.getString("reply_username"));
        m.put("repliedAt", fmt(rs.getTimestamp("replied_at")));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        return m;
    }

    public static Map<String, Object> get(long id) {
        if (!ready()) return null;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM sys_guestbook WHERE id=?", (rs, i) -> row(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Map<String, Object> add(String username, String nickname, String body) {
        if (!ready()) return null;
        String b = clip(body, BODY_MAX);
        if (b.isBlank()) return null;
        String nick = clip(nickname == null || nickname.isBlank() ? username : nickname, 64);
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO sys_guestbook (username,nickname,body) VALUES (?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, username == null ? "" : username);
            ps.setString(2, nick);
            ps.setString(3, b);
            return ps;
        }, kh);
        Number key = kh.getKey();
        return get(key == null ? 0L : key.longValue());
    }

    public static Map<String, Object> reply(long id, String reply, String replyUsername) {
        if (!ready()) return null;
        Map<String, Object> m = get(id);
        if (m == null) return null;
        String r = clip(reply, BODY_MAX);
        db().update(
                "UPDATE sys_guestbook SET reply=?, reply_username=?, replied_at=NOW() WHERE id=?",
                r,
                replyUsername == null ? "" : replyUsername,
                id);
        return get(id);
    }

    public static boolean delete(long id) {
        if (!ready()) return false;
        return db().update("DELETE FROM sys_guestbook WHERE id=?", id) > 0;
    }

    public static Map<String, Object> page(int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", List.of());
        out.put("total", 0);
        out.put("page", page < 1 ? 1 : page);
        out.put("size", size < 1 ? 10 : size);
        if (!ready()) return out;
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject("SELECT COUNT(*) FROM sys_guestbook", Integer.class);
        int t = total == null ? 0 : total;
        int offset = (page - 1) * size;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM sys_guestbook ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> row(rs), size, offset);
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }
}
