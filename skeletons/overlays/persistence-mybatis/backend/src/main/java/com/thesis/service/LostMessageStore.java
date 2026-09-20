package com.thesis.service;

import com.thesis.config.MybatisSupport;
import com.thesis.config.MbSql;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 失物线索留言：登录用户记 user_id；游客只填称呼，不建账号。
 */
public class LostMessageStore {

    private static final Set<String> MSG_TYPES = Set.of("clue", "ask");

    private static boolean enabled;
    private static Boolean tableReady;

    private LostMessageStore() {}

    public static void configure(boolean on) {
        enabled = on;
        tableReady = null;
    }

    public static boolean enabled() {
        return enabled;
    }

    private static MbSql db() {
        return MybatisSupport.db();
    }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='lost_message'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("线索留言功能暂不可用");
    }

    private static Map<String, Object> mapRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("lostItemId", rs.getLong("lost_item_id"));
        m.put("userId", rs.getString("user_id"));
        m.put("guestName", rs.getString("guest_name"));
        m.put("guestContact", rs.getString("guest_contact"));
        m.put("content", rs.getString("content"));
        m.put("type", rs.getString("msg_type"));
        m.put("createdAt", rs.getTimestamp("created_at") == null
                ? null : rs.getTimestamp("created_at").toLocalDateTime().toString().replace('T', ' '));
        return m;
    }

    public static List<Map<String, Object>> listByItem(long lostItemId) {
        require();
        return db().query(
                "SELECT * FROM lost_message WHERE lost_item_id=? ORDER BY id DESC",
                (rs, i) -> mapRow(rs),
                lostItemId);
    }

    public static List<Map<String, Object>> listRecent(int limit) {
        require();
        int lim = Math.max(1, Math.min(limit, 200));
        return db().query(
                "SELECT * FROM lost_message ORDER BY id DESC LIMIT " + lim,
                (rs, i) -> mapRow(rs));
    }

    public static long post(
            long lostItemId,
            String userId,
            String guestName,
            String guestContact,
            String content,
            String msgType) {
        require();
        if (lostItemId <= 0) throw new IllegalArgumentException("启事无效");
        String body = content == null ? "" : content.trim();
        if (body.isBlank()) throw new IllegalArgumentException("请填写留言内容");
        if (body.length() > 500) body = body.substring(0, 500);
        String type = msgType == null ? "clue" : msgType.trim().toLowerCase();
        if ("线索".equals(msgType)) type = "clue";
        else if ("询问".equals(msgType)) type = "ask";
        if (!MSG_TYPES.contains(type)) type = "clue";

        String uid = userId == null ? "" : userId.trim();
        String gName = guestName == null ? "" : guestName.trim();
        String gContact = guestContact == null ? "" : guestContact.trim();
        if (uid.isBlank() && gName.isBlank()) {
            throw new IllegalArgumentException("游客请填写称呼，或先登录");
        }
        if (gName.length() > 64) gName = gName.substring(0, 64);
        if (gContact.length() > 64) gContact = gContact.substring(0, 64);
        if (uid.length() > 64) uid = uid.substring(0, 64);

        String finalUid = uid.isBlank() ? null : uid;
        String finalName = gName.isBlank() ? null : gName;
        String finalContact = gContact.isBlank() ? null : gContact;
        String finalBody = body;
        String finalType = type;
        KeyHolder keys = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO lost_message (lost_item_id, user_id, guest_name, guest_contact, content, msg_type) "
                            + "VALUES (?,?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, lostItemId);
            ps.setString(2, finalUid);
            ps.setString(3, finalName);
            ps.setString(4, finalContact);
            ps.setString(5, finalBody);
            ps.setString(6, finalType);
            return ps;
        }, keys);
        Number key = keys.getKey();
        return key == null ? 0L : key.longValue();
    }
}
