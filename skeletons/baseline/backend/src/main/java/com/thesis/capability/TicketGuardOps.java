package com.thesis.capability;

import java.util.*;
import java.time.LocalDate;
import java.time.LocalDateTime;
import com.thesis.service.UserStore;
import com.thesis.service.ExamStore;

/**
 * TicketGuardOps：TicketStore 纯业务逻辑拆分（零 DB 接触）。
 *
 * <p>三栈共用：bake 时由 baseline 提供；mybatis/jpa overlay 不含此类
 * （helper 不出现任何 JDBC/MyBatis token，故不参与 persistence 覆盖）。
 * 对 TicketStore 静态成员的引用一律使用显式限定名。
 */
final class TicketGuardOps {

    private TicketGuardOps() {}

    /** matchProfileRoom：资料键↔档案列（查寝默认楼栋/房间；实习绑岗可配单位/岗位） */

    public static void assertMatchProfileRoomIfRequired(String username, long itemId) {
        if (!TicketStore.matchProfileRoom) return;
        com.thesis.service.UserStore.Profile p = com.thesis.service.UserStore.get(username);
        if (p == null) {
            throw new IllegalStateException("请先登录");
        }
        String building = p.extras == null ? "" : TicketSql.str(p.extras.get(TicketStore.matchProfileBuildingKey)).trim();
        String room = p.extras == null ? "" : TicketSql.str(p.extras.get(TicketStore.matchProfileRoomKey)).trim();
        if (building.isBlank() || room.isBlank()) {
            throw new IllegalStateException(TicketStore.matchProfileNeedMessage);
        }
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        String author = TicketSql.str(item.get(TicketStore.matchProfileBuildingField)).trim();
        String title = TicketSql.str(item.get(TicketStore.matchProfileRoomField)).trim();
        if (!TicketStore.profileRoomMatches(building, room, author, title, TicketStore.matchProfileLooseBuilding)) {
            throw new IllegalStateException(TicketStore.matchProfileDenyMessage);
        }
    
    }

    /** bedConstraint：档案限性别/年级 vs 个人资料 */

    public static void assertBedConstraintIfRequired(String username, long itemId) {
        if (!TicketStore.bedConstraint) return;
        com.thesis.service.UserStore.Profile p = com.thesis.service.UserStore.get(username);
        if (p == null) {
            throw new IllegalStateException("请先登录");
        }
        String gender = p.extras == null ? "" : TicketSql.str(p.extras.get("gender")).trim();
        String grade = p.extras == null ? "" : TicketSql.str(p.extras.get("grade")).trim();
        if (gender.isBlank() && grade.isBlank()) {
            throw new IllegalStateException(TicketStore.bedConstraintNeedMessage);
        }
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        String allowedGender = TicketSql.str(item.get("allowedGender")).trim();
        String allowedGrades = TicketSql.str(item.get("allowedGrades")).trim();
        if (!allowedGender.isBlank()
                && !"不限".equals(allowedGender)
                && !gender.isBlank()
                && !allowedGender.equals(gender)) {
            throw new IllegalStateException(TicketStore.bedConstraintDenyMessage);
        }
        if (!allowedGrades.isBlank() && !grade.isBlank()) {
            boolean ok = false;
            for (String part : allowedGrades.split("[,，、\\s]+")) {
                if (part != null && !part.isBlank() && part.trim().equals(grade)) {
                    ok = true;
                    break;
                }
            }
            if (!ok) {
                throw new IllegalStateException(TicketStore.bedConstraintDenyMessage);
            }
        }
    
    }

    /** 须知勾选 / 培训勾选 / 保险勾选：申请体校验 */

    public static void assertAckFlagsIfRequired(Map<String, Object> body) {
        if (body == null) body = Map.of();
        if (TicketStore.requireNoticeAck && !TicketNotifyOps.truthy(body.get("noticeAck"))) {
            throw new IllegalStateException("请先阅读并勾选须知");
        }
        if (TicketStore.requireTrainingAck && !TicketNotifyOps.truthy(body.get("trainingAck"))) {
            throw new IllegalStateException("请确认已完成相关培训");
        }
        if (TicketStore.requireInsuranceAck && !TicketNotifyOps.truthy(body.get("insuranceAck"))) {
            throw new IllegalStateException("请先阅读并勾选保险声明");
        }
        if (TicketStore.requireMeetingAck && !TicketNotifyOps.truthy(body.get("meetingAck"))) {
            throw new IllegalStateException("请确认已约定面交时间与地点");
        }
    
    }

    /** 档案有票价/单房差说明时，申请须勾选已读。 */

    public static void assertPriceNoteAckIfRequired(Map<String, Object> item, Map<String, Object> body) {
        if (!TicketStore.requirePriceNoteAck || item == null) return;
        String price = TicketSql.str(item.get("groupPriceNote")).trim();
        String room = TicketSql.str(item.get("singleRoomNote")).trim();
        if (price.isBlank() && room.isBlank()) return;
        if (body == null || !TicketNotifyOps.truthy(body.get("priceNoteAck"))) {
            throw new IllegalStateException("请先阅读并确认票价/单房差说明");
        }
    
    }

    /** 档案有赞助说明时，申请须勾选已知晓。 */

    public static void assertSponsorAckIfRequired(Map<String, Object> item, Map<String, Object> body) {
        if (!TicketStore.requireSponsorAck || item == null) return;
        String sponsor = TicketSql.str(item.get("sponsorNote")).trim();
        if (sponsor.isBlank()) return;
        if (body == null || !TicketNotifyOps.truthy(body.get("sponsorAck"))) {
            throw new IllegalStateException("请确认已知晓赞助说明");
        }
    
    }

    /** 档案有培养方案外链时，申请须勾选已查阅。 */

    public static void assertPlanAckIfRequired(Map<String, Object> item, Map<String, Object> body) {
        if (!TicketStore.requirePlanAck || item == null) return;
        String url = TicketSql.str(item.get("planUrl")).trim();
        if (url.isBlank()) return;
        if (body == null || !TicketNotifyOps.truthy(body.get("planAck"))) {
            throw new IllegalStateException("请先查阅培养方案外链并勾选确认");
        }
    
    }

    /** 档案有先修提示码时，申请须勾选已具备先修基础。 */
    public static void assertPrereqAckIfRequired(Map<String, Object> item, Map<String, Object> body) {
        if (!TicketStore.requirePrereqAck || item == null) return;
        String code = TicketSql.str(item.get("prereqCode")).trim();
        if (code.isBlank()) return;
        if (body == null || !TicketNotifyOps.truthy(body.get("prereqAck"))) {
            throw new IllegalStateException("请确认已具备先修基础后再提交");
        }
    }

    /** 线路年龄限制：档案 minAge/maxAge 对照资料 ageYears。 */
    public static void assertAgeConstraintIfRequired(String username, long itemId) {
        if (!TicketStore.ageConstraint) return;
        com.thesis.service.UserStore.Profile p = com.thesis.service.UserStore.get(username);
        if (p == null) {
            throw new IllegalStateException("请先登录");
        }
        String ageRaw = p.extras == null ? "" : TicketSql.str(p.extras.get("ageYears")).trim();
        if (ageRaw.isBlank()) {
            throw new IllegalStateException(TicketStore.ageConstraintNeedMessage);
        }
        int age;
        try {
            age = (int) Double.parseDouble(ageRaw);
        } catch (Exception e) {
            throw new IllegalStateException(TicketStore.ageConstraintNeedMessage);
        }
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        int minAge = 0;
        int maxAge = 0;
        try {
            Object mn = item.get("minAge");
            if (mn != null && !String.valueOf(mn).isBlank()) {
                minAge = (int) Double.parseDouble(String.valueOf(mn));
            }
        } catch (Exception ignored) {
        }
        try {
            Object mx = item.get("maxAge");
            if (mx != null && !String.valueOf(mx).isBlank()) {
                maxAge = (int) Double.parseDouble(String.valueOf(mx));
            }
        } catch (Exception ignored) {
        }
        if (minAge <= 0 && maxAge <= 0) return;
        if (minAge > 0 && age < minAge) {
            throw new IllegalStateException(TicketStore.ageConstraintDenyMessage);
        }
        if (maxAge > 0 && age > maxAge) {
            throw new IllegalStateException(TicketStore.ageConstraintDenyMessage);
        }
    }

    /** 档案有出团天气/须知时，申请须勾选已读。 */
    public static void assertTourNoticeAckIfRequired(Map<String, Object> item, Map<String, Object> body) {
        if (!TicketStore.requireTourNoticeAck || item == null) return;
        String note = TicketSql.str(item.get("weatherNote")).trim();
        if (note.isBlank()) return;
        if (body == null || !TicketNotifyOps.truthy(body.get("tourNoticeAck"))) {
            throw new IllegalStateException("请先阅读并确认出团天气与须知");
        }
    }

    /** 报名口令：与档案 applyInviteCode 比对（档案为空则不拦）。 */

    public static void assertApplyInviteIfRequired(long itemId, String code) {
        if (!TicketStore.requireApplyInvite) return;
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        String expect = TicketSql.str(item.get("applyInviteCode")).trim();
        if (expect.isBlank()) return;
        String got = code == null ? "" : code.trim();
        if (got.isBlank()) {
            throw new IllegalStateException("请填写报名口令");
        }
        if (!expect.equalsIgnoreCase(got)) {
            throw new IllegalStateException("报名口令不正确");
        }
    
    }

    /** 装修施工时段对照档案禁噪窗：档案空窗不拦；重叠则拒写。 */
    public static void assertFitoutQuietIfRequired(long itemId, String workStart, String workEnd) {
        if (!TicketStore.allowFitoutQuiet) return;
        String ws = workStart == null ? "" : workStart.trim();
        String we = workEnd == null ? "" : workEnd.trim();
        if (ws.isBlank() || we.isBlank()) {
            throw new IllegalStateException("请选择施工开始与结束时刻");
        }
        Integer a0 = parseHmMinutes(ws);
        Integer a1 = parseHmMinutes(we);
        if (a0 == null || a1 == null) {
            throw new IllegalStateException("施工时段格式须为 HH:mm");
        }
        if (a0.equals(a1)) {
            throw new IllegalStateException("施工结束须晚于开始时刻（可跨日）");
        }
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        String qs = TicketSql.str(item.get("quietStart")).trim();
        String qe = TicketSql.str(item.get("quietEnd")).trim();
        if (qs.isBlank() || qe.isBlank()) return;
        Integer q0 = parseHmMinutes(qs);
        Integer q1 = parseHmMinutes(qe);
        if (q0 == null || q1 == null || q0.equals(q1)) return;
        if (hmIntervalsOverlap(a0, a1, q0, q1)) {
            throw new IllegalStateException("施工时段与禁噪时段重叠，请改选其他时间");
        }
    }

    public static void assertIssueCopiesIfRequired(long itemId, Object issueCopies) {
        if (!TicketStore.allowIssueCopies) return;
        if (!TicketStore.hasColumn("issue_copies")) {
            throw new IllegalStateException("系统未配置开具份数字段");
        }
        int copies = (int) Math.round(TicketSql.toDouble(issueCopies));
        if (copies < 1) {
            throw new IllegalStateException("请填写开具份数（至少 1 份）");
        }
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        Object maxRaw = item.get("maxIssueCopies");
        if (maxRaw == null || String.valueOf(maxRaw).trim().isBlank()) return;
        double max = TicketSql.toDouble(maxRaw);
        if (max <= 0) return;
        if (copies > max + 1e-6) {
            throw new IllegalStateException("开具份数不可超过上限 " + (int) Math.round(max));
        }
    }

    public static void assertProcureBudgetIfRequired(long itemId, Object amount) {
        if (!TicketStore.allowProcureBudget) return;
        if (!TicketStore.hasColumn("procure_amount")) {
            throw new IllegalStateException("系统未配置申购金额字段");
        }
        double add = TicketSql.toDouble(amount);
        if (!(add > 0)) {
            throw new IllegalStateException("请填写大于 0 的申购金额");
        }
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        Object capRaw = item.get("budgetTotal");
        if (capRaw == null || String.valueOf(capRaw).trim().isBlank()) return;
        double cap = TicketSql.toDouble(capRaw);
        if (!(cap > 0)) return;
        double have = TicketStore.sumProcureAmount(itemId);
        if (have + add > cap + 1e-6) {
            throw new IllegalStateException("申购金额合计将超过该项预算余额");
        }
    }

    public static void assertVisitSlotIfRequired(long itemId, String visitOn) {
        if (!TicketStore.allowVisitSlotRemain) return;
        if (!TicketStore.hasColumn("visit_on")) {
            throw new IllegalStateException("系统未配置来访日期字段");
        }
        String day = visitOn == null ? "" : visitOn.trim();
        if (day.length() >= 10) day = day.substring(0, 10);
        if (day.isBlank()) {
            throw new IllegalStateException("请选择来访日期");
        }
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        Object capRaw = item.get("visitSlotCap");
        if (capRaw == null || String.valueOf(capRaw).trim().isBlank()) return;
        int cap = (int) Math.round(TicketSql.toDouble(capRaw));
        if (cap <= 0) return;
        long have = 0;
        try {
            Long n = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM " + TicketStore.TICKET
                            + " WHERE " + TicketStore.itemFkColumn()
                            + "=? AND LEFT(TRIM(visit_on),10)=? AND status IN ('approved','pending','pending_mid','pending_final','waitlisted')",
                    Long.class,
                    itemId,
                    day);
            have = n == null ? 0 : n;
        } catch (Exception e) {
            throw new IllegalStateException("查询当日预约余量失败", e);
        }
        if (have >= cap) {
            throw new IllegalStateException("该日预约名额已满");
        }
    }

    static boolean isAbsentException(String exceptionType) {
        String t = exceptionType == null ? "" : exceptionType.trim();
        return t.contains("未归") || t.contains("缺勤");
    }

    public static void assertAbsentStreakIfRequired(long itemId, String username, String exceptionType) {
        if (!TicketStore.allowAbsentStreak) return;
        if (!isAbsentException(exceptionType)) return;
        if (!TicketStore.hasColumn("exception_type")) {
            throw new IllegalStateException("系统未配置异常类型字段");
        }
        String user = username == null ? "" : username.trim();
        if (user.isBlank()) {
            throw new IllegalStateException("请先登录");
        }
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        Object capRaw = item.get("absentWarnN");
        if (capRaw == null || String.valueOf(capRaw).trim().isBlank()) return;
        int cap = (int) Math.round(TicketSql.toDouble(capRaw));
        if (cap <= 0) return;
        List<String> recent = List.of();
        try {
            recent = TicketSql.db().query(
                    "SELECT exception_type FROM " + TicketStore.TICKET
                            + " WHERE username=? ORDER BY id DESC LIMIT 40",
                    (rs, i) -> TicketSql.str(rs.getString("exception_type")),
                    user);
        } catch (Exception e) {
            throw new IllegalStateException("查询连续未归记录失败", e);
        }
        int streak = 0;
        if (recent != null) {
            for (String t : recent) {
                if (isAbsentException(t)) streak++;
                else break;
            }
        }
        if (streak + 1 >= cap) {
            throw new IllegalStateException("连续未归已达预警次数，暂不能再提交未归");
        }
    }

    public static void assertParkingMutexIfRequired(long itemId, String parkingOn, long excludeTicketId) {
        if (!TicketStore.allowCarpassParkingMutex) return;
        if (!TicketStore.hasColumn("parking_on")) {
            throw new IllegalStateException("系统未配置占用车位日期字段");
        }
        String day = parkingOn == null ? "" : parkingOn.trim();
        if (day.length() >= 10) day = day.substring(0, 10);
        if (day.isBlank()) {
            throw new IllegalStateException("请选择占用车位日期");
        }
        if (itemId <= 0) return;
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        if (!TicketNotifyOps.truthy(item.get("parkingMutex"))) return;
        long have = 0;
        try {
            Long n = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM " + TicketStore.TICKET
                            + " WHERE " + TicketStore.itemFkColumn()
                            + "=? AND LEFT(TRIM(parking_on),10)=? AND id<>? AND status IN ('approved','pending','pending_mid','pending_final','waitlisted')",
                    Long.class,
                    itemId,
                    day,
                    excludeTicketId);
            have = n == null ? 0 : n;
        } catch (Exception e) {
            throw new IllegalStateException("查询车位占用失败", e);
        }
        if (have > 0) {
            throw new IllegalStateException("该车位该日已有通行申请");
        }
    }

    public static Map<String, Object> applyWalkIn(String operator, Map<String, Object> body) {
        if (!TicketStore.allowVisitWalkIn) {
            throw new IllegalStateException("未开放现场补录");
        }
        if (body == null) body = Map.of();
        String forUser = TicketSql.str(body.get("forUsername")).trim();
        if (forUser.isBlank()) forUser = TicketSql.str(body.get("username")).trim();
        if (forUser.isBlank()) {
            throw new IllegalStateException("请选择被访人账号");
        }
        if (UserStore.get(forUser) == null) {
            throw new IllegalArgumentException("账号不存在");
        }
        long itemId = TicketSql.toLong(body.get("itemId"));
        if (itemId <= 0) itemId = TicketSql.toLong(body.get("bookId"));
        if (itemId <= 0) {
            throw new IllegalStateException("请选择来访对象");
        }
        String visitOn = TicketSql.str(body.get("visitOn")).trim();
        if (visitOn.length() >= 10) visitOn = visitOn.substring(0, 10);
        if (visitOn.isBlank()) {
            throw new IllegalStateException("请选择来访日期");
        }
        TicketStore.assertVisitSlotIfRequired(itemId, visitOn);
        String remark = TicketSql.str(body.get("remark")).trim();
        if (remark.isBlank()) remark = "现场补录";
        String attach = TicketSql.str(body.get("attachUrl"));
        Map<String, Object> created = TicketStore.apply(forUser, itemId, remark, attach, null, null, null, null);
        long tid = TicketSql.toLong(created.get("id"));
        Map<String, Object> patch = new LinkedHashMap<>(body);
        patch.put("walkIn", true);
        patch.put("visitOn", visitOn);
        try {
            TicketStore.patchTicketExtras(tid, patch);
        } catch (RuntimeException e) {
            TicketStore.deleteFreshTicket(tid);
            throw e;
        }
        return tid > 0 ? TicketStore.get(tid) : created;
    }

    public static Map<String, Object> applyCheckinProxy(String operator, Map<String, Object> body) {
        if (!TicketStore.allowCheckinProxy) {
            throw new IllegalStateException("未开放代登记");
        }
        if (body == null) body = Map.of();
        String forUser = TicketSql.str(body.get("forUsername")).trim();
        if (forUser.isBlank()) forUser = TicketSql.str(body.get("username")).trim();
        if (forUser.isBlank()) {
            throw new IllegalStateException("请选择学生账号");
        }
        if (UserStore.get(forUser) == null) {
            throw new IllegalArgumentException("账号不存在");
        }
        long itemId = TicketSql.toLong(body.get("itemId"));
        if (itemId <= 0) itemId = TicketSql.toLong(body.get("bookId"));
        if (itemId <= 0) {
            throw new IllegalStateException("请选择查寝对象");
        }
        String remark = TicketSql.str(body.get("remark")).trim();
        if (remark.isBlank()) remark = "楼栋长代登记";
        String attach = TicketSql.str(body.get("attachUrl"));
        Map<String, Object> created = TicketStore.apply(forUser, itemId, remark, attach, null, null, null, null);
        long tid = TicketSql.toLong(created.get("id"));
        Map<String, Object> patch = new LinkedHashMap<>(body);
        String by = operator == null ? "" : operator.trim();
        if (by.length() > 64) by = by.substring(0, 64);
        patch.put("checkinProxyBy", by);
        try {
            TicketStore.patchTicketExtras(tid, patch);
        } catch (RuntimeException e) {
            TicketStore.deleteFreshTicket(tid);
            throw e;
        }
        return tid > 0 ? TicketStore.get(tid) : created;
    }

    public static Map<String, Object> urgeEvalUnrated(long itemId) {
        if (!TicketStore.allowEvalUrge) {
            throw new IllegalStateException("未开放催评");
        }
        if (itemId <= 0) {
            throw new IllegalStateException("请选择课程");
        }
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        String title = TicketSql.str(item.get("title")).trim();
        if (title.isBlank()) title = "评教";
        java.util.Set<String> done = new java.util.HashSet<>();
        try {
            List<String> have = TicketSql.db().query(
                    "SELECT username FROM " + TicketStore.TICKET
                            + " WHERE " + TicketStore.itemFkColumn() + "=?",
                    (rs, i) -> TicketSql.str(rs.getString("username")),
                    itemId);
            if (have != null) {
                for (String u : have) {
                    if (u != null && !u.isBlank()) done.add(u.trim());
                }
            }
        } catch (Exception e) {
            throw new IllegalStateException("查询已评名单失败", e);
        }
        List<Map<String, Object>> users = UserStore.listManaged("user", "users", null);
        int sent = 0;
        for (Map<String, Object> row : users) {
            if (row == null) continue;
            String un = TicketSql.str(row.get("username")).trim();
            if (un.isBlank() || done.contains(un)) continue;
            com.thesis.service.MessageStore.send(
                    un,
                    "评教提醒",
                    "请尽快完成「" + title + "」的评教。",
                    "archive",
                    itemId);
            sent++;
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("sent", sent);
        out.put("itemId", itemId);
        return out;
    }

    public static void assertExamPassMinIfRequired(String username, long itemId) {
        if (!TicketStore.allowExamPassMin) return;
        if (itemId <= 0) return;
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        int min = (int) Math.round(TicketSql.toDouble(item.get("examPassMin")));
        if (min <= 0) return;
        if (!ExamStore.ready()) {
            throw new IllegalStateException("请先通过准入考试后再提交申请");
        }
        String user = username == null ? "" : username.trim();
        if (user.isBlank()) throw new IllegalStateException("请先登录");
        List<Map<String, Object>> rows;
        try {
            rows = TicketSql.db().query(
                    "SELECT a.score, a.total_score FROM exam_attempt a "
                            + "WHERE a.username=? AND a.mode='exam' AND a.status='submitted'",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("score", rs.getInt("score"));
                        m.put("total", rs.getInt("total_score"));
                        return m;
                    },
                    user);
        } catch (Exception e) {
            throw new IllegalStateException("查询考试成绩失败", e);
        }
        if (rows != null) {
            for (Map<String, Object> r : rows) {
                int sc = r.get("score") instanceof Number n ? n.intValue() : 0;
                int tot = r.get("total") instanceof Number n ? n.intValue() : 0;
                if (tot > 0 && sc * 100 >= min * tot) return;
                if (tot <= 0 && sc >= min) return;
            }
        }
        throw new IllegalStateException("准入考试成绩未达 " + min + " 分，暂不能提交申请");
    }

    public static void assertEvalBeforeGradeIfRequired(String username) {
        if (!TicketStore.allowEvalBeforeGrade) return;
        String user = username == null ? "" : username.trim();
        if (user.isBlank()) throw new IllegalStateException("请先登录");
        try {
            Map<String, Object> page = ArchiveStore.pageItems("", null, 1, 200);
            Object listObj = page == null ? null : page.get("list");
            int openItems = 0;
            if (listObj instanceof List<?> list) openItems = list.size();
            if (openItems <= 0) return;
            Long done = TicketSql.db().queryForObject(
                    "SELECT COUNT(DISTINCT " + TicketStore.itemFkColumn() + ") FROM " + TicketStore.TICKET
                            + " WHERE username=? AND status IN ('approved','returned','pending','pending_mid','pending_final')",
                    Long.class,
                    user);
            long have = done == null ? 0 : done;
            if (have >= openItems) return;
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("请先完成评教后再查看成绩");
        }
        throw new IllegalStateException("请先完成评教后再查看成绩");
    }

    public static Map<String, Object> generateCheckinSpot(String operator, Map<String, Object> body) {
        if (!TicketStore.allowCheckinSpot) {
            throw new IllegalStateException("未开放抽查任务");
        }
        if (!spotTableReady()) {
            throw new IllegalStateException("系统未配置抽查任务表");
        }
        if (body == null) body = Map.of();
        long itemId = TicketSql.toLong(body.get("itemId"));
        if (itemId <= 0) itemId = TicketSql.toLong(body.get("bookId"));
        if (itemId <= 0) throw new IllegalStateException("请选择查寝对象");
        if (ArchiveStore.getItem(itemId) == null) throw new IllegalArgumentException("对象不存在");
        String on = TicketSql.str(body.get("onDate")).trim();
        if (on.isBlank()) on = TicketSql.str(body.get("on")).trim();
        if (on.length() >= 10) on = on.substring(0, 10);
        if (on.isBlank()) throw new IllegalStateException("请选择抽查日期");
        int n = (int) Math.round(TicketSql.toDouble(body.get("sampleN")));
        if (n <= 0) n = 3;
        if (n > 200) n = 200;
        List<Map<String, Object>> users = UserStore.listManaged("user", "users", null);
        List<String> names = new ArrayList<>();
        if (users != null) {
            for (Map<String, Object> row : users) {
                if (row == null) continue;
                if (Boolean.FALSE.equals(row.get("enabled"))) continue;
                String un = TicketSql.str(row.get("username")).trim();
                if (!un.isBlank()) names.add(un);
            }
        }
        Collections.shuffle(names);
        if (n > names.size()) n = names.size();
        if (n <= 0) throw new IllegalStateException("暂无可抽查的学生");
        String by = operator == null ? "" : operator.trim();
        if (by.length() > 64) by = by.substring(0, 64);
        org.springframework.jdbc.support.KeyHolder kh = new org.springframework.jdbc.support.GeneratedKeyHolder();
        final long spotItemId = itemId;
        final int sampleN = n;
        final String onDate = on;
        final String createdBy = by;
        TicketSql.db().update(con -> {
            var ps = con.prepareStatement(
                    "INSERT INTO checkin_spot_task (item_id,on_date,sample_n,created_by) VALUES (?,?,?,?)",
                    java.sql.Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, spotItemId);
            ps.setString(2, onDate);
            ps.setInt(3, sampleN);
            ps.setString(4, createdBy);
            return ps;
        }, kh);
        Number key = kh.getKey();
        long taskId = key == null ? 0 : key.longValue();
        if (taskId <= 0) throw new IllegalStateException("抽查任务写入失败");
        int line = 1;
        for (int i = 0; i < sampleN; i++) {
            TicketSql.db().update(
                    "INSERT INTO checkin_spot_member (task_id,line_no,username) VALUES (?,?,?)",
                    taskId, line++, names.get(i));
        }
        return getCheckinSpot(taskId);
    }

    public static List<Map<String, Object>> listCheckinSpot(long itemId) {
        if (!TicketStore.allowCheckinSpot || !spotTableReady()) return List.of();
        try {
            String sql = "SELECT id FROM checkin_spot_task";
            List<Object> args = new ArrayList<>();
            if (itemId > 0) {
                sql += " WHERE item_id=?";
                args.add(itemId);
            }
            sql += " ORDER BY id DESC LIMIT 40";
            List<Long> ids = TicketSql.db().query(
                    sql,
                    (rs, i) -> rs.getLong("id"),
                    args.toArray());
            List<Map<String, Object>> out = new ArrayList<>();
            if (ids != null) {
                for (Long id : ids) {
                    if (id != null) out.add(getCheckinSpot(id));
                }
            }
            return out;
        } catch (Exception e) {
            return List.of();
        }
    }

    public static Map<String, Object> getCheckinSpot(long taskId) {
        if (taskId <= 0 || !spotTableReady()) return Map.of();
        List<Map<String, Object>> heads = TicketSql.db().query(
                "SELECT id, item_id, on_date, sample_n, created_by, created_at FROM checkin_spot_task WHERE id=?",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("itemId", rs.getLong("item_id"));
                    m.put("onDate", TicketSql.safeStr(rs, "on_date"));
                    m.put("sampleN", rs.getInt("sample_n"));
                    m.put("createdBy", TicketSql.safeStr(rs, "created_by"));
                    m.put("createdAt", TicketSql.fmt(TicketSql.safeTs(rs, "created_at")));
                    return m;
                },
                taskId);
        if (heads == null || heads.isEmpty()) return Map.of();
        Map<String, Object> head = heads.get(0);
        List<Map<String, Object>> members = TicketSql.db().query(
                "SELECT username FROM checkin_spot_member WHERE task_id=? ORDER BY line_no",
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("username", TicketSql.safeStr(rs, "username"));
                    return m;
                },
                taskId);
        head.put("members", members == null ? List.of() : members);
        return head;
    }

    public static boolean isSpotCheckedToday(String username) {
        if (!TicketStore.allowCheckinSpot || !spotTableReady()) return false;
        String user = username == null ? "" : username.trim();
        if (user.isBlank()) return false;
        try {
            Long n = TicketSql.db().queryForObject(
                    "SELECT COUNT(*) FROM checkin_spot_member m "
                            + "JOIN checkin_spot_task t ON t.id=m.task_id "
                            + "WHERE m.username=? AND LEFT(TRIM(t.on_date),10)=DATE_FORMAT(CURDATE(),'%Y-%m-%d')",
                    Long.class,
                    user);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    public static List<Map<String, Object>> approveDurationStats() {
        if (!TicketStore.allowApproveDurationStats) return List.of();
        String handlerExpr = TicketStore.hasColumn("assignee_username")
                ? "IFNULL(NULLIF(TRIM(assignee_username),''),'(未指定)')"
                : "'(未指定)'";
        try {
            return TicketSql.db().query(
                    "SELECT " + handlerExpr + " AS handler, "
                            + "COUNT(*) AS cnt, "
                            + "ROUND(AVG(TIMESTAMPDIFF(MINUTE, apply_at, approve_at)),1) AS avgMinutes "
                            + "FROM " + TicketStore.TICKET
                            + " WHERE approve_at IS NOT NULL AND apply_at IS NOT NULL "
                            + "AND status IN ('approved','rejected','returned') "
                            + "GROUP BY handler ORDER BY avgMinutes",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("handler", TicketSql.safeStr(rs, "handler"));
                        m.put("count", rs.getInt("cnt"));
                        m.put("avgMinutes", rs.getDouble("avgMinutes"));
                        return m;
                    });
        } catch (Exception e) {
            return List.of();
        }
    }

    public static Map<String, Object> redeemPickup(long ticketId, String operator, String code) {
        if (!TicketStore.allowCertPickupRedeem) {
            throw new IllegalStateException("未开放领取核销");
        }
        if (!TicketStore.hasColumn("pickup_redeem_code")) {
            throw new IllegalStateException("系统未配置领取核销码字段");
        }
        Map<String, Object> row = TicketRowMaps.load(ticketId);
        if (row == null) throw new IllegalArgumentException("单据不存在");
        String expect = TicketSql.str(row.get("pickupRedeemCode")).trim();
        String got = code == null ? "" : code.trim();
        if (expect.isBlank()) throw new IllegalStateException("该证明尚未签发领取核销码");
        if (!expect.equalsIgnoreCase(got)) throw new IllegalStateException("核销码不正确");
        if (TicketNotifyOps.truthy(row.get("pickupRedeemed"))) {
            throw new IllegalStateException("该证明已核销领取");
        }
        if (TicketStore.hasColumn("pickup_redeemed")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET pickup_redeemed=1 WHERE id=?", ticketId);
        }
        TicketDeriveOps.appendProgress(ticketId, "pickup_redeemed", operator, "领取已核销");
        return TicketStore.get(ticketId);
    }

    public static void keepAttachHistory(long ticketId, String oldUrl, String newUrl) {
        if (!TicketStore.allowAttachKeepOld || ticketId <= 0) return;
        if (!attachRevReady()) return;
        String oldU = oldUrl == null ? "" : oldUrl.trim();
        String newU = newUrl == null ? "" : newUrl.trim();
        if (oldU.isBlank() || oldU.equals(newU)) return;
        if (oldU.length() > 255) oldU = oldU.substring(0, 255);
        try {
            Integer max = TicketSql.db().queryForObject(
                    "SELECT MAX(line_no) FROM ticket_attach_rev WHERE ticket_id=?",
                    Integer.class,
                    ticketId);
            int line = (max == null ? 0 : max) + 1;
            TicketSql.db().update(
                    "INSERT INTO ticket_attach_rev (ticket_id,line_no,attach_url) VALUES (?,?,?)",
                    ticketId, line, oldU);
        } catch (Exception ignored) {
        }
    }

    public static List<Map<String, Object>> listAttachRevs(long ticketId) {
        if (!TicketStore.allowAttachKeepOld || ticketId <= 0 || !attachRevReady()) return List.of();
        try {
            return TicketSql.db().query(
                    "SELECT line_no, attach_url, created_at FROM ticket_attach_rev WHERE ticket_id=? ORDER BY line_no",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("lineNo", rs.getInt("line_no"));
                        m.put("attachUrl", TicketSql.safeStr(rs, "attach_url"));
                        m.put("createdAt", TicketSql.fmt(TicketSql.safeTs(rs, "created_at")));
                        return m;
                    },
                    ticketId);
        } catch (Exception e) {
            return List.of();
        }
    }

    public static Map<String, Object> checkinDailyReport(String onDate) {
        Map<String, Object> out = new LinkedHashMap<>();
        if (!TicketStore.allowCheckinDailyReport) {
            out.put("onDate", "");
            out.put("total", 0);
            out.put("list", List.of());
            return out;
        }
        String on = onDate == null ? "" : onDate.trim();
        if (on.length() >= 10) on = on.substring(0, 10);
        if (on.isBlank()) on = java.time.LocalDate.now().toString();
        out.put("onDate", on);
        try {
            List<Map<String, Object>> rows = TicketSql.db().query(
                    "SELECT id, username, status, title FROM " + TicketStore.TICKET
                            + " WHERE LEFT(TRIM(IFNULL(apply_at,'')),10)=? ORDER BY id",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("id", rs.getLong("id"));
                        m.put("username", TicketSql.safeStr(rs, "username"));
                        m.put("status", TicketSql.safeStr(rs, "status"));
                        m.put("title", TicketSql.safeStr(rs, "title"));
                        return m;
                    },
                    on);
            if (rows == null) rows = List.of();
            out.put("total", rows.size());
            int pending = 0, approved = 0, absent = 0;
            for (Map<String, Object> r : rows) {
                String st = TicketSql.str(r.get("status"));
                if ("pending".equals(st) || "pending_mid".equals(st) || "pending_final".equals(st)) pending++;
                else if ("approved".equals(st) || "returned".equals(st)) approved++;
                else if ("absent".equals(st) || "rejected".equals(st)) absent++;
            }
            out.put("pending", pending);
            out.put("approved", approved);
            out.put("absent", absent);
            out.put("list", rows);
            return out;
        } catch (Exception e) {
            out.put("total", 0);
            out.put("list", List.of());
            return out;
        }
    }

    public static List<Map<String, Object>> evalCollegeExport() {
        if (!TicketStore.allowEvalCollegeExport) return List.of();
        String item = ArchiveStore.itemTable();
        String fk = TicketStore.itemFkColumn();
        if (item == null || item.isBlank()) return List.of();
        try {
            String collegeExpr = "IFNULL(NULLIF(TRIM(a.college),''),'(未填学院)')";
            return TicketSql.db().query(
                    "SELECT " + collegeExpr + " AS college, COUNT(*) AS cnt "
                            + "FROM " + TicketStore.TICKET + " t "
                            + "JOIN " + item + " a ON a.id=t." + fk + " "
                            + "WHERE t.status IN ('approved','returned','pending','pending_mid','pending_final') "
                            + "GROUP BY college ORDER BY cnt DESC",
                    (rs, i) -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("college", TicketSql.safeStr(rs, "college"));
                        m.put("count", rs.getInt("cnt"));
                        return m;
                    });
        } catch (Exception e) {
            return List.of();
        }
    }

    private static boolean attachRevReady() {
        try {
            TicketSql.db().query("SELECT 1 FROM ticket_attach_rev LIMIT 1", (rs, i) -> 1);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private static boolean spotTableReady() {
        try {
            TicketSql.db().query("SELECT 1 FROM checkin_spot_task LIMIT 1", (rs, i) -> 1);
            TicketSql.db().query("SELECT 1 FROM checkin_spot_member LIMIT 1", (rs, i) -> 1);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    public static Map<String, Object> verifyByCode(String code) {
        if (!TicketStore.allowCertVerify) {
            return Map.of("found", false);
        }
        if (!TicketStore.hasColumn("verify_code")) {
            return Map.of("found", false);
        }
        String c = code == null ? "" : code.trim();
        if (c.isBlank()) {
            return Map.of("found", false);
        }
        if (c.length() > 32) c = c.substring(0, 32);
        try {
            Long id = TicketSql.db().queryForObject(
                    "SELECT id FROM " + TicketStore.TICKET
                            + " WHERE verify_code=? AND status IN ('approved','returned') ORDER BY id DESC LIMIT 1",
                    Long.class,
                    c);
            if (id == null || id <= 0) {
                return Map.of("found", false);
            }
            Map<String, Object> row = TicketRowMaps.load(id);
            if (row == null) return Map.of("found", false);
            Map<String, Object> out = new java.util.LinkedHashMap<>();
            out.put("found", true);
            out.put("verifyCode", c);
            out.put("status", TicketSql.str(row.get("status")));
            out.put("itemTitle", TicketSql.str(row.get("itemTitle")));
            if (TicketSql.str(row.get("itemTitle")).isBlank()) {
                out.put("itemTitle", TicketSql.str(row.get("title")));
            }
            out.put("approveAt", TicketSql.str(row.get("approveAt")));
            if (TicketStore.allowCertVerifyPage) {
                out.put("statusLabel", TicketSql.str(row.get("status")));
                String issueNo = TicketSql.str(row.get("certIssueNo"));
                if (!issueNo.isBlank()) out.put("certIssueNo", issueNo);
                String title = TicketSql.str(out.get("itemTitle"));
                out.put("itemTitle", title);
            }
            return out;
        } catch (Exception e) {
            return Map.of("found", false);
        }
    }

    @SuppressWarnings("unchecked")
    public static void maskBatch12ForUser(Map<String, Object> page) {
        if (page == null) return;
        Object listObj = page.get("list");
        if (!(listObj instanceof List<?> list) || list.isEmpty()) return;
        if (!TicketStore.allowHideEvalResult && !TicketStore.allowSignRemarkVisible) return;
        for (Object o : list) {
            if (!(o instanceof Map<?, ?> raw)) continue;
            Map<String, Object> row = (Map<String, Object>) raw;
            long itemId = TicketSql.toLong(row.get("itemId"));
            if (itemId <= 0) itemId = TicketSql.toLong(row.get("bookId"));
            Map<String, Object> item = itemId > 0 ? ArchiveStore.getItem(itemId) : null;
            if (TicketStore.allowHideEvalResult) {
                boolean hide = item != null && TicketNotifyOps.truthy(item.get("hideEvalResult"));
                row.put("hideEvalResult", hide);
                if (hide) {
                    row.remove("rating");
                    row.remove("ratingDimsJson");
                    row.remove("ratingRemark");
                    row.remove("ratedAt");
                }
            }
            if (TicketStore.allowSignRemarkVisible) {
                boolean visible = item == null || !item.containsKey("signRemarkVisible")
                        || TicketNotifyOps.truthy(item.get("signRemarkVisible"));
                row.put("signRemarkVisible", visible);
                if (!visible) {
                    String st = TicketSql.str(row.get("status"));
                    if ("approved".equals(st) || "rejected".equals(st) || "returned".equals(st)) {
                        row.remove("remark");
                    }
                }
            }
        }
    }

    public static Map<String, Object> lastApprovedMine(String username) {
        if (!TicketStore.allowClubCopyLast) return Map.of();
        String user = username == null ? "" : username.trim();
        if (user.isBlank()) return Map.of();
        String sql = TicketStore.hasColumn("created_at")
                ? "SELECT id FROM " + TicketStore.TICKET
                + " WHERE username=? AND status IN ('approved','returned')"
                + " AND YEAR(created_at)=YEAR(CURDATE())-1 ORDER BY id DESC LIMIT 1"
                : "SELECT id FROM " + TicketStore.TICKET
                + " WHERE username=? AND status IN ('approved','returned') ORDER BY id DESC LIMIT 1";
        try {
            Long id = TicketSql.db().queryForObject(sql, Long.class, user);
            if (id == null || id <= 0) return Map.of();
            Map<String, Object> row = TicketRowMaps.load(id);
            if (row == null) return Map.of();
            Map<String, Object> out = new java.util.LinkedHashMap<>();
            out.put("remark", TicketSql.str(row.get("remark")));
            out.put("attachUrl", TicketSql.str(row.get("attachUrl")));
            return out;
        } catch (Exception e) {
            return Map.of();
        }
    }

    public static Map<String, Object> fileMoralObjection(long ticketId, String username, String note) {
        if (!TicketStore.allowMoralObjection) {
            throw new IllegalStateException("当前未开放异议登记");
        }
        if (!TicketStore.hasColumn("objection_note")) {
            throw new IllegalStateException("系统未配置异议说明字段");
        }
        Map<String, Object> m = TicketRowMaps.load(ticketId);
        if (m == null) throw new IllegalArgumentException("单据不存在");
        if (!TicketSql.str(m.get("username")).equals(username == null ? "" : username.trim())) {
            throw new IllegalStateException("只能对自己的结果提出异议");
        }
        if (!"approved".equals(String.valueOf(m.get("status")))) {
            throw new IllegalStateException("仅已通过的结果可在公示期提出异议");
        }
        if (!TicketSql.str(m.get("objectionAt")).isBlank()
                || !TicketSql.str(m.get("objectionNote")).isBlank()) {
            throw new IllegalStateException("已提交过异议说明");
        }
        if (TicketStore.hasColumn("objection_due_at")) {
            String due = TicketSql.str(m.get("objectionDueAt")).trim();
            if (!due.isBlank()) {
                try {
                    java.time.LocalDate dueDay = java.time.LocalDate.parse(due.substring(0, Math.min(10, due.length())));
                    if (java.time.LocalDate.now().isAfter(dueDay)) {
                        throw new IllegalStateException("公示异议期已结束");
                    }
                } catch (IllegalStateException e) {
                    throw e;
                } catch (Exception ignored) {
                }
            }
        }
        String text = note == null ? "" : note.trim();
        if (text.isBlank()) throw new IllegalStateException("请填写异议说明");
        if (text.length() > 512) text = text.substring(0, 512);
        if (TicketStore.hasColumn("objection_at")) {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET objection_note=?, objection_at=NOW() WHERE id=?",
                    text, ticketId);
        } else {
            TicketSql.db().update(
                    "UPDATE " + TicketStore.TICKET + " SET objection_note=? WHERE id=?",
                    text, ticketId);
        }
        TicketDeriveOps.appendProgress(ticketId, "objection", username, text);
        return TicketDeriveOps.get(ticketId);
    }

    public static void setMoralObjectionDueIfNeeded(long ticketId) {
        if (!TicketStore.allowMoralObjection || ticketId <= 0) return;
        if (!TicketStore.hasColumn("objection_due_at")) return;
        java.sql.Timestamp due = java.sql.Timestamp.valueOf(
                java.time.LocalDateTime.now().plusDays(7));
        TicketSql.db().update(
                "UPDATE " + TicketStore.TICKET + " SET objection_due_at=? WHERE id=?", due, ticketId);
    }

    public static double dimWeight(Map<String, String> def, Map<String, Object> item) {
        if (!TicketStore.allowEvalDimWeight || def == null) return 1;
        String key = def.get("key");
        if (key != null && item != null) {
            String camel = key + "Weight";
            Object raw = item.get(camel);
            if (raw != null && !String.valueOf(raw).trim().isBlank()) {
                double w = TicketSql.toDouble(raw);
                if (w > 0) return w;
            }
        }
        String fromDef = def.get("weight");
        if (fromDef != null && !fromDef.isBlank()) {
            try {
                double w = Double.parseDouble(fromDef.trim());
                if (w > 0) return w;
            } catch (Exception ignored) {
            }
        }
        return 1;
    }

    static Integer parseHmMinutes(String raw) {
        String t = raw == null ? "" : raw.trim();
        if (t.length() >= 5) t = t.substring(0, 5);
        int colon = t.indexOf(':');
        if (colon < 1) return null;
        try {
            int h = Integer.parseInt(t.substring(0, colon));
            int m = Integer.parseInt(t.substring(colon + 1));
            if (h < 0 || h > 23 || m < 0 || m > 59) return null;
            return h * 60 + m;
        } catch (Exception e) {
            return null;
        }
    }

    static boolean hmIntervalsOverlap(int s0, int e0, int s1, int e1) {
        for (int[] a : hmSegments(s0, e0)) {
            for (int[] q : hmSegments(s1, e1)) {
                if (a[0] < q[1] && q[0] < a[1]) return true;
            }
        }
        return false;
    }

    static int[][] hmSegments(int start, int end) {
        if (start < end) {
            return new int[][] {{start, end}};
        }
        return new int[][] {{start, 24 * 60}, {0, end}};
    }

    /** 审核通过时：启事方确认面交安排。 */

    public static void assertOwnerMeetingAckIfRequired(boolean pass, Map<String, Object> body) {
        if (!pass || !TicketStore.requireMeetingAck) return;
        if (body == null || !TicketNotifyOps.truthy(body.get("ownerMeetingAck"))) {
            throw new IllegalStateException("请勾选启事方确认面交安排");
        }
    
    }

    /** 校准证书过期停借 */

    public static void assertCalibDueIfRequired(long itemId) {
        if (!TicketStore.blockIfCalibExpired) return;
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        String due = TicketSql.str(item.get("calibDue")).trim();
        if (due.isBlank()) return;
        try {
            java.time.LocalDate d = java.time.LocalDate.parse(due.substring(0, Math.min(10, due.length())));
            if (d.isBefore(java.time.LocalDate.now())) {
                throw new IllegalStateException("该设备校准证书已过期，暂不可借用");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception ignored) {
            // 日期格式异常时不拦截，避免误伤
        }
    
    }

    /** 失物认领冷却：启事发布后 N 小时才可提交。 */

    static void assertClaimCooldownIfRequired(Map<String, Object> item) {
        if (TicketStore.claimCooldownHours <= 0 || item == null) return;
        String created = TicketSql.str(item.get("createdAt")).trim();
        if (created.isBlank()) return;
        try {
            LocalDateTime at = TicketSql.parseDateTimeFlexible(created, false);
            if (at != null && LocalDateTime.now().isBefore(at.plusHours(TicketStore.claimCooldownHours))) {
                throw new IllegalStateException(
                        "启事发布后 " + TicketStore.claimCooldownHours + " 小时内暂不可认领，请稍后再试");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception ignored) {
        }
    
    }

    /** 选课学分上限：已选（含本单）合计不可超过学期上限。 */

    static void assertSemesterCreditCapIfRequired(String username, Map<String, Object> item) {
        if (TicketStore.semesterCreditCap <= 0 || item == null) return;
        double add = TicketDeriveOps.itemCredit(item);
        if (add <= 0) return;
        double have = TicketStore.sumApprovedCredits(username);
        if (have + add > TicketStore.semesterCreditCap + 1e-6) {
            throw new IllegalStateException(
                    "学分合计 " + TicketStore.trimCredit(have) + " + 本项 " + TicketStore.trimCredit(add)
                            + " 将超过学期上限 " + TicketStore.semesterCreditCap);
        }
    
    }


    static String creditWarnIfNearCap(String username, Map<String, Object> item) {
        if (TicketStore.semesterCreditCap <= 0 || TicketStore.creditWarnRemaining <= 0 || item == null) return "";
        double add = TicketDeriveOps.itemCredit(item);
        double have = TicketStore.sumApprovedCredits(username);
        double remain = TicketStore.semesterCreditCap - have - add;
        if (remain < 0) return "";
        if (remain <= TicketStore.creditWarnRemaining) {
            return "所选学分已接近学期上限，剩余约 " + TicketStore.trimCredit(remain) + " 学分";
        }
        return "";
    
    }

    /** 活动取消：开始前不足 N 小时则禁止申请人自行取消。 */

    static void assertCancelBeforeIfRequired(Map<String, Object> ticket, String actorUid) {
        if (TicketStore.cancelBeforeHours <= 0 || ticket == null) return;
        String owner = TicketSql.str(ticket.get("username")).trim();
        String actor = actorUid == null ? "" : actorUid.trim();
        if (actor.isBlank() || owner.isBlank() || !owner.equals(actor)) return;
        long itemId = TicketSql.toLong(ticket.get("bookId"));
        if (itemId <= 0) return;
        Map<String, Object> item = ArchiveStore.getItemRaw(itemId);
        if (item == null) return;
        String start = TicketSql.str(item.get("startAt")).trim();
        if (start.isBlank()) return;
        try {
            LocalDateTime startAt = TicketSql.parseDateTimeFlexible(start, false);
            if (startAt == null) return;
            LocalDateTime deadline = startAt.minusHours(TicketStore.cancelBeforeHours);
            if (!LocalDateTime.now().isBefore(deadline)) {
                throw new IllegalStateException(
                        "距开始不足 " + TicketStore.cancelBeforeHours + " 小时，不可自行取消");
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception ignored) {
        }
    
    }
}
