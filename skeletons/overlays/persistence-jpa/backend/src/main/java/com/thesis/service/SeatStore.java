package com.thesis.service;

import com.thesis.capability.ArchiveStore;
import com.thesis.capability.OrderStore;
import com.thesis.config.JpaSupport;
import com.thesis.config.JpaDb;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 影院选座（C-15）：场次座位图、演示占座并生成订单。
 */
public class SeatStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int DEFAULT_ROWS = 6;
    private static final int DEFAULT_COLS = 8;
    private static boolean enabled;
    private static Boolean tableReady;

    private SeatStore() {}

    public static void configure(boolean on) {
        enabled = on;
        tableReady = null;
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JpaDb db() {
        return JpaSupport.db();
    }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='cinema_seat'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("选座功能暂不可用");
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        String t = s.trim();
        return t.length() <= max ? t : t.substring(0, max);
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static Map<String, Object> mapShow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("title", rs.getString("title"));
        m.put("author", rs.getString("author"));
        m.put("isbn", rs.getString("isbn"));
        m.put("categoryId", rs.getObject("category_id"));
        m.put("stock", rs.getInt("stock"));
        m.put("status", rs.getString("status"));
        m.put("coverUrl", rs.getString("cover_url"));
        return m;
    }

    private static Map<String, Object> mapSeat(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("showId", rs.getLong("show_id"));
        m.put("seatCode", rs.getString("seat_code"));
        m.put("status", rs.getString("status"));
        m.put("username", rs.getString("username"));
        m.put("orderId", rs.getObject("order_id"));
        Timestamp sold = rs.getTimestamp("sold_at");
        m.put("soldAt", sold == null ? null : sold.toLocalDateTime().format(FMT));
        return m;
    }

    private static String seatCode(int row, int col) {
        return String.valueOf((char) ('A' + row)) + (col + 1);
    }

    private static void ensureSeatMap(long showId) {
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM cinema_seat WHERE show_id=?", Integer.class, showId);
        if (n != null && n > 0) return;
        for (int r = 0; r < DEFAULT_ROWS; r++) {
            for (int c = 0; c < DEFAULT_COLS; c++) {
                db().update(
                        "INSERT INTO cinema_seat (show_id, seat_code, status) VALUES (?,?, 'free')",
                        showId, seatCode(r, c));
            }
        }
    }

    public static List<Map<String, Object>> listOpenShows() {
        require();
        return db().query(
                "SELECT * FROM cinema_show WHERE status='available' AND stock>0 ORDER BY id DESC",
                (rs, i) -> mapShow(rs));
    }

    public static Map<String, Object> getShow(long id) {
        require();
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM cinema_show WHERE id=?", (rs, i) -> mapShow(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Map<String, Object> getMap(long showId) {
        require();
        Map<String, Object> show = getShow(showId);
        if (show == null) throw new IllegalArgumentException("场次不存在");
        ensureSeatMap(showId);
        List<Map<String, Object>> seats = db().query(
                "SELECT * FROM cinema_seat WHERE show_id=? ORDER BY seat_code",
                (rs, i) -> mapSeat(rs),
                showId);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("show", show);
        out.put("rows", DEFAULT_ROWS);
        out.put("cols", DEFAULT_COLS);
        out.put("seats", seats);
        long free = seats.stream().filter(s -> "free".equals(str(s.get("status")))).count();
        out.put("freeCount", free);
        return out;
    }

    private static double priceOf(Map<String, Object> show) {
        try {
            return Double.parseDouble(str(show.get("author")).replace("¥", "").replace("￥", ""));
        } catch (Exception e) {
            return 0;
        }
    }

    /** 选座下单：占座 + OrderStore.placeSimple。 */
    @SuppressWarnings("unchecked")
    public static Map<String, Object> purchase(String username, long showId, List<String> seatCodes) {
        require();
        String u = clip(username, 64);
        if (u.isBlank()) throw new IllegalArgumentException("未登录");
        if (seatCodes == null || seatCodes.isEmpty()) {
            throw new IllegalArgumentException("请至少选择一个座位");
        }
        List<String> codes = seatCodes.stream()
                .map(s -> clip(s, 16).toUpperCase(Locale.ROOT))
                .filter(s -> !s.isBlank())
                .distinct()
                .collect(Collectors.toList());
        if (codes.isEmpty()) throw new IllegalArgumentException("请至少选择一个座位");
        if (codes.size() > 6) throw new IllegalArgumentException("单次最多选 6 个座位");

        Map<String, Object> show = getShow(showId);
        if (show == null || !"available".equals(str(show.get("status")))) {
            throw new IllegalStateException("场次不可售");
        }
        ensureSeatMap(showId);

        for (String code : codes) {
            Integer free = db().queryForObject(
                    "SELECT COUNT(*) FROM cinema_seat WHERE show_id=? AND seat_code=? AND status='free'",
                    Integer.class, showId, code);
            if (free == null || free == 0) {
                throw new IllegalStateException("座位 " + code + " 不可选");
            }
        }

        if (!OrderStore.enabled()) {
            throw new IllegalStateException("订单功能暂不可用");
        }
        double unit = priceOf(show);
        String seatRemark = "座位 " + String.join(",", codes);
        String title = str(show.get("title"));
        Map<String, Object> order = OrderStore.placeSimple(
                u, showId, title, unit, codes.size(), seatRemark);
        if (order == null) throw new IllegalStateException("下单失败");
        long orderId = order.get("id") instanceof Number n ? n.longValue() : 0L;

        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        for (String code : codes) {
            int n = db().update(
                    "UPDATE cinema_seat SET status='sold', username=?, order_id=?, sold_at=? "
                            + "WHERE show_id=? AND seat_code=? AND status='free'",
                    u, orderId, now, showId, code);
            if (n == 0) {
                throw new IllegalStateException("座位 " + code + " 已被占用");
            }
        }
        ArchiveStore.adjustStock(showId, -codes.size());

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("order", order);
        out.put("seats", codes);
        out.put("totalYuan", BigDecimal.valueOf(unit * codes.size()).setScale(2, RoundingMode.HALF_UP));
        return out;
    }
}
