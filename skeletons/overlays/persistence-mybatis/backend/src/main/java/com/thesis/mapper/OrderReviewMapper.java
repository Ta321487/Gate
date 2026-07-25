package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.sql.Timestamp;
import java.util.List;
import java.util.Map;

@Mapper
public interface OrderReviewMapper {

    @Update("CREATE TABLE IF NOT EXISTS order_review ("
            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
            + "order_id BIGINT NOT NULL,"
            + "username VARCHAR(64) NOT NULL,"
            + "rating INT NOT NULL,"
            + "body VARCHAR(500) DEFAULT '',"
            + "reply VARCHAR(500) DEFAULT '',"
            + "replied_at DATETIME NULL,"
            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
            + "UNIQUE KEY uk_order_review (order_id),"
            + "KEY idx_review_user (username, id)"
            + ")")
    void ensureTable();

    @Select("SELECT COUNT(*) FROM order_review WHERE order_id=#{orderId}")
    int countByOrderId(@Param("orderId") long orderId);

    @Insert("INSERT INTO order_review (order_id,username,rating,body,created_at) "
            + "VALUES (#{orderId},#{username},#{rating},#{body},#{createdAt})")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insert(Map<String, Object> row);

    @Update("UPDATE order_review SET reply=#{reply}, replied_at=#{repliedAt} WHERE id=#{id}")
    int reply(
            @Param("id") long id,
            @Param("reply") String reply,
            @Param("repliedAt") Timestamp repliedAt);

    Map<String, Object> selectById(@Param("id") long id);

    Map<String, Object> selectByOrderId(@Param("orderId") long orderId);

    List<Map<String, Object>> selectAllOrderByIdDesc();

    List<Map<String, Object>> selectByUsername(@Param("username") String username);
}
