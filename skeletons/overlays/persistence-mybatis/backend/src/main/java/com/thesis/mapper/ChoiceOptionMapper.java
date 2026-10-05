package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;

@Mapper
public interface ChoiceOptionMapper {

    @Delete("DELETE FROM exam_option WHERE question_id=#{qid}")
    int deleteExamOptions(@Param("qid") long qid);

    @Insert("INSERT INTO exam_option (question_id,sort_no,label,content) VALUES (#{qid},#{sortNo},#{label},#{content})")
    int insertExamOption(
            @Param("qid") long qid,
            @Param("sortNo") int sortNo,
            @Param("label") String label,
            @Param("content") String content);

    @Select("SELECT content FROM exam_option WHERE question_id=#{qid} ORDER BY sort_no")
    List<String> listExamOptionContents(@Param("qid") long qid);

    @Delete("DELETE FROM survey_option WHERE question_id=#{qid}")
    int deleteSurveyOptions(@Param("qid") long qid);

    @Insert("INSERT INTO survey_option (question_id,sort_no,label,content) VALUES (#{qid},#{sortNo},#{label},#{content})")
    int insertSurveyOption(
            @Param("qid") long qid,
            @Param("sortNo") int sortNo,
            @Param("label") String label,
            @Param("content") String content);

    @Select("SELECT content FROM survey_option WHERE question_id=#{qid} ORDER BY sort_no")
    List<String> listSurveyOptionContents(@Param("qid") long qid);
}
