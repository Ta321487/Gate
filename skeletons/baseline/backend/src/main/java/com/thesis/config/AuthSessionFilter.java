package com.thesis.config;

import com.thesis.service.AuthSessionStore;
import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * XA-02：被踢会话下一请求作废。无登记行（升级前会话）放行。
 */
@Component
@Order(2)
public class AuthSessionFilter implements Filter {

    @Override
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest request = (HttpServletRequest) req;
        HttpServletResponse response = (HttpServletResponse) res;
        HttpSession session = request.getSession(false);
        if (session != null && session.getAttribute("uid") != null) {
            String sid = session.getId();
            if (!AuthSessionStore.isAlive(sid)) {
                try {
                    session.invalidate();
                } catch (IllegalStateException ignored) {
                }
                if (request.getRequestURI() != null && request.getRequestURI().contains("/api/")) {
                    response.setStatus(HttpServletResponse.SC_OK);
                    response.setCharacterEncoding(StandardCharsets.UTF_8.name());
                    response.setContentType("application/json;charset=UTF-8");
                    response.getWriter().write("{\"code\":40100,\"message\":\"登录已失效，请重新登录\",\"data\":null}");
                    return;
                }
            } else {
                AuthSessionStore.touch(sid);
            }
        }
        chain.doFilter(req, res);
    }
}
