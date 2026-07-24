package com.thesis.capability;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.config.DomainResourceJson;
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
    /** 逻辑键 author/isbn 对应的物理列（bake 写入 domain-archive-columns.json） */
    private static String COL_AUTHOR = "author";
    private static String COL_ISBN = "isbn";
    private static Boolean hasStartAt;
    private static Boolean hasEndAt;
    private static Boolean hasApplyDeadline;
    private static Boolean hasMutexCode;
    private static Boolean hasDeletedAt;
    private static Boolean hasCheckinCode;
    private static Boolean hasGalleryJson;
    private static boolean softDeleteEnabled = false;
    private static boolean userPublishEnabled = false;
    private static boolean galleryEnabled = false;
    private static String TAG = "";
    private static String ITEM_TAG = "";
    private static String itemTagFk = "post_id";
    /** bake 注入：库存/名额等列名，供不足提示复用 */
    private static String STOCK_LABEL = "库存";

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private ArchiveStore() {}

    public static void configureStockLabel(String label) {
        if (label != null && !label.isBlank()) STOCK_LABEL = label.trim();
    }

    public static String stockLabel() {
        return STOCK_LABEL == null || STOCK_LABEL.isBlank() ? "库存" : STOCK_LABEL;
    }

    public static String stockShortage(int remain) {
        return stockLabel() + "不足（剩余 " + remain + "）";
    }

    public static String stockShortageNeed(int need) {
        return stockLabel() + "不足，无法通过（需要 " + need + "）";
    }

    public static String stockShortageTitled(String title, int remain) {
        String t = title == null ? "" : title.trim();
        if (t.isBlank()) return stockShortage(remain);
        return stockLabel() + "不足：「" + t + "」仅剩 " + remain;
    }

    /** bake 写入的 domain-ticket-copy.json；无单据域也会有 stockLabel */
    private static void loadStockLabelFromResource() {
        Map<String, Object> root = DomainResourceJson.loadObjectMap("domain-ticket-copy.json");
        String lab = DomainResourceJson.str(root, "stockLabel", "");
        if (!lab.isBlank()) STOCK_LABEL = lab;
    }

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
        hasGalleryJson = null;
        TAG = "";
        ITEM_TAG = "";
        COL_AUTHOR = "author";
        COL_ISBN = "isbn";
        loadStockLabelFromResource();
        loadColumnMapFromResource();
    }

    private static void loadColumnMapFromResource() {
        Map<String, Object> root = DomainResourceJson.loadObjectMap("domain-archive-columns.json");
        COL_AUTHOR = DomainResourceJson.str(root, "authorColumn", "author");
        COL_ISBN = DomainResourceJson.str(root, "isbnColumn", "isbn");
    }

    /** 物理列名（SQL）；API JSON 仍用逻辑键 author / isbn */
    public static String authorColumn() {
        return COL_AUTHOR == null || COL_AUTHOR.isBlank() ? "author" : COL_AUTHOR;
    }

    public static String isbnColumn() {
        return COL_ISBN == null || COL_ISBN.isBlank() ? "isbn" : COL_ISBN;
    }

    public static void configureGallery(boolean enabled) {
        galleryEnabled = enabled;
        if (enabled) ensureGalleryColumn();
    }

    public static boolean galleryEnabled() {
        return galleryEnabled;
    }

    public static void configureSoftDelete(boolean enabled) {
        softDeleteEnabled = enabled;
        if (enabled) ensureSoftDeleteColumn();
    }

    public static boolean softDeleteEnabled() {
        return softDeleteEnabled;
    }

    public static void configureUserPublish(boolean enabled) {
        userPublishEnabled = enabled;
    }

    public static boolean userPublishEnabled() {
        return userPublishEnabled;
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
                    "INSERT INTO " + ITEM + " (title," + authorColumn() + "," + isbnColumn()
                            + ",category_id,stock,status,cover_url) VALUES (?,?,?,?,?,?,?)",
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

    /**
     * 门户用户发帖：即时上架（stock=1），作者列固定为登录名便于「我的主帖」归属。
     * 正文走 isbn 逻辑键（论坛/博客 schema bodyField → 物理 body_html）；站长下架走 soft-delete。
     */
    public static Map<String, Object> addUserPost(String username, String title, String body, long categoryId) {
        if (!userPublishEnabled) {
            throw new IllegalStateException("当前领域未开放用户发帖");
        }
        String uid = username == null ? "" : username.trim();
        if (uid.isBlank()) throw new IllegalArgumentException("未登录");
        String t = title == null ? "" : title.trim();
        if (t.isBlank()) throw new IllegalArgumentException("标题不能为空");
        long cat = categoryId > 0 ? categoryId : 1L;
        String content = body == null ? "" : body;
        return addItem(t, uid, content, cat, 1, "");
    }

    /** 本人主帖（含站长下架），按 id 倒序 */
    public static Map<String, Object> pageMine(String username, int page, int size) {
        if (!userPublishEnabled) {
            throw new IllegalStateException("当前领域未开放用户发帖");
        }
        String uid = username == null ? "" : username.trim();
        if (uid.isBlank()) throw new IllegalArgumentException("未登录");
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String where = " WHERE " + authorColumn() + "=?";
        Integer total = db().queryForObject("SELECT COUNT(*) FROM " + ITEM + where, Integer.class, uid);
        int t = total == null ? 0 : total;
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + ITEM + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> enrichItem(mapItemRow(rs)),
                uid, size, (page - 1) * size);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
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
                "UPDATE " + ITEM + " SET title=?, " + authorColumn() + "=?, " + isbnColumn()
                        + "=?, category_id=?, stock=?, status=?, cover_url=? WHERE id=?",
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
        if (galleryEnabled && hasGalleryJson() && patch.containsKey("galleryImages")) {
            db().update(
                    "UPDATE " + ITEM + " SET gallery_json=? WHERE id=?",
                    toGalleryJson(patch.get("galleryImages")), id);
        }
        patchOptStr(id, patch, "publisher", "publisher", 100);
        patchOptStr(id, patch, "callNo", "call_no", 64);
        patchOptStr(id, patch, "conditionGrade", "condition_grade", 16);
        patchOptStr(id, patch, "sellerNote", "seller_note", 255);
        patchOptStr(id, patch, "spicyLevel", "spicy_level", 16);
        patchOptInt(id, patch, "isVegetarian", "is_vegetarian");
        patchOptInt(id, patch, "requiresTraining", "requires_training");
        patchOptStr(id, patch, "ownerName", "owner_name", 64);
        patchOptStr(id, patch, "stage", "stage", 32);
        patchOptNum(id, patch, "credit", "credit");
        patchOptNum(id, patch, "serviceHours", "service_hours");
        patchOptInt(id, patch, "seatCapacity", "seat_capacity");
        patchOptStr(id, patch, "feeRule", "fee_rule", 64);
        patchOptStr(id, patch, "stylistName", "stylist_name", 32);
        patchOptInt(id, patch, "durationSec", "duration_sec");
        patchOptInt(id, patch, "releaseYear", "release_year");
        patchOptStr(id, patch, "region", "region", 64);
        patchOptStr(id, patch, "summary", "summary", 512);
        patchOptStr(id, patch, "itemKind", "item_kind", 16);
        if (patch.containsKey("foundAt")) {
            Timestamp ts = parseTs(patch.get("foundAt"));
            try {
                db().update("UPDATE " + ITEM + " SET found_at=? WHERE id=?", ts, id);
            } catch (Exception ignored) {
            }
        }
        if (patch.containsKey("tagIds") && tagsEnabled()) {
            syncItemTags(id, patch.get("tagIds"));
        }
        return getItemAdmin(id);
    }

    private static void patchOptStr(long id, Map<String, Object> patch, String key, String col, int max) {
        if (!patch.containsKey(key)) return;
        String v = str(patch.get(key)).trim();
        if (max > 0 && v.length() > max) v = v.substring(0, max);
        try {
            db().update("UPDATE " + ITEM + " SET `" + col + "`=? WHERE id=?", v, id);
        } catch (Exception ignored) {
        }
    }

    private static void patchOptInt(long id, Map<String, Object> patch, String key, String col) {
        if (!patch.containsKey(key)) return;
        try {
            db().update("UPDATE " + ITEM + " SET `" + col + "`=? WHERE id=?", toInt(patch.get(key)), id);
        } catch (Exception ignored) {
        }
    }

    private static void patchOptNum(long id, Map<String, Object> patch, String key, String col) {
        if (!patch.containsKey(key)) return;
        try {
            double v = 0;
            Object raw = patch.get(key);
            if (raw instanceof Number n) v = n.doubleValue();
            else if (raw != null && !String.valueOf(raw).isBlank()) v = Double.parseDouble(String.valueOf(raw).trim());
            db().update("UPDATE " + ITEM + " SET `" + col + "`=? WHERE id=?", v, id);
        } catch (Exception ignored) {
        }
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
            where.append(" AND (title LIKE ? OR " + authorColumn() + " LIKE ? OR " + isbnColumn() + " LIKE ?)");
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
        m.put("author", safeStr(rs, authorColumn()));
        m.put("isbn", safeStr(rs, isbnColumn()));
        m.put("categoryId", rs.getLong("category_id"));
        m.put("stock", rs.getInt("stock"));
        m.put("status", rs.getString("status"));
        m.put("coverUrl", rs.getString("cover_url"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        if (galleryEnabled && hasGalleryJson()) {
            try {
                String raw = rs.getString("gallery_json");
                m.put("galleryImages", parseGallery(raw));
            } catch (Exception e) {
                m.put("galleryImages", List.of());
            }
        }
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
        putOptStr(m, rs, "publisher", "publisher");
        putOptStr(m, rs, "call_no", "callNo");
        putOptStr(m, rs, "condition_grade", "conditionGrade");
        putOptStr(m, rs, "seller_note", "sellerNote");
        putOptStr(m, rs, "spicy_level", "spicyLevel");
        putOptInt(m, rs, "is_vegetarian", "isVegetarian");
        putOptInt(m, rs, "requires_training", "requiresTraining");
        putOptStr(m, rs, "owner_name", "ownerName");
        putOptStr(m, rs, "stage", "stage");
        putOptNum(m, rs, "credit", "credit");
        putOptNum(m, rs, "service_hours", "serviceHours");
        putOptInt(m, rs, "seat_capacity", "seatCapacity");
        putOptStr(m, rs, "fee_rule", "feeRule");
        putOptStr(m, rs, "stylist_name", "stylistName");
        putOptInt(m, rs, "duration_sec", "durationSec");
        putOptInt(m, rs, "release_year", "releaseYear");
        putOptStr(m, rs, "region", "region");
        putOptStr(m, rs, "summary", "summary");
        putOptStr(m, rs, "item_kind", "itemKind");
        try {
            m.put("foundAt", fmt(rs.getTimestamp("found_at")));
        } catch (Exception ignored) {
        }
        try {
            m.put("publishedAt", fmt(rs.getTimestamp("published_at")));
        } catch (Exception ignored) {
        }
        return m;
    }

    private static void putOptStr(Map<String, Object> m, java.sql.ResultSet rs, String col, String key) {
        try {
            String v = rs.getString(col);
            if (v != null) m.put(key, v);
        } catch (Exception ignored) {
        }
    }

    private static void putOptInt(Map<String, Object> m, java.sql.ResultSet rs, String col, String key) {
        try {
            int v = rs.getInt(col);
            if (!rs.wasNull()) m.put(key, v);
        } catch (Exception ignored) {
        }
    }

    private static void putOptNum(Map<String, Object> m, java.sql.ResultSet rs, String col, String key) {
        try {
            double v = rs.getDouble(col);
            if (!rs.wasNull()) m.put(key, v);
        } catch (Exception ignored) {
        }
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

    /** 门户/推荐等非管理端：去掉签到码等口令字段。 */
    public static void redactSensitiveForPublic(Map<String, Object> item) {
        if (item == null) return;
        item.remove("checkinCode");
    }

    @SuppressWarnings("unchecked")
    public static void redactSensitiveListForPublic(Object listOrPage) {
        if (listOrPage instanceof Map<?, ?> page) {
            Object list = page.get("list");
            if (list instanceof List<?> rows) {
                for (Object row : rows) {
                    if (row instanceof Map<?, ?> m) {
                        redactSensitiveForPublic((Map<String, Object>) m);
                    }
                }
            }
            return;
        }
        if (listOrPage instanceof List<?> rows) {
            for (Object row : rows) {
                if (row instanceof Map<?, ?> m) {
                    redactSensitiveForPublic((Map<String, Object>) m);
                }
            }
        }
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

    public static boolean hasGalleryJson() {
        if (hasGalleryJson == null) hasGalleryJson = hasItemColumn("gallery_json");
        return hasGalleryJson;
    }

    public static void ensureGalleryColumn() {
        if (hasGalleryJson()) return;
        try {
            db().execute("ALTER TABLE `" + ITEM + "` ADD COLUMN `gallery_json` TEXT NULL");
            hasGalleryJson = true;
        } catch (Exception ignored) {
            hasGalleryJson = hasItemColumn("gallery_json");
        }
    }

    /** 标题前缀联想（搜索辅助）。 */
    public static List<Map<String, Object>> suggestTitles(String q, int limit) {
        if (limit < 1) limit = 8;
        if (limit > 20) limit = 20;
        String prefix = q == null ? "" : q.trim();
        if (prefix.isBlank()) return List.of();
        if (prefix.length() > 64) prefix = prefix.substring(0, 64);
        String where = " WHERE title LIKE ?";
        List<Object> args = new ArrayList<>();
        args.add(prefix + "%");
        if (hasDeletedAt() && softDeleteEnabled) {
            where += " AND deleted_at IS NULL";
        }
        args.add(limit);
        try {
            return db().query(
                    "SELECT id, title, cover_url FROM " + ITEM + where + " ORDER BY id DESC LIMIT ?",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("title", rs.getString("title"));
                        m.put("coverUrl", rs.getString("cover_url"));
                        m.put("value", rs.getString("title"));
                        return m;
                    },
                    args.toArray());
        } catch (Exception e) {
            return List.of();
        }
    }

    private static List<String> parseGallery(String raw) {
        if (raw == null || raw.isBlank()) return List.of();
        try {
            List<String> list = new ObjectMapper().readValue(raw, new TypeReference<>() {});
            if (list == null) return List.of();
            List<String> out = new ArrayList<>();
            for (String s : list) {
                if (s == null) continue;
                String u = s.trim();
                if (!u.isBlank()) out.add(u);
                if (out.size() >= 9) break;
            }
            return out;
        } catch (Exception e) {
            return List.of();
        }
    }

    private static String toGalleryJson(Object raw) {
        List<String> urls = new ArrayList<>();
        if (raw instanceof List<?> list) {
            for (Object o : list) {
                if (o == null) continue;
                String u = String.valueOf(o).trim();
                if (!u.isBlank()) urls.add(u);
                if (urls.size() >= 9) break;
            }
        } else if (raw != null) {
            String s = String.valueOf(raw).trim();
            if (!s.isBlank()) {
                try {
                    urls.addAll(parseGallery(s.startsWith("[") ? s : "[]"));
                } catch (Exception ignored) {
                }
            }
        }
        try {
            return new ObjectMapper().writeValueAsString(urls);
        } catch (Exception e) {
            return "[]";
        }
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
        if (delta == 0) return;
        // 条件更新：MySQL 同句内后写 status 读到已更新的 stock；扣减要求 stock 够
        int n;
        if (delta < 0) {
            n = db().update(
                    "UPDATE " + ITEM
                            + " SET stock=stock+?, status=IF(stock>0,'available','unavailable') WHERE id=? AND stock>=?",
                    delta, itemId, -delta);
        } else {
            n = db().update(
                    "UPDATE " + ITEM + " SET stock=stock+?, status='available' WHERE id=?",
                    delta, itemId);
        }
        if (n <= 0) throw new IllegalStateException(stockShortage(0));
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

    private static final Set<String> IMPORT_CORE_KEYS = Set.of(
            "title", "author", "isbn", "category", "stock");

    /**
     * CSV 行导入：核心列 title/author/isbn/category/stock，其余列（时段、签到码、扩展字段等）写入 extra。
     * category 按名称匹配，不存在则新建；tags 按标签名解析（找不到则跳过）。
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
                Map<String, Object> extra = new LinkedHashMap<>();
                for (Map.Entry<String, String> e : row.entrySet()) {
                    String k = e.getKey();
                    if (k == null || IMPORT_CORE_KEYS.contains(k)) continue;
                    String v = e.getValue() == null ? "" : e.getValue().trim();
                    if (v.isBlank()) continue;
                    if ("tags".equals(k) || "tag".equals(k) || "tagNames".equals(k)) {
                        List<Long> tagIds = resolveTagIdsByCsv(v);
                        if (!tagIds.isEmpty()) extra.put("tagIds", tagIds);
                        continue;
                    }
                    extra.put(k, v);
                }
                addItem(title, author, isbn, catId, stock, "", extra.isEmpty() ? null : extra);
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

    /** 标签列：支持 id 或名称（逗号/顿号分隔）；名称未命中则跳过。 */
    private static List<Long> resolveTagIdsByCsv(String raw) {
        List<Long> ids = new ArrayList<>();
        if (raw == null || raw.isBlank() || !tagsEnabled()) return ids;
        for (String part : raw.split("[,，、\\s]+")) {
            String p = part.trim();
            if (p.isEmpty()) continue;
            try {
                long id = Long.parseLong(p);
                if (id > 0) ids.add(id);
                continue;
            } catch (Exception ignored) {
            }
            Long id = findTagIdByName(p);
            if (id != null) ids.add(id);
        }
        return ids;
    }

    private static Long findTagIdByName(String name) {
        if (name == null || name.isBlank() || !tagsEnabled()) return null;
        try {
            List<Long> ids = db().query(
                    "SELECT id FROM " + TAG + " WHERE name=? LIMIT 1",
                    (rs, i) -> rs.getLong(1),
                    name.trim());
            return ids.isEmpty() ? null : ids.get(0);
        } catch (Exception e) {
            return null;
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }

    private static String safeStr(java.sql.ResultSet rs, String col) {
        try {
            String v = rs.getString(col);
            return v == null ? "" : v;
        } catch (Exception e) {
            return "";
        }
    }
}
