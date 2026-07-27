package com.thesis.config;

import jakarta.persistence.EntityManager;
import jakarta.persistence.EntityManagerFactory;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;
import org.springframework.stereotype.Component;

import javax.sql.DataSource;

/**
 * 静态 Store 取 JpaDb / Repository；对标原 JdbcSupport。
 */
@Component
public class JpaSupport implements ApplicationContextAware {

    private static ApplicationContext CTX;
    private static JpaDb DB;
    private static EntityManagerFactory EMF;

    public static JpaDb db() {
        if (DB == null) {
            throw new IllegalStateException("JPA 数据源未就绪");
        }
        return DB;
    }

    /** 短生命周期 EM；调用方用完应 close（原生查询场景）。 */
    public static EntityManager em() {
        if (EMF == null) {
            throw new IllegalStateException("EntityManagerFactory 未就绪");
        }
        return EMF.createEntityManager();
    }

    public static <T> T repo(Class<T> type) {
        if (CTX == null) {
            throw new IllegalStateException("JPA 未就绪");
        }
        return CTX.getBean(type);
    }

    @Override
    public void setApplicationContext(ApplicationContext ctx) {
        CTX = ctx;
        DB = new JpaDb(ctx.getBean(DataSource.class));
        EMF = ctx.getBean(EntityManagerFactory.class);
    }
}
