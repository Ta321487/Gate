package com.thesis.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.common.PasswordHashes;
import com.thesis.config.AppPolicy;
import com.thesis.config.JpaSupport;
import com.thesis.config.JpaDb;
import com.thesis.config.SqlRowMapper;

import java.sql.ResultSet;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 基线用户档案（MySQL sys_user）：phone 列 + profile_json 扩展 + staff_post/staff_kind。
 */
public class UserStore {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static Boolean staffColsReady;

    private static final DateTimeFormatter MUTE_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final DateTimeFormatter AUTH_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
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
        if (end == null) return;
        if (LocalDateTime.now().isBefore(end)) {
            throw new IllegalStateException("您已被禁言至 " + until + "，期间不可发帖或回复");
        }
        try {
            db().update("UPDATE sys_user SET post_mute_until=NULL WHERE username=?", username.trim());
        } catch (Exception ignored) {
        }
    }

    public static int clearExpiredPostMutes() {
        if (!postMuteEnabled) return 0;
        try {
            return db().update(
                    "UPDATE sys_user SET post_mute_until=NULL "
                            + "WHERE post_mute_until IS NOT NULL AND post_mute_until < NOW()");
        } catch (Exception e) {
            return 0;
        }
    }

    public static String postMuteUntilOf(String username) {
        if (username == null || username.isBlank()) return "";
        Profile p = get(username.trim());
        if (p == null) return "";
        return p.postMuteUntil == null ? "" : p.postMuteUntil.trim();
    }

    /**
     * 设禁言截止；until 空白则解除。写入 sys_user.post_mute_until。
     * @return 更新后的档案 map（含 postMuteUntil）
     */
    public static Map<String, Object> setPostMuteUntil(String username, String untilRaw) {
        if (!postMuteEnabled) {
            throw new IllegalStateException("禁言功能暂不可用");
        }
        requireManaged(username);
        String raw = untilRaw == null ? "" : untilRaw.trim();
        String sqlVal = null;
        if (!(raw.isBlank() || "null".equalsIgnoreCase(raw))) {
            LocalDateTime end = parseMuteUntil(raw);
            if (end == null) {
                throw new IllegalArgumentException("禁言截止时间格式无效，请使用 yyyy-MM-dd HH:mm:ss");
            }
            if (!end.isAfter(LocalDateTime.now())) {
                throw new IllegalArgumentException("禁言截止须晚于当前时间");
            }
            sqlVal = end.format(MUTE_FMT);
        }
        db().update(
                "UPDATE sys_user SET post_mute_until=? WHERE username=?",
                sqlVal, username.trim());
        Profile updated = get(username.trim());
        return updated == null ? Map.of() : updated.toMap();
    }

    /** 按天数设禁言（默认 7 天）；days<=0 解除。 */
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
        public String postMuteUntil = "";
        /** §0 X-AUTH：连续失败次数（旧库无列时为 0） */
        public int failedLoginCount;
        public String lockUntil = "";
        public boolean mustChangePassword;
        public String passwordChangedAt = "";
        public String securityQuestion = "";
        /** 仅内部校验，不进 toMap */
        public String securityAnswerHash = "";
        public boolean emailActivated;
        public String activationCode = "";
        public boolean realNameAcked;

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
            m.put("postMuteUntil", postMuteUntil == null ? "" : postMuteUntil);
            m.put("mustChangePassword", effectiveMustChange(this));
            m.put("passwordChangedAt", passwordChangedAt == null ? "" : passwordChangedAt);
            m.put("hasSecurityQuestion", securityQuestion != null && !securityQuestion.isBlank());
            m.put("emailActivated", emailActivated);
            m.put("mustActivateEmail", effectiveMustActivate(this));
            m.put("realNameAcked", realNameAcked);
            if (extras != null) {
                for (Map.Entry<String, String> e : extras.entrySet()) {
                    m.putIfAbsent(e.getKey(), e.getValue());
                }
            }
            return m;
        }
    }

    private static final SqlRowMapper<Profile> MAPPER = (rs, i) -> mapRow(rs);

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
        try {
            String mu = rs.getString("post_mute_until");
            p.postMuteUntil = mu == null ? "" : mu.trim();
        } catch (Exception e) {
            p.postMuteUntil = "";
        }
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
        try {
            p.failedLoginCount = rs.getInt("failed_login_count");
        } catch (Exception e) {
            p.failedLoginCount = 0;
        }
        try {
            String lu = rs.getString("lock_until");
            p.lockUntil = lu == null ? "" : lu.trim();
        } catch (Exception e) {
            p.lockUntil = "";
        }
        try {
            p.mustChangePassword = rs.getInt("must_change_password") == 1;
        } catch (Exception e) {
            p.mustChangePassword = false;
        }
        try {
            String pca = rs.getString("password_changed_at");
            p.passwordChangedAt = pca == null ? "" : pca.trim();
        } catch (Exception e) {
            p.passwordChangedAt = "";
        }
        try {
            String sq = rs.getString("security_question");
            p.securityQuestion = sq == null ? "" : sq.trim();
        } catch (Exception e) {
            p.securityQuestion = "";
        }
        try {
            String sah = rs.getString("security_answer_hash");
            p.securityAnswerHash = sah == null ? "" : sah.trim();
        } catch (Exception e) {
            p.securityAnswerHash = "";
        }
        try {
            p.emailActivated = rs.getInt("email_activated") == 1;
        } catch (Exception e) {
            p.emailActivated = true;
        }
        try {
            String ac = rs.getString("activation_code");
            p.activationCode = ac == null ? "" : ac.trim();
        } catch (Exception e) {
            p.activationCode = "";
        }
        try {
            p.realNameAcked = rs.getInt("real_name_acked") == 1;
        } catch (Exception e) {
            p.realNameAcked = false;
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
            throw new IllegalStateException("扩展资料无法保存", e);
        }
    }

    private static void requireProfileJsonIfExtras(Map<String, String> extras) {
        if (extras == null || extras.isEmpty()) return;
        boolean any = extras.values().stream().anyMatch(v -> v != null && !v.isBlank());
        if (any && !hasProfileJson()) {
            throw new IllegalStateException("系统未配置扩展资料字段，无法保存");
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

    private static JpaDb db() {
        return JpaSupport.db();
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
        clearLoginFailures(username);
        Profile fresh = get(username);
        return fresh == null ? p : fresh;
    }

    /** 仅校验口令（不论是否停用），供登录区分「错密」与「已停用」。 */
    public static boolean passwordMatches(Profile p, String password) {
        return p != null && PasswordHashes.matches(password, p.password);
    }

/** 冷却剩余分钟；未锁定返回 0。旧库无列时视为未锁定。 */
    public static int lockRemainMinutes(Profile p) {
        if (p == null || p.lockUntil == null || p.lockUntil.isBlank()) return 0;
        LocalDateTime until = parseAuthDateTime(p.lockUntil);
        if (until == null) return 0;
        LocalDateTime now = LocalDateTime.now();
        if (!now.isBefore(until)) return 0;
        long mins = ChronoUnit.MINUTES.between(now, until);
        return (int) Math.max(1, mins + (ChronoUnit.SECONDS.between(now, until) % 60 == 0 ? 0 : 1));
    }

    public static void recordFailedLogin(String username) {
        if (username == null || username.isBlank()) return;
        if (!columnExists("failed_login_count")) return;
        String un = username.trim();
        Profile p = get(un);
        if (p == null) return;
        int n = p.failedLoginCount + 1;
        int max = Math.max(1, AppPolicy.AUTH_LOCK_MAX_ATTEMPTS);
        if (n >= max && columnExists("lock_until")) {
            LocalDateTime until = LocalDateTime.now().plusMinutes(Math.max(1, AppPolicy.AUTH_LOCK_MINUTES));
            db().update(
                    "UPDATE sys_user SET failed_login_count=0, lock_until=? WHERE username=?",
                    until.format(AUTH_FMT), un);
        } else {
            db().update("UPDATE sys_user SET failed_login_count=? WHERE username=?", n, un);
        }
    }

    public static void clearLoginFailures(String username) {
        if (username == null || username.isBlank()) return;
        if (!columnExists("failed_login_count") && !columnExists("lock_until")) return;
        try {
            if (columnExists("failed_login_count") && columnExists("lock_until")) {
                db().update(
                        "UPDATE sys_user SET failed_login_count=0, lock_until=NULL WHERE username=?",
                        username.trim());
            } else if (columnExists("failed_login_count")) {
                db().update("UPDATE sys_user SET failed_login_count=0 WHERE username=?", username.trim());
            } else {
                db().update("UPDATE sys_user SET lock_until=NULL WHERE username=?", username.trim());
            }
        } catch (Exception ignored) {
        }
    }

    public static boolean effectiveMustActivate(Profile p) {
        if (p == null) return false;
        if (AppPolicy.AUTH_REQUIRE_EMAIL_ACTIVATE <= 0) return false;
        return !p.emailActivated;
    }

    public static boolean effectiveMustChange(Profile p) {
        if (p == null) return false;
        if (p.mustChangePassword) return true;
        int maxDays = AppPolicy.AUTH_PASSWORD_MAX_DAYS;
        if (maxDays <= 0) return false;
        if (p.passwordChangedAt == null || p.passwordChangedAt.isBlank()) return true;
        LocalDateTime changed = parseAuthDateTime(p.passwordChangedAt);
        if (changed == null) return true;
        return changed.plusDays(maxDays).isBefore(LocalDateTime.now());
    }

    public static void assertPasswordStrength(String password) {
        int min = Math.max(1, AppPolicy.AUTH_PASSWORD_MIN_LENGTH);
        if (password == null || password.length() < min) {
            throw new IllegalArgumentException("密码至少 " + min + " 位");
        }
    }

    public static void forceChangePassword(String username, String newPassword) {
        assertPasswordStrength(newPassword);
        Profile p = get(username);
        if (p == null) throw new IllegalArgumentException("用户不存在");
        String encoded = PasswordHashes.encode(newPassword);
        String now = LocalDateTime.now().format(AUTH_FMT);
        if (columnExists("must_change_password") && columnExists("password_changed_at")) {
            db().update(
                    "UPDATE sys_user SET password=?, must_change_password=0, password_changed_at=?, "
                            + "failed_login_count=0, lock_until=NULL WHERE username=?",
                    encoded, now, username.trim());
        } else {
            db().update("UPDATE sys_user SET password=? WHERE username=?", encoded, username.trim());
        }
    }

    public static void setSecurityQuestion(String username, String question, String answer) {
        if (!columnExists("security_question")) {
            throw new IllegalStateException("当前系统未启用密保");
        }
        String q = question == null ? "" : question.trim();
        String a = answer == null ? "" : answer.trim();
        if (q.isBlank() || a.isBlank()) {
            throw new IllegalArgumentException("请填写密保问题与答案");
        }
        if (q.length() > 128) throw new IllegalArgumentException("密保问题过长");
        db().update(
                "UPDATE sys_user SET security_question=?, security_answer_hash=? WHERE username=?",
                q, PasswordHashes.encode(a.toLowerCase(Locale.ROOT)), username.trim());
    }

    /** 匿名查询：无用户或无密保时返回空串（防枚举）。 */
    public static String publicSecurityQuestion(String username) {
        if (username == null || username.isBlank() || !columnExists("security_question")) return "";
        Profile p = get(username.trim());
        if (p == null) return "";
        return p.securityQuestion == null ? "" : p.securityQuestion.trim();
    }

    public static void resetPasswordBySecurity(String username, String answer, String newPassword) {
        assertPasswordStrength(newPassword);
        if (!columnExists("security_answer_hash")) {
            throw new IllegalStateException("当前系统未启用密保");
        }
        Profile p = get(username == null ? "" : username.trim());
        if (p == null
                || p.securityAnswerHash == null
                || p.securityAnswerHash.isBlank()
                || answer == null
                || !PasswordHashes.matches(answer.trim().toLowerCase(Locale.ROOT), p.securityAnswerHash)) {
            throw new IllegalArgumentException("密保答案不正确");
        }
        forceChangePassword(p.username, newPassword);
    }

    private static LocalDateTime parseAuthDateTime(String raw) {
        if (raw == null || raw.isBlank()) return null;
        String s = raw.trim().replace('T', ' ');
        if (s.length() == 10) s = s + " 00:00:00";
        if (s.length() > 19) s = s.substring(0, 19);
        try {
            return LocalDateTime.parse(s, AUTH_FMT);
        } catch (Exception e) {
            try {
                return LocalDateTime.parse(s, DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"));
            } catch (Exception e2) {
                return null;
            }
        }
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
        assertPasswordStrength(password);
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
        assertPhoneUnique(ph, null);
        assertIdExtraUnique(ex, null);
        requireProfileJsonIfExtras(ex);
        String encoded = PasswordHashes.encode(password);
        ensureStaffColumns();
        String now = LocalDateTime.now().format(AUTH_FMT);
        if (hasProfileJson()) {
            if (columnExists("password_changed_at")) {
                db().update(
                        "INSERT INTO sys_user (username,password,role,nickname,phone,avatar_url,profile_json,"
                                + "super_admin,profile_editable,enabled,password_changed_at) "
                                + "VALUES (?,?,?,?,?,?,?,0,1,1,?)",
                        username, encoded, r, nick, ph, "", writeExtras(ex), now);
            } else {
                db().update(
                        "INSERT INTO sys_user (username,password,role,nickname,phone,avatar_url,profile_json,super_admin,profile_editable,enabled) "
                                + "VALUES (?,?,?,?,?,?,?,0,1,1)",
                        username, encoded, r, nick, ph, "", writeExtras(ex));
            }
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
        assertPasswordStrength(password);
        if (get(username) != null) {
            throw new IllegalStateException("用户名已存在");
        }
        String nick = nickname == null || nickname.isBlank() ? username : nickname.trim();
        String ph = phone == null ? "" : phone.trim();
        Map<String, String> ex = ProfileFields.filterExtras(extras);
        ProfileFields.requireFilled(ph, ex, true, "staff");
        requireProfileJsonIfExtras(ex);
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
        requireProfileJsonIfExtras(p.extras);
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
        assertPasswordStrength(newPassword);
        String encoded = PasswordHashes.encode(newPassword);
        if (columnExists("must_change_password")) {
            db().update(
                    "UPDATE sys_user SET password=?, must_change_password=1, password_changed_at=NULL, "
                            + "failed_login_count=0, lock_until=NULL WHERE username=?",
                    encoded, username);
        } else {
            db().update(
                    "UPDATE sys_user SET password=? WHERE username=?",
                    encoded, username);
        }
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

    private static final String[] ID_EXTRA_KEYS = {
        "studentNo", "studentId", "jobNo", "workNo", "employeeNo", "staffNo", "readerNo"
    };

    public static void assertPhoneUnique(String phone, String excludeUsername) {
        String ph = phone == null ? "" : phone.trim();
        if (ph.isBlank()) return;
        String sql = "SELECT COUNT(*) FROM sys_user WHERE phone=?";
        Object[] args;
        if (excludeUsername != null && !excludeUsername.isBlank()) {
            sql += " AND username<>?";
            args = new Object[] {ph, excludeUsername.trim()};
        } else {
            args = new Object[] {ph};
        }
        Integer n = db().queryForObject(sql, Integer.class, args);
        if (n != null && n > 0) {
            throw new IllegalStateException("该手机号已被使用，请更换");
        }
    }

    public static void assertIdExtraUnique(Map<String, String> extras, String excludeUsername) {
        if (extras == null || extras.isEmpty() || !hasProfileJson()) return;
        for (String key : ID_EXTRA_KEYS) {
            String val = extras.get(key);
            if (val == null || val.isBlank()) continue;
            String v = val.trim();
            List<Profile> all = db().query("SELECT * FROM sys_user", MAPPER);
            for (Profile other : all) {
                if (excludeUsername != null && excludeUsername.equals(other.username)) continue;
                if (other.extras == null) continue;
                String ov = other.extras.get(key);
                if (ov != null && v.equals(ov.trim())) {
                    throw new IllegalStateException("该学号或工号已被绑定，请核对");
                }
            }
        }
    }

    public static String issueActivationCode(String username) {
        if (username == null || username.isBlank() || !columnExists("activation_code")) return "";
        String code = String.format("%06d", new java.util.Random().nextInt(1_000_000));
        if (columnExists("email_activated")) {
            db().update(
                    "UPDATE sys_user SET activation_code=?, email_activated=0 WHERE username=?",
                    code, username.trim());
        } else {
            db().update("UPDATE sys_user SET activation_code=? WHERE username=?", code, username.trim());
        }
        return code;
    }

    public static void activateByCode(String username, String code) {
        Profile p = get(username);
        if (p == null) throw new IllegalArgumentException("账号不存在或激活码不正确");
        String expect = p.activationCode == null ? "" : p.activationCode.trim();
        String got = code == null ? "" : code.trim();
        if (expect.isBlank() || !expect.equalsIgnoreCase(got)) {
            throw new IllegalArgumentException("账号不存在或激活码不正确");
        }
        if (columnExists("email_activated") && columnExists("activation_code")) {
            db().update(
                    "UPDATE sys_user SET email_activated=1, activation_code=NULL WHERE username=?",
                    username.trim());
        } else if (columnExists("email_activated")) {
            db().update("UPDATE sys_user SET email_activated=1 WHERE username=?", username.trim());
        }
    }

    public static void changeContact(String username, String field, String value) {
        Profile p = get(username);
        if (p == null) throw new IllegalArgumentException("用户不存在");
        String f = field == null ? "" : field.trim().toLowerCase(Locale.ROOT);
        String v = value == null ? "" : value.trim();
        if ("phone".equals(f)) {
            if (!v.isBlank() && !v.matches("^1[3-9]\\d{9}$")) {
                throw new IllegalArgumentException("手机号格式不正确（11 位）");
            }
            assertPhoneUnique(v, username);
            db().update("UPDATE sys_user SET phone=? WHERE username=?", v, username.trim());
            return;
        }
        if ("email".equals(f)) {
            if (!v.isBlank() && !v.matches("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")) {
                throw new IllegalArgumentException("邮箱格式不正确");
            }
            Map<String, String> ex = new LinkedHashMap<>(p.extras == null ? Map.of() : p.extras);
            if (v.isBlank()) ex.remove("email");
            else ex.put("email", v);
            requireProfileJsonIfExtras(ex);
            if (!hasProfileJson()) {
                throw new IllegalStateException("系统未配置扩展资料字段，无法保存邮箱");
            }
            db().update(
                    "UPDATE sys_user SET profile_json=? WHERE username=?",
                    writeExtras(ex),
                    username.trim());
            return;
        }
        throw new IllegalArgumentException("仅支持修改手机号或邮箱");
    }

    public static void setRealNameAcked(String username, boolean acked) {
        Profile p = get(username);
        if (p == null) throw new IllegalArgumentException("用户不存在");
        if (acked) {
            String rn = "";
            if (p.extras != null) {
                rn = p.extras.getOrDefault("realName", "");
                if (rn == null || rn.isBlank()) rn = p.extras.getOrDefault("name", "");
            }
            if ((rn == null || rn.isBlank()) && (p.nickname == null || p.nickname.isBlank())) {
                throw new IllegalArgumentException("请先填写姓名后再确认实名");
            }
        }
        if (!columnExists("real_name_acked")) return;
        db().update(
                "UPDATE sys_user SET real_name_acked=? WHERE username=?",
                acked ? 1 : 0,
                username.trim());
    }

    public static void saveProfile(Profile p) {
        String audience = isStaffAccount(p) ? "staff" : "user";
        ProfileFields.requireFilled(p.phone, p.extras, false, audience);
        assertPhoneUnique(p.phone, p.username);
        assertIdExtraUnique(p.extras, p.username);
        requireProfileJsonIfExtras(p.extras);
        if (hasProfileJson()) {
            if (columnExists("real_name_acked")) {
                db().update(
                        "UPDATE sys_user SET nickname=?, phone=?, avatar_url=?, password=?, profile_json=?, real_name_acked=? WHERE username=?",
                        p.nickname, p.phone, p.avatarUrl, p.password, writeExtras(p.extras),
                        p.realNameAcked ? 1 : 0, p.username);
            } else {
                db().update(
                        "UPDATE sys_user SET nickname=?, phone=?, avatar_url=?, password=?, profile_json=? WHERE username=?",
                        p.nickname, p.phone, p.avatarUrl, p.password, writeExtras(p.extras), p.username);
            }
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
