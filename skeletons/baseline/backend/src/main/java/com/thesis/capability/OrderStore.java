package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import com.thesis.service.MessageStore;
import com.thesis.service.UserStore;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.PreparedStatement;
import java.sql.Statement;
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

    public static void bind(String cartTable, String orderTable, String lineTable, boolean quota) {
        CART = cartTable == null ? "" : cartTable.trim();
        ORDER = orderTable == null ? "" : orderTable.trim();
        LINE = lineTable == null ? "" : lineTable.trim();
        enabled = !CART.isBlank() && !ORDER.isBlank() && !LINE.isBlank();
        useQuota = quota;
        AddressStore.resetCache();
        // 履约列由 bake 按域写入 schema，禁止运行时补餐饮/物流超集
    }

    public static void unbind() {
        enabled = false;
        CART = ORDER = LINE = "";
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static String fmt(Timestamp ts) {
        return ts == null ? null : ts.toLocalDateTime().format(FMT);
    }

    private static double priceOf(Map<String, Object> item) {
        // 约定：author 存单价（元）
        Object raw = item.get("author");
        if (raw == null) return 0;
        try {
            return Double.parseDouble(String.valueOf(raw).replace("¥", "").trim());
        } catch (Exception e) {
            return 0;
        }
    }

    public static List<Map<String, Object>> listCart(String username) {
        requireEnabled();
        return db().query(
                "SELECT c.id, c.item_id, c.qty FROM " + CART + " c WHERE c.username=? ORDER BY c.id",
                (rs, i) -> enrichCartRow(rs.getLong("id"), rs.getLong("item_id"), rs.getInt("qty")),
                username);
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
        Integer exist = db().queryForObject(
                "SELECT COUNT(*) FROM " + CART + " WHERE username=? AND item_id=?",
                Integer.class, username, itemId);
        if (exist != null && exist > 0) {
            db().update("UPDATE " + CART + " SET qty=? WHERE username=? AND item_id=?", qty, username, itemId);
        } else {
            db().update("INSERT INTO " + CART + " (username,item_id,qty) VALUES (?,?,?)", username, itemId, qty);
        }
        List<Map<String, Object>> rows = db().query(
                "SELECT id, item_id, qty FROM " + CART + " WHERE username=? AND item_id=?",
                (rs, i) -> enrichCartRow(rs.getLong("id"), rs.getLong("item_id"), rs.getInt("qty")),
                username, itemId);
        return rows.isEmpty() ? Map.of() : rows.get(0);
    }

    public static boolean removeCart(String username, long itemId) {
        requireEnabled();
        return db().update("DELETE FROM " + CART + " WHERE username=? AND item_id=?", username, itemId) > 0;
    }

    public static void clearCart(String username) {
        requireEnabled();
        db().update("DELETE FROM " + CART + " WHERE username=?", username);
    }

    public static Map<String, Object> placeOrder(String username, String remark) {
        return placeOrder(username, remark, null, null, null, null, null, null);
    }

    /**
     * @param addressId 地址簿 id；也可直接传 receiver/phone/address 快照
     * @param tasteNote 口味 / 忌口等（点餐常用）
     */
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
        // 仅当 schema 含收货列时校验地址；酒店等瘦订单表跳过
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
        KeyHolder kh = new GeneratedKeyHolder();
        double finalTotal = payable;
        String fName = rName, fPhone = rPhone, fAddr = addr, fType = dtype, fTaste = taste;
        LinkedHashMap<String, Object> extraCols = new LinkedHashMap<>();
        if (hasOrderColumn("receiver_name")) extraCols.put("receiver_name", fName);
        if (hasOrderColumn("receiver_phone")) extraCols.put("receiver_phone", fPhone);
        if (hasOrderColumn("address_line")) extraCols.put("address_line", fAddr);
        if (hasOrderColumn("delivery_type")) extraCols.put("delivery_type", fType);
        if (hasOrderColumn("taste_note")) extraCols.put("taste_note", fTaste);
        db().update(con -> {
            Timestamp now = Timestamp.valueOf(LocalDateTime.now());
            StringBuilder cols = new StringBuilder("username,status,total_yuan,remark");
            StringBuilder marks = new StringBuilder("?,?,?,?");
            List<Object> args = new ArrayList<>();
            args.add(username);
            args.add("pending");
            args.add(BigDecimal.valueOf(finalTotal).setScale(2, RoundingMode.HALF_UP));
            String noteOut = note;
            if (extraCols.isEmpty() && !fTaste.isBlank()) {
                noteOut = (noteOut.isBlank() ? "" : noteOut + "；") + "口味:" + fTaste;
            }
            if (extraCols.isEmpty() && !fAddr.isBlank()) {
                noteOut = (noteOut.isBlank() ? "" : noteOut + "；")
                        + "地址:" + fName + " " + fPhone + " " + fAddr;
            }
            args.add(noteOut);
            for (Map.Entry<String, Object> e : extraCols.entrySet()) {
                cols.append(',').append(e.getKey());
                marks.append(",?");
                args.add(e.getValue());
            }
            cols.append(",created_at,updated_at");
            marks.append(",?,?");
            args.add(now);
            args.add(now);
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + ORDER + " (" + cols + ") VALUES (" + marks + ")",
                    Statement.RETURN_GENERATED_KEYS);
            for (int i = 0; i < args.size(); i++) {
                Object v = args.get(i);
                if (v instanceof Timestamp ts) ps.setTimestamp(i + 1, ts);
                else if (v instanceof BigDecimal bd) ps.setBigDecimal(i + 1, bd);
                else ps.setString(i + 1, v == null ? "" : String.valueOf(v));
            }
            return ps;
        }, kh);
        long orderId = kh.getKey() == null ? 0L : kh.getKey().longValue();
        List<long[]> deducted = new ArrayList<>();
        try {
            for (Map<String, Object> line : cart) {
                long itemId = ((Number) line.get("itemId")).longValue();
                int qty = ((Number) line.get("qty")).intValue();
                Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
                double price = priceOf(item);
                db().update(
                        "INSERT INTO " + LINE + " (order_id,item_id,title,price_yuan,qty) VALUES (?,?,?,?,?)",
                        orderId, itemId, String.valueOf(item.get("title")), price, qty);
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
                db().update("DELETE FROM " + LINE + " WHERE order_id=?", orderId);
                db().update("DELETE FROM " + ORDER + " WHERE id=?", orderId);
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

    /** 预约域联动：单明细订单 */
    public static Map<String, Object> placeSimple(
            String username, long itemId, String title, double priceYuan, int qty, String remark) {
        return placeSimple(username, itemId, title, priceYuan, qty, remark, null);
    }

    public static Map<String, Object> placeSimple(
            String username, long itemId, String title, double priceYuan, int qty, String remark, Long reservationId) {
        if (!enabled) return null;
        if (qty < 1) qty = 1;
        KeyHolder kh = new GeneratedKeyHolder();
        int q = qty;
        boolean withResv = reservationId != null && reservationId > 0 && hasOrderColumn("reservation_id");
        db().update(con -> {
            PreparedStatement ps;
            Timestamp now = Timestamp.valueOf(LocalDateTime.now());
            double total = round2(priceYuan * q);
            if (withResv) {
                ps = con.prepareStatement(
                        "INSERT INTO " + ORDER
                                + " (username,status,total_yuan,remark,reservation_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, username);
                ps.setString(2, "pending");
                ps.setBigDecimal(3, BigDecimal.valueOf(total).setScale(2, RoundingMode.HALF_UP));
                ps.setString(4, remark == null ? "" : remark);
                ps.setLong(5, reservationId);
                ps.setTimestamp(6, now);
                ps.setTimestamp(7, now);
            } else {
                ps = con.prepareStatement(
                        "INSERT INTO " + ORDER + " (username,status,total_yuan,remark,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, username);
                ps.setString(2, "pending");
                ps.setBigDecimal(3, BigDecimal.valueOf(total).setScale(2, RoundingMode.HALF_UP));
                ps.setString(4, remark == null ? "" : remark);
                ps.setTimestamp(5, now);
                ps.setTimestamp(6, now);
            }
            return ps;
        }, kh);
        long orderId = kh.getKey() == null ? 0L : kh.getKey().longValue();
        db().update(
                "INSERT INTO " + LINE + " (order_id,item_id,title,price_yuan,qty) VALUES (?,?,?,?,?)",
                orderId, itemId, title == null ? "" : title, priceYuan, q);
        return getOrder(orderId);
    }

    public static Map<String, Object> getOrder(long id) {
        requireEnabled();
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + ORDER + " WHERE id=?", (rs, i) -> mapOrder(rs), id);
        if (list.isEmpty()) return null;
        Map<String, Object> m = list.get(0);
        m.put("lines", listLines(id));
        return m;
    }

    private static List<Map<String, Object>> listLines(long orderId) {
        return db().query(
                "SELECT * FROM " + LINE + " WHERE order_id=? ORDER BY id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("orderId", rs.getLong("order_id"));
                    m.put("itemId", rs.getLong("item_id"));
                    m.put("title", rs.getString("title"));
                    m.put("priceYuan", rs.getDouble("price_yuan"));
                    m.put("qty", rs.getInt("qty"));
                    m.put("lineYuan", round2(rs.getDouble("price_yuan") * rs.getInt("qty")));
                    return m;
                },
                orderId);
    }

    public static Map<String, Object> pageOrders(String username, String status, int page, int size) {
        requireEnabled();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        if (username != null && !username.isBlank()) {
            where.append(" AND username=?");
            args.add(username);
        }
        if (status != null && !status.isBlank()) {
            where.append(" AND status=?");
            args.add(status);
        }
        Integer total = db().queryForObject("SELECT COUNT(*) FROM " + ORDER + where, Integer.class, args.toArray());
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + ORDER + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = mapOrder(rs);
                    m.put("lines", listLines(rs.getLong("id")));
                    return m;
                },
                args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    /** 宾馆等：预约办结时把关联订单一并完成 */
    public static void completeByReservation(long reservationId) {
        advanceByReservation(reservationId, "complete");
    }

    /** 取消预约时关掉关联订单（回补库存走 advance cancel） */
    public static void cancelByReservation(long reservationId) {
        advanceByReservation(reservationId, "cancel");
    }

    private static void advanceByReservation(long reservationId, String action) {
        if (!enabled || reservationId <= 0 || !hasOrderColumn("reservation_id")) return;
        List<Long> ids = db().query(
                "SELECT id FROM " + ORDER + " WHERE reservation_id=? AND status IN ('pending','confirmed','shipped')",
                (rs, i) -> rs.getLong("id"),
                reservationId);
        for (Long id : ids) {
            if (id == null) continue;
            try {
                // cancel 仅 pending/confirmed；shipped 走 complete 更稳妥
                String act = action;
                if ("cancel".equals(action)) {
                    Map<String, Object> m = getOrder(id);
                    if (m != null && "shipped".equals(String.valueOf(m.get("status")))) {
                        act = "complete";
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

    /** 超时关单：取消超时仍 pending 的订单（回补库存/退演示余额）。 */
    public static int cancelTimedOutPending(int minutes) {
        if (!enabled || minutes <= 0) return 0;
        List<Long> ids;
        try {
            ids = db().query(
                    "SELECT id FROM " + ORDER
                            + " WHERE status='pending' AND created_at < DATE_SUB(NOW(), INTERVAL ? MINUTE)",
                    (rs, i) -> rs.getLong(1),
                    minutes);
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
        else if ("ship".equals(act) && ("pending".equals(st) || "confirmed".equals(st))) next = "shipped";
        else if ("complete".equals(act) && ("confirmed".equals(st) || "shipped".equals(st) || "pending".equals(st)))
            next = "completed";
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
            StringBuilder sql = new StringBuilder("UPDATE " + ORDER + " SET status=?");
            List<Object> args = new ArrayList<>();
            args.add(next);
            if (hasOrderColumn("tracking_no")) {
                sql.append(", tracking_no=?");
                args.add(tracking);
            }
            if (hasOrderColumn("pickup_code")) {
                sql.append(", pickup_code=?");
                args.add(pickup);
            }
            if (hasOrderColumn("shipped_at")) {
                sql.append(", shipped_at=?");
                args.add(now);
            }
            sql.append(", updated_at=? WHERE id=?");
            args.add(now);
            args.add(orderId);
            db().update(sql.toString(), args.toArray());
        } else {
            db().update(
                    "UPDATE " + ORDER + " SET status=?, updated_at=? WHERE id=?",
                    next, now, orderId);
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
            if (paid <= 0) paid = 0;
            String uname = String.valueOf(m.get("username"));
            if (paid > 0) {
                LoyaltyStore.refundOrderPay(uname, orderId, paid);
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
        m.put("pendingOrders", countStatus("pending"));
        m.put("confirmedOrders", countStatus("confirmed"));
        m.put("shippedOrders", countStatus("shipped"));
        m.put("completedOrders", countStatus("completed"));
        return m;
    }

    public static Map<String, Object> chartStats() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("statusSeries", List.of());
        out.put("trendSeries", List.of());
        if (!enabled) return out;
        try {
            List<Map<String, Object>> status = db().query(
                    "SELECT status AS name, COUNT(*) AS value FROM " + ORDER + " GROUP BY status",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("name", rs.getString("name"));
                        row.put("value", rs.getLong("value"));
                        return row;
                    });
            out.put("statusSeries", status);
            List<Map<String, Object>> trend = db().query(
                    "SELECT DATE_FORMAT(created_at,'%Y-%m-%d') AS day, COUNT(*) AS value FROM " + ORDER
                            + " WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)"
                            + " GROUP BY DATE_FORMAT(created_at,'%Y-%m-%d') ORDER BY day",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("day", rs.getString("day"));
                        row.put("value", rs.getLong("value"));
                        return row;
                    });
            out.put("trendSeries", trend);
        } catch (Exception ignored) {
        }
        return out;
    }

    private static long countStatus(String st) {
        Long n = db().queryForObject("SELECT COUNT(*) FROM " + ORDER + " WHERE status=?", Long.class, st);
        return n == null ? 0 : n;
    }

    private static Map<String, Object> mapOrder(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("status", rs.getString("status"));
        m.put("totalYuan", rs.getDouble("total_yuan"));
        m.put("remark", rs.getString("remark"));
        m.put("receiverName", safeStr(rs, "receiver_name"));
        m.put("receiverPhone", safeStr(rs, "receiver_phone"));
        m.put("addressLine", safeStr(rs, "address_line"));
        m.put("deliveryType", safeStr(rs, "delivery_type"));
        m.put("tasteNote", safeStr(rs, "taste_note"));
        m.put("trackingNo", safeStr(rs, "tracking_no"));
        m.put("pickupCode", safeStr(rs, "pickup_code"));
        m.put("shippedAt", fmt(safeTs(rs, "shipped_at")));
        long rid = safeLong(rs, "reservation_id");
        if (rid > 0) m.put("reservationId", rid);
        m.put("discountYuan", safeDouble(rs, "discount_yuan"));
        m.put("payBalanceYuan", safeDouble(rs, "pay_balance_yuan"));
        m.put("pointsEarned", (int) safeLong(rs, "points_earned"));
        m.put("couponCode", safeStr(rs, "coupon_code"));
        m.put("refundStatus", safeStr(rs, "refund_status"));
        m.put("refundReason", safeStr(rs, "refund_reason"));
        m.put("refundAt", fmt(safeTs(rs, "refund_at")));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        m.put("updatedAt", fmt(rs.getTimestamp("updated_at")));
        String un = rs.getString("username");
        if (un != null && !un.isBlank()) m.put("displayName", UserStore.displayName(un));
        return m;
    }

    private static double safeDouble(java.sql.ResultSet rs, String col) {
        try {
            double v = rs.getDouble(col);
            return rs.wasNull() ? 0 : v;
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

    private static Timestamp safeTs(java.sql.ResultSet rs, String col) {
        try {
            return rs.getTimestamp(col);
        } catch (Exception e) {
            return null;
        }
    }

    private static long safeLong(java.sql.ResultSet rs, String col) {
        try {
            long v = rs.getLong(col);
            return rs.wasNull() ? 0L : v;
        } catch (Exception e) {
            return 0L;
        }
    }

    private static String safeStr(java.sql.ResultSet rs, String col) {
        try {
            String v = rs.getString(col);
            return v == null ? "" : v;
        } catch (Exception e) {
            return "";
        }
    }

    private static boolean hasOrderColumn(String col) {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=? AND COLUMN_NAME=?",
                    Integer.class, ORDER, col);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static void ensureDeliveryColumns() {
        // no-op：履约列由 bake 按域写入，禁止运行时补跨域超集
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
                if (hasOrderColumn("coupon_code")) {
                    db().update(
                            "UPDATE " + ORDER
                                    + " SET total_yuan=?, discount_yuan=?, pay_balance_yuan=?, coupon_code=?, updated_at=? WHERE id=?",
                            BigDecimal.valueOf(payable).setScale(2, RoundingMode.HALF_UP),
                            BigDecimal.valueOf(discount).setScale(2, RoundingMode.HALF_UP),
                            BigDecimal.valueOf(payBal).setScale(2, RoundingMode.HALF_UP),
                            coupon == null || "null".equals(coupon) ? "" : coupon,
                            Timestamp.valueOf(LocalDateTime.now()),
                            orderId);
                } else {
                    db().update(
                            "UPDATE " + ORDER + " SET total_yuan=?, discount_yuan=?, pay_balance_yuan=?, updated_at=? WHERE id=?",
                            BigDecimal.valueOf(payable).setScale(2, RoundingMode.HALF_UP),
                            BigDecimal.valueOf(discount).setScale(2, RoundingMode.HALF_UP),
                            BigDecimal.valueOf(payBal).setScale(2, RoundingMode.HALF_UP),
                            Timestamp.valueOf(LocalDateTime.now()),
                            orderId);
                }
            }
        } catch (Exception ignored) {
        }
    }

    /** 用户申请售后/退款：shipped/completed → refund_status=pending */
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
        db().update(
                "UPDATE " + ORDER + " SET refund_status='pending', refund_reason=?, updated_at=? WHERE id=?",
                why, Timestamp.valueOf(LocalDateTime.now()), orderId);
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

    /** 管理端：通过售后（回补库存、退余额、订单 cancelled）或驳回 */
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
            db().update(
                    "UPDATE " + ORDER + " SET refund_status='rejected', refund_reason=?, refund_at=?, updated_at=? WHERE id=?",
                    tip, now, now, orderId);
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
        // 通过：按取消回补库存与余额，状态改为 cancelled
        if (useQuota) {
            for (Map<String, Object> line : listLines(orderId)) {
                ArchiveStore.adjustStock(
                        ((Number) line.get("itemId")).longValue(),
                        ((Number) line.get("qty")).intValue());
            }
        }
        if (LoyaltyStore.anyEnabled()) {
            double paid = toDouble(m.get("payBalanceYuan"));
            if (paid > 0) {
                LoyaltyStore.refundOrderPay(String.valueOf(m.get("username")), orderId, paid);
            }
        }
        db().update(
                "UPDATE " + ORDER
                        + " SET status='cancelled', refund_status='approved', refund_at=?, updated_at=? WHERE id=?",
                now, now, orderId);
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

    /** 演示物流轨迹：按状态拼多节点时间线（含运输中/派送中；无第三方快递 API）。 */
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
            db().execute("ALTER TABLE " + ORDER + " ADD COLUMN " + col + " " + ddlType);
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
