package com.thesis.mapper;

import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Mapper
public interface ConsignMapper {

    @Select("SELECT id, username, status, fee_rate AS feeRate FROM consign_item "
            + "WHERE product_id=#{itemId} AND status<>'rate'")
    List<Map<String, Object>> findByProduct(@Param("itemId") long itemId);

    @Update("UPDATE consign_item SET status='sold' WHERE product_id=#{itemId} AND status='on_sale'")
    int markSold(@Param("itemId") long itemId);

    @Update("UPDATE ${itemTable} SET status=#{status} WHERE id=#{id}")
    int setItemStatus(@Param("itemTable") String itemTable, @Param("id") long id, @Param("status") String status);

    @Select("SELECT COUNT(*) FROM consign_ledger WHERE consign_id=#{consignId} AND order_id=#{orderId}")
    Integer countLedger(@Param("consignId") long consignId, @Param("orderId") long orderId);

    @Insert("INSERT INTO consign_ledger (consign_id, order_id, username, gross_yuan, fee_rate, payout_yuan, withdraw_status) "
            + "VALUES (#{consignId},#{orderId},#{username},#{gross},#{rate},#{payout},'ready')")
    int insertLedger(
            @Param("consignId") long consignId,
            @Param("orderId") long orderId,
            @Param("username") String username,
            @Param("gross") BigDecimal gross,
            @Param("rate") BigDecimal rate,
            @Param("payout") BigDecimal payout);

    @Delete("DELETE FROM consign_ledger WHERE order_id=#{orderId} AND withdraw_status IN ('ready','applied')")
    int deleteUnpaid(@Param("orderId") long orderId);

    @Update("UPDATE consign_item SET status='on_sale' WHERE product_id=#{itemId} AND status='sold'")
    int restore(@Param("itemId") long itemId);

    @Select("SELECT fee_rate AS feeRate FROM consign_item WHERE status='rate' ORDER BY id LIMIT 1")
    List<Map<String, Object>> rate();

    @Update("UPDATE consign_item SET fee_rate=#{rate} WHERE status='rate'")
    int updateRate(@Param("rate") BigDecimal rate);

    @Insert("INSERT INTO consign_item (username, title, expect_yuan, condition_note, status, fee_rate) "
            + "VALUES ('','',0,'','rate',#{rate})")
    int insertRate(@Param("rate") BigDecimal rate);

    @Insert("INSERT INTO consign_item (username, title, expect_yuan, condition_note, status, fee_rate) "
            + "VALUES (#{username},#{title},#{price},#{condition},'pending',#{rate})")
    int insertItem(
            @Param("username") String username,
            @Param("title") String title,
            @Param("price") BigDecimal price,
            @Param("condition") String condition,
            @Param("rate") BigDecimal rate);

    @Select("SELECT id, title, expect_yuan AS expectYuan, condition_note AS conditionNote, status, "
            + "reject_reason AS rejectReason, product_id AS productId, fee_rate AS feeRate "
            + "FROM consign_item WHERE username=#{username} AND status<>'rate' ORDER BY id DESC")
    List<Map<String, Object>> mineItems(@Param("username") String username);

    @Select("SELECT id, consign_id AS consignId, order_id AS orderId, gross_yuan AS grossYuan, "
            + "fee_rate AS feeRate, payout_yuan AS payoutYuan, withdraw_status AS withdrawStatus "
            + "FROM consign_ledger WHERE username=#{username} ORDER BY id DESC")
    List<Map<String, Object>> mineLedgers(@Param("username") String username);

    @Select("SELECT id, username, title, expect_yuan AS expectYuan, condition_note AS conditionNote, status, "
            + "reject_reason AS rejectReason, product_id AS productId, fee_rate AS feeRate "
            + "FROM consign_item WHERE status<>'rate' ORDER BY id DESC")
    List<Map<String, Object>> adminItems();

    @Select("SELECT id, username, title, expect_yuan AS expectYuan, status FROM consign_item WHERE id=#{id}")
    List<Map<String, Object>> findById(@Param("id") long id);

    @Update("UPDATE consign_item SET status='on_sale', product_id=#{productId}, reject_reason='' WHERE id=#{id}")
    int pass(@Param("id") long id, @Param("productId") long productId);

    @Update("UPDATE consign_item SET status='rejected', reject_reason=#{reason} WHERE id=#{id} AND status='pending'")
    int reject(@Param("id") long id, @Param("reason") String reason);

    @Update("UPDATE consign_ledger SET withdraw_status='applied' "
            + "WHERE id=#{id} AND username=#{username} AND withdraw_status='ready'")
    int withdraw(@Param("id") long id, @Param("username") String username);

    @Select("SELECT id, consign_id AS consignId, order_id AS orderId, username, gross_yuan AS grossYuan, "
            + "fee_rate AS feeRate, payout_yuan AS payoutYuan, withdraw_status AS withdrawStatus "
            + "FROM consign_ledger ORDER BY id DESC")
    List<Map<String, Object>> ledgers();

    @Update("UPDATE consign_ledger SET withdraw_status='paid' WHERE id=#{id} AND withdraw_status='applied'")
    int pay(@Param("id") long id);
}
