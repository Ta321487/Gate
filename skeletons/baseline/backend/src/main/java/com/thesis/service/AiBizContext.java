package com.thesis.service;

import com.thesis.capability.ArchiveStore;
import com.thesis.capability.CouponStore;
import com.thesis.capability.FavoriteStore;
import com.thesis.capability.LoyaltyStore;
import com.thesis.capability.OrderStore;
import com.thesis.capability.RecommendStore;
import com.thesis.capability.SlotStore;
import com.thesis.capability.TicketLookupStore;
import com.thesis.capability.TicketStore;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * AI 助手只读业务摘录：意图词 + {@code Store.enabled()} 才调用现有 API。
 * 禁止另写 SQL / 下单改状态；未开能力自动跳过（其它域不是「没写死就废」）。
 */
public final class AiBizContext {

    private static final int LIMIT = 5;

    private AiBizContext() {}

    /**
     * @return 供提示词/无 Key 直出的业务摘录；无匹配或能力未开则 null
     */
    public static String buildExcerpt(String username, String question, String categoryHint) {
        String q = question == null ? "" : question.trim();
        if (q.isBlank()) return null;

        String hint = categoryHint == null ? "" : categoryHint.trim();
        StringBuilder sb = new StringBuilder();
        try {
            // —— 货架 / 文库 ——
            if (wantCatalog(q) || !hint.isBlank()) {
                if (DoclibStore.enabled() && DoclibStore.ready()
                        && containsAny(q, "资料", "文件", "下载", "课件", "制度", "文库", "模板")) {
                    appendDoclib(sb);
                } else {
                    appendCatalog(sb, q, hint);
                }
            }
            // —— 交易 ——
            if (wantOrder(q) && OrderStore.enabled()) {
                appendCart(sb, username);
                appendOrders(sb, username);
            }
            // —— 借阅 / 报修 / 请假等办理票 ——
            if (wantTicket(q) && TicketStore.enabled()) {
                appendTicketTypes(sb);
                appendTickets(sb, username);
            }
            // —— 预约时段 ——
            if (wantReserve(q) && SlotStore.enabled()) {
                appendReservations(sb, username);
            }
            // —— 公告（基线常驻） ——
            if (wantNotice(q)) {
                appendNotices(sb);
            }
            // —— 规则推荐 / 收藏 ——
            if (wantRecommend(q)) {
                appendRecommend(sb, username);
            }
            if (wantFavorite(q) && FavoriteStore.enabled()) {
                appendFavorites(sb, username);
            }
            // —— 积分 / 券 ——
            if (wantLoyalty(q) && LoyaltyStore.anyEnabled()) {
                appendLoyalty(sb, username);
            }
            if (wantCoupon(q) && CouponStore.enabled()) {
                appendCoupons(sb, username);
            }
            // —— 考试 / 问卷 / 投票 ——
            if (wantExam(q) && ExamStore.enabled()) {
                appendExam(sb, username);
            }
            if (wantSurvey(q) && SurveyStore.enabled()) {
                appendSurvey(sb, username);
            }
            if (wantVote(q) && VoteStore.enabled()) {
                appendVote(sb, username);
            }
            // —— 选座 / 时间银行 / 电子签 ——
            if (wantSeat(q) && SeatStore.enabled()) {
                appendSeat(sb);
            }
            if (wantTimebank(q) && TimebankStore.enabled()) {
                appendTimebank(sb, username);
            }
            if (wantEsign(q) && ESignStore.enabled()) {
                appendEsign(sb, username);
            }
        } catch (Exception ignored) {
            // 域未绑表时静默，回落 FAQ
        }
        String out = sb.toString().trim();
        return out.isBlank() ? null : out;
    }

    private static boolean wantCatalog(String q) {
        return containsAny(q,
                "有什么", "有哪些", "库存", "分类", "商品", "图书", "菜品", "套餐", "面食", "饮品",
                "选购", "买", "借什么", "在馆", "资料", "文件", "下载", "课件", "制度", "热销", "配件",
                "水果", "蔬菜", "粮油", "教材", "数码", "条目", "上架");
    }

    private static boolean wantOrder(String q) {
        return containsAny(q, "订单", "物流", "发货", "收货", "购物车", "我买", "下单了", "待支付", "退款");
    }

    private static boolean wantTicket(String q) {
        return containsAny(q,
                "报修", "工单", "进度", "借阅", "我的借", "逾期", "续借", "归还", "请假", "销假", "审批", "假条");
    }

    private static boolean wantReserve(String q) {
        return containsAny(q, "预约", "我的预约", "时段", "订场", "车位", "会议室");
    }

    private static boolean wantNotice(String q) {
        return containsAny(q, "公告", "通知", "须知", "最新消息");
    }

    private static boolean wantRecommend(String q) {
        return containsAny(q, "猜你喜欢", "推荐", "相关推荐");
    }

    private static boolean wantFavorite(String q) {
        return containsAny(q, "收藏", "我的收藏");
    }

    private static boolean wantLoyalty(String q) {
        return containsAny(q, "积分", "余额", "钱包", "会员等级", "我的积分");
    }

    private static boolean wantCoupon(String q) {
        return containsAny(q, "优惠券", "代金券", "我的券", "领券");
    }

    private static boolean wantExam(String q) {
        return containsAny(q, "考试", "试卷", "答题", "成绩", "错题", "我的考试");
    }

    private static boolean wantSurvey(String q) {
        return containsAny(q, "问卷", "调研", "填写问卷");
    }

    private static boolean wantVote(String q) {
        return containsAny(q, "投票", "选举", "评选");
    }

    private static boolean wantSeat(String q) {
        return containsAny(q, "选座", "场次", "影票", "座位");
    }

    private static boolean wantTimebank(String q) {
        return containsAny(q, "时间银行", "志愿时", "服务时长");
    }

    private static boolean wantEsign(String q) {
        return containsAny(q, "电子签", "签章", "签署", "我的签署");
    }

    private static boolean containsAny(String q, String... keys) {
        String s = q.toLowerCase(Locale.ROOT);
        for (String k : keys) {
            if (k != null && !k.isBlank() && s.contains(k.toLowerCase(Locale.ROOT))) return true;
        }
        return false;
    }

    private static void appendCatalog(StringBuilder sb, String question, String categoryHint) {
        List<Map<String, Object>> cats;
        try {
            cats = ArchiveStore.listCategories();
        } catch (Exception e) {
            return;
        }
        if (cats == null || cats.isEmpty()) return;

        sb.append("【分类】");
        List<String> names = new ArrayList<>();
        for (Map<String, Object> c : cats) {
            String n = str(c.get("name"));
            if (!n.isBlank()) names.add(n);
        }
        sb.append(String.join("、", names)).append('\n');

        Long catId = resolveCategoryId(cats, categoryHint, question);
        String kw = extractKeyword(question, names);
        Map<String, Object> page;
        try {
            page = ArchiveStore.pageItems(kw, catId, null, false, 1, LIMIT, true);
        } catch (Exception e) {
            try {
                page = ArchiveStore.pageItems(kw, catId, 1, LIMIT);
            } catch (Exception e2) {
                return;
            }
        }
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> list = page == null ? null : (List<Map<String, Object>>) page.get("list");
        if (list == null || list.isEmpty()) {
            sb.append("【条目】当前条件下暂无在架记录。\n");
            return;
        }
        sb.append("【条目】\n");
        for (Map<String, Object> it : list) {
            sb.append("- ")
                    .append(str(it.get("title")))
                    .append("｜分类 ").append(str(it.get("categoryName")))
                    .append("｜").append(ArchiveStore.stockLabel()).append(' ').append(str(it.get("stock")))
                    .append("｜状态 ").append(str(it.get("status")))
                    .append('\n');
        }
    }

    private static Long resolveCategoryId(List<Map<String, Object>> cats, String hint, String question) {
        String probe = (hint == null ? "" : hint) + " " + (question == null ? "" : question);
        for (Map<String, Object> c : cats) {
            String n = str(c.get("name"));
            if (!n.isBlank() && probe.contains(n)) {
                Object id = c.get("id");
                if (id instanceof Number num) return num.longValue();
            }
        }
        return null;
    }

    private static String extractKeyword(String question, List<String> catNames) {
        if (question == null || question.isBlank()) return "";
        String q = question.trim();
        for (String n : catNames) {
            if (n != null && q.contains(n)) q = q.replace(n, " ");
        }
        for (String noise : List.of(
                "有什么", "有哪些", "推荐", "库存", "分类", "商品", "图书", "怎么", "如何", "一下",
                "查询", "看看", "介绍", "选购", "买", "借", "的")) {
            q = q.replace(noise, " ");
        }
        q = q.replaceAll("[\\s，,。？?！!、]+", " ").trim();
        if (q.length() < 2) return "";
        return q.length() > 32 ? q.substring(0, 32) : q;
    }

    private static void appendCart(StringBuilder sb, String username) {
        if (username == null || username.isBlank()) return;
        List<Map<String, Object>> cart = OrderStore.listCart(username);
        sb.append("【购物车】");
        if (cart == null || cart.isEmpty()) {
            sb.append("空\n");
            return;
        }
        sb.append('\n');
        int n = 0;
        for (Map<String, Object> row : cart) {
            if (n++ >= LIMIT) break;
            sb.append("- ")
                    .append(str(row.get("title")))
                    .append(" × ").append(str(row.get("qty")))
                    .append("｜小计 ").append(str(row.get("lineYuan")))
                    .append('\n');
        }
    }

    private static void appendOrders(StringBuilder sb, String username) {
        if (username == null || username.isBlank()) return;
        Map<String, Object> page = OrderStore.pageOrders(username, null, 1, LIMIT);
        appendNamedList(sb, "【我的订单】", page, row ->
                "- #" + str(row.get("id"))
                        + "｜状态 " + str(row.get("status"))
                        + "｜金额 " + str(row.get("totalYuan")));
    }

    private static void appendTicketTypes(StringBuilder sb) {
        try {
            List<Map<String, Object>> types = TicketLookupStore.listTypes();
            if (types == null || types.isEmpty()) return;
            List<String> names = new ArrayList<>();
            for (Map<String, Object> t : types) {
                String n = str(t.get("name"));
                if (!n.isBlank()) names.add(n);
            }
            if (!names.isEmpty()) sb.append("【业务类型】").append(String.join("、", names)).append('\n');
        } catch (Exception ignored) {
        }
    }

    private static void appendTickets(StringBuilder sb, String username) {
        if (username == null || username.isBlank()) return;
        Map<String, Object> page = TicketStore.page(username, null, 1, LIMIT);
        appendNamedList(sb, "【我的办理】", page, row ->
                "- #" + str(row.get("id"))
                        + " " + str(row.get("title"))
                        + "｜状态 " + str(row.get("status")));
    }

    private static void appendReservations(StringBuilder sb, String username) {
        if (username == null || username.isBlank()) return;
        Map<String, Object> page = SlotStore.pageReservations(username, null, 1, LIMIT);
        appendNamedList(sb, "【我的预约】", page, row ->
                "- #" + str(row.get("id"))
                        + "｜状态 " + str(row.get("status"))
                        + "｜" + str(row.get("startAt")) + "~" + str(row.get("endAt")));
    }

    private static void appendNotices(StringBuilder sb) {
        Map<String, Object> page = NoticeStore.page(1, LIMIT);
        appendNamedList(sb, "【公告】", page, row ->
                "- " + str(row.get("title")));
    }

    private static void appendRecommend(StringBuilder sb, String username) {
        Map<String, Object> rec = RecommendStore.recommend(username, LIMIT);
        if (rec == null) return;
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> list = (List<Map<String, Object>>) rec.get("list");
        sb.append("【推荐】模式 ").append(str(rec.get("mode")));
        if (list == null || list.isEmpty()) {
            sb.append("｜暂无\n");
            return;
        }
        sb.append('\n');
        for (Map<String, Object> it : list) {
            sb.append("- ")
                    .append(str(it.get("title")))
                    .append('\n');
        }
    }

    private static void appendFavorites(StringBuilder sb, String username) {
        if (username == null || username.isBlank()) return;
        Map<String, Object> page = FavoriteStore.page(username, 1, LIMIT);
        appendNamedList(sb, "【我的收藏】", page, row ->
                "- " + str(row.get("title")));
    }

    private static void appendLoyalty(StringBuilder sb, String username) {
        Map<String, Object> acc = LoyaltyStore.getAccount(username);
        if (acc == null) return;
        sb.append("【账户】");
        if (LoyaltyStore.isPointsEnabled()) sb.append("积分 ").append(str(acc.get("points"))).append(' ');
        if (LoyaltyStore.isWalletEnabled()) sb.append("余额 ").append(str(acc.get("balanceYuan"))).append(' ');
        String tier = str(acc.get("memberTierLabel"));
        if (tier.isBlank()) tier = str(acc.get("memberTier"));
        if (!tier.isBlank()) sb.append("会员 ").append(tier).append(' ');
        sb.append('\n');
        if (username != null && !username.isBlank() && LoyaltyStore.isPointsEnabled()) {
            try {
                List<Map<String, Object>> ledger = LoyaltyStore.listLedger(username, LIMIT);
                if (ledger != null && !ledger.isEmpty()) {
                    sb.append("【积分流水】\n");
                    for (Map<String, Object> row : ledger) {
                        sb.append("- ").append(str(row.get("remark")))
                                .append("｜").append(str(row.get("delta")))
                                .append('\n');
                    }
                }
            } catch (Exception ignored) {
            }
        }
    }

    private static void appendCoupons(StringBuilder sb, String username) {
        if (username == null || username.isBlank()) return;
        Map<String, Object> page = CouponStore.pageMine(username, null, 1, LIMIT);
        appendNamedList(sb, "【我的优惠券】", page, row ->
                "- " + str(row.get("label"))
                        + "｜" + str(row.get("code"))
                        + "｜状态 " + str(row.get("status")));
    }

    private static void appendExam(StringBuilder sb, String username) {
        try {
            List<Map<String, Object>> papers = ExamStore.listPublishedPapers();
            sb.append("【可考试卷】");
            if (papers == null || papers.isEmpty()) {
                sb.append("暂无\n");
            } else {
                sb.append('\n');
                int n = 0;
                for (Map<String, Object> p : papers) {
                    if (n++ >= LIMIT) break;
                    sb.append("- ").append(str(p.get("title"))).append('\n');
                }
            }
        } catch (Exception ignored) {
        }
        if (username != null && !username.isBlank()) {
            try {
                Map<String, Object> page = ExamStore.pageMyAttempts(username, 1, LIMIT);
                appendNamedList(sb, "【我的答题】", page, row ->
                        "- " + str(row.get("paperTitle"))
                                + "｜分数 " + str(row.get("score")));
            } catch (Exception ignored) {
            }
        }
    }

    private static void appendSurvey(StringBuilder sb, String username) {
        try {
            List<Map<String, Object>> forms = SurveyStore.listOpenForms();
            sb.append("【开放问卷】");
            if (forms == null || forms.isEmpty()) {
                sb.append("暂无\n");
            } else {
                sb.append('\n');
                int n = 0;
                for (Map<String, Object> f : forms) {
                    if (n++ >= LIMIT) break;
                    sb.append("- ").append(str(f.get("title"))).append('\n');
                }
            }
        } catch (Exception ignored) {
        }
        if (username != null && !username.isBlank()) {
            try {
                Map<String, Object> page = SurveyStore.pageMine(username, 1, LIMIT);
                appendNamedList(sb, "【我的问卷】", page, row ->
                        "- " + str(row.get("formTitle")) + "｜" + str(row.get("status")));
            } catch (Exception ignored) {
            }
        }
    }

    private static void appendVote(StringBuilder sb, String username) {
        try {
            List<Map<String, Object>> camps = VoteStore.listOpenCampaigns();
            sb.append("【开放投票】");
            if (camps == null || camps.isEmpty()) {
                sb.append("暂无\n");
            } else {
                sb.append('\n');
                int n = 0;
                for (Map<String, Object> c : camps) {
                    if (n++ >= LIMIT) break;
                    sb.append("- ").append(str(c.get("title"))).append('\n');
                }
            }
        } catch (Exception ignored) {
        }
        if (username != null && !username.isBlank()) {
            try {
                Map<String, Object> page = VoteStore.pageMine(username, 1, LIMIT);
                appendNamedList(sb, "【我的投票】", page, row ->
                        "- " + str(row.get("campaignTitle")));
            } catch (Exception ignored) {
            }
        }
    }

    private static void appendSeat(StringBuilder sb) {
        try {
            List<Map<String, Object>> shows = SeatStore.listOpenShows();
            sb.append("【开放场次】");
            if (shows == null || shows.isEmpty()) {
                sb.append("暂无\n");
                return;
            }
            sb.append('\n');
            int n = 0;
            for (Map<String, Object> s : shows) {
                if (n++ >= LIMIT) break;
                sb.append("- ").append(str(s.get("title"))).append('\n');
            }
        } catch (Exception ignored) {
        }
    }

    private static void appendTimebank(StringBuilder sb, String username) {
        try {
            List<Map<String, Object>> services = TimebankStore.listOpenServices();
            sb.append("【开放服务】");
            if (services == null || services.isEmpty()) {
                sb.append("暂无\n");
            } else {
                sb.append('\n');
                int n = 0;
                for (Map<String, Object> s : services) {
                    if (n++ >= LIMIT) break;
                    sb.append("- ").append(str(s.get("title"))).append('\n');
                }
            }
        } catch (Exception ignored) {
        }
        if (username != null && !username.isBlank()) {
            try {
                Map<String, Object> page = TimebankStore.pageLedgerMine(username, 1, LIMIT);
                appendNamedList(sb, "【我的时长流水】", page, row ->
                        "- " + str(row.get("remark")) + "｜" + str(row.get("delta")));
            } catch (Exception ignored) {
            }
        }
    }

    private static void appendEsign(StringBuilder sb, String username) {
        if (username == null || username.isBlank()) return;
        try {
            Map<String, Object> page = ESignStore.pageMine(username, 1, LIMIT);
            appendNamedList(sb, "【我的签署】", page, row ->
                    "- " + str(row.get("title")) + "｜状态 " + str(row.get("status")));
        } catch (Exception ignored) {
        }
    }

    private static void appendDoclib(StringBuilder sb) {
        List<Map<String, Object>> items = DoclibStore.listOpenItems(false);
        sb.append("【文库资料】");
        if (items == null || items.isEmpty()) {
            sb.append("暂无开放条目\n");
            return;
        }
        sb.append('\n');
        int n = 0;
        for (Map<String, Object> it : items) {
            if (n++ >= LIMIT) break;
            sb.append("- ")
                    .append(str(it.get("title")))
                    .append("｜权限 ").append(str(it.get("accessLevel")))
                    .append('\n');
        }
    }

    private interface LineFn {
        String line(Map<String, Object> row);
    }

    private static void appendNamedList(
            StringBuilder sb, String title, Map<String, Object> page, LineFn fn) {
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> list = page == null ? null : (List<Map<String, Object>>) page.get("list");
        sb.append(title);
        if (list == null || list.isEmpty()) {
            sb.append("暂无\n");
            return;
        }
        sb.append('\n');
        int n = 0;
        for (Map<String, Object> row : list) {
            if (n++ >= LIMIT) break;
            sb.append(fn.line(row)).append('\n');
        }
    }

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o).trim();
    }
}
