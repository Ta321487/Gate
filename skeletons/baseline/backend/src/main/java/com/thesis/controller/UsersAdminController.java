package com.thesis.controller;

import com.thesis.capability.AuditLogStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.AuthSessionStore;
import com.thesis.service.OrgStore;
import com.thesis.service.UserStore;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** 业务用户 + 子管任命：仅总管理员（super_admin） */
@RestController
@RequestMapping("/api/admin/users")
public class UsersAdminController {

    @Value("${thesis.register-role:user}")
    private String userRole;

    /** 门户业务用户可否任命为岗位；缺省 false，须 application.yml 显式打开 */
    @Value("${thesis.allow-appoint-from-users:false}")
    private boolean allowAppointFromUsers;

    @GetMapping
    public R<List<Map<String, Object>>> list(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String tag,
            @RequestParam(required = false) Long orgId,
            @RequestParam(required = false, defaultValue = "users") String scope,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        List<Map<String, Object>> rows = UserStore.listManaged(userRole, scope, keyword, tag);
        if (orgId != null && orgId > 0) {
            java.util.Set<Long> tree = OrgStore.subtreeIds(orgId);
            rows = rows.stream().filter(r -> {
                Object v = r.get("orgId");
                if (!(v instanceof Number n)) return false;
                return tree.contains(n.longValue());
            }).toList();
        }
        return R.ok(rows);
    }

    @PutMapping("/{username}")
    public R<Map<String, Object>> update(
            @PathVariable String username,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            Boolean enabled = null;
            if (body.get("enabled") != null) {
                enabled = Boolean.parseBoolean(String.valueOf(body.get("enabled")));
            }
            String nick = body.containsKey("nickname") ? String.valueOf(body.get("nickname")) : null;
            String phone = body.containsKey("phone") ? String.valueOf(body.get("phone")) : null;
            Map<String, String> extras = AuthController.extractExtras(body);
            if (extras.isEmpty() && !body.containsKey("extras")) extras = null;
            boolean protectLast = !allowAppointFromUsers;
            var updated = UserStore.adminUpdate(username, nick, phone, enabled, extras, protectLast);
            if (body.containsKey("adminTags")) {
                updated = UserStore.adminUpdateTags(username, String.valueOf(body.get("adminTags")));
            }
            if (body.containsKey("orgId")) {
                Object rawOrg = body.get("orgId");
                Long orgId = rawOrg == null || String.valueOf(rawOrg).isBlank()
                        || "null".equals(String.valueOf(rawOrg))
                        ? null
                        : Long.parseLong(String.valueOf(rawOrg).trim());
                updated = UserStore.updateOrgId(username, orgId);
            }
            if (enabled != null && !enabled) {
                AuthSessionStore.kickAll(username);
            }
            String op = AdminAuth.requireLogin(session);
            AuditLogStore.record(op, "user_update", "user", username, "更新用户资料或启用状态");
            return R.ok(updated.toMap());
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 批量启用/停用 */
    @PostMapping("/batch-enabled")
    public R<Map<String, Object>> batchEnabled(
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            Map<String, Object> b = body == null ? Map.of() : body;
            Object raw = b.get("usernames");
            List<String> names = new java.util.ArrayList<>();
            if (raw instanceof List<?> list) {
                for (Object o : list) {
                    if (o != null) names.add(String.valueOf(o).trim());
                }
            }
            boolean enabled = Boolean.parseBoolean(String.valueOf(b.getOrDefault("enabled", "true")));
            boolean protectLast = !allowAppointFromUsers;
            List<String> ok = UserStore.batchSetEnabled(names, enabled, protectLast);
            if (!enabled) {
                for (String u : ok) {
                    AuthSessionStore.kickAll(u);
                }
            }
            String op = AdminAuth.requireLogin(session);
            AuditLogStore.record(
                    op, "user_batch_enabled", "user", String.join(",", ok),
                    enabled ? "批量启用" : "批量停用");
            return R.ok(Map.of("count", ok.size(), "usernames", ok));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/{username}/reset-password")
    public R<Void> resetPassword(
            @PathVariable String username,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            UserStore.adminResetPassword(username, String.valueOf(body.getOrDefault("password", "")));
            String op = AdminAuth.requireLogin(session);
            AuditLogStore.record(op, "user_reset_password", "user", username, "重置密码");
            return R.ok(null);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 任命岗位（子管理 clerk / 业务员工 worker）；仅总管 */
    @PostMapping("/{username}/appoint")
    public R<Map<String, Object>> appoint(
            @PathVariable String username,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!allowAppointFromUsers) {
            throw new BizException(ErrorCode.BAD_REQUEST, "本系统不支持将业务用户任命为岗位，请使用预置岗位账号");
        }
        try {
            Map<String, Object> b = body == null ? Map.of() : body;
            String staffPost = String.valueOf(b.getOrDefault("staffPost", b.getOrDefault("staff_post", "")));
            String staffKind = String.valueOf(b.getOrDefault("staffKind", b.getOrDefault("staff_kind", "")));
            if ("null".equals(staffPost)) staffPost = "";
            if ("null".equals(staffKind)) staffKind = "";
            String op = AdminAuth.requireLogin(session);
            Map<String, Object> row;
            if (staffPost.isBlank() && staffKind.isBlank()) {
                row = UserStore.appointSubAdmin(username).toMap();
            } else {
                row = UserStore.appointSubAdmin(username, staffPost, staffKind).toMap();
            }
            AuditLogStore.record(op, "user_appoint", "user", username, "任命岗位");
            return R.ok(row);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 撤销子管，恢复为业务用户角色 */
    @PostMapping("/{username}/revoke")
    public R<Map<String, Object>> revoke(@PathVariable String username, HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        try {
            // 禁任命域：保护该岗最后一个账号，避免撤光后无法补岗
            boolean protectLast = !allowAppointFromUsers;
            var revoked = UserStore.revokeSubAdmin(username, userRole, protectLast);
            String op = AdminAuth.requireLogin(session);
            AuditLogStore.record(op, "user_revoke", "user", username, "撤销岗位");
            return R.ok(revoked.toMap());
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    /** 设/解除帖子禁言截止时间 */
    @PostMapping("/{username}/post-mute")
    public R<Map<String, Object>> postMute(
            @PathVariable String username,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        AdminAuth.requireSuperAdmin(session);
        if (!UserStore.postMuteEnabled()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "禁言功能暂不可用");
        }
        try {
            Map<String, Object> b = body == null ? Map.of() : body;
            String until = "";
            if (b.get("until") != null) {
                until = String.valueOf(b.get("until")).trim();
            }
            Object daysObj = b.get("days");
            Map<String, Object> row;
            if (daysObj != null && !String.valueOf(daysObj).isBlank()
                    && (until.isBlank() || "null".equalsIgnoreCase(until))) {
                int days = Integer.parseInt(String.valueOf(daysObj).trim());
                row = UserStore.setPostMuteDays(username, days);
            } else {
                row = UserStore.setPostMuteUntil(username, until);
            }
            String op = AdminAuth.requireLogin(session);
            String tip = row.get("postMuteUntil") == null || String.valueOf(row.get("postMuteUntil")).isBlank()
                    ? "解除禁言"
                    : "禁言至 " + row.get("postMuteUntil");
            AuditLogStore.record(op, "user_post_mute", "user", username, tip);
            return R.ok(row);
        } catch (NumberFormatException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "禁言天数无效");
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
