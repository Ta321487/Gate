package com.thesis.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.common.PasswordHashes;
import com.thesis.config.AppPolicy;
import com.thesis.config.MbSql;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.SchemaMapper;
import com.thesis.mapper.UserMapper;

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
        mapper().updatePostMuteUntil(username.trim(), sqlVal);
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
        public String staffPost = "";
        public String staffKind = "";
        public String postMuteUntil = "";
        /** 连续失败次数（旧库无列时为 0） */
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
        /** 管理端标签（逗号分隔；≠ 组织树） */
        public String adminTags = "";
        public Long orgId;

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
            m.put("adminTags", adminTags == null ? "" : adminTags);
            m.put("orgId", orgId);
            if (extras != null) {
                for (Map.Entry<String, String> e : extras.entrySet()) {
                    m.putIfAbsent(e.getKey(), e.getValue());
                }
            }
            return m;
        }
    }

    private static MbSql db() {
        return MybatisSupport.db();
    }

    private static UserMapper mapper() {
        return MybatisSupport.mapper(UserMapper.class);
    }

    private static SchemaMapper schema() {
        return MybatisSupport.mapper(SchemaMapper.class);
    }

    private static Profile fromMap(Map<String, Object> raw) {
        if (raw == null) return null;
        Profile p = new Profile();
        p.username = str(col(raw, "username"));
        p.password = str(col(raw, "password"));
        p.role = str(col(raw, "role"));
        p.nickname = str(col(raw, "nickname"));
        p.phone = str(col(raw, "phone"));
        // Map 结果键常为 JDBC 列名（snake）；mapUnderscoreToCamelCase 对 Map 不可靠
        p.avatarUrl = str(col(raw, "avatarUrl", "avatar_url"));
        p.superAdmin = flag(col(raw, "superAdmin", "super_admin"));
        p.profileEditable = flag(col(raw, "profileEditable", "profile_editable"));
        Object en = col(raw, "enabled");
        p.enabled = en == null || flag(en);
        p.extras = readExtras(col(raw, "profileJson", "profile_json"));
        p.postMuteUntil = str(col(raw, "postMuteUntil", "post_mute_until")).trim();
        if (hasStaffColumns()) {
            p.staffPost = str(col(raw, "staffPost", "staff_post")).trim();
            p.staffKind = str(col(raw, "staffKind", "staff_kind")).trim();
        }
        Object flc = col(raw, "failedLoginCount", "failed_login_count");
        p.failedLoginCount = flc instanceof Number n ? n.intValue() : 0;
        p.lockUntil = str(col(raw, "lockUntil", "lock_until")).trim();
        p.mustChangePassword = flag(col(raw, "mustChangePassword", "must_change_password"));
        p.passwordChangedAt = str(col(raw, "passwordChangedAt", "password_changed_at")).trim();
        p.securityQuestion = str(col(raw, "securityQuestion", "security_question")).trim();
        p.securityAnswerHash = str(col(raw, "securityAnswerHash", "security_answer_hash")).trim();
        Object ea = col(raw, "emailActivated", "email_activated");
        p.emailActivated = ea == null || flag(ea);
        p.activationCode = str(col(raw, "activationCode", "activation_code")).trim();
        p.realNameAcked = flag(col(raw, "realNameAcked", "real_name_acked"));
        p.adminTags = str(col(raw, "adminTags", "admin_tags")).trim();
        Object oid = col(raw, "orgId", "org_id");
        p.orgId = oid instanceof Number n ? n.longValue() : null;
        return p;
    }

    /** 兼容 camelCase / snake_case 列名（MyBatis resultType=map）。 */
    private static Object col(Map<String, Object> raw, String... keys) {
        if (raw == null || keys == null) return null;
        for (String k : keys) {
            if (k == null) continue;
            if (raw.containsKey(k)) return raw.get(k);
        }
        // 部分驱动返回大写列名
        for (String k : keys) {
            if (k == null) continue;
            for (Map.Entry<String, Object> e : raw.entrySet()) {
                if (e.getKey() != null && e.getKey().equalsIgnoreCase(k)) {
                    return e.getValue();
                }
            }
        }
        return null;
    }

    private static boolean flag(Object o) {
        if (o instanceof Boolean b) return b;
        if (o instanceof Number n) return n.intValue() == 1;
        return "1".equals(String.valueOf(o)) || "true".equalsIgnoreCase(String.valueOf(o));
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }

    private static Map<String, String> readExtras(Object rawObj) {
        try {
            String raw = rawObj == null ? null : String.valueOf(rawObj);
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
            Integer n = schema().countColumn("sys_user", "profile_json");
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static boolean columnExists(String column) {
        try {
            Integer n = schema().countColumn("sys_user", column);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    public static synchronized void ensureStaffColumns() {
        if (Boolean.TRUE.equals(staffColsReady)) return;
        try {
            if (!columnExists("staff_post")) {
                schema().executeDdl("ALTER TABLE sys_user ADD COLUMN staff_post VARCHAR(64) DEFAULT ''");
            }
            if (!columnExists("staff_kind")) {
                schema().executeDdl("ALTER TABLE sys_user ADD COLUMN staff_kind VARCHAR(16) DEFAULT ''");
            }
            staffColsReady = columnExists("staff_post") && columnExists("staff_kind");
        } catch (Exception e) {
            staffColsReady = null;
        }
    }

    private static boolean hasStaffColumns() {
        if (!Boolean.TRUE.equals(staffColsReady)) {
            ensureStaffColumns();
        }
        return Boolean.TRUE.equals(staffColsReady);
    }

    public static Profile get(String username) {
        return fromMap(mapper().selectByUsername(username));
    }

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
        if (p == null) return null;
        if (!PasswordHashes.matches(password, p.password)) return null;
        if (!p.enabled) return null;
        if (PasswordHashes.needsUpgrade(p.password)) {
            String encoded = PasswordHashes.encode(password);
            mapper().updatePassword(username, encoded);
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
            mapper().updateLoginLock(un, 0, until.format(AUTH_FMT));
        } else {
            mapper().updateFailedLoginCount(un, n);
        }
    }

    public static void clearLoginFailures(String username) {
        if (username == null || username.isBlank()) return;
        if (!columnExists("failed_login_count") && !columnExists("lock_until")) return;
        try {
            mapper().clearLoginFailures(username.trim());
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
            mapper().updatePasswordChanged(username.trim(), encoded, now);
        } else {
            mapper().updatePassword(username.trim(), encoded);
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
        mapper().updateSecurityQuestion(
                username.trim(), q, PasswordHashes.encode(a.toLowerCase(Locale.ROOT)));
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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("username", username);
        row.put("password", encoded);
        row.put("role", r);
        row.put("nickname", nick);
        row.put("phone", ph);
        row.put("avatarUrl", "");
        if (columnExists("password_changed_at")) {
            row.put("passwordChangedAt", LocalDateTime.now().format(AUTH_FMT));
        }
        if (hasProfileJson()) {
            row.put("profileJson", writeExtras(ex));
            mapper().insertWithProfile(row);
        } else {
            mapper().insertPlain(row);
        }
        return get(username);
    }

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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("username", username);
        row.put("password", encoded);
        row.put("nickname", nick);
        row.put("phone", ph);
        row.put("avatarUrl", "");
        if (hasProfileJson()) {
            row.put("profileJson", writeExtras(ex));
            mapper().insertMerchantWithProfile(row);
        } else {
            mapper().insertMerchantPlain(row);
        }
        return get(username);
    }

    public static List<Map<String, Object>> listByRole(String role, String keyword) {
        return listManaged(role, "users", keyword);
    }

    public static List<Map<String, Object>> listManaged(String userRole, String scope, String keyword) {
        return listManaged(userRole, scope, keyword, null);
    }

    public static List<Map<String, Object>> listManaged(
            String userRole, String scope, String keyword, String tag) {
        String kw = keyword == null ? "" : keyword.trim();
        String tagFilter = tag == null ? "" : tag.trim();
        String sc = scope == null || scope.isBlank() ? "users" : scope.trim();
        String ur = (userRole == null || userRole.isBlank()) ? "user" : userRole.trim();
        List<Map<String, Object>> raw = mapper().selectAll();
        List<Profile> all = new ArrayList<>();
        if (raw != null) {
            for (Map<String, Object> r : raw) {
                Profile p = fromMap(r);
                if (p != null) all.add(p);
            }
        }
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
                    if (tagFilter.isBlank()) return true;
                    return tagList(p.adminTags).stream().anyMatch(t -> t.equalsIgnoreCase(tagFilter)
                            || t.contains(tagFilter));
                })
                .filter(p -> {
                    if (kw.isBlank()) return true;
                    if (p.username.contains(kw)
                            || (p.nickname != null && p.nickname.contains(kw))
                            || (p.phone != null && p.phone.contains(kw))
                            || (p.staffPost != null && p.staffPost.contains(kw))
                            || (p.adminTags != null && p.adminTags.contains(kw))) {
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

    public static String normalizeAdminTags(String raw) {
        if (raw == null || raw.isBlank()) return "";
        LinkedHashSet<String> set = new LinkedHashSet<>();
        for (String part : raw.split("[,，;；\\s]+")) {
            String t = part == null ? "" : part.trim();
            if (!t.isBlank() && t.length() <= 32) set.add(t);
            if (set.size() >= 8) break;
        }
        return String.join(",", set);
    }

    private static List<String> tagList(String raw) {
        String n = normalizeAdminTags(raw);
        if (n.isBlank()) return List.of();
        return Arrays.asList(n.split(","));
    }

    public static Profile adminUpdateTags(String username, String tags) {
        Profile p = requireManaged(username);
        if (!columnExists("admin_tags")) {
            throw new IllegalStateException("系统未配置管理标签字段");
        }
        String normalized = normalizeAdminTags(tags);
        mapper().updateAdminTags(username, normalized);
        return get(username);
    }

    public static Profile updateOrgId(String username, Long orgId) {
        Profile p = get(username);
        if (p == null) throw new IllegalArgumentException("用户不存在");
        if (!columnExists("org_id")) {
            throw new IllegalStateException("系统未配置组织字段");
        }
        mapper().updateOrgId(username, orgId);
        return get(username);
    }

    public static List<String> batchSetEnabled(
            List<String> usernames, boolean enabled, boolean protectLastStaff) {
        if (usernames == null || usernames.isEmpty()) return List.of();
        List<String> ok = new ArrayList<>();
        for (String u : usernames) {
            if (u == null || u.isBlank()) continue;
            try {
                adminUpdate(u.trim(), null, null, enabled, null, protectLastStaff);
                ok.add(u.trim());
            } catch (IllegalArgumentException | IllegalStateException ignored) {
            }
        }
        return ok;
    }

    public static long countByRole(String role) {
        return mapper().countByRole(role);
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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("username", username);
        row.put("nickname", p.nickname);
        row.put("phone", p.phone);
        row.put("enabled", p.enabled ? 1 : 0);
        if (hasProfileJson()) {
            row.put("profileJson", writeExtras(p.extras));
            mapper().updateAdminWithProfile(row);
        } else {
            mapper().updateAdminPlain(row);
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
            mapper().updatePasswordForceChange(username, encoded);
        } else {
            mapper().updatePassword(username, encoded);
        }
    }

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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("username", username);
        row.put("role", "admin");
        row.put("staffPost", post);
        row.put("staffKind", kind);
        mapper().appointStaff(row);
        return get(username);
    }

    public static Profile appointSubAdmin(String username) {
        return appointSubAdmin(username, "subadmin", "clerk");
    }

    public static Profile revokeSubAdmin(String username, String userRole) {
        return revokeSubAdmin(username, userRole, true);
    }

    public static Profile revokeSubAdmin(String username, String userRole, boolean protectLastStaff) {
        ensureStaffColumns();
        Profile p = get(username);
        if (p == null) throw new IllegalArgumentException("用户不存在");
        if (p.superAdmin) throw new IllegalArgumentException("不可撤销总管");
        if (!"admin".equals(p.role)) throw new IllegalArgumentException("该账号不是岗位员工");
        assertNotSoleActiveStaff(p, protectLastStaff, "撤销");
        String ur = (userRole == null || userRole.isBlank()) ? "user" : userRole.trim();
        if (hasStaffColumns()) {
            mapper().revokeStaffWithCols(username, ur);
        } else {
            mapper().revokeStaffPlain(username, ur);
        }
        return get(username);
    }

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

    public static int countStaffWithPost(String staffPost, boolean enabledOnly) {
        ensureStaffColumns();
        String post = staffPost == null ? "" : staffPost.trim();
        return mapper().countStaff(post, enabledOnly, hasStaffColumns() && !post.isEmpty());
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
            for (Map<String, Object> raw : mapper().selectAll()) {
                Profile other = fromMap(raw);
                if (other == null) continue;
                if (excludeUsername != null && excludeUsername.equals(other.username)) continue;
                if (other.extras == null) continue;
                String ov = other.extras.get(key);
                if (ov != null && v.equals(ov.trim())) {
                    throw new IllegalStateException("该账号资料已被使用，请更换");
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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("username", p.username);
        row.put("nickname", p.nickname);
        row.put("phone", p.phone);
        row.put("avatarUrl", p.avatarUrl);
        row.put("password", p.password);
        if (hasProfileJson()) {
            row.put("profileJson", writeExtras(p.extras));
            mapper().saveProfileWithJson(row);
        } else {
            mapper().saveProfilePlain(row);
        }
        if (columnExists("real_name_acked")) {
            db().update(
                    "UPDATE sys_user SET real_name_acked=? WHERE username=?",
                    p.realNameAcked ? 1 : 0,
                    p.username);
        }
    }

    private static boolean isStaffAccount(Profile p) {
        if (p == null) return false;
        if (p.superAdmin) return true;
        if (p.staffPost != null && !p.staffPost.isBlank()) return true;
        return "admin".equals(p.role);
    }
}
