package com.thesis.service;

import com.thesis.config.JpaSupport;
import com.thesis.config.JpaDb;
import com.thesis.config.GeneratedKeyHolder;
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
import java.util.Map;

/**
 * 一对一私信（sys_dm_message）：用户↔用户；短轮询拉取，非站内信、非 WebSocket。
 */
public class DmStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int BODY_MAX = 500;
    private static Boolean tableReady;

    private static JpaDb db() {
        return JpaSupport.db();
    }

    public static boolean ready() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='sys_dm_message'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static String fmt(Timestamp ts) {
        return ts == null ? null : ts.toLocalDateTime().format(FMT);
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        String t = s.trim();
        return t.length() <= max ? t : t.substring(0, max);
    }

    private static Map<String, Object> row(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("fromUsername", rs.getString("from_username"));
        m.put("toUsername", rs.getString("to_username"));
        m.put("body", rs.getString("body"));
        m.put("readAt", fmt(rs.getTimestamp("read_at")));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        m.put("read", rs.getTimestamp("read_at") != null);
        return m;
    }

    public static Map<String, Object> get(long id) {
        if (!ready()) return null;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM sys_dm_message WHERE id=?", (rs, i) -> row(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    /** 可选会话对象：其它启用账号（含管理端），便于演示起聊。 */
    public static List<Map<String, Object>> peers(String me, int limit) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (!ready() || me == null || me.isBlank()) return out;
        int lim = limit < 1 ? 50 : Math.min(limit, 100);
        return db().query(
                "SELECT username, nickname, role FROM sys_user "
                        + "WHERE username<>? AND (enabled IS NULL OR enabled=1) "
                        + "ORDER BY role DESC, id ASC LIMIT ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("username", rs.getString("username"));
                    m.put("nickname", rs.getString("nickname"));
                    m.put("role", rs.getString("role"));
                    return m;
                },
                me.trim(),
                lim);
    }

    public static List<Map<String, Object>> conversations(String me) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (!ready() || me == null || me.isBlank()) return out;
        String u = me.trim();
        // 每个 peer 取最新一条 + 未读数
        List<Map<String, Object>> peers = db().query(
                "SELECT peer_user, MAX(id) AS last_id FROM ("
                        + "  SELECT CASE WHEN from_username=? THEN to_username ELSE from_username END AS peer_user, id"
                        + "  FROM sys_dm_message WHERE from_username=? OR to_username=?"
                        + ") t GROUP BY peer_user ORDER BY last_id DESC",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("peer", rs.getString("peer_user"));
                    m.put("lastId", rs.getLong("last_id"));
                    return m;
                },
                u, u, u);
        for (Map<String, Object> p : peers) {
            String peer = String.valueOf(p.get("peer"));
            long lastId = ((Number) p.get("lastId")).longValue();
            Map<String, Object> last = get(lastId);
            Integer unread = db().queryForObject(
                    "SELECT COUNT(*) FROM sys_dm_message WHERE to_username=? AND from_username=? AND read_at IS NULL",
                    Integer.class, u, peer);
            String nick = null;
            try {
                nick = db().queryForObject(
                        "SELECT nickname FROM sys_user WHERE username=?", String.class, peer);
            } catch (Exception ignored) {
            }
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("peer", peer);
            row.put("peerNickname", nick == null || nick.isBlank() ? peer : nick);
            row.put("unread", unread == null ? 0 : unread);
            row.put("lastMessage", last);
            out.add(row);
        }
        return out;
    }

    public static List<Map<String, Object>> messages(String me, String peer, long sinceId) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (!ready() || me == null || peer == null) return out;
        String u = me.trim();
        String p = peer.trim();
        if (u.isBlank() || p.isBlank()) return out;
        long since = Math.max(0L, sinceId);
        return db().query(
                "SELECT * FROM sys_dm_message WHERE "
                        + "((from_username=? AND to_username=?) OR (from_username=? AND to_username=?)) "
                        + "AND id>? ORDER BY id ASC LIMIT 200",
                (rs, i) -> row(rs),
                u, p, p, u, since);
    }

    public static Map<String, Object> send(String from, String to, String body) {
        if (!ready()) return null;
        String f = from == null ? "" : from.trim();
        String t = to == null ? "" : to.trim();
        String b = clip(body, BODY_MAX);
        if (f.isBlank() || t.isBlank() || b.isBlank() || f.equals(t)) return null;
        Integer exists = db().queryForObject(
                "SELECT COUNT(*) FROM sys_user WHERE username=? AND (enabled IS NULL OR enabled=1)",
                Integer.class, t);
        if (exists == null || exists == 0) return null;
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO sys_dm_message (from_username, to_username, body) VALUES (?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, f);
            ps.setString(2, t);
            ps.setString(3, b);
            return ps;
        }, kh);
        Number key = kh.getKey();
        return get(key == null ? 0L : key.longValue());
    }

    public static int markRead(String me, String peer) {
        if (!ready() || me == null || peer == null) return 0;
        return db().update(
                "UPDATE sys_dm_message SET read_at=? WHERE to_username=? AND from_username=? AND read_at IS NULL",
                Timestamp.valueOf(LocalDateTime.now()),
                me.trim(),
                peer.trim());
    }

    public static int unreadCount(String me) {
        if (!ready() || me == null || me.isBlank()) return 0;
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM sys_dm_message WHERE to_username=? AND read_at IS NULL",
                Integer.class, me.trim());
        return n == null ? 0 : n;
    }
}
