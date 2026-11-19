package com.thesis.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializer;
import org.springframework.session.data.redis.config.annotation.web.http.EnableRedisHttpSession;

/**
 * 登录会话存 Redis（Spring Session），与业务层 HttpSession / AdminAuth 调用面不变。
 * 答辩口径：Session 属性进 Redis，后端重启后未过期会话可续；在线踢人仍走 MySQL sys_auth_session。
 */
@Configuration
@EnableRedisHttpSession(maxInactiveIntervalInSeconds = 1800)
public class RedisSessionConfig {

    /** Session 属性用 JSON，便于 Redis CLI 抽查（勿存不可序列化对象）。 */
    @Bean
    public RedisSerializer<Object> springSessionDefaultRedisSerializer() {
        return new GenericJackson2JsonRedisSerializer();
    }
}
