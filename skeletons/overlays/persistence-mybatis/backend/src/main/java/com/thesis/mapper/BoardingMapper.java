package com.thesis.mapper;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.sql.Timestamp;
import java.util.List;
import java.util.Map;

@Mapper
public interface BoardingMapper {

    @Select("SELECT id, booked, capacity FROM resource_slot WHERE item_id=#{itemId} AND start_at>=#{from} AND start_at<#{to} ORDER BY start_at")
    List<Map<String, Object>> span(
            @Param("itemId") long itemId, @Param("from") Timestamp from, @Param("to") Timestamp to);

    @Update("UPDATE resource_slot SET booked=booked+1 WHERE id=#{id} AND booked<capacity")
    int bump(@Param("id") long id);

    @Update("UPDATE resource_slot SET booked=GREATEST(booked-1,0) WHERE id=#{id}")
    int unbump(@Param("id") long id);

    @Update("UPDATE resource_slot SET booked=GREATEST(booked-1,0) WHERE item_id=#{itemId} AND start_at>=#{from} AND start_at<#{to}")
    int releaseRange(@Param("itemId") long itemId, @Param("from") Timestamp from, @Param("to") Timestamp to);

    @Select("SELECT r.stay_from AS stayFrom, r.stay_to AS stayTo, s.item_id AS itemId FROM ${resv} r JOIN ${slot} s ON s.id=r.slot_id WHERE r.id=#{id}")
    List<Map<String, Object>> stayRow(
            @Param("resv") String resv, @Param("slot") String slot, @Param("id") long id);

    @Select("SELECT COUNT(*) FROM stay_log WHERE id=#{id} AND reservation_id IS NULL AND enabled=1")
    Integer careOn(@Param("id") long id);

    @Select("SELECT id, option_name AS name, enabled FROM stay_log WHERE reservation_id IS NULL AND enabled=1 ORDER BY id")
    List<Map<String, Object>> enabledCares();

    @Select("SELECT id, option_name AS name, enabled FROM stay_log WHERE reservation_id IS NULL ORDER BY id")
    List<Map<String, Object>> allCares();

    @Update("UPDATE stay_log SET option_name=#{name}, enabled=#{enabled} WHERE id=#{id} AND reservation_id IS NULL")
    int updateCare(@Param("id") long id, @Param("name") String name, @Param("enabled") int enabled);

    @Insert("INSERT INTO stay_log (option_name, enabled) VALUES (#{name}, #{enabled})")
    int insertCare(@Param("name") String name, @Param("enabled") int enabled);

    @Select("SELECT id, reservation_id AS reservationId, day_key AS dayKey, note, photo_url AS photoUrl "
            + "FROM stay_log WHERE reservation_id IS NOT NULL ORDER BY day_key DESC, id DESC")
    List<Map<String, Object>> logs();

    @Select("SELECT l.id, l.reservation_id AS reservationId, l.day_key AS dayKey, l.note, l.photo_url AS photoUrl "
            + "FROM stay_log l JOIN reservation r ON r.id=l.reservation_id "
            + "WHERE r.username=#{username} ORDER BY l.day_key DESC, l.id DESC")
    List<Map<String, Object>> mine(@Param("username") String username);

    @Insert("INSERT INTO stay_log (reservation_id, day_key, note, photo_url, enabled) "
            + "VALUES (#{resvId}, #{day}, #{note}, #{photo}, 1)")
    int insertLog(
            @Param("resvId") long resvId,
            @Param("day") String day,
            @Param("note") String note,
            @Param("photo") String photo);

    @Select("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='stay_log'")
    Integer tableCount();
}
