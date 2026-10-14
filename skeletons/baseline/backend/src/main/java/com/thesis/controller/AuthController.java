package com.thesis.controller;

import com.thesis.capability.AuditLogStore;
import com.thesis.capability.LoyaltyStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.config.AppPolicy;
import com.thesis.service.AuthSessionStore;
import com.thesis.service.InviteCodeStore;
import com.thesis.service.LoginLogStore;
import com.thesis.service.MessageStore;
import com.thesis.service.ProfileFields;
import com.thesis.service.UserStore;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.util.*;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    @Value("${thesis.register-role:user}")
    private String registerRole;

    /** 本机调试可回显验证码明文；默认关闭。 */
    @Value("${thesis.local-dev.captcha-plain:false}")
    private boolean captchaPlain;

    @Value("${thesis.shop-marketplace:false}")
    private boolean shopMarketplace;

    /** 去掉 0/O、1/I/L 等易混字符 */
    private static final char[] CAPTCHA_CHARS = "23456789ABCDEFGHJKMNPQRSTUVWXYZ".toCharArray();

    @GetMapping("/captcha")
    public R<Map<String, String>> captcha(HttpSession session) throws Exception {
        Random rnd = new Random();
        StringBuilder sb = new StringBuilder(4);
        for (int i = 0; i < 4; i++) {
            sb.append(CAPTCHA_CHARS[rnd.nextInt(CAPTCHA_CHARS.length)]);
        }
        String code = sb.toString();
        session.setAttribute("captcha", code);
        BufferedImage img = new BufferedImage(100, 36, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = img.createGraphics();
        g.setColor(new Color(245, 247, 250));
        g.fillRect(0, 0, 100, 36);
        for (int i = 0; i < 3; i++) {
            g.setColor(new Color(180 + rnd.nextInt(50), 190 + rnd.nextInt(40), 200 + rnd.nextInt(40)));
            g.drawLine(rnd.nextInt(100), rnd.nextInt(36), rnd.nextInt(100), rnd.nextInt(36));
        }
        g.setFont(new Font("Arial", Font.BOLD, 20));
        for (int i = 0; i < code.length(); i++) {
            g.setColor(new Color(11 + rnd.nextInt(40), 90 + rnd.nextInt(40), 100 + rnd.nextInt(40)));
            g.drawString(String.valueOf(code.charAt(i)), 14 + i * 20, 22 + rnd.nextInt(8));
        }
        g.dispose();
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ImageIO.write(img, "png", baos);
        String b64 = Base64.getEncoder().encodeToString(baos.toByteArray());
        Map<String, String> m = new HashMap<>();
        m.put("image", "data:image/png;base64," + b64);
        if (captchaPlain) {
            m.put("code", code);
        }
        return R.ok(m);
    }

    @PostMapping("/login")
    public R<Map<String, Object>> login(
            @RequestBody Map<String, String> body, HttpSession session, HttpServletRequest request) {
        verifyCaptcha(body, session);
        String username = body.getOrDefault("username", "");
        String password = body.getOrDefault("password", "");
        if (username.isBlank() || password.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "用户名或密码不能为空");
        }
        String un = username.trim();
        UserStore.Profile raw = UserStore.get(un);
        if (raw != null) {
            int locked = UserStore.lockRemainMinutes(raw);
            if (locked > 0) {
                throw new BizException(
                        ErrorCode.ACCOUNT_LOCKED,
                        "尝试次数过多，请 " + locked + " 分钟后再登录");
            }
        }
        if (raw != null && UserStore.passwordMatches(raw, password) && !raw.enabled) {
            throw new BizException(ErrorCode.ACCOUNT_DISABLED, AdminAuth.DISABLED_MSG);
        }
        UserStore.Profile profile = UserStore.authenticate(un, password);
        if (profile == null) {
            if (raw != null) {
                UserStore.recordFailedLogin(un);
                UserStore.Profile again = UserStore.get(un);
                int locked = UserStore.lockRemainMinutes(again);
                if (locked > 0) {
                    throw new BizException(
                            ErrorCode.ACCOUNT_LOCKED,
                            "尝试次数过多，请 " + locked + " 分钟后再登录");
                }
            }
            throw new BizException(ErrorCode.UNAUTHORIZED, "用户名或密码错误");
        }
        assertLoginAs(body.getOrDefault("loginAs", ""), profile);

        boolean remember = isTruthy(body.get("remember"));
        int idleSec = Math.max(60, AppPolicy.AUTH_SESSION_IDLE_MINUTES * 60);
        int rememberSec = Math.max(idleSec, AppPolicy.AUTH_REMEMBER_DAYS * 24 * 3600);
        session.setMaxInactiveInterval(remember ? rememberSec : idleSec);

        session.setAttribute("uid", profile.username);
        session.setAttribute("role", profile.role);
        session.setAttribute("superAdmin", profile.superAdmin);
        session.setAttribute("staffPost", profile.staffPost == null ? "" : profile.staffPost);
        session.setAttribute("staffKind", profile.staffKind == null ? "" : profile.staffKind);
        session.removeAttribute("captcha");
        session.removeAttribute("captchaFails");

        String ip = AuthSessionController.clientIp(request);
        String ua = request.getHeader("User-Agent");
        String prevGeo = LoginLogStore.lastSuccessGeo(profile.username);
        String geo = LoginLogStore.geoHint(ip);
        LoginLogStore.record(profile.username, ip, ua, true);
        AuthSessionStore.register(session.getId(), profile.username, ip, ua);
        if (!prevGeo.isBlank() && !prevGeo.equals(geo)) {
            try {
                MessageStore.send(
                        profile.username,
                        "异地登录提醒",
                        "检测到与上次不同的登录来源（" + geo + "），请确认是否本人操作。",
                        "auth_remote",
                        null);
            } catch (Exception ignored) {
            }
        }

        AuditLogStore.record(profile.username, "login", "session", "", "登录成功");
        try {
            LoyaltyStore.checkInOnLogin(profile.username);
            LoyaltyStore.sweepExpire(profile.username);
        } catch (Exception ignored) {
        }
        Map<String, Object> m = new HashMap<>(profile.toMap());
        m.put("token", session.getId());
        m.put("mustChangePassword", UserStore.effectiveMustChange(profile));
        m.put("mustActivateEmail", UserStore.effectiveMustActivate(profile));
        m.put("remember", remember);
        return R.ok(m);
    }

    @PostMapping("/logout")
    public R<Void> logout(HttpSession session) {
        try {
            AuthSessionStore.invalidate(session.getId());
        } catch (Exception ignored) {
        }
        try {
            session.invalidate();
        } catch (IllegalStateException ignored) {
        }
        return R.ok();
    }

    @GetMapping("/public-config")
    public R<Map<String, Object>> publicConfig() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("lockMaxAttempts", AppPolicy.AUTH_LOCK_MAX_ATTEMPTS);
        m.put("lockMinutes", AppPolicy.AUTH_LOCK_MINUTES);
        m.put("passwordMaxDays", AppPolicy.AUTH_PASSWORD_MAX_DAYS);
        m.put("rememberDays", AppPolicy.AUTH_REMEMBER_DAYS);
        m.put("passwordMinLength", AppPolicy.AUTH_PASSWORD_MIN_LENGTH);
        m.put("sessionIdleMinutes", AppPolicy.AUTH_SESSION_IDLE_MINUTES);
        m.put("maxSessions", AppPolicy.AUTH_MAX_SESSIONS);
        m.put("requireInvite", AppPolicy.AUTH_REQUIRE_INVITE);
        m.put("requireEmailActivate", AppPolicy.AUTH_REQUIRE_EMAIL_ACTIVATE);
        m.put("agreementPath", "/agreement");
        m.put("privacyPath", "/privacy");
        return R.ok(m);
    }

    @PostMapping("/activate")
    public R<Map<String, Object>> activate(@RequestBody Map<String, Object> body) {
        String username = str(body.get("username"));
        String code = str(body.get("activationCode"));
        if (code.isBlank()) code = str(body.get("code"));
        try {
            UserStore.activateByCode(username, code);
            Map<String, Object> m = new HashMap<>();
            m.put("needLogin", true);
            return R.ok(m);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/security-question")
    public R<Map<String, String>> securityQuestion(@RequestParam(value = "username", defaultValue = "") String username) {
        String q = UserStore.publicSecurityQuestion(username);
        Map<String, String> m = new HashMap<>();
        m.put("question", q == null ? "" : q);
        m.put("hint", "若账号已设置密保，将显示问题");
        return R.ok(m);
    }

    @PostMapping("/reset-by-security")
    public R<Map<String, Object>> resetBySecurity(@RequestBody Map<String, Object> body, HttpSession session) {
        verifyCaptchaObj(body, session);
        String username = str(body.get("username"));
        String answer = str(body.get("securityAnswer"));
        if (answer.isBlank()) answer = str(body.get("answer"));
        String newPassword = str(body.get("newPassword"));
        if (newPassword.isBlank()) newPassword = str(body.get("password"));
        String confirm = str(body.get("confirmPassword"));
        if (!confirm.isBlank() && !newPassword.equals(confirm)) {
            throw new BizException(ErrorCode.BAD_REQUEST, "两次密码不一致");
        }
        try {
            UserStore.resetPasswordBySecurity(username, answer, newPassword);
            session.removeAttribute("captcha");
            Map<String, Object> m = new HashMap<>();
            m.put("needLogin", true);
            return R.ok(m);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/force-change-password")
    public R<Map<String, Object>> forceChangePassword(@RequestBody Map<String, Object> body, HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        String newPassword = str(body.get("newPassword"));
        if (newPassword.isBlank()) newPassword = str(body.get("password"));
        String confirm = str(body.get("confirmPassword"));
        if (!newPassword.equals(confirm)) {
            throw new BizException(ErrorCode.BAD_REQUEST, "两次密码不一致");
        }
        try {
            UserStore.forceChangePassword(uid, newPassword);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
        try {
            AuthSessionStore.invalidate(session.getId());
        } catch (Exception ignored) {
        }
        try {
            session.invalidate();
        } catch (IllegalStateException ignored) {
        }
        Map<String, Object> m = new HashMap<>();
        m.put("requireRelogin", true);
        return R.ok(m);
    }

    /**
     * 登录身份校验：门户 / 总管 / 子管理(clerk) / 业务员工(worker) / 具体岗位 id。
     * 空 loginAs 表示不校验（统一登录模式）。
     */
    private static void assertLoginAs(String loginAs, UserStore.Profile profile) {
        if (loginAs == null || loginAs.isBlank()) return;
        String as = loginAs.trim().toLowerCase(Locale.ROOT);
        boolean isAdmin = "admin".equalsIgnoreCase(profile.role);
        String kind = profile.staffKind == null ? "" : profile.staffKind.trim().toLowerCase(Locale.ROOT);
        String post = profile.staffPost == null ? "" : profile.staffPost.trim().toLowerCase(Locale.ROOT);
        boolean isClerk = isAdmin && !profile.superAdmin && (kind.isBlank() || "clerk".equals(kind));
        boolean isWorker = isAdmin && !profile.superAdmin && "worker".equals(kind);
        boolean ok;
        switch (as) {
            case "user", "portal", "reader", "student", "patient" -> ok = !isAdmin;
            case "admin", "super" -> ok = isAdmin && profile.superAdmin;
            case "subadmin", "sub", "clerk" -> ok = isClerk;
            case "staff", "worker" -> ok = isWorker;
            default -> {
                // 具体岗位 id：须与账号 staff_post 一致
                if (!isAdmin || profile.superAdmin) {
                    ok = false;
                } else if (!post.isBlank()) {
                    ok = post.equals(as);
                } else if (isWorker) {
                    // 作业岗必须有 staff_post
                    ok = false;
                } else {
                    // 旧种子无 staff_post 的子管：前端已改发岗位 id，允许 clerk 通过
                    ok = isClerk;
                }
            }
        }
        if (!ok) {
            throw new BizException(ErrorCode.UNAUTHORIZED, "所选身份与账号不符");
        }
    }

    /** 开放注册：账号 + 领域资料字段 */
    @PostMapping("/register")
    public R<Map<String, Object>> register(@RequestBody Map<String, Object> body, HttpSession session) {
        verifyCaptchaObj(body, session);
        String username = str(body.get("username"));
        String password = str(body.get("password"));
        String confirm = str(body.get("confirmPassword"));
        String nickname = str(body.get("nickname"));
        String phone = str(body.get("phone"));
        if (!password.equals(confirm)) {
            throw new BizException(ErrorCode.BAD_REQUEST, "两次密码不一致");
        }
        if (!isTruthy(str(body.get("agreeTerms"))) && !isTruthy(str(body.get("agree")))) {
            throw new BizException(ErrorCode.BAD_REQUEST, "请先阅读并同意用户协议与隐私政策");
        }
        try {
            if (AppPolicy.AUTH_REQUIRE_INVITE > 0) {
                InviteCodeStore.consumeOrThrow(str(body.get("inviteCode")));
            }
            Map<String, String> extras = extractExtras(body);
            String accountType = str(body.get("accountType"));
            if (accountType.isBlank()) accountType = str(body.get("registerAs"));
            boolean asMerchant = "merchant".equalsIgnoreCase(accountType);
            UserStore.Profile profile;
            if (asMerchant) {
                if (!shopMarketplace) {
                    throw new BizException(ErrorCode.BAD_REQUEST, "当前不支持商家注册");
                }
                profile = UserStore.registerMerchant(username, password, nickname, phone, extras);
            } else {
                profile = UserStore.register(
                        username, password, nickname, registerRole, phone, extras);
            }
            String sq = str(body.get("securityQuestion"));
            String sa = str(body.get("securityAnswer"));
            if (!sq.isBlank() && !sa.isBlank()) {
                UserStore.setSecurityQuestion(profile.username, sq, sa);
                profile = UserStore.get(profile.username);
            }
            String activationCode = "";
            if (AppPolicy.AUTH_REQUIRE_EMAIL_ACTIVATE > 0) {
                activationCode = UserStore.issueActivationCode(profile.username);
                try {
                    MessageStore.send(
                            profile.username,
                            "账号激活码",
                            "您的站内激活码是：" + activationCode + "，请在激活页填写。",
                            "auth_activate",
                            null);
                } catch (Exception ignored) {
                }
                profile = UserStore.get(profile.username);
            }
            session.removeAttribute("captcha");
            session.removeAttribute("captchaFails");
            Map<String, Object> m = new HashMap<>(profile.toMap());
            m.put("needLogin", true);
            m.put("mustActivateEmail", UserStore.effectiveMustActivate(profile));
            if (!activationCode.isBlank()) m.put("activationCode", activationCode);
            if (asMerchant) m.put("pendingReview", true);
            return R.ok(m);
        } catch (BizException e) {
            throw e;
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/me")
    public R<Map<String, Object>> me(HttpSession session) {
        String uid = AdminAuth.requireLogin(session);
        UserStore.Profile p = UserStore.get(uid);
        if (p == null) throw new BizException(ErrorCode.UNAUTHORIZED, "用户不存在");
        return R.ok(p.toMap());
    }

    @SuppressWarnings("unchecked")
    static Map<String, String> extractExtras(Map<String, Object> body) {
        Object raw = body.get("extras");
        if (raw instanceof Map<?, ?> map) {
            Map<String, Object> m = new LinkedHashMap<>();
            for (Map.Entry<?, ?> e : map.entrySet()) {
                if (e.getKey() != null) m.put(String.valueOf(e.getKey()), e.getValue());
            }
            return ProfileFields.filterExtras(m);
        }
        // 也允许扁平提交领域字段
        return ProfileFields.filterExtras(body);
    }

    private static void verifyCaptcha(Map<String, String> body, HttpSession session) {
        String captcha = body.getOrDefault("captcha", "");
        Object expect = session.getAttribute("captcha");
        session.removeAttribute("captcha");
        if (expect == null || !expect.toString().equalsIgnoreCase(captcha)) {
            bumpCaptchaFails(session);
            throw new BizException(ErrorCode.CAPTCHA_INVALID, captchaFailMessage(session));
        }
        session.removeAttribute("captchaFails");
    }

    private static void verifyCaptchaObj(Map<String, Object> body, HttpSession session) {
        String captcha = str(body.get("captcha"));
        Object expect = session.getAttribute("captcha");
        session.removeAttribute("captcha");
        if (expect == null || !expect.toString().equalsIgnoreCase(captcha)) {
            bumpCaptchaFails(session);
            throw new BizException(ErrorCode.CAPTCHA_INVALID, captchaFailMessage(session));
        }
        session.removeAttribute("captchaFails");
    }

    /** Profile 改绑等复用图形验证码校验。 */
    public static void verifyCaptchaForProfile(Map<String, Object> body, HttpSession session) {
        verifyCaptchaObj(body, session);
    }

    private static void bumpCaptchaFails(HttpSession session) {
        int n = 0;
        Object raw = session.getAttribute("captchaFails");
        if (raw instanceof Number num) n = num.intValue();
        else if (raw != null) {
            try {
                n = Integer.parseInt(String.valueOf(raw));
            } catch (NumberFormatException ignored) {
            }
        }
        session.setAttribute("captchaFails", n + 1);
    }

    private static String captchaFailMessage(HttpSession session) {
        int n = 0;
        Object raw = session.getAttribute("captchaFails");
        if (raw instanceof Number num) n = num.intValue();
        if (n >= 2) return "验证码多次错误，请看清后重试";
        return "验证码错误";
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static boolean isTruthy(String raw) {
        if (raw == null) return false;
        String s = raw.trim();
        return "1".equals(s) || "true".equalsIgnoreCase(s) || "yes".equalsIgnoreCase(s) || "on".equalsIgnoreCase(s);
    }
}
