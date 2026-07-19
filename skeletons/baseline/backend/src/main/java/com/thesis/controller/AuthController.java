package com.thesis.controller;

import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.ProfileFields;
import com.thesis.service.UserStore;
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
        return R.ok(m);
    }

    @PostMapping("/login")
    public R<Map<String, Object>> login(@RequestBody Map<String, String> body, HttpSession session) {
        verifyCaptcha(body, session);
        String username = body.getOrDefault("username", "");
        String password = body.getOrDefault("password", "");
        if (username.isBlank() || password.isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "用户名或密码不能为空");
        }
        UserStore.Profile profile = UserStore.authenticate(username, password);
        if (profile == null) throw new BizException(ErrorCode.UNAUTHORIZED, "用户名或密码错误");

        session.setAttribute("uid", profile.username);
        session.setAttribute("role", profile.role);
        session.setAttribute("superAdmin", profile.superAdmin);
        session.removeAttribute("captcha");
        Map<String, Object> m = new HashMap<>(profile.toMap());
        m.put("token", session.getId());
        return R.ok(m);
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
        try {
            Map<String, String> extras = extractExtras(body);
            UserStore.Profile profile = UserStore.register(
                    username, password, nickname, registerRole, phone, extras);
            session.removeAttribute("captcha");
            Map<String, Object> m = new HashMap<>(profile.toMap());
            m.put("needLogin", true);
            return R.ok(m);
        } catch (IllegalArgumentException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/me")
    public R<Map<String, Object>> me(HttpSession session) {
        Object uid = session.getAttribute("uid");
        if (uid == null) throw new BizException(ErrorCode.UNAUTHORIZED, "未登录");
        UserStore.Profile p = UserStore.get(uid.toString());
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
            throw new BizException(ErrorCode.CAPTCHA_INVALID, "验证码错误");
        }
    }

    private static void verifyCaptchaObj(Map<String, Object> body, HttpSession session) {
        String captcha = str(body.get("captcha"));
        Object expect = session.getAttribute("captcha");
        session.removeAttribute("captcha");
        if (expect == null || !expect.toString().equalsIgnoreCase(captcha)) {
            throw new BizException(ErrorCode.CAPTCHA_INVALID, "验证码错误");
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }
}
