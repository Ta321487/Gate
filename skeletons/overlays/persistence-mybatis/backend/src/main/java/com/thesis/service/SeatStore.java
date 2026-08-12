package com.thesis.service;

import com.thesis.capability.ArchiveStore;
import com.thesis.capability.OrderStore;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.SeatMapper;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

/** 影院选座（C-15）MyBatis 叠层：排×列跟场次档案。 */
public class SeatStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int DEFAULT_ROWS = 6;
    private static final int DEFAULT_COLS = 8;
    private static final int MAX_ROWS = 15;
    private static final int MAX_COLS = 16;
    private static boolean enabled;
    private static Boolean tableReady;

    private SeatStore() {}

    private static SeatMapper mapper() {
        return MybatisSupport.mapper(SeatMapper.class);
    }

    public static void configure(boolean on) {
        enabled = on;
        tableReady = null;
    }

    public static boolean enabled() {
        return enabled;
    }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = mapper().countTable();
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

    public static int rowsOf(Map<String, Object> show) {
        return clamp(toInt(show == null ? null : show.get("seatRows"), DEFAULT_ROWS), 1, MAX_ROWS);
    }

    public static int colsOf(Map<String, Object> show) {
        return clamp(toInt(show == null ? null : show.get("seatCols"), DEFAULT_COLS), 1, MAX_COLS);
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        if (o instanceof java.util.Date d) return new Timestamp(d.getTime()).toLocalDateTime().format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
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

    private static void ensureSeatMap(long showId, Map<String, Object> show) {
        int rows = rowsOf(show);
        int cols = colsOf(show);
        List<String> expected = expectedCodes(rows, cols);
        for (String code : expected) {
            mapper().insertSeat(showId, code);
        }
        mapper().deleteFreeOutside(showId, expected);
        Integer sold = mapper().countSold(showId);
        if (sold != null && sold == 0) {
            int capacity = rows * cols;
            mapper().updateShowStock(showId, capacity);
            show.put("stock", capacity);
        }
        show.put("seatRows", rows);
        show.put("seatCols", cols);
    }

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

    /** 过开场时间：可售场次自动标为不可用。 */
    public static int expirePastShows() {
        if (!enabled) return 0;
        if (!ready()) return 0;
        try {
            return mapper().expirePastShows();
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

    public static List<Map<String, Object>> listOpenShows() {
        require();
        expirePastShows();
        return mapper().listOpenShows();
    }

    public static Map<String, Object> getShow(long id) {
        require();
        return mapper().getShow(id);
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
        List<Map<String, Object>> seats = mapper().listSeats(showId);
        for (Map<String, Object> s : seats) {
            if (s.containsKey("soldAt")) s.put("soldAt", fmt(s.get("soldAt")));
        }
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
            Integer free = mapper().countFreeSeat(showId, code);
            if (free == null || free == 0) {
                throw new IllegalStateException("座位 " + code + " 不可选");
            }
        }
        if (!OrderStore.enabled()) throw new IllegalStateException("订单功能暂不可用");
        double unit = priceOf(show);
        String seatRemark = "座位 " + String.join(",", codes);
        Map<String, Object> order = OrderStore.placeSimple(
                u, showId, str(show.get("title")), unit, codes.size(), seatRemark);
        if (order == null) throw new IllegalStateException("下单失败");
        long orderId = order.get("id") instanceof Number n ? n.longValue() : 0L;
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        for (String code : codes) {
            int n = mapper().sellSeat(showId, code, u, orderId, now);
            if (n == 0) throw new IllegalStateException("座位 " + code + " 已被占用");
        }
        ArchiveStore.adjustStock(showId, -codes.size());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("order", order);
        out.put("seats", codes);
        out.put("totalYuan", BigDecimal.valueOf(unit * codes.size()).setScale(2, RoundingMode.HALF_UP));
        return out;
    }

    public static void releaseByOrder(long orderId) {
        if (!enabled || orderId <= 0) return;
        if (!ready()) return;
        try {
            mapper().releaseByOrder(orderId);
        } catch (Exception ignored) {
        }
    }
}
