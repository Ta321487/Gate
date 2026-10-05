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

    @Update("UPDATE `${itemTable}` SET view_count=IFNULL(view_count,0)+1 WHERE id=#{id}")
    int bumpViewCount(@Param("itemTable") String itemTable, @Param("id") long id);

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

    @Update("UPDATE `${itemTable}` SET status='unavailable' "
            + "WHERE status='available' AND expire_on IS NOT NULL AND TRIM(expire_on)<>'' "
            + "AND LEFT(TRIM(expire_on),10) <= DATE_FORMAT(CURDATE(),'%Y-%m-%d')")
    int expirePastExpireOn(@Param("itemTable") String itemTable);

    @Update("UPDATE `${itemTable}` SET stage='已下架' "
            + "WHERE status='available' AND stage IN ('招领中','招领','') "
            + "AND expire_on IS NOT NULL AND TRIM(expire_on)<>'' "
            + "AND LEFT(TRIM(expire_on),10) <= DATE_FORMAT(CURDATE(),'%Y-%m-%d')")
    int expirePastExpireOnStage(@Param("itemTable") String itemTable);

    @Select("SELECT id, title, expire_on FROM `${itemTable}` "
            + "WHERE status='available' "
            + "AND expire_on IS NOT NULL AND TRIM(expire_on)<>'' "
            + "AND LEFT(TRIM(expire_on),10) > DATE_FORMAT(CURDATE(),'%Y-%m-%d') "
            + "AND LEFT(TRIM(expire_on),10) <= DATE_FORMAT(DATE_ADD(CURDATE(), INTERVAL #{days} DAY),'%Y-%m-%d') "
            + "AND expire_soon_notified_at IS NULL "
            + "LIMIT 50")
    List<Map<String, Object>> listExpireSoon(
            @Param("itemTable") String itemTable, @Param("days") int days);

    @Select("SELECT id, title, inspect_expire_on AS expire_on FROM `${itemTable}` "
            + "WHERE status='available' "
            + "AND inspect_expire_on IS NOT NULL AND TRIM(inspect_expire_on)<>'' "
            + "AND LEFT(TRIM(inspect_expire_on),10) > DATE_FORMAT(CURDATE(),'%Y-%m-%d') "
            + "AND LEFT(TRIM(inspect_expire_on),10) <= DATE_FORMAT(DATE_ADD(CURDATE(), INTERVAL #{days} DAY),'%Y-%m-%d') "
            + "AND expire_soon_notified_at IS NULL "
            + "LIMIT 50")
    List<Map<String, Object>> listInspectExpireSoon(
            @Param("itemTable") String itemTable, @Param("days") int days);

    @Select("SELECT id, title, mid_due_on AS expire_on FROM `${itemTable}` "
            + "WHERE status='available' "
            + "AND mid_due_on IS NOT NULL AND TRIM(mid_due_on)<>'' "
            + "AND LEFT(TRIM(mid_due_on),10) > DATE_FORMAT(CURDATE(),'%Y-%m-%d') "
            + "AND LEFT(TRIM(mid_due_on),10) <= DATE_FORMAT(DATE_ADD(CURDATE(), INTERVAL #{days} DAY),'%Y-%m-%d') "
            + "AND expire_soon_notified_at IS NULL "
            + "LIMIT 50")
    List<Map<String, Object>> listMidDueSoon(
            @Param("itemTable") String itemTable, @Param("days") int days);

    @Select("SELECT id, title, final_due_on AS expire_on FROM `${itemTable}` "
            + "WHERE status='available' "
            + "AND final_due_on IS NOT NULL AND TRIM(final_due_on)<>'' "
            + "AND LEFT(TRIM(final_due_on),10) > DATE_FORMAT(CURDATE(),'%Y-%m-%d') "
            + "AND LEFT(TRIM(final_due_on),10) <= DATE_FORMAT(DATE_ADD(CURDATE(), INTERVAL #{days} DAY),'%Y-%m-%d') "
            + "AND expire_soon_notified_at IS NULL "
            + "LIMIT 50")
    List<Map<String, Object>> listFinalDueSoon(
            @Param("itemTable") String itemTable, @Param("days") int days);

    @Update("UPDATE `${itemTable}` SET train_hours_total=IFNULL(train_hours_total,0)+#{hours} WHERE id=#{id}")
    int addTrainHours(
            @Param("itemTable") String itemTable, @Param("id") long id, @Param("hours") double hours);

    @Update("UPDATE `${itemTable}` SET expire_soon_notified_at=NOW() WHERE id=#{id}")
    int markExpireSoonNotified(@Param("itemTable") String itemTable, @Param("id") long id);

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

    /** 工作台：按档案列分组计数（stage / lead_source / rent_stage）。列名须调用方已白名单清洗。 */
    List<Map<String, Object>> countByItemColumn(
            @Param("itemTable") String itemTable,
            @Param("column") String column,
            @Param("limit") int limit);

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

    @Delete("DELETE FROM item_equipment WHERE item_id=#{itemId}")
    int deleteItemEquipment(@Param("itemId") long itemId);

    @Insert("INSERT IGNORE INTO item_equipment (item_id, equipment_id) VALUES (#{itemId}, #{equipmentId})")
    int insertItemEquipment(@Param("itemId") long itemId, @Param("equipmentId") long equipmentId);

    @Select("SELECT id FROM sys_equipment_dict WHERE name=#{name} AND enabled=1 LIMIT 1")
    Long selectEquipmentIdByName(@Param("name") String name);

    @Select("SELECT d.name FROM item_equipment ie JOIN sys_equipment_dict d ON d.id=ie.equipment_id "
            + "WHERE ie.item_id=#{itemId} ORDER BY d.sort_order, d.id")
    List<String> listItemEquipmentNames(@Param("itemId") long itemId);

    int countLowStock(
            @Param("itemTable") String itemTable,
            @Param("below") int below,
            @Param("excludeDeleted") boolean excludeDeleted,
            @Param("ownerUsername") String ownerUsername);
}
