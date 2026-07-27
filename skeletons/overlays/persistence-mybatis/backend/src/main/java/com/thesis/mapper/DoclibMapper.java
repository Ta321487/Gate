package com.thesis.mapper;

import org.apache.ibatis.annotations.*;
import java.util.List;
import java.util.Map;

@Mapper
public interface DoclibMapper {
    @Select("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='download_log'")
    Integer countTable();

    @Select("SELECT id, title, author, isbn, category_id AS categoryId, stock, status, cover_url AS coverUrl, file_url AS fileUrl, access_level AS accessLevel, created_at AS createdAt FROM doc_item WHERE status='available' AND access_level IN ('public','login') ORDER BY id DESC")
    List<Map<String, Object>> listOpenUser();

    @Select("SELECT id, title, author, isbn, category_id AS categoryId, stock, status, cover_url AS coverUrl, file_url AS fileUrl, access_level AS accessLevel, created_at AS createdAt FROM doc_item WHERE status='available' ORDER BY id DESC")
    List<Map<String, Object>> listOpenAdmin();

    @Select("SELECT id, title, author, isbn, category_id AS categoryId, stock, status, cover_url AS coverUrl, file_url AS fileUrl, access_level AS accessLevel, created_at AS createdAt FROM doc_item WHERE id=#{id}")
    Map<String, Object> getItem(long id);

    @Insert("INSERT INTO download_log(item_id, username) VALUES(#{itemId}, #{username})")
    int insertLog(@Param("itemId") long itemId, @Param("username") String username);

    @Select("SELECT COUNT(*) FROM download_log WHERE username=#{username}")
    Integer countMine(String username);

    @Select("SELECT l.id, l.item_id AS itemId, l.downloaded_at AS downloadedAt, d.title FROM download_log l JOIN doc_item d ON d.id=l.item_id WHERE l.username=#{username} ORDER BY l.id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageMine(@Param("username") String username, @Param("limit") int limit, @Param("offset") int offset);

    @Select("SELECT COUNT(*) FROM download_log")
    Integer countLogs();

    @Select("SELECT COUNT(*) FROM download_log WHERE item_id=#{itemId}")
    Integer countLogsByItem(long itemId);

    @Select("SELECT l.id, l.item_id AS itemId, l.username, l.downloaded_at AS downloadedAt, d.title FROM download_log l JOIN doc_item d ON d.id=l.item_id ORDER BY l.id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageLogs(@Param("limit") int limit, @Param("offset") int offset);

    @Select("SELECT l.id, l.item_id AS itemId, l.username, l.downloaded_at AS downloadedAt, d.title FROM download_log l JOIN doc_item d ON d.id=l.item_id WHERE l.item_id=#{itemId} ORDER BY l.id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageLogsByItem(@Param("itemId") long itemId, @Param("limit") int limit, @Param("offset") int offset);

    @Update("UPDATE doc_item SET file_url=#{fileUrl}, access_level=#{accessLevel} WHERE id=#{id}")
    int updateMeta(@Param("id") long id, @Param("fileUrl") String fileUrl, @Param("accessLevel") String accessLevel);
}
