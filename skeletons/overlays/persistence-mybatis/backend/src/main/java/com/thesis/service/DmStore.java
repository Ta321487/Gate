package com.thesis.service;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.DmMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 站内一对一会话（sys_dm_message，MyBatis）。
 * 前端定时拉取；不做第三方 IM。
 * 店铺客服开启时：买家只联系入驻商家，商家只回复买家。
 */
public class DmStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int BODY_MAX = 500;
    private static Boolean tableReady;
    private static boolean shopCustomerService = false;

    private static DmMapper mapper() {
        return MybatisSupport.mapper(DmMapper.class);
    }

    public static void configureShopCustomerService(boolean enabled) {
        shopCustomerService = enabled;
    }

    public static boolean shopCustomerService() {
        return shopCustomerService;
    }

    private static boolean isMerchant(UserStore.Profile p) {
        if (p == null || p.superAdmin) return false;
        if (!"admin".equals(p.role)) return false;
        String post = p.staffPost == null ? "" : p.staffPost.trim();
        return "shop_merchant".equals(post);
    }

    private static boolean isBuyer(UserStore.Profile p) {
        if (p == null || p.superAdmin) return false;
        return !"admin".equals(p.role);
    }

    public static boolean canMessage(String from, String to) {
        if (from == null || to == null) return false;
        String f = from.trim();
        String t = to.trim();
        if (f.isBlank() || t.isBlank() || f.equals(t)) return false;
        if (!shopCustomerService) return true;
        UserStore.Profile a = UserStore.get(f);
        UserStore.Profile b = UserStore.get(t);
        if (a == null || b == null || !b.enabled) return false;
        if (a.superAdmin || b.superAdmin) return true;
        if (isBuyer(a) && isMerchant(b)) return true;
        if (isMerchant(a) && isBuyer(b)) return true;
        return false;
    }

    public static boolean ready() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = mapper().countTable();
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return s.isBlank() ? null : s;
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        String t = s.trim();
        return t.length() <= max ? t : t.substring(0, max);
    }

    private static Map<String, Object> shape(Map<String, Object> raw) {
        if (raw == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", raw.get("id"));
        m.put("fromUsername", raw.get("fromUsername") != null ? raw.get("fromUsername") : raw.get("from_username"));
        m.put("toUsername", raw.get("toUsername") != null ? raw.get("toUsername") : raw.get("to_username"));
        m.put("body", raw.get("body"));
        Object readAt = raw.get("readAt") != null ? raw.get("readAt") : raw.get("read_at");
        Object createdAt = raw.get("createdAt") != null ? raw.get("createdAt") : raw.get("created_at");
        m.put("readAt", fmt(readAt));
        m.put("createdAt", fmt(createdAt));
        m.put("read", readAt != null);
        return m;
    }

    public static Map<String, Object> get(long id) {
        if (!ready()) return null;
        return shape(mapper().selectById(id));
    }

    public static List<Map<String, Object>> peers(String me, int limit) {
        if (!ready() || me == null || me.isBlank()) return List.of();
        int lim = limit < 1 ? 50 : Math.min(limit, 100);
        String u = me.trim();
        if (!shopCustomerService) {
            return mapper().selectPeers(u, lim);
        }
        UserStore.Profile self = UserStore.get(u);
        if (self == null) return List.of();
        if (self.superAdmin) {
            return mapper().selectPeers(u, lim);
        }
        if (isMerchant(self)) {
            return mapper().selectBuyerPeers(u, lim);
        }
        return mapper().selectMerchantPeers(u, lim);
    }

    public static List<Map<String, Object>> conversations(String me) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (!ready() || me == null || me.isBlank()) return out;
        String u = me.trim();
        List<Map<String, Object>> peers = mapper().selectConversationPeers(u);
        for (Map<String, Object> p : peers) {
            String peer = String.valueOf(p.get("peer"));
            Object lastIdObj = p.get("lastId") != null ? p.get("lastId") : p.get("last_id");
            long lastId = lastIdObj == null ? 0L : ((Number) lastIdObj).longValue();
            Map<String, Object> last = get(lastId);
            Integer unread = mapper().unreadWithPeer(u, peer);
            String nick = null;
            try {
                nick = mapper().nicknameOf(peer);
            } catch (Exception ignored) {
            }
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("peer", peer);
            row.put("peerNickname", nick == null || nick.isBlank() ? peer : nick);
            row.put("unread", unread == null ? 0 : unread);
            row.put("lastMessage", last);
            out.add(row);
        }
        return out;
    }

    public static List<Map<String, Object>> messages(String me, String peer, long sinceId) {
        if (!ready() || me == null || peer == null) return List.of();
        String u = me.trim();
        String p = peer.trim();
        if (u.isBlank() || p.isBlank()) return List.of();
        List<Map<String, Object>> raw = mapper().selectMessages(u, p, Math.max(0L, sinceId));
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> r : raw) {
            out.add(shape(r));
        }
        return out;
    }

    public static Map<String, Object> send(String from, String to, String body) {
        if (!ready()) return null;
        String f = from == null ? "" : from.trim();
        String t = to == null ? "" : to.trim();
        String b = clip(body, BODY_MAX);
        if (f.isBlank() || t.isBlank() || b.isBlank() || f.equals(t)) return null;
        Integer exists = mapper().userEnabled(t);
        if (exists == null || exists == 0) return null;
        if (!canMessage(f, t)) return null;
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("fromUsername", f);
        row.put("toUsername", t);
        row.put("body", b);
        mapper().insert(row);
        Object id = row.get("id");
        return get(id == null ? 0L : ((Number) id).longValue());
    }

    public static int markRead(String me, String peer) {
        if (!ready() || me == null || peer == null) return 0;
        return mapper().markRead(me.trim(), peer.trim(), Timestamp.valueOf(LocalDateTime.now()));
    }

    public static int unreadCount(String me) {
        if (!ready() || me == null || me.isBlank()) return 0;
        Integer n = mapper().unreadCount(me.trim());
        return n == null ? 0 : n;
    }
}
