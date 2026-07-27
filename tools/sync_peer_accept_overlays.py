"""把 baseline 的 peerAccept 能力同步到 mybatis/jpa TicketStore / DomainRuntimeBinder / ArchiveStore。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVS = [
    ROOT / "skeletons" / "overlays" / "persistence-mybatis" / "backend" / "src" / "main" / "java" / "com" / "thesis",
    ROOT / "skeletons" / "overlays" / "persistence-jpa" / "backend" / "src" / "main" / "java" / "com" / "thesis",
]

PEER_METHODS = r'''
    private static void notifyPeerOwnerNewTicket(long ticketId, long itemId, String applicant, String subject) {
        if (!peerAccept || ticketId <= 0 || itemId <= 0) return;
        try {
            Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
            if (item == null) return;
            String owner = TicketSql.str(item.get("ownerUsername"));
            if (owner.isBlank() || owner.equals(applicant)) return;
            String sub = subject == null || subject.isBlank() ? ("单据#" + ticketId) : subject;
            String who = UserStore.displayName(applicant);
            MessageStore.send(
                    owner,
                    "待确认志愿",
                    who + " 向「" + sub + "」提交了志愿，请确认或婉拒。",
                    "ticket",
                    ticketId);
        } catch (Exception ignored) {
        }
    }

    /** C-05：档案主人确认/拒绝志愿；通过时复用 approve 扣库存。 */
    public static Map<String, Object> peerRespond(long ticketId, String username, boolean pass, String remark) {
        if (!peerAccept) throw new IllegalStateException("当前未开启互选确认");
        if (MODE != Mode.ARCHIVE) throw new IllegalStateException("当前不支持互选确认");
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
        Map<String, Object> out = approve(ticketId, pass, note, username, true);
        appendProgress(
                ticketId,
                pass ? "peer_accept" : "peer_reject",
                username,
                pass ? "对方确认" : (note.isBlank() ? "对方婉拒" : note));
        return out;
    }

    /** 待我确认：档案 owner_username=我 且待审的志愿单。 */
    public static Map<String, Object> pagePeerInbox(String ownerUsername, String status, int page, int size) {
        if (!peerAccept || MODE != Mode.ARCHIVE) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("list", List.of());
            empty.put("total", 0);
            empty.put("page", Math.max(1, page));
            empty.put("size", Math.max(1, size));
            return empty;
        }
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        String owner = ownerUsername == null ? "" : ownerUsername.trim();
        if (owner.isBlank()) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("list", List.of());
            empty.put("total", 0);
            empty.put("page", page);
            empty.put("size", size);
            return empty;
        }
        String itemTable = ArchiveStore.itemTable();
        String fk = itemFkColumn();
        StringBuilder where = new StringBuilder(
                " WHERE i.owner_username=? AND t." + fk + "=i.id");
        List<Object> args = new ArrayList<>();
        args.add(owner);
        if (status != null && !status.isBlank()) {
            where.append(" AND t.status=?");
            args.add(status);
        } else {
            where.append(" AND t.status='pending'");
        }
        String from = " FROM " + TICKET + " t JOIN " + itemTable + " i ON t." + fk + "=i.id";
        Integer total = TicketSql.db().queryForObject(
                "SELECT COUNT(*)" + from + where, Integer.class, args.toArray());
        int t = total == null ? 0 : total;
        args.add(size);
        args.add((page - 1) * size);
        List<Map<String, Object>> list = TicketSql.db().query(
                "SELECT t.*" + from + where + " ORDER BY t.id DESC LIMIT ? OFFSET ?",
                (rs, i) -> TicketStatusOps.enrich(TicketRowMaps.mapRow(rs)),
                args.toArray());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", t);
        out.put("page", page);
        out.put("size", size);
        return out;
    }

    /** 当前用户是否为某单据关联档案的确认人 */
    public static boolean isPeerOwnerOf(long ticketId, String username) {
        if (!peerAccept || MODE != Mode.ARCHIVE || username == null || username.isBlank()) return false;
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) return false;
        long itemId = TicketSql.toLong(m.get("bookId"));
        if (itemId <= 0) itemId = TicketSql.toLong(m.get("itemId"));
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) return false;
        return username.trim().equals(TicketSql.str(item.get("ownerUsername")));
    }

'''


def patch_ticket(path: Path) -> None:
    t = path.read_text(encoding="utf-8")
    if "configurePeerAccept" in t:
        print("skip ticket", path.parent.parent.parent.parent.parent.name)
        return
    t = t.replace(
        "    /** L1：签到口令 */\n    static boolean allowCheckin = false;\n",
        "    /** L1：签到口令 */\n    static boolean allowCheckin = false;\n"
        "    /** C-05：档案主人可确认/拒绝志愿（互选） */\n"
        "    static boolean peerAccept = false;\n",
        1,
    )
    t = t.replace(
        "    public static void configureCheckin(boolean enabled) {\n"
        "        allowCheckin = enabled;\n"
        "        // checked_in_at / 档案 checkin_code 由 bake 按能力写入\n"
        "    }\n\n"
        "    public static void configureNoShow",
        "    public static void configureCheckin(boolean enabled) {\n"
        "        allowCheckin = enabled;\n"
        "        // checked_in_at / 档案 checkin_code 由 bake 按能力写入\n"
        "    }\n\n"
        "    public static void configurePeerAccept(boolean enabled) {\n"
        "        peerAccept = enabled;\n"
        "    }\n\n"
        "    public static boolean isPeerAccept() {\n"
        "        return peerAccept;\n"
        "    }\n\n"
        "    public static void configureNoShow",
        1,
    )
    t = t.replace(
        "        if (autoApprove) {\n"
        "            appendProgress(id, \"approved\", username, \"用户提交（即时生效）\");\n"
        "        } else {\n"
        "            appendProgress(id, \"pending\", username, \"用户提交\");\n"
        "            notifyAdminsNewTicket(id, username, subjectOf(get(id)));\n"
        "        }\n"
        "        return get(id);\n"
        "    }\n",
        "        if (autoApprove) {\n"
        "            appendProgress(id, \"approved\", username, \"用户提交（即时生效）\");\n"
        "        } else {\n"
        "            appendProgress(id, \"pending\", username, \"用户提交\");\n"
        "            String subj = subjectOf(get(id));\n"
        "            notifyAdminsNewTicket(id, username, subj);\n"
        "            notifyPeerOwnerNewTicket(id, itemId, username, subj);\n"
        "        }\n"
        "        return get(id);\n"
        "    }\n",
        1,
    )
    t = t.replace(
        "            MessageStore.notifyAdmins(\n"
        "                    \"待受理\",\n"
        "                    who + \" 提交了「\" + sub + \"」，请尽快处理。\",\n"
        "                    \"ticket\",\n"
        "                    ticketId);\n"
        "        } catch (Exception ignored) {\n"
        "        }\n"
        "    }\n\n"
        "    public static List<Map<String, Object>> listProgress(long ticketId) {",
        "            MessageStore.notifyAdmins(\n"
        "                    peerAccept ? \"待调剂\" : \"待受理\",\n"
        "                    who + \" 提交了「\" + sub + \"」，请尽快处理。\",\n"
        "                    \"ticket\",\n"
        "                    ticketId);\n"
        "        } catch (Exception ignored) {\n"
        "        }\n"
        "    }\n"
        + PEER_METHODS
        + "    public static List<Map<String, Object>> listProgress(long ticketId) {",
        1,
    )
    path.write_text(t, encoding="utf-8")
    print("ok ticket", path)


def patch_binder(path: Path) -> None:
    t = path.read_text(encoding="utf-8")
    if "ticketPeerAccept" in t:
        print("skip binder", path)
        return
    t = t.replace(
        '    @Value("${thesis.ticket-allow-checkin:false}")\n'
        "    private boolean ticketAllowCheckin;\n",
        '    @Value("${thesis.ticket-allow-checkin:false}")\n'
        "    private boolean ticketAllowCheckin;\n\n"
        '    @Value("${thesis.ticket-peer-accept:false}")\n'
        "    private boolean ticketPeerAccept;\n",
        1,
    )
    t = t.replace(
        "            TicketStore.configureCheckin(ticketAllowCheckin);\n"
        "            TicketStore.configureNoShow(ticketNoShowAfterEnd, ticketNoShowPenaltyYuan);\n",
        "            TicketStore.configureCheckin(ticketAllowCheckin);\n"
        "            TicketStore.configurePeerAccept(ticketPeerAccept);\n"
        "            TicketStore.configureNoShow(ticketNoShowAfterEnd, ticketNoShowPenaltyYuan);\n",
        1,
    )
    path.write_text(t, encoding="utf-8")
    print("ok binder", path)


def patch_archive(path: Path) -> None:
    t = path.read_text(encoding="utf-8")
    if "ownerUsername" in t and "owner_username" in t:
        # may already have only ownerName
        if 'patchOptStr(id, patch, "ownerUsername"' in t:
            print("skip archive", path)
            return
    if 'patchOptStr(id, patch, "ownerName", "owner_name", 64);' in t and "ownerUsername" not in t:
        t = t.replace(
            'patchOptStr(id, patch, "ownerName", "owner_name", 64);',
            'patchOptStr(id, patch, "ownerName", "owner_name", 64);\n'
            '        patchOptStr(id, patch, "ownerUsername", "owner_username", 64);',
            1,
        )
    # mybatis uses putOptStr(m, raw, ...) jpa uses putOptStr(m, rs, ...)
    if 'putOptStr(m, rs, "owner_name", "ownerName");' in t:
        t = t.replace(
            'putOptStr(m, rs, "owner_name", "ownerName");',
            'putOptStr(m, rs, "owner_name", "ownerName");\n'
            '        putOptStr(m, rs, "owner_username", "ownerUsername");',
            1,
        )
    if 'putOptStr(m, raw, "owner_name", "ownerName");' in t:
        t = t.replace(
            'putOptStr(m, raw, "owner_name", "ownerName");',
            'putOptStr(m, raw, "owner_name", "ownerName");\n'
            '        putOptStr(m, raw, "owner_username", "ownerUsername");',
            1,
        )
    path.write_text(t, encoding="utf-8")
    print("ok archive", path)


def main() -> None:
    for ov in OVS:
        patch_ticket(ov / "capability" / "TicketStore.java")
        patch_binder(ov / "config" / "DomainRuntimeBinder.java")
        patch_archive(ov / "capability" / "ArchiveStore.java")
    print("done")


if __name__ == "__main__":
    main()
