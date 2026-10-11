package com.thesis.mapper;

import org.apache.ibatis.annotations.*;
import java.util.List;
import java.util.Map;

@Mapper
public interface SurveyMapper {
    @Select("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='survey_question'")
    Integer countTable();

    @Update("CREATE TABLE IF NOT EXISTS survey_draft ("
            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
            + "form_id BIGINT NOT NULL,"
            + "username VARCHAR(64) NOT NULL,"
            + "answers_json TEXT,"
            + "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"
            + "UNIQUE KEY uk_survey_draft (form_id, username))")
    void ensureDraftTable();

    @Update("CREATE TABLE IF NOT EXISTS survey_audience ("
            + "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
            + "form_id BIGINT NOT NULL,"
            + "username VARCHAR(64) NOT NULL,"
            + "UNIQUE KEY uk_survey_audience (form_id, username))")
    void ensureAudienceTable();

    @Select("SELECT * FROM survey_form WHERE status='available' AND stock>0 ORDER BY id DESC")
    List<Map<String, Object>> listOpenForms();

    @Select("SELECT * FROM survey_form ORDER BY id DESC")
    List<Map<String, Object>> listAdminForms();

    @Select("SELECT * FROM survey_form WHERE id=#{id}")
    List<Map<String, Object>> getForm(@Param("id") long id);

    @Select("SELECT * FROM survey_form WHERE open_at IS NOT NULL OR close_at IS NOT NULL")
    List<Map<String, Object>> listTimedForms();

    @Select("SELECT * FROM survey_form WHERE close_at IS NOT NULL AND remind_before_hours>0 AND close_reminded_at IS NULL")
    List<Map<String, Object>> listRemindForms();

    @Update("UPDATE survey_form SET status=#{status} WHERE id=#{id}")
    int updateStatus(@Param("id") long id, @Param("status") String status);

    @Update("UPDATE survey_form SET close_reminded_at=NOW() WHERE id=#{id}")
    int markCloseReminded(@Param("id") long id);

    @Update("UPDATE survey_form SET open_at=#{openAt}, close_at=#{closeAt}, anonymous=#{anonymous}, "
            + "once_only=#{onceOnly}, target_org=#{targetOrg}, remind_before_hours=#{remindBeforeHours}, "
            + "target_count=#{targetCount}, status=#{status} WHERE id=#{id}")
    int updateFormSettings(Map<String, Object> row);

    @Select("SELECT * FROM survey_question WHERE form_id=#{formId} ORDER BY sort_no, id")
    List<Map<String, Object>> listQuestions(@Param("formId") long formId);

    @Select("SELECT COUNT(*) FROM survey_question WHERE form_id=#{formId}")
    int countQuestions(@Param("formId") long formId);

    @Select("SELECT * FROM survey_question WHERE form_id=#{formId} ORDER BY sort_no, id LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageQuestions(@Param("formId") long formId, @Param("limit") int limit, @Param("offset") int offset);

    @Options(useGeneratedKeys = true, keyProperty = "id")
    @Insert("INSERT INTO survey_question (form_id,type,stem,sort_no,required,"
            + "skip_when_label,skip_to_sort,show_when_qid,show_when_label,matrix_rows) "
            + "VALUES (#{formId},#{type},#{stem},#{sortNo},#{required},"
            + "#{skipWhenLabel},#{skipToSort},#{showWhenQid},#{showWhenLabel},#{matrixRows})")
    int insertQuestion(Map<String, Object> row);

    @Select("SELECT * FROM survey_question WHERE id=#{id}")
    List<Map<String, Object>> getQuestion(@Param("id") long id);

    @Delete("DELETE FROM survey_question WHERE id=#{id}")
    int deleteQuestion(@Param("id") long id);

    @Select("SELECT COUNT(*) FROM survey_response WHERE form_id=#{formId} AND username=#{username}")
    Integer countUserResponse(@Param("formId") long formId, @Param("username") String username);

    @Select("SELECT COUNT(*) FROM survey_response WHERE form_id=#{formId} AND (username=#{username} OR username LIKE #{like})")
    Integer countUserResponseAny(@Param("formId") long formId, @Param("username") String username, @Param("like") String like);

    @Options(useGeneratedKeys = true, keyProperty = "id")
    @Insert("INSERT INTO survey_response (form_id,username,submitted_at) VALUES (#{formId},#{username},NOW())")
    int insertResponse(Map<String, Object> row);

    @Insert("INSERT INTO survey_answer (response_id,question_id,answer_text) VALUES (#{responseId},#{questionId},#{answerText})")
    int insertAnswer(@Param("responseId") long responseId, @Param("questionId") long questionId, @Param("answerText") String answerText);

    @Select("SELECT * FROM survey_response WHERE id=#{id}")
    List<Map<String, Object>> getResponse(@Param("id") long id);

    @Select("SELECT COUNT(*) FROM survey_response WHERE username=#{username} OR username LIKE #{like}")
    int countMine(@Param("username") String username, @Param("like") String like);

    @Select("SELECT r.*, f.title AS form_title FROM survey_response r LEFT JOIN survey_form f ON f.id=r.form_id "
            + "WHERE r.username=#{username} OR r.username LIKE #{like} ORDER BY r.id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageMine(@Param("username") String username, @Param("like") String like,
                                       @Param("limit") int limit, @Param("offset") int offset);

    @Select("SELECT COUNT(*) FROM survey_response WHERE form_id=#{formId}")
    int countResponses(@Param("formId") long formId);

    @Select("SELECT * FROM survey_response WHERE form_id=#{formId} ORDER BY id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageResponses(@Param("formId") long formId, @Param("limit") int limit, @Param("offset") int offset);

    @Select("SELECT COUNT(*) FROM survey_answer WHERE question_id=#{qid} AND answer_text<>''")
    Integer countFilled(@Param("qid") long qid);

    @Select("SELECT COUNT(*) FROM survey_answer WHERE question_id=#{qid} AND (answer_text=#{v} OR answer_text LIKE #{p1} OR answer_text LIKE #{p2} OR answer_text LIKE #{p3})")
    Integer countOpt(@Param("qid") long qid, @Param("v") String v, @Param("p1") String p1, @Param("p2") String p2, @Param("p3") String p3);

    @Select("SELECT answer_text FROM survey_answer WHERE question_id=#{qid} AND answer_text<>''")
    List<String> listAnswerTexts(@Param("qid") long qid);

    @Select("SELECT COUNT(*) FROM survey_audience WHERE form_id=#{formId}")
    Integer countAudience(@Param("formId") long formId);

    @Select("SELECT COUNT(*) FROM survey_audience WHERE form_id=#{formId} AND username=#{username}")
    Integer countAudienceUser(@Param("formId") long formId, @Param("username") String username);

    @Select("SELECT profile_json FROM sys_user WHERE username=#{username}")
    List<String> getProfileJson(@Param("username") String username);

    @Select("SELECT username FROM sys_user WHERE enabled=1 AND role='user'")
    List<String> listEnabledUsers();

    @Select("SELECT username FROM sys_user WHERE enabled=1 AND role='user' AND profile_json LIKE #{pattern}")
    List<String> listUsersByOrg(@Param("pattern") String pattern);

    @Insert("INSERT INTO survey_draft (form_id, username, answers_json) VALUES (#{formId},#{username},#{answersJson}) "
            + "ON DUPLICATE KEY UPDATE answers_json=VALUES(answers_json), updated_at=NOW()")
    int upsertDraft(@Param("formId") long formId, @Param("username") String username, @Param("answersJson") String answersJson);

    @Select("SELECT * FROM survey_draft WHERE form_id=#{formId} AND username=#{username}")
    List<Map<String, Object>> getDraft(@Param("formId") long formId, @Param("username") String username);

    @Delete("DELETE FROM survey_draft WHERE form_id=#{formId} AND username=#{username}")
    int deleteDraft(@Param("formId") long formId, @Param("username") String username);

    @Select("SELECT username FROM survey_draft WHERE form_id=#{formId}")
    List<String> listDraftUsers(@Param("formId") long formId);
}
