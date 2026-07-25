package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface UserMapper {

    Map<String, Object> selectByUsername(@Param("username") String username);

    List<Map<String, Object>> selectAll();

    @Select("SELECT COUNT(*) FROM sys_user WHERE role=#{role}")
    long countByRole(@Param("role") String role);

    @Update("UPDATE sys_user SET password=#{password} WHERE username=#{username}")
    int updatePassword(@Param("username") String username, @Param("password") String password);

    @Insert("INSERT INTO sys_user (username,password,role,nickname,phone,avatar_url,profile_json,super_admin,profile_editable,enabled) "
            + "VALUES (#{username},#{password},#{role},#{nickname},#{phone},#{avatarUrl},#{profileJson},0,1,1)")
    int insertWithProfile(Map<String, Object> row);

    @Insert("INSERT INTO sys_user (username,password,role,nickname,phone,avatar_url,super_admin,profile_editable,enabled) "
            + "VALUES (#{username},#{password},#{role},#{nickname},#{phone},#{avatarUrl},0,1,1)")
    int insertPlain(Map<String, Object> row);

    @Update("UPDATE sys_user SET nickname=#{nickname}, phone=#{phone}, enabled=#{enabled}, profile_json=#{profileJson} WHERE username=#{username}")
    int updateAdminWithProfile(Map<String, Object> row);

    @Update("UPDATE sys_user SET nickname=#{nickname}, phone=#{phone}, enabled=#{enabled} WHERE username=#{username}")
    int updateAdminPlain(Map<String, Object> row);

    @Update("UPDATE sys_user SET role=#{role}, super_admin=0, staff_post=#{staffPost}, staff_kind=#{staffKind} WHERE username=#{username}")
    int appointStaff(Map<String, Object> row);

    @Update("UPDATE sys_user SET role=#{role}, super_admin=0, staff_post='', staff_kind='' WHERE username=#{username}")
    int revokeStaffWithCols(@Param("username") String username, @Param("role") String role);

    @Update("UPDATE sys_user SET role=#{role}, super_admin=0 WHERE username=#{username}")
    int revokeStaffPlain(@Param("username") String username, @Param("role") String role);

    int countStaff(
            @Param("staffPost") String staffPost,
            @Param("enabledOnly") boolean enabledOnly,
            @Param("hasStaffCols") boolean hasStaffCols);

    @Update("UPDATE sys_user SET nickname=#{nickname}, phone=#{phone}, avatar_url=#{avatarUrl}, password=#{password}, profile_json=#{profileJson} WHERE username=#{username}")
    int saveProfileWithJson(Map<String, Object> row);

    @Update("UPDATE sys_user SET nickname=#{nickname}, phone=#{phone}, avatar_url=#{avatarUrl}, password=#{password} WHERE username=#{username}")
    int saveProfilePlain(Map<String, Object> row);
}
