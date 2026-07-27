package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.math.BigDecimal;
import java.sql.Timestamp;
import java.util.List;
import java.util.Map;

@Mapper
public interface CouponMapper {

    @Update("CREATE TABLE IF NOT EXISTS promo_coupon ("
            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
            + "code VARCHAR(32) NOT NULL,"
            + "label VARCHAR(64) DEFAULT '',"
            + "min_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,"
            + "off_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,"
            + "total_quota INT NOT NULL DEFAULT 0,"
            + "claimed INT NOT NULL DEFAULT 0,"
            + "expire_at DATETIME NULL,"
            + "status VARCHAR(16) NOT NULL DEFAULT 'active',"
            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
            + "UNIQUE KEY uk_promo_code (code)"
            + ")")
    void ensurePromoTable();

    @Update("CREATE TABLE IF NOT EXISTS user_coupon ("
            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
            + "username VARCHAR(64) NOT NULL,"
            + "coupon_id BIGINT NOT NULL,"
            + "status VARCHAR(16) NOT NULL DEFAULT 'unused',"
            + "claimed_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
            + "used_at DATETIME NULL,"
            + "order_id BIGINT NULL,"
            + "UNIQUE KEY uk_user_coupon (username, coupon_id),"
            + "KEY idx_user_coupon_user (username, status, id)"
            + ")")
    void ensureMineTable();

    @Select("SELECT COUNT(*) FROM promo_coupon")
    int countPromo();

    @Insert("INSERT INTO promo_coupon (code,label,min_yuan,off_yuan,total_quota,claimed,expire_at,status) "
            + "VALUES (#{code},#{label},#{minYuan},#{offYuan},0,0,#{expireAt},'active')")
    int insertSeed(
            @Param("code") String code,
            @Param("label") String label,
            @Param("minYuan") BigDecimal minYuan,
            @Param("offYuan") BigDecimal offYuan,
            @Param("expireAt") Timestamp expireAt);

    List<Map<String, Object>> selectActivePromos();

    List<Map<String, Object>> selectAllPromosDesc();

    Map<String, Object> selectPromoById(@Param("id") long id);

    @Insert("INSERT INTO promo_coupon (code,label,min_yuan,off_yuan,total_quota,claimed,expire_at,status) "
            + "VALUES (#{code},#{label},#{minYuan},#{offYuan},#{totalQuota},0,#{expireAt},'active')")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insertPromo(Map<String, Object> row);

    @Update("UPDATE promo_coupon SET label=#{label}, min_yuan=#{minYuan}, off_yuan=#{offYuan}, "
            + "total_quota=#{totalQuota}, expire_at=#{expireAt}, status=#{status} WHERE id=#{id}")
    int updatePromo(Map<String, Object> row);

    @Select("SELECT COUNT(*) FROM user_coupon WHERE username=#{username} AND coupon_id=#{couponId}")
    int countMine(@Param("username") String username, @Param("couponId") long couponId);

    @Insert("INSERT INTO user_coupon (username,coupon_id,status,claimed_at) VALUES (#{username},#{couponId},'unused',#{claimedAt})")
    int insertMine(
            @Param("username") String username,
            @Param("couponId") long couponId,
            @Param("claimedAt") Timestamp claimedAt);

    @Update("UPDATE promo_coupon SET claimed=claimed+1 WHERE id=#{id}")
    int bumpClaimed(@Param("id") long id);

    int countMineFiltered(@Param("username") String username, @Param("status") String status);

    List<Map<String, Object>> selectMineJoined(
            @Param("username") String username, @Param("status") String status);

    Map<String, Object> selectMineJoinedOne(
            @Param("username") String username, @Param("couponId") long couponId);

    List<Map<String, Object>> selectUnusedMineByCode(
            @Param("username") String username, @Param("code") String code);

    List<Map<String, Object>> selectActivePromoByCode(@Param("code") String code);

    Long selectUnusedMineIdByCode(@Param("username") String username, @Param("code") String code);

    @Update("UPDATE user_coupon SET status='used', used_at=#{usedAt}, order_id=#{orderId} WHERE id=#{id}")
    int markMineUsed(
            @Param("id") long id, @Param("usedAt") Timestamp usedAt, @Param("orderId") long orderId);

    @Update("UPDATE user_coupon SET status='unused', used_at=NULL, order_id=NULL "
            + "WHERE order_id=#{orderId} AND status='used'")
    int releaseByOrder(@Param("orderId") long orderId);

    @Update("UPDATE user_coupon u JOIN promo_coupon p ON p.id=u.coupon_id "
            + "SET u.status='expired' "
            + "WHERE u.status='unused' AND p.expire_at IS NOT NULL AND p.expire_at < NOW()")
    int expireSweep();
}
