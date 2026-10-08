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

    @Insert("INSERT INTO `${lineTable}` (order_id,item_id,title,price_yuan,qty,line_kind) "
            + "VALUES (#{orderId},#{itemId},#{title},#{priceYuan},#{qty},#{lineKind})")
    int insertLineKind(
            @Param("lineTable") String lineTable,
            @Param("orderId") long orderId,
            @Param("itemId") long itemId,
            @Param("title") String title,
            @Param("priceYuan") double priceYuan,
            @Param("qty") int qty,
            @Param("lineKind") String lineKind);

    @Update("UPDATE `${orderTable}` SET total_yuan=total_yuan+#{addYuan}, updated_at=#{updatedAt} WHERE id=#{id}")
    int bumpOrderTotal(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("addYuan") double addYuan,
            @Param("updatedAt") Timestamp updatedAt);

    @Insert("INSERT INTO `${lineTable}` (order_id,item_id,title,price_yuan,qty,custom_text,spec_choice,attach_url) "
            + "VALUES (#{orderId},#{itemId},#{title},#{priceYuan},#{qty},#{customText},#{specChoice},#{attachUrl})")
    int insertLineCustom(
            @Param("lineTable") String lineTable,
            @Param("orderId") long orderId,
            @Param("itemId") long itemId,
            @Param("title") String title,
            @Param("priceYuan") double priceYuan,
            @Param("qty") int qty,
            @Param("customText") String customText,
            @Param("specChoice") String specChoice,
            @Param("attachUrl") String attachUrl);

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

    List<Map<String, Object>> selectOrdersOwnedByMerchant(
            @Param("orderTable") String orderTable,
            @Param("lineTable") String lineTable,
            @Param("itemTable") String itemTable,
            @Param("ownerUsername") String ownerUsername,
            @Param("status") String status);

    @Select("SELECT COUNT(*) FROM `${lineTable}` l JOIN `${itemTable}` p ON p.id=l.item_id "
            + "WHERE l.order_id=#{orderId} AND p.owner_username=#{ownerUsername}")
    int countMerchantOwnedLines(
            @Param("lineTable") String lineTable,
            @Param("itemTable") String itemTable,
            @Param("orderId") long orderId,
            @Param("ownerUsername") String ownerUsername);

    List<Long> selectIdsByReservation(
            @Param("orderTable") String orderTable, @Param("reservationId") long reservationId);

    List<Long> selectTimedOutPendingIds(
            @Param("orderTable") String orderTable, @Param("minutes") int minutes);

    List<Long> selectTimedOutUnreceivedIds(
            @Param("orderTable") String orderTable, @Param("minutes") int minutes);

    int updateOrderShip(Map<String, Object> row);

    int updateOrderAddress(Map<String, Object> row);

    @Update("UPDATE `${orderTable}` SET status=#{status}, updated_at=#{updatedAt} WHERE id=#{id}")
    int updateOrderStatus(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("status") String status,
            @Param("updatedAt") Timestamp updatedAt);

    @Update("UPDATE `${orderTable}` SET pickup_code=#{pickupCode}, updated_at=#{updatedAt} WHERE id=#{id}")
    int ensurePickupCode(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("pickupCode") String pickupCode,
            @Param("updatedAt") Timestamp updatedAt);

    @Update("UPDATE `${orderTable}` SET notice_agreed=1, updated_at=#{updatedAt} WHERE id=#{id}")
    int markNoticeAgreed(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("updatedAt") Timestamp updatedAt);

    @Update("UPDATE `${orderTable}` SET status=#{status}, pay_channel=#{payChannel}, updated_at=#{updatedAt} "
            + "WHERE id=#{id} AND status='pending'")
    int payPendingOrder(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("status") String status,
            @Param("payChannel") String payChannel,
            @Param("updatedAt") Timestamp updatedAt);

    @Select("SELECT COUNT(*) FROM `${orderTable}` WHERE status=#{status}")
    long countByStatus(@Param("orderTable") String orderTable, @Param("status") String status);

    @Select("SELECT COUNT(*) FROM `${orderTable}` o WHERE o.status=#{status} AND EXISTS ("
            + "SELECT 1 FROM `${lineTable}` l JOIN `${itemTable}` p ON p.id=l.item_id "
            + "WHERE l.order_id=o.id AND p.owner_username=#{ownerUsername})")
    long countByStatusOwned(
            @Param("orderTable") String orderTable,
            @Param("lineTable") String lineTable,
            @Param("itemTable") String itemTable,
            @Param("status") String status,
            @Param("ownerUsername") String ownerUsername);

    @Select("SELECT COALESCE(SUM(x.total_yuan),0) FROM ("
            + "SELECT DISTINCT o.id, o.total_yuan FROM `${orderTable}` o "
            + "INNER JOIN `${lineTable}` l ON l.order_id=o.id "
            + "INNER JOIN `${itemTable}` p ON p.id=l.item_id AND p.owner_username=#{ownerUsername} "
            + "WHERE o.status='completed') x")
    double sumCompletedSalesOwned(
            @Param("orderTable") String orderTable,
            @Param("lineTable") String lineTable,
            @Param("itemTable") String itemTable,
            @Param("ownerUsername") String ownerUsername);

    @Select("SELECT COALESCE(SUM(total_yuan),0) FROM `${orderTable}` WHERE status='completed'")
    double sumCompletedSales(@Param("orderTable") String orderTable);

    List<Map<String, Object>> selectStatusSeries(@Param("orderTable") String orderTable);

    List<Map<String, Object>> selectTrendSeries(@Param("orderTable") String orderTable);

    List<Map<String, Object>> selectMonthSeries(@Param("orderTable") String orderTable);

    List<Map<String, Object>> selectHotSeries(
            @Param("orderTable") String orderTable,
            @Param("lineTable") String lineTable);

    List<Map<String, Object>> selectSalesDailySeries(@Param("orderTable") String orderTable);

    List<Map<String, Object>> selectRefundReasonSeries(@Param("orderTable") String orderTable);

    Map<String, Object> selectOrderByShareToken(
            @Param("orderTable") String orderTable, @Param("token") String token);

    List<Map<String, Object>> selectShipNodes(@Param("orderId") long orderId);

    int insertShipNode(
            @Param("orderId") long orderId,
            @Param("happenedAt") Timestamp happenedAt,
            @Param("title") String title,
            @Param("detail") String detail);

    int applyLoyaltyWithCoupon(Map<String, Object> row);

    int applyLoyaltyPlain(Map<String, Object> row);

    @Update("UPDATE `${orderTable}` SET completed_at=#{completedAt} WHERE id=#{id} AND (completed_at IS NULL)")
    int markCompletedAtIfNull(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("completedAt") Timestamp completedAt);

    @Update("UPDATE `${orderTable}` SET refund_status='pending', refund_reason=#{reason},"
            + " refund_type=#{refundType}, refund_requested_at=#{requestedAt}, updated_at=#{updatedAt} WHERE id=#{id}")
    int requestRefund(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("reason") String reason,
            @Param("refundType") String refundType,
            @Param("requestedAt") Timestamp requestedAt,
            @Param("updatedAt") Timestamp updatedAt);

    @Update("UPDATE `${orderTable}` SET refund_tracking_no=#{trackingNo}, updated_at=#{updatedAt} WHERE id=#{id}")
    int updateRefundTracking(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("trackingNo") String trackingNo,
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

    @Update("UPDATE `${orderTable}` SET refund_status='approved', refund_at=#{refundAt}, updated_at=#{updatedAt} WHERE id=#{id}")
    int approveExchangeRefund(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("refundAt") Timestamp refundAt,
            @Param("updatedAt") Timestamp updatedAt);

    @Select("SELECT share_token FROM `${orderTable}` WHERE id=#{id}")
    String selectShareToken(@Param("orderTable") String orderTable, @Param("id") long id);

    @Update("UPDATE `${orderTable}` SET share_token=#{token} WHERE id=#{id} AND (share_token IS NULL OR share_token='')")
    int updateShareTokenIfEmpty(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("token") String token);

    @Update("UPDATE `${orderTable}` SET receive_verified_at=#{verifiedAt}, updated_at=#{updatedAt} WHERE id=#{id}")
    int verifyReceive(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("verifiedAt") Timestamp verifiedAt,
            @Param("updatedAt") Timestamp updatedAt);

    @Update("UPDATE `${orderTable}` SET warranty_until=#{warrantyUntil}, updated_at=#{updatedAt} WHERE id=#{id}")
    
    int updateInvoice(
            @Param("table") String table,
            @Param("id") long id,
            @Param("invoiceTitle") String invoiceTitle,
            @Param("invoiceStatus") String invoiceStatus,
            @Param("updatedAt") Timestamp updatedAt);

    int updateWarranty(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("warrantyUntil") java.sql.Date warrantyUntil,
            @Param("updatedAt") Timestamp updatedAt);

    @Update("UPDATE `${orderTable}` SET refund_fee_yuan=#{fee}, updated_at=#{updatedAt} WHERE id=#{id}")
    int updateRefundFee(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("fee") double fee,
            @Param("updatedAt") Timestamp updatedAt);

    @Update("UPDATE `${orderTable}` SET rider_username=#{rider}, rider_claimed_at=#{claimedAt}, status='confirmed', updated_at=#{updatedAt} "
            + "WHERE id=#{id} AND (rider_username IS NULL OR rider_username='' OR rider_username=#{rider})")
    int claimRider(
            @Param("orderTable") String orderTable,
            @Param("id") long id,
            @Param("rider") String rider,
            @Param("claimedAt") Timestamp claimedAt,
            @Param("updatedAt") Timestamp updatedAt);

    @Update("UPDATE `${orderTable}` SET rider_username='', rider_claimed_at=NULL, updated_at=NOW() "
            + "WHERE status='confirmed' AND rider_username IS NOT NULL AND rider_username<>'' "
            + "AND rider_claimed_at IS NOT NULL AND rider_claimed_at < DATE_SUB(NOW(), INTERVAL #{timeoutMinutes} MINUTE)")
    int releaseTimedOutRiderClaims(
            @Param("orderTable") String orderTable,
            @Param("timeoutMinutes") int timeoutMinutes);
}
