package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface ArchiveMapper {

    @Select("SELECT COUNT(*) FROM `${catTable}` WHERE name=#{name}")
    int countCategoryByName(@Param("catTable") String catTable, @Param("name") String name);

    @Select("SELECT COUNT(*) FROM `${catTable}` WHERE id=#{id}")
    int countCategoryById(@Param("catTable") String catTable, @Param("id") long id);

    @Select("SELECT COUNT(*) FROM `${catTable}` WHERE name=#{name} AND id<>#{id}")
    int countCategoryNameDup(
            @Param("catTable") String catTable, @Param("name") String name, @Param("id") long id);

    int insertCategory(Map<String, Object> row);

    @Update("UPDATE `${catTable}` SET name=#{name} WHERE id=#{id}")
    int updateCategory(
            @Param("catTable") String catTable, @Param("id") long id, @Param("name") String name);

    @Update("UPDATE `${catTable}` SET name=#{name}, dimension=#{dimension} WHERE id=#{id}")
    int updateCategoryWithDimension(
            @Param("catTable") String catTable,
            @Param("id") long id,
            @Param("name") String name,
            @Param("dimension") String dimension);

    @Delete("DELETE FROM `${catTable}` WHERE id=#{id}")
    int deleteCategory(@Param("catTable") String catTable, @Param("id") long id);

    List<Map<String, Object>> selectCategories(
            @Param("catTable") String catTable,
            @Param("itemTable") String itemTable,
            @Param("excludeDeleted") boolean excludeDeleted,
            @Param("multiCategory") boolean multiCategory,
            @Param("itemCatTable") String itemCatTable,
            @Param("includeDimension") boolean includeDimension);

    @Select("SELECT name FROM `${catTable}` WHERE id=#{id}")
    String selectCategoryName(@Param("catTable") String catTable, @Param("id") long id);

    @Select("SELECT id FROM `${catTable}` WHERE name=#{name} LIMIT 1")
    Long selectCategoryIdByName(@Param("catTable") String catTable, @Param("name") String name);

    @Select("SELECT COUNT(*) FROM `${catTable}`")
    long countCategories(@Param("catTable") String catTable);

    int countItemsByCategory(
            @Param("itemTable") String itemTable,
            @Param("categoryId") long categoryId,
            @Param("excludeDeleted") boolean excludeDeleted);

    @Select("SELECT COUNT(*) FROM `${itemCatTable}` WHERE category_id=#{categoryId}")
    int countJunctionByCategory(
            @Param("itemCatTable") String itemCatTable, @Param("categoryId") long categoryId);

    int insertItem(Map<String, Object> row);

    int updateItemCore(Map<String, Object> row);

    @Update("UPDATE `${itemTable}` SET `${col}`=#{val} WHERE id=#{id}")
    int updateItemColumn(
            @Param("itemTable") String itemTable,
            @Param("col") String col,
            @Param("val") Object val,
            @Param("id") long id);

    @Update("UPDATE `${itemTable}` SET deleted_at=NOW() WHERE id=#{id} AND deleted_at IS NULL")
    int softDeleteItem(@Param("itemTable") String itemTable, @Param("id") long id);

    @Update("UPDATE `${itemTable}` SET deleted_at=NULL WHERE id=#{id}")
    int restoreItem(@Param("itemTable") String itemTable, @Param("id") long id);

    @Delete("DELETE FROM `${itemTable}` WHERE id=#{id}")
    int hardDeleteItem(@Param("itemTable") String itemTable, @Param("id") long id);

    Map<String, Object> selectItemById(@Param("itemTable") String itemTable, @Param("id") long id);

    List<Map<String, Object>> selectItems(
            @Param("itemTable") String itemTable,
            @Param("authorCol") String authorCol,
            @Param("isbnCol") String isbnCol,
            @Param("excludeDeleted") boolean excludeDeleted,
            @Param("categoryId") Long categoryId,
            @Param("categoryIds") List<Long> categoryIds,
            @Param("multiCategoryFilter") boolean multiCategoryFilter,
            @Param("itemCatTable") String itemCatTable,
            @Param("like") String like,
            @Param("tagIds") List<Long> tagIds,
            @Param("itemTagTable") String itemTagTable,
            @Param("itemTagFk") String itemTagFk,
            @Param("requireAvailable") boolean requireAvailable,
            @Param("scheduleFilter") boolean scheduleFilter,
            @Param("filterByEnd") boolean filterByEnd,
            @Param("ownerUsername") String ownerUsername);

    @Update("UPDATE `${itemTable}` SET status='unavailable' "
            + "WHERE status='available' AND start_at IS NOT NULL AND start_at <= NOW()")
    int expirePastStarts(@Param("itemTable") String itemTable);

    @Update("UPDATE `${itemTable}` SET status='unavailable' "
            + "WHERE status='available' AND end_at IS NOT NULL AND end_at <= NOW()")
    int expirePastEnds(@Param("itemTable") String itemTable);

    List<Map<String, Object>> selectMine(
            @Param("itemTable") String itemTable,
            @Param("mineCol") String mineCol,
            @Param("username") String username);

    List<Map<String, Object>> suggestTitles(
            @Param("itemTable") String itemTable,
            @Param("prefix") String prefix,
            @Param("excludeDeleted") boolean excludeDeleted,
            @Param("requireAvailable") boolean requireAvailable,
            @Param("limit") int limit);

    @Update("UPDATE `${itemTable}` SET stock=stock+#{delta}, status=IF(stock>0,'available','unavailable') "
            + "WHERE id=#{id} AND stock>=#{need}")
    int adjustStockDown(
            @Param("itemTable") String itemTable,
            @Param("id") long id,
            @Param("delta") int delta,
            @Param("need") int need);

    @Update("UPDATE `${itemTable}` SET stock=stock+#{delta}, status='available' WHERE id=#{id}")
    int adjustStockUp(
            @Param("itemTable") String itemTable, @Param("id") long id, @Param("delta") int delta);

    long countItems(
            @Param("itemTable") String itemTable, @Param("excludeDeleted") boolean excludeDeleted);

    long countItemsOwned(
            @Param("itemTable") String itemTable,
            @Param("excludeDeleted") boolean excludeDeleted,
            @Param("ownerUsername") String ownerUsername);

    long sumStock(
            @Param("itemTable") String itemTable, @Param("excludeDeleted") boolean excludeDeleted);

    List<Map<String, Object>> stockByCategory(
            @Param("catTable") String catTable,
            @Param("itemTable") String itemTable,
            @Param("limit") int limit,
            @Param("ownerUsername") String ownerUsername);

    List<Map<String, Object>> selectTags(@Param("tagTable") String tagTable);

    List<Map<String, Object>> selectItemTags(
            @Param("tagTable") String tagTable,
            @Param("itemTagTable") String itemTagTable,
            @Param("itemTagFk") String itemTagFk,
            @Param("itemId") long itemId);

    List<Map<String, Object>> selectItemCategories(
            @Param("catTable") String catTable,
            @Param("itemCatTable") String itemCatTable,
            @Param("includeDimension") boolean includeDimension,
            @Param("itemId") long itemId);

    @Delete("DELETE FROM `${itemCatTable}` WHERE item_id=#{itemId}")
    int deleteItemCategories(@Param("itemCatTable") String itemCatTable, @Param("itemId") long itemId);

    @Insert("INSERT INTO `${itemCatTable}` (item_id, category_id) VALUES (#{itemId}, #{categoryId})")
    int insertItemCategory(
            @Param("itemCatTable") String itemCatTable,
            @Param("itemId") long itemId,
            @Param("categoryId") long categoryId);

    @Delete("DELETE FROM `${itemTagTable}` WHERE `${itemTagFk}`=#{itemId}")
    int deleteItemTags(
            @Param("itemTagTable") String itemTagTable,
            @Param("itemTagFk") String itemTagFk,
            @Param("itemId") long itemId);

    @Insert("INSERT INTO `${itemTagTable}` (`${itemTagFk}`, tag_id) VALUES (#{itemId}, #{tagId})")
    int insertItemTag(
            @Param("itemTagTable") String itemTagTable,
            @Param("itemTagFk") String itemTagFk,
            @Param("itemId") long itemId,
            @Param("tagId") long tagId);

    @Select("SELECT id FROM `${tagTable}` WHERE name=#{name} LIMIT 1")
    Long selectTagIdByName(@Param("tagTable") String tagTable, @Param("name") String name);

    int countLowStock(
            @Param("itemTable") String itemTable,
            @Param("below") int below,
            @Param("excludeDeleted") boolean excludeDeleted,
            @Param("ownerUsername") String ownerUsername);
}
