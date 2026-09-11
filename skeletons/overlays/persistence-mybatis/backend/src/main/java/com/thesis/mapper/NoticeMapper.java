package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface NoticeMapper {

    Map<String, Object> selectById(@Param("id") long id);

    int countAll();

    List<Map<String, Object>> selectAllOrderByIdDesc();

    List<Map<String, Object>> selectAllOrderByPinnedDesc();

    List<Map<String, Object>> selectApprovedOrderByIdDesc();

    List<Map<String, Object>> selectApprovedOrderByPinnedDesc();

    List<Map<String, Object>> selectBySubmitterOrderByIdDesc(@Param("submitter") String submitter);

    List<Map<String, Object>> selectBySubmitterOrderByPinnedDesc(@Param("submitter") String submitter);

    @Select("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE()"
            + " AND TABLE_NAME='sys_notice' AND COLUMN_NAME=#{col}")
    int countColumn(@Param("col") String col);

    @Insert(
            "INSERT INTO sys_notice (title,content,publisher_username,publisher_name) "
                    + "VALUES (#{title},#{content},#{publisherUsername},#{publisherName})")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insert(Map<String, Object> row);

    @Insert(
            "INSERT INTO sys_notice (title,content,publisher_username,publisher_name,audit_status) "
                    + "VALUES (#{title},#{content},#{publisherUsername},#{publisherName},#{auditStatus})")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insertWithAudit(Map<String, Object> row);

    @Insert(
            "INSERT INTO sys_notice (title,content,publisher_username,publisher_name,audit_status,submitter_username) "
                    + "VALUES (#{title},#{content},#{publisherUsername},#{publisherName},#{auditStatus},#{submitterUsername})")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insertWithAuditSubmitter(Map<String, Object> row);

    @Update("UPDATE sys_notice SET title=#{title}, content=#{content}, updated_at=NOW() WHERE id=#{id}")
    int update(@Param("id") long id, @Param("title") String title, @Param("content") String content);

    @Update("UPDATE sys_notice SET title=#{title}, content=#{content}, pinned=#{pinned}, updated_at=NOW() WHERE id=#{id}")
    int updateWithPinned(
            @Param("id") long id,
            @Param("title") String title,
            @Param("content") String content,
            @Param("pinned") int pinned);

    @Update("UPDATE sys_notice SET pinned=#{pinned}, updated_at=NOW() WHERE id=#{id}")
    int setPinned(@Param("id") long id, @Param("pinned") int pinned);

    @Update("UPDATE sys_notice SET audit_status='approved', updated_at=NOW() WHERE id=#{id}")
    int approve(@Param("id") long id);

    @Delete("DELETE FROM sys_notice WHERE id=#{id}")
    int deleteById(@Param("id") long id);

    @Select("SELECT COUNT(*) FROM sys_notice WHERE title=#{title}")
    int countByTitle(@Param("title") String title);
}
