package com.thesis.service;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.ESignMapper;

import java.util.*;

/** 本地签章（C-18）MyBatis 叠层。 */
public class ESignStore {

    private static boolean enabled;
    private static Boolean tableReady;

    private ESignStore() {}

    private static ESignMapper mapper() {
        return MybatisSupport.mapper(ESignMapper.class);
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
        if (!ready()) throw new IllegalStateException("签章功能暂不可用");
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        String t = s.trim();
        return t.length() <= max ? t : t.substring(0, max);
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static boolean asBool(Object o) {
        if (o instanceof Boolean b) return b;
        if (o instanceof Number n) return n.intValue() != 0;
        String s = str(o).toLowerCase(Locale.ROOT);
        return "1".equals(s) || "true".equals(s) || "yes".equals(s) || "on".equals(s);
    }

    private static Map<String, Object> pageOut(List<?> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> pageMine(String username, int page, int size) {
        require();
        String u = clip(username, 64);
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        Integer total = mapper().countMine(u);
        List<Map<String, Object>> list = mapper().pageMine(u, size, (page - 1) * size);
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> pageAdmin(int page, int size, String username) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        String u = clip(username, 64);
        if (!u.isBlank()) {
            return pageMine(u, page, size);
        }
        Integer total = mapper().countAll();
        List<Map<String, Object>> list = mapper().pageAll(size, (page - 1) * size);
        return pageOut(list, total, page, size);
    }

    public static Map<String, Object> submit(
            String username, String title, String signImageUrl, boolean agreed, Long ticketId, String remark) {
        require();
        String u = clip(username, 64);
        if (u.isBlank()) throw new IllegalArgumentException("用户无效");
        String t = clip(title, 200);
        if (t.isBlank()) throw new IllegalArgumentException("请填写签署标题");
        String img = clip(signImageUrl, 255);
        if (img.isBlank()) throw new IllegalArgumentException("请上传签章图");
        if (!agreed) throw new IllegalArgumentException("请勾选同意签署");
        String note = clip(remark, 255);
        Long tid = ticketId != null && ticketId > 0 ? ticketId : null;

        Map<String, Object> row = new LinkedHashMap<>();
        row.put("username", u);
        row.put("title", t);
        row.put("ticketId", tid);
        row.put("signImageUrl", img);
        row.put("remark", note);
        mapper().insert(row);
        Object idObj = row.get("id");
        long id = idObj instanceof Number num ? num.longValue() : 0L;
        Map<String, Object> out = mapper().getById(id);
        return out == null ? Map.of() : out;
    }

    public static Map<String, Object> submitFromBody(String username, Map<String, Object> body) {
        Map<String, Object> b = body == null ? Map.of() : body;
        Long ticketId = null;
        Object raw = b.get("ticketId");
        if (raw instanceof Number n) ticketId = n.longValue();
        else if (raw != null && !String.valueOf(raw).isBlank()) {
            ticketId = Long.parseLong(String.valueOf(raw).trim());
        }
        return submit(
                username,
                str(b.get("title")),
                str(b.get("signImageUrl")).isBlank() ? str(b.get("imageUrl")) : str(b.get("signImageUrl")),
                asBool(b.get("agreed")),
                ticketId,
                str(b.get("remark")));
    }
}
