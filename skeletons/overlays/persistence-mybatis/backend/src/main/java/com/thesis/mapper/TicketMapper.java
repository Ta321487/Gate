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

    List<Map<String, Object>> selectOpenApprovedOverdue(@Param("ticketTable") String ticketTable);

    List<Map<String, Object>> selectTickets(Map<String, Object> q);

    List<Map<String, Object>> selectPublicByItem(
            @Param("ticketTable") String ticketTable,
            @Param("itemFk") String itemFk,
            @Param("itemId") long itemId);

    @Select("SELECT COUNT(*) FROM `${ticketTable}` WHERE username=#{username} AND `${itemFk}`=#{itemId} "
            + "AND status IN ('pending','pending_mid','pending_final','approved','overdue')")
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

    @Update("UPDATE `${ticketTable}` SET checked_in_at=NOW(), status='returned' WHERE id=#{id}")
    int updateCheckin(@Param("ticketTable") String ticketTable, @Param("id") long id);

    int updateComplete(Map<String, Object> row);

    @Update("UPDATE `${ticketTable}` SET status=#{status} WHERE id=#{id}")
    int updateStatus(
            @Param("ticketTable") String ticketTable,
            @Param("status") String status,
            @Param("id") long id);

    @Update("UPDATE `${ticketTable}` SET contact_channel=#{channel} WHERE id=#{id}")
    int updateContactChannel(
            @Param("ticketTable") String ticketTable, @Param("id") long id, @Param("channel") String channel);

    @Update("UPDATE `${ticketTable}` SET next_follow_at=#{nextFollowAt} WHERE id=#{id}")
    int updateNextFollowAt(
            @Param("ticketTable") String ticketTable,
            @Param("id") long id,
            @Param("nextFollowAt") Timestamp nextFollowAt);

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
