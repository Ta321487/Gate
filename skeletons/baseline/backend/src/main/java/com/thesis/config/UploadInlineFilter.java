package com.thesis.config;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.Locale;

/** 访问 /uploads 时对图片/PDF 加 inline，避免浏览器直接下载。 */
@Component
@Order(1)
public class UploadInlineFilter implements Filter {

    @Override
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest request = (HttpServletRequest) req;
        HttpServletResponse response = (HttpServletResponse) res;
        String path = request.getRequestURI();
        String ctx = request.getContextPath() == null ? "" : request.getContextPath();
        if (path.startsWith(ctx + "/uploads/")) {
            String lower = path.toLowerCase(Locale.ROOT);
            if (lower.endsWith(".png") || lower.endsWith(".jpg") || lower.endsWith(".jpeg")
                    || lower.endsWith(".gif") || lower.endsWith(".webp") || lower.endsWith(".bmp")
                    || lower.endsWith(".svg") || lower.endsWith(".pdf")) {
                response.setHeader("Content-Disposition", "inline");
            }
        }
        chain.doFilter(req, res);
    }
}
