package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.sql.Timestamp;
import java.util.List;
import java.util.Map;

@Mapper
public interface SlotMapper {

    List<Map<String, Object>> selectSlots(
            @Param("slotTable") String slotTable,
            @Param("itemId") Long itemId,
            @Param("day") String day,
            @Param("bookableOnly") boolean bookableOnly);

    Map<String, Object> selectSlotById(@Param("slotTable") String slotTable, @Param("id") long id);

    @Select("SELECT COUNT(*) FROM `${slotTable}` WHERE item_id=#{itemId} AND start_at=#{startAt} AND end_at=#{endAt}")
    int countSlotRange(
            @Param("slotTable") String slotTable,
            @Param("itemId") long itemId,
            @Param("startAt") Timestamp startAt,
            @Param("endAt") Timestamp endAt);

    @Insert("INSERT INTO `${slotTable}` (item_id,start_at,end_at,capacity,booked) VALUES (#{itemId},#{startAt},#{endAt},#{capacity},0)")
    int insertSlot(
            @Param("slotTable") String slotTable,
            @Param("itemId") long itemId,
            @Param("startAt") Timestamp startAt,
            @Param("endAt") Timestamp endAt,
            @Param("capacity") int capacity);

    @Update("UPDATE `${slotTable}` SET booked=booked+1 WHERE id=#{id} AND booked<capacity")
    int bumpBooked(@Param("slotTable") String slotTable, @Param("id") long id);

    @Update("UPDATE `${slotTable}` SET booked=GREATEST(booked-1,0) WHERE id=#{id}")
    int releaseBooked(@Param("slotTable") String slotTable, @Param("id") long id);

    @Select("SELECT COUNT(*) FROM `${resvTable}` WHERE username=#{username} AND slot_id=#{slotId} AND status IN ('pending','confirmed','waitlisted')")
    int countActiveResv(
            @Param("resvTable") String resvTable,
            @Param("username") String username,
            @Param("slotId") long slotId);

    @Select("SELECT COUNT(*) FROM `${resvTable}` r JOIN `${slotTable}` s ON r.slot_id=s.id "
            + "WHERE r.patient_name=#{patientName} AND s.item_id=#{itemId} AND DATE(s.start_at)=#{day} "
            + "AND r.status IN ('pending','confirmed','waitlisted')")
    int countPatientDay(
            @Param("resvTable") String resvTable,
            @Param("slotTable") String slotTable,
            @Param("patientName") String patientName,
            @Param("itemId") long itemId,
            @Param("day") String day);

    @Select("SELECT id, username FROM `${resvTable}` WHERE slot_id=#{slotId} AND status='waitlisted' ORDER BY id ASC LIMIT 1")
    List<Map<String, Object>> selectOldestWaitlist(
            @Param("resvTable") String resvTable, @Param("slotId") long slotId);

    @Select("SELECT r.id FROM `${resvTable}` r JOIN `${slotTable}` s ON r.slot_id=s.id "
            + "WHERE s.item_id=#{itemId} AND r.status IN ('pending','confirmed','waitlisted') "
            + "AND DATE(s.start_at) BETWEEN #{fromDay} AND #{toDay}")
    List<Map<String, Object>> selectResvInMaintain(
            @Param("resvTable") String resvTable,
            @Param("slotTable") String slotTable,
            @Param("itemId") long itemId,
            @Param("fromDay") String fromDay,
            @Param("toDay") String toDay);

    int insertReservation(Map<String, Object> row);

    @Delete("DELETE FROM `${resvTable}` WHERE id=#{id}")
    int deleteReservation(@Param("resvTable") String resvTable, @Param("id") long id);

    @Update("UPDATE `${resvTable}` SET status=#{status} WHERE id=#{id}")
    int updateResvStatus(
            @Param("resvTable") String resvTable, @Param("id") long id, @Param("status") String status);

    @Update("UPDATE `${resvTable}` SET status='completed', entry_at=NOW() WHERE id=#{id}")
    int completeWithEntry(@Param("resvTable") String resvTable, @Param("id") long id);

    @Update("UPDATE `${resvTable}` SET rating=#{rating}, rating_remark=#{remark}, rated_at=NOW() WHERE id=#{id}")
    int rateReservation(
            @Param("resvTable") String resvTable,
            @Param("id") long id,
            @Param("rating") int rating,
            @Param("remark") String remark);

    Map<String, Object> selectResvById(@Param("resvTable") String resvTable, @Param("id") long id);

    List<Map<String, Object>> selectReservations(
            @Param("resvTable") String resvTable,
            @Param("username") String username,
            @Param("status") String status);

    @Select("SELECT COUNT(*) FROM `${resvTable}` WHERE status=#{status}")
    long countByStatus(@Param("resvTable") String resvTable, @Param("status") String status);

    List<Map<String, Object>> selectStatusSeries(@Param("resvTable") String resvTable);

    List<Map<String, Object>> selectTrendSeries(@Param("resvTable") String resvTable);

    @Update("UPDATE `${resvTable}` SET checked_in_at=NOW(), late_flag=#{lateFlag} WHERE id=#{id}")
    int checkInReservation(
            @Param("resvTable") String resvTable, @Param("id") long id, @Param("lateFlag") int lateFlag);

    @Update("UPDATE `${resvTable}` SET status='cancelled', no_show=1 WHERE id=#{id}")
    int markNoShow(@Param("resvTable") String resvTable, @Param("id") long id);

    @Update("UPDATE `${resvTable}` SET remind_sent=1 WHERE id=#{id}")
    int markRemindSent(@Param("resvTable") String resvTable, @Param("id") long id);

    @Select("SELECT COUNT(*) FROM `${resvTable}` WHERE username=#{username} AND no_show=1")
    int countNoShow(@Param("resvTable") String resvTable, @Param("username") String username);

    List<Map<String, Object>> selectRemindDue(
            @Param("resvTable") String resvTable,
            @Param("slotTable") String slotTable,
            @Param("aheadMinutes") int aheadMinutes);

    List<Map<String, Object>> selectDayFill(
            @Param("slotTable") String slotTable,
            @Param("itemId") long itemId,
            @Param("monthLike") String monthLike);
}
