package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface LessonMapper {

    @Select("SELECT id, name, sessions, price_yuan, valid_days FROM lesson_pack WHERE enabled=1 ORDER BY id")
    List<Map<String, Object>> packsOn();

    @Select("SELECT id, name, sessions, price_yuan, valid_days, enabled FROM lesson_pack ORDER BY id")
    List<Map<String, Object>> packsAll();

    @Insert("INSERT INTO lesson_pack (name, sessions, price_yuan, valid_days, enabled) VALUES (#{name}, #{sessions}, #{price}, #{days}, #{enabled})")
    int insertPack(Map<String, Object> row);

    @Update("UPDATE lesson_pack SET name=#{name}, sessions=#{sessions}, price_yuan=#{price}, valid_days=#{days}, enabled=#{enabled} WHERE id=#{id}")
    int updatePack(Map<String, Object> row);

    @Select("SELECT id, name, sessions, price_yuan, valid_days FROM lesson_pack WHERE id=#{id} AND enabled=1")
    Map<String, Object> packOn(@Param("id") long id);

    @Select("SELECT id, total_sessions, remain_sessions, expire_at FROM lesson_wallet WHERE username=#{username} AND reservation_id IS NULL ORDER BY id LIMIT 1")
    Map<String, Object> account(@Param("username") String username);

    @Insert("INSERT INTO lesson_wallet (username, total_sessions, remain_sessions, expire_at) VALUES (#{username}, #{sessions}, #{sessions}, #{expireAt})")
    int insertAccount(Map<String, Object> row);

    @Update("UPDATE lesson_wallet SET total_sessions=total_sessions+#{sessions}, remain_sessions=remain_sessions+#{sessions}, expire_at=#{expireAt} WHERE username=#{username} AND reservation_id IS NULL")
    int addSessions(Map<String, Object> row);

    @Update("UPDATE lesson_wallet SET remain_sessions=remain_sessions-1 WHERE username=#{username} AND reservation_id IS NULL AND remain_sessions>0")
    int decRemain(@Param("username") String username);

    @Insert("INSERT INTO lesson_wallet (username, reservation_id, total_sessions, remain_sessions) VALUES (#{username}, #{resvId}, 0, 0)")
    int insertUse(@Param("username") String username, @Param("resvId") long resvId);

    @Select("SELECT username FROM lesson_wallet WHERE reservation_id=#{resvId}")
    List<String> useUsers(@Param("resvId") long resvId);

    @Delete("DELETE FROM lesson_wallet WHERE reservation_id=#{resvId}")
    int deleteUse(@Param("resvId") long resvId);

    @Update("UPDATE lesson_wallet SET remain_sessions=remain_sessions+1 WHERE username=#{username} AND reservation_id IS NULL")
    int incRemain(@Param("username") String username);

    @Select("SELECT id, username, reservation_id, created_at FROM lesson_wallet WHERE reservation_id IS NOT NULL ORDER BY id DESC")
    List<Map<String, Object>> uses();
}
