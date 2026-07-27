package com.thesis.config;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 与 JdbcTemplate 常用子集同形，底层走 DataSource（与 JPA 共用库）。
 * 复杂业务 Store 用本类；核心实体另见 repository / entity。
 */
public final class JpaDb {

    private final DataSource dataSource;

    public JpaDb(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    public void execute(String sql) {
        try (Connection c = dataSource.getConnection();
             Statement st = c.createStatement()) {
            st.execute(sql);
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    public int update(String sql, Object... args) {
        try (Connection c = dataSource.getConnection();
             PreparedStatement ps = c.prepareStatement(sql)) {
            bind(ps, args);
            return ps.executeUpdate();
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    public int update(SqlPreparedStatementCreator psc, KeyHolder keyHolder) {
        try (Connection c = dataSource.getConnection();
             PreparedStatement ps = psc.createPreparedStatement(c)) {
            int n = ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                if (keys != null && keys.next()) {
                    keyHolder.setKey(keys.getObject(1));
                }
            }
            return n;
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    public <T> List<T> query(String sql, SqlRowMapper<T> mapper, Object... args) {
        try (Connection c = dataSource.getConnection();
             PreparedStatement ps = c.prepareStatement(sql)) {
            bind(ps, args);
            try (ResultSet rs = ps.executeQuery()) {
                List<T> list = new ArrayList<>();
                int i = 0;
                while (rs.next()) {
                    list.add(mapper.mapRow(rs, i++));
                }
                return list;
            }
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    public <T> T query(String sql, SqlResultSetExtractor<T> extractor, Object... args) {
        try (Connection c = dataSource.getConnection();
             PreparedStatement ps = c.prepareStatement(sql)) {
            bind(ps, args);
            try (ResultSet rs = ps.executeQuery()) {
                return extractor.extractData(rs);
            }
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    @SuppressWarnings("unchecked")
    public <T> T queryForObject(String sql, Class<T> type, Object... args) {
        try (Connection c = dataSource.getConnection();
             PreparedStatement ps = c.prepareStatement(sql)) {
            bind(ps, args);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return null;
                }
                Object v = rs.getObject(1);
                if (v == null) {
                    return null;
                }
                if (type.isInstance(v)) {
                    return (T) v;
                }
                if (type == Integer.class || type == int.class) {
                    return (T) Integer.valueOf(rs.getInt(1));
                }
                if (type == Long.class || type == long.class) {
                    return (T) Long.valueOf(rs.getLong(1));
                }
                if (type == Double.class || type == double.class) {
                    return (T) Double.valueOf(rs.getDouble(1));
                }
                if (type == String.class) {
                    return (T) String.valueOf(v);
                }
                return type.cast(v);
            }
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    public List<Map<String, Object>> queryForList(String sql, Object... args) {
        return query(sql, (rs, i) -> mapRow(rs), args);
    }

    private static Map<String, Object> mapRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        int n = rs.getMetaData().getColumnCount();
        for (int c = 1; c <= n; c++) {
            String label = rs.getMetaData().getColumnLabel(c);
            m.put(label, rs.getObject(c));
        }
        return m;
    }

    private static void bind(PreparedStatement ps, Object... args) throws SQLException {
        if (args == null) {
            return;
        }
        for (int i = 0; i < args.length; i++) {
            ps.setObject(i + 1, args[i]);
        }
    }
}
