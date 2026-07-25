package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface GuestbookMapper {

    @Select("SELECT COUNT(*) FROM information_schema.tables "
            + "WHERE table_schema=DATABASE() AND table_name='sys_guestbook'")
    Integer countTable();

    Map<String, Object> selectById(@Param("id") long id);

    List<Map<String, Object>> selectAllOrderByIdDesc();

    @Insert("INSERT INTO sys_guestbook (username,nickname,body) VALUES (#{username},#{nickname},#{body})")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insert(Map<String, Object> row);

    @Update("UPDATE sys_guestbook SET reply=#{reply}, reply_username=#{replyUsername}, replied_at=NOW() WHERE id=#{id}")
    int reply(
            @Param("id") long id,
            @Param("reply") String reply,
            @Param("replyUsername") String replyUsername);

    @Delete("DELETE FROM sys_guestbook WHERE id=#{id}")
    int deleteById(@Param("id") long id);
}
