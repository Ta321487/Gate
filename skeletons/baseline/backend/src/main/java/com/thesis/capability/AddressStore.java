package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.util.*;

/**
 * 收货地址簿：商城 / 点餐 / 交易壳共用。
 */
public final class AddressStore {

    private static final String TABLE = "user_address";
    private static Boolean tableReady;

    private AddressStore() {}

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static boolean available() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=?",
                    Integer.class, TABLE);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    public static void resetCache() {
        tableReady = null;
    }

    public static List<Map<String, Object>> list(String username) {
        if (!available()) return List.of();
        return db().query(
                "SELECT * FROM " + TABLE + " WHERE username=? ORDER BY is_default DESC, id DESC",
                (rs, i) -> mapRow(rs),
                username);
    }

    public static Map<String, Object> get(long id, String username) {
        if (!available() || id <= 0) return null;
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM " + TABLE + " WHERE id=? AND username=?",
                (rs, i) -> mapRow(rs),
                id, username);
        return rows.isEmpty() ? null : rows.get(0);
    }

    public static Map<String, Object> create(
            String username, String contactName, String phone, String addressLine, String tag, boolean asDefault) {
        requireTable();
        String name = nz(contactName);
        String ph = nz(phone);
        String addr = nz(addressLine);
        if (name.isBlank() || ph.isBlank() || addr.isBlank()) {
            throw new IllegalArgumentException("请填写联系人、手机与详细地址");
        }
        String tg = tag == null || tag.isBlank() ? "默认" : tag.trim();
        if (asDefault) clearDefault(username);
        else if (list(username).isEmpty()) asDefault = true;
        boolean def = asDefault;
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + TABLE + " (username,contact_name,phone,address_line,tag,is_default) VALUES (?,?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, username);
            ps.setString(2, name);
            ps.setString(3, ph);
            ps.setString(4, addr);
            ps.setString(5, tg);
            ps.setInt(6, def ? 1 : 0);
            return ps;
        }, kh);
        long id = kh.getKey() == null ? 0L : kh.getKey().longValue();
        return get(id, username);
    }

    public static Map<String, Object> update(
            long id, String username, String contactName, String phone, String addressLine, String tag, Boolean asDefault) {
        requireTable();
        Map<String, Object> cur = get(id, username);
        if (cur == null) throw new IllegalArgumentException("地址不存在");
        String name = contactName != null ? contactName.trim() : String.valueOf(cur.get("contactName"));
        String ph = phone != null ? phone.trim() : String.valueOf(cur.get("phone"));
        String addr = addressLine != null ? addressLine.trim() : String.valueOf(cur.get("addressLine"));
        String tg = tag != null ? (tag.isBlank() ? "默认" : tag.trim()) : String.valueOf(cur.get("tag"));
        if (name.isBlank() || ph.isBlank() || addr.isBlank()) {
            throw new IllegalArgumentException("请填写联系人、手机与详细地址");
        }
        boolean def = asDefault == null ? Boolean.TRUE.equals(cur.get("isDefault")) : asDefault;
        if (def) clearDefault(username);
        db().update(
                "UPDATE " + TABLE + " SET contact_name=?, phone=?, address_line=?, tag=?, is_default=? WHERE id=? AND username=?",
                name, ph, addr, tg, def ? 1 : 0, id, username);
        return get(id, username);
    }

    public static boolean delete(long id, String username) {
        requireTable();
        return db().update("DELETE FROM " + TABLE + " WHERE id=? AND username=?", id, username) > 0;
    }

    private static void clearDefault(String username) {
        db().update("UPDATE " + TABLE + " SET is_default=0 WHERE username=?", username);
    }

    private static void requireTable() {
        if (!available()) throw new IllegalStateException("收货地址功能暂不可用");
    }

    private static Map<String, Object> mapRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("contactName", rs.getString("contact_name"));
        m.put("phone", rs.getString("phone"));
        m.put("addressLine", rs.getString("address_line"));
        m.put("tag", rs.getString("tag"));
        m.put("isDefault", rs.getInt("is_default") == 1);
        return m;
    }

    private static String nz(String s) {
        return s == null ? "" : s.trim();
    }
}
