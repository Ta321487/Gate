package com.thesis.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.Collection;
import java.util.List;
import java.util.Map;

@Mapper
public interface RecommendMapper {

    List<Long> selectInteractedTicketItemIds(
            @Param("ticketTable") String ticketTable,
            @Param("itemFk") String itemFk,
            @Param("username") String username);

    List<Map<String, Object>> selectCategoryCounts(
            @Param("itemTable") String itemTable,
            @Param("ids") Collection<Long> ids);

    List<Map<String, Object>> selectAllCategories(@Param("catTable") String catTable);

    List<Long> selectIdsByCategories(
            @Param("itemTable") String itemTable,
            @Param("categoryIds") Collection<Long> categoryIds,
            @Param("excludeIds") Collection<Long> excludeIds,
            @Param("hotJoin") String hotJoin,
            @Param("limit") int limit);

    List<Long> selectHotIds(
            @Param("itemTable") String itemTable,
            @Param("excludeIds") Collection<Long> excludeIds,
            @Param("hotJoin") String hotJoin,
            @Param("limit") int limit);

    List<Long> selectLatestIds(
            @Param("itemTable") String itemTable,
            @Param("excludeIds") Collection<Long> excludeIds,
            @Param("limit") int limit,
            @Param("offset") int offset);
}
