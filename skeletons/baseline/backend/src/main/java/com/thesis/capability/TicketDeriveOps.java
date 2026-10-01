package com.thesis.capability;

import java.util.*;
import java.time.temporal.ChronoUnit;
import java.time.LocalDateTime;
import java.sql.Timestamp;

/**
 * TicketDeriveOps：TicketStore 纯业务逻辑拆分（零 DB 接触）。
 *
 * <p>三栈共用：bake 时由 baseline 提供；mybatis/jpa overlay 不含此类
 * （helper 不出现任何 JDBC/MyBatis token，故不参与 persistence 覆盖）。
 * 对 TicketStore 静态成员的引用一律使用显式限定名。
 */
final class TicketDeriveOps {

    private TicketDeriveOps() {}


    public static void bind(
            String ticketTable, boolean quota, boolean deadline, boolean multiTicket, boolean timeConflict) {
        if (ticketTable != null && !ticketTable.isBlank()) TicketStore.TICKET = ticketTable.trim();
        TicketStore.MODE = TicketStore.Mode.ARCHIVE;
        TicketStore.useQuota = quota;
        TicketStore.useDeadline = deadline;
        TicketStore.allowMultiTicket = multiTicket;
        TicketStore.checkTimeConflict = timeConflict;
        TicketStore.enabled = true;
        TicketStore.bindProgressDefault();
        TicketCopy.loadCopyFromResource();
        TicketStore.ensureProgressTable();
        TicketStore.ensureL1Columns();
        TicketStore.loadTicketColumnsFromResource();
    
    }


    public static void bindStandalone(String ticketTable, boolean deadline) {
        if (ticketTable != null && !ticketTable.isBlank()) TicketStore.TICKET = ticketTable.trim();
        TicketStore.MODE = TicketStore.Mode.STANDALONE;
        TicketStore.useQuota = false;
        TicketStore.useDeadline = deadline;
        TicketStore.enabled = true;
        TicketStore.bindProgressDefault();
        TicketCopy.loadCopyFromResource();
        TicketStore.ensureProgressTable();
        TicketStore.ensureL1Columns();
        TicketStore.loadTicketColumnsFromResource();
    
    }

    /** 等级 → 处理时限天数；levelSla 关时原样返回 fallback。 */

    static int levelSlaDays(Map<String, Object> m, int fallback) {
        if (!TicketStore.levelSla) return fallback;
        String lv = levelTextOf(m);
        if (lv.isBlank()) return fallback;
        if (lv.contains("高") || lv.contains("严重") || lv.contains("重大")
                || lv.contains("紧急") || lv.contains("一级") || lv.contains("红")) {
            return TicketStore.levelSlaHighDays;
        }
        if (lv.contains("中") || lv.contains("较重") || lv.contains("二级")
                || lv.contains("橙") || lv.contains("黄")) {
            return TicketStore.levelSlaMidDays;
        }
        if (lv.contains("低") || lv.contains("轻微") || lv.contains("一般")
                || lv.contains("三级") || lv.contains("蓝")) {
            return TicketStore.levelSlaLowDays;
        }
        return fallback;
    
    }

    /** 等级文本：单据行 level 优先，其次关联档案（event_case.level）。 */

    static String levelTextOf(Map<String, Object> m) {
        if (m == null) return "";
        String own = TicketSql.str(m.get("level"));
        if (!own.isBlank()) return own;
        long itemId = TicketSql.toLong(m.get("bookId"));
        if (itemId <= 0) return "";
        try {
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            return item == null ? "" : TicketSql.str(item.get("level"));
        } catch (Exception ignored) {
            return "";
        }
    
    }


    static double itemCredit(Map<String, Object> item) {
        if (item == null) return 0;
        Object c = item.get("credit");
        if (c instanceof Number n) return Math.max(0, n.doubleValue());
        try {
            return Math.max(0, Double.parseDouble(String.valueOf(c)));
        } catch (Exception e) {
            return 0;
        }
    
    }


    public static boolean profileRoomMatches(
            String building, String room, String author, String title, boolean looseBuilding) {
        String b = TicketStore.normRoomToken(building);
        String r = TicketStore.normRoomToken(room);
        String a = TicketStore.normRoomToken(author);
        String t = TicketStore.normRoomToken(title);
        if (b.isEmpty() || r.isEmpty()) return false;
        boolean buildingOk = looseBuilding
                ? (b.equals(a) || a.contains(b) || b.contains(a))
                : b.equals(a);
        if (!buildingOk) return false;
        return t.equals(r) || t.contains(r) || r.contains(t);
    
    }


    static LocalDateTime[] resolvePeriod(String periodStart, String periodEnd) {
        if (!TicketStore.pickDateRange) return null;
        if (periodStart == null || periodStart.isBlank() || periodEnd == null || periodEnd.isBlank()) {
            throw new IllegalStateException("请选择起止日期");
        }
        LocalDateTime start = TicketSql.parseDateTimeFlexible(periodStart.trim(), false);
        LocalDateTime end = TicketSql.parseDateTimeFlexible(periodEnd.trim(), true);
        if (!end.isAfter(start)) {
            throw new IllegalStateException("结束日期须晚于开始日期");
        }
        if (ChronoUnit.DAYS.between(start.toLocalDate(), end.toLocalDate()) > 90) {
            throw new IllegalStateException("起止跨度不能超过 90 天");
        }
        return new LocalDateTime[]{start, end};
    
    }


    static int resolveQty(Integer qty, int stock) {
        if (!TicketStore.allowQty) return 1;
        int n = qty == null ? 1 : qty;
        if (n < 1) throw new IllegalStateException("数量至少为 1");
        if (n > 99) throw new IllegalStateException("单次数量不能超过 99");
        if (stock > 0 && n > stock) throw new IllegalStateException(ArchiveStore.stockShortage(stock));
        return n;
    
    }


    static LocalDateTime resolveRequestedDue(String dueAt) {
        if (!TicketStore.pickLoanPeriod) return null;
        if (dueAt == null || dueAt.isBlank()) {
            throw new IllegalStateException("请选择到期日期");
        }
        LocalDateTime due = TicketSql.parseDateTimeFlexible(dueAt.trim(), true);
        LocalDateTime now = LocalDateTime.now();
        if (!due.isAfter(now)) {
            throw new IllegalStateException("到期日期须晚于当前时间");
        }
        if (due.isAfter(now.plusDays(90))) {
            throw new IllegalStateException("到期日期不能超过 90 天");
        }
        return due;
    
    }


    static int rowQty(Map<String, Object> m) {
        Object q = m.get("qty");
        if (q == null) return 1;
        String s = String.valueOf(q).trim();
        if (s.isBlank() || "null".equalsIgnoreCase(s)) return 1;
        if (q instanceof Number n) return Math.max(1, n.intValue());
        try {
            return Math.max(1, Integer.parseInt(s));
        } catch (Exception e) {
            throw new IllegalStateException("单据数量无效", e);
        }
    
    }

    /** C-05：档案主人确认/拒绝志愿；通过时复用 approve 扣库存。 */

    public static Map<String, Object> peerRespond(long ticketId, String username, boolean pass, String remark) {
        if (!TicketStore.peerAccept) throw new IllegalStateException("当前未开启互选确认");
        if (TicketStore.MODE != TicketStore.Mode.ARCHIVE) throw new IllegalStateException("当前不支持互选确认");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!"pending".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅待确认志愿可操作");
        }
        long itemId = TicketSql.toLong(m.get("bookId"));
        if (itemId <= 0) itemId = TicketSql.toLong(m.get("itemId"));
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalStateException(TicketCopy.archiveNoun() + "不存在");
        String owner = TicketSql.str(item.get("ownerUsername"));
        if (owner.isBlank()) throw new IllegalStateException("档案未绑定确认人");
        if (!owner.equals(username == null ? "" : username.trim())) {
            throw new IllegalStateException("仅档案确认人可操作");
        }
        String note = remark == null ? "" : remark.trim();
        if (!pass && note.isBlank()) {
            throw new IllegalStateException("请填写婉拒原因");
        }
        Map<String, Object> out = TicketStore.approve(ticketId, pass, note, username, true);
        appendProgress(
                ticketId,
                pass ? "peer_accept" : "peer_reject",
                username,
                pass ? "对方确认" : (note.isBlank() ? "对方婉拒" : note));
        return out;
    
    }

    /** 当前用户是否为某单据关联档案的确认人 */

    public static boolean isPeerOwnerOf(long ticketId, String username) {
        if (!TicketStore.peerAccept || TicketStore.MODE != TicketStore.Mode.ARCHIVE || username == null || username.isBlank()) return false;
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) return false;
        long itemId = TicketSql.toLong(m.get("bookId"));
        if (itemId <= 0) itemId = TicketSql.toLong(m.get("itemId"));
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) return false;
        return username.trim().equals(TicketSql.str(item.get("ownerUsername")));
    
    }


    static void appendProgress(long ticketId, String status, String operator, String remark) {
        if (ticketId <= 0) return;
        if (TicketStore.PROGRESS == null || TicketStore.PROGRESS.isBlank()) return;
        TicketStore.ensureProgressTable();
        try {
            TicketProgressOps.insertProgressRow(
                    ticketId,
                    status,
                    operator,
                    remark,
                    Timestamp.valueOf(LocalDateTime.now()));
        } catch (Exception e) {
            throw new IllegalStateException("审核进度写入失败", e);
        }
    
    }


    public static Map<String, Object> claimHold(long ticketId, String username) {
        if (!TicketStore.allowBookHold) throw new IllegalStateException("当前未开启图书预约");
        TicketStore.expireBookHolds();
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (username == null || username.isBlank()
                || !username.equals(String.valueOf(m.get("username")))) {
            throw new IllegalStateException("只能确认本人的预约");
        }
        if (!"hold_ready".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅待取书状态可确认借阅");
        }
        return TicketStore.finalizeHoldReadyApprove(ticketId, m, "用户确认借阅", username, "", false);
    
    }


    public static Map<String, Object> markOverdue(long ticketId) {
        if (!TicketStore.useDeadline) throw new IllegalStateException("当前不支持到期催办");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!"approved".equals(m.get("status")) && !"overdue".equals(m.get("status"))) {
            throw new IllegalStateException("仅进行中/逾期可标记");
        }
        m.put("status", "overdue");
        TicketStatusOps.applyFineAndRemind(m, false);
        TicketStatusOps.persistFine(m);
        TicketStatusOps.markEverOverdue(m);
        return get(ticketId);
    
    }

    /** 终态：全体子管可读（不按处理人隔离） */

    public static boolean isHistoryStatus(String status) {
        return "returned".equals(status)
                || "rejected".equals(status)
                || "cancelled".equals(status)
                || "noshow".equals(status)
                || "lost".equals(status)
                || "compensated".equals(status);
    
    }


    public static Map<String, Object> get(long id) {
        Map<String, Object> m = TicketRowMaps.load(id);
        if (m == null) return null;
        TicketStatusOps.touchTicketStatus(m);
        return TicketStatusOps.enrich(TicketRowMaps.load(id));
    
    }

    /** ASSET：确认领用单已关联申购单号（浅衔接，不跨库）。 */

    public static Map<String, Object> confirmProcureTransfer(long ticketId, String operator) {
        if (!TicketStore.allowProcureRef) throw new IllegalStateException("未开通申购单号衔接");
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!TicketStore.hasColumn("procure_ref_no")) throw new IllegalStateException("系统未配置申购单号字段");
        String ref = TicketSql.str(m.get("procureRefNo")).trim();
        if (ref.isBlank()) throw new IllegalStateException("请先填写申购单号");
        String op = operator == null ? "" : operator.trim();
        appendProgress(ticketId, String.valueOf(m.get("status")), op, "已确认申购单号「" + ref + "」转入领用");
        return get(ticketId);
    
    }


    public static boolean runMainPathSelfCheck() {
        try {
            if (TicketStore.MODE == TicketStore.Mode.STANDALONE) {
                String user = "gate_" + System.currentTimeMillis();
                Long typeId = null;
                Long roomId = null;
                if (TicketLookupStore.enabled()) {
                    List<Map<String, Object>> types = TicketLookupStore.listTypes();
                    List<Map<String, Object>> units = TicketLookupStore.listUnits(null);
                    if (types.isEmpty() || units.isEmpty()) return false;
                    typeId = TicketSql.toLong(types.get(0).get("id"));
                    roomId = TicketSql.toLong(units.get(0).get("id"));
                }
                Map<String, Object> br = TicketStore.applyStandalone(user, "门禁自检报修", "测试地点", "gate", typeId, roomId);
                long bid = TicketSql.toLong(br.get("id"));
                TicketStore.approve(bid, true, "gate");
                TicketStore.complete(bid);
                Map<String, Object> done = get(bid);
                return done != null && "returned".equals(done.get("status"));
            }
            Map<String, Object> page = ArchiveStore.pageItems(null, null, 1, 1);
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> list = (List<Map<String, Object>>) page.get("list");
            if (list == null || list.isEmpty()) return false;
            long itemId = TicketSql.toLong(list.get(0).get("id"));
            String user = "gate_" + System.currentTimeMillis();
            Map<String, Object> br = TicketStore.apply(user, itemId);
            long bid = TicketSql.toLong(br.get("id"));
            TicketStore.approve(bid, true, "gate");
            TicketStore.complete(bid);
            Map<String, Object> done = get(bid);
            return done != null && "returned".equals(done.get("status"));
        } catch (Exception e) {
            return false;
        }
    
    }
}
