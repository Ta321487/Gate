package com.thesis.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * 把既有 HttpSession（uid/role）桥进 Spring Security 上下文。
 * 登录仍走 AuthController；本过滤器只负责「已登录会话 → authenticated」。
 */
@Component
public class SessionAuthFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(
            HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        if (SecurityContextHolder.getContext().getAuthentication() == null) {
            HttpSession session = request.getSession(false);
            if (session != null && session.getAttribute("uid") != null) {
                String uid = String.valueOf(session.getAttribute("uid"));
                String role = String.valueOf(session.getAttribute("role"));
                List<SimpleGrantedAuthority> auths = new ArrayList<>();
                auths.add(new SimpleGrantedAuthority("ROLE_USER"));
                if ("admin".equals(role)) {
                    auths.add(new SimpleGrantedAuthority("ROLE_ADMIN"));
                }
                Object sa = session.getAttribute("superAdmin");
                if (sa instanceof Boolean b && b) {
                    auths.add(new SimpleGrantedAuthority("ROLE_SUPER_ADMIN"));
                }
                SecurityContextHolder.getContext().setAuthentication(
                        new UsernamePasswordAuthenticationToken(uid, null, auths));
            }
        }
        chain.doFilter(request, response);
    }
}
