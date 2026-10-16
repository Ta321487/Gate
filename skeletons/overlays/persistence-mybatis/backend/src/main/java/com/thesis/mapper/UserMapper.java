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

    @Update("UPDATE sys_user SET failed_login_count=#{count}, lock_until=#{lockUntil} WHERE username=#{username}")
    int updateLoginLock(@Param("username") String username, @Param("count") int count, @Param("lockUntil") String lockUntil);

    @Update("UPDATE sys_user SET failed_login_count=#{count} WHERE username=#{username}")
    int updateFailedLoginCount(@Param("username") String username, @Param("count") int count);

    @Update("UPDATE sys_user SET failed_login_count=0, lock_until=NULL WHERE username=#{username}")
    int clearLoginFailures(@Param("username") String username);

    @Update("UPDATE sys_user SET password=#{password}, must_change_password=0, password_changed_at=#{changedAt}, "
            + "failed_login_count=0, lock_until=NULL WHERE username=#{username}")
    int updatePasswordChanged(@Param("username") String username, @Param("password") String password,
                              @Param("changedAt") String changedAt);

    @Update("UPDATE sys_user SET password=#{password}, must_change_password=1, password_changed_at=NULL, "
            + "failed_login_count=0, lock_until=NULL WHERE username=#{username}")
    int updatePasswordForceChange(@Param("username") String username, @Param("password") String password);

    @Update("UPDATE sys_user SET security_question=#{question}, security_answer_hash=#{answerHash} WHERE username=#{username}")
    int updateSecurityQuestion(@Param("username") String username, @Param("question") String question,
                               @Param("answerHash") String answerHash);

    @Update("UPDATE sys_user SET post_mute_until=#{until} WHERE username=#{username}")
    int updatePostMuteUntil(@Param("username") String username, @Param("until") String until);

    @Insert("INSERT INTO sys_user (username,password,role,nickname,phone,avatar_url,profile_json,super_admin,profile_editable,enabled) "
            + "VALUES (#{username},#{password},#{role},#{nickname},#{phone},#{avatarUrl},#{profileJson},0,1,1)")
    int insertWithProfile(Map<String, Object> row);

    @Insert("INSERT INTO sys_user (username,password,role,nickname,phone,avatar_url,super_admin,profile_editable,enabled) "
            + "VALUES (#{username},#{password},#{role},#{nickname},#{phone},#{avatarUrl},0,1,1)")
    int insertPlain(Map<String, Object> row);

    /** 多店商家入驻：admin + shop_merchant，默认停用待审 */
    @Insert("INSERT INTO sys_user (username,password,role,nickname,phone,avatar_url,profile_json,"
            + "super_admin,profile_editable,enabled,staff_post,staff_kind) "
            + "VALUES (#{username},#{password},'admin',#{nickname},#{phone},#{avatarUrl},#{profileJson},"
            + "0,1,0,'shop_merchant','clerk')")
    int insertMerchantWithProfile(Map<String, Object> row);

    @Insert("INSERT INTO sys_user (username,password,role,nickname,phone,avatar_url,"
            + "super_admin,profile_editable,enabled,staff_post,staff_kind) "
            + "VALUES (#{username},#{password},'admin',#{nickname},#{phone},#{avatarUrl},"
            + "0,1,0,'shop_merchant','clerk')")
    int insertMerchantPlain(Map<String, Object> row);

    @Update("UPDATE sys_user SET nickname=#{nickname}, phone=#{phone}, enabled=#{enabled}, profile_json=#{profileJson} WHERE username=#{username}")
    int updateAdminWithProfile(Map<String, Object> row);

    @Update("UPDATE sys_user SET nickname=#{nickname}, phone=#{phone}, enabled=#{enabled} WHERE username=#{username}")
    int updateAdminPlain(Map<String, Object> row);

    @Update("UPDATE sys_user SET admin_tags=#{adminTags} WHERE username=#{username}")
    int updateAdminTags(@Param("username") String username, @Param("adminTags") String adminTags);

    @Update("UPDATE sys_user SET org_id=#{orgId} WHERE username=#{username}")
    int updateOrgId(@Param("username") String username, @Param("orgId") Long orgId);

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
