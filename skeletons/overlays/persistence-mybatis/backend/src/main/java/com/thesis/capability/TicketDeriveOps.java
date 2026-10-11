package com.thesis.capability;


import com.thesis.config.MbSql;
import com.thesis.config.MybatisSupport;
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
        // I-05：车主确认后锁座
        if (pass && TicketStore.hasColumn("seat_locked")) {
            try {
                MybatisSupport.db().update(
                        "UPDATE " + TicketStore.TICKET + " SET seat_locked=1 WHERE id=?", ticketId);
                out = get(ticketId);
            } catch (Exception ignored) {
            }
        }
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

    /** I-03：管理端调剂（非档案主人）审核后额外留痕。 */
    static void maybeAppendAdminAdjust(long ticketId, String operator, boolean pass, String remark) {
        if (!TicketStore.peerAccept || ticketId <= 0) return;
        String op = operator == null ? "" : operator.trim();
        if (op.isBlank() || "system".equals(op)) return;
        if (isPeerOwnerOf(ticketId, op)) return;
        String note = remark == null ? "" : remark.trim();
        appendProgress(
                ticketId,
                "admin_adjust",
                op,
                pass ? (note.isBlank() ? "调剂确认" : note) : (note.isBlank() ? "调剂驳回" : note));
    }

    /** I-03：档案是否仍在盲选窗口（有截止且未过）。 */
    static boolean isBlindPhaseActive(Map<String, Object> item) {
        if (!TicketStore.blindPhaseUntilDeadline || !TicketStore.peerAccept) return false;
        if (item == null || !ArchiveStore.hasApplyDeadline()) return false;
        Object raw = item.get("applyDeadlineAt");
        if (raw == null || String.valueOf(raw).isBlank()) return false;
        try {
            String s = String.valueOf(raw).trim().replace('T', ' ');
            LocalDateTime deadline;
            if (s.length() == 10) {
                deadline = LocalDateTime.parse(s + "T23:59:59");
            } else {
                deadline = LocalDateTime.parse(s.substring(0, Math.min(19, s.length())), TicketSql.FMT);
            }
            return LocalDateTime.now().isBefore(deadline) || LocalDateTime.now().isEqual(deadline);
        } catch (Exception e) {
            return false;
        }
    }

    /** I-03：盲选脱敏 peer-inbox 行。 */
    static void applyBlindRedaction(List<Map<String, Object>> list) {
        if (list == null || list.isEmpty() || !TicketStore.blindPhaseUntilDeadline) return;
        for (Map<String, Object> row : list) {
            if (row == null) continue;
            long itemId = TicketSql.toLong(row.get("bookId"));
            if (itemId <= 0) itemId = TicketSql.toLong(row.get("itemId"));
            Map<String, Object> item = itemId > 0 ? ArchiveStore.getItemRaw(itemId) : null;
            if (!isBlindPhaseActive(item)) continue;
            row.put("username", "");
            row.put("displayUsername", "盲选申请人");
            row.put("remark", "");
            row.put("blindMasked", true);
        }
    }

    /** I-03：截止前修改志愿说明/类型。 */
    public static Map<String, Object> editWishBeforeDeadline(
            long ticketId, String username, String remark, String contactChannel) {
        if (!TicketStore.peerAccept || !TicketStore.allowWishEditBeforeDeadline) {
            throw new IllegalStateException("当前不可修改志愿");
        }
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (username == null || username.isBlank()
                || !username.equals(String.valueOf(m.get("username")))) {
            throw new IllegalStateException("只能修改自己的志愿");
        }
        if (!"pending".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅待确认志愿可修改");
        }
        long itemId = TicketSql.toLong(m.get("bookId"));
        if (itemId <= 0) itemId = TicketSql.toLong(m.get("itemId"));
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalStateException(TicketCopy.archiveNoun() + "不存在");
        TicketAsserts.assertApplyDeadline(item);
        if (remark != null) {
            String note = remark.trim();
            com.thesis.service.SensitiveWordGate.assertClean(note);
            if (note.length() > 255) note = note.substring(0, 255);
            MybatisSupport.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET remark=? WHERE id=?", note, ticketId);
        }
        if (contactChannel != null && TicketStore.hasColumn("contact_channel")) {
            String ch = contactChannel.trim();
            if (ch.length() > 64) ch = ch.substring(0, 64);
            TicketAsserts.assertAdjustWishCap(username, ch, ticketId);
            MybatisSupport.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET contact_channel=? WHERE id=?", ch, ticketId);
        }
        appendProgress(ticketId, "wish_edit", username, "截止前修改志愿");
        return get(ticketId);
    }

    /** I-03：待确认超时自动婉拒。 */
    public static int autoRejectStalePeerPending() {
        if (!TicketStore.peerAccept || !TicketStore.allowPeerTimeoutReject) return 0;
        if (TicketStore.peerTimeoutRejectHours <= 0 || !TicketStore.enabled) return 0;
        List<Long> ids;
        try {
            ids = MybatisSupport.db().query(
                    "SELECT id FROM " + TicketStore.TICKET
                            + " WHERE status='pending'"
                            + " AND created_at <= DATE_SUB(NOW(), INTERVAL ? HOUR) LIMIT 50",
                    rs -> {
                        List<Long> list = new ArrayList<>();
                        while (rs.next()) list.add(rs.getLong("id"));
                        return list;
                    },
                    TicketStore.peerTimeoutRejectHours);
        } catch (Exception e) {
            return 0;
        }
        int n = 0;
        for (Long id : ids) {
            if (id == null || id <= 0) continue;
            try {
                Map<String, Object> m = TicketRowMaps.load(id);
                if (m == null || !"pending".equals(String.valueOf(m.get("status")))) continue;
                TicketStore.approve(id, false, "确认超时自动婉拒", "system", true);
                appendProgress(id, "peer_timeout_reject", "system", "确认超时自动婉拒");
                n++;
            } catch (Exception ignored) {
            }
        }
        return n;
    }

    /** I-03：互选结果公示（已通过名单，用户名脱敏）。 */
    public static List<Map<String, Object>> mutualMatchResult(Long itemId) {
        if (!TicketStore.peerAccept || TicketStore.MODE != TicketStore.Mode.ARCHIVE) return List.of();
        StringBuilder sql = new StringBuilder(
                "SELECT id, username, status, apply_at, " + TicketStore.itemFkColumn()
                        + " AS item_id FROM " + TicketStore.TICKET
                        + " WHERE status='approved'");
        List<Object> args = new ArrayList<>();
        if (itemId != null && itemId > 0) {
            sql.append(" AND ").append(TicketStore.itemFkColumn()).append("=?");
            args.add(itemId);
        }
        sql.append(" ORDER BY id DESC LIMIT 200");
        return MybatisSupport.db().query(
                sql.toString(),
                (rs, i) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getLong("id"));
                    String u = rs.getString("username");
                    if (u != null && u.length() > 2) {
                        u = u.substring(0, 1) + "**";
                    }
                    row.put("username", u == null ? "" : u);
                    row.put("status", rs.getString("status"));
                    row.put("applyAt", rs.getTimestamp("apply_at"));
                    row.put("itemId", rs.getLong("item_id"));
                    return row;
                },
                args.toArray());
    }

    /** I-03：管理端调剂留痕分页。 */
    public static Map<String, Object> pageAdjustLog(int page, int size) {
        Map<String, Object> empty = new LinkedHashMap<>();
        empty.put("list", List.of());
        empty.put("total", 0);
        empty.put("page", Math.max(1, page));
        empty.put("size", Math.max(1, size));
        if (!TicketStore.peerAccept) return empty;
        if (TicketStore.PROGRESS == null || TicketStore.PROGRESS.isBlank()) return empty;
        TicketStore.ensureProgressTable();
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Integer total = MybatisSupport.db().queryForObject(
                "SELECT COUNT(*) FROM " + TicketStore.PROGRESS + " WHERE status='admin_adjust'",
                Integer.class);
        int t = total == null ? 0 : total;
        List<Map<String, Object>> list = MybatisSupport.db().query(
                "SELECT id, ticket_id, status, operator, remark, created_at FROM "
                        + TicketStore.PROGRESS
                        + " WHERE status='admin_adjust' ORDER BY id DESC LIMIT ? OFFSET ?",
                (rs, i) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getLong("id"));
                    row.put("ticketId", rs.getLong("ticket_id"));
                    row.put("status", rs.getString("status"));
                    row.put("operator", rs.getString("operator"));
                    row.put("remark", rs.getString("remark"));
                    row.put("createdAt", rs.getTimestamp("created_at"));
                    return row;
                },
                size,
                (page - 1) * size);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    /** I-04 TEAM：向同学发送组队邀请站内信。 */
    public static Map<String, Object> sendTeamInvite(
            String fromUser, String toUser, long itemId, String note) {
        if (!TicketStore.peerAccept) throw new IllegalStateException("当前未开启组队互选");
        String from = fromUser == null ? "" : fromUser.trim();
        String to = toUser == null ? "" : toUser.trim();
        if (from.isBlank() || to.isBlank()) throw new IllegalStateException("请指定邀请对象");
        if (from.equals(to)) throw new IllegalStateException("不可邀请自己");
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) throw new IllegalArgumentException("组队资料不存在");
        String title = TicketSql.str(item.get("title"));
        if (title.isBlank()) title = "组队资料#" + itemId;
        String extra = note == null ? "" : note.trim();
        String body = "邀请你加入「" + title + "」，请到组队资料目录查看并提交志愿。"
                + (extra.isBlank() ? "" : (" " + extra));
        com.thesis.service.MessageStore.send(to, "组队邀请", body, "archive", itemId);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("to", to);
        out.put("itemId", itemId);
        out.put("ok", true);
        return out;
    }

    /** I-04 TEAM：已互选成员申请退出（须队长同意）。 */
    public static Map<String, Object> requestTeamExit(long ticketId, String username) {
        if (!TicketStore.peerAccept) throw new IllegalStateException("当前未开启组队互选");
        if (!TicketStore.hasColumn("exit_request")) {
            throw new IllegalStateException("系统未配置退出申请字段");
        }
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (username == null || username.isBlank()
                || !username.equals(String.valueOf(m.get("username")))) {
            throw new IllegalStateException("只能申请退出自己的组队");
        }
        if (!"approved".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅已互选成员可申请退出");
        }
        int prev = m.get("exitRequest") instanceof Number n ? n.intValue() : 0;
        if (prev > 0) throw new IllegalStateException("退出申请已在处理中");
        MybatisSupport.db().update(
                "UPDATE " + TicketStore.TICKET + " SET exit_request=1 WHERE id=?", ticketId);
        long itemId = TicketSql.toLong(m.get("bookId"));
        if (itemId <= 0) itemId = TicketSql.toLong(m.get("itemId"));
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        String owner = item == null ? "" : TicketSql.str(item.get("ownerUsername"));
        if (!owner.isBlank()) {
            try {
                com.thesis.service.MessageStore.send(
                        owner,
                        "退出申请待确认",
                        com.thesis.service.UserStore.displayName(username)
                                + " 申请退出「" + subjectOfTicket(m) + "」，请确认或拒绝。",
                        "ticket",
                        ticketId);
            } catch (Exception ignored) {
            }
        }
        appendProgress(ticketId, "exit_request", username, "申请退出");
        return get(ticketId);
    }

    /** I-04 TEAM：队长待处理的退出申请列表。 */
    public static Map<String, Object> pageExitInbox(String ownerUsername, int page, int size) {
        Map<String, Object> empty = new LinkedHashMap<>();
        empty.put("list", List.of());
        empty.put("total", 0);
        empty.put("page", Math.max(1, page));
        empty.put("size", Math.max(1, size));
        if (!TicketStore.peerAccept || !TicketStore.hasColumn("exit_request")) return empty;
        if (TicketStore.MODE != TicketStore.Mode.ARCHIVE) return empty;
        String owner = ownerUsername == null ? "" : ownerUsername.trim();
        if (owner.isBlank()) return empty;
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String itemTable = ArchiveStore.itemTable();
        String fk = TicketStore.itemFkColumn();
        String from = " FROM " + TicketStore.TICKET + " t JOIN " + itemTable + " i ON t." + fk + "=i.id";
        String where = " WHERE i.owner_username=? AND t.status='approved' AND t.exit_request=1";
        Integer total = MybatisSupport.db().queryForObject(
                "SELECT COUNT(*)" + from + where, Integer.class, owner);
        int t = total == null ? 0 : total;
        List<Map<String, Object>> list = MybatisSupport.db().query(
                "SELECT t.*" + from + where + " ORDER BY t.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> TicketStatusOps.enrich(TicketRowMaps.mapRow(rs)),
                owner,
                size,
                (page - 1) * size);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    /** I-04 TEAM：队长处理退出申请。 */
    public static Map<String, Object> peerExitRespond(
            long ticketId, String ownerUsername, boolean pass, String remark) {
        if (!TicketStore.peerAccept) throw new IllegalStateException("当前未开启组队互选");
        if (!TicketStore.hasColumn("exit_request")) {
            throw new IllegalStateException("系统未配置退出申请字段");
        }
        if (!isPeerOwnerOf(ticketId, ownerUsername)) {
            throw new IllegalStateException("仅队长可处理退出申请");
        }
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!"approved".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅已互选单据可处理退出");
        }
        int req = m.get("exitRequest") instanceof Number n ? n.intValue() : 0;
        if (req <= 0) throw new IllegalStateException("该成员未申请退出");
        String note = remark == null ? "" : remark.trim();
        if (pass) {
            // 同意退出：回补名额并完结
            long itemId = TicketSql.toLong(m.get("bookId"));
            if (itemId <= 0) itemId = TicketSql.toLong(m.get("itemId"));
            if (TicketStore.MODE == TicketStore.Mode.ARCHIVE && TicketStore.useQuota && itemId > 0) {
                ArchiveStore.adjustStock(itemId, rowQty(m));
            }
            MybatisSupport.db().update(
                    "UPDATE " + TicketStore.TICKET
                            + " SET status='returned', exit_request=0, remark=? WHERE id=?",
                    note.isBlank() ? "队长同意退出" : note,
                    ticketId);
            appendProgress(ticketId, "exit_accept", ownerUsername, note.isBlank() ? "同意退出" : note);
            try {
                String user = TicketSql.str(m.get("username"));
                if (!user.isBlank()) {
                    com.thesis.service.MessageStore.send(
                            user, "退出已同意", "队长已同意你退出组队。", "ticket", ticketId);
                }
            } catch (Exception ignored) {
            }
        } else {
            MybatisSupport.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET exit_request=0 WHERE id=?", ticketId);
            appendProgress(ticketId, "exit_reject", ownerUsername, note.isBlank() ? "拒绝退出" : note);
            try {
                String user = TicketSql.str(m.get("username"));
                if (!user.isBlank()) {
                    com.thesis.service.MessageStore.send(
                            user,
                            "退出未通过",
                            note.isBlank() ? "队长未同意退出申请。" : note,
                            "ticket",
                            ticketId);
                }
            } catch (Exception ignored) {
            }
        }
        return get(ticketId);
    }

    private static String subjectOfTicket(Map<String, Object> ticket) {
        String subject = TicketSql.str(ticket.get("title"));
        if (subject.isBlank()) subject = TicketSql.str(ticket.get("bookTitle"));
        if (subject.isBlank()) subject = "单据#" + ticket.get("id");
        return subject;
    }

    /** I-03：向已互选学生发站内通知；返回通知条数。 */
    public static int notifyMutualMatchResults() {
        if (!TicketStore.peerAccept) return 0;
        List<Map<String, Object>> rows = MybatisSupport.db().query(
                "SELECT id, username FROM " + TicketStore.TICKET
                        + " WHERE status='approved' ORDER BY id DESC LIMIT 500",
                (rs, i) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getLong("id"));
                    row.put("username", rs.getString("username"));
                    return row;
                });
        int n = 0;
        for (Map<String, Object> row : rows) {
            String user = TicketSql.str(row.get("username")).trim();
            long tid = TicketSql.toLong(row.get("id"));
            if (user.isBlank() || tid <= 0) continue;
            try {
                com.thesis.service.MessageStore.send(
                        user,
                        "互选结果通知",
                        "你的志愿已确认互选，请到「我的志愿」查看详情。",
                        "ticket",
                        tid);
                n++;
            } catch (Exception ignored) {
            }
        }
        return n;
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
