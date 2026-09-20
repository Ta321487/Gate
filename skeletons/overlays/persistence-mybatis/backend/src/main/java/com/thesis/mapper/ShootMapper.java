package com.thesis.mapper;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Mapper
public interface ShootMapper {

    @Select("SELECT id, name, price_yuan AS priceYuan FROM service_bundle WHERE id=#{id} AND enabled=1")
    List<Map<String, Object>> bundle(@Param("id") long id);

    @Update("UPDATE reservation SET bundle_id=#{bundleId}, bundle_yuan=#{price} WHERE id=#{id}")
    int snap(@Param("id") long id, @Param("bundleId") long bundleId, @Param("price") BigDecimal price);

    @Insert("INSERT INTO deliverable (reservation_id, file_url, delivered) VALUES (#{id}, '', 0)")
    int insertFile(@Param("id") long id);

    @Select("SELECT id, title FROM ${itemTable} WHERE status='available' ORDER BY id")
    List<Map<String, Object>> photographers(@Param("itemTable") String itemTable);

    @Select("SELECT id, name, price_yuan AS priceYuan, detail FROM service_bundle WHERE enabled=1 ORDER BY id")
    List<Map<String, Object>> enabledBundles();

    @Select("SELECT id, name, price_yuan AS priceYuan, detail, enabled FROM service_bundle ORDER BY id")
    List<Map<String, Object>> allBundles();

    @Update("UPDATE service_bundle SET name=#{name}, price_yuan=#{price}, detail=#{detail}, enabled=#{enabled} WHERE id=#{id}")
    int updateBundle(
            @Param("id") long id,
            @Param("name") String name,
            @Param("price") BigDecimal price,
            @Param("detail") String detail,
            @Param("enabled") int enabled);

    @Insert("INSERT INTO service_bundle (name, price_yuan, detail, enabled) VALUES (#{name},#{price},#{detail},#{enabled})")
    int insertBundle(
            @Param("name") String name,
            @Param("price") BigDecimal price,
            @Param("detail") String detail,
            @Param("enabled") int enabled);

    @Select("SELECT d.id, d.reservation_id AS reservationId, d.file_url AS fileUrl, d.delivered "
            + "FROM deliverable d JOIN reservation r ON r.id=d.reservation_id "
            + "WHERE r.username=#{username} ORDER BY d.id DESC")
    List<Map<String, Object>> mine(@Param("username") String username);

    @Select("SELECT d.id, d.reservation_id AS reservationId, d.file_url AS fileUrl, d.delivered, r.username "
            + "FROM deliverable d JOIN reservation r ON r.id=d.reservation_id ORDER BY d.id DESC")
    List<Map<String, Object>> files();

    @Update("UPDATE deliverable SET file_url=#{url}, delivered=#{delivered} WHERE id=#{id}")
    int saveFile(@Param("id") long id, @Param("url") String url, @Param("delivered") int delivered);
}
