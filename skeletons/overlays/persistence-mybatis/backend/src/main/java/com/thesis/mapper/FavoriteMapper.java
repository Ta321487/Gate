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
}
