package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface AddressMapper {

    @Select("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='user_address'")
    Integer countTable();

    List<Map<String, Object>> selectByUsername(@Param("username") String username);

    Map<String, Object> selectById(@Param("id") long id, @Param("username") String username);

    @Insert("INSERT INTO user_address (username,contact_name,phone,address_line,tag,is_default) "
            + "VALUES (#{username},#{contactName},#{phone},#{addressLine},#{tag},#{isDefault})")
    @Options(useGeneratedKeys = true, keyProperty = "id", keyColumn = "id")
    int insert(Map<String, Object> row);

    @Update("UPDATE user_address SET contact_name=#{contactName}, phone=#{phone}, address_line=#{addressLine}, "
            + "tag=#{tag}, is_default=#{isDefault} WHERE id=#{id} AND username=#{username}")
    int update(Map<String, Object> row);

    @Delete("DELETE FROM user_address WHERE id=#{id} AND username=#{username}")
    int delete(@Param("id") long id, @Param("username") String username);

    @Update("UPDATE user_address SET is_default=0 WHERE username=#{username}")
    int clearDefault(@Param("username") String username);
}
