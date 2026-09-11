package com.thesis.service;

import com.thesis.config.GeneratedKeyHolder;
import com.thesis.config.JpaDb;
import com.thesis.config.JpaSupport;
import com.thesis.config.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * 门户留言板（sys_guestbook）：用户发表；管理端删除/简短回复。
 * 多店时 channel=user（买家↔平台）/ merchant（商家↔平台）。
 */
public class GuestbookStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int BODY_MAX = 500;
    private static Boolean tableReady;
    private static Boolean hasChannel;

    private static JpaDb db() {
        return JpaSupport.db();
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

    public static boolean hasChannel() {
        if (hasChannel == null) {
            try {
                Integer n = db().queryForObject(
                        "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE()"
                                + " AND TABLE_NAME='sys_guestbook' AND COLUMN_NAME='channel'",
                        Integer.class);
                hasChannel = n != null && n > 0;
            } catch (Exception e) {
                hasChannel = false;
            }
        }
        return hasChannel;
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

    private static String normChannel(String channel) {
        String c = channel == null ? "" : channel.trim().toLowerCase(Locale.ROOT);
        if ("merchant".equals(c) || "shop".equals(c) || "seller".equals(c)) return "merchant";
        return "user";
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
        if (hasChannel()) {
            try {
                String ch = rs.getString("channel");
                m.put("channel", ch == null || ch.isBlank() ? "user" : ch);
            } catch (Exception ignored) {
                m.put("channel", "user");
            }
        } else {
            m.put("channel", "user");
        }
        return m;
    }

    public static Map<String, Object> get(long id) {
        if (!ready()) return null;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM sys_guestbook WHERE id=?", (rs, i) -> row(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Map<String, Object> add(String username, String nickname, String body) {
        return add(username, nickname, body, "user");
    }

    public static Map<String, Object> add(String username, String nickname, String body, String channel) {
        if (!ready()) return null;
        String b = clip(body, BODY_MAX);
        if (b.isBlank()) return null;
        String nick = clip(nickname == null || nickname.isBlank() ? username : nickname, 64);
        String ch = normChannel(channel);
        if ("merchant".equals(ch) && !hasChannel()) {
            throw new IllegalStateException("系统未配置留言通道字段，无法保存");
        }
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps;
            if (hasChannel()) {
                ps = con.prepareStatement(
                        "INSERT INTO sys_guestbook (username,nickname,body,channel) VALUES (?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, username == null ? "" : username);
                ps.setString(2, nick);
                ps.setString(3, b);
                ps.setString(4, ch);
            } else {
                ps = con.prepareStatement(
                        "INSERT INTO sys_guestbook (username,nickname,body) VALUES (?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, username == null ? "" : username);
                ps.setString(2, nick);
                ps.setString(3, b);
            }
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
        return page(page, size, null, null);
    }

    /**
     * @param channel 多店：user / merchant；空=不过滤通道
     * @param onlyUsername 非空时仅本人留言（商家看自己的平台沟通）
     */
    public static Map<String, Object> page(int page, int size, String channel, String onlyUsername) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", List.of());
        out.put("total", 0);
        out.put("page", page < 1 ? 1 : page);
        out.put("size", size < 1 ? 10 : size);
        if (!ready()) return out;
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        if (hasChannel() && channel != null && !channel.isBlank()) {
            where.append(" AND IFNULL(NULLIF(channel,''),'user')=?");
            args.add(normChannel(channel));
        }
        if (onlyUsername != null && !onlyUsername.isBlank()) {
            where.append(" AND username=?");
            args.add(onlyUsername.trim());
        }
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM sys_guestbook" + where, Integer.class, args.toArray());
        int t = total == null ? 0 : total;
        int offset = (page - 1) * size;
        List<Object> listArgs = new ArrayList<>(args);
        listArgs.add(size);
        listArgs.add(offset);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM sys_guestbook" + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> row(rs),
                listArgs.toArray());
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }
}
