package com.thesis.controller;

import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import com.thesis.service.TimebankStore;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/timebank")
public class TimebankController {

    private static void requireTb() {
        if (!TimebankStore.ready()) {
            throw new BizException(ErrorCode.NOT_FOUND, "未开通时间银行功能");
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    @GetMapping("/account")
    public R<Map<String, Object>> account(HttpSession session) {
        requireTb();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(TimebankStore.getAccount(uid));
    }

    @GetMapping("/ledger/mine")
    public R<Map<String, Object>> ledgerMine(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireTb();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(TimebankStore.pageLedgerMine(uid, page, size));
    }

    @GetMapping("/services")
    public R<List<Map<String, Object>>> services(HttpSession session) {
        requireTb();
        AdminAuth.requireLogin(session);
        return R.ok(TimebankStore.listOpenServices());
    }

    /** 用户自助存入（选服务事项 + 小时数，演示即时入账）。 */
    @PostMapping("/earn")
    public R<Map<String, Object>> earn(@RequestBody Map<String, Object> body, HttpSession session) {
        requireTb();
        String uid = AdminAuth.requireLogin(session);
        try {
            boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
            return R.ok(TimebankStore.creditFromBody(uid, body == null ? Map.of() : body, admin));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/admin/accounts")
    public R<Map<String, Object>> adminAccounts(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            HttpSession session) {
        requireTb();
        AdminAuth.requireAdmin(session);
        return R.ok(TimebankStore.pageAccounts(page, size));
    }

    @GetMapping("/admin/ledger")
    public R<Map<String, Object>> adminLedger(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String username,
            HttpSession session) {
        requireTb();
        AdminAuth.requireAdmin(session);
        return R.ok(TimebankStore.pageLedgerAdmin(page, size, username));
    }

    @PostMapping("/admin/earn")
    public R<Map<String, Object>> adminEarn(@RequestBody Map<String, Object> body, HttpSession session) {
        requireTb();
        AdminAuth.requireAdmin(session);
        try {
            String uid = AdminAuth.requireLogin(session);
            return R.ok(TimebankStore.creditFromBody(uid, body == null ? Map.of() : body, true));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    // —— I-06 ——

    @GetMapping("/rank")
    public R<List<Map<String, Object>>> rank(
            @RequestParam(defaultValue = "20") int limit, HttpSession session) {
        requireTb();
        AdminAuth.requireLogin(session);
        return R.ok(TimebankStore.rankByHours(limit));
    }

    @GetMapping("/admin/ledger/export")
    public void exportLedger(
            @RequestParam(required = false) String username,
            HttpSession session,
            HttpServletResponse response) {
        requireTb();
        AdminAuth.requireAdmin(session);
        try {
            String csv = TimebankStore.exportLedgerCsv(username);
            response.setCharacterEncoding(StandardCharsets.UTF_8.name());
            response.setContentType("text/csv;charset=UTF-8");
            response.setHeader("Content-Disposition", "attachment; filename=tb_ledger.csv");
            response.getOutputStream().write(new byte[] {(byte) 0xEF, (byte) 0xBB, (byte) 0xBF});
            response.getOutputStream().write(csv.getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/skills")
    public R<Map<String, Object>> updateMySkills(
            @RequestBody Map<String, Object> body, HttpSession session) {
        requireTb();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(TimebankStore.updateSkills(
                    uid, str(body == null ? null : body.get("skillTags")), null, false));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/admin/skills")
    public R<Map<String, Object>> adminSkills(
            @RequestBody Map<String, Object> body, HttpSession session) {
        requireTb();
        AdminAuth.requireAdmin(session);
        try {
            String user = str(body == null ? null : body.get("username"));
            String tags = body != null && body.containsKey("skillTags")
                    ? str(body.get("skillTags")) : null;
            Boolean cert = null;
            if (body != null && body.containsKey("skillCertified")) {
                Object c = body.get("skillCertified");
                cert = Boolean.TRUE.equals(c)
                        || "1".equals(String.valueOf(c))
                        || "true".equalsIgnoreCase(String.valueOf(c));
            }
            return R.ok(TimebankStore.updateSkills(user, tags, cert, true));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/admin/freeze")
    public R<Map<String, Object>> freeze(
            @RequestBody Map<String, Object> body, HttpSession session) {
        requireTb();
        AdminAuth.requireAdmin(session);
        try {
            String user = str(body.get("username"));
            BigDecimal h = new BigDecimal(str(body.get("hours")));
            boolean freeze = !"unfreeze".equalsIgnoreCase(str(body.get("action")));
            return R.ok(TimebankStore.adjustFreeze(user, h, freeze));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (Exception e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "参数无效");
        }
    }

    @PostMapping("/transfer")
    public R<Map<String, Object>> transfer(
            @RequestBody Map<String, Object> body, HttpSession session) {
        requireTb();
        String uid = AdminAuth.requireLogin(session);
        try {
            BigDecimal h = new BigDecimal(str(body.get("hours")));
            return R.ok(TimebankStore.transfer(
                    uid, str(body.get("toUsername")), h, str(body.get("reason"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (Exception e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "参数无效");
        }
    }

    @GetMapping("/catalog")
    public R<List<Map<String, Object>>> catalog(HttpSession session) {
        requireTb();
        AdminAuth.requireLogin(session);
        return R.ok(TimebankStore.listCatalog(true));
    }

    @GetMapping("/admin/catalog")
    public R<List<Map<String, Object>>> adminCatalog(HttpSession session) {
        requireTb();
        AdminAuth.requireAdmin(session);
        return R.ok(TimebankStore.listCatalog(false));
    }

    @PostMapping("/admin/catalog")
    public R<Map<String, Object>> saveCatalog(
            @RequestBody Map<String, Object> body, HttpSession session) {
        requireTb();
        AdminAuth.requireAdmin(session);
        try {
            Long id = null;
            String idRaw = str(body.get("id"));
            if (!idRaw.isBlank()) id = Long.parseLong(idRaw);
            BigDecimal cost = new BigDecimal(str(body.get("costHours")).isBlank()
                    ? "1" : str(body.get("costHours")));
            int stock = 0;
            try {
                stock = Integer.parseInt(str(body.get("stock")));
            } catch (Exception ignored) {
            }
            boolean enabled = true;
            Object en = body.get("enabled");
            if (en != null) {
                enabled = Boolean.TRUE.equals(en)
                        || "1".equals(String.valueOf(en))
                        || "true".equalsIgnoreCase(String.valueOf(en));
            }
            return R.ok(TimebankStore.saveCatalog(
                    id, str(body.get("title")), cost, stock, enabled, str(body.get("remark"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        } catch (Exception e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "参数无效");
        }
    }

    @PostMapping("/catalog/{id}/redeem")
    public R<Map<String, Object>> redeemCatalog(@PathVariable long id, HttpSession session) {
        requireTb();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(TimebankStore.redeemCatalog(uid, id));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PostMapping("/appeal")
    public R<Map<String, Object>> appeal(
            @RequestBody Map<String, Object> body, HttpSession session) {
        requireTb();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(TimebankStore.submitAppeal(uid, str(body.get("reason"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/appeal/mine")
    public R<Map<String, Object>> appealMine(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {
        requireTb();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(TimebankStore.pageAppeals(page, size, uid));
    }

    @GetMapping("/admin/appeals")
    public R<Map<String, Object>> adminAppeals(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String username,
            HttpSession session) {
        requireTb();
        AdminAuth.requireAdmin(session);
        return R.ok(TimebankStore.pageAppeals(page, size, username));
    }

    @PostMapping("/admin/appeals/{id}/resolve")
    public R<Map<String, Object>> resolveAppeal(
            @PathVariable long id,
            @RequestBody Map<String, Object> body,
            HttpSession session) {
        requireTb();
        AdminAuth.requireAdmin(session);
        try {
            boolean pass = Boolean.TRUE.equals(body.get("pass"))
                    || "true".equalsIgnoreCase(str(body.get("pass")))
                    || "1".equals(str(body.get("pass")));
            return R.ok(TimebankStore.resolveAppeal(id, pass, str(body.get("adminRemark"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/clear-rule")
    public R<Map<String, Object>> clearRule(HttpSession session) {
        requireTb();
        AdminAuth.requireLogin(session);
        return R.ok(Map.of("body", TimebankStore.getClearRule()));
    }

    @PostMapping("/admin/clear-rule")
    public R<Map<String, Object>> saveClearRule(
            @RequestBody Map<String, Object> body, HttpSession session) {
        requireTb();
        AdminAuth.requireAdmin(session);
        try {
            String text = TimebankStore.saveClearRule(str(body.get("body")));
            return R.ok(Map.of("body", text));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }
}
