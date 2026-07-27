package com.thesis.config;

import java.sql.ResultSet;
import java.sql.SQLException;

@FunctionalInterface
public interface SqlRowMapper<T> {
    T mapRow(ResultSet rs, int rowNum) throws SQLException;
}
