package com.thesis.controller;

import com.thesis.capability.AddressStore;
import com.thesis.capability.OrderStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
public class OrderController {

    private static void requireOrder() {
        if (!OrderStore.enabled()) throw new BizException(ErrorCode.BAD_REQUEST, "订单功能暂不可用");
    }

    @GetMapping("/api/cart")
    public R<?> cart(HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(OrderStore.listCart(uid));
    }

    /* @@CART_MUTATE_BEGIN */
    @PostMapping("/api/cart")
    public R<?> upsertCart(@RequestBody Map<String, Object> body, HttpSession session) {
        return doUpsertCart(toLong(body.get("itemId")), qtyOf(body), session);
    }

    @PostMapping("/api/cart/remove")
    public R<Void> removeCart(@RequestBody Map<String, Object> body, HttpSession session) {
        return doRemoveCart(toLong(body.get("itemId")), session);
    }

    private R<?> doUpsertCart(long itemId, int qty, HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(OrderStore.upsertCart(uid, itemId, qty));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private R<Void> doRemoveCart(long itemId, HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        OrderStore.removeCart(uid, itemId);
        return R.ok(null);
    }

    private static int qtyOf(Map<String, Object> body) {
        if (body == null || body.get("qty") == null) return 1;
        try {
            return Integer.parseInt(String.valueOf(body.get("qty")));
        } catch (NumberFormatException e) {
            return 1;
        }
    }
    /* @@CART_MUTATE_END */

    @GetMapping("/api/addresses")
    public R<?> addresses(HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(AddressStore.list(uid));
    }

    @PostMapping("/api/addresses")
    public R<?> createAddress(@RequestBody Map<String, Object> body, HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(AddressStore.create(
                    uid,
                    str(body.get("contactName")),
                    str(body.get("phone")),
                    str(body.get("addressLine")),
                    str(body.get("tag")),
                    bool(body.get("isDefault"), false)));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @PutMapping("/api/addresses/{id}")
    public R<?> updateAddress(@PathVariable long id, @RequestBody Map<String, Object> body, HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        try {
            Boolean asDefault = body.containsKey("isDefault") ? bool(body.get("isDefault"), false) : null;
            return R.ok(AddressStore.update(
                    id,
                    uid,
                    body.containsKey("contactName") ? str(body.get("contactName")) : null,
                    body.containsKey("phone") ? str(body.get("phone")) : null,
                    body.containsKey("addressLine") ? str(body.get("addressLine")) : null,
                    body.containsKey("tag") ? str(body.get("tag")) : null,
                    asDefault));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @DeleteMapping("/api/addresses/{id}")
    public R<Void> deleteAddress(@PathVariable long id, HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        if (!AddressStore.delete(id, uid)) {
            throw new BizException(ErrorCode.NOT_FOUND, "地址不存在");
        }
        return R.ok(null);
    }

    @PostMapping("/api/orders")
    public R<?> place(@RequestBody(required = false) Map<String, Object> body, HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        Map<String, Object> b = body == null ? Map.of() : body;
        String remark = str(b.get("remark"));
        Long addressId = b.get("addressId") == null || str(b.get("addressId")).isBlank()
                ? null
                : toLong(b.get("addressId"));
        try {
            return R.ok(OrderStore.placeOrder(
                    uid,
                    remark,
                    addressId,
                    str(b.get("receiverName")),
                    str(b.get("receiverPhone")),
                    str(b.get("addressLine")),
                    str(b.get("deliveryType")),
                    str(b.get("tasteNote")),
                    str(b.get("couponCode"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/api/orders/{id}/trace")
    public R<?> trace(@PathVariable long id, HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        Map<String, Object> m = OrderStore.getOrder(id);
        if (m == null) throw new BizException(ErrorCode.NOT_FOUND, "订单不存在");
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        if (!admin && !uid.equals(String.valueOf(m.get("username")))) {
            throw new BizException(ErrorCode.FORBIDDEN, "无权查看");
        }
        return R.ok(OrderStore.logisticsTrace(id));
    }

    @PostMapping("/api/orders/{id}/refund")
    public R<?> refund(@PathVariable long id, @RequestBody(required = false) Map<String, Object> body, HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        Map<String, Object> b = body == null ? Map.of() : body;
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        try {
            if (admin && b.containsKey("pass")) {
                boolean pass = bool(b.get("pass"), true);
                return R.ok(OrderStore.decideRefund(id, pass, str(b.get("note"))));
            }
            return R.ok(OrderStore.requestRefund(id, uid, str(b.get("reason"))));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    @GetMapping("/api/orders")
    public R<?> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String status,
            HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        return R.ok(OrderStore.pageOrders(admin ? null : uid, status, page, size));
    }

    @GetMapping("/api/orders/{id}")
    public R<?> detail(@PathVariable long id, HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        Map<String, Object> m = OrderStore.getOrder(id);
        if (m == null) throw new BizException(ErrorCode.NOT_FOUND, "订单不存在");
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        if (!admin && !uid.equals(String.valueOf(m.get("username")))) {
            throw new BizException(ErrorCode.FORBIDDEN, "无权查看");
        }
        return R.ok(m);
    }

    @PostMapping("/api/orders/{id}/{action}")
    public R<?> advance(
            @PathVariable long id,
            @PathVariable String action,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        boolean admin = "admin".equals(String.valueOf(session.getAttribute("role")));
        Map<String, Object> m = OrderStore.getOrder(id);
        if (m == null) throw new BizException(ErrorCode.NOT_FOUND, "订单不存在");
        if ("cancel".equalsIgnoreCase(action)) {
            if (!admin && !uid.equals(String.valueOf(m.get("username")))) {
                throw new BizException(ErrorCode.FORBIDDEN, "无权取消");
            }
        } else {
            AdminAuth.requireAdmin(session);
        }
        try {
            return R.ok(OrderStore.advance(id, action, body));
        } catch (IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private static long toLong(Object o) {
        if (o == null) return 0;
        return Long.parseLong(String.valueOf(o));
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static boolean bool(Object o, boolean def) {
        if (o == null) return def;
        if (o instanceof Boolean b) return b;
        String s = String.valueOf(o).trim();
        return "1".equals(s) || "true".equalsIgnoreCase(s) || "yes".equalsIgnoreCase(s);
    }
}
