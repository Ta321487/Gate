package com.thesis.capability;

import com.thesis.config.JpaSupport;
import com.thesis.service.MessageStore;
import com.thesis.service.SeatStore;
import com.thesis.service.UserStore;
import com.thesis.config.JpaDb;
import com.thesis.config.GeneratedKeyHolder;
import com.thesis.config.KeyHolder;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 能力 order_lines：购物车 + 多明细订单（无真支付）。
 */
public final class OrderStore {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private static String CART = "";
    private static String ORDER = "";
    private static String LINE = "";
    private static boolean enabled = false;
    private static boolean useQuota = true;
    private static boolean lineCustom = false;
    private static boolean lineCustomPlaceConfirmed = false;
    private static boolean noCasualRefund = false;
    /** 收货后可申请售后天数；0=不限（开题未钉 afterSaleDays 时）。 */
    private static int afterSaleDays = 0;
    private static final ThreadLocal<Set<Long>> CART_ITEM_FILTER = new ThreadLocal<>();
    private static final ThreadLocal<Map<String, Object>> PLACE_EXTRAS = new ThreadLocal<>();
    private static double packagingFeeYuan = 0;
    private static double deliveryFeeBaseYuan = 0;
    private static double deliveryFeeFreeYuan = 0;
    private static int etaMinutes = 0;

    private OrderStore() {}

    public static void bind(String cartTable, String orderTable, String lineTable, boolean quota) {
        CART = cartTable == null ? "" : cartTable.trim();
        ORDER = orderTable == null ? "" : orderTable.trim();
        LINE = lineTable == null ? "" : lineTable.trim();
        enabled = !CART.isBlank() && !ORDER.isBlank() && !LINE.isBlank();
        useQuota = quota;
        AddressStore.resetCache();
        // 履约列由 bake 按域写入 schema，禁止运行时补餐饮/物流超集
    }

    public static void unbind() {
        enabled = false;
        CART = ORDER = LINE = "";
    }

    public static boolean enabled() {
        return enabled;
    }

    public static void configureLineCustom(boolean on, boolean placeConfirmed, boolean noCasual) {
        lineCustom = on;
        lineCustomPlaceConfirmed = on && placeConfirmed;
        noCasualRefund = noCasual;
    }

    /** 收货后 N 天可售后；≤0 表示不按天限。 */
    public static void configureAfterSaleDays(int days) {
        afterSaleDays = Math.max(0, days);
    }

    /** 供评价等跨 Store 联表 */
    public static String orderTable() {
        return ORDER;
    }

    public static String lineTable() {
        return LINE;
    }

    private static JpaDb db() {
        return JpaSupport.db();
    }

    private static String fmt(Timestamp ts) {
        return ts == null ? null : ts.toLocalDateTime().format(FMT);
    }

    private static double priceOf(Map<String, Object> item) {
        return unitPriceOf(item);
    }

    /** 档案单价：挂 flash_price 时窗内用活动价，否则 author/price_yuan。 */
    public static double unitPriceOf(Map<String, Object> item) {
        return ArchiveStore.effectiveUnitPrice(item);
    }

    public static List<Map<String, Object>> listCart(String username) {
        requireEnabled();
        return db().query(
                "SELECT c.id, c.item_id, c.qty FROM " + CART + " c WHERE c.username=? ORDER BY c.id",
                (rs, i) -> enrichCartRow(rs.getLong("id"), rs.getLong("item_id"), rs.getInt("qty")),
                username);
    }

    private static Map<String, Object> enrichCartRow(long id, long itemId, int qty) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("itemId", itemId);
        m.put("qty", qty);
        Map<String, Object> live = ArchiveStore.getItem(itemId);
        Map<String, Object> raw = live != null ? live : ArchiveStore.getItemRaw(itemId);
        if (live != null) {
            m.put("title", ArchiveStore.lineTitleWithSpec(live));
            m.put("priceYuan", priceOf(live));
            m.put("sellByWeight", live.get("sellByWeight"));
            m.put("weightUnit", live.get("weightUnit"));
            m.put("stock", live.get("stock"));
            m.put("coverUrl", live.get("coverUrl"));
            m.put("categoryName", live.get("categoryName"));
            if (live.get("shopName") != null) m.put("shopName", live.get("shopName"));
            if (live.get("ownerUsername") != null) m.put("ownerUsername", live.get("ownerUsername"));
            if (live.get("specNote") != null) m.put("specNote", live.get("specNote"));
            if (live.get("isbn") != null) m.put("isbn", live.get("isbn"));
            if (live.get("freeShipYuan") != null) m.put("freeShipYuan", live.get("freeShipYuan"));
            m.put("status", live.get("status"));
            int stock = live.get("stock") instanceof Number n ? n.intValue() : 0;
            boolean invalid = stock <= 0 || !"available".equals(String.valueOf(live.get("status")));
            m.put("invalid", invalid);
            m.put("invalidReason", invalid ? (stock <= 0 ? "暂无库存" : "已下架") : "");
            if (!invalid) {
                m.put("specAlts", ArchiveStore.listAvailableByTitle(String.valueOf(live.get("title")), itemId));
            } else {
                m.put("specAlts", List.of());
            }
        } else {
            m.put("title", raw != null ? String.valueOf(raw.getOrDefault("title", "")) : "");
            m.put("priceYuan", 0);
            m.put("stock", 0);
            m.put("invalid", true);
            m.put("invalidReason", "已下架");
            m.put("specAlts", List.of());
        }
        double price = ((Number) m.get("priceYuan")).doubleValue();
        m.put("lineYuan", round2(price * qty));
        return m;
    }

    public static void beginCartItemFilter(Collection<Long> itemIds) {
        if (itemIds == null || itemIds.isEmpty()) {
            CART_ITEM_FILTER.remove();
            return;
        }
        Set<Long> ids = new LinkedHashSet<>();
        for (Long id : itemIds) {
            if (id != null && id > 0) ids.add(id);
        }
        if (ids.isEmpty()) CART_ITEM_FILTER.remove();
        else CART_ITEM_FILTER.set(ids);
    }

    public static void endCartItemFilter() {
        CART_ITEM_FILTER.remove();
    }

    public static void beginPlaceExtras(Map<String, Object> extras) {
        if (extras == null || extras.isEmpty()) {
            PLACE_EXTRAS.remove();
            return;
        }
        PLACE_EXTRAS.set(new LinkedHashMap<>(extras));
    }

    public static void endPlaceExtras() {
        PLACE_EXTRAS.remove();
    }

    public static void configureFoodFees(
            double packaging, double deliveryBase, double deliveryFree, int eta) {
        packagingFeeYuan = packaging > 0 ? packaging : 0;
        deliveryFeeBaseYuan = deliveryBase > 0 ? deliveryBase : 0;
        deliveryFeeFreeYuan = deliveryFree > 0 ? deliveryFree : 0;
        etaMinutes = eta > 0 ? eta : 0;
    }

    private static List<Map<String, Object>> applyCartItemFilter(List<Map<String, Object>> cart) {
        Set<Long> want = CART_ITEM_FILTER.get();
        if (want == null || want.isEmpty()) return cart;
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> line : cart) {
            long iid = line.get("itemId") instanceof Number n ? n.longValue() : 0L;
            if (want.contains(iid)) out.add(line);
        }
        return out;
    }

    private static void clearPlacedCart(String username, List<Map<String, Object>> cart) {
        Set<Long> want = CART_ITEM_FILTER.get();
        if (want == null || want.isEmpty()) {
            clearCart(username);
            return;
        }
        for (Map<String, Object> line : cart) {
            long iid = line.get("itemId") instanceof Number n ? n.longValue() : 0L;
            removeCart(username, iid);
        }
    }

    public static int clearInvalidCart(String username) {
        requireEnabled();
        int n = 0;
        for (Map<String, Object> row : listCart(username)) {
            if (!Boolean.TRUE.equals(row.get("invalid"))) continue;
            long iid = row.get("itemId") instanceof Number num ? num.longValue() : 0L;
            if (iid > 0 && removeCart(username, iid)) n++;
        }
        return n;
    }

    public static Map<String, Object> replaceCartItem(String username, long fromId, long toId) {
        requireEnabled();
        if (fromId <= 0 || toId <= 0) throw new IllegalArgumentException("请选择规格");
        if (fromId == toId) {
            for (Map<String, Object> row : listCart(username)) {
                long iid = row.get("itemId") instanceof Number n ? n.longValue() : 0L;
                if (iid == fromId) return row;
            }
            throw new IllegalArgumentException("购物车里没有这件商品");
        }
        Map<String, Object> from = ArchiveStore.getItem(fromId);
        if (from == null) throw new IllegalArgumentException("原商品已下架");
        Map<String, Object> to = ArchiveStore.getItem(toId);
        if (to == null) throw new IllegalArgumentException("该规格暂不可选");
        String fromTitle = String.valueOf(from.getOrDefault("title", "")).trim();
        String toTitle = String.valueOf(to.getOrDefault("title", "")).trim();
        if (!fromTitle.equals(toTitle)) {
            throw new IllegalArgumentException("只能换成同一商品的其它规格");
        }
        int qty = 1;
        for (Map<String, Object> row : listCart(username)) {
            long iid = row.get("itemId") instanceof Number n ? n.longValue() : 0L;
            if (iid == fromId) {
                qty = row.get("qty") instanceof Number n ? n.intValue() : 1;
                break;
            }
        }
        removeCart(username, fromId);
        int existQty = 0;
        for (Map<String, Object> row : listCart(username)) {
            long iid = row.get("itemId") instanceof Number n ? n.longValue() : 0L;
            if (iid == toId) {
                existQty = row.get("qty") instanceof Number n ? n.intValue() : 0;
                break;
            }
        }
        return upsertCart(username, toId, Math.max(1, existQty + qty));
    }

    public static Map<String, Object> upsertCart(String username, long itemId, int qty) {
        requireEnabled();
        if (qty <= 0) {
            removeCart(username, itemId);
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("removed", true);
            return out;
        }
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalArgumentException("商品不存在");
        PurchaseGateStore.assertCanBuy(username, itemId, qty);
        BlindBoxStore.assertPurchasable(itemId);
        ConsignStore.assertOnSale(itemId);
        BuybackStore.assertListed(itemId);
        Integer exist = db().queryForObject(
                "SELECT COUNT(*) FROM " + CART + " WHERE username=? AND item_id=?",
                Integer.class, username, itemId);
        if (exist != null && exist > 0) {
            db().update("UPDATE " + CART + " SET qty=? WHERE username=? AND item_id=?", qty, username, itemId);
        } else {
            db().update("INSERT INTO " + CART + " (username,item_id,qty) VALUES (?,?,?)", username, itemId, qty);
        }
        List<Map<String, Object>> rows = db().query(
                "SELECT id, item_id, qty FROM " + CART + " WHERE username=? AND item_id=?",
                (rs, i) -> enrichCartRow(rs.getLong("id"), rs.getLong("item_id"), rs.getInt("qty")),
                username, itemId);
        return rows.isEmpty() ? Map.of() : rows.get(0);
    }

    public static boolean removeCart(String username, long itemId) {
        requireEnabled();
        return db().update("DELETE FROM " + CART + " WHERE username=? AND item_id=?", username, itemId) > 0;
    }

    public static void clearCart(String username) {
        requireEnabled();
        db().update("DELETE FROM " + CART + " WHERE username=?", username);
    }

    public static Map<String, Object> placeOrder(String username, String remark) {
        return placeOrder(username, remark, null, null, null, null, null, null);
    }

    /**
     * @param addressId 地址簿 id；也可直接传 receiver/phone/address 快照
     * @param tasteNote 口味 / 忌口等（点餐常用）
     */
    public static Map<String, Object> placeOrder(
            String username,
            String remark,
            Long addressId,
            String receiverName,
            String receiverPhone,
            String addressLine,
            String deliveryType,
            String tasteNote) {
        return placeOrder(
                username, remark, addressId, receiverName, receiverPhone, addressLine, deliveryType, tasteNote, null, null, null);
    }

    public static Map<String, Object> placeOrder(
            String username,
            String remark,
            Long addressId,
            String receiverName,
            String receiverPhone,
            String addressLine,
            String deliveryType,
            String tasteNote,
            String couponCode) {
        return placeOrder(
                username,
                remark,
                addressId,
                receiverName,
                receiverPhone,
                addressLine,
                deliveryType,
                tasteNote,
                couponCode,
                null,
                null);
    }

    public static Map<String, Object> placeOrder(
            String username,
            String remark,
            Long addressId,
            String receiverName,
            String receiverPhone,
            String addressLine,
            String deliveryType,
            String tasteNote,
            String couponCode,
            String payChannel,
            String payPassword) {
        return placeOrder(
                username, remark, addressId, receiverName, receiverPhone, addressLine,
                deliveryType, tasteNote, couponCode, payChannel, payPassword, null, null, null, null);
    }

    public static Map<String, Object> placeOrder(
            String username,
            String remark,
            Long addressId,
            String receiverName,
            String receiverPhone,
            String addressLine,
            String deliveryType,
            String tasteNote,
            String couponCode,
            String payChannel,
            String payPassword,
            List<Map<String, Object>> lineExtras,
            String deliveryOn,
            Long slotId,
            Long campaignId) {
        requireEnabled();
        if (GroupBuyStore.enabled()) GroupBuyStore.sweep();
        if (LoyaltyStore.anyEnabled()) {
            ensureLoyaltyColumns();
        }
        if (hasOrderColumn("refund_status")) {
            ensureRefundColumns();
        }
        boolean demoPay = ArchiveStore.shopMarketplaceEnabled();
        String channel = payChannel == null ? "" : payChannel.trim().toLowerCase(Locale.ROOT);
        if (demoPay) {
            ensurePayChannelColumn();
            if (!"alipay".equals(channel) && !"wechat".equals(channel)) {
                throw new IllegalArgumentException("请选择支付宝或微信支付");
            }
            String pw = payPassword == null ? "" : payPassword.trim();
            if (pw.length() < 4) {
                throw new IllegalArgumentException("请输入支付密码（至少 4 位）");
            }
        }
        List<Map<String, Object>> cart = applyCartItemFilter(listCart(username));
        List<Map<String, Object>> buyable = new ArrayList<>();
        for (Map<String, Object> line : cart) {
            if (Boolean.TRUE.equals(line.get("invalid"))) continue;
            buyable.add(line);
        }
        cart = buyable;
        if (cart.isEmpty()) throw new IllegalStateException("请先勾选要结算的商品");
        if (campaignId != null && campaignId > 0) {
            java.util.ArrayList<Long> ids = new java.util.ArrayList<>();
            for (Map<String, Object> line : cart) {
                ids.add(((Number) line.get("itemId")).longValue());
            }
            GroupBuyStore.assertJoin(campaignId, username, ids);
        }
        double total = 0;
        for (Map<String, Object> line : cart) {
            int qty = ((Number) line.get("qty")).intValue();
            long itemId = ((Number) line.get("itemId")).longValue();
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            if (item == null) throw new IllegalStateException("商品不存在：" + line.get("title"));
            int stock = item.get("stock") instanceof Number n ? n.intValue() : 0;
            if (useQuota && stock < qty) {
                throw new IllegalStateException(ArchiveStore.stockShortageTitled(
                        String.valueOf(item.get("title")), stock));
            }
            PurchaseGateStore.assertCanBuy(username, itemId, qty);
            BlindBoxStore.assertPurchasable(itemId);
            ConsignStore.assertOnSale(itemId);
        BuybackStore.assertListed(itemId);
            Map<String, Object> priced = WeighSaleStore.priceLine(item, qty, extraForItem(lineExtras, itemId));
            total += ((Number) priced.get("lineYuan")).doubleValue();
        }
        double subtotal = round2(total);
        Map<String, Object> windowSnap = null;
        if (DeliveryWindowStore.enabled()) {
            windowSnap = DeliveryWindowStore.quote(slotId == null ? 0L : slotId, deliveryOn);
            double rate = windowSnap.get("priceRate") instanceof Number n ? n.doubleValue() : 1;
            if (rate < 1) rate = 1;
            subtotal = round2(subtotal * rate);
        }
        String coupon = couponCode == null ? "" : couponCode.trim();
        Map<String, Object> priceSnap = null;
        double payable = subtotal;
        if (LoyaltyStore.anyEnabled()) {
            priceSnap = LoyaltyStore.previewPrice(subtotal, username, coupon);
            payable = ((Number) priceSnap.get("payableYuan")).doubleValue();
            // 在线支付仍扣账户余额；不对接微信/支付宝商户 SDK ≠ 免除余额
            if (LoyaltyStore.isWalletEnabled() && !Boolean.TRUE.equals(priceSnap.get("balanceEnough"))) {
                throw new IllegalStateException(String.valueOf(priceSnap.getOrDefault(
                        "message",
                        "账户余额不足，请先在个人中心或购物车充值")));
            }
            if (!coupon.isBlank() && LoyaltyStore.isCouponEnabled()
                    && priceSnap.get("couponCode") == null
                    && priceSnap.get("couponMessage") != null) {
                throw new IllegalStateException(String.valueOf(priceSnap.get("couponMessage")));
            }
        }
        String note = remark == null ? "" : remark.trim();
        String taste = tasteNote == null ? "" : tasteNote.trim();
        String dtype = deliveryType == null ? "" : deliveryType.trim();
        String rName = receiverName == null ? "" : receiverName.trim();
        String rPhone = receiverPhone == null ? "" : receiverPhone.trim();
        String addr = addressLine == null ? "" : addressLine.trim();
        if (addressId != null && addressId > 0 && AddressStore.available()) {
            Map<String, Object> a = AddressStore.get(addressId, username);
            if (a == null) throw new IllegalArgumentException("收货地址不存在");
            if (rName.isBlank()) rName = String.valueOf(a.getOrDefault("contactName", ""));
            if (rPhone.isBlank()) rPhone = String.valueOf(a.getOrDefault("phone", ""));
            if (addr.isBlank()) addr = String.valueOf(a.getOrDefault("addressLine", ""));
        }
        // 仅当 schema 含收货列时校验地址；酒店等瘦订单表跳过
        if (hasOrderColumn("receiver_name")) {
            boolean needAddr = dtype.isBlank() || dtype.contains("配送") || dtype.contains("快递")
                    || "配送到家".equals(dtype);
            if (needAddr && (rName.isBlank() || rPhone.isBlank() || addr.isBlank())) {
                throw new IllegalArgumentException("请选择或填写收货人、手机与地址");
            }
            if (!needAddr && rName.isBlank()) {
                rName = username;
            }
        }
        // 多店在线支付成功后进入待发货；单店仍待确认；成团单为 grouping（须一次算完，供下方 lambda 捕获）
        final String initialStatus = (campaignId != null && campaignId > 0)
                ? "grouping"
                : ((demoPay || lineCustomPlaceConfirmed) ? "confirmed" : "pending");
        Map<String, Object> placeX = PLACE_EXTRAS.get();
        if (placeX == null) placeX = Map.of();
        String tableNo = strPlace(placeX.get("tableNo"));
        String utensilOpt = strPlace(placeX.get("utensilOpt"));
        String packOpt = strPlace(placeX.get("packOpt"));
        String mergeCode = strPlace(placeX.get("mergeCode")).toUpperCase(Locale.ROOT);
        boolean wantPackaging = boolPlace(placeX.get("packagingFee"))
                || packOpt.contains("打包")
                || boolPlace(placeX.get("wantPackaging"));
        assertStallOpenForCart(cart);
        assertRequiredCategoryInCart(cart);
        double packagingFee = 0;
        if (wantPackaging && hasOrderColumn("packaging_fee_yuan") && packagingFeeYuan > 0) {
            packagingFee = packagingFeeYuan;
        }
        double deliveryFee = 0;
        boolean isDelivery = dtype.contains("配送") || dtype.contains("外卖");
        if (isDelivery && hasOrderColumn("delivery_fee_yuan") && deliveryFeeBaseYuan > 0) {
            if (deliveryFeeFreeYuan <= 0 || payable < deliveryFeeFreeYuan) {
                deliveryFee = deliveryFeeBaseYuan;
            }
        }
        if (dtype.contains("堂食") && tableNo.isBlank() && hasOrderColumn("table_no")) {
            throw new IllegalArgumentException("请填写桌号");
        }
        String etaText = "";
        if (isDelivery && hasOrderColumn("eta_text") && etaMinutes > 0) {
            etaText = "约 " + etaMinutes + " 分钟送达";
        }
        payable = round2(payable + packagingFee + deliveryFee);
        KeyHolder kh = new GeneratedKeyHolder();
        double finalTotal = payable;
        String fName = rName, fPhone = rPhone, fAddr = addr, fType = dtype, fTaste = taste;
        // food thicken snapshot for extraCols (assigned after LinkedHashMap created)
        final String fTableNo = tableNo;
        final String fUtensil = utensilOpt;
        final String fPack = packOpt;
        final String fMerge = mergeCode;
        final double fPackagingFee = packagingFee;
        final double fDeliveryFee = deliveryFee;
        final String fEtaText = etaText;
        requireOrderColIfPresent("receiver_name", "收货人", !fName.isBlank());
        requireOrderColIfPresent("receiver_phone", "收货电话", !fPhone.isBlank());
        requireOrderColIfPresent("address_line", "收货地址", !fAddr.isBlank());
        requireOrderColIfPresent("delivery_type", "配送方式", !fType.isBlank());
        requireOrderColIfPresent("taste_note", "口味备注", !fTaste.isBlank());
        if (demoPay && channel != null && !channel.isBlank()) {
            requireOrderColIfPresent("pay_channel", "支付渠道", true);
        }
        LinkedHashMap<String, Object> extraCols = new LinkedHashMap<>();
        if (hasOrderColumn("receiver_name")) extraCols.put("receiver_name", fName);
        if (hasOrderColumn("receiver_phone")) extraCols.put("receiver_phone", fPhone);
        if (hasOrderColumn("address_line")) extraCols.put("address_line", fAddr);
        if (hasOrderColumn("delivery_type")) extraCols.put("delivery_type", fType);
        if (hasOrderColumn("taste_note")) extraCols.put("taste_note", fTaste);
        if (demoPay && hasOrderColumn("pay_channel")) extraCols.put("pay_channel", channel);
        if (windowSnap != null) {
            requireOrderColIfPresent("delivery_on", "配送日期", true);
            requireOrderColIfPresent("slot_id", "配送时段", true);
            requireOrderColIfPresent("fulfill_mode", "履约方式", true);
            requireOrderColIfPresent("slot_label", "时段", true);
            requireOrderColIfPresent("price_rate", "节日倍率", true);
            if (hasOrderColumn("delivery_on")) extraCols.put("delivery_on", windowSnap.get("deliveryOn"));
            if (hasOrderColumn("slot_id")) extraCols.put("slot_id", windowSnap.get("slotId"));
            if (hasOrderColumn("fulfill_mode")) extraCols.put("fulfill_mode", windowSnap.get("fulfillMode"));
            if (hasOrderColumn("slot_label")) extraCols.put("slot_label", windowSnap.get("slotLabel"));
            if (hasOrderColumn("price_rate")) extraCols.put("price_rate", windowSnap.get("priceRate"));
        }
        requireOrderColIfPresent("table_no", "桌号", !fTableNo.isBlank());
        requireOrderColIfPresent("utensil_opt", "餐具", !fUtensil.isBlank());
        requireOrderColIfPresent("pack_opt", "打包", !fPack.isBlank());
        requireOrderColIfPresent("merge_code", "拼单码", !fMerge.isBlank());
        if (hasOrderColumn("table_no") && !fTableNo.isBlank()) extraCols.put("table_no", fTableNo);
        if (hasOrderColumn("utensil_opt") && !fUtensil.isBlank()) extraCols.put("utensil_opt", fUtensil);
        if (hasOrderColumn("pack_opt") && !fPack.isBlank()) extraCols.put("pack_opt", fPack);
        if (hasOrderColumn("merge_code") && !fMerge.isBlank()) extraCols.put("merge_code", fMerge);
        if (hasOrderColumn("packaging_fee_yuan") && fPackagingFee > 0) {
            extraCols.put("packaging_fee_yuan", String.format(java.util.Locale.ROOT, "%.2f", fPackagingFee));
        }
        if (hasOrderColumn("delivery_fee_yuan") && fDeliveryFee > 0) {
            extraCols.put("delivery_fee_yuan", String.format(java.util.Locale.ROOT, "%.2f", fDeliveryFee));
        }
                if (hasOrderColumn("eta_text") && !fEtaText.isBlank()) extraCols.put("eta_text", fEtaText);
        String invoiceTitle = strPlace(placeX.get("invoiceTitle"));
        if (hasOrderColumn("invoice_title") && !invoiceTitle.isBlank()) {
            extraCols.put("invoice_title", invoiceTitle);
            if (hasOrderColumn("invoice_status")) {
                extraCols.put("invoice_status", "pending");
            }
        }
        db().update(con -> {
            Timestamp now = Timestamp.valueOf(LocalDateTime.now());
            StringBuilder cols = new StringBuilder("username,status,total_yuan,remark");
            StringBuilder marks = new StringBuilder("?,?,?,?");
            List<Object> args = new ArrayList<>();
            args.add(username);
            args.add(initialStatus);
            args.add(BigDecimal.valueOf(finalTotal).setScale(2, RoundingMode.HALF_UP));
            String noteOut = note;
            if (extraCols.isEmpty() && !fTaste.isBlank()) {
                noteOut = (noteOut.isBlank() ? "" : noteOut + "；") + "口味:" + fTaste;
            }
            if (extraCols.isEmpty() && !fAddr.isBlank()) {
                noteOut = (noteOut.isBlank() ? "" : noteOut + "；")
                        + "地址:" + fName + " " + fPhone + " " + fAddr;
            }
            args.add(noteOut);
            for (Map.Entry<String, Object> e : extraCols.entrySet()) {
                cols.append(',').append(e.getKey());
                marks.append(",?");
                args.add(e.getValue());
            }
            cols.append(",created_at,updated_at");
            marks.append(",?,?");
            args.add(now);
            args.add(now);
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO " + ORDER + " (" + cols + ") VALUES (" + marks + ")",
                    Statement.RETURN_GENERATED_KEYS);
            for (int i = 0; i < args.size(); i++) {
                Object v = args.get(i);
                if (v instanceof Timestamp ts) ps.setTimestamp(i + 1, ts);
                else if (v instanceof BigDecimal bd) ps.setBigDecimal(i + 1, bd);
                else ps.setString(i + 1, v == null ? "" : String.valueOf(v));
            }
            return ps;
        }, kh);
        long orderId = kh.getKey() == null ? 0L : kh.getKey().longValue();
        ensureShareToken(orderId);
        if (hasOrderColumn("table_no") || hasOrderColumn("utensil_opt") || hasOrderColumn("pack_opt")) {
            ensurePickupCode(orderId);
        }
        List<long[]> deducted = new ArrayList<>();
        try {
            for (Map<String, Object> line : cart) {
                long itemId = ((Number) line.get("itemId")).longValue();
                int qty = ((Number) line.get("qty")).intValue();
                Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
                Map<String, Object> extra = extraForItem(lineExtras, itemId);
                Map<String, Object> priced = WeighSaleStore.priceLine(item, qty, extra);
                int lineQty = ((Number) priced.get("qty")).intValue();
                insertOrderLine(
                        orderId,
                        itemId,
                        ArchiveStore.lineTitleWithSpec(item),
                        ((Number) priced.get("unit")).doubleValue(),
                        lineQty,
                        extra);
                WeighSaleStore.saveWeight(orderId, itemId, priced.get("weight"));
                if (useQuota) {
                    ArchiveStore.adjustStock(itemId, -lineQty);
                    deducted.add(new long[] {itemId, lineQty});
                }
                ConsignStore.markSold(itemId);
            }
            if (LoyaltyStore.anyEnabled()) {
                // 渠道+密码仅为收银台形态校验（长度≥4，不验登录密码哈希）；有钱包时一律 settle 扣余额
                Map<String, Object> snap = LoyaltyStore.settleOnPlace(username, subtotal, orderId, coupon);
                applyLoyaltySnapshot(orderId, snap);
                if (!coupon.isBlank() && LoyaltyStore.isCouponEnabled()) {
                    CouponStore.markUsed(username, coupon, orderId);
                }
            }
            if (campaignId != null && campaignId > 0) {
                GroupBuyStore.join(username, orderId, campaignId);
            }
            if (BlindBoxStore.enabled()) {
                for (Map<String, Object> line : cart) {
                    long boxId = ((Number) line.get("itemId")).longValue();
                    int boxQty = ((Number) line.get("qty")).intValue();
                    if (boxQty <= 0 || !BlindBoxStore.isBox(boxId)) continue;
                    List<Map<String, Object>> prizes = BlindBoxStore.drawAll(username, orderId, boxId, boxQty);
                    if (useQuota) {
                        for (Map<String, Object> prize : prizes) {
                            long prizeId = ((Number) prize.get("itemId")).longValue();
                            ArchiveStore.adjustStock(prizeId, -1);
                            deducted.add(new long[] {prizeId, 1});
                        }
                    }
                }
            }
        } catch (RuntimeException ex) {
            for (int i = deducted.size() - 1; i >= 0; i--) {
                long[] d = deducted.get(i);
                try {
                    ArchiveStore.adjustStock(d[0], (int) d[1]);
                } catch (Exception ignored) {
                }
            }
            try {
                if (LoyaltyStore.anyEnabled()) {
                    Map<String, Object> m = getOrder(orderId);
                    if (m != null) {
                        double paid = 0;
                        Object pb = m.get("payBalanceYuan");
                        if (pb instanceof Number n) paid = n.doubleValue();
                        if (paid > 0) {
                            LoyaltyStore.refundOrderPay(username, orderId, paid);
                        }
                    }
                }
            } catch (Exception ignored) {
            }
            try {
                db().update("DELETE FROM " + LINE + " WHERE order_id=?", orderId);
                db().update("DELETE FROM " + ORDER + " WHERE id=?", orderId);
            } catch (Exception ignored) {
            }
            throw ex;
        }
        clearPlacedCart(username, cart);
        try {
            MessageStore.notifyAdmins(
                    "新订单待确认",
                    UserStore.displayName(username) + " 下单 ¥" + round2(subtotal) + "，请确认处理。",
                    "order",
                    orderId);
        } catch (Exception ignored) {
        }
        if (DigitalGoodsStore.enabled()) {
            DigitalGoodsStore.deliverOnPay(orderId);
        }
        return getOrder(orderId);
    }

    /** 预约域联动：单明细订单 */
    public static Map<String, Object> placeSimple(
            String username, long itemId, String title, double priceYuan, int qty, String remark) {
        return placeSimple(username, itemId, title, priceYuan, qty, remark, null);
    }

    public static Map<String, Object> placeSimple(
            String username, long itemId, String title, double priceYuan, int qty, String remark, Long reservationId) {
        if (!enabled) return null;
        if (qty < 1) qty = 1;
        if (reservationId != null && reservationId > 0 && !hasOrderColumn("reservation_id")) {
            throw new IllegalStateException("系统未配置预约订单联动字段，无法下单");
        }
        KeyHolder kh = new GeneratedKeyHolder();
        int q = qty;
        boolean withResv = reservationId != null && reservationId > 0;
        db().update(con -> {
            PreparedStatement ps;
            Timestamp now = Timestamp.valueOf(LocalDateTime.now());
            double total = round2(priceYuan * q);
            if (withResv) {
                ps = con.prepareStatement(
                        "INSERT INTO " + ORDER
                                + " (username,status,total_yuan,remark,reservation_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, username);
                ps.setString(2, "pending");
                ps.setBigDecimal(3, BigDecimal.valueOf(total).setScale(2, RoundingMode.HALF_UP));
                ps.setString(4, remark == null ? "" : remark);
                ps.setLong(5, reservationId);
                ps.setTimestamp(6, now);
                ps.setTimestamp(7, now);
            } else {
                ps = con.prepareStatement(
                        "INSERT INTO " + ORDER + " (username,status,total_yuan,remark,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                        Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, username);
                ps.setString(2, "pending");
                ps.setBigDecimal(3, BigDecimal.valueOf(total).setScale(2, RoundingMode.HALF_UP));
                ps.setString(4, remark == null ? "" : remark);
                ps.setTimestamp(5, now);
                ps.setTimestamp(6, now);
            }
            return ps;
        }, kh);
        long orderId = kh.getKey() == null ? 0L : kh.getKey().longValue();
        ensureShareToken(orderId);
        db().update(
                "INSERT INTO " + LINE + " (order_id,item_id,title,price_yuan,qty) VALUES (?,?,?,?,?)",
                orderId, itemId, title == null ? "" : title, priceYuan, q);
        double total = round2(priceYuan * q);
        if (LoyaltyStore.anyEnabled()) {
            try {
                ensureLoyaltyColumns();
                Map<String, Object> snap = LoyaltyStore.settleOnPlace(username, total, orderId, null);
                applyLoyaltySnapshot(orderId, snap);
            } catch (RuntimeException ex) {
                try {
                    db().update("DELETE FROM " + LINE + " WHERE order_id=?", orderId);
                    db().update("DELETE FROM " + ORDER + " WHERE id=?", orderId);
                } catch (Exception ignored) {
                }
                throw ex;
            }
        }
        if (RentalBondStore.enabled()) {
            RentalBondStore.onOrderPlaced(orderId, itemId, total);
        }
        if (DigitalGoodsStore.enabled()) {
            DigitalGoodsStore.deliverOnPay(orderId);
        }
        return getOrder(orderId);
    }

    /** 影院选座等：订单号派生取票码（列存在且为空时写入）。 */
    public static void ensurePickupCode(long orderId) {
        if (!enabled || orderId <= 0 || !hasOrderColumn("pickup_code")) return;
        try {
            String cur = db().queryForObject(
                    "SELECT pickup_code FROM " + ORDER + " WHERE id=?", String.class, orderId);
            if (cur != null && !cur.isBlank()) return;
        } catch (Exception ignored) {
            return;
        }
        String code = String.format("%04d", (int) (orderId % 10000));
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        db().update(
                "UPDATE " + ORDER + " SET pickup_code=?, updated_at=? WHERE id=?",
                code, now, orderId);
    }

    public static void markNoticeAgreed(long orderId) {
        if (!enabled || orderId <= 0 || !hasOrderColumn("notice_agreed")) return;
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        try {
            db().update(
                    "UPDATE " + ORDER + " SET notice_agreed=1, updated_at=? WHERE id=?",
                    now, orderId);
        } catch (Exception ignored) {
        }
    }

    /**
     * 选座等「先下单再履约」失败时关单：退余额、释放券，不回补库存（库存由调用方按是否已扣处理）。
     * 与 advance(cancel) 不同，避免尚未扣库存时误 +stock。
     */
    public static void abortPendingPurchase(long orderId) {
        if (!enabled || orderId <= 0) return;
        Map<String, Object> m = getOrder(orderId);
        if (m == null) return;
        String st = String.valueOf(m.get("status"));
        if (!"pending".equals(st) && !"confirmed".equals(st)) return;
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        db().update(
                "UPDATE " + ORDER + " SET status='cancelled', updated_at=? WHERE id=? AND status IN ('pending','confirmed')",
                now, orderId);
        restoreSnackStockForOrder(orderId);
        if (LoyaltyStore.anyEnabled()) {
            double paid = toDouble(m.get("payBalanceYuan"));
            String uname = String.valueOf(m.get("username"));
            if (paid > 1e-9) {
                LoyaltyStore.refundOrderPay(uname, orderId, paid);
            }
            if (LoyaltyStore.isCouponEnabled()) {
                CouponStore.releaseByOrder(orderId);
            }
        }
    }

    /**
     * 影院卖品加购：附加 order_line（line_kind=snack）并扣卖品库存、累加订单金额。
     * snacks 项：{id|snackId, qty}；空列表为 no-op。
     */
    public static void attachCinemaSnacks(long orderId, List<Map<String, Object>> snacks) {
        if (!enabled || orderId <= 0 || snacks == null || snacks.isEmpty()) return;
        if (!hasLineColumn("line_kind")) {
            throw new IllegalStateException("系统未配置卖品明细字段，无法加购");
        }
        if (!SeatStore.snackReady()) {
            throw new IllegalStateException("卖品功能暂不可用");
        }
        List<long[]> deducted = new ArrayList<>();
        double add = 0;
        try {
            for (Map<String, Object> sel : snacks) {
                if (sel == null) continue;
                long snackId = 0;
                Object sid = sel.get("id");
                if (sid == null) sid = sel.get("snackId");
                if (sid instanceof Number n) snackId = n.longValue();
                else if (sid != null && !String.valueOf(sid).isBlank()) {
                    snackId = Long.parseLong(String.valueOf(sid).trim());
                }
                int qty = 0;
                Object q = sel.get("qty");
                if (q instanceof Number n) qty = n.intValue();
                else if (q != null && !String.valueOf(q).isBlank()) {
                    qty = Integer.parseInt(String.valueOf(q).trim());
                }
                if (snackId <= 0 || qty < 1) continue;
                if (qty > 6) throw new IllegalArgumentException("单种卖品最多加购 6 份");
                Map<String, Object> snack = SeatStore.getSnack(snackId);
                if (snack == null || !"on".equals(String.valueOf(snack.get("status")))) {
                    throw new IllegalStateException("所选卖品不可用");
                }
                int stock = snack.get("stock") instanceof Number sn ? sn.intValue() : 0;
                if (stock < qty) {
                    throw new IllegalStateException("卖品暂时无货");
                }
                double price = toDouble(snack.get("priceYuan"));
                String title = "卖品·" + String.valueOf(snack.get("title"));
                SeatStore.adjustSnackStock(snackId, -qty);
                deducted.add(new long[]{snackId, qty});
                db().update(
                        "INSERT INTO " + LINE
                                + " (order_id,item_id,title,price_yuan,qty,line_kind) VALUES (?,?,?,?,?,'snack')",
                        orderId, snackId, title, price, qty);
                add = round2(add + price * qty);
            }
            if (add > 1e-9) {
                Timestamp now = Timestamp.valueOf(LocalDateTime.now());
                db().update(
                        "UPDATE " + ORDER + " SET total_yuan=total_yuan+?, updated_at=? WHERE id=?",
                        add, now, orderId);
            }
        } catch (RuntimeException ex) {
            for (long[] d : deducted) {
                try {
                    SeatStore.adjustSnackStock(d[0], (int) d[1]);
                } catch (Exception ignored) {
                }
            }
            throw ex;
        }
    }

    /** 取消/失败回滚：按 snack 明细回补卖品库存（不碰场次库存）。 */
    public static void restoreSnackStockForOrder(long orderId) {
        if (!enabled || orderId <= 0 || !hasLineColumn("line_kind")) return;
        if (!SeatStore.snackReady()) return;
        for (Map<String, Object> line : listLines(orderId)) {
            if (!"snack".equals(String.valueOf(line.get("lineKind")))) continue;
            long itemId = line.get("itemId") instanceof Number n ? n.longValue() : 0L;
            int qty = line.get("qty") instanceof Number n ? n.intValue() : 0;
            if (itemId > 0 && qty > 0) {
                try {
                    SeatStore.adjustSnackStock(itemId, qty);
                } catch (Exception ignored) {
                }
            }
        }
    }

    public static Map<String, Object> getOrder(long id) {
        requireEnabled();
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + ORDER + " WHERE id=?", (rs, i) -> mapOrder(rs), id);
        if (list.isEmpty()) return null;
        Map<String, Object> m = list.get(0);
        m.put("lines", listLines(id));
        return m;
    }

    private static List<Map<String, Object>> listLines(long orderId) {
        return db().query(
                "SELECT * FROM " + LINE + " WHERE order_id=? ORDER BY id",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("orderId", rs.getLong("order_id"));
                    long itemId = rs.getLong("item_id");
                    m.put("itemId", itemId);
                    m.put("title", rs.getString("title"));
                    m.put("priceYuan", rs.getDouble("price_yuan"));
                    m.put("qty", rs.getInt("qty"));
                    m.put("lineYuan", round2(rs.getDouble("price_yuan") * rs.getInt("qty")));
                    m.put("lineKind", safeStr(rs, "line_kind"));
                    m.put("customText", safeStr(rs, "custom_text"));
                    m.put("specChoice", safeStr(rs, "spec_choice"));
                    m.put("attachUrl", safeStr(rs, "attach_url"));
                    m.put("drawTitle", safeStr(rs, "draw_title"));
                    if (!String.valueOf(m.get("drawTitle")).isBlank() && BlindBoxStore.enabled()) {
                        m.put("pityText", BlindBoxStore.pityText(orderId, itemId));
                    }
                    if (ArchiveStore.shopMarketplaceEnabled()
                            && !"snack".equals(String.valueOf(m.get("lineKind")))) {
                        try {
                            Map<String, Object> item = ArchiveStore.getItem(itemId);
                            if (item != null && item.get("shopName") != null) {
                                m.put("shopName", item.get("shopName"));
                            }
                        } catch (Exception ignored) {
                        }
                    }
                    return m;
                },
                orderId);
    }

    public static Map<String, Object> pageOrders(String username, String status, int page, int size) {
        requireEnabled();
        if (GroupBuyStore.enabled()) GroupBuyStore.sweep();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> args = new ArrayList<>();
        if (username != null && !username.isBlank()) {
            where.append(" AND username=?");
            args.add(username);
        }
        if (status != null && !status.isBlank()) {
            where.append(" AND status=?");
            args.add(status);
        }
        Integer total = db().queryForObject("SELECT COUNT(*) FROM " + ORDER + where, Integer.class, args.toArray());
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + ORDER + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = mapOrder(rs);
                    m.put("lines", listLines(rs.getLong("id")));
                    return m;
                },
                args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static Map<String, Object> pageOrdersOwnedByMerchant(
            String ownerUsername, String status, int page, int size) {
        requireEnabled();
        String owner = ownerUsername == null ? "" : ownerUsername.trim();
        if (owner.isBlank()) throw new IllegalArgumentException("未登录");
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String item = ArchiveStore.itemTable();
        String ownClause = " EXISTS (SELECT 1 FROM " + LINE + " l JOIN " + item
                + " p ON p.id=l.item_id WHERE l.order_id=" + ORDER + ".id AND p.owner_username=?)";
        StringBuilder where = new StringBuilder(" WHERE ").append(ownClause);
        List<Object> args = new ArrayList<>();
        args.add(owner);
        if (status != null && !status.isBlank()) {
            where.append(" AND status=?");
            args.add(status);
        }
        Integer total = db().queryForObject("SELECT COUNT(*) FROM " + ORDER + where, Integer.class, args.toArray());
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + ORDER + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> m = mapOrder(rs);
                    m.put("lines", listLines(rs.getLong("id")));
                    return m;
                },
                args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", total == null ? 0 : total);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static boolean merchantOwnsOrder(String ownerUsername, long orderId) {
        requireEnabled();
        String owner = ownerUsername == null ? "" : ownerUsername.trim();
        if (owner.isBlank() || orderId <= 0) return false;
        String item = ArchiveStore.itemTable();
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM " + LINE + " l JOIN " + item
                        + " p ON p.id=l.item_id WHERE l.order_id=? AND p.owner_username=?",
                Integer.class, orderId, owner);
        return n != null && n > 0;
    }

    /** 宾馆等：预约办结时把关联订单一并完成 */
    public static void completeByReservation(long reservationId) {
        advanceByReservation(reservationId, "complete");
    }

    /** 取消预约时关掉关联订单（回补库存走 advance cancel） */
    public static void cancelByReservation(long reservationId) {
        advanceByReservation(reservationId, "cancel");
    }

    private static void advanceByReservation(long reservationId, String action) {
        if (!enabled || reservationId <= 0 || !hasOrderColumn("reservation_id")) return;
        List<Long> ids = db().query(
                "SELECT id FROM " + ORDER + " WHERE reservation_id=? AND status IN ('pending','confirmed','shipped')",
                (rs, i) -> rs.getLong("id"),
                reservationId);
        for (Long id : ids) {
            if (id == null) continue;
            // cancel 仅 pending/confirmed；shipped 走 complete 更稳妥
            String act = action;
            if ("cancel".equals(action)) {
                Map<String, Object> m = getOrder(id);
                if (m != null && "shipped".equals(String.valueOf(m.get("status")))) {
                    act = "complete";
                }
            }
            // 办结关联订单：须先确认再履约，再完成（与前台按钮规则一致）
            if ("complete".equals(act)) {
                Map<String, Object> m = getOrder(id);
                String st = m == null ? "" : String.valueOf(m.get("status"));
                if ("pending".equals(st)) {
                    advance(id, "confirm", null);
                    advance(id, "ship", null);
                } else if ("confirmed".equals(st)) {
                    advance(id, "ship", null);
                }
            }
            advance(id, act, null);
        }
    }

    public static Map<String, Object> payOrder(long orderId, String username, String payChannel, String payPassword) {
        requireEnabled();
        if (!ArchiveStore.shopMarketplaceEnabled()) {
            throw new IllegalStateException("当前未开启在线支付");
        }
        ensurePayChannelColumn();
        Map<String, Object> m = getOrder(orderId);
        if (m == null) throw new IllegalArgumentException("订单不存在");
        if (!String.valueOf(m.get("username")).equals(username)) {
            throw new IllegalStateException("无权支付该订单");
        }
        if (!"pending".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("订单不是待付款状态");
        }
        String channel = payChannel == null ? "" : payChannel.trim().toLowerCase(Locale.ROOT);
        if (!"alipay".equals(channel) && !"wechat".equals(channel)) {
            throw new IllegalArgumentException("请选择支付宝或微信支付");
        }
        String pw = payPassword == null ? "" : payPassword.trim();
        if (pw.length() < 4) {
            throw new IllegalArgumentException("请输入支付密码（至少 4 位）");
        }
        if (LoyaltyStore.isWalletEnabled()) {
            ensureLoyaltyColumns();
            double already = toDouble(m.get("payBalanceYuan"));
            if (already <= 1e-9) {
                double pay = round2(toDouble(m.get("totalYuan")));
                LoyaltyStore.captureOrderPay(username, pay, orderId);
                if (hasOrderColumn("pay_balance_yuan")) {
                    db().update(
                            "UPDATE " + ORDER + " SET pay_balance_yuan=?, updated_at=? WHERE id=?",
                            BigDecimal.valueOf(pay).setScale(2, RoundingMode.HALF_UP),
                            Timestamp.valueOf(LocalDateTime.now()),
                            orderId);
                }
            }
        }
        db().update(
                "UPDATE " + ORDER + " SET status='confirmed', pay_channel=?, updated_at=? WHERE id=? AND status='pending'",
                channel,
                Timestamp.valueOf(LocalDateTime.now()),
                orderId);
        return getOrder(orderId);
    }

    public static Map<String, Object> advance(long orderId, String action) {
        return advance(orderId, action, null);
    }

    /** 超时关单：取消超时仍 pending 的订单（回补库存/退账户余额）。 */
    public static int cancelTimedOutPending(int minutes) {
        if (!enabled || minutes <= 0) return 0;
        List<Long> ids;
        try {
            ids = db().query(
                    "SELECT id FROM " + ORDER
                            + " WHERE status='pending' AND created_at < DATE_SUB(NOW(), INTERVAL ? MINUTE)",
                    (rs, i) -> rs.getLong(1),
                    minutes);
        } catch (Exception e) {
            return 0;
        }
        if (ids == null || ids.isEmpty()) return 0;
        int n = 0;
        for (Long id : ids) {
            if (id == null) continue;
            try {
                advance(id, "cancel", null);
                n++;
            } catch (Exception ignored) {
            }
        }
        return n;
    }

    /** 确认收货超时：发货后超时未办结的订单自动 complete。 */
    public static int completeTimedOutUnreceived(int minutes) {
        if (!enabled || minutes <= 0) return 0;
        if (!hasOrderColumn("shipped_at")) return 0;
        List<Long> ids;
        try {
            ids = db().query(
                    "SELECT id FROM " + ORDER
                            + " WHERE status IN ('shipped','in_transit','signed')"
                            + " AND shipped_at IS NOT NULL"
                            + " AND shipped_at < DATE_SUB(NOW(), INTERVAL ? MINUTE)",
                    (rs, i) -> rs.getLong(1),
                    minutes);
        } catch (Exception e) {
            return 0;
        }
        if (ids == null || ids.isEmpty()) return 0;
        int n = 0;
        for (Long id : ids) {
            if (id == null) continue;
            try {
                advance(id, "complete", null);
                n++;
            } catch (Exception ignored) {
            }
        }
        return n;
    }

    /** 发货前改收货信息：仅 pending / confirmed。 */
    public static Map<String, Object> updateShippingAddress(
            long orderId, String username, boolean admin,
            String receiverName, String receiverPhone, String addressLine) {
        requireEnabled();
        Map<String, Object> m = getOrder(orderId);
        if (m == null) throw new IllegalArgumentException("订单不存在");
        if (!admin && !String.valueOf(m.get("username")).equals(username)) {
            throw new IllegalStateException("无权修改该订单");
        }
        String st = String.valueOf(m.get("status"));
        if (!"pending".equals(st) && !"confirmed".equals(st)) {
            throw new IllegalStateException("已发货后不可修改地址");
        }
        String name = receiverName == null ? "" : receiverName.trim();
        String phone = receiverPhone == null ? "" : receiverPhone.trim();
        String addr = addressLine == null ? "" : addressLine.trim();
        if (name.isBlank() && phone.isBlank() && addr.isBlank()) {
            throw new IllegalArgumentException("请填写收货人、电话或地址");
        }
        if (!name.isBlank() && !hasOrderColumn("receiver_name")) {
            throw new IllegalStateException("系统未配置收货人字段");
        }
        if (!phone.isBlank() && !hasOrderColumn("receiver_phone")) {
            throw new IllegalStateException("系统未配置收货电话字段");
        }
        if (!addr.isBlank() && !hasOrderColumn("address_line")) {
            throw new IllegalStateException("系统未配置收货地址字段");
        }
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        StringBuilder sql = new StringBuilder("UPDATE " + ORDER + " SET updated_at=?");
        List<Object> args = new ArrayList<>();
        args.add(now);
        if (!name.isBlank() && hasOrderColumn("receiver_name")) {
            sql.append(", receiver_name=?");
            args.add(name);
        }
        if (!phone.isBlank() && hasOrderColumn("receiver_phone")) {
            sql.append(", receiver_phone=?");
            args.add(phone);
        }
        if (!addr.isBlank() && hasOrderColumn("address_line")) {
            sql.append(", address_line=?");
            args.add(addr);
        }
        sql.append(" WHERE id=?");
        args.add(orderId);
        db().update(sql.toString(), args.toArray());
        return getOrder(orderId);
    }

    public static Map<String, Object> advance(long orderId, String action, Map<String, Object> opts) {
        requireEnabled();
        Map<String, Object> m = getOrder(orderId);
        if (m == null) throw new IllegalArgumentException("订单不存在");
        String st = String.valueOf(m.get("status"));
        String act = action == null ? "" : action.trim().toLowerCase(Locale.ROOT);
        String next;
        if ("confirm".equals(act) && "pending".equals(st)) next = "confirmed";
        // 发货/出餐须先确认，禁止 pending 跳步
        else if ("ship".equals(act) && "confirmed".equals(st)) next = "shipped";
        else if ("transit".equals(act) && "shipped".equals(st) && ArchiveStore.shopMarketplaceEnabled()) {
            next = "in_transit";
        }
        else if ("sign".equals(act)
                && ("shipped".equals(st) || "in_transit".equals(st))
                && ArchiveStore.shopMarketplaceEnabled()) {
            next = "signed";
        }
        // 完成：单店 shipped→completed；多店 signed→completed（亦可商家从运输中办结）
        else if ("complete".equals(act)) {
            boolean mp = ArchiveStore.shopMarketplaceEnabled();
            boolean ok = mp
                    ? ("signed".equals(st) || "in_transit".equals(st) || "shipped".equals(st))
                    : "shipped".equals(st);
            if (!ok) throw new IllegalStateException("当前状态不可执行：" + act);
            if ("pending".equals(String.valueOf(m.getOrDefault("refundStatus", "")))) {
                throw new IllegalStateException("售后处理中，不可完成订单");
            }
            next = "completed";
        }
        else if ("cancel".equals(act) && ("pending".equals(st) || "confirmed".equals(st))) next = "cancelled";
        else if ("ship".equals(act) && "grouping".equals(st)) throw new IllegalStateException("未成团不能发货");
        else throw new IllegalStateException("当前状态不可执行：" + act);
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        String tracking = "";
        String pickup = "";
        if ("shipped".equals(next)) {
            tracking = opts == null ? "" : String.valueOf(opts.getOrDefault("trackingNo", "")).trim();
            pickup = opts == null ? "" : String.valueOf(opts.getOrDefault("pickupCode", "")).trim();
            if (!tracking.isBlank() && !hasOrderColumn("tracking_no")) {
                throw new IllegalStateException("系统未配置物流单号字段，无法保存");
            }
            if (!pickup.isBlank() && !hasOrderColumn("pickup_code")) {
                throw new IllegalStateException("系统未配置取货码字段，无法保存");
            }
        }
        if ("shipped".equals(next)
                && (hasOrderColumn("tracking_no")
                || hasOrderColumn("pickup_code")
                || hasOrderColumn("shipped_at"))) {
            if (pickup.isBlank() && hasOrderColumn("pickup_code")) {
                String dtype = String.valueOf(m.getOrDefault("deliveryType", ""));
                if (dtype.contains("自取") || dtype.contains("堂食") || dtype.contains("自提")) {
                    pickup = String.format("%04d", (int) (orderId % 10000));
                }
            }
            StringBuilder sql = new StringBuilder("UPDATE " + ORDER + " SET status=?");
            List<Object> args = new ArrayList<>();
            args.add(next);
            if (hasOrderColumn("tracking_no")) {
                sql.append(", tracking_no=?");
                args.add(tracking);
            }
            if (hasOrderColumn("pickup_code")) {
                sql.append(", pickup_code=?");
                args.add(pickup);
            }
            if (hasOrderColumn("shipped_at")) {
                sql.append(", shipped_at=?");
                args.add(now);
            }
            if (hasOrderColumn("partial_ship")) {
                boolean partial = opts != null && Boolean.TRUE.equals(opts.get("partialShip"));
                if (!partial) {
                    Object raw = opts == null ? null : opts.get("partialShip");
                    String s = raw == null ? "" : String.valueOf(raw).trim();
                    partial = "1".equals(s) || "true".equalsIgnoreCase(s);
                }
                sql.append(", partial_ship=?");
                args.add(partial ? 1 : 0);
            }
            sql.append(", updated_at=? WHERE id=?");
            args.add(now);
            args.add(orderId);
            db().update(sql.toString(), args.toArray());
            if ("shipped".equals(next)) ensurePickupCode(orderId);
        } else {
            db().update(
                    "UPDATE " + ORDER + " SET status=?, updated_at=? WHERE id=?",
                    next, now, orderId);
        }
        if (("signed".equals(next) || "completed".equals(next)) && hasOrderColumn("completed_at")) {
            Object already = m.get("completedAt");
            if (already == null || String.valueOf(already).isBlank() || "null".equals(String.valueOf(already))) {
                try {
                    db().update(
                            "UPDATE " + ORDER + " SET completed_at=? WHERE id=? AND (completed_at IS NULL)",
                            now, orderId);
                } catch (Exception ignored) {
                }
            }
        }
        if ("cancelled".equals(next) && useQuota) {
            for (Map<String, Object> line : listLines(orderId)) {
                if ("snack".equals(String.valueOf(line.get("lineKind")))) continue;
                ArchiveStore.adjustStock(
                        ((Number) line.get("itemId")).longValue(),
                        ((Number) line.get("qty")).intValue());
            }
        }
        if ("cancelled".equals(next)) {
            restoreSnackStockForOrder(orderId);
            SeatStore.releaseByOrder(orderId);
            ConsignStore.release(orderId, listLines(orderId));
        }
        if ("cancelled".equals(next) && LoyaltyStore.anyEnabled()) {
            double paid = toDouble(m.get("payBalanceYuan"));
            if (paid <= 0) paid = 0;
            String uname = String.valueOf(m.get("username"));
            if (paid > 0) {
                LoyaltyStore.refundOrderPay(uname, orderId, paid);
            }
            if (LoyaltyStore.isCouponEnabled()) {
                CouponStore.releaseByOrder(orderId);
            }
        }
        if ("shipped".equals(next) && RentalBondStore.enabled()) {
            RentalBondStore.onShipped(orderId);
        }
        if ("completed".equals(next) && RentalBondStore.enabled()) {
            RentalBondStore.onCompleted(orderId);
        }
        if ("completed".equals(next) && LoyaltyStore.anyEnabled()) {
            String uname = String.valueOf(m.get("username"));
            double pay = toDouble(m.get("payBalanceYuan"));
            if (pay <= 0) pay = toDouble(m.get("totalYuan"));
            LoyaltyStore.onOrderCompleted(uname, orderId, pay);
        }
        if ("completed".equals(next)) {
            ConsignStore.settle(orderId, listLines(orderId));
        }
        if ("completed".equals(next) && OrderReviewStore.enabled()) {
            try {
                MessageStore.send(
                        String.valueOf(m.get("username")),
                        "邀请评价",
                        "您的订单已完成，欢迎前往「我的订单」写下评价。",
                        "order",
                        orderId);
            } catch (Exception ignored) {
            }
        }
        return getOrder(orderId);
    }

    public static Map<String, Object> dashboard() {
        return dashboard(null);
    }

    /** @param ownerUsername 多店商家：只统计本店订单；超管/单店传 null */
    public static Map<String, Object> dashboard(String ownerUsername) {
        if (!enabled) return Map.of();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("pendingOrders", countStatus("pending", ownerUsername));
        m.put("confirmedOrders", countStatus("confirmed", ownerUsername));
        m.put("shippedOrders", countStatus("shipped", ownerUsername));
        m.put("completedOrders", countStatus("completed", ownerUsername));
        m.put("salesTotalYuan", sumCompletedSales(ownerUsername));
        if (ArchiveStore.shopMarketplaceEnabled()) {
            m.put("inTransitOrders", countStatus("in_transit", ownerUsername));
            m.put("signedOrders", countStatus("signed", ownerUsername));
        }
        return m;
    }

    public static Map<String, Object> chartStats() {
        return chartStats(null);
    }

    public static Map<String, Object> chartStats(String ownerUsername) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("statusSeries", List.of());
        out.put("trendSeries", List.of());
        out.put("monthSeries", List.of());
        out.put("hotItemSeries", List.of());
        out.put("salesDailySeries", List.of());
        out.put("refundReasonSeries", List.of());
        if (!enabled) return out;
        String owner = ownerUsername == null ? "" : ownerUsername.trim();
        boolean byOwner = !owner.isBlank() && ArchiveStore.hasOwnerUsername();
        try {
            if (!byOwner) {
                List<Map<String, Object>> status = db().query(
                        "SELECT status AS name, COUNT(*) AS value FROM " + ORDER + " GROUP BY status",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("name", rs.getString("name"));
                            row.put("value", rs.getLong("value"));
                            return row;
                        });
                out.put("statusSeries", status);
                List<Map<String, Object>> trend = db().query(
                        "SELECT DATE_FORMAT(created_at,'%Y-%m-%d') AS day, COUNT(*) AS value FROM " + ORDER
                                + " WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)"
                                + " GROUP BY DATE_FORMAT(created_at,'%Y-%m-%d') ORDER BY day",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("day", rs.getString("day"));
                            row.put("value", rs.getLong("value"));
                            return row;
                        });
                out.put("trendSeries", trend);
                out.put("monthSeries", db().query(
                        "SELECT DATE_FORMAT(created_at,'%Y-%m') AS month, COUNT(*) AS value FROM " + ORDER
                                + " WHERE created_at >= DATE_SUB(DATE_FORMAT(CURDATE(), '%Y-%m-01'), INTERVAL 5 MONTH)"
                                + " GROUP BY DATE_FORMAT(created_at,'%Y-%m') ORDER BY month",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("month", rs.getString("month"));
                            row.put("value", rs.getLong("value"));
                            return row;
                        }));
            } else {
                String base = " FROM " + ORDER + " o"
                        + " INNER JOIN " + LINE + " l ON l.order_id=o.id"
                        + " INNER JOIN " + ArchiveStore.itemTable() + " p ON p.id=l.item_id AND p.owner_username=?";
                List<Map<String, Object>> status = db().query(
                        "SELECT o.status AS name, COUNT(DISTINCT o.id) AS value" + base + " GROUP BY o.status",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("name", rs.getString("name"));
                            row.put("value", rs.getLong("value"));
                            return row;
                        },
                        owner);
                out.put("statusSeries", status);
                List<Map<String, Object>> trend = db().query(
                        "SELECT DATE_FORMAT(o.created_at,'%Y-%m-%d') AS day, COUNT(DISTINCT o.id) AS value" + base
                                + " WHERE o.created_at >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)"
                                + " GROUP BY DATE_FORMAT(o.created_at,'%Y-%m-%d') ORDER BY day",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("day", rs.getString("day"));
                            row.put("value", rs.getLong("value"));
                            return row;
                        },
                        owner);
                out.put("trendSeries", trend);
                out.put("monthSeries", db().query(
                        "SELECT DATE_FORMAT(o.created_at,'%Y-%m') AS month, COUNT(DISTINCT o.id) AS value" + base
                                + " WHERE o.created_at >= DATE_SUB(DATE_FORMAT(CURDATE(), '%Y-%m-01'), INTERVAL 5 MONTH)"
                                + " GROUP BY DATE_FORMAT(o.created_at,'%Y-%m') ORDER BY month",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("month", rs.getString("month"));
                            row.put("value", rs.getLong("value"));
                            return row;
                        },
                        owner));
            }
            if (LINE != null && !LINE.isBlank()) {
                if (!byOwner) {
                    List<Map<String, Object>> hot = db().query(
                            "SELECT l.title AS name, SUM(l.qty) AS value FROM " + LINE + " l"
                                    + " INNER JOIN " + ORDER + " o ON o.id=l.order_id AND o.status='completed'"
                                    + " GROUP BY l.title ORDER BY value DESC LIMIT 8",
                            (rs, i) -> {
                                Map<String, Object> row = new LinkedHashMap<>();
                                row.put("name", rs.getString("name"));
                                row.put("value", rs.getLong("value"));
                                return row;
                            });
                    out.put("hotItemSeries", hot);
                } else {
                    List<Map<String, Object>> hot = db().query(
                            "SELECT l.title AS name, SUM(l.qty) AS value FROM " + LINE + " l"
                                    + " INNER JOIN " + ORDER + " o ON o.id=l.order_id AND o.status='completed'"
                                    + " INNER JOIN " + ArchiveStore.itemTable()
                                    + " p ON p.id=l.item_id AND p.owner_username=?"
                                    + " GROUP BY l.title ORDER BY value DESC LIMIT 8",
                            (rs, i) -> {
                                Map<String, Object> row = new LinkedHashMap<>();
                                row.put("name", rs.getString("name"));
                                row.put("value", rs.getLong("value"));
                                return row;
                            },
                            owner);
                    out.put("hotItemSeries", hot);
                }
            }
            if (!byOwner) {
                List<Map<String, Object>> daily = db().query(
                        "SELECT DATE_FORMAT(created_at,'%Y-%m-%d') AS day,"
                                + " COUNT(*) AS orderCount,"
                                + " COALESCE(SUM(CASE WHEN status='completed' THEN total_yuan ELSE 0 END),0) AS amountYuan"
                                + " FROM " + ORDER
                                + " WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 13 DAY)"
                                + " GROUP BY DATE_FORMAT(created_at,'%Y-%m-%d') ORDER BY day",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("day", rs.getString("day"));
                            row.put("orderCount", rs.getLong("orderCount"));
                            row.put("amountYuan", round2(rs.getDouble("amountYuan")));
                            return row;
                        });
                out.put("salesDailySeries", daily);
            } else {
                String dailyBase = " FROM " + ORDER + " o"
                        + " INNER JOIN " + LINE + " l ON l.order_id=o.id"
                        + " INNER JOIN " + ArchiveStore.itemTable() + " p ON p.id=l.item_id AND p.owner_username=?";
                List<Map<String, Object>> daily = db().query(
                        "SELECT DATE_FORMAT(o.created_at,'%Y-%m-%d') AS day,"
                                + " COUNT(DISTINCT o.id) AS orderCount,"
                                + " COALESCE(SUM(DISTINCT CASE WHEN o.status='completed' THEN o.total_yuan ELSE 0 END),0) AS amountYuan"
                                + dailyBase
                                + " WHERE o.created_at >= DATE_SUB(CURDATE(), INTERVAL 13 DAY)"
                                + " GROUP BY DATE_FORMAT(o.created_at,'%Y-%m-%d') ORDER BY day",
                        (rs, i) -> {
                            Map<String, Object> row = new LinkedHashMap<>();
                            row.put("day", rs.getString("day"));
                            row.put("orderCount", rs.getLong("orderCount"));
                            row.put("amountYuan", round2(rs.getDouble("amountYuan")));
                            return row;
                        },
                        owner);
                out.put("salesDailySeries", daily);
            }
            if (hasOrderColumn("refund_reason")) {
                if (!byOwner) {
                    List<Map<String, Object>> reasons = db().query(
                            "SELECT refund_reason AS name, COUNT(*) AS value FROM " + ORDER
                                    + " WHERE refund_reason IS NOT NULL AND TRIM(refund_reason)<>''"
                                    + " AND refund_status IN ('pending','approved','rejected')"
                                    + " GROUP BY refund_reason ORDER BY value DESC LIMIT 12",
                            (rs, i) -> {
                                Map<String, Object> row = new LinkedHashMap<>();
                                row.put("name", rs.getString("name"));
                                row.put("value", rs.getLong("value"));
                                return row;
                            });
                    out.put("refundReasonSeries", reasons);
                } else {
                    String reasonBase = " FROM " + ORDER + " o"
                            + " INNER JOIN " + LINE + " l ON l.order_id=o.id"
                            + " INNER JOIN " + ArchiveStore.itemTable() + " p ON p.id=l.item_id AND p.owner_username=?";
                    List<Map<String, Object>> reasons = db().query(
                            "SELECT o.refund_reason AS name, COUNT(DISTINCT o.id) AS value" + reasonBase
                                    + " WHERE o.refund_reason IS NOT NULL AND TRIM(o.refund_reason)<>''"
                                    + " AND o.refund_status IN ('pending','approved','rejected')"
                                    + " GROUP BY o.refund_reason ORDER BY value DESC LIMIT 12",
                            (rs, i) -> {
                                Map<String, Object> row = new LinkedHashMap<>();
                                row.put("name", rs.getString("name"));
                                row.put("value", rs.getLong("value"));
                                return row;
                            },
                            owner);
                    out.put("refundReasonSeries", reasons);
                }
            }
        } catch (Exception ignored) {
        }
        return out;
    }

    private static long countStatus(String st, String ownerUsername) {
        String owner = ownerUsername == null ? "" : ownerUsername.trim();
        if (owner.isBlank() || !ArchiveStore.hasOwnerUsername()) {
            Long n = db().queryForObject("SELECT COUNT(*) FROM " + ORDER + " WHERE status=?", Long.class, st);
            return n == null ? 0 : n;
        }
        String sql = "SELECT COUNT(*) FROM " + ORDER + " o WHERE o.status=?"
                + " AND EXISTS (SELECT 1 FROM " + LINE + " l JOIN " + ArchiveStore.itemTable()
                + " p ON p.id=l.item_id WHERE l.order_id=o.id AND p.owner_username=?)";
        Long n = db().queryForObject(sql, Long.class, st, owner);
        return n == null ? 0 : n;
    }

    private static double sumCompletedSales(String ownerUsername) {
        try {
            String owner = ownerUsername == null ? "" : ownerUsername.trim();
            if (owner.isBlank() || !ArchiveStore.hasOwnerUsername()) {
                Double n = db().queryForObject(
                        "SELECT COALESCE(SUM(total_yuan),0) FROM " + ORDER + " WHERE status='completed'",
                        Double.class);
                return n == null ? 0 : round2(n);
            }
            Double n = db().queryForObject(
                    "SELECT COALESCE(SUM(x.total_yuan),0) FROM ("
                            + "SELECT DISTINCT o.id, o.total_yuan FROM " + ORDER + " o"
                            + " INNER JOIN " + LINE + " l ON l.order_id=o.id"
                            + " INNER JOIN " + ArchiveStore.itemTable() + " p ON p.id=l.item_id AND p.owner_username=?"
                            + " WHERE o.status='completed'"
                            + ") x",
                    Double.class,
                    owner);
            return n == null ? 0 : round2(n);
        } catch (Exception e) {
            return 0;
        }
    }

    private static Map<String, Object> mapOrder(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("status", rs.getString("status"));
        m.put("totalYuan", rs.getDouble("total_yuan"));
        m.put("remark", rs.getString("remark"));
        m.put("receiverName", safeStr(rs, "receiver_name"));
        m.put("receiverPhone", safeStr(rs, "receiver_phone"));
        m.put("addressLine", safeStr(rs, "address_line"));
        m.put("deliveryType", safeStr(rs, "delivery_type"));
        m.put("tasteNote", safeStr(rs, "taste_note"));
        m.put("trackingNo", safeStr(rs, "tracking_no"));
        m.put("pickupCode", safeStr(rs, "pickup_code"));
        m.put("tableNo", safeStr(rs, "table_no"));
        m.put("utensilOpt", safeStr(rs, "utensil_opt"));
        m.put("packOpt", safeStr(rs, "pack_opt"));
        m.put("packagingFeeYuan", safeDouble(rs, "packaging_fee_yuan"));
        m.put("deliveryFeeYuan", safeDouble(rs, "delivery_fee_yuan"));
        m.put("etaText", safeStr(rs, "eta_text"));
        m.put("mergeCode", safeStr(rs, "merge_code"));
        m.put("riderUsername", safeStr(rs, "rider_username"));
        m.put("riderClaimedAt", fmt(safeTs(rs, "rider_claimed_at")));
        m.put("noticeAgreed", (int) safeLong(rs, "notice_agreed") > 0);
        m.put("shippedAt", fmt(safeTs(rs, "shipped_at")));
        long rid = safeLong(rs, "reservation_id");
        if (rid > 0) m.put("reservationId", rid);
        m.put("discountYuan", safeDouble(rs, "discount_yuan"));
        m.put("payBalanceYuan", safeDouble(rs, "pay_balance_yuan"));
        m.put("pointsEarned", (int) safeLong(rs, "points_earned"));
        m.put("couponCode", safeStr(rs, "coupon_code"));
        try {
            if (GroupBuyStore.enabled()) {
                Map<String, Object> gp = GroupBuyStore.progressForOrder(rs.getLong("id"));
                if (gp != null) m.put("groupBuy", gp);
            }
        } catch (Exception ignored) {
        }
        m.put("refundStatus", safeStr(rs, "refund_status"));
        m.put("refundReason", safeStr(rs, "refund_reason"));
        m.put("refundAt", fmt(safeTs(rs, "refund_at")));
        m.put("refundType", safeStr(rs, "refund_type"));
        m.put("refundTrackingNo", safeStr(rs, "refund_tracking_no"));
        m.put("refundRequestedAt", fmt(safeTs(rs, "refund_requested_at")));
        m.put("completedAt", fmt(safeTs(rs, "completed_at")));
        m.put("shareToken", safeStr(rs, "share_token"));
        m.put("warrantyUntil", safeStr(rs, "warranty_until"));
        m.put("invoiceTitle", safeStr(rs, "invoice_title"));
        m.put("invoiceStatus", safeStr(rs, "invoice_status"));
        m.put("refundFeeYuan", safeDouble(rs, "refund_fee_yuan"));
        m.put("partialShip", (int) safeLong(rs, "partial_ship") > 0);
        m.put("receiveVerifiedAt", fmt(safeTs(rs, "receive_verified_at")));
        m.put("payChannel", safeStr(rs, "pay_channel"));
        m.put("fulfillMode", safeStr(rs, "fulfill_mode"));
        m.put("deliveryOn", safeStr(rs, "delivery_on"));
        m.put("slotLabel", safeStr(rs, "slot_label"));
        long slotId = safeLong(rs, "slot_id");
        if (slotId > 0) m.put("slotId", slotId);
        m.put("priceRate", safeDouble(rs, "price_rate"));
        m.put("depositYuan", safeDouble(rs, "deposit_yuan"));
        m.put("rentYuan", safeDouble(rs, "rent_yuan"));
        m.put("lateFeeYuan", safeDouble(rs, "late_fee_yuan"));
        m.put("depositStatus", safeStr(rs, "deposit_status"));
        m.put("damageNote", safeStr(rs, "damage_note"));
        m.put("damageDeductYuan", safeDouble(rs, "damage_deduct_yuan"));
        m.put("createdAt", fmt(rs.getTimestamp("created_at")));
        m.put("updatedAt", fmt(rs.getTimestamp("updated_at")));
        String un = rs.getString("username");
        if (un != null && !un.isBlank()) m.put("displayName", UserStore.displayName(un));
        return m;
    }

    private static double safeDouble(java.sql.ResultSet rs, String col) {
        try {
            double v = rs.getDouble(col);
            return rs.wasNull() ? 0 : v;
        } catch (Exception e) {
            return 0;
        }
    }

    private static double toDouble(Object o) {
        if (o instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(o));
        } catch (Exception e) {
            return 0;
        }
    }

    private static Timestamp safeTs(java.sql.ResultSet rs, String col) {
        try {
            return rs.getTimestamp(col);
        } catch (Exception e) {
            return null;
        }
    }

    private static long safeLong(java.sql.ResultSet rs, String col) {
        try {
            long v = rs.getLong(col);
            return rs.wasNull() ? 0L : v;
        } catch (Exception e) {
            return 0L;
        }
    }

    private static String safeStr(java.sql.ResultSet rs, String col) {
        try {
            String v = rs.getString(col);
            return v == null ? "" : v;
        } catch (Exception e) {
            return "";
        }
    }

    private static void requireOrderColIfPresent(String col, String label, boolean present) {
        if (!present) return;
        if (!hasOrderColumn(col)) {
            throw new IllegalStateException("系统未配置「" + label + "」字段，无法保存");
        }
    }

    private static boolean hasLineColumn(String col) {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=? AND COLUMN_NAME=?",
                    Integer.class, LINE, col);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static Map<String, Object> extraForItem(List<Map<String, Object>> lineExtras, long itemId) {
        if (lineExtras == null) return Map.of();
        for (Map<String, Object> row : lineExtras) {
            if (row == null) continue;
            Object id = row.get("itemId");
            if (id == null) id = row.get("item_id");
            long n = 0;
            if (id instanceof Number num) n = num.longValue();
            else if (id != null) {
                try {
                    n = Long.parseLong(String.valueOf(id).trim());
                } catch (NumberFormatException ignored) {
                    n = 0;
                }
            }
            if (n == itemId) return row;
        }
        return Map.of();
    }

    private static String extraStr(Map<String, Object> extra, String... keys) {
        if (extra == null) return "";
        for (String key : keys) {
            Object v = extra.get(key);
            if (v == null) continue;
            String s = String.valueOf(v).trim();
            if (!s.isBlank() && !"null".equals(s)) return s;
        }
        return "";
    }

    private static void insertOrderLine(
            long orderId,
            long itemId,
            String title,
            double price,
            int qty,
            Map<String, Object> extra) {
        String customText = extraStr(extra, "customText", "custom_text");
        String specChoice = extraStr(extra, "specChoice", "spec_choice");
        String attachUrl = extraStr(extra, "attachUrl", "attach_url");
        if (customText.length() > 200) customText = customText.substring(0, 200);
        if (specChoice.length() > 120) specChoice = specChoice.substring(0, 120);
        if (attachUrl.length() > 255) attachUrl = attachUrl.substring(0, 255);
        boolean any = !customText.isBlank() || !specChoice.isBlank() || !attachUrl.isBlank();
        if (lineCustom && customText.isBlank()) {
            throw new IllegalArgumentException("请填写定制内容");
        }
        if ((lineCustom || any) && !hasLineColumn("custom_text")) {
            throw new IllegalStateException("系统未配置定制内容字段，无法保存");
        }
        if (!specChoice.isBlank() && !hasLineColumn("spec_choice")) {
            throw new IllegalStateException("系统未配置规格选项字段，无法保存");
        }
        if (!specChoice.isBlank()) {
            LineCustomStore.assertKnown(specChoice);
        }
        if (!attachUrl.isBlank() && !hasLineColumn("attach_url")) {
            throw new IllegalStateException("系统未配置定制图片字段，无法保存");
        }
        if (hasLineColumn("custom_text")) {
            db().update(
                    "INSERT INTO " + LINE
                            + " (order_id,item_id,title,price_yuan,qty,custom_text,spec_choice,attach_url) VALUES (?,?,?,?,?,?,?,?)",
                    orderId, itemId, title, price, qty, customText, specChoice, attachUrl);
        } else {
            db().update(
                    "INSERT INTO " + LINE + " (order_id,item_id,title,price_yuan,qty) VALUES (?,?,?,?,?)",
                    orderId, itemId, title, price, qty);
        }
    }

    private static boolean casualRefundReason(String why) {
        String s = why == null ? "" : why.trim();
        if (s.isBlank()) return true;
        return s.contains("无理由") || s.contains("不想要") || s.contains("不喜欢")
                || s.contains("拍错") || s.contains("买错");
    }

    private static boolean hasOrderColumn(String col) {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=? AND COLUMN_NAME=?",
                    Integer.class, ORDER, col);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static void ensureDeliveryColumns() {
        // no-op：履约列由 bake 按域写入，禁止运行时补跨域超集
    }

    private static void ensureLoyaltyColumns() {
        ensureOrderColumn("discount_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0");
        ensureOrderColumn("pay_balance_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0");
        ensureOrderColumn("points_earned", "INT NOT NULL DEFAULT 0");
        ensureOrderColumn("coupon_code", "VARCHAR(32) DEFAULT ''");
    }

    private static void ensureRefundColumns() {
        ensureOrderColumn("refund_status", "VARCHAR(16) DEFAULT ''");
        ensureOrderColumn("refund_reason", "VARCHAR(255) DEFAULT ''");
        ensureOrderColumn("refund_at", "DATETIME NULL");
        ensureOrderColumn("refund_type", "VARCHAR(32) DEFAULT ''");
        ensureOrderColumn("refund_tracking_no", "VARCHAR(64) DEFAULT ''");
        ensureOrderColumn("refund_requested_at", "DATETIME NULL");
        ensureOrderColumn("completed_at", "DATETIME NULL");
        ensureOrderColumn("share_token", "VARCHAR(16) DEFAULT ''");
        ensureOrderColumn("warranty_until", "DATE NULL");
        ensureOrderColumn("refund_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0");
        ensureOrderColumn("partial_ship", "TINYINT NOT NULL DEFAULT 0");
        ensureOrderColumn("receive_verified_at", "DATETIME NULL");
        ensureOrderColumn("invoice_title", "VARCHAR(128) DEFAULT ''");
        ensureOrderColumn("invoice_status", "VARCHAR(16) DEFAULT ''");
    }

    private static void ensurePayChannelColumn() {
        ensureOrderColumn("pay_channel", "VARCHAR(16) DEFAULT ''");
    }

    private static void applyLoyaltySnapshot(long orderId, Map<String, Object> snap) {
        if (snap == null || orderId <= 0) return;
        double discount = toDouble(snap.get("discountYuan"));
        double payBal = toDouble(snap.get("payBalanceYuan"));
        double payable = toDouble(snap.get("payableYuan"));
        String coupon = String.valueOf(snap.getOrDefault("couponCode", ""));
        if (!(hasOrderColumn("discount_yuan") && hasOrderColumn("pay_balance_yuan"))) {
            if (payBal > 1e-9) {
                throw new IllegalStateException("订单缺少余额字段，无法记扣款");
            }
            return;
        }
        try {
            if (hasOrderColumn("coupon_code")) {
                db().update(
                        "UPDATE " + ORDER
                                + " SET total_yuan=?, discount_yuan=?, pay_balance_yuan=?, coupon_code=?, updated_at=? WHERE id=?",
                        BigDecimal.valueOf(payable).setScale(2, RoundingMode.HALF_UP),
                        BigDecimal.valueOf(discount).setScale(2, RoundingMode.HALF_UP),
                        BigDecimal.valueOf(payBal).setScale(2, RoundingMode.HALF_UP),
                        coupon == null || "null".equals(coupon) ? "" : coupon,
                        Timestamp.valueOf(LocalDateTime.now()),
                        orderId);
            } else {
                db().update(
                        "UPDATE " + ORDER + " SET total_yuan=?, discount_yuan=?, pay_balance_yuan=?, updated_at=? WHERE id=?",
                        BigDecimal.valueOf(payable).setScale(2, RoundingMode.HALF_UP),
                        BigDecimal.valueOf(discount).setScale(2, RoundingMode.HALF_UP),
                        BigDecimal.valueOf(payBal).setScale(2, RoundingMode.HALF_UP),
                        Timestamp.valueOf(LocalDateTime.now()),
                        orderId);
            }
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("订单支付快照写入失败", e);
        }
    }

    /** 用户申请售后/退款：shipped/completed → refund_status=pending */
    public static Map<String, Object> requestRefund(long orderId, String username, String reason) {
        return requestRefund(orderId, username, reason, "");
    }

    /**
     * 用户申请售后。refundType：refund_only / return_refund（空则按域默认仅退款语义）。
     */
    public static Map<String, Object> requestRefund(
            long orderId, String username, String reason, String refundType) {
        requireEnabled();
        ensureRefundColumns();
        Map<String, Object> m = getOrder(orderId);
        if (m == null) throw new IllegalArgumentException("订单不存在");
        if (!username.equals(String.valueOf(m.get("username")))) {
            throw new IllegalStateException("无权申请");
        }
        String st = String.valueOf(m.get("status"));
        if (SeatStore.enabled()) {
            if (!"pending".equals(st) && !"confirmed".equals(st)
                    && !"shipped".equals(st) && !"in_transit".equals(st)
                    && !"signed".equals(st) && !"completed".equals(st)) {
                throw new IllegalStateException("当前状态不可退票");
            }
            SeatStore.assertOrderRefundOpen(orderId);
        } else if (!"shipped".equals(st) && !"in_transit".equals(st) && !"signed".equals(st) && !"completed".equals(st)) {
            throw new IllegalStateException("仅已发货及之后状态可申请售后");
        }
        assertWithinAfterSaleWindow(m, st);
        String rs = String.valueOf(m.getOrDefault("refundStatus", ""));
        if ("pending".equals(rs) || "approved".equals(rs)) {
            throw new IllegalStateException("已有售后申请");
        }
        String why = reason == null ? "" : reason.trim();
        if (why.isBlank()) throw new IllegalStateException("请填写售后原因");
        if (why.length() > 255) why = why.substring(0, 255);
        if (noCasualRefund && casualRefundReason(why)) {
            throw new IllegalStateException("不支持无理由退货，请填写质量问题等具体原因");
        }
        String type = normalizeRefundType(refundType);
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        if (hasOrderColumn("refund_type") && hasOrderColumn("refund_requested_at")) {
            db().update(
                    "UPDATE " + ORDER
                            + " SET refund_status='pending', refund_reason=?, refund_type=?,"
                            + " refund_requested_at=?, updated_at=? WHERE id=?",
                    why, type, now, now, orderId);
        } else {
            db().update(
                    "UPDATE " + ORDER + " SET refund_status='pending', refund_reason=?, updated_at=? WHERE id=?",
                    why, now, orderId);
        }
        try {
            String typeTip = "return_refund".equals(type) ? "退货退款"
                    : ("refund_only".equals(type) ? "仅退款"
                    : ("exchange_only".equals(type) ? "仅换货"
                    : ("exchange".equals(type) ? "换货" : "")));
            MessageStore.notifyAdmins(
                    "售后待处理",
                    UserStore.displayName(username) + " 申请订单 #" + orderId
                            + (typeTip.isBlank() ? "" : ("（" + typeTip + "）"))
                            + " 售后：" + why,
                    "order",
                    orderId);
        } catch (Exception ignored) {
        }
        return getOrder(orderId);
    }

    /** 用户或商家回填退货物流单号（退货退款时）。 */
    public static Map<String, Object> updateRefundTracking(
            long orderId, String username, boolean admin, String trackingNo) {
        requireEnabled();
        ensureRefundColumns();
        Map<String, Object> m = getOrder(orderId);
        if (m == null) throw new IllegalArgumentException("订单不存在");
        if (!admin && !username.equals(String.valueOf(m.get("username")))) {
            throw new IllegalStateException("无权填写");
        }
        if (!"pending".equals(String.valueOf(m.getOrDefault("refundStatus", "")))) {
            throw new IllegalStateException("当前无待处理售后");
        }
        String type = String.valueOf(m.getOrDefault("refundType", ""));
        if (!"return_refund".equals(type) && !"exchange".equals(type) && !type.isBlank()) {
            throw new IllegalStateException("仅退货或换货需填写退货单号");
        }
        if (!hasOrderColumn("refund_tracking_no")) {
            throw new IllegalStateException("系统未配置退货物流字段");
        }
        String track = trackingNo == null ? "" : trackingNo.trim();
        if (track.isBlank()) throw new IllegalArgumentException("请填写退货物流单号");
        if (track.length() > 64) track = track.substring(0, 64);
        db().update(
                "UPDATE " + ORDER + " SET refund_tracking_no=?, updated_at=? WHERE id=?",
                track, Timestamp.valueOf(LocalDateTime.now()), orderId);
        return getOrder(orderId);
    }

    /** 售后进度时间轴（申请 → 退货寄出 → 审结）。 */
    public static List<Map<String, Object>> refundTrace(long orderId) {
        requireEnabled();
        Map<String, Object> m = getOrder(orderId);
        if (m == null) throw new IllegalArgumentException("订单不存在");
        List<Map<String, Object>> nodes = new ArrayList<>();
        String rs = String.valueOf(m.getOrDefault("refundStatus", ""));
        if (rs.isBlank() || "null".equals(rs)) {
            return nodes;
        }
        String why = String.valueOf(m.getOrDefault("refundReason", ""));
        String type = String.valueOf(m.getOrDefault("refundType", ""));
        String typeTip = "return_refund".equals(type) ? "退货退款"
                : ("refund_only".equals(type) ? "仅退款"
                : ("exchange_only".equals(type) ? "仅换货"
                : ("exchange".equals(type) ? "换货" : "售后")));
        Object reqAt = m.get("refundRequestedAt");
        if (reqAt == null || String.valueOf(reqAt).isBlank()) reqAt = m.get("updatedAt");
        nodes.add(traceNode(reqAt, "已提交申请", typeTip + (why.isBlank() ? "" : (" · " + why))));
        String track = String.valueOf(m.getOrDefault("refundTrackingNo", ""));
        if (!track.isBlank() && !"null".equals(track)) {
            nodes.add(traceNode(m.get("updatedAt"), "退货已寄出", "运单 " + track));
        } else if ("return_refund".equals(type) && "pending".equals(rs)) {
            nodes.add(traceNode(null, "待寄回商品", "请填写退货物流单号"));
        }
        if ("pending".equals(rs)) {
            nodes.add(traceNode(null, "商家审核中", "请耐心等待处理结果"));
        } else if ("approved".equals(rs)) {
            String done = "exchange".equals(type) || "exchange_only".equals(type) ? "已同意换货" : "已退款办结";
            nodes.add(traceNode(m.get("refundAt"), "售后已通过", done));
        } else if ("rejected".equals(rs)) {
            nodes.add(traceNode(m.get("refundAt"), "售后已驳回", why.isBlank() ? "未通过" : why));
        }
        return nodes;
    }

    private static String normalizeRefundType(String raw) {
        String t = raw == null ? "" : raw.trim().toLowerCase(Locale.ROOT);
        if ("return_refund".equals(t) || "return-refund".equals(t) || "退货退款".equals(raw == null ? "" : raw.trim())) {
            return "return_refund";
        }
        if ("exchange_only".equals(t) || "exchange-only".equals(t) || "仅换货".equals(raw == null ? "" : raw.trim())) {
            return "exchange_only";
        }
        if ("exchange".equals(t) || "换货".equals(raw == null ? "" : raw.trim())) {
            return "exchange";
        }
        if ("refund_only".equals(t) || "refund-only".equals(t) || "仅退款".equals(raw == null ? "" : raw.trim())) {
            return "refund_only";
        }
        return t.isBlank() ? "" : "refund_only";
    }

    private static void assertWithinAfterSaleWindow(Map<String, Object> m, String st) {
        if (afterSaleDays <= 0) return;
        if (!"signed".equals(st) && !"completed".equals(st)) return;
        Object doneAt = m.get("completedAt");
        if (doneAt == null || String.valueOf(doneAt).isBlank() || "null".equals(String.valueOf(doneAt))) {
            doneAt = m.get("updatedAt");
        }
        if (doneAt == null || String.valueOf(doneAt).isBlank()) return;
        try {
            LocalDateTime t = LocalDateTime.parse(String.valueOf(doneAt).replace(' ', 'T').substring(0, 19));
            if (t.plusDays(afterSaleDays).isBefore(LocalDateTime.now())) {
                throw new IllegalStateException("已超过售后时限（收货后 " + afterSaleDays + " 天内可申请）");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception ignored) {
        }
    }

    /** 管理端：通过售后（回补库存、退余额、订单 cancelled）或驳回 */
    public static Map<String, Object> decideRefund(long orderId, boolean pass, String note) {
        requireEnabled();
        ensureRefundColumns();
        Map<String, Object> m = getOrder(orderId);
        if (m == null) throw new IllegalArgumentException("订单不存在");
        if (!"pending".equals(String.valueOf(m.getOrDefault("refundStatus", "")))) {
            throw new IllegalStateException("当前无待审售后");
        }
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        if (!pass) {
            String tip = note == null || note.isBlank() ? "售后已驳回" : note.trim();
            db().update(
                    "UPDATE " + ORDER + " SET refund_status='rejected', refund_reason=?, refund_at=?, updated_at=? WHERE id=?",
                    tip, now, now, orderId);
            try {
                MessageStore.send(
                        String.valueOf(m.get("username")),
                        "售后已驳回",
                        "订单 #" + orderId + "：" + tip,
                        "order",
                        orderId);
            } catch (Exception ignored) {
            }
            return getOrder(orderId);
        }
        String rType = String.valueOf(m.getOrDefault("refundType", ""));
        boolean exchange = "exchange".equals(rType) || "exchange_only".equals(rType);
        if (exchange) {
            db().update(
                    "UPDATE " + ORDER + " SET refund_status='approved', refund_at=?, updated_at=? WHERE id=?",
                    now, now, orderId);
            try {
                MessageStore.send(
                        String.valueOf(m.get("username")),
                        "售后已通过",
                        "订单 #" + orderId + ("exchange_only".equals(rType) ? " 已同意换货。" : " 已同意换货办理。"),
                        "order",
                        orderId);
            } catch (Exception ignored) {
            }
            return getOrder(orderId);
        }
        // 通过：按取消回补库存与余额，状态改为 cancelled
        String prevStatus = String.valueOf(m.get("status"));
        if (useQuota) {
            for (Map<String, Object> line : listLines(orderId)) {
                if ("snack".equals(String.valueOf(line.get("lineKind")))) continue;
                ArchiveStore.adjustStock(
                        ((Number) line.get("itemId")).longValue(),
                        ((Number) line.get("qty")).intValue());
            }
        }
        if (LoyaltyStore.anyEnabled()) {
            String uname = String.valueOf(m.get("username"));
            double paid = toDouble(m.get("payBalanceYuan"));
            if (paid > 0) {
                LoyaltyStore.refundOrderPay(uname, orderId, paid);
            }
            if ("completed".equals(prevStatus)) {
                int pts = 0;
                Object pe = m.get("pointsEarned");
                if (pe instanceof Number n) pts = n.intValue();
                double pay = paid > 0 ? paid : toDouble(m.get("totalYuan"));
                LoyaltyStore.clawbackOrderCompleted(uname, orderId, pts, pay);
            }
            if (LoyaltyStore.isCouponEnabled()) {
                CouponStore.releaseByOrder(orderId);
            }
        }
        db().update(
                "UPDATE " + ORDER
                        + " SET status='cancelled', refund_status='approved', refund_at=?, updated_at=? WHERE id=?",
                now, now, orderId);
        restoreSnackStockForOrder(orderId);
        SeatStore.releaseByOrder(orderId);
        ConsignStore.release(orderId, listLines(orderId));
        try {
            MessageStore.send(
                    String.valueOf(m.get("username")),
                    "售后已通过",
                    "订单 #" + orderId + " 已退款办结。",
                    "order",
                    orderId);
        } catch (Exception ignored) {
        }
        return getOrder(orderId);
    }

    /** 物流轨迹：按状态拼多节点时间线（含运输中/派送中；不对接快递公司 API）。 */
    public static List<Map<String, Object>> logisticsTrace(long orderId) {
        requireEnabled();
        Map<String, Object> m = getOrder(orderId);
        if (m == null) throw new IllegalArgumentException("订单不存在");
        List<Map<String, Object>> nodes = new ArrayList<>();
        nodes.add(traceNode(m.get("createdAt"), "已下单", "商家待确认"));
        String st = String.valueOf(m.get("status"));
        boolean shipPhase = "shipped".equals(st)
                || "in_transit".equals(st)
                || "signed".equals(st)
                || "completed".equals(st);
        Object shipAt = shipPhase
                ? (m.get("shippedAt") != null ? m.get("shippedAt") : m.get("updatedAt"))
                : null;
        if (!"pending".equals(st) && !"cancelled".equals(st)) {
            // 发货后 updatedAt 常被刷新到 shippedAt 之后，确认节点改用稳定时刻避免时间倒序
            nodes.add(traceNode(confirmTraceAt(m, shipAt), "商家已确认", "备货中"));
        }
        if (shipPhase) {
            String track = String.valueOf(m.getOrDefault("trackingNo", ""));
            String dtype = String.valueOf(m.getOrDefault("deliveryType", ""));
            boolean pickup = dtype.contains("自取") || dtype.contains("堂食") || dtype.contains("自提");
            if (pickup) {
                boolean foodStyle = pickupFoodStyle(dtype);
                String code = String.valueOf(m.getOrDefault("pickupCode", ""));
                if (foodStyle) {
                    String tip = code.isBlank() || "null".equals(code) ? "请到店领取" : ("取餐码 " + code);
                    nodes.add(traceNode(shipAt, "已出餐", tip));
                    nodes.add(traceNode(shipAt, "待取餐", "请尽快到店领取"));
                } else {
                    String tip = code.isBlank() || "null".equals(code) ? "请到店领取" : ("取货码 " + code);
                    nodes.add(traceNode(shipAt, "已备货", tip));
                    nodes.add(traceNode(shipAt, "待自提", "请尽快到店领取"));
                }
            } else {
                boolean partial = Boolean.TRUE.equals(m.get("partialShip"));
                String tip = track.isBlank() || "null".equals(track) ? "已交接承运" : ("运单 " + track);
                nodes.add(traceNode(shipAt, partial ? "部分发货" : "已发货", tip));
                nodes.add(traceNode(shipAt, "运输中", "快件运输途中"));
                nodes.add(traceNode(shipAt, "派送中", "快递员正在派送"));
            }
        }
        for (Map<String, Object> extra : listShipNodes(orderId)) {
            nodes.add(traceNode(extra.get("at"), String.valueOf(extra.get("title")), String.valueOf(extra.get("detail"))));
        }
        if ("signed".equals(st)) {
            nodes.add(traceNode(m.get("updatedAt"), "已签收", "买家已签收"));
        } else if ("completed".equals(st)) {
            nodes.add(traceNode(m.get("updatedAt"), "已签收/完成", "订单完结"));
        }
        if ("cancelled".equals(st)) {
            nodes.add(traceNode(m.get("updatedAt"), "已取消", "订单关闭"));
        }
        String rs = String.valueOf(m.getOrDefault("refundStatus", ""));
        if ("pending".equals(rs)) {
            nodes.add(traceNode(m.get("updatedAt"), "售后申请中", String.valueOf(m.getOrDefault("refundReason", ""))));
        } else if ("approved".equals(rs)) {
            nodes.add(traceNode(m.get("refundAt"), "售后已通过", "已退款办结"));
        } else if ("rejected".equals(rs)) {
            nodes.add(traceNode(m.get("refundAt"), "售后已驳回", String.valueOf(m.getOrDefault("refundReason", ""))));
        }
        return nodes;
    }

    /** 确认节点时间：有发货时刻时避免用晚于发货的 updatedAt。 */
    private static Object confirmTraceAt(Map<String, Object> m, Object shipAt) {
        Object updated = m.get("updatedAt");
        Object created = m.get("createdAt");
        if (shipAt == null || isBlankTraceAt(shipAt)) {
            return updated != null ? updated : created;
        }
        if (!isBlankTraceAt(updated) && String.valueOf(updated).compareTo(String.valueOf(shipAt)) <= 0) {
            return updated;
        }
        if (!isBlankTraceAt(created) && String.valueOf(created).compareTo(String.valueOf(shipAt)) <= 0) {
            return created;
        }
        return shipAt;
    }

    /** 堂食/纯自取走餐饮词；商城自提等多店场景走备货/取货。 */
    private static boolean pickupFoodStyle(String dtype) {
        String d = dtype == null ? "" : dtype.trim();
        if (d.contains("堂食")) return true;
        if (ArchiveStore.shopMarketplaceEnabled()) return false;
        return "自取".equals(d);
    }

    private static boolean isBlankTraceAt(Object at) {
        if (at == null) return true;
        String s = String.valueOf(at).trim();
        return s.isEmpty() || "null".equals(s);
    }

    private static Map<String, Object> traceNode(Object at, String title, String detail) {
        Map<String, Object> n = new LinkedHashMap<>();
        n.put("at", at == null || "null".equals(String.valueOf(at)) ? "" : String.valueOf(at));
        n.put("title", title);
        n.put("detail", detail == null ? "" : detail);
        return n;
    }

    static void ensureShareToken(long orderId) {
        if (orderId <= 0 || !hasOrderColumn("share_token")) return;
        try {
            String cur = db().queryForObject(
                    "SELECT share_token FROM " + ORDER + " WHERE id=?", String.class, orderId);
            if (cur != null && !cur.isBlank()) return;
        } catch (Exception ignored) {
            return;
        }
        String token = UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase(Locale.ROOT);
        db().update(
                "UPDATE " + ORDER + " SET share_token=? WHERE id=? AND (share_token IS NULL OR share_token='')",
                token, orderId);
    }

    public static Map<String, Object> getOrderByShareToken(String token) {
        requireEnabled();
        String t = token == null ? "" : token.trim().toUpperCase(Locale.ROOT);
        if (t.isBlank() || !hasOrderColumn("share_token")) {
            throw new IllegalArgumentException("口令无效");
        }
        List<Map<String, Object>> list = db().query(
                "SELECT * FROM " + ORDER + " WHERE share_token=?",
                (rs, i) -> mapOrder(rs),
                t);
        if (list.isEmpty()) throw new IllegalArgumentException("口令无效");
        Map<String, Object> m = list.get(0);
        m.put("lines", listLines(((Number) m.get("id")).longValue()));
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", m.get("id"));
        out.put("status", m.get("status"));
        out.put("totalYuan", m.get("totalYuan"));
        out.put("createdAt", m.get("createdAt"));
        out.put("trackingNo", m.get("trackingNo"));
        out.put("partialShip", m.get("partialShip"));
        out.put("lines", m.get("lines"));
        out.put("shareToken", m.get("shareToken"));
        return out;
    }

    public static List<Map<String, Object>> listShipNodes(long orderId) {
        if (!hasShipNodeTable()) return List.of();
        try {
            return db().query(
                    "SELECT happened_at, title, detail FROM order_ship_node WHERE order_id=? ORDER BY id",
                    (rs, i) -> {
                        Map<String, Object> n = new LinkedHashMap<>();
                        n.put("at", fmt(rs.getTimestamp("happened_at")));
                        n.put("title", rs.getString("title"));
                        n.put("detail", rs.getString("detail"));
                        return n;
                    },
                    orderId);
        } catch (Exception e) {
            return List.of();
        }
    }

    public static Map<String, Object> addShipNode(
            long orderId, String title, String detail, String happenedAt) {
        requireEnabled();
        if (!hasShipNodeTable()) throw new IllegalStateException("系统未配置物流进度");
        if (getOrder(orderId) == null) throw new IllegalArgumentException("订单不存在");
        String t = title == null ? "" : title.trim();
        if (t.isBlank()) throw new IllegalArgumentException("请填写进度说明");
        if (t.length() > 64) t = t.substring(0, 64);
        String d = detail == null ? "" : detail.trim();
        if (d.length() > 255) d = d.substring(0, 255);
        Timestamp at = Timestamp.valueOf(LocalDateTime.now());
        if (happenedAt != null && !happenedAt.isBlank()) {
            String raw = happenedAt.trim().replace('T', ' ');
            if (raw.length() >= 16 && raw.length() < 19) raw = raw + ":00";
            try {
                at = Timestamp.valueOf(raw.substring(0, Math.min(19, raw.length())));
            } catch (Exception ignored) {
            }
        }
        db().update(
                "INSERT INTO order_ship_node (order_id, happened_at, title, detail) VALUES (?,?,?,?)",
                orderId, at, t, d);
        return getOrder(orderId);
    }

    public static Map<String, Object> verifyReceiveCode(long orderId, String code) {
        requireEnabled();
        Map<String, Object> m = getOrder(orderId);
        if (m == null) throw new IllegalArgumentException("订单不存在");
        if (!hasOrderColumn("pickup_code")) {
            throw new IllegalStateException("系统未配置收货码");
        }
        String expect = String.valueOf(m.getOrDefault("pickupCode", "")).trim();
        String got = code == null ? "" : code.trim();
        if (expect.isBlank() || !expect.equals(got)) {
            throw new IllegalStateException("收货码不正确");
        }
        if (hasOrderColumn("receive_verified_at")) {
            Timestamp now = Timestamp.valueOf(LocalDateTime.now());
            db().update(
                    "UPDATE " + ORDER + " SET receive_verified_at=?, updated_at=? WHERE id=?",
                    now, now, orderId);
        }
        return getOrder(orderId);
    }

    public static Map<String, Object> updateWarranty(long orderId, String until) {
        requireEnabled();
        if (!hasOrderColumn("warranty_until")) {
            throw new IllegalStateException("系统未配置延保字段");
        }
        if (getOrder(orderId) == null) throw new IllegalArgumentException("订单不存在");
        String day = until == null ? "" : until.trim();
        if (day.length() >= 10) day = day.substring(0, 10);
        if (day.isBlank()) throw new IllegalArgumentException("请选择延保截止日期");
        db().update(
                "UPDATE " + ORDER + " SET warranty_until=?, updated_at=? WHERE id=?",
                java.sql.Date.valueOf(day),
                Timestamp.valueOf(LocalDateTime.now()),
                orderId);
        return getOrder(orderId);
    }

    
    public static Map<String, Object> updateInvoice(long orderId, String title, String status, boolean asAdmin) {
        requireEnabled();
        if (!hasOrderColumn("invoice_title") && !hasOrderColumn("invoice_status")) {
            throw new IllegalStateException("系统未配置发票字段");
        }
        if (getOrder(orderId) == null) throw new IllegalArgumentException("订单不存在");
        String tt = title == null ? "" : title.trim();
        if (tt.length() > 128) tt = tt.substring(0, 128);
        String st = status == null ? "" : status.trim().toLowerCase(java.util.Locale.ROOT);
        if (st.isBlank()) {
            st = tt.isBlank() ? "" : "pending";
        }
        if (!st.isBlank() && !"pending".equals(st) && !"issued".equals(st)) {
            throw new IllegalArgumentException("开票状态无效");
        }
        if ("issued".equals(st) && !asAdmin) {
            throw new IllegalStateException("仅商家可标记已开");
        }
        if ("pending".equals(st) && tt.isBlank() && hasOrderColumn("invoice_title")) {
            throw new IllegalArgumentException("请填写发票抬头");
        }
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        if (hasOrderColumn("invoice_title") && hasOrderColumn("invoice_status")) {
            db().update(
                    "UPDATE " + ORDER + " SET invoice_title=?, invoice_status=?, updated_at=? WHERE id=?",
                    tt, st, now, orderId);
        } else if (hasOrderColumn("invoice_title")) {
            db().update(
                    "UPDATE " + ORDER + " SET invoice_title=?, updated_at=? WHERE id=?",
                    tt, now, orderId);
        } else {
            db().update(
                    "UPDATE " + ORDER + " SET invoice_status=?, updated_at=? WHERE id=?",
                    st, now, orderId);
        }
        return getOrder(orderId);
    }

    public static Map<String, Object> claimRider(long orderId, String riderUsername) {
        requireEnabled();
        if (!hasOrderColumn("rider_username") || !hasOrderColumn("rider_claimed_at")) {
            throw new IllegalStateException("系统未配置骑手接单");
        }
        String rider = riderUsername == null ? "" : riderUsername.trim();
        if (rider.isBlank()) throw new IllegalArgumentException("请登录骑手账号后接单");
        Map<String, Object> m = getOrder(orderId);
        if (m == null) throw new IllegalArgumentException("订单不存在");
        String st = String.valueOf(m.getOrDefault("status", ""));
        if (!"confirmed".equals(st) && !"pending".equals(st)) {
            throw new IllegalStateException("当前状态不可接单");
        }
        String cur = String.valueOf(m.getOrDefault("riderUsername", "")).trim();
        if (!cur.isBlank() && !cur.equals(rider)) {
            throw new IllegalStateException("该单已有骑手接单");
        }
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        int n = db().update(
                "UPDATE " + ORDER + " SET rider_username=?, rider_claimed_at=?, status='confirmed', updated_at=? "
                        + "WHERE id=? AND (rider_username IS NULL OR rider_username='' OR rider_username=?)",
                rider, now, now, orderId, rider);
        if (n <= 0) throw new IllegalStateException("接单失败，请刷新后重试");
        return getOrder(orderId);
    }

    public static int releaseTimedOutRiderClaims(int timeoutMinutes) {
        if (!enabled || timeoutMinutes <= 0) return 0;
        if (!hasOrderColumn("rider_username") || !hasOrderColumn("rider_claimed_at")) return 0;
        try {
            return db().update(
                    "UPDATE " + ORDER + " SET rider_username='', rider_claimed_at=NULL, updated_at=NOW() "
                            + "WHERE status='confirmed' "
                            + "AND rider_username IS NOT NULL AND rider_username<>'' "
                            + "AND rider_claimed_at IS NOT NULL "
                            + "AND rider_claimed_at < DATE_SUB(NOW(), INTERVAL ? MINUTE)",
                    timeoutMinutes);
        } catch (Exception e) {
            return 0;
        }
    }

    private static String strPlace(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static boolean boolPlace(Object o) {
        if (o == null) return false;
        if (o instanceof Boolean b) return b;
        String s = String.valueOf(o).trim();
        return "1".equals(s) || "true".equalsIgnoreCase(s) || "yes".equalsIgnoreCase(s);
    }

    private static void assertStallOpenForCart(List<Map<String, Object>> cart) {
        LocalDateTime now = LocalDateTime.now();
        int hm = now.getHour() * 100 + now.getMinute();
        for (Map<String, Object> line : cart) {
            long itemId = line.get("itemId") instanceof Number n ? n.longValue() : 0L;
            if (itemId <= 0) continue;
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            if (item == null) continue;
            String hours = String.valueOf(item.getOrDefault("openHours", "")).trim();
            if (hours.isBlank()) hours = String.valueOf(item.getOrDefault("open_hours", "")).trim();
            if (hours.isBlank() || !hours.contains("-")) continue;
            String[] parts = hours.split("-", 2);
            int start = parseHm(parts[0]);
            int end = parseHm(parts[1]);
            if (start < 0 || end < 0) continue;
            boolean open = start <= end ? (hm >= start && hm <= end) : (hm >= start || hm <= end);
            if (!open) {
                throw new IllegalStateException("当前不在营业时段，请稍后再点");
            }
        }
    }

    private static int parseHm(String raw) {
        String s = raw == null ? "" : raw.trim().replace("：", ":");
        if (s.length() < 4) return -1;
        try {
            String[] p = s.split(":");
            int h = Integer.parseInt(p[0].trim());
            int m = p.length > 1 ? Integer.parseInt(p[1].trim()) : 0;
            if (h < 0 || h > 23 || m < 0 || m > 59) return -1;
            return h * 100 + m;
        } catch (Exception e) {
            return -1;
        }
    }

    private static void assertRequiredCategoryInCart(List<Map<String, Object>> cart) {
        if (!ArchiveStore.hasRequiredPickCategories()) return;
        List<Long> need = ArchiveStore.listRequiredCategoryIds();
        if (need == null || need.isEmpty()) return;
        for (Map<String, Object> line : cart) {
            long itemId = line.get("itemId") instanceof Number n ? n.longValue() : 0L;
            if (itemId <= 0) continue;
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            if (item == null) continue;
            long cid = item.get("categoryId") instanceof Number n ? n.longValue() : 0L;
            if (cid > 0 && need.contains(cid)) return;
            Object names = item.get("categoryIds");
            if (names instanceof List<?> ids) {
                for (Object o : ids) {
                    long id = o instanceof Number n ? n.longValue() : 0L;
                    if (id > 0 && need.contains(id)) return;
                }
            }
        }
        throw new IllegalStateException("请先选择必选品类中的餐品");
    }

    public static Map<String, Object> updateRefundFee(long orderId, Object feeObj) {
        requireEnabled();
        if (!hasOrderColumn("refund_fee_yuan")) {
            throw new IllegalStateException("系统未配置退票手续费字段");
        }
        if (getOrder(orderId) == null) throw new IllegalArgumentException("订单不存在");
        double fee = toDouble(feeObj);
        if (fee < 0) throw new IllegalArgumentException("手续费不能为负");
        fee = round2(fee);
        db().update(
                "UPDATE " + ORDER + " SET refund_fee_yuan=?, updated_at=? WHERE id=?",
                fee,
                Timestamp.valueOf(LocalDateTime.now()),
                orderId);
        return getOrder(orderId);
    }

    private static boolean hasShipNodeTable() {
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='order_ship_node'",
                    Integer.class);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static void ensureOrderColumn(String col, String ddlType) {
        if (hasOrderColumn(col)) return;
        try {
            db().execute("ALTER TABLE " + ORDER + " ADD COLUMN " + col + " " + ddlType);
        } catch (Exception ignored) {
        }
    }

    private static void requireEnabled() {
        if (!enabled) throw new IllegalStateException("订单功能暂不可用");
    }

    private static double round2(double v) {
        return Math.round(v * 100.0) / 100.0;
    }
}
