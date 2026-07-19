package com.thesis;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 图书领域：使用 MySQL（schema.sql + 工厂 ensure）；不再排除 DataSource。
 */
@SpringBootApplication
public class ThesisApplication {
    public static void main(String[] args) {
        SpringApplication.run(ThesisApplication.class, args);
    }
}
