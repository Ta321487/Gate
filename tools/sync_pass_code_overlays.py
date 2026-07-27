"""同步 C-09 issuePassCode 到 mybatis/jpa overlays。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVS = [
    ROOT / "skeletons" / "overlays" / "persistence-mybatis" / "backend" / "src" / "main" / "java" / "com" / "thesis",
    ROOT / "skeletons" / "overlays" / "persistence-jpa" / "backend" / "src" / "main" / "java" / "com" / "thesis",
]

ISSUE_METHOD = r'''
    /** C-09：通过后签发演示通行码（字符串；非硬件门禁）。 */
    private static String issuePassCodeIfNeeded(long ticketId) {
        if (!issuePassCode || !hasColumn("pass_code") || ticketId <= 0) return "";
        try {
            Map<String, Object> cur = get(ticketId);
            if (cur != null) {
                String prev = TicketSql.str(cur.get("passCode"));
                if (!prev.isBlank()) return prev;
            }
            String code = "VIS" + String.format("%08d", Math.floorMod(System.nanoTime(), 100_000_000));
            TicketSql.db().update("UPDATE " + TICKET + " SET pass_code=? WHERE id=?", code, ticketId);
            appendProgress(ticketId, "pass_code", "system", "通行码 " + code);
            return code;
        } catch (Exception ignored) {
            return "";
        }
    }

'''


def patch_ticket(path: Path) -> None:
    t = path.read_text(encoding="utf-8")
    if "configureIssuePassCode" in t:
        print("skip ticket", path)
        return
    t = t.replace(
        "    /** C-05：档案主人可确认/拒绝志愿（互选） */\n    static boolean peerAccept = false;\n",
        "    /** C-05：档案主人可确认/拒绝志愿（互选） */\n    static boolean peerAccept = false;\n"
        "    /** C-09：审核通过签发演示通行码（非真门禁） */\n"
        "    static boolean issuePassCode = false;\n",
        1,
    )
    t = t.replace(
        "    public static boolean isPeerAccept() {\n"
        "        return peerAccept;\n"
        "    }\n\n"
        "    public static void configureNoShow",
        "    public static boolean isPeerAccept() {\n"
        "        return peerAccept;\n"
        "    }\n\n"
        "    public static void configureIssuePassCode(boolean enabled) {\n"
        "        issuePassCode = enabled;\n"
        "    }\n\n"
        "    public static boolean isIssuePassCode() {\n"
        "        return issuePassCode;\n"
        "    }\n\n"
        "    public static void configureNoShow",
        1,
    )
    t = t.replace(
        "        notifyTicketResult(m, true, note);\n"
        "        appendProgress(ticketId, \"approved\", op, note.isBlank()\n"
        "                ? TicketCopy.stateLabel(\"approved\", TicketCopy.verbLabel(\"approve\", \"审核通过\")) : note);",
        "        String passCode = issuePassCodeIfNeeded(ticketId);\n"
        "        notifyTicketResult(m, true, note, passCode);\n"
        "        appendProgress(ticketId, \"approved\", op, note.isBlank()\n"
        "                ? TicketCopy.stateLabel(\"approved\", TicketCopy.verbLabel(\"approve\", \"审核通过\")) : note);",
        1,
    )
    # insert issuePassCodeIfNeeded before notifyTicketResult or after approve return block
    if "issuePassCodeIfNeeded" not in t:
        # place after autoRejected block's closing - use notifyTicketResult private method as anchor
        old_notify = (
            "    /** 审核结果写入申请人站内消息（无表或失败则静默跳过） */\n"
            "    private static void notifyTicketResult(Map<String, Object> ticket, boolean pass, String note) {\n"
            "        try {\n"
            "            String user = TicketSql.str(ticket.get(\"username\"));\n"
            "            if (user.isBlank()) return;\n"
            "            String subject = subjectOf(ticket);\n"
            "            String title = pass ? \"审核已通过\" : \"审核未通过\";\n"
            "            String body = pass\n"
            "                    ? (\"「\" + subject + \"」已通过\" + (note == null || note.isBlank() ? \"\" : \"：\" + note))\n"
            "                    : (\"「\" + subject + \"」已驳回\" + (note == null || note.isBlank() ? \"\" : \"：\" + note));\n"
            "            if (pass && hasColumn(\"pickup_at\") && !bizPickupPlace.isBlank()) {\n"
            "                body = body + \"。请到「\" + bizPickupPlace + \"」领取，到场后由工作人员登记实发。\";\n"
            "            }\n"
            "            MessageStore.send(user, title, body, \"ticket\", TicketSql.toLong(ticket.get(\"id\")));\n"
            "        } catch (Exception ignored) {\n"
            "            // 消息失败不影响主流程\n"
            "        }\n"
            "    }\n"
        )
        new_notify = (
            ISSUE_METHOD
            + "    /** 审核结果写入申请人站内消息（无表或失败则静默跳过） */\n"
            "    private static void notifyTicketResult(Map<String, Object> ticket, boolean pass, String note) {\n"
            "        notifyTicketResult(ticket, pass, note, \"\");\n"
            "    }\n\n"
            "    private static void notifyTicketResult(Map<String, Object> ticket, boolean pass, String note, String passCode) {\n"
            "        try {\n"
            "            String user = TicketSql.str(ticket.get(\"username\"));\n"
            "            if (user.isBlank()) return;\n"
            "            String subject = subjectOf(ticket);\n"
            "            String title = pass ? \"审核已通过\" : \"审核未通过\";\n"
            "            String body = pass\n"
            "                    ? (\"「\" + subject + \"」已通过\" + (note == null || note.isBlank() ? \"\" : \"：\" + note))\n"
            "                    : (\"「\" + subject + \"」已驳回\" + (note == null || note.isBlank() ? \"\" : \"：\" + note));\n"
            "            if (pass && hasColumn(\"pickup_at\") && !bizPickupPlace.isBlank()) {\n"
            "                body = body + \"。请到「\" + bizPickupPlace + \"」领取，到场后由工作人员登记实发。\";\n"
            "            }\n"
            "            if (pass && passCode != null && !passCode.isBlank()) {\n"
            "                body = body + \"。演示通行码：\" + passCode + \"（非真门禁，到访时出示即可）。\";\n"
            "            }\n"
            "            MessageStore.send(user, title, body, \"ticket\", TicketSql.toLong(ticket.get(\"id\")));\n"
            "        } catch (Exception ignored) {\n"
            "            // 消息失败不影响主流程\n"
            "        }\n"
            "    }\n"
        )
        if old_notify not in t:
            raise SystemExit(f"miss notify block: {path}")
        t = t.replace(old_notify, new_notify, 1)
    path.write_text(t, encoding="utf-8")
    print("ok ticket", path)


def patch_binder(path: Path) -> None:
    t = path.read_text(encoding="utf-8")
    if "ticketIssuePassCode" in t:
        print("skip binder", path)
        return
    t = t.replace(
        '    @Value("${thesis.ticket-peer-accept:false}")\n'
        "    private boolean ticketPeerAccept;\n",
        '    @Value("${thesis.ticket-peer-accept:false}")\n'
        "    private boolean ticketPeerAccept;\n\n"
        '    @Value("${thesis.ticket-issue-pass-code:false}")\n'
        "    private boolean ticketIssuePassCode;\n",
        1,
    )
    t = t.replace(
        "            TicketStore.configurePeerAccept(ticketPeerAccept);\n"
        "            TicketStore.configureNoShow(ticketNoShowAfterEnd, ticketNoShowPenaltyYuan);\n",
        "            TicketStore.configurePeerAccept(ticketPeerAccept);\n"
        "            TicketStore.configureIssuePassCode(ticketIssuePassCode);\n"
        "            TicketStore.configureNoShow(ticketNoShowAfterEnd, ticketNoShowPenaltyYuan);\n",
        1,
    )
    path.write_text(t, encoding="utf-8")
    print("ok binder", path)


def patch_rowmaps(path: Path) -> None:
    if not path.is_file():
        print("skip rowmaps missing", path)
        return
    t = path.read_text(encoding="utf-8")
    if '"passCode"' in t or "pass_code" in t:
        print("skip rowmaps", path)
        return
    t = t.replace(
        'm.put("checkedInAt", TicketSql.fmt(TicketSql.safeTs(rs, "checked_in_at")));',
        'm.put("checkedInAt", TicketSql.fmt(TicketSql.safeTs(rs, "checked_in_at")));\n'
        '        m.put("passCode", TicketSql.safeStr(rs, "pass_code"));',
        1,
    )
    path.write_text(t, encoding="utf-8")
    print("ok rowmaps", path)


def main() -> None:
    for ov in OVS:
        patch_ticket(ov / "capability" / "TicketStore.java")
        patch_binder(ov / "config" / "DomainRuntimeBinder.java")
        patch_rowmaps(ov / "capability" / "TicketRowMaps.java")
    print("done")


if __name__ == "__main__":
    main()
