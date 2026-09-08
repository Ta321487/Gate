package com.thesis.capability;

import com.thesis.config.JdbcSupport;
import com.thesis.service.MessageStore;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** 能力 book_suggest：读者荐购单 → 审核通过/驳回台账（E-13）；不自动建档入库。 */
public final class BookSuggestStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final String TABLE = "book_suggest";
    private static final Set<String> STATUSES = Set.of("pending", "approved", "rejected");
    private static boolean enabled = false;

    private BookSuggestStore() {}

    public static void configure(boolean on) {
        enabled = on;
        if (enabled) ensureTable();
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static void ensureTable() {
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS " + TABLE + " ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "username VARCHAR(64) NOT NULL,"
                            + "title VARCHAR(200) NOT NULL,"
                            + "isbn VARCHAR(32) DEFAULT '',"
                            + "author VARCHAR(100) DEFAULT '',"
                            + "reason VARCHAR(512) DEFAULT '',"
                            + "status VARCHAR(16) NOT NULL DEFAULT 'pending',"
                            + "handler VARCHAR(64) DEFAULT '',"
                            + "handle_note VARCHAR(512) DEFAULT '',"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "handled_at DATETIME NULL,"
                            + "KEY idx_bs_user (username, id),"
                            + "KEY idx_bs_status (status, id)"
                            + ")");
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> submit(
            String username, String title, String isbn, String author, String reason) {
        require();
        String uid = username == null ? "" : username.trim();
        if (uid.isBlank()) throw new IllegalArgumentException("未登录");
        String t = title == null ? "" : title.trim();
        if (t.isBlank()) throw new IllegalArgumentException("请填写书名");
        if (t.length() > 200) t = t.substring(0, 200);
        String isbnV = isbn == null ? "" : isbn.trim();
        if (isbnV.length() > 32) isbnV = isbnV.substring(0, 32);
        String authorV = author == null ? "" : author.trim();
        if (authorV.length() > 100) authorV = authorV.substring(0, 100);
        String reasonV = reason == null ? "" : reason.trim();
        if (reasonV.length() > 512) reasonV = reasonV.substring(0, 512);
        String finalTitle = t;
        String finalIsbn = isbnV;
        String finalAuthor = authorV;
        String finalReason = reasonV;
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + TABLE
                            + " (username,title,isbn,author,reason,status,created_at) VALUES (?,?,?,?,?,'pending',?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, uid);
            ps.setString(2, finalTitle);
            ps.setString(3, finalIsbn);
            ps.setString(4, finalAuthor);
            ps.setString(5, finalReason);
            ps.setTimestamp(6, Timestamp.valueOf(LocalDateTime.now()));
            return ps;
        }, kh);
        Number key = kh.getKey();
        long id = key == null ? 0L : key.longValue();
        try {
            MessageStore.notifyAdmins(
                    "新荐购申请",
                    "读者提交荐购「" + finalTitle + "」",
                    "book_suggest",
                    id,
                    uid);
        } catch (Exception ignored) {
        }
        return get(id);
    }

    public static Map<String, Object> pageMine(String username, int page, int size) {
        require();
        String uid = username == null ? "" : username.trim();
        if (uid.isBlank()) throw new IllegalArgumentException("未登录");
        return page(uid, "", page, size);
    }

    public static Map<String, Object> page(String username, String status, int page, int size) {
        require();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        String user = username == null ? "" : username.trim();
        if (!user.isBlank()) {
            where.append(" AND username=?");
            args.add(user);
        }
        String st = status == null ? "" : status.trim();
        if (!st.isBlank()) {
            if (!STATUSES.contains(st)) throw new IllegalArgumentException("状态无效");
            where.append(" AND status=?");
            args.add(st);
        }
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM " + TABLE + where, Integer.class, args.toArray());
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(size);
        pageArgs.add((page - 1) * size);
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM " + TABLE + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> mapRow(rs),
                pageArgs.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", rows == null ? List.of() : rows);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> resolve(long id, String action, String handler, String note) {
        require();
        Map<String, Object> row = get(id);
        if (row == null) throw new IllegalArgumentException("荐购单不存在");
        if (!"pending".equals(String.valueOf(row.get("status")))) {
            throw new IllegalStateException("该荐购单已处理");
        }
        String act = action == null ? "" : action.trim();
        if (!"approve".equals(act) && !"reject".equals(act)) {
            throw new IllegalStateException("处理方式须为通过或驳回");
        }
        String noteV = note == null ? "" : note.trim();
        if ("reject".equals(act) && noteV.isBlank()) {
            throw new IllegalArgumentException("驳回请填写说明");
        }
        if (noteV.length() > 512) noteV = noteV.substring(0, 512);
        String status = "approve".equals(act) ? "approved" : "rejected";
        db().update(
                "UPDATE " + TABLE
                        + " SET status=?, handler=?, handle_note=?, handled_at=NOW() WHERE id=?",
                status,
                handler == null ? "" : handler.trim(),
                noteV,
                id);
        Map<String, Object> updated = get(id);
        String title = updated == null ? "" : String.valueOf(updated.getOrDefault("title", ""));
        String un = updated == null ? "" : String.valueOf(updated.getOrDefault("username", ""));
        try {
            if ("approved".equals(status)) {
                MessageStore.send(
                        un,
                        "荐购已通过",
                        "您荐购的「" + title + "」已通过审核，已记入馆方台账。",
                        "book_suggest",
                        id);
            } else {
                MessageStore.send(
                        un,
                        "荐购未通过",
                        "您荐购的「" + title + "」未通过：" + noteV,
                        "book_suggest",
                        id);
            }
        } catch (Exception ignored) {
        }
        return updated;
    }

    public static Map<String, Object> get(long id) {
        try {
            return db().queryForObject(
                    "SELECT * FROM " + TABLE + " WHERE id=?",
                    (rs, i) -> mapRow(rs),
                    id);
        } catch (Exception e) {
            return null;
        }
    }

    private static void require() {
        if (!enabled) throw new IllegalStateException("荐购功能暂不可用");
    }

    private static Map<String, Object> mapRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("title", rs.getString("title"));
        m.put("isbn", rs.getString("isbn"));
        m.put("author", rs.getString("author"));
        m.put("reason", rs.getString("reason"));
        m.put("status", rs.getString("status"));
        m.put("handler", rs.getString("handler"));
        m.put("handleNote", rs.getString("handle_note"));
        Timestamp c = rs.getTimestamp("created_at");
        m.put("createdAt", c == null ? null : c.toLocalDateTime().format(FMT));
        Timestamp h = rs.getTimestamp("handled_at");
        m.put("handledAt", h == null ? null : h.toLocalDateTime().format(FMT));
        return m;
    }
}
