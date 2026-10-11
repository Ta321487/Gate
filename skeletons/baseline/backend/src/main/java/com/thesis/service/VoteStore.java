package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 投票评选（C-04 + I-10）：候选档案、限票/每日限票、匿名、延迟公示、弃权、IP 提示、结果导出。
 */
public class VoteStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final long ABSTAIN_CANDIDATE_ID = 0L;

    private static boolean enabled;
    private static Boolean tableReady;
    private static final Map<String, Boolean> colReady = new HashMap<>();

    private VoteStore() {}

    public static void configure(boolean on) {
        enabled = on;
        tableReady = null;
        colReady.clear();
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
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

    private static synchronized boolean ensureCol(String table, String column, String ddlType) {
        String key = table + "." + column;
        Boolean cached = colReady.get(key);
        if (cached != null) return cached;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE()"
                            + " AND TABLE_NAME=? AND COLUMN_NAME=?",
                    Integer.class, table, column);
            if (n != null && n > 0) {
                colReady.put(key, true);
                return true;
            }
            db().execute("ALTER TABLE " + table + " ADD COLUMN " + column + " " + ddlType);
            colReady.put(key, true);
            return true;
        } catch (Exception e) {
            try {
                Integer n = db().queryForObject(
                        "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE()"
                                + " AND TABLE_NAME=? AND COLUMN_NAME=?",
                        Integer.class, table, column);
                boolean ok = n != null && n > 0;
                colReady.put(key, ok);
                return ok;
            } catch (Exception ignored) {
                colReady.put(key, false);
                return false;
            }
        }
    }

    private static void ensureI10Columns() {
        ensureCol("vote_candidate", "avatar_url", "VARCHAR(255) DEFAULT ''");
        ensureCol("vote_candidate", "slogan", "VARCHAR(255) NOT NULL DEFAULT ''");
        ensureCol("vote_campaign", "anonymous", "TINYINT NOT NULL DEFAULT 0");
        ensureCol("vote_campaign", "daily_vote_limit", "INT NOT NULL DEFAULT 0");
        ensureCol("vote_campaign", "results_publish_at", "DATETIME NULL");
        ensureCol("vote_campaign", "allow_abstain", "TINYINT NOT NULL DEFAULT 0");
        ensureCol("vote_campaign", "require_real_name", "TINYINT NOT NULL DEFAULT 0");
        ensureCol("vote_campaign", "poll_seconds", "INT NOT NULL DEFAULT 0");
        ensureCol("vote_campaign", "ip_hint_enabled", "TINYINT NOT NULL DEFAULT 1");
        ensureCol("vote_ballot", "client_ip", "VARCHAR(64) NOT NULL DEFAULT ''");
        ensureCol("vote_ballot", "abstain", "TINYINT NOT NULL DEFAULT 0");
    }

    public static boolean hasAvatarUrl() {
        if (!ready()) return false;
        return ensureCol("vote_candidate", "avatar_url", "VARCHAR(255) DEFAULT ''");
    }

    private static boolean hasSlogan() {
        return ensureCol("vote_candidate", "slogan", "VARCHAR(255) NOT NULL DEFAULT ''");
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

    private static boolean toBool(Object o, boolean def) {
        if (o == null || String.valueOf(o).isBlank()) return def;
        if (o instanceof Boolean b) return b;
        String s = String.valueOf(o).trim();
        if ("1".equals(s) || "true".equalsIgnoreCase(s) || "yes".equalsIgnoreCase(s)) return true;
        if ("0".equals(s) || "false".equalsIgnoreCase(s) || "no".equalsIgnoreCase(s)) return false;
        return def;
    }

    private static Map<String, Object> pageOut(List<?> list, Integer total, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static void putAvatar(Map<String, Object> m, java.sql.ResultSet rs) throws java.sql.SQLException {
        if (!hasAvatarUrl()) {
            m.put("avatarUrl", "");
            return;
        }
        try {
            String av = rs.getString("avatar_url");
            m.put("avatarUrl", av == null ? "" : av.trim());
        } catch (Exception e) {
            m.put("avatarUrl", "");
        }
    }

    private static void putSlogan(Map<String, Object> m, java.sql.ResultSet rs) throws java.sql.SQLException {
        if (!hasSlogan()) {
            m.put("slogan", "");
            return;
        }
        try {
            String s = rs.getString("slogan");
            m.put("slogan", s == null ? "" : s.trim());
        } catch (Exception e) {
            m.put("slogan", "");
        }
    }

    private static boolean resultPublished(Map<String, Object> camp) {
        String at = str(camp.get("resultsPublishAt"));
        if (at.isBlank()) return true;
        try {
            LocalDateTime publish = LocalDateTime.parse(at.length() == 10 ? at + " 00:00:00" : at, FMT);
            return !LocalDateTime.now().isBefore(publish);
        } catch (Exception e) {
            try {
                LocalDateTime publish = LocalDateTime.parse(at.replace(' ', 'T'));
                return !LocalDateTime.now().isBefore(publish);
            } catch (Exception ignored) {
                return true;
            }
        }
    }

    private static Map<String, Object> mapCampaign(java.sql.ResultSet rs) throws java.sql.SQLException {
        ensureI10Columns();
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
        try {
            m.put("anonymous", rs.getInt("anonymous") == 1);
        } catch (Exception e) {
            m.put("anonymous", false);
        }
        try {
            m.put("dailyVoteLimit", rs.getInt("daily_vote_limit"));
        } catch (Exception e) {
            m.put("dailyVoteLimit", 0);
        }
        try {
            m.put("resultsPublishAt", fmt(rs.getTimestamp("results_publish_at")));
        } catch (Exception e) {
            m.put("resultsPublishAt", null);
        }
        try {
            m.put("allowAbstain", rs.getInt("allow_abstain") == 1);
        } catch (Exception e) {
            m.put("allowAbstain", false);
        }
        try {
            m.put("requireRealName", rs.getInt("require_real_name") == 1);
        } catch (Exception e) {
            m.put("requireRealName", false);
        }
        try {
            m.put("pollSeconds", rs.getInt("poll_seconds"));
        } catch (Exception e) {
            m.put("pollSeconds", 0);
        }
        try {
            m.put("ipHintEnabled", rs.getInt("ip_hint_enabled") == 1);
        } catch (Exception e) {
            m.put("ipHintEnabled", true);
        }
        m.put("resultPublished", resultPublished(m));
        return m;
    }

    private static final String CAMP_COLS =
            "id, title, author, isbn, category_id, stock, status, cover_url, created_at, "
                    + "anonymous, daily_vote_limit, results_publish_at, allow_abstain, "
                    + "require_real_name, poll_seconds, ip_hint_enabled";

    public static List<Map<String, Object>> listOpenCampaigns() {
        require();
        ensureI10Columns();
        return db().query(
                "SELECT " + CAMP_COLS + " FROM vote_campaign WHERE status='available' ORDER BY id DESC",
                (rs, i) -> mapCampaign(rs));
    }

    public static Map<String, Object> getCampaign(long id) {
        require();
        ensureI10Columns();
        List<Map<String, Object>> rows = db().query(
                "SELECT " + CAMP_COLS + " FROM vote_campaign WHERE id=?",
                (rs, i) -> mapCampaign(rs),
                id);
        return rows.isEmpty() ? null : rows.get(0);
    }

    public static Map<String, Object> updateCampaignSettings(long campaignId, Map<String, Object> body) {
        require();
        ensureI10Columns();
        if (getCampaign(campaignId) == null) throw new IllegalArgumentException("评选活动不存在");
        if (body == null) body = Map.of();
        if (body.containsKey("anonymous")) {
            db().update("UPDATE vote_campaign SET anonymous=? WHERE id=?",
                    toBool(body.get("anonymous"), false) ? 1 : 0, campaignId);
        }
        if (body.containsKey("dailyVoteLimit") || body.containsKey("daily_vote_limit")) {
            Object v = body.get("dailyVoteLimit") != null ? body.get("dailyVoteLimit") : body.get("daily_vote_limit");
            db().update("UPDATE vote_campaign SET daily_vote_limit=? WHERE id=?",
                    Math.max(0, toInt(v, 0)), campaignId);
        }
        if (body.containsKey("resultsPublishAt") || body.containsKey("results_publish_at")) {
            Object v = body.get("resultsPublishAt") != null ? body.get("resultsPublishAt") : body.get("results_publish_at");
            String s = str(v);
            if (s.isBlank()) {
                db().update("UPDATE vote_campaign SET results_publish_at=NULL WHERE id=?", campaignId);
            } else {
                db().update("UPDATE vote_campaign SET results_publish_at=? WHERE id=?", s, campaignId);
            }
        }
        if (body.containsKey("allowAbstain") || body.containsKey("allow_abstain")) {
            Object v = body.get("allowAbstain") != null ? body.get("allowAbstain") : body.get("allow_abstain");
            db().update("UPDATE vote_campaign SET allow_abstain=? WHERE id=?",
                    toBool(v, false) ? 1 : 0, campaignId);
        }
        if (body.containsKey("requireRealName") || body.containsKey("require_real_name")) {
            Object v = body.get("requireRealName") != null ? body.get("requireRealName") : body.get("require_real_name");
            db().update("UPDATE vote_campaign SET require_real_name=? WHERE id=?",
                    toBool(v, false) ? 1 : 0, campaignId);
        }
        if (body.containsKey("pollSeconds") || body.containsKey("poll_seconds")) {
            Object v = body.get("pollSeconds") != null ? body.get("pollSeconds") : body.get("poll_seconds");
            db().update("UPDATE vote_campaign SET poll_seconds=? WHERE id=?",
                    Math.max(0, Math.min(3600, toInt(v, 0))), campaignId);
        }
        if (body.containsKey("ipHintEnabled") || body.containsKey("ip_hint_enabled")) {
            Object v = body.get("ipHintEnabled") != null ? body.get("ipHintEnabled") : body.get("ip_hint_enabled");
            db().update("UPDATE vote_campaign SET ip_hint_enabled=? WHERE id=?",
                    toBool(v, true) ? 1 : 0, campaignId);
        }
        if (body.containsKey("maxVotes") || body.containsKey("stock")) {
            Object v = body.get("maxVotes") != null ? body.get("maxVotes") : body.get("stock");
            db().update("UPDATE vote_campaign SET stock=? WHERE id=?",
                    Math.max(1, toInt(v, 1)), campaignId);
        }
        return getCampaign(campaignId);
    }

    public static List<Map<String, Object>> listCandidates(long campaignId) {
        require();
        ensureI10Columns();
        String cols = "id, campaign_id, name, intro, sort_no, status, created_at"
                + (hasAvatarUrl() ? ", avatar_url" : "")
                + (hasSlogan() ? ", slogan" : "");
        return db().query(
                "SELECT " + cols
                        + " FROM vote_candidate WHERE campaign_id=? AND status='available' ORDER BY sort_no, id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("campaignId", rs.getLong("campaign_id"));
                    m.put("name", rs.getString("name"));
                    m.put("intro", rs.getString("intro"));
                    m.put("sortNo", rs.getInt("sort_no"));
                    m.put("status", rs.getString("status"));
                    putAvatar(m, rs);
                    putSlogan(m, rs);
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    return m;
                },
                campaignId);
    }

    public static Map<String, Object> pageCandidatesAdmin(long campaignId, int page, int size) {
        require();
        ensureI10Columns();
        int p = Math.max(1, page);
        int s = Math.min(100, Math.max(1, size));
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM vote_candidate WHERE campaign_id=?", Integer.class, campaignId);
        String cols = "id, campaign_id, name, intro, sort_no, status, created_at"
                + (hasAvatarUrl() ? ", avatar_url" : "")
                + (hasSlogan() ? ", slogan" : "");
        List<Map<String, Object>> list = db().query(
                "SELECT " + cols
                        + " FROM vote_candidate WHERE campaign_id=? ORDER BY sort_no, id LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("campaignId", rs.getLong("campaign_id"));
                    m.put("name", rs.getString("name"));
                    m.put("intro", rs.getString("intro"));
                    m.put("sortNo", rs.getInt("sort_no"));
                    m.put("status", rs.getString("status"));
                    putAvatar(m, rs);
                    putSlogan(m, rs);
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    return m;
                },
                campaignId, s, (p - 1) * s);
        return pageOut(list, total, p, s);
    }

    public static Map<String, Object> createCandidate(Map<String, Object> body) {
        require();
        ensureI10Columns();
        Long campaignId = toLong(body.get("campaignId"));
        if (campaignId == null) throw new IllegalArgumentException("缺少评选活动");
        if (getCampaign(campaignId) == null) throw new IllegalArgumentException("评选活动不存在");
        String name = clip(str(body.get("name")), 128);
        if (name.isBlank()) throw new IllegalArgumentException("候选人姓名不能为空");
        String intro = clip(str(body.get("intro")), 1000);
        String slogan = clip(str(body.get("slogan") != null ? body.get("slogan") : body.get("pitch")), 255);
        int sortNo = toInt(body.get("sortNo"), 0);
        String avatarUrl = clip(str(body.get("avatarUrl") != null ? body.get("avatarUrl") : body.get("avatar_url")), 255);
        if (!avatarUrl.isBlank() && !hasAvatarUrl()) {
            throw new IllegalStateException("系统未配置候选人头像字段，无法保存");
        }
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            boolean av = hasAvatarUrl();
            boolean sg = hasSlogan();
            String sql;
            if (av && sg) {
                sql = "INSERT INTO vote_candidate(campaign_id, name, intro, sort_no, status, avatar_url, slogan) VALUES(?,?,?,?,?,?,?)";
            } else if (av) {
                sql = "INSERT INTO vote_candidate(campaign_id, name, intro, sort_no, status, avatar_url) VALUES(?,?,?,?,?,?)";
            } else if (sg) {
                sql = "INSERT INTO vote_candidate(campaign_id, name, intro, sort_no, status, slogan) VALUES(?,?,?,?,?,?)";
            } else {
                sql = "INSERT INTO vote_candidate(campaign_id, name, intro, sort_no, status) VALUES(?,?,?,?,?)";
            }
            PreparedStatement ps = con.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, campaignId);
            ps.setString(2, name);
            ps.setString(3, intro);
            ps.setInt(4, sortNo);
            ps.setString(5, "available");
            int idx = 6;
            if (av) ps.setString(idx++, avatarUrl);
            if (sg) ps.setString(idx, slogan);
            return ps;
        }, kh);
        Number key = kh.getKey();
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", key == null ? null : key.longValue());
        out.put("campaignId", campaignId);
        out.put("name", name);
        out.put("intro", intro);
        out.put("slogan", slogan);
        out.put("avatarUrl", avatarUrl);
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

    private static void assertRealName(String username, Map<String, Object> camp) {
        if (!Boolean.TRUE.equals(camp.get("requireRealName"))) return;
        UserStore.Profile p = UserStore.get(username);
        String real = "";
        if (p != null && p.extras != null) {
            real = str(p.extras.get("realName"));
        }
        if (real.isBlank()) {
            throw new IllegalStateException("本评选需实名后投票，请先在资料中填写真实姓名");
        }
    }

    public static Map<String, Object> cast(
            String username, long campaignId, List<Long> candidateIds, boolean abstain, String clientIp) {
        require();
        ensureI10Columns();
        Map<String, Object> camp = getCampaign(campaignId);
        if (camp == null || !"available".equals(str(camp.get("status")))) {
            throw new IllegalStateException("评选未开放");
        }
        assertRealName(username, camp);
        int maxVotes = Math.max(1, toInt(camp.get("maxVotes"), 1));
        int dailyLimit = Math.max(0, toInt(camp.get("dailyVoteLimit"), 0));
        String ip = clip(clientIp, 64);

        if (abstain) {
            if (!Boolean.TRUE.equals(camp.get("allowAbstain"))) {
                throw new IllegalStateException("本评选未开放弃权");
            }
            Integer used = db().queryForObject(
                    "SELECT COUNT(*) FROM vote_ballot WHERE campaign_id=? AND username=?",
                    Integer.class, campaignId, username);
            if (used != null && used > 0) {
                throw new IllegalStateException("您已投过票，不能再弃权");
            }
            db().update(
                    "INSERT INTO vote_ballot(campaign_id, username, candidate_id, client_ip, abstain) VALUES(?,?,?,?,1)",
                    campaignId, username, ABSTAIN_CANDIDATE_ID, ip);
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("campaignId", campaignId);
            out.put("castCount", 0);
            out.put("abstain", true);
            out.put("maxVotes", maxVotes);
            out.put("usedVotes", 0);
            out.put("ipHint", ipHint(campaignId, username, ip, camp));
            return out;
        }

        if (candidateIds == null || candidateIds.isEmpty()) {
            throw new IllegalArgumentException("请选择候选人");
        }
        LinkedHashSet<Long> uniq = new LinkedHashSet<>();
        for (Long id : candidateIds) {
            if (id != null && id > 0) uniq.add(id);
        }
        if (uniq.isEmpty()) throw new IllegalArgumentException("请选择候选人");
        Integer used = db().queryForObject(
                "SELECT COUNT(*) FROM vote_ballot WHERE campaign_id=? AND username=? AND abstain=0",
                Integer.class, campaignId, username);
        int already = used == null ? 0 : used;
        if (already + uniq.size() > maxVotes) {
            throw new IllegalStateException("超出限票数（每人最多 " + maxVotes + " 票）");
        }
        if (dailyLimit > 0) {
            Integer today = db().queryForObject(
                    "SELECT COUNT(*) FROM vote_ballot WHERE campaign_id=? AND username=? "
                            + "AND DATE(created_at)=CURDATE() AND abstain=0",
                    Integer.class, campaignId, username);
            int t = today == null ? 0 : today;
            if (t + uniq.size() > dailyLimit) {
                throw new IllegalStateException("超出每日限票（每天最多 " + dailyLimit + " 票）");
            }
        }
        Integer abs = db().queryForObject(
                "SELECT COUNT(*) FROM vote_ballot WHERE campaign_id=? AND username=? AND abstain=1",
                Integer.class, campaignId, username);
        if (abs != null && abs > 0) {
            throw new IllegalStateException("您已弃权，不能再投票");
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
                    "INSERT INTO vote_ballot(campaign_id, username, candidate_id, client_ip, abstain) VALUES(?,?,?,?,0)",
                    campaignId, username, cid, ip);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("campaignId", campaignId);
        out.put("castCount", uniq.size());
        out.put("abstain", false);
        out.put("maxVotes", maxVotes);
        out.put("usedVotes", already + uniq.size());
        out.put("ipHint", ipHint(campaignId, username, ip, camp));
        return out;
    }

    /** 兼容旧调用。 */
    public static Map<String, Object> cast(String username, long campaignId, List<Long> candidateIds) {
        return cast(username, campaignId, candidateIds, false, "");
    }

    private static String ipHint(long campaignId, String username, String ip, Map<String, Object> camp) {
        if (!Boolean.TRUE.equals(camp.get("ipHintEnabled"))) return "";
        if (ip == null || ip.isBlank()) return "";
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM vote_ballot WHERE campaign_id=? AND client_ip=? AND username<>? AND client_ip<>''",
                    Integer.class, campaignId, ip, username);
            if (n != null && n > 0) {
                return "检测到同一网络地址已有其他人投票，请确认是否本人操作（仅提示，不拦截）。";
            }
        } catch (Exception ignored) {
            // ignore
        }
        return "";
    }

    public static List<Map<String, Object>> results(long campaignId, boolean admin) {
        require();
        ensureI10Columns();
        Map<String, Object> camp = getCampaign(campaignId);
        if (camp == null) throw new IllegalArgumentException("评选不存在");
        if (!admin && !resultPublished(camp)) {
            throw new IllegalStateException("结果尚未到公布时间");
        }
        String avCol = hasAvatarUrl() ? ", c.avatar_url " : " ";
        String sgCol = hasSlogan() ? ", c.slogan " : " ";
        return db().query(
                "SELECT c.id, c.name, c.intro, c.sort_no" + avCol + sgCol
                        + ", COALESCE((SELECT COUNT(*) FROM vote_ballot b WHERE b.candidate_id=c.id AND b.abstain=0),0) AS votes "
                        + "FROM vote_candidate c WHERE c.campaign_id=? ORDER BY votes DESC, c.sort_no, c.id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("name", rs.getString("name"));
                    m.put("intro", rs.getString("intro"));
                    m.put("sortNo", rs.getInt("sort_no"));
                    putAvatar(m, rs);
                    putSlogan(m, rs);
                    m.put("votes", rs.getInt("votes"));
                    return m;
                },
                campaignId);
    }

    public static List<Map<String, Object>> results(long campaignId) {
        return results(campaignId, false);
    }

    public static String exportResultsCsv(long campaignId) {
        require();
        ensureI10Columns();
        Map<String, Object> camp = getCampaign(campaignId);
        if (camp == null) throw new IllegalArgumentException("评选不存在");
        boolean anon = Boolean.TRUE.equals(camp.get("anonymous"));
        List<Map<String, Object>> ranks = results(campaignId, true);
        StringBuilder sb = new StringBuilder("rank,candidate_id,name,votes,intro,slogan\n");
        int rank = 1;
        for (Map<String, Object> r : ranks) {
            sb.append(rank++).append(',')
                    .append(r.get("id")).append(',')
                    .append(csv(str(r.get("name")))).append(',')
                    .append(r.get("votes")).append(',')
                    .append(csv(str(r.get("intro")))).append(',')
                    .append(csv(str(r.get("slogan")))).append('\n');
        }
        sb.append("\nballot_id,username,candidate_id,candidate_name,abstain,client_ip,created_at\n");
        List<Map<String, Object>> ballots = db().query(
                "SELECT b.id, b.username, b.candidate_id, b.abstain, b.client_ip, b.created_at, "
                        + "COALESCE(c.name, CASE WHEN b.abstain=1 THEN '弃权' ELSE '' END) AS candidate_name "
                        + "FROM vote_ballot b LEFT JOIN vote_candidate c ON c.id=b.candidate_id "
                        + "WHERE b.campaign_id=? ORDER BY b.id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("username", rs.getString("username"));
                    m.put("candidateId", rs.getLong("candidate_id"));
                    m.put("candidateName", rs.getString("candidate_name"));
                    m.put("abstain", rs.getInt("abstain") == 1);
                    m.put("clientIp", rs.getString("client_ip"));
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    return m;
                },
                campaignId);
        for (Map<String, Object> b : ballots) {
            String user = anon ? "匿名" : str(b.get("username"));
            sb.append(b.get("id")).append(',')
                    .append(csv(user)).append(',')
                    .append(b.get("candidateId")).append(',')
                    .append(csv(str(b.get("candidateName")))).append(',')
                    .append(Boolean.TRUE.equals(b.get("abstain")) ? 1 : 0).append(',')
                    .append(csv(str(b.get("clientIp")))).append(',')
                    .append(csv(str(b.get("createdAt")))).append('\n');
        }
        return sb.toString();
    }

    private static String csv(String s) {
        if (s == null) return "";
        if (s.contains(",") || s.contains("\"") || s.contains("\n")) {
            return "\"" + s.replace("\"", "\"\"") + "\"";
        }
        return s;
    }

    public static Map<String, Object> pageMine(String username, int page, int size) {
        require();
        ensureI10Columns();
        int p = Math.max(1, page);
        int s = Math.min(100, Math.max(1, size));
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM vote_ballot WHERE username=?", Integer.class, username);
        List<Map<String, Object>> list = db().query(
                "SELECT b.id, b.campaign_id, b.candidate_id, b.abstain, b.created_at, "
                        + "v.title AS campaign_title, "
                        + "COALESCE(c.name, CASE WHEN b.abstain=1 THEN '弃权' ELSE '' END) AS candidate_name "
                        + "FROM vote_ballot b "
                        + "JOIN vote_campaign v ON v.id=b.campaign_id "
                        + "LEFT JOIN vote_candidate c ON c.id=b.candidate_id "
                        + "WHERE b.username=? ORDER BY b.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("campaignId", rs.getLong("campaign_id"));
                    m.put("candidateId", rs.getLong("candidate_id"));
                    m.put("abstain", rs.getInt("abstain") == 1);
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
        ensureI10Columns();
        Map<String, Object> camp = getCampaign(campaignId);
        boolean anon = camp != null && Boolean.TRUE.equals(camp.get("anonymous"));
        int p = Math.max(1, page);
        int s = Math.min(100, Math.max(1, size));
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM vote_ballot WHERE campaign_id=?", Integer.class, campaignId);
        List<Map<String, Object>> list = db().query(
                "SELECT b.id, b.username, b.candidate_id, b.abstain, b.client_ip, b.created_at, "
                        + "COALESCE(c.name, CASE WHEN b.abstain=1 THEN '弃权' ELSE '' END) AS candidate_name "
                        + "FROM vote_ballot b LEFT JOIN vote_candidate c ON c.id=b.candidate_id "
                        + "WHERE b.campaign_id=? ORDER BY b.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    String user = rs.getString("username");
                    m.put("username", anon ? "匿名" : user);
                    m.put("candidateId", rs.getLong("candidate_id"));
                    m.put("candidateName", rs.getString("candidate_name"));
                    m.put("abstain", rs.getInt("abstain") == 1);
                    m.put("clientIp", rs.getString("client_ip"));
                    m.put("createdAt", fmt(rs.getTimestamp("created_at")));
                    return m;
                },
                campaignId, s, (p - 1) * s);
        return pageOut(list, total, p, s);
    }
}
