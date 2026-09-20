package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 租赁押金/租金/逾期费分记；还车后验损退押。 */
public final class RentalBondStore {

    private static boolean enabled;

    private RentalBondStore() {}

    public static void configure(boolean on) {
        enabled = on;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static void onOrderPlaced(long orderId, long itemId, double rentYuan) {
        if (!enabled || orderId <= 0) return;
        String order = orderTable();
        BigDecimal deposit = itemDeposit(itemId);
        BigDecimal rent = money(rentYuan);
        BigDecimal total = deposit.add(rent).setScale(2, RoundingMode.HALF_UP);
        try {
            db().update(
                    "UPDATE " + order
                            + " SET deposit_yuan=?, rent_yuan=?, late_fee_yuan=0, deposit_status='held', total_yuan=? WHERE id=?",
                    deposit, rent, total, orderId);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置押金租金字段，无法下单", e);
        }
        if (LoyaltyStore.isWalletEnabled()) {
            Map<String, Object> row = OrderStore.getOrder(orderId);
            if (row == null) return;
            String user = String.valueOf(row.get("username"));
            double already = money(row.get("payBalanceYuan")).doubleValue();
            double need = total.doubleValue() - already;
            if (need > 1e-9) {
                LoyaltyStore.captureOrderPay(user, need, orderId);
                try {
                    db().update("UPDATE " + order + " SET pay_balance_yuan=? WHERE id=?", total, orderId);
                } catch (Exception ignored) {
                }
            }
        }
    }

    public static void onShipped(long orderId) {
        if (!enabled || orderId <= 0) return;
        Long itemId = firstItemId(orderId);
        if (itemId != null && itemId > 0) setRentStage(itemId, "rented");
    }

    public static void onCompleted(long orderId) {
        if (!enabled || orderId <= 0) return;
        Map<String, Object> order = OrderStore.getOrder(orderId);
        if (order == null) return;
        BigDecimal late = calcLateFee(order);
        try {
            db().update(
                    "UPDATE " + orderTable()
                            + " SET late_fee_yuan=?, deposit_status='inspecting', updated_at=? WHERE id=?",
                    late, Timestamp.valueOf(LocalDateTime.now()), orderId);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置验损字段", e);
        }
        if (late.signum() > 0 && LoyaltyStore.isWalletEnabled()) {
            LoyaltyStore.captureOrderPay(String.valueOf(order.get("username")), late.doubleValue(), orderId);
        }
    }

    public static List<Map<String, Object>> pendingInspect() {
        requireOn();
        return db().query(
                "SELECT id, username, total_yuan, deposit_yuan, rent_yuan, late_fee_yuan, deposit_status,"
                        + " damage_note, damage_deduct_yuan, status FROM " + orderTable()
                        + " WHERE deposit_status='inspecting' ORDER BY id DESC",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("username", rs.getString("username"));
                    m.put("totalYuan", rs.getBigDecimal("total_yuan"));
                    m.put("depositYuan", rs.getBigDecimal("deposit_yuan"));
                    m.put("rentYuan", rs.getBigDecimal("rent_yuan"));
                    m.put("lateFeeYuan", rs.getBigDecimal("late_fee_yuan"));
                    m.put("depositStatus", rs.getString("deposit_status"));
                    m.put("damageNote", rs.getString("damage_note"));
                    m.put("damageDeductYuan", rs.getBigDecimal("damage_deduct_yuan"));
                    m.put("status", rs.getString("status"));
                    return m;
                });
    }

    public static Map<String, Object> inspect(long orderId, String note, Object deductYuan, boolean repair) {
        requireOn();
        Map<String, Object> order = OrderStore.getOrder(orderId);
        if (order == null) throw new IllegalArgumentException("订单不存在");
        String ds = String.valueOf(order.getOrDefault("depositStatus", ""));
        if (!"inspecting".equals(ds) && !"held".equals(ds)) {
            throw new IllegalStateException("当前不可验损");
        }
        BigDecimal deposit = money(order.get("depositYuan"));
        BigDecimal deduct = money(deductYuan);
        if (deduct.signum() < 0) throw new IllegalArgumentException("扣款不能为负");
        if (deduct.compareTo(deposit) > 0) deduct = deposit;
        BigDecimal refund = deposit.subtract(deduct).setScale(2, RoundingMode.HALF_UP);
        String status = deduct.signum() > 0 ? "deducted" : "refunded";
        String why = note == null ? "" : note.trim();
        db().update(
                "UPDATE " + orderTable()
                        + " SET deposit_status=?, damage_note=?, damage_deduct_yuan=?, updated_at=? WHERE id=?",
                status, why, deduct, Timestamp.valueOf(LocalDateTime.now()), orderId);
        if (refund.signum() > 0 && LoyaltyStore.isWalletEnabled()) {
            LoyaltyStore.refundOrderPay(String.valueOf(order.get("username")), orderId, refund.doubleValue());
        }
        Long itemId = firstItemId(orderId);
        if (itemId != null && itemId > 0) setRentStage(itemId, repair ? "repair" : "available");
        return OrderStore.getOrder(orderId);
    }

    private static BigDecimal calcLateFee(Map<String, Object> order) {
        Object resvId = order.get("reservationId");
        if (resvId == null) return BigDecimal.ZERO;
        try {
            long id = Long.parseLong(String.valueOf(resvId));
            List<Timestamp> ends = db().query(
                    "SELECT end_at FROM reservation WHERE id=?",
                    (rs, i) -> rs.getTimestamp(1),
                    id);
            if (ends.isEmpty() || ends.get(0) == null) return BigDecimal.ZERO;
            LocalDate end = ends.get(0).toLocalDateTime().toLocalDate();
            long days = ChronoUnit.DAYS.between(end, LocalDate.now());
            if (days <= 0) return BigDecimal.ZERO;
            return BigDecimal.valueOf(20).multiply(BigDecimal.valueOf(days)).setScale(2, RoundingMode.HALF_UP);
        } catch (Exception e) {
            return BigDecimal.ZERO;
        }
    }

    private static BigDecimal itemDeposit(long itemId) {
        if (itemId <= 0) return BigDecimal.valueOf(500);
        try {
            List<BigDecimal> rows = db().query(
                    "SELECT deposit_yuan FROM " + itemTable() + " WHERE id=?",
                    (rs, i) -> rs.getBigDecimal(1),
                    itemId);
            if (!rows.isEmpty() && rows.get(0) != null && rows.get(0).signum() > 0) {
                return rows.get(0).setScale(2, RoundingMode.HALF_UP);
            }
        } catch (Exception ignored) {
        }
        return BigDecimal.valueOf(500);
    }

    private static void setRentStage(long itemId, String stage) {
        try {
            db().update("UPDATE " + itemTable() + " SET rent_stage=? WHERE id=?", stage, itemId);
        } catch (Exception e) {
            throw new IllegalStateException("系统未配置租用状态字段", e);
        }
    }

    private static Long firstItemId(long orderId) {
        try {
            String line = OrderStore.lineTable();
            if (line == null || line.isBlank()) line = "order_line";
            List<Long> ids = db().query(
                    "SELECT item_id FROM " + line + " WHERE order_id=? ORDER BY id LIMIT 1",
                    (rs, i) -> rs.getLong(1),
                    orderId);
            return ids.isEmpty() ? null : ids.get(0);
        } catch (Exception e) {
            return null;
        }
    }

    private static String orderTable() {
        String t = OrderStore.orderTable();
        return t == null || t.isBlank() ? "biz_order" : t;
    }

    private static String itemTable() {
        String t = ArchiveStore.itemTable();
        return t == null || t.isBlank() ? "vehicle" : t;
    }

    private static void requireOn() {
        if (!enabled) throw new IllegalStateException("未开启租赁押金验损");
    }

    private static BigDecimal money(Object v) {
        if (v == null) return BigDecimal.ZERO;
        try {
            return new BigDecimal(String.valueOf(v)).setScale(2, RoundingMode.HALF_UP);
        } catch (Exception e) {
            return BigDecimal.ZERO;
        }
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }
}
