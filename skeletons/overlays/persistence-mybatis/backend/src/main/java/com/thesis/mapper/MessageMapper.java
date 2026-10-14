package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface MessageMapper {

    @Select("SELECT COUNT(*) FROM information_schema.tables "
            + "WHERE table_schema=DATABASE() AND table_name='sys_message'")
    Integer countMessageTable();

    @Select("SELECT COUNT(*) FROM information_schema.columns "
            + "WHERE table_schema=DATABASE() AND table_name='sys_message' AND column_name='deleted_at'")
    Integer countDeletedAtColumn();

    @Update("ALTER TABLE sys_message ADD COLUMN deleted_at DATETIME NULL")
    int addDeletedAtColumn();

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

    List<Map<String, Object>> selectByUsername(
            @Param("username") String username,
            @Param("kind") String kind,
            @Param("hasDeletedAt") boolean hasDeletedAt);

    int countUnread(@Param("username") String username, @Param("hasDeletedAt") boolean hasDeletedAt);

    @Select("SELECT COUNT(*) FROM sys_message WHERE username=#{username} AND ref_type=#{refType} AND ref_id=#{refId}")
    int countByRef(
            @Param("username") String username,
            @Param("refType") String refType,
            @Param("refId") Long refId);

    int countOwned(
            @Param("id") long id,
            @Param("username") String username,
            @Param("hasDeletedAt") boolean hasDeletedAt);

    int markRead(
            @Param("readAt") java.sql.Timestamp readAt,
            @Param("id") long id,
            @Param("username") String username,
            @Param("hasDeletedAt") boolean hasDeletedAt);

    int markAllRead(
            @Param("readAt") java.sql.Timestamp readAt,
            @Param("username") String username,
            @Param("hasDeletedAt") boolean hasDeletedAt);

    @Update("UPDATE sys_message SET deleted_at=#{deletedAt} WHERE id=#{id} AND username=#{username} AND deleted_at IS NULL")
    int softDelete(
            @Param("deletedAt") java.sql.Timestamp deletedAt,
            @Param("id") long id,
            @Param("username") String username);
}
