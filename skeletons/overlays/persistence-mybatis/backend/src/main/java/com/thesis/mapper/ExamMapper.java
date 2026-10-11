package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface ExamMapper {

    @Select("SELECT COUNT(*) FROM information_schema.tables "
            + "WHERE table_schema=DATABASE() AND table_name='exam_question'")
    Integer countExamQuestionTable();

    @Select("SELECT COUNT(*) FROM information_schema.tables "
            + "WHERE table_schema=DATABASE() AND table_name='exam_wrongbook'")
    Integer countWrongbookTable();

    List<Map<String, Object>> selectQuestion(@Param("id") long id);

    int countQuestions(@Param("subjectId") Long subjectId);

    List<Map<String, Object>> pageQuestions(
            @Param("subjectId") Long subjectId,
            @Param("limit") int limit,
            @Param("offset") int offset);

    @Options(useGeneratedKeys = true, keyProperty = "id")
    @Insert("INSERT INTO exam_question (subject_id,type,stem,answer_key,score,explain_text) "
            + "VALUES (#{subjectId},#{type},#{stem},#{answerKey},#{score},#{explainText})")
    int insertQuestion(Map<String, Object> row);

    @Options(useGeneratedKeys = true, keyProperty = "id")
    @Insert("INSERT INTO exam_question (subject_id,type,stem,answer_key,score,explain_text,mark_rubric) "
            + "VALUES (#{subjectId},#{type},#{stem},#{answerKey},#{score},#{explainText},#{markRubric})")
    int insertQuestionWithRubric(Map<String, Object> row);

    int updateQuestion(Map<String, Object> row);

    @Select("SELECT COUNT(*) FROM exam_paper_question WHERE question_id=#{id}")
    Integer countPaperRefs(@Param("id") long id);

    @Delete("DELETE FROM exam_question WHERE id=#{id}")
    int deleteQuestion(@Param("id") long id);

    List<Map<String, Object>> selectPaper(@Param("id") long id);

    @Select("SELECT COUNT(*) FROM exam_paper")
    Integer countPapers();

    @Select("SELECT * FROM exam_paper ORDER BY id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pagePapers(@Param("limit") int limit, @Param("offset") int offset);

    @Select("SELECT * FROM exam_paper WHERE status='published' ORDER BY id DESC")
    List<Map<String, Object>> listPublishedPapers();

    @Options(useGeneratedKeys = true, keyProperty = "id")
    @Insert("INSERT INTO exam_paper (title,duration_min,status,subject_id,max_attempts,pass_score,"
            + "shuffle_questions,shuffle_options,explain_after_score,partial_multi,lock_after_submit,"
            + "open_at,late_enter_min,entry_code,difficulty) "
            + "VALUES (#{title},#{durationMin},#{status},#{subjectId},#{maxAttempts},#{passScore},"
            + "#{shuffleQuestions},#{shuffleOptions},#{explainAfterScore},#{partialMulti},#{lockAfterSubmit},"
            + "#{openAt},#{lateEnterMin},#{entryCode},#{difficulty})")
    int insertPaper(Map<String, Object> row);

    @Select("SELECT COUNT(*) FROM information_schema.columns "
            + "WHERE table_schema=DATABASE() AND table_name='exam_paper' AND column_name='entry_code'")
    Integer countEntryCodeCol();

    @Select("SELECT COUNT(*) FROM information_schema.columns "
            + "WHERE table_schema=DATABASE() AND table_name='exam_question' AND column_name='mark_rubric'")
    Integer countMarkRubricCol();

    @Select("SELECT COUNT(*) FROM information_schema.columns "
            + "WHERE table_schema=DATABASE() AND table_name='exam_attempt' AND column_name='blur_count'")
    Integer countBlurCol();

    @Select("SELECT COUNT(*) FROM exam_attempt WHERE username=#{username} AND paper_id=#{paperId} "
            + "AND mode='exam' AND status IN ('submitted','reviewing')")
    Integer countLockedExam(
            @Param("username") String username, @Param("paperId") long paperId);

    @Update("UPDATE exam_attempt SET blur_count=IFNULL(blur_count,0)+1 WHERE id=#{id}")
    int bumpBlur(@Param("id") long id);

    @Select("SELECT label, content FROM exam_option WHERE question_id=#{questionId} ORDER BY sort_no")
    List<Map<String, Object>> listOptionRows(@Param("questionId") long questionId);

    int updatePaper(Map<String, Object> row);

    @Delete("DELETE FROM exam_paper_question WHERE paper_id=#{id}")
    int deletePaperQuestions(@Param("id") long id);

    @Delete("DELETE FROM exam_paper WHERE id=#{id}")
    int deletePaper(@Param("id") long id);

    List<Map<String, Object>> listPaperQuestions(@Param("paperId") long paperId);

    @Insert("INSERT INTO exam_paper_question (paper_id,question_id,sort_no) VALUES (#{paperId},#{questionId},#{sortNo})")
    int insertPaperQuestion(
            @Param("paperId") long paperId,
            @Param("questionId") long questionId,
            @Param("sortNo") int sortNo);

    @Select("SELECT COALESCE(MAX(sort_no),0) FROM exam_paper_question WHERE paper_id=#{paperId}")
    Integer maxPaperQuestionSort(@Param("paperId") long paperId);

    List<Long> listRandomQuestionIds(
            @Param("paperId") long paperId,
            @Param("type") String type,
            @Param("count") int count);

    List<Map<String, Object>> selectAttempt(@Param("id") long id);

    @Select("SELECT * FROM exam_attempt WHERE username=#{username} AND paper_id=#{paperId} AND status='in_progress' LIMIT 1")
    List<Map<String, Object>> findInProgress(
            @Param("username") String username, @Param("paperId") long paperId);

    @Select("SELECT COUNT(*) FROM exam_attempt WHERE username=#{username} AND paper_id=#{paperId} "
            + "AND mode='exam' AND status='submitted'")
    Integer countSubmittedExam(
            @Param("username") String username, @Param("paperId") long paperId);

    @Options(useGeneratedKeys = true, keyProperty = "id")
    @Insert("INSERT INTO exam_attempt (paper_id,username,mode,status,score,total_score) "
            + "VALUES (#{paperId},#{username},#{mode},'in_progress',0,0)")
    int insertAttempt(Map<String, Object> row);

    List<Map<String, Object>> listAttemptQuestions(@Param("attemptId") long attemptId);

    @Delete("DELETE FROM exam_answer WHERE attempt_id=#{attemptId}")
    int deleteAnswers(@Param("attemptId") long attemptId);

    @Insert("INSERT INTO exam_answer (attempt_id,question_id,answer_text,is_correct,score) "
            + "VALUES (#{attemptId},#{questionId},#{answerText},#{isCorrect},#{score})")
    int insertAnswer(
            @Param("attemptId") long attemptId,
            @Param("questionId") long questionId,
            @Param("answerText") String answerText,
            @Param("isCorrect") int isCorrect,
            @Param("score") int score);

    @Update("UPDATE exam_attempt SET status=#{status}, score=#{score}, total_score=#{totalScore}, "
            + "submitted_at=NOW(), timed_out=#{timedOut} WHERE id=#{id}")
    int submitAttempt(
            @Param("id") long id,
            @Param("status") String status,
            @Param("score") int score,
            @Param("totalScore") int totalScore,
            @Param("timedOut") int timedOut);

    @Select("SELECT a.id, a.paper_id AS paperId, a.username, a.submitted_at AS submittedAt, p.title AS paperTitle "
            + "FROM exam_attempt a JOIN exam_paper p ON p.id=a.paper_id "
            + "WHERE a.status='reviewing' ORDER BY a.id ASC")
    List<Map<String, Object>> listReviewing();

    @Select("SELECT q.id AS questionId, q.type, q.stem, q.answer_key AS answerKey, q.score AS maxScore, "
            + "ea.answer_text AS userAnswer, ea.is_correct AS isCorrect, ea.score AS earnedScore "
            + "FROM exam_paper_question pq "
            + "JOIN exam_question q ON q.id=pq.question_id "
            + "JOIN exam_attempt a ON a.paper_id=pq.paper_id "
            + "LEFT JOIN exam_answer ea ON ea.attempt_id=a.id AND ea.question_id=q.id "
            + "WHERE a.id=#{attemptId} ORDER BY pq.sort_no, pq.id")
    List<Map<String, Object>> listReviewAnswers(@Param("attemptId") long attemptId);

    @Select("SELECT q.id AS questionId, q.type, q.stem, q.answer_key AS answerKey, q.score AS maxScore, "
            + "q.mark_rubric AS markRubric, "
            + "ea.answer_text AS userAnswer, ea.is_correct AS isCorrect, ea.score AS earnedScore "
            + "FROM exam_paper_question pq "
            + "JOIN exam_question q ON q.id=pq.question_id "
            + "JOIN exam_attempt a ON a.paper_id=pq.paper_id "
            + "LEFT JOIN exam_answer ea ON ea.attempt_id=a.id AND ea.question_id=q.id "
            + "WHERE a.id=#{attemptId} ORDER BY pq.sort_no, pq.id")
    List<Map<String, Object>> listReviewAnswersWithRubric(@Param("attemptId") long attemptId);

    @Select("SELECT type, score FROM exam_question WHERE id=#{id}")
    List<Map<String, Object>> selectQuestionScore(@Param("id") long id);

    @Update("UPDATE exam_answer SET score=#{score}, is_correct=#{isCorrect} "
            + "WHERE attempt_id=#{attemptId} AND question_id=#{questionId} AND is_correct=-1")
    int markAnswer(
            @Param("attemptId") long attemptId,
            @Param("questionId") long questionId,
            @Param("score") int score,
            @Param("isCorrect") int isCorrect);

    @Select("SELECT COUNT(*) FROM exam_answer WHERE attempt_id=#{attemptId} AND is_correct=-1")
    Integer countPending(@Param("attemptId") long attemptId);

    @Select("SELECT COALESCE(SUM(score),0) FROM exam_answer WHERE attempt_id=#{attemptId}")
    Integer sumScores(@Param("attemptId") long attemptId);

    @Update("UPDATE exam_attempt SET status='submitted', score=#{score} WHERE id=#{id}")
    int publishScore(@Param("id") long id, @Param("score") int score);

    int countMyAttempts(@Param("username") String username);

    List<Map<String, Object>> pageMyAttempts(
            @Param("username") String username,
            @Param("limit") int limit,
            @Param("offset") int offset);

    int countAttemptsAdmin(@Param("paperId") Long paperId);

    List<Map<String, Object>> pageAttemptsAdmin(
            @Param("paperId") Long paperId,
            @Param("limit") int limit,
            @Param("offset") int offset);

    int countRank(@Param("paperId") long paperId);

    List<Map<String, Object>> pageRank(
            @Param("paperId") long paperId,
            @Param("limit") int limit,
            @Param("offset") int offset);

    @Insert("INSERT INTO exam_wrongbook (username,question_id,last_answer) VALUES (#{username},#{questionId},#{lastAnswer}) "
            + "ON DUPLICATE KEY UPDATE last_answer=VALUES(last_answer)")
    int upsertWrongbook(
            @Param("username") String username,
            @Param("questionId") long questionId,
            @Param("lastAnswer") String lastAnswer);

    int countWrongbook(@Param("username") String username);

    List<Map<String, Object>> pageWrongbook(
            @Param("username") String username,
            @Param("limit") int limit,
            @Param("offset") int offset);

    @Delete("DELETE FROM exam_wrongbook WHERE id=#{id} AND username=#{username}")
    int deleteWrongbook(@Param("username") String username, @Param("id") long id);

    @Select("SELECT w.question_id AS questionId, q.type, q.stem, q.answer_key AS answerKey "
            + "FROM exam_wrongbook w JOIN exam_question q ON q.id=w.question_id "
            + "WHERE w.username=#{username} ORDER BY w.id DESC")
    List<Map<String, Object>> listWrongbookExport(@Param("username") String username);

    @Insert("INSERT INTO exam_attempt (paper_id,username,mode,status,score,total_score,started_at,submitted_at) "
            + "VALUES (#{paperId},#{username},'exam','submitted',#{score},#{totalScore},#{startedAt},#{submittedAt})")
    int insertAttemptImported(
            @Param("paperId") long paperId,
            @Param("username") String username,
            @Param("score") int score,
            @Param("totalScore") int totalScore,
            @Param("startedAt") java.sql.Timestamp startedAt,
            @Param("submittedAt") java.sql.Timestamp submittedAt);

    @Select("SELECT COUNT(*) FROM exam_paper WHERE status='published' AND gate_ticket=1")
    Integer countGatePapers();

    @Select("SELECT a.score, a.total_score, p.pass_score FROM exam_attempt a "
            + "JOIN exam_paper p ON p.id=a.paper_id "
            + "WHERE a.username=#{username} AND a.mode='exam' AND a.status='submitted' "
            + "AND p.gate_ticket=1 AND p.status='published'")
    List<Map<String, Object>> listGateAttempts(@Param("username") String username);
}
