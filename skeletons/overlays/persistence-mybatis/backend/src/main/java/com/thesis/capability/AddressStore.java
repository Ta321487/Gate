package com.thesis.capability;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.AddressMapper;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 收货地址簿：商城 / 点餐 / 交易壳共用。
 */
public final class AddressStore {

    private static Boolean tableReady;

    private AddressStore() {}

    private static AddressMapper mapper() {
        return MybatisSupport.mapper(AddressMapper.class);
    }

    public static boolean available() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = mapper().countTable();
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    public static void resetCache() {
        tableReady = null;
    }

    private static Map<String, Object> shape(Map<String, Object> raw) {
        if (raw == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", raw.get("id"));
        m.put("username", raw.get("username"));
        m.put("contactName", raw.get("contactName"));
        m.put("phone", raw.get("phone"));
        m.put("addressLine", raw.get("addressLine"));
        m.put("tag", raw.get("tag"));
        Object def = raw.get("isDefault");
        if (def == null) def = raw.get("is_default");
        m.put("isDefault", def instanceof Number n ? n.intValue() == 1 : Boolean.TRUE.equals(def));
        return m;
    }

    public static List<Map<String, Object>> list(String username) {
        if (!available()) return List.of();
        List<Map<String, Object>> raw = mapper().selectByUsername(username);
        List<Map<String, Object>> out = new ArrayList<>();
        if (raw != null) {
            for (Map<String, Object> r : raw) {
                out.add(shape(r));
            }
        }
        return out;
    }

    public static Map<String, Object> get(long id, String username) {
        if (!available() || id <= 0) return null;
        return shape(mapper().selectById(id, username));
    }

    public static Map<String, Object> create(
            String username, String contactName, String phone, String addressLine, String tag, boolean asDefault) {
        requireTable();
        String name = nz(contactName);
        String ph = nz(phone);
        String addr = nz(addressLine);
        if (name.isBlank() || ph.isBlank() || addr.isBlank()) {
            throw new IllegalArgumentException("请填写联系人、手机与详细地址");
        }
        if (findDuplicate(username, name, ph, addr, 0) != null) {
            throw new IllegalArgumentException("地址簿中已有相同收货信息（联系人、手机与地址一致）");
        }
        String tg = tag == null || tag.isBlank() ? "默认" : tag.trim();
        if (asDefault) clearDefault(username);
        else if (list(username).isEmpty()) asDefault = true;
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("username", username);
        row.put("contactName", name);
        row.put("phone", ph);
        row.put("addressLine", addr);
        row.put("tag", tg);
        row.put("isDefault", asDefault ? 1 : 0);
        mapper().insert(row);
        long id = row.get("id") == null ? 0L : ((Number) row.get("id")).longValue();
        return get(id, username);
    }

    public static Map<String, Object> update(
            long id, String username, String contactName, String phone, String addressLine, String tag, Boolean asDefault) {
        requireTable();
        Map<String, Object> cur = get(id, username);
        if (cur == null) throw new IllegalArgumentException("地址不存在");
        String name = contactName != null ? contactName.trim() : String.valueOf(cur.get("contactName"));
        String ph = phone != null ? phone.trim() : String.valueOf(cur.get("phone"));
        String addr = addressLine != null ? addressLine.trim() : String.valueOf(cur.get("addressLine"));
        String tg = tag != null ? (tag.isBlank() ? "默认" : tag.trim()) : String.valueOf(cur.get("tag"));
        if (name.isBlank() || ph.isBlank() || addr.isBlank()) {
            throw new IllegalArgumentException("请填写联系人、手机与详细地址");
        }
        if (findDuplicate(username, name, ph, addr, id) != null) {
            throw new IllegalArgumentException("地址簿中已有相同收货信息（联系人、手机与地址一致）");
        }
        boolean def = asDefault == null ? Boolean.TRUE.equals(cur.get("isDefault")) : asDefault;
        if (def) clearDefault(username);
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", id);
        row.put("username", username);
        row.put("contactName", name);
        row.put("phone", ph);
        row.put("addressLine", addr);
        row.put("tag", tg);
        row.put("isDefault", def ? 1 : 0);
        mapper().update(row);
        return get(id, username);
    }

    public static boolean delete(long id, String username) {
        requireTable();
        return mapper().delete(id, username) > 0;
    }

    /** 同用户下联系人+手机+详细地址完全一致视为重复（标签不同也算重复）。 */
    private static Map<String, Object> findDuplicate(
            String username, String contactName, String phone, String addressLine, long excludeId) {
        for (Map<String, Object> row : list(username)) {
            long rid = row.get("id") instanceof Number n ? n.longValue() : 0L;
            if (excludeId > 0 && rid == excludeId) continue;
            if (contactName.equals(nz(String.valueOf(row.get("contactName"))))
                    && phone.equals(nz(String.valueOf(row.get("phone"))))
                    && addressLine.equals(nz(String.valueOf(row.get("addressLine"))))) {
                return row;
            }
        }
        return null;
    }

    private static void clearDefault(String username) {
        mapper().clearDefault(username);
    }

    private static void requireTable() {
        if (!available()) throw new IllegalStateException("收货地址功能暂不可用");
    }

    private static String nz(String s) {
        return s == null ? "" : s.trim();
    }
}
