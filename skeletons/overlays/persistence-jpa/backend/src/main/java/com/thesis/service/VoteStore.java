package com.thesis.service;

import com.thesis.config.JpaSupport;
import com.thesis.config.JpaDb;
import com.thesis.config.GeneratedKeyHolder;
import com.thesis.config.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 投票评选（C-04）：候选档案、一票/限票、结果公示。
 */
public class VoteStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static boolean enabled;
    private static Boolean tableReady;

    private VoteStore() {}

    public static void configure(boolean on) {
        enabled = on;
        tableReady = null;
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JpaDb db() {
        return JpaSupport.db();
    }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='vote_ballot'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("投票功能暂不可用");
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

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

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
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static List<Map<String, Object>> listOpenCampaigns() {
        require();
        return db().query(
                "SELECT id, title, author, isbn, category_id, stock, status, cover_url, created_at "
                        + "FROM vote_campaign WHERE status='available' ORDER BY id DESC",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("title", rs.getString("title"));
                    m.put("author", rs.getString("author"));
                    m.put("isbn", rs.getString("isbn"));
                    m.put("categoryId", rs.getObject("category_id"));
                    m.put("maxVotes", rs.getInt("stock"));
                    m.put("status", rs.getString("status"));
                    m.put("coverUrl", rs.getString("cover_url"));
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    return m;
                });
    }

    public static Map<String, Object> getCampaign(long id) {
        require();
        List<Map<String, Object>> rows = db().query(
                "SELECT id, title, author, isbn, category_id, stock, status, cover_url, created_at "
                        + "FROM vote_campaign WHERE id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("title", rs.getString("title"));
                    m.put("author", rs.getString("author"));
                    m.put("isbn", rs.getString("isbn"));
                    m.put("categoryId", rs.getObject("category_id"));
                    m.put("maxVotes", rs.getInt("stock"));
                    m.put("status", rs.getString("status"));
                    m.put("coverUrl", rs.getString("cover_url"));
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    return m;
                },
                id);
        return rows.isEmpty() ? null : rows.get(0);
    }

    public static List<Map<String, Object>> listCandidates(long campaignId) {
        require();
        return db().query(
                "SELECT id, campaign_id, name, intro, sort_no, status, created_at "
                        + "FROM vote_candidate WHERE campaign_id=? AND status='available' ORDER BY sort_no, id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("campaignId", rs.getLong("campaign_id"));
                    m.put("name", rs.getString("name"));
                    m.put("intro", rs.getString("intro"));
                    m.put("sortNo", rs.getInt("sort_no"));
                    m.put("status", rs.getString("status"));
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    return m;
                },
                campaignId);
    }

    public static Map<String, Object> pageCandidatesAdmin(long campaignId, int page, int size) {
        require();
        int p = Math.max(1, page);
        int s = Math.min(100, Math.max(1, size));
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM vote_candidate WHERE campaign_id=?", Integer.class, campaignId);
        List<Map<String, Object>> list = db().query(
                "SELECT id, campaign_id, name, intro, sort_no, status, created_at "
                        + "FROM vote_candidate WHERE campaign_id=? ORDER BY sort_no, id LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("campaignId", rs.getLong("campaign_id"));
                    m.put("name", rs.getString("name"));
                    m.put("intro", rs.getString("intro"));
                    m.put("sortNo", rs.getInt("sort_no"));
                    m.put("status", rs.getString("status"));
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    return m;
                },
                campaignId, s, (p - 1) * s);
        return pageOut(list, total, p, s);
    }

    public static Map<String, Object> createCandidate(Map<String, Object> body) {
        require();
        Long campaignId = toLong(body.get("campaignId"));
        if (campaignId == null) throw new IllegalArgumentException("缺少评选活动");
        if (getCampaign(campaignId) == null) throw new IllegalArgumentException("评选活动不存在");
        String name = clip(str(body.get("name")), 128);
        if (name.isBlank()) throw new IllegalArgumentException("候选人姓名不能为空");
        String intro = clip(str(body.get("intro")), 1000);
        int sortNo = toInt(body.get("sortNo"), 0);
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO vote_candidate(campaign_id, name, intro, sort_no, status) VALUES(?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, campaignId);
            ps.setString(2, name);
            ps.setString(3, intro);
            ps.setInt(4, sortNo);
            ps.setString(5, "available");
            return ps;
        }, kh);
        Number key = kh.getKey();
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", key == null ? null : key.longValue());
        out.put("campaignId", campaignId);
        out.put("name", name);
        return out;
    }

    public static boolean deleteCandidate(long id) {
        require();
        Integer ballots = db().queryForObject(
                "SELECT COUNT(*) FROM vote_ballot WHERE candidate_id=?", Integer.class, id);
        if (ballots != null && ballots > 0) {
            throw new IllegalStateException("已有选票，不能删除该候选人");
        }
        return db().update("DELETE FROM vote_candidate WHERE id=?", id) > 0;
    }

    public static Map<String, Object> cast(String username, long campaignId, List<Long> candidateIds) {
        require();
        Map<String, Object> camp = getCampaign(campaignId);
        if (camp == null || !"available".equals(str(camp.get("status")))) {
            throw new IllegalStateException("评选未开放");
        }
        int maxVotes = Math.max(1, toInt(camp.get("maxVotes"), 1));
        if (candidateIds == null || candidateIds.isEmpty()) {
            throw new IllegalArgumentException("请选择候选人");
        }
        LinkedHashSet<Long> uniq = new LinkedHashSet<>();
        for (Long id : candidateIds) {
            if (id != null) uniq.add(id);
        }
        if (uniq.isEmpty()) throw new IllegalArgumentException("请选择候选人");
        Integer used = db().queryForObject(
                "SELECT COUNT(*) FROM vote_ballot WHERE campaign_id=? AND username=?",
                Integer.class, campaignId, username);
        int already = used == null ? 0 : used;
        if (already + uniq.size() > maxVotes) {
            throw new IllegalStateException("超出限票数（每人最多 " + maxVotes + " 票）");
        }
        for (Long cid : uniq) {
            Integer ok = db().queryForObject(
                    "SELECT COUNT(*) FROM vote_candidate WHERE id=? AND campaign_id=? AND status='available'",
                    Integer.class, cid, campaignId);
            if (ok == null || ok == 0) throw new IllegalArgumentException("候选人不存在或已停用");
            Integer dup = db().queryForObject(
                    "SELECT COUNT(*) FROM vote_ballot WHERE campaign_id=? AND username=? AND candidate_id=?",
                    Integer.class, campaignId, username, cid);
            if (dup != null && dup > 0) throw new IllegalStateException("已投过该候选人");
            db().update(
                    "INSERT INTO vote_ballot(campaign_id, username, candidate_id) VALUES(?,?,?)",
                    campaignId, username, cid);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("campaignId", campaignId);
        out.put("castCount", uniq.size());
        out.put("maxVotes", maxVotes);
        out.put("usedVotes", already + uniq.size());
        return out;
    }

    public static List<Map<String, Object>> results(long campaignId) {
        require();
        return db().query(
                "SELECT c.id, c.name, c.intro, c.sort_no, "
                        + "COALESCE((SELECT COUNT(*) FROM vote_ballot b WHERE b.candidate_id=c.id),0) AS votes "
                        + "FROM vote_candidate c WHERE c.campaign_id=? ORDER BY votes DESC, c.sort_no, c.id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("name", rs.getString("name"));
                    m.put("intro", rs.getString("intro"));
                    m.put("sortNo", rs.getInt("sort_no"));
                    m.put("votes", rs.getInt("votes"));
                    return m;
                },
                campaignId);
    }

    public static Map<String, Object> pageMine(String username, int page, int size) {
        require();
        int p = Math.max(1, page);
        int s = Math.min(100, Math.max(1, size));
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM vote_ballot WHERE username=?", Integer.class, username);
        List<Map<String, Object>> list = db().query(
                "SELECT b.id, b.campaign_id, b.candidate_id, b.created_at, "
                        + "v.title AS campaign_title, c.name AS candidate_name "
                        + "FROM vote_ballot b "
                        + "JOIN vote_campaign v ON v.id=b.campaign_id "
                        + "JOIN vote_candidate c ON c.id=b.candidate_id "
                        + "WHERE b.username=? ORDER BY b.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("campaignId", rs.getLong("campaign_id"));
                    m.put("candidateId", rs.getLong("candidate_id"));
                    m.put("campaignTitle", rs.getString("campaign_title"));
                    m.put("candidateName", rs.getString("candidate_name"));
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    return m;
                },
                username, s, (p - 1) * s);
        return pageOut(list, total, p, s);
    }

    public static Map<String, Object> pageBallotsAdmin(long campaignId, int page, int size) {
        require();
        int p = Math.max(1, page);
        int s = Math.min(100, Math.max(1, size));
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM vote_ballot WHERE campaign_id=?", Integer.class, campaignId);
        List<Map<String, Object>> list = db().query(
                "SELECT b.id, b.username, b.candidate_id, b.created_at, c.name AS candidate_name "
                        + "FROM vote_ballot b JOIN vote_candidate c ON c.id=b.candidate_id "
                        + "WHERE b.campaign_id=? ORDER BY b.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("username", rs.getString("username"));
                    m.put("candidateId", rs.getLong("candidate_id"));
                    m.put("candidateName", rs.getString("candidate_name"));
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    return m;
                },
                campaignId, s, (p - 1) * s);
        return pageOut(list, total, p, s);
    }
}
