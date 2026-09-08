package com.thesis.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.common.PasswordHashes;
import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;

import java.sql.ResultSet;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 基线用户档案（MySQL sys_user）：phone 列 + profile_json 扩展 + staff_post/staff_kind。
 */
public class UserStore {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final DateTimeFormatter MUTE_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static Boolean staffColsReady;
    private static boolean postMuteEnabled = false;

    public static void configurePostMute(boolean on) {
        postMuteEnabled = on;
    }

    public static boolean postMuteEnabled() {
        return postMuteEnabled;
    }

    /** 禁言期内不可发帖/回复（能力关闭时直接放行）。 */
    public static void assertNotPostMuted(String username) {
        if (!postMuteEnabled) return;
        String until = postMuteUntilOf(username);
        if (until == null || until.isBlank()) return;
        LocalDateTime end = parseMuteUntil(until);
        if (end != null && LocalDateTime.now().isBefore(end)) {
            throw new IllegalStateException("您已被禁言至 " + until + "，期间不可发帖或回复");
        }
    }

    public static String postMuteUntilOf(String username) {
        if (username == null || username.isBlank()) return "";
        Profile p = get(username.trim());
        if (p == null || p.extras == null) return "";
        String v = p.extras.get("postMuteUntil");
        return v == null ? "" : v.trim();
    }

    /**
     * 设禁言截止；until 空白则解除。写入 profile_json，不经 ProfileFields 过滤。
     * @return 更新后的档案 map（含 postMuteUntil）
     */
    public static Map<String, Object> setPostMuteUntil(String username, String untilRaw) {
        if (!postMuteEnabled) {
            throw new IllegalStateException("禁言功能暂不可用");
        }
        if (!hasProfileJson()) {
            throw new IllegalStateException("当前库不支持禁言扩展字段");
        }
        Profile p = requireManaged(username);
        Map<String, String> merged = new LinkedHashMap<>(p.extras == null ? Map.of() : p.extras);
        String raw = untilRaw == null ? "" : untilRaw.trim();
        if (raw.isBlank() || "null".equalsIgnoreCase(raw)) {
            merged.remove("postMuteUntil");
        } else {
            LocalDateTime end = parseMuteUntil(raw);
            if (end == null) {
                throw new IllegalArgumentException("禁言截止时间格式无效，请使用 yyyy-MM-dd HH:mm:ss");
            }
            if (!end.isAfter(LocalDateTime.now())) {
                throw new IllegalArgumentException("禁言截止须晚于当前时间");
            }
            merged.put("postMuteUntil", end.format(MUTE_FMT));
        }
        p.extras = merged;
        db().update(
                "UPDATE sys_user SET profile_json=? WHERE username=?",
                writeExtras(merged), username.trim());
        Profile updated = get(username.trim());
        return updated == null ? Map.of() : updated.toMap();
    }

    /** 按天数设禁言（默认 7 天）；days&lt;=0 解除。 */
    public static Map<String, Object> setPostMuteDays(String username, int days) {
        if (days <= 0) {
            return setPostMuteUntil(username, "");
        }
        LocalDateTime end = LocalDateTime.now().plusDays(days).withHour(23).withMinute(59).withSecond(59).withNano(0);
        return setPostMuteUntil(username, end.format(MUTE_FMT));
    }

    private static LocalDateTime parseMuteUntil(String raw) {
        if (raw == null || raw.isBlank()) return null;
        String s = raw.trim().replace('T', ' ');
        if (s.length() == 10) s = s + " 23:59:59";
        if (s.length() > 19) s = s.substring(0, 19);
        try {
            return LocalDateTime.parse(s, MUTE_FMT);
        } catch (Exception e) {
            try {
                return LocalDateTime.parse(s, DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"));
            } catch (Exception e2) {
                return null;
            }
        }
    }

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
            String muteUntil = "";
            if (extras != null && extras.get("postMuteUntil") != null) {
                muteUntil = extras.get("postMuteUntil");
            }
            m.put("postMuteUntil", muteUntil == null ? "" : muteUntil);
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

    /** 站内信等展示用：昵称 → 资料真实姓名 → 用户名。 */
    public static String displayName(String username) {
        if (username == null || username.isBlank()) return "用户";
        Profile p = get(username.trim());
        if (p == null) return username.trim();
        if (p.nickname != null && !p.nickname.isBlank()) return p.nickname.trim();
        if (p.extras != null) {
            String real = p.extras.get("realName");
            if (real != null && !real.isBlank()) return real.trim();
        }
        return p.username;
    }

    /**
     * 管理端通知里的「谁」：账号展示名为主；业务名（就诊人/入住人）若有效且不同于登录名则附带。
     * 避免把 username 原样写进文案。
     */
    public static String notifyWho(String username, String... bizNames) {
        String shown = displayName(username);
        String un = username == null ? "" : username.trim();
        for (String raw : bizNames) {
            if (raw == null) continue;
            String n = raw.trim();
            if (n.isEmpty() || n.equalsIgnoreCase(un)) continue;
            if (n.equals(shown)) return shown;
            return shown + "（" + n + "）";
        }
        return shown;
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

    /** 仅校验口令（不论是否停用），供登录区分「错密」与「已停用」。 */
    public static boolean passwordMatches(Profile p, String password) {
        return p != null && PasswordHashes.matches(password, p.password);
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

    /**
     * 多店商家入驻：role=admin、非超管、岗位 shop_merchant、默认停用待审。
     */
    public static Profile registerMerchant(
            String username,
            String password,
            String nickname,
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
        String nick = nickname == null || nickname.isBlank() ? username : nickname.trim();
        String ph = phone == null ? "" : phone.trim();
        Map<String, String> ex = ProfileFields.filterExtras(extras);
        // 商家入驻：校验 staff 受众字段（店铺名称等），勿套买家收货字段
        ProfileFields.requireFilled(ph, ex, true, "staff");
        String encoded = PasswordHashes.encode(password);
        ensureStaffColumns();
        if (hasProfileJson()) {
            db().update(
                    "INSERT INTO sys_user (username,password,role,nickname,phone,avatar_url,profile_json,"
                            + "super_admin,profile_editable,enabled,staff_post,staff_kind) "
                            + "VALUES (?,?,?,?,?,?,?,0,1,0,'shop_merchant','clerk')",
                    username, encoded, "admin", nick, ph, "", writeExtras(ex));
        } else {
            db().update(
                    "INSERT INTO sys_user (username,password,role,nickname,phone,avatar_url,"
                            + "super_admin,profile_editable,enabled,staff_post,staff_kind) "
                            + "VALUES (?,?,?,?,?,?,0,1,0,'shop_merchant','clerk')",
                    username, encoded, "admin", nick, ph, "");
        }
        return get(username);
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
                    boolean isMerchant = isSub && "shop_merchant".equals(
                            p.staffPost == null ? "" : p.staffPost.trim());
                    boolean isUser = !isSub && (ur.equals(p.role) || "user".equals(p.role)
                            || "student".equals(p.role) || "reader".equals(p.role)
                            || "patient".equals(p.role));
                    if ("merchants".equals(sc)) return isMerchant;
                    if ("subadmins".equals(sc)) return isSub && !isMerchant;
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
        return adminUpdate(username, nickname, phone, enabled, extras, false);
    }

    public static Profile adminUpdate(
            String username,
            String nickname,
            String phone,
            Boolean enabled,
            Map<String, String> extras,
            boolean protectLastStaff) {
        Profile p = requireManaged(username);
        if (nickname != null) p.nickname = nickname.trim();
        if (phone != null) p.phone = phone.trim();
        if (enabled != null && !enabled && p.enabled) {
            assertNotSoleActiveStaff(p, protectLastStaff, "停用");
        }
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
        return adminUpdate(username, nickname, phone, enabled, null, false);
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
        return revokeSubAdmin(username, userRole, true);
    }

    /**
     * @param protectLastStaff 为 true 且本岗仅剩一名启用账号时拒绝撤销（禁任命域）
     */
    public static Profile revokeSubAdmin(String username, String userRole, boolean protectLastStaff) {
        ensureStaffColumns();
        Profile p = get(username);
        if (p == null) throw new IllegalArgumentException("用户不存在");
        if (p.superAdmin) throw new IllegalArgumentException("不可撤销总管");
        if (!"admin".equals(p.role)) throw new IllegalArgumentException("该账号不是岗位员工");
        assertNotSoleActiveStaff(p, protectLastStaff, "撤销");
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

    /**
     * 禁任命域：该岗「启用中」只剩此人时不可撤/停用。
     * 与 countStaffWithPost(enabledOnly=true) 共用计数，避免两套规则。
     */
    public static void assertNotSoleActiveStaff(Profile p, boolean protect, String action) {
        if (!protect || p == null) return;
        if (!"admin".equals(p.role) || p.superAdmin) return;
        if (!p.enabled) return;
        String post = p.staffPost == null ? "" : p.staffPost.trim();
        if (countStaffWithPost(post, true) <= 1) {
            throw new IllegalArgumentException(
                    "这是该岗位唯一启用账号，" + action + "后无法再任命业务用户顶替，已禁止" + action);
        }
    }

    public static int countStaffWithPost(String staffPost) {
        return countStaffWithPost(staffPost, false);
    }

    /** 非总管且 role=admin、同一 staff_post；enabledOnly 时只计启用中 */
    public static int countStaffWithPost(String staffPost, boolean enabledOnly) {
        ensureStaffColumns();
        String post = staffPost == null ? "" : staffPost.trim();
        String en = enabledOnly ? " AND IFNULL(enabled,1)=1" : "";
        Integer n;
        if (post.isEmpty()) {
            n = db().queryForObject(
                    "SELECT COUNT(*) FROM sys_user WHERE role='admin' AND IFNULL(super_admin,0)=0" + en,
                    Integer.class);
        } else if (hasStaffColumns()) {
            n = db().queryForObject(
                    "SELECT COUNT(*) FROM sys_user WHERE role='admin' AND IFNULL(super_admin,0)=0"
                            + en + " AND IFNULL(staff_post,'')=?",
                    Integer.class,
                    post);
        } else {
            n = db().queryForObject(
                    "SELECT COUNT(*) FROM sys_user WHERE role='admin' AND IFNULL(super_admin,0)=0" + en,
                    Integer.class);
        }
        return n == null ? 0 : n;
    }

    private static Profile requireManaged(String username) {
        Profile p = get(username);
        if (p == null) throw new IllegalArgumentException("用户不存在");
        if (p.superAdmin) throw new IllegalArgumentException("不可在此管理总管账号");
        return p;
    }

    public static void saveProfile(Profile p) {
        String audience = isStaffAccount(p) ? "staff" : "user";
        ProfileFields.requireFilled(p.phone, p.extras, false, audience);
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

    /** 总管/子管/业务岗：不校验终端用户业务档案（就诊卡等） */
    private static boolean isStaffAccount(Profile p) {
        if (p == null) return false;
        if (p.superAdmin) return true;
        if (p.staffPost != null && !p.staffPost.isBlank()) return true;
        return "admin".equals(p.role);
    }
}
