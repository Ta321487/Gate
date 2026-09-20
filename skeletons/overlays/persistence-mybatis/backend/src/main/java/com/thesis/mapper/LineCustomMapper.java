package com.thesis.mapper;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;
import java.util.Map;

@Mapper
public interface LineCustomMapper {

    @Select("SELECT id, label, enabled, sort_no AS sortNo FROM line_spec_option WHERE enabled=1 ORDER BY sort_no, id")
    List<Map<String, Object>> enabled();

    @Select("SELECT id, label, enabled, sort_no AS sortNo FROM line_spec_option ORDER BY sort_no, id")
    List<Map<String, Object>> all();

    @Select("SELECT COUNT(*) FROM line_spec_option WHERE enabled=1 AND label=#{label}")
    Integer countLabel(@Param("label") String label);

    @Update("UPDATE line_spec_option SET label=#{label}, enabled=#{enabled}, sort_no=#{sortNo} WHERE id=#{id}")
    int update(
            @Param("id") long id,
            @Param("label") String label,
            @Param("enabled") int enabled,
            @Param("sortNo") int sortNo);

    @Insert("INSERT INTO line_spec_option (label, enabled, sort_no) VALUES (#{label},#{enabled},#{sortNo})")
    int insert(
            @Param("label") String label,
            @Param("enabled") int enabled,
            @Param("sortNo") int sortNo);
}
