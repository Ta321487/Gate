package com.thesis.capability;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 报销明细、出差行程、社团名册：各写一张子表，一行一条，用 ticket_id 挂申请单。
 * 页面仍一次提交多行数组，入库时拆开写，答辩时按 1:N 讲，不把多行塞进 JSON 列。
 */
final class TicketLineOps {

    private TicketLineOps() {}

    /** 读单时把子表拼回数组，前端还是看到多行列表。 */
    static void attach(Map<String, Object> m) {
        if (m == null) return;
        Object idObj = m.get("id");
        if (!(idObj instanceof Number n)) return;
        long ticketId = n.longValue();
        if (TicketStore.allowExpenseLines) {
            m.put("expenseLines", listExpenseLines(ticketId));
        }
        if (TicketStore.allowTripLegs) {
            m.put("tripLegs", listTripLegs(ticketId));
        }
        if (TicketStore.allowClubRoster) {
            m.put("clubMembers", listClubMembers(ticketId));
        }
        attachRatingDims(m, ticketId);
        attachCompanions(m, ticketId);
    }

    static void replaceRatingDims(long ticketId, Map<String, Integer> dims) {
        if (!tableReady("ticket_rating_dim")) {
            throw new IllegalStateException("系统未配置多维评分表");
        }
        TicketSql.db().update("DELETE FROM ticket_rating_dim WHERE ticket_id=?", ticketId);
        if (dims == null || dims.isEmpty()) return;
        for (Map.Entry<String, Integer> e : dims.entrySet()) {
            String key = e.getKey() == null ? "" : e.getKey().trim();
            if (key.isBlank() || e.getValue() == null) continue;
            if (key.length() > 64) key = key.substring(0, 64);
            TicketSql.db().update(
                    "INSERT INTO ticket_rating_dim (ticket_id,dim_key,score) VALUES (?,?,?)",
                    ticketId, key, e.getValue());
        }
    }

    static boolean ratingDimTableReady() {
        return tableReady("ticket_rating_dim");
    }

    static void replaceCompanions(long ticketId, Object raw) {
        List<String> names = parseCompanionNames(raw);
        if (!tableReady("ticket_companion")) {
            throw new IllegalStateException("系统未配置随行人员表");
        }
        TicketSql.db().update("DELETE FROM ticket_companion WHERE ticket_id=?", ticketId);
        int no = 1;
        for (String name : names) {
            TicketSql.db().update(
                    "INSERT INTO ticket_companion (ticket_id,line_no,name) VALUES (?,?,?)",
                    ticketId, no++, name);
        }
    }

    static String companionNamesCsv(long ticketId) {
        List<String> names = listCompanionNames(ticketId);
        return String.join("，", names);
    }

    private static void attachRatingDims(Map<String, Object> m, long ticketId) {
        if (!tableReady("ticket_rating_dim")) return;
        List<Map<String, Object>> rows = TicketSql.db().query(
                "SELECT dim_key, score FROM ticket_rating_dim WHERE ticket_id=? ORDER BY id",
                (rs, i) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("key", TicketSql.safeStr(rs, "dim_key"));
                    row.put("score", rs.getInt("score"));
                    return row;
                },
                ticketId);
        if (rows.isEmpty()) return;
        StringBuilder json = new StringBuilder("{");
        int n = 0;
        for (Map<String, Object> row : rows) {
            if (n++ > 0) json.append(",");
            json.append("\"").append(String.valueOf(row.get("key")).replace("\"", "")).append("\":")
                    .append(row.get("score"));
        }
        json.append("}");
        m.put("ratingDimsJson", json.toString());
    }

    private static void attachCompanions(Map<String, Object> m, long ticketId) {
        String csv = companionNamesCsv(ticketId);
        if (!csv.isBlank()) m.put("companionNames", csv);
    }

    private static List<String> parseCompanionNames(Object raw) {
        List<String> out = new ArrayList<>();
        if (raw instanceof List<?> list) {
            for (Object o : list) {
                String s = TicketSql.str(o).trim();
                if (!s.isBlank()) out.add(clipName(s));
            }
            return out;
        }
        String s = TicketSql.str(raw).trim();
        if (s.isBlank()) return out;
        for (String part : s.split("[,，;；、]+")) {
            String n = part.trim();
            if (!n.isBlank()) out.add(clipName(n));
        }
        return out;
    }

    private static String clipName(String s) {
        return s.length() > 64 ? s.substring(0, 64) : s;
    }

    private static List<String> listCompanionNames(long ticketId) {
        if (!tableReady("ticket_companion")) return List.of();
        return TicketSql.db().query(
                "SELECT name FROM ticket_companion WHERE ticket_id=? ORDER BY line_no",
                (rs, i) -> TicketSql.safeStr(rs, "name"),
                ticketId);
    }

    /** 申请写入：先删旧行再按顺序插入，避免改单后留下脏行。 */
    static void replaceExpenseLines(long ticketId, Object raw) {
        List<Map<String, Object>> lines = parseExpenseLines(raw);
        if (!tableReady("ticket_expense_line")) {
            throw new IllegalStateException("系统未配置报销明细表");
        }
        TicketSql.db().update("DELETE FROM ticket_expense_line WHERE ticket_id=?", ticketId);
        int no = 1;
        for (Map<String, Object> line : lines) {
            TicketSql.db().update(
                    "INSERT INTO ticket_expense_line (ticket_id,line_no,category,amount,note) VALUES (?,?,?,?,?)",
                    ticketId,
                    no++,
                    line.get("category"),
                    line.get("amount"),
                    line.get("note"));
        }
    }

    /** 申请写入：名册一人一行（姓名必填，学号可空）。 */
    static void replaceClubRoster(long ticketId, Object raw) {
        List<Map<String, Object>> rows = parseClubMembers(raw);
        if (!tableReady("ticket_club_member")) {
            throw new IllegalStateException("系统未配置成员名册表");
        }
        TicketSql.db().update("DELETE FROM ticket_club_member WHERE ticket_id=?", ticketId);
        int no = 1;
        for (Map<String, Object> row : rows) {
            TicketSql.db().update(
                    "INSERT INTO ticket_club_member (ticket_id,line_no,member_name,student_no) VALUES (?,?,?,?)",
                    ticketId,
                    no++,
                    row.get("name"),
                    row.get("studentNo"));
        }
    }

    /** 申请写入：出差一段一行（出发/途经/到达/日期）。 */
    static void replaceTripLegs(long ticketId, Object raw) {
        List<Map<String, Object>> legs = parseTripLegs(raw);
        if (!tableReady("ticket_trip_leg")) {
            throw new IllegalStateException("系统未配置行程表");
        }
        TicketSql.db().update("DELETE FROM ticket_trip_leg WHERE ticket_id=?", ticketId);
        int no = 1;
        for (Map<String, Object> leg : legs) {
            TicketSql.db().update(
                    "INSERT INTO ticket_trip_leg (ticket_id,line_no,from_place,via_place,to_place,on_date) VALUES (?,?,?,?,?,?)",
                    ticketId,
                    no++,
                    leg.get("from"),
                    leg.get("via"),
                    leg.get("to"),
                    leg.get("on"));
        }
    }

    private static List<Map<String, Object>> parseExpenseLines(Object raw) {
        if (!(raw instanceof List<?> list) || list.isEmpty()) {
            throw new IllegalStateException("请至少填写一行报销明细");
        }
        List<Map<String, Object>> out = new ArrayList<>();
        for (Object o : list) {
            if (!(o instanceof Map<?, ?> m)) continue;
            String cat = TicketSql.str(m.get("category")).trim();
            if (cat.length() > 32) cat = cat.substring(0, 32);
            double amt = TicketSql.toDouble(m.get("amount"));
            String note = TicketSql.str(m.get("note")).trim();
            if (note.length() > 128) note = note.substring(0, 128);
            if (cat.isBlank() || !(amt > 0)) {
                throw new IllegalStateException("每行报销明细须填写类别和大于 0 的金额");
            }
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("category", cat);
            row.put("amount", amt);
            row.put("note", note);
            out.add(row);
        }
        if (out.isEmpty()) throw new IllegalStateException("请至少填写一行报销明细");
        return out;
    }

    private static List<Map<String, Object>> parseTripLegs(Object raw) {
        if (!(raw instanceof List<?> list) || list.isEmpty()) {
            throw new IllegalStateException("请至少填写一段出差行程");
        }
        List<Map<String, Object>> out = new ArrayList<>();
        for (Object o : list) {
            if (!(o instanceof Map<?, ?> m)) continue;
            String from = TicketSql.str(m.get("from")).trim();
            String via = TicketSql.str(m.get("via")).trim();
            String to = TicketSql.str(m.get("to")).trim();
            String on = TicketSql.str(m.get("on")).trim();
            if (on.length() >= 10) on = on.substring(0, 10);
            if (from.length() > 64) from = from.substring(0, 64);
            if (via.length() > 64) via = via.substring(0, 64);
            if (to.length() > 64) to = to.substring(0, 64);
            if (from.isBlank() || to.isBlank() || on.isBlank()) {
                throw new IllegalStateException("每段行程须填写出发地、到达地和日期");
            }
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("from", from);
            row.put("via", via);
            row.put("to", to);
            row.put("on", on);
            out.add(row);
        }
        if (out.isEmpty()) throw new IllegalStateException("请至少填写一段出差行程");
        return out;
    }

    private static List<Map<String, Object>> parseClubMembers(Object raw) {
        if (!(raw instanceof List<?> list) || list.isEmpty()) {
            throw new IllegalStateException("请至少填写一名成员");
        }
        List<Map<String, Object>> out = new ArrayList<>();
        for (Object o : list) {
            if (!(o instanceof Map<?, ?> m)) continue;
            String name = TicketSql.str(m.get("name")).trim();
            if (name.isBlank()) name = TicketSql.str(m.get("memberName")).trim();
            if (name.length() > 64) name = name.substring(0, 64);
            String no = TicketSql.str(m.get("studentNo")).trim();
            if (no.isBlank()) no = TicketSql.str(m.get("student_no")).trim();
            if (no.length() > 32) no = no.substring(0, 32);
            if (name.isBlank()) {
                throw new IllegalStateException("每行名册须填写姓名");
            }
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("name", name);
            row.put("studentNo", no);
            out.add(row);
        }
        if (out.isEmpty()) throw new IllegalStateException("请至少填写一名成员");
        return out;
    }

    private static List<Map<String, Object>> listExpenseLines(long ticketId) {
        if (!tableReady("ticket_expense_line")) return List.of();
        return TicketSql.db().query(
                "SELECT category, amount, note FROM ticket_expense_line WHERE ticket_id=? ORDER BY line_no",
                (rs, i) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("category", TicketSql.safeStr(rs, "category"));
                    row.put("amount", rs.getBigDecimal("amount"));
                    row.put("note", TicketSql.safeStr(rs, "note"));
                    return row;
                },
                ticketId);
    }

    private static List<Map<String, Object>> listTripLegs(long ticketId) {
        if (!tableReady("ticket_trip_leg")) return List.of();
        return TicketSql.db().query(
                "SELECT from_place, via_place, to_place, on_date FROM ticket_trip_leg WHERE ticket_id=? ORDER BY line_no",
                (rs, i) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("from", TicketSql.safeStr(rs, "from_place"));
                    row.put("via", TicketSql.safeStr(rs, "via_place"));
                    row.put("to", TicketSql.safeStr(rs, "to_place"));
                    row.put("on", TicketSql.safeStr(rs, "on_date"));
                    return row;
                },
                ticketId);
    }

    private static List<Map<String, Object>> listClubMembers(long ticketId) {
        if (!tableReady("ticket_club_member")) return List.of();
        return TicketSql.db().query(
                "SELECT member_name, student_no FROM ticket_club_member WHERE ticket_id=? ORDER BY line_no",
                (rs, i) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("name", TicketSql.safeStr(rs, "member_name"));
                    row.put("studentNo", TicketSql.safeStr(rs, "student_no"));
                    return row;
                },
                ticketId);
    }

    /** 表还没 bake 出来时先失败，避免假成功。 */
    private static boolean tableReady(String table) {
        try {
            TicketSql.db().query("SELECT 1 FROM " + table + " LIMIT 1", (rs, i) -> 1);
            return true;
        } catch (Exception e) {
            return false;
        }
    }
}
