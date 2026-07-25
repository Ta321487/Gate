package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.math.BigDecimal;
import java.sql.Timestamp;
import java.util.List;
import java.util.Map;

@Mapper
public interface OrderMapper {

    List<Map<String, Object>> selectCart(@Param("cartTable") String cartTable, @Param("username") String username);

    Map<String, Object> selectCartItem(
            @Param("cartTable") String cartTable,
            @Param("username") String username,
            @Param("itemId") long itemId);

    @Select("SELECT COUNT(*) FROM `${cartTable}` WHERE username=#{username} AND item_id=#{itemId}")
    int countCartItem(
            @Param("cartTable") String cartTable,
            @Param("username") String username,
            @Param("itemId") long itemId);

    @Update("UPDATE `${cartTable}` SET qty=#{qty} WHERE username=#{username} AND item_id=#{itemId}")
    int updateCartQty(
            @Param("cartTable") String cartTable,
            @Param("username") String username,
            @Param("itemId") long itemId,
            @Param("qty") int qty);

    @Insert("INSERT INTO `${cartTable}` (username,item_id,qty) VALUES (#{username},#{itemId},#{qty})")
    int insertCart(
            @Param("cartTable") String cartTable,
            @Param("username") String username,
            @Param("itemId") long itemId,
            @Param("qty") int qty);

    @Delete("DELETE FROM `${cartTable}` WHERE username=#{username} AND item_id=#{itemId}")
    int deleteCartItem(
            @Param("cartTable") String cartTable,
            @Param("username") String username,
            @Param("itemId") long itemId);

    @Delete("DELETE FROM `${cartTable}` WHERE username=#{username}")
    int clearCart(@Param("cartTable") String cartTable, @Param("username") String username);

    int insertOrder(Map<String, Object> row);

    @Insert("INSERT INTO `${lineTable}` (order_id,item_id,title,price_yuan,qty) "
            + "VALUES (#{orderId},#{itemId},#{title},#{priceYuan},#{qty})")
    int insertLine(
            @Param("lineTable") String lineTable,
            @Param("orderId") long orderId,
            @Param("itemId") long itemId,
            @Param("title") String title,
            @Param("priceYuan") double priceYuan,
            @Param("qty") int qty);

    @Delete("DELETE FROM `${lineTable}` WHERE order_id=#{orderId}")
    int deleteLines(@Param("lineTable") String lineTable, @Param("orderId") long orderId);

    @Delete("DELETE FROM `${orderTable}` WHERE id=#{id}")
    int deleteOrder(@Param("orderTable") String orderTable, @Param("id") long id);

    Map<String, Object> selectOrderById(@Param("orderTable") String orderTable, @Param("id") long id);

    List<Map<String, Object>> selectLines(@Param("lineTable") String lineTable, @Param("orderId") long orderId);

    List<Map<String, Object>> selectOrders(
            @Param("orderTable") String orderTable,
            @Param("username") String username,
            @Param("status") String status);

    List<Long> selectIdsByReservation(
            @Param("orderTable") String orderTable, @Param("reservationId") long reservationId);

    List<Long> selectTimedOutPendingIds(
            @Param("orderTable") String orderTable, @Param("minutes") int minutes);

    int updateOrderShip(Map<String, Object> row);

    @Update("UPDATE `${orderTable}` SET status=#{status}, updated_at=#{updatedAt} WHERE id=#{id}")
    int updateOrderStatus(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("status") String status,
            @Param("updatedAt") Timestamp updatedAt);

    @Select("SELECT COUNT(*) FROM `${orderTable}` WHERE status=#{status}")
    long countByStatus(@Param("orderTable") String orderTable, @Param("status") String status);

    List<Map<String, Object>> selectStatusSeries(@Param("orderTable") String orderTable);

    List<Map<String, Object>> selectTrendSeries(@Param("orderTable") String orderTable);

    int applyLoyaltyWithCoupon(Map<String, Object> row);

    int applyLoyaltyPlain(Map<String, Object> row);

    @Update("UPDATE `${orderTable}` SET refund_status='pending', refund_reason=#{reason}, updated_at=#{updatedAt} WHERE id=#{id}")
    int requestRefund(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("reason") String reason,
            @Param("updatedAt") Timestamp updatedAt);

    @Update("UPDATE `${orderTable}` SET refund_status='rejected', refund_reason=#{reason}, refund_at=#{refundAt}, updated_at=#{updatedAt} WHERE id=#{id}")
    int rejectRefund(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("reason") String reason,
            @Param("refundAt") Timestamp refundAt,
            @Param("updatedAt") Timestamp updatedAt);

    @Update("UPDATE `${orderTable}` SET status='cancelled', refund_status='approved', refund_at=#{refundAt}, updated_at=#{updatedAt} WHERE id=#{id}")
    int approveRefund(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("refundAt") Timestamp refundAt,
            @Param("updatedAt") Timestamp updatedAt);
}
