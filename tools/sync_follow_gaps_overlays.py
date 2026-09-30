"""把跟进组 7 键闭环同步到 persistence-mybatis overlay。

jpa overlay 由 tools/gen_persistence_jpa_overlay.py 从 baseline 全量重建，本脚本只负责 mybatis。
每处 patch 都做唯一性断言，缺锚点或已打过（幂等）都明确报错。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MB = ROOT / "skeletons" / "overlays" / "persistence-mybatis" / "backend" / "src" / "main"
TS = MB / "java" / "com" / "thesis" / "capability" / "TicketStore.java"
BINDER = MB / "java" / "com" / "thesis" / "config" / "DomainRuntimeBinder.java"
MAPPER = MB / "java" / "com" / "thesis" / "mapper" / "TicketMapper.java"
MAPPER_XML = MB / "resources" / "mapper" / "TicketMapper.xml"

MARK = "configureFollowOps"

FIELDS_OLD = """    static int maxReviseTimes = 0;
    static boolean requireCloseAttach = false;"""

FIELDS_NEW = """    static int maxReviseTimes = 0;
    /** 未跟进 N 天列表筛（0=关） */
    static int staleFollowDays = 0;
    /** 同联系电话拦重号（开题扫 CRM 查重提示） */
    static boolean phoneDupCheck = false;
    static boolean requireCloseAttach = false;"""

CONF_OLD = """        weekReportDeadlineDay = Math.max(0, Math.min(28, weekReportDeadlineDayIn));
    }"""

CONF_NEW = """        weekReportDeadlineDay = Math.max(0, Math.min(28, weekReportDeadlineDayIn));
    }

    /** 跟进组列表闸：未跟进 N 天筛 + 同联系电话拦重号。 */
    public static void configureFollowOps(int staleFollowDaysIn, boolean phoneDupCheckIn) {
        staleFollowDays = Math.max(0, Math.min(90, staleFollowDaysIn));
        phoneDupCheck = phoneDupCheckIn;
    }"""

DUP_OLD = """    /** 同房间未结同类提示（浅：返回文案，不阻断提交）。 */"""

DUP_NEW = """    /** 同联系电话是否已有未办结单；返回单据号（0=未开或未命中）。 */
    static long dupPhoneOpenId(String phone) {
        if (!phoneDupCheck || !hasColumn("contact_phone")) return 0L;
        String p = phone == null ? "" : phone.trim();
        if (p.isBlank()) return 0L;
        try {
            Long hit = mapper().selectOpenIdByPhone(TICKET, p);
            return hit == null ? 0L : hit;
        } catch (Exception ignored) {
            return 0L;
        }
    }

""" + DUP_OLD

HOOK_OLD = """        if (t.isBlank()) throw new IllegalArgumentException("请填写标题");"""

HOOK_NEW = """        if (t.isBlank()) throw new IllegalArgumentException("请填写标题");
        long dupPhoneId = dupPhoneOpenId(contactPhone);
        if (dupPhoneId > 0) {
            throw new IllegalStateException(
                    "该联系电话已有未办结单据#" + dupPhoneId + "，请确认是否重复提交。");
        }"""

STALE_OLD = """            if ("todo".equals(status)) {
                q.put("statusTodo", true);
            } else {
                q.put("statusExact", status);
            }"""

STALE_NEW = """            if ("todo".equals(status)) {
                q.put("statusTodo", true);
            } else if ("stale".equals(status) && staleFollowDays > 0 && hasColumn("next_follow_at")) {
                // 未跟进 N 天：无下次跟进或已过期 N 天以上的未结单
                q.put("statusStale", true);
                q.put("staleBefore", LocalDateTime.now().minusDays(staleFollowDays).format(TicketSql.FMT));
            } else {
                q.put("statusExact", status);
            }"""

OUT_OLD = """        out.put("size", size);
        return out;
    }

    /**
     * 内容举报下架：将回帖/单据标为 rejected，从前台楼层消失。"""

OUT_NEW = """        out.put("size", size);
        out.put("staleFollowDays", staleFollowDays);
        return out;
    }

    /**
     * 内容举报下架：将回帖/单据标为 rejected，从前台楼层消失。"""

REVISE_OLD = """    /**
     * 内容举报下架：将回帖/单据标为 rejected，从前台楼层消失。"""

REVISE_NEW = """    /**
     * 管理端退回修改：revise_count 记库；maxReviseTimes&gt;0 时超上限拒绝。
     */
    public static Map<String, Object> returnForRevise(long ticketId, String op, String note) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String st = String.valueOf(m.get("status"));
        if (!"pending".equals(st) && !"pending_mid".equals(st) && !"pending_final".equals(st)) {
            throw new IllegalStateException("仅待审单据可退回修改");
        }
        int used = reviseCountOf(m);
        if (maxReviseTimes > 0 && used >= maxReviseTimes) {
            throw new IllegalStateException(
                    "退回修改次数已达上限（" + maxReviseTimes + " 次），请直接驳回或联系管理员。");
        }
        int next = used + 1;
        String reason = note == null || note.isBlank() ? ("退回修改第 " + next + " 次") : note.trim();
        if (hasColumn("revise_count")) {
            mapper().updateReturnRevise(TICKET, ticketId, next);
        } else {
            mapper().updateStatus(TICKET, "returned", ticketId);
        }
        appendProgress(ticketId, "returned", op == null ? "" : op, reason);
        return get(ticketId);
    }

    /** 用户重新提交被退回的单据；修改次数未超上限才放行。 */
    public static Map<String, Object> resubmit(long ticketId, String username, String remark) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!String.valueOf(m.get("username")).equals(username)) {
            throw new IllegalStateException("只能重新提交自己的单据");
        }
        if (!"returned".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅被退回的单据可重新提交");
        }
        if (maxReviseTimes > 0 && reviseCountOf(m) >= maxReviseTimes) {
            throw new IllegalStateException("修改次数已达上限（" + maxReviseTimes + " 次），请联系管理员。");
        }
        mapper().updateStatus(TICKET, "pending", ticketId);
        appendProgress(ticketId, "pending", username,
                remark == null || remark.isBlank() ? "重新提交" : remark.trim());
        return get(ticketId);
    }

    private static int reviseCountOf(Map<String, Object> m) {
        return m.get("reviseCount") instanceof Number n ? n.intValue() : 0;
    }

""" + REVISE_OLD


BINDER_FIELD_OLD = """    @Value("${thesis.ticket-max-revise-times:0}")
    private int ticketMaxReviseTimes;"""

BINDER_FIELD_NEW = """    @Value("${thesis.ticket-max-revise-times:0}")
    private int ticketMaxReviseTimes;

    @Value("${thesis.ticket-stale-follow-days:0}")
    private int ticketStaleFollowDays;

    @Value("${thesis.ticket-phone-dup-check:false}")
    private boolean ticketPhoneDupCheck;"""

BINDER_CALL_OLD = """                    ticketWeekReportDeadlineDay);"""

BINDER_CALL_NEW = """                    ticketWeekReportDeadlineDay);
            TicketStore.configureFollowOps(ticketStaleFollowDays, ticketPhoneDupCheck);"""

MAPPER_OLD = """    @Update("UPDATE `${ticketTable}` SET status=#{status} WHERE id=#{id}")
    int updateStatus("""

MAPPER_NEW = """    @Select("SELECT id FROM `${ticketTable}` WHERE contact_phone=#{phone} "
            + "AND status IN ('pending','pending_final','pending_mid','approved','overdue','paused') "
            + "ORDER BY id DESC LIMIT 1")
    Long selectOpenIdByPhone(
            @Param("ticketTable") String ticketTable,
            @Param("phone") String phone);

    @Update("UPDATE `${ticketTable}` SET status='returned', revise_count=#{count} WHERE id=#{id}")
    int updateReturnRevise(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("count") int count);

""" + MAPPER_OLD

XML_OLD = """            <if test="statusTodo">
                AND status IN ('pending','pending_mid','pending_final','hold_ready','verifying')
            </if>"""

XML_NEW = """            <if test="statusTodo">
                AND status IN ('pending','pending_mid','pending_final','hold_ready','verifying')
            </if>
            <if test="statusStale">
                AND status IN ('pending','pending_mid','pending_final','approved','overdue','paused')
                AND (next_follow_at IS NULL OR next_follow_at &lt;= #{staleBefore})
            </if>"""

JPA = ROOT / "skeletons" / "overlays" / "persistence-jpa" / "backend" / "src" / "main"
jTS = JPA / "java" / "com" / "thesis" / "capability" / "TicketStore.java"
jBINDER = JPA / "java" / "com" / "thesis" / "config" / "DomainRuntimeBinder.java"

# jpa 为手改变体：page 的 status/out 段与 baseline 不同，且没有 saveDraft/dup 提示方法
JPA_ANCHOR = """    /**
     * 内容举报下架：将回帖/单据标为 rejected，从前台楼层消失。"""

JPA_DUP_NEW = """    /** 同联系电话是否已有未办结单；返回单据号（0=未开或未命中）。 */
    static long dupPhoneOpenId(String phone) {
        if (!phoneDupCheck || !hasColumn("contact_phone")) return 0L;
        String p = phone == null ? "" : phone.trim();
        if (p.isBlank()) return 0L;
        try {
            Long hit = TicketSql.db().queryForObject(
                    "SELECT id FROM " + TICKET
                            + " WHERE contact_phone=? AND status IN"
                            + " ('pending','pending_final','pending_mid','approved','overdue','paused')"
                            + " ORDER BY id DESC LIMIT 1",
                    Long.class, p);
            return hit == null ? 0L : hit;
        } catch (Exception ignored) {
            return 0L;
        }
    }

""" + JPA_ANCHOR

JPA_STALE_OLD = """        if (status != null && !status.isBlank()) {
            if ("todo".equals(status)) {
                where.append(" AND status IN ('pending','pending_mid','pending_final','verifying')");
            } else {
                where.append(" AND status=?");
                args.add(status);
            }
        }"""

JPA_STALE_NEW = """        if (status != null && !status.isBlank()) {
            if ("todo".equals(status)) {
                where.append(" AND status IN ('pending','pending_mid','pending_final','verifying')");
            } else if ("stale".equals(status) && staleFollowDays > 0 && hasColumn("next_follow_at")) {
                // 未跟进 N 天：无下次跟进或已过期 N 天以上的未结单
                where.append(" AND status IN ('pending','pending_mid','pending_final','approved','overdue','paused')")
                        .append(" AND (next_follow_at IS NULL OR next_follow_at <= ?)");
                args.add(Timestamp.valueOf(LocalDateTime.now().minusDays(staleFollowDays)));
            } else {
                where.append(" AND status=?");
                args.add(status);
            }
        }"""

JPA_OUT_OLD = """                (rs, i) -> TicketStatusOps.enrich(TicketRowMaps.mapRow(rs)), args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }"""

JPA_OUT_NEW = """                (rs, i) -> TicketStatusOps.enrich(TicketRowMaps.mapRow(rs)), args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        out.put("staleFollowDays", staleFollowDays);
        return out;
    }"""

JPA_REVISE_NEW = """    /**
     * 管理端退回修改：revise_count 记库；maxReviseTimes&gt;0 时超上限拒绝。
     */
    public static Map<String, Object> returnForRevise(long ticketId, String op, String note) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        String st = String.valueOf(m.get("status"));
        if (!"pending".equals(st) && !"pending_mid".equals(st) && !"pending_final".equals(st)) {
            throw new IllegalStateException("仅待审单据可退回修改");
        }
        int used = reviseCountOf(m);
        if (maxReviseTimes > 0 && used >= maxReviseTimes) {
            throw new IllegalStateException(
                    "退回修改次数已达上限（" + maxReviseTimes + " 次），请直接驳回或联系管理员。");
        }
        int next = used + 1;
        String reason = note == null || note.isBlank() ? ("退回修改第 " + next + " 次") : note.trim();
        if (hasColumn("revise_count")) {
            TicketSql.db().update(
                    "UPDATE " + TICKET + " SET status='returned', revise_count=? WHERE id=?",
                    next, ticketId);
        } else {
            TicketSql.db().update("UPDATE " + TICKET + " SET status='returned' WHERE id=?", ticketId);
        }
        appendProgress(ticketId, "returned", op == null ? "" : op, reason);
        return get(ticketId);
    }

    /** 用户重新提交被退回的单据；修改次数未超上限才放行。 */
    public static Map<String, Object> resubmit(long ticketId, String username, String remark) {
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!String.valueOf(m.get("username")).equals(username)) {
            throw new IllegalStateException("只能重新提交自己的单据");
        }
        if (!"returned".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅被退回的单据可重新提交");
        }
        if (maxReviseTimes > 0 && reviseCountOf(m) >= maxReviseTimes) {
            throw new IllegalStateException("修改次数已达上限（" + maxReviseTimes + " 次），请联系管理员。");
        }
        TicketSql.db().update("UPDATE " + TICKET + " SET status='pending' WHERE id=?", ticketId);
        appendProgress(ticketId, "pending", username,
                remark == null || remark.isBlank() ? "重新提交" : remark.trim());
        return get(ticketId);
    }

    private static int reviseCountOf(Map<String, Object> m) {
        return m.get("reviseCount") instanceof Number n ? n.intValue() : 0;
    }

""" + JPA_ANCHOR

PATCHES: list[tuple[str, Path, str, str, str]] = [
    ("mybatis:fields", TS, FIELDS_OLD, FIELDS_NEW, "static int staleFollowDays = 0;"),
    ("mybatis:configureFollowOps", TS, CONF_OLD, CONF_NEW, "public static void configureFollowOps("),
    ("mybatis:dupPhoneOpenId", TS, DUP_OLD, DUP_NEW, "static long dupPhoneOpenId(String phone) {"),
    ("mybatis:applyStandalone-hook", TS, HOOK_OLD, HOOK_NEW, "long dupPhoneId = dupPhoneOpenId(contactPhone);"),
    ("mybatis:page-stale", TS, STALE_OLD, STALE_NEW, '"stale".equals(status) && staleFollowDays > 0'),
    ("mybatis:page-out", TS, OUT_OLD, OUT_NEW, 'out.put("staleFollowDays"'),
    ("mybatis:revise-actions", TS, REVISE_OLD, REVISE_NEW, "public static Map<String, Object> returnForRevise("),
    ("mybatis:binder-fields", BINDER, BINDER_FIELD_OLD, BINDER_FIELD_NEW, "thesis.ticket-stale-follow-days"),
    ("mybatis:binder-call", BINDER, BINDER_CALL_OLD, BINDER_CALL_NEW, "TicketStore.configureFollowOps(ticketStaleFollowDays"),
    ("mybatis:mapper-methods", MAPPER, MAPPER_OLD, MAPPER_NEW, "Long selectOpenIdByPhone("),
    ("mybatis:mapper-xml-stale", MAPPER_XML, XML_OLD, XML_NEW, 'test="statusStale"'),
    ("jpa:fields", jTS, FIELDS_OLD, FIELDS_NEW, "static int staleFollowDays = 0;"),
    ("jpa:configureFollowOps", jTS, CONF_OLD, CONF_NEW, "public static void configureFollowOps("),
    ("jpa:dupPhoneOpenId", jTS, JPA_ANCHOR, JPA_DUP_NEW, "static long dupPhoneOpenId(String phone) {"),
    ("jpa:applyStandalone-hook", jTS, HOOK_OLD, HOOK_NEW, "long dupPhoneId = dupPhoneOpenId(contactPhone);"),
    ("jpa:page-stale", jTS, JPA_STALE_OLD, JPA_STALE_NEW, '"stale".equals(status) && staleFollowDays > 0'),
    ("jpa:page-out", jTS, JPA_OUT_OLD, JPA_OUT_NEW, 'out.put("staleFollowDays"'),
    ("jpa:revise-actions", jTS, JPA_ANCHOR, JPA_REVISE_NEW, "public static Map<String, Object> returnForRevise("),
    ("jpa:binder-fields", jBINDER, BINDER_FIELD_OLD, BINDER_FIELD_NEW, "thesis.ticket-stale-follow-days"),
    ("jpa:binder-call", jBINDER, BINDER_CALL_OLD, BINDER_CALL_NEW, "TicketStore.configureFollowOps(ticketStaleFollowDays"),
]


def main() -> None:
    cache: dict[Path, str] = {}
    changed = 0
    for tag, path, old, new, marker in PATCHES:
        if not path.is_file():
            raise SystemExit(f"[FAIL] {tag}: 文件不存在 {path}")
        text = cache.get(path, path.read_text(encoding="utf-8"))
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
        path.write_text(text, encoding="utf-8", newline="\n")
    if not cache:
        print("[DONE] 无变更：" + MARK + " 已就位")
    else:
        print(f"[DONE] 已更新 {len(cache)} 个文件，{changed} 处变更")


if __name__ == "__main__":
    main()
