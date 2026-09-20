package com.thesis.config;

import org.apache.ibatis.session.SqlSessionFactory;

import javax.sql.DataSource;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;
import org.springframework.stereotype.Component;

/**
 * 静态 Store 取 Mapper Bean / SqlSessionFactory；对标原 JdbcSupport。
 */
@Component
public class MybatisSupport implements ApplicationContextAware {

    private static ApplicationContext CTX;
    private static MbSql SQL;

    public static <T> T mapper(Class<T> type) {
        if (CTX == null) {
            throw new IllegalStateException("MyBatis 未就绪");
        }
        return CTX.getBean(type);
    }

    public static SqlSessionFactory factory() {
        if (CTX == null) {
            throw new IllegalStateException("MyBatis 未就绪");
        }
        return CTX.getBean(SqlSessionFactory.class);
    }

    /** 尚未 Mapper 化的 Store 取原生 SQL 入口；对标原 JdbcSupport.jdbc()。 */
    public static MbSql db() {
        if (SQL == null) {
            throw new IllegalStateException("MyBatis 数据源未就绪");
        }
        return SQL;
    }

    @Override
    public void setApplicationContext(ApplicationContext ctx) {
        CTX = ctx;
        SQL = new MbSql(ctx.getBean(DataSource.class));
    }
}
