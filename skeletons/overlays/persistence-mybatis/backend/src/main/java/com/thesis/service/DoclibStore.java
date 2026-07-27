package com.thesis.service;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.DoclibMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

public class DoclibStore {
    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final Set<String> ACCESS = Set.of("public", "login", "staff");
    private static boolean enabled;
    private static Boolean tableReady;

    private DoclibStore() {}
    private static DoclibMapper mapper() { return MybatisSupport.mapper(DoclibMapper.class); }

    public static void configure(boolean on) { enabled = on; tableReady = null; }
    public static boolean enabled() { return enabled; }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = mapper().countTable();
            tableReady = n != null && n > 0;
        } catch (Exception e) { tableReady = false; }
        return tableReady;
    }

    private static void require() { if (!ready()) throw new IllegalStateException("文库功能暂不可用"); }
    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        if (o instanceof java.util.Date d) return new Timestamp(d.getTime()).toLocalDateTime().format(FMT);
        String s = String.valueOf(o); return s.isBlank() ? null : s;
    }
    private static String clip(String s, int max) {
        if (s == null) return "";
        String t = s.trim(); return t.length() <= max ? t : t.substring(0, max);
    }
    private static String str(Object o) { return o == null ? "" : String.valueOf(o).trim(); }
    private static Map<String, Object> pageOut(List<?> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list); out.put("total", total == null ? 0 : total);
        out.put("page", page); out.put("size", size); return out;
    }
    private static void normalize(List<Map<String, Object>> rows, String... keys) {
        for (Map<String, Object> m : rows) {
            for (String k : keys) if (m.containsKey(k)) m.put(k, fmt(m.get(k)));
        }
    }

    public static List<Map<String, Object>> listOpenItems(boolean admin) {
        require();
        List<Map<String, Object>> list = admin ? mapper().listOpenAdmin() : mapper().listOpenUser();
        normalize(list, "createdAt");
        return list;
    }
    public static Map<String, Object> getItem(long id) {
        require();
        Map<String, Object> m = mapper().getItem(id);
        if (m != null && m.containsKey("createdAt")) m.put("createdAt", fmt(m.get("createdAt")));
        return m;
    }
    private static void assertAccess(Map<String, Object> item, boolean admin) {
        String level = str(item.get("accessLevel")).toLowerCase(Locale.ROOT);
        if (level.isBlank()) level = "login";
        if ("staff".equals(level) && !admin) throw new IllegalStateException("该资料仅管理人员可下载");
        if (!"available".equals(str(item.get("status")))) throw new IllegalStateException("资料未开放");
    }
    public static Map<String, Object> download(String username, long id, boolean admin) {
        require();
        Map<String, Object> item = getItem(id);
        if (item == null) throw new IllegalArgumentException("资料不存在");
        assertAccess(item, admin);
        String url = str(item.get("fileUrl"));
        if (url.isBlank()) throw new IllegalStateException("未配置附件地址");
        mapper().insertLog(id, username);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("itemId", id); out.put("title", item.get("title"));
        out.put("url", url); out.put("accessLevel", item.get("accessLevel"));
        return out;
    }
    public static Map<String, Object> pageMine(String username, int page, int size) {
        require();
        int p = Math.max(1, page); int s = Math.min(100, Math.max(1, size));
        Integer total = mapper().countMine(username);
        List<Map<String, Object>> list = mapper().pageMine(username, s, (p - 1) * s);
        normalize(list, "downloadedAt");
        return pageOut(list, total, p, s);
    }
    public static Map<String, Object> pageLogsAdmin(int page, int size, Long itemId) {
        require();
        int p = Math.max(1, page); int s = Math.min(100, Math.max(1, size));
        if (itemId != null) {
            Integer total = mapper().countLogsByItem(itemId);
            List<Map<String, Object>> list = mapper().pageLogsByItem(itemId, s, (p - 1) * s);
            normalize(list, "downloadedAt");
            return pageOut(list, total, p, s);
        }
        Integer total = mapper().countLogs();
        List<Map<String, Object>> list = mapper().pageLogs(s, (p - 1) * s);
        normalize(list, "downloadedAt");
        return pageOut(list, total, p, s);
    }
    public static Map<String, Object> updateMeta(long id, Map<String, Object> body) {
        require();
        Map<String, Object> item = getItem(id);
        if (item == null) throw new IllegalArgumentException("资料不存在");
        String fileUrl = clip(str(body.get("fileUrl")), 255);
        String access = clip(str(body.get("accessLevel")), 16).toLowerCase(Locale.ROOT);
        if (access.isBlank()) access = "login";
        if (!ACCESS.contains(access)) throw new IllegalArgumentException("权限须为 public/login/staff");
        mapper().updateMeta(id, fileUrl, access);
        item.put("fileUrl", fileUrl); item.put("accessLevel", access);
        return item;
    }
}
