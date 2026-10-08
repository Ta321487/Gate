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
    private static Boolean holdColReady;
    private static Boolean seatAttrColReady;
    private static Boolean snackTableReady;
    private static int holdTimeoutMinutes = 10;
    private static int ticketRefundCutoffMinutes = 30;

    private SeatStore() {}

    private static SeatMapper mapper() {
        return MybatisSupport.mapper(SeatMapper.class);
    }

    public static void configure(boolean on) {
        enabled = on;
        tableReady = null;
        holdColReady = null;
        seatAttrColReady = null;
        snackTableReady = null;
    }

    public static void configureHoldTimeoutMinutes(int minutes) {
        holdTimeoutMinutes = Math.max(0, minutes);
    }

    public static void configureTicketRefundCutoffMinutes(int minutes) {
        ticketRefundCutoffMinutes = Math.max(0, minutes);
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

    private static void enrichShowCategory(Map<String, Object> show) {
        if (show == null) return;
        Object cid = show.get("categoryId");
        if (!(cid instanceof Number n) || n.longValue() <= 0) {
            show.putIfAbsent("categoryName", "");
            return;
        }
        try {
            String name = mapper().getCategoryName(n.longValue());
            show.put("categoryName", name == null ? "" : name);
        } catch (Exception e) {
            show.putIfAbsent("categoryName", "");
        }
    }

    private static String normalizeSeatAttr(String raw) {
        String a = raw == null ? "" : raw.trim().toLowerCase(Locale.ROOT);
        if ("couple".equals(a) || "accessible".equals(a)) return a;
        return "";
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
        Integer sold = mapper().countBusy(showId);
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
        if (!ready()) {
            throw new IllegalStateException("选座功能暂不可用，无法同步布局");
        }
        try {
            Map<String, Object> show = getShow(showId);
            if (show == null) {
                throw new IllegalStateException("场次不存在，无法同步选座布局");
            }
            ensureSeatMap(showId, show);
            syncShowSaleStatus(showId);
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("同步选座布局失败", e);
        }
    }

    public static int expirePastShows() {
        if (!enabled) return 0;
        if (!ready()) return 0;
        try {
            return mapper().expirePastShows();
        } catch (Exception e) {
            return 0;
        }
    }

    private static boolean holdColReady() {
        if (!ready()) return false;
        if (holdColReady != null) return holdColReady;
        try {
            Integer n = mapper().countHoldColumn();
            holdColReady = n != null && n > 0;
        } catch (Exception e) {
            holdColReady = false;
        }
        return holdColReady;
    }

    private static boolean seatAttrColReady() {
        if (!ready()) return false;
        if (seatAttrColReady != null) return seatAttrColReady;
        try {
            Integer n = mapper().countSeatAttrColumn();
            seatAttrColReady = n != null && n > 0;
        } catch (Exception e) {
            seatAttrColReady = false;
        }
        return seatAttrColReady;
    }

    public static void updateSeatAttrs(long showId, Map<String, String> attrs) {
        require();
        if (!seatAttrColReady()) {
            throw new IllegalStateException("系统未配置座位属性");
        }
        if (showId <= 0) throw new IllegalArgumentException("场次无效");
        Map<String, Object> show = getShow(showId);
        if (show == null) throw new IllegalArgumentException("场次不存在");
        ensureSeatMap(showId, show);
        if (attrs == null || attrs.isEmpty()) return;
        for (Map.Entry<String, String> e : attrs.entrySet()) {
            String code = clip(e.getKey(), 16);
            if (code.isBlank()) continue;
            String attr = normalizeSeatAttr(e.getValue());
            mapper().updateSeatAttr(showId, code, attr);
        }
    }

    public static int releaseExpiredHolds() {
        if (!enabled || !ready() || !holdColReady()) return 0;
        try {
            return mapper().releaseExpiredHolds();
        } catch (Exception e) {
            return 0;
        }
    }

    public static int syncSoldOutShows() {
        if (!enabled || !ready()) return 0;
        int n = 0;
        try {
            n += mapper().markSoldOut();
            n += mapper().reopenSoldOut();
        } catch (Exception e) {
            return n;
        }
        return n;
    }

    public static void syncShowSaleStatus(long showId) {
        if (!enabled || !ready() || showId <= 0) return;
        try {
            mapper().markSoldOutOne(showId);
            mapper().reopenSoldOutOne(showId);
        } catch (Exception ignored) {
        }
    }

    public static void assertOrderRefundOpen(long orderId) {
        if (!enabled || ticketRefundCutoffMinutes <= 0 || orderId <= 0) return;
        if (!OrderStore.enabled()) return;
        Map<String, Object> order = OrderStore.getOrder(orderId);
        if (order == null) return;
        Object linesObj = order.get("lines");
        if (!(linesObj instanceof List<?> lines) || lines.isEmpty()) return;
        for (Object raw : lines) {
            if (!(raw instanceof Map<?, ?> line)) continue;
            Object iid = line.get("itemId");
            if (!(iid instanceof Number n)) continue;
            Map<String, Object> show = getShow(n.longValue());
            if (show == null) continue;
            if (isPastRefundCutoff(show)) {
                throw new IllegalStateException(
                        "开场前 " + ticketRefundCutoffMinutes + " 分钟内不可退票");
            }
        }
    }

    private static boolean isPastRefundCutoff(Map<String, Object> show) {
        if (ticketRefundCutoffMinutes <= 0) return false;
        LocalDateTime start = parseStart(str(show.get("startAt")));
        if (start == null) return false;
        return !LocalDateTime.now().isBefore(start.minusMinutes(ticketRefundCutoffMinutes));
    }

    private static LocalDateTime parseStart(String sa) {
        if (sa == null || sa.isBlank()) return null;
        try {
            String norm = sa.length() >= 19 ? sa.substring(0, 19) : sa;
            return LocalDateTime.parse(norm.replace(' ', 'T'));
        } catch (Exception e) {
            try {
                return LocalDateTime.parse(sa, FMT);
            } catch (Exception ignored) {
                return null;
            }
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
                return true;
            }
        }
    }

    public static List<Map<String, Object>> listOpenShows() {
        require();
        expirePastShows();
        releaseExpiredHolds();
        syncSoldOutShows();
        List<Map<String, Object>> list = mapper().listOpenShows();
        for (Map<String, Object> show : list) enrichShowCategory(show);
        return list;
    }

    public static Map<String, Object> getShow(long id) {
        require();
        Map<String, Object> show = mapper().getShow(id);
        if (show != null) enrichShowCategory(show);
        return show;
    }

    public static Map<String, Object> getMap(long showId) {
        return getMap(showId, null);
    }

    public static Map<String, Object> getMap(long showId, String username) {
        require();
        expirePastShows();
        releaseExpiredHolds();
        syncSoldOutShows();
        Map<String, Object> show = getShow(showId);
        if (show == null) throw new IllegalArgumentException("场次不存在");
        String st = str(show.get("status"));
        if ("sold_out".equals(st) || toInt(show.get("stock"), 0) <= 0) {
            throw new IllegalStateException("本场次已售罄");
        }
        if (!"available".equals(st) || isPastStart(show)) {
            throw new IllegalStateException("场次已开场或已下架，不可选座");
        }
        ensureSeatMap(showId, show);
        show = getShow(showId);
        int rows = rowsOf(show);
        int cols = colsOf(show);
        List<Map<String, Object>> seats = mapper().listSeats(showId);
        for (Map<String, Object> s : seats) {
            if (s.containsKey("soldAt")) s.put("soldAt", fmt(s.get("soldAt")));
            if (s.containsKey("holdUntil")) s.put("holdUntil", fmt(s.get("holdUntil")));
            Object attr = s.get("seatAttr");
            s.put("seatAttr", attr == null ? "" : String.valueOf(attr).trim());
        }
        return decorateMap(show, rows, cols, seats, username);
    }

    private static Map<String, Object> decorateMap(
            Map<String, Object> show,
            int rows,
            int cols,
            List<Map<String, Object>> seats,
            String username) {
        String uid = clip(username, 64);
        List<String> adjacent = new ArrayList<>();
        Set<String> open = new HashSet<>();
        String holdUntil = null;
        for (Map<String, Object> s : seats) {
            String code = str(s.get("seatCode"));
            String st = str(s.get("status"));
            boolean mine = "held".equals(st) && !uid.isBlank() && uid.equals(str(s.get("username")));
            s.put("mine", mine);
            if ("free".equals(st) || mine) open.add(code);
            if (mine) {
                String hu = str(s.get("holdUntil"));
                if (!hu.isBlank() && (holdUntil == null || hu.compareTo(holdUntil) < 0)) holdUntil = hu;
            }
        }
        for (String code : open) {
            String next = nextSeatCode(code);
            if (next != null && open.contains(next) && code.compareTo(next) < 0) {
                adjacent.add(code + "-" + next);
            }
        }
        Collections.sort(adjacent);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("show", show);
        out.put("rows", rows);
        out.put("cols", cols);
        out.put("seats", seats);
        out.put("freeCount", open.size());
        out.put("adjacentPairs", adjacent);
        out.put("adjacentHint", adjacent.isEmpty() ? "" : ("建议连坐：" + String.join("、",
                adjacent.subList(0, Math.min(6, adjacent.size())))));
        out.put("holdUntil", holdUntil);
        out.put("holdTimeoutMinutes", holdTimeoutMinutes);
        return out;
    }

    private static String nextSeatCode(String code) {
        if (code == null || code.length() < 2) return null;
        char row = code.charAt(0);
        try {
            int col = Integer.parseInt(code.substring(1));
            return row + String.valueOf(col + 1);
        } catch (Exception e) {
            return null;
        }
    }

    public static Map<String, Object> holdSeats(String username, long showId, List<String> seatCodes) {
        require();
        String u = clip(username, 64);
        if (u.isBlank()) throw new IllegalArgumentException("未登录");
        releaseExpiredHolds();
        Map<String, Object> show = getShow(showId);
        if (show == null || !"available".equals(str(show.get("status"))) || isPastStart(show)) {
            throw new IllegalStateException("场次已开场或已下架，不可选座");
        }
        ensureSeatMap(showId, show);
        List<String> codes = seatCodes == null ? List.of() : seatCodes.stream()
                .map(s -> clip(s, 16).toUpperCase(Locale.ROOT))
                .filter(s -> !s.isBlank())
                .distinct()
                .collect(Collectors.toList());
        if (codes.size() > 6) throw new IllegalArgumentException("单次最多选 6 个座位");
        if (!holdColReady() || holdTimeoutMinutes <= 0) {
            return getMap(showId, u);
        }
        Timestamp until = Timestamp.valueOf(LocalDateTime.now().plusMinutes(holdTimeoutMinutes));
        if (codes.isEmpty()) {
            mapper().releaseMineHolds(showId, u);
            return getMap(showId, u);
        }
        mapper().releaseMineHoldsExcept(showId, u, codes);
        for (String code : codes) {
            int n = mapper().holdSeat(showId, code, u, until);
            if (n == 0) throw new IllegalStateException("座位 " + code + " 不可选");
        }
        return getMap(showId, u);
    }

    private static double priceOf(Map<String, Object> show) {
        Object raw = show.get("author");
        if (raw == null) return 0;
        String s = String.valueOf(raw).replace("¥", "").replace("￥", "").trim();
        if (s.isBlank()) return 0;
        try {
            return Double.parseDouble(s);
        } catch (Exception e) {
            throw new IllegalArgumentException("票价无效，请填写数字金额");
        }
    }

    public static boolean snackReady() {
        if (!enabled) return false;
        if (snackTableReady != null) return snackTableReady;
        try {
            Integer n = mapper().countSnackTable();
            snackTableReady = n != null && n > 0;
        } catch (Exception e) {
            snackTableReady = false;
        }
        return snackTableReady;
    }

    public static List<Map<String, Object>> listOpenSnacks() {
        if (!snackReady()) return List.of();
        List<Map<String, Object>> list = mapper().listOpenSnacks();
        return list == null ? List.of() : list;
    }

    public static List<Map<String, Object>> listAllSnacks() {
        if (!snackReady()) return List.of();
        List<Map<String, Object>> list = mapper().listAllSnacks();
        return list == null ? List.of() : list;
    }

    public static Map<String, Object> getSnack(long id) {
        if (!snackReady() || id <= 0) return null;
        return mapper().getSnack(id);
    }

    public static Map<String, Object> saveSnack(Map<String, Object> body) {
        require();
        if (!snackReady()) throw new IllegalStateException("卖品功能暂不可用");
        long id = 0;
        Object rawId = body == null ? null : body.get("id");
        if (rawId instanceof Number n) id = n.longValue();
        else if (rawId != null && !String.valueOf(rawId).isBlank()) {
            id = Long.parseLong(String.valueOf(rawId).trim());
        }
        String title = clip(body == null ? null : String.valueOf(body.getOrDefault("title", "")), 80);
        if (title.isBlank()) throw new IllegalArgumentException("请填写卖品名称");
        double price = 0;
        Object pr = body == null ? null : body.get("priceYuan");
        if (pr == null && body != null) pr = body.get("price");
        if (pr instanceof Number n) price = n.doubleValue();
        else if (pr != null && !String.valueOf(pr).isBlank()) {
            price = Double.parseDouble(String.valueOf(pr).trim());
        }
        if (price < 0) throw new IllegalArgumentException("售价不能为负");
        int stock = 0;
        Object st = body == null ? null : body.get("stock");
        if (st instanceof Number n) stock = n.intValue();
        else if (st != null && !String.valueOf(st).isBlank()) {
            stock = Integer.parseInt(String.valueOf(st).trim());
        }
        if (stock < 0) throw new IllegalArgumentException("库存不能为负");
        String status = clip(body == null ? null : String.valueOf(body.getOrDefault("status", "on")), 16);
        if (!"on".equals(status) && !"off".equals(status)) status = "on";
        if (id > 0) {
            int n = mapper().updateSnack(id, title, price, stock, status);
            if (n == 0) throw new IllegalArgumentException("卖品不存在");
            return getSnack(id);
        }
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("title", title);
        row.put("priceYuan", price);
        row.put("stock", stock);
        row.put("status", status);
        mapper().insertSnack(row);
        Object nid = row.get("id");
        long newId = nid instanceof Number n ? n.longValue() : 0L;
        return getSnack(newId);
    }

    public static void adjustSnackStock(long snackId, int delta) {
        if (!snackReady() || snackId <= 0 || delta == 0) return;
        if (delta < 0) {
            int n = mapper().adjustSnackStockDown(snackId, delta, -delta);
            if (n == 0) throw new IllegalStateException("卖品暂时无货");
        } else {
            mapper().adjustSnackStockUp(snackId, delta);
        }
    }

    public static Map<String, Object> purchase(
            String username, long showId, List<String> seatCodes, boolean noticeAgreed) {
        return purchase(username, showId, seatCodes, noticeAgreed, null);
    }

    public static Map<String, Object> purchase(
            String username,
            long showId,
            List<String> seatCodes,
            boolean noticeAgreed,
            List<Map<String, Object>> snacks) {
        require();
        String u = clip(username, 64);
        if (u.isBlank()) throw new IllegalArgumentException("未登录");
        if (!noticeAgreed) throw new IllegalArgumentException("请先确认已阅读观影须知");
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

        releaseExpiredHolds();
        Map<String, Object> show = getShow(showId);
        if (show == null || "sold_out".equals(str(show.get("status"))) || toInt(show.get("stock"), 0) <= 0) {
            throw new IllegalStateException("本场次已售罄");
        }
        if (!"available".equals(str(show.get("status"))) || isPastStart(show)) {
            expirePastShows();
            throw new IllegalStateException("场次已开场或已下架，不可购票");
        }
        ensureSeatMap(showId, show);
        for (String code : codes) {
            Integer ok = mapper().countClaimableSeat(showId, code, u);
            if (ok == null || ok == 0) {
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
        OrderStore.ensurePickupCode(orderId);
        OrderStore.markNoticeAgreed(orderId);
        boolean stockAdjusted = false;
        try {
            if (snacks != null && !snacks.isEmpty()) {
                OrderStore.attachCinemaSnacks(orderId, snacks);
            }
            Timestamp now = Timestamp.valueOf(LocalDateTime.now());
            for (String code : codes) {
                int n = mapper().sellSeat(showId, code, u, orderId, now);
                if (n == 0) throw new IllegalStateException("座位 " + code + " 已被占用");
            }
            ArchiveStore.adjustStock(showId, -codes.size());
            stockAdjusted = true;
            syncShowSaleStatus(showId);
        } catch (RuntimeException ex) {
            rollbackFailedPurchase(orderId, showId, codes.size(), stockAdjusted);
            throw ex;
        }
        order = OrderStore.getOrder(orderId);
        if (order == null) throw new IllegalStateException("下单失败");
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("order", order);
        out.put("seats", codes);
        out.put("totalYuan", order.get("totalYuan"));
        return out;
    }

    private static void rollbackFailedPurchase(
            long orderId, long showId, int qty, boolean stockAdjusted) {
        RuntimeException first = null;
        try {
            releaseByOrder(orderId);
        } catch (RuntimeException e) {
            first = e;
        }
        if (stockAdjusted) {
            try {
                ArchiveStore.adjustStock(showId, qty);
            } catch (RuntimeException e) {
                if (first == null) first = e;
                else first.addSuppressed(e);
            }
        }
        try {
            OrderStore.abortPendingPurchase(orderId);
        } catch (RuntimeException e) {
            if (first == null) first = e;
            else first.addSuppressed(e);
        }
        if (first != null) throw first;
    }

    public static void releaseByOrder(long orderId) {
        if (!enabled || orderId <= 0) return;
        if (!ready()) return;
        try {
            mapper().releaseByOrder(orderId);
        } catch (Exception e) {
            throw new IllegalStateException("释放座位失败，请重试", e);
        }
    }
}
