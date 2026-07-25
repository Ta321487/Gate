package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface MessageMapper {

    @Select("SELECT COUNT(*) FROM information_schema.tables "
            + "WHERE table_schema=DATABASE() AND table_name='sys_message'")
    Integer countMessageTable();

    @Insert("INSERT INTO sys_message (username,title,body,ref_type,ref_id) VALUES "
            + "(#{username},#{title},#{body},#{refType},#{refId})")
    int insert(
            @Param("username") String username,
            @Param("title") String title,
            @Param("body") String body,
            @Param("refType") String refType,
            @Param("refId") Long refId);

    @Select("SELECT username FROM sys_user WHERE role='admin' AND (enabled IS NULL OR enabled=1)")
    List<String> listAdminUsernames();

    @Select("SELECT username FROM sys_user WHERE role='admin'")
    List<String> listAdminUsernamesFallback();

    List<Map<String, Object>> selectByUsername(@Param("username") String username);

    @Select("SELECT COUNT(*) FROM sys_message WHERE username=#{username} AND read_at IS NULL")
    int countUnread(@Param("username") String username);

    @Select("SELECT COUNT(*) FROM sys_message WHERE id=#{id} AND username=#{username}")
    int countOwned(@Param("id") long id, @Param("username") String username);

    @Update("UPDATE sys_message SET read_at=#{readAt} WHERE id=#{id} AND username=#{username} AND read_at IS NULL")
    int markRead(
            @Param("readAt") java.sql.Timestamp readAt,
            @Param("id") long id,
            @Param("username") String username);

    @Update("UPDATE sys_message SET read_at=#{readAt} WHERE username=#{username} AND read_at IS NULL")
    int markAllRead(@Param("readAt") java.sql.Timestamp readAt, @Param("username") String username);
}
