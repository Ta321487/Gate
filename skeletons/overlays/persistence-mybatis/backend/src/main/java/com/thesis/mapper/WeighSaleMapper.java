package com.thesis.mapper;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Mapper
public interface WeighSaleMapper {

    @Update("UPDATE ${lineTable} SET weight_qty=#{weight} WHERE order_id=#{orderId} AND item_id=#{itemId}")
    int saveWeight(
            @Param("lineTable") String lineTable,
            @Param("orderId") long orderId,
            @Param("itemId") long itemId,
            @Param("weight") BigDecimal weight);

    @Select("SELECT enabled, cap_yuan AS capYuan FROM loss_policy WHERE id=1")
    List<Map<String, Object>> policy();

    @Update("UPDATE loss_policy SET enabled=#{enabled}, cap_yuan=#{cap} WHERE id=1")
    int updatePolicy(@Param("enabled") int enabled, @Param("cap") BigDecimal cap);

    @Insert("INSERT INTO loss_policy (id, enabled, cap_yuan) VALUES (1,#{enabled},#{cap})")
    int insertPolicy(@Param("enabled") int enabled, @Param("cap") BigDecimal cap);

    @Select("SELECT username, status FROM ${orderTable} WHERE id=#{id}")
    List<Map<String, Object>> order(@Param("orderTable") String orderTable, @Param("id") long id);

    @Select("SELECT COUNT(*) FROM loss_claim WHERE order_id=#{orderId} AND status='pending'")
    Integer countPending(@Param("orderId") long orderId);

    @Insert("INSERT INTO loss_claim (username, order_id, amount_yuan, reason, status) "
            + "VALUES (#{username},#{orderId},#{amount},#{reason},'pending')")
    int insertClaim(
            @Param("username") String username,
            @Param("orderId") long orderId,
            @Param("amount") BigDecimal amount,
            @Param("reason") String reason);

    @Select("SELECT id, order_id AS orderId, amount_yuan AS amountYuan, reason, status, paid_yuan AS paidYuan "
            + "FROM loss_claim WHERE username=#{username} ORDER BY id DESC")
    List<Map<String, Object>> mine(@Param("username") String username);

    @Select("SELECT id, username, order_id AS orderId, amount_yuan AS amountYuan, reason, status, paid_yuan AS paidYuan "
            + "FROM loss_claim ORDER BY id DESC")
    List<Map<String, Object>> admin();

    @Select("SELECT id, username, amount_yuan AS amountYuan, status FROM loss_claim WHERE id=#{id}")
    List<Map<String, Object>> find(@Param("id") long id);

    @Update("UPDATE loss_claim SET status='approved', paid_yuan=#{paid} WHERE id=#{id}")
    int approve(@Param("id") long id, @Param("paid") BigDecimal paid);

    @Update("UPDATE loss_claim SET status='rejected', reason=#{reason} WHERE id=#{id} AND status='pending'")
    int reject(@Param("id") long id, @Param("reason") String reason);

    @Update("UPDATE sys_user SET balance_yuan=IFNULL(balance_yuan,0)+#{yuan} WHERE username=#{username}")
    int credit(@Param("username") String username, @Param("yuan") BigDecimal yuan);
}
