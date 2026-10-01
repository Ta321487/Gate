package com.thesis.capability;

import java.util.*;
import java.time.LocalDate;
import java.time.LocalDateTime;
import com.thesis.service.UserStore;

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
                    "已选学分 " + TicketStore.trimCredit(have) + " + 本课 " + TicketStore.trimCredit(add)
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

    public static void assertClaimCodeIfRequired(long itemId, String code) {
        if (!TicketStore.requireClaimCode) return;
        String got = code == null ? "" : code.trim();
        if (got.isBlank()) {
            throw new IllegalStateException("请填写取件码");
        }
        Map<String, Object> item = ArchiveStore.getItem(itemId);
        if (item == null) throw new IllegalArgumentException("对象不存在");
        String expect = TicketSql.str(item.get("isbn")).trim();
        if (expect.isBlank()) {
            throw new IllegalStateException("该包裹尚未登记取件码");
        }
        // 档案可能写成「取件码 3182 / 柜 / 手机」；取第一段比对，也允许纯数字码
        String expectCode = expect;
        int slash = expect.indexOf('/');
        if (slash > 0) expectCode = expect.substring(0, slash).trim();
        int dot = expectCode.indexOf('·');
        if (dot > 0) expectCode = expectCode.substring(0, dot).trim();
        String gotNorm = got.replace("取件码", "").replace(" ", "").trim();
        String expectNorm = expectCode.replace("取件码", "").replace(" ", "").trim();
        if (expectCode.equalsIgnoreCase(got)
                || expect.equalsIgnoreCase(got)
                || expectNorm.equalsIgnoreCase(gotNorm)
                || (!gotNorm.isEmpty() && expectNorm.contains(gotNorm))
                || (!gotNorm.isEmpty() && expect.replace(" ", "").toLowerCase().contains(gotNorm.toLowerCase()))) {
            return;
        }
        throw new IllegalStateException("取件码不正确");
    }
}
