package com.thesis.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.sql.Date;
import java.time.LocalDate;
import java.util.List;

@Mapper
public interface SchemaMapper {

    Integer countTable(@Param("tableName") String tableName);

    Integer countColumn(@Param("tableName") String tableName, @Param("columnName") String columnName);

    void executeDdl(@Param("ddl") String ddl);

    List<String> listTablesWithColumn(@Param("columnName") String columnName);

    LocalDate minDate(@Param("table") String table, @Param("column") String column, @Param("floor") Date floor);

    int shiftDates(
            @Param("table") String table,
            @Param("column") String column,
            @Param("days") long days,
            @Param("floor") Date floor);
}
