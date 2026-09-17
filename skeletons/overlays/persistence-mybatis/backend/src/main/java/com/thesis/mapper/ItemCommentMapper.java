package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface ItemCommentMapper {

    @Select("SELECT COUNT(*) FROM information_schema.tables "
            + "WHERE table_schema=DATABASE() AND table_name='item_comment'")
    Integer countTable();

    Map<String, Object> selectById(@Param("id") long id);

    List<Map<String, Object>> selectByItem(@Param("itemId") long itemId);

    List<Map<String, Object>> selectAdmin(@Param("itemId") Long itemId);

    @Insert("INSERT INTO item_comment (item_id,username,nickname,body) VALUES (#{itemId},#{username},#{nickname},#{body})")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insert(Map<String, Object> row);

    @Delete("DELETE FROM item_comment WHERE id=#{id}")
    int deleteById(@Param("id") long id);
}
