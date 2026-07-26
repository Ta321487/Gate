package com.thesis.capability;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.OrderMapper;
import com.thesis.mapper.SchemaMapper;
import com.thesis.service.MessageStore;
import com.thesis.service.UserStore;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 能力 order_lines：购物车 + 多明细订单（无真支付）。
 */
public final class OrderStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private static String CART = "";
    private static String ORDER = "";
    private static String LINE = "";
    private static boolean enabled = false;
    private static boolean useQuota = true;

    private OrderStore() {}

    private static OrderMapper mapper() {
        return MybatisSupport.mapper(OrderMapper.class);
    }

    private static SchemaMapper schema() {
        return MybatisSupport.mapper(SchemaMapper.class);
    }

    public static void bind(String cartTable, String orderTable, String lineTable, boolean quota) {
        CART = cartTable == null ? "" : cartTable.trim();
        ORDER = orderTable == null ? "" : orderTable.trim();
        LINE = lineTable == null ? "" : lineTable.trim();
        enabled = !CART.isBlank() && !ORDER.isBlank() && !LINE.isBlank();
        useQuota = quota;
        AddressStore.resetCache();
    }

    public static void unbind() {
        enabled = false;
        CART = ORDER = LINE = "";
    }

    public static boolean enabled() {
        return enabled;
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o).trim();
        return s.isBlank() || "null".equals(s) ? null : s;
    }

    private static double priceOf(Map<String, Object> item) {
        return unitPriceOf(item);
    }

    /** 档案单价：逻辑键 author（物理列常为 price_yuan）。 */
    public static double unitPriceOf(Map<String, Object> item) {
        if (item == null) return 0;
        Object raw = item.get("author");
        if (raw == null) raw = item.get("priceYuan");
        if (raw == null) return 0;
        try {
            return Double.parseDouble(String.valueOf(raw).replace("¥", "").replace("￥", "").trim());
        } catch (Exception e) {
            return 0;
        }
    }

    public static List<Map<String, Object>> listCart(String username) {
        requireEnabled();
        List<Map<String, Object>> raw = mapper().selectCart(CART, username);
        List<Map<String, Object>> out = new ArrayList<>();
        if (raw != null) {
            for (Map<String, Object> r : raw) {
                out.add(enrichCartRow(
                        num(r.get("id")),
                        num(first(r, "itemId", "item_id")),
                        toInt(r.get("qty"))));
            }
        }
        return out;
    }

    private static Map<String, Object> enrichCartRow(long id, long itemId, int qty) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("itemId", itemId);
        m.put("qty", qty);
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item != null) {
            m.put("title", item.get("title"));
            m.put("priceYuan", priceOf(item));
            m.put("stock", item.get("stock"));
            m.put("coverUrl", item.get("coverUrl"));
            m.put("categoryName", item.get("categoryName"));
        } else {
            m.put("title", "");
            m.put("priceYuan", 0);
            m.put("stock", 0);
        }
        double price = ((Number) m.get("priceYuan")).doubleValue();
        m.put("lineYuan", round2(price * qty));
        return m;
    }

    public static Map<String, Object> upsertCart(String username, long itemId, int qty) {
        requireEnabled();
        if (qty <= 0) {
            removeCart(username, itemId);
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("removed", true);
            return out;
        }
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalArgumentException("商品不存在");
        if (mapper().countCartItem(CART, username, itemId) > 0) {
            mapper().updateCartQty(CART, username, itemId, qty);
        } else {
            mapper().insertCart(CART, username, itemId, qty);
        }
        Map<String, Object> row = mapper().selectCartItem(CART, username, itemId);
        if (row == null) return Map.of();
        return enrichCartRow(num(row.get("id")), num(first(row, "itemId", "item_id")), toInt(row.get("qty")));
    }

    public static boolean removeCart(String username, long itemId) {
        requireEnabled();
        return mapper().deleteCartItem(CART, username, itemId) > 0;
    }

    public static void clearCart(String username) {
        requireEnabled();
        mapper().clearCart(CART, username);
    }

    public static Map<String, Object> placeOrder(String username, String remark) {
        return placeOrder(username, remark, null, null, null, null, null, null);
    }

    public static Map<String, Object> placeOrder(
            String username,
            String remark,
            Long addressId,
            String receiverName,
            String receiverPhone,
            String addressLine,
            String deliveryType,
            String tasteNote) {
        return placeOrder(
                username, remark, addressId, receiverName, receiverPhone, addressLine, deliveryType, tasteNote, null);
    }

    public static Map<String, Object> placeOrder(
            String username,
            String remark,
            Long addressId,
            String receiverName,
            String receiverPhone,
            String addressLine,
            String deliveryType,
            String tasteNote,
            String couponCode) {
        requireEnabled();
        if (LoyaltyStore.anyEnabled()) {
            ensureLoyaltyColumns();
        }
        if (hasOrderColumn("refund_status")) {
            ensureRefundColumns();
        }
        List<Map<String, Object>> cart = listCart(username);
        if (cart.isEmpty()) throw new IllegalStateException("购物车为空");
        double total = 0;
        for (Map<String, Object> line : cart) {
            int qty = ((Number) line.get("qty")).intValue();
            long itemId = ((Number) line.get("itemId")).longValue();
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            if (item == null) throw new IllegalStateException("商品不存在：" + line.get("title"));
            int stock = item.get("stock") instanceof Number n ? n.intValue() : 0;
            if (useQuota && stock < qty) {
                throw new IllegalStateException(ArchiveStore.stockShortageTitled(
                        String.valueOf(item.get("title")), stock));
            }
            total += priceOf(item) * qty;
        }
        double subtotal = round2(total);
        String coupon = couponCode == null ? "" : couponCode.trim();
        Map<String, Object> priceSnap = null;
        double payable = subtotal;
        if (LoyaltyStore.anyEnabled()) {
            priceSnap = LoyaltyStore.previewPrice(subtotal, username, coupon);
            payable = ((Number) priceSnap.get("payableYuan")).doubleValue();
            if (LoyaltyStore.isWalletEnabled() && !Boolean.TRUE.equals(priceSnap.get("balanceEnough"))) {
                throw new IllegalStateException(String.valueOf(priceSnap.getOrDefault(
                        "message",
                        "演示余额不足，请联系管理员充值")));
            }
            if (!coupon.isBlank() && LoyaltyStore.isCouponEnabled()
                    && priceSnap.get("couponCode") == null
                    && priceSnap.get("couponMessage") != null) {
                throw new IllegalStateException(String.valueOf(priceSnap.get("couponMessage")));
            }
        }
        String note = remark == null ? "" : remark.trim();
        String taste = tasteNote == null ? "" : tasteNote.trim();
        String dtype = deliveryType == null ? "" : deliveryType.trim();
        String rName = receiverName == null ? "" : receiverName.trim();
        String rPhone = receiverPhone == null ? "" : receiverPhone.trim();
        String addr = addressLine == null ? "" : addressLine.trim();
        if (addressId != null && addressId > 0 && AddressStore.available()) {
            Map<String, Object> a = AddressStore.get(addressId, username);
            if (a == null) throw new IllegalArgumentException("收货地址不存在");
            if (rName.isBlank()) rName = String.valueOf(a.getOrDefault("contactName", ""));
            if (rPhone.isBlank()) rPhone = String.valueOf(a.getOrDefault("phone", ""));
            if (addr.isBlank()) addr = String.valueOf(a.getOrDefault("addressLine", ""));
        }
        if (hasOrderColumn("receiver_name")) {
            boolean needAddr = dtype.isBlank() || dtype.contains("配送") || dtype.contains("快递")
                    || "配送到家".equals(dtype);
            if (needAddr && (rName.isBlank() || rPhone.isBlank() || addr.isBlank())) {
                throw new IllegalArgumentException("请选择或填写收货人、手机与地址");
            }
            if (!needAddr && rName.isBlank()) {
                rName = username;
            }
        }
        LinkedHashMap<String, Object> extraCols = new LinkedHashMap<>();
        if (hasOrderColumn("receiver_name")) extraCols.put("receiver_name", rName);
        if (hasOrderColumn("receiver_phone")) extraCols.put("receiver_phone", rPhone);
        if (hasOrderColumn("address_line")) extraCols.put("address_line", addr);
        if (hasOrderColumn("delivery_type")) extraCols.put("delivery_type", dtype);
        if (hasOrderColumn("taste_note")) extraCols.put("taste_note", taste);
        String noteOut = note;
        if (extraCols.isEmpty() && !taste.isBlank()) {
            noteOut = (noteOut.isBlank() ? "" : noteOut + "；") + "口味:" + taste;
        }
        if (extraCols.isEmpty() && !addr.isBlank()) {
            noteOut = (noteOut.isBlank() ? "" : noteOut + "；")
                    + "地址:" + rName + " " + rPhone + " " + addr;
        }
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        Map<String, Object> orderRow = new LinkedHashMap<>();
        orderRow.put("orderTable", ORDER);
        orderRow.put("username", username);
        orderRow.put("status", "pending");
        orderRow.put("totalYuan", BigDecimal.valueOf(payable).setScale(2, RoundingMode.HALF_UP));
        orderRow.put("remark", noteOut);
        orderRow.put("extraCols", extraCols);
        orderRow.put("createdAt", now);
        orderRow.put("updatedAt", now);
        mapper().insertOrder(orderRow);
        long orderId = orderRow.get("id") == null ? 0L : ((Number) orderRow.get("id")).longValue();
        List<long[]> deducted = new ArrayList<>();
        try {
            for (Map<String, Object> line : cart) {
                long itemId = ((Number) line.get("itemId")).longValue();
                int qty = ((Number) line.get("qty")).intValue();
                Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
                double price = priceOf(item);
                mapper().insertLine(LINE, orderId, itemId, String.valueOf(item.get("title")), price, qty);
                if (useQuota) {
                    ArchiveStore.adjustStock(itemId, -qty);
                    deducted.add(new long[] {itemId, qty});
                }
            }
            if (LoyaltyStore.anyEnabled()) {
                Map<String, Object> snap = LoyaltyStore.settleOnPlace(username, subtotal, orderId, coupon);
                applyLoyaltySnapshot(orderId, snap);
                if (!coupon.isBlank() && LoyaltyStore.isCouponEnabled()) {
                    try {
                        CouponStore.markUsed(username, coupon, orderId);
                    } catch (Exception ignored) {
                    }
                }
            }
        } catch (RuntimeException ex) {
            for (int i = deducted.size() - 1; i >= 0; i--) {
                long[] d = deducted.get(i);
                try {
                    ArchiveStore.adjustStock(d[0], (int) d[1]);
                } catch (Exception ignored) {
                }
            }
            try {
                if (LoyaltyStore.anyEnabled()) {
                    Map<String, Object> m = getOrder(orderId);
                    if (m != null) {
                        double paid = 0;
                        Object pb = m.get("payBalanceYuan");
                        if (pb instanceof Number n) paid = n.doubleValue();
                        if (paid > 0) {
                            LoyaltyStore.refundOrderPay(username, orderId, paid);
                        }
                    }
                }
            } catch (Exception ignored) {
            }
            try {
                mapper().deleteLines(LINE, orderId);
                mapper().deleteOrder(ORDER, orderId);
            } catch (Exception ignored) {
            }
            throw ex;
        }
        clearCart(username);
        try {
            MessageStore.notifyAdmins(
                    "新订单待确认",
                    UserStore.displayName(username) + " 下单 ¥" + round2(subtotal) + "，请确认处理。",
                    "order",
                    orderId);
        } catch (Exception ignored) {
        }
        return getOrder(orderId);
    }

    public static Map<String, Object> placeSimple(
            String username, long itemId, String title, double priceYuan, int qty, String remark) {
        return placeSimple(username, itemId, title, priceYuan, qty, remark, null);
    }

    public static Map<String, Object> placeSimple(
            String username, long itemId, String title, double priceYuan, int qty, String remark, Long reservationId) {
        if (!enabled) return null;
        if (qty < 1) qty = 1;
        int q = qty;
        boolean withResv = reservationId != null && reservationId > 0 && hasOrderColumn("reservation_id");
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        double total = round2(priceYuan * q);
        Map<String, Object> orderRow = new LinkedHashMap<>();
        orderRow.put("orderTable", ORDER);
        orderRow.put("username", username);
        orderRow.put("status", "pending");
        orderRow.put("totalYuan", BigDecimal.valueOf(total).setScale(2, RoundingMode.HALF_UP));
        orderRow.put("remark", remark == null ? "" : remark);
        LinkedHashMap<String, Object> extra = new LinkedHashMap<>();
        if (withResv) extra.put("reservation_id", reservationId);
        orderRow.put("extraCols", extra);
        orderRow.put("createdAt", now);
        orderRow.put("updatedAt", now);
        mapper().insertOrder(orderRow);
        long orderId = orderRow.get("id") == null ? 0L : ((Number) orderRow.get("id")).longValue();
        mapper().insertLine(LINE, orderId, itemId, title == null ? "" : title, priceYuan, q);
        return getOrder(orderId);
    }

    public static Map<String, Object> getOrder(long id) {
        requireEnabled();
        Map<String, Object> raw = mapper().selectOrderById(ORDER, id);
        if (raw == null) return null;
        Map<String, Object> m = shapeOrder(raw);
        m.put("lines", listLines(id));
        return m;
    }

    private static List<Map<String, Object>> listLines(long orderId) {
        List<Map<String, Object>> raw = mapper().selectLines(LINE, orderId);
        List<Map<String, Object>> out = new ArrayList<>();
        if (raw != null) {
            for (Map<String, Object> r : raw) {
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("id", r.get("id"));
                m.put("orderId", first(r, "orderId", "order_id"));
                m.put("itemId", first(r, "itemId", "item_id"));
                m.put("title", r.get("title"));
                double price = toDouble(first(r, "priceYuan", "price_yuan"));
                int qty = toInt(r.get("qty"));
                m.put("priceYuan", price);
                m.put("qty", qty);
                m.put("lineYuan", round2(price * qty));
                out.add(m);
            }
        }
        return out;
    }

    public static Map<String, Object> pageOrders(String username, String status, int page, int size) {
        requireEnabled();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String u = username == null || username.isBlank() ? null : username;
        String st = status == null || status.isBlank() ? null : status;
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectOrders(ORDER, u, st);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw == null ? List.of() : raw);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : pi.getList()) {
            Map<String, Object> m = shapeOrder(r);
            m.put("lines", listLines(num(r.get("id"))));
            list.add(m);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", pi.getTotal());
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static void completeByReservation(long reservationId) {
        advanceByReservation(reservationId, "complete");
    }

    public static void cancelByReservation(long reservationId) {
        advanceByReservation(reservationId, "cancel");
    }

    private static void advanceByReservation(long reservationId, String action) {
        if (!enabled || reservationId <= 0 || !hasOrderColumn("reservation_id")) return;
        List<Long> ids = mapper().selectIdsByReservation(ORDER, reservationId);
        if (ids == null) return;
        for (Long id : ids) {
            if (id == null) continue;
            try {
                String act = action;
                if ("cancel".equals(action)) {
                    Map<String, Object> m = getOrder(id);
                    if (m != null && "shipped".equals(String.valueOf(m.get("status")))) {
                        act = "complete";
                    }
                }
                // 办结关联订单：须先确认再履约，再完成（与基线一致）
                if ("complete".equals(act)) {
                    Map<String, Object> m = getOrder(id);
                    String st = m == null ? "" : String.valueOf(m.get("status"));
                    if ("pending".equals(st)) {
                        advance(id, "confirm", null);
                        advance(id, "ship", null);
                    } else if ("confirmed".equals(st)) {
                        advance(id, "ship", null);
                    }
                }
                advance(id, act, null);
            } catch (Exception ignored) {
            }
        }
    }

    public static Map<String, Object> advance(long orderId, String action) {
        return advance(orderId, action, null);
    }

    public static int cancelTimedOutPending(int minutes) {
        if (!enabled || minutes <= 0) return 0;
        List<Long> ids;
        try {
            ids = mapper().selectTimedOutPendingIds(ORDER, minutes);
        } catch (Exception e) {
            return 0;
        }
        if (ids == null || ids.isEmpty()) return 0;
        int n = 0;
        for (Long id : ids) {
            if (id == null) continue;
            try {
                advance(id, "cancel", null);
                n++;
            } catch (Exception ignored) {
            }
        }
        return n;
    }

    public static Map<String, Object> advance(long orderId, String action, Map<String, Object> opts) {
        requireEnabled();
        Map<String, Object> m = getOrder(orderId);
        if (m == null) throw new IllegalArgumentException("订单不存在");
        String st = String.valueOf(m.get("status"));
        String act = action == null ? "" : action.trim().toLowerCase(Locale.ROOT);
        String next;
        if ("confirm".equals(act) && "pending".equals(st)) next = "confirmed";
        // 发货/出餐须先确认，禁止 pending 跳步（与基线一致）
        else if ("ship".equals(act) && "confirmed".equals(st)) next = "shipped";
        // 完成必须先发货/出餐；售后中不可完成
        else if ("complete".equals(act) && "shipped".equals(st)) {
            if ("pending".equals(String.valueOf(m.getOrDefault("refundStatus", "")))) {
                throw new IllegalStateException("售后处理中，不可完成订单");
            }
            next = "completed";
        }
        else if ("cancel".equals(act) && ("pending".equals(st) || "confirmed".equals(st))) next = "cancelled";
        else throw new IllegalStateException("当前状态不可执行：" + act);
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        if ("shipped".equals(next)
                && (hasOrderColumn("tracking_no")
                || hasOrderColumn("pickup_code")
                || hasOrderColumn("shipped_at"))) {
            String tracking = opts == null ? "" : String.valueOf(opts.getOrDefault("trackingNo", "")).trim();
            String pickup = opts == null ? "" : String.valueOf(opts.getOrDefault("pickupCode", "")).trim();
            if (pickup.isBlank() && hasOrderColumn("pickup_code")) {
                String dtype = String.valueOf(m.getOrDefault("deliveryType", ""));
                if (dtype.contains("自取") || dtype.contains("堂食") || dtype.contains("自提")) {
                    pickup = String.format("%04d", (int) (orderId % 10000));
                }
            }
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("orderTable", ORDER);
            row.put("id", orderId);
            row.put("status", next);
            row.put("updatedAt", now);
            if (hasOrderColumn("tracking_no")) row.put("trackingNo", tracking);
            if (hasOrderColumn("pickup_code")) row.put("pickupCode", pickup);
            if (hasOrderColumn("shipped_at")) row.put("shippedAt", now);
            mapper().updateOrderShip(row);
        } else {
            mapper().updateOrderStatus(ORDER, orderId, next, now);
        }
        if ("cancelled".equals(next) && useQuota) {
            for (Map<String, Object> line : listLines(orderId)) {
                ArchiveStore.adjustStock(
                        ((Number) line.get("itemId")).longValue(),
                        ((Number) line.get("qty")).intValue());
            }
        }
        if ("cancelled".equals(next) && LoyaltyStore.anyEnabled()) {
            double paid = toDouble(m.get("payBalanceYuan"));
            String uname = String.valueOf(m.get("username"));
            if (paid > 0) {
                LoyaltyStore.refundOrderPay(uname, orderId, paid);
            }
            if (LoyaltyStore.isCouponEnabled()) {
                CouponStore.releaseByOrder(orderId);
            }
        }
        if ("completed".equals(next) && LoyaltyStore.anyEnabled()) {
            String uname = String.valueOf(m.get("username"));
            double pay = toDouble(m.get("payBalanceYuan"));
            if (pay <= 0) pay = toDouble(m.get("totalYuan"));
            LoyaltyStore.onOrderCompleted(uname, orderId, pay);
        }
        return getOrder(orderId);
    }

    public static Map<String, Object> dashboard() {
        if (!enabled) return Map.of();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("pendingOrders", mapper().countByStatus(ORDER, "pending"));
        m.put("confirmedOrders", mapper().countByStatus(ORDER, "confirmed"));
        m.put("shippedOrders", mapper().countByStatus(ORDER, "shipped"));
        m.put("completedOrders", mapper().countByStatus(ORDER, "completed"));
        return m;
    }

    public static Map<String, Object> chartStats() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("statusSeries", List.of());
        out.put("trendSeries", List.of());
        if (!enabled) return out;
        try {
            List<Map<String, Object>> status = mapper().selectStatusSeries(ORDER);
            out.put("statusSeries", status == null ? List.of() : status);
            List<Map<String, Object>> trend = mapper().selectTrendSeries(ORDER);
            out.put("trendSeries", trend == null ? List.of() : trend);
        } catch (Exception ignored) {
        }
        return out;
    }

    private static Map<String, Object> shapeOrder(Map<String, Object> raw) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", raw.get("id"));
        m.put("username", raw.get("username"));
        m.put("status", raw.get("status"));
        m.put("totalYuan", toDouble(first(raw, "totalYuan", "total_yuan")));
        m.put("remark", raw.get("remark"));
        m.put("receiverName", str(first(raw, "receiverName", "receiver_name")));
        m.put("receiverPhone", str(first(raw, "receiverPhone", "receiver_phone")));
        m.put("addressLine", str(first(raw, "addressLine", "address_line")));
        m.put("deliveryType", str(first(raw, "deliveryType", "delivery_type")));
        m.put("tasteNote", str(first(raw, "tasteNote", "taste_note")));
        m.put("trackingNo", str(first(raw, "trackingNo", "tracking_no")));
        m.put("pickupCode", str(first(raw, "pickupCode", "pickup_code")));
        m.put("shippedAt", fmt(first(raw, "shippedAt", "shipped_at")));
        long rid = num(first(raw, "reservationId", "reservation_id"));
        if (rid > 0) m.put("reservationId", rid);
        m.put("discountYuan", toDouble(first(raw, "discountYuan", "discount_yuan")));
        m.put("payBalanceYuan", toDouble(first(raw, "payBalanceYuan", "pay_balance_yuan")));
        m.put("pointsEarned", toInt(first(raw, "pointsEarned", "points_earned")));
        m.put("couponCode", str(first(raw, "couponCode", "coupon_code")));
        m.put("refundStatus", str(first(raw, "refundStatus", "refund_status")));
        m.put("refundReason", str(first(raw, "refundReason", "refund_reason")));
        m.put("refundAt", fmt(first(raw, "refundAt", "refund_at")));
        m.put("createdAt", fmt(first(raw, "createdAt", "created_at")));
        m.put("updatedAt", fmt(first(raw, "updatedAt", "updated_at")));
        String un = str(raw.get("username"));
        if (!un.isBlank()) m.put("displayName", UserStore.displayName(un));
        return m;
    }

    private static Object first(Map<String, Object> raw, String... keys) {
        for (String k : keys) {
            if (raw.containsKey(k) && raw.get(k) != null) return raw.get(k);
        }
        return null;
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static long num(Object o) {
        if (o instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(o));
        } catch (Exception e) {
            return 0L;
        }
    }

    private static int toInt(Object o) {
        if (o instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(String.valueOf(o).trim());
        } catch (Exception e) {
            return 0;
        }
    }

    private static double toDouble(Object o) {
        if (o instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(o));
        } catch (Exception e) {
            return 0;
        }
    }

    private static boolean hasOrderColumn(String col) {
        try {
            Integer n = schema().countColumn(ORDER, col);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static void ensureLoyaltyColumns() {
        ensureOrderColumn("discount_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0");
        ensureOrderColumn("pay_balance_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0");
        ensureOrderColumn("points_earned", "INT NOT NULL DEFAULT 0");
        ensureOrderColumn("coupon_code", "VARCHAR(32) DEFAULT ''");
    }

    private static void ensureRefundColumns() {
        ensureOrderColumn("refund_status", "VARCHAR(16) DEFAULT ''");
        ensureOrderColumn("refund_reason", "VARCHAR(255) DEFAULT ''");
        ensureOrderColumn("refund_at", "DATETIME NULL");
    }

    private static void applyLoyaltySnapshot(long orderId, Map<String, Object> snap) {
        if (snap == null || orderId <= 0) return;
        double discount = toDouble(snap.get("discountYuan"));
        double payBal = toDouble(snap.get("payBalanceYuan"));
        double payable = toDouble(snap.get("payableYuan"));
        String coupon = String.valueOf(snap.getOrDefault("couponCode", ""));
        try {
            if (hasOrderColumn("discount_yuan") && hasOrderColumn("pay_balance_yuan")) {
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("orderTable", ORDER);
                row.put("id", orderId);
                row.put("totalYuan", BigDecimal.valueOf(payable).setScale(2, RoundingMode.HALF_UP));
                row.put("discountYuan", BigDecimal.valueOf(discount).setScale(2, RoundingMode.HALF_UP));
                row.put("payBalanceYuan", BigDecimal.valueOf(payBal).setScale(2, RoundingMode.HALF_UP));
                row.put("updatedAt", Timestamp.valueOf(LocalDateTime.now()));
                if (hasOrderColumn("coupon_code")) {
                    row.put("couponCode", coupon == null || "null".equals(coupon) ? "" : coupon);
                    mapper().applyLoyaltyWithCoupon(row);
                } else {
                    mapper().applyLoyaltyPlain(row);
                }
            }
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> requestRefund(long orderId, String username, String reason) {
        requireEnabled();
        ensureRefundColumns();
        Map<String, Object> m = getOrder(orderId);
        if (m == null) throw new IllegalArgumentException("订单不存在");
        if (!username.equals(String.valueOf(m.get("username")))) {
            throw new IllegalStateException("无权申请");
        }
        String st = String.valueOf(m.get("status"));
        if (!"shipped".equals(st) && !"completed".equals(st)) {
            throw new IllegalStateException("仅配送中/已完成订单可申请售后");
        }
        String rs = String.valueOf(m.getOrDefault("refundStatus", ""));
        if ("pending".equals(rs) || "approved".equals(rs)) {
            throw new IllegalStateException("已有售后申请");
        }
        String why = reason == null ? "" : reason.trim();
        if (why.isBlank()) throw new IllegalStateException("请填写售后原因");
        if (why.length() > 255) why = why.substring(0, 255);
        mapper().requestRefund(ORDER, orderId, why, Timestamp.valueOf(LocalDateTime.now()));
        try {
            MessageStore.notifyAdmins(
                    "售后待处理",
                    UserStore.displayName(username) + " 申请订单 #" + orderId + " 售后：" + why,
                    "order",
                    orderId);
        } catch (Exception ignored) {
        }
        return getOrder(orderId);
    }

    public static Map<String, Object> decideRefund(long orderId, boolean pass, String note) {
        requireEnabled();
        ensureRefundColumns();
        Map<String, Object> m = getOrder(orderId);
        if (m == null) throw new IllegalArgumentException("订单不存在");
        if (!"pending".equals(String.valueOf(m.getOrDefault("refundStatus", "")))) {
            throw new IllegalStateException("当前无待审售后");
        }
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        if (!pass) {
            String tip = note == null || note.isBlank() ? "售后已驳回" : note.trim();
            mapper().rejectRefund(ORDER, orderId, tip, now, now);
            try {
                MessageStore.send(
                        String.valueOf(m.get("username")),
                        "售后已驳回",
                        "订单 #" + orderId + "：" + tip,
                        "order",
                        orderId);
            } catch (Exception ignored) {
            }
            return getOrder(orderId);
        }
        String prevStatus = String.valueOf(m.get("status"));
        if (useQuota) {
            for (Map<String, Object> line : listLines(orderId)) {
                ArchiveStore.adjustStock(
                        ((Number) line.get("itemId")).longValue(),
                        ((Number) line.get("qty")).intValue());
            }
        }
        if (LoyaltyStore.anyEnabled()) {
            String uname = String.valueOf(m.get("username"));
            double paid = toDouble(m.get("payBalanceYuan"));
            if (paid > 0) {
                LoyaltyStore.refundOrderPay(uname, orderId, paid);
            }
            if ("completed".equals(prevStatus)) {
                int pts = 0;
                Object pe = m.get("pointsEarned");
                if (pe instanceof Number n) pts = n.intValue();
                double pay = paid > 0 ? paid : toDouble(m.get("totalYuan"));
                LoyaltyStore.clawbackOrderCompleted(uname, orderId, pts, pay);
            }
            if (LoyaltyStore.isCouponEnabled()) {
                CouponStore.releaseByOrder(orderId);
            }
        }
        mapper().approveRefund(ORDER, orderId, now, now);
        try {
            MessageStore.send(
                    String.valueOf(m.get("username")),
                    "售后已通过",
                    "订单 #" + orderId + " 已退款办结（演示环境）。",
                    "order",
                    orderId);
        } catch (Exception ignored) {
        }
        return getOrder(orderId);
    }

    public static List<Map<String, Object>> logisticsTrace(long orderId) {
        requireEnabled();
        Map<String, Object> m = getOrder(orderId);
        if (m == null) throw new IllegalArgumentException("订单不存在");
        List<Map<String, Object>> nodes = new ArrayList<>();
        nodes.add(traceNode(m.get("createdAt"), "已下单", "商家待确认"));
        String st = String.valueOf(m.get("status"));
        if (!"pending".equals(st) && !"cancelled".equals(st)) {
            nodes.add(traceNode(m.get("updatedAt"), "商家已确认", "备货中"));
        }
        boolean inTransit = "shipped".equals(st) || "completed".equals(st);
        if (inTransit) {
            Object shipAt = m.get("shippedAt") != null ? m.get("shippedAt") : m.get("updatedAt");
            String track = String.valueOf(m.getOrDefault("trackingNo", ""));
            String dtype = String.valueOf(m.getOrDefault("deliveryType", ""));
            boolean pickup = dtype.contains("自取") || dtype.contains("堂食") || dtype.contains("自提");
            if (pickup) {
                String code = String.valueOf(m.getOrDefault("pickupCode", ""));
                String tip = code.isBlank() || "null".equals(code) ? "请到店领取" : ("取餐码 " + code);
                nodes.add(traceNode(shipAt, "已出餐", tip));
                nodes.add(traceNode(shipAt, "待取餐", "请尽快到店领取"));
            } else {
                String tip = track.isBlank() || "null".equals(track) ? "已交接承运" : ("运单 " + track);
                nodes.add(traceNode(shipAt, "已发货", tip));
                nodes.add(traceNode(shipAt, "运输中", "快件运输途中（演示）"));
                nodes.add(traceNode(shipAt, "派送中", "快递员正在派送（演示）"));
            }
        }
        if ("completed".equals(st)) {
            nodes.add(traceNode(m.get("updatedAt"), "已签收/完成", "订单完结"));
        }
        if ("cancelled".equals(st)) {
            nodes.add(traceNode(m.get("updatedAt"), "已取消", "订单关闭"));
        }
        String rs = String.valueOf(m.getOrDefault("refundStatus", ""));
        if ("pending".equals(rs)) {
            nodes.add(traceNode(m.get("updatedAt"), "售后申请中", String.valueOf(m.getOrDefault("refundReason", ""))));
        } else if ("approved".equals(rs)) {
            nodes.add(traceNode(m.get("refundAt"), "售后已通过", "已退款办结"));
        } else if ("rejected".equals(rs)) {
            nodes.add(traceNode(m.get("refundAt"), "售后已驳回", String.valueOf(m.getOrDefault("refundReason", ""))));
        }
        return nodes;
    }

    private static Map<String, Object> traceNode(Object at, String title, String detail) {
        Map<String, Object> n = new LinkedHashMap<>();
        n.put("at", at == null || "null".equals(String.valueOf(at)) ? "" : String.valueOf(at));
        n.put("title", title);
        n.put("detail", detail == null ? "" : detail);
        return n;
    }

    private static void ensureOrderColumn(String col, String ddlType) {
        if (hasOrderColumn(col)) return;
        try {
            schema().executeDdl("ALTER TABLE " + ORDER + " ADD COLUMN " + col + " " + ddlType);
        } catch (Exception ignored) {
        }
    }

    private static void requireEnabled() {
        if (!enabled) throw new IllegalStateException("订单功能暂不可用");
    }

    private static double round2(double v) {
        return Math.round(v * 100.0) / 100.0;
    }
}
