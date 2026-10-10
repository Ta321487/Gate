package com.thesis.service;

import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.LinkedHashMap;
import java.util.Map;

/** C-08：用户互关浅表（评论仅粉丝可见）。 */
public final class UserFollowStore {

    private static boolean enabled;

    private UserFollowStore() {}

    public static void configure(boolean on) {
        enabled = on;
        if (on) ensureTable();
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
                    "CREATE TABLE IF NOT EXISTS user_follow ("
                            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
                            + "follower VARCHAR(64) NOT NULL,"
                            + "followee VARCHAR(64) NOT NULL,"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "UNIQUE KEY uk_uf_pair (follower, followee),"
                            + "KEY idx_uf_followee (followee))");
        } catch (Exception ignored) {
        }
    }

    public static boolean isFollowing(String follower, String followee) {
        if (!enabled || follower == null || followee == null) return false;
        String a = follower.trim();
        String b = followee.trim();
        if (a.isBlank() || b.isBlank() || a.equals(b)) return a.equals(b);
        ensureTable();
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM user_follow WHERE follower=? AND followee=?",
                    Integer.class, a, b);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    public static Map<String, Object> follow(String follower, String followee) {
        if (!enabled) throw new IllegalStateException("未开放关注");
        String a = follower == null ? "" : follower.trim();
        String b = followee == null ? "" : followee.trim();
        if (a.isBlank() || b.isBlank()) throw new IllegalArgumentException("用户无效");
        if (a.equals(b)) throw new IllegalArgumentException("不能关注自己");
        ensureTable();
        db().update("INSERT IGNORE INTO user_follow(follower, followee) VALUES(?,?)", a, b);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("follower", a);
        out.put("followee", b);
        out.put("following", true);
        return out;
    }

    public static Map<String, Object> unfollow(String follower, String followee) {
        if (!enabled) throw new IllegalStateException("未开放关注");
        String a = follower == null ? "" : follower.trim();
        String b = followee == null ? "" : followee.trim();
        ensureTable();
        db().update("DELETE FROM user_follow WHERE follower=? AND followee=?", a, b);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("follower", a);
        out.put("followee", b);
        out.put("following", false);
        return out;
    }
}
