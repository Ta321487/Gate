package com.thesis.mapper;

import org.apache.ibatis.annotations.*;
import java.util.List;
import java.util.Map;

@Mapper
public interface VoteMapper {
    @Select("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='vote_ballot'")
    Integer countTable();

    @Select("SELECT id, title, author, isbn, category_id AS categoryId, stock AS maxVotes, status, cover_url AS coverUrl, created_at AS createdAt FROM vote_campaign WHERE status='available' ORDER BY id DESC")
    List<Map<String, Object>> listOpenCampaigns();

    @Select("SELECT id, title, author, isbn, category_id AS categoryId, stock AS maxVotes, status, cover_url AS coverUrl, created_at AS createdAt FROM vote_campaign WHERE id=#{id}")
    Map<String, Object> getCampaign(long id);

    @Select("SELECT id, campaign_id AS campaignId, name, intro, sort_no AS sortNo, status, created_at AS createdAt FROM vote_candidate WHERE campaign_id=#{campaignId} AND status='available' ORDER BY sort_no, id")
    List<Map<String, Object>> listCandidates(long campaignId);

    @Select("SELECT COUNT(*) FROM vote_candidate WHERE campaign_id=#{campaignId}")
    Integer countCandidates(long campaignId);

    @Select("SELECT id, campaign_id AS campaignId, name, intro, sort_no AS sortNo, status, created_at AS createdAt FROM vote_candidate WHERE campaign_id=#{campaignId} ORDER BY sort_no, id LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageCandidates(@Param("campaignId") long campaignId, @Param("limit") int limit, @Param("offset") int offset);

    @Insert("INSERT INTO vote_candidate(campaign_id, name, intro, sort_no, status) VALUES(#{campaignId}, #{name}, #{intro}, #{sortNo}, 'available')")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertCandidate(Map<String, Object> row);

    @Select("SELECT COUNT(*) FROM vote_ballot WHERE candidate_id=#{id}")
    Integer countBallotsByCandidate(long id);

    @Delete("DELETE FROM vote_candidate WHERE id=#{id}")
    int deleteCandidate(long id);

    @Select("SELECT COUNT(*) FROM vote_ballot WHERE campaign_id=#{campaignId} AND username=#{username}")
    Integer countUserBallots(@Param("campaignId") long campaignId, @Param("username") String username);

    @Select("SELECT COUNT(*) FROM vote_candidate WHERE id=#{id} AND campaign_id=#{campaignId} AND status='available'")
    Integer countCandidateOk(@Param("id") long id, @Param("campaignId") long campaignId);

    @Select("SELECT COUNT(*) FROM vote_ballot WHERE campaign_id=#{campaignId} AND username=#{username} AND candidate_id=#{candidateId}")
    Integer countDup(@Param("campaignId") long campaignId, @Param("username") String username, @Param("candidateId") long candidateId);

    @Insert("INSERT INTO vote_ballot(campaign_id, username, candidate_id) VALUES(#{campaignId}, #{username}, #{candidateId})")
    int insertBallot(@Param("campaignId") long campaignId, @Param("username") String username, @Param("candidateId") long candidateId);

    @Select("SELECT c.id, c.name, c.intro, c.sort_no AS sortNo, COALESCE((SELECT COUNT(*) FROM vote_ballot b WHERE b.candidate_id=c.id),0) AS votes FROM vote_candidate c WHERE c.campaign_id=#{campaignId} ORDER BY votes DESC, c.sort_no, c.id")
    List<Map<String, Object>> results(long campaignId);

    @Select("SELECT COUNT(*) FROM vote_ballot WHERE username=#{username}")
    Integer countMine(String username);

    @Select("SELECT b.id, b.campaign_id AS campaignId, b.candidate_id AS candidateId, b.created_at AS createdAt, v.title AS campaignTitle, c.name AS candidateName FROM vote_ballot b JOIN vote_campaign v ON v.id=b.campaign_id JOIN vote_candidate c ON c.id=b.candidate_id WHERE b.username=#{username} ORDER BY b.id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageMine(@Param("username") String username, @Param("limit") int limit, @Param("offset") int offset);

    @Select("SELECT COUNT(*) FROM vote_ballot WHERE campaign_id=#{campaignId}")
    Integer countBallots(long campaignId);

    @Select("SELECT b.id, b.username, b.candidate_id AS candidateId, b.created_at AS createdAt, c.name AS candidateName FROM vote_ballot b JOIN vote_candidate c ON c.id=b.candidate_id WHERE b.campaign_id=#{campaignId} ORDER BY b.id DESC LIMIT #{limit} OFFSET #{offset}")
    List<Map<String, Object>> pageBallots(@Param("campaignId") long campaignId, @Param("limit") int limit, @Param("offset") int offset);
}
