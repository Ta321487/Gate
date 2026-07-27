package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface ESignMapper {

    @Select("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='e_sign_record'")
    Integer countTable();

    @Select("SELECT COUNT(*) FROM e_sign_record WHERE username=#{username}")
    Integer countMine(String username);

    @Select("SELECT id, username, title, ticket_id AS ticketId, sign_image_url AS signImageUrl, agreed, remark, signed_at AS signedAt "
            + "FROM e_sign_record WHERE username=#{username} ORDER BY id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageMine(
            @Param("username") String username, @Param("limit") int limit, @Param("offset") int offset);

    @Select("SELECT COUNT(*) FROM e_sign_record")
    Integer countAll();

    @Select("SELECT id, username, title, ticket_id AS ticketId, sign_image_url AS signImageUrl, agreed, remark, signed_at AS signedAt "
            + "FROM e_sign_record ORDER BY id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageAll(@Param("limit") int limit, @Param("offset") int offset);

    @Insert("INSERT INTO e_sign_record (username, title, ticket_id, sign_image_url, agreed, remark) "
            + "VALUES (#{username}, #{title}, #{ticketId}, #{signImageUrl}, 1, #{remark})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(Map<String, Object> row);

    @Select("SELECT id, username, title, ticket_id AS ticketId, sign_image_url AS signImageUrl, agreed, remark, signed_at AS signedAt "
            + "FROM e_sign_record WHERE id=#{id}")
    Map<String, Object> getById(long id);
}
