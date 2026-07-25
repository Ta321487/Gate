package com.thesis.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.context.SecurityContextHolderFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.List;

/**
 * Spring Security 过滤器链：会话鉴权 + 公开接口白名单。
 * 角色细粒度仍由业务层 AdminAuth 校验（与无 Security 包行为对齐）。
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final SessionAuthFilter sessionAuthFilter;
    private final ObjectMapper objectMapper;

    public SecurityConfig(SessionAuthFilter sessionAuthFilter, ObjectMapper objectMapper) {
        this.sessionAuthFilter = sessionAuthFilter;
        this.objectMapper = objectMapper;
    }

    /** 登录走 AuthController + HttpSession，禁用默认内存用户与随机密码日志。 */
    @Bean
    public UserDetailsService userDetailsService() {
        return new InMemoryUserDetailsManager();
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .cors(Customizer.withDefaults())
                .httpBasic(AbstractHttpConfigurer::disable)
                .formLogin(AbstractHttpConfigurer::disable)
                .logout(AbstractHttpConfigurer::disable)
                // 登录态在 AuthController 已写入 HttpSession；默认 changeSessionId
                // 会在 SessionAuthFilter 首次桥接认证时换新 JSESSIONID，与 SPA 并发 XHR 竞态导致 401 踢登录。
                .sessionManagement(s -> s
                        .sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED)
                        .sessionFixation(sf -> sf.none()))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(
                                "/api/auth/**",
                                "/api/meta",
                                "/api/gate/**",
                                "/actuator/health",
                                "/actuator/health/**",
                                "/error",
                                "/uploads/**")
                        .permitAll()
                        .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
                        .requestMatchers(HttpMethod.GET,
                                "/api/notices/**",
                                "/api/archive/**",
                                "/api/guestbook/**",
                                "/api/items/**",
                                "/api/recommend/**",
                                "/api/categories/**",
                                "/api/tags/**",
                                "/api/slots/**",
                                "/api/lookups/**")
                        .permitAll()
                        .requestMatchers("/api/dm/**").authenticated()
                        .requestMatchers(HttpMethod.POST, "/api/upload").permitAll()
                        .anyRequest().authenticated())
                .exceptionHandling(ex -> ex.authenticationEntryPoint((req, res, e) -> {
                    res.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                    res.setCharacterEncoding("UTF-8");
                    res.setContentType(MediaType.APPLICATION_JSON_VALUE);
                    objectMapper.writeValue(
                            res.getOutputStream(),
                            R.fail(ErrorCode.UNAUTHORIZED, "未登录"));
                }))
                .addFilterAfter(sessionAuthFilter, SecurityContextHolderFilter.class);
        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration c = new CorsConfiguration();
        c.setAllowedOriginPatterns(List.of("*"));
        c.setAllowedMethods(List.of("*"));
        c.setAllowedHeaders(List.of("*"));
        c.setAllowCredentials(true);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", c);
        source.registerCorsConfiguration("/uploads/**", c);
        return source;
    }
}
