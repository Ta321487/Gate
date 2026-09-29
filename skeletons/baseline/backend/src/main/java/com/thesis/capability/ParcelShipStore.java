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

/** 能力 parcel_ship：用户寄件登记 → 店员受理 → 已寄出。 */
public final class ParcelShipStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final String TABLE = "parcel_ship";
    private static final Set<String> STATUSES = Set.of("pending", "accepted", "shipped", "rejected");
    private static boolean enabled = false;

    private ParcelShipStore() {}

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
                            + "receiver_name VARCHAR(64) NOT NULL DEFAULT '',"
                            + "receiver_phone VARCHAR(32) NOT NULL DEFAULT '',"
                            + "dest_address VARCHAR(255) NOT NULL DEFAULT '',"
                            + "item_desc VARCHAR(255) NOT NULL DEFAULT '',"
                            + "status VARCHAR(16) NOT NULL DEFAULT 'pending',"
                            + "tracking_no VARCHAR(64) DEFAULT '',"
                            + "handler VARCHAR(64) DEFAULT '',"
                            + "handle_note VARCHAR(512) DEFAULT '',"
                            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                            + "handled_at DATETIME NULL,"
                            + "KEY idx_ps_user (username, id),"
                            + "KEY idx_ps_status (status, id)"
                            + ")");
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> submit(
            String username,
            String receiverName,
            String receiverPhone,
            String destAddress,
            String itemDesc) {
        require();
        String uid = username == null ? "" : username.trim();
        if (uid.isBlank()) throw new IllegalArgumentException("未登录");
        String name = trim(receiverName, 64);
        if (name.isBlank()) throw new IllegalArgumentException("请填写收件人");
        String phone = trim(receiverPhone, 32);
        if (phone.isBlank()) throw new IllegalArgumentException("请填写收件电话");
        String addr = trim(destAddress, 255);
        if (addr.isBlank()) throw new IllegalArgumentException("请填写收件地址");
        String desc = trim(itemDesc, 255);
        if (desc.isBlank()) throw new IllegalArgumentException("请填写物品说明");
        String finalName = name;
        String finalPhone = phone;
        String finalAddr = addr;
        String finalDesc = desc;
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + TABLE
                            + " (username,receiver_name,receiver_phone,dest_address,item_desc,status,created_at)"
                            + " VALUES (?,?,?,?,?,'pending',?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, uid);
            ps.setString(2, finalName);
            ps.setString(3, finalPhone);
            ps.setString(4, finalAddr);
            ps.setString(5, finalDesc);
            ps.setTimestamp(6, Timestamp.valueOf(LocalDateTime.now()));
            return ps;
        }, kh);
        Number key = kh.getKey();
        long id = key == null ? 0L : key.longValue();
        try {
            MessageStore.notifyAdmins(
                    "新寄件登记",
                    "用户提交寄件「" + finalDesc + "」",
                    "parcel_ship",
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

    public static Map<String, Object> resolve(
            long id, String action, String handler, String note, String trackingNo) {
        require();
        Map<String, Object> row = get(id);
        if (row == null) throw new IllegalArgumentException("寄件单不存在");
        String cur = String.valueOf(row.get("status"));
        String act = action == null ? "" : action.trim();
        String op = handler == null ? "" : handler.trim();
        String noteV = note == null ? "" : note.trim();
        if (noteV.length() > 512) noteV = noteV.substring(0, 512);
        String track = trackingNo == null ? "" : trackingNo.trim();
        if (track.length() > 64) track = track.substring(0, 64);
        String desc = String.valueOf(row.getOrDefault("itemDesc", ""));
        String un = String.valueOf(row.getOrDefault("username", ""));

        if ("accept".equals(act)) {
            if (!"pending".equals(cur)) throw new IllegalStateException("当前状态不可受理");
            db().update(
                    "UPDATE " + TABLE + " SET status='accepted', handler=?, handled_at=NOW() WHERE id=?",
                    op, id);
            try {
                MessageStore.send(un, "寄件已受理", "您的寄件「" + desc + "」已受理，请到站交件。", "parcel_ship", id);
            } catch (Exception ignored) {
            }
        } else if ("ship".equals(act)) {
            if (!"accepted".equals(cur)) throw new IllegalStateException("请先受理再登记寄出");
            db().update(
                    "UPDATE " + TABLE
                            + " SET status='shipped', tracking_no=?, handler=?, handled_at=NOW() WHERE id=?",
                    track, op, id);
            try {
                String body = "您的寄件「" + desc + "」已寄出。";
                if (!track.isBlank()) body += "运单号：" + track;
                MessageStore.send(un, "寄件已寄出", body, "parcel_ship", id);
            } catch (Exception ignored) {
            }
        } else if ("reject".equals(act)) {
            if (!"pending".equals(cur)) throw new IllegalStateException("当前状态不可驳回");
            if (noteV.isBlank()) throw new IllegalArgumentException("驳回请填写说明");
            db().update(
                    "UPDATE " + TABLE
                            + " SET status='rejected', handler=?, handle_note=?, handled_at=NOW() WHERE id=?",
                    op, noteV, id);
            try {
                MessageStore.send(un, "寄件未受理", "您的寄件「" + desc + "」未受理：" + noteV, "parcel_ship", id);
            } catch (Exception ignored) {
            }
        } else {
            throw new IllegalStateException("处理方式须为受理、寄出或驳回");
        }
        return get(id);
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
        if (!enabled) throw new IllegalStateException("寄件功能暂不可用");
    }

    private static String trim(String v, int max) {
        String s = v == null ? "" : v.trim();
        if (s.length() > max) s = s.substring(0, max);
        return s;
    }

    private static Map<String, Object> mapRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("receiverName", rs.getString("receiver_name"));
        m.put("receiverPhone", rs.getString("receiver_phone"));
        m.put("destAddress", rs.getString("dest_address"));
        m.put("itemDesc", rs.getString("item_desc"));
        m.put("status", rs.getString("status"));
        m.put("trackingNo", rs.getString("tracking_no"));
        m.put("handler", rs.getString("handler"));
        m.put("handleNote", rs.getString("handle_note"));
        Timestamp c = rs.getTimestamp("created_at");
        m.put("createdAt", c == null ? null : c.toLocalDateTime().format(FMT));
        Timestamp h = rs.getTimestamp("handled_at");
        m.put("handledAt", h == null ? null : h.toLocalDateTime().format(FMT));
        return m;
    }
}
