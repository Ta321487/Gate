package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Mapper
public interface TimebankMapper {
    @Select("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='tb_account'")
    Integer countTable();

    @Select("SELECT COUNT(*) FROM tb_account WHERE username=#{username}")
    Integer countAccount(String username);

    @Insert("INSERT INTO tb_account (username, balance_hours) VALUES (#{username}, 0)")
    int insertAccount(String username);

    @Select("SELECT id, username, balance_hours AS balanceHours, updated_at AS updatedAt FROM tb_account WHERE username=#{username}")
    Map<String, Object> getAccount(String username);

    @Select("SELECT COUNT(*) FROM tb_account")
    Integer countAccounts();

    @Select("SELECT id, username, balance_hours AS balanceHours, updated_at AS updatedAt FROM tb_account ORDER BY updated_at DESC, id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageAccounts(@Param("limit") int limit, @Param("offset") int offset);

    @Select("SELECT COUNT(*) FROM tb_ledger WHERE username=#{username}")
    Integer countLedgerMine(String username);

    @Select("SELECT id, username, delta_hours AS deltaHours, reason, ref_type AS refType, ref_id AS refId, created_at AS createdAt FROM tb_ledger WHERE username=#{username} ORDER BY id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageLedgerMine(@Param("username") String username, @Param("limit") int limit, @Param("offset") int offset);

    @Select("SELECT COUNT(*) FROM tb_ledger")
    Integer countLedgerAll();

    @Select("SELECT id, username, delta_hours AS deltaHours, reason, ref_type AS refType, ref_id AS refId, created_at AS createdAt FROM tb_ledger ORDER BY id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageLedgerAll(@Param("limit") int limit, @Param("offset") int offset);

    @Update("UPDATE tb_account SET balance_hours = balance_hours + #{hours} WHERE username=#{username}")
    int addBalance(@Param("username") String username, @Param("hours") BigDecimal hours);

    @Update("UPDATE tb_account SET balance_hours = balance_hours - #{hours} WHERE username=#{username}")
    int subBalance(@Param("username") String username, @Param("hours") BigDecimal hours);

    @Insert("INSERT INTO tb_ledger (username, delta_hours, reason, ref_type, ref_id) VALUES (#{username}, #{delta}, #{reason}, #{refType}, #{refId})")
    int insertLedger(
            @Param("username") String username,
            @Param("delta") BigDecimal delta,
            @Param("reason") String reason,
            @Param("refType") String refType,
            @Param("refId") Long refId);

    @Select("SELECT COUNT(*) FROM tb_service WHERE id=#{id} AND status='available'")
    Integer countOpenService(long id);

    @Select("SELECT id, title, author, isbn, category_id AS categoryId, stock, status FROM tb_service WHERE status='available' AND stock>0 ORDER BY id DESC")
    List<Map<String, Object>> listOpenServices();
}
