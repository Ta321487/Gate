package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.util.List;
import java.util.Map;

@Mapper
public interface TicketLookupMapper {

    List<Map<String, Object>> selectSites(@Param("siteTable") String siteTable);

    List<Map<String, Object>> selectSitesAdmin(@Param("siteTable") String siteTable);

    Map<String, Object> selectSiteById(@Param("siteTable") String siteTable, @Param("id") long id);

    @Insert("INSERT INTO `${siteTable}` (name, remark) VALUES (#{name}, #{remark})")
    int insertSite(
            @Param("siteTable") String siteTable,
            @Param("name") String name,
            @Param("remark") String remark);

    @Select("SELECT MAX(id) FROM `${siteTable}` WHERE name=#{name}")
    Long maxSiteIdByName(@Param("siteTable") String siteTable, @Param("name") String name);

    @Update("UPDATE `${siteTable}` SET name=#{name}, remark=#{remark} WHERE id=#{id}")
    int updateSite(
            @Param("siteTable") String siteTable,
            @Param("id") long id,
            @Param("name") String name,
            @Param("remark") String remark);

    @Delete("DELETE FROM `${siteTable}` WHERE id=#{id}")
    int deleteSite(@Param("siteTable") String siteTable, @Param("id") long id);

    List<Map<String, Object>> selectUnits(
            @Param("unitTable") String unitTable, @Param("siteId") Long siteId);

    List<Map<String, Object>> selectUnitsAdmin(
            @Param("unitTable") String unitTable, @Param("siteId") Long siteId);

    Map<String, Object> selectUnitById(@Param("unitTable") String unitTable, @Param("id") long id);

    @Select("SELECT COUNT(*) FROM `${unitTable}` WHERE building_id=#{siteId}")
    int countUnitsBySite(@Param("unitTable") String unitTable, @Param("siteId") long siteId);

    @Select("SELECT COUNT(*) FROM `${unitTable}` WHERE id=#{id}")
    int countUnit(@Param("unitTable") String unitTable, @Param("id") long id);

    @Insert("INSERT INTO `${unitTable}` (building_id, code, capacity) VALUES (#{siteId}, #{code}, #{capacity})")
    int insertUnit(
            @Param("unitTable") String unitTable,
            @Param("siteId") long siteId,
            @Param("code") String code,
            @Param("capacity") int capacity);

    @Select("SELECT id FROM `${unitTable}` WHERE building_id=#{siteId} AND code=#{code}")
    Long unitIdBySiteCode(
            @Param("unitTable") String unitTable,
            @Param("siteId") long siteId,
            @Param("code") String code);

    @Update("UPDATE `${unitTable}` SET building_id=#{siteId}, code=#{code}, capacity=#{capacity} WHERE id=#{id}")
    int updateUnit(
            @Param("unitTable") String unitTable,
            @Param("id") long id,
            @Param("siteId") long siteId,
            @Param("code") String code,
            @Param("capacity") int capacity);

    @Delete("DELETE FROM `${unitTable}` WHERE id=#{id}")
    int deleteUnit(@Param("unitTable") String unitTable, @Param("id") long id);

    List<Map<String, Object>> selectTypes(@Param("typeTable") String typeTable);

    List<Map<String, Object>> selectTypesAdmin(@Param("typeTable") String typeTable);

    Map<String, Object> selectTypeById(@Param("typeTable") String typeTable, @Param("id") long id);

    @Select("SELECT name FROM `${typeTable}` WHERE id=#{id}")
    String typeName(@Param("typeTable") String typeTable, @Param("id") long id);

    @Select("SELECT COUNT(*) FROM `${typeTable}` WHERE id=#{id}")
    int countType(@Param("typeTable") String typeTable, @Param("id") long id);

    @Insert("INSERT INTO `${typeTable}` (name, sort_no) VALUES (#{name}, #{sortNo})")
    int insertType(
            @Param("typeTable") String typeTable,
            @Param("name") String name,
            @Param("sortNo") int sortNo);

    @Select("SELECT id FROM `${typeTable}` WHERE name=#{name}")
    Long typeIdByName(@Param("typeTable") String typeTable, @Param("name") String name);

    @Update("UPDATE `${typeTable}` SET name=#{name}, sort_no=#{sortNo} WHERE id=#{id}")
    int updateType(
            @Param("typeTable") String typeTable,
            @Param("id") long id,
            @Param("name") String name,
            @Param("sortNo") int sortNo);

    @Delete("DELETE FROM `${typeTable}` WHERE id=#{id}")
    int deleteType(@Param("typeTable") String typeTable, @Param("id") long id);

    Map<String, Object> selectLocation(
            @Param("unitTable") String unitTable,
            @Param("siteTable") String siteTable,
            @Param("unitId") long unitId);
}
