package com.thesis.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.common.PasswordHashes;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.SchemaMapper;
import com.thesis.mapper.UserMapper;

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
        public String staffPost = "";
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
        if (hasStaffColumns()) {
            p.staffPost = str(col(raw, "staffPost", "staff_post")).trim();
            p.staffKind = str(col(raw, "staffKind", "staff_kind")).trim();
        }
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
            return "{}";
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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("username", username);
        row.put("password", encoded);
        row.put("role", r);
        row.put("nickname", nick);
        row.put("phone", ph);
        row.put("avatarUrl", "");
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

    public static List<Map<String, Object>> listByRole(String role, String keyword) {
        return listManaged(role, "users", keyword);
    }

    public static List<Map<String, Object>> listManaged(String userRole, String scope, String keyword) {
        String kw = keyword == null ? "" : keyword.trim();
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
        if (newPassword == null || newPassword.length() < 6) {
            throw new IllegalArgumentException("密码至少 6 位");
        }
        mapper().updatePassword(username, PasswordHashes.encode(newPassword));
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

    public static void saveProfile(Profile p) {
        String audience = isStaffAccount(p) ? "staff" : "user";
        ProfileFields.requireFilled(p.phone, p.extras, false, audience);
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
    }

    private static boolean isStaffAccount(Profile p) {
        if (p == null) return false;
        if (p.superAdmin) return true;
        if (p.staffPost != null && !p.staffPost.isBlank()) return true;
        return "admin".equals(p.role);
    }
}
