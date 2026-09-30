"""把「本组待补」第二批 4 键（levelAffectsDeadline / notifyDutyOnReport /
allowObjectionWindow / objectionDays）从 baseline 同步到 mybatis + jpa 两个 overlay。

背景：persistence-mybatis / persistence-jpa 是手写叠层，capability/、config/、service/
（mapper 除外）与 baseline 同构但各按其持久化惯用法改写；本脚本按「同一处 old 文本 →
同一处 new 文本」的精确锚点做幂等 patch，命中数不为 1 立即失败（不留半成品）。

用法：python tools/sync_objection_event_overlays.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVL = ROOT / "skeletons" / "overlays"

MB = OVL / "persistence-mybatis" / "backend" / "src" / "main"
JP = OVL / "persistence-jpa" / "backend" / "src" / "main"
JB = "java/com/thesis"
mbTS = MB / JB / "capability/TicketStore.java"
jpTS = JP / JB / "capability/TicketStore.java"
mbBINDER = MB / JB / "config/DomainRuntimeBinder.java"
jpBINDER = JP / JB / "config/DomainRuntimeBinder.java"
mbFUND = MB / JB / "service/FundPublicityStore.java"
jpFUND = JP / JB / "service/FundPublicityStore.java"
mbGRADE = MB / JB / "service/GradeScoreStore.java"
jpGRADE = JP / JB / "service/GradeScoreStore.java"
mbGRADE_MAPPER = MB / JB / "mapper/GradeScoreMapper.java"

# ---------------------------------------------------------------- TicketStore

TS_HELPERS_OLD = """    /** 跟进组列表闸：未跟进 N 天筛 + 同联系电话拦重号。 */
    public static void configureFollowOps(int staleFollowDaysIn, boolean phoneDupCheckIn) {
        staleFollowDays = Math.max(0, Math.min(90, staleFollowDaysIn));
        phoneDupCheck = phoneDupCheckIn;
    }
"""

TS_HELPERS_NEW = """    /** 开题扫：事件等级 → 处理时限天数（高/中/低） */
    static boolean levelSla = false;
    static int levelSlaHighDays = 1;
    static int levelSlaMidDays = 3;
    static int levelSlaLowDays = 7;
    /** 开题扫：事件上报后一键通知当日值班（站内信浅群发） */
    static boolean dutyNotify = false;

    /** 跟进组列表闸：未跟进 N 天筛 + 同联系电话拦重号。 */
    public static void configureFollowOps(int staleFollowDaysIn, boolean phoneDupCheckIn) {
        staleFollowDays = Math.max(0, Math.min(90, staleFollowDaysIn));
        phoneDupCheck = phoneDupCheckIn;
    }

    /** 事件组闸：等级影响处理时限 + 上报群发值班。 */
    public static void configureEventOps(
            boolean levelSlaIn, int highDaysIn, int midDaysIn, int lowDaysIn, boolean dutyNotifyIn) {
        levelSla = levelSlaIn;
        levelSlaHighDays = Math.max(1, Math.min(60, highDaysIn));
        levelSlaMidDays = Math.max(1, Math.min(60, midDaysIn));
        levelSlaLowDays = Math.max(1, Math.min(60, lowDaysIn));
        dutyNotify = dutyNotifyIn;
    }

    /** 等级 → 处理时限天数；levelSla 关时原样返回 fallback。 */
    static int levelSlaDays(Map<String, Object> m, int fallback) {
        if (!levelSla) return fallback;
        String lv = levelTextOf(m);
        if (lv.isBlank()) return fallback;
        if (lv.contains("高") || lv.contains("严重") || lv.contains("重大")
                || lv.contains("紧急") || lv.contains("一级") || lv.contains("红")) {
            return levelSlaHighDays;
        }
        if (lv.contains("中") || lv.contains("较重") || lv.contains("二级")
                || lv.contains("橙") || lv.contains("黄")) {
            return levelSlaMidDays;
        }
        if (lv.contains("低") || lv.contains("轻微") || lv.contains("一般")
                || lv.contains("三级") || lv.contains("蓝")) {
            return levelSlaLowDays;
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

    /** 高,中,低 时限天数（未开时为空串），供前端展示。 */
    static String levelSlaCsv() {
        return levelSla ? (levelSlaHighDays + "," + levelSlaMidDays + "," + levelSlaLowDays) : "";
    }

    /** 事件上报群发当日值班；返回实际通知人数。 */
    static int notifyDutyOnNewReport(long ticketId, String applicant, String subject) {
        if (!dutyNotify || ticketId <= 0) return 0;
        try {
            Set<String> onDuty = StaffRosterStore.onDutyUsernames(LocalDate.now().toString());
            if (onDuty.isEmpty()) return 0;
            String sub = subject == null || subject.isBlank() ? ("单据#" + ticketId) : subject;
            String who = UserStore.displayName(applicant);
            int sent = 0;
            for (String un : onDuty) {
                if (un == null || un.isBlank() || un.equals(applicant)) continue;
                MessageStore.send(un, "新事件上报", who + " 上报了「" + sub + "」，请当日值班关注。", "ticket", ticketId);
                sent++;
            }
            return sent;
        } catch (Exception ignored) {
            return 0;
        }
    }
"""

TS_IMPORT_OLD = "import java.time.LocalDateTime;"
TS_IMPORT_NEW = "import java.time.LocalDate;\nimport java.time.LocalDateTime;"

MB_DUE_OLD = """        if (useDeadline) {
            LocalDateTime approveAt = LocalDateTime.now();
            LocalDateTime dueAt = approveAt.plusDays(loanDays());
            if (MODE == Mode.ARCHIVE) {"""

MB_DUE_NEW = """        if (useDeadline) {
            LocalDateTime approveAt = LocalDateTime.now();
            LocalDateTime dueAt = approveAt.plusDays(levelSlaDays(m, loanDays()));
            if (MODE == Mode.ARCHIVE) {"""

JP_DUE_ARCHIVE_OLD = """        if (MODE == Mode.ARCHIVE && useDeadline) {
            LocalDateTime approveAt = LocalDateTime.now();
            LocalDateTime dueAt = approveAt.plusDays(loanDays());"""

JP_DUE_ARCHIVE_NEW = """        if (MODE == Mode.ARCHIVE && useDeadline) {
            LocalDateTime approveAt = LocalDateTime.now();
            LocalDateTime dueAt = approveAt.plusDays(levelSlaDays(m, loanDays()));"""

JP_DUE_STANDALONE_OLD = """        } else if (useDeadline) {
            LocalDateTime approveAt = LocalDateTime.now();
            LocalDateTime dueAt = approveAt.plusDays(loanDays());"""

JP_DUE_STANDALONE_NEW = """        } else if (useDeadline) {
            // 独立工单 SLA：等级影响时限时按等级取天数
            LocalDateTime approveAt = LocalDateTime.now();
            LocalDateTime dueAt = approveAt.plusDays(levelSlaDays(m, loanDays()));"""

APPLY_TAIL_OLD = """            notifyAdminsNewTicket(id, username, subj);
            notifyPeerOwnerNewTicket(id, itemId, username, subj);
        }
        return get(id);
    }"""

APPLY_TAIL_NEW = """            notifyAdminsNewTicket(id, username, subj);
            notifyPeerOwnerNewTicket(id, itemId, username, subj);
        }
        Map<String, Object> applied = get(id);
        if (applied != null) {
            int dutyNotified = notifyDutyOnNewReport(id, username, subjectOf(applied));
            if (dutyNotified > 0) applied.put("dutyNotified", dutyNotified);
        }
        return applied;
    }"""

STD_TAIL_OLD = """        appendProgress(id, "pending", username, "用户提交");
        notifyAdminsNewTicket(id, username, t);
        return get(id);
    }"""

STD_TAIL_NEW = """        appendProgress(id, "pending", username, "用户提交");
        notifyAdminsNewTicket(id, username, t);
        Map<String, Object> createdStd = get(id);
        if (createdStd != null) {
            int dutyNotified = notifyDutyOnNewReport(id, username, t);
            if (dutyNotified > 0) createdStd.put("dutyNotified", dutyNotified);
        }
        return createdStd;
    }"""

PAGE_OUT_OLD = """        out.put("size", size);
        out.put("staleFollowDays", staleFollowDays);
        return out;
    }"""

PAGE_OUT_NEW = """        out.put("size", size);
        out.put("staleFollowDays", staleFollowDays);
        out.put("levelSlaDays", levelSlaCsv());
        out.put("dutyNotify", dutyNotify);
        return out;
    }"""

# ------------------------------------------------------------------- Binder

BINDER_IMPORT_OLD = "import com.thesis.service.GradeScoreStore;"
BINDER_IMPORT_NEW = (
    "import com.thesis.service.GradeScoreStore;\nimport com.thesis.service.FundPublicityStore;"
)

BINDER_FIELDS_OLD = """    @Value("${thesis.ticket-stale-follow-days:0}")
    private int ticketStaleFollowDays;
"""

BINDER_FIELDS_NEW = """    @Value("${thesis.ticket-stale-follow-days:0}")
    private int ticketStaleFollowDays;

    @Value("${thesis.ticket-level-affects-deadline:false}")
    private boolean ticketLevelAffectsDeadline;

    @Value("${thesis.ticket-level-sla-high-days:0}")
    private int ticketLevelSlaHighDays;

    @Value("${thesis.ticket-level-sla-mid-days:0}")
    private int ticketLevelSlaMidDays;

    @Value("${thesis.ticket-level-sla-low-days:0}")
    private int ticketLevelSlaLowDays;

    @Value("${thesis.ticket-notify-duty-on-report:false}")
    private boolean ticketNotifyDutyOnReport;

    @Value("${thesis.ticket-allow-objection-window:false}")
    private boolean ticketAllowObjectionWindow;

    @Value("${thesis.ticket-objection-days:0}")
    private int ticketObjectionDays;
"""

BINDER_CALL_OLD = "            TicketStore.configureFollowOps(ticketStaleFollowDays, ticketPhoneDupCheck);"

BINDER_CALL_NEW = """            TicketStore.configureFollowOps(ticketStaleFollowDays, ticketPhoneDupCheck);
            TicketStore.configureEventOps(
                    ticketLevelAffectsDeadline,
                    Math.max(1, ticketLevelSlaHighDays),
                    Math.max(1, ticketLevelSlaMidDays),
                    Math.max(1, ticketLevelSlaLowDays),
                    ticketNotifyDutyOnReport);
            FundPublicityStore.configureObjection(ticketAllowObjectionWindow, ticketObjectionDays);
            GradeScoreStore.configureObjectionDays(ticketObjectionDays);"""

# --------------------------------------------------------- FundPublicityStore

FUND_HEAD_MB_OLD = """public class FundPublicityStore {

    private static Boolean tableReady;

    private FundPublicityStore() {}

    private static MbSql db() {
        return MybatisSupport.db();
    }
"""

FUND_HEAD_JP_OLD = """public class FundPublicityStore {

    private static Boolean tableReady;

    private FundPublicityStore() {}

    private static JpaDb db() {
        return JpaSupport.db();
    }
"""

FUND_HEAD_MB_NEW = """public class FundPublicityStore {

    private static Boolean tableReady;
    /** 公示异议登记窗口（开题扫 FUND）：开关 + 天数（公示结束日 + N 天） */
    private static boolean objectionWindow = false;
    private static int objectionDays = 0;

    private FundPublicityStore() {}

    private static MbSql db() {
        return MybatisSupport.db();
    }
"""

FUND_HEAD_JP_NEW = """public class FundPublicityStore {

    private static Boolean tableReady;
    /** 公示异议登记窗口（开题扫 FUND）：开关 + 天数（公示结束日 + N 天） */
    private static boolean objectionWindow = false;
    private static int objectionDays = 0;

    private FundPublicityStore() {}

    private static JpaDb db() {
        return JpaSupport.db();
    }
"""

FUND_FIELDS_TAIL_NEW = """
    /** 异议窗口：days<=0 视为未开；写入申请单 objection_due_at。 */
    public static void configureObjection(boolean on, int days) {
        objectionWindow = on;
        objectionDays = Math.max(0, Math.min(60, days));
    }

    public static boolean objectionEnabled() {
        return objectionWindow && objectionDays > 0;
    }

    public static int objectionDays() {
        return objectionDays;
    }

    private static LocalDate parseDay(String raw) {
        String s = raw == null ? "" : raw.trim();
        if (s.isEmpty()) return null;
        if (s.length() > 10) s = s.substring(0, 10);
        try {
            return LocalDate.parse(s);
        } catch (Exception e) {
            return null;
        }
    }

    /** 窗口截止日：公示结束日 + N 天（无结束日退起算日，再无则今天）。 */
    static java.sql.Date windowDue(String startAt, String endAt) {
        if (!objectionEnabled()) return null;
        LocalDate base = parseDay(endAt);
        if (base == null) base = parseDay(startAt);
        if (base == null) base = LocalDate.now();
        return java.sql.Date.valueOf(base.plusDays(objectionDays));
    }

    /** 申请单是否已注入异议扩展列（由 bake 按 ticket.allowObjectionWindow 注入）。 */
    static boolean hasObjectionCols() {
        String t = ticketTable();
        if (t.isEmpty()) return false;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.columns "
                            + "WHERE table_schema=DATABASE() AND table_name=? "
                            + "AND column_name='objection_due_at'",
                    Integer.class,
                    t);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static String cellStr(ResultSet rs, String col) {
        try {
            Object v = rs.getObject(col);
            return v == null ? "" : String.valueOf(v);
        } catch (Exception e) {
            return "";
        }
    }
"""

FUND_IMPORT_OLD = """import java.sql.SQLException;
import java.util.LinkedHashMap;"""

FUND_IMPORT_NEW = """import java.sql.SQLException;
import java.time.LocalDate;
import java.util.LinkedHashMap;"""

FUND_SELECT_OLD = """    private static String selectSql(String tail) {
        String t = ticketTable();
        if (t.isEmpty()) {
            return "SELECT p.id, p.ticket_id, '' AS username, p.title, p.start_at, p.end_at, "
                    + "p.status, p.operator, p.created_at FROM fund_publicity p " + tail;
        }
        return "SELECT p.id, p.ticket_id, IFNULL(t.username,'') AS username, p.title, "
                + "p.start_at, p.end_at, p.status, p.operator, p.created_at "
                + "FROM fund_publicity p LEFT JOIN `" + t + "` t ON t.id=p.ticket_id " + tail;
    }"""

FUND_SELECT_NEW = """    private static String selectSql(String tail) {
        String t = ticketTable();
        String objection = hasObjectionCols()
                ? "t.objection_due_at AS objection_due_at, t.objection_note AS objection_note, "
                        + "t.objection_at AS objection_at "
                : "NULL AS objection_due_at, '' AS objection_note, NULL AS objection_at ";
        if (t.isEmpty()) {
            return "SELECT p.id, p.ticket_id, '' AS username, p.title, p.start_at, p.end_at, "
                    + "p.status, p.operator, p.created_at, "
                    + "NULL AS objection_due_at, '' AS objection_note, NULL AS objection_at "
                    + "FROM fund_publicity p " + tail;
        }
        return "SELECT p.id, p.ticket_id, IFNULL(t.username,'') AS username, p.title, "
                + "p.start_at, p.end_at, p.status, p.operator, p.created_at, " + objection
                + "FROM fund_publicity p LEFT JOIN `" + t + "` t ON t.id=p.ticket_id " + tail;
    }"""

FUND_MAPROW_OLD = """        m.put("operator", rs.getString("operator"));
        m.put("createdAt", rs.getString("created_at"));
        return m;"""

FUND_MAPROW_NEW = """        m.put("operator", rs.getString("operator"));
        m.put("createdAt", rs.getString("created_at"));
        m.put("objectionDueAt", cellStr(rs, "objection_due_at"));
        m.put("objectionNote", cellStr(rs, "objection_note"));
        m.put("objectionAt", cellStr(rs, "objection_at"));
        return m;"""

FUND_SAVE_OLD = """                clip(operator, 64));
"""

FUND_SAVE_NEW = """                clip(operator, 64));
        // 异议登记窗口：公示结束日 + N 天写回申请单（用户端超期拒收）
        java.sql.Date due = windowDue(startAt, endAt);
        if (due != null && hasObjectionCols()) {
            db().update(
                    "UPDATE `" + t + "` SET objection_due_at=?, objection_note='', objection_at=NULL WHERE id=?",
                    due,
                    ticketId);
        }
"""

FUND_OBJECTION_OLD = """    /** 结束公示（公示期已满）。 */
    public static void close(long id, String operator) {"""

FUND_OBJECTION_NEW = """    /** 用户端：对本人公示登记异议（窗口内可写，超期/未开拒绝）。 */
    public static Map<String, Object> submitObjection(long publicityId, String username, String note) {
        require();
        String t = ticketTable();
        if (t.isEmpty()) throw new IllegalStateException("当前系统没有资助申请单");
        if (!objectionEnabled() || !hasObjectionCols()) {
            throw new IllegalStateException("未开通公示异议登记");
        }
        String u = clip(username, 64);
        String text = clip(note, 255);
        if (text.isEmpty()) throw new IllegalArgumentException("请填写异议说明");
        List<Map<String, Object>> rows = db().query(
                "SELECT p.ticket_id, p.status, IFNULL(t.username,'') AS username "
                        + "FROM fund_publicity p LEFT JOIN `" + t + "` t ON t.id=p.ticket_id "
                        + "WHERE p.id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("ticketId", rs.getLong("ticket_id"));
                    m.put("status", rs.getString("status"));
                    m.put("username", rs.getString("username"));
                    return m;
                },
                publicityId);
        if (rows.isEmpty()) throw new IllegalArgumentException("公示记录不存在");
        Map<String, Object> row = rows.get(0);
        if (!"publicizing".equals(String.valueOf(row.get("status")))) {
            throw new IllegalStateException("公示已结束，无法登记异议");
        }
        String owner = String.valueOf(row.get("username"));
        if (!u.isEmpty() && !u.equals(owner)) {
            throw new IllegalStateException("只能对本人申请的公示登记异议");
        }
        long ticketId = row.get("ticketId") instanceof Number n ? n.longValue() : 0L;
        String due = dueOf(ticketId);
        LocalDate dueDay = parseDay(due);
        if (dueDay != null && LocalDate.now().isAfter(dueDay)) {
            throw new IllegalStateException("异议登记窗口已于 " + dueDay + " 关闭");
        }
        db().update(
                "UPDATE `" + t + "` SET objection_note=?, objection_at=NOW() WHERE id=?",
                text,
                ticketId);
        try {
            MessageStore.notifyAdmins(
                    "公示异议",
                    UserStore.displayName(u) + " 对「" + titleOf(publicityId) + "」提出异议：" + text,
                    "fund_publicity",
                    publicityId);
        } catch (Exception ignored) {
            // 站内信失败不影响异议落库
        }
        List<Map<String, Object>> out = db().query(
                selectSql("WHERE p.id=? LIMIT 1"), (rs, i) -> mapRow(rs, i), publicityId);
        if (out.isEmpty()) throw new IllegalStateException("异议登记后未能读回");
        return out.get(0);
    }

    private static String dueOf(long ticketId) {
        String t = ticketTable();
        if (t.isEmpty() || ticketId <= 0 || !hasObjectionCols()) return "";
        try {
            List<String> rows = db().query(
                    "SELECT objection_due_at FROM `" + t + "` WHERE id=?",
                    (rs, i) -> {
                        Object v = rs.getObject("objection_due_at");
                        return v == null ? "" : String.valueOf(v);
                    },
                    ticketId);
            return rows.isEmpty() ? "" : rows.get(0);
        } catch (Exception e) {
            return "";
        }
    }

    private static String titleOf(long publicityId) {
        try {
            List<String> rows = db().query(
                    "SELECT title FROM fund_publicity WHERE id=?",
                    (rs, i) -> String.valueOf(rs.getString("title")),
                    publicityId);
            return rows.isEmpty() ? ("公示#" + publicityId) : rows.get(0);
        } catch (Exception e) {
            return "公示#" + publicityId;
        }
    }

    /** 结束公示（公示期已满）。 */
    public static void close(long id, String operator) {"""

# --------------------------------------------------------- GradeScoreStore

GRADE_FIELDS_OLD = """    private static boolean enabled;
    private static Boolean tableReady;

    private GradeScoreStore() {}
"""

GRADE_TAIL_SHARED = """

    /** 异议时限开关：days<=0 视为未开。 */
    public static void configureObjectionDays(int days) {
        objectionDays = Math.max(0, Math.min(60, days));
    }

    public static int objectionDays() {
        return objectionDays;
    }

    /** 服务端闸：已发布成绩超期后拒绝成绩更正/异议申请（入口按时限关）。 */
    public static void assertObjectionOpen(String username, long courseId) {
        if (objectionDays <= 0 || !ready()) return;
        Map<String, Object> w = objectionWindow(username, courseId);
        String due = String.valueOf(w.getOrDefault("dueAt", ""));
        if (!due.isBlank() && !Boolean.TRUE.equals(w.get("open"))) {
            throw new IllegalStateException("成绩异议申请已于 " + due + " 截止，入口已关闭");
        }
    }

    private static LocalDate parseDay(String raw) {
        String s = raw == null ? "" : raw.trim();
        if (s.isEmpty()) return null;
        if (s.length() > 10) s = s.substring(0, 10);
        try {
            return LocalDate.parse(s);
        } catch (Exception e) {
            return null;
        }
    }
"""

# jpa / baseline 惯用法：JdbcTemplate 查 grade_score
JP_GRADE_FIELDS_NEW = (
    """    private static boolean enabled;
    private static Boolean tableReady;
    /** 成绩异议申请时限（开题扫 GRADE）：成绩登记后 N 天内可提交更正/异议申请 */
    private static int objectionDays = 0;

    private GradeScoreStore() {}

    /** 异议窗口：以本人该课程最近一次成绩登记时间为发布基准。 */
    public static Map<String, Object> objectionWindow(String username, long courseId) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("days", objectionDays);
        out.put("open", false);
        out.put("dueAt", "");
        out.put("publishedAt", "");
        if (objectionDays <= 0 || !ready()) return out;
        String user = clip(username, 64);
        if (user.isEmpty() || courseId <= 0) return out;
        try {
            List<String> rows = db().query(
                    "SELECT MAX(created_at) AS published_at FROM grade_score "
                            + "WHERE username=? AND course_id=?",
                    (rs, i) -> {
                        Object v = rs.getObject("published_at");
                        return v == null ? "" : String.valueOf(v);
                    },
                    user,
                    courseId);
            String published = rows.isEmpty() ? "" : rows.get(0);
            LocalDate base = parseDay(published);
            if (base == null) return out;
            LocalDate due = base.plusDays(objectionDays);
            out.put("publishedAt", base.toString());
            out.put("dueAt", due.toString());
            out.put("open", !LocalDate.now().isAfter(due));
        } catch (Exception ignored) {
            // 成绩表不可用按未开处理
        }
        return out;
    }
"""
    + GRADE_TAIL_SHARED
)

# mybatis 惯用法：mapper 取发布基准
MB_GRADE_FIELDS_NEW = (
    """    private static boolean enabled;
    private static Boolean tableReady;
    /** 成绩异议申请时限（开题扫 GRADE）：成绩登记后 N 天内可提交更正/异议申请 */
    private static int objectionDays = 0;

    private GradeScoreStore() {}

    /** 异议窗口：以本人该课程最近一次成绩登记时间为发布基准。 */
    public static Map<String, Object> objectionWindow(String username, long courseId) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("days", objectionDays);
        out.put("open", false);
        out.put("dueAt", "");
        out.put("publishedAt", "");
        if (objectionDays <= 0 || !ready()) return out;
        String user = clip(username, 64);
        if (user.isEmpty() || courseId <= 0) return out;
        try {
            LocalDate base = parseDay(mapper().selectPublishedAt(user, courseId));
            if (base == null) return out;
            LocalDate due = base.plusDays(objectionDays);
            out.put("publishedAt", base.toString());
            out.put("dueAt", due.toString());
            out.put("open", !LocalDate.now().isAfter(due));
        } catch (Exception ignored) {
            // 成绩表不可用按未开处理
        }
        return out;
    }
"""
    + GRADE_TAIL_SHARED
)

GRADE_IMPORT_OLD = """import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;"""

GRADE_IMPORT_NEW = """import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;"""

JP_GRADE_META_OLD = """        out.put("courses", courses);
        return out;"""

JP_GRADE_META_NEW = """        out.put("courses", courses);
        out.put("objectionDays", objectionDays);
        return out;"""

JP_GRADE_MINE_OLD = """        return db().query(
                RANK_SQL + "WHERE s.username=? ORDER BY s.term_id, s.course_id",
                (rs, i) -> mapRow(rs),
                username);
    }"""

JP_GRADE_MINE_NEW = """        List<Map<String, Object>> rows = db().query(
                RANK_SQL + "WHERE s.username=? ORDER BY s.term_id, s.course_id",
                (rs, i) -> mapRow(rs),
                username);
        if (objectionDays <= 0) return rows;
        for (Map<String, Object> row : rows) {
            long courseId = row.get("courseId") instanceof Number n ? n.longValue() : 0L;
            Map<String, Object> w = objectionWindow(username, courseId);
            row.put("objectionDueAt", w.get("dueAt"));
            row.put("objectionOpen", w.get("open"));
        }
        return rows;
    }"""

MB_GRADE_META_OLD = """        out.put("courses", mapper().listCourses());
        return out;"""

MB_GRADE_META_NEW = """        out.put("courses", mapper().listCourses());
        out.put("objectionDays", objectionDays);
        return out;"""

MB_GRADE_MINE_OLD = """        return mapper().listMine(username).stream().map(GradeScoreStore::normalize).toList();
    }"""

MB_GRADE_MINE_NEW = """        List<Map<String, Object>> rows = new java.util.ArrayList<>(
                mapper().listMine(username).stream().map(GradeScoreStore::normalize).toList());
        if (objectionDays <= 0) return rows;
        for (Map<String, Object> row : rows) {
            long courseId = row.get("courseId") instanceof Number n ? n.longValue() : 0L;
            Map<String, Object> w = objectionWindow(username, courseId);
            row.put("objectionDueAt", w.get("dueAt"));
            row.put("objectionOpen", w.get("open"));
        }
        return rows;
    }"""

MB_GRADE_MAPPER_OLD = """    @Select("SELECT COUNT(*) FROM course_item WHERE id=#{id}")"""

MB_GRADE_MAPPER_NEW = """    @Select("SELECT DATE_FORMAT(MAX(created_at), '%Y-%m-%d') FROM grade_score "
            + "WHERE username=#{username} AND course_id=#{courseId}")
    String selectPublishedAt(
            @Param("username") String username, @Param("courseId") long courseId);

    @Select("SELECT COUNT(*) FROM course_item WHERE id=#{id}")"""

# ------------------------------------------------------------------ patches
# (tag, path, old, new, marker)：marker 命中即视为已同步（幂等）。
PATCHES: list[tuple[str, Path, str, str, str]] = [
    ("mb:ticket-helpers", mbTS, TS_HELPERS_OLD, TS_HELPERS_NEW, "static int levelSlaHighDays = 1;"),
    ("jp:ticket-helpers", jpTS, TS_HELPERS_OLD, TS_HELPERS_NEW, "static int levelSlaHighDays = 1;"),
    ("mb:ticket-import", mbTS, TS_IMPORT_OLD, TS_IMPORT_NEW, "import java.time.LocalDate;"),
    ("jp:ticket-import", jpTS, TS_IMPORT_OLD, TS_IMPORT_NEW, "import java.time.LocalDate;"),
    ("mb:ticket-due-archive", mbTS, MB_DUE_OLD, MB_DUE_NEW, "plusDays(levelSlaDays(m, loanDays()))"),
    ("jp:ticket-due-archive", jpTS, JP_DUE_ARCHIVE_OLD, JP_DUE_ARCHIVE_NEW, "plusDays(levelSlaDays(m, loanDays()))"),
    ("jp:ticket-due-standalone", jpTS, JP_DUE_STANDALONE_OLD, JP_DUE_STANDALONE_NEW, "独立工单 SLA：等级影响时限时按等级取天数"),
    ("mb:ticket-apply-tail", mbTS, APPLY_TAIL_OLD, APPLY_TAIL_NEW, "notifyDutyOnNewReport(id, username, subjectOf(applied))"),
    ("jp:ticket-apply-tail", jpTS, APPLY_TAIL_OLD, APPLY_TAIL_NEW, "notifyDutyOnNewReport(id, username, subjectOf(applied))"),
    ("mb:ticket-std-tail", mbTS, STD_TAIL_OLD, STD_TAIL_NEW, 'createdStd.put("dutyNotified"'),
    ("jp:ticket-std-tail", jpTS, STD_TAIL_OLD, STD_TAIL_NEW, 'createdStd.put("dutyNotified"'),
    ("mb:ticket-page-out", mbTS, PAGE_OUT_OLD, PAGE_OUT_NEW, 'out.put("levelSlaDays"'),
    ("jp:ticket-page-out", jpTS, PAGE_OUT_OLD, PAGE_OUT_NEW, 'out.put("levelSlaDays"'),
    ("mb:binder-import", mbBINDER, BINDER_IMPORT_OLD, BINDER_IMPORT_NEW, "import com.thesis.service.FundPublicityStore;"),
    ("jp:binder-import", jpBINDER, BINDER_IMPORT_OLD, BINDER_IMPORT_NEW, "import com.thesis.service.FundPublicityStore;"),
    ("mb:binder-fields", mbBINDER, BINDER_FIELDS_OLD, BINDER_FIELDS_NEW, "thesis.ticket-level-affects-deadline"),
    ("jp:binder-fields", jpBINDER, BINDER_FIELDS_OLD, BINDER_FIELDS_NEW, "thesis.ticket-level-affects-deadline"),
    ("mb:binder-call", mbBINDER, BINDER_CALL_OLD, BINDER_CALL_NEW, "TicketStore.configureEventOps("),
    ("jp:binder-call", jpBINDER, BINDER_CALL_OLD, BINDER_CALL_NEW, "TicketStore.configureEventOps("),
    ("mb:fund-head", mbFUND, FUND_HEAD_MB_OLD, FUND_HEAD_MB_NEW + FUND_FIELDS_TAIL_NEW, "public static void configureObjection("),
    ("jp:fund-head", jpFUND, FUND_HEAD_JP_OLD, FUND_HEAD_JP_NEW + FUND_FIELDS_TAIL_NEW, "public static void configureObjection("),
    ("mb:fund-import", mbFUND, FUND_IMPORT_OLD, FUND_IMPORT_NEW, "import java.time.LocalDate;"),
    ("jp:fund-import", jpFUND, FUND_IMPORT_OLD, FUND_IMPORT_NEW, "import java.time.LocalDate;"),
    ("mb:fund-select", mbFUND, FUND_SELECT_OLD, FUND_SELECT_NEW, "AS objection_due_at"),
    ("jp:fund-select", jpFUND, FUND_SELECT_OLD, FUND_SELECT_NEW, "AS objection_due_at"),
    ("mb:fund-maprow", mbFUND, FUND_MAPROW_OLD, FUND_MAPROW_NEW, 'm.put("objectionDueAt"'),
    ("jp:fund-maprow", jpFUND, FUND_MAPROW_OLD, FUND_MAPROW_NEW, 'm.put("objectionDueAt"'),
    ("mb:fund-save-window", mbFUND, FUND_SAVE_OLD, FUND_SAVE_NEW, "SET objection_due_at=?"),
    ("jp:fund-save-window", jpFUND, FUND_SAVE_OLD, FUND_SAVE_NEW, "SET objection_due_at=?"),
    ("mb:fund-objection", mbFUND, FUND_OBJECTION_OLD, FUND_OBJECTION_NEW, "public static Map<String, Object> submitObjection("),
    ("jp:fund-objection", jpFUND, FUND_OBJECTION_OLD, FUND_OBJECTION_NEW, "public static Map<String, Object> submitObjection("),
    ("jp:grade-fields", jpGRADE, GRADE_FIELDS_OLD, JP_GRADE_FIELDS_NEW, "static int objectionDays = 0;"),
    ("mb:grade-fields", mbGRADE, GRADE_FIELDS_OLD, MB_GRADE_FIELDS_NEW, "static int objectionDays = 0;"),
    ("jp:grade-import", jpGRADE, GRADE_IMPORT_OLD, GRADE_IMPORT_NEW, "import java.time.LocalDate;"),
    ("mb:grade-import", mbGRADE, GRADE_IMPORT_OLD, GRADE_IMPORT_NEW, "import java.time.LocalDate;"),
    ("jp:grade-meta", jpGRADE, JP_GRADE_META_OLD, JP_GRADE_META_NEW, 'out.put("objectionDays"'),
    ("mb:grade-meta", mbGRADE, MB_GRADE_META_OLD, MB_GRADE_META_NEW, 'out.put("objectionDays"'),
    ("jp:grade-mine", jpGRADE, JP_GRADE_MINE_OLD, JP_GRADE_MINE_NEW, 'row.put("objectionDueAt"'),
    ("mb:grade-mine", mbGRADE, MB_GRADE_MINE_OLD, MB_GRADE_MINE_NEW, 'row.put("objectionDueAt"'),
    ("mb:grade-mapper", mbGRADE_MAPPER, MB_GRADE_MAPPER_OLD, MB_GRADE_MAPPER_NEW, "selectPublishedAt("),
]


def main() -> None:
    cache: dict[Path, str] = {}
    crlf: dict[Path, bool] = {}
    changed = 0
    for tag, path, old, new, marker in PATCHES:
        if not path.is_file():
            raise SystemExit(f"[FAIL] {tag}: 文件不存在 {path}")
        if path not in cache:
            raw = path.read_text(encoding="utf-8")
            crlf[path] = "\r\n" in raw
            cache[path] = raw.replace("\r\n", "\n")
        text = cache[path]
        if marker in text:
            print(f"[SKIP] {tag}: 已同步")
            continue
        hits = text.count(old)
        if hits != 1:
            raise SystemExit(f"[FAIL] {tag}: 锚点命中 {hits} 次（应为 1）")
        cache[path] = text.replace(old, new, 1)
        changed += 1
        print(f"[OK  ] {tag}")
    for path, text in cache.items():
        out = text.replace("\n", "\r\n") if crlf.get(path) else text
        path.write_text(out, encoding="utf-8")
    print(f"[DONE] 已更新 {len(cache)} 个文件，{changed} 处变更")


if __name__ == "__main__":
    sys.exit(main())
