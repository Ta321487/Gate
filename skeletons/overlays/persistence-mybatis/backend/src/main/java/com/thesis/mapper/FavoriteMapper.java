package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.sql.Timestamp;
import java.util.List;
import java.util.Map;

@Mapper
public interface FavoriteMapper {

    @Update("CREATE TABLE IF NOT EXISTS user_favorite ("
            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
            + "username VARCHAR(64) NOT NULL,"
            + "item_id BIGINT NOT NULL,"
            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
            + "UNIQUE KEY uk_fav_user_item (username, item_id),"
            + "KEY idx_fav_user (username, id)"
            + ")")
    void ensureTable();

    @Update("CREATE TABLE IF NOT EXISTS user_post_like ("
            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
            + "username VARCHAR(64) NOT NULL,"
            + "item_id BIGINT NOT NULL,"
            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
            + "UNIQUE KEY uk_like_user_item (username, item_id),"
            + "KEY idx_like_item (item_id)"
            + ")")
    void ensureLikeTable();

    @Update("CREATE TABLE IF NOT EXISTS content_report ("
            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
            + "username VARCHAR(64) NOT NULL,"
            + "target_type VARCHAR(32) NOT NULL DEFAULT 'archive',"
            + "target_id BIGINT NOT NULL,"
            + "reason VARCHAR(512) NOT NULL,"
            + "status VARCHAR(32) NOT NULL DEFAULT 'pending',"
            + "handler VARCHAR(64) DEFAULT '',"
            + "handle_note VARCHAR(512) DEFAULT '',"
            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
            + "handled_at DATETIME NULL,"
            + "KEY idx_creport_status (status, id),"
            + "KEY idx_creport_target (target_type, target_id)"
            + ")")
    void ensureReportTable();

    @Update("ALTER TABLE `${itemTable}` ADD COLUMN `like_count` INT NOT NULL DEFAULT 0")
    void ensureLikeCountColumn(@Param("itemTable") String itemTable);

    @Select("SELECT COUNT(*) FROM user_favorite WHERE username=#{username} AND item_id=#{itemId}")
    int count(@Param("username") String username, @Param("itemId") long itemId);

    @Delete("DELETE FROM user_favorite WHERE username=#{username} AND item_id=#{itemId}")
    int delete(@Param("username") String username, @Param("itemId") long itemId);

    @Insert("INSERT INTO user_favorite (username,item_id,created_at) VALUES (#{username},#{itemId},#{createdAt})")
    int insert(
            @Param("username") String username,
            @Param("itemId") long itemId,
            @Param("createdAt") Timestamp createdAt);

    List<Map<String, Object>> selectByUsername(@Param("username") String username);

    @Select("SELECT item_id FROM user_favorite WHERE username=#{username}")
    List<Long> selectItemIds(@Param("username") String username);

    @Select("SELECT COUNT(*) FROM user_post_like WHERE username=#{username} AND item_id=#{itemId}")
    int countLike(@Param("username") String username, @Param("itemId") long itemId);

    @Delete("DELETE FROM user_post_like WHERE username=#{username} AND item_id=#{itemId}")
    int deleteLike(@Param("username") String username, @Param("itemId") long itemId);

    @Insert("INSERT INTO user_post_like (username,item_id,created_at) VALUES (#{username},#{itemId},#{createdAt})")
    int insertLike(
            @Param("username") String username,
            @Param("itemId") long itemId,
            @Param("createdAt") Timestamp createdAt);

    @Select("SELECT item_id FROM user_post_like WHERE username=#{username}")
    List<Long> selectLikedItemIds(@Param("username") String username);

    @Update("UPDATE `${itemTable}` SET like_count = GREATEST(0, COALESCE(like_count,0) + #{delta}) WHERE id=#{itemId}")
    int bumpLikeCount(
            @Param("itemTable") String itemTable,
            @Param("itemId") long itemId,
            @Param("delta") int delta);

    @Select("SELECT COUNT(*) FROM content_report "
            + "WHERE username=#{username} AND target_type=#{targetType} AND target_id=#{targetId} AND status='pending'")
    int countPendingDup(
            @Param("username") String username,
            @Param("targetType") String targetType,
            @Param("targetId") long targetId);

    @Insert("INSERT INTO content_report (username,target_type,target_id,reason,status,created_at) "
            + "VALUES (#{username},#{targetType},#{targetId},#{reason},#{status},#{createdAt})")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insertReport(Map<String, Object> row);

    @Select({"<script>",
            "SELECT COUNT(*) FROM content_report",
            "<where>",
            "<if test='status != null and status != \"\"'>",
            "AND status=#{status}",
            "</if>",
            "</where>",
            "</script>"})
    int countReports(@Param("status") String status);

    @Select({"<script>",
            "SELECT * FROM content_report",
            "<where>",
            "<if test='status != null and status != \"\"'>",
            "AND status=#{status}",
            "</if>",
            "</where>",
            "ORDER BY id DESC",
            "</script>"})
    List<Map<String, Object>> selectReports(@Param("status") String status);

    @Select("SELECT * FROM content_report WHERE id=#{id}")
    Map<String, Object> selectReportById(@Param("id") long id);

    @Update("UPDATE content_report SET status=#{status}, handler=#{handler}, "
            + "handle_note=#{handleNote}, handled_at=NOW() WHERE id=#{id}")
    int updateResolve(
            @Param("id") long id,
            @Param("status") String status,
            @Param("handler") String handler,
            @Param("handleNote") String handleNote);
}
