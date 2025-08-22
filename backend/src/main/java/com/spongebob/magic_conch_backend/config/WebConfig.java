package com.spongebob.magic_conch_backend.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

// 让浏览器允许前端页面（例如 http://localhost:5173）安全地调用本后端接口，解决“同源策略”导致的跨域请求被浏览器拦截的问题。
// 标记为配置类，Spring 启动时自动加载
@Configuration
public class WebConfig implements WebMvcConfigurer {

    // 重写 WebMvcConfigurer 的跨域设置方法，registry是Spring提供的CORS注册器，用来声明跨域规则
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")      // 匹配所有接口路径（/** 表示全部
                .allowedOrigins("http://localhost:5173")  // 只允许来自 http://localhost:5173 的跨域请求
                .allowedMethods("GET", "POST", "PUT", "DELETE")     // 允许的 HTTP 方法
                .allowCredentials(true);        // 允许携带 Cookie / Authorization 等凭证
    }
}
