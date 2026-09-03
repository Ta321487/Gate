"""从 baseline JDBC Store 生成 persistence-jpa 叠层（不改 baseline / mybatis）。

Store 表面签名不变；JdbcTemplate → JpaDb（DataSource 原生 SQL）；
并附带 Spring Data JPA Entity/Repository 供答辩与门禁哨兵。
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_JAVA = ROOT / "skeletons" / "baseline" / "backend" / "src" / "main" / "java"
BASE_POM = ROOT / "skeletons" / "baseline" / "backend" / "pom.xml"
OUT = ROOT / "skeletons" / "overlays" / "persistence-jpa"
OUT_JAVA = OUT / "backend" / "src" / "main" / "java"
OUT_RES = OUT / "backend" / "src" / "main" / "resources"

REPLACEMENTS = [
    ("import org.springframework.jdbc.core.JdbcTemplate;\n", "import com.thesis.config.JpaDb;\n"),
    ("import org.springframework.jdbc.core.RowMapper;\n", "import com.thesis.config.SqlRowMapper;\n"),
    (
        "import org.springframework.jdbc.support.GeneratedKeyHolder;\n",
        "import com.thesis.config.GeneratedKeyHolder;\n",
    ),
    (
        "import org.springframework.jdbc.support.KeyHolder;\n",
        "import com.thesis.config.KeyHolder;\n",
    ),
    ("import com.thesis.config.JdbcSupport;\n", "import com.thesis.config.JpaSupport;\n"),
    ("JdbcSupport.jdbc()", "JpaSupport.db()"),
    ("JdbcTemplate", "JpaDb"),
    ("RowMapper<", "SqlRowMapper<"),
    ("保证 JdbcSupport", "保证 JpaSupport"),
    ("对标原 JdbcSupport", "对标原 JdbcSupport；本包为 JPA"),
]


def transform_java(text: str) -> str:
    for a, b in REPLACEMENTS:
        text = text.replace(a, b)
    # 兜底：残留 spring.jdbc 引用
    text = text.replace("org.springframework.jdbc.core.JdbcTemplate", "com.thesis.config.JpaDb")
    text = text.replace("org.springframework.jdbc.support.GeneratedKeyHolder", "com.thesis.config.GeneratedKeyHolder")
    text = text.replace("org.springframework.jdbc.support.KeyHolder", "com.thesis.config.KeyHolder")
    return text


def collect_sources() -> list[Path]:
    out: list[Path] = []
    for p in BASE_JAVA.rglob("*.java"):
        if p.name == "JdbcSupport.java":
            continue
        t = p.read_text(encoding="utf-8")
        if (
            "JdbcSupport" in t
            or "JdbcTemplate" in t
            or "org.springframework.jdbc" in t
        ):
            out.append(p)
    return out


JPADB = r'''package com.thesis.config;

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
'''

JPASUPPORT = r'''package com.thesis.config;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;
import org.springframework.stereotype.Component;

import javax.sql.DataSource;

/**
 * 静态 Store 取 JpaDb / Repository / EntityManager；对标原 JdbcSupport。
 */
@Component
public class JpaSupport implements ApplicationContextAware {

    private static ApplicationContext CTX;
    private static JpaDb DB;

    @PersistenceContext
    private EntityManager entityManager;

    private static EntityManager EM;

    public static JpaDb db() {
        if (DB == null) {
            throw new IllegalStateException("JPA 数据源未就绪");
        }
        return DB;
    }

    public static EntityManager em() {
        if (EM == null) {
            throw new IllegalStateException("EntityManager 未就绪");
        }
        return EM;
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
        EM = entityManager;
    }
}
'''

# Fix JpaSupport - @PersistenceContext on instance field won't assign to static EM in setApplicationContext reliably
# Better inject EntityManager in setApplicationContext via ctx.getBean(EntityManager.class) - might not work
# Use EntityManagerFactory instead

JPASUPPORT = r'''package com.thesis.config;

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
'''

SQL_ROW = r'''package com.thesis.config;

import java.sql.ResultSet;
import java.sql.SQLException;

@FunctionalInterface
public interface SqlRowMapper<T> {
    T mapRow(ResultSet rs, int rowNum) throws SQLException;
}
'''

SQL_RSE = r'''package com.thesis.config;

import java.sql.ResultSet;
import java.sql.SQLException;

@FunctionalInterface
public interface SqlResultSetExtractor<T> {
    T extractData(ResultSet rs) throws SQLException;
}
'''

SQL_PSC = r'''package com.thesis.config;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;

@FunctionalInterface
public interface SqlPreparedStatementCreator {
    PreparedStatement createPreparedStatement(Connection con) throws SQLException;
}
'''

KEY_HOLDER = r'''package com.thesis.config;

public interface KeyHolder {
    Number getKey();

    void setKey(Object key);
}
'''

GEN_KEY = r'''package com.thesis.config;

public class GeneratedKeyHolder implements KeyHolder {

    private Number key;

    @Override
    public Number getKey() {
        return key;
    }

    @Override
    public void setKey(Object key) {
        if (key == null) {
            this.key = null;
        } else if (key instanceof Number n) {
            this.key = n;
        } else {
            try {
                this.key = Long.valueOf(String.valueOf(key));
            } catch (NumberFormatException e) {
                this.key = null;
            }
        }
    }
}
'''

NOTICE_ENTITY = r'''package com.thesis.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Temporal;
import jakarta.persistence.TemporalType;

import java.util.Date;

/** 公告实体（sys_notice）；演示 Spring Data JPA Entity 映射。 */
@Entity
@Table(name = "sys_notice")
public class NoticeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String title;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String content;

    @Column(name = "publisher_username")
    private String publisherUsername;

    @Column(name = "publisher_name")
    private String publisherName;

    @Temporal(TemporalType.TIMESTAMP)
    @Column(name = "created_at", insertable = false, updatable = false)
    private Date createdAt;

    @Temporal(TemporalType.TIMESTAMP)
    @Column(name = "updated_at", insertable = false, updatable = false)
    private Date updatedAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }
    public String getPublisherUsername() { return publisherUsername; }
    public void setPublisherUsername(String publisherUsername) { this.publisherUsername = publisherUsername; }
    public String getPublisherName() { return publisherName; }
    public void setPublisherName(String publisherName) { this.publisherName = publisherName; }
    public Date getCreatedAt() { return createdAt; }
    public Date getUpdatedAt() { return updatedAt; }
}
'''

NOTICE_REPO = r'''package com.thesis.repository;

import com.thesis.entity.NoticeEntity;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface NoticeRepository extends JpaRepository<NoticeEntity, Long> {
    long countByTitle(String title);

    Page<NoticeEntity> findAllByOrderByIdDesc(Pageable pageable);
}
'''

# NoticeStore rewritten to use NoticeRepository (true JPA path)
NOTICE_STORE = r'''package com.thesis.service;

import com.thesis.config.JpaSupport;
import com.thesis.entity.NoticeEntity;
import com.thesis.repository.NoticeRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 基线公告（MySQL sys_notice）— Spring Data JPA Repository。
 */
public class NoticeStore {

    private static final SimpleDateFormat FMT = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

    private static NoticeRepository repo() {
        return JpaSupport.repo(NoticeRepository.class);
    }

    private static String fmt(Date d) {
        if (d == null) return null;
        synchronized (FMT) {
            return FMT.format(d);
        }
    }

    private static Map<String, Object> shape(NoticeEntity e) {
        if (e == null) return null;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", e.getId());
        m.put("title", e.getTitle());
        m.put("content", e.getContent());
        m.put("publisherUsername", e.getPublisherUsername());
        m.put("publisherName", e.getPublisherName());
        m.put("createdAt", fmt(e.getCreatedAt()));
        m.put("updatedAt", fmt(e.getUpdatedAt()));
        return m;
    }

    public static Map<String, Object> add(String title, String content, String publisherUsername, String publisherName) {
        String name = publisherName == null || publisherName.isBlank()
                ? (publisherUsername == null ? "系统" : publisherUsername)
                : publisherName;
        NoticeEntity e = new NoticeEntity();
        e.setTitle(title == null ? "" : title);
        e.setContent(content == null ? "" : content);
        e.setPublisherUsername(publisherUsername == null ? "" : publisherUsername);
        e.setPublisherName(name);
        e = repo().save(e);
        return get(e.getId() == null ? 0L : e.getId());
    }

    /** 领域启动时追加种子；表内已有同标题则跳过。 */
    public static void seedDomain(String title, String content, String publisherUsername, String publisherName) {
        if (repo().countByTitle(title) > 0) return;
        add(title, content, publisherUsername, publisherName);
    }

    public static Map<String, Object> get(long id) {
        return repo().findById(id).map(NoticeStore::shape).orElse(null);
    }

    public static Map<String, Object> update(long id, String title, String content) {
        return repo().findById(id).map(e -> {
            if (title != null) e.setTitle(title);
            if (content != null) e.setContent(content);
            repo().save(e);
            return shape(e);
        }).orElse(null);
    }

    public static boolean delete(long id) {
        if (!repo().existsById(id)) return false;
        repo().deleteById(id);
        return true;
    }

    public static Map<String, Object> page(int page, int size) {
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        Page<NoticeEntity> p = repo().findAllByOrderByIdDesc(PageRequest.of(page - 1, size));
        List<Map<String, Object>> list = new ArrayList<>();
        for (NoticeEntity e : p.getContent()) {
            list.add(shape(e));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("list", list);
        out.put("total", p.getTotalElements());
        out.put("page", page);
        out.put("size", size);
        return out;
    }
}
'''

APP = r'''package com.thesis;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@EnableJpaRepositories("com.thesis.repository")
public class ThesisApplication {
    public static void main(String[] args) {
        SpringApplication.run(ThesisApplication.class, args);
    }
}
'''

POM = r'''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.4.5</version>
  </parent>
  <groupId>com.thesis</groupId>
  <artifactId>thesis-app</artifactId>
  <version>1.0.0</version>
  <name>thesis-app</name>
  <properties>
    <java.version>17</java.version>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
    <dependency>
      <groupId>com.mysql</groupId>
      <artifactId>mysql-connector-j</artifactId>
      <scope>runtime</scope>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
    <!-- 仅 BCrypt 编码器，不启用 Spring Security 过滤器链 -->
    <dependency>
      <groupId>org.springframework.security</groupId>
      <artifactId>spring-security-crypto</artifactId>
    </dependency>
    <dependency>
      <groupId>org.projectlombok</groupId>
      <artifactId>lombok</artifactId>
      <optional>true</optional>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>
'''


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    for src in collect_sources():
        rel = src.relative_to(BASE_JAVA)
        if src.name == "NoticeStore.java":
            continue  # hand-written JPA version
        text = transform_java(src.read_text(encoding="utf-8"))
        # update() with lambda PreparedStatementCreator → our functional interface
        # Baseline uses: db().update(con -> { ... return ps; }, kh);
        # JpaDb.update(SqlPreparedStatementCreator, KeyHolder) — same lambda shape
        write(OUT_JAVA / rel, text)

    write(OUT_JAVA / "com/thesis/config/JpaDb.java", JPADB)
    write(OUT_JAVA / "com/thesis/config/JpaSupport.java", JPASUPPORT)
    write(OUT_JAVA / "com/thesis/config/SqlRowMapper.java", SQL_ROW)
    write(OUT_JAVA / "com/thesis/config/SqlResultSetExtractor.java", SQL_RSE)
    write(OUT_JAVA / "com/thesis/config/SqlPreparedStatementCreator.java", SQL_PSC)
    write(OUT_JAVA / "com/thesis/config/KeyHolder.java", KEY_HOLDER)
    write(OUT_JAVA / "com/thesis/config/GeneratedKeyHolder.java", GEN_KEY)
    write(OUT_JAVA / "com/thesis/entity/NoticeEntity.java", NOTICE_ENTITY)
    write(OUT_JAVA / "com/thesis/repository/NoticeRepository.java", NOTICE_REPO)
    write(OUT_JAVA / "com/thesis/service/NoticeStore.java", NOTICE_STORE)
    write(OUT_JAVA / "com/thesis/ThesisApplication.java", APP)
    write(OUT / "backend" / "pom.xml", POM)

    # DomainRuntimeBinder comment tweak if present
    binder = OUT_JAVA / "com/thesis/config/DomainRuntimeBinder.java"
    if binder.is_file():
        t = binder.read_text(encoding="utf-8")
        t = t.replace("JdbcSupport", "JpaSupport")
        binder.write_text(t, encoding="utf-8", newline="\n")

    print(f"wrote {OUT}")
    n = len(list(OUT.rglob("*")))
    print(f"files={n}")


if __name__ == "__main__":
    main()
