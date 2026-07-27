package com.thesis.config;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;

@FunctionalInterface
public interface SqlPreparedStatementCreator {
    PreparedStatement createPreparedStatement(Connection con) throws SQLException;
}
