package com.thesis.mapper;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;
import java.util.Map;

@Mapper
public interface DeliveryWindowMapper {

    @Select("SELECT id, label, start_hm AS startHm, end_hm AS endHm, capacity, fulfill_mode AS fulfillMode, "
            + "cutoff_hm AS cutoffHm, enabled, sort_no AS sortNo FROM delivery_slot ORDER BY sort_no, id")
    List<Map<String, Object>> listSlots();

    @Select("SELECT id, name, date_from AS dateFrom, date_to AS dateTo, rate, enabled FROM price_span ORDER BY date_from, id")
    List<Map<String, Object>> listSpans();

    @Select("SELECT COUNT(*) FROM ${orderTable} WHERE slot_id=#{slotId} AND delivery_on=#{day} AND status<>'cancelled'")
    Integer countBooked(
            @Param("orderTable") String orderTable,
            @Param("slotId") long slotId,
            @Param("day") String day);

    @Select("SELECT name, rate FROM price_span WHERE enabled=1 AND date_from<=#{day} AND date_to>=#{day} "
            + "ORDER BY rate DESC LIMIT 1")
    Map<String, Object> topSpan(@Param("day") String day);

    @Insert("INSERT INTO delivery_slot (label, start_hm, end_hm, capacity, fulfill_mode, cutoff_hm, enabled, sort_no) "
            + "VALUES (#{label},#{startHm},#{endHm},#{capacity},#{fulfillMode},#{cutoffHm},#{enabled},#{sortNo})")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insertSlot(Map<String, Object> row);

    @Update("UPDATE delivery_slot SET label=#{label}, start_hm=#{startHm}, end_hm=#{endHm}, capacity=#{capacity}, "
            + "fulfill_mode=#{fulfillMode}, cutoff_hm=#{cutoffHm}, enabled=#{enabled}, sort_no=#{sortNo} WHERE id=#{id}")
    int updateSlot(Map<String, Object> row);

    @Insert("INSERT INTO price_span (name, date_from, date_to, rate, enabled) "
            + "VALUES (#{name},#{dateFrom},#{dateTo},#{rate},#{enabled})")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insertSpan(Map<String, Object> row);

    @Update("UPDATE price_span SET name=#{name}, date_from=#{dateFrom}, date_to=#{dateTo}, rate=#{rate}, enabled=#{enabled} "
            + "WHERE id=#{id}")
    int updateSpan(Map<String, Object> row);
}
