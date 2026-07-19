package com.thesis.capability;

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
 * 能力 archive：分类 + 业务对象 CRUD / 检索 / 库存字段。
 * 默认表名兼容 LIBRARY（category / book）；其它领域可 bind 换表。
 */
public final class ArchiveStore {

    private static String CAT = "category";
    private static String ITEM = "book";
    private static Boolean hasStartAt;
    private static Boolean hasEndAt;
    private static Boolean hasApplyDeadline;
    private static Boolean hasMutexCode;
    private static Boolean hasDeletedAt;
    private static Boolean hasCheckinCode;
    private static boolean softDeleteEnabled = false;
    private static String TAG = "";
    private static String ITEM_TAG = "";
    private static String itemTagFk = "post_id";

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private ArchiveStore() {}

    /** 换表（新领域薄落地时调用一次） */
    public static void bind(String categoryTable, String itemTable) {
        if (categoryTable != null && !categoryTable.isBlank()) CAT = categoryTable.trim();
        if (itemTable != null && !itemTable.isBlank()) ITEM = itemTable.trim();
        hasStartAt = null;
        hasEndAt = null;
        hasApplyDeadline = null;
        hasMutexCode = null;
        hasDeletedAt = null;
        hasCheckinCode = null;
        TAG = "";
        ITEM_TAG = "";
    }

    public static void configureSoftDelete(boolean enabled) {
        softDeleteEnabled = enabled;
        if (enabled) ensureSoftDeleteColumn();
    }

    /** L1 标签：FORUM 的 tag + post_tag */
    public static void bindTags(String tagTable, String itemTagTable) {
        TAG = tagTable == null ? "" : tagTable.trim();
        ITEM_TAG = itemTagTable == null ? "" : itemTagTable.trim();
        if (!ITEM_TAG.isBlank()) {
            itemTagFk = ITEM_TAG.contains("post") ? "post_id" : "item_id";
        }
    }

    public static boolean tagsEnabled() {
        return TAG != null && !TAG.isBlank() && ITEM_TAG != null && !ITEM_TAG.isBlank();
    }

    public static String categoryTable() {
        return CAT;
    }

    public static String itemTable() {
        return ITEM;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o);
        return (s.isBlank() || "null".equals(s)) ? null : s;
    }

    private static long toLong(Object o) {
        if (o == null) return 0L;
        if (o instanceof Number n) return n.longValue();
        return Long.parseLong(String.valueOf(o));
    }

    private static int toInt(Object o) {
        if (o == null) return 0;
        if (o instanceof Number n) return n.intValue();
        return Integer.parseInt(String.valueOf(o));
    }

    public static long addCategory(String name) {
        String n = name == null ? "" : name.trim();
        if (n.isBlank()) throw new IllegalArgumentException("分类名不能为空");
        Integer dup = db().queryForObject("SELECT COUNT(*) FROM " + CAT + " WHERE name=?", Integer.class, n);
        if (dup != null && dup > 0) throw new IllegalStateException("分类名已存在");
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + CAT + " (name) VALUES (?)", Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, n);
            return ps;
        }, kh);
        Number key = kh.getKey();
        return key == null ? 0L : key.longValue();
    }

    public static Map<String, Object> createCategory(String name) {
        long id = addCategory(name);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("name", name.trim());
        m.put("bookCount", 0);
        return m;
    }

    public static Map<String, Object> updateCategory(long id, String name) {
        Integer exists = db().queryForObject("SELECT COUNT(*) FROM " + CAT + " WHERE id=?", Integer.class, id);
        if (exists == null || exists == 0) throw new IllegalArgumentException("分类不存在");
        String n = name == null ? "" : name.trim();
        if (n.isBlank()) throw new IllegalArgumentException("分类名不能为空");
        Integer dup = db().queryForObject(
                "SELECT COUNT(*) FROM " + CAT + " WHERE name=? AND id<>?", Integer.class, n, id);
        if (dup != null && dup > 0) throw new IllegalStateException("分类名已存在");
        db().update("UPDATE " + CAT + " SET name=? WHERE id=?", n, id);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("name", n);
        return m;
    }

    public static void deleteCategory(long id) {
        Integer exists = db().queryForObject("SELECT COUNT(*) FROM " + CAT + " WHERE id=?", Integer.class, id);
        if (exists == null || exists == 0) throw new IllegalArgumentException("分类不存在");
        Integer used = db().queryForObject(
                softDeleteEnabled && hasDeletedAt()
                        ? "SELECT COUNT(*) FROM " + ITEM + " WHERE category_id=? AND deleted_at IS NULL"
                        : "SELECT COUNT(*) FROM " + ITEM + " WHERE category_id=?",
                Integer.class, id);
        if (used != null && used > 0) {
            throw new IllegalStateException("该分类下仍有 " + used + " 条记录，无法删除");
        }
        db().update("DELETE FROM " + CAT + " WHERE id=?", id);
    }

    public static List<Map<String, Object>> listCategories() {
        String cntSql = softDeleteEnabled && hasDeletedAt()
                ? "(SELECT COUNT(*) FROM " + ITEM + " b WHERE b.category_id=c.id AND b.deleted_at IS NULL)"
                : "(SELECT COUNT(*) FROM " + ITEM + " b WHERE b.category_id=c.id)";
        return db().query(
                "SELECT c.id, c.name, " + cntSql + " AS item_count "
                        + "FROM " + CAT + " c ORDER BY c.id",
                (rs, i) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getLong("id"));
                    row.put("name", rs.getString("name"));
                    long cnt = rs.getLong("item_count");
                    row.put("bookCount", cnt);
                    row.put("itemCount", cnt);
                    return row;
                });
    }

    public static Map<String, Object> addItem(String title, String author, String isbn, long categoryId, int stock, String coverUrl) {
        return addItem(title, author, isbn, categoryId, stock, coverUrl, null);
    }

    public static Map<String, Object> addItem(
            String title, String author, String isbn, long categoryId, int stock, String coverUrl, Map<String, Object> extra) {
        String status = stock > 0 ? "available" : "unavailable";
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + ITEM + " (title,author,isbn,category_id,stock,status,cover_url) VALUES (?,?,?,?,?,?,?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, title);
            ps.setString(2, author);
            ps.setString(3, isbn);
            ps.setLong(4, categoryId);
            ps.setInt(5, stock);
            ps.setString(6, status);
            ps.setString(7, coverUrl == null ? "" : coverUrl);
            return ps;
        }, kh);
        Number key = kh.getKey();
        long id = key == null ? 0L : key.longValue();
        if (extra != null && id > 0) {
            updateItem(id, extra);
        }
        return getItem(id);
    }

    public static Map<String, Object> updateItem(long id, Map<String, Object> patch) {
        Map<String, Object> m = getItemRaw(id);
        if (m == null) return null;
        String title = patch.containsKey("title") && patch.get("title") != null
                ? String.valueOf(patch.get("title")) : String.valueOf(m.get("title"));
        String author = patch.containsKey("author") && patch.get("author") != null
                ? String.valueOf(patch.get("author")) : String.valueOf(m.get("author"));
        String isbn = patch.containsKey("isbn") && patch.get("isbn") != null
                ? String.valueOf(patch.get("isbn")) : String.valueOf(m.get("isbn"));
        String cover = patch.containsKey("coverUrl") && patch.get("coverUrl") != null
                ? String.valueOf(patch.get("coverUrl")) : String.valueOf(m.get("coverUrl"));
        long categoryId = patch.get("categoryId") != null
                ? toLong(patch.get("categoryId")) : toLong(m.get("categoryId"));
        int stock = patch.get("stock") != null ? toInt(patch.get("stock")) : toInt(m.get("stock"));
        String status = stock > 0 ? "available" : "unavailable";
        db().update(
                "UPDATE " + ITEM + " SET title=?, author=?, isbn=?, category_id=?, stock=?, status=?, cover_url=? WHERE id=?",
                title, author, isbn, categoryId, stock, status, cover, id);
        if (hasStartAt()) {
            Timestamp ts = parseTs(patch.containsKey("startAt") ? patch.get("startAt") : m.get("startAt"));
            db().update("UPDATE " + ITEM + " SET start_at=? WHERE id=?", ts, id);
        }
        if (hasEndAt()) {
            Timestamp ts = parseTs(patch.containsKey("endAt") ? patch.get("endAt") : m.get("endAt"));
            db().update("UPDATE " + ITEM + " SET end_at=? WHERE id=?", ts, id);
        }
        if (hasApplyDeadline()) {
            Timestamp ts = parseTs(patch.containsKey("applyDeadlineAt") ? patch.get("applyDeadlineAt") : m.get("applyDeadlineAt"));
            db().update("UPDATE " + ITEM + " SET apply_deadline_at=? WHERE id=?", ts, id);
        }
        if (hasMutexCode()) {
            String code = patch.containsKey("mutexCode")
                    ? str(patch.get("mutexCode")).trim()
                    : str(m.get("mutexCode")).trim();
            if (code.length() > 32) code = code.substring(0, 32);
            db().update("UPDATE " + ITEM + " SET mutex_code=? WHERE id=?", code, id);
        }
        if (hasCheckinCode()) {
            String code = patch.containsKey("checkinCode")
                    ? str(patch.get("checkinCode")).trim()
                    : str(m.get("checkinCode")).trim();
            if (code.length() > 16) code = code.substring(0, 16);
            db().update("UPDATE " + ITEM + " SET checkin_code=? WHERE id=?", code, id);
        }
        if (patch.containsKey("tagIds") && tagsEnabled()) {
            syncItemTags(id, patch.get("tagIds"));
        }
        return getItemAdmin(id);
    }

    public static boolean deleteItem(long id) {
        if (softDeleteEnabled && hasDeletedAt()) {
            return db().update("UPDATE " + ITEM + " SET deleted_at=NOW() WHERE id=? AND deleted_at IS NULL", id) > 0;
        }
        if (tagsEnabled()) {
            try {
                db().update("DELETE FROM " + ITEM_TAG + " WHERE " + itemTagFk + "=?", id);
            } catch (Exception ignored) {
            }
        }
        return db().update("DELETE FROM " + ITEM + " WHERE id=?", id) > 0;
    }

    public static boolean restoreItem(long id) {
        if (!hasDeletedAt()) return false;
        return db().update("UPDATE " + ITEM + " SET deleted_at=NULL WHERE id=?", id) > 0;
    }

    public static Map<String, Object> getItemRaw(long id) {
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + ITEM + " WHERE id=?",
                (rs, i) -> mapItemRow(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    /** 用户侧：已下架视为不存在 */
    public static Map<String, Object> getItem(long id) {
        Map<String, Object> m = getItemRaw(id);
        if (m == null) return null;
        if (isSoftDeleted(m)) return null;
        return enrichItem(m);
    }

    /** 管理侧：含已下架 */
    public static Map<String, Object> getItemAdmin(long id) {
        Map<String, Object> m = getItemRaw(id);
        return m == null ? null : enrichItem(m);
    }

    public static Map<String, Object> pageItems(String keyword, Long categoryId, int page, int size) {
        return pageItems(keyword, categoryId, null, false, page, size);
    }

    public static Map<String, Object> pageItems(
            String keyword, Long categoryId, List<Long> tagIds, boolean includeDeleted, int page, int size) {
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        if (hasDeletedAt() && !(includeDeleted && softDeleteEnabled)) {
            where.append(" AND deleted_at IS NULL");
        }
        if (categoryId != null && categoryId > 0) {
            where.append(" AND category_id=?");
            args.add(categoryId);
        }
        if (keyword != null && !keyword.isBlank()) {
            where.append(" AND (title LIKE ? OR author LIKE ? OR isbn LIKE ?)");
            String like = "%" + keyword.trim() + "%";
            args.add(like);
            args.add(like);
            args.add(like);
        }
        if (tagIds != null && !tagIds.isEmpty() && tagsEnabled()) {
            for (Long tid : tagIds) {
                if (tid == null || tid <= 0) continue;
                where.append(" AND EXISTS (SELECT 1 FROM ").append(ITEM_TAG)
                        .append(" it WHERE it.").append(itemTagFk).append("=").append(ITEM)
                        .append(".id AND it.tag_id=?)");
                args.add(tid);
            }
        }
        Integer total = db().queryForObject("SELECT COUNT(*) FROM " + ITEM + where, Integer.class, args.toArray());
        int t = total == null ? 0 : total;
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + ITEM + where + " ORDER BY id LIMIT ? OFFSET ?",
                (rs, i) -> enrichItem(mapItemRow(rs)), args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static Map<String, Object> mapItemRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("title", rs.getString("title"));
        m.put("author", rs.getString("author"));
        m.put("isbn", rs.getString("isbn"));
        m.put("categoryId", rs.getLong("category_id"));
        m.put("stock", rs.getInt("stock"));
        m.put("status", rs.getString("status"));
        m.put("coverUrl", rs.getString("cover_url"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        if (hasStartAt()) m.put("startAt", fmt(rs.getTimestamp("start_at")));
        if (hasEndAt()) m.put("endAt", fmt(rs.getTimestamp("end_at")));
        if (hasApplyDeadline()) m.put("applyDeadlineAt", fmt(rs.getTimestamp("apply_deadline_at")));
        if (hasMutexCode()) {
            try {
                m.put("mutexCode", rs.getString("mutex_code") == null ? "" : rs.getString("mutex_code"));
            } catch (Exception ignored) {
                m.put("mutexCode", "");
            }
        }
        if (hasDeletedAt()) {
            try {
                m.put("deletedAt", fmt(rs.getTimestamp("deleted_at")));
            } catch (Exception ignored) {
                m.put("deletedAt", null);
            }
        }
        if (hasCheckinCode()) {
            try {
                m.put("checkinCode", rs.getString("checkin_code") == null ? "" : rs.getString("checkin_code"));
            } catch (Exception ignored) {
                m.put("checkinCode", "");
            }
        }
        return m;
    }

    private static boolean isSoftDeleted(Map<String, Object> m) {
        if (!softDeleteEnabled || !hasDeletedAt()) return false;
        Object d = m.get("deletedAt");
        return d != null && !String.valueOf(d).isBlank() && !"null".equalsIgnoreCase(String.valueOf(d));
    }

    private static Map<String, Object> enrichItem(Map<String, Object> b) {
        Map<String, Object> m = new LinkedHashMap<>(b);
        long cid = toLong(b.get("categoryId"));
        List<String> names = db().query(
                "SELECT name FROM " + CAT + " WHERE id=?", (rs, i) -> rs.getString(1), cid);
        m.put("categoryName", names.isEmpty() ? "" : names.get(0));
        m.put("deleted", isSoftDeleted(m));
        if (tagsEnabled()) {
            long id = toLong(b.get("id"));
            List<Map<String, Object>> tags = db().query(
                    "SELECT t.id, t.name FROM " + TAG + " t JOIN " + ITEM_TAG + " it ON it.tag_id=t.id "
                            + "WHERE it." + itemTagFk + "=? ORDER BY t.id",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("id", rs.getLong("id"));
                        row.put("name", rs.getString("name"));
                        return row;
                    }, id);
            List<Long> ids = new ArrayList<>();
            List<String> tnames = new ArrayList<>();
            for (Map<String, Object> t : tags) {
                ids.add(toLong(t.get("id")));
                tnames.add(str(t.get("name")));
            }
            m.put("tagIds", ids);
            m.put("tagNames", tnames);
            m.put("tags", tags);
        }
        return m;
    }

    public static boolean hasScheduleColumns() {
        return hasStartAt() && hasEndAt();
    }

    public static boolean hasStartAt() {
        if (hasStartAt == null) hasStartAt = hasItemColumn("start_at");
        return hasStartAt;
    }

    public static boolean hasEndAt() {
        if (hasEndAt == null) hasEndAt = hasItemColumn("end_at");
        return hasEndAt;
    }

    public static boolean hasApplyDeadline() {
        if (hasApplyDeadline == null) hasApplyDeadline = hasItemColumn("apply_deadline_at");
        return hasApplyDeadline;
    }

    public static boolean hasMutexCode() {
        if (hasMutexCode == null) hasMutexCode = hasItemColumn("mutex_code");
        return hasMutexCode;
    }

    public static boolean hasDeletedAt() {
        if (hasDeletedAt == null) hasDeletedAt = hasItemColumn("deleted_at");
        return hasDeletedAt;
    }

    public static boolean hasCheckinCode() {
        if (hasCheckinCode == null) hasCheckinCode = hasItemColumn("checkin_code");
        return hasCheckinCode;
    }

    /** L1 互斥：缺列时补上（选课域 bake 后亦应有 SQL 列） */
    public static void ensureMutexColumn() {
        if (hasMutexCode()) return;
        try {
            db().execute("ALTER TABLE `" + ITEM + "` ADD COLUMN `mutex_code` VARCHAR(32) NOT NULL DEFAULT ''");
            hasMutexCode = true;
        } catch (Exception ignored) {
            hasMutexCode = hasItemColumn("mutex_code");
        }
    }

    public static void ensureSoftDeleteColumn() {
        if (hasDeletedAt()) return;
        try {
            db().execute("ALTER TABLE `" + ITEM + "` ADD COLUMN `deleted_at` DATETIME NULL");
            hasDeletedAt = true;
        } catch (Exception ignored) {
            hasDeletedAt = hasItemColumn("deleted_at");
        }
    }

    public static void ensureCheckinCodeColumn() {
        if (hasCheckinCode()) return;
        try {
            db().execute("ALTER TABLE `" + ITEM + "` ADD COLUMN `checkin_code` VARCHAR(16) NOT NULL DEFAULT ''");
            hasCheckinCode = true;
        } catch (Exception ignored) {
            hasCheckinCode = hasItemColumn("checkin_code");
        }
    }

    public static List<Map<String, Object>> listTags() {
        if (!tagsEnabled()) return List.of();
        return db().query(
                "SELECT id, name FROM " + TAG + " ORDER BY id",
                (rs, i) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getLong("id"));
                    row.put("name", rs.getString("name"));
                    return row;
                });
    }

    @SuppressWarnings("unchecked")
    private static void syncItemTags(long itemId, Object raw) {
        if (!tagsEnabled()) return;
        List<Long> ids = new ArrayList<>();
        if (raw instanceof List<?> list) {
            for (Object o : list) {
                long id = toLong(o);
                if (id > 0) ids.add(id);
            }
        } else if (raw instanceof String s && !s.isBlank()) {
            for (String part : s.split("[,\\s]+")) {
                try {
                    long id = Long.parseLong(part.trim());
                    if (id > 0) ids.add(id);
                } catch (Exception ignored) {
                }
            }
        }
        db().update("DELETE FROM " + ITEM_TAG + " WHERE " + itemTagFk + "=?", itemId);
        for (Long tid : ids) {
            try {
                db().update(
                        "INSERT INTO " + ITEM_TAG + " (" + itemTagFk + ", tag_id) VALUES (?,?)",
                        itemId, tid);
            } catch (Exception ignored) {
            }
        }
    }

    private static boolean hasItemColumn(String col) {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=? AND COLUMN_NAME=?",
                    Integer.class, ITEM, col);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static Timestamp parseTs(Object o) {
        if (o == null) return null;
        String s = String.valueOf(o).trim();
        if (s.isBlank() || "null".equalsIgnoreCase(s)) return null;
        try {
            if (s.contains("T")) s = s.replace('T', ' ');
            if (s.length() == 16) s = s + ":00";
            return Timestamp.valueOf(LocalDateTime.parse(s.substring(0, Math.min(19, s.length())), FMT));
        } catch (Exception e) {
            try {
                return Timestamp.valueOf(s.substring(0, Math.min(19, s.length())));
            } catch (Exception e2) {
                return null;
            }
        }
    }

    public static void adjustStock(long itemId, int delta) {
        Map<String, Object> book = getItemRaw(itemId);
        if (book == null || isSoftDeleted(book)) throw new IllegalStateException("对象不存在");
        int stock = toInt(book.get("stock")) + delta;
        if (stock < 0) throw new IllegalStateException("库存不足");
        db().update(
                "UPDATE " + ITEM + " SET stock=?, status=? WHERE id=?",
                stock, stock > 0 ? "available" : "unavailable", itemId);
    }

    public static long countItems() {
        if (softDeleteEnabled && hasDeletedAt()) {
            Long n = db().queryForObject(
                    "SELECT COUNT(*) FROM " + ITEM + " WHERE deleted_at IS NULL", Long.class);
            return n == null ? 0 : n;
        }
        Long n = db().queryForObject("SELECT COUNT(*) FROM " + ITEM, Long.class);
        return n == null ? 0 : n;
    }

    public static long sumStock() {
        if (softDeleteEnabled && hasDeletedAt()) {
            Long n = db().queryForObject(
                    "SELECT COALESCE(SUM(stock),0) FROM " + ITEM + " WHERE deleted_at IS NULL", Long.class);
            return n == null ? 0 : n;
        }
        Long n = db().queryForObject("SELECT COALESCE(SUM(stock),0) FROM " + ITEM, Long.class);
        return n == null ? 0 : n;
    }

    public static long countCategories() {
        Long n = db().queryForObject("SELECT COUNT(*) FROM " + CAT, Long.class);
        return n == null ? 0 : n;
    }

    /** 分类库存柱状图：名称 + 库存合计。 */
    public static List<Map<String, Object>> stockByCategory(int limit) {
        int lim = Math.max(1, Math.min(limit, 20));
        try {
            return db().query(
                    "SELECT c.name AS name, COALESCE(SUM(i.stock),0) AS value FROM " + CAT + " c"
                            + " LEFT JOIN " + ITEM + " i ON i.category_id=c.id"
                            + " GROUP BY c.id, c.name ORDER BY value DESC LIMIT " + lim,
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("name", rs.getString("name"));
                        row.put("value", rs.getLong("value"));
                        return row;
                    });
        } catch (Exception e) {
            return List.of();
        }
    }

    public static Long findCategoryIdByName(String name) {
        if (name == null || name.isBlank()) return null;
        List<Long> ids = db().query(
                "SELECT id FROM " + CAT + " WHERE name=? LIMIT 1",
                (rs, i) -> rs.getLong(1),
                name.trim());
        return ids.isEmpty() ? null : ids.get(0);
    }

    /**
     * CSV 行导入：title,author,isbn,category,stock。
     * category 按名称匹配，不存在则新建。
     */
    public static Map<String, Object> importRows(List<Map<String, String>> rows) {
        int ok = 0;
        List<Map<String, Object>> errors = new ArrayList<>();
        if (rows == null) rows = List.of();
        for (int i = 0; i < rows.size(); i++) {
            Map<String, String> row = rows.get(i);
            int lineNo = i + 2; // 含表头
            try {
                String title = str(row.get("title")).trim();
                if (title.isBlank()) throw new IllegalArgumentException("名称不能为空");
                String author = str(row.get("author")).trim();
                String isbn = str(row.get("isbn")).trim();
                String catName = str(row.get("category")).trim();
                if (catName.isBlank()) catName = "未分类";
                Long catId = findCategoryIdByName(catName);
                if (catId == null) {
                    catId = addCategory(catName);
                }
                int stock = 1;
                String stockRaw = str(row.get("stock")).trim();
                if (!stockRaw.isBlank()) {
                    stock = Integer.parseInt(stockRaw.replaceAll("[^0-9\\-]", ""));
                    if (stock < 0) stock = 0;
                }
                addItem(title, author, isbn, catId, stock, "");
                ok++;
            } catch (Exception ex) {
                Map<String, Object> err = new LinkedHashMap<>();
                err.put("line", lineNo);
                err.put("message", ex.getMessage() == null ? "导入失败" : ex.getMessage());
                errors.add(err);
                if (errors.size() >= 50) break;
            }
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("ok", ok);
        result.put("fail", errors.size());
        result.put("errors", errors);
        return result;
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }
}
