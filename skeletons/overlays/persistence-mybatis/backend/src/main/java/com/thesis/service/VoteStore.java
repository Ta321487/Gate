package com.thesis.service;

import com.thesis.config.MybatisSupport;
import com.thesis.mapper.VoteMapper;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

public class VoteStore {
    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled;
    private static Boolean tableReady;

    private VoteStore() {}
    private static VoteMapper mapper() { return MybatisSupport.mapper(VoteMapper.class); }

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

    private static void require() { if (!ready()) throw new IllegalStateException("投票功能暂不可用"); }
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
    private static Long toLong(Object o) {
        if (o == null || String.valueOf(o).isBlank()) return null;
        return Long.parseLong(String.valueOf(o));
    }
    private static int toInt(Object o, int def) {
        if (o == null || String.valueOf(o).isBlank()) return def;
        return Integer.parseInt(String.valueOf(o));
    }
    private static Map<String, Object> pageOut(List<?> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list); out.put("total", total == null ? 0 : total);
        out.put("page", page); out.put("size", size); return out;
    }
    private static void normalizeTimes(List<Map<String, Object>> rows, String... keys) {
        for (Map<String, Object> m : rows) {
            for (String k : keys) if (m.containsKey(k)) m.put(k, fmt(m.get(k)));
        }
    }

    public static List<Map<String, Object>> listOpenCampaigns() {
        require();
        List<Map<String, Object>> list = mapper().listOpenCampaigns();
        normalizeTimes(list, "createdAt");
        return list;
    }
    public static Map<String, Object> getCampaign(long id) {
        require();
        Map<String, Object> m = mapper().getCampaign(id);
        if (m != null && m.containsKey("createdAt")) m.put("createdAt", fmt(m.get("createdAt")));
        return m;
    }
    public static List<Map<String, Object>> listCandidates(long campaignId) {
        require();
        List<Map<String, Object>> list = mapper().listCandidates(campaignId);
        normalizeTimes(list, "createdAt");
        return list;
    }
    public static Map<String, Object> pageCandidatesAdmin(long campaignId, int page, int size) {
        require();
        int p = Math.max(1, page); int s = Math.min(100, Math.max(1, size));
        Integer total = mapper().countCandidates(campaignId);
        List<Map<String, Object>> list = mapper().pageCandidates(campaignId, s, (p - 1) * s);
        normalizeTimes(list, "createdAt");
        return pageOut(list, total, p, s);
    }
    public static Map<String, Object> createCandidate(Map<String, Object> body) {
        require();
        Long campaignId = toLong(body.get("campaignId"));
        if (campaignId == null) throw new IllegalArgumentException("缺少评选活动");
        if (getCampaign(campaignId) == null) throw new IllegalArgumentException("评选活动不存在");
        String name = clip(str(body.get("name")), 128);
        if (name.isBlank()) throw new IllegalArgumentException("候选人姓名不能为空");
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("campaignId", campaignId);
        row.put("name", name);
        row.put("intro", clip(str(body.get("intro")), 1000));
        row.put("sortNo", toInt(body.get("sortNo"), 0));
        mapper().insertCandidate(row);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", row.get("id")); out.put("campaignId", campaignId); out.put("name", name);
        return out;
    }
    public static boolean deleteCandidate(long id) {
        require();
        Integer ballots = mapper().countBallotsByCandidate(id);
        if (ballots != null && ballots > 0) throw new IllegalStateException("已有选票，不能删除该候选人");
        return mapper().deleteCandidate(id) > 0;
    }
    public static Map<String, Object> cast(String username, long campaignId, List<Long> candidateIds) {
        require();
        Map<String, Object> camp = getCampaign(campaignId);
        if (camp == null || !"available".equals(str(camp.get("status")))) throw new IllegalStateException("评选未开放");
        int maxVotes = Math.max(1, toInt(camp.get("maxVotes"), 1));
        if (candidateIds == null || candidateIds.isEmpty()) throw new IllegalArgumentException("请选择候选人");
        LinkedHashSet<Long> uniq = new LinkedHashSet<>();
        for (Long id : candidateIds) if (id != null) uniq.add(id);
        if (uniq.isEmpty()) throw new IllegalArgumentException("请选择候选人");
        Integer used = mapper().countUserBallots(campaignId, username);
        int already = used == null ? 0 : used;
        if (already + uniq.size() > maxVotes) throw new IllegalStateException("超出限票数（每人最多 " + maxVotes + " 票）");
        for (Long cid : uniq) {
            Integer ok = mapper().countCandidateOk(cid, campaignId);
            if (ok == null || ok == 0) throw new IllegalArgumentException("候选人不存在或已停用");
            Integer dup = mapper().countDup(campaignId, username, cid);
            if (dup != null && dup > 0) throw new IllegalStateException("已投过该候选人");
            mapper().insertBallot(campaignId, username, cid);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("campaignId", campaignId); out.put("castCount", uniq.size());
        out.put("maxVotes", maxVotes); out.put("usedVotes", already + uniq.size());
        return out;
    }
    public static List<Map<String, Object>> results(long campaignId) { require(); return mapper().results(campaignId); }
    public static Map<String, Object> pageMine(String username, int page, int size) {
        require();
        int p = Math.max(1, page); int s = Math.min(100, Math.max(1, size));
        Integer total = mapper().countMine(username);
        List<Map<String, Object>> list = mapper().pageMine(username, s, (p - 1) * s);
        normalizeTimes(list, "createdAt");
        return pageOut(list, total, p, s);
    }
    public static Map<String, Object> pageBallotsAdmin(long campaignId, int page, int size) {
        require();
        int p = Math.max(1, page); int s = Math.min(100, Math.max(1, size));
        Integer total = mapper().countBallots(campaignId);
        List<Map<String, Object>> list = mapper().pageBallots(campaignId, s, (p - 1) * s);
        normalizeTimes(list, "createdAt");
        return pageOut(list, total, p, s);
    }
}
