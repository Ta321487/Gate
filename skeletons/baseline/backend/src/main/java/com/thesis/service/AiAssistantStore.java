package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * AI 助手岛：知识条目 + 会话消息 + 满意度。
 * 回答优先只读业务摘录（AiBizContext→现有 Store）与 FAQ；无命中不调用大模型自由发挥。
 */
public class AiAssistantStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int CONTENT_MAX = 2000;
    private static final int MSG_MAX = 4000;
    /** 无关问题固定婉拒 */
    private static final String REPLY_OFF_TOPIC =
            "我只能回答与本系统业务、流程或知识库相关的问题。请换一个与本平台功能有关的问法。";
    /** 无 FAQ 且无业务数据：不调大模型补答 */
    private static final String REPLY_NO_FAQ =
            "暂未匹配到相关知识或业务数据。请换个问法，或请管理员在「AI知识库」补充条目。";
    private static Boolean tableReady;

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static boolean ready() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='sys_ai_knowledge'",
                    Integer.class);
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

    private static Map<String, Object> knowledgeRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("category", rs.getString("category"));
        m.put("title", rs.getString("title"));
        m.put("content", rs.getString("content"));
        m.put("keywords", rs.getString("keywords"));
        m.put("hitCount", rs.getInt("hit_count"));
        m.put("enabled", rs.getInt("enabled") == 1);
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        m.put("updatedAt", fmt(rs.getTimestamp("updated_at")));
        return m;
    }

    private static Map<String, Object> messageRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("role", rs.getString("role"));
        m.put("content", rs.getString("content"));
        m.put("source", rs.getString("source"));
        m.put("category", rs.getString("category"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        return m;
    }

    /** 图片品类映射：文件名/用户指定分类 → 规范化分类名（跨域常见词，非 CNN） */
    public static String resolveCategoryHint(String category, String filename) {
        String c = category == null ? "" : category.trim();
        if (!c.isBlank()) return clip(c, 64);
        String f = filename == null ? "" : filename.toLowerCase(Locale.ROOT);
        if (f.contains("水果") || f.contains("fruit") || f.contains("apple") || f.contains("橙") || f.contains("莓")) {
            return "水果";
        }
        if (f.contains("菜") || f.contains("蔬") || f.contains("veg") || f.contains("叶")) {
            return "蔬菜";
        }
        if (f.contains("粮") || f.contains("油") || f.contains("米") || f.contains("面")) {
            return "粮油";
        }
        if (f.contains("书") || f.contains("book") || f.contains("教材") || f.contains("小说")) {
            return "检索";
        }
        if (f.contains("借") || f.contains("馆")) {
            return "借阅";
        }
        if (f.contains("修") || f.contains("故障") || f.contains("水电") || f.contains("repair")) {
            return "水电";
        }
        if (f.contains("门禁") || f.contains("门卡")) {
            return "门禁";
        }
        if (f.contains("假") || f.contains("leave") || f.contains("考勤")) {
            return "事假类";
        }
        if (f.contains("餐") || f.contains("food") || f.contains("套餐")) {
            return "套餐";
        }
        if (f.contains("面") && (f.contains("食") || f.contains("条"))) {
            return "面食";
        }
        if (f.contains("教材") || f.contains("教辅")) {
            return "教材教辅";
        }
        if (f.contains("数码") || f.contains("手机") || f.contains("耳机")) {
            return "数码";
        }
        return "";
    }

    public static Map<String, Object> matchFaq(String question, String category) {
        if (!ready()) return null;
        String q = clip(question, 500).toLowerCase(Locale.ROOT);
        String cat = category == null ? "" : category.trim();
        List<Map<String, Object>> rows;
        if (!cat.isBlank()) {
            rows = db().query(
                    "SELECT * FROM sys_ai_knowledge WHERE enabled=1 AND category=? ORDER BY hit_count DESC, id DESC LIMIT 40",
                    (rs, i) -> knowledgeRow(rs), cat);
        } else {
            rows = db().query(
                    "SELECT * FROM sys_ai_knowledge WHERE enabled=1 ORDER BY hit_count DESC, id DESC LIMIT 80",
                    (rs, i) -> knowledgeRow(rs));
        }
        Map<String, Object> best = null;
        int bestScore = 0;
        for (Map<String, Object> row : rows) {
            int score = scoreFaq(q, row);
            if (score > bestScore) {
                bestScore = score;
                best = row;
            }
        }
        // 必须关键词/标题有分才算命中；禁止「有分类就硬塞第一条」导致偏题
        if (best == null || bestScore <= 0) return null;
        bumpHit(((Number) best.get("id")).longValue());
        return best;
    }

    /** 明显偏离业务助手：写诗/写代码/算题/闲聊等 */
    static boolean looksOffTopic(String question) {
        if (question == null || question.isBlank()) return false;
        String q = question.toLowerCase(Locale.ROOT);
        String[] hints = {
                "写一首", "作一首", "写诗", "写个段子", "讲个笑话", "讲笑话",
                "帮我写代码", "写代码", "写一段代码", "写程序", "debug", "leetcode",
                "今天天气", "明天天气", "天气预报",
                "股票", "基金", "彩票", "星座", "算命",
                "恋爱", "表白", "吵架",
                "政治", "选举", "战争",
                "翻译成英文", "翻译成日文", "translate to",
                "忽略以上", "忽略之前", "jailbreak", "提示词破解"
        };
        for (String h : hints) {
            if (q.contains(h.toLowerCase(Locale.ROOT))) return true;
        }
        return false;
    }

    private static int scoreFaq(String qLower, Map<String, Object> row) {
        if (qLower == null || qLower.isBlank()) return 0;
        int score = 0;
        String title = String.valueOf(row.getOrDefault("title", "")).toLowerCase(Locale.ROOT);
        String content = String.valueOf(row.getOrDefault("content", "")).toLowerCase(Locale.ROOT);
        String keywords = String.valueOf(row.getOrDefault("keywords", "")).toLowerCase(Locale.ROOT);
        String category = String.valueOf(row.getOrDefault("category", "")).toLowerCase(Locale.ROOT);
        if (!title.isBlank() && qLower.contains(title)) score += 8;
        for (String part : keywords.split("[,，;；\\s]+")) {
            String p = part.trim();
            if (p.length() >= 2 && qLower.contains(p)) score += 5;
        }
        if (!category.isBlank() && qLower.contains(category)) score += 3;
        for (String token : qLower.split("[\\s，,。？?！!、]+")) {
            if (token.length() >= 2 && (title.contains(token) || content.contains(token) || keywords.contains(token))) {
                score += 2;
            }
        }
        return score;
    }

    private static void bumpHit(long id) {
        db().update("UPDATE sys_ai_knowledge SET hit_count=hit_count+1 WHERE id=?", id);
    }

    public static Map<String, Object> ask(String username, String question, String categoryHint) {
        return ask(username, question, categoryHint, null);
    }

    public static Map<String, Object> ask(
            String username, String question, String categoryHint, String appTitle) {
        if (!ready()) return null;
        String q = clip(question, MSG_MAX);
        if (q.isBlank()) return null;
        String cat = clip(categoryHint, 64);
        saveMessage(username, "user", q, "user", cat);

        String answer;
        String source;
        Map<String, Object> faq = null;
        String bizExcerpt = null;

        if (looksOffTopic(q)) {
            answer = REPLY_OFF_TOPIC;
            source = "off_topic";
        } else {
            bizExcerpt = AiBizContext.buildExcerpt(username, q, cat);
            faq = matchFaq(q, cat);
            if ((bizExcerpt == null || bizExcerpt.isBlank()) && faq == null) {
                answer = REPLY_NO_FAQ;
                source = "fallback";
            } else {
                if (faq != null && cat.isBlank() && faq.get("category") != null) {
                    cat = String.valueOf(faq.get("category"));
                }
                answer = null;
                source = faq != null ? "faq" : "biz";
                if (DeepSeekClient.configured()) {
                    String title = (appTitle == null || appTitle.isBlank()) ? "本系统" : clip(appTitle, 80);
                    StringBuilder sys = new StringBuilder();
                    sys.append("你是「").append(title).append("」的智能助手。");
                    sys.append("只能依据下方提供的【业务数据】与【知识摘录】用简洁中文回答，");
                    sys.append("可稍作口语化改写，不得编造列表中不存在的商品/订单/工单，");
                    sys.append("不得写诗、写代码或闲聊，不得替用户下单或改状态。");
                    if (bizExcerpt != null && !bizExcerpt.isBlank()) {
                        sys.append("\n【业务数据】\n").append(clip(bizExcerpt, 2500));
                    }
                    if (faq != null) {
                        sys.append("\n【知识摘录】标题：").append(faq.get("title"));
                        sys.append("\n分类：").append(faq.get("category"));
                        sys.append("\n内容：").append(faq.get("content"));
                    }
                    List<Map<String, String>> msgs = new ArrayList<>();
                    msgs.add(Map.of("role", "system", "content", sys.toString()));
                    msgs.add(Map.of("role", "user", "content", q));
                    String llm = DeepSeekClient.chat(msgs);
                    if (llm != null && !llm.isBlank()) {
                        answer = llm;
                        if (bizExcerpt != null && !bizExcerpt.isBlank() && faq != null) {
                            source = "deepseek+biz+faq";
                        } else if (bizExcerpt != null && !bizExcerpt.isBlank()) {
                            source = "deepseek+biz";
                        } else {
                            source = "deepseek+faq";
                        }
                    }
                }
                // 无 Key / LLM 失败：有 FAQ 则 FAQ 回落（契约）；勿让空货架 biz 抢答
                if (answer == null || answer.isBlank()) {
                    if (faq != null) {
                        answer = String.valueOf(faq.get("content"));
                        source = "faq";
                    } else if (bizExcerpt != null && !bizExcerpt.isBlank()) {
                        answer = bizExcerpt;
                        source = "biz";
                    }
                }
            }
        }

        Map<String, Object> assistant = saveMessage(username, "assistant", answer, source, cat);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("reply", assistant);
        out.put("source", source);
        out.put("faq", faq);
        out.put("biz", bizExcerpt != null && !bizExcerpt.isBlank());
        out.put("deepseekConfigured", DeepSeekClient.configured());
        return out;
    }

    public static Map<String, Object> saveMessage(
            String username, String role, String content, String source, String category) {
        if (!ready()) return null;
        String body = clip(content, MSG_MAX);
        if (body.isBlank()) return null;
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO sys_ai_message (username, role, content, source, category) VALUES (?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, username == null ? "" : username);
            ps.setString(2, role == null ? "user" : role);
            ps.setString(3, body);
            ps.setString(4, source == null ? "" : clip(source, 32));
            ps.setString(5, category == null ? "" : clip(category, 64));
            return ps;
        }, kh);
        Number key = kh.getKey();
        return getMessage(key == null ? 0L : key.longValue());
    }

    public static Map<String, Object> getMessage(long id) {
        if (!ready()) return null;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM sys_ai_message WHERE id=?", (rs, i) -> messageRow(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Map<String, Object> pageMessages(String username, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", List.of());
        out.put("total", 0);
        out.put("page", page < 1 ? 1 : page);
        out.put("size", size < 1 ? 20 : size);
        if (!ready() || username == null || username.isBlank()) return out;
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM sys_ai_message WHERE username=?", Integer.class, username);
        int t = total == null ? 0 : total;
        int offset = (page - 1) * size;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM sys_ai_message WHERE username=? ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> messageRow(rs), username, size, offset);
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> addFeedback(String username, Long messageId, boolean satisfied, String comment) {
        if (!ready()) return null;
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO sys_ai_feedback (username, message_id, satisfied, comment) VALUES (?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, username == null ? "" : username);
            if (messageId == null) ps.setObject(2, null);
            else ps.setLong(2, messageId);
            ps.setInt(3, satisfied ? 1 : 0);
            ps.setString(4, clip(comment, 255));
            return ps;
        }, kh);
        Map<String, Object> m = new LinkedHashMap<>();
        Number key = kh.getKey();
        m.put("id", key == null ? 0L : key.longValue());
        m.put("satisfied", satisfied);
        m.put("comment", clip(comment, 255));
        return m;
    }

    public static List<Map<String, Object>> hotKnowledge(int limit) {
        if (!ready()) return List.of();
        int n = limit < 1 ? 8 : Math.min(limit, 30);
        return db().query(
                "SELECT * FROM sys_ai_knowledge WHERE enabled=1 ORDER BY hit_count DESC, id DESC LIMIT ?",
                (rs, i) -> knowledgeRow(rs), n);
    }

    public static Map<String, Object> pageKnowledge(String category, int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", List.of());
        out.put("total", 0);
        out.put("page", page < 1 ? 1 : page);
        out.put("size", size < 1 ? 10 : size);
        if (!ready()) return out;
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String cat = category == null ? "" : category.trim();
        Integer total;
        List<Map<String, Object>> list;
        if (!cat.isBlank()) {
            total = db().queryForObject(
                    "SELECT COUNT(*) FROM sys_ai_knowledge WHERE category=?", Integer.class, cat);
            list = db().query(
                    "SELECT * FROM sys_ai_knowledge WHERE category=? ORDER BY id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> knowledgeRow(rs), cat, size, (page - 1) * size);
        } else {
            total = db().queryForObject("SELECT COUNT(*) FROM sys_ai_knowledge", Integer.class);
            list = db().query(
                    "SELECT * FROM sys_ai_knowledge ORDER BY id DESC LIMIT ? OFFSET ?",
                    (rs, i) -> knowledgeRow(rs), size, (page - 1) * size);
        }
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> getKnowledge(long id) {
        if (!ready()) return null;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM sys_ai_knowledge WHERE id=?", (rs, i) -> knowledgeRow(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Map<String, Object> saveKnowledge(Long id, Map<String, Object> body) {
        if (!ready() || body == null) return null;
        String category = clip(String.valueOf(body.getOrDefault("category", "通用")), 64);
        if (category.isBlank()) category = "通用";
        String title = clip(String.valueOf(body.getOrDefault("title", "")), 128);
        String content = clip(String.valueOf(body.getOrDefault("content", "")), CONTENT_MAX);
        String keywords = clip(String.valueOf(body.getOrDefault("keywords", "")), 255);
        boolean enabled = true;
        Object en = body.get("enabled");
        if (en instanceof Boolean b) enabled = b;
        else if (en != null) enabled = !"0".equals(String.valueOf(en)) && !"false".equalsIgnoreCase(String.valueOf(en));
        if (title.isBlank() || content.isBlank()) return null;
        if (id == null || id <= 0) {
            KeyHolder kh = new GeneratedKeyHolder();
            String finalCategory = category;
            int enabledFlag = enabled ? 1 : 0;
            db().update(con -> {
                PreparedStatement ps = con.prepareStatement(
                        "INSERT INTO sys_ai_knowledge (category, title, content, keywords, enabled) VALUES (?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, finalCategory);
                ps.setString(2, title);
                ps.setString(3, content);
                ps.setString(4, keywords);
                ps.setInt(5, enabledFlag);
                return ps;
            }, kh);
            Number key = kh.getKey();
            return getKnowledge(key == null ? 0L : key.longValue());
        }
        db().update(
                "UPDATE sys_ai_knowledge SET category=?, title=?, content=?, keywords=?, enabled=? WHERE id=?",
                category, title, content, keywords, enabled ? 1 : 0, id);
        return getKnowledge(id);
    }

    public static boolean deleteKnowledge(long id) {
        if (!ready()) return false;
        return db().update("DELETE FROM sys_ai_knowledge WHERE id=?", id) > 0;
    }

    public static Map<String, Object> stats() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("knowledgeCount", 0);
        out.put("messageCount", 0);
        out.put("feedbackCount", 0);
        out.put("satisfiedRate", 0);
        out.put("deepseekConfigured", DeepSeekClient.configured());
        out.put("hot", List.of());
        if (!ready()) return out;
        Integer kc = db().queryForObject("SELECT COUNT(*) FROM sys_ai_knowledge WHERE enabled=1", Integer.class);
        Integer mc = db().queryForObject("SELECT COUNT(*) FROM sys_ai_message", Integer.class);
        Integer fc = db().queryForObject("SELECT COUNT(*) FROM sys_ai_feedback", Integer.class);
        Integer sat = db().queryForObject("SELECT COUNT(*) FROM sys_ai_feedback WHERE satisfied=1", Integer.class);
        int f = fc == null ? 0 : fc;
        int s = sat == null ? 0 : sat;
        out.put("knowledgeCount", kc == null ? 0 : kc);
        out.put("messageCount", mc == null ? 0 : mc);
        out.put("feedbackCount", f);
        out.put("satisfiedRate", f == 0 ? 0 : Math.round(s * 1000.0 / f) / 10.0);
        out.put("hot", hotKnowledge(8));
        return out;
    }
}
