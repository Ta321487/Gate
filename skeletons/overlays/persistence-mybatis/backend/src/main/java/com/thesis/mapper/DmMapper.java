package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface DmMapper {

    @Select("SELECT COUNT(*) FROM information_schema.tables "
            + "WHERE table_schema=DATABASE() AND table_name='sys_dm_message'")
    Integer countTable();

    Map<String, Object> selectById(@Param("id") long id);

    List<Map<String, Object>> selectPeers(@Param("me") String me, @Param("limit") int limit);

    List<Map<String, Object>> selectConversationPeers(@Param("me") String me);

    List<Map<String, Object>> selectMessages(
            @Param("me") String me, @Param("peer") String peer, @Param("sinceId") long sinceId);

    @Insert("INSERT INTO sys_dm_message (from_username, to_username, body) "
            + "VALUES (#{fromUsername}, #{toUsername}, #{body})")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insert(Map<String, Object> row);

    @Update("UPDATE sys_dm_message SET read_at=#{readAt} "
            + "WHERE to_username=#{me} AND from_username=#{peer} AND read_at IS NULL")
    int markRead(
            @Param("me") String me, @Param("peer") String peer, @Param("readAt") java.sql.Timestamp readAt);

    @Select("SELECT COUNT(*) FROM sys_dm_message WHERE to_username=#{me} AND read_at IS NULL")
    Integer unreadCount(@Param("me") String me);

    @Select("SELECT COUNT(*) FROM sys_dm_message WHERE to_username=#{me} AND from_username=#{peer} AND read_at IS NULL")
    Integer unreadWithPeer(@Param("me") String me, @Param("peer") String peer);

    @Select("SELECT COUNT(*) FROM sys_user WHERE username=#{username} AND (enabled IS NULL OR enabled=1)")
    Integer userEnabled(@Param("username") String username);

    @Select("SELECT nickname FROM sys_user WHERE username=#{username}")
    String nicknameOf(@Param("username") String username);
}
