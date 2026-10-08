package com.thesis.capability;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.thesis.config.MybatisSupport;
import com.thesis.mapper.OrderMapper;
import com.thesis.mapper.SchemaMapper;
import com.thesis.service.MessageStore;
import com.thesis.service.SeatStore;
import com.thesis.service.UserStore;

import java.math.BigDecimal;
import java.math.RoundingMode;
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

    private static OrderMapper mapper() {
        return MybatisSupport.mapper(OrderMapper.class);
    }

    private static SchemaMapper schema() {
        return MybatisSupport.mapper(SchemaMapper.class);
    }

    public static void bind(String cartTable, String orderTable, String lineTable, boolean quota) {
        CART = cartTable == null ? "" : cartTable.trim();
        ORDER = orderTable == null ? "" : orderTable.trim();
        LINE = lineTable == null ? "" : lineTable.trim();
        enabled = !CART.isBlank() && !ORDER.isBlank() && !LINE.isBlank();
        useQuota = quota;
        AddressStore.resetCache();
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

    private static String fmt(Object o) {
        if (o == null) return null;
        if (o instanceof Timestamp ts) return ts.toLocalDateTime().format(FMT);
        if (o instanceof LocalDateTime ldt) return ldt.format(FMT);
        String s = String.valueOf(o).trim();
        return s.isBlank() || "null".equals(s) ? null : s;
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
        List<Map<String, Object>> raw = mapper().selectCart(CART, username);
        List<Map<String, Object>> out = new ArrayList<>();
        if (raw != null) {
            for (Map<String, Object> r : raw) {
                out.add(enrichCartRow(
                        num(r.get("id")),
                        num(first(r, "itemId", "item_id")),
                        toInt(r.get("qty"))));
            }
        }
        return out;
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
        if (mapper().countCartItem(CART, username, itemId) > 0) {
            mapper().updateCartQty(CART, username, itemId, qty);
        } else {
            mapper().insertCart(CART, username, itemId, qty);
        }
        Map<String, Object> row = mapper().selectCartItem(CART, username, itemId);
        if (row == null) return Map.of();
        return enrichCartRow(num(row.get("id")), num(first(row, "itemId", "item_id")), toInt(row.get("qty")));
    }

    public static boolean removeCart(String username, long itemId) {
        requireEnabled();
        return mapper().deleteCartItem(CART, username, itemId) > 0;
    }

    public static void clearCart(String username) {
        requireEnabled();
        mapper().clearCart(CART, username);
    }

    public static Map<String, Object> placeOrder(String username, String remark) {
        return placeOrder(username, remark, null, null, null, null, null, null);
    }

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
            // 在线支付仍扣账户余额；不对接微信/支付宝商户 SDK ≠ 免余额
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
        requireOrderColIfPresent("receiver_name", "收货人", !rName.isBlank());
        requireOrderColIfPresent("receiver_phone", "收货电话", !rPhone.isBlank());
        requireOrderColIfPresent("address_line", "收货地址", !addr.isBlank());
        requireOrderColIfPresent("delivery_type", "配送方式", !dtype.isBlank());
        requireOrderColIfPresent("taste_note", "口味备注", !taste.isBlank());
        if (demoPay && channel != null && !channel.isBlank()) {
            requireOrderColIfPresent("pay_channel", "支付渠道", true);
        }
        LinkedHashMap<String, Object> extraCols = new LinkedHashMap<>();
        if (hasOrderColumn("receiver_name")) extraCols.put("receiver_name", rName);
        if (hasOrderColumn("receiver_phone")) extraCols.put("receiver_phone", rPhone);
        if (hasOrderColumn("address_line")) extraCols.put("address_line", addr);
        if (hasOrderColumn("delivery_type")) extraCols.put("delivery_type", dtype);
        if (hasOrderColumn("taste_note")) extraCols.put("taste_note", taste);
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
        requireOrderColIfPresent("table_no", "桌号", !tableNo.isBlank());
        requireOrderColIfPresent("utensil_opt", "餐具", !utensilOpt.isBlank());
        requireOrderColIfPresent("pack_opt", "打包", !packOpt.isBlank());
        requireOrderColIfPresent("merge_code", "拼单码", !mergeCode.isBlank());
        if (hasOrderColumn("table_no") && !tableNo.isBlank()) extraCols.put("table_no", tableNo);
        if (hasOrderColumn("utensil_opt") && !utensilOpt.isBlank()) extraCols.put("utensil_opt", utensilOpt);
        if (hasOrderColumn("pack_opt") && !packOpt.isBlank()) extraCols.put("pack_opt", packOpt);
        if (hasOrderColumn("merge_code") && !mergeCode.isBlank()) extraCols.put("merge_code", mergeCode);
        if (hasOrderColumn("packaging_fee_yuan") && packagingFee > 0) {
            extraCols.put("packaging_fee_yuan", String.format(java.util.Locale.ROOT, "%.2f", packagingFee));
        }
        if (hasOrderColumn("delivery_fee_yuan") && deliveryFee > 0) {
            extraCols.put("delivery_fee_yuan", String.format(java.util.Locale.ROOT, "%.2f", deliveryFee));
        }
        if (hasOrderColumn("eta_text") && !etaText.isBlank()) extraCols.put("eta_text", etaText);
        String invoiceTitle = strPlace(placeX.get("invoiceTitle"));
        if (hasOrderColumn("invoice_title") && !invoiceTitle.isBlank()) {
            extraCols.put("invoice_title", invoiceTitle);
            if (hasOrderColumn("invoice_status")) {
                extraCols.put("invoice_status", "pending");
            }
        }
        String noteOut = note;
        if (extraCols.isEmpty() && !taste.isBlank()) {
            noteOut = (noteOut.isBlank() ? "" : noteOut + "；") + "口味:" + taste;
        }
        if (extraCols.isEmpty() && !addr.isBlank()) {
            noteOut = (noteOut.isBlank() ? "" : noteOut + "；")
                    + "地址:" + rName + " " + rPhone + " " + addr;
        }
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        Map<String, Object> orderRow = new LinkedHashMap<>();
        orderRow.put("orderTable", ORDER);
        orderRow.put("username", username);
        final String placed = (campaignId != null && campaignId > 0)
                ? "grouping"
                : ((demoPay || lineCustomPlaceConfirmed) ? "confirmed" : "pending");
        orderRow.put("status", placed);
        orderRow.put("totalYuan", BigDecimal.valueOf(payable).setScale(2, RoundingMode.HALF_UP));
        orderRow.put("remark", noteOut);
        orderRow.put("extraCols", extraCols);
        orderRow.put("createdAt", now);
        orderRow.put("updatedAt", now);
        mapper().insertOrder(orderRow);
        long orderId = orderRow.get("id") == null ? 0L : ((Number) orderRow.get("id")).longValue();
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
                insertOrderLine(orderId, itemId, ArchiveStore.lineTitleWithSpec(item), ((Number) priced.get("unit")).doubleValue(), lineQty, extra);
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
                mapper().deleteLines(LINE, orderId);
                mapper().deleteOrder(ORDER, orderId);
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
        int q = qty;
        boolean withResv = reservationId != null && reservationId > 0;
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        double total = round2(priceYuan * q);
        Map<String, Object> orderRow = new LinkedHashMap<>();
        orderRow.put("orderTable", ORDER);
        orderRow.put("username", username);
        orderRow.put("status", "pending");
        orderRow.put("totalYuan", BigDecimal.valueOf(total).setScale(2, RoundingMode.HALF_UP));
        orderRow.put("remark", remark == null ? "" : remark);
        LinkedHashMap<String, Object> extra = new LinkedHashMap<>();
        if (withResv) extra.put("reservation_id", reservationId);
        orderRow.put("extraCols", extra);
        orderRow.put("createdAt", now);
        orderRow.put("updatedAt", now);
        mapper().insertOrder(orderRow);
        long orderId = orderRow.get("id") == null ? 0L : ((Number) orderRow.get("id")).longValue();
        ensureShareToken(orderId);
        mapper().insertLine(LINE, orderId, itemId, title == null ? "" : title, priceYuan, q);
        if (LoyaltyStore.anyEnabled()) {
            Map<String, Object> snap = null;
            try {
                ensureLoyaltyColumns();
                snap = LoyaltyStore.settleOnPlace(username, total, orderId, null);
                applyLoyaltySnapshot(orderId, snap);
            } catch (RuntimeException ex) {
                try {
                    double paid = snap != null ? toDouble(snap.get("payBalanceYuan")) : 0;
                    if (paid <= 1e-9) {
                        Map<String, Object> m = getOrder(orderId);
                        if (m != null) paid = toDouble(m.get("payBalanceYuan"));
                    }
                    if (paid > 1e-9) {
                        LoyaltyStore.refundOrderPay(username, orderId, paid);
                    }
                } catch (Exception ignored) {
                }
                try {
                    mapper().deleteLines(LINE, orderId);
                    mapper().deleteOrder(ORDER, orderId);
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
        Map<String, Object> m = getOrder(orderId);
        if (m == null) return;
        String cur = String.valueOf(m.getOrDefault("pickupCode", "")).trim();
        if (!cur.isBlank() && !"null".equalsIgnoreCase(cur)) return;
        String code = String.format("%04d", (int) (orderId % 10000));
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        mapper().ensurePickupCode(ORDER, orderId, code, now);
    }

    public static void markNoticeAgreed(long orderId) {
        if (!enabled || orderId <= 0 || !hasOrderColumn("notice_agreed")) return;
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        try {
            mapper().markNoticeAgreed(ORDER, orderId, now);
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
        mapper().updateOrderStatus(ORDER, orderId, "cancelled", now);
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
                mapper().insertLineKind(LINE, orderId, snackId, title, price, qty, "snack");
                add = round2(add + price * qty);
            }
            if (add > 1e-9) {
                Timestamp now = Timestamp.valueOf(LocalDateTime.now());
                mapper().bumpOrderTotal(ORDER, orderId, add, now);
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
        Map<String, Object> raw = mapper().selectOrderById(ORDER, id);
        if (raw == null) return null;
        Map<String, Object> m = shapeOrder(raw);
        m.put("lines", listLines(id));
        return m;
    }

    private static List<Map<String, Object>> listLines(long orderId) {
        List<Map<String, Object>> raw = mapper().selectLines(LINE, orderId);
        List<Map<String, Object>> out = new ArrayList<>();
        if (raw != null) {
            for (Map<String, Object> r : raw) {
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("id", r.get("id"));
                m.put("orderId", first(r, "orderId", "order_id"));
                m.put("itemId", first(r, "itemId", "item_id"));
                m.put("title", r.get("title"));
                double price = toDouble(first(r, "priceYuan", "price_yuan"));
                int qty = toInt(r.get("qty"));
                m.put("priceYuan", price);
                m.put("qty", qty);
                m.put("lineYuan", round2(price * qty));
                m.put("lineKind", str(first(r, "lineKind", "line_kind")));
                m.put("customText", str(first(r, "customText", "custom_text")));
                m.put("specChoice", str(first(r, "specChoice", "spec_choice")));
                m.put("attachUrl", str(first(r, "attachUrl", "attach_url")));
                m.put("drawTitle", str(first(r, "drawTitle", "draw_title")));
                if (BlindBoxStore.enabled() && !str(m.get("drawTitle")).isBlank()) {
                    m.put("pityText", BlindBoxStore.pityText(num(m.get("orderId")), num(m.get("itemId"))));
                }
                if (ArchiveStore.shopMarketplaceEnabled()
                        && !"snack".equals(String.valueOf(m.get("lineKind")))) {
                    try {
                        long itemId = num(first(r, "itemId", "item_id"));
                        Map<String, Object> item = ArchiveStore.getItem(itemId);
                        if (item != null && item.get("shopName") != null) {
                            m.put("shopName", item.get("shopName"));
                        }
                    } catch (Exception ignored) {
                    }
                }
                out.add(m);
            }
        }
        return out;
    }

    public static Map<String, Object> pageOrders(String username, String status, int page, int size) {
        requireEnabled();
        if (GroupBuyStore.enabled()) GroupBuyStore.sweep();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String u = username == null || username.isBlank() ? null : username;
        String st = status == null || status.isBlank() ? null : status;
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectOrders(ORDER, u, st);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw == null ? List.of() : raw);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : pi.getList()) {
            Map<String, Object> m = shapeOrder(r);
            m.put("lines", listLines(num(r.get("id"))));
            list.add(m);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", pi.getTotal());
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
        String st = status == null || status.isBlank() ? null : status;
        PageHelper.startPage(page, size);
        List<Map<String, Object>> raw = mapper().selectOrdersOwnedByMerchant(
                ORDER, LINE, ArchiveStore.itemTable(), owner, st);
        PageInfo<Map<String, Object>> pi = new PageInfo<>(raw == null ? List.of() : raw);
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map<String, Object> r : pi.getList()) {
            Map<String, Object> m = shapeOrder(r);
            m.put("lines", listLines(num(r.get("id"))));
            list.add(m);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", pi.getTotal());
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    public static boolean merchantOwnsOrder(String ownerUsername, long orderId) {
        requireEnabled();
        String owner = ownerUsername == null ? "" : ownerUsername.trim();
        if (owner.isBlank() || orderId <= 0) return false;
        return mapper().countMerchantOwnedLines(LINE, ArchiveStore.itemTable(), orderId, owner) > 0;
    }

    public static void completeByReservation(long reservationId) {
        advanceByReservation(reservationId, "complete");
    }

    public static void cancelByReservation(long reservationId) {
        advanceByReservation(reservationId, "cancel");
    }

    private static void advanceByReservation(long reservationId, String action) {
        if (!enabled || reservationId <= 0 || !hasOrderColumn("reservation_id")) return;
        List<Long> ids = mapper().selectIdsByReservation(ORDER, reservationId);
        if (ids == null) return;
        for (Long id : ids) {
            if (id == null) continue;
            String act = action;
            if ("cancel".equals(action)) {
                Map<String, Object> m = getOrder(id);
                if (m != null && "shipped".equals(String.valueOf(m.get("status")))) {
                    act = "complete";
                }
            }
            // 办结关联订单：须先确认再履约，再完成（与基线一致）
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
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("orderTable", ORDER);
                    row.put("id", orderId);
                    row.put("totalYuan", BigDecimal.valueOf(toDouble(m.get("totalYuan"))).setScale(2, RoundingMode.HALF_UP));
                    row.put("discountYuan", BigDecimal.valueOf(toDouble(m.get("discountYuan"))).setScale(2, RoundingMode.HALF_UP));
                    row.put("payBalanceYuan", BigDecimal.valueOf(pay).setScale(2, RoundingMode.HALF_UP));
                    row.put("updatedAt", Timestamp.valueOf(LocalDateTime.now()));
                    if (hasOrderColumn("coupon_code")) {
                        row.put("couponCode", String.valueOf(m.getOrDefault("couponCode", "")));
                        mapper().applyLoyaltyWithCoupon(row);
                    } else {
                        mapper().applyLoyaltyPlain(row);
                    }
                }
            }
        }
        Timestamp now = Timestamp.valueOf(LocalDateTime.now());
        int n = mapper().payPendingOrder(ORDER, orderId, "confirmed", channel, now);
        if (n <= 0) throw new IllegalStateException("支付失败，请刷新后重试");
        return getOrder(orderId);
    }

    public static Map<String, Object> advance(long orderId, String action) {
        return advance(orderId, action, null);
    }

    public static int cancelTimedOutPending(int minutes) {
        if (!enabled || minutes <= 0) return 0;
        List<Long> ids;
        try {
            ids = mapper().selectTimedOutPendingIds(ORDER, minutes);
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
            ids = mapper().selectTimedOutUnreceivedIds(ORDER, minutes);
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
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("orderTable", ORDER);
        row.put("id", orderId);
        row.put("updatedAt", now);
        if (!name.isBlank() && hasOrderColumn("receiver_name")) row.put("receiverName", name);
        if (!phone.isBlank() && hasOrderColumn("receiver_phone")) row.put("receiverPhone", phone);
        if (!addr.isBlank() && hasOrderColumn("address_line")) row.put("addressLine", addr);
        mapper().updateOrderAddress(row);
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
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("orderTable", ORDER);
            row.put("id", orderId);
            row.put("status", next);
            row.put("updatedAt", now);
            if (hasOrderColumn("tracking_no")) row.put("trackingNo", tracking);
            if (hasOrderColumn("pickup_code")) row.put("pickupCode", pickup);
            if (hasOrderColumn("shipped_at")) row.put("shippedAt", now);
            if (hasOrderColumn("partial_ship")) {
                boolean partial = opts != null && Boolean.TRUE.equals(opts.get("partialShip"));
                if (!partial) {
                    Object raw = opts == null ? null : opts.get("partialShip");
                    String s = raw == null ? "" : String.valueOf(raw).trim();
                    partial = "1".equals(s) || "true".equalsIgnoreCase(s);
                }
                row.put("partialShip", partial ? 1 : 0);
            }
            mapper().updateOrderShip(row);
            if ("shipped".equals(next)) ensurePickupCode(orderId);
        } else {
            mapper().updateOrderStatus(ORDER, orderId, next, now);
        }
        if (("signed".equals(next) || "completed".equals(next)) && hasOrderColumn("completed_at")) {
            Object already = m.get("completedAt");
            if (already == null || String.valueOf(already).isBlank() || "null".equals(String.valueOf(already))) {
                try {
                    mapper().markCompletedAtIfNull(ORDER, orderId, now);
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

    public static Map<String, Object> dashboard(String ownerUsername) {
        if (!enabled) return Map.of();
        Map<String, Object> m = new LinkedHashMap<>();
        String owner = ownerUsername == null ? "" : ownerUsername.trim();
        boolean byOwner = !owner.isBlank() && ArchiveStore.hasOwnerUsername();
        if (byOwner) {
            String item = ArchiveStore.itemTable();
            m.put("pendingOrders", mapper().countByStatusOwned(ORDER, LINE, item, "pending", owner));
            m.put("confirmedOrders", mapper().countByStatusOwned(ORDER, LINE, item, "confirmed", owner));
            m.put("shippedOrders", mapper().countByStatusOwned(ORDER, LINE, item, "shipped", owner));
            m.put("completedOrders", mapper().countByStatusOwned(ORDER, LINE, item, "completed", owner));
            try {
                m.put("salesTotalYuan", mapper().sumCompletedSalesOwned(ORDER, LINE, item, owner));
            } catch (Exception e) {
                m.put("salesTotalYuan", 0.0);
            }
            if (ArchiveStore.shopMarketplaceEnabled()) {
                try {
                    m.put("inTransitOrders", mapper().countByStatusOwned(ORDER, LINE, item, "in_transit", owner));
                    m.put("signedOrders", mapper().countByStatusOwned(ORDER, LINE, item, "signed", owner));
                } catch (Exception ignored) {
                    m.put("inTransitOrders", 0);
                    m.put("signedOrders", 0);
                }
            }
            return m;
        }
        m.put("pendingOrders", mapper().countByStatus(ORDER, "pending"));
        m.put("confirmedOrders", mapper().countByStatus(ORDER, "confirmed"));
        m.put("shippedOrders", mapper().countByStatus(ORDER, "shipped"));
        m.put("completedOrders", mapper().countByStatus(ORDER, "completed"));
        try {
            m.put("salesTotalYuan", mapper().sumCompletedSales(ORDER));
        } catch (Exception e) {
            m.put("salesTotalYuan", 0.0);
        }
        if (ArchiveStore.shopMarketplaceEnabled()) {
            try {
                m.put("inTransitOrders", mapper().countByStatus(ORDER, "in_transit"));
                m.put("signedOrders", mapper().countByStatus(ORDER, "signed"));
            } catch (Exception ignored) {
                m.put("inTransitOrders", 0);
                m.put("signedOrders", 0);
            }
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
        try {
            List<Map<String, Object>> status = mapper().selectStatusSeries(ORDER);
            out.put("statusSeries", status == null ? List.of() : status);
            List<Map<String, Object>> trend = mapper().selectTrendSeries(ORDER);
            out.put("trendSeries", trend == null ? List.of() : trend);
            List<Map<String, Object>> months = mapper().selectMonthSeries(ORDER);
            out.put("monthSeries", months == null ? List.of() : months);
            if (LINE != null && !LINE.isBlank()) {
                List<Map<String, Object>> hot = mapper().selectHotSeries(ORDER, LINE);
                out.put("hotItemSeries", hot == null ? List.of() : hot);
            }
            List<Map<String, Object>> daily = mapper().selectSalesDailySeries(ORDER);
            out.put("salesDailySeries", daily == null ? List.of() : daily);
            if (hasOrderColumn("refund_reason")) {
                List<Map<String, Object>> reasons = mapper().selectRefundReasonSeries(ORDER);
                out.put("refundReasonSeries", reasons == null ? List.of() : reasons);
            }
        } catch (Exception ignored) {
        }
        return out;
    }

    private static Map<String, Object> shapeOrder(Map<String, Object> raw) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", raw.get("id"));
        m.put("username", raw.get("username"));
        m.put("status", raw.get("status"));
        m.put("totalYuan", toDouble(first(raw, "totalYuan", "total_yuan")));
        m.put("remark", raw.get("remark"));
        m.put("receiverName", str(first(raw, "receiverName", "receiver_name")));
        m.put("receiverPhone", str(first(raw, "receiverPhone", "receiver_phone")));
        m.put("addressLine", str(first(raw, "addressLine", "address_line")));
        m.put("deliveryType", str(first(raw, "deliveryType", "delivery_type")));
        m.put("tasteNote", str(first(raw, "tasteNote", "taste_note")));
        m.put("trackingNo", str(first(raw, "trackingNo", "tracking_no")));
        m.put("pickupCode", str(first(raw, "pickupCode", "pickup_code")));
        m.put("tableNo", str(first(raw, "tableNo", "table_no")));
        m.put("utensilOpt", str(first(raw, "utensilOpt", "utensil_opt")));
        m.put("packOpt", str(first(raw, "packOpt", "pack_opt")));
        m.put("packagingFeeYuan", toDouble(first(raw, "packagingFeeYuan", "packaging_fee_yuan")));
        m.put("deliveryFeeYuan", toDouble(first(raw, "deliveryFeeYuan", "delivery_fee_yuan")));
        m.put("etaText", str(first(raw, "etaText", "eta_text")));
        m.put("mergeCode", str(first(raw, "mergeCode", "merge_code")));
        m.put("riderUsername", str(first(raw, "riderUsername", "rider_username")));
        m.put("riderClaimedAt", str(first(raw, "riderClaimedAt", "rider_claimed_at")));
        m.put("noticeAgreed", toInt(first(raw, "noticeAgreed", "notice_agreed")) > 0);
        m.put("shippedAt", fmt(first(raw, "shippedAt", "shipped_at")));
        long rid = num(first(raw, "reservationId", "reservation_id"));
        if (rid > 0) m.put("reservationId", rid);
        m.put("discountYuan", toDouble(first(raw, "discountYuan", "discount_yuan")));
        m.put("payBalanceYuan", toDouble(first(raw, "payBalanceYuan", "pay_balance_yuan")));
        m.put("pointsEarned", toInt(first(raw, "pointsEarned", "points_earned")));
        m.put("couponCode", str(first(raw, "couponCode", "coupon_code")));
        try {
            if (GroupBuyStore.enabled()) {
                long oid = num(first(raw, "id", "id"));
                Map<String, Object> gp = GroupBuyStore.progressForOrder(oid);
                if (gp != null) m.put("groupBuy", gp);
            }
        } catch (Exception ignored) {
        }
        m.put("refundStatus", str(first(raw, "refundStatus", "refund_status")));
        m.put("refundReason", str(first(raw, "refundReason", "refund_reason")));
        m.put("refundAt", fmt(first(raw, "refundAt", "refund_at")));
        m.put("refundType", str(first(raw, "refundType", "refund_type")));
        m.put("refundTrackingNo", str(first(raw, "refundTrackingNo", "refund_tracking_no")));
        m.put("refundRequestedAt", fmt(first(raw, "refundRequestedAt", "refund_requested_at")));
        m.put("completedAt", fmt(first(raw, "completedAt", "completed_at")));
        m.put("shareToken", str(first(raw, "shareToken", "share_token")));
        m.put("warrantyUntil", str(first(raw, "warrantyUntil", "warranty_until")));
        m.put("invoiceTitle", str(first(raw, "invoiceTitle", "invoice_title")));
        m.put("invoiceStatus", str(first(raw, "invoiceStatus", "invoice_status")));
        m.put("refundFeeYuan", toDouble(first(raw, "refundFeeYuan", "refund_fee_yuan")));
        m.put("partialShip", toInt(first(raw, "partialShip", "partial_ship")) > 0);
        m.put("receiveVerifiedAt", fmt(first(raw, "receiveVerifiedAt", "receive_verified_at")));
        m.put("payChannel", str(first(raw, "payChannel", "pay_channel")));
        m.put("fulfillMode", str(first(raw, "fulfillMode", "fulfill_mode")));
        m.put("deliveryOn", str(first(raw, "deliveryOn", "delivery_on")));
        m.put("slotLabel", str(first(raw, "slotLabel", "slot_label")));
        long windowSlot = num(first(raw, "slotId", "slot_id"));
        if (windowSlot > 0) m.put("slotId", windowSlot);
        m.put("priceRate", toDouble(first(raw, "priceRate", "price_rate")));
        m.put("depositYuan", toDouble(first(raw, "depositYuan", "deposit_yuan")));
        m.put("rentYuan", toDouble(first(raw, "rentYuan", "rent_yuan")));
        m.put("lateFeeYuan", toDouble(first(raw, "lateFeeYuan", "late_fee_yuan")));
        m.put("depositStatus", str(first(raw, "depositStatus", "deposit_status")));
        m.put("damageNote", str(first(raw, "damageNote", "damage_note")));
        m.put("damageDeductYuan", toDouble(first(raw, "damageDeductYuan", "damage_deduct_yuan")));
        m.put("createdAt", fmt(first(raw, "createdAt", "created_at")));
        m.put("updatedAt", fmt(first(raw, "updatedAt", "updated_at")));
        String un = str(raw.get("username"));
        if (!un.isBlank()) m.put("displayName", UserStore.displayName(un));
        return m;
    }

    private static Object first(Map<String, Object> raw, String... keys) {
        for (String k : keys) {
            if (raw.containsKey(k) && raw.get(k) != null) return raw.get(k);
        }
        return null;
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }

    private static long num(Object o) {
        if (o instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(o));
        } catch (Exception e) {
            return 0L;
        }
    }

    private static int toInt(Object o) {
        if (o instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(String.valueOf(o).trim());
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

    private static void requireOrderColIfPresent(String col, String label, boolean present) {
        if (!present) return;
        if (!hasOrderColumn(col)) {
            throw new IllegalStateException("系统未配置「" + label + "」字段，无法保存");
        }
    }

    private static boolean hasLineColumn(String col) {
        try {
            Integer n = schema().countColumn(LINE, col);
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
            long orderId, long itemId, String title, double price, int qty, Map<String, Object> extra) {
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
            mapper().insertLineCustom(
                    LINE, orderId, itemId, title, price, qty, customText, specChoice, attachUrl);
        } else {
            mapper().insertLine(LINE, orderId, itemId, title, price, qty);
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
            Integer n = schema().countColumn(ORDER, col);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
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
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("orderTable", ORDER);
            row.put("id", orderId);
            row.put("totalYuan", BigDecimal.valueOf(payable).setScale(2, RoundingMode.HALF_UP));
            row.put("discountYuan", BigDecimal.valueOf(discount).setScale(2, RoundingMode.HALF_UP));
            row.put("payBalanceYuan", BigDecimal.valueOf(payBal).setScale(2, RoundingMode.HALF_UP));
            row.put("updatedAt", Timestamp.valueOf(LocalDateTime.now()));
            if (hasOrderColumn("coupon_code")) {
                row.put("couponCode", coupon == null || "null".equals(coupon) ? "" : coupon);
                mapper().applyLoyaltyWithCoupon(row);
            } else {
                mapper().applyLoyaltyPlain(row);
            }
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("订单支付快照写入失败", e);
        }
    }

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
        mapper().requestRefund(ORDER, orderId, why, type, now, now);
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
        mapper().updateRefundTracking(ORDER, orderId, track, Timestamp.valueOf(LocalDateTime.now()));
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
            mapper().rejectRefund(ORDER, orderId, tip, now, now);
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
            mapper().approveExchangeRefund(ORDER, orderId, now, now);
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
        mapper().approveRefund(ORDER, orderId, now, now);
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
            String cur = mapper().selectShareToken(ORDER, orderId);
            if (cur != null && !cur.isBlank()) return;
        } catch (Exception ignored) {
            return;
        }
        String token = UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase(Locale.ROOT);
        mapper().updateShareTokenIfEmpty(ORDER, orderId, token);
    }

    public static Map<String, Object> getOrderByShareToken(String token) {
        requireEnabled();
        String t = token == null ? "" : token.trim().toUpperCase(Locale.ROOT);
        if (t.isBlank() || !hasOrderColumn("share_token")) {
            throw new IllegalArgumentException("口令无效");
        }
        Map<String, Object> raw = mapper().selectOrderByShareToken(ORDER, t);
        if (raw == null) throw new IllegalArgumentException("口令无效");
        Map<String, Object> m = shapeOrder(raw);
        long id = ((Number) m.get("id")).longValue();
        m.put("lines", listLines(id));
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
            List<Map<String, Object>> raw = mapper().selectShipNodes(orderId);
            List<Map<String, Object>> out = new ArrayList<>();
            if (raw == null) return out;
            for (Map<String, Object> r : raw) {
                Map<String, Object> n = new LinkedHashMap<>();
                n.put("at", fmt(first(r, "happened_at", "happenedAt")));
                n.put("title", str(r.get("title")));
                n.put("detail", str(r.get("detail")));
                out.add(n);
            }
            return out;
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
        mapper().insertShipNode(orderId, at, t, d);
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
            mapper().verifyReceive(ORDER, orderId, now, now);
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
        mapper().updateWarranty(ORDER, orderId, java.sql.Date.valueOf(day), Timestamp.valueOf(LocalDateTime.now()));
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
        mapper().updateInvoice(ORDER, orderId, tt, st, now);
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
        int n = mapper().claimRider(ORDER, orderId, rider, now, now);
        if (n <= 0) throw new IllegalStateException("接单失败，请刷新后重试");
        return getOrder(orderId);
    }

    public static int releaseTimedOutRiderClaims(int timeoutMinutes) {
        if (!enabled || timeoutMinutes <= 0) return 0;
        if (!hasOrderColumn("rider_username") || !hasOrderColumn("rider_claimed_at")) return 0;
        try {
            return mapper().releaseTimedOutRiderClaims(ORDER, timeoutMinutes);
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
        mapper().updateRefundFee(ORDER, orderId, fee, Timestamp.valueOf(LocalDateTime.now()));
        return getOrder(orderId);
    }

    private static boolean hasShipNodeTable() {
        try {
            Integer n = schema().countTable("order_ship_node");
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static void ensureOrderColumn(String col, String ddlType) {
        if (hasOrderColumn(col)) return;
        try {
            schema().executeDdl("ALTER TABLE " + ORDER + " ADD COLUMN " + col + " " + ddlType);
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
