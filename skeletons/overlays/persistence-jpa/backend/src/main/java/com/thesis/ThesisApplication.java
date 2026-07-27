package com.thesis;

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
