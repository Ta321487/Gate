package com.thesis.mapper;

import org.apache.ibatis.annotations.*;
import java.util.List;
import java.util.Map;

@Mapper
public interface SurveyMapper {
    @Select("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='survey_question'")
    Integer countTable();

    @Select("SELECT * FROM survey_form WHERE status='available' AND stock>0 ORDER BY id DESC")
    List<Map<String, Object>> listOpenForms();

    @Select("SELECT * FROM survey_form WHERE id=#{id}")
    List<Map<String, Object>> getForm(@Param("id") long id);

    @Select("SELECT * FROM survey_question WHERE form_id=#{formId} ORDER BY sort_no, id")
    List<Map<String, Object>> listQuestions(@Param("formId") long formId);

    @Select("SELECT COUNT(*) FROM survey_question WHERE form_id=#{formId}")
    int countQuestions(@Param("formId") long formId);

    @Select("SELECT * FROM survey_question WHERE form_id=#{formId} ORDER BY sort_no, id LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageQuestions(@Param("formId") long formId, @Param("limit") int limit, @Param("offset") int offset);

    @Options(useGeneratedKeys = true, keyProperty = "id")
    @Insert("INSERT INTO survey_question (form_id,type,stem,options_json,sort_no,required) VALUES (#{formId},#{type},#{stem},#{optionsJson},#{sortNo},#{required})")
    int insertQuestion(Map<String, Object> row);

    @Select("SELECT * FROM survey_question WHERE id=#{id}")
    List<Map<String, Object>> getQuestion(@Param("id") long id);

    @Delete("DELETE FROM survey_question WHERE id=#{id}")
    int deleteQuestion(@Param("id") long id);

    @Select("SELECT COUNT(*) FROM survey_response WHERE form_id=#{formId} AND username=#{username}")
    Integer countUserResponse(@Param("formId") long formId, @Param("username") String username);

    @Options(useGeneratedKeys = true, keyProperty = "id")
    @Insert("INSERT INTO survey_response (form_id,username,submitted_at) VALUES (#{formId},#{username},NOW())")
    int insertResponse(Map<String, Object> row);

    @Insert("INSERT INTO survey_answer (response_id,question_id,answer_text) VALUES (#{responseId},#{questionId},#{answerText})")
    int insertAnswer(@Param("responseId") long responseId, @Param("questionId") long questionId, @Param("answerText") String answerText);

    @Select("SELECT * FROM survey_response WHERE id=#{id}")
    List<Map<String, Object>> getResponse(@Param("id") long id);

    @Select("SELECT COUNT(*) FROM survey_response WHERE username=#{username}")
    int countMine(@Param("username") String username);

    @Select("SELECT r.*, f.title AS form_title FROM survey_response r LEFT JOIN survey_form f ON f.id=r.form_id WHERE r.username=#{username} ORDER BY r.id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageMine(@Param("username") String username, @Param("limit") int limit, @Param("offset") int offset);

    @Select("SELECT COUNT(*) FROM survey_response WHERE form_id=#{formId}")
    int countResponses(@Param("formId") long formId);

    @Select("SELECT * FROM survey_response WHERE form_id=#{formId} ORDER BY id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageResponses(@Param("formId") long formId, @Param("limit") int limit, @Param("offset") int offset);

    @Select("SELECT COUNT(*) FROM survey_answer WHERE question_id=#{qid} AND answer_text<>''")
    Integer countFilled(@Param("qid") long qid);

    @Select("SELECT COUNT(*) FROM survey_answer WHERE question_id=#{qid} AND (answer_text=#{v} OR answer_text LIKE #{p1} OR answer_text LIKE #{p2} OR answer_text LIKE #{p3})")
    Integer countOpt(@Param("qid") long qid, @Param("v") String v, @Param("p1") String p1, @Param("p2") String p2, @Param("p3") String p3);
}
