package com.thesis.mapper;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;
import java.util.Map;

@Mapper
public interface PurchaseGateMapper {

    @Select("SELECT id, title, category_id AS categoryId, need_permit AS needPermit, month_limit AS monthLimit "
            + "FROM ${itemTable} WHERE id=#{id}")
    Map<String, Object> gate(@Param("itemTable") String itemTable, @Param("id") long id);

    @Select("SELECT id, title, category_id AS categoryId, month_limit AS monthLimit FROM ${itemTable} "
            + "WHERE need_permit=1 ORDER BY id")
    List<Map<String, Object>> targets(@Param("itemTable") String itemTable);

    @Select("SELECT status FROM purchase_permit WHERE username=#{username} AND item_id=#{itemId} "
            + "ORDER BY id DESC LIMIT 1")
    String latestStatus(@Param("username") String username, @Param("itemId") long itemId);

    @Select("SELECT COUNT(*) FROM purchase_permit WHERE username=#{username} AND status='approved' "
            + "AND category_id=#{categoryId} AND (item_id IS NULL OR item_id=0)")
    Integer categoryApproved(@Param("username") String username, @Param("categoryId") long categoryId);

    @Select("SELECT COALESCE(SUM(l.qty),0) FROM ${lineTable} l JOIN ${orderTable} o ON o.id=l.order_id "
            + "WHERE o.username=#{username} AND l.item_id=#{itemId} AND o.status<>'cancelled' "
            + "AND o.created_at>=#{start} AND o.created_at<#{end}")
    Integer monthQty(
            @Param("orderTable") String orderTable,
            @Param("lineTable") String lineTable,
            @Param("username") String username,
            @Param("itemId") long itemId,
            @Param("start") String start,
            @Param("end") String end);

    @Select("SELECT id, username, item_id AS itemId, category_id AS categoryId, image_url AS imageUrl, status, "
            + "reviewer, reject_reason AS rejectReason, created_at AS createdAt, reviewed_at AS reviewedAt "
            + "FROM purchase_permit WHERE username=#{username} ORDER BY id DESC")
    List<Map<String, Object>> mine(@Param("username") String username);

    @Select("SELECT id, username, item_id AS itemId, category_id AS categoryId, image_url AS imageUrl, status, "
            + "reviewer, reject_reason AS rejectReason, created_at AS createdAt, reviewed_at AS reviewedAt "
            + "FROM purchase_permit ORDER BY id DESC")
    List<Map<String, Object>> listAll();

    @Insert("INSERT INTO purchase_permit (username, item_id, category_id, image_url, status) "
            + "VALUES (#{username}, #{itemId}, #{categoryId}, #{imageUrl}, 'pending')")
    int insert(Map<String, Object> row);

    @Update("UPDATE purchase_permit SET status=#{status}, reviewer=#{reviewer}, reject_reason=#{rejectReason}, "
            + "reviewed_at=NOW() WHERE id=#{id}")
    int review(Map<String, Object> row);
}
