package com.thesis.capability;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.Map;

/**
 * ArchivePriceOps：标价 / 限时价 / 规格文案 / 库存不足提示（零业务 SQL 正文）。
 * package-private；ArchiveStore 保留 public 门面。
 */
final class ArchivePriceOps {

    private ArchivePriceOps() {}

    /** null=非空但无法解析；0=空/缺省。 */
    static Double tryParseMoney(Object raw) {
        if (raw == null) return 0.0;
        String s = String.valueOf(raw).replace("¥", "").replace("￥", "").trim();
        if (s.isBlank()) return 0.0;
        try {
            return Double.parseDouble(s);
        } catch (Exception e) {
            return null;
        }
    }

    /** 写库/成交：非空且不可解析则硬失败；空或显式 0 允许。 */
    static double parseMoney(Object raw) {
        Double v = tryParseMoney(raw);
        if (v == null) {
            throw new IllegalArgumentException("价格无效，请填写数字金额");
        }
        return v;
    }

    /** 列表展示：脏价格当 0，不抛错。 */
    static double parseMoneySoft(Object raw) {
        Double v = tryParseMoney(raw);
        return v == null ? 0 : v;
    }

    static double listUnitPrice(Map<String, Object> item, boolean strict) {
        if (item == null) return 0;
        Double v = tryParseMoney(item.get("author"));
        if (v == null) {
            if (strict) throw new IllegalArgumentException("价格无效，请填写数字金额");
            v = 0.0;
        }
        if (v > 0) return v;
        Double list = tryParseMoney(item.get("listPriceYuan"));
        if (list == null) {
            if (strict) throw new IllegalArgumentException("价格无效，请填写数字金额");
            return 0;
        }
        return list;
    }

    static double effectiveUnitPrice(Map<String, Object> item) {
        double list = listUnitPrice(item, true);
        if (!ArchiveStore.flashPriceEnabled || item == null) return list;
        if (!isPromoActive(item)) return list;
        double promo = parseMoney(item.get("promoPrice"));
        return promo > 0 ? promo : list;
    }

    static boolean isPromoActive(Map<String, Object> item) {
        if (!ArchiveStore.flashPriceEnabled || item == null) return false;
        double promo = parseMoneySoft(item.get("promoPrice"));
        if (promo <= 0) return false;
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime start = parseLocalDateTime(item.get("promoStart"));
        LocalDateTime end = parseLocalDateTime(item.get("promoEnd"));
        if (start != null && now.isBefore(start)) return false;
        if (end != null && now.isAfter(end)) return false;
        return true;
    }

    static LocalDateTime parseLocalDateTime(Object raw) {
        if (raw == null) return null;
        if (raw instanceof LocalDateTime ldt) return ldt;
        if (raw instanceof Timestamp ts) return ts.toLocalDateTime();
        String s = String.valueOf(raw).trim();
        if (s.isBlank() || "null".equalsIgnoreCase(s)) return null;
        try {
            if (s.length() == 10) return LocalDateTime.parse(s + "T00:00:00");
            return LocalDateTime.parse(s.replace(" ", "T"));
        } catch (Exception e) {
            try {
                return Timestamp.valueOf(s.length() == 16 ? s + ":00" : s).toLocalDateTime();
            } catch (Exception ignored) {
                return null;
            }
        }
    }

    static String productSpecText(Map<String, Object> item) {
        if (!ArchiveStore.productSpecEnabled || item == null) return "";
        if (ArchiveStore.usesDedicatedSpecNote()) {
            return ArchiveStore.str(item.get("specNote")).trim();
        }
        return ArchiveStore.str(item.get("isbn")).trim();
    }

    static String lineTitleWithSpec(Map<String, Object> item) {
        String title = item == null ? "" : ArchiveStore.str(item.get("title")).trim();
        if (title.isBlank()) title = "";
        String spec = productSpecText(item);
        if (spec.isBlank()) return title;
        if (title.contains(spec)) return title;
        String combined = title.isBlank() ? spec : (title + "（" + spec + "）");
        if (combined.length() > 200) combined = combined.substring(0, 200);
        return combined;
    }

    static String stockLabel() {
        return ArchiveStore.STOCK_LABEL == null || ArchiveStore.STOCK_LABEL.isBlank()
                ? "库存"
                : ArchiveStore.STOCK_LABEL;
    }

    static String stockShortage(int remain) {
        return stockLabel() + "不足（剩余 " + remain + "）";
    }

    static String stockShortageNeed(int need) {
        return stockLabel() + "不足，无法通过（需要 " + need + "）";
    }

    static String stockShortageTitled(String title, int remain) {
        String t = title == null ? "" : title.trim();
        if (t.isBlank()) return stockShortage(remain);
        return stockLabel() + "不足：「" + t + "」仅剩 " + remain;
    }
}
