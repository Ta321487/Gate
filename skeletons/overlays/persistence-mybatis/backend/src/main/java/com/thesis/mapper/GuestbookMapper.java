package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface GuestbookMapper {

    @Select("SELECT COUNT(*) FROM information_schema.tables "
            + "WHERE table_schema=DATABASE() AND table_name='sys_guestbook'")
    Integer countTable();

    @Select("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE()"
            + " AND TABLE_NAME='sys_guestbook' AND COLUMN_NAME=#{col}")
    int countColumn(@Param("col") String col);

    Map<String, Object> selectById(@Param("id") long id);

    List<Map<String, Object>> selectPage(
            @Param("channel") String channel,
            @Param("onlyUsername") String onlyUsername);

    @Insert("INSERT INTO sys_guestbook (username,nickname,body) VALUES (#{username},#{nickname},#{body})")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insert(Map<String, Object> row);

    @Insert("INSERT INTO sys_guestbook (username,nickname,body,channel) VALUES (#{username},#{nickname},#{body},#{channel})")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insertWithChannel(Map<String, Object> row);

    @Update("UPDATE sys_guestbook SET reply=#{reply}, reply_username=#{replyUsername}, replied_at=NOW() WHERE id=#{id}")
    int reply(
            @Param("id") long id,
            @Param("reply") String reply,
            @Param("replyUsername") String replyUsername);

    @Delete("DELETE FROM sys_guestbook WHERE id=#{id}")
    int deleteById(@Param("id") long id);
}
