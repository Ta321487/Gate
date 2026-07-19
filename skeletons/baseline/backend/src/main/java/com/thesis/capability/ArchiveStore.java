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

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private ArchiveStore() {}

    /** 换表（新领域薄落地时调用一次） */
    public static void bind(String categoryTable, String itemTable) {
        if (categoryTable != null && !categoryTable.isBlank()) CAT = categoryTable.trim();
        if (itemTable != null && !itemTable.isBlank()) ITEM = itemTable.trim();
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
                "SELECT COUNT(*) FROM " + ITEM + " WHERE category_id=?", Integer.class, id);
        if (used != null && used > 0) {
            throw new IllegalStateException("该分类下仍有 " + used + " 条记录，无法删除");
        }
        db().update("DELETE FROM " + CAT + " WHERE id=?", id);
    }

    public static List<Map<String, Object>> listCategories() {
        return db().query(
                "SELECT c.id, c.name, (SELECT COUNT(*) FROM " + ITEM + " b WHERE b.category_id=c.id) AS item_count "
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
        return getItem(key == null ? 0L : key.longValue());
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
        return getItem(id);
    }

    public static boolean deleteItem(long id) {
        return db().update("DELETE FROM " + ITEM + " WHERE id=?", id) > 0;
    }

    public static Map<String, Object> getItemRaw(long id) {
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + ITEM + " WHERE id=?",
                (rs, i) -> {
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
                    return m;
                }, id);
        return list.isEmpty() ? null : list.get(0);
    }

    public static Map<String, Object> getItem(long id) {
        Map<String, Object> m = getItemRaw(id);
        return m == null ? null : enrichItem(m);
    }

    public static Map<String, Object> pageItems(String keyword, Long categoryId, int page, int size) {
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
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
        Integer total = db().queryForObject("SELECT COUNT(*) FROM " + ITEM + where, Integer.class, args.toArray());
        int t = total == null ? 0 : total;
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + ITEM + where + " ORDER BY id LIMIT ? OFFSET ?",
                (rs, i) -> {
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
                    return enrichItem(m);
                }, args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static Map<String, Object> enrichItem(Map<String, Object> b) {
        Map<String, Object> m = new LinkedHashMap<>(b);
        long cid = toLong(b.get("categoryId"));
        List<String> names = db().query(
                "SELECT name FROM " + CAT + " WHERE id=?", (rs, i) -> rs.getString(1), cid);
        m.put("categoryName", names.isEmpty() ? "" : names.get(0));
        return m;
    }

    public static void adjustStock(long itemId, int delta) {
        Map<String, Object> book = getItemRaw(itemId);
        if (book == null) throw new IllegalStateException("对象不存在");
        int stock = toInt(book.get("stock")) + delta;
        if (stock < 0) throw new IllegalStateException("库存不足");
        db().update(
                "UPDATE " + ITEM + " SET stock=?, status=? WHERE id=?",
                stock, stock > 0 ? "available" : "unavailable", itemId);
    }

    public static long countItems() {
        Long n = db().queryForObject("SELECT COUNT(*) FROM " + ITEM, Long.class);
        return n == null ? 0 : n;
    }

    public static long sumStock() {
        Long n = db().queryForObject("SELECT COALESCE(SUM(stock),0) FROM " + ITEM, Long.class);
        return n == null ? 0 : n;
    }

    public static long countCategories() {
        Long n = db().queryForObject("SELECT COUNT(*) FROM " + CAT, Long.class);
        return n == null ? 0 : n;
    }
}
