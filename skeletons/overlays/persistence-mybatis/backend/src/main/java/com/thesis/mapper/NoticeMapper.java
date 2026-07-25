package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface NoticeMapper {

    Map<String, Object> selectById(@Param("id") long id);

    int countAll();

    List<Map<String, Object>> selectAllOrderByIdDesc();

    @Insert(
            "INSERT INTO sys_notice (title,content,publisher_username,publisher_name) "
                    + "VALUES (#{title},#{content},#{publisherUsername},#{publisherName})")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insert(Map<String, Object> row);

    @Update("UPDATE sys_notice SET title=#{title}, content=#{content}, updated_at=NOW() WHERE id=#{id}")
    int update(@Param("id") long id, @Param("title") String title, @Param("content") String content);

    @Delete("DELETE FROM sys_notice WHERE id=#{id}")
    int deleteById(@Param("id") long id);

    @Select("SELECT COUNT(*) FROM sys_notice WHERE title=#{title}")
    int countByTitle(@Param("title") String title);
}
