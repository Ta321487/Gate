package com.thesis.mapper;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;
import java.util.Map;

@Mapper
public interface GroupBuyMapper {

    @Select("SELECT id, target_size AS targetSize, deadline, status FROM group_campaign WHERE status='open'")
    List<Map<String, Object>> openCampaigns();

    @Select("SELECT id, item_id AS itemId, target_size AS targetSize, deadline, status FROM group_campaign WHERE id=#{id}")
    Map<String, Object> campaign(@Param("id") long id);

    @Select("SELECT COUNT(*) FROM group_member WHERE campaign_id=#{id}")
    Integer countMembers(@Param("id") long id);

    @Select("SELECT COUNT(*) FROM group_member WHERE campaign_id=#{id} AND username=#{username}")
    Integer countMine(@Param("id") long id, @Param("username") String username);

    @Select("SELECT order_id FROM group_member WHERE campaign_id=#{id}")
    List<Long> memberOrders(@Param("id") long id);

    @Select("SELECT m.order_id AS orderId, m.username, o.total_yuan AS paid FROM group_member m "
            + "JOIN ${orderTable} o ON o.id=m.order_id WHERE m.campaign_id=#{id} AND o.status='grouping'")
    List<Map<String, Object>> groupingOrders(@Param("orderTable") String orderTable, @Param("id") long id);

    @Insert("INSERT INTO group_member (campaign_id, order_id, username) VALUES (#{campaignId},#{orderId},#{username})")
    int insertMember(
            @Param("campaignId") long campaignId,
            @Param("orderId") long orderId,
            @Param("username") String username);

    @Update("UPDATE group_campaign SET status='formed' WHERE id=#{id} AND status='open'")
    int markFormed(@Param("id") long id);

    @Update("UPDATE group_campaign SET status='failed' WHERE id=#{id} AND status='open'")
    int markFailed(@Param("id") long id);

    @Update("UPDATE ${orderTable} SET status='confirmed', updated_at=NOW() WHERE id=#{id} AND status='grouping'")
    int confirmOrder(@Param("orderTable") String orderTable, @Param("id") long id);

    @Update("UPDATE ${orderTable} SET status='cancelled', updated_at=NOW() WHERE id=#{id} AND status='grouping'")
    int cancelOrder(@Param("orderTable") String orderTable, @Param("id") long id);

    @Select("SELECT c.id, c.item_id AS itemId, c.target_size AS targetSize, c.deadline, c.status, i.title, "
            + "(SELECT COUNT(*) FROM group_member m WHERE m.campaign_id=c.id) AS joined "
            + "FROM group_campaign c LEFT JOIN ${itemTable} i ON i.id=c.item_id "
            + "WHERE c.status='open' AND c.deadline>NOW() ORDER BY c.deadline, c.id")
    List<Map<String, Object>> listOpen(@Param("itemTable") String itemTable);

    @Select("SELECT c.id, c.item_id AS itemId, c.target_size AS targetSize, c.deadline, c.status, i.title, "
            + "(SELECT COUNT(*) FROM group_member m WHERE m.campaign_id=c.id) AS joined "
            + "FROM group_campaign c LEFT JOIN ${itemTable} i ON i.id=c.item_id ORDER BY c.id DESC")
    List<Map<String, Object>> listAll(@Param("itemTable") String itemTable);

    @Select("SELECT id, title FROM ${itemTable} ORDER BY id")
    List<Map<String, Object>> products(@Param("itemTable") String itemTable);

    @Insert("INSERT INTO group_campaign (item_id, target_size, deadline, status) "
            + "VALUES (#{itemId},#{targetSize},#{deadline},'open')")
    int insertCampaign(Map<String, Object> row);

    @Update("UPDATE group_campaign SET item_id=#{itemId}, target_size=#{targetSize}, deadline=#{deadline} "
            + "WHERE id=#{id} AND status='open'")
    int updateCampaign(Map<String, Object> row);
}
