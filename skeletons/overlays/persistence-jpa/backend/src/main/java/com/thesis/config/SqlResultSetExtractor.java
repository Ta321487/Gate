package com.thesis.config;

import java.sql.ResultSet;
import java.sql.SQLException;

@FunctionalInterface
public interface SqlResultSetExtractor<T> {
    T extractData(ResultSet rs) throws SQLException;
}
