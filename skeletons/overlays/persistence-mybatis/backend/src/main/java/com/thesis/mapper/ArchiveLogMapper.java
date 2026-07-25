package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.sql.Date;
import java.util.List;
import java.util.Map;

@Mapper
public interface ArchiveLogMapper {

    @Update("CREATE TABLE IF NOT EXISTS archive_log ("
            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
            + "item_id BIGINT NOT NULL,"
            + "username VARCHAR(64) NOT NULL,"
            + "log_date DATE NOT NULL,"
            + "log_type VARCHAR(32) NOT NULL DEFAULT 'checkin',"
            + "payload_json TEXT,"
            + "abnormal TINYINT DEFAULT 0,"
            + "remark VARCHAR(512) DEFAULT '',"
            + "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
            + "KEY idx_alog_item_date (item_id, log_date),"
            + "KEY idx_alog_date_type (log_date, log_type),"
            + "KEY idx_alog_user (username, id)"
            + ")")
    void ensureTable();

    @Insert("INSERT INTO archive_log (item_id,username,log_date,log_type,payload_json,abnormal,remark) "
            + "VALUES (#{itemId},#{username},#{logDate},#{logType},#{payloadJson},#{abnormal},#{remark})")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insert(Map<String, Object> row);

    Map<String, Object> selectById(@Param("id") long id);

    List<Map<String, Object>> selectByItemId(@Param("itemId") long itemId);

    List<Map<String, Object>> selectAdmin(
            @Param("itemId") Long itemId,
            @Param("logType") String logType,
            @Param("day") Date day,
            @Param("abnormalOnly") Boolean abnormalOnly);

    List<Map<String, Object>> selectMissingToday(
            @Param("itemTable") String itemTable,
            @Param("soft") boolean soft,
            @Param("day") Date day,
            @Param("logType") String logType);
}
