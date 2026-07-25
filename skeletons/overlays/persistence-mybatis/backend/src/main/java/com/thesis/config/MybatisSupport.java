package com.thesis.config;

import org.apache.ibatis.session.SqlSessionFactory;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;
import org.springframework.stereotype.Component;

/**
 * 静态 Store 取 Mapper Bean / SqlSessionFactory；对标原 JdbcSupport。
 */
@Component
public class MybatisSupport implements ApplicationContextAware {

    private static ApplicationContext CTX;

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

    @Override
    public void setApplicationContext(ApplicationContext ctx) {
        CTX = ctx;
    }
}
