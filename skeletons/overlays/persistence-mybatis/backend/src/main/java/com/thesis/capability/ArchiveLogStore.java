package com.thesis.capability;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.ArchiveLogMapper;

import java.sql.Date;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 能力 archive_log：挂档案的打卡/随访/评估记录。 */
public final class ArchiveLogStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final DateTimeFormatter DAY = DateTimeFormatter.ofPattern("yyyy-MM-dd");
    private static final ObjectMapper JSON = new ObjectMapper();
    private static boolean enabled = false;

    private ArchiveLogStore() {}

    private static ArchiveLogMapper mapper() {
        return MybatisSupport.mapper(ArchiveLogMapper.class);
    }

    public static void configure(boolean on) {
        enabled = on;
        if (enabled) {
            try {
                mapper().ensureTable();
            } catch (Exception ignored) {
            }
        }
    }

    public static boolean enabled() {
        return enabled;
    }

    public static Map<String, Object> submit(
            String username,
            long itemId,
            String logType,
            LocalDate logDate,
            Map<String, Object> payload,
            boolean abnormal,
            String remark) {
        require();
        if (username == null || username.isBlank()) {
            throw new IllegalArgumentException("未登录");
        }
        if (itemId <= 0 || ArchiveStore.getItemRaw(itemId) == null) {
            throw new IllegalArgumentException("档案不存在");
        }
        String type = (logType == null || logType.isBlank()) ? "checkin" : logType.trim();
        LocalDate day = logDate == null ? LocalDate.now() : logDate;
        String payloadJson = "{}";
        try {
            payloadJson = JSON.writeValueAsString(payload == null ? Map.of() : payload);
        } catch (Exception ignored) {
        }
        String rem = remark == null ? "" : remark.trim();
        if (rem.length() > 500) rem = rem.substring(0, 500);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("itemId", itemId);
        row.put("username", username);
        row.put("logDate", Date.valueOf(day));
        row.put("logType", type);
        row.put("payloadJson", payloadJson);
        row.put("abnormal", abnormal ? 1 : 0);
        row.put("remark", rem);
        mapper().insert(row);
        long id = row.get("id") == null ? 0L : ((Number) row.get("id")).longValue();
        return get(id);
    }

    public static Map<String, Object> get(long id) {
        require();
        return shape(mapper().selectById(id));
    }

    public static Map<String, Object> pageByItem(long itemId, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectByItemId(itemId);
        return pageOut(shapeList(raw), new PageInfo<>(raw).getTotal(), page, size);
    }

    public static Map<String, Object> pageAdmin(
            Long itemId, String logType, LocalDate day, Boolean abnormalOnly, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectAdmin(
                itemId,
                logType == null || logType.isBlank() ? null : logType.trim(),
                day == null ? null : Date.valueOf(day),
                abnormalOnly);
        List<Map<String, Object>> rows = shapeList(raw);
        for (Map<String, Object> m : rows) {
            attachItemTitle(m);
        }
        return pageOut(rows, new PageInfo<>(raw).getTotal(), page, size);
    }

    public static List<Map<String, Object>> missingToday(String logType) {
        require();
        String type = (logType == null || logType.isBlank()) ? "checkin" : logType.trim();
        String item = ArchiveStore.itemTable();
        List<Map<String, Object>> rows = mapper().selectMissingToday(
                item,
                ArchiveStore.softDeleteEnabled(),
                Date.valueOf(LocalDate.now()),
                type);
        return rows == null ? List.of() : rows;
    }

    public static int countMissingToday(String logType) {
        if (!enabled) return 0;
        try {
            return missingToday(logType).size();
        } catch (Exception e) {
            return 0;
        }
    }

    private static Map<String, Object> pageOut(List<Map<String, Object>> rows, long total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", rows == null ? List.of() : rows);
        out.put("total", total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static void attachItemTitle(Map<String, Object> m) {
        Object idObj = m.get("itemId");
        if (!(idObj instanceof Number n)) return;
        Map<String, Object> item = ArchiveStore.getItemRaw(n.longValue());
        if (item != null) {
            m.put("itemTitle", item.get("title"));
        }
    }

    private static List<Map<String, Object>> shapeList(List<Map<String, Object>> raw) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (raw == null) return out;
        for (Map<String, Object> r : raw) {
            Map<String, Object> s = shape(r);
            if (s != null) out.add(s);
        }
        return out;
    }

    private static Map<String, Object> shape(Map<String, Object> raw) {
        if (raw == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", raw.get("id"));
        m.put("itemId", raw.get("itemId"));
        m.put("username", raw.get("username"));
        Object d = raw.get("logDate");
        if (d instanceof Date sqlDate) {
            m.put("logDate", sqlDate.toLocalDate().format(DAY));
        } else if (d instanceof LocalDate ld) {
            m.put("logDate", ld.format(DAY));
        } else {
            m.put("logDate", d == null ? null : String.valueOf(d));
        }
        m.put("logType", raw.get("logType"));
        String payload = raw.get("payloadJson") == null ? "{}" : String.valueOf(raw.get("payloadJson"));
        m.put("payloadJson", payload);
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> parsed =
                    payload.isBlank() ? Map.of() : JSON.readValue(payload, Map.class);
            m.put("payload", parsed);
        } catch (Exception e) {
            m.put("payload", Map.of());
        }
        Object ab = raw.get("abnormal");
        m.put("abnormal", ab instanceof Number n ? n.intValue() == 1 : Boolean.TRUE.equals(ab));
        Object rem = raw.get("remark");
        m.put("remark", rem == null ? "" : String.valueOf(rem));
        m.put("createdAt", fmt(raw.get("createdAt")));
        return m;
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    private static void require() {
        if (!enabled) throw new IllegalStateException("监测记录暂不可用");
    }
}
