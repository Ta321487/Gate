package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.sql.Timestamp;
import java.util.List;
import java.util.Map;

@Mapper
public interface BrowseHistoryMapper {

    @Update("CREATE TABLE IF NOT EXISTS user_browse_history ("
            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
            + "username VARCHAR(64) NOT NULL,"
            + "item_id BIGINT NOT NULL,"
            + "viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
            + "UNIQUE KEY uk_browse_user_item (username, item_id),"
            + "KEY idx_browse_user_time (username, viewed_at)"
            + ")")
    void ensureTable();

    @Select("SELECT COUNT(*) FROM user_browse_history WHERE username=#{username} AND item_id=#{itemId}")
    int count(@Param("username") String username, @Param("itemId") long itemId);

    @Update("UPDATE user_browse_history SET viewed_at=#{viewedAt} WHERE username=#{username} AND item_id=#{itemId}")
    int touch(
            @Param("viewedAt") Timestamp viewedAt,
            @Param("username") String username,
            @Param("itemId") long itemId);

    @Insert("INSERT INTO user_browse_history (username,item_id,viewed_at) VALUES (#{username},#{itemId},#{viewedAt})")
    int insert(
            @Param("username") String username,
            @Param("itemId") long itemId,
            @Param("viewedAt") Timestamp viewedAt);

    @Select("SELECT id FROM user_browse_history WHERE username=#{username} ORDER BY viewed_at DESC")
    List<Long> selectIdsByUsername(@Param("username") String username);

    @Delete("DELETE FROM user_browse_history WHERE id=#{id}")
    int deleteById(@Param("id") long id);

    List<Map<String, Object>> selectByUsername(@Param("username") String username);

    @Select("SELECT item_id FROM user_browse_history WHERE username=#{username} ORDER BY viewed_at DESC")
    List<Long> selectItemIds(@Param("username") String username);

    @Delete("DELETE FROM user_browse_history WHERE username=#{username}")
    int clear(@Param("username") String username);
}
