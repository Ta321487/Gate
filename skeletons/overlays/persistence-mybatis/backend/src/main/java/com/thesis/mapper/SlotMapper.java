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
            @Param("day") String day);

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

    @Select("SELECT COUNT(*) FROM `${resvTable}` WHERE username=#{username} AND slot_id=#{slotId} AND status IN ('pending','confirmed')")
    int countActiveResv(
            @Param("resvTable") String resvTable,
            @Param("username") String username,
            @Param("slotId") long slotId);

    int insertReservation(Map<String, Object> row);

    @Delete("DELETE FROM `${resvTable}` WHERE id=#{id}")
    int deleteReservation(@Param("resvTable") String resvTable, @Param("id") long id);

    @Update("UPDATE `${resvTable}` SET status=#{status} WHERE id=#{id}")
    int updateResvStatus(
            @Param("resvTable") String resvTable, @Param("id") long id, @Param("status") String status);

    @Update("UPDATE `${resvTable}` SET status='completed', entry_at=NOW() WHERE id=#{id}")
    int completeWithEntry(@Param("resvTable") String resvTable, @Param("id") long id);

    Map<String, Object> selectResvById(@Param("resvTable") String resvTable, @Param("id") long id);

    List<Map<String, Object>> selectReservations(
            @Param("resvTable") String resvTable,
            @Param("username") String username,
            @Param("status") String status);

    @Select("SELECT COUNT(*) FROM `${resvTable}` WHERE status=#{status}")
    long countByStatus(@Param("resvTable") String resvTable, @Param("status") String status);

    List<Map<String, Object>> selectStatusSeries(@Param("resvTable") String resvTable);

    List<Map<String, Object>> selectTrendSeries(@Param("resvTable") String resvTable);
}
