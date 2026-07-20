package com.thesis.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.common.PasswordHashes;
import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;

import java.sql.ResultSet;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 基线用户档案（MySQL sys_user）：phone 列 + profile_json 扩展 + staff_post/staff_kind。
 */
public class UserStore {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static Boolean staffColsReady;

    public static class Profile {
        public String username;
        public String password;
        public String role;
        public String nickname;
        public String phone;
        public String avatarUrl;
        public Map<String, String> extras = new LinkedHashMap<>();
        public boolean superAdmin;
        public boolean profileEditable;
        public boolean enabled = true;
        /** 岗位 id，如 claim_clerk / rider */
        public String staffPost = "";
        /** clerk | worker；总管为空 */
        public String staffKind = "";

        public Map<String, Object> toMap() {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("username", username);
            m.put("role", role);
            m.put("nickname", nickname == null ? "" : nickname);
            m.put("phone", phone == null ? "" : phone);
            m.put("avatarUrl", avatarUrl == null ? "" : avatarUrl);
            m.put("extras", extras == null ? Map.of() : new LinkedHashMap<>(extras));
            m.put("superAdmin", superAdmin);
            m.put("profileEditable", profileEditable);
            m.put("enabled", enabled);
            m.put("staffPost", staffPost == null ? "" : staffPost);
            m.put("staffKind", staffKind == null ? "" : staffKind);
            if (extras != null) {
                for (Map.Entry<String, String> e : extras.entrySet()) {
                    m.putIfAbsent(e.getKey(), e.getValue());
                }
            }
            return m;
        }
    }

    private static final RowMapper<Profile> MAPPER = (rs, i) -> mapRow(rs);

    private static Profile mapRow(ResultSet rs) throws java.sql.SQLException {
        Profile p = new Profile();
        p.username = rs.getString("username");
        p.password = rs.getString("password");
        p.role = rs.getString("role");
        p.nickname = rs.getString("nickname");
        p.phone = rs.getString("phone");
        p.avatarUrl = rs.getString("avatar_url");
        p.superAdmin = rs.getInt("super_admin") == 1;
        p.profileEditable = rs.getInt("profile_editable") == 1;
        try {
            p.enabled = rs.getInt("enabled") == 1;
        } catch (Exception e) {
            p.enabled = true;
        }
        p.extras = readExtras(rs);
        if (hasStaffColumns()) {
            try {
                String sp = rs.getString("staff_post");
                p.staffPost = sp == null ? "" : sp.trim();
            } catch (Exception e) {
                p.staffPost = "";
            }
            try {
                String sk = rs.getString("staff_kind");
                p.staffKind = sk == null ? "" : sk.trim();
            } catch (Exception e) {
                p.staffKind = "";
            }
        }
        return p;
    }

    private static Map<String, String> readExtras(ResultSet rs) {
        try {
            String raw = rs.getString("profile_json");
            if (raw == null || raw.isBlank()) return new LinkedHashMap<>();
            Map<String, Object> m = JSON.readValue(raw, new TypeReference<>() {});
            Map<String, String> out = new LinkedHashMap<>();
            for (Map.Entry<String, Object> e : m.entrySet()) {
                if (e.getValue() != null) out.put(e.getKey(), String.valueOf(e.getValue()));
            }
            return out;
        } catch (Exception e) {
            return new LinkedHashMap<>();
        }
    }

    private static String writeExtras(Map<String, String> extras) {
        try {
            return JSON.writeValueAsString(extras == null ? Map.of() : extras);
        } catch (Exception e) {
            return "{}";
        }
    }

    private static boolean hasProfileJson() {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                            + "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='sys_user' AND COLUMN_NAME='profile_json'",
                    Integer.class);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static boolean columnExists(String column) {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                            + "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='sys_user' AND COLUMN_NAME=?",
                    Integer.class, column);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    public static synchronized void ensureStaffColumns() {
        if (Boolean.TRUE.equals(staffColsReady)) return;
        try {
            if (!columnExists("staff_post")) {
                db().execute("ALTER TABLE sys_user ADD COLUMN staff_post VARCHAR(64) DEFAULT ''");
            }
            if (!columnExists("staff_kind")) {
                db().execute("ALTER TABLE sys_user ADD COLUMN staff_kind VARCHAR(16) DEFAULT ''");
            }
            staffColsReady = columnExists("staff_post") && columnExists("staff_kind");
        } catch (Exception e) {
            // 数据源未就绪时不缓存失败，避免永久读不到 staff_post → 登录身份全拒
            staffColsReady = null;
        }
    }

    private static boolean hasStaffColumns() {
        if (!Boolean.TRUE.equals(staffColsReady)) {
            ensureStaffColumns();
        }
        return Boolean.TRUE.equals(staffColsReady);
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static Profile get(String username) {
        List<Profile> list = db().query(
                "SELECT * FROM sys_user WHERE username=?", MAPPER, username);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Profile authenticate(String username, String password) {
        Profile p = get(username);
        if (p == null || !PasswordHashes.matches(password, p.password)) return null;
        if (!p.enabled) return null;
        if (PasswordHashes.needsUpgrade(p.password)) {
            String encoded = PasswordHashes.encode(password);
            db().update("UPDATE sys_user SET password=? WHERE username=?", encoded, username);
            p.password = encoded;
        }
        return p;
    }

    public static Profile register(
            String username,
            String password,
            String nickname,
            String role,
            String phone,
            Map<String, String> extras) {
        if (username == null || !username.matches("^[a-zA-Z0-9_]{3,32}$")) {
            throw new IllegalArgumentException("用户名需为 3–32 位字母/数字/下划线");
        }
        if (password == null || password.length() < 6) {
            throw new IllegalArgumentException("密码至少 6 位");
        }
        if (get(username) != null) {
            throw new IllegalStateException("用户名已存在");
        }
        String r = (role == null || role.isBlank()) ? "user" : role.trim();
        if ("admin".equalsIgnoreCase(r)) {
            throw new IllegalArgumentException("不可注册管理员账号");
        }
        String nick = nickname == null || nickname.isBlank() ? username : nickname.trim();
        String ph = phone == null ? "" : phone.trim();
        Map<String, String> ex = ProfileFields.filterExtras(extras);
        ProfileFields.requireFilled(ph, ex, true);
        String encoded = PasswordHashes.encode(password);
        ensureStaffColumns();
        if (hasProfileJson()) {
            db().update(
                    "INSERT INTO sys_user (username,password,role,nickname,phone,avatar_url,profile_json,super_admin,profile_editable,enabled) "
                            + "VALUES (?,?,?,?,?,?,?,0,1,1)",
                    username, encoded, r, nick, ph, "", writeExtras(ex));
        } else {
            db().update(
                    "INSERT INTO sys_user (username,password,role,nickname,phone,avatar_url,super_admin,profile_editable,enabled) "
                            + "VALUES (?,?,?,?,?,?,0,1,1)",
                    username, encoded, r, nick, ph, "");
        }
        return get(username);
    }

    /** 兼容旧调用 */
    public static Profile register(String username, String password, String nickname, String role) {
        return register(username, password, nickname, role, "", Map.of());
    }

    public static List<Map<String, Object>> listByRole(String role, String keyword) {
        return listManaged(role, "users", keyword);
    }

    public static List<Map<String, Object>> listManaged(String userRole, String scope, String keyword) {
        String kw = keyword == null ? "" : keyword.trim();
        String sc = scope == null || scope.isBlank() ? "users" : scope.trim();
        String ur = (userRole == null || userRole.isBlank()) ? "user" : userRole.trim();
        List<Profile> all = db().query("SELECT * FROM sys_user", MAPPER);
        return all.stream()
                .filter(p -> !p.superAdmin)
                .filter(p -> {
                    boolean isSub = "admin".equals(p.role);
                    boolean isUser = !isSub && (ur.equals(p.role) || "user".equals(p.role)
                            || "student".equals(p.role) || "reader".equals(p.role)
                            || "patient".equals(p.role));
                    if ("subadmins".equals(sc)) return isSub;
                    if ("all".equals(sc)) return isSub || isUser;
                    return isUser;
                })
                .filter(p -> {
                    if (kw.isBlank()) return true;
                    if (p.username.contains(kw)
                            || (p.nickname != null && p.nickname.contains(kw))
                            || (p.phone != null && p.phone.contains(kw))
                            || (p.staffPost != null && p.staffPost.contains(kw))) {
                        return true;
                    }
                    if (p.extras == null) return false;
                    return p.extras.values().stream().anyMatch(v -> v != null && v.contains(kw));
                })
                .sorted(Comparator.comparing((Profile p) -> "admin".equals(p.role) ? 0 : 1)
                        .thenComparing(p -> p.username))
                .map(Profile::toMap)
                .collect(Collectors.toList());
    }

    public static long countByRole(String role) {
        Long n = db().queryForObject(
                "SELECT COUNT(*) FROM sys_user WHERE role=?", Long.class, role);
        return n == null ? 0 : n;
    }

    public static Profile adminUpdate(
            String username,
            String nickname,
            String phone,
            Boolean enabled,
            Map<String, String> extras) {
        Profile p = requireManaged(username);
        if (nickname != null) p.nickname = nickname.trim();
        if (phone != null) p.phone = phone.trim();
        if (enabled != null) p.enabled = enabled;
        if (extras != null) {
            Map<String, String> merged = new LinkedHashMap<>(p.extras == null ? Map.of() : p.extras);
            merged.putAll(ProfileFields.filterExtras(extras));
            p.extras = merged;
        }
        if (hasProfileJson()) {
            db().update(
                    "UPDATE sys_user SET nickname=?, phone=?, enabled=?, profile_json=? WHERE username=?",
                    p.nickname, p.phone, p.enabled ? 1 : 0, writeExtras(p.extras), username);
        } else {
            db().update(
                    "UPDATE sys_user SET nickname=?, phone=?, enabled=? WHERE username=?",
                    p.nickname, p.phone, p.enabled ? 1 : 0, username);
        }
        return get(username);
    }

    public static Profile adminUpdate(String username, String nickname, String phone, Boolean enabled) {
        return adminUpdate(username, nickname, phone, enabled, null);
    }

    public static void adminResetPassword(String username, String newPassword) {
        requireManaged(username);
        if (newPassword == null || newPassword.length() < 6) {
            throw new IllegalArgumentException("密码至少 6 位");
        }
        db().update(
                "UPDATE sys_user SET password=? WHERE username=?",
                PasswordHashes.encode(newPassword), username);
    }

    /**
     * 任命子管或业务员工。staffPost / staffKind 必填（clerk|worker）。
     */
    public static Profile appointSubAdmin(String username, String staffPost, String staffKind) {
        ensureStaffColumns();
        Profile p = get(username);
        if (p == null) throw new IllegalArgumentException("用户不存在");
        if (p.superAdmin) throw new IllegalArgumentException("不可操作总管账号");
        if ("admin".equals(p.role)) throw new IllegalArgumentException("已是岗位账号，请先撤销再任命");
        String post = staffPost == null ? "" : staffPost.trim();
        String kind = staffKind == null ? "" : staffKind.trim().toLowerCase(Locale.ROOT);
        if (post.isBlank()) throw new IllegalArgumentException("请选择岗位");
        if (!"clerk".equals(kind) && !"worker".equals(kind)) {
            throw new IllegalArgumentException("岗位类型须为 clerk 或 worker");
        }
        db().update(
                "UPDATE sys_user SET role=?, super_admin=0, staff_post=?, staff_kind=? WHERE username=?",
                "admin", post, kind, username);
        return get(username);
    }

    /** 兼容旧调用：无岗位时记为 clerk / subadmin */
    public static Profile appointSubAdmin(String username) {
        return appointSubAdmin(username, "subadmin", "clerk");
    }

    public static Profile revokeSubAdmin(String username, String userRole) {
        ensureStaffColumns();
        Profile p = get(username);
        if (p == null) throw new IllegalArgumentException("用户不存在");
        if (p.superAdmin) throw new IllegalArgumentException("不可撤销总管");
        if (!"admin".equals(p.role)) throw new IllegalArgumentException("该账号不是岗位员工");
        String ur = (userRole == null || userRole.isBlank()) ? "user" : userRole.trim();
        if (hasStaffColumns()) {
            db().update(
                    "UPDATE sys_user SET role=?, super_admin=0, staff_post='', staff_kind='' WHERE username=?",
                    ur, username);
        } else {
            db().update(
                    "UPDATE sys_user SET role=?, super_admin=0 WHERE username=?",
                    ur, username);
        }
        return get(username);
    }

    private static Profile requireManaged(String username) {
        Profile p = get(username);
        if (p == null) throw new IllegalArgumentException("用户不存在");
        if (p.superAdmin) throw new IllegalArgumentException("不可在此管理总管账号");
        return p;
    }

    public static void saveProfile(Profile p) {
        ProfileFields.requireFilled(p.phone, p.extras, false);
        if (hasProfileJson()) {
            db().update(
                    "UPDATE sys_user SET nickname=?, phone=?, avatar_url=?, password=?, profile_json=? WHERE username=?",
                    p.nickname, p.phone, p.avatarUrl, p.password, writeExtras(p.extras), p.username);
        } else {
            db().update(
                    "UPDATE sys_user SET nickname=?, phone=?, avatar_url=?, password=? WHERE username=?",
                    p.nickname, p.phone, p.avatarUrl, p.password, p.username);
        }
    }
}
