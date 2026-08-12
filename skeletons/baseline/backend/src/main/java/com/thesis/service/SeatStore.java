package com.thesis.service;

import com.thesis.capability.ArchiveStore;
import com.thesis.capability.OrderStore;
import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

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
 * 影院选座（C-15）：场次座位图（排×列可配）、占座并生成订单。
 */
public class SeatStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int DEFAULT_ROWS = 6;
    private static final int DEFAULT_COLS = 8;
    private static final int MAX_ROWS = 15;
    private static final int MAX_COLS = 16;
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

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
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

    private static int toInt(Object o, int def) {
        if (o == null) return def;
        if (o instanceof Number n) return n.intValue();
        try {
            String s = String.valueOf(o).trim();
            if (s.isBlank()) return def;
            return Integer.parseInt(s);
        } catch (Exception e) {
            return def;
        }
    }

    private static int clamp(int v, int lo, int hi) {
        return Math.max(lo, Math.min(hi, v));
    }

    /** 场次档案 seatRows / seatCols；缺省 6×8，上限 15×16。 */
    public static int rowsOf(Map<String, Object> show) {
        return clamp(toInt(show == null ? null : show.get("seatRows"), DEFAULT_ROWS), 1, MAX_ROWS);
    }

    public static int colsOf(Map<String, Object> show) {
        return clamp(toInt(show == null ? null : show.get("seatCols"), DEFAULT_COLS), 1, MAX_COLS);
    }

    private static Map<String, Object> mapShow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("title", rs.getString("title"));
        m.put("author", rs.getString(ArchiveStore.authorColumn()));
        m.put("isbn", rs.getString(ArchiveStore.isbnColumn()));
        m.put("categoryId", rs.getObject("category_id"));
        m.put("stock", rs.getInt("stock"));
        m.put("status", rs.getString("status"));
        m.put("coverUrl", rs.getString("cover_url"));
        try {
            Object rows = rs.getObject("seat_rows");
            m.put("seatRows", rows == null ? DEFAULT_ROWS : toInt(rows, DEFAULT_ROWS));
        } catch (SQLException e) {
            m.put("seatRows", DEFAULT_ROWS);
        }
        try {
            Object cols = rs.getObject("seat_cols");
            m.put("seatCols", cols == null ? DEFAULT_COLS : toInt(cols, DEFAULT_COLS));
        } catch (SQLException e) {
            m.put("seatCols", DEFAULT_COLS);
        }
        try {
            Timestamp start = rs.getTimestamp("start_at");
            m.put("startAt", start == null ? null : start.toLocalDateTime().format(FMT));
        } catch (SQLException e) {
            m.put("startAt", null);
        }
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

    private static List<String> expectedCodes(int rows, int cols) {
        List<String> codes = new ArrayList<>(rows * cols);
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                codes.add(seatCode(r, c));
            }
        }
        return codes;
    }

    /**
     * 按场次排×列同步座位：补缺空闲座、删掉布局外仍空闲的座；已售保留。
     * 无已售时把档案余座对齐为排×列。
     */
    private static void ensureSeatMap(long showId, Map<String, Object> show) {
        int rows = rowsOf(show);
        int cols = colsOf(show);
        List<String> expected = expectedCodes(rows, cols);
        for (String code : expected) {
            db().update(
                    "INSERT IGNORE INTO cinema_seat (show_id, seat_code, status) VALUES (?,?, 'free')",
                    showId, code);
        }
        if (!expected.isEmpty()) {
            String in = expected.stream().map(c -> "?").collect(Collectors.joining(","));
            List<Object> args = new ArrayList<>();
            args.add(showId);
            args.addAll(expected);
            db().update(
                    "DELETE FROM cinema_seat WHERE show_id=? AND status='free' AND seat_code NOT IN (" + in + ")",
                    args.toArray());
        }
        Integer sold = db().queryForObject(
                "SELECT COUNT(*) FROM cinema_seat WHERE show_id=? AND status='sold'",
                Integer.class, showId);
        if (sold != null && sold == 0) {
            int capacity = rows * cols;
            Integer cur = db().queryForObject(
                    "SELECT stock FROM cinema_show WHERE id=?", Integer.class, showId);
            if (cur == null || cur != capacity) {
                db().update("UPDATE cinema_show SET stock=? WHERE id=?", capacity, showId);
                show.put("stock", capacity);
            }
        }
        show.put("seatRows", rows);
        show.put("seatCols", cols);
    }

    /** 过开场时间：可售场次自动标为不可用（答辩常见逻辑，非真锁座）。 */
    public static int expirePastShows() {
        if (!enabled) return 0;
        if (!ready()) return 0;
        try {
            return db().update(
                    "UPDATE cinema_show SET status='unavailable' "
                            + "WHERE status='available' AND start_at IS NOT NULL AND start_at <= NOW()");
        } catch (Exception e) {
            return 0;
        }
    }

    private static boolean isPastStart(Map<String, Object> show) {
        String sa = str(show == null ? null : show.get("startAt"));
        if (sa.isBlank()) return false;
        try {
            String norm = sa.length() >= 19 ? sa.substring(0, 19) : sa;
            LocalDateTime t = LocalDateTime.parse(norm.replace(' ', 'T'));
            return !t.isAfter(LocalDateTime.now());
        } catch (Exception e) {
            try {
                LocalDateTime t = LocalDateTime.parse(sa, FMT);
                return !t.isAfter(LocalDateTime.now());
            } catch (Exception ignored) {
                return false;
            }
        }
    }

    /** 管理端改排×列后可显式同步（getMap/purchase 也会自动同步）。 */
    public static void syncLayout(long showId) {
        if (!enabled || showId <= 0) return;
        if (!ready()) return;
        try {
            Map<String, Object> show = getShow(showId);
            if (show == null) return;
            ensureSeatMap(showId, show);
        } catch (Exception ignored) {
        }
    }

    public static List<Map<String, Object>> listOpenShows() {
        require();
        expirePastShows();
        return db().query(
                "SELECT * FROM cinema_show WHERE status='available' AND stock>0 "
                        + "AND (start_at IS NULL OR start_at > NOW()) ORDER BY id DESC",
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
        expirePastShows();
        Map<String, Object> show = getShow(showId);
        if (show == null) throw new IllegalArgumentException("场次不存在");
        if (!"available".equals(str(show.get("status"))) || isPastStart(show)) {
            throw new IllegalStateException("场次已开场或已下架，不可选座");
        }
        ensureSeatMap(showId, show);
        show = getShow(showId);
        int rows = rowsOf(show);
        int cols = colsOf(show);
        List<Map<String, Object>> seats = db().query(
                "SELECT * FROM cinema_seat WHERE show_id=? ORDER BY seat_code",
                (rs, i) -> mapSeat(rs),
                showId);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("show", show);
        out.put("rows", rows);
        out.put("cols", cols);
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
        if (show == null || !"available".equals(str(show.get("status"))) || isPastStart(show)) {
            expirePastShows();
            throw new IllegalStateException("场次已开场或已下架，不可购票");
        }
        ensureSeatMap(showId, show);

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

    /** 取消订单时释放座位（status→free），与 OrderStore.advance cancel 钩子对齐。 */
    public static void releaseByOrder(long orderId) {
        if (!enabled || orderId <= 0) return;
        if (!ready()) return;
        try {
            db().update(
                    "UPDATE cinema_seat SET status='free', username=NULL, order_id=NULL, sold_at=NULL "
                            + "WHERE order_id=? AND status='sold'",
                    orderId);
        } catch (Exception ignored) {
        }
    }
}
