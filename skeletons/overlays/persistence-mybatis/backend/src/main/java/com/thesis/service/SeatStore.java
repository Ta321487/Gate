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

/** 影院选座（C-15）MyBatis 叠层。 */
public class SeatStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int DEFAULT_ROWS = 6;
    private static final int DEFAULT_COLS = 8;
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

    private static void ensureSeatMap(long showId) {
        Integer n = mapper().countSeats(showId);
        if (n != null && n > 0) return;
        for (int r = 0; r < DEFAULT_ROWS; r++) {
            for (int c = 0; c < DEFAULT_COLS; c++) {
                mapper().insertSeat(showId, seatCode(r, c));
            }
        }
    }

    public static List<Map<String, Object>> listOpenShows() {
        require();
        return mapper().listOpenShows();
    }

    public static Map<String, Object> getShow(long id) {
        require();
        return mapper().getShow(id);
    }

    public static Map<String, Object> getMap(long showId) {
        require();
        Map<String, Object> show = getShow(showId);
        if (show == null) throw new IllegalArgumentException("场次不存在");
        ensureSeatMap(showId);
        List<Map<String, Object>> seats = mapper().listSeats(showId);
        for (Map<String, Object> s : seats) {
            if (s.containsKey("soldAt")) s.put("soldAt", fmt(s.get("soldAt")));
        }
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
}
