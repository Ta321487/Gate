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
import java.util.Map;

/**
 * 档案条下评论（item_comment）：挂在影音/曲目/文章下；≠ 门户留言 guestbook。
 */
public class ItemCommentStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int BODY_MAX = 500;
    private static Boolean tableReady;
    private static boolean authorNotifyEnabled = false;
    private static boolean followersOnlyOn = false;

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    /** C-04：新评论站内信通知文章作者。 */
    public static void configureAuthorNotify(boolean on) {
        authorNotifyEnabled = on;
    }

    /** C-08：评论仅粉丝可见。 */
    public static void configureFollowersOnly(boolean on) {
        followersOnlyOn = on;
    }

    public static boolean ready() {
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='item_comment'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    /** 测试或热切换后清缓存 */
    public static void resetReadyCache() {
        tableReady = null;
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

    private static Map<String, Object> row(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("itemId", rs.getLong("item_id"));
        m.put("username", rs.getString("username"));
        m.put("nickname", rs.getString("nickname"));
        m.put("body", rs.getString("body"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        try {
            Object pid = rs.getObject("parent_id");
            if (pid instanceof Number n && n.longValue() > 0) m.put("parentId", n.longValue());
        } catch (Exception ignored) {
        }
        try {
            m.put("likeCount", rs.getInt("like_count"));
        } catch (Exception ignored) {
            m.put("likeCount", 0);
        }
        try {
            m.put("followersOnly", rs.getInt("followers_only") == 1);
        } catch (Exception ignored) {
            m.put("followersOnly", false);
        }
        return m;
    }

    public static Map<String, Object> get(long id) {
        if (!ready()) return null;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM item_comment WHERE id=?", (rs, i) -> row(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Map<String, Object> add(long itemId, String username, String nickname, String body) {
        return add(itemId, username, nickname, body, null);
    }

    public static Map<String, Object> add(
            long itemId, String username, String nickname, String body, Long parentId) {
        return add(itemId, username, nickname, body, parentId, false);
    }

    public static Map<String, Object> add(
            long itemId,
            String username,
            String nickname,
            String body,
            Long parentId,
            boolean followersOnly) {
        if (!ready() || itemId <= 0) return null;
        String b = clip(body, BODY_MAX);
        if (b.isBlank()) return null;
        SensitiveWordGate.assertClean(b);
        long pid = parentId == null ? 0L : parentId;
        if (pid > 0) {
            Map<String, Object> parent = get(pid);
            if (parent == null) throw new IllegalArgumentException("回复对象不存在");
            if (toLong(parent.get("itemId")) != itemId) {
                throw new IllegalStateException("只能回复同一内容下的评论");
            }
            if (toLong(parent.get("parentId")) > 0) {
                throw new IllegalStateException("该回复下不能再盖楼");
            }
        }
        String nick = clip(nickname == null || nickname.isBlank() ? username : nickname, 64);
        int fo = followersOnlyOn && followersOnly ? 1 : 0;
        KeyHolder kh = new GeneratedKeyHolder();
        final long pidFinal = pid;
        final int foFinal = fo;
        db().update(con -> {
            boolean hasFo = hasFollowersOnlyCol();
            if (pidFinal > 0 && hasParentCol() && hasFo) {
                PreparedStatement ps = con.prepareStatement(
                        "INSERT INTO item_comment (item_id,username,nickname,body,parent_id,followers_only) VALUES (?,?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setLong(1, itemId);
                ps.setString(2, username == null ? "" : username);
                ps.setString(3, nick);
                ps.setString(4, b);
                ps.setLong(5, pidFinal);
                ps.setInt(6, foFinal);
                return ps;
            }
            if (pidFinal > 0 && hasParentCol()) {
                PreparedStatement ps = con.prepareStatement(
                        "INSERT INTO item_comment (item_id,username,nickname,body,parent_id) VALUES (?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setLong(1, itemId);
                ps.setString(2, username == null ? "" : username);
                ps.setString(3, nick);
                ps.setString(4, b);
                ps.setLong(5, pidFinal);
                return ps;
            }
            if (hasFo) {
                PreparedStatement ps = con.prepareStatement(
                        "INSERT INTO item_comment (item_id,username,nickname,body,followers_only) VALUES (?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setLong(1, itemId);
                ps.setString(2, username == null ? "" : username);
                ps.setString(3, nick);
                ps.setString(4, b);
                ps.setInt(5, foFinal);
                return ps;
            }
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO item_comment (item_id,username,nickname,body) VALUES (?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, itemId);
            ps.setString(2, username == null ? "" : username);
            ps.setString(3, nick);
            ps.setString(4, b);
            return ps;
        }, kh);
        Number key = kh.getKey();
        long id = key == null ? 0L : key.longValue();
        Map<String, Object> created = get(id);
        try {
            MentionNotify.notifyFromText(username, b, "item_comment", id, "评论");
        } catch (Exception ignored) {
        }
        try {
            notifyAuthor(itemId, username, b);
        } catch (Exception ignored) {
        }
        return created;
    }

    private static void notifyAuthor(long itemId, String fromUser, String body) {
        if (!authorNotifyEnabled || itemId <= 0) return;
        Map<String, Object> item = com.thesis.capability.ArchiveStore.getItemRaw(itemId);
        if (item == null) return;
        String author = item.get("ownerUsername") == null ? "" : String.valueOf(item.get("ownerUsername")).trim();
        if (author.isBlank() && item.get("author") != null) {
            author = String.valueOf(item.get("author")).trim();
        }
        String from = fromUser == null ? "" : fromUser.trim();
        if (author.isBlank() || author.equals(from)) return;
        String snippet = body == null ? "" : body.trim();
        if (snippet.length() > 40) snippet = snippet.substring(0, 40) + "…";
        MessageStore.send(
                author,
                "收到新评论",
                (from.isBlank() ? "有人" : from) + "评论了你的文章" + (snippet.isBlank() ? "。" : "：" + snippet),
                "archive",
                Long.valueOf(itemId));
    }

    private static boolean hasParentCol() {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.columns "
                            + "WHERE table_schema=DATABASE() AND table_name='item_comment' AND column_name='parent_id'",
                    Integer.class);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static boolean hasFollowersOnlyCol() {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.columns "
                            + "WHERE table_schema=DATABASE() AND table_name='item_comment' AND column_name='followers_only'",
                    Integer.class);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static long toLong(Object o) {
        if (o instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(o));
        } catch (Exception e) {
            return 0L;
        }
    }

    /** @return true=已赞 */
    public static boolean toggleLike(String username, long commentId) {
        if (!ready() || commentId <= 0 || username == null || username.isBlank()) return false;
        ensureCommentLikeTable();
        if (get(commentId) == null) throw new IllegalArgumentException("评论不存在");
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM user_comment_like WHERE username=? AND comment_id=?",
                Integer.class, username.trim(), commentId);
        if (n != null && n > 0) {
            db().update("DELETE FROM user_comment_like WHERE username=? AND comment_id=?",
                    username.trim(), commentId);
            bumpCommentLike(commentId, -1);
            return false;
        }
        db().update(
                "INSERT INTO user_comment_like (username,comment_id,created_at) VALUES (?,?,?)",
                username.trim(), commentId, Timestamp.valueOf(LocalDateTime.now()));
        bumpCommentLike(commentId, 1);
        return true;
    }

    private static void ensureCommentLikeTable() {
        try {
            db().execute(
                    "CREATE TABLE IF NOT EXISTS user_comment_like ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "username VARCHAR(64) NOT NULL,"
                            + "comment_id BIGINT NOT NULL,"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_ucl (username, comment_id)"
                            + ")");
        } catch (Exception ignored) {
        }
        try {
            db().execute("ALTER TABLE item_comment ADD COLUMN like_count INT NOT NULL DEFAULT 0");
        } catch (Exception ignored) {
        }
    }

    private static void bumpCommentLike(long commentId, int delta) {
        try {
            db().update(
                    "UPDATE item_comment SET like_count = GREATEST(0, COALESCE(like_count,0) + ?) WHERE id=?",
                    delta, commentId);
        } catch (Exception ignored) {
        }
    }

    public static boolean delete(long id) {
        if (!ready()) return false;
        return db().update("DELETE FROM item_comment WHERE id=?", id) > 0;
    }

    public static Map<String, Object> pageByItem(long itemId, int page, int size) {
        return pageByItem(itemId, page, size, null);
    }

    public static Map<String, Object> pageByItem(long itemId, int page, int size, String viewer) {
        Map<String, Object> out = emptyPage(page, size);
        if (!ready() || itemId <= 0) return out;
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM item_comment WHERE item_id=?", Integer.class, itemId);
        int t = total == null ? 0 : total;
        int offset = (page - 1) * size;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM item_comment WHERE item_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> row(rs),
                itemId, size, offset);
        if (followersOnlyOn) {
            String v = viewer == null ? "" : viewer.trim();
            List<Map<String, Object>> filtered = new ArrayList<>();
            for (Map<String, Object> c : list) {
                if (!Boolean.TRUE.equals(c.get("followersOnly"))) {
                    filtered.add(c);
                    continue;
                }
                String author = c.get("username") == null ? "" : String.valueOf(c.get("username")).trim();
                if (!v.isBlank() && (v.equals(author) || UserFollowStore.isFollowing(v, author))) {
                    filtered.add(c);
                }
            }
            list = filtered;
            t = filtered.size();
        }
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> pageAdmin(int page, int size, Long itemId) {
        Map<String, Object> out = emptyPage(page, size);
        if (!ready()) return out;
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        if (itemId != null && itemId > 0) {
            where.append(" AND item_id=?");
            args.add(itemId);
        }
        Integer total = db().queryForObject(
                "SELECT COUNT(*) FROM item_comment" + where, Integer.class, args.toArray());
        int t = total == null ? 0 : total;
        int offset = (page - 1) * size;
        List<Object> listArgs = new ArrayList<>(args);
        listArgs.add(size);
        listArgs.add(offset);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM item_comment" + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> row(rs),
                listArgs.toArray());
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static Map<String, Object> emptyPage(int page, int size) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", List.of());
        out.put("total", 0);
        out.put("page", page < 1 ? 1 : page);
        out.put("size", size < 1 ? 10 : size);
        return out;
    }
}
