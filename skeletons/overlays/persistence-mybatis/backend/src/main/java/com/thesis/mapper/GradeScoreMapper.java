package com.thesis.mapper;

import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Mapper
public interface GradeScoreMapper {

    String RANK =
            "SELECT s.id, s.username, s.course_id AS courseId, c.title AS courseTitle, "
                    + "s.term_id AS termId, t.name AS termName, s.score, "
                    + "(SELECT 1 + COUNT(*) FROM grade_score s2 "
                    + " WHERE s2.course_id=s.course_id AND s2.term_id=s.term_id "
                    + " AND s2.score > s.score) AS rankNo "
                    + "FROM grade_score s "
                    + "JOIN course_item c ON c.id=s.course_id "
                    + "JOIN grade_term t ON t.id=s.term_id ";

    @Select("SELECT COUNT(*) FROM information_schema.tables "
            + "WHERE table_schema=DATABASE() AND table_name='grade_score'")
    Integer countTable();

    @Select("SELECT id, name FROM grade_term ORDER BY id")
    List<Map<String, Object>> listTerms();

    @Select("SELECT id, title FROM course_item ORDER BY id")
    List<Map<String, Object>> listCourses();

    @Select({"<script>",
            RANK,
            "WHERE 1=1",
            "<if test='courseId != null and courseId &gt; 0'> AND s.course_id=#{courseId}</if>",
            "<if test='termId != null and termId &gt; 0'> AND s.term_id=#{termId}</if>",
            "ORDER BY s.term_id, s.course_id, rankNo, s.username",
            "</script>"})
    List<Map<String, Object>> listAdmin(
            @Param("courseId") Long courseId, @Param("termId") Long termId);

    @Select(RANK + "WHERE s.username=#{username} ORDER BY s.term_id, s.course_id")
    List<Map<String, Object>> listMine(String username);

    @Select("SELECT COUNT(*) FROM course_item WHERE id=#{id}")
    Integer countCourse(long id);

    @Select("SELECT COUNT(*) FROM grade_term WHERE id=#{id}")
    Integer countTerm(long id);

    @Select("SELECT id FROM grade_score WHERE username=#{username} AND course_id=#{courseId} AND term_id=#{termId}")
    List<Long> findIds(
            @Param("username") String username,
            @Param("courseId") long courseId,
            @Param("termId") long termId);

    @Insert("INSERT INTO grade_score (username, course_id, term_id, score) "
            + "VALUES (#{username}, #{courseId}, #{termId}, #{score})")
    int insert(
            @Param("username") String username,
            @Param("courseId") long courseId,
            @Param("termId") long termId,
            @Param("score") BigDecimal score);

    @Update("UPDATE grade_score SET score=#{score} WHERE id=#{id}")
    int updateScore(@Param("id") long id, @Param("score") BigDecimal score);

    @Delete("DELETE FROM grade_score WHERE id=#{id}")
    int delete(long id);

    @Select(RANK + "WHERE s.username=#{username} AND s.course_id=#{courseId} AND s.term_id=#{termId}")
    List<Map<String, Object>> findOne(
            @Param("username") String username,
            @Param("courseId") long courseId,
            @Param("termId") long termId);
}
