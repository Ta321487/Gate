package com.thesis.config;

import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

/**
 * 静态 Store 取 JdbcTemplate；Controller 无需改注入签名。
 */
@Component
public class JdbcSupport implements ApplicationContextAware {

    private static JdbcTemplate JDBC;

    public static JdbcTemplate jdbc() {
        if (JDBC == null) {
            throw new IllegalStateException("数据源未就绪");
        }
        return JDBC;
    }

    @Override
    public void setApplicationContext(ApplicationContext ctx) {
        JDBC = ctx.getBean(JdbcTemplate.class);
    }
}
