package com.thesis.capability;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.config.DomainResourceJson;
import com.thesis.config.JpaSupport;
import com.thesis.config.JpaDb;
import com.thesis.config.GeneratedKeyHolder;
import com.thesis.config.KeyHolder;
import com.thesis.service.UserStore;

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
    private static Boolean hasOwnerUsername;
    private static Boolean hasGalleryJson;
    private static Boolean hasEquipmentJson;
    static boolean softDeleteEnabled = false;
    static boolean userPublishEnabled = false;
    /** 开题点名投稿审核/先审后发：用户发布为 pending_review，通过后才进公开目录。 */
    static boolean publishReviewEnabled = false;
    private static boolean galleryEnabled = false;
    private static boolean detailAttrsEnabled = false;
    private static List<String> detailAttrKeys = List.of();
    private static Map<String, String> detailAttrTypes = Map.of();
    private static Boolean hasDetailJson;
    private static boolean roomEquipmentEnabled = false;

    static boolean flashPriceEnabled = false;
    private static Boolean hasPromoPrice;

    static boolean productSpecEnabled = false;
    private static Boolean hasDedicatedSpecNote;

    static boolean stockWarnNotify = false;
    static int stockWarnBelow = 10;

    public static void configureFlashPrice(boolean enabled) {
        flashPriceEnabled = enabled;
        hasPromoPrice = null;
        if (flashPriceEnabled) {
            ensurePromoColumns();
        }
    }

    public static boolean flashPriceEnabled() {
        return flashPriceEnabled;
    }

    public static void configureStockWarn(boolean notify, int below) {
        ArchiveCfgOps.configureStockWarn(notify, below);
    }

    private static void ensurePromoColumns() {
        if (ITEM == null || ITEM.isBlank()) return;
        for (String col : new String[] {"promo_price", "promo_start", "promo_end"}) {
            try {
                db().execute("ALTER TABLE `" + ITEM + "` ADD COLUMN `" + col + "` "
                        + ("promo_price".equals(col) ? "DECIMAL(10,2) NULL" : "DATETIME NULL"));
            } catch (Exception ignored) {
            }
        }
        hasPromoPrice = hasItemColumn("promo_price");
    }

    private static boolean hasPromoPrice() {
        if (!flashPriceEnabled) return false;
        if (hasPromoPrice == null) hasPromoPrice = hasItemColumn("promo_price");
        return Boolean.TRUE.equals(hasPromoPrice);
    }

    public static void configureProductSpec(boolean enabled) {
        productSpecEnabled = enabled;
        hasDedicatedSpecNote = null;
        if (productSpecEnabled) {
            ensureDedicatedSpecNoteColumn();
        }
    }

    public static boolean productSpecEnabled() {
        return productSpecEnabled;
    }

    /** isbn 物理列已是 spec_note（如 FOOD）时不另开列；SHOP 货号场景才补 spec_note。 */
    private static void ensureDedicatedSpecNoteColumn() {
        if (ITEM == null || ITEM.isBlank()) return;
        if ("spec_note".equalsIgnoreCase(isbnColumn())) return;
        try {
            db().execute("ALTER TABLE `" + ITEM + "` ADD COLUMN `spec_note` VARCHAR(128) DEFAULT ''");
        } catch (Exception ignored) {
        }
        hasDedicatedSpecNote = hasItemColumn("spec_note");
    }

    static boolean usesDedicatedSpecNote() {
        if (!productSpecEnabled) return false;
        if ("spec_note".equalsIgnoreCase(isbnColumn())) return false;
        if (hasDedicatedSpecNote == null) hasDedicatedSpecNote = hasItemColumn("spec_note");
        return Boolean.TRUE.equals(hasDedicatedSpecNote);
    }

    /** 规格文案：专用列或 isbn（FOOD/农产规格）。 */
    public static String productSpecText(Map<String, Object> item) {
        return ArchivePriceOps.productSpecText(item);
    }

    /** 下单明细标题快照：有规格则追加「（规格）」。 */
    public static String lineTitleWithSpec(Map<String, Object> item) {
        return ArchivePriceOps.lineTitleWithSpec(item);
    }

    private static double parseMoney(Object raw) {
        return ArchivePriceOps.parseMoney(raw);
    }

    private static double parseMoneySoft(Object raw) {
        return ArchivePriceOps.parseMoneySoft(raw);
    }

    /** 列表价（原价）：author / priceYuan。浏览用软解析（author 可能是书名作者）。 */
    public static double listUnitPrice(Map<String, Object> item) {
        return ArchivePriceOps.listUnitPrice(item, false);
    }

    /** 窗内活动价，否则原价。未挂 flash_price 时等同 listUnitPrice。下单路径严格校验。 */
    public static double effectiveUnitPrice(Map<String, Object> item) {
        return ArchivePriceOps.effectiveUnitPrice(item);
    }

    public static boolean isPromoActive(Map<String, Object> item) {
        return ArchivePriceOps.isPromoActive(item);
    }


    static boolean shopMarketplaceEnabled = false;
    private static String TAG = "";
    private static String ITEM_TAG = "";
    private static String ITEM_CAT = "";
    static boolean multiCategoryEnabled = false;
    static Boolean hasDimensionCol = null;
    private static String itemTagFk = "post_id";
    /** bake 注入：库存/名额等列名，供不足提示复用 */
    static String STOCK_LABEL = "库存";

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private ArchiveStore() {}

    public static void configureStockLabel(String label) {
        ArchiveCfgOps.configureStockLabel(label);
    }

    public static String stockLabel() {
        return ArchivePriceOps.stockLabel();
    }

    public static String stockShortage(int remain) {
        return ArchivePriceOps.stockShortage(remain);
    }

    public static String stockShortageNeed(int need) {
        return ArchivePriceOps.stockShortageNeed(need);
    }

    public static String stockShortageTitled(String title, int remain) {
        return ArchivePriceOps.stockShortageTitled(title, remain);
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
        hasEquipmentJson = null;
        TAG = "";
        ITEM_TAG = "";
        ITEM_CAT = "";
        hasDimensionCol = null;
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

    public static void configureDetailAttrs(boolean enabled, String keysCsv) {
        detailAttrsEnabled = enabled;
        Map<String, String> types = new LinkedHashMap<>();
        detailAttrKeys = parseDetailKeys(keysCsv, types);
        detailAttrTypes = Map.copyOf(types);
        if (detailAttrsEnabled && !detailAttrKeys.isEmpty()) {
            ensureDetailAttrColumns();
        }
    }

    public static boolean galleryEnabled() {
        return galleryEnabled;
    }

    public static void configureRoomEquipment(boolean enabled) {
        roomEquipmentEnabled = enabled;
        if (enabled) ensureEquipmentColumn();
    }

    public static boolean roomEquipmentEnabled() {
        return roomEquipmentEnabled;
    }

    public static void configureSoftDelete(boolean enabled) {
        ArchiveCfgOps.configureSoftDelete(enabled);
        if (enabled) ensureSoftDeleteColumn();
    }

    public static boolean softDeleteEnabled() {
        return softDeleteEnabled;
    }

    public static void configureUserPublish(boolean enabled) {
        ArchiveCfgOps.configureUserPublish(enabled);
    }

    public static boolean userPublishEnabled() {
        return userPublishEnabled;
    }

    public static void configurePublishReview(boolean enabled) {
        ArchiveCfgOps.configurePublishReview(enabled);
    }

    public static boolean publishReviewEnabled() {
        return publishReviewEnabled;
    }

    public static void configureShopMarketplace(boolean enabled) {
        ArchiveCfgOps.configureShopMarketplace(enabled);
    }

    public static boolean shopMarketplaceEnabled() {
        return shopMarketplaceEnabled;
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

    /** 多维分类：商品-分类关联表（如 product_category） */
    public static void bindItemCategories(String table) {
        ITEM_CAT = table == null ? "" : table.trim();
    }

    public static void configureMultiCategory(boolean enabled) {
        ArchiveCfgOps.configureMultiCategory(enabled);
    }

    public static boolean multiCategoryEnabled() {
        return multiCategoryEnabled;
    }

    private static boolean multiCategoryActive() {
        return multiCategoryEnabled && ITEM_CAT != null && !ITEM_CAT.isBlank();
    }

    public static boolean hasDimensionColumn() {
        if (hasDimensionCol == null) hasDimensionCol = hasCategoryColumn("dimension");
        return hasDimensionCol;
    }

    public static String categoryTable() {
        return CAT;
    }

    public static String itemTable() {
        return ITEM;
    }

    private static JpaDb db() {
        return JpaSupport.db();
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
        if (o instanceof Boolean b) return b ? 1 : 0;
        String s = String.valueOf(o).trim();
        if ("true".equalsIgnoreCase(s) || "yes".equalsIgnoreCase(s) || "on".equalsIgnoreCase(s)) return 1;
        if ("false".equalsIgnoreCase(s) || "no".equalsIgnoreCase(s) || "off".equalsIgnoreCase(s) || s.isBlank()) return 0;
        return Integer.parseInt(s);
    }

    public static long addCategory(String name) {
        return addCategory(name, null);
    }

    public static long addCategory(String name, String dimension) {
        String n = name == null ? "" : name.trim();
        if (n.isBlank()) throw new IllegalArgumentException("分类名不能为空");
        Integer dup = db().queryForObject("SELECT COUNT(*) FROM " + CAT + " WHERE name=?", Integer.class, n);
        if (dup != null && dup > 0) throw new IllegalStateException("分类名已存在");
        String dim = dimension == null ? "" : dimension.trim();
        boolean withDim = multiCategoryActive() && hasDimensionColumn() && !dim.isBlank();
        KeyHolder kh = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    withDim
                            ? "INSERT INTO " + CAT + " (name, dimension) VALUES (?,?)"
                            : "INSERT INTO " + CAT + " (name) VALUES (?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, n);
            if (withDim) ps.setString(2, dim);
            return ps;
        }, kh);
        Number key = kh.getKey();
        return key == null ? 0L : key.longValue();
    }

    public static Map<String, Object> createCategory(String name) {
        return createCategory(name, null);
    }

    public static Map<String, Object> createCategory(String name, String dimension) {
        long id = addCategory(name, dimension);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("name", name.trim());
        m.put("bookCount", 0);
        m.put("itemCount", 0);
        String dim = dimension == null ? "" : dimension.trim();
        if (multiCategoryActive() && hasDimensionColumn() && !dim.isBlank()) {
            m.put("dimension", dim);
        }
        return m;
    }

    public static Map<String, Object> updateCategory(long id, String name) {
        return updateCategory(id, name, null);
    }

    public static Map<String, Object> updateCategory(long id, String name, String dimension) {
        Integer exists = db().queryForObject("SELECT COUNT(*) FROM " + CAT + " WHERE id=?", Integer.class, id);
        if (exists == null || exists == 0) throw new IllegalArgumentException("分类不存在");
        String n = name == null ? "" : name.trim();
        if (n.isBlank()) throw new IllegalArgumentException("分类名不能为空");
        Integer dup = db().queryForObject(
                "SELECT COUNT(*) FROM " + CAT + " WHERE name=? AND id<>?", Integer.class, n, id);
        if (dup != null && dup > 0) throw new IllegalStateException("分类名已存在");
        String dim = dimension == null ? "" : dimension.trim();
        if (multiCategoryActive() && hasDimensionColumn() && !dim.isBlank()) {
            db().update("UPDATE " + CAT + " SET name=?, dimension=? WHERE id=?", n, dim, id);
        } else {
            db().update("UPDATE " + CAT + " SET name=? WHERE id=?", n, id);
        }
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("name", n);
        if (multiCategoryActive() && hasDimensionColumn() && !dim.isBlank()) {
            m.put("dimension", dim);
        }
        return m;
    }

    public static void deleteCategory(long id) {
        Integer exists = db().queryForObject("SELECT COUNT(*) FROM " + CAT + " WHERE id=?", Integer.class, id);
        if (exists == null || exists == 0) throw new IllegalArgumentException("分类不存在");
        Integer used;
        if (multiCategoryActive()) {
            used = db().queryForObject(
                    "SELECT COUNT(*) FROM " + ITEM_CAT + " WHERE category_id=?", Integer.class, id);
        } else {
            used = db().queryForObject(
                    softDeleteEnabled && hasDeletedAt()
                            ? "SELECT COUNT(*) FROM " + ITEM + " WHERE category_id=? AND deleted_at IS NULL"
                            : "SELECT COUNT(*) FROM " + ITEM + " WHERE category_id=?",
                    Integer.class, id);
        }
        if (used != null && used > 0) {
            throw new IllegalStateException("该分类下仍有 " + used + " 条记录，无法删除");
        }
        db().update("DELETE FROM " + CAT + " WHERE id=?", id);
    }

    public static List<Map<String, Object>> listCategories() {
        String cntSql;
        if (multiCategoryActive()) {
            cntSql = softDeleteEnabled && hasDeletedAt()
                    ? "(SELECT COUNT(DISTINCT ic.item_id) FROM " + ITEM_CAT + " ic JOIN " + ITEM
                            + " b ON b.id=ic.item_id WHERE ic.category_id=c.id AND b.deleted_at IS NULL)"
                    : "(SELECT COUNT(DISTINCT ic.item_id) FROM " + ITEM_CAT
                            + " ic WHERE ic.category_id=c.id)";
        } else {
            cntSql = softDeleteEnabled && hasDeletedAt()
                    ? "(SELECT COUNT(*) FROM " + ITEM + " b WHERE b.category_id=c.id AND b.deleted_at IS NULL)"
                    : "(SELECT COUNT(*) FROM " + ITEM + " b WHERE b.category_id=c.id)";
        }
        String dimSel = multiCategoryActive() && hasDimensionColumn() ? ", c.dimension" : "";
        return db().query(
                "SELECT c.id, c.name" + dimSel + ", " + cntSql + " AS item_count "
                        + "FROM " + CAT + " c ORDER BY c.id",
                (rs, i) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getLong("id"));
                    row.put("name", rs.getString("name"));
                    if (multiCategoryActive() && hasDimensionColumn()) {
                        try {
                            row.put("dimension", rs.getString("dimension"));
                        } catch (Exception ignored) {
                        }
                    }
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
        Map<String, Object> visible = getItem(id);
        if (visible != null) return visible;
        if (publishReviewEnabled) return getItemAdmin(id);
        return null;
    }

    /**
     * 门户用户发布档案：即时上架；owner_username 固定登录名（「我的」归属）。
     * author 可填业务字段（如联系人）；未传则仍用登录名。
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
        com.thesis.service.UserStore.assertNotPostMuted(uid);
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
        if (publishReviewEnabled) {
            extra.put("status", "pending_review");
        }
        return addItem(t, author, content, cat, stock, "", extra);
    }

    /** 本人发布（含站长下架）：优先按 owner_username，否则按作者列=登录名 */
    public static Map<String, Object> pageMine(String username, int page, int size) {
        if (!userPublishEnabled) {
            throw new IllegalStateException("当前领域未开放用户发帖");
        }
        String uid = username == null ? "" : username.trim();
        if (uid.isBlank()) throw new IllegalArgumentException("未登录");
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String where = hasOwnerUsername()
                ? " WHERE owner_username=?"
                : (" WHERE " + authorColumn() + "=?");
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
        if (patch.containsKey("categoryIds") && multiCategoryActive()) {
            List<Long> catIds = parseIdList(patch.get("categoryIds"));
            syncItemCategories(id, catIds);
            categoryId = catIds.isEmpty() ? 0L : catIds.get(0);
        }
        int stock = patch.get("stock") != null ? toInt(patch.get("stock")) : toInt(m.get("stock"));
        Object startRaw = patch.containsKey("startAt") ? patch.get("startAt") : m.get("startAt");
        Object endRaw = patch.containsKey("endAt") ? patch.get("endAt") : m.get("endAt");
        String status = availStatus(stock, startRaw, endRaw);
        if (shopMarketplaceEnabled || publishReviewEnabled) {
            String cur = str(m.get("status")).trim();
            // 待审/驳回只能走 approve/reject，禁止 update 改写为 available 进公开目录
            if ("pending_review".equals(cur) || "rejected".equals(cur)) {
                status = cur;
            } else if (patch.containsKey("status") && patch.get("status") != null) {
                String st = String.valueOf(patch.get("status")).trim();
                if (!st.isBlank() && !"pending_review".equals(st) && !"rejected".equals(st)) {
                    status = st;
                }
            }
        }
        db().update(
                "UPDATE " + ITEM + " SET title=?, " + authorColumn() + "=?, " + isbnColumn()
                        + "=?, category_id=?, stock=?, status=?, cover_url=? WHERE id=?",
                title, author, isbn, categoryId, stock, status, cover, id);
        if (hasStartAt()) {
            Timestamp ts = parseTs(startRaw);
            db().update("UPDATE " + ITEM + " SET start_at=? WHERE id=?", ts, id);
        }
        if (hasEndAt()) {
            Timestamp ts = parseTs(patch.containsKey("endAt") ? patch.get("endAt") : m.get("endAt"));
            db().update("UPDATE " + ITEM + " SET end_at=? WHERE id=?", ts, id);
        }
        if (hasApplyDeadline()) {
            Timestamp ts = parseTs(
                    patch.containsKey("applyDeadlineAt") ? patch.get("applyDeadlineAt") : m.get("applyDeadlineAt"),
                    true);
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
        if (galleryEnabled && patch.containsKey("galleryImages")) {
            if (!hasGalleryJson()) {
                throw new IllegalStateException("系统未配置图集字段，无法保存");
            }
            db().update(
                    "UPDATE " + ITEM + " SET gallery_json=? WHERE id=?",
                    toGalleryJson(patch.get("galleryImages")), id);
        }
        writeDetailAttrs(id, patch, m);
        if (roomEquipmentEnabled && patch.containsKey("equipmentNames")) {
            replaceItemEquipment(id, patch.get("equipmentNames"));
        }
        patchOptStr(id, patch, "publisher", "publisher", 100);
        patchOptStr(id, patch, "callNo", "call_no", 64);
        patchOptStr(id, patch, "conditionGrade", "condition_grade", 16);
        patchOptStr(id, patch, "sellerNote", "seller_note", 255);
        patchOptInt(id, patch, "needPermit", "need_permit");
        patchOptInt(id, patch, "monthLimit", "month_limit");
        patchOptInt(id, patch, "pityN", "pity_n");
        patchOptNum(id, patch, "depositYuan", "deposit_yuan");
        patchOptStr(id, patch, "rentStage", "rent_stage", 16);
        patchOptStr(id, patch, "digitalKind", "digital_kind", 16);
        patchOptInt(id, patch, "sellByWeight", "sell_by_weight");
        patchOptStr(id, patch, "weightUnit", "weight_unit", 8);
        patchOptStr(id, patch, "spicyLevel", "spicy_level", 16);
        patchOptInt(id, patch, "isVegetarian", "is_vegetarian");
        patchOptInt(id, patch, "requiresTraining", "requires_training");
        patchOptStr(id, patch, "ownerName", "owner_name", 64);
        patchOptStr(id, patch, "ownerUsername", "owner_username", 64);
        patchOptStr(id, patch, "stage", "stage", 32);
        if (hasItemColumn("stage") && patch.containsKey("stage")) {
            syncSignupStageAvailability(id, stock);
        }
        patchOptNum(id, patch, "credit", "credit");
        patchOptNum(id, patch, "serviceHours", "service_hours");
        patchOptInt(id, patch, "seatCapacity", "seat_capacity");
        patchOptInt(id, patch, "seatRows", "seat_rows");
        patchOptInt(id, patch, "seatCols", "seat_cols");
        patchOptStr(id, patch, "feeRule", "fee_rule", 64);
        patchOptStr(id, patch, "stylistName", "stylist_name", 32);
        patchOptInt(id, patch, "durationSec", "duration_sec");
        patchOptInt(id, patch, "releaseYear", "release_year");
        patchOptStr(id, patch, "region", "region", 64);
        patchOptStr(id, patch, "summary", "summary", 512);
        patchOptStr(id, patch, "harvestOn", "harvest_on", 32);
        if (flashPriceEnabled
                && (patch.containsKey("promoPrice")
                        || patch.containsKey("promoStart")
                        || patch.containsKey("promoEnd"))) {
            if (!hasPromoPrice()) {
                throw new IllegalStateException("系统未配置秒杀价字段，无法保存");
            }
            if (patch.containsKey("promoPrice")) {
                Object pr = patch.get("promoPrice");
                if (pr == null || String.valueOf(pr).isBlank()) {
                    db().update("UPDATE " + ITEM + " SET promo_price=NULL WHERE id=?", id);
                } else {
                    db().update("UPDATE " + ITEM + " SET promo_price=? WHERE id=?", parseMoney(pr), id);
                }
            }
            if (patch.containsKey("promoStart")) {
                db().update("UPDATE " + ITEM + " SET promo_start=? WHERE id=?", parseTs(patch.get("promoStart")), id);
            }
            if (patch.containsKey("promoEnd")) {
                db().update("UPDATE " + ITEM + " SET promo_end=? WHERE id=?", parseTs(patch.get("promoEnd")), id);
            }
        }
        if (usesDedicatedSpecNote() && patch.containsKey("specNote")) {
            patchOptStr(id, patch, "specNote", "spec_note", 128);
        }
        patchOptStr(id, patch, "itemKind", "item_kind", 16);
        patchOptStr(id, patch, "holdingLoc", "holding_loc", 128);
        patchOptStr(id, patch, "campusZone", "campus_zone", 64);
        patchOptStr(id, patch, "shelfNo", "shelf_no", 64);
        patchOptStr(id, patch, "batchNo", "batch_no", 64);
        patchOptStr(id, patch, "expireOn", "expire_on", 32);
        patchOptStr(id, patch, "evalOpenOn", "eval_open_on", 32);
        patchOptStr(id, patch, "evalCloseOn", "eval_close_on", 32);
        patchOptStr(id, patch, "promoSize", "promo_size", 64);
        patchOptStr(id, patch, "hangPlace", "hang_place", 128);
        patchOptStr(id, patch, "quietStart", "quiet_start", 8);
        patchOptStr(id, patch, "quietEnd", "quiet_end", 8);
        patchOptNum(id, patch, "maxIssueCopies", "max_issue_copies");
        patchOptNum(id, patch, "trainHoursTotal", "train_hours_total");
        patchOptStr(id, patch, "inspectExpireOn", "inspect_expire_on", 32);
        patchOptNum(id, patch, "budgetTotal", "budget_total");
        patchOptInt(id, patch, "visitSlotCap", "visit_slot_cap");
        patchOptInt(id, patch, "absentWarnN", "absent_warn_n");
        patchOptInt(id, patch, "hideEvalResult", "hide_eval_result");
        patchOptInt(id, patch, "signRemarkVisible", "sign_remark_visible");
        patchOptInt(id, patch, "parkingMutex", "parking_mutex");
        patchOptInt(id, patch, "examPassMin", "exam_pass_min");
        patchOptNum(id, patch, "teachingWeight", "teaching_weight");
        patchOptNum(id, patch, "attitudeWeight", "attitude_weight");
        patchOptNum(id, patch, "contentWeight", "content_weight");
        patchOptStr(id, patch, "midDueOn", "mid_due_on", 32);
        patchOptStr(id, patch, "finalDueOn", "final_due_on", 32);
        patchOptStr(id, patch, "meetingOn", "meeting_on", 32);
        patchOptStr(id, patch, "resolutionNote", "resolution_note", 512);
        patchOptStr(id, patch, "supplierContact", "supplier_contact", 64);
        patchOptStr(id, patch, "allowedGender", "allowed_gender", 16);
        patchOptStr(id, patch, "allowedGrades", "allowed_grades", 64);
        patchOptStr(id, patch, "maintainDue", "maintain_due", 32);
        patchOptStr(id, patch, "loanOrg", "loan_org", 128);
        patchOptStr(id, patch, "clcCode", "clc_code", 32);
        patchOptStr(id, patch, "calibCertUrl", "calib_cert_url", 255);
        patchOptStr(id, patch, "calibDue", "calib_due", 32);
        patchOptStr(id, patch, "repairTicketNo", "repair_ticket_no", 64);
        patchOptStr(id, patch, "slotStatus", "slot_status", 16);
        patchOptStr(id, patch, "buildingZone", "building_zone", 64);
        patchOptStr(id, patch, "bountyNote", "bounty_note", 128);
        patchOptStr(id, patch, "textbook", "textbook", 255);
        patchOptStr(id, patch, "dayItinerary", "day_itinerary", 2000);
        patchOptStr(id, patch, "leaderContact", "leader_contact", 128);
        patchOptStr(id, patch, "meetingPoint", "meeting_point", 128);
        patchOptStr(id, patch, "checkinPlace", "checkin_place", 128);
        patchOptStr(id, patch, "courseKind", "course_kind", 16);
        patchOptStr(id, patch, "prereqCode", "prereq_code", 64);
        patchOptInt(id, patch, "minGroupSize", "min_group_size");
        patchOptStr(id, patch, "sessionGroup", "session_group", 64);
        patchOptStr(id, patch, "applyInviteCode", "apply_invite_code", 64);
        patchOptStr(id, patch, "sponsorNote", "sponsor_note", 255);
        patchOptStr(id, patch, "groupPriceNote", "group_price_note", 2000);
        patchOptNum(id, patch, "feeYuan", "fee_yuan");
        patchOptNum(id, patch, "minAge", "min_age");
        patchOptNum(id, patch, "maxAge", "max_age");
        patchOptStr(id, patch, "lostCategory", "lost_category", 32);
        patchOptInt(id, patch, "viewCount", "view_count");
        patchOptInt(id, patch, "pinTop", "pin_top");
        patchOptStr(id, patch, "college", "college", 64);
        patchOptStr(id, patch, "planUrl", "plan_url", 255);
        patchOptStr(id, patch, "volunteerRole", "volunteer_role", 64);
        patchOptInt(id, patch, "surveyFormId", "survey_form_id");
        patchOptStr(id, patch, "weatherNote", "weather_note", 2000);
        patchOptStr(id, patch, "singleRoomNote", "single_room_note", 2000);
        patchOptStr(id, patch, "tags", "tags", 255);
        patchOptStr(id, patch, "leadSource", "lead_source", 64);
        patchOptStr(id, patch, "paymentPlan", "payment_plan", 255);
        patchOptStr(id, patch, "locationDesc", "location_desc", 255);
        patchOptStr(id, patch, "fundForm", "fund_form", 32);
        patchOptStr(id, patch, "hireDept", "hire_dept", 64);
        patchOptStr(id, patch, "priceHistory", "price_history", 255);
        patchOptStr(id, patch, "vrUrl", "vr_url", 255);
        if (patch.containsKey("foundAt")) {
            if (!hasItemColumn("found_at")) {
                throw new IllegalStateException("系统未配置该字段");
            }
            Timestamp ts = parseTs(patch.get("foundAt"));
            try {
                db().update("UPDATE " + ITEM + " SET found_at=? WHERE id=?", ts, id);
            } catch (Exception e) {
                throw new IllegalStateException("保存字段失败: foundAt", e);
            }
        }
        if (patch.containsKey("tagIds") && tagsEnabled()) {
            syncItemTags(id, patch.get("tagIds"));
        }
        if (patch.containsKey("seatRows") || patch.containsKey("seatCols")) {
            try {
                com.thesis.service.SeatStore.syncLayout(id);
            } catch (RuntimeException e) {
                throw e;
            } catch (Exception e) {
                throw new IllegalStateException("同步选座布局失败", e);
            }
        }
        return getItemAdmin(id);
    }

    private static void patchOptStr(long id, Map<String, Object> patch, String key, String col, int max) {
        if (!patch.containsKey(key)) return;
        if (!hasItemColumn(col)) {
            throw new IllegalStateException("系统未配置该字段");
        }
        String v = str(patch.get(key)).trim();
        if (max > 0 && v.length() > max) v = v.substring(0, max);
        try {
            db().update("UPDATE " + ITEM + " SET `" + col + "`=? WHERE id=?", v, id);
        } catch (Exception e) {
            throw new IllegalStateException("保存字段失败: " + key, e);
        }
    }

    private static void patchOptInt(long id, Map<String, Object> patch, String key, String col) {
        if (!patch.containsKey(key)) return;
        if (!hasItemColumn(col)) {
            throw new IllegalStateException("系统未配置该字段");
        }
        try {
            db().update("UPDATE " + ITEM + " SET `" + col + "`=? WHERE id=?", toInt(patch.get(key)), id);
        } catch (Exception e) {
            throw new IllegalStateException("保存字段失败: " + key, e);
        }
    }

    private static void patchOptNum(long id, Map<String, Object> patch, String key, String col) {
        if (!patch.containsKey(key)) return;
        if (!hasItemColumn(col)) {
            throw new IllegalStateException("系统未配置该字段");
        }
        try {
            double v = 0;
            Object raw = patch.get(key);
            if (raw instanceof Number n) v = n.doubleValue();
            else if (raw != null && !String.valueOf(raw).isBlank()) v = Double.parseDouble(String.valueOf(raw).trim());
            db().update("UPDATE " + ITEM + " SET `" + col + "`=? WHERE id=?", v, id);
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("保存字段失败: " + key, e);
        }
    }

    public static boolean deleteItem(long id) {
        if (softDeleteEnabled) {
            if (!hasDeletedAt()) {
                throw new IllegalStateException("系统未配置下架字段，无法软删除");
            }
            return db().update("UPDATE " + ITEM + " SET deleted_at=NOW() WHERE id=? AND deleted_at IS NULL", id) > 0;
        }
        if (tagsEnabled()) {
            try {
                db().update("DELETE FROM " + ITEM_TAG + " WHERE " + itemTagFk + "=?", id);
            } catch (Exception ignored) {
            }
        }
        if (multiCategoryActive()) {
            try {
                db().update("DELETE FROM " + ITEM_CAT + " WHERE item_id=?", id);
            } catch (Exception ignored) {
            }
        }
        return db().update("DELETE FROM " + ITEM + " WHERE id=?", id) > 0;
    }

    public static boolean restoreItem(long id) {
        if (!hasDeletedAt()) return false;
        return db().update("UPDATE " + ITEM + " SET deleted_at=NULL WHERE id=?", id) > 0;
    }

    /** 多店商品 / 投稿先审：超管将待审设为上架（有库存）或不可用（无库存）。 */
    public static Map<String, Object> approveMarketplaceItem(long id) {
        Map<String, Object> m = getItemRaw(id);
        if (m == null) return null;
        String cur = str(m.get("status")).trim();
        if (!"pending_review".equals(cur)) {
            throw new IllegalStateException("仅待审核条目可通过审核上架");
        }
        int stock = m.get("stock") instanceof Number n ? n.intValue() : 0;
        String status = stock > 0 ? "available" : "unavailable";
        db().update("UPDATE " + ITEM + " SET status=? WHERE id=?", status, id);
        return getItemAdmin(id);
    }

    /** 多店商品 / 投稿先审：超管驳回，不进公开目录。 */
    public static Map<String, Object> rejectPublishItem(long id) {
        Map<String, Object> m = getItemRaw(id);
        if (m == null) return null;
        String cur = str(m.get("status")).trim();
        if (!"pending_review".equals(cur)) {
            throw new IllegalStateException("仅待审核条目可驳回");
        }
        db().update("UPDATE " + ITEM + " SET status='rejected' WHERE id=?", id);
        return getItemAdmin(id);
    }

    /** 库存预警：stock &lt; below；可选按店主过滤。 */
    public static int countLowStock(int below, String ownerUsername) {
        if (ITEM.isBlank() || below < 1) return 0;
        try {
            StringBuilder sql = new StringBuilder("SELECT COUNT(*) FROM " + ITEM + " WHERE stock < ?");
            List<Object> args = new ArrayList<>();
            args.add(below);
            if (hasDeletedAt()) sql.append(" AND deleted_at IS NULL");
            if (ownerUsername != null && !ownerUsername.isBlank() && hasOwnerUsername()) {
                sql.append(" AND owner_username=?");
                args.add(ownerUsername.trim());
            }
            Integer n = db().queryForObject(sql.toString(), Integer.class, args.toArray());
            return n == null ? 0 : n;
        } catch (Exception e) {
            return 0;
        }
    }

    public static Map<String, Object> getItemRaw(long id) {
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + ITEM + " WHERE id=?",
                (rs, i) -> mapItemRow(rs), id);
        return list.isEmpty() ? null : list.get(0);
    }

    /** 用户侧：已下架视为不存在 */
    public static Map<String, Object> getItem(long id) {
        expirePastStarts();
        Map<String, Object> m = getItemRaw(id);
        if (m == null) return null;
        if (isSoftDeleted(m)) return null;
        if (publishReviewEnabled) {
            String st = str(m.get("status")).trim();
            if ("pending_review".equals(st) || "rejected".equals(st)) return null;
        }
        return enrichItem(m);
    }

    /** 管理侧：含已下架 */
    public static Map<String, Object> getItemAdmin(long id) {
        Map<String, Object> m = getItemRaw(id);
        return m == null ? null : enrichItem(m);
    }

    /** 启事浏览计数 +1（无 view_count 列时 no-op）。 */
    public static void bumpViewCount(long id) {
        if (id <= 0 || !hasItemColumn("view_count")) return;
        try {
            db().update("UPDATE " + ITEM + " SET view_count=IFNULL(view_count,0)+1 WHERE id=?", id);
        } catch (Exception ignored) {
        }
    }

    public static Map<String, Object> pageItems(String keyword, Long categoryId, int page, int size) {
        return pageItems(keyword, categoryId, null, null, false, page, size, false, null);
    }

    public static Map<String, Object> pageItems(
            String keyword, Long categoryId, List<Long> tagIds, boolean includeDeleted, int page, int size) {
        return pageItems(keyword, categoryId, null, tagIds, includeDeleted, page, size, false, null);
    }

    /**
     * @param openCatalogOnly 用户目录：有 start_at 时只列未开场且可售（管理端传 false）
     */
    public static Map<String, Object> pageItems(
            String keyword,
            Long categoryId,
            List<Long> tagIds,
            boolean includeDeleted,
            int page,
            int size,
            boolean openCatalogOnly) {
        return pageItems(keyword, categoryId, null, tagIds, includeDeleted, page, size, openCatalogOnly, null);
    }

    /** 多维分类筛选：categoryIds 非空时走关联表；未开岛时忽略 categoryIds。 */
    public static Map<String, Object> pageItems(
            String keyword,
            Long categoryId,
            List<Long> categoryIds,
            List<Long> tagIds,
            boolean includeDeleted,
            int page,
            int size,
            boolean openCatalogOnly) {
        return pageItems(keyword, categoryId, categoryIds, tagIds, includeDeleted, page, size, openCatalogOnly, null);
    }

    /**
     * @param ownerUsernameFilter 非空且有 owner_username 列时按店主过滤；null/空白 = 不过滤
     */
    public static Map<String, Object> pageItems(
            String keyword,
            Long categoryId,
            List<Long> categoryIds,
            List<Long> tagIds,
            boolean includeDeleted,
            int page,
            int size,
            boolean openCatalogOnly,
            String ownerUsernameFilter) {
        expirePastStarts();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        if (hasDeletedAt() && !(includeDeleted && softDeleteEnabled)) {
            where.append(" AND deleted_at IS NULL");
        }
        if (openCatalogOnly && (hasStartAt() || hasEndAt())) {
            where.append(" AND status='available'");
            if (hasEndAt()) {
                where.append(" AND (end_at IS NULL OR end_at > NOW())");
            } else {
                where.append(" AND (start_at IS NULL OR start_at > NOW())");
            }
        }
        if (openCatalogOnly && shopMarketplaceEnabled) {
            where.append(" AND status='available'");
        }
        if (openCatalogOnly && publishReviewEnabled) {
            where.append(" AND status='available'");
        }
        if (ownerUsernameFilter != null && !ownerUsernameFilter.isBlank() && hasOwnerUsername()) {
            where.append(" AND owner_username=?");
            args.add(ownerUsernameFilter.trim());
        }
        if (multiCategoryActive()) {
            List<Long> cids = categoryIds;
            if ((cids == null || cids.isEmpty()) && categoryId != null && categoryId > 0) {
                cids = List.of(categoryId);
            }
            if (cids != null) {
                for (Long cid : cids) {
                    if (cid == null || cid <= 0) continue;
                    where.append(" AND EXISTS (SELECT 1 FROM ").append(ITEM_CAT)
                            .append(" ic WHERE ic.item_id=").append(ITEM)
                            .append(".id AND ic.category_id=?)");
                    args.add(cid);
                }
            }
        } else if (categoryId != null && categoryId > 0) {
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
        int tcount = total == null ? 0 : total;
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + ITEM + where
                        + (hasItemColumn("pin_top") ? " ORDER BY pin_top DESC, id DESC" : " ORDER BY id")
                        + " LIMIT ? OFFSET ?",
                (rs, i) -> enrichItem(mapItemRow(rs)), args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", tcount);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    /** 商家后台：仅本店商品（含待审）。 */
    public static Map<String, Object> pageItemsForMerchant(
            String ownerUsername, String keyword, Long categoryId, int page, int size) {
        return pageItems(keyword, categoryId, null, null, false, page, size, false, ownerUsername);
    }

    private static Map<String, Object> mapItemRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("title", rs.getString("title"));
        m.put("author", safeStr(rs, authorColumn()));
        if (flashPriceEnabled && hasPromoPrice()) {
            try {
                double promo = rs.getDouble("promo_price");
                if (!rs.wasNull()) m.put("promoPrice", promo);
            } catch (Exception ignored) {
            }
            try {
                m.put("promoStart", fmt(rs.getTimestamp("promo_start")));
            } catch (Exception ignored) {
            }
            try {
                m.put("promoEnd", fmt(rs.getTimestamp("promo_end")));
            } catch (Exception ignored) {
            }
            double list = parseMoneySoft(m.get("author"));
            m.put("listPriceYuan", list);
            boolean active = isPromoActive(m);
            m.put("promoActive", active);
            if (active) {
                double promo = parseMoneySoft(m.get("promoPrice"));
                m.put("priceYuan", promo > 0 ? promo : list);
            } else {
                m.put("priceYuan", list);
            }
        }
        m.put("isbn", safeStr(rs, isbnColumn()));
        m.put("categoryId", rs.getLong("category_id"));
        m.put("stock", rs.getInt("stock"));
        m.put("status", rs.getString("status"));
        if (usesDedicatedSpecNote()) {
            try {
                m.put("specNote", safeStr(rs, "spec_note"));
            } catch (Exception ignored) {
                m.put("specNote", "");
            }
        }
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
        putDetailAttrs(m, rs);
        if (roomEquipmentEnabled) {
            try {
                m.put("equipmentNames", listItemEquipmentNames(rs.getLong("id")));
            } catch (Exception e) {
                m.put("equipmentNames", List.of());
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
        putOptInt(m, rs, "need_permit", "needPermit");
        putOptInt(m, rs, "month_limit", "monthLimit");
        putOptInt(m, rs, "pity_n", "pityN");
        putOptNum(m, rs, "deposit_yuan", "depositYuan");
        putOptStr(m, rs, "rent_stage", "rentStage");
        putOptStr(m, rs, "digital_kind", "digitalKind");
        putOptInt(m, rs, "sell_by_weight", "sellByWeight");
        putOptStr(m, rs, "weight_unit", "weightUnit");
        putOptStr(m, rs, "spicy_level", "spicyLevel");
        putOptInt(m, rs, "is_vegetarian", "isVegetarian");
        putOptInt(m, rs, "requires_training", "requiresTraining");
        putOptStr(m, rs, "owner_name", "ownerName");
        putOptStr(m, rs, "owner_username", "ownerUsername");
        putOptStr(m, rs, "stage", "stage");
        putOptNum(m, rs, "credit", "credit");
        putOptNum(m, rs, "service_hours", "serviceHours");
        putOptInt(m, rs, "seat_capacity", "seatCapacity");
        putOptInt(m, rs, "seat_rows", "seatRows");
        putOptInt(m, rs, "seat_cols", "seatCols");
        putOptStr(m, rs, "fee_rule", "feeRule");
        putOptStr(m, rs, "stylist_name", "stylistName");
        putOptInt(m, rs, "duration_sec", "durationSec");
        putOptInt(m, rs, "release_year", "releaseYear");
        putOptStr(m, rs, "region", "region");
        putOptStr(m, rs, "summary", "summary");
        putOptStr(m, rs, "harvest_on", "harvestOn");
        putOptStr(m, rs, "item_kind", "itemKind");
        putOptStr(m, rs, "holding_loc", "holdingLoc");
        putOptStr(m, rs, "campus_zone", "campusZone");
        putOptStr(m, rs, "shelf_no", "shelfNo");
        putOptStr(m, rs, "batch_no", "batchNo");
        putOptStr(m, rs, "expire_on", "expireOn");
        putOptStr(m, rs, "eval_open_on", "evalOpenOn");
        putOptStr(m, rs, "eval_close_on", "evalCloseOn");
        putOptStr(m, rs, "promo_size", "promoSize");
        putOptStr(m, rs, "hang_place", "hangPlace");
        putOptStr(m, rs, "meeting_on", "meetingOn");
        putOptStr(m, rs, "resolution_note", "resolutionNote");
        putOptStr(m, rs, "supplier_contact", "supplierContact");
        putOptStr(m, rs, "allowed_gender", "allowedGender");
        putOptStr(m, rs, "allowed_grades", "allowedGrades");
        putOptStr(m, rs, "maintain_due", "maintainDue");
        putOptStr(m, rs, "loan_org", "loanOrg");
        putOptStr(m, rs, "clc_code", "clcCode");
        putOptStr(m, rs, "calib_cert_url", "calibCertUrl");
        putOptStr(m, rs, "calib_due", "calibDue");
        putOptStr(m, rs, "repair_ticket_no", "repairTicketNo");
        putOptStr(m, rs, "slot_status", "slotStatus");
        putOptStr(m, rs, "building_zone", "buildingZone");
        putOptStr(m, rs, "bounty_note", "bountyNote");
        putOptStr(m, rs, "textbook", "textbook");
        putOptStr(m, rs, "day_itinerary", "dayItinerary");
        putOptStr(m, rs, "leader_contact", "leaderContact");
        putOptStr(m, rs, "meeting_point", "meetingPoint");
        putOptStr(m, rs, "checkin_place", "checkinPlace");
        putOptStr(m, rs, "course_kind", "courseKind");
        putOptStr(m, rs, "prereq_code", "prereqCode");
        putOptInt(m, rs, "min_group_size", "minGroupSize");
        putOptStr(m, rs, "session_group", "sessionGroup");
        putOptStr(m, rs, "apply_invite_code", "applyInviteCode");
        putOptStr(m, rs, "quiet_start", "quietStart");
        putOptStr(m, rs, "quiet_end", "quietEnd");
        putOptNum(m, rs, "max_issue_copies", "maxIssueCopies");
        putOptNum(m, rs, "train_hours_total", "trainHoursTotal");
        putOptStr(m, rs, "inspect_expire_on", "inspectExpireOn");
        putOptNum(m, rs, "budget_total", "budgetTotal");
        putOptInt(m, rs, "visit_slot_cap", "visitSlotCap");
        putOptInt(m, rs, "absent_warn_n", "absentWarnN");
        putOptInt(m, rs, "hide_eval_result", "hideEvalResult");
        putOptInt(m, rs, "sign_remark_visible", "signRemarkVisible");
        putOptInt(m, rs, "parking_mutex", "parkingMutex");
        putOptInt(m, rs, "exam_pass_min", "examPassMin");
        putOptNum(m, rs, "teaching_weight", "teachingWeight");
        putOptNum(m, rs, "attitude_weight", "attitudeWeight");
        putOptNum(m, rs, "content_weight", "contentWeight");
        putOptStr(m, rs, "mid_due_on", "midDueOn");
        putOptStr(m, rs, "final_due_on", "finalDueOn");
        putOptStr(m, rs, "sponsor_note", "sponsorNote");
        putOptStr(m, rs, "group_price_note", "groupPriceNote");
        putOptNum(m, rs, "fee_yuan", "feeYuan");
        putOptNum(m, rs, "min_age", "minAge");
        putOptNum(m, rs, "max_age", "maxAge");
        putOptStr(m, rs, "lost_category", "lostCategory");
        putOptInt(m, rs, "view_count", "viewCount");
        putOptInt(m, rs, "pin_top", "pinTop");
        putOptStr(m, rs, "college", "college");
        putOptStr(m, rs, "plan_url", "planUrl");
        putOptStr(m, rs, "volunteer_role", "volunteerRole");
        putOptInt(m, rs, "survey_form_id", "surveyFormId");
        putOptStr(m, rs, "weather_note", "weatherNote");
        putOptStr(m, rs, "single_room_note", "singleRoomNote");
        putOptStr(m, rs, "tags", "tags");
        putOptStr(m, rs, "lead_source", "leadSource");
        putOptStr(m, rs, "payment_plan", "paymentPlan");
        putOptStr(m, rs, "location_desc", "locationDesc");
        putOptStr(m, rs, "fund_form", "fundForm");
        putOptStr(m, rs, "hire_dept", "hireDept");
        putOptStr(m, rs, "price_history", "priceHistory");
        putOptStr(m, rs, "vr_url", "vrUrl");
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
        if (multiCategoryActive()) {
            long id = toLong(b.get("id"));
            String dimSel = hasDimensionColumn() ? ", c.dimension" : "";
            List<Map<String, Object>> cats = db().query(
                    "SELECT c.id, c.name" + dimSel + " FROM " + CAT + " c JOIN " + ITEM_CAT
                            + " ic ON ic.category_id=c.id WHERE ic.item_id=? ORDER BY c.id",
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("id", rs.getLong("id"));
                        row.put("name", rs.getString("name"));
                        if (hasDimensionColumn()) {
                            try {
                                row.put("dimension", rs.getString("dimension"));
                            } catch (Exception ignored) {
                            }
                        }
                        return row;
                    },
                    id);
            List<Long> ids = new ArrayList<>();
            List<String> names = new ArrayList<>();
            for (Map<String, Object> c : cats) {
                ids.add(toLong(c.get("id")));
                names.add(str(c.get("name")));
            }
            m.put("categoryIds", ids);
            m.put("categoryNames", names);
            m.put("categories", cats);
            m.put("categoryName", String.join("、", names));
            if (!ids.isEmpty()) {
                m.put("categoryId", ids.get(0));
            }
        } else {
            long cid = toLong(b.get("categoryId"));
            List<String> names = db().query(
                    "SELECT name FROM " + CAT + " WHERE id=?", (rs, i) -> rs.getString(1), cid);
            m.put("categoryName", names.isEmpty() ? "" : names.get(0));
        }
        m.put("deleted", isSoftDeleted(m));
        if (shopMarketplaceEnabled && hasOwnerUsername()) {
            String owner = str(b.get("ownerUsername"));
            if (!owner.isBlank()) {
                m.put("shopName", resolveShopName(owner));
            }
        }
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

    private static String resolveShopName(String ownerUsername) {
        try {
            com.thesis.service.UserStore.Profile p = com.thesis.service.UserStore.get(ownerUsername);
            if (p == null) return ownerUsername;
            if (p.extras != null) {
                String shop = p.extras.get("shopName");
                if (shop != null && !shop.isBlank()) return shop.trim();
            }
            if (p.nickname != null && !p.nickname.isBlank()) return p.nickname.trim();
            return ownerUsername;
        } catch (Exception e) {
            return ownerUsername;
        }
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

    /** 过档期：仅 start→过开始下架；有 end（查寝窗等）→过结束下架；另叠 expire_on 日期下架。 */
    public static int expirePastStarts() {
        int n = 0;
        if (hasEndAt()) {
            try {
                n += db().update(
                        "UPDATE " + ITEM + " SET status='unavailable' "
                                + "WHERE status='available' AND end_at IS NOT NULL AND end_at <= NOW()");
            } catch (Exception ignored) {
            }
        } else if (hasStartAt()) {
            try {
                n += db().update(
                        "UPDATE " + ITEM + " SET status='unavailable' "
                                + "WHERE status='available' AND start_at IS NOT NULL AND start_at <= NOW()");
            } catch (Exception ignored) {
            }
        }
        n += expirePastExpireOn();
        return n;
    }

    /**
     * 招聘岗位等：expire_on（yyyy-MM-dd）到期自动下架。
     */
    public static int expirePastExpireOn() {
        if (!hasItemColumn("expire_on")) return 0;
        try {
            if (hasItemColumn("stage")) {
                db().update(
                        "UPDATE " + ITEM + " SET stage='已下架' "
                                + "WHERE status='available' AND stage IN ('招领中','招领','') "
                                + "AND expire_on IS NOT NULL AND TRIM(expire_on)<>'' "
                                + "AND LEFT(TRIM(expire_on),10) <= DATE_FORMAT(CURDATE(),'%Y-%m-%d')");
            }
            return db().update(
                    "UPDATE " + ITEM + " SET status='unavailable' "
                            + "WHERE status='available' AND expire_on IS NOT NULL AND TRIM(expire_on)<>'' "
                            + "AND LEFT(TRIM(expire_on),10) <= DATE_FORMAT(CURDATE(),'%Y-%m-%d')");
        } catch (Exception e) {
            return 0;
        }
    }

    /**
     * 合同/许可/年检：日期列临近到期前 N 天站内信提醒管理端（每档一次）。
     * N 来自 TicketStore.notifyArchiveExpireDays；缺列或未开则 no-op。
     */
    public static void addTrainHours(long id, double hours) {
        if (id <= 0 || !(hours > 0)) return;
        if (!hasItemColumn("train_hours_total")) {
            throw new IllegalStateException("系统未配置累计培训学时字段");
        }
        try {
            int n = db().update(
                    "UPDATE " + ITEM + " SET train_hours_total=IFNULL(train_hours_total,0)+? WHERE id=?",
                    hours, id);
            if (n <= 0) {
                throw new IllegalStateException("累计培训学时写入失败");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("累计培训学时写入失败", e);
        }
    }

    public static int maybeNotifyExpireSoon() {
        return notifyExpireSoonOn("expire_on")
                + notifyExpireSoonOn("inspect_expire_on")
                + notifyExpireSoonOn("mid_due_on")
                + notifyExpireSoonOn("final_due_on");
    }

    private static int notifyExpireSoonOn(String dateCol) {
        if (!Set.of("expire_on", "inspect_expire_on", "mid_due_on", "final_due_on").contains(dateCol)) return 0;
        int days = TicketStore.notifyArchiveExpireDays;
        if (days <= 0) return 0;
        if (!hasItemColumn(dateCol) || !hasItemColumn("expire_soon_notified_at")) return 0;
        List<Map<String, Object>> rows;
        try {
            rows = db().queryForList(
                    "SELECT id, title, " + dateCol + " AS expire_on FROM " + ITEM
                            + " WHERE status='available' "
                            + "AND " + dateCol + " IS NOT NULL AND TRIM(" + dateCol + ")<>'' "
                            + "AND LEFT(TRIM(" + dateCol + "),10) > DATE_FORMAT(CURDATE(),'%Y-%m-%d') "
                            + "AND LEFT(TRIM(" + dateCol + "),10) <= DATE_FORMAT(DATE_ADD(CURDATE(), INTERVAL ? DAY),'%Y-%m-%d') "
                            + "AND expire_soon_notified_at IS NULL "
                            + "LIMIT 50",
                    days);
        } catch (Exception e) {
            return 0;
        }
        if (rows == null || rows.isEmpty()) return 0;
        List<Map<String, Object>> admins;
        try {
            admins = UserStore.listManaged("admin", "subadmins", null);
        } catch (Exception e) {
            admins = List.of();
        }
        if (admins == null || admins.isEmpty()) return 0;
        int notified = 0;
        Timestamp ts = Timestamp.valueOf(LocalDateTime.now());
        for (Map<String, Object> row : rows) {
            long id = 0L;
            Object idObj = row.get("id");
            if (idObj instanceof Number n) id = n.longValue();
            else {
                try { id = Long.parseLong(String.valueOf(idObj)); } catch (Exception ignored) {}
            }
            if (id <= 0) continue;
            String title = row.get("title") == null ? "" : String.valueOf(row.get("title")).trim();
            if (title.isBlank()) title = "档案#" + id;
            String expireOn = row.get("expire_on") == null ? "" : String.valueOf(row.get("expire_on")).trim();
            if (expireOn.length() > 10) expireOn = expireOn.substring(0, 10);
            String body = "inspect_expire_on".equals(dateCol)
                    ? "「" + title + "」年检将于 " + expireOn + " 到期，请及时办理。"
                    : "mid_due_on".equals(dateCol)
                    ? "「" + title + "」中期材料节点为 " + expireOn + "，请及时提交。"
                    : "final_due_on".equals(dateCol)
                    ? "「" + title + "」结题材料节点为 " + expireOn + "，请及时提交。"
                    : "「" + title + "」将于 " + expireOn + " 到期，请及时办理续签或延期。";
            String msgTitle = TicketStore.allowContractExpireRemind && "expire_on".equals(dateCol)
                    ? "合同续签提醒"
                    : "即将到期提醒";
            int sent = 0;
            for (Map<String, Object> admin : admins) {
                String un = admin.get("username") == null ? "" : String.valueOf(admin.get("username")).trim();
                if (un.isBlank()) continue;
                try {
                    com.thesis.service.MessageStore.send(un, msgTitle, body, "archive", id);
                    sent++;
                } catch (Exception ignored) {
                }
            }
            if (TicketStore.allowContractExpireRemind && "expire_on".equals(dateCol)) {
                try {
                    List<String> owners = TicketSql.db().query(
                            "SELECT DISTINCT username FROM " + TicketStore.TICKET
                                    + " WHERE " + TicketStore.itemFkColumn()
                                    + "=? AND status IN ('approved','returned')",
                            (rs, i) -> TicketSql.str(rs.getString("username")),
                            id);
                    if (owners != null) {
                        for (String un : owners) {
                            if (un == null || un.isBlank()) continue;
                            try {
                                com.thesis.service.MessageStore.send(un.trim(), msgTitle, body, "archive", id);
                                sent++;
                            } catch (Exception ignored) {
                            }
                        }
                    }
                } catch (Exception ignored) {
                }
            }
            if (sent <= 0) continue;
            try {
                db().update(
                        "UPDATE " + ITEM + " SET expire_soon_notified_at=? WHERE id=?",
                        ts, id);
                notified++;
            } catch (Exception ignored) {
            }
        }
        return notified;
    }

    /** 档期已关闭：有结束时间看 end；否则看 start（出发/开场）。 */
    static boolean isScheduleClosed(Map<String, Object> item) {
        if (item == null) return false;
        if (hasEndAt()) return isPastEndValue(item.get("endAt"));
        if (hasStartAt()) return isPastStartValue(item.get("startAt"));
        return false;
    }

    static boolean isPastStart(Map<String, Object> item) {
        return isPastStartValue(item == null ? null : item.get("startAt"));
    }

    private static boolean isPastStartValue(Object raw) {
        return isPastTs(raw);
    }

    private static boolean isPastEndValue(Object raw) {
        return isPastTs(raw);
    }

    private static boolean isPastTs(Object raw) {
        if (raw == null) return false;
        String sa = String.valueOf(raw).trim();
        if (sa.isBlank() || "null".equalsIgnoreCase(sa)) return false;
        try {
            String norm = sa.length() >= 19 ? sa.substring(0, 19) : sa;
            LocalDateTime t = LocalDateTime.parse(norm.replace(' ', 'T'));
            return !t.isAfter(LocalDateTime.now());
        } catch (Exception e) {
            try {
                LocalDateTime t = LocalDateTime.parse(sa, FMT);
                return !t.isAfter(LocalDateTime.now());
            } catch (Exception ignored) {
                // 脏时间：视为已过，标为不可用
                return true;
            }
        }
    }

    private static String availStatus(int stock, Object startAt, Object endAt) {
        if (stock <= 0) return "unavailable";
        if (hasEndAt() && isPastEndValue(endAt)) return "unavailable";
        if (!hasEndAt() && hasStartAt() && isPastStartValue(startAt)) return "unavailable";
        return "available";
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
            db().execute("ALTER TABLE `" + ITEM + "` ADD COLUMN `gallery_json` TEXT NULL");
            hasGalleryJson = true;
        } catch (Exception ignored) {
            hasGalleryJson = hasItemColumn("gallery_json");
        }
    }

    public static boolean hasDetailJson() {
        if (hasDetailJson == null) hasDetailJson = hasItemColumn("detail_json");
        return hasDetailJson;
    }

    /** 开题属性落真列；旧包仍可能只有 detail_json。 */
    public static void ensureDetailAttrColumns() {
        for (String key : detailAttrKeys) {
            String col = detailAttrColumn(key);
            if (col.isBlank() || hasItemColumn(col)) continue;
            String ddl = detailAttrSqlDdl(detailAttrTypes.getOrDefault(key, "string"));
            try {
                db().execute("ALTER TABLE `" + ITEM + "` ADD COLUMN `" + col + "` " + ddl);
            } catch (Exception ignored) {
            }
        }
    }

    /** @deprecated 旧包回退探测；新 bake 禁止补 detail_json 列 */
    public static void ensureDetailColumn() {
        hasDetailJson = hasItemColumn("detail_json");
    }

    private static List<String> parseDetailKeys(String keysCsv, Map<String, String> typesOut) {
        if (keysCsv == null || keysCsv.isBlank()) return List.of();
        List<String> keys = new ArrayList<>();
        for (String part : keysCsv.split(",")) {
            String raw = part == null ? "" : part.trim();
            if (raw.isBlank()) continue;
            String key = raw;
            String type = "string";
            int colon = raw.indexOf(':');
            if (colon > 0) {
                key = raw.substring(0, colon).trim();
                String t = raw.substring(colon + 1).trim().toLowerCase();
                if ("number".equals(t) || "date".equals(t) || "string".equals(t)) type = t;
            }
            if (!key.matches("[A-Za-z][A-Za-z0-9]{0,31}") || keys.contains(key)) continue;
            keys.add(key);
            if (typesOut != null) typesOut.put(key, type);
        }
        return List.copyOf(keys);
    }

    private static String detailAttrColumn(String key) {
        if (key == null || key.isBlank()) return "";
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < key.length(); i++) {
            char c = key.charAt(i);
            if (Character.isUpperCase(c) && i > 0) sb.append('_');
            sb.append(Character.toLowerCase(c));
        }
        String col = sb.toString();
        return col.matches("[a-z][a-z0-9_]{0,47}") ? col : "";
    }

    private static String detailAttrSqlDdl(String fieldType) {
        if ("date".equals(fieldType)) return "DATE NULL";
        if ("number".equals(fieldType)) return "DECIMAL(10,2) NULL";
        return "VARCHAR(80) DEFAULT ''";
    }

    private static Object detailAttrSqlValue(String key, String value) {
        String type = detailAttrTypes.getOrDefault(key, "string");
        if ("number".equals(type)) {
            if (value == null || value.isBlank()) return null;
            try {
                return new java.math.BigDecimal(value);
            } catch (Exception e) {
                throw new IllegalStateException("详情属性数值格式不正确");
            }
        }
        if ("date".equals(type)) {
            if (value == null || value.isBlank()) return null;
            String s = value.trim();
            if (s.length() >= 10) s = s.substring(0, 10);
            try {
                return java.sql.Date.valueOf(s);
            } catch (Exception e) {
                throw new IllegalStateException("详情属性日期格式不正确");
            }
        }
        if (value == null) return "";
        return value.length() > 80 ? value.substring(0, 80) : value;
    }

    private static void writeDetailAttrs(long id, Map<String, Object> patch, Map<String, Object> current) {
        if (!detailAttrsEnabled || detailAttrKeys.isEmpty() || patch == null) return;
        boolean hit = false;
        for (String key : detailAttrKeys) {
            if (patch.containsKey(key)) {
                hit = true;
                break;
            }
        }
        if (!hit) return;
        boolean wroteCol = false;
        boolean needJsonFallback = false;
        Map<String, String> bag = new LinkedHashMap<>();
        for (String key : detailAttrKeys) {
            String col = detailAttrColumn(key);
            Object prev = current == null ? null : current.get(key);
            if (prev != null) bag.put(key, String.valueOf(prev));
            if (!patch.containsKey(key) || patch.get(key) == null) {
                if (col.isBlank() || !hasItemColumn(col)) needJsonFallback = true;
                continue;
            }
            String value = String.valueOf(patch.get(key)).trim();
            bag.put(key, value);
            if (!col.isBlank() && hasItemColumn(col)) {
                try {
                    db().update("UPDATE " + ITEM + " SET `" + col + "`=? WHERE id=?", detailAttrSqlValue(key, value), id);
                    wroteCol = true;
                } catch (IllegalStateException e) {
                    throw e;
                } catch (Exception e) {
                    throw new IllegalStateException("详情属性保存失败");
                }
            } else {
                needJsonFallback = true;
            }
        }
        if (wroteCol && !needJsonFallback) return;
        if (!hasDetailJson()) {
            if (!wroteCol) {
                throw new IllegalStateException("系统未配置详情属性字段，无法保存");
            }
            return;
        }
        try {
            db().update(
                    "UPDATE " + ITEM + " SET detail_json=? WHERE id=?",
                    new ObjectMapper().writeValueAsString(bag), id);
        } catch (Exception e) {
            throw new IllegalStateException("详情属性保存失败");
        }
    }

    private static void putDetailAttrs(Map<String, Object> row, java.sql.ResultSet rs) {
        if (!detailAttrsEnabled || detailAttrKeys.isEmpty()) return;
        for (String key : detailAttrKeys) {
            String col = detailAttrColumn(key);
            if (col.isBlank()) continue;
            try {
                String v = rs.getString(col);
                if (v != null && !v.isBlank()) row.put(key, v);
            } catch (Exception ignored) {
            }
        }
        if (!hasDetailJson()) return;
        try {
            String raw = rs.getString("detail_json");
            if (raw == null || raw.isBlank()) return;
            Map<String, Object> bag = new ObjectMapper().readValue(raw, new TypeReference<>() {});
            for (String key : detailAttrKeys) {
                if (row.containsKey(key)) continue;
                Object value = bag.get(key);
                if (value != null) row.put(key, String.valueOf(value));
            }
        } catch (Exception ignored) {
        }
    }

    public static boolean hasEquipmentJson() {
        return hasItemEquipmentTable();
    }

    public static void ensureEquipmentColumn() {
        /* 关联表由 bake 注入，禁止 ALTER 补 equipment_json */
    }

    private static boolean hasItemEquipmentTable() {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='item_equipment'",
                    Integer.class);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static void replaceItemEquipment(long itemId, Object raw) {
        if (!hasItemEquipmentTable()) {
            throw new IllegalStateException("系统未配置配套设施表，无法保存");
        }
        List<String> names = equipmentNamesOf(raw);
        db().update("DELETE FROM item_equipment WHERE item_id=?", itemId);
        for (String name : names) {
            Long eid = db().queryForObject(
                    "SELECT id FROM sys_equipment_dict WHERE name=? AND enabled=1 LIMIT 1",
                    Long.class, name);
            if (eid != null) {
                db().update(
                        "INSERT IGNORE INTO item_equipment (item_id, equipment_id) VALUES (?,?)",
                        itemId, eid);
            }
        }
    }

    private static List<String> listItemEquipmentNames(long itemId) {
        if (!hasItemEquipmentTable()) return List.of();
        try {
            return db().query(
                    "SELECT d.name FROM item_equipment ie "
                            + "JOIN sys_equipment_dict d ON d.id=ie.equipment_id "
                            + "WHERE ie.item_id=? ORDER BY d.sort_order, d.id",
                    (rs, i) -> rs.getString("name"),
                    itemId);
        } catch (Exception e) {
            return List.of();
        }
    }

    private static List<String> equipmentNamesOf(Object raw) {
        List<String> names = new ArrayList<>();
        if (raw instanceof List<?> list) {
            for (Object o : list) {
                if (o == null) continue;
                String u = String.valueOf(o).trim();
                if (!u.isBlank()) names.add(u);
                if (names.size() >= 20) break;
            }
            return names;
        }
        if (raw != null) {
            String s = String.valueOf(raw).trim();
            if (s.startsWith("[")) names.addAll(parseEquipment(s));
        }
        return names;
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
        if (publishReviewEnabled || shopMarketplaceEnabled) {
            where += " AND status='available'";
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

    private static List<String> parseEquipment(String raw) {
        if (raw == null || raw.isBlank()) return List.of();
        try {
            List<String> list = new ObjectMapper().readValue(raw, new TypeReference<>() {});
            if (list == null) return List.of();
            List<String> out = new ArrayList<>();
            for (String s : list) {
                if (s == null) continue;
                String u = s.trim();
                if (!u.isBlank()) out.add(u);
                if (out.size() >= 20) break;
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
        syncJunctionIds(itemId, parseIdList(raw), ITEM_TAG, itemTagFk, "tag_id");
    }

    private static void syncItemCategories(long itemId, Object raw) {
        if (!multiCategoryActive()) return;
        syncJunctionIds(itemId, parseIdList(raw), ITEM_CAT, "item_id", "category_id");
    }

    private static void syncJunctionIds(
            long itemId, List<Long> ids, String junction, String itemFk, String refFk) {
        db().update("DELETE FROM " + junction + " WHERE " + itemFk + "=?", itemId);
        for (Long refId : ids) {
            try {
                db().update(
                        "INSERT INTO " + junction + " (" + itemFk + ", " + refFk + ") VALUES (?,?)",
                        itemId, refId);
            } catch (Exception ignored) {
            }
        }
    }

    @SuppressWarnings("unchecked")
    private static List<Long> parseIdList(Object raw) {
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
        return ids;
    }

    private static boolean hasCategoryColumn(String col) {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=? AND COLUMN_NAME=?",
                    Integer.class, CAT, col);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
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
        return parseTs(o, false);
    }

    /** @param endOfDay 纯日期（YYYY-MM-DD）时取当日 23:59:59（报名截止） */
    private static Timestamp parseTs(Object o, boolean endOfDay) {
        if (o == null) return null;
        String s = String.valueOf(o).trim();
        if (s.isBlank() || "null".equalsIgnoreCase(s)) return null;
        try {
            if (s.contains("T")) s = s.replace('T', ' ');
            if (s.length() == 10) {
                s = s + (endOfDay ? " 23:59:59" : " 00:00:00");
            } else if (s.length() == 16) {
                s = s + ":00";
            }
            return Timestamp.valueOf(LocalDateTime.parse(s.substring(0, Math.min(19, s.length())), FMT));
        } catch (Exception e) {
            try {
                return Timestamp.valueOf(s.substring(0, Math.min(19, s.length())));
            } catch (Exception e2) {
                throw new IllegalStateException("时间格式无效", e2);
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
        syncOccupyStageWithStock(itemId, delta);
        if (delta < 0 && stockWarnNotify) {
            maybeNotifyLowStock(itemId);
        }
    }

    /** 扣减后库存低于预警值 → 站内信提醒总管（开题挂 stockWarnNotify）。 */
    private static void maybeNotifyLowStock(long itemId) {
        Map<String, Object> book = getItemRaw(itemId);
        if (book == null) return;
        int stock = toInt(book.get("stock"));
        if (stock >= stockWarnBelow) return;
        String title = str(book.get("title")).trim();
        if (title.isBlank()) title = "档案#" + itemId;
        try {
            com.thesis.service.MessageStore.notifyAdmins(
                    "库存预警",
                    "「" + title + "」当前库存 " + stock + "，已低于预警值 " + stockWarnBelow + "，请及时补货。",
                    "archive",
                    itemId);
        } catch (Exception ignored) {
        }
    }

    /**
     * 床位占用皮：stock 扣至 0 且 stage 为「空闲」→「已分配」；回补且为「已分配」→「空闲」。
     * 线路报名皮：stock 扣至 0 且 stage 为「开放报名」→「满员」；回补且为「满员」→「开放报名」。
     * 已出团/下架/维修中等其它 stage 语义不动。
     */
    private static void syncOccupyStageWithStock(long itemId, int delta) {
        if (!hasItemColumn("stage")) return;
        Map<String, Object> book = getItemRaw(itemId);
        if (book == null || !book.containsKey("stage")) return;
        String stage = str(book.get("stage")).trim();
        int stock = toInt(book.get("stock"));
        try {
            if (delta < 0 && stock <= 0 && (stage.isEmpty() || "空闲".equals(stage))) {
                db().update("UPDATE " + ITEM + " SET stage=? WHERE id=?", "已分配", itemId);
            } else if (delta > 0 && stock > 0 && "已分配".equals(stage)) {
                db().update("UPDATE " + ITEM + " SET stage=? WHERE id=?", "空闲", itemId);
            } else if (delta < 0 && stock <= 0 && ("在库".equals(stage) || stage.isEmpty())) {
                db().update("UPDATE " + ITEM + " SET stage=? WHERE id=?", "借出", itemId);
            } else if (delta > 0 && stock > 0 && "借出".equals(stage)) {
                db().update("UPDATE " + ITEM + " SET stage=? WHERE id=?", "在库", itemId);
            } else if (delta < 0 && stock <= 0 && "开放报名".equals(stage)) {
                db().update("UPDATE " + ITEM + " SET stage=? WHERE id=?", "满员", itemId);
            } else if (delta > 0 && stock > 0 && "满员".equals(stage)) {
                db().update("UPDATE " + ITEM + " SET stage=? WHERE id=?", "开放报名", itemId);
            } else if (delta < 0 && stock <= 0 && "开放".equals(stage)) {
                db().update("UPDATE " + ITEM + " SET stage=? WHERE id=?", "已满", itemId);
            } else if (delta > 0 && stock > 0 && "已满".equals(stage)) {
                db().update("UPDATE " + ITEM + " SET stage=? WHERE id=?", "开放", itemId);
            } else if (delta < 0 && stock <= 0
                    && ("招领中".equals(stage) || "招领".equals(stage) || stage.isEmpty())) {
                db().update("UPDATE " + ITEM + " SET stage=? WHERE id=?", "已认领", itemId);
            } else if (delta > 0 && stock > 0 && "已认领".equals(stage)) {
                db().update("UPDATE " + ITEM + " SET stage=? WHERE id=?", "招领中", itemId);
            }
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("同步档案阶段失败", e);
        }
    }

    /** 线路报名：手改 stage 为满员/已出团/下架时同步 status=unavailable；改回开放报名且有余位则 available。 */
    private static void syncSignupStageAvailability(long id, int stock) {
        Map<String, Object> book = getItemRaw(id);
        if (book == null || !book.containsKey("stage")) return;
        String audit = str(book.get("status")).trim();
        if ("pending_review".equals(audit) || "rejected".equals(audit)) {
            return;
        }
        String stage = str(book.get("stage")).trim();
        try {
            if ("满员".equals(stage) || "已出团".equals(stage) || "下架".equals(stage)) {
                db().update("UPDATE " + ITEM + " SET status='unavailable' WHERE id=?", id);
            } else if ("开放报名".equals(stage) && stock > 0) {
                db().update("UPDATE " + ITEM + " SET status='available' WHERE id=?", id);
            }
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("同步报名状态失败", e);
        }
    }

    public static long countItems() {
        return countItems(null);
    }

    /** @param ownerUsername 多店商家只计本店商品；超管/单店传 null */
    public static long countItems(String ownerUsername) {
        String owner = ownerUsername == null ? "" : ownerUsername.trim();
        boolean byOwner = !owner.isBlank() && hasOwnerUsername();
        if (softDeleteEnabled && hasDeletedAt()) {
            if (byOwner) {
                Long n = db().queryForObject(
                        "SELECT COUNT(*) FROM " + ITEM + " WHERE deleted_at IS NULL AND owner_username=?",
                        Long.class,
                        owner);
                return n == null ? 0 : n;
            }
            Long n = db().queryForObject(
                    "SELECT COUNT(*) FROM " + ITEM + " WHERE deleted_at IS NULL", Long.class);
            return n == null ? 0 : n;
        }
        if (byOwner) {
            Long n = db().queryForObject(
                    "SELECT COUNT(*) FROM " + ITEM + " WHERE owner_username=?", Long.class, owner);
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
        return stockByCategory(limit, null);
    }

    /** @param ownerUsername 非空且有 owner_username 列时只合计该店主商品 */
    public static List<Map<String, Object>> stockByCategory(int limit, String ownerUsername) {
        int lim = Math.max(1, Math.min(limit, 20));
        try {
            boolean byOwner = ownerUsername != null && !ownerUsername.isBlank() && hasOwnerUsername();
            String sql = "SELECT c.name AS name, COALESCE(SUM(i.stock),0) AS value FROM " + CAT + " c"
                    + " LEFT JOIN " + ITEM + " i ON i.category_id=c.id"
                    + (byOwner ? " AND i.owner_username=?" : "")
                    + " GROUP BY c.id, c.name ORDER BY value DESC LIMIT " + lim;
            if (byOwner) {
                return db().query(
                        sql,
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("name", rs.getString("name"));
                            row.put("value", rs.getLong("value"));
                            return row;
                        },
                        ownerUsername.trim());
            }
            return db().query(
                    sql,
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

    /**
     * 档案字段分组计数（工作台饼图/漏斗：stage、lead_source、rent_stage 等）。
     */
    public static List<Map<String, Object>> countByItemColumn(String column, int limit) {
        if (column == null || column.isBlank() || !hasItemColumn(column.trim())) {
            return List.of();
        }
        String col = column.trim().replaceAll("[^a-zA-Z0-9_]", "");
        if (col.isEmpty() || !hasItemColumn(col)) return List.of();
        int lim = Math.max(1, Math.min(limit, 20));
        try {
            return db().query(
                    "SELECT COALESCE(NULLIF(TRIM(" + col + "),''),'未填') AS name, COUNT(*) AS value FROM " + ITEM
                            + " GROUP BY COALESCE(NULLIF(TRIM(" + col + "),''),'未填')"
                            + " ORDER BY value DESC LIMIT " + lim,
                    (rs, i) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("name", rs.getString("name"));
                        row.put("value", rs.getLong("value"));
                        return row;
                    });
        } catch (Exception ignored) {
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

    static String str(Object o) {
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
