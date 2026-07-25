package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Mapper
public interface LoyaltyMapper {

    @Update("CREATE TABLE IF NOT EXISTS user_ledger ("
            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
            + "username VARCHAR(64) NOT NULL,"
            + "kind VARCHAR(16) NOT NULL,"
            + "delta DECIMAL(12,2) NOT NULL,"
            + "balance_after DECIMAL(12,2) NOT NULL DEFAULT 0,"
            + "reason VARCHAR(64) DEFAULT '',"
            + "ref_type VARCHAR(32) DEFAULT '',"
            + "ref_id BIGINT NULL,"
            + "operator VARCHAR(64) DEFAULT '',"
            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
            + "KEY idx_ledger_user (username, id))")
    void ensureLedgerTable();

    Map<String, Object> selectAccount(@Param("username") String username);

    @Update("UPDATE sys_user SET balance_yuan=#{balanceYuan} WHERE username=#{username}")
    int updateBalance(@Param("username") String username, @Param("balanceYuan") BigDecimal balanceYuan);

    @Update("UPDATE sys_user SET points=#{points} WHERE username=#{username}")
    int updatePoints(@Param("username") String username, @Param("points") int points);

    @Update("UPDATE sys_user SET spend_total_yuan=IFNULL(spend_total_yuan,0)+#{pay} WHERE username=#{username}")
    int addSpend(@Param("username") String username, @Param("pay") BigDecimal pay);

    @Update("UPDATE sys_user SET member_tier=#{tier} WHERE username=#{username}")
    int updateTier(@Param("username") String username, @Param("tier") String tier);

    @Update("UPDATE biz_order SET points_earned=#{points} WHERE id=#{orderId}")
    int updateOrderPoints(@Param("orderId") long orderId, @Param("points") int points);

    @Insert("INSERT INTO user_ledger (username,kind,delta,balance_after,reason,ref_type,ref_id,operator) "
            + "VALUES (#{username},#{kind},#{delta},#{balanceAfter},#{reason},#{refType},#{refId},#{operator})")
    int insertLedger(Map<String, Object> row);

    List<Map<String, Object>> selectLedger(@Param("username") String username);
}
