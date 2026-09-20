package com.thesis.mapper;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;
import java.util.Map;

@Mapper
public interface BlindBoxMapper {

    @Select("SELECT COUNT(*) FROM blind_pool WHERE box_id=#{boxId} AND enabled=1")
    Integer countBox(@Param("boxId") long boxId);

    @Select("SELECT p.prize_id AS prizeId, p.weight, p.hidden, i.title, i.stock "
            + "FROM blind_pool p LEFT JOIN ${itemTable} i ON i.id=p.prize_id "
            + "WHERE p.box_id=#{boxId} AND p.enabled=1 ORDER BY p.id")
    List<Map<String, Object>> pool(@Param("itemTable") String itemTable, @Param("boxId") long boxId);

    @Select("SELECT draws, hidden_got AS hiddenGot FROM blind_pity WHERE username=#{username} AND box_id=#{boxId}")
    Map<String, Object> pity(@Param("username") String username, @Param("boxId") long boxId);

    @Select("SELECT pity_n FROM ${itemTable} WHERE id=#{id}")
    Integer pityN(@Param("itemTable") String itemTable, @Param("id") long id);

    @Insert("INSERT INTO blind_pity (username, box_id, draws, hidden_got) VALUES (#{username},#{boxId},#{draws},#{hiddenGot}) "
            + "ON DUPLICATE KEY UPDATE draws=#{draws}, hidden_got=#{hiddenGot}")
    int upsertPity(
            @Param("username") String username,
            @Param("boxId") long boxId,
            @Param("draws") int draws,
            @Param("hiddenGot") int hiddenGot);

    @Update("UPDATE ${lineTable} SET draw_title=#{title}, draw_hidden=#{hidden} WHERE order_id=#{orderId} AND item_id=#{itemId}")
    int stamp(
            @Param("lineTable") String lineTable,
            @Param("orderId") long orderId,
            @Param("itemId") long itemId,
            @Param("title") String title,
            @Param("hidden") int hidden);

    @Select("SELECT username FROM ${orderTable} WHERE id=#{id}")
    String orderUser(@Param("orderTable") String orderTable, @Param("id") long id);

    @Select("SELECT p.id, p.box_id AS boxId, b.title AS boxTitle, p.prize_id AS prizeId, i.title AS prizeTitle, "
            + "p.weight, p.hidden, p.enabled, b.pity_n AS pityN, i.stock AS prizeStock "
            + "FROM blind_pool p "
            + "LEFT JOIN ${itemTable} b ON b.id=p.box_id "
            + "LEFT JOIN ${itemTable} i ON i.id=p.prize_id "
            + "ORDER BY p.box_id, p.id")
    List<Map<String, Object>> listAll(@Param("itemTable") String itemTable);

    @Select("SELECT id, title, pity_n AS pityN FROM ${itemTable} ORDER BY id")
    List<Map<String, Object>> products(@Param("itemTable") String itemTable);

    @Select("SELECT p.box_id AS id, MAX(i.title) AS title, MAX(i.pity_n) AS pityN, "
            + "MAX(IFNULL(y.draws,0)) AS draws, MAX(IFNULL(y.hidden_got,0)) AS hiddenGot "
            + "FROM blind_pool p "
            + "LEFT JOIN ${itemTable} i ON i.id=p.box_id "
            + "LEFT JOIN blind_pity y ON y.box_id=p.box_id AND y.username=#{username} "
            + "WHERE p.enabled=1 GROUP BY p.box_id ORDER BY p.box_id")
    List<Map<String, Object>> boxes(@Param("itemTable") String itemTable, @Param("username") String username);

    @Select("SELECT DISTINCT prize_id AS id FROM blind_pool WHERE enabled=1 "
            + "AND prize_id NOT IN (SELECT box_id FROM blind_pool WHERE enabled=1)")
    List<Map<String, Object>> prizeOnly();

    @Select("SELECT COUNT(*) FROM blind_pool WHERE prize_id=#{id} AND enabled=1")
    Integer countPrize(@Param("id") long id);

    @Select("SELECT COUNT(*) FROM blind_pool WHERE box_id=#{boxId} AND prize_id=#{prizeId} AND id<>#{id}")
    Integer countDup(@Param("boxId") long boxId, @Param("prizeId") long prizeId, @Param("id") long id);

    @Update("UPDATE blind_pool SET box_id=#{boxId}, prize_id=#{prizeId}, weight=#{weight}, hidden=#{hidden}, enabled=#{enabled} WHERE id=#{id}")
    int updatePool(
            @Param("id") long id,
            @Param("boxId") long boxId,
            @Param("prizeId") long prizeId,
            @Param("weight") int weight,
            @Param("hidden") int hidden,
            @Param("enabled") int enabled);

    @Insert("INSERT INTO blind_pool (box_id, prize_id, weight, hidden, enabled) VALUES (#{boxId},#{prizeId},#{weight},#{hidden},#{enabled})")
    int insertPool(
            @Param("boxId") long boxId,
            @Param("prizeId") long prizeId,
            @Param("weight") int weight,
            @Param("hidden") int hidden,
            @Param("enabled") int enabled);

    @Update("UPDATE ${itemTable} SET pity_n=#{pityN} WHERE id=#{id}")
    int updatePity(
            @Param("itemTable") String itemTable,
            @Param("id") long id,
            @Param("pityN") int pityN);
}
