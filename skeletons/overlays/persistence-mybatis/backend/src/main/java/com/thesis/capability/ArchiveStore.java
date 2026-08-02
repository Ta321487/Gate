package com.thesis.capability;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.DomainResourceJson;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.ArchiveMapper;
import com.thesis.mapper.SchemaMapper;

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
    private static Boolean hasOwnerUsername;
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

    private static ArchiveMapper mapper() {
        return MybatisSupport.mapper(ArchiveMapper.class);
    }

    private static SchemaMapper schema() {
        return MybatisSupport.mapper(SchemaMapper.class);
    }

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
        hasOwnerUsername = null;
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
        if (mapper().countCategoryByName(CAT, n) > 0) throw new IllegalStateException("分类名已存在");
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("catTable", CAT);
        row.put("name", n);
        mapper().insertCategory(row);
        return row.get("id") == null ? 0L : ((Number) row.get("id")).longValue();
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
        if (mapper().countCategoryById(CAT, id) == 0) throw new IllegalArgumentException("分类不存在");
        String n = name == null ? "" : name.trim();
        if (n.isBlank()) throw new IllegalArgumentException("分类名不能为空");
        if (mapper().countCategoryNameDup(CAT, n, id) > 0) throw new IllegalStateException("分类名已存在");
        mapper().updateCategory(CAT, id, n);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("name", n);
        return m;
    }

    public static void deleteCategory(long id) {
        if (mapper().countCategoryById(CAT, id) == 0) throw new IllegalArgumentException("分类不存在");
        boolean excludeDeleted = softDeleteEnabled && hasDeletedAt();
        int used = mapper().countItemsByCategory(ITEM, id, excludeDeleted);
        if (used > 0) {
            throw new IllegalStateException("该分类下仍有 " + used + " 条记录，无法删除");
        }
        mapper().deleteCategory(CAT, id);
    }

    public static List<Map<String, Object>> listCategories() {
        boolean excludeDeleted = softDeleteEnabled && hasDeletedAt();
        List<Map<String, Object>> raw = mapper().selectCategories(CAT, ITEM, excludeDeleted);
        List<Map<String, Object>> out = new ArrayList<>();
        if (raw == null) return out;
        for (Map<String, Object> r : raw) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id", r.get("id"));
            row.put("name", r.get("name"));
            long cnt = toLong(first(r, "itemCount", "item_count"));
            row.put("bookCount", cnt);
            row.put("itemCount", cnt);
            out.add(row);
        }
        return out;
    }

    public static Map<String, Object> addItem(String title, String author, String isbn, long categoryId, int stock, String coverUrl) {
        return addItem(title, author, isbn, categoryId, stock, coverUrl, null);
    }

    public static Map<String, Object> addItem(
            String title, String author, String isbn, long categoryId, int stock, String coverUrl, Map<String, Object> extra) {
        String status = stock > 0 ? "available" : "unavailable";
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("itemTable", ITEM);
        row.put("authorCol", authorColumn());
        row.put("isbnCol", isbnColumn());
        row.put("title", title);
        row.put("author", author);
        row.put("isbn", isbn);
        row.put("categoryId", categoryId);
        row.put("stock", stock);
        row.put("status", status);
        row.put("coverUrl", coverUrl == null ? "" : coverUrl);
        mapper().insertItem(row);
        long id = row.get("id") == null ? 0L : ((Number) row.get("id")).longValue();
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
        return addUserPost(username, title, body, categoryId, null, null);
    }

    public static Map<String, Object> addUserPost(
            String username,
            String title,
            String body,
            long categoryId,
            String authorOpt,
            Integer stockOpt) {
        if (!userPublishEnabled) {
            throw new IllegalStateException("当前领域未开放用户发帖");
        }
        String uid = username == null ? "" : username.trim();
        if (uid.isBlank()) throw new IllegalArgumentException("未登录");
        String t = title == null ? "" : title.trim();
        if (t.isBlank()) throw new IllegalArgumentException("标题不能为空");
        long cat = categoryId > 0 ? categoryId : 1L;
        String content = body == null ? "" : body;
        String author = authorOpt == null ? "" : authorOpt.trim();
        if (author.isBlank()) author = uid;
        if (author.length() > 100) author = author.substring(0, 100);
        int stock = 1;
        if (stockOpt != null && stockOpt > 0) {
            stock = Math.min(99, stockOpt);
        }
        Map<String, Object> extra = new LinkedHashMap<>();
        extra.put("ownerUsername", uid);
        return addItem(t, author, content, cat, stock, "", extra);
    }

    /** 本人发布（含站长下架）：优先按 owner_username */
    public static Map<String, Object> pageMine(String username, int page, int size) {
        if (!userPublishEnabled) {
            throw new IllegalStateException("当前领域未开放用户发帖");
        }
        String uid = username == null ? "" : username.trim();
        if (uid.isBlank()) throw new IllegalArgumentException("未登录");
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String mineCol = hasOwnerUsername() ? "owner_username" : authorColumn();
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectMine(ITEM, mineCol, uid);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw == null ? List.of() : raw);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : pi.getList()) {
            list.add(enrichItem(shapeItem(r)));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", pi.getTotal());
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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("itemTable", ITEM);
        row.put("authorCol", authorColumn());
        row.put("isbnCol", isbnColumn());
        row.put("id", id);
        row.put("title", title);
        row.put("author", author);
        row.put("isbn", isbn);
        row.put("categoryId", categoryId);
        row.put("stock", stock);
        row.put("status", status);
        row.put("coverUrl", cover);
        mapper().updateItemCore(row);
        if (hasStartAt()) {
            Timestamp ts = parseTs(patch.containsKey("startAt") ? patch.get("startAt") : m.get("startAt"));
            mapper().updateItemColumn(ITEM, "start_at", ts, id);
        }
        if (hasEndAt()) {
            Timestamp ts = parseTs(patch.containsKey("endAt") ? patch.get("endAt") : m.get("endAt"));
            mapper().updateItemColumn(ITEM, "end_at", ts, id);
        }
        if (hasApplyDeadline()) {
            Timestamp ts = parseTs(patch.containsKey("applyDeadlineAt") ? patch.get("applyDeadlineAt") : m.get("applyDeadlineAt"));
            mapper().updateItemColumn(ITEM, "apply_deadline_at", ts, id);
        }
        if (hasMutexCode()) {
            String code = patch.containsKey("mutexCode")
                    ? str(patch.get("mutexCode")).trim()
                    : str(m.get("mutexCode")).trim();
            if (code.length() > 32) code = code.substring(0, 32);
            mapper().updateItemColumn(ITEM, "mutex_code", code, id);
        }
        if (hasCheckinCode()) {
            String code = patch.containsKey("checkinCode")
                    ? str(patch.get("checkinCode")).trim()
                    : str(m.get("checkinCode")).trim();
            if (code.length() > 16) code = code.substring(0, 16);
            mapper().updateItemColumn(ITEM, "checkin_code", code, id);
        }
        if (galleryEnabled && hasGalleryJson() && patch.containsKey("galleryImages")) {
            mapper().updateItemColumn(ITEM, "gallery_json", toGalleryJson(patch.get("galleryImages")), id);
        }
        patchOptStr(id, patch, "publisher", "publisher", 100);
        patchOptStr(id, patch, "callNo", "call_no", 64);
        patchOptStr(id, patch, "conditionGrade", "condition_grade", 16);
        patchOptStr(id, patch, "sellerNote", "seller_note", 255);
        patchOptStr(id, patch, "spicyLevel", "spicy_level", 16);
        patchOptInt(id, patch, "isVegetarian", "is_vegetarian");
        patchOptInt(id, patch, "requiresTraining", "requires_training");
        patchOptStr(id, patch, "ownerName", "owner_name", 64);
        patchOptStr(id, patch, "ownerUsername", "owner_username", 64);
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
                mapper().updateItemColumn(ITEM, "found_at", ts, id);
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
            mapper().updateItemColumn(ITEM, col, v, id);
        } catch (Exception ignored) {
        }
    }

    private static void patchOptInt(long id, Map<String, Object> patch, String key, String col) {
        if (!patch.containsKey(key)) return;
        try {
            mapper().updateItemColumn(ITEM, col, toInt(patch.get(key)), id);
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
            mapper().updateItemColumn(ITEM, col, v, id);
        } catch (Exception ignored) {
        }
    }

    public static boolean deleteItem(long id) {
        if (softDeleteEnabled && hasDeletedAt()) {
            return mapper().softDeleteItem(ITEM, id) > 0;
        }
        if (tagsEnabled()) {
            try {
                mapper().deleteItemTags(ITEM_TAG, itemTagFk, id);
            } catch (Exception ignored) {
            }
        }
        return mapper().hardDeleteItem(ITEM, id) > 0;
    }

    public static boolean restoreItem(long id) {
        if (!hasDeletedAt()) return false;
        return mapper().restoreItem(ITEM, id) > 0;
    }

    public static Map<String, Object> getItemRaw(long id) {
        Map<String, Object> raw = mapper().selectItemById(ITEM, id);
        return raw == null ? null : shapeItem(raw);
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
        boolean excludeDeleted = hasDeletedAt() && !(includeDeleted && softDeleteEnabled);
        String like = null;
        if (keyword != null && !keyword.isBlank()) {
            like = "%" + keyword.trim() + "%";
        }
        List<Long> tids = null;
        if (tagIds != null && !tagIds.isEmpty() && tagsEnabled()) {
            tids = new ArrayList<>();
            for (Long tid : tagIds) {
                if (tid != null && tid > 0) tids.add(tid);
            }
            if (tids.isEmpty()) tids = null;
        }
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectItems(
                ITEM,
                authorColumn(),
                isbnColumn(),
                excludeDeleted,
                categoryId,
                like,
                tids,
                tagsEnabled() ? ITEM_TAG : null,
                tagsEnabled() ? itemTagFk : null);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw == null ? List.of() : raw);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : pi.getList()) {
            list.add(enrichItem(shapeItem(r)));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", pi.getTotal());
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    private static Map<String, Object> shapeItem(Map<String, Object> raw) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", raw.get("id"));
        m.put("title", raw.get("title"));
        m.put("author", str(rawCol(raw, authorColumn())));
        m.put("isbn", str(rawCol(raw, isbnColumn())));
        m.put("categoryId", toLong(first(raw, "categoryId", "category_id")));
        m.put("stock", toInt(first(raw, "stock")));
        m.put("status", raw.get("status"));
        m.put("coverUrl", first(raw, "coverUrl", "cover_url"));
        m.put("createdAt", fmt(first(raw, "createdAt", "created_at")));
        if (galleryEnabled && hasGalleryJson()) {
            Object g = rawCol(raw, "gallery_json");
            m.put("galleryImages", parseGallery(g == null ? null : String.valueOf(g)));
        }
        if (hasStartAt()) m.put("startAt", fmt(first(raw, "startAt", "start_at")));
        if (hasEndAt()) m.put("endAt", fmt(first(raw, "endAt", "end_at")));
        if (hasApplyDeadline()) m.put("applyDeadlineAt", fmt(first(raw, "applyDeadlineAt", "apply_deadline_at")));
        if (hasMutexCode()) {
            Object v = first(raw, "mutexCode", "mutex_code");
            m.put("mutexCode", v == null ? "" : String.valueOf(v));
        }
        if (hasDeletedAt()) {
            m.put("deletedAt", fmt(first(raw, "deletedAt", "deleted_at")));
        }
        if (hasCheckinCode()) {
            Object v = first(raw, "checkinCode", "checkin_code");
            m.put("checkinCode", v == null ? "" : String.valueOf(v));
        }
        putOptStr(m, raw, "publisher", "publisher");
        putOptStr(m, raw, "call_no", "callNo");
        putOptStr(m, raw, "condition_grade", "conditionGrade");
        putOptStr(m, raw, "seller_note", "sellerNote");
        putOptStr(m, raw, "spicy_level", "spicyLevel");
        putOptInt(m, raw, "is_vegetarian", "isVegetarian");
        putOptInt(m, raw, "requires_training", "requiresTraining");
        putOptStr(m, raw, "owner_name", "ownerName");
        putOptStr(m, raw, "owner_username", "ownerUsername");
        putOptStr(m, raw, "stage", "stage");
        putOptNum(m, raw, "credit", "credit");
        putOptNum(m, raw, "service_hours", "serviceHours");
        putOptInt(m, raw, "seat_capacity", "seatCapacity");
        putOptStr(m, raw, "fee_rule", "feeRule");
        putOptStr(m, raw, "stylist_name", "stylistName");
        putOptInt(m, raw, "duration_sec", "durationSec");
        putOptInt(m, raw, "release_year", "releaseYear");
        putOptStr(m, raw, "region", "region");
        putOptStr(m, raw, "summary", "summary");
        putOptStr(m, raw, "item_kind", "itemKind");
        Object foundAt = first(raw, "foundAt", "found_at");
        if (foundAt != null || hasMapKey(raw, "found_at", "foundAt")) {
            m.put("foundAt", fmt(foundAt));
        }
        Object publishedAt = first(raw, "publishedAt", "published_at");
        if (publishedAt != null || hasMapKey(raw, "published_at", "publishedAt")) {
            m.put("publishedAt", fmt(publishedAt));
        }
        return m;
    }

    private static Object rawCol(Map<String, Object> raw, String physical) {
        return first(raw, physical, snakeToCamel(physical));
    }

    private static boolean hasMapKey(Map<String, Object> raw, String... keys) {
        for (String k : keys) {
            if (raw.containsKey(k)) return true;
        }
        return false;
    }

    private static String snakeToCamel(String s) {
        if (s == null || !s.contains("_")) return s;
        StringBuilder sb = new StringBuilder();
        boolean up = false;
        for (char c : s.toCharArray()) {
            if (c == '_') {
                up = true;
                continue;
            }
            sb.append(up ? Character.toUpperCase(c) : c);
            up = false;
        }
        return sb.toString();
    }

    private static void putOptStr(Map<String, Object> m, Map<String, Object> raw, String col, String key) {
        Object v = rawCol(raw, col);
        if (v != null) m.put(key, String.valueOf(v));
    }

    private static void putOptInt(Map<String, Object> m, Map<String, Object> raw, String col, String key) {
        if (!hasMapKey(raw, col, snakeToCamel(col))) return;
        Object v = rawCol(raw, col);
        if (v == null) return;
        m.put(key, toInt(v));
    }

    private static void putOptNum(Map<String, Object> m, Map<String, Object> raw, String col, String key) {
        if (!hasMapKey(raw, col, snakeToCamel(col))) return;
        Object v = rawCol(raw, col);
        if (v == null) return;
        if (v instanceof Number n) {
            m.put(key, n.doubleValue());
            return;
        }
        try {
            m.put(key, Double.parseDouble(String.valueOf(v).trim()));
        } catch (Exception ignored) {
        }
    }

    private static Object first(Map<String, Object> raw, String... keys) {
        for (String k : keys) {
            if (k != null && raw.containsKey(k) && raw.get(k) != null) return raw.get(k);
        }
        return null;
    }

    private static boolean isSoftDeleted(Map<String, Object> m) {
        if (!softDeleteEnabled || !hasDeletedAt()) return false;
        Object d = m.get("deletedAt");
        return d != null && !String.valueOf(d).isBlank() && !"null".equalsIgnoreCase(String.valueOf(d));
    }

    private static Map<String, Object> enrichItem(Map<String, Object> b) {
        Map<String, Object> m = new LinkedHashMap<>(b);
        long cid = toLong(b.get("categoryId"));
        String name = null;
        try {
            name = mapper().selectCategoryName(CAT, cid);
        } catch (Exception ignored) {
        }
        m.put("categoryName", name == null ? "" : name);
        m.put("deleted", isSoftDeleted(m));
        if (tagsEnabled()) {
            long id = toLong(b.get("id"));
            List<Map<String, Object>> tagsRaw = mapper().selectItemTags(TAG, ITEM_TAG, itemTagFk, id);
            List<Map<String, Object>> tags = new ArrayList<>();
            List<Long> ids = new ArrayList<>();
            List<String> tnames = new ArrayList<>();
            if (tagsRaw != null) {
                for (Map<String, Object> t : tagsRaw) {
                    Map<String, Object> row = new LinkedHashMap<>();
                    long tid = toLong(t.get("id"));
                    String tn = str(t.get("name"));
                    row.put("id", tid);
                    row.put("name", tn);
                    tags.add(row);
                    ids.add(tid);
                    tnames.add(tn);
                }
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

    public static boolean hasOwnerUsername() {
        if (hasOwnerUsername == null) hasOwnerUsername = hasItemColumn("owner_username");
        return hasOwnerUsername;
    }

    public static boolean hasGalleryJson() {
        if (hasGalleryJson == null) hasGalleryJson = hasItemColumn("gallery_json");
        return hasGalleryJson;
    }

    public static void ensureGalleryColumn() {
        if (hasGalleryJson()) return;
        try {
            schema().executeDdl("ALTER TABLE `" + ITEM + "` ADD COLUMN `gallery_json` TEXT NULL");
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
        boolean excludeDeleted = hasDeletedAt() && softDeleteEnabled;
        try {
            List<Map<String, Object>> raw = mapper().suggestTitles(ITEM, prefix + "%", excludeDeleted, limit);
            List<Map<String, Object>> out = new ArrayList<>();
            if (raw == null) return out;
            for (Map<String, Object> r : raw) {
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("id", r.get("id"));
                m.put("title", r.get("title"));
                Object cover = first(r, "coverUrl", "cover_url");
                m.put("coverUrl", cover);
                m.put("value", r.get("title"));
                out.add(m);
            }
            return out;
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
            schema().executeDdl(
                    "ALTER TABLE `" + ITEM + "` ADD COLUMN `mutex_code` VARCHAR(32) NOT NULL DEFAULT ''");
            hasMutexCode = true;
        } catch (Exception ignored) {
            hasMutexCode = hasItemColumn("mutex_code");
        }
    }

    public static void ensureSoftDeleteColumn() {
        if (hasDeletedAt()) return;
        try {
            schema().executeDdl("ALTER TABLE `" + ITEM + "` ADD COLUMN `deleted_at` DATETIME NULL");
            hasDeletedAt = true;
        } catch (Exception ignored) {
            hasDeletedAt = hasItemColumn("deleted_at");
        }
    }

    public static void ensureCheckinCodeColumn() {
        if (hasCheckinCode()) return;
        try {
            schema().executeDdl(
                    "ALTER TABLE `" + ITEM + "` ADD COLUMN `checkin_code` VARCHAR(16) NOT NULL DEFAULT ''");
            hasCheckinCode = true;
        } catch (Exception ignored) {
            hasCheckinCode = hasItemColumn("checkin_code");
        }
    }

    public static List<Map<String, Object>> listTags() {
        if (!tagsEnabled()) return List.of();
        List<Map<String, Object>> raw = mapper().selectTags(TAG);
        List<Map<String, Object>> out = new ArrayList<>();
        if (raw == null) return out;
        for (Map<String, Object> r : raw) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id", r.get("id"));
            row.put("name", r.get("name"));
            out.add(row);
        }
        return out;
    }

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
        mapper().deleteItemTags(ITEM_TAG, itemTagFk, itemId);
        for (Long tid : ids) {
            try {
                mapper().insertItemTag(ITEM_TAG, itemTagFk, itemId, tid);
            } catch (Exception ignored) {
            }
        }
    }

    private static boolean hasItemColumn(String col) {
        try {
            Integer n = schema().countColumn(ITEM, col);
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
        int n;
        if (delta < 0) {
            n = mapper().adjustStockDown(ITEM, itemId, delta, -delta);
        } else {
            n = mapper().adjustStockUp(ITEM, itemId, delta);
        }
        if (n <= 0) throw new IllegalStateException(stockShortage(0));
        syncOccupyStageWithStock(itemId, delta);
    }

    /**
     * 床位占用皮：stock 扣至 0 且 stage 为「空闲」→「已分配」；回补且为「已分配」→「空闲」。
     * 维修中/开放及其它域 stage 语义不动。
     */
    private static void syncOccupyStageWithStock(long itemId, int delta) {
        if (!hasItemColumn("stage")) return;
        Map<String, Object> book = getItemRaw(itemId);
        if (book == null || !book.containsKey("stage")) return;
        String stage = str(book.get("stage")).trim();
        int stock = toInt(book.get("stock"));
        try {
            if (delta < 0 && stock <= 0 && (stage.isEmpty() || "空闲".equals(stage))) {
                mapper().updateItemColumn(ITEM, "stage", "已分配", itemId);
            } else if (delta > 0 && stock > 0 && "已分配".equals(stage)) {
                mapper().updateItemColumn(ITEM, "stage", "空闲", itemId);
            }
        } catch (Exception ignored) {
            // 无 stage 列或写失败时忽略，stock/status 已更新
        }
    }

    public static long countItems() {
        boolean excludeDeleted = softDeleteEnabled && hasDeletedAt();
        return mapper().countItems(ITEM, excludeDeleted);
    }

    public static long sumStock() {
        boolean excludeDeleted = softDeleteEnabled && hasDeletedAt();
        return mapper().sumStock(ITEM, excludeDeleted);
    }

    public static long countCategories() {
        return mapper().countCategories(CAT);
    }

    /** 分类库存柱状图：名称 + 库存合计。 */
    public static List<Map<String, Object>> stockByCategory(int limit) {
        int lim = Math.max(1, Math.min(limit, 20));
        try {
            List<Map<String, Object>> raw = mapper().stockByCategory(CAT, ITEM, lim);
            List<Map<String, Object>> out = new ArrayList<>();
            if (raw == null) return out;
            for (Map<String, Object> r : raw) {
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("name", r.get("name"));
                row.put("value", toLong(r.get("value")));
                out.add(row);
            }
            return out;
        } catch (Exception e) {
            return List.of();
        }
    }

    public static Long findCategoryIdByName(String name) {
        if (name == null || name.isBlank()) return null;
        return mapper().selectCategoryIdByName(CAT, name.trim());
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
            return mapper().selectTagIdByName(TAG, name.trim());
        } catch (Exception e) {
            return null;
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }
}
