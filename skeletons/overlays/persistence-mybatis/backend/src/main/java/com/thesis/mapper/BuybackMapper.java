package com.thesis.mapper;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Mapper
public interface BuybackMapper {

    @Select("SELECT COUNT(*) FROM buyback_order WHERE product_id=#{id} AND status<>'listed'")
    Integer unlisted(@Param("id") long id);

    @Select("SELECT id, name, enabled FROM buyback_slot WHERE enabled=1 ORDER BY id")
    List<Map<String, Object>> enabledSlots();

    @Select("SELECT id, name, enabled FROM buyback_slot ORDER BY id")
    List<Map<String, Object>> allSlots();

    @Update("UPDATE buyback_slot SET name=#{name}, enabled=#{enabled} WHERE id=#{id}")
    int updateSlot(@Param("id") long id, @Param("name") String name, @Param("enabled") int enabled);

    @Insert("INSERT INTO buyback_slot (name, enabled) VALUES (#{name}, #{enabled})")
    int insertSlot(@Param("name") String name, @Param("enabled") int enabled);

    @Select("SELECT COUNT(*) FROM buyback_slot WHERE enabled=1")
    Integer openSlotCount();

    @Select("SELECT COUNT(*) FROM buyback_slot WHERE id=#{id} AND enabled=1")
    Integer slotOn(@Param("id") long id);

    @Insert("INSERT INTO buyback_order (username, book_title, condition_note, slot_id, status) "
            + "VALUES (#{username}, #{title}, #{note}, #{slotId}, 'pending')")
    int insertOrder(
            @Param("username") String username,
            @Param("title") String title,
            @Param("note") String note,
            @Param("slotId") Long slotId);

    @Select("SELECT o.id, o.book_title AS bookTitle, o.condition_note AS conditionNote, o.quote_yuan AS quoteYuan, "
            + "o.status, o.product_id AS productId, s.name AS slotName "
            + "FROM buyback_order o LEFT JOIN buyback_slot s ON s.id=o.slot_id "
            + "WHERE o.username=#{username} ORDER BY o.id DESC")
    List<Map<String, Object>> mine(@Param("username") String username);

    @Select("SELECT o.id, o.username, o.book_title AS bookTitle, o.condition_note AS conditionNote, "
            + "o.quote_yuan AS quoteYuan, o.status, o.product_id AS productId, s.name AS slotName "
            + "FROM buyback_order o LEFT JOIN buyback_slot s ON s.id=o.slot_id ORDER BY o.id DESC")
    List<Map<String, Object>> allOrders();

    @Select("SELECT id, username, book_title AS bookTitle, condition_note AS conditionNote, "
            + "quote_yuan AS quoteYuan, status, product_id AS productId FROM buyback_order WHERE id=#{id}")
    List<Map<String, Object>> one(@Param("id") long id);

    @Update("UPDATE buyback_order SET status=#{status} WHERE id=#{id}")
    int setStatus(@Param("id") long id, @Param("status") String status);

    @Update("UPDATE buyback_order SET quote_yuan=#{price}, status='quoted' WHERE id=#{id}")
    int quote(@Param("id") long id, @Param("price") BigDecimal price);

    @Update("UPDATE buyback_order SET product_id=#{productId}, status='stocked' WHERE id=#{id}")
    int stock(@Param("id") long id, @Param("productId") long productId);

    @Insert("INSERT INTO ${table} (title, ${author}, ${isbn}, category_id, stock, status, cover_url) "
            + "VALUES (#{title}, #{price}, '', 1, 0, 'unavailable', '')")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insertProduct(Map<String, Object> row);

    @Update("UPDATE ${table} SET condition_grade=#{note} WHERE id=#{id}")
    int setGrade(@Param("table") String table, @Param("note") String note, @Param("id") long id);

    @Select("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() "
            + "AND table_name=#{table} AND column_name='condition_grade'")
    Integer gradeColumn(@Param("table") String table);

    @Update("UPDATE ${table} SET stock=1, status='available' WHERE id=#{id}")
    int publish(@Param("table") String table, @Param("id") long id);
}
