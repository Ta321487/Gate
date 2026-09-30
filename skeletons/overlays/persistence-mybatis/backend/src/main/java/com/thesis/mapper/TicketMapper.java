package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.sql.Timestamp;
import java.util.List;
import java.util.Map;

@Mapper
public interface TicketMapper {

    int insertArchive(Map<String, Object> row);

    int insertStandalone(Map<String, Object> row);

    Map<String, Object> selectById(@Param("ticketTable") String ticketTable, @Param("id") long id);

    @Delete("DELETE FROM `${ticketTable}` WHERE id=#{id}")
    int deleteById(@Param("ticketTable") String ticketTable, @Param("id") long id);

    List<Map<String, Object>> selectPeerInbox(
            @Param("ticketTable") String ticketTable,
            @Param("itemTable") String itemTable,
            @Param("itemFk") String itemFk,
            @Param("owner") String owner,
            @Param("status") String status);

    @Update("UPDATE `${ticketTable}` SET pass_code=#{passCode} WHERE id=#{id}")
    int updatePassCode(
            @Param("ticketTable") String ticketTable, @Param("id") long id, @Param("passCode") String passCode);

    List<Map<String, Object>> selectOpenApprovedOverdue(@Param("ticketTable") String ticketTable);

    List<Map<String, Object>> selectTickets(Map<String, Object> q);

    List<Map<String, Object>> selectPublicByItem(
            @Param("ticketTable") String ticketTable,
            @Param("itemFk") String itemFk,
            @Param("itemId") long itemId);

    @Select("SELECT COUNT(*) FROM `${ticketTable}` WHERE username=#{username} AND `${itemFk}`=#{itemId} "
            + "AND status IN ('pending','pending_mid','pending_final','approved','overdue','waitlisted','held','hold_ready')")
    int countActiveDup(
            @Param("ticketTable") String ticketTable,
            @Param("itemFk") String itemFk,
            @Param("username") String username,
            @Param("itemId") long itemId);

    int countActiveByUser(
            @Param("ticketTable") String ticketTable,
            @Param("username") String username,
            @Param("multiTicket") boolean multiTicket);

    List<String> selectMutexConflictTitles(Map<String, Object> q);

    int countCategoryActive(Map<String, Object> q);

    List<Map<String, Object>> selectTimeConflictOccupied(Map<String, Object> q);

    int updatePickup(Map<String, Object> row);

    @Update("UPDATE `${ticketTable}` SET fine_status='paid' WHERE id=#{id}")
    int updateFinePaid(@Param("ticketTable") String ticketTable, @Param("id") long id);

    int updateFineWaived(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("withFineYuan") boolean withFineYuan);

    int updateReject(Map<String, Object> row);

    int updatePendingFinal(Map<String, Object> row);

    int updateApproveStage(Map<String, Object> row);

    int updateApproved(Map<String, Object> row);

    List<Long> selectSiblingPendingIds(
            @Param("ticketTable") String ticketTable,
            @Param("itemFk") String itemFk,
            @Param("itemId") long itemId,
            @Param("excludeId") long excludeId);

    @Update("UPDATE `${ticketTable}` SET status='rejected', approve_at=NOW(), remark=#{remark} "
            + "WHERE id=#{id} AND status IN ('pending','pending_mid','pending_final')")
    int updateRejectSibling(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("remark") String remark);

    @Update("UPDATE `${ticketTable}` SET rating=#{rating}, rating_remark=#{ratingRemark}, rated_at=NOW(), "
            + "rating_dims_json=#{ratingDimsJson}, rating_anonymous=#{ratingAnonymous} WHERE id=#{id}")
    int updateRating(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("rating") int rating,
            @Param("ratingRemark") String ratingRemark,
            @Param("ratingDimsJson") String ratingDimsJson,
            @Param("ratingAnonymous") int ratingAnonymous);

    @Update("UPDATE `${ticketTable}` SET rating=#{rating}, rating_remark=#{ratingRemark}, rated_at=NOW() WHERE id=#{id}")
    int updateRatingBasic(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("rating") int rating,
            @Param("ratingRemark") String ratingRemark);

    @Update("UPDATE `${ticketTable}` SET checked_in_at=NOW(), status='returned' WHERE id=#{id}")
    int updateCheckin(@Param("ticketTable") String ticketTable, @Param("id") long id);

    int updateComplete(Map<String, Object> row);

    @Update("UPDATE `${ticketTable}` SET status=#{status} WHERE id=#{id}")
    int updateStatus(
            @Param("ticketTable") String ticketTable,
            @Param("status") String status,
            @Param("id") long id);

    @Update("UPDATE `${ticketTable}` SET status='verifying' WHERE id=#{id} AND status IN ('pending','verifying')")
    int updateMarkVerifying(@Param("ticketTable") String ticketTable, @Param("id") long id);

    @Update("UPDATE `${ticketTable}` SET status='pending' WHERE id=#{id} AND status='verifying'")
    int updateMarkPendingForProof(@Param("ticketTable") String ticketTable, @Param("id") long id);

    @Update("UPDATE `${ticketTable}` SET contact_channel=#{channel} WHERE id=#{id}")
    int updateContactChannel(
            @Param("ticketTable") String ticketTable, @Param("id") long id, @Param("channel") String channel);

    @Update("UPDATE `${ticketTable}` SET next_follow_at=#{nextFollowAt} WHERE id=#{id}")
    int updateNextFollowAt(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("nextFollowAt") Timestamp nextFollowAt);

    @Update("UPDATE `${ticketTable}` SET week_no=#{weekNo} WHERE id=#{id}")
    int updateWeekNo(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("weekNo") int weekNo);

    @Update("UPDATE `${ticketTable}` SET interview_result=#{result} WHERE id=#{id}")
    int updateInterviewResult(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("result") String result);

    @Update("UPDATE `${ticketTable}` SET interview_place=#{place} WHERE id=#{id}")
    int updateInterviewPlace(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("place") String place);

    @Update("UPDATE `${ticketTable}` SET fine_yuan=#{fineYuan} WHERE id=#{id}")
    int updateFineYuan(
            @Param("ticketTable") String ticketTable, @Param("id") long id, @Param("fineYuan") double fineYuan);

    int updateFinePersist(Map<String, Object> row);

    @Select("SELECT COUNT(*) FROM `${ticketTable}` WHERE status IN ('pending','pending_mid','pending_final')")
    long countPending(@Param("ticketTable") String ticketTable);

    @Select("SELECT COUNT(*) FROM `${ticketTable}` WHERE status=#{status}")
    long countByStatus(@Param("ticketTable") String ticketTable, @Param("status") String status);

    @Select("SELECT COALESCE(SUM(fine_yuan),0) FROM `${ticketTable}` WHERE status='overdue'")
    Double sumOpenFine(@Param("ticketTable") String ticketTable);

    @Select("SELECT AVG(rating) FROM `${ticketTable}` WHERE rating IS NOT NULL AND rating > 0")
    Double avgRating(@Param("ticketTable") String ticketTable);

    @Select("SELECT COUNT(*) FROM `${ticketTable}` WHERE rating IS NOT NULL AND rating > 0")
    long countRated(@Param("ticketTable") String ticketTable);

    List<Map<String, Object>> selectStatusSeries(@Param("ticketTable") String ticketTable);

    List<Map<String, Object>> selectTrendSeries(@Param("ticketTable") String ticketTable);

    List<Map<String, Object>> selectChannelSeries(@Param("ticketTable") String ticketTable);

    List<Map<String, Object>> selectHotItemSeries(
            @Param("ticketTable") String ticketTable,
            @Param("itemTable") String itemTable,
            @Param("itemFk") String itemFk);

    @Select("SELECT DISTINCT username FROM `${ticketTable}` "
            + "WHERE username IS NOT NULL AND TRIM(username)<>'' LIMIT 200")
    List<String> selectDistinctUsernames(@Param("ticketTable") String ticketTable);

    @Select("SELECT COUNT(*) FROM `${ticketTable}` WHERE username=#{username} AND week_no=#{weekNo}")
    int countByUsernameWeekNo(
            @Param("ticketTable") String ticketTable,
            @Param("username") String username,
            @Param("weekNo") int weekNo);

    @Select("SELECT COUNT(*) FROM `${ticketTable}` WHERE username=#{username} AND status='cancelled'")
    int countCancelledByUser(
            @Param("ticketTable") String ticketTable, @Param("username") String username);

    @Select("SELECT COUNT(*) FROM `${ticketTable}` WHERE username=#{username} AND ever_overdue=1")
    int countEverOverdueByUser(
            @Param("ticketTable") String ticketTable, @Param("username") String username);

    @Select("SELECT COUNT(*) FROM `${ticketTable}` WHERE `${itemFk}`=#{itemId} "
            + "AND status IN ('held','hold_ready') AND username<>#{username}")
    int countHoldsByItemExcludingUser(
            @Param("ticketTable") String ticketTable,
            @Param("itemFk") String itemFk,
            @Param("itemId") long itemId,
            @Param("username") String username);

    @Select("SELECT id FROM `${ticketTable}` WHERE `${itemFk}`=#{itemId} AND status='waitlisted' "
            + "ORDER BY apply_at ASC, id ASC LIMIT 1")
    Long selectEarliestWaitlistedId(
            @Param("ticketTable") String ticketTable,
            @Param("itemFk") String itemFk,
            @Param("itemId") long itemId);

    @Select("SELECT id FROM `${ticketTable}` WHERE `${itemFk}`=#{itemId} AND status='held' "
            + "ORDER BY apply_at ASC, id ASC LIMIT 1")
    Long selectEarliestHeldId(
            @Param("ticketTable") String ticketTable,
            @Param("itemFk") String itemFk,
            @Param("itemId") long itemId);

    List<Long> selectExpiredHoldReadyIds(@Param("ticketTable") String ticketTable);

    @Update("UPDATE `${ticketTable}` SET status='pending' WHERE id=#{id} AND status='waitlisted'")
    int updatePromoteWaitlist(@Param("ticketTable") String ticketTable, @Param("id") long id);

    @Update("UPDATE `${ticketTable}` SET status='hold_ready', hold_expire_at=#{holdExpireAt} "
            + "WHERE id=#{id} AND status='held'")
    int updatePromoteHoldReady(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("holdExpireAt") Timestamp holdExpireAt);

    @Update("UPDATE `${ticketTable}` SET status='cancelled', hold_expire_at=NULL "
            + "WHERE id=#{id} AND status='hold_ready'")
    int updateCancelExpiredHold(@Param("ticketTable") String ticketTable, @Param("id") long id);

    @Update("UPDATE `${ticketTable}` SET due_soon_notified_at=#{ts} WHERE id=#{id}")
    int updateDueSoonNotified(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("ts") Timestamp ts);

    @Update("UPDATE `${ticketTable}` SET follow_soon_notified_at=#{ts} WHERE id=#{id}")
    int updateFollowSoonNotified(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("ts") Timestamp ts);

    @Update("UPDATE `${ticketTable}` SET ever_overdue=1 WHERE id=#{id}")
    int updateEverOverdue(@Param("ticketTable") String ticketTable, @Param("id") long id);

    /** 撤销申请 / 驳回待取书：status + 可选清 hold_expire_at */
    int updateCancelOrRejectHold(Map<String, Object> row);

    /** hold_ready → approved（确认借阅，不二次扣库存） */
    int updateHoldReadyApprove(Map<String, Object> row);

    /** 续借：延 due_at、renew_count、清逾期标记 */
    int updateRenew(Map<String, Object> row);

    /** 任意已校验列名写回（patchTicketExtras / 跟进加厚字段）。 */
    int updateColumnById(
            @Param("ticketTable") String ticketTable,
            @Param("column") String column,
            @Param("value") Object value,
            @Param("id") long id);

    @Update("UPDATE `${ticketTable}` SET proxy_name=#{proxyName}, proxy_phone=#{proxyPhone} WHERE id=#{id}")
    int updateProxyPair(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("proxyName") String proxyName,
            @Param("proxyPhone") String proxyPhone);

    @Update("UPDATE `${ticketTable}` SET peer_username=#{peerUsername}, peer_ack=0 WHERE id=#{id}")
    int updatePeerUsername(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("peerUsername") String peerUsername);

    @Update("UPDATE `${ticketTable}` SET peer_ack=1 WHERE id=#{id}")
    int updatePeerAck(@Param("ticketTable") String ticketTable, @Param("id") long id);

    @Update("UPDATE `${ticketTable}` SET status='rejected', remark=#{remark}, peer_ack=0 WHERE id=#{id}")
    int updatePeerReject(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("remark") String remark);

    @Update("UPDATE `${ticketTable}` SET status='rejected', approve_at=NOW(), remark=#{remark} WHERE id=#{id}")
    int updateHideRejected(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("remark") String remark);

    int countPeerConfirmInbox(
            @Param("ticketTable") String ticketTable, @Param("username") String username);

    List<Map<String, Object>> selectPeerConfirmInbox(
            @Param("ticketTable") String ticketTable, @Param("username") String username);

    @Select("SELECT COUNT(*) FROM procure_line WHERE ticket_id=#{ticketId}")
    int countProcureLineByTicket(@Param("ticketId") long ticketId);

    @Insert("INSERT INTO procure_line (ticket_id, item_title, qty, unit_price) VALUES (#{ticketId},#{title},#{qty},0)")
    int insertProcureLine(
            @Param("ticketId") long ticketId, @Param("title") String title, @Param("qty") int qty);

    List<Map<String, Object>> selectProgress(
            @Param("progressTable") String progressTable, @Param("ticketId") long ticketId);

    @Insert("INSERT INTO `${progressTable}` (ticket_id,status,operator,remark,created_at) "
            + "VALUES (#{ticketId},#{status},#{operator},#{remark},#{createdAt})")
    int insertProgress(
            @Param("progressTable") String progressTable,
            @Param("ticketId") long ticketId,
            @Param("status") String status,
            @Param("operator") String operator,
            @Param("remark") String remark,
            @Param("createdAt") Timestamp createdAt);

    Map<String, Object> selectTicketForBackfill(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("withRating") boolean withRating);
}
