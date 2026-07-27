package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface StockIoMapper {

    @Select("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='stock_move'")
    Integer countTable();

    @Select("SELECT COUNT(*) FROM stock_move")
    Integer countAll();

    @Select("SELECT COUNT(*) FROM stock_move WHERE move_type=#{moveType}")
    Integer countByType(String moveType);

    @Select("SELECT id, move_type AS moveType, item_id AS itemId, item_title AS itemTitle, qty, remark, operator, created_at AS createdAt "
            + "FROM stock_move ORDER BY id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageAll(@Param("limit") int limit, @Param("offset") int offset);

    @Select("SELECT id, move_type AS moveType, item_id AS itemId, item_title AS itemTitle, qty, remark, operator, created_at AS createdAt "
            + "FROM stock_move WHERE move_type=#{moveType} ORDER BY id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageByType(
            @Param("moveType") String moveType, @Param("limit") int limit, @Param("offset") int offset);

    @Insert("INSERT INTO stock_move (move_type, item_id, item_title, qty, remark, operator) "
            + "VALUES (#{moveType}, #{itemId}, #{itemTitle}, #{qty}, #{remark}, #{operator})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(Map<String, Object> row);

    @Select("SELECT id, move_type AS moveType, item_id AS itemId, item_title AS itemTitle, qty, remark, operator, created_at AS createdAt "
            + "FROM stock_move WHERE id=#{id}")
    Map<String, Object> getById(long id);
}
